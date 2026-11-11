/**
 * Colour theme preference. "system" follows the operating system; "light" and "dark" pin the
 * theme through `data-theme` on the document element, which the design tokens key on. The same
 * storage key is read by public/theme-init.js (linked from index.html) so the first paint uses the saved theme.
 *
 * The account popover and Settings › Appearance can be open together, so the choice is one store
 * that every user of the hook follows.
 */

import { useSyncExternalStore } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "rdm:theme:v1";

const isTheme = (value: unknown): value is ThemePreference =>
  value === "system" || value === "light" || value === "dark";

export function applyTheme(theme: ThemePreference) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
}

let current: ThemePreference | undefined;
const listeners = new Set<() => void>();

function snapshot(): ThemePreference {
  current ??= readLocalPreference(THEME_STORAGE_KEY, "system", isTheme);
  return current;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Forgets the remembered choice so the next read is from storage; for tests. */
export function resetThemePreference() {
  current = undefined;
}

export function useThemePreference() {
  const theme = useSyncExternalStore(subscribe, snapshot);
  return {
    theme,
    setTheme: (next: ThemePreference) => {
      current = next;
      writeLocalPreference(THEME_STORAGE_KEY, next);
      applyTheme(next);
      listeners.forEach((listener) => listener());
    },
  };
}

// The documentation and the API reference write the same key (HD): a choice made there reaches an open
// application tab through the storage event.
if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key !== null && event.key !== THEME_STORAGE_KEY) return;
    current = undefined;
    applyTheme(snapshot());
    listeners.forEach((listener) => listener());
  });
}
