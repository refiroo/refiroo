/**
 * The table every list of records in rows is drawn with (U-D14): a collection, a record panel's
 * children and its relationships. It owns the table's look and behaviour — sortable and resizable
 * headers, the continuous scroll window (ADR-030), the loading rows and the empty state, the row's
 * type colour (ADR-040) and the narrow layout's column toggle. What a row is, how it is keyed, what
 * its cells show and what can be done with it stay with the caller: `ui/ObjectTable` lists records,
 * `RelationsPanel` lists relationships, where one record may stand on two rows.
 *
 * Column widths (UA4 revision): the table lays its columns out by their content until the user
 * sizes one. The first resize keeps every column at the width it had and changes only the one being
 * dragged; from then on the widths are fixed, a column may be narrower than its content (the cell
 * ends in an ellipsis), and the actions column, or the table's own width, takes up the difference.
 *
 * Until then the widths stay as the first rows laid them out: the window holds different rows as it
 * scrolls, and a table laid out by its content moved its columns, and with them the rows' heights
 * and the rows under the reader, at every page (reported 2026-10-19). They are measured again when
 * the columns, the density or the table's room change. Cells still wrap.
 *
 * The resize handles are not inside the header cells (UA7): a header's name is its content, and a
 * handle there added "Resize … column" to it. They stand in one layer before the table, sticky
 * at the top of the scroll window, each at its column's measured right edge.
 */

import {
  memo,
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
/** The range a column may be sized to; a stored width outside it is ignored. */
export const COLUMN_WIDTH = { min: 48, max: 800 } as const;

export interface DataColumn<Row> {
  /** The column's field (or another stable key): its sort field and the key of its stored width. */
  key: string;
  label: string;
  cell: (row: Row) => ReactNode;
}

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
}) {
  const [allColumns, setAllColumns] = useState(false);
  // A cut-off cell shows its whole value on hover, focus or a long press (ui/CellReveal).
  const reveal = useCellReveal();
  const headers = useRef(new Map<string, HTMLTableCellElement>());
  const resizers = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState<{ height: number; ends: Record<string, number> }>({ height: 0, ends: {} });
  const identity = identityColumn ?? columns[0]?.key;
  const mobileColumns = [identity, ...columns.map((column) => column.key).filter((key) => key !== identity)].slice(
    0,
    3,
  );
  const secondary = (key: string) => (!mobileColumns.includes(key) ? "mobile-secondary-column" : undefined);
  const sized = columns.some((column) => columnWidths[column.key] !== undefined);
  const columnCount = columns.length + Number(Boolean(actions)) + Number(Boolean(selection));

  // The widths the first rows laid out (see above), for these columns at this room.
  const table = useRef<HTMLTableElement>(null);
  const [room, setRoom] = useState(0);
  const [frozen, setFrozen] = useState<{ key: string; room: number; widths: number[] }>();
  const freezeKey = [
    columns.map((column) => column.key).join("\n"),
    compact,
    allColumns,
    Boolean(selection),
    Boolean(actions),
  ].join("|");
  const shown = frozen && !sized && frozen.key === freezeKey && frozen.room === room ? frozen : undefined;
  const settledRows = list.items.length > 0 && !list.loading;
  useLayoutEffect(() => {
    const holder = table.current?.parentElement;
    if (!holder || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setRoom(holder.clientWidth));
    observer.observe(holder);
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    const head = table.current?.tHead?.rows[0];
    if (shown || sized || !settledRows || !room || !head || !window.matchMedia?.(WIDE_LAYOUT).matches) return;
    setFrozen({ key: freezeKey, room, widths: Array.from(head.cells, (cell) => cell.getBoundingClientRect().width) });
  }, [shown, sized, settledRows, room, freezeKey]);
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
  const bodyHandlers = {
    ...reveal.handlers,
    onPointerOver: (event: React.PointerEvent<HTMLElement>) => {
      reveal.handlers.onPointerOver(event);
      active.setHovered(rowOf(event.target));
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
      {columns.length > 3 && (
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
        {...(whole ? { edgeMarkers: "partial" as const, footer: false } : {})}
        className={`table-wrap object-table${compact ? " density-compact" : ""}${allColumns ? " show-all-columns" : ""}`}
      >
        {(drawn) => (
          <>
            {onColumnWidths && (
              <div
                ref={resizers}
                className="column-resizers"
                style={{ "--header-row-height": `${edges.height}px` } as CSSProperties}
              >
                {columns.map((column) => (
                  <ResizeHandle
                    key={column.key}
                    className="column-resizer"
                    label={`Resize ${column.label} column`}
                    value={columnWidths[column.key] ?? 100}
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
              ref={table}
              className={
                sized ? `sized-columns${actions ? " sized-columns-fill" : ""}` : shown ? "frozen-columns" : undefined
              }
              style={
                shown
                  ? { width: `${shown.widths.reduce((sum, width) => sum + width, 0)}px` }
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
                        key={column.key}
                        ref={(node) => {
                          if (node) headers.current.set(column.key, node);
                          else headers.current.delete(column.key);
                        }}
                        className={secondary(column.key)}
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
                          column.label
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
 * 2026-10-19). When the table itself draws again, its functions are new and every row follows.
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
        {columns.map((column) => (
          <td key={column.key} className={secondary(column.key)} data-reveal="">
            <CellRoom.Provider value={rooms?.[column.key]}>{column.cell(row)}</CellRoom.Provider>
          </td>
        ))}
        {actions && (
          <td className={`actions-column ${actions.className ?? "record-actions-column"}`}>{actions.cell(row)}</td>
        )}
      </tr>
    </RowActive.Provider>
  );
}

const noSubscription = () => () => undefined;
