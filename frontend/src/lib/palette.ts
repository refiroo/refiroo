/**
 * The type palette (U-D13): B (magenta and olive in slots 3 and 4, the default) or A (plum and
 * gold), chosen on Settings › Appearance and saved in this browser. A sets `data-palette="a"` on
 * the document element, which the design tokens key on; public/theme-init.js (linked from index.html) applies the
 * saved choice before the first paint, as it does the theme.
 */

import { useSyncExternalStore } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type TypePalette = "a" | "b";

export const PALETTE_STORAGE_KEY = "rdm:palette:v1";

const isPalette = (value: unknown): value is TypePalette => value === "a" || value === "b";

export function applyPalette(palette: TypePalette) {
  if (palette === "a") document.documentElement.dataset.palette = "a";
  else delete document.documentElement.dataset.palette;
}

let current: TypePalette | undefined;
const listeners = new Set<() => void>();

function snapshot(): TypePalette {
  current ??= readLocalPreference(PALETTE_STORAGE_KEY, "b", isPalette);
  return current;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Forgets the remembered choice so the next read is from storage; for tests. */
export function resetPalettePreference() {
  current = undefined;
}

export function usePalettePreference() {
  const palette = useSyncExternalStore(subscribe, snapshot);
  return {
    palette,
    setPalette: (next: TypePalette) => {
      current = next;
      writeLocalPreference(PALETTE_STORAGE_KEY, next);
      applyPalette(next);
      listeners.forEach((listener) => listener());
    },
  };
}
