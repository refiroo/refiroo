import type { EngineModel, ObjectItem } from "@/types";
import { formatValue } from "@/ui/formatValue";
import { attributeName, fieldValue } from "@/model/fields";

export function ObjectTable({
  model,
  columns,
  objects,
  loading = false,
  onOpen,
  label = "Objects",
  emptyMessage = "Nothing to show yet.",
}: {
  model: EngineModel;
  columns: string[];
  objects: ObjectItem[];
  loading?: boolean;
  onOpen: (item: ObjectItem) => void;
  label?: string;
  emptyMessage?: string;
}) {
  return (
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      <table aria-busy={loading || undefined}>
        <caption className="visually-hidden">{label}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{attributeName(model, column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="empty-row">
                Loading…
              </td>
            </tr>
          ) : objects.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="empty-row">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            objects.map((item) => (
              <tr key={item.id}>
                {columns.map((column, index) => (
                  <td key={column}>
                    {index === 0 ? (
                      <button className="cell-link" onClick={() => onOpen(item)}>
                        {formatValue(fieldValue(item, column, model))}
                      </button>
                    ) : (
                      formatValue(fieldValue(item, column, model))
                    )}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
