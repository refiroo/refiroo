/**
 * How a change reads on a person's Changes page and on Home (0.12 Z6, D343): a title naming what
 * changed, a summary of its type and fields, and the line after its time (workspace, change set,
 * cause). Never values: a record's history has them.
 */

import type { ChangeEntry, ChangeEntryKind, ChangePeriod, HeldAnywhere, RouteState } from "@/types";
import { changeReviewFor } from "@/routing/routes";

// Shared with every timeline grouped by day (`ui/Timeline`, 0.12 RH1).
export { byDay, dayLabel } from "@/lib/dates";

const quoted = (name: string | null | undefined, fallback: string) => (name ? `“${name}”` : fallback);

function recordName(entry: ChangeEntry) {
  if (entry.subject.name) return entry.subject.name;
  return entry.subject.removed ? "a record since removed" : "a record";
}

function end(object: { name: string | null } | undefined) {
  return object?.name ?? "a removed record";
}

const RECORD_ACTIONS: Record<string, string> = {
  created: "Added",
  updated: "Updated",
  deleted: "Deleted",
  reclassified: "Changed the type of",
};
const CHANGE_SET_ACTIONS: Record<string, string> = {
  created: "Created",
  renamed: "Renamed",
  validated: "Validated",
  discarded: "Discarded",
  derived: "Derived",
  "model-release-changed": "Moved to another model release:",
  moved: "Kept the submitted request on the moved version of",
};
const DRAFT_ACTIONS: Record<string, string> = { created: "Created", updated: "Changed", deleted: "Deleted" };

/** What the entry did, as its title reads. */
export function changeTitle(entry: ChangeEntry): string {
  const subject = entry.subject;
  switch (entry.kind) {
    case "record":
      return `${RECORD_ACTIONS[entry.action] ?? "Changed"} ${recordName(entry)}`;
    case "relationship": {
      const from = end(subject.fromObject);
      const to = end(subject.toObject);
      if (entry.action === "created") return `Linked ${from} to ${to}`;
      if (entry.action === "deleted") return `Unlinked ${from} from ${to}`;
      return `Changed the link from ${from} to ${to}`;
    }
    case "change-set":
      return `${CHANGE_SET_ACTIONS[entry.action] ?? "Changed"} change set ${quoted(subject.name, "without a name")}`;
    case "publication":
      return `${entry.action === "withdrawn" ? "Withdrew" : "Published"} publication ${subject.number ?? ""}`.trim();
    case "model":
      if (entry.action === "installed") return `Installed release ${subject.name ?? ""}`.trim();
      if (entry.action === "activated") return `Activated release ${subject.name ?? ""}`.trim();
      return `${DRAFT_ACTIONS[entry.action] ?? "Changed"} model draft ${quoted(subject.name, "")}`.trim();
  }
}

/** Fields a person recognises, as a record's history names them. */
const READABLE_FIELDS: Record<string, string> = { name: "name", parentObjectId: "parent", parent: "parent" };

/** The entry's type and what it changed, under its title; empty when there is nothing to add. */
export function changeSummary(entry: ChangeEntry): string {
  const subject = entry.subject;
  if (entry.kind === "record") {
    const changed = [
      ...entry.changedFields.flatMap((field) => (READABLE_FIELDS[field] ? [READABLE_FIELDS[field]] : [])),
      ...entry.attributes.map((attribute) => attribute.name),
    ];
    const type = subject.objectTypeName ?? subject.objectTypeKey ?? "Record";
    return entry.action === "updated" && changed.length ? `${type} · changed ${changed.join(", ")}` : type;
  }
  if (entry.kind === "relationship") return subject.relationTypeName ?? subject.relationTypeKey ?? "Relationship";
  if (entry.kind === "publication" && entry.changeSet)
    return `From change set ${quoted(entry.changeSet.name, "without a name")}`;
  if (entry.kind === "model")
    return entry.action === "activated" || entry.action === "installed" ? "Model release" : "Model draft";
  return "";
}

/** Where and how, after the time: the workspace, the change set it was made in, and its cause. */
export function changeWhere(entry: ChangeEntry): string[] {
  const parts = [entry.workspace?.label ?? (entry.kind === "model" ? "Model administration" : "A deleted workspace")];
  if ((entry.kind === "record" || entry.kind === "relationship") && entry.changeSet)
    parts.push(`in change set ${quoted(entry.changeSet.name, "without a name")}`);
  if (entry.cause.kind === "job") parts.push("in a background job");
  if (entry.cause.kind === "publication") parts.push("applied by a publication");
  return parts;
}

/** The page's heading: "Your changes", "Ana Varga's changes", or a plain one before a name is known. */
export function changesHeading(self: boolean, name: string | undefined) {
  if (self) return "Your changes";
  return name ? `${name}'s changes` : "Changes";
}

/**
 * Whether someone's changes would show the caller anything (D342, D323): Browse anywhere, or
 * Model authoring at the instance. Without either the list would always be empty, so no way to it
 * is offered.
 */
export function readsChanges(held: readonly HeldAnywhere[] | undefined) {
  return Boolean(
    held?.some(
      (group) =>
        (group.key === "browse" && (group.instance || group.workspaces.length > 0)) ||
        (group.key === "model-authoring" && group.instance),
    ),
  );
}

/** Under the heading: whose changes, and which. */
export function changesSubtitle(self: boolean, kind: "user" | "client" | undefined) {
  const which = "newest first, in the workspaces you can read";
  if (self || !kind) return which[0].toUpperCase() + which.slice(1);
  return `${kind === "client" ? "Client" : "Person"} · ${which}`;
}

const PERIOD_DAYS: Record<ChangePeriod, number> = { day: 1, week: 7, month: 30 };

export const PERIOD_LABELS: Record<ChangePeriod | "", string> = {
  "": "Any time",
  day: "Last 24 hours",
  week: "Last 7 days",
  month: "Last 30 days",
};

export const KIND_LABELS: Record<ChangeEntryKind | "", string> = {
  "": "Everything",
  record: "Records",
  relationship: "Relationships",
  "change-set": "Change sets",
  publication: "Publications",
  model: "Model",
};

/** The instant a period starts, for `since`; none for any time. */
export function periodSince(period: ChangePeriod | undefined, now: Date = new Date()): string | undefined {
  if (!period) return undefined;
  return new Date(now.valueOf() - PERIOD_DAYS[period] * 86_400_000).toISOString();
}

/**
 * Where an entry's title leads while what it changed exists: the record in its workspace (in its
 * change set while that is open), the change set's review, the workspace's publications, the draft
 * or the release. `application` is the workspace's first application, which opens a change set or
 * publications; none where the entry's workspace cannot be opened.
 */
export function changeTarget(entry: ChangeEntry, application: string | undefined): RouteState | undefined {
  const workspaceKey = entry.workspace?.key;
  const openSet = entry.changeSet?.open ? entry.changeSet.id : undefined;
  const subject = entry.subject;
  switch (entry.kind) {
    case "record":
      if (!workspaceKey || subject.removed || !subject.applicationKey || !subject.objectTypeKey) return undefined;
      return {
        kind: "detail",
        applicationKey: subject.applicationKey,
        objectTypeKey: subject.objectTypeKey,
        objectId: subject.id,
        workspaceKey,
        ...(openSet ? { changeSetId: openSet } : {}),
      };
    case "change-set":
      return workspaceKey && application && openSet ? changeReviewFor(application, workspaceKey, openSet) : undefined;
    case "publication":
      return workspaceKey && application
        ? { kind: "publications", applicationKey: application, workspaceKey }
        : undefined;
    case "model":
      if (entry.action === "activated" || entry.action === "installed")
        return { kind: "settings", page: "model", releaseId: subject.id };
      return entry.action === "deleted" ? undefined : { kind: "settings", page: "model", draftId: subject.id };
    default:
      return undefined;
  }
}
