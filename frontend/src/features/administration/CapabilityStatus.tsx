/**
 * Read-only status of the deployment's administration capabilities, shown on the Models and
 * Workspaces screens. A disabled group names the setting that enables it, taken from the
 * capabilities response, so an operator learns why an action is missing without reading the code.
 * The settings are deployment guards, not permissions.
 */

import { useId } from "react";
import type { CapabilitiesResponse } from "@/types";

export function CapabilityStatus({ capabilities }: { capabilities: CapabilitiesResponse }) {
  const headingId = useId();
  const groups = [
    {
      name: "Model administration",
      enabled: capabilities.modelAdmin.manageDrafts,
      setting: capabilities.modelAdmin.setting,
      scope: "model drafts, installation and activation",
    },
    {
      name: "Workspace administration",
      enabled: capabilities.workspaceAdmin.manageWorkspaces,
      setting: capabilities.workspaceAdmin.setting,
      scope: "creating, renaming, retiring and deleting workspaces and choosing the default",
    },
  ];
  return (
    <section className="capability-status" aria-labelledby={headingId}>
      <h2 id={headingId} className="nav-label">
        Deployment capabilities
      </h2>
      <ul>
        {groups.map((group) => (
          <li key={group.name}>
            <span className="capability-name">
              <strong>{group.name}</strong>
              <span className={group.enabled ? "pill active-pill" : "pill"}>
                {group.enabled ? "Enabled" : "Disabled"}
              </span>
            </span>
            <small>
              {group.enabled ? (
                <>Allows {group.scope}.</>
              ) : (
                <>
                  Read only. <code>{group.setting}</code> controls {group.scope}.
                </>
              )}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}
