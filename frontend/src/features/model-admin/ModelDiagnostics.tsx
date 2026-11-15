import type { ModelDiagnostic } from "@/types";
import { StatusPill } from "@/ui/StatusPill";

export function ModelDiagnostics({
  diagnostics,
  onPath,
}: {
  diagnostics: ModelDiagnostic[];
  onPath?: (path: string) => void;
}) {
  if (!diagnostics.length) return <p className="model-ok">No validation diagnostics.</p>;
  return (
    <ul className="diagnostic-list list-reset">
      {diagnostics.map((item, index) => (
        <li key={`${item.path}:${item.code}:${index}`} className={item.severity}>
          <div>
            <StatusPill tone={item.severity}>{item.severity}</StatusPill>
            <strong>{item.code}</strong>
            {item.count !== undefined && <small>{item.count} affected</small>}
          </div>
          {onPath ? (
            <button type="button" onClick={() => onPath(item.path)}>
              {item.path || "/"}
            </button>
          ) : (
            <code>{item.path || "/"}</code>
          )}
          <p>{item.message}</p>
        </li>
      ))}
    </ul>
  );
}
