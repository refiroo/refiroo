import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { attributeName, fallbackDetail, fieldValue, objectTypeFor } from "./model";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { formatValue, ObjectTable, Pagination } from "./ObjectTable";
import type {
  ApplicationDefinition,
  AttributesPanelDefinition,
  ChildrenPanelDefinition,
  EngineModel,
  HierarchyPanelDefinition,
  ObjectItem,
  ObjectPage,
  PanelDefinition,
  RelationItem,
  RelationsPanelDefinition,
  TablePanelDefinition,
} from "./types";

interface PanelProps {
  model: EngineModel;
  application: ApplicationDefinition;
  object: ObjectItem;
  panel: PanelDefinition;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged: () => void;
}

type PanelComponent = (props: PanelProps) => React.ReactNode;

export const panelComponentRegistry: Record<PanelDefinition["type"], PanelComponent> = {
  attributes: AttributesPanel,
  children: ChildrenPanel,
  relations: RelationsPanel,
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
  onChanged,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  objectTypeKey: string;
  objectId: string;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onBack: () => void;
  onChanged: () => void;
}) {
  const [object, setObject] = useState<ObjectItem>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const objectType = objectTypeFor(model, objectTypeKey);
  const detail = application.details.find((item) => item.objectTypeKey === objectTypeKey) ?? (objectType ? fallbackDetail(objectType) : undefined);

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

  const panels = detail.panels.filter((panel) => panel.visible);
  const mainPanels = panels.filter((panel) => panel.region === "main").sort((a, b) => a.order - b.order);
  const sidePanels = panels.filter((panel) => panel.region === "side").sort((a, b) => a.order - b.order);
  const title = fieldValue(object, detail.header.titleField, model);
  const subtitle = detail.header.subtitleField ? fieldValue(object, detail.header.subtitleField, model) : undefined;

  function renderPanel(panel: PanelDefinition) {
    const Component = panelComponentRegistry[panel.type];
    return <section className="panel surface" key={panel.key}><h2>{panel.title}</h2>{Component({ model, application, object: currentObject, panel, onOpen, onChanged })}</section>;
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
    </>
  );
}

function AttributesPanel({ model, object, panel }: PanelProps) {
  const definition = panel as AttributesPanelDefinition;
  return (
    <dl className="attribute-grid">
      {definition.config.fields.map((field) => (
        <div key={field}><dt>{attributeName(model, field)}</dt><dd>{formatValue(fieldValue(object, field, model))}</dd></div>
      ))}
    </dl>
  );
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
      {creating && <ObjectFormDialog model={model} applicationKey={application.key} objectType={objectType} parentObjectId={parentObjectId} onClose={() => setCreating(false)} onSaved={() => { setCreating(false); refresh(); }} />}
    </div>
  );
}

function RelationsPanel({ model, object, panel, onOpen }: PanelProps) {
  const definition = panel as RelationsPanelDefinition;
  const [relations, setRelations] = useState<RelationItem[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api.relations(object.id).then((items) => active && setRelations(items)).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [object.id]);
  const visible = useMemo(() => relations.filter((item) =>
    definition.config.relationTypeKeys.includes(item.relation.relationTypeKey)
    && (definition.config.direction === "both" || definition.config.direction === item.direction)
  ), [definition.config.direction, definition.config.relationTypeKeys, relations]);
  return <ObjectTable model={model} columns={definition.config.columns} objects={visible.map((item) => item.object)} loading={loading} onOpen={(item) => onOpen(item.objectTypeKey, item.id, item.applicationKey)} />;
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
