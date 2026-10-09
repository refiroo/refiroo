/**
 * A collection's filter on a relationship (0.9 K6, D153–D158): the records related to any of chosen
 * records, to none, or to any, through the relationship a view's `filterFields` names
 * (`related:<key>`). The filter is part of the list's `query.filters`, so the list, its selection,
 * the bulk actions and Export all read it: "is any of" is one `eq` entry per chosen record, "has
 * none" and "has any" one `isNull` entry. The address keeps the records' IDs; their names are read
 * back by ID for the chip (D157).
 */

import { useEffect, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { relatedTargetTypes } from "@/model/lookup";
import type { CollectionFilter, EngineModel } from "@/types";
import { RecordListField, type ChosenRecord } from "@/ui/RecordListField";

type Mode = "any" | "none" | "some";

const MODE_LABELS: Record<Mode, string> = { any: "is any of", none: "has none", some: "has any" };

export interface NamedRecord extends ChosenRecord {
  objectTypeKey: string;
}

/** What a relationship filter's entries ask. */
export function relationFilterMode(entries: readonly CollectionFilter[]): Mode {
  const flag = entries.find((entry) => entry.operator === "isNull");
  if (flag) return flag.value === "true" ? "none" : "some";
  return "any";
}

/** The chip's words: "is any of Alpha, Bravo", "has none", "has any". */
export function relationFilterText(entries: readonly CollectionFilter[], names: ReadonlyMap<string, NamedRecord>) {
  const mode = relationFilterMode(entries);
  if (mode !== "any") return MODE_LABELS[mode];
  const chosen = entries.map((entry) => names.get(entry.value)?.name ?? "…");
  return `${MODE_LABELS.any} ${chosen.join(", ")}`;
}

/** The entries a relationship filter stores for a mode and the chosen records. */
export function relationFilterEntries(field: string, mode: Mode, chosen: readonly ChosenRecord[]): CollectionFilter[] {
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
  const wanted = filters.filter((filter) => filter.field.startsWith("related:") && filter.operator === "eq");
  const signature = JSON.stringify(wanted.map((filter) => [filter.field, filter.value]));
  const [names, setNames] = useState<{ of: string; map: Map<string, NamedRecord> }>();
  useEffect(() => {
    const pairs = JSON.parse(signature) as [string, string][];
    if (!pairs.length) return;
    let cancelled = false;
    const ids = [...new Set(pairs.map(([, id]) => id))];
    const types = [
      ...new Set(pairs.flatMap(([field]) => relatedTargetTypes(model, objectTypeKey, field).map((type) => type.key))),
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

export function RelationFilterControl({
  model,
  objectTypeKey,
  field,
  label,
  entries,
  names,
  workspaceKey,
  onApply,
}: {
  model: EngineModel;
  objectTypeKey: string;
  field: string;
  label: string;
  entries: readonly CollectionFilter[];
  names: ReadonlyMap<string, NamedRecord>;
  workspaceKey?: string;
  onApply: (entries: CollectionFilter[]) => void;
}) {
  const [mode, setMode] = useState<Mode>(relationFilterMode(entries));
  const [shownMode, setShownMode] = useState(relationFilterMode(entries));
  if (shownMode !== relationFilterMode(entries)) {
    setShownMode(relationFilterMode(entries));
    setMode(relationFilterMode(entries));
  }
  const chosen: NamedRecord[] = entries
    .filter((entry) => entry.operator === "eq")
    .map((entry) => names.get(entry.value) ?? { id: entry.value, name: "…", objectTypeKey: "" });
  const targets = relatedTargetTypes(model, objectTypeKey, field);
  return (
    <div className="toolbar-filter relation-filter">
      <span>{label}</span>
      <select
        aria-label={`${label} operator`}
        value={mode}
        onChange={(event) => {
          const next = event.target.value as Mode;
          setMode(next);
          onApply(relationFilterEntries(field, next, next === "any" ? chosen : []));
        }}
      >
        {(Object.keys(MODE_LABELS) as Mode[]).map((item) => (
          <option key={item} value={item}>
            {MODE_LABELS[item]}
          </option>
        ))}
      </select>
      {mode === "any" &&
        targets.map((target) => (
          <RecordListField
            key={target.key}
            label={targets.length > 1 ? `${label}: ${target.pluralName}` : target.pluralName}
            objectTypeKey={target.key}
            workspaceKey={workspaceKey}
            values={chosen.filter((record) => (record.objectTypeKey || target.key) === target.key)}
            onChange={(values) =>
              onApply(
                relationFilterEntries(field, "any", [
                  ...chosen.filter((record) => record.objectTypeKey && record.objectTypeKey !== target.key),
                  ...values,
                ]),
              )
            }
          />
        ))}
    </div>
  );
}
