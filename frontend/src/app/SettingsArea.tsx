/**
 * The Settings area's pages inside its shell (Track U U3). The top bar is the application pages'
 * own: the tab of the application the user last looked at returns to that exact route, another
 * application's tab to its last collection or its default view, and the product mark home.
 */

import { AboutPage } from "@/features/settings/AboutPage";
import { ApiReferencePage } from "@/features/settings/ApiReferencePage";
import { AccountPage } from "@/features/settings/AccountPage";
import { AppearancePage } from "@/features/settings/AppearancePage";
import { ConsumerApisPage } from "@/features/settings/ConsumerApisPage";
import { DeploymentPage } from "@/features/settings/DeploymentPage";
import { OperationsPage } from "@/features/settings/OperationsPage";
import { ImportProfilesPage } from "@/features/settings/ImportProfilesPage";
import { JobsPage } from "@/features/settings/JobsPage";
import { MoveEditor } from "@/features/moves/MoveEditor";
import { MovesPage } from "@/features/moves/MovesPage";
import { WebhooksPage } from "@/features/settings/WebhooksPage";
import { GroupsPage } from "@/features/security/GroupsPage";
import { PeoplePage } from "@/features/security/PeoplePage";
import { RolesPage } from "@/features/security/RolesPage";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { ModelEditor } from "@/features/model-editor/ModelEditor";
import { workspaceModel } from "@/model/workspaceModels";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";
import { applicationFor } from "@/model/lookup";
import { changeReviewFor, HOME, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, SettingsRoute } from "@/types";
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

  const editing = route.page === "model" && route.draftId && route.editor ? route : undefined;
  const moving = route.page === "moves" ? route.move : undefined;
  // A change set's review, in the application last used there if its model has it.
  const openChangeSet = (changeSetWorkspace: string, changeSetId: string) =>
    void workspaceModel(changeSetWorkspace).then((active) => {
      const last = lastApplicationRoute();
      const application = (last && applicationFor(active, last.applicationKey)) ?? active.applications[0];
      if (application) navigate(changeReviewFor(application.key, changeSetWorkspace, changeSetId));
      else router.openWorkspace(changeSetWorkspace);
    });
  return (
    <SettingsShell
      model={model}
      page={route.page}
      fullWidth={Boolean(editing || moving)}
      onHome={() => navigate(HOME)}
      onSelectApplication={selectApplication}
      onNavigate={(next) => navigate(next)}
    >
      {editing?.page === "model" && editing.draftId ? (
        <ModelEditor
          key={editing.draftId}
          draftId={editing.draftId}
          selection={editing.editor ?? {}}
          onSelect={(selection) => navigate({ ...editing, editor: selection })}
          onNavigate={(next) => navigate(next)}
          onActivated={router.reloadModel}
          activeModel={model}
          workspaceKey={workspaceKey}
          onOpenChangeSet={({ applicationKey, workspaceKey: changeSetWorkspace, changeSetId }) =>
            navigate({
              kind: "changeSetChanges",
              applicationKey,
              workspaceKey: changeSetWorkspace,
              changeSetId,
              tab: "records",
              changeKinds: [],
            })
          }
          onOpenApplication={(applicationKey, openedWorkspace = workspaceKey) => {
            // The workspace's model was just reloaded; read it so the new application is known here.
            void workspaceModel(openedWorkspace).then((active) => {
              const opened = applicationFor(active, applicationKey);
              if (opened) navigate(viewRoute(opened, opened.defaultView, openedWorkspace));
              else router.openWorkspace(openedWorkspace);
            });
          }}
        />
      ) : moving ? (
        <MoveEditor
          key={`${moving.mappingKey}:${moving.from}:${moving.to}`}
          address={moving}
          onAddress={(move, replace) => navigate({ kind: "settings", page: "moves", move }, replace)}
          onNavigate={(next) => navigate(next)}
          onOpenChangeSet={openChangeSet}
        />
      ) : route.page === "moves" ? (
        <MovesPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "about" ? (
        <AboutPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "appearance" ? (
        <AppearancePage />
      ) : route.page === "account" ? (
        <AccountPage />
      ) : route.page === "deployment" ? (
        <DeploymentPage />
      ) : route.page === "operations" ? (
        <OperationsPage />
      ) : route.page === "consumer-apis" ? (
        <ConsumerApisPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "webhooks" ? (
        <WebhooksPage route={route} model={model} onNavigate={(next) => navigate(next)} />
      ) : route.page === "import-profiles" ? (
        <ImportProfilesPage
          model={model}
          route={route}
          defaultWorkspace={workspaceKey}
          onNavigate={(next) => navigate(next)}
        />
      ) : route.page === "jobs" ? (
        <JobsPage model={model} route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "people" ? (
        <PeoplePage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "groups" ? (
        <GroupsPage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "roles" ? (
        <RolesPage />
      ) : route.page === "api-reference" ? (
        <ApiReferencePage />
      ) : route.page === "workspaces" ? (
        <WorkspaceAdmin
          route={route}
          onRouteChange={(next) => navigate(next)}
          onNavigate={(next) => navigate(next)}
          onDefaultChanged={router.defaultWorkspaceChanged}
          onWorkspaceDeleted={(workspaceKey) => {
            // Back to applications never returns to a deleted workspace.
            if (lastApplicationRoute()?.workspaceKey === workspaceKey) router.rememberWorkspace(defaultWorkspaceKey);
          }}
          onOpenWorkspace={(workspaceKey) => {
            // Its own model's start: the application shown last may not be in its model (0.11 M5).
            router.openWorkspace(workspaceKey);
            router.rememberWorkspace(workspaceKey);
          }}
        />
      ) : route.page === "model" ? (
        <ModelWorkbench
          route={route}
          onRouteChange={(next) => navigate(next)}
          onActiveModelChange={router.reloadModel}
          onOpenWorkspace={(workspaceKey) => navigate({ kind: "settings", page: "workspaces", workspaceKey })}
          onOpenChangeSet={openChangeSet}
        />
      ) : null}
    </SettingsShell>
  );
}
