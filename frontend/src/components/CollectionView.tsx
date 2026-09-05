import { useEffect, useState } from "react";
import { api } from "../api/client";
import { errorMessage, isApiError } from "../api/errors";
import { objectTypeFor } from "../utils/model";
import { InlineError } from "./AsyncState";
import { ConfirmDialog } from "./ConfirmDialog";
import { DeleteImpactSummary } from "./ObjectDetail";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { ObjectTable, Pagination } from "./ObjectTable";
import { ObjectToolbar } from "./ObjectToolbar";
import type {
  ApplicationDefinition,
  CollectionQueryState,
  DeleteImpact,
  EngineModel,
  ObjectItem,
  ObjectPage,
  ViewDefinition,
} from "../types";

export interface ViewComponentProps {
  model: EngineModel;
  application: ApplicationDefinition;
  view: ViewDefinition;
  workspaceKey: string;
  query: CollectionQueryState;
  onQueryChange: (query: CollectionQueryState) => void;
  onOpen: (item: ObjectItem) => void;
  onChanged: () => void;
}

/**
 * View type key to the component that renders it.
 *
 * Every declared view type currently resolves to the same collection renderer, so a model
 * declaring `tree` or `mappingGrid` is shown a flat table under that label. Base 0.6 decision D3
 * governs how declared-but-unimplemented view types are represented; this registry is the single
 * seam where that decision is expressed. See Phase 6 of docs/FRONTEND_STRUCTURE_REFACTOR.md.
 */
export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
  tree: ObjectCollectionView,
  mappingGrid: ObjectCollectionView,
  form: ObjectCollectionView,
  dashboard: ObjectCollectionView,
};

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  return <Component {...props} />;
}

function ObjectCollectionView({
  model,
  application,
  view,
  workspaceKey,
  query,
  onQueryChange,
  onOpen,
  onChanged,
}: ViewComponentProps) {
  const objectType = view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
  const queryKey = JSON.stringify([
    application.key,
    view.key,
    workspaceKey,
    query.search,
    query.states,
    query.sort,
    query.pageSize,
  ]);
  const [paging, setPaging] = useState<{ key: string; cursors: Array<string | undefined>; index: number }>({
    key: queryKey,
    cursors: [undefined],
    index: 0,
  });
  const activePaging = paging.key === queryKey ? paging : { key: queryKey, cursors: [undefined], index: 0 };
  const activeCursor = activePaging.cursors[activePaging.index];
  const [page, setPage] = useState<ObjectPage>({ items: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryToken, setRetryToken] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ObjectItem>();
  const [deleting, setDeleting] = useState<ObjectItem>();
  const [deleteImpact, setDeleteImpact] = useState<DeleteImpact>();
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => setPaging({ key: queryKey, cursors: [undefined], index: 0 }), [queryKey]);

  useEffect(() => {
    if (!objectType) return;
    let active = true;
    setLoading(true);
    setError("");
    api
      .objects(objectType.key, {
        applicationKey: application.key,
        workspaceKey,
        search: query.search,
        state: query.states,
        sort: query.sort,
        cursor: activeCursor,
        pageSize: query.pageSize,
      })
      .then((loaded) => {
        if (active) {
          setPage(loaded);
          setError("");
        }
      })
      .catch((cause) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [application.key, objectType?.key, queryKey, activePaging.index, activeCursor, retryToken]);

  if (!objectType) return <div className="empty-state">This configured view does not select an object type.</div>;
  const activeObjectType = objectType;
  const columns = view.config.columns ?? [
    "name",
    ...objectType.attributes.slice(0, 4).map((item) => item.attributeTypeKey),
  ];

  function nextPage() {
    if (!page.nextCursor) return;
    setPaging({
      key: queryKey,
      cursors: [...activePaging.cursors.slice(0, activePaging.index + 1), page.nextCursor],
      index: activePaging.index + 1,
    });
  }

  function refresh() {
    setRetryToken((value) => value + 1);
    onChanged();
  }

  async function deleteObject() {
    if (!deleting) return;
    setDeletePending(true);
    setDeleteError("");
    try {
      await api.deleteObject(activeObjectType.key, deleting.id, deleting.version, Boolean(deleteImpact));
      setDeleting(undefined);
      setDeleteImpact(undefined);
      refresh();
    } catch (cause) {
      if (isApiError(cause, "object_has_dependents") && cause.details) {
        setDeleteImpact(cause.details as DeleteImpact);
      } else if (isApiError(cause, "version_conflict")) {
        try {
          setDeleting(await api.object(activeObjectType.key, deleting.id));
          setDeleteImpact(undefined);
          setDeleteError("The object changed. Its latest version has been loaded; review and try again.");
        } catch (reloadCause) {
          setDeleteError(errorMessage(reloadCause));
        }
      } else setDeleteError(errorMessage(cause));
    } finally {
      setDeletePending(false);
    }
  }

  return (
    <>
      <header className="page-header collection-header">
        <div>
          <div className="context-line">
            <span>{application.name}</span>
            <span>/</span>
            <span>{view.name}</span>
            <span>/</span>
            <span>{workspaceKey}</span>
          </div>
          <h1>{view.name}</h1>
          <p>{objectType.description ?? application.description}</p>
        </div>
        {objectType.features.rootCreatable === true && (
          <button className="primary" onClick={() => setShowCreate(true)}>
            + New {objectType.name}
          </button>
        )}
      </header>
      <section className="surface collection-surface">
        <ObjectToolbar
          query={query}
          onChange={onQueryChange}
          placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
        />
        <div className="collection-meta">
          <span className="view-kind">
            <span>{view.type}</span>
            {!error && (
              <>
                <strong>{page.items.length}</strong> on this page
              </>
            )}
          </span>
        </div>
        {error && <InlineError message={error} onRetry={() => setRetryToken((value) => value + 1)} />}
        <ObjectTable
          model={model}
          columns={columns}
          objects={error ? [] : page.items}
          loading={loading && !error}
          onOpen={onOpen}
          onEdit={setEditing}
          onDelete={setDeleting}
        />
        {!error && (
          <Pagination
            page={activePaging.index + 1}
            hasNext={Boolean(page.nextCursor)}
            onPrevious={() => setPaging({ ...activePaging, index: Math.max(0, activePaging.index - 1) })}
            onNext={nextPage}
          />
        )}
      </section>
      {showCreate && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            refresh();
          }}
        />
      )}
      {editing && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          object={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            refresh();
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={deleteImpact ? `Cascade delete ${deleteImpact.objectCount} objects?` : `Delete “${deleting.name}”?`}
          confirmLabel={deleteImpact ? "Cascade delete" : "Delete object"}
          pending={deletePending}
          error={deleteError}
          onCancel={() => {
            setDeleting(undefined);
            setDeleteImpact(undefined);
            setDeleteError("");
          }}
          onConfirm={deleteObject}
        >
          {deleteImpact ? (
            <DeleteImpactSummary model={model} impact={deleteImpact} />
          ) : (
            <p>The engine will check dependencies before deleting. A cascade always requires separate confirmation.</p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}
