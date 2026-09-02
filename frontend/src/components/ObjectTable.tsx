import type { EngineModel, ObjectItem } from "../types";
import { attributeName, fieldValue } from "../utils/model";

export function ObjectTable({
  model,
  columns,
  objects,
  loading = false,
  onOpen,
}: {
  model: EngineModel;
  columns: string[];
  objects: ObjectItem[];
  loading?: boolean;
  onOpen: (item: ObjectItem) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{attributeName(model, column)}</th>)}</tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan={columns.length} className="empty-row">Loading…</td></tr>
          ) : objects.length === 0 ? (
            <tr><td colSpan={columns.length} className="empty-row">Nothing to show yet.</td></tr>
          ) : objects.map((item) => (
            <tr key={item.id}>
              {columns.map((column, index) => (
                <td key={column}>
                  {index === 0 ? (
                    <button className="cell-link" onClick={() => onOpen(item)}>
                      {formatValue(fieldValue(item, column, model))}
                    </button>
                  ) : formatValue(fieldValue(item, column, model))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function formatValue(value: unknown) {
  if (typeof value === "boolean") {
    return <span className={value ? "pill active-pill" : "pill"}>{value ? "Yes" : "No"}</span>;
  }
  if (value === undefined || value === null || value === "") return <span className="muted">—</span>;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function Pagination({
  page,
  hasNext,
  onPrevious,
  onNext,
}: {
  page: number;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <div className="pagination" aria-label="Pagination">
      <span>Page {page}</span>
      <button className="icon-button" onClick={onPrevious} disabled={page === 1} aria-label="Previous page">←</button>
      <button className="icon-button" onClick={onNext} disabled={!hasNext} aria-label="Next page">→</button>
    </div>
  );
}
