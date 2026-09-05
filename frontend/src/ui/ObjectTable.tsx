import type { EngineModel, ObjectItem } from "@/types";
import { formatValue } from "@/ui/formatValue";
import { attributeName, fieldValue } from "@/model/fields";

export function ObjectTable({
  model,
  columns,
  objects,
  loading = false,
  onOpen,
  onEdit,
  onDelete,
}: {
  model: EngineModel;
  columns: string[];
  objects: ObjectItem[];
  loading?: boolean;
  onOpen: (item: ObjectItem) => void;
  onEdit?: (item: ObjectItem) => void;
  onDelete?: (item: ObjectItem) => void;
}) {
  const hasActions = Boolean(onEdit || onDelete);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{attributeName(model, column)}</th>
            ))}
            {hasActions && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columns.length + (hasActions ? 1 : 0)} className="empty-row">
                Loading…
              </td>
            </tr>
          ) : objects.length === 0 ? (
            <tr>
              <td colSpan={columns.length + (hasActions ? 1 : 0)} className="empty-row">
                Nothing to show yet.
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
                {hasActions && (
                  <td>
                    <div className="row-actions">
                      <button onClick={() => onOpen(item)}>Open</button>
                      {onEdit && <button onClick={() => onEdit(item)}>Edit</button>}
                      {onDelete && (
                        <button className="text-danger" onClick={() => onDelete(item)}>
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
