import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { cachedRead } from "@/state/cachedRead";
import { holdsAnywhere, useHeldAnywhere, useWorkspacePermissions } from "@/state/permissions";
import { staticSystem } from "@/state/useSystem";
import type { Me, MyPermissions, SystemResponse } from "@/types";

// Who is signed in, read once per page load: it changes only by signing in again (0.12 I2).
const signedIn = cachedRead(() => api.me());

/** The signed-in person, or `undefined` while it loads or when it cannot be read. */
export function useMe(): Me | undefined {
  const [me, setMe] = useState<Me>();
  useEffect(() => {
    let active = true;
    signedIn.get().then(
      (loaded) => active && setMe(loaded),
      () => undefined,
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
  const permissions = useWorkspacePermissions(workspaceKey);
  return permissions && roleLine(permissions);
}

/**
 * Whether the caller holds an action group anywhere, such as Security administration (0.12 SP1,
 * D303; Z5, D328): `undefined` while it loads, `false` when it cannot be read. Only offers or hides
 * what the engine would refuse anyway.
 */
export function useHoldsGroup(groupKey: string): boolean | undefined {
  const held = useHeldAnywhere();
  return held && holdsAnywhere(held, groupKey);
}

export function roleLine(permissions: MyPermissions): string {
  const names = permissions.roles.map((role) => role.name);
  const where = permissions.workspaceLabel;
  if (!names.length) return `No role in ${where}`;
  const listed = names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
  return `${listed} in ${where}`;
}

/** The licence and the source address the engine offers its users (AGPL section 13), or `undefined`
 * while they load or when they cannot be read. Read once per page load (0.12 L1, D219). */
export function useSourceOffer(): Pick<SystemResponse["engine"], "license" | "sourceCode"> | undefined {
  const [offer, setOffer] = useState<SystemResponse["engine"]>();
  useEffect(() => {
    let active = true;
    staticSystem().then(
      (loaded) => active && setOffer(loaded.engine),
      () => undefined,
    );
    return () => {
      active = false;
    };
  }, []);
  return offer;
}
