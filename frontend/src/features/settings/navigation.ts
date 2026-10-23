/**
 * The settings navigation: groups and their pages, in order. Only built pages are listed (U-D11).
 * A group that needs an action group is listed only to a person holding it (Security, 0.12 SP1,
 * D303); the engine refuses the pages to anyone else either way.
 */

import type { SettingsPage } from "@/types";

export interface SettingsGroup {
  label: string;
  pages: { page: SettingsPage; label: string }[];
  /** The action group the caller must hold for the group to be listed. */
  requires?: "security-admin";
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
      { page: "model", label: "Model" },
      { page: "deployment", label: "Deployment" },
      { page: "operations", label: "Operations" },
    ],
  },
  {
    // Work done on the data rather than configuration: loading workbooks and following jobs (the
    // user, 2026-10-14). They are not settings either, and move out of Settings together later.
    label: "Data operations",
    pages: [
      { page: "import-profiles", label: "Import profiles" },
      { page: "moves", label: "Copy and move" },
      { page: "jobs", label: "Jobs" },
    ],
  },
  {
    label: "Security",
    requires: "security-admin",
    pages: [
      { page: "people", label: "People" },
      { page: "groups", label: "Groups" },
      { page: "roles", label: "Roles" },
    ],
  },
  {
    label: "Integration",
    pages: [
      { page: "consumer-apis", label: "Consumer APIs" },
      { page: "webhooks", label: "Webhooks" },
      { page: "api-reference", label: "API reference" },
    ],
  },
];

export function settingsGroupOf(page: SettingsPage) {
  return SETTINGS_NAVIGATION.find((group) => group.pages.some((item) => item.page === page))!.label;
}
