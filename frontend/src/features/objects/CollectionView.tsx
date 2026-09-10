/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { useState } from "react";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { objectTypeFor } from "@/model/lookup";
import { InlineError } from "@/ui/InlineError";
import { ObjectTable } from "@/ui/ObjectTable";
import { Pagination } from "@/ui/Pagination";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { useCursorPages } from "@/lib/hooks/useCursorPages";
import type { ObjectItem } from "@/types";
import type { ViewComponentProps } from "./views/types";

export function ObjectCollectionView({
  model,
  application,
  view,
  workspaceKey,
  query,
  onQueryChange,
  onOpen,
  readOnly = true,
  onChanged,
}: ViewComponentProps) {
  const api = useDataApi();
  const [creating, setCreating] = useState(false);
  const objectType = view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
  const pages = useCursorPages<ObjectItem>(
    objectType
      ? (cursor) =>
          api.objects(objectType.key, {
            applicationKey: application.key,
            workspaceKey,
            search: query.search,
            sort: query.sort,
            filters: query.filters,
            cursor,
            pageSize: query.pageSize,
          })
      : null,
    [application.key, view.key, workspaceKey, query.search, query.sort, query.pageSize, query.filters],
    { cursors: query.cursors ?? [], onChange: (cursors) => onQueryChange({ ...query, cursors }) },
  );
  const { loading, error } = pages;

  if (!objectType) return <div className="empty-state">This configured view does not select an object type.</div>;
  const columns = view.config.columns ?? [
    "name",
    ...objectType.attributes.slice(0, 4).map((item) => item.attributeTypeKey),
  ];

  return (
    <>
      <header className="page-header collection-header">
        <div>
          <h1>{view.name}</h1>
          <p>{objectType.description ?? application.description}</p>
        </div>
        {!readOnly && (
          <button className="primary" onClick={() => setCreating(true)}>
            Add {objectType.name}
          </button>
        )}
      </header>
      <section className="surface collection-surface">
        <ObjectToolbar
          model={model}
          view={view}
          query={query}
          onChange={(next) => onQueryChange({ ...next, cursors: undefined })}
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
        {(!error || pages.items.length > 0) && (
          <ObjectTable
            model={model}
            columns={columns}
            objects={pages.items}
            loading={loading}
            onOpen={onOpen}
            label={`${view.name} table`}
            emptyMessage={
              query.search || query.filters.length > 0
                ? "No results match these filters"
                : `No ${objectType.pluralName.toLowerCase()} in this workspace yet`
            }
          />
        )}
        {!error && (
          <Pagination
            disabled={loading}
            page={pages.pageNumber}
            hasNext={pages.hasNext}
            onPrevious={pages.previous}
            onNext={pages.next}
          />
        )}
      </section>
      {creating && !readOnly && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          onClose={() => setCreating(false)}
          onSaved={(item) => {
            setCreating(false);
            onChanged?.();
            onOpen(item);
          }}
        />
      )}
    </>
  );
}
