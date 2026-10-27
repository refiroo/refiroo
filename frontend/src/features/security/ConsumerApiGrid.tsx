/**
 * The consumer APIs a grant dialog offers, as a grid (0.12 U9): a row per consumer API, a column per
 * workspace, a tick per grant. A row or column heading ticks the whole line, Shift extends a range
 * from the last tick, and what the holder already has is shown ticked and locked. A workspace whose
 * model does not declare an API has no tick for it (workspaces may run different models).
 */

import { useMemo, useRef } from "react";
import type { GrantOptions } from "@/types";
import { Skeleton } from "@/ui/Skeleton";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { cellKey } from "./grantPlan";

export interface GridWorkspace {
  key: string;
  label: string;
}

/** A workspace's options, "error" when they could not be read, nothing while they load. */
export type GridOptions = Readonly<Record<string, GrantOptions | "error" | undefined>>;

type State = "all" | "some" | "none";

const stateOf = (cells: readonly string[], ticked: ReadonlySet<string>): State => {
  const count = cells.filter((cell) => ticked.has(cell)).length;
  return count === 0 ? "none" : count === cells.length ? "all" : "some";
};

export function ConsumerApiGrid({
  workspaces,
  options,
  held,
  ticked,
  onChange,
}: {
  workspaces: readonly GridWorkspace[];
  options: GridOptions;
  held: ReadonlySet<string>;
  ticked: ReadonlySet<string>;
  onChange: (ticked: Set<string>) => void;
}) {
  const last = useRef<{ row: number; column: number }>(undefined);

  const apis = useMemo(() => {
    const found = new Map<string, string>();
    for (const workspace of workspaces) {
      const loaded = options[workspace.key];
      if (loaded && loaded !== "error")
        for (const item of loaded.consumerApis) if (!found.has(item.key)) found.set(item.key, item.name);
    }
    return [...found].map(([key, name]) => ({ key, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [workspaces, options]);

  const declared = (apiKey: string, workspaceKey: string) => {
    const loaded = options[workspaceKey];
    return !!loaded && loaded !== "error" && loaded.consumerApis.some((item) => item.key === apiKey);
  };
  /** The cells that can be ticked: declared by the workspace's model and not already held. */
  const open = (apiKey: string, workspaceKey: string) =>
    declared(apiKey, workspaceKey) && !held.has(cellKey(apiKey, workspaceKey));

  const rowCells = (apiKey: string) =>
    workspaces.filter((workspace) => open(apiKey, workspace.key)).map((workspace) => cellKey(apiKey, workspace.key));
  const columnCells = (workspaceKey: string) =>
    apis.filter((api) => open(api.key, workspaceKey)).map((api) => cellKey(api.key, workspaceKey));
  const allCells = apis.flatMap((api) => rowCells(api.key));

  /** Tick the cells, or untick them all when every one is already ticked. */
  function toggle(cells: readonly string[]) {
    if (!cells.length) return;
    const next = new Set(ticked);
    const unset = stateOf(cells, ticked) === "all";
    for (const cell of cells) {
      if (unset) next.delete(cell);
      else next.add(cell);
    }
    onChange(next);
  }

  function toggleCell(row: number, column: number, extend: boolean) {
    const api = apis[row];
    const workspace = workspaces[column];
    if (!api || !workspace) return;
    const next = new Set(ticked);
    const set = !ticked.has(cellKey(api.key, workspace.key));
    const from = extend && last.current ? last.current : { row, column };
    for (let r = Math.min(from.row, row); r <= Math.max(from.row, row); r++) {
      for (let c = Math.min(from.column, column); c <= Math.max(from.column, column); c++) {
        const target = apis[r];
        const place = workspaces[c];
        if (!target || !place || !open(target.key, place.key)) continue;
        if (set) next.add(cellKey(target.key, place.key));
        else next.delete(cellKey(target.key, place.key));
      }
    }
    last.current = { row, column };
    onChange(next);
  }

  const loading = workspaces.some((workspace) => options[workspace.key] === undefined);
  if (!apis.length && loading) return <Skeleton label="Loading the consumer APIs" lines={3} />;
  if (!apis.length)
    return (
      <p className="admin-hint">
        {workspaces.length === 1
          ? `${workspaces[0]?.label}’s model declares no consumer API.`
          : "No workspace’s model declares a consumer API."}
      </p>
    );

  return (
    <div className="grant-table-wrap">
      <table className="grant-table grant-grid">
        <thead>
          <tr>
            <th className="grant-first" scope="col">
              <span className="grant-line">
                <SelectionCheckbox
                  label="All consumer APIs in all workspaces"
                  state={stateOf(allCells, ticked)}
                  onSelect={() => toggle(allCells)}
                />
                Consumer API
              </span>
            </th>
            {workspaces.map((workspace) => (
              <th key={workspace.key} scope="col">
                <span className="grant-stack">
                  {workspace.label}
                  <SelectionCheckbox
                    label={`All consumer APIs in ${workspace.label}`}
                    state={stateOf(columnCells(workspace.key), ticked)}
                    onSelect={() => toggle(columnCells(workspace.key))}
                  />
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {apis.map((api, row) => (
            <tr key={api.key}>
              <th scope="row" className="grant-first">
                <span className="grant-line">
                  <SelectionCheckbox
                    label={`${api.name} in all workspaces`}
                    state={stateOf(rowCells(api.key), ticked)}
                    onSelect={() => toggle(rowCells(api.key))}
                  />
                  <span>
                    {api.name}
                    <small>{api.key}</small>
                  </span>
                </span>
              </th>
              {workspaces.map((workspace, column) => {
                const key = cellKey(api.key, workspace.key);
                const loaded = options[workspace.key];
                if (loaded === undefined)
                  return (
                    <td key={workspace.key} className="grant-grid-note">
                      …
                    </td>
                  );
                if (loaded === "error")
                  return (
                    <td key={workspace.key} className="grant-grid-note">
                      unavailable
                    </td>
                  );
                if (!declared(api.key, workspace.key))
                  return (
                    <td key={workspace.key} className="grant-grid-note">
                      not in this model
                    </td>
                  );
                if (held.has(key))
                  return (
                    <td key={workspace.key} className="grant-grid-held">
                      <input
                        type="checkbox"
                        className="selection-checkbox"
                        checked
                        disabled
                        readOnly
                        aria-label={`${api.name} in ${workspace.label}: already granted`}
                      />
                    </td>
                  );
                return (
                  <td key={workspace.key} className={ticked.has(key) ? "grant-grid-on" : undefined}>
                    <SelectionCheckbox
                      label={`${api.name} in ${workspace.label}`}
                      state={ticked.has(key) ? "all" : "none"}
                      onSelect={(extend) => toggleCell(row, column, extend)}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
