/**
 * What a grant dialog's ticks come to (0.12 U9): the grants to make, leaving out those the holder
 * already has, and the sentence that says so. One tick is one grant; the API takes one at a time.
 */

import type { Grant, GrantCreate } from "@/types";

type Principal = GrantCreate["principal"];

/** A consumer API in a workspace, as the grid keys its cells. */
export const cellKey = (apiKey: string, workspaceKey: string) => `${apiKey}|${workspaceKey}`;

/** A role at the instance (`*`) or in a workspace, as the role cards key what is held. */
export const roleKey = (role: string, where: string) => `${role}|${where}`;

/** The consumer API grants held, as cell keys. */
export function heldConsumerApis(grants: readonly Grant[]): Set<string> {
  const held = new Set<string>();
  for (const grant of grants)
    if (grant.consumerApi && grant.scope.workspaceKey) held.add(cellKey(grant.consumerApi.key, grant.scope.workspaceKey));
  return held;
}

/** The roles held with nothing narrowed, at the instance or in a workspace. A narrowed grant is a
 * different grant from an unnarrowed one, so it does not stand for it. */
export function heldRoles(grants: readonly Grant[]): Set<string> {
  const held = new Set<string>();
  for (const grant of grants) {
    if (!grant.role || grant.scope.applications.length || grant.scope.recordTypes.length) continue;
    held.add(roleKey(grant.role.key, grant.scope.instance ? "*" : (grant.scope.workspaceKey ?? "")));
  }
  return held;
}

/** The consumer API grants for the ticked cells, none of them already held. */
export function consumerRequests(
  principal: Principal,
  ticked: Iterable<string>,
  held: ReadonlySet<string>,
): GrantCreate[] {
  const requests: GrantCreate[] = [];
  for (const cell of ticked) {
    if (held.has(cell)) continue;
    const [consumerApi = "", workspaceKey = ""] = cell.split("|");
    requests.push({ principal, consumerApi, scope: { workspaceKey } });
  }
  return requests;
}

/** The role grants for every ticked role at every place, none of them already held (an unnarrowed
 * request only; a narrowed one is always made). */
export function roleRequests(
  principal: Principal,
  roles: readonly string[],
  places: readonly string[] | "instance",
  narrowing: { applications: string[]; recordTypes: string[] },
  held: ReadonlySet<string>,
): GrantCreate[] {
  const narrowed = narrowing.applications.length > 0 || narrowing.recordTypes.length > 0;
  const requests: GrantCreate[] = [];
  for (const role of roles) {
    if (places === "instance") {
      if (!held.has(roleKey(role, "*"))) requests.push({ principal, role, scope: { instance: true } });
      continue;
    }
    for (const workspaceKey of places) {
      if (!narrowed && held.has(roleKey(role, workspaceKey))) continue;
      requests.push({ principal, role, scope: { workspaceKey, ...narrowing } });
    }
  }
  return requests;
}

const list = (items: readonly string[]) =>
  items.length > 1 ? `${items.slice(0, -1).join(", ")} and ${items.at(-1)}` : (items[0] ?? "");

const grants = (count: number) => `${count} grant${count === 1 ? "" : "s"}`;

/** "3 grants will be made: Test client reads RDM in default and pilot, and Master data in default." */
export function consumerPlanSentence(who: string, reads: readonly { api: string; where: readonly string[] }[]): string {
  const count = reads.reduce((sum, read) => sum + read.where.length, 0);
  if (!count) return "";
  const parts = reads.map((read) => `${read.api} in ${list(read.where)}`);
  return `${grants(count)} will be made: ${who} reads ${list(parts)}. It changes nothing and opens nothing on the management API.`;
}

/** "4 grants: Reader and Editor, each in default and pilot. Anna already holds 1 of them." */
export function rolePlanSentence(args: {
  who: string;
  roles: readonly string[];
  where: readonly string[] | "instance";
  count: number;
  skipped: number;
}): string {
  if (!args.count && !args.skipped) return "";
  const each = args.roles.length > 1 ? "each " : "";
  const where = args.where === "instance" ? "for the whole instance" : `in ${list(args.where)}`;
  const skipped = args.skipped
    ? ` ${args.who} already holds ${args.skipped === 1 ? "one of them" : `${args.skipped} of them`}, so ${args.skipped === 1 ? "it is" : "they are"} skipped.`
    : "";
  return `${grants(args.count)} will be made: ${list(args.roles)}, ${each}${where}.${skipped}`;
}
