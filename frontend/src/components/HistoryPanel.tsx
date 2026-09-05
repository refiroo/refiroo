import { useEffect, useState } from "react";
import { api } from "../api/client";
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
  const [items, setItems] = useState<AuditEventItem[]>([]);
  const [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryReset, setRetryReset] = useState(true);

  async function load(reset = true) {
    setLoading(true);
    setError("");
    try {
      const page = await api.objectHistory(objectTypeKey, objectId, {
        cursor: reset ? undefined : cursor,
        pageSize: 20,
      });
      setItems((current) => (reset ? page.items : [...current, ...page.items]));
      setCursor(page.nextCursor ?? undefined);
    } catch (cause) {
      setRetryReset(reset);
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [objectId, objectTypeKey, refreshToken]);

  return (
    <section className="panel surface history-panel">
      <h2>History</h2>
      {error && <InlineError message={error} onRetry={() => void load(retryReset)} />}
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
      {cursor && !error && (
        <button
          type="button"
          className="load-more inline history-more"
          disabled={loading}
          onClick={() => void load(false)}
        >
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
