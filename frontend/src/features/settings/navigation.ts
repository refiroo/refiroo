/**
 * The settings navigation: groups and their pages, in order. Only built pages are listed (U-D11);
 * Security's pages come with U8.
 */

import type { SettingsPage } from "@/types";

export interface SettingsGroup {
  label: string;
  pages: { page: SettingsPage; label: string }[];
}

export const SETTINGS_NAVIGATION: SettingsGroup[] = [
  {
    label: "General",
    pages: [
      { page: "about", label: "About" },
      { page: "appearance", label: "Appearance" },
    ],
  },
  {
    label: "Administration",
    pages: [
      { page: "workspaces", label: "Workspaces" },
      { page: "model", label: "Model" },
      { page: "deployment", label: "Deployment" },
    ],
  },
  {
    label: "Integration",
    pages: [
      { page: "consumer-apis", label: "Consumer APIs" },
      { page: "imports", label: "Imports" },
      { page: "webhooks", label: "Webhooks" },
      { page: "jobs", label: "Jobs and feed" },
      { page: "api-reference", label: "API reference" },
    ],
  },
];

export function settingsGroupOf(page: SettingsPage) {
  return SETTINGS_NAVIGATION.find((group) => group.pages.some((item) => item.page === page))!.label;
}
