/**
 * What the signed-in person may do, read once and kept for the page load (0.12 Z5, D321).
 *
 * Two reads answer every question the interface asks: `/me/permissions` for a workspace (the
 * groups held there and their narrowing) and `/me/action-groups` (every group held anywhere,
 * which the settings navigation and the first workspace follow). Both are kept per page load and
 * read again after a `403 FORBIDDEN`, which means a role changed since (D330). The interface only
 * avoids offering what the engine would refuse; the engine decides.
 */

import { useEffect, useSyncExternalStore } from "react";
import { api } from "@/api/client";
import { onForbidden } from "@/api/forbidden";
import type { HeldAnywhere, MyPermissions } from "@/types";

/** One read: its last answer, whether it failed, and whether it was asked since last forgotten. */
type Entry<T> = { value?: T; failed?: boolean; requested?: boolean };

const byWorkspace = new Map<string, Entry<MyPermissions>>();
let anywhere: Entry<HeldAnywhere[]> = {};
let generation = 0;
const listeners = new Set<() => void>();

function changed() {
  generation += 1;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function ensure<T>(entry: Entry<T>, read: () => Promise<T>) {
  if (entry.requested) return;
  entry.requested = true;
  Promise.resolve()
    .then(read)
    .then(
      (value) => {
        entry.value = value;
        entry.failed = false;
        changed();
      },
      () => {
        entry.failed = true;
        changed();
      },
    );
}

/** Read every permission again on its next use; what is shown stays until the new answer. */
export function forgetPermissions() {
  for (const entry of byWorkspace.values()) entry.requested = false;
  anywhere.requested = false;
  changed();
}

onForbidden(forgetPermissions);

/** Forget everything read, for a test's fresh start. */
export function resetPermissionsForTests() {
  byWorkspace.clear();
  anywhere = {};
  changed();
}

function entryFor(key: string) {
  let entry = byWorkspace.get(key);
  if (!entry) byWorkspace.set(key, (entry = {}));
  return entry;
}

/**
 * The person's permissions in `workspaceKey` (the default workspace without one); `undefined`
 * while they load or when they cannot be read.
 */
export function useWorkspacePermissions(workspaceKey?: string): MyPermissions | undefined {
  const version = useSyncExternalStore(subscribe, () => generation);
  const key = workspaceKey ?? "";
  useEffect(() => ensure(entryFor(key), () => api.myPermissions(workspaceKey)), [key, workspaceKey, version]);
  return byWorkspace.get(key)?.value;
}

/** Whether the person's permissions in `workspaceKey` could not be read. */
export function usePermissionsFailed(workspaceKey?: string): boolean {
  useSyncExternalStore(subscribe, () => generation);
  return Boolean(byWorkspace.get(workspaceKey ?? "")?.failed);
}

/** Every group the person holds anywhere; `undefined` while it loads, `[]` when it cannot be read. */
export function useHeldAnywhere(): HeldAnywhere[] | undefined {
  const version = useSyncExternalStore(subscribe, () => generation);
  useEffect(() => ensure(anywhere, () => api.myActionGroups().then((list) => list.items)), [version]);
  return anywhere.failed && !anywhere.value ? [] : anywhere.value;
}

/**
 * Whether the person holds `group` in the workspace these permissions are for; false while the
 * permissions are unknown (loading or unreadable), so nothing is offered before it is known (D323).
 */
export function holds(permissions: MyPermissions | undefined, group: string): boolean {
  return Boolean(permissions?.actionGroups.some((held) => held.key === group));
}

/** Whether the person holds `group` anywhere. */
export function holdsAnywhere(held: HeldAnywhere[] | undefined, group: string): boolean {
  return Boolean(held?.some((item) => item.key === group));
}

/** Which records a group lets the person write in a workspace (Z2, D289, D329). */
export interface RecordWrites {
  /** Whether the group is held there at all. */
  any: boolean;
  /** Whether a record of `objectTypeKey` in `applicationKey` may be written. */
  permits: (applicationKey: string, objectTypeKey: string) => boolean;
  /**
   * Whether a record of `objectTypeKey` may be written whatever its application: by its type, or
   * by an unnarrowed group. For the far end of a relationship before its record is chosen.
   */
  permitsType: (objectTypeKey: string) => boolean;
  /** Whether a relationship between two records may be written: either end will do (D291). */
  permitsRelation: (from: RecordRef, to: RecordRef) => boolean;
  /** The narrowing, when the group is narrowed; the band names it. */
  narrowing?: { applications: string[]; recordTypes: string[] };
}

export interface RecordRef {
  applicationKey: string;
  objectTypeKey: string;
}

export const NO_WRITES: RecordWrites = {
  any: false,
  permits: () => false,
  permitsType: () => false,
  permitsRelation: () => false,
};

export const ALL_WRITES: RecordWrites = {
  any: true,
  permits: () => true,
  permitsType: () => true,
  permitsRelation: () => true,
};

/** What `group` lets the holder of `permissions` write: the engine's rule, from its answer. */
export function recordWrites(permissions: MyPermissions | undefined, group: string): RecordWrites {
  const held = permissions?.actionGroups.find((item) => item.key === group);
  if (!held) return NO_WRITES;
  if (!held.applications.length && !held.recordTypes.length) return ALL_WRITES;
  const applications = new Set(held.applications);
  const types = new Set(held.recordTypes);
  const permits = (applicationKey: string, objectTypeKey: string) =>
    applications.has(applicationKey) || types.has(objectTypeKey);
  return {
    any: true,
    permits,
    permitsType: (objectTypeKey) => types.has(objectTypeKey),
    permitsRelation: (from, to) =>
      permits(from.applicationKey, from.objectTypeKey) || permits(to.applicationKey, to.objectTypeKey),
    narrowing: { applications: held.applications, recordTypes: held.recordTypes },
  };
}
