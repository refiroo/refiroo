/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { objectTypeFor } from "@/model/lookup";
import { InlineError } from "@/ui/InlineError";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { RetirementImpactSummary } from "@/features/objects/RetirementImpactSummary";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { ObjectTable } from "@/ui/ObjectTable";
import { Pagination } from "@/ui/Pagination";
import { Icon } from "@/ui/Icon";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { useCursorPages } from "@/lib/hooks/useCursorPages";
import type { ObjectItem, RetirementImpact } from "@/types";
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
  readOnly = false,
}: ViewComponentProps) {
  const objectType = view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
  const pages = useCursorPages<ObjectItem>(
    objectType
      ? (cursor) =>
          api.objects(objectType.key, {
            applicationKey: application.key,
            workspaceKey,
            search: query.search,
            lifecycle: "active",
            sort: query.sort,
            filters: query.filters,
            cursor,
            pageSize: query.pageSize,
          })
      : null,
    [application.key, view.key, workspaceKey, query.search, query.sort, query.pageSize, query.filters],
  );
  const { loading, error } = pages;
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ObjectItem>();
  const [retiring, setRetiring] = useState<ObjectItem>();
  const [retirementImpact, setRetirementImpact] = useState<RetirementImpact>();
  const [retirementPending, setRetirementPending] = useState(false);
  const [retirementError, setRetirementError] = useState("");

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

  async function retireObject() {
    if (!retiring) return;
    setRetirementPending(true);
    setRetirementError("");
    try {
      await api.retireObject(activeObjectType.key, retiring.id, retiring.activeRevisionId!, Boolean(retirementImpact));
      setRetiring(undefined);
      setRetirementImpact(undefined);
      refresh();
    } catch (cause) {
      if (isApiError(cause, "object_has_dependants") && cause.details) {
        setRetirementImpact(cause.details as RetirementImpact);
      } else if (isApiError(cause, "active_revision_conflict")) {
        try {
          setRetiring(await api.object(activeObjectType.key, retiring.id));
          setRetirementImpact(undefined);
          setRetirementError("The object changed. Its latest version has been loaded; review and try again.");
        } catch (reloadCause) {
          setRetirementError(errorMessage(reloadCause));
        }
      } else setRetirementError(errorMessage(cause));
    } finally {
      setRetirementPending(false);
    }
  }

  return (
    <>
      <header className="page-header collection-header">
        <div>
          <h1>{view.name}</h1>
          <p>{objectType.description ?? application.description}</p>
        </div>
        {!readOnly && objectType.features.rootCreatable === true && (
          <button className="primary" onClick={() => setShowCreate(true)}>
            <Icon name="plus" /> New {objectType.name}
          </button>
        )}
      </header>
      <section className="surface collection-surface">
        <ObjectToolbar
          model={model}
          view={view}
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
          {query.filters.length > 0 && (
            <span aria-label="Applied filters">
              {query.filters.map((filter) => `${filter.field} ${filter.operator} ${filter.value}`).join(" · ")}
            </span>
          )}
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        <ObjectTable
          model={model}
          columns={columns}
          objects={error ? [] : pages.items}
          loading={loading && !error}
          onOpen={onOpen}
          onEdit={readOnly ? undefined : setEditing}
          onDelete={readOnly ? undefined : setRetiring}
          label={`${view.name} table`}
          emptyMessage={
            query.search || query.filters.length > 0
              ? "No results match these filters"
              : `No ${objectType.pluralName.toLowerCase()} in this workspace yet`
          }
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
      {retiring && (
        <ConfirmDialog
          title={retirementImpact ? `Retire ${retirementImpact.objectCount} objects?` : `Retire “${retiring.name}”?`}
          confirmLabel={retirementImpact ? "Confirm retirement" : "Retire object"}
          pending={retirementPending}
          error={retirementError}
          onCancel={() => {
            setRetiring(undefined);
            setRetirementImpact(undefined);
            setRetirementError("");
          }}
          onConfirm={retireObject}
        >
          {retirementImpact ? (
            <RetirementImpactSummary model={model} impact={retirementImpact} />
          ) : (
            <p>
              The engine will check dependencies before retirement. A cascade always requires separate confirmation.
            </p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}
