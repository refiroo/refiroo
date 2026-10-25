/**
 * The settings navigation: groups and their pages, in order. Only built pages are listed (U-D11).
 * A page that needs an action group is listed only to a person holding one of its groups somewhere
 * (0.12 SP1, D303; Z5, D328), and a group with no page left is not shown; the engine refuses the
 * pages to anyone else either way.
 */

import type { SettingsPage } from "@/types";

export interface SettingsGroup {
  label: string;
  /** Each page, and the action groups any of which lists it; none for a page everyone opens. */
  pages: { page: SettingsPage; label: string; requires?: string[] }[];
}

export const SETTINGS_NAVIGATION: SettingsGroup[] = [
  {
    label: "General",
    pages: [
      { page: "about", label: "About" },
      { page: "appearance", label: "Appearance" },
      { page: "account", label: "Account" },
    ],
  },
  {
    label: "Administration",
    pages: [
      { page: "workspaces", label: "Workspaces" },
      { page: "model", label: "Model", requires: ["model-authoring", "model-release"] },
      { page: "deployment", label: "Deployment", requires: ["operations"] },
      { page: "operations", label: "Operations", requires: ["operations"] },
    ],
  },
  {
    // Work done on the data rather than configuration: loading workbooks and following jobs (the
    // user, 2026-10-14). They are not settings either, and move out of Settings together later.
    label: "Data operations",
    pages: [
      { page: "import-profiles", label: "Import profiles", requires: ["bulk"] },
      { page: "moves", label: "Copy and move", requires: ["copy-move"] },
      { page: "jobs", label: "Jobs" },
    ],
  },
  {
    label: "Security",
    pages: [
      { page: "people", label: "People", requires: ["security-admin"] },
      { page: "groups", label: "Groups", requires: ["security-admin"] },
      { page: "roles", label: "Roles", requires: ["security-admin"] },
      { page: "clients", label: "Clients", requires: ["security-admin"] },
      { page: "signing-keys", label: "Signing keys", requires: ["security-admin"] },
    ],
  },
  {
    label: "Integration",
    pages: [
      { page: "consumer-apis", label: "Consumer APIs", requires: ["browse"] },
      { page: "webhooks", label: "Webhooks", requires: ["integration-admin"] },
      { page: "api-reference", label: "API reference" },
    ],
  },
];

/** The navigation a person sees, holding `held` somewhere; `undefined` while it loads lists only
 * what everyone opens. */
export function navigationFor(held: { key: string }[] | undefined): SettingsGroup[] {
  const keys = new Set(held?.map((group) => group.key));
  return SETTINGS_NAVIGATION.map((group) => ({
    ...group,
    pages: group.pages.filter((item) => !item.requires || item.requires.some((key) => keys.has(key))),
  })).filter((group) => group.pages.length > 0);
}

export function settingsGroupOf(page: SettingsPage) {
  return SETTINGS_NAVIGATION.find((group) => group.pages.some((item) => item.page === page))!.label;
}
