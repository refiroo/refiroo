import type { ModelChange, ModelCompatibility } from "@/types";
import { ModelDiagnostics } from "@/features/model-admin/ModelDiagnostics";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";

function preview(value: unknown) {
  if (value === undefined) return "—";
  const encoded = JSON.stringify(value);
  return encoded && encoded.length > 160 ? `${encoded.slice(0, 157)}…` : encoded;
}

const CHANGE_TONES: Record<ModelChange["kind"], StatusTone> = {
  added: "success",
  changed: "neutral",
  removed: "error",
};

/** The activation assessment of a release against the active one, as a state. */
export function CompatibilityPill({ classification }: { classification: ModelCompatibility["classification"] }) {
  return (
    <StatusPill tone={classification === "compatible" ? "success" : "error"}>
      {classification.replace("_", " ")}
    </StatusPill>
  );
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
        {compatibility && <CompatibilityPill classification={compatibility.classification} />}
      </div>
      {changes.length ? (
        <SettingsTable plain label="Semantic changes" columns={["Kind", "Path", "Before", "After"]}>
          {changes.map((change, index) => (
            <tr key={`${change.kind}:${change.path}:${index}`}>
              <td data-label="Kind">
                <StatusPill tone={CHANGE_TONES[change.kind]}>{change.kind}</StatusPill>
              </td>
              <td data-label="Path">
                <code>{change.path}</code>
              </td>
              <td data-label="Before">
                <code>{preview(change.before)}</code>
              </td>
              <td data-label="After">
                <code>{preview(change.after)}</code>
              </td>
            </tr>
          ))}
        </SettingsTable>
      ) : (
        <p className="panel-state">{emptyMessage}</p>
      )}
      {compatibility && compatibility.diagnostics.length > 0 && (
        <ModelDiagnostics diagnostics={compatibility.diagnostics} />
      )}
    </section>
  );
}
