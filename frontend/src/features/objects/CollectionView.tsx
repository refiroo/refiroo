/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { useEffect, useRef, useState } from "react";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { objectTypeFor } from "@/model/lookup";
import { InlineError } from "@/ui/InlineError";
import { ObjectTable } from "@/ui/ObjectTable";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
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
  refreshToken = 0,
  selectedId,
}: ViewComponentProps) {
  const api = useDataApi();
  const [creating, setCreating] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const previousSelection = useRef(selectedId);
  const focusedRow = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (previousSelection.current && !selectedId) {
      const buttons = root.current?.querySelectorAll<HTMLButtonElement>("[data-record-id]");
      const selected = Array.from(buttons ?? []).find(
        (button) => button.dataset.recordId === previousSelection.current,
      );
      (selected ?? root.current?.querySelector<HTMLElement>("h1"))?.focus();
    }
    previousSelection.current = selectedId;
  }, [selectedId]);
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
    refreshToken,
  );
  const { loading, error } = pages;
  useEffect(() => {
    if (!loading && !error && pages.items.length === 0 && pages.pageNumber > 1) pages.previous();
    if (
      focusedRow.current &&
      !loading &&
      document.activeElement === document.body &&
      !pages.items.some((item) => item.id === focusedRow.current)
    ) {
      root.current?.querySelector<HTMLElement>("h1")?.focus();
      focusedRow.current = undefined;
    }
  }, [loading, error, pages]);

  const columns = view.config.columns ?? [
    "name",
    ...(objectType?.attributes.slice(0, 4).map((item) => item.attributeTypeKey) ?? []),
  ];
  const display = useTableDisplay(columns, `${application.key}:${view.key}`);
  if (!objectType) return <div className="empty-state">This configured view does not select an object type.</div>;

  return (
    <div
      ref={root}
      onFocusCapture={(event) => {
        focusedRow.current = (event.target as HTMLElement).dataset.recordId;
      }}
    >
      <header className="page-header collection-header">
        <div>
          <h1 tabIndex={-1}>{view.name}</h1>
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
          display={
            <TableDisplay
              model={model}
              columns={columns}
              display={display}
              pageSize={query.pageSize}
              defaultPageSize={view.config.pageSize}
              onPageSize={(pageSize) => onQueryChange({ ...query, pageSize, cursors: undefined })}
              urlBacked
            />
          }
          model={model}
          view={view}
          query={query}
          onChange={(next) => onQueryChange({ ...next, cursors: undefined })}
          placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
        />
        <div className="collection-meta">
          <span role="status">
            {loading
              ? "Loading records…"
              : !error
                ? `${pages.items.length} on this page`
                : pages.items.length > 0
                  ? "Showing previously loaded records"
                  : "Records unavailable"}
          </span>
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        {(!error || pages.items.length > 0) && (
          <ObjectTable
            model={model}
            columns={display.columns}
            compact={display.compact}
            columnWidths={display.widths}
            onColumnWidth={display.setWidth}
            identityColumn={display.identity}
            sort={query.sort}
            sortFields={view.config.sortFields}
            onSort={(sort) => onQueryChange({ ...query, sort, cursors: undefined })}
            objects={pages.items}
            loading={loading}
            onOpen={onOpen}
            selectedId={selectedId}
            renderActions={(item, menu) => (
              <RecordActionMenu
                object={item}
                readOnly={readOnly}
                onEdit={() => onOpen(item, "edit")}
                onDelete={() => onOpen(item, "delete")}
                {...menu}
              />
            )}
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
    </div>
  );
}
