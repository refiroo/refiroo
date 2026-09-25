import { useState, type ReactNode } from "react";
import type { EngineModel, ObjectItem } from "@/types";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { formatValue } from "@/ui/formatValue";
import { attributeName, fieldValue } from "@/model/fields";
import { ResizeHandle } from "@/ui/ResizeHandle";

export function ObjectTable({
  compact = false,
  identityColumn,
  sort,
  sortFields = [],
  onSort,
  model,
  columns,
  list,
  pageSize,
  noun = ["record", "records"],
  seekLabel,
  onAnchorChange,
  onOpen,
  selectedId,
  renderActions,
  label = "Objects",
  emptyMessage = "Nothing to show yet.",
  columnWidths = {},
  onColumnWidth,
}: {
  compact?: boolean;
  identityColumn?: string;
  sort?: string;
  sortFields?: string[];
  onSort?: (sort: string) => void;
  model: EngineModel;
  columns: string[];
  /** The continuous window of rows; the table scrolls it (ADR-030). */
  list: CursorWindow<ObjectItem>;
  pageSize: number;
  noun?: [string, string];
  seekLabel?: string;
  onAnchorChange?: (anchor: string | undefined) => void;
  onOpen: (item: ObjectItem) => void;
  selectedId?: string;
  renderActions?: (item: ObjectItem, menu: { isOpen: boolean; onOpenChange: (open: boolean) => void }) => ReactNode;
  label?: string;
  emptyMessage?: string;
  columnWidths?: Record<string, number>;
  onColumnWidth?: (column: string, width: number) => void;
}) {
  const [allColumns, setAllColumns] = useState(false);
  const [menuId, setMenuId] = useState<string>();
  const identity = identityColumn ?? (columns.includes("name") ? "name" : columns.includes("id") ? "id" : columns[0]);
  const mobileColumns = [identity, ...columns.filter((column) => column !== identity)].slice(0, 3);
  const secondary = (column: string) => (!mobileColumns.includes(column) ? "mobile-secondary-column" : undefined);
  const objects = list.items;
  const loading = list.loading;
  return (
    <>
      {columns.length > 3 && (
        <button
          className="secondary mobile-columns-toggle"
          aria-expanded={allColumns}
          onClick={() => setAllColumns(!allColumns)}
        >
          {allColumns ? "Show fewer columns" : `Show all ${columns.length} columns`}
        </button>
      )}
      <ScrollWindow
        list={list}
        label={label}
        noun={noun}
        pageSize={pageSize}
        seekLabel={seekLabel}
        onAnchorChange={onAnchorChange}
        className={`table-wrap object-table${compact ? " density-compact" : ""}${allColumns ? " show-all-columns" : ""}`}
      >
        <table
          aria-busy={loading || undefined}
          aria-rowcount={list.totalCount !== null && objects.length > 0 ? list.totalCount + 1 : undefined}
        >
          <caption className="visually-hidden">{label}</caption>
          <thead>
            <tr aria-rowindex={1}>
              {columns.map((column) => (
                <th
                  key={column}
                  className={secondary(column)}
                  scope="col"
                  aria-sort={
                    sort?.replace(/^-/, "") === column ? (sort.startsWith("-") ? "descending" : "ascending") : undefined
                  }
                  style={
                    columnWidths[column] ? { width: columnWidths[column], minWidth: columnWidths[column] } : undefined
                  }
                >
                  {onSort && sortFields.includes(column) ? (
                    <button className="column-sort" onClick={() => onSort(sort === column ? `-${column}` : column)}>
                      {attributeName(model, column)}
                      {sort?.replace(/^-/, "") === column && (
                        <span aria-hidden="true">{sort.startsWith("-") ? " ↓" : " ↑"}</span>
                      )}
                    </button>
                  ) : (
                    attributeName(model, column)
                  )}
                  {onColumnWidth && (
                    <ResizeHandle
                      className="column-resizer"
                      label={`Resize ${attributeName(model, column)} column`}
                      value={columnWidths[column] ?? 100}
                      min={120}
                      max={520}
                      onChange={(width) => onColumnWidth(column, width)}
                    />
                  )}
                </th>
              ))}
              {renderActions && (
                <th scope="col" className="record-actions-column">
                  <span className="visually-hidden">Record actions</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {loading && objects.length === 0 ? (
              <tr>
                <td colSpan={columns.length + Number(Boolean(renderActions))} className="empty-row">
                  Loading…
                </td>
              </tr>
            ) : objects.length === 0 ? (
              <tr>
                <td colSpan={columns.length + Number(Boolean(renderActions))} className="empty-row">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              objects.map((item, position) => (
                <tr
                  key={item.id}
                  data-row-key={item.id}
                  data-row-index={list.startIndex + position}
                  aria-rowindex={list.startIndex + position + 2}
                  className={`clickable-row${selectedId === item.id ? " selected-record" : ""}`}
                  onClick={(event) => {
                    // The identity button is the keyboard path; the row is a larger pointer target.
                    const target = event.target as HTMLElement;
                    if (target.closest("button, a, input, select, textarea, [role='menu']")) return;
                    if (window.getSelection()?.toString()) return;
                    onOpen(item);
                  }}
                  onContextMenu={
                    renderActions
                      ? (event) => {
                          event.preventDefault();
                          setMenuId(item.id);
                        }
                      : undefined
                  }
                  onKeyDown={
                    renderActions
                      ? (event) => {
                          if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
                            event.preventDefault();
                            setMenuId(item.id);
                          }
                        }
                      : undefined
                  }
                >
                  {columns.map((column) => (
                    <td key={column} className={secondary(column)}>
                      {column === identity ? (
                        <button
                          className="cell-link"
                          data-record-id={item.id}
                          data-row-focus
                          aria-current={selectedId === item.id ? "true" : undefined}
                          onClick={() => onOpen(item)}
                        >
                          {formatValue(fieldValue(item, column, model))}
                        </button>
                      ) : (
                        formatValue(fieldValue(item, column, model))
                      )}
                    </td>
                  ))}
                  {renderActions && (
                    <td className="record-actions-column">
                      {renderActions(item, {
                        isOpen: menuId === item.id,
                        onOpenChange: (open) => setMenuId(open ? item.id : undefined),
                      })}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </ScrollWindow>
    </>
  );
}
