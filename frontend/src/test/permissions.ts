import type { HeldAnywhereList, MyPermissions } from "@/types";

/** Every action group the catalogue has (0.12 Z1). */
export const EVERY_GROUP = [
  "browse",
  "edit-live",
  "change-sets",
  "publish",
  "bulk",
  "copy-move",
  "model-authoring",
  "model-release",
  "workspace-admin",
  "integration-admin",
  "feed",
  "operations",
  "security-admin",
];

/**
 * A `GET /me/permissions` answer holding `groups` unnarrowed in `workspaceKey` (every group by
 * default: the person every test before 0.12 Z5 was), or narrowed to `recordTypes` for writes.
 */
export function permissionsFixture(
  workspaceKey = "default",
  groups: string[] = EVERY_GROUP,
  narrowing: { applications?: string[]; recordTypes?: string[] } = {},
): MyPermissions {
  return {
    workspaceKey,
    workspaceLabel: workspaceKey,
    roles: [{ key: "test", name: "Test role" }],
    actionGroups: groups.map((key) => ({
      key,
      name: key,
      applications: narrowing.applications ?? [],
      recordTypes: narrowing.recordTypes ?? [],
      sources: [],
    })),
  };
}

/** A `GET /me/action-groups` answer holding `groups` at the instance (every group by default). */
export function heldAnywhereFixture(groups: string[] = EVERY_GROUP): HeldAnywhereList {
  return { items: groups.map((key) => ({ key, name: key, instance: true, workspaces: [] })) };
}
