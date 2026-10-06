/**
 * The settings navigation: groups and their pages, in order. Only built pages are listed (U-D11);
 * Integration's pages come with U4 and U5, Security's with U8.
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
];

export function settingsGroupOf(page: SettingsPage) {
  return SETTINGS_NAVIGATION.find((group) => group.pages.some((item) => item.page === page))!.label;
}
