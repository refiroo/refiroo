/**
 * The Settings area's pages inside its shell (Track U U3). Back to applications returns to the
 * application route the user last looked at in this session, or to the default route.
 */

import { AboutPage } from "@/features/settings/AboutPage";
import { AppearancePage } from "@/features/settings/AppearancePage";
import { DeploymentPage } from "@/features/settings/DeploymentPage";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";
import { applicationFor } from "@/model/lookup";
import { defaultRoute, routePath, viewRoute } from "@/routing/routes";
import type { EngineModel, SettingsRoute } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { SettingsShell } from "./SettingsShell";
import type { Router } from "./useRouter";

export function SettingsArea({ router, model, route }: { router: Router; model: EngineModel; route: SettingsRoute }) {
  const { navigate, lastApplicationRoute, defaultWorkspaceKey } = router;
  const backRoute = lastApplicationRoute() ?? defaultRoute(model, defaultWorkspaceKey);
  // A workspace opens in the application the user last worked in.
  const application = applicationFor(model, lastApplicationRoute()?.applicationKey ?? "") ?? model.applications[0];

  return (
    <ToastProvider>
      <SettingsShell
        productName={model.product.name}
        page={route.page}
        backHref={routePath(backRoute)}
        onBack={() => navigate(backRoute)}
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
