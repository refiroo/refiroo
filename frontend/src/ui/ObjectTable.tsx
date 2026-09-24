import { useState, type ReactNode } from "react";
import type { EngineModel, ObjectItem } from "@/types";
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
  objects,
  loading = false,
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
  objects: ObjectItem[];
  loading?: boolean;
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
      <div
        className={`table-wrap object-table${compact ? " density-compact" : ""}${allColumns ? " show-all-columns" : ""}`}
        role="region"
        aria-label={label}
        tabIndex={0}
      >
        <table aria-busy={loading || undefined}>
          <caption className="visually-hidden">{label}</caption>
          <thead>
            <tr>
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
              objects.map((item) => (
                <tr
                  key={item.id}
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
      </div>
    </>
  );
}
