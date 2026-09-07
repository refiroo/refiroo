/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { api } from "@/api/client";
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
}: ViewComponentProps) {
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
    </>
  );
}
