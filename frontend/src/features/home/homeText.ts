/**
 * What the home page says (0.12 HM1, D337): the greeting, the summary sentence from the counts, the
 * person's roles as pills, each card's tile, role and quiet line. Pure, so the page stays markup.
 */

import { listedNames } from "@/state/permissionText";
import type { Grant, HeldAnywhere, OwnWorkspace } from "@/types";

const NUMBERS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

/** "Three", or "12": a count that starts a sentence. */
function counted(count: number): string {
  return NUMBERS[count] ?? String(count);
}

function plural(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}

export function greeting(name: string, hour: number): string {
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const first = name.trim().split(/\s+/)[0];
  return first ? `Good ${part}, ${first}` : `Good ${part}`;
}

/** The welcome card's sentence: how many workspaces, what is open and what waits to be published. */
export function summary(workspaces: OwnWorkspace[]): string {
  const own = workspaces.reduce((total, item) => total + item.ownChangeSets, 0);
  const waiting = workspaces.reduce((total, item) => total + (item.openChangeSets ?? 0), 0);
  const first = `${counted(workspaces.length)} ${plural(workspaces.length, "workspace is", "workspaces are")} open to you.`;
  const parts: string[] = [];
  if (own) parts.push(`${counted(own)} of your change sets ${plural(own, "is", "are")} open`);
  if (waiting)
    parts.push(
      `${parts.length ? counted(waiting).toLowerCase() : counted(waiting)} ${plural(waiting, "change set waits", "change sets wait")} for someone to publish ${plural(waiting, "it", "them")}`,
    );
  if (!parts.length) return `${first} Open an application below, or pick up where you were.`;
  return `${first} ${parts.join(", and ")}.`;
}

/** The roles a person holds in `workspaceKey`, by name: instance grants apply in every workspace. */
export function rolesIn(grants: Grant[], workspaceKey: string): string[] {
  const names = grants
    .filter((grant) => grant.role && (grant.scope.instance || grant.scope.workspaceKey === workspaceKey))
    .map((grant) => grant.role!.name);
  return [...new Set(names)].sort();
}

/** The welcome card's pills: each role and where it applies among the cards. */
export function rolePills(grants: Grant[], workspaces: OwnWorkspace[]): string[] {
  const labels = new Map(workspaces.map((item) => [item.key, item.label]));
  const where = new Map<string, Set<string> | "instance">();
  for (const grant of grants) {
    if (!grant.role) continue;
    const name = grant.role.name;
    if (grant.scope.instance) where.set(name, "instance");
    else if (grant.scope.workspaceKey && labels.has(grant.scope.workspaceKey) && where.get(name) !== "instance") {
      const keys = (where.get(name) as Set<string> | undefined) ?? new Set<string>();
      keys.add(grant.scope.workspaceKey);
      where.set(name, keys);
    }
  }
  return [...where.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, keys]) => {
      if (keys === "instance") return name;
      if (keys.size === 1) return `${name} in ${labels.get([...keys][0])}`;
      return `${name} in ${keys.size} workspaces`;
    });
}

/** A card's role line: "Data steward", "Reader and Contributor"; empty when none is known. */
export function roleLine(grants: Grant[], workspaceKey: string): string {
  return listedNames(rolesIn(grants, workspaceKey));
}

/**
 * The person's roles in one workspace on one line (0.17 SH1): the first that fit, then "and n more"; the
 * whole list is `roleLine`, which the card keeps as the line's title and accessible name.
 */
export function roleSummary(grants: Grant[], workspaceKey: string, budget = 44): string {
  const names = rolesIn(grants, workspaceKey);
  if (names.length <= 1) return listedNames(names);
  const text = (shown: number) => {
    const rest = names.length - shown;
    return rest ? `${names.slice(0, shown).join(", ")} and ${rest} more` : listedNames(names);
  };
  // As many names as the line holds (`budget` characters), then "and n more": never a cut word.
  for (let shown = names.length; shown > 1; shown -= 1) if (text(shown).length <= budget) return text(shown);
  return text(1);
}

/**
 * What a card with nothing open says the person can do there, from the groups they hold: a writer
 * says nothing more, a proposer is told how to propose, a reader that they read.
 */
export function quietNote(held: HeldAnywhere[] | undefined, workspaceKey: string): string | undefined {
  if (!held) return undefined;
  const has = (group: string) =>
    held.some((item) => item.key === group && (item.instance || item.workspaces.some((w) => w.key === workspaceKey)));
  if (has("edit-live") || has("publish")) return undefined;
  if (has("change-sets")) return "Propose a change from any record.";
  return "You can read this workspace.";
}

/** A count's label under its figure: "your change set", "open change sets to publish". */
export function ownLabel(count: number): string {
  return plural(count, "your change set", "your change sets");
}

export function openLabel(count: number): string {
  return plural(count, "open change set to publish", "open change sets to publish");
}
