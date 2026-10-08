/**
 * The records selected in a collection (0.9 K1), as pure functions over an immutable state.
 *
 * A selection is either records picked by hand, each with the version the row showed (D102), or
 * "all matching": the collection's search, filters and scope, with records unchecked since kept as
 * exceptions (D103, D109). The matching records and their versions are read when an action runs,
 * so here "all matching" holds only how many matched and what was left out.
 *
 * A range covers the rows loaded (D104): `rows` is always the loaded window, in its order.
 */

export interface SelectableRow {
  id: string;
  version: number;
}

export type RecordSelection =
  | { mode: "ids"; ids: ReadonlyMap<string, number>; anchor?: string }
  | { mode: "matching"; total: number; except: ReadonlySet<string>; anchor?: string };

export const emptySelection: RecordSelection = { mode: "ids", ids: new Map() };

export function isSelected(selection: RecordSelection, id: string): boolean {
  return selection.mode === "ids" ? selection.ids.has(id) : !selection.except.has(id);
}

export function selectedCount(selection: RecordSelection): number {
  return selection.mode === "ids" ? selection.ids.size : Math.max(0, selection.total - selection.except.size);
}

/** Sets the given rows to `selected`; a selection left with nothing becomes empty. */
function setRows(
  selection: RecordSelection,
  rows: readonly SelectableRow[],
  selected: boolean,
  anchor: string | undefined,
): RecordSelection {
  if (selection.mode === "ids") {
    const ids = new Map(selection.ids);
    for (const row of rows) {
      if (selected) ids.set(row.id, row.version);
      else ids.delete(row.id);
    }
    return { mode: "ids", ids, anchor };
  }
  const except = new Set(selection.except);
  for (const row of rows) {
    if (selected) except.delete(row.id);
    else except.add(row.id);
  }
  const next: RecordSelection = { mode: "matching", total: selection.total, except, anchor };
  return selectedCount(next) === 0 ? { ...emptySelection, anchor } : next;
}

/** Adds or removes one row; it becomes the anchor of the next range. */
export function toggle(selection: RecordSelection, row: SelectableRow): RecordSelection {
  return setRows(selection, [row], !isSelected(selection, row.id), row.id);
}

/**
 * Sets every loaded row from the anchor to `row` to the state the clicked row takes, as a click on
 * it would. Without an anchor among the loaded rows it is a toggle of `row` alone.
 */
export function range(selection: RecordSelection, rows: readonly SelectableRow[], row: SelectableRow): RecordSelection {
  const from = rows.findIndex((candidate) => candidate.id === selection.anchor);
  const to = rows.findIndex((candidate) => candidate.id === row.id);
  if (from < 0 || to < 0) return toggle(selection, row);
  const covered = rows.slice(Math.min(from, to), Math.max(from, to) + 1);
  return setRows(selection, covered, !isSelected(selection, row.id), row.id);
}

/** The header checkbox's state over the loaded rows. */
export function loadedState(selection: RecordSelection, rows: readonly SelectableRow[]): "all" | "some" | "none" {
  const count = rows.filter((row) => isSelected(selection, row.id)).length;
  if (rows.length > 0 && count === rows.length) return "all";
  return count > 0 ? "some" : "none";
}

/**
 * The header checkbox: selects the loaded rows, or, when every one is selected, clears them. Under
 * "all matching" clearing them clears the whole selection, since the header then stands for it.
 */
export function toggleLoaded(selection: RecordSelection, rows: readonly SelectableRow[]): RecordSelection {
  if (loadedState(selection, rows) !== "all") return setRows(selection, rows, true, selection.anchor);
  return selection.mode === "matching" ? emptySelection : setRows(selection, rows, false, undefined);
}

export function selectMatching(total: number): RecordSelection {
  return total > 0 ? { mode: "matching", total, except: new Set() } : emptySelection;
}
