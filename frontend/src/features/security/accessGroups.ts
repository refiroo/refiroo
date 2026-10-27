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

export type ChipHue = 1 | 2 | 3 | 4 | 7 | 8 | "neutral";

const ADMINISTRATION = new Set(["workspace-admin", "model-admin", "integration-admin", "operator", "security-admin"]);

/** The hue slot of a grant's chip, by the kind of its role. */
export function chipHue(grant: Grant): ChipHue {
  if (!grant.role) return 2;
  const key = grant.role.key;
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
