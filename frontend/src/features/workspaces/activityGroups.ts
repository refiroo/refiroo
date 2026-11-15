/**
 * The workspace Activity tab's grouping (0.12): consecutive record and relationship changes made in
 * the same change set by the same actor on the same day read as one line. A pure function over the
 * entries loaded so far, run on every render, so a group that ended a page grows when the next page
 * continues it.
 */

import { plural } from "@/lib/count";
import type { ChangeEntry } from "@/types";
import type { StatusTone } from "@/ui/StatusPill";

export type ActivityItem =
  | { type: "single"; key: string; occurredAt: string; entry: ChangeEntry }
  | {
      type: "group";
      key: string;
      occurredAt: string;
      changeSetName: string | null;
      entries: ChangeEntry[];
      /** The last group of a list with more pages: the next page may add to it. */
      mayContinue: boolean;
    };

const isDataChange = (entry: ChangeEntry) => entry.kind === "record" || entry.kind === "relationship";

function groupKey(entry: ChangeEntry): string | undefined {
  if (!isDataChange(entry) || !entry.changeSet) return undefined;
  const actor = entry.actor
    ? entry.actor.kind === "engine"
      ? "engine"
      : `${entry.actor.kind}:${entry.actor.id}`
    : "none";
  return [entry.changeSet.id, actor, new Date(entry.occurredAt).toDateString()].join("|");
}

export function groupActivity(entries: readonly ChangeEntry[], hasMore: boolean): ActivityItem[] {
  const items: ActivityItem[] = [];
  let run: ChangeEntry[] = [];
  const flush = (last: boolean) => {
    if (!run.length) return;
    const first = run[0];
    if (run.length === 1) items.push({ type: "single", key: first.id, occurredAt: first.occurredAt, entry: first });
    else
      items.push({
        type: "group",
        key: `group:${first.id}`,
        occurredAt: first.occurredAt,
        changeSetName: first.changeSet?.name ?? null,
        entries: run,
        mayContinue: last && hasMore,
      });
    run = [];
  };
  for (const entry of entries) {
    const key = groupKey(entry);
    if (run.length && key !== undefined && key === groupKey(run[0])) {
      run.push(entry);
      continue;
    }
    flush(false);
    if (key === undefined) items.push({ type: "single", key: entry.id, occurredAt: entry.occurredAt, entry });
    else run = [entry];
  }
  flush(true);
  return items;
}

export type ChangeOutcome = "created" | "changed" | "removed";

/** What a record or relationship change did, from the entry's action. */
export function outcomeOf(entry: ChangeEntry): ChangeOutcome {
  if (entry.action === "created") return "created";
  if (entry.action === "deleted") return "removed";
  return "changed";
}

export const OUTCOME_PILL: Record<ChangeOutcome, { label: string; tone: StatusTone }> = {
  created: { label: "Created", tone: "success" },
  changed: { label: "Changed", tone: "neutral" },
  removed: { label: "Removed", tone: "error" },
};

/** "9 changed · 2 created · 1 removed · Brand ×7, Type ×5": the group's sub-line. */
export function groupSummary(entries: readonly ChangeEntry[], typeName: (entry: ChangeEntry) => string): string {
  const counts: Record<ChangeOutcome, number> = { created: 0, changed: 0, removed: 0 };
  const types = new Map<string, number>();
  let links = 0;
  for (const entry of entries) {
    counts[outcomeOf(entry)] += 1;
    if (entry.kind === "relationship") links += 1;
    else types.set(typeName(entry), (types.get(typeName(entry)) ?? 0) + 1);
  }
  const parts = (["changed", "created", "removed"] as const)
    .filter((outcome) => counts[outcome])
    .map((outcome) => `${counts[outcome]} ${outcome}`);
  const byType = [...types].sort((a, b) => b[1] - a[1]).map(([name, count]) => `${name} ×${count}`);
  if (links) byType.push(`${plural(links, "link")} ×${links}`);
  return [...parts, byType.join(", ")].filter(Boolean).join(" · ");
}
