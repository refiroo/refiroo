import { api } from "@/api/client";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { formatServerTime } from "@/lib/dates";
import { attributeName } from "@/model/fields";
import type { AuditEventItem, EngineModel } from "@/types";
import { InlineError } from "@/ui/InlineError";

export function HistoryPanel({
  model,
  objectTypeKey,
  objectId,
  refreshToken = 0,
}: {
  /** Resolves attribute keys to their model names; keys are shown when absent. */
  model?: EngineModel;
  objectTypeKey: string;
  objectId: string;
  refreshToken?: number;
}) {
  const { items, loading, error, hasMore, loadMore, retry } = useCursorFeed<AuditEventItem>(
    (cursor) => api.objectHistory(objectTypeKey, objectId, { cursor, pageSize: 20 }),
    [objectId, objectTypeKey, refreshToken],
  );

  return (
    <section className="panel surface history-panel">
      <h2>History</h2>
      {error && <InlineError message={error} onRetry={retry} />}
      {loading && items.length === 0 ? (
        <div className="panel-state">Loading history…</div>
      ) : !error && items.length === 0 ? (
        <div className="panel-state">No history recorded yet.</div>
      ) : (
        <ol className="history-timeline">
          {items.map((item) => (
            <li key={item.id}>
              <span className="history-marker" />
              <div>
                <strong>{historyTitle(item)}</strong>
                {historySummary(item, model) && <p>{historySummary(item, model)}</p>}
                <small>
                  <time dateTime={item.occurredAt} title={formatServerTime(item.occurredAt)}>
                    {relativeTime(item.occurredAt)}
                  </time>{" "}
                  · version {item.version}
                </small>
              </div>
            </li>
          ))}
        </ol>
      )}
      {hasMore && !error && (
        <button type="button" className="load-more inline history-more" disabled={loading} onClick={loadMore}>
          {loading ? "Loading…" : "Load older history"}
        </button>
      )}
    </section>
  );
}

const SUBJECTS: Record<string, string> = { object: "Record", relation: "Relationship", attribute: "Field value" };
const ACTIONS: Record<string, string> = { created: "added", deleted: "removed" };

function historyTitle(item: AuditEventItem) {
  const subject = SUBJECTS[item.aggregateType] ?? "Record";
  const action = item.action.replaceAll("_", " ");
  return `${subject} ${item.aggregateType === "attribute" ? (ACTIONS[action] ?? action) : action}`;
}

/** Fields a person recognises. Identifiers and concurrency tokens stay in the audit record. */
const READABLE_FIELDS: Record<string, string> = { name: "name", parentObjectId: "parent" };

function historySummary(item: AuditEventItem, model?: EngineModel) {
  const fields = item.changedFields.flatMap((field) => (READABLE_FIELDS[field] ? [READABLE_FIELDS[field]] : []));
  const attributes = item.attributeTypeKeys.map((key) => (model ? attributeName(model, key) : key));
  const parts = [...fields, ...attributes];
  return parts.length ? `Changed ${parts.join(", ")}` : "";
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400_000],
  ["hour", 3_600_000],
  ["minute", 60_000],
];

function relativeTime(iso: string) {
  const elapsed = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(elapsed) || Math.abs(elapsed) > 7 * 86_400_000) return formatServerTime(iso);
  for (const [unit, size] of UNITS) {
    if (Math.abs(elapsed) >= size) return relative.format(Math.round(elapsed / size), unit);
  }
  return "just now";
}
