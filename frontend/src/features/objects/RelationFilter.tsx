/**
 * A collection's filter on a relationship (0.9 K6, D153–D158): the records related to any of chosen
 * records, to none, or to any, through the relationship a view's `filterFields` names
 * (`related:<key>`). The filter is part of the list's `query.filters`, so the list, its selection,
 * the bulk actions and Export all read it: "is any of" is one `eq` entry per chosen record, "has
 * none" and "has any" one `isNull` entry. The address keeps the records' IDs; their names are read
 * back by ID for the pill (D157). Its editor is the filter bar's (K6a, `filters/FilterBar`).
 *
 * Two more conditions name a record by ID too (0.16 AG4): "has none under" and "has any under" keep
 * the records with no related record, or some, standing below that record at any depth (`notUnder`
 * and `under`). One entry each; the record is of a type the related records can stand under.
 */

import type { CollectionFilter } from "@/types";
import type { NamedRecord } from "@/ui/relationFilterNames";
import type { ChosenRecord } from "@/ui/RecordListField";

export type RelationMode = "any" | "none" | "some" | "notUnder" | "under";

const MODE_LABELS: Record<RelationMode, string> = {
  any: "is any of",
  none: "has none",
  some: "has any",
  notUnder: "has none under",
  under: "has any under",
};

/** What a relationship filter's entries ask. */
export function relationFilterMode(entries: readonly CollectionFilter[]): RelationMode {
  const under = entries.find((entry) => entry.operator === "under" || entry.operator === "notUnder");
  if (under) return under.operator as "under" | "notUnder";
  const flag = entries.find((entry) => entry.operator === "isNull");
  if (flag) return flag.value === "true" ? "none" : "some";
  return "any";
}

/** The chip's words: "is any of Alpha, Bravo", "has none", "has any". */
export function relationFilterText(entries: readonly CollectionFilter[], names: ReadonlyMap<string, NamedRecord>) {
  const mode = relationFilterMode(entries);
  if (mode === "under" || mode === "notUnder")
    return `${MODE_LABELS[mode]} ${names.get(entries[0].value)?.name ?? "…"}`;
  if (mode !== "any") return MODE_LABELS[mode];
  const chosen = entries.map((entry) => names.get(entry.value)?.name ?? "…");
  return `${MODE_LABELS.any} ${chosen.join(", ")}`;
}

/** The entries a relationship filter stores for a mode and the chosen records. */
export function relationFilterEntries(
  field: string,
  mode: RelationMode,
  chosen: readonly ChosenRecord[],
): CollectionFilter[] {
  if (mode === "under" || mode === "notUnder")
    return chosen.length ? [{ field, operator: mode, value: chosen[0].id }] : [];
  if (mode === "none") return [{ field, operator: "isNull", value: "true" }];
  if (mode === "some") return [{ field, operator: "isNull", value: "false" }];
  return chosen.map((record) => ({ field, operator: "eq", value: record.id }));
}
