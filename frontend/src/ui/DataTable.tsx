/**
 * The table every list of records in rows is drawn with (U-D14): a collection, a record panel's
 * children and its relationships. It owns the table's look and behaviour — sortable and resizable
 * headers, the continuous scroll window (ADR-030), the loading rows and the empty state, the row's
 * type colour (ADR-040) and the narrow layout's column toggle. What a row is, how it is keyed, what
 * its cells show and what can be done with it stay with the caller: `ui/ObjectTable` lists records,
 * `RelationsPanel` lists relationships, where one record may stand on two rows, the mapping grid
 * lists sources with their targets and the relation matrix lists rows with a cell per column record
 * (a column may be a row header, carry its own header content and cell attributes, and the table its
 * own role and keyboard handler, which a grid needs).
 *
 * Column widths (UA4 revision): the table lays its columns out by their content until the user
 * sizes one. The first resize keeps every column at the width it had and changes only the one being
 * dragged; from then on the widths are fixed, a column may be narrower than its content (the cell
 * ends in an ellipsis), and the actions column, or the table's own width, takes up the difference.
 *
 * Until then the widths stay as the first rows laid them out: the window holds different rows as it
 * scrolls, and a table laid out by its content moved its columns, and with them the rows' heights
 * and the rows under the reader, at every page (reported 2026-10-19). They are measured again when
 * the columns, the density or the table's room change. Cells still wrap, except in a table of
 * `oneLine` rows (a record list, 0.12 LS1, D375): once its columns are laid out, each cell keeps to
 * one line and ends in an ellipsis, so every row is as tall as the first and nothing is corrected
 * while the list scrolls.
 *
 * Columns that fit (0.17 SH1): in a table that asks for it (`foldColumns`) the identity column is never
 * cut, and the columns that still do not fit once the others are cut to their floor fold behind
 * "Columns · n of m", from the right; the control is the phone layout's column toggle, and the folded
 * columns are its `mobile-secondary-column`s. Showing them all scrolls sideways as before. Columns the
 * person sized keep their widths and nothing folds.
 *
 * The resize handles are not inside the header cells (UA7): a header's name is its content, and a
 * handle there added "Resize … column" to it. They stand in one layer before the table, sticky
 * at the top of the scroll window, each at its column's measured right edge.
 */

import {
  memo,
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type HTMLAttributes,
  type ReactNode,
  type Ref,
} from "react";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { recentlyScrolled } from "@/lib/scrollActivity";
import type { Hue } from "@/model/hues";
import { useCellReveal } from "@/ui/CellReveal";
import { EmptyState } from "@/ui/EmptyState";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";
import { SortAnnouncement, SortHeader, headerSort, type TableSort } from "@/ui/TableSort";
import { activeRows, canHover, CellRoom, RowActive, type ActiveRows } from "@/ui/tableCell";

const LOADING_ROWS = 6;
/** Where the table lays out its columns (sized or frozen); below it, the narrow layout by content. */
const WIDE_LAYOUT = "(min-width: 761px)";
/** The narrowest a column is made when the table is fitted to its room. */
const FIT_FLOOR = 120;
/** The most a folding table gives a column that is not the name (0.17 SH1): a longer value ends in an ellipsis. */
const NATURAL_CAP = 320;

/**
 * The widths cut down to the room: the widest columns (never a fixed one) give up the excess until
 * they meet the next widest, down to FIT_FLOOR. What cannot be cut scrolls (`.object-table`'s edge shade).
 */
function fitWidths(widths: number[], room: number, fixed: Set<number>): number[] {
  const result = [...widths];
  let excess = result.reduce((sum, width) => sum + width, 0) - room;
  while (excess > 0.5) {
    const open = result.map((width, index) => ({ width, index })).filter(({ index }) => !fixed.has(index));
    const top = Math.max(...open.map(({ width }) => width));
    if (top <= FIT_FLOOR) break;
    const widest = open.filter(({ width }) => width > top - 0.01);
    const next = Math.max(FIT_FLOOR, ...open.filter(({ width }) => width <= top - 0.01).map(({ width }) => width));
    const cut = Math.min((top - next) * widest.length, excess);
    for (const { index } of widest) result[index] = (result[index] ?? 0) - cut / widest.length;
    excess -= cut;
  }
  return result;
}

/**
 * The columns that do not fit `room`, from the right (0.17 SH1): the widths are the table's, the
 * selection column and the actions column among them (`leading` columns come before the first of
 * `columns`). A pinned column (the identity, one that says it always shows) is never folded. A folded column
 * that still fits what the others leave is kept, so one wide column does not hide the narrow ones after it.
 */
export function columnsToFold(
  columns: readonly { key: string; pinned: boolean }[],
  widths: readonly number[],
  room: number,
  leading: number,
): string[] {
  const folded: string[] = [];
  let total = widths.reduce((sum, width) => sum + width, 0);
  for (let position = columns.length - 1; position >= 0 && total > room + 0.5; position -= 1) {
    if (columns[position].pinned) continue;
    folded.push(columns[position].key);
    total -= widths[leading + position] ?? 0;
  }
  // A wide column in the middle (a long identifier) must not cost every column after it: of the folded ones,
  // those that still fit the room that is left come back, the leftmost first.
  for (let position = 0; position < columns.length; position += 1) {
    const at = folded.indexOf(columns[position].key);
    const width = widths[leading + position] ?? 0;
    if (at < 0 || total + width > room + 0.5) continue;
    folded.splice(at, 1);
    total += width;
  }
  return folded;
}

/** The range a column may be sized to; a stored width outside it is ignored. */
export const COLUMN_WIDTH = { min: 48, max: 800 } as const;

export interface DataColumn<Row> {
  /** The column's field (or another stable key): its sort field and the key of its stored width. */
  key: string;
  label: string;
  /** The cell's content; `index` is the row's place in the whole list, for a cell that reads its neighbour. */
  cell: (row: Row, index: number) => ReactNode;
  /** The header's content where it is more than the label (the matrix's column name under its label). */
  header?: ReactNode;
  /** Stays on narrow screens; when any column says so, the others are the "Show all" ones (the identity column always stays). */
  alwaysShown?: boolean;
  /** The column names the row: its cells are row headers (`th scope="row"`), not data cells. */
  rowHeader?: boolean;
  /** A class for the column's header and its cells. */
  className?: string;
  /** The header cell's own attributes (a title, a column index). */
  headerProps?: CellAttributes;
  /** A cell's own attributes: a grid's role, tab stop, click and focus handlers. */
  cellProps?: (row: Row, index: number) => CellAttributes;
}

/** A header or data cell's attributes, `data-*` ones included. */
export type CellAttributes = HTMLAttributes<HTMLTableCellElement> & {
  [attribute: `data-${string}`]: string | number | boolean | undefined;
};

export function DataTable<Row>({
  columns,
  identityColumn,
  list,
  rowKey,
  rowFilter,
  rowHue,
  rowAttributes,
  selection,
  actions,
  sorting,
  columnWidths = {},
  onColumnWidths,
  foldColumns = false,
  label,
  noun,
  pageSize,
  seekLabel,
  onAnchorChange,
  compact = false,
  emptyMessage,
  emptyIcon,
  emptyAction,
  whole = false,
  oneLine = false,
  fill = false,
  tableAttributes,
  className,
}: {
  columns: DataColumn<Row>[];
  /** The column that names a row; it stays on narrow screens. Defaults to the first. */
  identityColumn?: string;
  /** The continuous window of rows; the table scrolls it (ADR-030). */
  list: CursorWindow<Row>;
  rowKey: (row: Row) => string;
  /**
   * Leaves out rows the request could not exclude; the others keep their places in the list (a
   * left-out row is drawn with no height).
   */
  rowFilter?: (row: Row) => boolean;
  /** The row's kind of record, which colours it when selected. */
  rowHue?: (row: Row) => Hue | undefined;
  /** The row's own attributes: its class, pointer and keyboard handlers. */
  rowAttributes?: (row: Row) => HTMLAttributes<HTMLTableRowElement>;
  /**
   * The leading selection column (0.9 K1): its header, each row's cell and its width. It is not
   * resized, and it stays on narrow screens.
   */
  selection?: { header: ReactNode; cell: (row: Row) => ReactNode; width: number };
  /**
   * The trailing actions column: its header (which may be visually hidden), each row's cell and the
   * width it needs. Once columns are sized it takes up whatever width the others leave.
   */
  actions?: { header: ReactNode; cell: (row: Row) => ReactNode; width: number; className?: string };
  sorting?: TableSort;
  columnWidths?: Record<string, number>;
  /** Stores the widths after a resize; without it the columns do not resize. */
  onColumnWidths?: (widths: Record<string, number>) => void;
  /** Columns that do not fit the room fold behind "Columns · n of m" (see above). */
  foldColumns?: boolean;
  label: string;
  noun: [string, string];
  pageSize: number;
  seekLabel?: string;
  onAnchorChange?: (anchor: string | undefined) => void;
  compact?: boolean;
  emptyMessage: ReactNode;
  emptyIcon?: ReactNode;
  emptyAction?: ReactNode;
  /**
   * The list is held whole and short (the model editor's tables): no start and end markers and no
   * footer, which serve a list that pages.
   */
  whole?: boolean;
  /** Each cell on one line once the columns are laid out (see above). */
  oneLine?: boolean;
  /** The list fills its page, which does not scroll (`ScrollWindow`'s `fill`, 0.12 LS1, D372). */
  fill?: boolean;
  /** The table's own attributes: a grid's role, its keyboard handler and its column count. */
  tableAttributes?: HTMLAttributes<HTMLTableElement>;
  /** A further class of the scroll window, for a view's own styles over the shared table. */
  className?: string;
}) {
  const [allColumns, setAllColumns] = useState(false);
  // A cut-off cell shows its whole value on hover, focus or a long press (ui/CellReveal).
  const reveal = useCellReveal();
  const headers = useRef(new Map<string, HTMLTableCellElement>());
  const resizers = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState<{ height: number; ends: Record<string, number> }>({ height: 0, ends: {} });
  const identity = identityColumn ?? columns[0]?.key;
  const pinned = columns.filter((column) => column.alwaysShown).map((column) => column.key);
  const mobileKeys = (
    pinned.length
      ? [identity, ...pinned]
      : [identity, ...columns.map((column) => column.key).filter((key) => key !== identity)].slice(0, 3)
  ).filter((key, position, all) => all.indexOf(key) === position);
  const mobileKey = mobileKeys.join("\n");
  const narrowToggle = columns.some((column) => !mobileKeys.includes(column.key));
  const sized = columns.some((column) => columnWidths[column.key] !== undefined);
  const columnCount = columns.length + Number(Boolean(actions)) + Number(Boolean(selection));

  // The widths the first rows laid out (see above), for these columns at this room.
  const table = useRef<HTMLTableElement | null>(null);
  const [room, setRoom] = useState(0);
  const [frozen, setFrozen] = useState<{ key: string; room: number; widths: number[]; folded: string[] }>();
  const freezeKey = [
    columns.map((column) => column.key).join("\n"),
    compact,
    Boolean(selection),
    Boolean(actions),
  ].join("|");
  const shown = frozen && !sized && frozen.key === freezeKey && frozen.room === room ? frozen : undefined;
  const hasRows = list.items.length > 0;
  const settledRows = hasRows && !list.loading;
  // The columns that do not fit, from the right; they are out of the table until "Columns" shows them all.
  const foldedColumns = shown?.folded ?? [];
  const foldedKey = allColumns ? "" : foldedColumns.join("\n");
  // Given to every row, so it changes only with the columns: a new one drew every row again. A column
  // is secondary on a phone when it is not among the few kept, and on a wide screen when it was folded.
  const secondary = useCallback(
    (key: string) => {
      const phone = !mobileKey.split("\n").includes(key);
      const folded = foldedKey !== "" && foldedKey.split("\n").includes(key);
      return phone || folded ? `mobile-secondary-column${folded ? " folded-column" : ""}` : undefined;
    },
    [mobileKey, foldedKey],
  );
  useLayoutEffect(() => {
    const holder = table.current?.parentElement;
    if (!holder || typeof ResizeObserver === "undefined") return;
    // Read the room at once, before the first paint; the observer follows later changes. A browser calls an
    // observer only when it renders, so a page opened in a background tab would otherwise wait unfolded.
    setRoom(holder.clientWidth);
    const observer = new ResizeObserver(() => setRoom(holder.clientWidth));
    observer.observe(holder);
    return () => observer.disconnect();
    // The table is drawn only once the first rows arrive, so the container is found then, not at mount.
  }, [hasRows, list.loading]);
  useLayoutEffect(() => {
    const head = table.current?.tHead?.rows[0];
    if (shown || sized || !settledRows || !room || !head || !window.matchMedia?.(WIDE_LAYOUT).matches) return;
    const element = table.current;
    // A table that folds measures what each column's content needs to show whole: the cells on one
    // line in a table as wide as they ask (`.measuring-columns`), read and put back before it paints.
    let laidOut: number[];
    if (foldColumns && element) {
      element.classList.add("measuring-columns");
      laidOut = Array.from(head.cells, (cell) => Math.ceil(cell.getBoundingClientRect().width));
      element.classList.remove("measuring-columns");
    } else laidOut = Array.from(head.cells, (cell) => cell.getBoundingClientRect().width);
    // One-line cells end in an ellipsis, so the widest data columns give up what the first rows asked
    // for beyond the room instead of pushing the last column and its actions out of sight.
    const identityPosition = columns.findIndex((column) => column.key === identity);
    const fixed = new Set([
      ...(selection ? [0] : []),
      ...(actions ? [laidOut.length - 1] : []),
      // The name is never cut (0.17 SH1): the others give way, then fold.
      ...(foldColumns && identityPosition >= 0 ? [Number(Boolean(selection)) + identityPosition] : []),
    ]);
    // A long free-text value may still end in an ellipsis: a column asks for at most this much.
    const widths: number[] = foldColumns
      ? laidOut.map((width, position) => (fixed.has(position) ? width : Math.min(width, NATURAL_CAP)))
      : oneLine
        ? fitWidths(laidOut, room, fixed)
        : laidOut;
    const folded = foldColumns
      ? columnsToFold(
          columns.map((column) => ({ key: column.key, pinned: column.key === identity || !!column.alwaysShown })),
          widths,
          room,
          Number(Boolean(selection)),
        )
      : [];
    // What the kept columns leave is theirs (0.17 SH1): the capped ones first, up to what their content
    // asks, then the name column, so the table spans its container.
    if (foldColumns) {
      const kept = (position: number) => !folded.includes(columns[position - Number(Boolean(selection))]?.key ?? "");
      let free = room - widths.reduce((sum, width, position) => sum + (kept(position) ? width : 0), 0);
      if (free > 0) {
        for (let position = 0; position < widths.length && free > 0; position += 1) {
          if (!kept(position) || fixed.has(position)) continue;
          const more = Math.min(free, laidOut[position] - widths[position]);
          if (more > 0) {
            widths[position] += more;
            free -= more;
          }
        }
        if (free > 0 && identityPosition >= 0) widths[Number(Boolean(selection)) + identityPosition] += free;
      }
    }
    setFrozen({ key: freezeKey, room, widths, folded });
  }, [shown, sized, settledRows, room, freezeKey, oneLine, selection, actions, foldColumns, columns, identity]);
  const leading = Number(Boolean(selection));
  // Each column's content width, read once from the first drawn row whenever the columns are laid
  // out anew (frozen or sized), so its cells need not measure themselves (ui/tableCell, 0.11 X6).
  const [rooms, setRooms] = useState<{ of: string; widths: Record<string, number> }>();
  const roomsKey = `${freezeKey}|${room}|${shown ? shown.widths.join(",") : ""}|${
    sized ? columns.map((column) => columnWidths[column.key] ?? "").join(",") : ""
  }`;
  const roomsNow = rooms?.of === roomsKey ? rooms.widths : undefined;
  useLayoutEffect(() => {
    if (roomsNow || !(shown || sized) || !window.matchMedia?.(WIDE_LAYOUT).matches) return;
    const row = table.current?.tBodies[0]?.querySelector<HTMLTableRowElement>("tr[data-row-key]");
    if (!row) return;
    const widths: Record<string, number> = {};
    columns.forEach((column, position) => {
      const cell = row.cells[leading + position];
      if (!cell) return;
      const style = getComputedStyle(cell);
      widths[column.key] =
        cell.clientWidth - (Number.parseFloat(style.paddingLeft) || 0) - (Number.parseFloat(style.paddingRight) || 0);
    });
    setRooms({ of: roomsKey, widths });
  }, [roomsNow, shown, sized, columns, roomsKey, leading, list.items.length]);
  // The row the pointer is over and the row holding focus draw their cells' edit controls; on a
  // screen without hover every row does (ui/tableCell).
  const [active] = useState<ActiveRows>(activeRows);
  const [hoverable] = useState(canHover);
  const rowOf = (target: EventTarget | null) =>
    target instanceof Element ? target.closest<HTMLElement>("tr[data-row-key]")?.dataset.rowKey : undefined;
  // Rows moving under a still pointer while the list scrolls are not hovered: each would draw its
  // edit icons; the pointer's own movement points at a row again (0.12 LS1, D373).
  const hover = (event: React.PointerEvent<HTMLElement>) =>
    active.setHovered(recentlyScrolled() ? undefined : rowOf(event.target));
  const bodyHandlers = {
    ...reveal.handlers,
    onPointerOver: (event: React.PointerEvent<HTMLElement>) => {
      reveal.handlers.onPointerOver(event);
      hover(event);
    },
    onPointerMove: (event: React.PointerEvent<HTMLElement>) => {
      reveal.handlers.onPointerMove(event);
      hover(event);
    },
    onPointerLeave: (event: React.PointerEvent<HTMLElement>) => {
      reveal.handlers.onPointerLeave(event);
      active.setHovered(undefined);
    },
    onFocus: (event: React.FocusEvent<HTMLElement>) => {
      reveal.handlers.onFocus(event);
      active.setFocused(rowOf(event.target));
    },
    onBlur: (event: React.FocusEvent<HTMLElement>) => {
      reveal.handlers.onBlur();
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) active.setFocused(undefined);
    },
  };
  /** A header cell's frozen width, by its place in the row. */
  const frozenWidth = (position: number): CSSProperties | undefined =>
    shown?.widths[position] !== undefined ? { width: `${shown.widths[position]}px` } : undefined;
  // A placeholder row's cells, in the table's columns (D163).
  const actionsClass = `actions-column ${actions?.className ?? "record-actions-column"}`;
  const cells = [
    ...(selection ? ["selection-column"] : []),
    ...columns.map((column) => secondary(column.key)),
    ...(actions ? [actionsClass] : []),
  ];

  // Where each column ends, for its resize handle; measured again whenever a header changes size.
  const columnKeys = columns.map((column) => column.key).join("\n");
  useLayoutEffect(() => {
    if (!onColumnWidths) return;
    const measure = () =>
      setEdges((current) => {
        const nodes = Array.from(headers.current);
        const origin = resizers.current?.getBoundingClientRect().left ?? 0;
        const height = nodes[0]?.[1].offsetHeight ?? 0;
        const ends = Object.fromEntries(
          nodes.map(([key, node]) => {
            const box = node.getBoundingClientRect();
            return [key, box.width ? Math.round(box.right - origin) : 0];
          }),
        );
        const same =
          height === current.height &&
          Object.keys(ends).length === Object.keys(current.ends).length &&
          Object.entries(ends).every(([key, end]) => current.ends[key] === end);
        return same ? current : { height, ends };
      });
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    headers.current.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [onColumnWidths, columnKeys]);

  /** Every shown column's width as drawn now: stored, or measured from its header. */
  function drawnWidths() {
    return Object.fromEntries(
      columns.map((column) => [
        column.key,
        columnWidths[column.key] ??
          (Math.ceil(headers.current.get(column.key)?.getBoundingClientRect().width ?? 0) || 180),
      ]),
    );
  }

  return (
    <>
      {foldedColumns.length > 0 && (
        <div className="table-controls table-controls-folded">
          <button
            type="button"
            className="secondary folded-columns-toggle"
            aria-expanded={allColumns}
            onClick={() => setAllColumns(!allColumns)}
          >
            Columns · {columns.length - (allColumns ? 0 : foldedColumns.length)} of {columns.length}
          </button>
        </div>
      )}
      {narrowToggle && (
        <div className="table-controls table-controls-narrow">
          <button
            className="secondary mobile-columns-toggle"
            aria-expanded={allColumns}
            onClick={() => setAllColumns(!allColumns)}
          >
            {allColumns ? "Show fewer columns" : `Show all ${columns.length} columns`}
          </button>
        </div>
      )}
      {sorting && <SortAnnouncement sorting={sorting} />}
      <ScrollWindow
        list={list}
        label={label}
        noun={noun}
        pageSize={pageSize}
        seekLabel={seekLabel}
        onAnchorChange={onAnchorChange}
        fill={fill}
        {...(whole ? { edgeMarkers: "partial" as const, footer: false } : {})}
        className={`table-wrap object-table${compact ? " density-compact" : ""}${allColumns ? " show-all-columns" : ""}${className ? ` ${className}` : ""}`}
      >
        {(drawn) => (
          <>
            {onColumnWidths && (
              <div
                ref={resizers}
                className="column-resizers"
                style={{ "--header-row-height": `${edges.height}px` } as CSSProperties}
              >
                {columns
                  .filter((column) => !foldedKey.split("\n").includes(column.key))
                  .map((column) => (
                    <ResizeHandle
                      key={column.key}
                      className="column-resizer"
                      label={`Resize ${column.label} column`}
                      value={columnWidths[column.key] ?? 180}
                      min={COLUMN_WIDTH.min}
                      max={COLUMN_WIDTH.max}
                      start={() => drawnWidths()[column.key]}
                      onChange={(next) => onColumnWidths({ ...drawnWidths(), [column.key]: next })}
                      style={{ left: `${(edges.ends[column.key] ?? 0) - 4}px` }}
                    />
                  ))}
              </div>
            )}
            <table
              {...tableAttributes}
              ref={table}
              className={
                [
                  sized ? `sized-columns${actions ? " sized-columns-fill" : ""}` : shown ? "frozen-columns" : "",
                  oneLine && (sized || shown) ? "one-line-rows" : "",
                ]
                  .filter(Boolean)
                  .join(" ") || undefined
              }
              style={
                shown
                  ? {
                      // The columns that stay, and for a folding table the whole room: it fills its container.
                      width: `${Math.max(
                        shown.widths.reduce(
                          (sum, width, position) =>
                            sum +
                            (foldedKey && foldedKey.split("\n").includes(columns[position - leading]?.key ?? "")
                              ? 0
                              : width),
                          0,
                        ),
                        foldColumns ? shown.room : 0,
                      )}px`,
                    }
                  : sized
                    ? ({
                        "--table-width": `${columns.reduce(
                          (sum, column) => sum + (columnWidths[column.key] ?? 180),
                          (actions?.width ?? 0) + (selection?.width ?? 0),
                        )}px`,
                      } as CSSProperties)
                    : undefined
              }
              aria-busy={list.loading || undefined}
              aria-rowcount={list.totalCount !== null && list.items.length > 0 ? list.totalCount + 1 : undefined}
            >
              <caption className="visually-hidden">{label}</caption>
              <thead>
                <tr aria-rowindex={1}>
                  {selection && (
                    <th
                      scope="col"
                      className="selection-column"
                      style={{ "--selection-width": `${selection.width}px`, ...frozenWidth(0) } as CSSProperties}
                    >
                      {selection.header}
                    </th>
                  )}
                  {columns.map((column, position) => {
                    // Once any column is sized, every column is: one without a stored width takes the default.
                    const width = columnWidths[column.key] ?? (sized ? 180 : undefined);
                    return (
                      <th
                        {...column.headerProps}
                        key={column.key}
                        ref={(node) => {
                          if (node) headers.current.set(column.key, node);
                          else headers.current.delete(column.key);
                        }}
                        className={cellClass(secondary(column.key), column.className, column.headerProps?.className)}
                        scope="col"
                        aria-sort={sorting && headerSort(sorting, column.key)}
                        style={
                          width !== undefined
                            ? ({ "--column-width": `${width}px` } as CSSProperties)
                            : frozenWidth(leading + position)
                        }
                      >
                        {sorting ? (
                          <SortHeader field={column.key} label={column.label} sorting={sorting} />
                        ) : (
                          (column.header ?? column.label)
                        )}
                      </th>
                    );
                  })}
                  {actions && (
                    <th
                      scope="col"
                      className={`actions-column ${actions.className ?? "record-actions-column"}`}
                      style={
                        {
                          "--actions-width": `${actions.width}px`,
                          ...frozenWidth(leading + columns.length),
                        } as CSSProperties
                      }
                    >
                      {actions.header}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody {...bodyHandlers}>
                {list.loading && list.items.length === 0 ? (
                  // Rows in the table's own shape while the first page loads; one status announces it.
                  Array.from({ length: LOADING_ROWS }, (_, row) => (
                    <tr key={row} className="loading-row">
                      {selection && <td className="selection-column" />}
                      {columns.map((column, index) => (
                        <td key={column.key} className={secondary(column.key)}>
                          {row === 0 && index === 0 && (
                            <span className="visually-hidden" role="status">
                              Loading {noun[1]}…
                            </span>
                          )}
                          <span className="skeleton-line" aria-hidden="true" />
                        </td>
                      ))}
                      {actions && <td className={`actions-column ${actions.className ?? "record-actions-column"}`} />}
                    </tr>
                  ))
                ) : list.items.length === 0 ? (
                  <tr>
                    <td colSpan={columnCount} className="empty-row">
                      <EmptyState icon={emptyIcon} action={emptyAction}>
                        {emptyMessage}
                      </EmptyState>
                    </td>
                  </tr>
                ) : (
                  <>
                    <WindowSpacer as="tr" edge="before" height={drawn.before} columns={columnCount} />
                    {drawn.rows.map(({ index, item, size }) =>
                      item === undefined ? (
                        <WindowPlaceholder
                          key={`placeholder-${index}`}
                          as="tr"
                          index={index}
                          size={size}
                          cells={cells}
                        />
                      ) : rowFilter && !rowFilter(item) ? (
                        <tr key={rowKey(item)} ref={drawn.measure} data-row-index={index} hidden />
                      ) : (
                        <DataRow
                          key={rowKey(item)}
                          rowRef={drawn.measure}
                          rooms={roomsNow}
                          active={hoverable ? active : undefined}
                          rowId={rowKey(item)}
                          row={item}
                          index={index}
                          columns={columns}
                          secondary={secondary}
                          rowHue={rowHue}
                          rowAttributes={rowAttributes}
                          selection={selection}
                          actions={actions}
                        />
                      ),
                    )}
                    <WindowSpacer as="tr" edge="after" height={drawn.after} columns={columnCount} />
                  </>
                )}
              </tbody>
            </table>
          </>
        )}
      </ScrollWindow>
      {reveal.overlay}
    </>
  );
}

/**
 * One row, as a component of its own: a page arriving while the reader scrolls is drawn in the
 * background (`useCursorWindow`), and React can pause that work only between components, so rows
 * drawn inline in the table held up scrolling for as long as all of them took (reported 2026-10-19).
 *
 * Memoised (0.11 X6): scrolling changes the range `ScrollWindow` draws without drawing the table
 * again, so a row already on the page gets the very same props and is skipped; only rows entering
 * the range are drawn. Drawing every row in range at each step made scrolling lag (the user,
 * 2026-10-19). The table's own functions to the rows are stable, and what the caller gives
 * (`ui/ObjectTable`) changes only with what the rows show, so the table drawing again (a cell's
 * whole value shown, a page arriving) draws no row that is already on the page (0.12 LS1, D373).
 */
const DataRow = memo(DataRowContent) as typeof DataRowContent;

function DataRowContent<Row>({
  rowRef,
  rooms,
  active,
  rowId,
  row,
  index,
  columns,
  secondary,
  rowHue,
  rowAttributes,
  selection,
  actions,
}: {
  rowRef: Ref<HTMLTableRowElement>;
  /** Each column's content width, once the table measured it. */
  rooms?: Record<string, number>;
  /** Which rows are active; every row is when not given (a screen without hover). */
  active?: ActiveRows;
  rowId: string;
  row: Row;
  index: number;
  columns: DataColumn<Row>[];
  secondary: (key: string) => string | undefined;
  rowHue?: (row: Row) => Hue | undefined;
  rowAttributes?: (row: Row) => HTMLAttributes<HTMLTableRowElement>;
  selection?: { cell: (row: Row) => ReactNode };
  actions?: { cell: (row: Row) => ReactNode; className?: string };
}) {
  const isActive = useSyncExternalStore(
    active?.subscribe ?? noSubscription,
    () => !active || active.isActive(rowId),
    () => true,
  );
  return (
    <RowActive.Provider value={isActive}>
      <tr
        ref={rowRef}
        data-row-key={rowId}
        data-row-index={index}
        aria-rowindex={index + 2}
        data-hue={rowHue?.(row)}
        {...rowAttributes?.(row)}
      >
        {selection && <td className="selection-column">{selection.cell(row)}</td>}
        {columns.map((column) => {
          const attributes = column.cellProps?.(row, index);
          const Cell = column.rowHeader ? "th" : "td";
          return (
            <Cell
              {...attributes}
              key={column.key}
              scope={column.rowHeader ? "row" : undefined}
              className={cellClass(secondary(column.key), column.className, attributes?.className)}
              // A row header wraps its name; only data cells end in an ellipsis and reveal their value.
              data-reveal={column.rowHeader ? undefined : ""}
            >
              <CellRoom.Provider value={rooms?.[column.key]}>{column.cell(row, index)}</CellRoom.Provider>
            </Cell>
          );
        })}
        {actions && (
          <td className={`actions-column ${actions.className ?? "record-actions-column"}`}>{actions.cell(row)}</td>
        )}
      </tr>
    </RowActive.Provider>
  );
}

const noSubscription = () => () => undefined;

const cellClass = (...names: (string | undefined)[]) => names.filter(Boolean).join(" ") || undefined;
