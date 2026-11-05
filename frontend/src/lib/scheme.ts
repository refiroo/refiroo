/**
 * The colour theme (package TH): Normal, or Website purple, chosen on Settings › Appearance and saved in this
 * browser. It is independent of the light and dark mode (`theme.ts`) and of the type palette (`palette.ts`):
 * Website purple sets `data-scheme="purple"` on the document element, which the design tokens key on, and Normal
 * sets nothing. The inline script in index.html applies the saved choice before the first paint; the guide and
 * the API reference an instance serves read the same key, and a choice made there reaches an open application
 * tab through the storage event.
 */

import { useSyncExternalStore } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type ColourScheme = "normal" | "purple";

export const SCHEME_STORAGE_KEY = "rdm:scheme:v1";

const isScheme = (value: unknown): value is ColourScheme => value === "normal" || value === "purple";

/** The browser's address-bar colour for each theme, light and dark; Normal's are index.html's own. */
const THEME_COLOURS: Record<ColourScheme, { light: string; dark: string }> = {
  normal: { light: "#f5f7f6", dark: "#101614" },
  purple: { light: "#fbf8f1", dark: "#0e1130" },
};

export function applyScheme(scheme: ColourScheme) {
  if (scheme === "purple") document.documentElement.dataset.scheme = "purple";
  else delete document.documentElement.dataset.scheme;
  for (const [mode, content] of Object.entries(THEME_COLOURS[scheme])) {
    document
      .querySelector(`meta[name="theme-color"][media="(prefers-color-scheme: ${mode})"]`)
      ?.setAttribute("content", content);
  }
}

let current: ColourScheme | undefined;
const listeners = new Set<() => void>();

function snapshot(): ColourScheme {
  current ??= readLocalPreference(SCHEME_STORAGE_KEY, "normal", isScheme);
  return current;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Forgets the remembered choice so the next read is from storage; for tests. */
export function resetSchemePreference() {
  current = undefined;
}

export function useSchemePreference() {
  const scheme = useSyncExternalStore(subscribe, snapshot);
  return {
    scheme,
    setScheme: (next: ColourScheme) => {
      current = next;
      writeLocalPreference(SCHEME_STORAGE_KEY, next);
      applyScheme(next);
      listeners.forEach((listener) => listener());
    },
  };
}

// The documentation and the API reference write the same key: a choice made there reaches an open application
// tab through the storage event.
if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key !== null && event.key !== SCHEME_STORAGE_KEY) return;
    current = undefined;
    applyScheme(snapshot());
    listeners.forEach((listener) => listener());
  });
}
