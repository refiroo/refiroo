/**
 * A collection's filters (0.9 K6a, D160–D164): the active filters as pills, each opening its own
 * editor; ＋ Filter opens the view's filter fields, then the chosen field's editor in the same
 * popover. One compact editor per kind of field: text, number, date, yes/no, relationship. Text,
 * number, date and record checklists apply with Apply; yes/no applies as it is chosen (D161). At
 * phone width the popover is a bottom sheet whose Apply counts the records the draft shows (D163).
 *
 * The filters stay `query.filters` entries ({field, operator, value}), so the address, the
 * selection, the bulk actions and Export read them as before; a relationship filter is several
 * entries of one field (K6). A field of another kind may hold several entries, such as the two ends
 * of a date range, each its own pill (0.16 AG4).
 */

import { keyScope } from "@/model/candidates";
import { useEffect, useState } from "react";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import {
  relationFilterEntries,
  relationFilterMode,
  type NamedRecord,
  type RelationMode,
} from "@/features/objects/RelationFilter";
import { attributeName } from "@/model/fields";
import { RELATED_FIELD_PREFIX, relatedAncestorTypes, relatedTargetTypes } from "@/model/lookup";
import type { CollectionFilter, EngineModel, ValueType } from "@/types";
import { Choice } from "@/ui/Choice";
import { ControlPopover } from "@/ui/ControlPopover";
import { FieldMenu } from "@/ui/FieldMenu";
import { Icon, type IconName } from "@/ui/Icon";
import { RecordChecklist, type ChecklistRecord } from "@/ui/RecordChecklist";

export type FilterKind = "text" | "number" | "date" | "boolean" | "relation";

export interface FilterField {
  field: string;
  label: string;
  kind: FilterKind;
  /** Whether the field is a bound attribute, which may be unset as well as empty. */
  attribute: boolean;
}

const KIND_ICON: Record<FilterKind, IconName> = {
  text: "type",
  number: "number",
  date: "calendar",
  boolean: "toggle",
  relation: "link",
};

/** The conditions each kind offers: the common ones in the segmented control, the rest under More (D162). */
const CONDITIONS: Record<Exclude<FilterKind, "relation">, { common: [string, string][]; more: [string, string][] }> = {
  text: {
    common: [
      ["contains", "Contains"],
      ["eq", "Is"],
      ["startsWith", "Starts with"],
    ],
    more: [
      ["isNull", "Is empty"],
      ["isNull:false", "Has a value"],
    ],
  },
  number: {
    common: [
      ["eq", "Is"],
      ["lt", "Less than"],
      ["gt", "More than"],
    ],
    more: [
      ["lte", "At most"],
      ["gte", "At least"],
      ["isNull", "Is empty"],
      ["isNull:false", "Has a value"],
    ],
  },
  date: {
    common: [
      ["eq", "Is"],
      ["lt", "Before"],
      ["gt", "After"],
    ],
    more: [
      ["lte", "On or before"],
      ["gte", "On or after"],
      ["isNull", "Is empty"],
      ["isNull:false", "Has a value"],
    ],
  },
  boolean: {
    common: [],
    more: [
      ["isNull", "Is empty"],
      ["isNull:false", "Has a value"],
    ],
  },
};

const NO_VALUE = new Set(["isNull", "isUnset"]);

function conditions(kind: Exclude<FilterKind, "relation">, attribute: boolean) {
  const { common, more } = CONDITIONS[kind];
  return {
    common,
    more: attribute
      ? [...more, ["isUnset", "Not set"] as [string, string], ["isUnset:false", "Is set"] as [string, string]]
      : more,
  };
}

function conditionWord(kind: Exclude<FilterKind, "relation">, operator: string): string {
  const { common, more } = conditions(kind, true);
  return ([...common, ...more].find(([key]) => key === operator)?.[1] ?? operator).toLowerCase();
}

/** A More condition's key is its operator, with `:false` for the negated no-value conditions. */
function splitCondition(key: string): { operator: string; value: string } {
  const [operator, flag] = key.split(":");
  return { operator, value: flag === "false" ? "false" : "true" };
}
const conditionKey = (entry: CollectionFilter) =>
  NO_VALUE.has(entry.operator) && entry.value === "false" ? `${entry.operator}:false` : entry.operator;

/** The field's kind, from the model: a relationship, or the attribute's value type. */
export function filterKind(model: EngineModel, field: string): FilterKind {
  if (field.startsWith("relation:")) return filterKind(model, field.slice("relation:".length));
  if (field.startsWith(RELATED_FIELD_PREFIX)) return "relation";
  if (["createdAt", "updatedAt"].includes(field)) return "date";
  const type: ValueType | undefined = model.attributeTypes.find((item) => item.key === field)?.valueType;
  if (type === "boolean") return "boolean";
  if (type === "integer" || type === "decimal") return "number";
  if (type === "date" || type === "dateTime") return "date";
  return "text";
}

export function filterFields(model: EngineModel, fields: readonly string[]): FilterField[] {
  return fields.map((field) => ({
    field,
    label: attributeName(model, field),
    kind: filterKind(model, field),
    attribute: !field.startsWith(RELATED_FIELD_PREFIX) && !["id", "name", "createdAt", "updatedAt"].includes(field),
  }));
}

/** A pill's two parts: the field (with its condition) and the value. */
export function pillText(
  spec: FilterField,
  entries: readonly CollectionFilter[],
  names: ReadonlyMap<string, NamedRecord>,
): { label: string; value: string } {
  if (spec.kind === "relation") {
    const mode = relationFilterMode(entries);
    if (mode === "none") return { label: spec.label, value: "none" };
    if (mode === "some") return { label: spec.label, value: "any" };
    if (mode === "under" || mode === "notUnder")
      return {
        label: spec.label,
        value: `${mode === "under" ? "has any under" : "has none under"} ${names.get(entries[0].value)?.name ?? "…"}`,
      };
    const chosen = entries.map((entry) => names.get(entry.value)?.name ?? "…");
    return {
      label: spec.label,
      value: chosen.length > 2 ? `${chosen.slice(0, 2).join(", ")} +${chosen.length - 2}` : chosen.join(", "),
    };
  }
  const [entry] = entries;
  if (NO_VALUE.has(entry.operator)) {
    const negated = entry.value === "false";
    const word = entry.operator === "isNull" ? (negated ? "has a value" : "is empty") : negated ? "is set" : "not set";
    return { label: spec.label, value: word };
  }
  if (spec.kind === "boolean") return { label: spec.label, value: entry.value === "true" ? "Yes" : "No" };
  return { label: `${spec.label} ${conditionWord(spec.kind, entry.operator)}`, value: entry.value };
}

/**
 * The pills a set of filters makes: one per field, a relationship's records together; any other
 * field's entries are a pill each, such as the two ends of a date range (0.16 AG4).
 */
export function filterPills(fields: readonly FilterField[], filters: readonly CollectionFilter[]) {
  return fields.flatMap((spec) => {
    const entries = filters.filter((filter) => filter.field === spec.field);
    return spec.kind === "relation"
      ? entries.length
        ? [{ spec, entries }]
        : []
      : entries.map((entry) => ({ spec, entries: [entry] }));
  });
}

/** Below this width the editors are drawn as a bottom sheet (D163). */
const NARROW = "(max-width: 600px)";

/** A filter as a read-only pill: the same words as the bar's, for one that is only proposed or shown. */
export function FilterPill({ label, value, proposed = false }: { label: string; value: string; proposed?: boolean }) {
  return (
    <span className={proposed ? "filter-pill proposed" : "filter-pill"}>
      <span className="filter-pill-label">{label}</span> <span className="filter-pill-value">{value}</span>
    </span>
  );
}

export function FilterBar({
  model,
  objectTypeKey,
  fields,
  filters,
  names,
  workspaceKey,
  noun,
  countDraft,
  onChange,
}: {
  model: EngineModel;
  objectTypeKey: string;
  fields: readonly FilterField[];
  filters: readonly CollectionFilter[];
  names: ReadonlyMap<string, NamedRecord>;
  workspaceKey?: string;
  /** The listed records' names, singular and plural, for "Show 3 master values" (D163). */
  noun: readonly [string, string];
  /** How many records the list shows with these filters (the sheet's Apply). */
  countDraft: (filters: CollectionFilter[]) => Promise<number | undefined>;
  onChange: (filters: CollectionFilter[]) => void;
}) {
  const active = fields.filter((spec) => filters.some((filter) => filter.field === spec.field));
  const pills = filterPills(fields, filters);
  const replace = (taken: readonly CollectionFilter[], entries: CollectionFilter[]) =>
    onChange([...filters.filter((filter) => !taken.includes(filter)), ...entries]);
  /** What a new filter on the field replaces: its entries where it holds one condition only, else nothing. */
  const replaced = (spec: FilterField) =>
    spec.kind === "relation" || spec.kind === "boolean" ? filters.filter((f) => f.field === spec.field) : [];
  const editorProps = (spec: FilterField, taken: readonly CollectionFilter[]) => ({
    model,
    objectTypeKey,
    spec,
    entries: taken,
    others: filters.filter((filter) => !taken.includes(filter)),
    names,
    workspaceKey,
    noun,
    countDraft,
  });

  return (
    <div className="filter-bar" role="group" aria-label="Filters">
      {pills.map(({ spec, entries }, index) => {
        const text = pillText(spec, entries, names);
        return (
          <span key={`${spec.field}:${index}`} className="filter-pill">
            <ControlPopover
              label={`${text.label}: ${text.value}. Change this filter`}
              trigger={
                <>
                  <span className="filter-pill-label">{text.label}</span>
                  <span className="filter-pill-value">{text.value}</span>
                </>
              }
              triggerClassName="filter-pill-open"
              className="filter-popover"
              placement="bottom start"
              header={false}
            >
              {(close) => (
                <FilterEditor
                  {...editorProps(spec, entries)}
                  onApply={(next) => {
                    replace(entries, next);
                    close();
                  }}
                  onCancel={close}
                />
              )}
            </ControlPopover>
            <button
              type="button"
              className="filter-pill-remove"
              aria-label={`Remove the ${spec.label} filter`}
              onClick={() => replace(entries, [])}
            >
              <Icon name="close" size={13} />
            </button>
          </span>
        );
      })}
      {fields.length > 0 && (
        <ControlPopover
          label="Filter"
          trigger={
            <>
              <Icon name="plus" size={14} /> Filter
            </>
          }
          triggerClassName="filter-add"
          className="filter-popover"
          placement="bottom start"
          header={false}
        >
          {(close) => (
            <AddFilter
              fields={fields}
              active={new Set(active.map((spec) => spec.field))}
              editor={(spec, back) => (
                <FilterEditor
                  {...editorProps(spec, replaced(spec))}
                  onApply={(next) => {
                    replace(replaced(spec), next);
                    close();
                  }}
                  onCancel={back}
                />
              )}
            />
          )}
        </ControlPopover>
      )}
      {active.length > 0 && (
        <button type="button" className="ghost filter-clear" onClick={() => onChange([])}>
          Clear all
        </button>
      )}
    </div>
  );
}

/** ＋ Filter's popover: the field menu, then the chosen field's editor. */
function AddFilter({
  fields,
  active,
  editor,
}: {
  fields: readonly FilterField[];
  active: ReadonlySet<string>;
  editor: (spec: FilterField, back: () => void) => React.ReactNode;
}) {
  const [picked, setPicked] = useState<FilterField>();
  if (picked) return <>{editor(picked, () => setPicked(undefined))}</>;
  return (
    <FieldMenu
      label="Filter by"
      items={fields.map((spec) => ({
        key: spec.field,
        label: spec.label,
        icon: KIND_ICON[spec.kind],
        group: spec.kind === "relation" ? "Relationships" : "Fields",
        active: active.has(spec.field),
      }))}
      onPick={(key) => setPicked(fields.find((spec) => spec.field === key))}
    />
  );
}

function FilterEditor({
  model,
  objectTypeKey,
  spec,
  entries,
  others,
  names,
  workspaceKey,
  noun,
  countDraft,
  onApply,
  onCancel,
}: {
  model: EngineModel;
  objectTypeKey: string;
  spec: FilterField;
  entries: readonly CollectionFilter[];
  /** The list's other filters, which the sheet's count reads with the draft. */
  others: readonly CollectionFilter[];
  names: ReadonlyMap<string, NamedRecord>;
  workspaceKey?: string;
  noun: readonly [string, string];
  countDraft: (filters: CollectionFilter[]) => Promise<number | undefined>;
  onApply: (entries: CollectionFilter[]) => void;
  onCancel: () => void;
}) {
  const narrow = useMediaQuery(NARROW);
  const [draft, setDraft] = useState<CollectionFilter[]>(() => entries.slice());
  // The relationship editor's ticked records, with their names for the checklist.
  const [picked, setPicked] = useState<ChecklistRecord[]>(() =>
    entries
      .filter((entry) => entry.operator === "eq")
      .map((entry) => {
        const named = names.get(entry.value);
        return { id: entry.value, name: named?.name ?? "…", objectTypeKey: named?.objectTypeKey ?? "" };
      }),
  );
  // "Has none under" and "has any under" choose one record above the related ones (0.16 AG4); the
  // mode is kept here, as that draft holds no entry until a record is chosen.
  const [mode, setMode] = useState<RelationMode>(() => relationFilterMode(entries));
  const [under, setUnder] = useState<ChecklistRecord[]>(() =>
    entries
      .filter((entry) => entry.operator === "under" || entry.operator === "notUnder")
      .map((entry) => {
        const named = names.get(entry.value);
        return { id: entry.value, name: named?.name ?? "…", objectTypeKey: named?.objectTypeKey ?? "" };
      }),
  );
  const [count, setCount] = useState<{ of: string; total: number | undefined }>();
  const draftKey = JSON.stringify([...others, ...draft]);
  useEffect(() => {
    if (!narrow) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void countDraft(JSON.parse(draftKey) as CollectionFilter[]).then((total) => {
        if (!cancelled) setCount({ of: draftKey, total });
      });
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [narrow, draftKey, countDraft]);
  const shown = count?.of === draftKey ? count.total : undefined;
  const pluralName = noun[1];
  const applyLabel =
    narrow && shown !== undefined
      ? `Show ${shown.toLocaleString("en")} ${(shown === 1 ? noun[0] : noun[1]).toLowerCase()}`
      : "Apply";

  const header = (
    <div className="filter-editor-header">
      <h2>{spec.label}</h2>
      {spec.kind === "relation" && <span>Relationship</span>}
    </div>
  );

  if (spec.kind === "relation") {
    const chosen = picked;
    const targets = relatedTargetTypes(model, objectTypeKey, spec.field);
    const ancestors = relatedAncestorTypes(model, objectTypeKey, spec.field);
    const beneath = mode === "under" || mode === "notUnder";
    const choose = (next: RelationMode) => {
      setMode(next);
      setDraft(
        relationFilterEntries(
          spec.field,
          next,
          next === "any" ? picked : next === "under" || next === "notUnder" ? under : [],
        ),
      );
    };
    return (
      <form
        className="filter-editor"
        aria-label={`Filter by ${spec.label}`}
        onSubmit={(event) => {
          event.preventDefault();
          onApply(draft);
        }}
      >
        {header}
        <Choice
          name={`filter-${spec.field}-mode`}
          value={mode}
          options={[
            ["any", "Is any of"],
            ["none", "Has none"],
            ["some", "Has any"],
            ...(ancestors.length
              ? ([
                  ["notUnder", "Has none under"],
                  ["under", "Has any under"],
                ] as const)
              : []),
          ]}
          onChange={choose}
        />
        {beneath ? (
          <>
            <RecordChecklist
              model={model}
              label={ancestors.length === 1 ? ancestors[0].pluralName : "Records"}
              objectTypeKeys={ancestors.map((type) => type.key)}
              workspaceKey={workspaceKey}
              chosen={under}
              onChange={(next) => {
                // One record: the one just ticked replaces the one before.
                const added = next.find((record) => !under.some((item) => item.id === record.id));
                const one = added ? [added] : next.slice(0, 1);
                setUnder(one);
                setDraft(relationFilterEntries(spec.field, mode, one));
              }}
            />
            <p className="filter-editor-explain">
              {mode === "notUnder"
                ? `Shows the ${pluralName.toLowerCase()} with no ${spec.label.toLowerCase()} record at any depth below the chosen one.`
                : `Shows the ${pluralName.toLowerCase()} with some ${spec.label.toLowerCase()} record at any depth below the chosen one.`}
            </p>
          </>
        ) : mode === "any" ? (
          <RecordChecklist
            model={model}
            label={targets.length === 1 ? targets[0].pluralName : "Records"}
            objectTypeKeys={targets.map((type) => type.key)}
            workspaceKey={workspaceKey}
            candidates={keyScope(model, spec.field.slice(RELATED_FIELD_PREFIX.length), objectTypeKey)}
            chosen={chosen}
            onChange={(next) => {
              setPicked(next);
              setDraft(relationFilterEntries(spec.field, "any", next));
            }}
          />
        ) : (
          <p className="filter-editor-explain">
            {mode === "none"
              ? `Shows the ${pluralName.toLowerCase()} with no ${spec.label.toLowerCase()} relationship.`
              : `Shows the ${pluralName.toLowerCase()} with at least one ${spec.label.toLowerCase()} relationship.`}
          </p>
        )}
        <div className="filter-editor-actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Cancel
          </button>
          <button className="primary" disabled={beneath && under.length === 0}>
            {applyLabel}
          </button>
        </div>
      </form>
    );
  }

  const [entry] = draft.length
    ? draft
    : [{ field: spec.field, operator: spec.kind === "text" ? "contains" : "eq", value: "" }];
  const { common, more } = conditions(spec.kind, spec.attribute);
  const set = (next: Partial<CollectionFilter>) => setDraft([{ ...entry, ...next, field: spec.field }]);

  if (spec.kind === "boolean") {
    // Yes, No or Any, applied as it is chosen (D161).
    const value = entry.operator === "eq" && draft.length ? entry.value : "any";
    return (
      <div className="filter-editor" role="group" aria-label={`Filter by ${spec.label}`}>
        {header}
        <Choice
          name={`filter-${spec.field}`}
          value={value as "true" | "false" | "any"}
          options={[
            ["true", "Yes"],
            ["false", "No"],
            ["any", "Any"],
          ]}
          onChange={(next) => onApply(next === "any" ? [] : [{ field: spec.field, operator: "eq", value: next }])}
        />
        <MoreConditions
          label={spec.label}
          more={more}
          value={NO_VALUE.has(entry.operator) && draft.length ? conditionKey(entry) : ""}
          onChange={(key) => onApply([{ field: spec.field, ...splitCondition(key) }])}
        />
        <p className="filter-editor-explain">Applies as you choose.</p>
      </div>
    );
  }

  const noValue = NO_VALUE.has(entry.operator);
  return (
    <form
      className="filter-editor"
      aria-label={`Filter by ${spec.label}`}
      onSubmit={(event) => {
        event.preventDefault();
        onApply(noValue ? [entry] : entry.value.trim() ? [{ ...entry, value: entry.value.trim() }] : []);
      }}
    >
      {header}
      <div className="filter-editor-conditions">
        <Choice
          name={`filter-${spec.field}-condition`}
          value={common.some(([key]) => key === entry.operator) ? entry.operator : ""}
          options={common as [string, string][]}
          onChange={(operator) => set({ operator, value: noValue ? "" : entry.value })}
        />
        <MoreConditions
          label={spec.label}
          more={more}
          value={more.some(([key]) => key === conditionKey(entry)) ? conditionKey(entry) : ""}
          onChange={(key) => {
            const next = splitCondition(key);
            set(NO_VALUE.has(next.operator) ? next : { operator: next.operator, value: entry.value });
          }}
        />
      </div>
      {!noValue && (
        <input
          className="filter-editor-input"
          aria-label={spec.label}
          type={spec.kind === "number" ? "number" : spec.kind === "date" ? "date" : "text"}
          value={entry.value}
          autoFocus
          onChange={(event) => set({ value: event.target.value })}
        />
      )}
      <div className="filter-editor-actions">
        <button type="button" className="ghost" onClick={onCancel}>
          Cancel
        </button>
        <button className="primary">{applyLabel}</button>
      </div>
    </form>
  );
}

/** The rarer conditions, at the segmented control's end (D162). */
function MoreConditions({
  label,
  more,
  value,
  onChange,
}: {
  label: string;
  more: [string, string][];
  value: string;
  onChange: (operator: string) => void;
}) {
  if (!more.length) return null;
  return (
    <select
      className={value ? "filter-more chosen" : "filter-more"}
      aria-label={`More conditions for ${label}`}
      value={value}
      onChange={(event) => event.target.value && onChange(event.target.value)}
    >
      <option value="">More</option>
      {more.map(([key, word]) => (
        <option key={key} value={key}>
          {word}
        </option>
      ))}
    </select>
  );
}
