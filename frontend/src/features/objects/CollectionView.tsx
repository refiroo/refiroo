/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { Card } from "@/ui/Card";
import { useEffect, useMemo, useRef, useState } from "react";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { attributeName, isQueryableField, listSortFields } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { HueTile } from "@/ui/HueTile";
import { objectTypeHue } from "@/model/hues";
import { PageHeader } from "@/ui/PageHeader";
import { ObjectTable } from "@/ui/ObjectTable";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { ScopeBanner } from "@/features/objects/CollectionScope";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import type { ObjectItem, TableViewDefinition } from "@/types";
import type { ViewComponentProps } from "./views/types";

export function ObjectCollectionView({
  model,
  application,
  view: rawView,
  workspaceKey,
  query: requestedQuery,
  onQueryChange,
  onAnchorChange,
  onOpen,
  readOnly = true,
  onChanged,
  refreshToken = 0,
  selectedId,
  lenses,
}: ViewComponentProps) {
  const declaredView = rawView as TableViewDefinition;
  const api = useDataApi();
  const { changeSet, publication } = useWorkspaceData();
  // Change sets and history record no timestamps, so they are neither offered nor requested there, and
  // a view whose default sort is a timestamp sorts by name instead.
  const live = !changeSet && !publication;
  const view = useMemo<TableViewDefinition>(
    () =>
      live
        ? declaredView
        : {
            ...declaredView,
            config: {
              ...declaredView.config,
              filterFields: declaredView.config.filterFields.filter((field) => isQueryableField(field, false)),
              sortFields: declaredView.config.sortFields.filter((field) => isQueryableField(field, false)),
            },
          },
    [declaredView, live],
  );
  const queryableFilters = useMemo(
    () =>
      live ? requestedQuery.filters : requestedQuery.filters.filter((filter) => isQueryableField(filter.field, false)),
    [requestedQuery.filters, live],
  );
  const query = live
    ? requestedQuery
    : {
        ...requestedQuery,
        sort: isQueryableField(requestedQuery.sort, false) ? requestedQuery.sort : "name",
        filters: queryableFilters,
      };
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
  const pages = useCursorWindow<ObjectItem>(
    objectType
      ? (selector) =>
          api.objects(objectType.key, {
            applicationKey: application.key,
            workspaceKey,
            search: query.search,
            sort: query.sort,
            filters: query.filters,
            parentObjectId: query.parentObjectId,
            ...selector,
            pageSize: query.pageSize,
          })
      : null,
    [
      application.key,
      view.key,
      workspaceKey,
      query.search,
      query.sort,
      query.pageSize,
      query.filters,
      query.parentObjectId,
    ],
    { anchor: query.anchor, refreshToken },
  );
  const { loading, error } = pages;
  useEffect(() => {
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
  const sorting = useTableSort({
    sort: query.sort,
    fields: objectType ? listSortFields(model, [objectType], columns, view.config.sortFields, live) : [],
    onSort: (sort) => onQueryChange({ ...query, sort, anchor: undefined }),
    labelFor: (field) => attributeName(model, field),
  });
  if (!objectType) return <div className="empty-state">This configured view does not select an object type.</div>;
  const hue = objectTypeHue(model, objectType.key);
  const narrowed = query.search !== "" || query.filters.length > 0;
  const add = !readOnly && (
    <button className="primary" onClick={() => setCreating(true)}>
      <Icon name="plus" /> Add {objectType.name}
    </button>
  );

  return (
    <div
      ref={root}
      onFocusCapture={(event) => {
        focusedRow.current = (event.target as HTMLElement).dataset.recordId;
      }}
    >
      <PageHeader
        focusTitle
        icon={<HueTile hue={hue} icon={objectType.icon} size={40} />}
        title={view.name}
        description={objectType.description ?? application.description}
        actions={add}
      />
      <ScopeBanner
        model={model}
        workspaceKey={workspaceKey}
        query={query}
        onQueryChange={onQueryChange}
        pluralName={objectType.pluralName}
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <ObjectToolbar
          display={
            <TableDisplay
              model={model}
              columns={columns}
              display={display}
              pageSize={query.pageSize}
              defaultPageSize={view.config.pageSize}
              onPageSize={(pageSize) => onQueryChange({ ...query, pageSize, anchor: undefined })}
              urlBacked
            />
          }
          sortMenu={<SortMenu sorting={sorting} />}
          model={model}
          view={view}
          query={query}
          onChange={(next) => onQueryChange({ ...next, anchor: undefined })}
          placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
        />
        {error && <InlineError message={error} onRetry={pages.retry} />}
        {(!error || pages.items.length > 0) && (
          <ObjectTable
            model={model}
            columns={display.columns}
            compact={display.compact}
            columnWidths={display.widths}
            onColumnWidths={display.setWidths}
            identityColumn={display.identity}
            sorting={sorting}
            list={pages}
            pageSize={query.pageSize}
            seekLabel={query.sort ? attributeName(model, query.sort.replace(/^-/, "")).toLowerCase() : undefined}
            onAnchorChange={onAnchorChange}
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
            emptyIcon={<HueTile hue={hue} icon={objectType.icon} size={40} />}
            emptyMessage={
              narrowed
                ? "No results match these filters"
                : `No ${objectType.pluralName.toLowerCase()} in this workspace yet`
            }
            // A narrowed list's way back is the toolbar's Clear filters, right above it.
            emptyAction={narrowed ? undefined : add}
          />
        )}
      </Card>
      {creating && !readOnly && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          parentObjectId={query.parentObjectId}
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
