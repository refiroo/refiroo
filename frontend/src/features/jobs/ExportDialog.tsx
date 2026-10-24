/**
 * Start an export (0.9 J1u, J27.6). From a collection the dialog is prefilled with what the page
 * shows: its type, its data context, its filters and its parent scope; the search is not carried
 * (D60). From Settings › Jobs it starts empty, with a workspace to choose (D57). The export runs in
 * the background; the notifications follow it (`JobNotifications`).
 *
 * From a collection it also offers a workbook for people (0.9 J6, J27.15, D179): the columns the
 * table shows, in its order, and in Advanced the columns, the field a relation column shows and the
 * relationships that get a sheet of their own (by default those the table shows as columns).
 */

import { useId, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  CollectionFilter,
  EngineModel,
  ExportFormat,
  ExportLayout,
  ExportRelations,
  ExportRequest,
  Job,
} from "@/types";
import { attributeName } from "@/model/fields";
import { RELATED_FIELD_PREFIX } from "@/model/lookup";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import { Icon } from "@/ui/Icon";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import {
  criteriaFromFilters,
  exportField,
  exportableTypes,
  peopleLayout,
  relationFields,
  relationKeyOf,
  sheetRelationships,
  ownedType,
  type ExportField,
  type OwnedChoice,
  type PeopleColumn,
} from "./exportRequest";
import { parentObjectTypeKeys } from "@/model/placements";
import { RecordListField } from "@/ui/RecordListField";

export interface ExportStart {
  /** The workspace; none lets the user choose one. */
  workspaceKey?: string;
  changeSetId?: string;
  publicationId?: string;
  /** The types offered, in the model's order, and those chosen at first. */
  objectTypeKeys: readonly string[];
  selected: readonly string[];
  /** The collection's filters, for its type. */
  filters?: { objectTypeKey: string; filters: CollectionFilter[] };
  search?: string;
  /** The page's parent scope: records directly below this record, of the filtered type. */
  parentObjectId?: string;
  /**
   * The table's columns as its Display shows them, in order, and those it hides: given, the dialog
   * offers a workbook for people of the filtered type (0.9 J6).
   */
  columns?: { shown: readonly string[]; hidden: readonly string[] };
}

const RELATIONS: readonly (readonly [ExportRelations, string])[] = [
  ["withinScope", "Between exported records"],
  ["all", "All their relationships"],
  ["none", "None"],
];

const KINDS: readonly (readonly [ExportLayout, string])[] = [
  ["technical", "Technical"],
  ["people", "For people"],
];

const FORMATS: readonly (readonly [ExportFormat, string])[] = [
  ["xlsx", "Excel (XLSX)"],
  ["csv", "CSV"],
  ["jsonl", "JSON Lines"],
];

export function ExportDialog({
  model,
  start,
  onClose,
  onStarted,
}: {
  model: EngineModel;
  start: ExportStart;
  onClose: () => void;
  onStarted: (job: Job) => void;
}) {
  const types = useMemo(() => exportableTypes(model, start.objectTypeKeys), [model, start.objectTypeKeys]);
  const [workspaceKey, setWorkspaceKey] = useState(start.workspaceKey ?? "");
  const [chosen, setChosen] = useState<string[]>([...start.selected]);
  const [belowParent, setBelowParent] = useState(Boolean(start.parentObjectId));
  const [asOf, setAsOf] = useState("");
  const [relations, setRelations] = useState<ExportRelations>("withinScope");
  const [format, setFormat] = useState<ExportFormat>("xlsx");
  const people = start.columns && start.filters ? start.filters.objectTypeKey : undefined;
  const [layout, setLayout] = useState<ExportLayout>("technical");
  const [columns, setColumns] = useState<PeopleColumn[]>(() => [
    ...(start.columns?.shown ?? []).map((key) => ({ key, shown: true })),
    ...(start.columns?.hidden ?? []).map((key) => ({ key, shown: false })),
  ]);
  const [fields, setFields] = useState<Record<string, string>>({});
  const relationships = useMemo(() => (people ? sheetRelationships(model, people) : []), [model, people]);
  // By default the relationships the table shows as columns get a sheet of their own (D182).
  const [sheets, setSheets] = useState<string[]>(() =>
    relationships
      .map((item) => item.key)
      .filter((key) =>
        (start.columns?.shown ?? []).some(
          (column) => column.startsWith(RELATED_FIELD_PREFIX) && relationKeyOf(model, column) === key,
        ),
      ),
  );
  const forPeople = layout === "people" && people !== undefined;
  // Owned relationships laid out as columns per parent, and whether cells offer lists (0.9 J6a).
  const [owned, setOwned] = useState<Record<string, OwnedChoice>>({});
  const [lists, setLists] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: ExportField; message: string }>();

  const dated = types.some((type) => chosen.includes(type.key) && type.effectivePeriod);
  const filtered = start.filters && chosen.includes(start.filters.objectTypeKey) ? start.filters : undefined;
  // The page's scope is a criterion on its own type, as the page reads it: direct children only.
  const scoped = filtered && start.parentObjectId && belowParent ? start.parentObjectId : undefined;
  const context = start.changeSetId ? "the change set" : start.publicationId ? "the publication" : "live data";

  async function submit() {
    const chosenTypes = forPeople ? [people] : chosen;
    const body: ExportRequest = {
      workspaceKey,
      context: { changeSetId: start.changeSetId ?? null, publicationId: start.publicationId ?? null },
      scope: {
        types: types
          .filter((type) => chosenTypes.includes(type.key))
          .map((type) => ({
            objectTypeKey: type.key,
            where:
              filtered?.objectTypeKey === type.key
                ? [
                    ...criteriaFromFilters(model, filtered.filters),
                    ...(scoped ? [{ field: "parentObjectId", op: "eq", value: scoped }] : []),
                  ]
                : [],
          })),
        parentObjectId: null,
        asOf: dated && asOf ? asOf : null,
      },
      include: { relations },
      format: forPeople ? "xlsx" : format,
      ...(forPeople ? { layout: "people" as const, people: peopleLayout(columns, sheets, fields, owned, lists) } : {}),
    };
    setPending(true);
    setError(undefined);
    try {
      onStarted(await api.createExport(body));
    } catch (cause) {
      const pointer = isApiError(cause) ? (cause.details as { path?: unknown } | undefined)?.path : undefined;
      setError({ field: exportField(pointer), message: errorMessage(cause) });
    } finally {
      setPending(false);
    }
  }

  const fieldError = (field: ExportField) => (error?.field === field ? error.message : undefined);

  return (
    <Modal title="Export" size="wide" busy={pending} onClose={onClose}>
      <form
        className="dialog-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <section className="dialog-form-section" aria-labelledby="export-what">
          <h3 id="export-what">What to export</h3>
          {people && (
            <FormField
              label="Kind of file"
              help={
                forPeople
                  ? "A workbook people work in: the table's columns, a sheet per chosen relationship, and what it needs to be imported back as it is."
                  : "The engine's exact tables, for integrations and round trips of several types."
              }
              group
            >
              {() => <Choice name="export-layout" value={layout} options={KINDS} onChange={setLayout} />}
            </FormField>
          )}
          {!start.workspaceKey && (
            <WorkspaceField
              holding="browse"
              value={workspaceKey}
              onChange={setWorkspaceKey}
              onError={(message) => setError({ field: "form", message })}
            />
          )}
          {!forPeople && (
            <FormField
              label="Record types"
              help={`Read from ${context}${start.workspaceKey ? ` in workspace “${start.workspaceKey}”` : ""}, all at one instant.`}
              error={fieldError("types")}
            >
              {(control) => (
                <MultiSelect
                  label="Record types"
                  describedBy={control["aria-describedby"]}
                  options={types.map((type) => ({ id: type.key, label: type.pluralName }))}
                  selected={chosen}
                  onChange={setChosen}
                  addLabel="Add a type"
                  emptyLabel="No type chosen yet."
                />
              )}
            </FormField>
          )}
          {filtered && filtered.filters.length > 0 && (
            <p className="admin-hint">
              {model.objectTypes.find((type) => type.key === filtered.objectTypeKey)?.pluralName} are exported with this
              page's {filtered.filters.length === 1 ? "filter" : `${filtered.filters.length} filters`}.
            </p>
          )}
          {start.search && (
            <Notice tone="info">
              The page's search “{start.search}” is not applied: an export selects records by filters only.
            </Notice>
          )}
          {start.parentObjectId && filtered && (
            <FormField label="Where" error={fieldError("scope")} group>
              {() => (
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={belowParent}
                    onChange={(event) => setBelowParent(event.target.checked)}
                  />
                  Only the{" "}
                  {model.objectTypes.find((type) => type.key === filtered.objectTypeKey)?.pluralName.toLowerCase()} this
                  page is narrowed to
                </label>
              )}
            </FormField>
          )}
          {dated && (
            <FormField
              label="Valid on"
              help="Types with a validity period export the records valid on this date; the others are exported as they are. Leave empty for all."
              error={fieldError("asOf")}
            >
              {(control) => (
                <input {...control} type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
              )}
            </FormField>
          )}
        </section>

        {forPeople ? (
          <PeopleAdvanced
            model={model}
            objectTypeKey={people}
            columns={columns}
            onColumns={setColumns}
            fields={fields}
            onFields={setFields}
            relationships={relationships}
            sheets={sheets}
            onSheets={setSheets}
            owned={owned}
            onOwned={setOwned}
            lists={lists}
            onLists={setLists}
            workspaceKey={workspaceKey}
            error={fieldError("layout")}
          />
        ) : (
          <section className="dialog-form-section" aria-labelledby="export-file">
            <h3 id="export-file">The file</h3>
            <FormField label="Relationships" group>
              {() => <Choice name="export-relations" value={relations} options={RELATIONS} onChange={setRelations} />}
            </FormField>
            <FormField label="Format" group>
              {() => <Choice name="export-format" value={format} options={FORMATS} onChange={setFormat} />}
            </FormField>
          </section>
        )}

        {error?.field === "form" && (
          <Notice tone="error" title="The export was not started">
            {error.message}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              pending || !workspaceKey || (forPeople ? !columns.some((column) => column.shown) : !chosen.length)
            }
          >
            {pending ? "Starting…" : "Start export"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * The workbook's Advanced section (0.9 J6): the main sheet's columns (shown or not, in order), the
 * field a relation column of names shows instead, and the relationships with a sheet of their own.
 */
function PeopleAdvanced({
  model,
  objectTypeKey,
  columns,
  onColumns,
  fields,
  onFields,
  relationships,
  sheets,
  onSheets,
  owned,
  onOwned,
  lists,
  onLists,
  workspaceKey,
  error,
}: {
  model: EngineModel;
  objectTypeKey: string;
  columns: PeopleColumn[];
  onColumns: (columns: PeopleColumn[]) => void;
  fields: Record<string, string>;
  onFields: (fields: Record<string, string>) => void;
  relationships: { key: string; label: string }[];
  sheets: string[];
  onSheets: (sheets: string[]) => void;
  owned: Record<string, OwnedChoice>;
  onOwned: (owned: Record<string, OwnedChoice>) => void;
  lists: boolean;
  onLists: (lists: boolean) => void;
  workspaceKey: string;
  error?: string;
}) {
  const id = useId();
  const move = (index: number, by: number) => {
    const next = [...columns];
    [next[index], next[index + by]] = [next[index + by], next[index]];
    onColumns(next);
  };
  return (
    <section className="dialog-form-section" aria-labelledby={`${id}-file`}>
      <h3 id={`${id}-file`}>The workbook</h3>
      <p className="admin-hint">
        One Excel workbook. Columns of names list every related record, separated by “; ”. A relationship with a sheet
        of its own is edited there; its column is written for reading only.
      </p>
      {error && (
        <Notice tone="error" title="The workbook cannot be made this way">
          {error}
        </Notice>
      )}
      <details className="export-advanced">
        <summary>Advanced: columns and sheets</summary>
        <div className="export-advanced-body">
          <fieldset>
            <legend>Columns of the main sheet</legend>
            <ul className="export-columns">
              {columns.map((column, index) => {
                const label = attributeName(model, column.key);
                const choices = relationFields(model, objectTypeKey, column.key);
                return (
                  <li key={column.key}>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={column.shown}
                        onChange={(event) =>
                          onColumns(
                            columns.map((item) =>
                              item.key === column.key ? { ...item, shown: event.target.checked } : item,
                            ),
                          )
                        }
                      />
                      {label}
                    </label>
                    <span className="export-column-moves">
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Move ${label} up`}
                        disabled={index === 0}
                        onClick={() => move(index, -1)}
                      >
                        <Icon name="sort-ascending" size={14} />
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Move ${label} down`}
                        disabled={index === columns.length - 1}
                        onClick={() => move(index, 1)}
                      >
                        <Icon name="sort-descending" size={14} />
                      </button>
                    </span>
                    {choices.length > 0 && column.shown && (
                      <select
                        aria-label={`${label} shows`}
                        value={fields[column.key] ?? ""}
                        onChange={(event) => onFields({ ...fields, [column.key]: event.target.value })}
                      >
                        <option value="">Names</option>
                        {choices.map((choice) => (
                          <option key={choice.key} value={choice.key}>
                            {choice.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </li>
                );
              })}
            </ul>
          </fieldset>
          {relationships.length > 0 && (
            <fieldset>
              <legend>Relationships with a sheet of their own</legend>
              {relationships.map((relationship) => {
                const ownedKey = ownedType(model, objectTypeKey, relationship.key);
                const ticked = sheets.includes(relationship.key);
                return (
                  <div key={relationship.key} className="export-sheet">
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={ticked}
                        onChange={(event) =>
                          onSheets(
                            event.target.checked
                              ? [...sheets, relationship.key]
                              : sheets.filter((key) => key !== relationship.key),
                          )
                        }
                      />
                      {relationship.label}
                    </label>
                    {ownedKey && ticked && (
                      <OwnedLayoutField
                        model={model}
                        label={relationship.label}
                        ownedKey={ownedKey}
                        workspaceKey={workspaceKey}
                        choice={owned[relationship.key] ?? defaultOwned(model, ownedKey)}
                        onChange={(choice) => onOwned({ ...owned, [relationship.key]: choice })}
                      />
                    )}
                  </div>
                );
              })}
            </fieldset>
          )}
          <label className="checkbox">
            <input type="checkbox" checked={lists} onChange={(event) => onLists(event.target.checked)} />
            <span>
              Cells naming one record offer a list to choose from
              <small>
                A sheet per list holds the records the relationship may choose; a value outside it is refused on import.
              </small>
            </span>
          </label>
        </div>
      </details>
    </section>
  );
}

/** The fields an owned type's columns per parent hold by default: its writable attributes. */
function defaultOwned(model: EngineModel, ownedKey: string): OwnedChoice {
  const owned = model.objectTypes.find((item) => item.key === ownedKey);
  const writable = (owned?.attributes ?? []).filter((item) => !item.readOnly).map((item) => item.attributeTypeKey);
  return { columns: false, parents: {}, fields: writable.length ? writable : ["name"] };
}

const OWNED_LAYOUTS: readonly (readonly ["rows" | "columns", string])[] = [
  ["rows", "Rows"],
  ["columns", "Columns per parent"],
];

/**
 * An owned relationship's layout (0.9 J6a, D191, D192): rows, or a column per parent and field;
 * the parents holding records come by themselves, others are added with the record search.
 */
function OwnedLayoutField({
  model,
  label,
  ownedKey,
  workspaceKey,
  choice,
  onChange,
}: {
  model: EngineModel;
  label: string;
  ownedKey: string;
  workspaceKey: string;
  choice: OwnedChoice;
  onChange: (choice: OwnedChoice) => void;
}) {
  const ownedType = model.objectTypes.find((item) => item.key === ownedKey);
  const parentTypes = [
    ...new Set(
      model.applications
        .filter((application) => application.objectTypeKeys.includes(ownedKey))
        .flatMap((application) => parentObjectTypeKeys(model, application, ownedKey)),
    ),
  ];
  const fields = [
    "name",
    ...(ownedType?.attributes ?? []).filter((item) => !item.readOnly).map((item) => item.attributeTypeKey),
  ];
  return (
    <div className="export-owned">
      <FormField label={`${label}: layout`} group>
        {() => (
          <Choice
            name={`owned-${ownedKey}-${label}`}
            value={choice.columns ? "columns" : "rows"}
            options={OWNED_LAYOUTS}
            onChange={(value) => onChange({ ...choice, columns: value === "columns" })}
          />
        )}
      </FormField>
      {choice.columns && (
        <>
          <p className="admin-hint">
            One row per record, a column per parent and field. Parents already holding{" "}
            {ownedType?.pluralName.toLowerCase()} get columns; add others to fill in new ones.
          </p>
          {parentTypes.map((parentKey) => (
            <RecordListField
              key={parentKey}
              label={`More columns for these ${model.objectTypes.find((item) => item.key === parentKey)?.pluralName ?? parentKey}`}
              objectTypeKey={parentKey}
              workspaceKey={workspaceKey}
              values={choice.parents[parentKey] ?? []}
              onChange={(values) => onChange({ ...choice, parents: { ...choice.parents, [parentKey]: values } })}
            />
          ))}
          <fieldset>
            <legend>{`${label}: fields per parent`}</legend>
            {fields.map((field) => (
              <label key={field} className="checkbox">
                <input
                  type="checkbox"
                  checked={choice.fields.includes(field)}
                  onChange={(event) =>
                    onChange({
                      ...choice,
                      fields: event.target.checked
                        ? fields.filter((item) => item === field || choice.fields.includes(item))
                        : choice.fields.filter((item) => item !== field),
                    })
                  }
                />
                {attributeName(model, field)}
              </label>
            ))}
          </fieldset>
        </>
      )}
    </div>
  );
}
