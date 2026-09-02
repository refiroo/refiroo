import { useEffect, useState } from "react";
import { api } from "./api";
import { objectTypeFor } from "./model";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { ObjectTable, Pagination } from "./ObjectTable";
import type { ApplicationDefinition, EngineModel, ObjectItem, ObjectPage, ViewDefinition } from "./types";

export interface ViewComponentProps {
  model: EngineModel;
  application: ApplicationDefinition;
  view: ViewDefinition;
  onOpen: (item: ObjectItem) => void;
  onChanged: () => void;
}

type ViewComponent = (props: ViewComponentProps) => React.ReactNode;

export const viewComponentRegistry: Record<ViewDefinition["type"], ViewComponent> = {
  table: ObjectCollectionView,
  tree: ObjectCollectionView,
  mappingGrid: ObjectCollectionView,
  form: ObjectCollectionView,
  dashboard: ObjectCollectionView,
};

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  return <>{Component(props)}</>;
}

function ObjectCollectionView({ model, application, view, onOpen, onChanged }: ViewComponentProps) {
  const objectType = view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [cursors, setCursors] = useState<Array<string | undefined>>([undefined]);
  const [pageIndex, setPageIndex] = useState(0);
  const [page, setPage] = useState<ObjectPage>({ items: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setCursors([undefined]);
    setPageIndex(0);
  }, [application.key, view.key, search]);

  useEffect(() => {
    if (!objectType) return;
    let active = true;
    setLoading(true);
    api.objects(objectType.key, {
      applicationKey: application.key,
      search,
      cursor: cursors[pageIndex],
      pageSize: 20,
    }).then((loaded) => {
      if (active) { setPage(loaded); setError(""); }
    }).catch((cause) => active && setError(String(cause))).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [application.key, objectType?.key, pageIndex, cursors, search]);

  if (!objectType) {
    return <div className="empty-state">This configured view does not select an object type.</div>;
  }
  const activeObjectType = objectType;
  const columns = view.config.columns ?? ["name", ...objectType.attributes.slice(0, 4).map((item) => item.attributeTypeKey)];

  function nextPage() {
    if (!page.nextCursor) return;
    setCursors((current) => [...current.slice(0, pageIndex + 1), page.nextCursor!]);
    setPageIndex((current) => current + 1);
  }

  function refresh() {
    api.objects(activeObjectType.key, {
      applicationKey: application.key,
      search,
      cursor: cursors[pageIndex],
      pageSize: 20,
    }).then(setPage).catch((cause) => setError(String(cause)));
    onChanged();
  }

  return (
    <>
      <header className="page-header collection-header">
        <div>
          <div className="context-line"><span>{application.name}</span><span>/</span><span>{view.name}</span></div>
          <h1>{view.name}</h1>
          <p>{objectType.description ?? application.description}</p>
        </div>
        <button className="primary" onClick={() => setShowCreate(true)}>+ New {objectType.name}</button>
      </header>
      <section className="surface collection-surface">
        <div className="collection-toolbar">
          <label className="search-box">
            <span>⌕</span>
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={`Search ${objectType.pluralName.toLowerCase()}`} />
          </label>
          <div className="view-kind"><span>{view.type}</span><strong>{page.items.length}</strong> on this page</div>
        </div>
        {error && <div className="notice">{error}</div>}
        <ObjectTable model={model} columns={columns} objects={page.items} loading={loading} onOpen={onOpen} />
        <Pagination page={pageIndex + 1} hasNext={Boolean(page.nextCursor)} onPrevious={() => setPageIndex((current) => Math.max(0, current - 1))} onNext={nextPage} />
      </section>
      {showCreate && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          objectType={objectType}
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); refresh(); }}
        />
      )}
    </>
  );
}
