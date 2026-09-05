/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { objectTypeFor } from "@/model/lookup";
import { InlineError } from "@/ui/InlineError";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { DeleteImpactSummary } from "@/features/objects/DeleteImpactSummary";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { ObjectTable } from "@/ui/ObjectTable";
import { Pagination } from "@/ui/Pagination";
import { Icon } from "@/ui/Icon";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { useCursorPages } from "@/lib/hooks/useCursorPages";
import type { DeleteImpact, ObjectItem } from "@/types";
import type { ViewComponentProps } from "./views/types";

export function ObjectCollectionView({
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
  const pages = useCursorPages<ObjectItem>(
    objectType
      ? (cursor) =>
          api.objects(objectType.key, {
            applicationKey: application.key,
            workspaceKey,
            search: query.search,
            state: query.states,
            sort: query.sort,
            cursor,
            pageSize: query.pageSize,
          })
      : null,
    [application.key, view.key, workspaceKey, query.search, query.states, query.sort, query.pageSize],
  );
  const { loading, error } = pages;
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ObjectItem>();
  const [deleting, setDeleting] = useState<ObjectItem>();
  const [deleteImpact, setDeleteImpact] = useState<DeleteImpact>();
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  if (!objectType) return <div className="empty-state">This configured view does not select an object type.</div>;
  const activeObjectType = objectType;
  const columns = view.config.columns ?? [
    "name",
    ...objectType.attributes.slice(0, 4).map((item) => item.attributeTypeKey),
  ];

  function refresh() {
    pages.retry();
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
          <h1>{view.name}</h1>
          <p>{objectType.description ?? application.description}</p>
        </div>
        {objectType.features.rootCreatable === true && (
          <button className="primary" onClick={() => setShowCreate(true)}>
            <Icon name="plus" /> New {objectType.name}
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
                <strong>{pages.items.length}</strong> on this page
              </>
            )}
          </span>
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        <ObjectTable
          model={model}
          columns={columns}
          objects={error ? [] : pages.items}
          loading={loading && !error}
          onOpen={onOpen}
          onEdit={setEditing}
          onDelete={setDeleting}
          label={`${view.name} table`}
        />
        {!error && (
          <Pagination page={pages.pageNumber} hasNext={pages.hasNext} onPrevious={pages.previous} onNext={pages.next} />
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
