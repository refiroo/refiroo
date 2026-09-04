import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { fallbackDetail, fieldValue, objectTypeFor } from "../utils/model";
import { AttributesPanel as EditableAttributesPanel } from "./AttributesPanel";
import { ConfirmDialog } from "./ConfirmDialog";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { ObjectTable, Pagination } from "./ObjectTable";
import { RelationsPanel as EditableRelationsPanel } from "./RelationsPanel";
import type {
  ApplicationDefinition,
  ChildrenPanelDefinition,
  DeleteImpact,
  EngineModel,
  HierarchyPanelDefinition,
  ObjectItem,
  ObjectPage,
  PanelDefinition,
  TablePanelDefinition,
} from "../types";

interface PanelProps {
  model: EngineModel;
  application: ApplicationDefinition;
  object: ObjectItem;
  panel: PanelDefinition;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged: () => void;
  onObjectChanged: (object: ObjectItem) => void;
  onReload: () => Promise<void>;
}

type PanelComponent = (props: PanelProps) => React.ReactNode;

export const panelComponentRegistry: Record<PanelDefinition["type"], PanelComponent> = {
  attributes: (props) => <EditableAttributesPanel model={props.model} object={props.object} panel={props.panel as import("../types").AttributesPanelDefinition} onObjectChanged={props.onObjectChanged} onReload={props.onReload} />,
  children: ChildrenPanel,
  relations: (props) => <EditableRelationsPanel model={props.model} object={props.object} panel={props.panel as import("../types").RelationsPanelDefinition} onOpen={props.onOpen} />,
  table: TablePanel,
  hierarchy: HierarchyPanel,
};

export function ObjectDetail({
  model,
  application,
  objectTypeKey,
  objectId,
  onOpen,
  onBack,
  onDeleted,
  onChanged,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  objectTypeKey: string;
  objectId: string;
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
  const objectType = objectTypeFor(model, objectTypeKey);
  const detail = application.details.find((item) => item.objectTypeKey === objectTypeKey) ?? (objectType ? fallbackDetail(objectType) : undefined);

  async function loadObject() {
    const loaded = await api.object(objectTypeKey, objectId);
    if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
    setObject(loaded); setError("");
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    api.object(objectTypeKey, objectId).then((loaded) => {
      if (!active) return;
      if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
      setObject(loaded);
      setError("");
    }).catch((cause) => active && setError(String(cause))).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [application.key, objectId, objectTypeKey]);

  if (loading) return <div className="page-loading">Loading object…</div>;
  if (error || !object || !objectType || !detail) return <div className="empty-state error-state"><h1>Object unavailable</h1><p>{error}</p><button className="secondary" onClick={onBack}>Back to list</button></div>;
  const currentObject = object;
  const currentObjectType = objectType;

  const panels = detail.panels.filter((panel) => panel.visible);
  const mainPanels = panels.filter((panel) => panel.region === "main").sort((a, b) => a.order - b.order);
  const sidePanels = panels.filter((panel) => panel.region === "side").sort((a, b) => a.order - b.order);
  const title = fieldValue(object, detail.header.titleField, model);
  const subtitle = detail.header.subtitleField ? fieldValue(object, detail.header.subtitleField, model) : undefined;

  async function deleteObject() {
    setDeletePending(true); setDeleteError("");
    try { await api.deleteObject(currentObjectType.key, currentObject.id, currentObject.version, Boolean(deleteImpact)); onChanged(); onDeleted(); }
    catch (cause) {
      if (cause instanceof ApiError && cause.code === "object_has_dependents" && cause.details) {
        setDeleteImpact(cause.details as DeleteImpact);
        setDeleteError("");
      } else {
        setDeleteError(cause instanceof Error ? cause.message : String(cause));
      }
      if ((cause as { code?: string }).code === "version_conflict") {
        try { await loadObject(); } catch (reloadCause) { setDeleteError(reloadCause instanceof Error ? reloadCause.message : String(reloadCause)); }
        setDeleteImpact(undefined);
      }
      setDeletePending(false);
    }
  }

  function renderPanel(panel: PanelDefinition) {
    const Component = panelComponentRegistry[panel.type];
    return <section className="panel surface" key={panel.key}><h2>{panel.title}</h2>{Component({ model, application, object: currentObject, panel, onOpen, onChanged, onObjectChanged: (saved) => { setObject(saved); onChanged(); }, onReload: loadObject })}</section>;
  }

  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        {detail.breadcrumbs.showApplication && <button onClick={onBack}>{application.name}</button>}
        {detail.breadcrumbs.showAncestors && object.path.slice(0, -1).map((part) => (
          <span key={part.id}>/<button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button></span>
        ))}
        {detail.breadcrumbs.showObjectType && <span>/<span>{objectType.name}</span></span>}
      </nav>
      <header className="page-header detail-header">
        <div className="object-icon" style={{ background: application.color }}>{iconLetters(objectType.icon ?? objectType.name)}</div>
        <div className="detail-title">
          {detail.header.showObjectType && <p className="eyebrow">{objectType.name}</p>}
          <h1>{String(title ?? object.name)}</h1>
          {subtitle !== undefined && subtitle !== null && subtitle !== "" && <p>{String(subtitle)}</p>}
        </div>
        <div className="detail-actions">
          <span className="version">v{object.version}</span>
          <button className="primary" onClick={() => setEditing(true)}>Edit</button>
          <button className="danger-outline" onClick={() => setDeleting(true)}>Delete object</button>
        </div>
      </header>
      <div className={`detail-grid ${sidePanels.length ? "with-side" : ""}`}>
        <div className="panel-column">{mainPanels.map(renderPanel)}</div>
        {sidePanels.length > 0 && <aside className="panel-column side-panels">{sidePanels.map(renderPanel)}</aside>}
      </div>
      {editing && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          objectType={objectType}
          object={object}
          onClose={() => setEditing(false)}
          onSaved={(saved) => { setObject(saved); setEditing(false); onChanged(); }}
        />
      )}
      {deleting && <ConfirmDialog title={deleteImpact ? `Cascade delete ${deleteImpact.objectCount} objects?` : `Delete “${object.name}”?`} confirmLabel={deleteImpact ? "Cascade delete" : "Delete object"} pending={deletePending} error={deleteError} onCancel={() => { setDeleting(false); setDeleteError(""); setDeleteImpact(undefined); }} onConfirm={deleteObject}>{deleteImpact ? <DeleteImpactSummary model={model} impact={deleteImpact} /> : <p>The engine will first check for children and relationships. If dependencies exist, nothing will be deleted until you review and confirm the cascade.</p>}</ConfirmDialog>}
    </>
  );
}

function DeleteImpactSummary({ model, impact }: { model: EngineModel; impact: DeleteImpact }) {
  const objectName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  const relationName = (key: string) => model.relationTypes.find((item) => item.key === key)?.name ?? key;
  return <div className="delete-impact">
    <p><strong>Nothing has been deleted yet.</strong> Confirming will permanently delete the selected object and the following dependencies.</p>
    {impact.objectsToDelete.length > 0 && <section><h3>Objects to delete</h3><ul>{impact.objectsToDelete.map((item) => <li key={item.id}><strong>{item.name}</strong> <span>({objectName(item.objectTypeKey)})</span><small>{item.reason === "child" ? "Child object" : `FK dependent through ${relationName(item.relationTypeKey ?? "")}`}</small></li>)}</ul></section>}
    {impact.relationshipsToRemove.length > 0 && <section><h3>Relationships to remove</h3><ul>{impact.relationshipsToRemove.map((item) => <li key={item.id}><strong>{item.fromObject.name}</strong> <span>— {relationName(item.relationTypeKey)} → {item.toObject.name}</span><small>{item.fkPk ? (item.relatedObjectWillBeDeleted ? "PK/FK relationship; dependent object will be deleted" : "PK/FK relationship") : item.relatedObjectWillBeDeleted ? "Both endpoints are already in the deletion set" : "The object at the other endpoint is preserved"}</small></li>)}</ul></section>}
    <p className="cascade-total">Total: {impact.objectCount} objects and {impact.relationshipCount} relationships will be deleted.</p>
  </div>;
}

function ChildrenPanel(props: PanelProps) {
  const panel = props.panel as ChildrenPanelDefinition;
  return <div className="panel-tables">{panel.config.objectTypeKeys.map((key) => (
    <CollectionPanelTable key={key} {...props} objectTypeKey={key} columns={panel.config.columns} pageSize={panel.config.pageSize} parentObjectId={props.object.id} allowCreate />
  ))}</div>;
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
  const objectType = objectTypeFor(model, objectTypeKey)!;
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [cursors, setCursors] = useState<Array<string | undefined>>([undefined]);
  const [pageIndex, setPageIndex] = useState(0);
  const [page, setPage] = useState<ObjectPage>({ items: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);
  useEffect(() => { setCursors([undefined]); setPageIndex(0); }, [search, objectTypeKey, parentObjectId]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.objects(objectTypeKey, { applicationKey: application.key, search, cursor: cursors[pageIndex], pageSize, parentObjectId })
      .then((loaded) => active && setPage(loaded)).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [application.key, cursors, objectTypeKey, pageIndex, pageSize, parentObjectId, search]);

  function nextPage() {
    if (!page.nextCursor) return;
    setCursors((current) => [...current.slice(0, pageIndex + 1), page.nextCursor!]);
    setPageIndex((current) => current + 1);
  }
  function refresh() {
    api.objects(objectTypeKey, { applicationKey: application.key, search, cursor: cursors[pageIndex], pageSize, parentObjectId }).then(setPage);
    onChanged();
  }

  return (
    <div className="embedded-table">
      <div className="embedded-toolbar">
        <label className="search-box compact"><span>⌕</span><input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={`Search ${objectType.pluralName.toLowerCase()}`} /></label>
        {allowCreate && <button className="secondary" onClick={() => setCreating(true)}>+ Add {objectType.name}</button>}
      </div>
      <ObjectTable model={model} columns={columns} objects={page.items} loading={loading} onOpen={(item) => onOpen(item.objectTypeKey, item.id, item.applicationKey)} />
      <Pagination page={pageIndex + 1} hasNext={Boolean(page.nextCursor)} onPrevious={() => setPageIndex((value) => Math.max(0, value - 1))} onNext={nextPage} />
      {creating && <ObjectFormDialog model={model} applicationKey={application.key} objectType={objectType} parentObjectId={parentObjectId} parentObjectTypeKey={parentObjectId ? object.objectTypeKey : undefined} onClose={() => setCreating(false)} onSaved={() => { setCreating(false); refresh(); }} />}
    </div>
  );
}

function HierarchyPanel({ model, object, panel, onOpen }: PanelProps) {
  const definition = panel as HierarchyPanelDefinition;
  const visiblePath = definition.config.showAncestors ? object.path : object.path.slice(-1);
  const parent = object.path.at(-2);
  return (
    <div className="hierarchy-panel">
      {definition.config.showParent && <div><span>Parent</span>{parent ? <button onClick={() => onOpen(parent.objectTypeKey, parent.id)}>{parent.name}</button> : <strong>Root object</strong>}</div>}
      <ol>{visiblePath.map((part, index) => <li key={part.id}><button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button><small>{objectTypeFor(model, part.objectTypeKey)?.name}</small>{index < visiblePath.length - 1 && <span>›</span>}</li>)}</ol>
    </div>
  );
}

function iconLetters(icon: string) {
  return icon.split(/[-\s]/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}
