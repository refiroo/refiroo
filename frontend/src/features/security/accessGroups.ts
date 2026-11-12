/**
 * The workspace Access list, one line per principal (0.12): grants grouped by who holds them, and the
 * colour a grant's chip takes from the kind of role. The role keys are the security feature's own
 * predefined vocabulary; any other role is a custom one and stays neutral.
 */

import type { Grant } from "@/types";
import { grantHeld, grantNarrowing } from "./securityText";

export interface AccessRow {
  /** Kind and id: unique per principal. */
  key: string;
  principal: Grant["principal"];
  grants: Grant[];
}

/**
 * Merges consecutive grants of the same principal into one row. The server orders the list by
 * principal, so a principal's grants are adjacent, also across a page boundary.
 */
export function groupByPrincipal(grants: readonly Grant[]): AccessRow[] {
  const rows: AccessRow[] = [];
  for (const grant of grants) {
    const key = `${grant.principal.kind}:${grant.principal.id}`;
    const last = rows.at(-1);
    if (last?.key === key) last.grants.push(grant);
    else rows.push({ key, principal: grant.principal, grants: [grant] });
  }
  return rows;
}

/** The grants of one place: every workspace, or one workspace. */
export interface PlaceRow {
  /** "instance" or the workspace's key. */
  key: string;
  label: string;
  instance: boolean;
  grants: Grant[];
}

/**
 * A principal's grants by where they apply (0.17 ST1, the user: "group the accesses"): every workspace first,
 * then each workspace by its name; in a place, roles before consumer APIs, each by name.
 */
export function groupByPlace(grants: readonly Grant[], labels: ReadonlyMap<string, string>): PlaceRow[] {
  const rows = new Map<string, PlaceRow>();
  for (const grant of grants) {
    const key = grant.scope.instance ? "instance" : (grant.scope.workspaceKey ?? "");
    const label = grant.scope.instance ? "Every workspace" : (labels.get(key) ?? key);
    const row = rows.get(key) ?? { key, label, instance: grant.scope.instance, grants: [] };
    row.grants.push(grant);
    rows.set(key, row);
  }
  const held = (grant: Grant) => `${grant.role ? 0 : 1}${grantHeld(grant).toLowerCase()}`;
  for (const row of rows.values()) row.grants.sort((a, b) => held(a).localeCompare(held(b)));
  return [...rows.values()].sort((a, b) =>
    a.instance !== b.instance ? (a.instance ? -1 : 1) : a.label.localeCompare(b.label),
  );
}

export type ChipHue = 1 | 2 | 3 | 4 | 7 | 8 | "neutral";

const ADMINISTRATION = new Set(["workspace-admin", "model-admin", "integration-admin", "operator", "security-admin"]);

/** The hue slot of a grant's chip, by the kind of its role. */
export function chipHue(grant: Grant): ChipHue {
  return grant.role ? roleKeyHue(grant.role.key) : 2;
}

/** The hue slot of a role's chip, by its key (a person's roles in a list carry the key, not a grant). */
export function roleKeyHue(key: string): ChipHue {
  if (key === "reader") return 8;
  if (key === "contributor") return 7;
  if (key === "steward") return 1;
  if (key === "owner") return 4;
  if (ADMINISTRATION.has(key)) return 3;
  return "neutral";
}

/** What a chip says of its narrowing: the first two names and a count; empty when not narrowed. */
export function narrowingShort(grant: Grant): string {
  const names = [...grant.scope.applicationNames, ...grant.scope.recordTypeNames];
  if (!names.length) return "";
  return names.length > 2 ? `${names.slice(0, 2).join(", ")} +${names.length - 2}` : names.join(", ");
}

export { grantHeld, grantNarrowing };

/** The roles present among grants, by key, for the Role filter. */
export function rolesPresent(grants: readonly Grant[]): { value: string; label: string }[] {
  const seen = new Map<string, string>();
  for (const grant of grants) {
    const value = grant.role ? `role:${grant.role.key}` : "consumer-api";
    if (!seen.has(value)) seen.set(value, grant.role ? grant.role.name : "Consumer API");
  }
  return [...seen].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
}

export function holdsRole(row: AccessRow, value: string): boolean {
  return row.grants.some((grant) => (grant.role ? `role:${grant.role.key}` : "consumer-api") === value);
}
