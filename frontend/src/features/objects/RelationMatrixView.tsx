/**
 * The `relationMatrix` lens (Base 0.8 A4): the view's rows down the side, records of an ancestor
 * type across the top, and in each cell the row's related records under that column record. Every
 * label, field and action comes from the view and its binding; nothing here names a starter type.
 *
 * Rows scroll through `useCursorWindow` (ADR-030); columns are either the ones the user chose or a
 * page of the column type, paged sideways with the column cursor (D10). A cell opens a dialog that
 * offers only the view's `cellActions`, and a save re-reads that one cell.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { Icon } from "@/ui/Icon";
import { formatValue } from "@/ui/formatValue";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { RelationMatrixCellDialog } from "@/features/objects/RelationMatrixCellDialog";
import { RelationMatrixFilter } from "@/features/objects/RelationMatrixFilter";
import {
  columnLabel,
  matrixBinding,
  MATRIX_STATES,
  StateMark,
  stateLabel,
  type MatrixStateKey,
} from "@/features/objects/relationMatrixStates";
import { CollectionScope } from "@/features/objects/CollectionScope";
import type {
  RelationMatrixCell,
  RelationMatrixColumn,
  RelationMatrixRow,
  RelationMatrixViewDefinition,
} from "@/types";
import type { ViewComponentProps } from "./views/types";

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
}: ViewComponentProps) {
  const view = rawView as RelationMatrixViewDefinition;
  const { config } = view;
  const api = useDataApi();
  const { changeSet, publication } = useWorkspaceData();
  const [search, setSearch] = useState(query.search);
  const [columnCursor, setColumnCursor] = useState<string>();
  const [open, setOpen] = useState<{ rowId: string; columnId: string }>();
  const [active, setActive] = useState<{ rowId: string; column: number }>();
  const [patches, setPatches] = useState<{ key: string; rows: Record<string, RowPatch> }>({ key: "", rows: {} });
  const grid = useRef<HTMLTableElement>(null);
  const restoreTo = useRef<{ rowId: string; columnId: string } | undefined>(undefined);

  const rowType = objectTypeFor(model, config.rowObjectTypeKey);
  const columnType = objectTypeFor(model, config.columnObjectTypeKey);
  const cellType = objectTypeFor(model, config.cellObjectTypeKey);
  const binding = matrixBinding(model, config);
  const actions = readOnly || publication ? [] : (config.cellActions ?? []);
  const columnIds = query.matrixColumnIds;
  const state = columnIds?.length ? query.matrixState : undefined;
  const pageSize = query.pageSize || config.pageSize;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const trimmed = search.trim();
      if (trimmed !== query.search) onQueryChange({ ...query, search: trimmed, anchor: undefined });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, query, onQueryChange]);

  // The columns come with each page; they depend only on what selects them, so every page of one
  // list carries the same ones and a late page of an earlier list is ignored.
  const columnsKey = JSON.stringify([columnIds ?? null, columnIds ? null : (columnCursor ?? null), changeSet?.id]);
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
              state,
              ...selector,
              pageSize,
            })
            .then((page) => {
              if (requestKey === columnsKeyRef.current)
                setColumnPage({
                  key: requestKey,
                  columns: page.columns,
                  next: page.columnsNextCursor ?? null,
                  prev: page.columnsPrevCursor ?? null,
                });
              return page;
            });
        }
      : null,
    listDeps,
    { anchor: query.anchor, refreshToken },
  );
  const columns = useMemo(() => (columnPage?.key === columnsKey ? columnPage.columns : []), [columnPage, columnsKey]);
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
          pages.reload();
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
        pages.reload();
      }
    },
    [api, workspaceKey, application.key, view.key, query.parentObjectId, pages, listKey],
  );

  if (!rowType || !columnType || !cellType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This matrix references an object type that does not exist in the active model.</p>
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
    const last = columns.length;
    let next: number | undefined;
    if (event.key === "ArrowRight") next = Math.min(last, column + 1);
    else if (event.key === "ArrowLeft") next = Math.max(0, column - 1);
    else if (event.key === "Home" && !event.ctrlKey && !event.metaKey) next = 0;
    else if (event.key === "End" && !event.ctrlKey && !event.metaKey) next = last;
    else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      cell.click();
      return;
    }
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

  return (
    <div>
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="matrix" size={20} />
          </span>
          <div>
            <h1 tabIndex={-1}>{view.name}</h1>
            <p className="mapping-direction">
              <span>{rowType.pluralName}</span>
              <Icon name="arrow-right" size={14} />
              <span>{cellType.pluralName}</span>
              <span className="muted">by {columnType.name.toLowerCase()}</span>
            </p>
          </div>
        </div>
      </header>
      {query.parentObjectId && (
        <div className="scope-banner">
          <CollectionScope
            model={model}
            workspaceKey={workspaceKey}
            parentObjectId={query.parentObjectId}
            parentObjectTypeKey={query.parentObjectTypeKey}
          />
          <button
            className="ghost"
            onClick={() =>
              onQueryChange({ ...query, parentObjectId: undefined, parentObjectTypeKey: undefined, anchor: undefined })
            }
          >
            Show all {rowsPlural}
          </button>
        </div>
      )}
      {lenses}
      <section className="surface collection-surface">
        <div className="collection-toolbar object-toolbar">
          <label className="search-box">
            <Icon name="search" />
            <input
              aria-label="Search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={`Search ${rowsPlural}`}
            />
          </label>
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
          {changeSet && <span className="pill matrix-context">Saves to change set {changeSet.name ?? ""}</span>}
        </div>
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
          <ScrollWindow
            list={pages}
            label={`${view.name} matrix`}
            noun={["row", "rows"]}
            pageSize={pageSize}
            onAnchorChange={onAnchorChange}
            className="table-wrap matrix-table"
          >
            <table
              ref={grid}
              role="grid"
              aria-busy={pages.loading || undefined}
              aria-readonly={actions.length ? undefined : true}
              aria-rowcount={pages.totalCount !== null && rows.length > 0 ? pages.totalCount + 1 : undefined}
              aria-colcount={columns.length + 1}
              onKeyDown={onGridKeyDown}
            >
              <caption className="visually-hidden">
                {view.name}: {rowsPlural} by {columnType.name.toLowerCase()}
              </caption>
              <thead>
                <tr aria-rowindex={1}>
                  <th scope="col" className="matrix-row-header" aria-colindex={1}>
                    {rowType.name}
                  </th>
                  {columns.map((column, index) => (
                    <th key={column.id} scope="col" aria-colindex={index + 2} title={column.name}>
                      <span className="matrix-column-label">{columnLabel(column)}</span>
                      {columnLabel(column) !== column.name && <span className="matrix-column-name">{column.name}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pages.loading && rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} className="empty-row">
                      Loading…
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} className="empty-row">
                      {emptyMessage}
                    </td>
                  </tr>
                ) : (
                  rows.map((item, position) => (
                    <tr
                      key={item.row.id}
                      data-row-key={item.row.id}
                      data-row-index={pages.startIndex + position}
                      aria-rowindex={pages.startIndex + position + 2}
                    >
                      <th
                        scope="row"
                        className="matrix-row-header"
                        aria-colindex={1}
                        data-grid-col={0}
                        data-row-focus
                        tabIndex={tabRow === item.row.id && tabColumn === 0 ? 0 : -1}
                        onFocus={() => setActive({ rowId: item.row.id, column: 0 })}
                        onClick={() =>
                          onOpen({
                            id: item.row.id,
                            objectTypeKey: item.row.objectTypeKey,
                            applicationKey: application.key,
                            workspaceKey,
                          })
                        }
                      >
                        <span className="matrix-row-name">{item.row.name}</span>
                        {rowColumns.map((field) => (
                          <span key={field} className="matrix-row-field">
                            <span className="visually-hidden">{attributeName(model, field)}: </span>
                            {formatValue(item.row.fields[field])}
                          </span>
                        ))}
                      </th>
                      {columns.map((column, index) => {
                        const cell = item.cells.find((candidate) => candidate.columnId === column.id);
                        return (
                          <MatrixCell
                            key={column.id}
                            cell={cell}
                            column={index + 1}
                            tabbable={tabRow === item.row.id && tabColumn === index + 1}
                            onFocus={() => setActive({ rowId: item.row.id, column: index + 1 })}
                            onOpen={() => cell && openCellAt(item.row.id, column.id)}
                          />
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </ScrollWindow>
        )}
        {!pages.loading && !pages.error && rows.length > 0 && columns.length === 0 && (
          <p className="muted-text matrix-no-columns">
            No {columnType.pluralName.toLowerCase()} in this workspace yet, so there are no cells to show.
          </p>
        )}
      </section>
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

function MatrixCell({
  cell,
  column,
  tabbable,
  onFocus,
  onOpen,
}: {
  cell: RelationMatrixCell | undefined;
  column: number;
  tabbable: boolean;
  onFocus: () => void;
  onOpen: () => void;
}) {
  if (!cell)
    return <td role="gridcell" aria-colindex={column + 1} data-grid-col={column} tabIndex={-1} onFocus={onFocus} />;
  const summary = cell.records[0];
  const more = cell.recordCount - (summary ? 1 : 0);
  return (
    <td
      role="gridcell"
      aria-colindex={column + 1}
      data-grid-col={column}
      tabIndex={tabbable ? 0 : -1}
      className={`matrix-cell matrix-state-${cell.state}${cell.conflict ? " matrix-conflict" : ""}`}
      aria-haspopup="dialog"
      onFocus={onFocus}
      onClick={onOpen}
    >
      <span className="matrix-cell-state">
        <StateMark state={cell.state} conflict={cell.conflict} />
        <span>{stateLabel(cell.state as MatrixStateKey, cell.conflict, cell.recordCount)}</span>
      </span>
      {summary && (
        <span className="matrix-cell-record">
          {summary.name}
          {more > 0 && <span className="muted"> +{more}</span>}
        </span>
      )}
    </td>
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
