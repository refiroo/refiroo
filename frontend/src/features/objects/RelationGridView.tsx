/**
 * A relationships grid (0.13 RG), the grid layout of a relationships table: each record of the
 * `from` type once, linked or not, with its own columns, and one column group per related record
 * with the relationship's attributes under it. Rows scroll in a `ScrollWindow` over a cursor window;
 * filtering, sorting and the column groups are the engine's (`GET /workspaces/{key}/relation-grid`).
 * It is built from what a collection and the relationships table use: the search and filter fields,
 * the Display menu for the columns and attributes shown, the selection and its bar, and a bulk
 * dialog for Change relationship values. A value is edited in its cell with the shared
 * `RelationValueCell` (a yes/no value flips with one click); a cell saved is read again on its own,
 * not the whole list, and the rows are memoised, so ticking and saving draw only the rows they touch.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import { RelationGridChangeDialog } from "@/features/objects/RelationGridChangeDialog";
import { RelationGridLocations } from "@/features/objects/RelationGridLocations";
import { RelationGridRowView } from "@/features/objects/RelationGridRow";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { SelectionBar, selectionText } from "@/features/objects/SelectionBar";
import { RELATION_ATTRIBUTES_LABEL, relationAttributeTypes } from "@/features/objects/relations/RelationAttributes";
import { relationAttributeColumn } from "@/features/objects/relations/relationAttributeColumns";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useRecordSelection } from "@/lib/hooks/useRecordSelection";
import { attributeName } from "@/model/fields";
import { endFilterView } from "@/model/relationGrid";
import { objectTypeHue, objectTypeTile } from "@/model/hues";
import { isManagedRelation, objectTypeFor } from "@/model/lookup";
import type { EngineModel, RelationGridColumn, RelationGridRow, RelationTableViewDefinition } from "@/types";
import { Card } from "@/ui/Card";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { PageHeader } from "@/ui/PageHeader";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import type { ViewComponentProps } from "./views/types";

type End = "from" | "to";

/**
 * Keeps the second header row under the first, whatever height the first has (a wrapped group name,
 * a resize): the first row's height is the second's sticky offset (`--grid-head-1`).
 */
function stackHeaderRows(row: HTMLTableRowElement | null) {
  const table = row?.closest("table");
  if (!row || !table) return;
  const measure = () => table.style.setProperty("--grid-head-1", `${row.getBoundingClientRect().height}px`);
  measure();
  if (typeof ResizeObserver === "undefined") return;
  const observer = new ResizeObserver(measure);
  observer.observe(row);
  return () => observer.disconnect();
}

interface Shown {
  key: string;
  columns: RelationGridColumn[];
  columnTotal: number;
  rowTotal: number;
}

const listingApplication = (model: EngineModel, applicationKey: string, objectTypeKey: string) =>
  model.applications.find((item) => item.key === applicationKey && item.objectTypeKeys.includes(objectTypeKey))?.key ??
  model.applications.find((item) => item.objectTypeKeys.includes(objectTypeKey))?.key ??
  applicationKey;

export function RelationGridView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly: contextReadOnly,
  onChanged,
  query,
  onQueryChange,
  onAnchorChange,
  refreshToken = 0,
  lenses,
  onOpen,
  bulkSelection,
}: ViewComponentProps) {
  const view = rawView as RelationTableViewDefinition;
  const { config } = view;
  const api = useDataApi();
  const { changeSet } = useWorkspaceData();
  const writes = useRecordWrites();
  const [internalRefresh, setInternalRefresh] = useState(0);
  const [shown, setShown] = useState<Shown>({ key: "", columns: [], columnTotal: 0, rowTotal: 0 });
  // A row read again after one of its cells was saved, instead of the whole list.
  const [patched, setPatched] = useState<{ base: unknown; rows: Map<string, RelationGridRow> }>();
  const [linking, setLinking] = useState<string>();
  const [linkError, setLinkError] = useState<string>();
  const [changing, setChanging] = useState(false);

  const fromType = objectTypeFor(model, config.fromObjectTypeKey);
  const toType = objectTypeFor(model, config.toObjectTypeKey);
  const binding = model.objectTypeRelations.find(
    (item) =>
      item.relationTypeKey === config.relationTypeKey &&
      item.fromObjectTypeKey === config.fromObjectTypeKey &&
      item.toObjectTypeKey === config.toObjectTypeKey,
  );
  const declared = relationAttributeTypes(model, binding);
  const attributes = useMemo(
    () => config.attributeColumns.flatMap((key) => declared.filter((item) => item.key === key)),
    // The model and the view's columns are what the attributes follow.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [model, config.attributeColumns, binding],
  );
  const fromApplicationKey = listingApplication(model, application.key, config.fromObjectTypeKey);
  const toApplicationKey = listingApplication(model, application.key, config.toObjectTypeKey);
  // A relationship is written where either end's type may be (0.12 Z5, D291, D329); none in a publication.
  const readOnly =
    contextReadOnly ||
    !(writes.permits(fromApplicationKey, config.fromObjectTypeKey) || writes.permitsType(config.toObjectTypeKey));
  const managed = !!binding && isManagedRelation(model, binding);
  const editable = !readOnly && attributes.length > 0 && !managed;
  const canLink = !readOnly && !managed;
  const selectable = editable && !!bulkSelection;

  const pageSize = query.pageSize || config.pageSize;
  const sort = query.sort || config.defaultSort;
  const filters = query.filters;
  const columnIds = query.gridColumnIds;
  const queryKey = JSON.stringify([
    view.key,
    query.search,
    sort,
    filters,
    columnIds ?? null,
    query.gridSearch,
    changeSet?.id,
  ]);

  const list = useCursorWindow<RelationGridRow>(
    (selector) =>
      api
        .relationGrid({
          workspaceKey,
          applicationKey: application.key,
          viewKey: view.key,
          search: query.search || undefined,
          sort,
          filters: filters.map(({ field, operator, value }) => ({ field, operator, value })),
          toObjectIds: columnIds,
          toSearch: query.gridSearch,
          ...selector,
          pageSize,
        })
        .then((page) => {
          setShown({
            key: queryKey,
            columns: page.columns ?? [],
            columnTotal: page.columnTotal ?? 0,
            rowTotal: page.rowTotal ?? 0,
          });
          return page;
        }),
    [
      application.key,
      view.key,
      workspaceKey,
      query.search,
      sort,
      JSON.stringify(filters),
      JSON.stringify(columnIds ?? null),
      query.gridSearch,
      pageSize,
      changeSet?.id,
    ],
    { anchor: query.anchor, refreshToken: refreshToken + internalRefresh },
  );
  const current = shown.key === queryKey ? shown : { ...shown, key: queryKey };
  const columns = current.columns;

  // --- columns and attributes shown (the Display menu, as the relationships table has it) ---
  const fieldLabel = (end: End, field: string) => {
    const type = end === "from" ? fromType : toType;
    return field === "name" ? (type?.name ?? field) : `${attributeName(model, field)} (${type?.name ?? end})`;
  };
  // The name is the record's identity in the Display menu, as in a collection: always shown, the rest may be hidden.
  const fromColumnKeys = [
    "name",
    ...config.fromColumns.filter((field) => field !== "name").map((field) => `from:${field}`),
  ];
  const attributeColumnKeys = attributes.map((item) => relationAttributeColumn(item.key));
  const display = useTableDisplay([...fromColumnKeys, ...attributeColumnKeys], `${application.key}:${view.key}`);
  // Keyed by what they hold, so the rows' props stay the same arrays until the Display menu changes.
  const shownKey = display.columns.join("\n");
  const fromFields = useMemo(() => {
    const keys = new Set(shownKey.split("\n"));
    return config.fromColumns.filter((field) => field !== "name" && keys.has(`from:${field}`));
  }, [config.fromColumns, shownKey]);
  const shownAttributes = useMemo(() => {
    const keys = new Set(shownKey.split("\n"));
    const chosen = attributes.filter((item) => keys.has(relationAttributeColumn(item.key)));
    return chosen.length > 0 ? chosen : attributes;
  }, [attributes, shownKey]);
  const settable = attributes.filter((item) => item.valueType !== "json");

  // --- the selection, as a collection's ---
  const items = useMemo(() => {
    if (!patched || patched.base !== list.items) return list.items;
    return list.items.map((row) => patched.rows.get(row.source.id) ?? row);
  }, [list.items, patched]);
  const selectable_rows = useMemo(
    () => items.map((row) => ({ id: row.source.id, version: 0, name: row.source.name })),
    [items],
  );
  const listKey = JSON.stringify([query.search, filters, columnIds ?? null, query.gridSearch]);
  const selection = useRecordSelection(listKey, selectable_rows, bulkSelection?.maxItems ?? 0);
  const more = list.hasNext || list.hasPrevious;
  const offerMatching = selectable && selection.selection.mode === "ids" && selection.loaded === "all" && more;
  const announcement = selection.count > 0 ? selectionText(selection.selection, selection.count) : "Nothing selected";

  // The row handlers read the latest state through a ref, so they stay the same functions and the
  // memoised rows do not draw again for them.
  const latest = useRef({ selection, columns, items });
  useEffect(() => {
    latest.current = { selection, columns, items };
  });
  const onToggle = useCallback(
    (row: RelationGridRow, extend: boolean) =>
      latest.current.selection.toggle({ id: row.source.id, version: 0, name: row.source.name }, extend),
    [],
  );
  const openRecord = useCallback(
    (end: End, record: { id: string; objectTypeKey: string }) =>
      onOpen({
        id: record.id,
        objectTypeKey: record.objectTypeKey,
        applicationKey: end === "from" ? fromApplicationKey : toApplicationKey,
        workspaceKey,
      }),
    [onOpen, fromApplicationKey, toApplicationKey, workspaceKey],
  );
  const onOpenRow = useCallback((row: RelationGridRow) => openRecord("from", row.source), [openRecord]);

  /** How many rows the filters select, for the filter sheet's Show N (D163). */
  const countRows = (next: { field: string; operator: string; value: string }[]) =>
    api
      .relationGrid({
        workspaceKey,
        applicationKey: application.key,
        viewKey: view.key,
        search: query.search || undefined,
        filters: [
          ...filters.filter((filter) => filter.field.startsWith("to:")),
          ...next.map((filter) =>
            filter.field.startsWith("relation:") ? filter : { ...filter, field: `from:${filter.field}` },
          ),
        ].map(({ field, operator, value }) => ({ field, operator, value })),
        toObjectIds: columnIds,
        pageSize: 1,
      })
      .then((page) => page.rowTotal);

  function reload() {
    setInternalRefresh((value) => value + 1);
    selection.clear();
    onChanged?.();
  }

  const onSaved = useCallback(
    async (row: RelationGridRow, column: RelationGridColumn, relationId: string) => {
      try {
        const fresh = await api.relation(relationId, workspaceKey);
        setPatched((held) => {
          const base = latest.current.items === list.items ? list.items : held?.base;
          const rows = held && held.base === base ? new Map(held.rows) : new Map<string, RelationGridRow>();
          const was = rows.get(row.source.id) ?? row;
          const related = was.relations[column.id];
          if (!related) return held;
          rows.set(row.source.id, {
            ...was,
            relations: {
              ...was.relations,
              [column.id]: { ...related, version: fresh.version, attributes: fresh.attributes },
            },
          });
          return { base, rows };
        });
      } catch {
        setInternalRefresh((value) => value + 1);
      }
    },
    // `list.items` is the list the patch is read against.
    [api, workspaceKey, list.items],
  );

  const onLink = useCallback(
    async (row: RelationGridRow, column: RelationGridColumn) => {
      setLinking(`${row.source.id}:${column.id}`);
      setLinkError(undefined);
      try {
        await api.createRelation({
          relationTypeKey: config.relationTypeKey,
          fromObjectId: row.source.id,
          toObjectId: column.id,
          attributes: {},
          expectedRelationSetVersion: row.mappingVersion,
          relationSetDirection: "outgoing",
        });
        setInternalRefresh((value) => value + 1);
        onChanged?.();
      } catch (cause) {
        setLinkError(`${row.source.name} · ${column.label}: ${errorMessage(cause)}`);
      } finally {
        setLinking(undefined);
      }
    },
    [api, config.relationTypeKey, onChanged],
  );

  if (!fromType || !toType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This relationships grid references an object type that does not exist in the active model.</p>
      </div>
    );
  }

  const relationType = model.relationTypes.find((item) => item.key === config.relationTypeKey);
  const rowsFilter = endFilterView(model, application.key, view.key, config, "from");
  const toFilter = endFilterView(model, application.key, view.key, config, "to");
  // The rows' bar speaks the collection's plain field names; the grid's address prefixes them.
  const rowsToolbarFilters = filters.flatMap((filter) =>
    filter.field.startsWith("from:")
      ? [{ ...filter, field: filter.field.slice(5) }]
      : filter.field.startsWith("relation:")
        ? [filter]
        : [],
  );
  const span = Math.max(1, shownAttributes.length);
  const toPlural = toType.pluralName.toLowerCase();
  const fromPlural = fromType.pluralName.toLowerCase();
  const columnCount = (selectable ? 1 : 0) + 1 + fromFields.length + columns.length * span;
  const empty = query.search || filters.length ? `No ${fromPlural} match these filters.` : `No ${fromPlural} yet.`;
  const proposedAny = !!changeSet;
  const hue = objectTypeHue(model, toType.key);

  return (
    <div>
      <PageHeader
        focusTitle
        icon={<HueTile hue={objectTypeHue(model, fromType.key)} icon={fromType.icon} size={40} />}
        title={view.name}
        descriptionClassName="mapping-direction"
        description={
          <>
            <span>{fromType.name}</span>
            <Icon name="arrow-right" size={14} />
            <span>{relationType?.name ?? config.relationTypeKey}</span>
            <Icon name="arrow-right" size={14} />
            <span>{toType.name}</span>
          </>
        }
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <ObjectToolbar
          model={model}
          view={rowsFilter.view}
          query={{ ...query, filters: rowsToolbarFilters }}
          onChange={(next) =>
            onQueryChange({
              ...query,
              search: next.search,
              filters: [
                ...filters.filter((filter) => filter.field.startsWith("to:")),
                ...next.filters.map((filter) =>
                  filter.field.startsWith("relation:") ? filter : { ...filter, field: `from:${filter.field}` },
                ),
              ],
              anchor: undefined,
            })
          }
          placeholder={`Search ${fromPlural}`}
          workspaceKey={workspaceKey}
          applicationKey={rowsFilter.applicationKey}
          noun={[fromType.name, fromType.pluralName]}
          countDraft={countRows}
          display={
            <>
              <RelationGridLocations
                model={model}
                toType={toType}
                filterView={toFilter.view}
                applicationKey={toFilter.applicationKey}
                query={query}
                workspaceKey={workspaceKey}
                countDraft={async () => undefined}
                onChange={(next) => onQueryChange({ ...query, ...next, anchor: undefined })}
              />
              <TableDisplay
                model={model}
                columns={fromColumnKeys}
                extraColumns={{ legend: RELATION_ATTRIBUTES_LABEL, columns: attributeColumnKeys }}
                columnLabel={(key) =>
                  key === "name"
                    ? (fromType?.name ?? key)
                    : key.startsWith("from:")
                      ? fieldLabel("from", key.slice(5))
                      : (attributes.find((item) => relationAttributeColumn(item.key) === key)?.name ?? key)
                }
                display={display}
                pageSize={pageSize}
                defaultPageSize={config.pageSize}
                onPageSize={(size) => onQueryChange({ ...query, pageSize: size, anchor: undefined })}
                urlBacked
              />
            </>
          }
        />
        {selectable && bulkSelection && (
          <>
            <SelectionBar
              selection={selection.selection}
              selected={selection.count}
              matchingTotal={offerMatching ? current.rowTotal : undefined}
              limit={bulkSelection.maxItems}
              refusedTotal={selection.refusedTotal}
              pluralName={fromType.pluralName}
              onSelectMatching={() => selection.selectMatching(current.rowTotal)}
              onClear={selection.clear}
            >
              {selection.count > 0 && settable.length > 0 && columns.length > 0 && (
                <button type="button" className="ghost" onClick={() => setChanging(true)}>
                  <Icon name="pencil" size={15} /> Change relationship values
                </button>
              )}
            </SelectionBar>
            <p className="visually-hidden selection-status" role="status">
              {announcement}
            </p>
          </>
        )}
        {current.columnTotal > columns.length && (
          <Notice tone="info">
            Showing {columns.length} of {current.columnTotal} {toPlural}. Narrow the {toType.pluralName} filter to see
            the others.
          </Notice>
        )}
        {linkError && (
          <Notice tone="error" title="Not linked" focusOnMount>
            <p>{linkError}</p>
          </Notice>
        )}
        {list.error && <InlineError message={list.error} onRetry={list.retry} />}
        {(!list.error || items.length > 0) && (
          <ScrollWindow
            list={list}
            label={view.name}
            noun={[fromType.name.toLowerCase(), fromPlural]}
            pageSize={pageSize}
            onAnchorChange={onAnchorChange}
            className={`table-wrap object-table relation-grid${display.compact ? " density-compact" : ""}`}
          >
            {(drawn) => (
              <table className="data-table relation-grid-table">
                <thead>
                  <tr ref={stackHeaderRows}>
                    {selectable && (
                      <th rowSpan={2} className="relation-grid-select">
                        <SelectionCheckbox
                          label="Select all shown"
                          state={selection.loaded}
                          onSelect={() => selection.toggleLoaded()}
                        />
                      </th>
                    )}
                    <th rowSpan={2} className="relation-grid-name">
                      {fromType.name}
                    </th>
                    {fromFields.map((field) => (
                      <th key={field} rowSpan={2}>
                        {fieldLabel("from", field)}
                      </th>
                    ))}
                    {columns.map((column) => (
                      <th
                        key={column.id}
                        colSpan={span}
                        scope="colgroup"
                        className="relation-grid-group"
                        data-hue={hue}
                      >
                        <span className="relation-grid-group-name">
                          <HueTile {...objectTypeTile(model, toType.key)} size={18} />
                          <button className="cell-link" onClick={() => openRecord("to", column)}>
                            {column.label}
                          </button>
                          <span className="muted">
                            · {column.linkedCount} of {current.rowTotal} linked
                          </span>
                        </span>
                      </th>
                    ))}
                  </tr>
                  <tr>
                    {columns.flatMap((column) =>
                      shownAttributes.map((attribute, position) => (
                        <th
                          key={`${column.id}:${attribute.key}`}
                          scope="col"
                          className={`relation-grid-sub${position === 0 ? " first" : ""}`}
                        >
                          {attribute.name}
                        </th>
                      )),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 && !list.loading ? (
                    <tr>
                      <td colSpan={columnCount} className="empty-row">
                        {empty}
                      </td>
                    </tr>
                  ) : (
                    <>
                      <WindowSpacer as="tr" edge="before" height={drawn.before} columns={columnCount} />
                      {drawn.rows.map(({ index, item: row, size }) =>
                        row === undefined ? (
                          <WindowPlaceholder
                            key={`placeholder-${index}`}
                            as="tr"
                            index={index}
                            size={size}
                            cells={[undefined]}
                          />
                        ) : (
                          <RelationGridRowView
                            key={row.source.id}
                            row={patched?.base === list.items ? (patched.rows.get(row.source.id) ?? row) : row}
                            index={index}
                            rowRef={drawn.measure}
                            columns={columns}
                            attributes={shownAttributes}
                            fromFields={fromFields}
                            selectable={selectable}
                            selected={selection.isSelected(row.source.id)}
                            editable={editable}
                            canLink={canLink}
                            linking={!!linking?.startsWith(`${row.source.id}:`)}
                            proposedAny={proposedAny}
                            workspaceKey={workspaceKey}
                            onToggle={onToggle}
                            onOpen={onOpenRow}
                            onLink={onLink}
                            onSaved={onSaved}
                          />
                        ),
                      )}
                      <WindowSpacer as="tr" edge="after" height={drawn.after} columns={columnCount} />
                    </>
                  )}
                </tbody>
              </table>
            )}
          </ScrollWindow>
        )}
        <div className="relation-grid-legend">
          {proposedAny && (
            <span className="relation-grid-legend-item">
              <i className="relation-grid-proposed relation-grid-proposed-key" aria-hidden="true" /> Proposed in this
              change set
            </span>
          )}
          <span className="relation-grid-legend-item">
            <i className="relation-grid-hatch" aria-hidden="true" /> Not linked
          </span>
        </div>
      </Card>
      {changing && (
        <RelationGridChangeDialog
          applicationKey={application.key}
          viewKey={view.key}
          workspaceKey={workspaceKey}
          noun={[fromType.name.toLowerCase(), fromPlural]}
          toNoun={[toType.name.toLowerCase(), toPlural]}
          attributes={settable}
          columns={columns}
          selection={selection.selection}
          selected={selection.count}
          search={query.search}
          filters={filters}
          onClose={() => setChanging(false)}
          onApplied={reload}
        />
      )}
    </div>
  );
}
