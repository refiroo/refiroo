/**
 * The theme (package TH; 0.17 UX1, PP-D38): Normal (today's, the reference), Website purple, Hearth, Studio or
 * Instrument, chosen on Settings › Appearance and saved in this browser. It is independent of the light and dark
 * mode (`theme.ts`) and of the type palette (`palette.ts`): a theme other than Normal sets `data-scheme` on the
 * document element, which the design tokens key on, and Normal sets nothing. A theme also names how the frame's
 * parts are arranged (`data-frame`, read by the frame's styles): `bars` is the top bar and sidebar and sets
 * nothing, `sheet` is one sidebar and a raised page, `rail` is an icon rail, a list panel and a status line.
 * public/theme-init.js (linked from index.html) applies the saved choice before the first paint. The guide and
 * the API reference an instance serves read the same key and know Normal and Website purple only: any other
 * theme shows them in Normal. A choice made there reaches an open application tab through the storage event.
 */

import { useSyncExternalStore } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type ColourScheme = "normal" | "purple" | "hearth" | "studio" | "instrument";
export type FrameArrangement = "bars" | "sheet" | "rail";

export const SCHEMES: readonly ColourScheme[] = ["normal", "purple", "hearth", "studio", "instrument"];

/** How each theme arranges the frame's parts (PP-D39). */
export const SCHEME_FRAME: Record<ColourScheme, FrameArrangement> = {
  normal: "bars",
  purple: "bars",
  hearth: "bars",
  studio: "sheet",
  instrument: "rail",
};

export const SCHEME_STORAGE_KEY = "rdm:scheme:v1";

const isScheme = (value: unknown): value is ColourScheme => SCHEMES.includes(value as ColourScheme);

/** The browser's address-bar colour for each theme, light and dark; Normal's are index.html's own. */
const THEME_COLOURS: Record<ColourScheme, { light: string; dark: string }> = {
  normal: { light: "#f5f7f6", dark: "#101614" },
  purple: { light: "#fbf8f1", dark: "#0e1130" },
  hearth: { light: "#f6f2ec", dark: "#181613" },
  studio: { light: "#efeaf6", dark: "#100f16" },
  instrument: { light: "#fbfaf8", dark: "#111113" },
};

export function applyScheme(scheme: ColourScheme) {
  if (scheme === "normal") delete document.documentElement.dataset.scheme;
  else document.documentElement.dataset.scheme = scheme;
  if (SCHEME_FRAME[scheme] === "bars") delete document.documentElement.dataset.frame;
  else document.documentElement.dataset.frame = SCHEME_FRAME[scheme];
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

/** The frame arrangement of the chosen theme; the frame's components read it to place their parts. */
export function useFrameArrangement(): FrameArrangement {
  return SCHEME_FRAME[useSyncExternalStore(subscribe, snapshot)];
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
