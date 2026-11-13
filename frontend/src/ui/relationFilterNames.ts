/**
 * The names a relationship filter shows for the records it chose (0.9 K6): read by ID, for the filter bar's pills
 * and for Export, which describes the same filter.
 */

import { useEffect, useState } from "react";
import { relatedAncestorTypes, relatedTargetTypes } from "@/model/lookup";
import { useDataApi } from "@/state/WorkspaceDataContext";
import type { CollectionFilter, EngineModel } from "@/types";
import type { ChosenRecord } from "@/ui/RecordListField";

export interface NamedRecord extends ChosenRecord {
  objectTypeKey: string;
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
