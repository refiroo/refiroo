/**
 * The `relationMatrix` lens (Base 0.8 A4): the view's rows down the side, records of an ancestor
 * type across the top, and in each cell the row's related records under that column record. Every
 * label, field and action comes from the view and its binding; nothing here names a starter type.
 *
 * Rows scroll through `useCursorWindow` (ADR-030); columns are either the ones the user chose or a
 * page of the column type, paged sideways with the column cursor (D10). A cell opens a dialog that
 * offers only the view's `cellActions`, and a save re-reads that one cell.
 */

import { StatusPill } from "@/ui/StatusPill";
import { Card } from "@/ui/Card";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { nextGridCell } from "@/lib/gridNavigation";
import { InlineError } from "@/ui/InlineError";
import { DataTable, type CellAttributes, type DataColumn } from "@/ui/DataTable";
import { readHideEmptyColumns, useTableDisplay, writeHideEmptyColumns } from "@/ui/TableDisplay";
import { Switch } from "@/ui/Switch";
import { Icon } from "@/ui/Icon";
import { pageTitle } from "@/model/collections";
import { PageHeader } from "@/ui/PageHeader";
import { HueTile } from "@/ui/HueTile";
import { RecordChip } from "@/ui/RecordChip";
import { objectTypeHue, type Hue } from "@/model/hues";
import { formatValue } from "@/ui/formatValue";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { RelationMatrixCellDialog } from "@/features/objects/RelationMatrixCellDialog";
import { RelationMatrixFilter } from "@/features/objects/RelationMatrixFilter";
import {
  cellRecordLabel,
  columnLabel,
  matrixBinding,
  MATRIX_STATES,
  StateMark,
  stateLabel,
  type MatrixStateKey,
} from "@/features/objects/relationMatrixStates";
import { ScopeBanner } from "@/features/objects/CollectionScope";
import type {
  RelationMatrixCell,
  RelationMatrixColumn,
  RelationMatrixRow,
  RelationMatrixViewDefinition,
} from "@/types";
import type { ViewComponentProps } from "./views/types";
import { useExportExtra, windowTotal } from "./views/useViewExport";
import { DebouncedSearchField } from "@/ui/SearchField";

/** A cell re-read after a save, kept over the loaded page until the list reloads. */
interface RowPatch {
  relationSetVersion: number;
  cells: Record<string, RelationMatrixCell>;
}

export function RelationMatrixView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly,
  query,
  onQueryChange,
  onAnchorChange,
  refreshToken = 0,
  lenses,
  onOpen,
  exportExtraRef,
}: ViewComponentProps) {
  const view = rawView as RelationMatrixViewDefinition;
  const { config } = view;
  const api = useDataApi();
  const { changeSet, publication } = useWorkspaceData();
  const [columnCursor, setColumnCursor] = useState<string>();
  const [open, setOpen] = useState<{ rowId: string; columnId: string }>();
  const [active, setActive] = useState<{ rowId: string; column: number }>();
  const [patches, setPatches] = useState<{ key: string; rows: Record<string, RowPatch> }>({ key: "", rows: {} });
  const grid = useRef<HTMLDivElement>(null);
  const restoreTo = useRef<{ rowId: string; columnId: string } | undefined>(undefined);
  // Set while a reload is in flight: its rows supersede every cell re-read since the list loaded.
  const reloadPending = useRef(false);

  const rowType = objectTypeFor(model, config.rowObjectTypeKey);
  const columnType = objectTypeFor(model, config.columnObjectTypeKey);
  const cellType = objectTypeFor(model, config.cellObjectTypeKey);
  const binding = matrixBinding(model, config);
  // A cell's actions write its cell record and that record's relationships, so they follow the
  // cell type's writes (0.12 Z5, D329).
  const writes = useRecordWrites();
  const cellApplication =
    model.applications.find((item) => item.objectTypeKeys.includes(config.cellObjectTypeKey))?.key ?? application.key;
  const actions =
    readOnly || publication || !writes.permits(cellApplication, config.cellObjectTypeKey)
      ? []
      : (config.cellActions ?? []);
  const columnIds = query.matrixColumnIds;
  const state = columnIds?.length ? query.matrixState : undefined;
  const pageSize = query.pageSize || config.pageSize;
  // Hide empty columns (0.13 LB-D8): kept per view in this browser with the other display choices.
  // Columns named in Filter win, so the choice then has no effect.
  const displayScope = `${application.key}:${view.key}`;
  const [hideChoice, setHideChoice] = useState(() => ({ scope: displayScope, on: readHideEmptyColumns(displayScope) }));
  const hideRequested = hideChoice.scope === displayScope ? hideChoice.on : readHideEmptyColumns(displayScope);
  const hideEmpty = hideRequested && !columnIds?.length;
  const chooseHideEmpty = (on: boolean) => {
    setHideChoice({ scope: displayScope, on });
    writeHideEmptyColumns(displayScope, on);
    setColumnCursor(undefined);
  };

  // The columns come with each page; they depend only on what selects them, so every page of one
  // list carries the same ones and a late page of an earlier list is ignored.
  const columnsKey = JSON.stringify([
    columnIds ?? null,
    columnIds ? null : (columnCursor ?? null),
    changeSet?.id,
    hideEmpty,
  ]);
  const columnsKeyRef = useRef(columnsKey);
  // Declared before the list's own effects, so its first request already reads the new key.
  useEffect(() => {
    columnsKeyRef.current = columnsKey;
  });
  const [columnPage, setColumnPage] = useState<{
    key: string;
    columns: RelationMatrixColumn[];
    next: string | null;
    prev: string | null;
    emptyHidden: number;
  }>();

  const listDeps = [
    application.key,
    view.key,
    workspaceKey,
    query.search,
    query.pageSize,
    query.parentObjectId,
    columnIds?.join(",") ?? "",
    state ?? "",
    columnIds ? "" : (columnCursor ?? ""),
    changeSet?.id,
    hideEmpty,
  ];
  const listKey = JSON.stringify([...listDeps, refreshToken]);
  const pages = useCursorWindow<RelationMatrixRow>(
    rowType && columnType && cellType
      ? (selector) => {
          const requestKey = columnsKey;
          return api
            .relationMatrix({
              workspaceKey,
              applicationKey: application.key,
              viewKey: view.key,
              parentObjectId: query.parentObjectId,
              search: query.search || undefined,
              columnIds,
              columnCursor: columnIds ? undefined : columnCursor,
              hideEmptyColumns: hideEmpty,
              state,
              ...selector,
              pageSize,
            })
            .then((page) => {
              if (reloadPending.current) {
                reloadPending.current = false;
                setPatches({ key: "", rows: {} });
              }
              if (requestKey === columnsKeyRef.current)
                setColumnPage({
                  key: requestKey,
                  columns: page.columns,
                  next: page.columnsNextCursor ?? null,
                  prev: page.columnsPrevCursor ?? null,
                  emptyHidden: page.emptyColumnsHidden ?? 0,
                });
              return page;
            });
        }
      : null,
    listDeps,
    { anchor: query.anchor, refreshToken },
  );
  const columns = useMemo(() => (columnPage?.key === columnsKey ? columnPage.columns : []), [columnPage, columnsKey]);
  // The file's size for the page's Export: the columns are known only once all are read and none is hidden.
  const allColumns = columnIds?.length
    ? columnIds.length
    : columnPage?.key === columnsKey && columnPage.next === null && !columnPage.emptyHidden
      ? columns.length
      : undefined;
  useExportExtra(exportExtraRef, { size: { rows: windowTotal(pages), columns: allColumns } });
  // The columns keep their widths per view on this device, as every table's do (ui/TableDisplay).
  const display = useTableDisplay(["row", ...columns.map((column) => column.id)], displayScope);
  // Once the cell dialog has gone, focus returns to its cell unless the user already moved on.
  useEffect(() => {
    const target = restoreTo.current;
    if (open || !target) return;
    restoreTo.current = undefined;
    const frame = requestAnimationFrame(() => {
      if (document.activeElement && document.activeElement !== document.body) return;
      const column = columns.findIndex((item) => item.id === target.columnId) + 1;
      grid.current
        ?.querySelector<HTMLElement>(`[data-row-key="${CSS.escape(target.rowId)}"] [data-grid-col="${column}"]`)
        ?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [open, columns]);
  const rows = useMemo(() => {
    const rowPatches = patches.key === listKey ? patches.rows : {};
    return pages.items.map((item) => {
      const patch = rowPatches[item.row.id];
      if (!patch) return item;
      return {
        ...item,
        relationSetVersion: patch.relationSetVersion,
        cells: item.cells.map((cell) => patch.cells[cell.columnId] ?? cell),
      };
    });
  }, [pages.items, patches, listKey]);
  const patchedRows = useMemo(() => new Map(rows.map((item) => [item.row.id, item])), [rows]);

  /** Re-reads the page where the cell alone cannot be; the fresh rows replace the patched cells. */
  const reloadRows = useCallback(() => {
    reloadPending.current = true;
    pages.reload();
  }, [pages]);

  /** Re-reads one cell after a write, so the rest of the matrix keeps its place and data. */
  const refreshCell = useCallback(
    async (row: RelationMatrixRow, columnId: string) => {
      try {
        // The row is found by seeking its name in name order, without the search or state filter
        // that might now exclude it; same-named rows sit together, so one short page holds it.
        const page = await api.relationMatrix({
          workspaceKey,
          applicationKey: application.key,
          viewKey: view.key,
          parentObjectId: query.parentObjectId,
          columnIds: [columnId],
          seek: row.row.name,
          pageSize: 20,
        });
        const fresh = page.items.find((item) => item.row.id === row.row.id);
        const cell = fresh?.cells.find((item) => item.columnId === columnId);
        if (!fresh || !cell) {
          reloadRows();
          return;
        }
        setPatches((previous) => {
          const rowsPatched = previous.key === listKey ? previous.rows : {};
          const current = rowsPatched[row.row.id];
          return {
            key: listKey,
            rows: {
              ...rowsPatched,
              [row.row.id]: {
                relationSetVersion: fresh.relationSetVersion,
                cells: { ...current?.cells, [columnId]: cell },
              },
            },
          };
        });
      } catch {
        reloadRows();
      }
    },
    [api, workspaceKey, application.key, view.key, query.parentObjectId, reloadRows, listKey],
  );

  if (!rowType || !columnType || !cellType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This matrix shows a record type that does not exist in the current model.</p>
      </div>
    );
  }

  const rowColumns = config.rowColumns.filter((field) => field !== "name");
  const possibleStates = MATRIX_STATES.filter((item) => item.key !== "inactive" || binding.conditional);
  const openRow = open && rows.find((item) => item.row.id === open.rowId);
  const openColumn = open && columns.find((item) => item.id === open.columnId);
  const openCell = openRow?.cells.find((item) => item.columnId === open?.columnId);
  const activeIndex = active ? rows.findIndex((item) => item.row.id === active.rowId) : -1;
  const tabRow = activeIndex >= 0 ? rows[activeIndex].row.id : rows[0]?.row.id;
  const tabColumn = activeIndex >= 0 ? Math.min(active!.column, columns.length) : 0;
  const filtered = Boolean(state);
  const rowsPlural = rowType.pluralName.toLowerCase();
  const cellHue = objectTypeHue(model, cellType.key);

  function openCellAt(rowId: string, columnId: string) {
    setOpen({ rowId, columnId });
  }

  /**
   * Closes the cell dialog and returns focus to its cell. A save disables the focused button, which
   * drops focus to the page before the dialog could restore it, so the lens restores it itself.
   */
  function closeCell() {
    restoreTo.current = open;
    setOpen(undefined);
  }

  function onGridKeyDown(event: KeyboardEvent<HTMLTableElement>) {
    const target = event.target as HTMLElement;
    const cell = target.closest<HTMLElement>("[data-grid-col]");
    const rowElement = cell?.closest<HTMLElement>("[data-row-key]");
    if (!cell || !rowElement || target !== cell) return;
    const column = Number(cell.dataset.gridCol);
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      cell.click();
      return;
    }
    // The rows scroll in their own window, which moves between them.
    const next = nextGridCell(
      event.key,
      { row: 0, column },
      { columns: columns.length + 1 },
      event.ctrlKey || event.metaKey,
    )?.column;
    if (next === undefined) return;
    event.preventDefault();
    const nextCell = rowElement.querySelector<HTMLElement>(`[data-grid-col="${next}"]`);
    nextCell?.focus();
    nextCell?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }

  const emptyMessage = filtered
    ? "No rows match these filters"
    : query.search
      ? "No results match this search"
      : `No ${rowsPlural} in this workspace yet`;

  /** The page's row with the cells re-read since the list loaded. */
  const current = (held: RelationMatrixRow) => patchedRows.get(held.row.id) ?? held;
  const dataColumns: DataColumn<RelationMatrixRow>[] = [
    {
      key: "row",
      label: rowType.name,
      rowHeader: true,
      alwaysShown: true,
      className: "matrix-row-header",
      headerProps: { "aria-colindex": 1 },
      cellProps: (held) => ({
        "aria-colindex": 1,
        "data-grid-col": 0,
        "data-row-focus": true,
        tabIndex: tabRow === held.row.id && tabColumn === 0 ? 0 : -1,
        onFocus: () => setActive({ rowId: held.row.id, column: 0 }),
        onClick: () =>
          onOpen({
            id: held.row.id,
            objectTypeKey: held.row.objectTypeKey,
            applicationKey: application.key,
            workspaceKey,
          }),
      }),
      cell: (held) => {
        const item = current(held);
        return (
          <>
            <span className="matrix-row-name">{item.row.name}</span>
            {rowColumns.map((field) => (
              <span key={field} className="matrix-row-field">
                <span className="visually-hidden">{attributeName(model, field)}: </span>
                {formatValue(item.row.fields[field])}
              </span>
            ))}
          </>
        );
      },
    },
    ...columns.map((column, position): DataColumn<RelationMatrixRow> => {
      const place = position + 1;
      return {
        key: column.id,
        label: columnLabel(column),
        alwaysShown: true,
        headerProps: { "aria-colindex": position + 2, title: column.name },
        header: (
          <>
            <span className="matrix-column-label">{columnLabel(column)}</span>
            {columnLabel(column) !== column.name && <span className="matrix-column-name">{column.name}</span>}
          </>
        ),
        cellProps: (held) => {
          const item = current(held);
          const cell = item.cells.find((candidate) => candidate.columnId === column.id);
          const attributes: CellAttributes = {
            role: "gridcell",
            "aria-colindex": place + 1,
            "data-grid-col": place,
            tabIndex: tabRow === item.row.id && tabColumn === place ? 0 : -1,
            onFocus: () => setActive({ rowId: item.row.id, column: place }),
          };
          if (!cell) return { ...attributes, tabIndex: -1 };
          return {
            ...attributes,
            className: `matrix-cell matrix-state-${cell.state}${cell.conflict ? " matrix-conflict" : ""}`,
            "aria-haspopup": "dialog",
            onClick: () => openCellAt(item.row.id, column.id),
          };
        },
        cell: (held) => (
          <MatrixCellBody
            cell={current(held).cells.find((candidate) => candidate.columnId === column.id)}
            cellHue={cellHue}
            cellFields={config.cellFields}
          />
        ),
      };
    }),
  ];

  return (
    <div>
      <PageHeader
        focusTitle
        icon={<HueTile hue={objectTypeHue(model, rowType.key)} icon={rowType.icon} size={40} />}
        title={pageTitle(model, application, view)}
        descriptionClassName="mapping-direction"
        description={
          <>
            <span>{rowType.pluralName}</span>
            <Icon name="arrow-right" size={14} />
            <span>{cellType.pluralName}</span>
            <span className="muted">by {columnType.name.toLowerCase()}</span>
          </>
        }
      />
      <ScopeBanner
        model={model}
        workspaceKey={workspaceKey}
        query={query}
        onQueryChange={onQueryChange}
        pluralName={rowType.pluralName}
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <div className="collection-toolbar object-toolbar">
          <DebouncedSearchField
            appliedValue={query.search}
            onApply={(search) => onQueryChange({ ...query, search, anchor: undefined })}
            placeholder={`Search ${rowsPlural}`}
          />
          <RelationMatrixFilter
            model={model}
            workspaceKey={workspaceKey}
            columnType={columnType}
            labelField={config.columnLabelField}
            shownColumns={columns}
            query={query}
            states={possibleStates}
            onChange={(next) => {
              setColumnCursor(undefined);
              onQueryChange({ ...query, ...next, anchor: undefined });
            }}
          />
          <label className="toolbar-switch matrix-hide-empty">
            <Switch label="Hide empty columns" checked={hideRequested} onChange={chooseHideEmpty} />
            <span>Hide empty columns</span>
            {columnIds?.length ? <span className="muted">No effect while columns are chosen in Filter</span> : null}
          </label>
          {!columnIds && (columnPage?.prev || columnPage?.next) && (
            <div className="matrix-column-paging" role="group" aria-label={`${columnType.pluralName} shown`}>
              <button
                type="button"
                className="secondary icon-button"
                aria-label={`Previous ${columnType.pluralName.toLowerCase()}`}
                disabled={!columnPage?.prev || pages.loading}
                onClick={() => setColumnCursor(columnPage?.prev ?? undefined)}
              >
                <Icon name="arrow-left" />
              </button>
              <button
                type="button"
                className="secondary icon-button"
                aria-label={`Next ${columnType.pluralName.toLowerCase()}`}
                disabled={!columnPage?.next || pages.loading}
                onClick={() => setColumnCursor(columnPage?.next ?? undefined)}
              >
                <Icon name="arrow-right" />
              </button>
            </div>
          )}
          {changeSet && (
            <StatusPill tone="changeSet" className="matrix-context">
              Saves to change set {changeSet.name ?? ""}
            </StatusPill>
          )}
        </div>
        {hideEmpty && columnPage?.key === columnsKey && columnPage.emptyHidden > 0 && (
          <p className="matrix-hidden-columns" role="status">
            {columnPage.emptyHidden} empty {columnPage.emptyHidden === 1 ? "column" : "columns"} hidden ·{" "}
            <button type="button" className="ghost" onClick={() => chooseHideEmpty(false)}>
              Show all
            </button>
          </p>
        )}
        <MatrixChips
          query={query}
          columns={columns}
          onChange={(next) => onQueryChange({ ...query, ...next, anchor: undefined })}
        />
        <ul className="matrix-legend" aria-label="Cell states">
          {possibleStates.map((item) => (
            <li key={item.key}>
              <StateMark state={item.key} />
              <span>
                <strong>{item.label}</strong> {item.description(binding)}
              </span>
            </li>
          ))}
          {binding.scoped && (
            <li>
              <StateMark state="several" conflict />
              <span>
                <strong>Conflict</strong> more than one where only one is allowed
              </span>
            </li>
          )}
        </ul>
        {!actions.length && (
          <p className="matrix-read-only muted-text">
            <Icon name="info" size={14} /> {publication ? "Publications are read-only." : "This matrix is read-only."}
          </p>
        )}
        {pages.error && <InlineError message={pages.error} onRetry={pages.retry} />}
        {(!pages.error || rows.length > 0) && (
          <div ref={grid}>
            <DataTable<RelationMatrixRow>
              columns={dataColumns}
              list={pages}
              rowKey={(item) => item.row.id}
              columnWidths={display.widths}
              onColumnWidths={display.setWidths}
              tableAttributes={{
                role: "grid",
                "aria-readonly": actions.length ? undefined : true,
                "aria-colcount": columns.length + 1,
                onKeyDown: onGridKeyDown,
              }}
              label={`${view.name} matrix`}
              noun={["row", "rows"]}
              pageSize={pageSize}
              onAnchorChange={onAnchorChange}
              className="matrix-table"
              oneLine
              emptyMessage={emptyMessage}
            />
          </div>
        )}
        {!pages.loading && !pages.error && rows.length > 0 && columns.length === 0 && (
          <p className="muted-text matrix-no-columns">
            No {columnType.pluralName.toLowerCase()} in this workspace yet, so there are no cells to show.
          </p>
        )}
      </Card>
      {openRow && openColumn && openCell && (
        <RelationMatrixCellDialog
          key={`${openRow.row.id}:${openColumn.id}`}
          model={model}
          application={application}
          view={view}
          workspaceKey={workspaceKey}
          row={openRow}
          column={openColumn}
          cell={openCell}
          actions={actions}
          binding={binding}
          onClose={closeCell}
          onRefresh={() => refreshCell(openRow, openColumn.id)}
          onSaved={async () => {
            await refreshCell(openRow, openColumn.id);
            closeCell();
          }}
          onOpenRecord={(id, objectTypeKey) =>
            onOpen({ id, objectTypeKey, applicationKey: application.key, workspaceKey })
          }
        />
      )}
    </div>
  );
}

/** What a matrix cell shows: its state and its first record, with how many more. */
function MatrixCellBody({
  cell,
  cellHue,
  cellFields,
}: {
  cell: RelationMatrixCell | undefined;
  /** The cell records' type colour: a record in the matrix's data is a chip (ADR-040). */
  cellHue: Hue | undefined;
  cellFields: readonly string[];
}) {
  if (!cell) return null;
  const summary = cell.records[0];
  const more = cell.recordCount - (summary ? 1 : 0);
  return (
    <>
      <span className="matrix-cell-state">
        <StateMark state={cell.state} conflict={cell.conflict} />
        <span>{stateLabel(cell.state as MatrixStateKey, cell.conflict, cell.recordCount)}</span>
      </span>
      {summary && (
        <span className="matrix-cell-record">
          <RecordChip hue={cellHue}>{cellRecordLabel(summary, cellFields)}</RecordChip>
          {more > 0 && <span className="muted">+{more}</span>}
        </span>
      )}
    </>
  );
}

function MatrixChips({
  query,
  columns,
  onChange,
}: {
  query: ViewComponentProps["query"];
  columns: RelationMatrixColumn[];
  onChange: (next: Pick<ViewComponentProps["query"], "matrixColumnIds" | "matrixState">) => void;
}) {
  const columnIds = query.matrixColumnIds;
  if (!columnIds?.length) return null;
  const names = columnIds.map((id) => {
    const column = columns.find((item) => item.id === id);
    return column ? columnLabel(column) : "…";
  });
  return (
    <div className="filter-chips" aria-label="Applied filters">
      {query.matrixState && (
        <button
          className="filter-chip"
          aria-label={`Remove cell state ${stateLabel(query.matrixState, false)}`}
          onClick={() => onChange({ matrixColumnIds: columnIds, matrixState: undefined })}
        >
          <span>
            Cell <em>is</em> {stateLabel(query.matrixState, false)}
          </span>
          <Icon name="close" size={13} />
        </button>
      )}
      <button
        className="filter-chip"
        aria-label={`Remove chosen columns ${names.join(", ")}`}
        onClick={() => onChange({ matrixColumnIds: undefined, matrixState: undefined })}
      >
        <span>
          Columns <em>are</em>{" "}
          {names.length > 3 ? `${names.slice(0, 3).join(", ")} and ${names.length - 3} more` : names.join(", ")}
        </span>
        <Icon name="close" size={13} />
      </button>
    </div>
  );
}
