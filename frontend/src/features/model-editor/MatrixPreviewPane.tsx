import type { MatrixPreview } from "@/features/model-editor/matrixView";
import { Notice } from "@/ui/Notice";

const SAMPLE_COLUMNS = [1, 2];

/** The matrix's shape as chosen so far. A draft has no records, so it shows the fields, not values. */
export function MatrixPreviewPane({ preview }: { preview: MatrixPreview }) {
  return (
    <aside className="matrix-preview" aria-label="Preview">
      <div className="matrix-preview-eyebrow">Preview</div>
      <strong>{preview.title || "Relation matrix"}</strong>
      <div className="matrix-preview-scroll">
        <table>
          <thead>
            <tr>
              {preview.rowColumns.map((column) => (
                <th key={column}>{column}</th>
              ))}
              {SAMPLE_COLUMNS.map((column) => (
                <th key={column}>{preview.heading}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {preview.rowColumns.map((column) => (
                <td key={column} className="muted">
                  …
                </td>
              ))}
              {SAMPLE_COLUMNS.map((column) => (
                <td key={column}>
                  {preview.cellFields.map((field) => (
                    <span key={field} className="matrix-preview-field">
                      {field}
                    </span>
                  ))}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="muted">One column for each {preview.columnType} record.</p>
      {preview.listed.length > 0 && (
        <Notice tone="info" title="Also listed here">
          {preview.listed.join(", ")} will also be listed in this application. Records stay in the application they
          stand in.
        </Notice>
      )}
    </aside>
  );
}
