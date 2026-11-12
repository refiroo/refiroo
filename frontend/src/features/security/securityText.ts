/**
 * The words the Security pages put on roles and grants (0.12 SP1): a person's role line in the
 * People list (D298), where a grant applies and what it narrows, and the grant dialog's sentence of
 * what a grant allows. Roles, workspaces, applications and record types are named as data.
 */

import { formatServerAgo, formatServerDayTime } from "@/lib/dates";
import type {
  ActionGroup,
  Client,
  Grant,
  LocalSignIn,
  SecurityEvent,
  SignInProvider,
  SigningKey,
  User,
  UserRole,
} from "@/types";

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

/**
 * A client's access in the Clients list (SP2, D348): its consumer APIs by key with their
 * workspaces, then its roles as a person's line says them; "No access yet" with neither.
 */
export function clientAccessLine(client: Pick<Client, "roles" | "consumerApis">): string {
  const apis = client.consumerApis.map((api) => {
    const where =
      api.workspaces.length > 2
        ? `${api.workspaces.length} workspaces`
        : api.workspaces.map((workspace) => workspace.label).join(", ");
    return `${api.key} · ${where}`;
  });
  const roles = client.roles.length ? [userRoleLine(client.roles)] : [];
  const parts = [...apis, ...roles];
  if (!parts.length) return "No access yet";
  return apis.length > 2
    ? `${[...apis.slice(0, 2), ...roles].join("; ")}; and ${apis.length - 2} more APIs`
    : parts.join("; ");
}

/** A client's second line: when it last obtained a token, or that it is deactivated. */
export function clientUseLine(client: Pick<Client, "active" | "lastUsedAt">, now: Date = new Date()): string {
  if (!client.active) return "Deactivated";
  return client.lastUsedAt ? `Last token ${formatServerAgo(client.lastUsedAt, now)}` : "No token yet";
}

/** A sign-in provider's line on Sign-in (I3): "42 people · last sign-in 4 min ago". */
export function providerUseLine(
  provider: Pick<SignInProvider, "people" | "lastSignInAt">,
  now: Date = new Date(),
): string {
  if (!provider.lastSignInAt) return "Nobody has signed in yet";
  const people = `${provider.people} ${provider.people === 1 ? "person" : "people"}`;
  return `${people} · last sign-in ${formatServerAgo(provider.lastSignInAt, now)}`;
}

/** How a person signs in, on their page (I3): "Signs in with Northfield Entra ID · last signed
 * in …", "Has not set a password yet", "Last signed in …", "Never signed in". */
export function personSignInLine(user: Pick<User, "identities" | "hasPassword" | "lastSignInAt">): string {
  const last = user.lastSignInAt ? formatServerDayTime(user.lastSignInAt) : undefined;
  if (user.identities.length) {
    const names = [...new Set(user.identities.map((identity) => identity.provider.name))].join(" and ");
    return `Signs in with ${names}${last ? ` · last signed in ${last}` : ""}`;
  }
  if (!user.hasPassword) return "Has not set a password yet";
  return last ? `Last signed in ${last}` : "Never signed in";
}

/** The providers a person signs in with, by name: "Northfield Entra ID" or "A and B". */
export function identityNames(user: Pick<User, "identities">): string {
  return [...new Set(user.identities.map((identity) => identity.provider.name))].join(" and ");
}

/** What linking a provider sign-in to an existing person does (I4a, D377, D378). */
export function linkSentence(from: Pick<User, "name" | "identities">, to: string): string {
  const names = identityNames(from);
  return `${to} will sign in with ${names} from now on, keeping their roles and history, and the groups ${names} names. ${from.name}, made at the first sign-in, is deactivated; what they changed keeps their name.`;
}

/** What unlinking a provider does (I4a). */
export function unlinkSentence(person: string, provider: string): string {
  return `${person} no longer signs in with ${provider}: the groups it gave them are removed and the sessions it started end. Signing in with ${provider} again makes a new person, whom you can link again.`;
}

/** Local accounts' line on Sign-in (D365). */
export function localSignInLine(local: Pick<LocalSignIn, "enabled" | "keptPeople">): string {
  if (local.enabled) return "On · people sign in with an e-mail address and password";
  return `Off · ${administrators(local.keptPeople)} ${local.keptPeople === 1 ? "keeps" : "keep"} a password`;
}

function administrators(count: number): string {
  return `${count} administrator${count === 1 ? "" : "s"}`;
}

/** What turning local sign-in off does (D365), naming the providers people continue with. */
export function turnOffSentence(providers: readonly string[], keptPeople: number): string {
  const names =
    providers.length > 1 ? `${providers.slice(0, -1).join(", ")} or ${providers.at(-1)}` : (providers[0] ?? "");
  const kept = keptPeople
    ? `except for the ${administrators(keptPeople)} made on the server, who ${keptPeople === 1 ? "keeps" : "keep"} local sign-in as the way back`
    : "and nobody keeps local sign-in: make an administrator on the server with create_admin first";
  return `People sign in with ${names} only. Passwords stop working, ${kept}. Clients are not affected.`;
}

/** What a consumer API grant allows (D354). */
export function consumerApiSentence(who: string, api: string, where: string): string {
  return `${who} will read the ${api} consumer API in ${where}. It changes nothing and opens nothing on the management API.`;
}

/** A token signing key's state as Signing keys shows it (D356). */
export function signingKeyState(key: SigningKey, now: Date = new Date()): string {
  if (key.state === "current") return "Signing";
  if (key.state === "verifying")
    return key.retiredAt ? `Verifying until ${formatServerDayTime(key.retiredAt, now)}` : "Verifying";
  return "Retired";
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
  "ai-proposals": "ask the AI provider for proposals and summaries",
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

/** The mail settings' fields as a person names them, for a security event. */
const MAIL_FIELDS: Record<string, string> = {
  method: "sending method",
  tenantId: "tenant ID",
  clientId: "application ID",
  clientSecret: "client secret",
  certificate: "certificate",
  certificateThumbprint: "certificate",
  identityMode: "managed identity",
  identityClientId: "managed identity client ID",
  authorityUrl: "token address",
  graphUrl: "Graph address",
  host: "server",
  port: "port",
  security: "connection security",
  username: "user name",
  password: "password",
  fromAddress: "from address",
  applicationUrl: "application address",
};

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
  "second-factor-added": "Authenticator app set up",
  "second-factor-removed": "Second factor removed",
  "recovery-codes-created": "New recovery codes made",
  "passkey-renamed": "A passkey was renamed",
};

/** A security event in a line, for a person's recent activity (0.12 Z4, D319): what happened, never
 * a secret, which the event does not hold. */
export function securityEventTitle(event: SecurityEvent, labels: ReadonlyMap<string, string> = new Map()): string {
  const { details } = event;
  const address = text(details.address);
  const from = address ? ` from ${address}` : "";
  const changed = Array.isArray(details.changedFields) ? (details.changedFields as string[]) : [];
  switch (event.aggregateType) {
    case "sign-in": {
      const provider = text(details.provider);
      const way = provider ? ` with ${provider}` : "";
      if (event.action === "succeeded")
        return `Signed in${details.method === "passkey" ? " with a passkey" : way}${from}`;
      const reason = text(details.reason);
      return `Sign-in${way} failed${reason ? ` (${reason})` : ""}${from}`;
    }
    case "sign-in-provider":
      if (event.aggregateId === "local") {
        if (changed.includes("secondFactorRequired"))
          return details.secondFactorRequired
            ? "A second factor required with a password"
            : "A second factor no longer required with a password";
        return details.enabled ? "Local sign-in turned on" : "Local sign-in turned off";
      }
      if (event.action === "updated" && changed.includes("enabled"))
        return `Sign-in provider ${event.aggregateId} ${details.enabled ? "enabled" : "disabled"}`;
      return `Sign-in provider ${event.aggregateId} ${event.action}`;
    case "mail-settings": {
      if (event.action === "created") return "Mail set up";
      if (event.action === "deleted") return "Mail settings removed";
      const words = changed.map((field) => MAIL_FIELDS[field] ?? field);
      return words.length ? `Mail settings changed: ${words.join(", ")}` : "Mail settings saved";
    }
    case "approval-policy":
      return `Approval policy of workspace ${event.aggregateId} changed`;
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
        if (changed.length === 1 && changed[0] === "localKept")
          return details.localKept ? "Keeps local sign-in" : "No longer keeps local sign-in";
        if (changed.length === 1 && changed[0] === "signInManaged")
          return details.signInManaged ? "Sign-in managed by an administrator" : "Sign-in no longer managed";
        return changed.length ? `Changed ${changed.join(", ")}` : "Details saved";
      }
      if (event.action === "created" && details.provider)
        return `Person created at their first sign-in with ${text(details.provider)}`;
      if (event.action === "identity-linked") {
        const providers = Array.isArray(details.providers) ? (details.providers as string[]).join(", ") : "";
        return `Sign-in with ${providers || "a provider"} linked from ${text(details.fromEmail) || text(details.fromUsername) || "another person"}`;
      }
      if (event.action === "passkey-added") return `Passkey added: ${text(details.name)}`;
      if (event.action === "passkey-removed")
        return `Passkey removed: ${text(details.name)}${details.by === "administrator" ? " by an administrator" : ""}`;
      if (event.action === "identity-unlinked") return `Sign-in with ${text(details.provider)} unlinked`;
      return USER_ACTIONS[event.action] ?? event.action;
    case "client": {
      if (event.action === "application-registered") return `Registered the assistant ${text(details.name)}`;
      if (event.action === "application-blocked") return `Blocked the assistant ${text(details.name)}`;
      if (event.action === "application-restored") return `Restored the assistant ${text(details.name)}`;
      if (event.action === "created") return "Client created";
      if (event.action === "secret-added") {
        const hours = typeof details.overlapHours === "number" ? details.overlapHours : undefined;
        if (hours === 0) return "New secret made; the earlier ones stopped at once";
        return hours
          ? `New secret made; the earlier one works ${hours} more hour${hours === 1 ? "" : "s"}`
          : "New secret made";
      }
      if (event.action === "secret-removed") return "A secret was ended";
      if (event.action === "updated" && changed.includes("active")) return details.active ? "Restored" : "Deactivated";
      if (event.action === "updated" && changed.includes("name")) return `Renamed to ${text(details.name)}`;
      return `Client ${text(details.name)} ${event.action}`.replace(/\s+/g, " ");
    }
    case "role":
      return `Role ${text(details.name)} ${event.action}`;
    case "token-signing-key":
      return "Token signing key rotated";
  }
}
