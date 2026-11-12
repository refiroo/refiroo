/**
 * What a grant dialog's ticks come to (0.12 U9; edits since 0.17): the grants to make, leaving out those
 * the holder already has, the grants to remove when the dialog sets a holder's access (a held cell
 * unticked), and the sentences that say so. One tick is one grant; the API takes one at a time.
 */

import type { Grant, GrantCreate } from "@/types";

type Principal = GrantCreate["principal"];

/** What a dialog changed: the grants it made and the grants it removed, for the page's toast and its Undo. */
export interface GrantChange {
  added: Grant[];
  removed: Grant[];
}

/** A consumer API in a workspace, as the grid keys its cells. */
export const cellKey = (apiKey: string, workspaceKey: string) => `${apiKey}|${workspaceKey}`;

/** A role at the instance (`*`) or in a workspace, as the role cards key what is held. */
export const roleKey = (role: string, where: string) => `${role}|${where}`;

/** The grants a holder has that a dialog can express, by cell: a consumer API in a workspace (`cellKey`) or an
 * unnarrowed role at the instance (`*`) or in a workspace (`roleKey`). A narrowed role grant is a different
 * grant from an unnarrowed one, so it has no cell and the dialog neither shows nor changes it. */
export function grantCells(grants: readonly Grant[]): { apis: Map<string, Grant>; roles: Map<string, Grant> } {
  const apis = new Map<string, Grant>();
  const roles = new Map<string, Grant>();
  for (const grant of grants) {
    if (grant.consumerApi && grant.scope.workspaceKey) {
      apis.set(cellKey(grant.consumerApi.key, grant.scope.workspaceKey), grant);
      continue;
    }
    if (!grant.role || grant.scope.applications.length || grant.scope.recordTypes.length) continue;
    roles.set(roleKey(grant.role.key, grant.scope.instance ? "*" : (grant.scope.workspaceKey ?? "")), grant);
  }
  return { apis, roles };
}

/** The consumer API grants held, as cell keys. */
export const heldConsumerApis = (grants: readonly Grant[]): Set<string> => new Set(grantCells(grants).apis.keys());

/** The roles held with nothing narrowed, at the instance or in a workspace. */
export const heldRoles = (grants: readonly Grant[]): Set<string> => new Set(grantCells(grants).roles.keys());

/** The held grants whose cell is among `shown` and not wanted: what unticking them removes. */
export function removals(
  held: ReadonlyMap<string, Grant>,
  wanted: ReadonlySet<string>,
  shown: ReadonlySet<string>,
): Grant[] {
  return [...held].filter(([cell]) => shown.has(cell) && !wanted.has(cell)).map(([, grant]) => grant);
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

/** The role grants for the wanted role cells (`roleKey`), none of them already held. Narrowing goes to every
 * grant made in a workspace; the dialog offers it for one grant only. */
export function roleRequests(
  principal: Principal,
  wanted: Iterable<string>,
  held: ReadonlySet<string>,
  narrowing: { applications: string[]; recordTypes: string[] },
): GrantCreate[] {
  const requests: GrantCreate[] = [];
  for (const cell of wanted) {
    if (held.has(cell)) continue;
    const [role = "", where = ""] = cell.split("|");
    requests.push(
      where === "*"
        ? { principal, role, scope: { instance: true } }
        : { principal, role, scope: { workspaceKey: where, ...narrowing } },
    );
  }
  return requests;
}

/** What a held grant is made again as, in the same place with the same narrowing (Undo of a removal). */
export function recreation(grant: Grant): GrantCreate {
  const principal = { kind: grant.principal.kind, id: grant.principal.id };
  const scope: GrantCreate["scope"] = grant.scope.instance
    ? { instance: true }
    : {
        workspaceKey: grant.scope.workspaceKey ?? "",
        ...(grant.scope.applications.length ? { applications: grant.scope.applications } : {}),
        ...(grant.scope.recordTypes.length ? { recordTypes: grant.scope.recordTypes } : {}),
      };
  return grant.consumerApi
    ? { principal, consumerApi: grant.consumerApi.key, scope }
    : { principal, role: grant.role?.key ?? "", scope };
}

export const list = (items: readonly string[]) =>
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

/** What one dialog Save changed: "Test client will read RDM API in default; RDM Master API in pilot is removed." */
export function changeSentence(args: {
  who: string;
  verb: "read" | "hold";
  added: readonly string[];
  removed: readonly string[];
}): string {
  const { who, verb, added, removed } = args;
  if (added.length && removed.length)
    return `${who} will ${verb} ${list(added)}; ${list(removed)} ${removed.length > 1 ? "are" : "is"} removed.`;
  if (added.length)
    return `${who} will ${verb} ${list(added)}.${verb === "read" ? " It changes nothing and opens nothing on the management API." : ""}`;
  if (removed.length) return `${who} will no longer ${verb} ${list(removed)}.`;
  return "";
}
