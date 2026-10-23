import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Me, MyPermissions } from "@/types";

// Who is signed in, read once per page load: it changes only by signing in again (0.12 I2).
let loading: Promise<Me> | undefined;

/** The signed-in person, or `undefined` while it loads or when it cannot be read. */
export function useMe(): Me | undefined {
  const [me, setMe] = useState<Me>();
  useEffect(() => {
    let active = true;
    loading ??= Promise.resolve().then(() => api.me());
    loading.then(
      (loaded) => active && setMe(loaded),
      () => {
        loading = undefined;
      },
    );
    return () => {
      active = false;
    };
  }, []);
  return me;
}

/**
 * The roles the caller holds in a workspace (the default one without a key), as the account menu
 * names them: "Data steward in Herbarium", "Reader and Contributor in Herbarium", "No role in
 * Herbarium" (Z1). `undefined` while it loads or when it cannot be read.
 */
export function useRoleLine(workspaceKey?: string): string | undefined {
  const [permissions, setPermissions] = useState<MyPermissions>();
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => api.myPermissions(workspaceKey))
      .then(
        (loaded) => active && setPermissions(loaded),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  return permissions && roleLine(permissions);
}

/**
 * Whether the caller holds an instance action group, such as Security administration (0.12 SP1,
 * D303), read from their permissions in the default workspace, where an instance group appears as
 * in every workspace: `undefined` while it loads, `false` when it cannot be read. Only offers or
 * hides what the engine would refuse anyway.
 */
export function useHoldsGroup(groupKey: string): boolean | undefined {
  const [held, setHeld] = useState<boolean>();
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => api.myPermissions())
      .then(
        (loaded) => active && setHeld(loaded.actionGroups.some((group) => group.key === groupKey)),
        () => active && setHeld(false),
      );
    return () => {
      active = false;
    };
  }, [groupKey]);
  return held;
}

export function roleLine(permissions: MyPermissions): string {
  const names = permissions.roles.map((role) => role.name);
  const where = permissions.workspaceLabel;
  if (!names.length) return `No role in ${where}`;
  const listed = names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
  return `${listed} in ${where}`;
}

/** A person's initials for the avatar: the first letters of their first and last names. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return letters.map((word) => word[0]?.toUpperCase() ?? "").join("");
}
