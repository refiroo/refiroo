import { api } from "../api/client";
import { useCursorFeed } from "../lib/hooks/useCursorFeed";
import type { AuditEventItem } from "../types";
import { InlineError } from "./AsyncState";

export function HistoryPanel({
  objectTypeKey,
  objectId,
  refreshToken = 0,
}: {
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
                <p>{historySummary(item)}</p>
                <small>
                  <time dateTime={item.occurredAt}>{new Date(item.occurredAt).toLocaleString()}</time> · aggregate v
                  {item.version}
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

function historyTitle(item: AuditEventItem) {
  const subject =
    item.aggregateType === "relation" ? "Relationship" : item.aggregateType === "attribute" ? "Attribute" : "Object";
  return `${subject} ${item.action.replaceAll("_", " ")}`;
}

function historySummary(item: AuditEventItem) {
  const fields = item.changedFields.filter((field) => field !== "attributes");
  const parts = [...fields, ...item.attributeTypeKeys.map((key) => `attribute: ${key}`)];
  return parts.length ? `Changed ${parts.join(", ")}` : "No field details recorded.";
}
