/**
 * The application's place for a person who may browse no workspace (0.12 Z5, D326): it says so
 * plainly, names the roles they hold, and leads to Settings, which opens without a workspace. A
 * Security administrator, whose role reads no workspace's data, is led to People, where a role in
 * a workspace is granted.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { EngineModel, RouteState } from "@/types";
import { listedNames } from "@/state/permissionText";
import { BrandMascot } from "@/ui/ProductMark";
import { ShellFrame } from "./ShellFrame";
import { TopBar } from "./TopBar";
import { useHoldsGroup } from "@/state/useMe";

/** The roles a person holds, from their grants (a consumer API grant holds none). */
function useRoleNames(): string[] | undefined {
  const [names, setNames] = useState<string[]>();
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => api.myGrants())
      .then(
        (grants) =>
          active && setNames([...new Set(grants.flatMap((grant) => (grant.role ? [grant.role.name] : [])))].sort()),
        () => active && setNames([]),
      );
    return () => {
      active = false;
    };
  }, []);
  return names;
}

/** What the page says about the person's roles. */
export function noWorkspaceText(roles: string[], securityAdmin: boolean): string {
  if (!roles.length) return "You hold no roles yet. Ask a security administrator for a role in a workspace.";
  const held = `You hold ${listedNames(roles)}`;
  return securityAdmin
    ? `${held}, which reads no workspace's data. A role in a workspace is granted on People.`
    : `${held}, which reads no workspace's data. Ask a security administrator for a role in a workspace.`;
}

export function NoWorkspace({ model, onNavigate }: { model: EngineModel; onNavigate: (route: RouteState) => void }) {
  const roles = useRoleNames();
  const securityAdmin = Boolean(useHoldsGroup("security-admin"));
  return (
    <ShellFrame
      topBar={
        <TopBar model={model} onHome={() => undefined} onSelectApplication={() => undefined} onNavigate={onNavigate} />
      }
      main={{ className: "no-workspace" }}
    >
      <section className="no-workspace-page" aria-labelledby="no-workspace-title">
        <BrandMascot />
        <h1 id="no-workspace-title">There is no workspace you can open yet</h1>
        {roles && <p>{noWorkspaceText(roles, securityAdmin)}</p>}
        <div className="no-workspace-actions">
          {securityAdmin ? (
            <button type="button" className="primary" onClick={() => onNavigate({ kind: "settings", page: "people" })}>
              People
            </button>
          ) : (
            <button type="button" className="primary" onClick={() => onNavigate({ kind: "settings", page: "about" })}>
              Settings
            </button>
          )}
          <button type="button" className="secondary" onClick={() => onNavigate({ kind: "settings", page: "account" })}>
            Account
          </button>
        </div>
      </section>
    </ShellFrame>
  );
}
