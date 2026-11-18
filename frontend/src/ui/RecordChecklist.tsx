/**
 * Choosing records by ticking them (0.9 K6a): a search, then a list of records with a checkbox each,
 * the ticked ones pinned on top and counted. The records are either searched in the data context
 * (every record of `objectTypeKeys`, by name) or given (`records`, such as the ones a selection
 * holds, searched in place). Several types are listed under a heading each. Ticking changes nothing
 * until the caller applies it.
 */

import { useEffect, useId, useState } from "react";
import { count } from "@/lib/count";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeHue } from "@/model/hues";
import type { CandidateScope } from "@/model/candidates";
import { typeName } from "@/model/lookup";
import type { EngineModel } from "@/types";
import { SearchField } from "@/ui/SearchField";
import { RecordChip } from "@/ui/RecordChip";

export interface ChecklistRecord {
  id: string;
  name: string;
  objectTypeKey: string;
  /** Said at the row's end: "on 4 of 12", "already on 9". */
  hint?: string;
}

const PAGE = 50;

export function RecordChecklist({
  model,
  label,
  objectTypeKeys,
  heldTypeKeys = [],
  workspaceKey,
  records,
  chosen,
  hintFor,
  emptyText,
  candidates,
  onChange,
}: {
  model: EngineModel;
  /** What the records are, as the search and the list name them ("Master values"). */
  label: string;
  objectTypeKeys: readonly string[];
  /** Types of ticked records that are not searched, listed under their heading so they stay visible. */
  heldTypeKeys?: readonly string[];
  workspaceKey?: string;
  /** The records to choose from; omitted, every record of the types is searched. */
  records?: readonly ChecklistRecord[];
  chosen: readonly ChecklistRecord[];
  /** A hint for a searched record, such as how many selected records already hold it. */
  hintFor?: (id: string) => string | undefined;
  emptyText?: string;
  /** Only the records a relationship may choose, when searching (0.9 K7). */
  candidates?: CandidateScope;
  onChange: (chosen: ChecklistRecord[]) => void;
}) {
  const api = useDataApi();
  const id = useId();
  const [query, setQuery] = useState("");
  const search = useDebouncedValue(query.trim());
  const [found, setFound] = useState<{ of: string; records: ChecklistRecord[] }>();
  const typesKey = objectTypeKeys.join(" ");
  const candidateFor = candidates?.candidateFor;
  const anchorTypeKey = candidates?.anchorTypeKey;

  useEffect(() => {
    if (records) return;
    let cancelled = false;
    Promise.all(
      typesKey.split(" ").map((type) =>
        api.objects(type, {
          workspaceKey,
          search: search || undefined,
          pageSize: PAGE,
          sort: "name",
          candidateFor,
          anchorTypeKey,
        }),
      ),
    )
      .then((pages) => {
        if (cancelled) return;
        setFound({
          of: `${typesKey}|${search}|${candidateFor ?? ""}`,
          records: pages.flatMap((page) =>
            page.items.map((item) => ({ id: item.id, name: item.name, objectTypeKey: item.objectTypeKey })),
          ),
        });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [anchorTypeKey, api, candidateFor, records, search, typesKey, workspaceKey]);

  const term = query.trim().toLowerCase();
  const listed = records
    ? records.filter((record) => !term || record.name.toLowerCase().includes(term))
    : found?.of === `${typesKey}|${search}|${candidateFor ?? ""}`
      ? found.records
      : undefined;
  const chosenIds = new Set(chosen.map((record) => record.id));
  // The ticked records stay on top, whether or not the search finds them.
  const rows = [
    ...chosen.filter((record) => !term || record.name.toLowerCase().includes(term)),
    ...(listed ?? []).filter((record) => !chosenIds.has(record.id)),
  ];
  const listedTypes = [...objectTypeKeys, ...heldTypeKeys.filter((type) => !objectTypeKeys.includes(type))];
  const groups = listedTypes.length > 1 ? listedTypes : [undefined];

  function toggle(record: ChecklistRecord) {
    onChange(chosenIds.has(record.id) ? chosen.filter((item) => item.id !== record.id) : [...chosen, record]);
  }

  return (
    <div className="record-checklist">
      <SearchField
        className="record-checklist-search"
        type="search"
        iconSize={15}
        label={`Search ${label.toLowerCase()}`}
        placeholder={`Search ${label.toLowerCase()}`}
        value={query}
        onChange={setQuery}
      />
      <div className="record-checklist-list" role="group" aria-label={label} aria-describedby={`${id}-count`}>
        {groups.map((type) => {
          const inGroup = type ? rows.filter((record) => record.objectTypeKey === type) : rows;
          if (type && !inGroup.length) return null;
          return (
            <div key={type ?? "all"}>
              {type && <p className="record-checklist-heading">{typeName(model, type, { plural: true })}</p>}
              {inGroup.map((record) => {
                const hint = record.hint ?? hintFor?.(record.id);
                return (
                  <label
                    key={record.id}
                    className={chosenIds.has(record.id) ? "record-checklist-row chosen" : "record-checklist-row"}
                  >
                    <input type="checkbox" checked={chosenIds.has(record.id)} onChange={() => toggle(record)} />
                    <RecordChip hue={objectTypeHue(model, record.objectTypeKey)}>{record.name}</RecordChip>
                    {hint && <span className="record-checklist-hint">{hint}</span>}
                  </label>
                );
              })}
            </div>
          );
        })}
        {listed !== undefined && !rows.length && (
          <p className="record-checklist-empty">
            {term ? `Nothing matches “${query.trim()}”.` : (emptyText ?? "Nothing to choose.")}
          </p>
        )}
        {listed === undefined && <p className="record-checklist-empty">Searching…</p>}
      </div>
      <p id={`${id}-count`} className="record-checklist-count" aria-live="polite">
        {count(chosen.length)} selected
      </p>
    </div>
  );
}
