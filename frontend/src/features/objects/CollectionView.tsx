/**
 * The table renderer behind every declared view type. Selected through `views/registry`.
 */

import { Card } from "@/ui/Card";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { attributeName, isQueryableField, listSortFields, RELATED_EXPAND_LIMIT, relatedKeys } from "@/model/fields";
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
import { useRecordSelection } from "@/lib/hooks/useRecordSelection";
import { SelectionBar, selectionText } from "@/features/objects/SelectionBar";
import { BulkChangeDialog } from "@/features/objects/BulkChangeDialog";
import { BulkDeleteDialog } from "@/features/objects/BulkDeleteDialog";
import { BulkRelationDialog, hasBulkRelations } from "@/features/objects/BulkRelationDialog";
import { readMatching } from "@/lib/readMatching";
import type { CollectionFilter, ObjectItem, TableViewDefinition } from "@/types";
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
  onExport,
  onImport,
  bulkSelection,
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
  // The bulk action open over the selection (0.9 K2, K2b).
  const [bulkAction, setBulkAction] = useState<BulkActionKind>();
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
  // The phone sheet's count of a filter draft (K6a, D163): the list's own read, totalled.
  const countDraft = useCallback(
    async (filters: CollectionFilter[]) =>
      objectType
        ? (
            await api.objects(objectType.key, {
              applicationKey: application.key,
              workspaceKey,
              search: query.search,
              parentObjectId: query.parentObjectId,
              filters,
              pageSize: 1,
              includeTotal: true,
            })
          ).totalCount
        : undefined,
    [api, objectType, application.key, workspaceKey, query.search, query.parentObjectId],
  );
  const columns = view.config.columns ?? [
    "name",
    ...(objectType?.attributes.slice(0, 4).map((item) => item.attributeTypeKey) ?? []),
  ];
  const display = useTableDisplay(columns, `${application.key}:${view.key}`);
  // Only the shown relation columns are read (0.9 K5, D146).
  const expand = relatedKeys(display.columns);
  const expandKey = expand.join(" ");
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
            expand,
            // As many as a wide column can show; the cell draws what fits (K5b).
            expandLimit: expand.length ? RELATED_EXPAND_LIMIT : undefined,
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
      expandKey,
    ],
    { anchor: query.anchor, refreshToken },
  );
  const { loading, error } = pages;
  // The selection belongs to the list its search, filters and scope define (K1, D108).
  const listKey = JSON.stringify([query.search, query.filters, query.parentObjectId ?? null]);
  const selection = useRecordSelection(listKey, pages.items, bulkSelection?.maxItems ?? 0);
  const more = pages.hasNext || pages.hasPrevious;
  // How many records the list matches: read once per list at the first selection gesture, so the
  // bar can offer "all matching" as soon as every loaded row is selected.
  const countKey = `${listKey}#${refreshToken}`;
  const [counted, setCounted] = useState<{ key: string; total: number }>();
  const knownTotal = !more
    ? pages.items.length
    : (pages.totalCount ?? (counted?.key === countKey ? counted.total : undefined));
  const offerMatching =
    Boolean(bulkSelection) && selection.selection.mode === "ids" && selection.loaded === "all" && more;
  async function readTotal(): Promise<number | undefined> {
    if (knownTotal !== undefined) return knownTotal;
    if (!objectType) return undefined;
    const page = await api.objects(objectType.key, {
      applicationKey: application.key,
      workspaceKey,
      search: query.search,
      filters: query.filters,
      parentObjectId: query.parentObjectId,
      pageSize: 1,
      includeTotal: true,
    });
    if (page.totalCount === undefined) return undefined;
    setCounted({ key: countKey, total: page.totalCount });
    return page.totalCount;
  }
  const countMatching = () => {
    if (knownTotal === undefined) void readTotal().catch(() => undefined);
  };
  /** Cmd+A (Ctrl+A) in the table: every record the list matches (D104 amended). */
  async function selectAll() {
    if (!more) return selection.selectLoaded();
    const total = await readTotal().catch(() => undefined);
    if (total !== undefined) selection.selectMatching(total);
  }
  // Said by the status region at each change of count.
  const announcement = selection.count > 0 ? selectionText(selection.selection, selection.count) : "Nothing selected";
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
  // Export changes nothing, so it is offered in every context; the search is not carried (D60).
  const exportAction = onExport && (
    <button
      type="button"
      className="secondary"
      onClick={() =>
        onExport({
          workspaceKey,
          changeSetId: changeSet?.id,
          publicationId: publication?.id,
          objectTypeKeys: application.objectTypeKeys,
          selected: [objectType.key],
          filters: { objectTypeKey: objectType.key, filters: query.filters },
          search: query.search || undefined,
          parentObjectId: query.parentObjectId,
        })
      }
    >
      Export
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
        actions={
          <>
            {onImport && (
              <button type="button" className="secondary" onClick={onImport}>
                Import
              </button>
            )}
            {exportAction}
            {add}
          </>
        }
      />
      <ScopeBanner
        model={model}
        workspaceKey={workspaceKey}
        query={query}
        onQueryChange={onQueryChange}
        pluralName={objectType.pluralName}
      />
      {lenses}
      <Card
        as="section"
        flush
        className="collection-surface"
        onKeyDown={(event) => {
          if (!bulkSelection || !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "a") return;
          const target = event.target as HTMLElement;
          // Text fields keep Cmd+A for their text; only the table selects records with it.
          if (target.closest("input:not([type='checkbox']), textarea, select, [contenteditable='true']")) return;
          if (!target.closest(".object-table")) return;
          event.preventDefault();
          void selectAll();
        }}
      >
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
          workspaceKey={workspaceKey}
          noun={[objectType.name, objectType.pluralName]}
          countDraft={countDraft}
        />
        {bulkSelection && (
          <>
            <SelectionBar
              selection={selection.selection}
              selected={selection.count}
              matchingTotal={offerMatching ? knownTotal : undefined}
              limit={bulkSelection.maxItems}
              refusedTotal={selection.refusedTotal}
              pluralName={objectType.pluralName}
              onSelectMatching={() => knownTotal !== undefined && selection.selectMatching(knownTotal)}
              onClear={selection.clear}
            >
              {selection.count > 0 && (
                <>
                  <button type="button" className="ghost" onClick={() => setBulkAction("change")}>
                    <Icon name="pencil" size={15} /> Change values
                  </button>
                  {hasBulkRelations(model, objectType) && (
                    <button type="button" className="ghost" onClick={() => setBulkAction("relations")}>
                      <Icon name="link" size={15} /> Change relationships
                    </button>
                  )}
                  <button type="button" className="ghost danger-action" onClick={() => setBulkAction("delete")}>
                    <Icon name="trash" size={15} /> Delete
                  </button>
                </>
              )}
            </SelectionBar>
            <p className="visually-hidden selection-status" role="status">
              {announcement}
            </p>
          </>
        )}
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
            selection={
              bulkSelection && {
                isSelected: selection.isSelected,
                loaded: selection.loaded,
                onToggle: (item, extend) => {
                  selection.toggle(item, extend);
                  countMatching();
                },
                onToggleLoaded: () => {
                  selection.toggleLoaded();
                  countMatching();
                },
              }
            }
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
      {/* Kept open once opened: a delete empties the selection it acted on (D125). */}
      {bulkAction && bulkSelection && (
        <BulkAction
          action={bulkAction}
          model={model}
          objectType={objectType}
          workspaceKey={workspaceKey}
          selection={selection.selection}
          selected={selection.count}
          readMatching={(signal, onProgress) =>
            readMatching(
              (selector) =>
                api.objects(objectType.key, {
                  applicationKey: application.key,
                  workspaceKey,
                  search: query.search,
                  filters: query.filters,
                  parentObjectId: query.parentObjectId,
                  ...selector,
                }),
              { signal, onProgress },
            )
          }
          onClose={() => setBulkAction(undefined)}
          onApplied={(_, versions) => {
            selection.takeVersions(versions);
            onChanged?.();
          }}
          onDeleted={(_, deleted) => {
            selection.dropDeleted(deleted);
            onChanged?.();
          }}
          onRelated={() => onChanged?.()}
          onOpenRecord={(id) =>
            onOpen({ id, objectTypeKey: objectType.key, applicationKey: application.key, workspaceKey })
          }
        />
      )}
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

type BulkActionKind = "change" | "relations" | "delete";

/** The bulk dialog open over the selection: its props are shared, its action is its own. */
function BulkAction({
  action,
  onApplied,
  onDeleted,
  onRelated,
  ...shared
}: { action: BulkActionKind; onRelated: () => void } & Omit<Parameters<typeof BulkChangeDialog>[0], "onApplied"> &
  Pick<Parameters<typeof BulkChangeDialog>[0], "onApplied"> &
  Pick<Parameters<typeof BulkDeleteDialog>[0], "onDeleted">) {
  if (action === "change") return <BulkChangeDialog {...shared} onApplied={onApplied} />;
  if (action === "relations") return <BulkRelationDialog {...shared} onApplied={onRelated} />;
  return <BulkDeleteDialog {...shared} onDeleted={onDeleted} />;
}
