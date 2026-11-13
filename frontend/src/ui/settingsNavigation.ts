/**
 * The settings navigation: groups and their pages, in order. Only built pages are listed (U-D11).
 * A page that needs an action group is listed only to a person holding one of its groups somewhere
 * (0.12 SP1, D303; Z5, D328), and a group with no page left is not shown; the engine refuses the
 * pages to anyone else either way.
 */

import type { Hue } from "@/model/hues";
import type { SettingsPage } from "@/types";
import type { IconName } from "@/ui/Icon";

/**
 * A page the navigation lists. TypeScript only matches `{ kind: "settings", page }` to the route union by its
 * discriminant while `page` has at most 25 values, so the pages that are never listed (the index, an AI task)
 * are left out of it.
 */
export type ListedPage = Exclude<SettingsPage, "index" | "ai-tasks">;

export interface SettingsGroup {
  label: string;
  /** What the group is for, said on the index (0.17 SH1). */
  description: string;
  /** The group's colour, on the index, on each of its pages' title tile and on their rows (0.17 ST1, PP-D67). */
  hue: Hue;
  /**
   * Each page, its glyph, one line saying what it is for (the index, PP-D65), and the action groups any of
   * which lists it; none for a page everyone opens.
   */
  pages: { page: ListedPage; label: string; icon: IconName; line: string; requires?: string[] }[];
}

/**
 * Settings by task (0.17 SH1, PP-D37): the groups are the index's and the menu's, About last.
 * Every page that was reachable stays reachable, each under the same permission as before.
 */
export const SETTINGS_NAVIGATION: SettingsGroup[] = [
  {
    label: "You",
    hue: 1,
    description: "How refiroo looks for you, your password and what is mailed to you.",
    pages: [
      { page: "appearance", label: "Appearance", icon: "sun", line: "Theme, light or dark, table density" },
      { page: "account", label: "Account", icon: "user", line: "Your password, passkeys, second factor and sessions" },
      { page: "notifications", label: "Notification email", icon: "bell", line: "Which notices are mailed to you" },
    ],
  },
  {
    label: "Workspaces and models",
    hue: 2,
    description: "Create a workspace, change what a workspace holds, move data between workspaces.",
    pages: [
      {
        page: "workspaces",
        label: "Workspaces",
        icon: "workspace",
        line: "Create, rename, retire; who may work in each",
      },
      {
        page: "model",
        label: "Model",
        icon: "model",
        line: "The lists and fields each workspace holds, and their releases",
        requires: ["model-authoring", "model-release"],
      },
      {
        page: "import-profiles",
        label: "Import profiles",
        icon: "document",
        line: "How a workbook is read, kept for the next load",
        requires: ["bulk"],
      },
      {
        page: "moves",
        label: "Copy and move",
        icon: "swap",
        line: "Records from one workspace to another",
        requires: ["copy-move"],
      },
    ],
  },
  {
    label: "People and access",
    hue: 3,
    description: "Who signs in, what they may do and how they sign in.",
    pages: [
      {
        page: "people",
        label: "People",
        icon: "user",
        line: "Who signs in, their roles and groups",
        requires: ["security-admin"],
      },
      {
        page: "groups",
        label: "Groups",
        icon: "users",
        line: "People who share the same roles",
        requires: ["security-admin"],
      },
      { page: "roles", label: "Roles", icon: "shield", line: "What each role allows", requires: ["security-admin"] },
      {
        page: "sign-in",
        label: "Sign-in",
        icon: "lock",
        line: "Passwords, or your organisation's sign-in provider",
        requires: ["security-admin"],
      },
      {
        page: "signing-keys",
        label: "Signing keys",
        icon: "key",
        line: "The keys that sign access tokens",
        requires: ["security-admin"],
      },
    ],
  },
  {
    label: "Connections",
    hue: 4,
    description: "Other systems and assistants that read or change the data.",
    pages: [
      {
        page: "clients",
        label: "Clients",
        icon: "api",
        line: "Systems that call the API with an ID and a secret",
        requires: ["security-admin"],
      },
      {
        page: "agent-access",
        label: "Agent access",
        icon: "bot",
        line: "Assistants that work through refiroo's tools",
        requires: ["security-admin"],
      },
      {
        page: "consumer-apis",
        label: "Consumer APIs",
        icon: "server",
        line: "The read APIs each workspace's model declares",
        requires: ["browse"],
      },
      {
        page: "webhooks",
        label: "Webhooks",
        icon: "webhook",
        line: "Changes sent to another system as they happen",
        requires: ["integration-admin"],
      },
      { page: "api-reference", label: "API reference", icon: "book", line: "The documentation of every route" },
    ],
  },
  {
    label: "This instance",
    hue: 6,
    description: "Background work, health, configuration and the version it runs.",
    pages: [
      { page: "jobs", label: "Jobs", icon: "activity", line: "Imports, exports and other background work" },
      {
        page: "operations",
        label: "Operations",
        icon: "shield",
        line: "Whether the engine's processes are healthy",
        requires: ["operations"],
      },
      {
        page: "deployment",
        label: "Deployment",
        icon: "settings",
        line: "Every setting this instance runs with",
        requires: ["operations"],
      },
      {
        page: "mail",
        label: "Mail",
        icon: "mail",
        line: "The mail server, and what was sent",
        requires: ["security-admin"],
      },
      {
        page: "mail-template",
        label: "E-mail template",
        icon: "pencil",
        line: "How every mail from refiroo looks",
        requires: ["operations"],
      },
      {
        page: "ai",
        label: "AI",
        icon: "sparkle",
        line: "What the AI provider is used for, and its calls",
        requires: ["operations"],
      },
      { page: "about", label: "About", icon: "info", line: "The version and its licence" },
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

/**
 * What a Settings page's header takes from the navigation: its group as the eyebrow, the group's colour and
 * the page's glyph (`<SettingsLayout {...settingsHead("people")} …>`).
 */
export function settingsHead(page: ListedPage): { eyebrow: string; hue: Hue; icon: IconName } {
  const group = SETTINGS_NAVIGATION.find((entry) => entry.pages.some((item) => item.page === page))!;
  return { eyebrow: group.label, hue: group.hue, icon: group.pages.find((item) => item.page === page)!.icon };
}

export function settingsGroupOf(page: SettingsPage) {
  return SETTINGS_NAVIGATION.find((group) => group.pages.some((item) => item.page === page))!.label;
}
