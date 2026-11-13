/**
 * Start an export (0.9 J1u, J27.6; 0.17 EX1). One dialog for every page: from a list view it opens
 * on "This view", the file that view shows for editing; the other choices are the view's type, its
 * application and the whole workspace, each a sheet per type. From a collection it is prefilled with
 * what the page shows (its filters, its parent scope, its search); from Settings › Jobs it starts
 * empty, with a workspace to choose (D57). The export runs in the background; the notifications
 * follow it (`JobNotifications`).
 *
 * For editing, a table also offers the workbook's Advanced (0.9 J6, D179): the columns, the field a
 * relation column shows and the relationships that get a sheet of their own. A matrix that creates
 * cell records asks where each column's new cells go (PP-D20).
 */

import { useEffect, useId, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ExportFormat, ExportLayout, ExportRelations, ExportRequest, Job } from "@/types";
import { useRelationFilterNames } from "@/ui/relationFilterNames";
import { attributeName } from "@/model/fields";
import { RELATED_FIELD_PREFIX } from "@/model/lookup";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { WorkspaceField } from "@/ui/WorkspaceField";
import { Icon } from "@/ui/Icon";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import {
  criteriaFromFilters,
  exportField,
  exportViewState,
  viewCountLine,
  exportableTypes,
  identifyingFields,
  peopleLayout,
  relationFields,
  relationKeyOf,
  needsSheet,
  sheetRelationships,
  ownedType,
  type ExportField,
  type ExportStart,
  type ExportViewStart,
  type OwnedChoice,
  type PeopleColumn,
} from "@/model/exportRequest";
import { parentObjectTypeKeys } from "@/model/placements";
import { RecordListField } from "@/ui/RecordListField";

/** What an export is of: the page's view, its type, its application or the whole workspace. */
type What = "view" | "type" | "application" | "workspace";

const RELATIONS: readonly (readonly [ExportRelations, string])[] = [
  ["withinScope", "Between exported records"],
  ["all", "All their relationships"],
  ["none", "None"],
];

const KINDS: readonly (readonly [ExportLayout, string])[] = [
  ["people", "For editing in a spreadsheet"],
  ["technical", "Technical"],
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
  const viewStart = start.view;
  const typeName = (key: string) => model.objectTypes.find((item) => item.key === key)?.pluralName ?? key;
  const application = model.applications.find((item) => item.key === viewStart?.applicationKey);
  const [workspaceKey, setWorkspaceKey] = useState(start.workspaceKey ?? "");
  const [what, setWhat] = useState<What>("view");
  const [chosen, setChosen] = useState<string[]>([...start.selected]);
  const [belowParent, setBelowParent] = useState(Boolean(start.parentObjectId));
  const [asOf, setAsOf] = useState("");
  const [relations, setRelations] = useState<ExportRelations>("withinScope");
  const [format, setFormat] = useState<ExportFormat>("xlsx");
  // The page's table, for a workbook of one type's collection with its Advanced (0.9 J6).
  const people = start.columns && start.filters ? start.filters.objectTypeKey : undefined;
  const [layout, setLayout] = useState<ExportLayout>(viewStart ? "people" : "technical");
  const [columns, setColumns] = useState<PeopleColumn[]>(() => [
    ...(start.columns?.shown ?? []).map((key) => ({ key, shown: true })),
    ...(start.columns?.hidden ?? []).map((key) => ({ key, shown: false })),
  ]);
  const [fields, setFields] = useState<Record<string, string>>({});
  const relationships = useMemo(() => (people ? sheetRelationships(model, people) : []), [model, people]);
  // By default the relationships the table shows as columns get a sheet of their own (D182), but for
  // a column that edits its relationships on the main sheet (one related record, by name, no fields).
  const [sheets, setSheets] = useState<string[]>(() =>
    relationships
      .map((item) => item.key)
      .filter((key) =>
        (start.columns?.shown ?? []).some(
          (column) =>
            column.startsWith(RELATED_FIELD_PREFIX) &&
            relationKeyOf(model, column) === key &&
            people !== undefined &&
            needsSheet(model, people, column),
        ),
      ),
  );
  // This view, as it is shown (EX1), or the types the page's collection offers (0.9 J1u).
  const ofView = viewStart !== undefined && what === "view";
  // A workbook of the page's table keeps its Advanced; every other choice is a sheet per type.
  const tableWorkbook = people !== undefined && (viewStart === undefined || (ofView && viewStart.kind === "table"));
  const forPeople = layout === "people" && (viewStart !== undefined || people !== undefined);
  // Owned relationships laid out as columns per parent, and whether cells offer lists (0.9 J6a).
  const [owned, setOwned] = useState<Record<string, OwnedChoice>>({});
  const [lists, setLists] = useState(true);
  const [cellField, setCellField] = useState("name");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: ExportField; message: string }>();

  // What is exported, by the choice: the view's own state, or whole types (no filters).
  const exportedTypes: readonly string[] = !viewStart
    ? chosen
    : what === "type"
      ? [viewStart.typeKey]
      : what === "application"
        ? (application?.objectTypeKeys ?? start.objectTypeKeys)
        : what === "workspace"
          ? model.objectTypes.map((item) => item.key)
          : [viewStart.typeKey];
  const dated = types.some((type) => exportedTypes.includes(type.key) && type.effectivePeriod);
  const filtered =
    !viewStart && start.filters && chosen.includes(start.filters.objectTypeKey) ? start.filters : undefined;
  // A "has none under" filter names a record; its criterion needs the record's type (0.16 AG4).
  const filterNames = useRelationFilterNames(
    model,
    viewStart?.typeKey ?? start.filters?.objectTypeKey ?? "",
    viewStart ? [...viewStart.filters, ...viewStart.toFilters] : (start.filters?.filters ?? []),
    start.workspaceKey ?? workspaceKey,
  );
  const awaitingNames = Boolean(
    (viewStart ? ofView : filtered) &&
    (viewStart ? [...viewStart.filters, ...viewStart.toFilters] : (filtered?.filters ?? [])).some(
      (filter) => (filter.operator === "under" || filter.operator === "notUnder") && !filterNames.has(filter.value),
    ),
  );
  // The page's scope is a criterion on its own type, as the page reads it: direct children only.
  const scoped = filtered && start.parentObjectId && belowParent ? start.parentObjectId : undefined;
  const context = start.changeSetId ? "the change set" : start.publicationId ? "the publication" : "live data";
  const cellFields =
    ofView && forPeople && viewStart?.lists ? identifyingFields(model, viewStart.lists.cellTypeKey) : [];
  const askCellField = cellFields.length > 0;

  // The file's size: what the page holds, or for a tree the records of its types, read as the page reads them.
  const treeRecords = useTreeRecords(
    ofView && viewStart?.kind === "tree" ? viewStart : undefined,
    start,
    start.workspaceKey ?? workspaceKey,
  );
  const source = start.changeSetId
    ? `change set \u201c${start.changeSetName ?? "unnamed"}\u201d`
    : start.publicationId
      ? "the publication"
      : "live data";
  const countLine = ofView
    ? viewCountLine(viewStart?.kind === "tree" ? { records: treeRecords } : start.size, source)
    : undefined;

  async function submit() {
    const base = {
      workspaceKey,
      context: { changeSetId: start.changeSetId ?? null, publicationId: start.publicationId ?? null },
    };
    let body: ExportRequest;
    if (viewStart && ofView) {
      const state = exportViewState(model, viewStart, filterNames);
      const edited =
        viewStart.kind === "table" && forPeople && columns.some((column) => column.shown)
          ? columns.filter((column) => column.shown)
          : undefined;
      body = {
        ...base,
        view: {
          applicationKey: viewStart.applicationKey,
          viewKey: viewStart.viewKey,
          state: edited ? { ...state, columns: edited.map((column) => column.key) } : state,
          ...(askCellField ? { cellField } : {}),
        },
        format: forPeople ? "xlsx" : format,
        layout,
        // A table's Advanced: the sheets and fields, its columns being the view's state.
        ...(forPeople && tableWorkbook
          ? { people: { ...peopleLayout(columns, sheets, fields, owned, lists), columns: undefined } }
          : {}),
        ...(forPeople ? {} : { include: { relations } }),
      };
    } else {
      const chosenTypes = tableWorkbook && forPeople && !viewStart ? [people] : exportedTypes;
      body = {
        ...base,
        scope: {
          types: types
            .filter((type) => chosenTypes.includes(type.key))
            .map((type) => ({
              objectTypeKey: type.key,
              where:
                filtered?.objectTypeKey === type.key
                  ? [
                      ...criteriaFromFilters(model, filtered.filters, filterNames),
                      ...(scoped ? [{ field: "parentObjectId", op: "eq", value: scoped }] : []),
                    ]
                  : [],
            })),
          parentObjectId: null,
          asOf: dated && asOf ? asOf : null,
        },
        include: { relations },
        format: forPeople ? "xlsx" : format,
        ...(forPeople ? { layout: "people" as const } : viewStart ? { layout } : {}),
        ...(forPeople && tableWorkbook && !viewStart
          ? { people: peopleLayout(columns, sheets, fields, owned, lists) }
          : {}),
      };
    }
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
  const whatOptions: readonly (readonly [What, string])[] = viewStart
    ? [
        ["view", `This view: ${viewStart.name}`],
        ["type", `The type: ${typeName(viewStart.typeKey)}`],
        ["application", `The application: ${application?.name ?? viewStart.applicationKey}`],
        ["workspace", "The whole workspace"],
      ]
    : [];
  // Technical is offered for a type, an application, a workspace and a table view (PP-D18, PP-D21).
  const kindOptions = KINDS.filter(([key]) => key === "people" || !ofView || viewStart?.kind === "table");

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
          {viewStart && (
            <FormField
              label="What"
              help={
                ofView
                  ? "The view as it is shown, with the filters and search the page has."
                  : "Every record of each type, a sheet per type."
              }
              group
            >
              {() => (
                <>
                  <Choice name="export-what" value={what} options={whatOptions} onChange={setWhat} />
                  {countLine && (
                    <p className="admin-hint" data-testid="export-count">
                      {countLine}
                    </p>
                  )}
                </>
              )}
            </FormField>
          )}
          {(viewStart || people) && (
            <FormField
              label="Kind of file"
              help={
                forPeople
                  ? ofView && viewStart?.kind !== "table"
                    ? "A workbook people work in and import back as it is, shaped as the view is."
                    : "A workbook people work in: a sheet per type, and what it needs to be imported back as it is."
                  : "The engine's exact tables, for integrations and round trips of several types."
              }
              group
            >
              {() => <Choice name="export-layout" value={layout} options={kindOptions} onChange={setLayout} />}
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
          {!viewStart && !forPeople && (
            <FormField
              label="Record types"
              help={`Read from ${context}, all at one instant.`}
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
          {viewStart && <p className="admin-hint">Read from {context}, all at one instant.</p>}
          {ofView && viewStart?.notCarried && <Notice tone="info">{viewStart.notCarried}</Notice>}
          {ofView && viewStart && viewStart.filters.length + viewStart.toFilters.length > 0 && (
            <p className="admin-hint">
              {typeName(viewStart.typeKey)} are exported with this page's{" "}
              {viewStart.filters.length + viewStart.toFilters.length === 1
                ? "filter"
                : `${viewStart.filters.length + viewStart.toFilters.length} filters`}
              .
            </p>
          )}
          {filtered && filtered.filters.length > 0 && (
            <p className="admin-hint">
              {model.objectTypes.find((type) => type.key === filtered.objectTypeKey)?.pluralName} are exported with this
              page's {filtered.filters.length === 1 ? "filter" : `${filtered.filters.length} filters`}.
            </p>
          )}
          {!viewStart && start.search && (
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
          {dated && !ofView && (
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

        {forPeople && tableWorkbook ? (
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
        ) : forPeople ? (
          askCellField ? (
            <section className="dialog-form-section" aria-labelledby="export-cell-field">
              <h3 id="export-cell-field">What each cell lists</h3>
              <FormField
                label="Each linked record is listed by its"
                help="The file records the choice, and importing it reads the cells the same way."
                error={fieldError("layout")}
              >
                {(props) => (
                  <select {...props} value={cellField} onChange={(event) => setCellField(event.target.value)}>
                    {cellFields.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
            </section>
          ) : (
            fieldError("layout") && (
              <Notice tone="error" title="The workbook cannot be made this way">
                {fieldError("layout")}
              </Notice>
            )
          )
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
              pending ||
              !workspaceKey ||
              awaitingNames ||
              (forPeople && tableWorkbook
                ? !columns.some((column) => column.shown)
                : viewStart
                  ? false
                  : forPeople
                    ? false
                    : !chosen.length)
            }
          >
            {pending ? "Starting…" : "Start export"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** A tree's records, counted over its types with the list read the page uses; undefined until read. */
function useTreeRecords(tree: ExportViewStart | undefined, start: ExportStart, workspaceKey: string) {
  const [counted, setCounted] = useState<{ key: string; total: number }>();
  const key = tree ? JSON.stringify([tree.viewKey, workspaceKey, start.changeSetId, start.publicationId]) : "";
  useEffect(() => {
    if (!tree?.typeKeys || !workspaceKey) return;
    let cancelled = false;
    void Promise.all(
      tree.typeKeys.map((typeKey) =>
        api.objects(typeKey, {
          workspaceKey,
          changeSetId: start.changeSetId,
          publicationId: start.publicationId,
          pageSize: 1,
          includeTotal: true,
        }),
      ),
    )
      .then((pages) => {
        if (!cancelled && pages.every((page) => page.totalCount !== undefined))
          setCounted({ key, total: pages.reduce((sum, page) => sum + (page.totalCount ?? 0), 0) });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return counted?.key === key ? counted.total : undefined;
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
