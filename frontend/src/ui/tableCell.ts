/**
 * What a table row tells the cells drawn in it (0.11 X6), for `ui/DataTable`.
 *
 * `CellRoom`: the content width of the cell's column, measured once per column by the table, so a
 * cell that fits its content to its width (`ui/RelatedRecordChips`) need not measure itself.
 * Undefined where the table has not measured (its narrow layout sizes columns to their content).
 *
 * `RowActive`: whether the row is the one the pointer is over or that holds focus. A cell's edit
 * controls (`ui/EditInPlace`) are drawn in that row only, so the rows scrolled past are plain values;
 * every cell drawing its own hidden buttons made scrolling stutter (the user, 2026-10-19). Outside a
 * table, and on a screen without hover, every row is active, as before.
 */

import { createContext } from "react";

export const CellRoom = createContext<number | undefined>(undefined);

export const RowActive = createContext(true);

/** The row the pointer is over and the row holding focus, which a row reads without the table redrawing. */
export interface ActiveRows {
  isActive: (rowKey: string) => boolean;
  subscribe: (listener: () => void) => () => void;
  setHovered: (rowKey: string | undefined) => void;
  setFocused: (rowKey: string | undefined) => void;
}

export function activeRows(): ActiveRows {
  let hovered: string | undefined;
  let focused: string | undefined;
  const listeners = new Set<() => void>();
  const notify = () => listeners.forEach((listener) => listener());
  return {
    isActive: (rowKey) => rowKey === hovered || rowKey === focused,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setHovered: (rowKey) => {
      if (rowKey === hovered) return;
      hovered = rowKey;
      notify();
    },
    setFocused: (rowKey) => {
      if (rowKey === focused) return;
      focused = rowKey;
      notify();
    },
  };
}

/** Whether the device has a pointer that hovers; unknown (no `matchMedia`) counts as none. */
export const canHover = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(hover: hover)").matches;
