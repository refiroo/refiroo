/**
 * The Settings area's pages inside its shell (Track U U3). The top bar is the application pages'
 * own: the tab of the application the user last looked at returns to that exact route, another
 * application's tab to its last collection or its default view, and the product mark home.
 */

import { WorkbookCanvas } from "@/features/workbook-canvas/WorkbookCanvas";
import { AboutPage } from "@/features/settings/AboutPage";
import { SettingsIndex } from "@/features/settings/SettingsIndex";
import { ApiReferencePage } from "@/features/settings/ApiReferencePage";
import { AccountPage } from "@/features/settings/AccountPage";
import { NotificationsPage } from "@/features/settings/NotificationsPage";
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
import { ClientsPage } from "@/features/security/ClientsPage";
import { SignInPage } from "@/features/security/SignInPage";
import { SigningKeysPage } from "@/features/security/SigningKeysPage";
import { AiTaskPage } from "@/features/ai-tasks/AiTaskPage";
import { AgentAccessPage } from "@/features/settings/AgentAccessPage";
import { AiPage } from "@/features/settings/AiPage";
import { MailPage } from "@/features/settings/MailPage";
import { MailTemplatePage } from "@/features/settings/MailTemplatePage";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { ModelEditor } from "@/features/model-editor/ModelEditor";
import { workspaceModel } from "@/model/workspaceModels";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";
import { applicationFor } from "@/model/lookup";
import { changeReviewFor, HOME, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, SettingsRoute } from "@/types";
import { useState } from "react";
import { AiTaskJourneyBar } from "@/features/ai-tasks/AiTaskJourneyBar";
import { SettingsShell } from "./SettingsShell";
import type { Router } from "./useRouter";

export function SettingsArea({ router, model, route }: { router: Router; model: EngineModel; route: SettingsRoute }) {
  const { navigate, lastApplicationRoute, lastCollection, defaultWorkspaceKey } = router;
  const workspaceKey = lastApplicationRoute()?.workspaceKey ?? defaultWorkspaceKey;
  // A workspace deleted here is not one to go back to.
  const [deletedKey, setDeletedKey] = useState<string>();
  const comeFrom = router.modelWorkspaceKey ?? workspaceKey;
  const backWorkspaceKey = comeFrom === deletedKey ? defaultWorkspaceKey : comeFrom;
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
  // The assistant's load is a journey over the task's page, the editor opened from it and the change set.
  const editingJourney = editing?.journey?.kind === "aiTask" ? editing.journey : undefined;
  const journeyTaskId = route.page === "ai-tasks" ? route.taskId : editingJourney?.taskId;
  const journeyBar = journeyTaskId && (
    <AiTaskJourneyBar
      key={journeyTaskId}
      journey={{ kind: "aiTask", taskId: journeyTaskId }}
      place={editing ? "editor" : "task"}
      onNavigate={(next) => navigate(next)}
    />
  );
  return (
    <SettingsShell
      journey={journeyBar || undefined}
      model={model}
      // A load of a workbook is a data operation: the rail keeps Jobs current.
      page={route.page === "ai-tasks" ? "jobs" : route.page}
      workspaceKey={backWorkspaceKey}
      fullWidth={Boolean(editing || moving)}
      onHome={() => navigate(HOME)}
      onSelectApplication={selectApplication}
      onNavigate={(next) => navigate(next)}
    >
      {editing?.page === "model" && editing.draftId && editing.editor?.show === "canvas" ? (
        <WorkbookCanvas
          key={editing.draftId}
          draftId={editing.draftId}
          forWorkspace={editing.forWorkspace}
          workspaceKey={editing.forWorkspace ?? workspaceKey}
          journey={editing.journey}
          selection={editing.editor}
          onSelect={(selection) => navigate({ ...editing, editor: selection })}
          activeModel={model}
          onNavigate={(next) => navigate(next)}
          onActivated={router.reloadModel}
          onOpenWorkspace={router.openWorkspace}
          onOpenChangeSet={({ applicationKey, workspaceKey: changeSetWorkspace, changeSetId }) =>
            navigate({
              kind: "changeSetChanges",
              applicationKey,
              workspaceKey: changeSetWorkspace,
              changeSetId,
              tab: "records",
              changeKinds: [],
              ...(editing.journey ? { journey: editing.journey } : {}),
            })
          }
        />
      ) : editing?.page === "model" && editing.draftId ? (
        <ModelEditor
          key={editing.draftId}
          draftId={editing.draftId}
          journey={editing.journey}
          forWorkspace={editing.forWorkspace}
          onOpenWorkspace={router.openWorkspace}
          selection={editing.editor ?? {}}
          onSelect={(selection) => navigate({ ...editing, editor: selection })}
          onNavigate={(next) => navigate(next)}
          onActivated={router.reloadModel}
          activeModel={model}
          workspaceKey={editing.forWorkspace ?? workspaceKey}
          onOpenChangeSet={({ applicationKey, workspaceKey: changeSetWorkspace, changeSetId }) =>
            navigate({
              kind: "changeSetChanges",
              applicationKey,
              workspaceKey: changeSetWorkspace,
              changeSetId,
              tab: "records",
              changeKinds: [],
              ...(editing.journey ? { journey: editing.journey } : {}),
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
      ) : route.page === "index" ? (
        <SettingsIndex onNavigate={(next) => navigate(next)} />
      ) : route.page === "about" ? (
        <AboutPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "appearance" ? (
        <AppearancePage />
      ) : route.page === "account" ? (
        <AccountPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "notifications" ? (
        <NotificationsPage />
      ) : route.page === "deployment" ? (
        <DeploymentPage />
      ) : route.page === "operations" ? (
        <OperationsPage />
      ) : route.page === "consumer-apis" ? (
        <ConsumerApisPage route={route} onNavigate={(next, replace) => navigate(next, replace)} />
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
      ) : route.page === "ai-tasks" && route.taskId ? (
        <AiTaskPage
          key={route.taskId}
          taskId={route.taskId}
          onNavigate={(next) => navigate(next)}
          onActiveModelChange={router.reloadModel}
          onOpenWorkspace={(key) => {
            router.openWorkspace(key);
            router.rememberWorkspace(key);
          }}
        />
      ) : route.page === "people" ? (
        <PeoplePage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "groups" ? (
        <GroupsPage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "roles" ? (
        <RolesPage />
      ) : route.page === "clients" ? (
        <ClientsPage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "sign-in" ? (
        <SignInPage route={route} onNavigate={(next) => navigate(next)} />
      ) : route.page === "signing-keys" ? (
        <SigningKeysPage />
      ) : route.page === "agent-access" ? (
        <AgentAccessPage onNavigate={(next) => navigate(next)} />
      ) : route.page === "ai" ? (
        <AiPage />
      ) : route.page === "mail" ? (
        <MailPage />
      ) : route.page === "mail-template" ? (
        <MailTemplatePage />
      ) : route.page === "api-reference" ? (
        <ApiReferencePage route={route} onNavigate={(next, replace) => navigate(next, replace)} />
      ) : route.page === "workspaces" ? (
        <WorkspaceAdmin
          route={route}
          onRouteChange={(next) => navigate(next)}
          onNavigate={(next) => navigate(next)}
          onDefaultChanged={router.defaultWorkspaceChanged}
          onWorkspaceDeleted={(workspaceKey) => {
            // Back to applications never returns to a deleted workspace.
            setDeletedKey(workspaceKey);
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
          onReturnToWorkspace={router.openWorkspace}
          onReturnToTask={(taskId) => navigate({ kind: "settings", page: "ai-tasks", taskId })}
          onOpenChangeSet={openChangeSet}
          onOpenChangeSetReview={(review) => navigate(review)}
          onOpenApplication={(applicationWorkspace, applicationKey) =>
            void workspaceModel(applicationWorkspace).then((active) => {
              const opened = applicationFor(active, applicationKey) ?? active.applications[0];
              if (opened) navigate(viewRoute(opened, opened.defaultView, applicationWorkspace));
              else router.openWorkspace(applicationWorkspace);
            })
          }
        />
      ) : null}
    </SettingsShell>
  );
}
