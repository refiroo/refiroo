import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { workspaceModel } from "@/model/workspaceModels";
import { ChangeTitle } from "@/ui/ChangeTitle";
import { periodLabel, WhatChanged, type ShownFact } from "@/ui/WhatChanged";
import { NarrowedBanner } from "@/ui/CollectionScope";
import { KIND_LABELS, changeSummary, changeWhere } from "@/ui/changeText";
import {
  OUTCOME_PILL,
  groupActivity,
  groupSummary,
  outcomeOf,
  type ActivityItem,
} from "@/features/workspaces/activityGroups";
import { byDay, formatServerTime, timeOfDay } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { objectTypeHue } from "@/model/hues";
import { objectTypeFor } from "@/model/lookup";
import type { ChangeEntry, ChangeEntryKind, EngineModel, RouteState } from "@/types";
import { ActorName } from "@/ui/ActorName";
import { EmptyState } from "@/ui/EmptyState";
import { HueTile } from "@/ui/HueTile";
import { Icon, type IconName } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";

const ACTIVITY_KINDS = (Object.keys(KIND_LABELS) as (ChangeEntryKind | "")[]).filter((kind) => kind !== "model");

/** The colour dot of a filter chip: records teal, change sets coral, publications the primary tint. */
const KIND_DOT: Partial<Record<ChangeEntryKind, string>> = {
  record: "var(--hue-1-marker)",
  relationship: "var(--text-tertiary)",
  "change-set": "var(--hue-6-marker)",
  publication: "var(--state-selected-text)",
};

function MarkTile({ mark, hue, icon }: { mark: string; hue?: 6 | 8; icon: IconName }) {
  return (
    <span className="hue-tile hue-tile-22" data-hue={hue} data-mark={mark}>
      <Icon name={icon} size={12} />
    </span>
  );
}

/** The leading tile of an entry: the record type's own tile, or the kind's colour. */
function EntryTile({ entry, model }: { entry: ChangeEntry; model: EngineModel | undefined }) {
  switch (entry.kind) {
    case "record": {
      const key = entry.subject.objectTypeKey;
      const type = model && key ? objectTypeFor(model, key) : undefined;
      return <HueTile hue={model && key ? objectTypeHue(model, key) : undefined} icon={type?.icon} size={22} />;
    }
    case "relationship":
      return <MarkTile mark="relationship" icon="link" />;
    case "change-set":
      return <MarkTile mark="change-set" hue={6} icon="copy" />;
    case "publication":
      return <MarkTile mark="publication" icon="to-end" />;
    case "model":
      return <MarkTile mark="model" hue={8} icon="model" />;
  }
}

function EntryPill({ entry }: { entry: ChangeEntry }) {
  if (entry.kind === "record" || entry.kind === "relationship") {
    const pill = OUTCOME_PILL[outcomeOf(entry)];
    return <StatusPill tone={pill.tone}>{pill.label}</StatusPill>;
  }
  const tone: StatusTone =
    entry.kind === "change-set" ? "changeSet" : entry.kind === "publication" ? "publication" : "neutral";
  const label =
    entry.kind === "change-set"
      ? "Change set"
      : entry.kind === "publication"
        ? entry.action === "withdrawn"
          ? "Withdrawn"
          : "Published"
        : "Model";
  return <StatusPill tone={tone}>{label}</StatusPill>;
}

/**
 * The workspace's changes newest first, by day: the changes list narrowed to this workspace, which
 * names the record and its type, the change set and who made each (the change feed carries
 * identifiers only and reads forward). Each entry has a coloured tile and a kind pill; changes made
 * in one change set by one person on one day fold into one line that opens to its members. Above the filters,
 * What changed (0.16 AO2) words a period, and a fact of it narrows this list, in place, to the changes it counted.
 */
export function WorkspaceActivity({
  workspaceKey,
  onNavigate,
}: {
  workspaceKey: string;
  onNavigate: (route: RouteState) => void;
}) {
  const [kind, setKind] = useState<ChangeEntryKind | "">("");
  // The fact whose changes the list is narrowed to, over the account's period.
  const [narrow, setNarrow] = useState<ShownFact>();
  const feed = useCursorFeed<ChangeEntry>(
    (cursor) => {
      const query = narrow?.fact.link?.query;
      return api.changes({
        workspaceKey,
        kinds: kind ? [kind] : undefined,
        ...(narrow && query
          ? {
              since: narrow.since,
              until: narrow.until,
              objectTypeKey: query.objectTypeKey,
              relationTypeKey: query.relationTypeKey,
              causeId: query.causeId,
              action: query.action,
              attributeKey: query.attributeKey,
              live: query.live,
            }
          : {}),
        cursor,
      });
    },
    [workspaceKey, kind, narrow],
  );
  // Opening a change set or the publications needs an application of this workspace; the tiles
  // need the model's types.
  const [model, setModel] = useState<EngineModel>();
  const application = model?.applications[0]?.key;
  useEffect(() => {
    let active = true;
    workspaceModel(workspaceKey).then(
      (loaded) => active && setModel(loaded),
      () => undefined,
    );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const toggle = (key: string) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const typeName = (entry: ChangeEntry) => {
    const key = entry.subject.objectTypeKey;
    return (model && key && objectTypeFor(model, key)?.name) || entry.subject.objectTypeName || key || "Record";
  };

  const line = (entry: ChangeEntry, member: boolean) => (
    <div className="activity-line">
      <EntryTile entry={entry} model={model} />
      <EntryPill entry={entry} />
      <div className="activity-main">
        <strong>
          <ChangeTitle entry={entry} application={application} onNavigate={onNavigate} />
        </strong>
        {changeSummary(entry) && <div className="activity-sub">{changeSummary(entry)}</div>}
      </div>
      <div className="activity-who">
        {!member && (
          <>
            <ActorName actor={entry.actor} onOpenChanges={onNavigate} />
            {changeWhere(entry)
              .slice(1)
              .map((part) => ` · ${part}`)}
            {" · "}
          </>
        )}
        <time dateTime={entry.occurredAt} title={formatServerTime(entry.occurredAt)}>
          {timeOfDay(entry.occurredAt)}
        </time>
      </div>
    </div>
  );

  const render = (item: ActivityItem) => {
    if (item.type === "single") return <li key={item.key}>{line(item.entry, false)}</li>;
    const first = item.entries[0];
    const expanded = open.has(item.key);
    const count = `${item.entries.length}${item.mayContinue ? "+" : ""}`;
    const noun = item.entries.every((entry) => entry.kind === "record") ? "records" : "changes";
    return (
      <li key={item.key} className="activity-group">
        <div className="activity-line">
          <button type="button" className="activity-toggle" aria-expanded={expanded} onClick={() => toggle(item.key)}>
            <span className="activity-chevron" aria-hidden="true">
              {expanded ? "▾" : "▸"}
            </span>
            <MarkTile mark="change-set" hue={6} icon="copy" />
            <StatusPill tone="changeSet">Change set</StatusPill>
            <span className="activity-main">
              <strong>
                {count} {noun} changed in {item.changeSetName ? `“${item.changeSetName}”` : "a change set"}
              </strong>
              <span className="activity-count" aria-hidden="true">
                {count}
              </span>
              <span className="activity-sub">{groupSummary(item.entries, typeName)}</span>
            </span>
          </button>
          <div className="activity-who">
            <ActorName actor={first.actor} onOpenChanges={onNavigate} />
            {" · "}
            <time dateTime={first.occurredAt} title={formatServerTime(first.occurredAt)}>
              {timeOfDay(first.occurredAt)}
            </time>
          </div>
        </div>
        {expanded && (
          <ol className="activity-members" aria-label="Changes in this group">
            {item.entries.map((entry) => (
              <li key={entry.id}>{line(entry, true)}</li>
            ))}
          </ol>
        )}
      </li>
    );
  };

  return (
    <section className="workspace-activity" aria-label="Activity">
      <WhatChanged
        headingLevel={2}
        workspaceKey={workspaceKey}
        application={application}
        onNavigate={onNavigate}
        onShow={(shown) => {
          const kinds = shown.fact.link?.query?.kind;
          const first = Array.isArray(kinds) ? kinds[0] : kinds;
          setKind(first === "record" || first === "relationship" ? first : "");
          setNarrow(shown);
        }}
      />
      <div className="activity-filters" role="group" aria-label="Filter the activity">
        <span className="activity-filters-label">What</span>
        {ACTIVITY_KINDS.map((value) => (
          <button
            key={value}
            type="button"
            className="activity-chip"
            aria-pressed={kind === value}
            onClick={() => {
              setKind(value);
              setNarrow(undefined);
            }}
          >
            {value && KIND_DOT[value] && (
              <i className="activity-dot" style={{ background: KIND_DOT[value] }} aria-hidden="true" />
            )}
            {KIND_LABELS[value]}
          </button>
        ))}
      </div>
      {narrow && (
        <NarrowedBanner clearLabel="Show all activity" onClear={() => setNarrow(undefined)}>
          <p className="context-line">
            Narrowed by: {narrow.fact.text.split(" (")[0]}, {periodLabel(narrow.since, narrow.until)}
          </p>
        </NarrowedBanner>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading the activity" lines={5} />
      ) : !feed.items.length ? (
        <EmptyState>No activity yet.</EmptyState>
      ) : (
        <>
          <div className="history-days" aria-label="Activity" role="group">
            {byDay(groupActivity(feed.items, feed.hasMore)).map((day) => (
              <section key={day.day} aria-label={day.day}>
                {/* Level 2: "What changed" above is an h2 and renders nothing when the AI offer is off, so an h3 would skip a level under the page's h1. */}
                <h2 className="history-day">{day.day}</h2>
                <ol className="activity-list">{day.entries.map(render)}</ol>
              </section>
            ))}
          </div>
          {feed.hasMore && (
            <div>
              <button type="button" className="secondary" disabled={feed.loading} onClick={feed.loadMore}>
                {feed.loading ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
