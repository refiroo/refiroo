/**
 * Opening a workspace or one of its applications from a link (Home, Settings › Account): the route
 * is built from the workspace's own model, so it lands where the workspace switcher and the
 * application navigation land; a model that cannot be read is left to the address itself.
 */

import { applicationFor } from "@/model/lookup";
import { workspaceModel } from "@/model/workspaceModels";
import { routePath, viewRoute, workspaceRoute } from "@/routing/routes";
import type { EngineModel, RouteState, WorkspaceApplication } from "@/types";

export type Navigate = (route: RouteState) => void;

/**
 * Open `path` in `workspaceKey` once its model is loaded, since the route needs its views and types.
 * A model that cannot be read is left to the address itself, whose page then says what failed.
 */
export function openIn(
  workspaceKey: string,
  path: string,
  onNavigate: Navigate,
  route: (model: EngineModel) => RouteState | undefined,
) {
  workspaceModel(workspaceKey).then(
    (model) => {
      const next = route(model);
      if (next) onNavigate(next);
      else window.location.assign(path);
    },
    () => window.location.assign(path),
  );
}

export const appPath = (workspaceKey: string, application: Pick<WorkspaceApplication, "key" | "defaultView">) =>
  `/apps/${encodeURIComponent(application.key)}/views/${encodeURIComponent(application.defaultView)}?workspaceKey=${encodeURIComponent(workspaceKey)}`;

export function openApplication(
  workspaceKey: string,
  application: Pick<WorkspaceApplication, "key" | "defaultView">,
  onNavigate: Navigate,
) {
  openIn(workspaceKey, appPath(workspaceKey, application), onNavigate, (model) => {
    const found = applicationFor(model, application.key);
    return found && viewRoute(found, found.defaultView, workspaceKey);
  });
}

export const workspacePathOf = (workspaceKey: string) => routePath(workspaceRoute(workspaceKey));

/** Open the workspace's own page (0.17 SH1): its search, applications and what waits there. */
export function openWorkspace(workspaceKey: string, onNavigate: Navigate) {
  onNavigate(workspaceRoute(workspaceKey));
}
