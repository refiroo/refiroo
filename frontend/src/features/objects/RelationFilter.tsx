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

import { useEffect, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { relatedAncestorTypes, relatedTargetTypes } from "@/model/lookup";
import type { CollectionFilter, EngineModel } from "@/types";
import type { ChosenRecord } from "@/ui/RecordListField";

export type RelationMode = "any" | "none" | "some" | "notUnder" | "under";

const MODE_LABELS: Record<RelationMode, string> = {
  any: "is any of",
  none: "has none",
  some: "has any",
  notUnder: "has none under",
  under: "has any under",
};

export interface NamedRecord extends ChosenRecord {
  objectTypeKey: string;
}

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

/**
 * The names of the records the list's relationship filters choose, read by ID in the list's data
 * context, once per set of IDs: one read of each type at the other end.
 */
export function useRelationFilterNames(
  model: EngineModel,
  objectTypeKey: string,
  filters: readonly CollectionFilter[],
  workspaceKey?: string,
): ReadonlyMap<string, NamedRecord> {
  const api = useDataApi();
  const wanted = filters.filter(
    (filter) => filter.field.startsWith("related:") && ["eq", "under", "notUnder"].includes(filter.operator),
  );
  const signature = JSON.stringify(wanted.map((filter) => [filter.field, filter.value, filter.operator]));
  const [names, setNames] = useState<{ of: string; map: Map<string, NamedRecord> }>();
  useEffect(() => {
    const pairs = JSON.parse(signature) as [string, string, string][];
    if (!pairs.length) return;
    let cancelled = false;
    const ids = [...new Set(pairs.map(([, id]) => id))];
    // A record named by eq is of a type at the other end; one named by under is of a type above it.
    const types = [
      ...new Set(
        pairs.flatMap(([field, , operator]) =>
          (operator === "eq"
            ? relatedTargetTypes(model, objectTypeKey, field)
            : relatedAncestorTypes(model, objectTypeKey, field)
          ).map((type) => type.key),
        ),
      ),
    ];
    Promise.all(
      types.map((type) =>
        api.objects(type, {
          workspaceKey,
          pageSize: Math.min(500, Math.max(ids.length, 1)),
          filters: ids.map((id) => ({ field: "id", operator: "eq", value: id })),
        }),
      ),
    )
      .then((pages) => {
        if (cancelled) return;
        const map = new Map<string, NamedRecord>();
        for (const page of pages)
          for (const item of page.items)
            map.set(item.id, { id: item.id, name: item.name, objectTypeKey: item.objectTypeKey });
        setNames({ of: signature, map });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [signature, api, model, objectTypeKey, workspaceKey]);
  return names?.of === signature ? names.map : new Map();
}
