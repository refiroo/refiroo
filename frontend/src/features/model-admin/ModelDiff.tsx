import type { ModelChange, ModelCompatibility } from "@/types";
import { ModelDiagnostics } from "@/features/model-admin/ModelDiagnostics";

function preview(value: unknown) {
  if (value === undefined) return "—";
  const encoded = JSON.stringify(value);
  return encoded && encoded.length > 160 ? `${encoded.slice(0, 157)}…` : encoded;
}

/** Semantic changes; `compatibility`, when given, is shown alongside as the activation assessment. */
export function ModelDiff({
  changes,
  compatibility,
  emptyMessage = "No semantic changes from the comparison release.",
}: {
  changes: ModelChange[];
  compatibility?: ModelCompatibility;
  emptyMessage?: string;
}) {
  return (
    <section className="model-diff">
      <div className="model-result-heading">
        <h3>Semantic changes</h3>
        {compatibility && (
          <span className={`compatibility ${compatibility.classification}`}>
            {compatibility.classification.replace("_", " ")}
          </span>
        )}
      </div>
      {changes.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Kind</th>
                <th>Path</th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change, index) => (
                <tr key={`${change.kind}:${change.path}:${index}`}>
                  <td>
                    <span className="pill">{change.kind}</span>
                  </td>
                  <td>
                    <code>{change.path}</code>
                  </td>
                  <td>
                    <code>{preview(change.before)}</code>
                  </td>
                  <td>
                    <code>{preview(change.after)}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="panel-state">{emptyMessage}</p>
      )}
      {compatibility && compatibility.diagnostics.length > 0 && (
        <ModelDiagnostics diagnostics={compatibility.diagnostics} />
      )}
    </section>
  );
}
