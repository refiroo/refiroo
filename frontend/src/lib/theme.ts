/**
 * Colour theme preference. "system" follows the operating system; "light" and "dark" pin the
 * theme through `data-theme` on the document element, which the design tokens key on. The same
 * storage key is read by the inline script in index.html so the first paint uses the saved theme.
 */

import { useState } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "rdm:theme:v1";

const isTheme = (value: unknown): value is ThemePreference =>
  value === "system" || value === "light" || value === "dark";

export function applyTheme(theme: ThemePreference) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
}

export function useThemePreference() {
  const [theme, setTheme] = useState<ThemePreference>(() => readLocalPreference(THEME_STORAGE_KEY, "system", isTheme));
  return {
    theme,
    setTheme: (next: ThemePreference) => {
      setTheme(next);
      writeLocalPreference(THEME_STORAGE_KEY, next);
      applyTheme(next);
    },
  };
}
