import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useCursorPages } from "../lib/hooks/useCursorPages";
import { useDebouncedValue } from "../lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "../api/errors";
import { fallbackDetail, fieldValue, objectTypeFor } from "../utils/model";
import { AttributesPanel as EditableAttributesPanel } from "./AttributesPanel";
import { ConfirmDialog } from "./ConfirmDialog";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { ObjectTable, Pagination } from "./ObjectTable";
import { RelationsPanel as EditableRelationsPanel } from "./RelationsPanel";
import { HistoryPanel } from "./HistoryPanel";
import { InlineError } from "./AsyncState";
import type {
  ApplicationDefinition,
  AttributesPanelDefinition,
  ChildrenPanelDefinition,
  DeleteImpact,
  EngineModel,
  HierarchyPanelDefinition,
  ObjectItem,
  PanelDefinition,
  RelationsPanelDefinition,
  TablePanelDefinition,
} from "../types";

interface PanelProps<P extends PanelDefinition = PanelDefinition> {
  model: EngineModel;
  application: ApplicationDefinition;
  object: ObjectItem;
  panel: P;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged: () => void;
  onObjectChanged: (object: ObjectItem) => void;
  onReload: () => Promise<void>;
}

/**
 * Panel type key to the component that renders it. `PanelDefinition` is a discriminated union on
 * `type`, so keying the registry by that discriminant hands every entry its own narrowed panel
 * definition and removes the per-entry cast this registry used to carry.
 */
type PanelComponentRegistry = {
  [K in PanelDefinition["type"]]: React.ComponentType<PanelProps<Extract<PanelDefinition, { type: K }>>>;
};

function AttributesPanelSection(props: PanelProps<AttributesPanelDefinition>) {
  return (
    <EditableAttributesPanel
      model={props.model}
      object={props.object}
      panel={props.panel}
      onObjectChanged={props.onObjectChanged}
      onReload={props.onReload}
      onChanged={props.onChanged}
    />
  );
}

function RelationsPanelSection(props: PanelProps<RelationsPanelDefinition>) {
  return (
    <EditableRelationsPanel
      model={props.model}
      object={props.object}
      panel={props.panel}
      onOpen={props.onOpen}
      onChanged={props.onChanged}
    />
  );
}

export const panelComponentRegistry: PanelComponentRegistry = {
  attributes: AttributesPanelSection,
  children: ChildrenPanel,
  relations: RelationsPanelSection,
  table: TablePanel,
  hierarchy: HierarchyPanel,
};

export function ObjectDetail({
  model,
  application,
  objectTypeKey,
  objectId,
  workspaceKey,
  onOpen,
  onBack,
  onDeleted,
  onChanged,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  objectTypeKey: string;
  objectId: string;
  workspaceKey: string;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onBack: () => void;
  onDeleted: () => void;
  onChanged: () => void;
}) {
  const [object, setObject] = useState<ObjectItem>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleteImpact, setDeleteImpact] = useState<DeleteImpact>();
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const objectType = objectTypeFor(model, objectTypeKey);
  const detail =
    application.details.find((item) => item.objectTypeKey === objectTypeKey) ??
    (objectType ? fallbackDetail(objectType) : undefined);

  /**
   * Loads the object and rejects when it does not belong to the application and workspace the
   * route names. Panels call this through `onReload` and rely on it rejecting, so the rejection is
   * deliberately not converted into component state here.
   */
  async function loadObject() {
    const loaded = await api.object(objectTypeKey, objectId);
    if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
    if (loaded.workspaceKey !== workspaceKey)
      throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
    setObject(loaded);
    setError("");
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .object(objectTypeKey, objectId)
      .then((loaded) => {
        if (!active) return;
        if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
        if (loaded.workspaceKey !== workspaceKey)
          throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
        setObject(loaded);
        setError("");
      })
      .catch((cause) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // The effect repeats loadObject rather than calling it, because it must ignore a response that
    // arrives after the route moved on and loadObject has no cancellation of its own.
  }, [application.key, objectId, objectTypeKey, workspaceKey]);

  if (loading) return <div className="page-loading">Loading object…</div>;
  if (error || !object || !objectType || !detail)
    return (
      <div className="empty-state error-state">
        <h1>Object unavailable</h1>
        <p>{error}</p>
        <div className="empty-actions">
          <button
            className="secondary"
            onClick={() => {
              setLoading(true);
              loadObject()
                .catch((cause) => setError(errorMessage(cause)))
                .finally(() => setLoading(false));
            }}
          >
            Retry
          </button>
          <button className="secondary" onClick={onBack}>
            Back to list
          </button>
        </div>
      </div>
    );
  const currentObject = object;
  const currentObjectType = objectType;

  function handleChanged() {
    setHistoryRefresh((value) => value + 1);
    onChanged();
  }

  const panels = detail.panels.filter((panel) => panel.visible);
  const mainPanels = panels.filter((panel) => panel.region === "main").sort((a, b) => a.order - b.order);
  const sidePanels = panels.filter((panel) => panel.region === "side").sort((a, b) => a.order - b.order);
  const title = fieldValue(object, detail.header.titleField, model);
  const subtitle = detail.header.subtitleField ? fieldValue(object, detail.header.subtitleField, model) : undefined;

  async function deleteObject() {
    setDeletePending(true);
    setDeleteError("");
    try {
      await api.deleteObject(currentObjectType.key, currentObject.id, currentObject.version, Boolean(deleteImpact));
      onChanged();
      onDeleted();
    } catch (cause) {
      if (isApiError(cause, "object_has_dependents") && cause.details) {
        setDeleteImpact(cause.details as DeleteImpact);
        setDeleteError("");
      } else {
        setDeleteError(errorMessage(cause));
      }
      if (isApiError(cause, "version_conflict")) {
        try {
          await loadObject();
        } catch (reloadCause) {
          setDeleteError(errorMessage(reloadCause));
        }
        setDeleteImpact(undefined);
      }
      setDeletePending(false);
    }
  }

  function renderPanel(panel: PanelDefinition) {
    // The registry is keyed by the union discriminant, so each entry is narrower than the union
    // being dispatched. TypeScript cannot correlate the two across an index access, which is why
    // this one widening assertion stands in for the per-entry casts the registry used to carry.
    const Component = panelComponentRegistry[panel.type] as React.ComponentType<PanelProps>;
    return (
      <section className="panel surface" key={panel.key}>
        <h2>{panel.title}</h2>
        <Component
          model={model}
          application={application}
          object={currentObject}
          panel={panel}
          onOpen={onOpen}
          onChanged={handleChanged}
          onObjectChanged={(saved) => {
            setObject(saved);
            handleChanged();
          }}
          onReload={loadObject}
        />
      </section>
    );
  }

  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        {detail.breadcrumbs.showApplication && <button onClick={onBack}>{application.name}</button>}
        {detail.breadcrumbs.showAncestors &&
          object.path.slice(0, -1).map((part) => (
            <span key={part.id}>
              /<button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button>
            </span>
          ))}
        {detail.breadcrumbs.showObjectType && (
          <span>
            /<span>{objectType.name}</span>
          </span>
        )}
      </nav>
      <header className="page-header detail-header">
        <div className="object-icon" style={{ background: application.color }}>
          {iconLetters(objectType.icon ?? objectType.name)}
        </div>
        <div className="detail-title">
          {detail.header.showObjectType && <p className="eyebrow">{objectType.name}</p>}
          <h1>{String(title ?? object.name)}</h1>
          {subtitle !== undefined && subtitle !== null && subtitle !== "" && <p>{String(subtitle)}</p>}
        </div>
        <div className="detail-actions">
          <span className="version">v{object.version}</span>
          <button className="primary" onClick={() => setEditing(true)}>
            Edit
          </button>
          <button className="danger-outline" onClick={() => setDeleting(true)}>
            Delete object
          </button>
        </div>
      </header>
      <div className={`detail-grid ${sidePanels.length ? "with-side" : ""}`}>
        <div className="panel-column">
          {mainPanels.map(renderPanel)}
          <HistoryPanel objectTypeKey={objectTypeKey} objectId={objectId} refreshToken={historyRefresh} />
        </div>
        {sidePanels.length > 0 && <aside className="panel-column side-panels">{sidePanels.map(renderPanel)}</aside>}
      </div>
      {editing && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          object={object}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setObject(saved);
            setEditing(false);
            handleChanged();
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={deleteImpact ? `Cascade delete ${deleteImpact.objectCount} objects?` : `Delete “${object.name}”?`}
          confirmLabel={deleteImpact ? "Cascade delete" : "Delete object"}
          pending={deletePending}
          error={deleteError}
          onCancel={() => {
            setDeleting(false);
            setDeleteError("");
            setDeleteImpact(undefined);
          }}
          onConfirm={deleteObject}
        >
          {deleteImpact ? (
            <DeleteImpactSummary model={model} impact={deleteImpact} />
          ) : (
            <p>
              The engine will first check for children and relationships. If dependencies exist, nothing will be deleted
              until you review and confirm the cascade.
            </p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}

export function DeleteImpactSummary({ model, impact }: { model: EngineModel; impact: DeleteImpact }) {
  const objectName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  const relationName = (key: string) => model.relationTypes.find((item) => item.key === key)?.name ?? key;
  return (
    <div className="delete-impact">
      <p>
        <strong>Nothing has been deleted yet.</strong> Confirming will permanently delete the selected object and the
        following dependencies.
      </p>
      {impact.objectsToDelete.length > 0 && (
        <section>
          <h3>Objects to delete</h3>
          <ul>
            {impact.objectsToDelete.map((item) => (
              <li key={item.id}>
                <strong>{item.name}</strong> <span>({objectName(item.objectTypeKey)})</span>
                <small>
                  {item.reason === "child"
                    ? "Child object"
                    : `FK dependent through ${relationName(item.relationTypeKey ?? "")}`}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      {impact.relationshipsToRemove.length > 0 && (
        <section>
          <h3>Relationships to remove</h3>
          <ul>
            {impact.relationshipsToRemove.map((item) => (
              <li key={item.id}>
                <strong>{item.fromObject.name}</strong>{" "}
                <span>
                  — {relationName(item.relationTypeKey)} → {item.toObject.name}
                </span>
                <small>
                  {item.fkPk
                    ? item.relatedObjectWillBeDeleted
                      ? "PK/FK relationship; dependent object will be deleted"
                      : "PK/FK relationship"
                    : item.relatedObjectWillBeDeleted
                      ? "Both endpoints are already in the deletion set"
                      : "The object at the other endpoint is preserved"}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="cascade-total">
        Total: {impact.objectCount} objects and {impact.relationshipCount} relationships will be deleted.
      </p>
    </div>
  );
}

function ChildrenPanel(props: PanelProps) {
  const panel = props.panel as ChildrenPanelDefinition;
  return (
    <div className="panel-tables">
      {panel.config.objectTypeKeys.map((key) => (
        <CollectionPanelTable
          key={key}
          {...props}
          objectTypeKey={key}
          columns={panel.config.columns}
          pageSize={panel.config.pageSize}
          parentObjectId={props.object.id}
          allowCreate
        />
      ))}
    </div>
  );
}

function TablePanel(props: PanelProps) {
  const panel = props.panel as TablePanelDefinition;
  return (
    <CollectionPanelTable
      {...props}
      objectTypeKey={panel.config.objectTypeKey}
      columns={panel.config.columns}
      pageSize={panel.config.pageSize}
      parentObjectId={panel.config.filterByParent ? props.object.id : undefined}
      allowCreate={panel.config.filterByParent}
    />
  );
}

function CollectionPanelTable({
  model,
  application,
  object,
  objectTypeKey,
  columns,
  pageSize,
  parentObjectId,
  allowCreate,
  onOpen,
  onChanged,
}: PanelProps & {
  objectTypeKey: string;
  columns: string[];
  pageSize: number;
  parentObjectId?: string;
  allowCreate: boolean;
}) {
  const objectType = objectTypeFor(model, objectTypeKey);
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [creating, setCreating] = useState(false);
  const pages = useCursorPages<ObjectItem>(
    objectType
      ? (cursor) =>
          api.objects(objectTypeKey, {
            applicationKey: application.key,
            workspaceKey: object.workspaceKey,
            search,
            cursor,
            pageSize,
            parentObjectId,
          })
      : null,
    [application.key, object.workspaceKey, objectTypeKey, pageSize, parentObjectId, search],
  );
  const { loading, error } = pages;

  function refresh() {
    pages.retry();
    onChanged();
  }

  // A release can retire an object type that a configured panel still names. Reporting that is
  // better than the non-null assertion this used to carry, which crashed the whole detail screen.
  if (!objectType)
    return (
      <div className="panel-state">This panel refers to object type “{objectTypeKey}”, which is not in the model.</div>
    );

  return (
    <div className="embedded-table">
      <div className="embedded-toolbar">
        <label className="search-box compact">
          <span>⌕</span>
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
          />
        </label>
        {allowCreate && (
          <button className="secondary" onClick={() => setCreating(true)}>
            + Add {objectType.name}
          </button>
        )}
      </div>
      {error && <InlineError message={error} onRetry={pages.retry} />}
      <ObjectTable
        model={model}
        columns={columns}
        objects={error ? [] : pages.items}
        loading={loading && !error}
        onOpen={(item) => onOpen(item.objectTypeKey, item.id, item.applicationKey)}
      />
      {!error && (
        <Pagination page={pages.pageNumber} hasNext={pages.hasNext} onPrevious={pages.previous} onNext={pages.next} />
      )}
      {creating && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={object.workspaceKey}
          objectType={objectType}
          parentObjectId={parentObjectId}
          parentObjectTypeKey={parentObjectId ? object.objectTypeKey : undefined}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function HierarchyPanel({ model, object, panel, onOpen }: PanelProps) {
  const definition = panel as HierarchyPanelDefinition;
  const visiblePath = definition.config.showAncestors ? object.path : object.path.slice(-1);
  const parent = object.path.at(-2);
  return (
    <div className="hierarchy-panel">
      {definition.config.showParent && (
        <div>
          <span>Parent</span>
          {parent ? (
            <button onClick={() => onOpen(parent.objectTypeKey, parent.id)}>{parent.name}</button>
          ) : (
            <strong>Root object</strong>
          )}
        </div>
      )}
      <ol>
        {visiblePath.map((part, index) => (
          <li key={part.id}>
            <button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button>
            <small>{objectTypeFor(model, part.objectTypeKey)?.name}</small>
            {index < visiblePath.length - 1 && <span>›</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function iconLetters(icon: string) {
  return icon
    .split(/[-\s]/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
