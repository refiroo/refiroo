/**
 * The selection of one collection's records (0.9 K1) over `lib/recordSelection`.
 *
 * The selection belongs to the list it was made over (D108): a new `listKey` (the search, the
 * filters and the scope) starts from nothing, while sorting, scrolling and opening records keep it.
 * "All matching" is refused over `maxItems`, the most one bulk change may hold (D104); the refusal
 * is kept to be explained until the selection or the list changes.
 */

import { useState } from "react";
import {
  emptySelection,
  isSelected,
  loadedState,
  range,
  selectedCount,
  selectMatching,
  toggle,
  toggleLoaded,
  withVersions,
  withoutDeleted,
  type RecordSelection,
  type SelectableRow,
} from "@/lib/recordSelection";

interface Held {
  listKey: string;
  selection: RecordSelection;
  /** How many records matched when "all matching" was refused. */
  refusedTotal?: number;
}

export function useRecordSelection(listKey: string, rows: readonly SelectableRow[], maxItems: number) {
  const [held, setHeld] = useState<Held>({ listKey, selection: emptySelection });
  const current: Held = held.listKey === listKey ? held : { listKey, selection: emptySelection };
  const { selection } = current;

  const change = (next: (selection: RecordSelection) => RecordSelection) =>
    setHeld((previous) => ({
      listKey,
      selection: next(previous.listKey === listKey ? previous.selection : emptySelection),
    }));

  return {
    selection,
    count: selectedCount(selection),
    refusedTotal: current.refusedTotal,
    loaded: loadedState(selection, rows),
    isSelected: (id: string) => isSelected(selection, id),
    toggle: (row: SelectableRow, extend: boolean) =>
      change((previous) => (extend ? range(previous, rows, row) : toggle(previous, row))),
    toggleLoaded: () => change((previous) => toggleLoaded(previous, rows)),
    /** Selects the loaded rows, keeping what is selected (Cmd+A over a list that is all loaded). */
    selectLoaded: () =>
      change((previous) => (loadedState(previous, rows) === "all" ? previous : toggleLoaded(previous, rows))),
    /** Selects every record the list matches, or refuses it over `maxItems`. */
    selectMatching: (total: number) =>
      total > maxItems ? setHeld({ listKey, selection, refusedTotal: total }) : change(() => selectMatching(total)),
    clear: () => change(() => emptySelection),
    /** The versions a bulk change left on the records it wrote (0.9 K2, D118). */
    takeVersions: (versions: ReadonlyMap<string, number>) => change((previous) => withVersions(previous, versions)),
    /** The records a bulk delete removed leave the selection (0.9 K2b, D125). */
    dropDeleted: (deleted: ReadonlySet<string>) => change((previous) => withoutDeleted(previous, deleted)),
  };
}
