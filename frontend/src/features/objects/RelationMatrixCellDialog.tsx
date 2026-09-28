/**
 * What a relation matrix cell offers (Base 0.8 A4), limited to the view's `cellActions`: its records,
 * editing their `cellFields`, creating a record under the column (row and column fixed, the
 * container preselected when the column has only one), linking an existing one (candidates listed
 * with the reason any cannot be linked) and unlinking. Every write goes through the generic object
 * and relation APIs (A3); the lens re-reads only this cell afterwards. A failure keeps what the user
 * entered and says why; a uniqueness conflict links to the record already in the column.
 */

import { useState, type FormEvent, type ReactNode } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "@/api/errors";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { formatValue } from "@/ui/formatValue";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { columnLabel, StateMark, stateLabel, type MatrixBinding } from "@/features/objects/relationMatrixStates";
import type {
  ApplicationDefinition,
  EngineModel,
  ObjectAttributeInput,
  ObjectTypeDefinition,
  RelationMatrixCell,
  RelationMatrixCellAction,
  RelationMatrixCellRecord,
  RelationMatrixColumn,
  RelationMatrixContainer,
  RelationMatrixLinkCandidate,
  RelationMatrixRow,
  RelationMatrixViewDefinition,
} from "@/types";

type Mode =
  | { kind: "view" }
  | { kind: "edit"; recordId: string }
  | { kind: "create"; prefill?: Record<string, unknown> }
  | { kind: "link" }
  | { kind: "unlink"; recordId: string };

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
  const history = cell.state === "historyOnly";
  const single = (cell.state === "one" || cell.state === "inactive") && cell.records.length === 1;
  const [mode, setMode] = useState<Mode>(() =>
    single && can("edit") ? { kind: "edit", recordId: cell.records[0].id } : { kind: "view" },
  );
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
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
      if (isApiError(cause, "duplicate_relation_scope")) {
        const details = cause.details as
          { conflictingObjectId?: string; ancestorObjectId?: string; ancestorObjectTypeKey?: string } | undefined;
        setError({
          message: duplicateMessage(details) ?? errorMessage(cause),
          conflictingObjectId: details?.conflictingObjectId,
        });
      } else if (isApiError(cause, "version_conflict") || isApiError(cause, "relation_set_version_conflict")) {
        setError({ message: errorMessage(cause), stale: true });
        await onRefresh();
      } else {
        setError({ message: errorMessage(cause) });
      }
    } finally {
      setSaving(false);
    }
  }

  const editing = mode.kind === "edit" ? cell.records.find((record) => record.id === mode.recordId) : undefined;
  const unlinking = mode.kind === "unlink" ? cell.records.find((record) => record.id === mode.recordId) : undefined;
  const back = () => {
    setMode({ kind: "view" });
    setError(undefined);
    setDirty(false);
  };

  return (
    <Modal title={heading} eyebrow={view.name} busy={saving} dirty={dirty} onClose={onClose}>
      <div className="matrix-cell-dialog">
        <p className="matrix-cell-dialog-state">
          <StateMark state={cell.state} conflict={cell.conflict} />
          <strong>{stateLabel(cell.state, cell.conflict, cell.recordCount)}</strong>
          <span className="muted">
            {cell.conflict
              ? ` · only one ${cellType.name.toLowerCase()} may count here${binding.conditionText ? ` (${binding.conditionText})` : ""}`
              : history && cell.publication
                ? ` · held in publication ${cell.publication.number}, read-only`
                : cell.state === "none"
                  ? ` · no ${cellType.name.toLowerCase()} yet`
                  : ""}
          </span>
        </p>

        {mode.kind === "view" && (
          <>
            {cell.records.length > 0 && (
              <ul className="matrix-cell-records" aria-label={`${cellType.pluralName} in this cell`}>
                {cell.records.map((record) => (
                  <li key={record.id}>
                    <RecordSummary model={model} record={record} fields={config.cellFields} binding={binding} />
                    <div className="matrix-cell-record-actions">
                      {!history && (
                        <button type="button" className="ghost" onClick={() => onOpenRecord(record.id, cellType.key)}>
                          Open<span className="visually-hidden"> {record.name}</span>
                        </button>
                      )}
                      {!history && can("edit") && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setMode({ kind: "edit", recordId: record.id })}
                        >
                          Edit<span className="visually-hidden"> {record.name}</span>
                        </button>
                      )}
                      {!history && can("unlink") && (
                        <button
                          type="button"
                          className="danger-ghost"
                          onClick={() => setMode({ kind: "unlink", recordId: record.id })}
                        >
                          Unlink<span className="visually-hidden"> {record.name}</span>
                        </button>
                      )}
                      {history && can("create") && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setMode({ kind: "create", prefill: { name: record.name, ...record.fields } })}
                        >
                          Create from this
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {cell.recordCount > cell.records.length && (
              <p className="muted-text">
                And {cell.recordCount - cell.records.length} more.{" "}
                <button type="button" className="ghost" onClick={() => onOpenRecord(row.row.id, row.row.objectTypeKey)}>
                  Open {row.row.name}
                </button>{" "}
                to see every related {cellType.name.toLowerCase()}.
              </p>
            )}
            {!actions.length && <p className="muted-text">This cell is read-only here.</p>}
            <div className="dialog-actions">
              {can("create") && (cell.state === "none" || cell.state === "inactive" || history) && (
                <button type="button" className="primary" onClick={() => setMode({ kind: "create" })}>
                  <Icon name="plus" size={15} /> Create {cellType.name.toLowerCase()}
                </button>
              )}
              {can("link") && (
                <button type="button" className="secondary" onClick={() => setMode({ kind: "link" })}>
                  Link existing {cellType.name.toLowerCase()}
                </button>
              )}
              <span className="dialog-actions-spacer" />
              <button type="button" className="secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        )}

        {editing && (
          <CellRecordForm
            key={editing.id}
            model={model}
            cellType={cellType}
            fields={config.cellFields}
            values={{ name: editing.name, ...editing.fields }}
            submitLabel="Save"
            saving={saving}
            onDirty={() => setDirty(true)}
            onCancel={single ? onClose : back}
            cancelLabel={single ? "Cancel" : "Back"}
            extra={
              <>
                {can("unlink") && single && (
                  <button
                    type="button"
                    className="danger-ghost"
                    disabled={saving}
                    onClick={() => setMode({ kind: "unlink", recordId: editing.id })}
                  >
                    Unlink
                  </button>
                )}
                <button type="button" className="ghost" onClick={() => onOpenRecord(editing.id, cellType.key)}>
                  Open {editing.name}
                </button>
              </>
            }
            onSubmit={(values) => {
              const attributes = values.attributes.filter(
                ({ attributeTypeKey, value }) =>
                  JSON.stringify(value ?? null) !== JSON.stringify(editing.fields[attributeTypeKey] ?? null),
              );
              const name = values.name !== undefined && values.name !== editing.name ? values.name : undefined;
              if (!attributes.length && name === undefined) {
                onClose();
                return;
              }
              void run(() =>
                api.updateObject(cellType.key, editing.id, {
                  expectedVersion: editing.version,
                  ...(name !== undefined ? { name } : {}),
                  ...(attributes.length ? { attributes } : {}),
                }),
              );
            }}
          />
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
            prefill={mode.prefill}
            saving={saving}
            onDirty={() => setDirty(true)}
            onCancel={back}
            onCreate={(payload) => void run(() => api.createObject(cellType.key, payload))}
          />
        )}

        {mode.kind === "link" && (
          <LinkCandidates
            view={view}
            application={application}
            workspaceKey={workspaceKey}
            row={row}
            column={column}
            cellType={cellType}
            rowType={rowType}
            binding={binding}
            saving={saving}
            onCancel={back}
            onLink={(candidate) =>
              void run(() =>
                api.createRelation({
                  relationTypeKey: config.relationTypeKey,
                  fromObjectId: config.direction === "outgoing" ? row.row.id : candidate.id,
                  toObjectId: config.direction === "outgoing" ? candidate.id : row.row.id,
                  attributes: {},
                  expectedRelationSetVersion: row.relationSetVersion,
                  relationSetDirection: config.direction,
                }),
              )
            }
          />
        )}

        {unlinking && (
          <div className="matrix-unlink">
            <p>
              Unlink <strong>{unlinking.name}</strong> from <strong>{row.row.name}</strong>? The{" "}
              {cellType.name.toLowerCase()} itself is kept.
            </p>
            <div className="dialog-actions">
              <span className="dialog-actions-spacer" />
              <button type="button" className="secondary" disabled={saving} onClick={back}>
                Cancel
              </button>
              <button
                type="button"
                className="danger"
                autoFocus
                disabled={saving}
                onClick={() =>
                  void run(() =>
                    api.deleteRelation(
                      unlinking.relationId,
                      unlinking.relationVersion,
                      {},
                      { expectedRelationSetVersion: row.relationSetVersion, relationSetDirection: config.direction },
                    ),
                  )
                }
              >
                {saving ? "Unlinking…" : "Unlink"}
              </button>
            </div>
          </div>
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
                Open the {cellType.name.toLowerCase()} already here
              </button>
            )}
          </Notice>
        )}
      </div>
    </Modal>
  );
}

function RecordSummary({
  model,
  record,
  fields,
  binding,
}: {
  model: EngineModel;
  record: RelationMatrixCellRecord;
  fields: string[];
  binding: MatrixBinding;
}) {
  return (
    <div className="matrix-record-summary">
      <span className="matrix-record-name">
        {record.name}
        {binding.conditional && !record.meetsCondition && <span className="pill"> Does not count</span>}
      </span>
      <dl>
        {fields
          .filter((field) => field !== "name")
          .map((field) => (
            <div key={field}>
              <dt>{attributeName(model, field)}</dt>
              <dd>{formatValue(record.fields[field])}</dd>
            </div>
          ))}
      </dl>
    </div>
  );
}

interface CellValues {
  name?: string;
  attributes: ObjectAttributeInput[];
}

/** The view's `cellFields` as a form; `name` is the record's name, anything else an attribute. */
function CellRecordForm({
  model,
  cellType,
  fields,
  values,
  submitLabel,
  saving,
  children,
  extra,
  cancelLabel = "Cancel",
  onDirty,
  onCancel,
  onSubmit,
}: {
  model: EngineModel;
  cellType: ObjectTypeDefinition;
  fields: string[];
  values: Record<string, unknown>;
  submitLabel: string;
  saving: boolean;
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
      <div className="dialog-actions">
        {extra}
        <span className="dialog-actions-spacer" />
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>
          {cancelLabel}
        </button>
        <button className="primary" disabled={saving}>
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
      submitLabel={`Create ${cellType.name.toLowerCase()}`}
      saving={saving}
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
              attributes: {},
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
            {containers.items.map((container, position) => (
              <label
                key={container.id}
                data-row-key={container.id}
                data-row-index={containers.startIndex + position}
                className={containerId === container.id ? "candidate selected" : "candidate"}
              >
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
                <span className="candidate-text">
                  <span className="candidate-name">{container.name}</span>
                  <small>{pathOf(container)}</small>
                </span>
              </label>
            ))}
            {containers.loading && !containers.items.length && <p className="candidate-state">Loading…</p>}
            {!containers.loading && !containers.error && !containers.items.length && (
              <p className="candidate-state">
                {debounced
                  ? `No places match “${debounced}”.`
                  : `Nothing under ${column.name} can hold a ${cellType.name.toLowerCase()}.`}
              </p>
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
  view,
  application,
  workspaceKey,
  row,
  column,
  cellType,
  rowType,
  binding,
  saving,
  onCancel,
  onLink,
}: {
  view: RelationMatrixViewDefinition;
  application: ApplicationDefinition;
  workspaceKey: string;
  row: RelationMatrixRow;
  column: RelationMatrixColumn;
  cellType: ObjectTypeDefinition;
  rowType: ObjectTypeDefinition;
  binding: MatrixBinding;
  saving: boolean;
  onCancel: () => void;
  onLink: (candidate: RelationMatrixLinkCandidate) => void;
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
      onSubmit={(event) => {
        event.preventDefault();
        if (selected?.eligible) onLink(selected);
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
          {candidates.items.map((candidate, position) => (
            <label
              key={candidate.id}
              data-row-key={candidate.id}
              data-row-index={candidates.startIndex + position}
              className={`candidate${selectedId === candidate.id ? " selected" : ""}${candidate.eligible ? "" : " is-disabled"}`}
            >
              <input
                type="radio"
                name="matrix-link"
                value={candidate.id}
                checked={selectedId === candidate.id}
                disabled={!candidate.eligible}
                onChange={() => setSelectedId(candidate.id)}
              />
              <span className="candidate-text">
                <span className="candidate-name">{candidate.name}</span>
                <small>{candidateDetails(candidate)}</small>
              </span>
              {!candidate.eligible && candidate.reason && (
                <span className="pill">{REASONS[candidate.reason](context)}</span>
              )}
            </label>
          ))}
          {candidates.loading && !candidates.items.length && <p className="candidate-state">Loading…</p>}
          {!candidates.loading && !candidates.error && !candidates.items.length && (
            <p className="candidate-state">
              No {plural} under {column.name}
              {debounced ? ` match “${debounced}”` : ""}.
            </p>
          )}
        </ScrollWindow>
        {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
      </fieldset>
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
