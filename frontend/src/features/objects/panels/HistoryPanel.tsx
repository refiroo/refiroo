import { useState } from "react";
import { periodLabel, WhatChanged, type ShownFact } from "@/ui/WhatChanged";
import { NarrowedBanner } from "@/ui/CollectionScope";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { attributeName } from "@/model/fields";
import type { Hue } from "@/model/hues";
import { relationTypeFor } from "@/model/lookup";
import type { Actor, AuditEventItem, EngineModel, HistoryKind, HistoryValue, RouteState } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ActorName, actorText } from "@/ui/ActorName";
import { AiOriginMark } from "@/ui/AiOriginMark";
import { Card } from "@/ui/Card";
import { Choice } from "@/ui/Choice";
import { Timeline } from "@/ui/Timeline";
import { TIMELINE_FIRST, TIMELINE_MORE, TimelinePaging, useTimelineLimit } from "@/ui/TimelinePaging";

const KINDS = [
  ["all", "All"],
  ["values", "Values"],
  ["relationships", "Relationships"],
  ["structure", "Moves"],
] as const;

/**
 * A record's history (0.12 RH1): its changes by day, one line each (what, who, when), opened for
 * each value with the one before (D389, D390); filtered by kind and by who made them, in the API
 * (D391); the 10 newest, then 20 more at a time, and Show fewer (D393). With `workspaceKey` it opens with
 * What changed (0.16 AO2): an account of a period, whose facts lead to this history narrowed to the changes
 * they counted.
 */
export function HistoryPanel({
  model,
  objectTypeKey,
  objectId,
  hue,
  refreshToken = 0,
  onOpenChanges,
  workspaceKey,
  application,
}: {
  /** Resolves attribute keys to their model names; keys are shown when absent. */
  model?: EngineModel;
  objectTypeKey: string;
  objectId: string;
  /** The record type's hue (`model/hues`), which colours the timeline's markers. */
  hue?: Hue;
  refreshToken?: number;
  /** Opens a person's or client's changes from their name (0.12 Z6); names stay text without it. */
  onOpenChanges?: (route: RouteState) => void;
  /** The record's workspace: offers What changed, which is not drawn without it (a preview has none). */
  workspaceKey?: string;
  /** An application of the workspace, to open a change set from a fact. */
  application?: string;
}) {
  // The page's client: in the model editor's preview it answers an empty record's history itself.
  const api = useDataApi();
  const [kind, setKind] = useState<HistoryKind | "all">("all");
  const [actorId, setActorId] = useState("");
  // The fact whose changes this history is narrowed to, which counted live changes only.
  const [shown, setShown] = useState<ShownFact>();
  const { limit, reset, more } = useTimelineLimit();
  // The people seen in this record's history so far, for the By choice; kept across filters.
  const [seen, setSeen] = useState<ReadonlyMap<string, string>>(new Map());
  const { items, loading, error, hasMore, loadMore, retry } = useCursorFeed<AuditEventItem>(
    async (cursor) => {
      const page = await api.objectHistory(objectTypeKey, objectId, {
        cursor,
        pageSize: cursor ? TIMELINE_MORE : TIMELINE_FIRST,
        kind: kind === "all" ? undefined : kind,
        actorId: actorId || undefined,
        live: shown ? true : undefined,
      });
      setSeen((current) => withActors(current, page.items));
      return page;
    },
    [objectId, objectTypeKey, refreshToken, kind, actorId, shown],
  );
  const visible = items.slice(0, limit);
  const narrowed = kind !== "all" || actorId !== "" || shown !== undefined;

  return (
    <Card as="section" flush className="panel history-panel" data-hue={hue}>
      <div className="history-head">
        <h2>History</h2>
        {seen.size > 0 && (
          <label className="history-by">
            By
            <select
              value={actorId}
              onChange={(event) => {
                setActorId(event.target.value);
                reset();
              }}
            >
              <option value="">Anyone</option>
              {[...seen].map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {workspaceKey && (
        <WhatChanged
          workspaceKey={workspaceKey}
          record={{ objectTypeKey, objectId }}
          application={application}
          onNavigate={(route) => onOpenChanges?.(route)}
          onShow={(fact) => {
            const narrowing = fact.fact.link?.query?.kind;
            setKind(
              narrowing === "values" || narrowing === "relationships" || narrowing === "structure" ? narrowing : "all",
            );
            setShown(fact);
            reset();
          }}
        />
      )}
      {shown && (
        <NarrowedBanner
          clearLabel="Show all history"
          onClear={() => {
            setShown(undefined);
            setKind("all");
            reset();
          }}
        >
          <p className="context-line">
            Narrowed by: {shown.fact.text.split(" (")[0]}, {periodLabel(shown.since, shown.until)}, live changes
          </p>
        </NarrowedBanner>
      )}
      <div className="history-kinds">
        <Choice
          name={`history-kind-${objectId}`}
          value={kind}
          options={KINDS}
          onChange={(next) => {
            setKind(next);
            setShown(undefined);
            reset();
          }}
        />
      </div>
      {error && <InlineError message={error} onRetry={retry} />}
      {loading && items.length === 0 ? (
        <div className="panel-state">Loading history…</div>
      ) : !error && items.length === 0 ? (
        <div className="panel-state">{narrowed ? "No change matches." : "No history recorded yet."}</div>
      ) : (
        <Timeline
          byDay
          label="Changes"
          entries={visible.map((item) => ({
            key: item.id,
            title: historyLine(item, model),
            at: item.occurredAt,
            tone: item.kind,
            after: ` · ${lineActor(item.actor)}${item.origin ? (item.origin.kind === "agent" ? " · prepared by an assistant" : " · proposed by the AI") : ""}`,
            details: <HistoryDetails item={item} model={model} onOpenChanges={onOpenChanges} people={seen} />,
          }))}
        />
      )}
      <TimelinePaging
        limit={limit}
        loaded={items.length}
        hasMore={hasMore}
        loading={loading}
        failed={Boolean(error)}
        moreLabel="Load older history"
        onMore={more}
        onLoad={loadMore}
        onFewer={reset}
      />
    </Card>
  );
}

/** The opened entry: each value with the one before, then who made it, its version and its time. */
function HistoryDetails({
  item,
  model,
  onOpenChanges,
  people,
}: {
  item: AuditEventItem;
  model?: EngineModel;
  onOpenChanges?: (route: RouteState) => void;
  /** The people seen in this history by ID, to name who asked for an AI proposal when they appear in it. */
  people: ReadonlyMap<string, string>;
}) {
  const values = item.values ?? [];
  const named = values.length ? undefined : historySummary(item, model);
  return (
    <>
      {values.length > 0 && (
        <table className="history-values">
          <tbody>
            {values.map((value) => (
              <tr key={value.field}>
                <th scope="row">{fieldLabel(value, model)}</th>
                <td className="history-value-before">
                  {value.fromKnown ? shownValue(value.from) : <em>not recorded</em>}
                </td>
                <td aria-hidden="true">→</td>
                <td className="history-value-after">{shownValue(value.to)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {named && <p className="history-named">{named}</p>}
      {item.origin && (
        <AiOriginMark
          origin={item.origin}
          variant="history"
          askedBy={item.origin.proposedBy ? people.get(item.origin.proposedBy) : undefined}
        />
      )}
      <p className="history-meta">
        <ActorName actor={item.actor} onOpenChanges={onOpenChanges} /> · version {item.version}
      </p>
    </>
  );
}

function withActors(current: ReadonlyMap<string, string>, items: readonly AuditEventItem[]) {
  let next: Map<string, string> | undefined;
  for (const { actor } of items) {
    const id = actor ? (actor.kind === "engine" ? "engine" : actor.id) : undefined;
    if (!id || current.has(id) || next?.has(id)) continue;
    next ??= new Map(current);
    next.set(id, actor?.kind === "engine" ? "The engine" : actorText(actor).replace(/^by /, ""));
  }
  return next ?? current;
}

/** Who made it, as the one line says it: a name, never a link inside the line's button. */
function lineActor(actor: Actor | null) {
  return actorText(actor).replace(/^by /, "");
}

const SUBJECTS: Record<string, string> = { object: "Record", relation: "Relationship", attribute: "Field value" };
const ACTIONS: Record<string, string> = { created: "added", deleted: "removed" };

/** What the change did, in one line: "Code and Name changed", "Offered in French added". */
function historyLine(item: AuditEventItem, model?: EngineModel) {
  const related = item.related;
  if (related && item.aggregateType === "relation") {
    const action = ACTIONS[item.action] ?? item.action;
    return `${relationLabel(related.relationTypeKey, related.direction, model)} ${related.name ?? "a record"} ${action}`;
  }
  const parent = item.values?.find((value) => value.kind === "parent");
  if (parent) return parent.to ? `Moved under ${String(parent.to)}` : "Moved to the top level";
  if (item.action === "reclassified") return "Type changed";
  if (item.action === "created" || item.action === "deleted") return historyTitle(item);
  const fields = (item.values ?? []).map((value) => fieldLabel(value, model));
  if (fields.length) return `${list(fields)} changed`;
  return historyTitle(item);
}

function historyTitle(item: AuditEventItem) {
  const subject = SUBJECTS[item.aggregateType] ?? "Record";
  const action = item.action.replaceAll("_", " ");
  return `${subject} ${item.aggregateType === "attribute" ? (ACTIONS[action] ?? action) : action}`;
}

/** Fields a person recognises. Identifiers and concurrency tokens stay in the audit record. */
const READABLE_FIELDS: Record<string, string> = { name: "name", parentObjectId: "parent" };

/** What an entry that kept names only changed (a publish, a type change): its fields, no values. */
function historySummary(item: AuditEventItem, model?: EngineModel) {
  const fields = item.changedFields.flatMap((field) => (READABLE_FIELDS[field] ? [READABLE_FIELDS[field]] : []));
  const attributes = item.attributeTypeKeys.map((key) => (model ? attributeName(model, key) : key));
  const parts = [...fields, ...attributes];
  return parts.length ? `Changed ${parts.join(", ")}` : "";
}

function fieldLabel(value: HistoryValue, model?: EngineModel) {
  if (value.kind === "name") return "Name";
  if (value.kind === "parent") return "Parent";
  if (value.kind === "relation") return relationLabel(value.field, "outgoing", model);
  return model ? attributeName(model, value.field) : value.field;
}

function relationLabel(key: string | null, direction: "outgoing" | "incoming", model?: EngineModel) {
  const definition = model ? relationTypeFor(model, key) : undefined;
  if (!definition) return key ?? "Relationship";
  return direction === "outgoing" ? definition.name : definition.reverseName || definition.name;
}

function shownValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(shownValue).join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function list(parts: string[]) {
  return parts.length < 2 ? parts.join("") : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}
