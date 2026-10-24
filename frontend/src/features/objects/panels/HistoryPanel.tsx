import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { attributeName } from "@/model/fields";
import type { Hue } from "@/model/hues";
import type { AuditEventItem, EngineModel } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ActorName } from "@/ui/ActorName";
import { Card } from "@/ui/Card";
import { Timeline } from "@/ui/Timeline";

export function HistoryPanel({
  model,
  objectTypeKey,
  objectId,
  hue,
  refreshToken = 0,
}: {
  /** Resolves attribute keys to their model names; keys are shown when absent. */
  model?: EngineModel;
  objectTypeKey: string;
  objectId: string;
  /** The record type's hue (`model/hues`), which colours the timeline's markers. */
  hue?: Hue;
  refreshToken?: number;
}) {
  // The page's client: in the model editor's preview it answers an empty record's history itself.
  const api = useDataApi();
  const { items, loading, error, hasMore, loadMore, retry } = useCursorFeed<AuditEventItem>(
    (cursor) => api.objectHistory(objectTypeKey, objectId, { cursor, pageSize: 20 }),
    [objectId, objectTypeKey, refreshToken],
  );

  return (
    <Card as="section" flush className="panel history-panel" data-hue={hue}>
      <h2>History</h2>
      {error && <InlineError message={error} onRetry={retry} />}
      {loading && items.length === 0 ? (
        <div className="panel-state">Loading history…</div>
      ) : !error && items.length === 0 ? (
        <div className="panel-state">No history recorded yet.</div>
      ) : (
        <Timeline
          entries={items.map((item) => ({
            key: item.id,
            title: historyTitle(item),
            summary: historySummary(item, model),
            at: item.occurredAt,
            after: (
              <>
                {" "}
                · <ActorName actor={item.actor} /> · version {item.version}
              </>
            ),
          }))}
        />
      )}
      {hasMore && !error && (
        <button type="button" className="load-more inline history-more" disabled={loading} onClick={loadMore}>
          {loading ? "Loading…" : "Load older history"}
        </button>
      )}
    </Card>
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
