/**
 * The words the Security pages put on roles and grants (0.12 SP1): a person's role line in the
 * People list (D298), where a grant applies and what it narrows, and the grant dialog's sentence of
 * what a grant allows. Roles, workspaces, applications and record types are named as data.
 */

import type { ActionGroup, Grant, SecurityEvent, UserRole } from "@/types";

/** "Data steward · Herbarium; Reader · Field stations", "Security administrator", "No roles yet". */
export function userRoleLine(roles: readonly UserRole[]): string {
  if (!roles.length) return "No roles yet";
  const parts = roles.map((role) => {
    if (role.instance) return role.name;
    const where =
      role.workspaces.length > 2
        ? `${role.workspaces.length} workspaces`
        : role.workspaces.map((workspace) => workspace.label).join(", ");
    return `${role.name} · ${where}`;
  });
  return parts.length > 2 ? `${parts.slice(0, 2).join("; ")}; and ${parts.length - 2} more` : parts.join("; ");
}

/** What a grant gives: its role's name, or "Consumer API: Name" for a consumer API grant (Z3). */
export function grantHeld(grant: Grant): string {
  if (grant.role) return grant.role.name;
  const api = grant.consumerApi;
  return `Consumer API: ${api?.name ?? api?.key ?? ""}`;
}

/** Where a grant applies: "Every workspace", or the workspace's label (its key when not known). */
export function grantWhere(grant: Grant, labels: ReadonlyMap<string, string>): string {
  if (grant.scope.instance) return "Every workspace";
  const key = grant.scope.workspaceKey ?? "";
  return labels.get(key) ?? key;
}

/** What a grant's writes are narrowed to, by name; "—" for none. */
export function grantNarrowing(grant: Grant): string {
  const names = [...grant.scope.applicationNames, ...grant.scope.recordTypeNames];
  return names.length ? names.join(", ") : "—";
}

/** A stale narrowing's missing keys, as a sentence (D296); empty when not stale. */
export function staleNote(grant: Grant): string {
  const missing = [...(grant.scope.missingApplications ?? []), ...(grant.scope.missingRecordTypes ?? [])];
  if (grant.stale && grant.consumerApi && grant.consumerApi.name === null)
    return `Stale: consumer API “${grant.consumerApi.key}” is no longer in this workspace’s model, and allows nothing.`;
  if (!grant.stale || !missing.length) return "";
  const named = missing.map((key) => `“${key}”`).join(", ");
  return `Stale: ${named} ${missing.length > 1 ? "are" : "is"} no longer in this workspace’s model, and allow${missing.length > 1 ? "" : "s"} nothing.`;
}

// What each action group lets its holder do, as the grant dialog's sentence says it.
const DOING: Record<string, string> = {
  browse: "read everything",
  "edit-live": "change records live",
  "change-sets": "change records in change sets",
  publish: "publish change sets",
  bulk: "run batches and imports",
  "copy-move": "copy and move records",
  feed: "read the change feed",
  "model-authoring": "author models",
  "model-release": "install, activate and migrate model releases",
  "workspace-admin": "manage workspaces",
  "integration-admin": "manage webhooks",
  operations: "follow the instance's operations",
  "security-admin": "manage people, groups, roles and clients",
};

function listed(items: readonly string[]): string {
  if (items.length < 2) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** The groups of a role that a workspace grant does not give: those held only at the instance. */
export function instanceOnly(groups: readonly string[], catalogue: readonly ActionGroup[]): ActionGroup[] {
  return catalogue.filter((group) => groups.includes(group.key) && group.grantableAt === "instance");
}

/**
 * What a grant would allow, in one sentence or two: "Jonah will read everything in Herbarium and
 * change records in change sets, changing only Collections and Determination." A workspace grant
 * names the groups it leaves out because they are held only at the instance (D302).
 */
export function grantSentence({
  who,
  groups,
  catalogue,
  where,
  narrowedTo,
}: {
  who: string;
  /** The role's action groups. */
  groups: readonly string[];
  catalogue: readonly ActionGroup[];
  /** A workspace's label, or undefined for the whole instance. */
  where?: string;
  /** The names writes are narrowed to; empty for everything. */
  narrowedTo: readonly string[];
}): string {
  const left = where ? instanceOnly(groups, catalogue).map((group) => group.key) : [];
  const given = catalogue.filter((group) => groups.includes(group.key) && !left.includes(group.key));
  if (!given.length) return `${who} will be able to do nothing${where ? ` in ${where}` : ""} with this role.`;
  const place = where ? ` in ${where}` : " across the whole instance";
  const doing = given.map((group) => DOING[group.key] ?? group.name.toLowerCase());
  const reads = given.some((group) => group.key === "browse");
  const writes = given.some((group) => group.narrowable);
  let sentence = `${who} will ${listed(doing)}${place}`;
  if (writes && narrowedTo.length) sentence += `, changing only ${listed(narrowedTo)}`;
  sentence += ".";
  if (!reads && writes) sentence += " Without Browse they cannot read the records they change.";
  if (left.length) {
    const names = catalogue.filter((group) => left.includes(group.key)).map((group) => group.name);
    sentence += ` ${listed(names)} ${names.length > 1 ? "are" : "is"} held only for the whole instance, so this grant does not give ${names.length > 1 ? "them" : "it"}.`;
  }
  return sentence;
}

const text = (value: unknown) => (typeof value === "string" ? value : "");

/** What a grant event names: "Data steward in Herbarium", "Consumer API: x in …", by the
 * workspace's label where known, else its key. */
function grantEventWords(details: Record<string, unknown>, labels: ReadonlyMap<string, string>): string {
  const role = details.role as { name?: string } | null | undefined;
  const held = role?.name ?? `Consumer API: ${text(details.consumerApi)}`;
  const workspace = text(details.workspaceKey);
  return `${held} ${workspace ? `in ${labels.get(workspace) ?? workspace}` : "in every workspace"}`;
}

const USER_ACTIONS: Record<string, string> = {
  created: "Person created",
  "password-link-created": "One-time password link made",
  "password-set": "Password set from a one-time link",
  "password-changed": "Password changed",
  "signed-out-everywhere": "Signed out everywhere",
};

/** A security event in a line, for a person's recent activity (0.12 Z4, D319): what happened, never
 * a secret, which the event does not hold. */
export function securityEventTitle(event: SecurityEvent, labels: ReadonlyMap<string, string> = new Map()): string {
  const { details } = event;
  const address = text(details.address);
  const from = address ? ` from ${address}` : "";
  const changed = Array.isArray(details.changedFields) ? (details.changedFields as string[]) : [];
  switch (event.aggregateType) {
    case "sign-in":
      return event.action === "succeeded" ? `Signed in${from}` : `Sign-in failed${from}`;
    case "grant":
      return `${event.action === "created" ? "Granted" : "Grant removed:"} ${grantEventWords(details, labels)}`;
    case "group": {
      const group = text(details.groupName) || text(details.name);
      if (event.action === "member-added") return `Added to ${group}`;
      if (event.action === "member-removed") return `Removed from ${group}`;
      return `Group ${group} ${event.action}`;
    }
    case "user":
      if (event.action === "updated") {
        if (changed.includes("active")) return details.active ? "Restored" : "Deactivated";
        return changed.length ? `Changed ${changed.join(", ")}` : "Details saved";
      }
      return USER_ACTIONS[event.action] ?? event.action;
    case "client":
      if (event.action === "secret-added") return "New client secret";
      if (event.action === "secret-removed") return "Client secret stopped";
      return `Client ${text(details.name)} ${event.action}`.replace(/\s+/g, " ");
    case "role":
      return `Role ${text(details.name)} ${event.action}`;
    case "token-signing-key":
      return "Token signing key rotated";
  }
}
