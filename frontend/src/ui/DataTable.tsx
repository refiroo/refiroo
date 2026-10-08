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
 * The resize handles are not inside the header cells (UA7): a header's name is its content, and a
 * handle there added "Resize … column" to it. They stand in one layer before the table, sticky
 * at the top of the scroll window, each at its column's measured right edge.
 */

import { useLayoutEffect, useRef, useState, type CSSProperties, type HTMLAttributes, type ReactNode } from "react";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import type { Hue } from "@/model/hues";
import { EmptyState } from "@/ui/EmptyState";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { SortAnnouncement, SortHeader, headerSort, type TableSort } from "@/ui/TableSort";

const LOADING_ROWS = 6;
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
}: {
  columns: DataColumn<Row>[];
  /** The column that names a row; it stays on narrow screens. Defaults to the first. */
  identityColumn?: string;
  /** The continuous window of rows; the table scrolls it (ADR-030). */
  list: CursorWindow<Row>;
  rowKey: (row: Row) => string;
  /** Leaves out rows the request could not exclude; the others keep their positions in the list. */
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
}) {
  const [allColumns, setAllColumns] = useState(false);
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
  const rows = list.items.flatMap((row, position) =>
    !rowFilter || rowFilter(row) ? [{ row, index: list.startIndex + position }] : [],
  );
  const columnCount = columns.length + Number(Boolean(actions)) + Number(Boolean(selection));

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
        className={`table-wrap object-table${compact ? " density-compact" : ""}${allColumns ? " show-all-columns" : ""}`}
      >
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
          className={sized ? `sized-columns${actions ? " sized-columns-fill" : ""}` : undefined}
          style={
            sized
              ? ({
                  "--table-width": `${columns.reduce(
                    (sum, column) => sum + (columnWidths[column.key] ?? 100),
                    (actions?.width ?? 0) + (selection?.width ?? 0),
                  )}px`,
                } as CSSProperties)
              : undefined
          }
          aria-busy={list.loading || undefined}
          aria-rowcount={list.totalCount !== null && rows.length > 0 ? list.totalCount + 1 : undefined}
        >
          <caption className="visually-hidden">{label}</caption>
          <thead>
            <tr aria-rowindex={1}>
              {selection && (
                <th
                  scope="col"
                  className="selection-column"
                  style={{ "--selection-width": `${selection.width}px` } as CSSProperties}
                >
                  {selection.header}
                </th>
              )}
              {columns.map((column) => {
                // Once any column is sized, every column is: one without a stored width takes the default.
                const width = columnWidths[column.key] ?? (sized ? 100 : undefined);
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
                    style={width !== undefined ? ({ "--column-width": `${width}px` } as CSSProperties) : undefined}
                  >
                    {sorting ? <SortHeader field={column.key} label={column.label} sorting={sorting} /> : column.label}
                  </th>
                );
              })}
              {actions && (
                <th
                  scope="col"
                  className={`actions-column ${actions.className ?? "record-actions-column"}`}
                  style={{ "--actions-width": `${actions.width}px` } as CSSProperties}
                >
                  {actions.header}
                </th>
              )}
            </tr>
          </thead>
          <tbody>
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
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columnCount} className="empty-row">
                  <EmptyState icon={emptyIcon} action={emptyAction}>
                    {emptyMessage}
                  </EmptyState>
                </td>
              </tr>
            ) : (
              rows.map(({ row, index }) => {
                const key = rowKey(row);
                return (
                  <tr
                    key={key}
                    data-row-key={key}
                    data-row-index={index}
                    aria-rowindex={index + 2}
                    data-hue={rowHue?.(row)}
                    {...rowAttributes?.(row)}
                  >
                    {selection && <td className="selection-column">{selection.cell(row)}</td>}
                    {columns.map((column) => (
                      <td key={column.key} className={secondary(column.key)}>
                        {column.cell(row)}
                      </td>
                    ))}
                    {actions && (
                      <td className={`actions-column ${actions.className ?? "record-actions-column"}`}>
                        {actions.cell(row)}
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </ScrollWindow>
    </>
  );
}
