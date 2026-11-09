/**
 * What a relation matrix cell offers (Base 0.8 A4), limited to the view's `cellActions`: its records
 * as a table (`RelationMatrixCellTable`) whose `cellFields` and relationship values edit in place,
 * creating a record under the column (row and column fixed, the
 * container preselected when the column has only one), linking an existing one (candidates listed
 * with the reason any cannot be linked) and unlinking. Every write goes through the generic object
 * and relation APIs (A3); the lens re-reads only this cell afterwards. A failure keeps what the user
 * entered and says why; a uniqueness conflict links to the record already in the column.
 */

import { StatusPill } from "@/ui/StatusPill";
import { useState, type FormEvent, type ReactNode } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "@/api/errors";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";
import { Candidate } from "@/ui/Candidate";
import { objectTypeTile } from "@/model/hues";
import { objectTypeFor } from "@/model/lookup";
import { columnLabel, StateMark, stateLabel, type MatrixBinding } from "@/features/objects/relationMatrixStates";
import {
  RelationAttributes,
  relationAttributeTypes,
  relationValuesFromForm,
} from "@/features/objects/relations/RelationAttributes";
import { RelationMatrixCellTable } from "@/features/objects/RelationMatrixCellTable";
import type {
  ApplicationDefinition,
  AttributeTypeDefinition,
  EngineModel,
  ObjectAttributeInput,
  ObjectTypeDefinition,
  RelationMatrixCell,
  RelationMatrixCellAction,
  RelationMatrixColumn,
  RelationMatrixContainer,
  RelationMatrixLinkCandidate,
  RelationMatrixRow,
  RelationMatrixViewDefinition,
} from "@/types";

/** What a new relationship is given: the values entered, leaving out those left empty. */
const setValues = (values: Record<string, unknown>) =>
  Object.fromEntries(Object.entries(values).filter(([, value]) => value !== null));

type Mode = { kind: "view" } | { kind: "create"; prefill?: Record<string, unknown> } | { kind: "link" };

export function RelationMatrixCellDialog({
  model,
  application,
  view,
  workspaceKey,
  row,
  column,
  cell,
  actions,
  binding,
  onClose,
  onRefresh,
  onSaved,
  onOpenRecord,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  view: RelationMatrixViewDefinition;
  workspaceKey: string;
  row: RelationMatrixRow;
  column: RelationMatrixColumn;
  cell: RelationMatrixCell;
  actions: RelationMatrixCellAction[];
  binding: MatrixBinding;
  onClose: () => void;
  /** Re-reads the cell, for example after another write made this one stale. */
  onRefresh: () => Promise<void>;
  /** Re-reads the cell after a successful write and closes the dialog. */
  onSaved: () => Promise<void>;
  onOpenRecord: (id: string, objectTypeKey: string) => void;
}) {
  const { config } = view;
  const api = useDataApi();
  const cellType = objectTypeFor(model, config.cellObjectTypeKey)!;
  const rowType = objectTypeFor(model, config.rowObjectTypeKey)!;
  const can = (action: RelationMatrixCellAction) => actions.includes(action);
  // The attributes the binding gives its relationships, edited wherever the cell can be written at
  // all: the row, the relationship and the permission follow `actions` (read-only, publication).
  const relationAttributes = relationAttributeTypes(
    model,
    model.objectTypeRelations.find(
      (item) =>
        item.relationTypeKey === config.relationTypeKey &&
        item.fromObjectTypeKey ===
          (config.direction === "outgoing" ? config.rowObjectTypeKey : config.cellObjectTypeKey) &&
        item.toObjectTypeKey === (config.direction === "outgoing" ? config.cellObjectTypeKey : config.rowObjectTypeKey),
    ),
  );
  const writable = actions.length > 0;
  const history = cell.state === "historyOnly";
  const [mode, setMode] = useState<Mode>({ kind: "view" });
  const [filter, setFilter] = useState("");
  const [saving, setSaving] = useState(false);
  // The create and link forms, the table's open record field and its open relationship values each
  // keep their own flag, so none clears another's.
  const [dirty, setDirty] = useState(false);
  const [recordDirty, setRecordDirty] = useState(false);
  const [valuesDirty, setValuesDirty] = useState(false);
  const [error, setError] = useState<{ message: string; conflictingObjectId?: string; stale?: boolean }>();
  const heading = `${row.row.name} · ${columnLabel(column)}`;

  /**
   * A uniqueness refusal in the steward's terms: the row already has a counting record in this
   * column, or under the same record of the scope's type. Read outgoing, the row is the binding's
   * from end and the cell records its to end, which is what the scope limits; otherwise the API's
   * own message is kept.
   */
  function duplicateMessage(details?: { ancestorObjectId?: string; ancestorObjectTypeKey?: string }) {
    if (config.direction !== "outgoing" || !details?.ancestorObjectId) return undefined;
    const scope =
      details.ancestorObjectId === column.id
        ? `in ${columnLabel(column)}`
        : `under the same ${(objectTypeFor(model, details.ancestorObjectTypeKey ?? "")?.name ?? "record").toLowerCase()}`;
    const condition = binding.conditionText ? ` where ${binding.conditionText}` : "";
    return `${row.row.name} already has a ${cellType.name.toLowerCase()} ${scope}${condition}, and only one may count there.`;
  }

  async function run(perform: () => Promise<unknown>) {
    setSaving(true);
    setError(undefined);
    try {
      await perform();
      setDirty(false);
      await onSaved();
    } catch (cause) {
      if (isApiError(cause, "DUPLICATE_RELATION_SCOPE")) {
        const details = cause.details as
          { conflictingObjectId?: string; ancestorObjectId?: string; ancestorObjectTypeKey?: string } | undefined;
        setError({
          message: duplicateMessage(details) ?? errorMessage(cause),
          conflictingObjectId: details?.conflictingObjectId,
        });
      } else if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "RELATION_SET_VERSION_CONFLICT")) {
        setError({ message: errorMessage(cause), stale: true });
        await onRefresh();
      } else {
        setError({ message: errorMessage(cause) });
      }
    } finally {
      setSaving(false);
    }
  }

  const showing = mode.kind;
  /** Starts another action from the cell; a notice about an earlier one no longer applies. */
  const choose = (next: Mode) => {
    setMode(next);
    setError(undefined);
    setDirty(false);
  };
  const back = () => {
    setMode({ kind: "view" });
    setError(undefined);
    setDirty(false);
  };
  const typeName = cellType.name.toLowerCase();
  const canLink = can("link");
  const canCreate = can("create");
  const empty = cell.records.length === 0;
  // The dialog grows with the table's columns, up to most of the window.
  const columnCount = 1 + config.cellFields.filter((field) => field !== "name").length + relationAttributes.length;
  const width = showing === "view" && !empty ? `${Math.max(640, 330 + columnCount * 150)}px` : undefined;
  const linkButton = canLink && (
    <button type="button" className="secondary" onClick={() => choose({ kind: "link" })}>
      <Icon name="link" size={15} /> Link existing {typeName}
    </button>
  );
  const createButton = canCreate && (empty || cell.state === "inactive" || history) && (
    <button type="button" className="primary" onClick={() => choose({ kind: "create" })}>
      <Icon name="plus" size={15} /> Create {typeName}
    </button>
  );

  return (
    <Modal
      title={heading}
      eyebrow={view.name}
      busy={saving}
      dirty={dirty || recordDirty || valuesDirty}
      width={width}
      onClose={onClose}
    >
      <div className="matrix-cell-dialog">
        <div className="matrix-cell-bar">
          <p className="matrix-cell-dialog-state">
            <StateMark state={cell.state} conflict={cell.conflict} />
            <strong>{stateLabel(cell.state, cell.conflict, cell.recordCount)}</strong>
            <span className="muted">
              {cell.conflict
                ? ` · only one ${typeName} may count here${binding.conditionText ? ` (${binding.conditionText})` : ""}`
                : history && cell.publication
                  ? ` · held in publication ${cell.publication.number}, read-only`
                  : cell.state === "none"
                    ? ` · no ${typeName} yet`
                    : ""}
            </span>
          </p>
          {showing === "view" && (
            <>
              <span className="dialog-actions-spacer" />
              {!empty && (
                <label className="matrix-cell-filter">
                  <Icon name="search" size={14} />
                  <input
                    type="search"
                    aria-label={`Filter ${cellType.pluralName.toLowerCase()}`}
                    placeholder={`Filter ${cellType.pluralName.toLowerCase()}`}
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                  />
                </label>
              )}
              {!actions.length
                ? !empty && <span className="muted">Read-only here</span>
                : !empty && (
                    <>
                      {linkButton}
                      {createButton}
                    </>
                  )}
            </>
          )}
        </div>

        {showing === "view" && (
          <>
            {empty ? (
              <div className="matrix-cell-empty">
                <span className="matrix-cell-empty-ring" aria-hidden="true">
                  <Icon name="plus" size={18} />
                </span>
                <p>
                  <strong>{row.row.name}</strong> has no {typeName} in {columnLabel(column)} yet.
                </p>
                {(linkButton || createButton) && (
                  <div className="matrix-cell-empty-actions">
                    {linkButton}
                    {createButton}
                  </div>
                )}
              </div>
            ) : (
              <RelationMatrixCellTable
                model={model}
                cellType={cellType}
                applicationKey={application.key}
                records={cell.records}
                fields={config.cellFields}
                relationAttributes={relationAttributes}
                binding={binding}
                workspaceKey={workspaceKey}
                rowName={row.row.name}
                columnName={columnLabel(column)}
                filter={filter}
                history={history}
                editRecords={!history && can("edit")}
                editValues={writable && !history}
                canUnlink={!history && can("unlink")}
                canCreateFrom={history && can("create")}
                saving={saving}
                onRefresh={onRefresh}
                onOpenRecord={(record) => onOpenRecord(record.id, cellType.key)}
                onUnlink={(record) =>
                  void run(() =>
                    api.deleteRelation(
                      record.relationId,
                      record.relationVersion,
                      {},
                      { expectedRelationSetVersion: row.relationSetVersion, relationSetDirection: config.direction },
                    ),
                  )
                }
                onCreateFrom={(record) => choose({ kind: "create", prefill: { name: record.name, ...record.fields } })}
                describeError={(cause) => {
                  if (!isApiError(cause, "DUPLICATE_RELATION_SCOPE")) return undefined;
                  const details = cause.details as
                    | { conflictingObjectId?: string; ancestorObjectId?: string; ancestorObjectTypeKey?: string }
                    | undefined;
                  return {
                    message: duplicateMessage(details) ?? errorMessage(cause),
                    action: details?.conflictingObjectId && (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => onOpenRecord(details.conflictingObjectId!, cellType.key)}
                      >
                        Open the {typeName} already here
                      </button>
                    ),
                  };
                }}
                onRecordDirty={setRecordDirty}
                onValuesDirty={setValuesDirty}
              />
            )}
            {cell.recordCount > cell.records.length && (
              <p className="muted-text">
                And {cell.recordCount - cell.records.length} more.{" "}
                <button type="button" className="ghost" onClick={() => onOpenRecord(row.row.id, row.row.objectTypeKey)}>
                  Open {row.row.name}
                </button>{" "}
                to see every related {typeName}.
              </p>
            )}
            {!actions.length && <p className="muted-text">This cell is read-only here.</p>}
          </>
        )}

        {mode.kind === "create" && (
          <CreateCellRecord
            model={model}
            application={application}
            view={view}
            workspaceKey={workspaceKey}
            row={row}
            column={column}
            cellType={cellType}
            relationAttributes={writable ? relationAttributes : []}
            prefill={mode.prefill}
            saving={saving}
            onDirty={() => setDirty(true)}
            onCancel={back}
            onCreate={(payload) => void run(() => api.createObject(cellType.key, payload))}
          />
        )}

        {mode.kind === "link" && (
          <LinkCandidates
            model={model}
            view={view}
            application={application}
            workspaceKey={workspaceKey}
            row={row}
            column={column}
            cellType={cellType}
            rowType={rowType}
            binding={binding}
            relationAttributes={relationAttributes}
            saving={saving}
            onCancel={back}
            onDirty={() => setDirty(true)}
            onLink={(candidate, values) =>
              void run(() =>
                api.createRelation({
                  relationTypeKey: config.relationTypeKey,
                  fromObjectId: config.direction === "outgoing" ? row.row.id : candidate.id,
                  toObjectId: config.direction === "outgoing" ? candidate.id : row.row.id,
                  attributes: values,
                  expectedRelationSetVersion: row.relationSetVersion,
                  relationSetDirection: config.direction,
                }),
              )
            }
          />
        )}

        {error && (
          <Notice
            tone={error.stale ? "warning" : "error"}
            title={error.stale ? "Changed elsewhere" : "Not saved"}
            focusOnMount
          >
            <p>{error.message}</p>
            {error.stale && <p>This cell now shows the current state. Your input is kept; review it and try again.</p>}
            {error.conflictingObjectId && (
              <button
                type="button"
                className="secondary"
                onClick={() => onOpenRecord(error.conflictingObjectId!, cellType.key)}
              >
                Open the {typeName} already here
              </button>
            )}
          </Notice>
        )}

        {showing === "view" && (
          <div className="matrix-cell-footer">
            {!actions.length || history ? null : (
              <span className="matrix-cell-hint">
                Each change saves on its own · <kbd>Enter</kbd> saves, <kbd>Esc</kbd> cancels
              </span>
            )}
            <span className="dialog-actions-spacer" />
            <button type="button" className="secondary" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}

interface CellValues {
  name?: string;
  attributes: ObjectAttributeInput[];
  /** The relationship's values, when the form asked for them (a create). */
  relation: Record<string, unknown>;
}

/** The view's `cellFields` as a form; `name` is the record's name, anything else an attribute. */
function CellRecordForm({
  model,
  cellType,
  fields,
  values,
  submitLabel,
  saving,
  ready = true,
  children,
  extra,
  cancelLabel = "Cancel",
  relationAttributes = [],
  onDirty,
  onCancel,
  onSubmit,
}: {
  model: EngineModel;
  cellType: ObjectTypeDefinition;
  fields: string[];
  /** The relationship's attributes asked for beside the record's, a create's (0.13 RV). */
  relationAttributes?: AttributeTypeDefinition[];
  values: Record<string, unknown>;
  submitLabel: string;
  saving: boolean;
  /** False while what the submit needs is still loading: the submit button waits. */
  ready?: boolean;
  /** Fields placed before the cell fields. */
  children?: ReactNode;
  /** Further actions beside Cancel. */
  extra?: ReactNode;
  cancelLabel?: string;
  onDirty: () => void;
  onCancel: () => void;
  onSubmit: (values: CellValues) => void;
}) {
  const attributes = fields.flatMap((field) => {
    const definition = model.attributeTypes.find((item) => item.key === field);
    const binding = cellType.attributes.find((item) => item.attributeTypeKey === field);
    return definition && binding ? [{ definition, binding }] : [];
  });
  const focusFirstField = !children && !fields.includes("name");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const raw = new FormData(form).get("name");
    const name = raw === null ? undefined : String(raw);
    onSubmit({
      name,
      attributes: attributes
        .filter(({ binding }) => !binding.readOnly)
        .map(({ definition }) => ({
          attributeTypeKey: definition.key,
          value: attributeValueFromForm(form, definition),
        })),
      relation: relationValuesFromForm(form, relationAttributes),
    });
  }
  return (
    <form className="matrix-cell-form dialog-form" onSubmit={submit} onChange={onDirty}>
      {children}
      {fields.includes("name") && (
        <label>
          Name
          <input name="name" required defaultValue={String(values.name ?? "")} autoFocus={!children} />
        </label>
      )}
      {attributes.map(({ definition, binding }, index) => (
        <AttributeField
          key={definition.key}
          attribute={definition}
          binding={binding}
          value={values[definition.key]}
          autoFocus={focusFirstField && index === 0}
        />
      ))}
      <RelationAttributes attributes={relationAttributes} mode="edit" />
      <div className="dialog-actions">
        {extra}
        <span className="dialog-actions-spacer" />
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>
          {cancelLabel}
        </button>
        <button className="primary" disabled={saving || !ready}>
          {saving ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

function CreateCellRecord({
  model,
  application,
  view,
  workspaceKey,
  row,
  column,
  cellType,
  relationAttributes,
  prefill,
  saving,
  onDirty,
  onCancel,
  onCreate,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  view: RelationMatrixViewDefinition;
  workspaceKey: string;
  row: RelationMatrixRow;
  column: RelationMatrixColumn;
  cellType: ObjectTypeDefinition;
  relationAttributes: AttributeTypeDefinition[];
  prefill?: Record<string, unknown>;
  saving: boolean;
  onDirty: () => void;
  onCancel: () => void;
  onCreate: (payload: Parameters<ReturnType<typeof useDataApi>["createObject"]>[1]) => void;
}) {
  const { config } = view;
  const api = useDataApi();
  const [containerId, setContainerId] = useState<string>();
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search.trim());
  const [defaults, setDefaults] = useState<{ id: string | null; container?: RelationMatrixContainer }>();
  const pageSize = 20;
  const containers = useCursorWindow<RelationMatrixContainer>(
    (selector) =>
      api
        .relationMatrixContainers({
          workspaceKey,
          applicationKey: application.key,
          viewKey: view.key,
          columnId: column.id,
          search: debounced || undefined,
          ...selector,
          pageSize,
        })
        .then((page) => {
          if (!defaults) {
            const container = page.items.find((item) => item.id === page.defaultContainerId);
            setDefaults({ id: page.defaultContainerId, container });
            if (page.defaultContainerId) setContainerId((current) => current ?? page.defaultContainerId!);
          }
          return page;
        }),
    [workspaceKey, application.key, view.key, column.id, debounced],
  );
  const [missingContainer, setMissingContainer] = useState(false);
  // A record belongs to one application; the lens's own is used when it holds the cell type.
  const owner = application.objectTypeKeys.includes(cellType.key)
    ? application.key
    : (model.applications.find((item) => item.objectTypeKeys.includes(cellType.key))?.key ?? application.key);
  const pathOf = (container: RelationMatrixContainer) =>
    [column.name, ...container.path.map((part) => part.name)].join(" / ");
  const single = defaults?.id && defaults.container;

  return (
    <CellRecordForm
      model={model}
      cellType={cellType}
      fields={config.cellFields}
      values={prefill ?? {}}
      relationAttributes={relationAttributes}
      submitLabel={`Create ${cellType.name.toLowerCase()}`}
      saving={saving}
      // A submit before the containers answer would have no container; once they do, a single one
      // is shown without the list that says one is missing, and the submit was lost (0.9 R).
      ready={defaults !== undefined}
      onDirty={onDirty}
      onCancel={onCancel}
      cancelLabel="Back"
      onSubmit={(values) => {
        if (!containerId) {
          setMissingContainer(true);
          return;
        }
        const name = values.name ?? "";
        onCreate({
          applicationKey: owner,
          workspaceKey,
          name,
          parentObjectId: containerId,
          attributes: values.attributes.filter(({ attributeTypeKey, value }) => {
            const binding = cellType.attributes.find((item) => item.attributeTypeKey === attributeTypeKey);
            return value !== null || binding?.required;
          }),
          initialRelations: [
            {
              relationTypeKey: config.relationTypeKey,
              // The row is the binding's from end when the view reads outgoing, so the new record
              // sees it as incoming.
              direction: config.direction === "outgoing" ? "incoming" : "outgoing",
              otherObjectId: row.row.id,
              attributes: setValues(values.relation),
            },
          ],
        });
      }}
    >
      <p className="matrix-create-for">
        For <strong>{row.row.name}</strong> under <strong>{columnLabel(column)}</strong>
      </p>
      {!config.cellFields.includes("name") && (
        <label>
          Name
          <input
            name="name"
            required
            autoFocus
            defaultValue={String(prefill?.name ?? `${row.row.name} ${columnLabel(column)}`)}
          />
        </label>
      )}
      {single ? (
        <div className="form-fact">
          <span>Goes in</span>
          <strong>{pathOf(defaults.container!)}</strong>
        </div>
      ) : (
        <fieldset className="candidate-list matrix-containers" aria-busy={containers.loading || undefined}>
          <legend>Goes in</legend>
          <label className="search-box candidate-search">
            <Icon name="search" />
            <input
              aria-label="Search places"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search places…"
            />
          </label>
          <ScrollWindow
            list={containers}
            label="Places to create it in"
            noun={["place", "places"]}
            pageSize={pageSize}
            rowNavigation={false}
            footer={false}
            className="candidate-scroll"
          >
            {(drawn) => (
              <>
                <WindowSpacer as="div" edge="before" height={drawn.before} />
                {drawn.rows.map(({ index, item: container, size }) =>
                  container === undefined ? (
                    <WindowPlaceholder
                      key={`placeholder-${index}`}
                      as="div"
                      index={index}
                      size={size}
                      className="candidate"
                    />
                  ) : (
                    <Candidate
                      key={container.id}
                      data-row-key={container.id}
                      ref={drawn.measure}
                      data-row-index={index}
                      selected={containerId === container.id}
                      control={
                        <input
                          type="radio"
                          name="matrix-container"
                          value={container.id}
                          checked={containerId === container.id}
                          onChange={() => {
                            setContainerId(container.id);
                            setMissingContainer(false);
                          }}
                        />
                      }
                      type={objectTypeTile(model, container.objectTypeKey)}
                      name={container.name}
                      detail={pathOf(container)}
                    />
                  ),
                )}
                <WindowSpacer as="div" edge="after" height={drawn.after} />
                {containers.loading && !containers.items.length && <p className="candidate-state">Loading…</p>}
                {!containers.loading && !containers.error && !containers.items.length && (
                  <p className="candidate-state">
                    {debounced
                      ? `No places match “${debounced}”.`
                      : `Nothing under ${column.name} can hold a ${cellType.name.toLowerCase()}.`}
                  </p>
                )}
              </>
            )}
          </ScrollWindow>
          {containers.error && <InlineError message={containers.error} onRetry={containers.retry} />}
          {missingContainer && <p className="field-error">Choose where the {cellType.name.toLowerCase()} goes.</p>}
        </fieldset>
      )}
    </CellRecordForm>
  );
}

/** Where a candidate sits below the column record, then its other values, without repeating its name. */
function candidateDetails(candidate: RelationMatrixLinkCandidate) {
  const ancestors = candidate.path.filter((part) => part.id !== candidate.id).map((part) => part.name);
  const values = Object.values(candidate.fields)
    .filter((value) => value !== null && value !== undefined && value !== "" && typeof value !== "boolean")
    .map(String)
    .filter((value) => value !== candidate.name);
  return [...new Set([ancestors.join(" / "), ...values].filter(Boolean))].join(" · ");
}

const REASONS: Record<NonNullable<RelationMatrixLinkCandidate["reason"]>, (context: ReasonContext) => string> = {
  alreadyLinked: () => "Already linked",
  rowCardinality: ({ rowName }) => `${rowName} cannot take another`,
  candidateCardinality: ({ rowTypePlural }) => `Already linked to as many ${rowTypePlural} as allowed`,
  scopeTaken: ({ rowName, conditionText }) =>
    `${rowName} already has one here${conditionText ? ` where ${conditionText}` : ""}`,
};

interface ReasonContext {
  rowName: string;
  rowTypePlural: string;
  conditionText: string;
}

function LinkCandidates({
  model,
  view,
  application,
  workspaceKey,
  row,
  column,
  cellType,
  rowType,
  binding,
  relationAttributes,
  saving,
  onCancel,
  onDirty,
  onLink,
}: {
  model: EngineModel;
  view: RelationMatrixViewDefinition;
  application: ApplicationDefinition;
  workspaceKey: string;
  row: RelationMatrixRow;
  column: RelationMatrixColumn;
  cellType: ObjectTypeDefinition;
  rowType: ObjectTypeDefinition;
  binding: MatrixBinding;
  /** The relationship's attributes, asked for with the link (0.13 RV). */
  relationAttributes: AttributeTypeDefinition[];
  saving: boolean;
  onCancel: () => void;
  onDirty: () => void;
  onLink: (candidate: RelationMatrixLinkCandidate, values: Record<string, unknown>) => void;
}) {
  const api = useDataApi();
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search.trim());
  const [selectedId, setSelectedId] = useState<string>();
  const pageSize = 20;
  const candidates = useCursorWindow<RelationMatrixLinkCandidate>(
    (selector) =>
      api.relationMatrixLinkCandidates({
        workspaceKey,
        applicationKey: application.key,
        viewKey: view.key,
        columnId: column.id,
        rowId: row.row.id,
        search: debounced || undefined,
        ...selector,
        pageSize,
      }),
    [workspaceKey, application.key, view.key, column.id, row.row.id, debounced],
  );
  const selected = candidates.items.find((item) => item.id === selectedId);
  const plural = cellType.pluralName.toLowerCase();
  const context: ReasonContext = {
    rowName: row.row.name,
    rowTypePlural: rowType.pluralName.toLowerCase(),
    conditionText: binding.conditionText,
  };
  return (
    <form
      className="mapping-dialog"
      onChange={onDirty}
      onSubmit={(event) => {
        event.preventDefault();
        if (selected?.eligible)
          onLink(selected, setValues(relationValuesFromForm(event.currentTarget, relationAttributes)));
      }}
    >
      <label className="search-box candidate-search">
        <Icon name="search" />
        <input
          aria-label={`Search ${plural}`}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={`Search ${plural} under ${column.name}…`}
          autoFocus
        />
      </label>
      <fieldset className="candidate-list" aria-busy={candidates.loading || undefined}>
        <legend className="visually-hidden">Choose a {cellType.name.toLowerCase()} to link</legend>
        <ScrollWindow
          list={candidates}
          label={`${cellType.pluralName} to link`}
          noun={[cellType.name.toLowerCase(), plural]}
          pageSize={pageSize}
          rowNavigation={false}
          footer={false}
          className="candidate-scroll"
        >
          {(drawn) => (
            <>
              <WindowSpacer as="div" edge="before" height={drawn.before} />
              {drawn.rows.map(({ index, item: candidate, size }) =>
                candidate === undefined ? (
                  <WindowPlaceholder
                    key={`placeholder-${index}`}
                    as="div"
                    index={index}
                    size={size}
                    className="candidate"
                  />
                ) : (
                  <Candidate
                    key={candidate.id}
                    data-row-key={candidate.id}
                    ref={drawn.measure}
                    data-row-index={index}
                    selected={selectedId === candidate.id}
                    disabled={!candidate.eligible}
                    control={
                      <input
                        type="radio"
                        name="matrix-link"
                        value={candidate.id}
                        checked={selectedId === candidate.id}
                        disabled={!candidate.eligible}
                        onChange={() => setSelectedId(candidate.id)}
                      />
                    }
                    type={objectTypeTile(model, candidate.objectTypeKey)}
                    name={candidate.name}
                    detail={candidateDetails(candidate)}
                  >
                    {!candidate.eligible && candidate.reason && (
                      <StatusPill tone="neutral" marker={false}>
                        {REASONS[candidate.reason](context)}
                      </StatusPill>
                    )}
                  </Candidate>
                ),
              )}
              <WindowSpacer as="div" edge="after" height={drawn.after} />
              {candidates.loading && !candidates.items.length && <p className="candidate-state">Loading…</p>}
              {!candidates.loading && !candidates.error && !candidates.items.length && (
                <p className="candidate-state">
                  No {plural} under {column.name}
                  {debounced ? ` match “${debounced}”` : ""}.
                </p>
              )}
            </>
          )}
        </ScrollWindow>
        {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
      </fieldset>
      <RelationAttributes attributes={relationAttributes} mode="edit" />
      <div className="dialog-actions">
        <span className="dialog-actions-spacer" />
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>
          Back
        </button>
        <button className="primary" disabled={saving || !selected?.eligible}>
          {saving ? "Linking…" : "Link"}
        </button>
      </div>
    </form>
  );
}
