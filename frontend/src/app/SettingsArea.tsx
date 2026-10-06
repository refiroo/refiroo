/**
 * The Settings area's pages inside its shell (Track U U3). The top bar is the application pages'
 * own: the tab of the application the user last looked at returns to that exact route, another
 * application's tab to its last collection or its default view, and the product mark home.
 */

import { AboutPage } from "@/features/settings/AboutPage";
import { AppearancePage } from "@/features/settings/AppearancePage";
import { DeploymentPage } from "@/features/settings/DeploymentPage";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";
import { applicationFor } from "@/model/lookup";
import { defaultRoute, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, SettingsRoute } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { SettingsShell } from "./SettingsShell";
import type { Router } from "./useRouter";

export function SettingsArea({ router, model, route }: { router: Router; model: EngineModel; route: SettingsRoute }) {
  const { navigate, lastApplicationRoute, lastCollection, defaultWorkspaceKey } = router;
  const workspaceKey = lastApplicationRoute()?.workspaceKey ?? defaultWorkspaceKey;
  const selectApplication = (selected: ApplicationDefinition) => {
    const last = lastApplicationRoute();
    navigate(
      last?.applicationKey === selected.key
        ? last
        : (lastCollection(selected.key) ?? viewRoute(selected, selected.defaultView, workspaceKey)),
    );
  };
  // A workspace opens in the application the user last worked in.
  const application = applicationFor(model, lastApplicationRoute()?.applicationKey ?? "") ?? model.applications[0];

  return (
    <ToastProvider>
      <SettingsShell
        model={model}
        page={route.page}
        onHome={() => navigate(defaultRoute(model, workspaceKey))}
        onSelectApplication={selectApplication}
        onNavigate={(next) => navigate(next)}
      >
        {route.page === "about" ? (
          <AboutPage onNavigate={(next) => navigate(next)} />
        ) : route.page === "appearance" ? (
          <AppearancePage />
        ) : route.page === "deployment" ? (
          <DeploymentPage />
        ) : route.page === "workspaces" ? (
          <WorkspaceAdmin
            route={route}
            onRouteChange={(next) => navigate(next)}
            onDefaultChanged={router.defaultWorkspaceChanged}
            onWorkspaceDeleted={(workspaceKey) => {
              // Back to applications never returns to a deleted workspace.
              if (lastApplicationRoute()?.workspaceKey === workspaceKey) router.rememberWorkspace(defaultWorkspaceKey);
            }}
            onOpenWorkspace={(workspaceKey) => {
              if (navigate(viewRoute(application, application.defaultView, workspaceKey)))
                router.rememberWorkspace(workspaceKey);
            }}
          />
        ) : route.page === "model" ? (
          <ModelWorkbench
            route={route}
            onRouteChange={(next) => navigate(next)}
            onActiveModelChange={router.reloadModel}
          />
        ) : null}
      </SettingsShell>
    </ToastProvider>
  );
}
