import { useState } from "react";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { defaultRoute, viewRoute } from "@/routing/routes";
import { applicationFor } from "@/model/lookup";
import type { ApplicationDefinition, CollectionQueryState, ObjectItem, Workspace } from "@/types";
import { AppShell } from "./AppShell";
import { useRouter, type Router } from "./useRouter";
import { WorkspaceDataProvider, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { DraftActions, WorkspaceDrafts } from "@/features/workspaces/WorkspaceDrafts";
import { Notice } from "@/ui/Notice";

export default function App() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const { model, route, error } = router;
  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const draftId = route.kind === "models" ? undefined : route.workspaceDraftId;
  return (
    <WorkspaceDataProvider
      key={`${route.kind === "models" ? "models" : route.workspaceKey}:${draftId ?? "live"}`}
      draftId={draftId}
      workspaceKey={route.kind === "models" ? "" : route.workspaceKey}
      model={model}
    >
      <AppContent router={router} message={message} setMessage={setMessage} />
    </WorkspaceDataProvider>
  );
}

function AppContent({
  router,
  message,
  setMessage,
}: {
  router: Router;
  message: string;
  setMessage: (message: string) => void;
}) {
  const { model: currentModel, error, route, navigate, lastCollection, rememberWorkspace, reloadModel } = router;
  const data = useWorkspaceData();
  const model = data.model ?? currentModel;
  const [refreshToken, setRefreshToken] = useState(0);
  const [workspace, setWorkspace] = useState<Workspace>();

  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requested = route.kind === "models" ? undefined : applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute = route;
  // Aliased because the handlers below are hoisted function declarations, which TypeScript types
  // from the declaration rather than from the narrowing performed by the guard above.
  const activeModel = model;

  const workspaceDraftId = activeRoute.kind === "models" ? undefined : activeRoute.workspaceDraftId;
  const readOnly =
    workspace?.key !== (activeRoute.kind === "models" ? "" : activeRoute.workspaceKey) ||
    workspace?.status !== "active";

  function selectApplication(selected: ApplicationDefinition) {
    const workspaceKey =
      activeRoute.kind === "models" ? (lastCollection()?.workspaceKey ?? "default") : activeRoute.workspaceKey;
    const remembered = lastCollection(selected.key);
    navigate(
      remembered
        ? {
            ...remembered,
            workspaceKey,
            workspaceDraftId,
            cursors:
              remembered.workspaceKey === workspaceKey && remembered.workspaceDraftId === workspaceDraftId
                ? remembered.cursors
                : undefined,
          }
        : { ...viewRoute(selected, selected.defaultView, workspaceKey), workspaceDraftId },
    );
  }

  function openObject(item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) {
    navigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      workspaceKey: activeRoute.kind === "models" ? item.workspaceKey : activeRoute.workspaceKey,
      workspaceDraftId,
    });
  }

  function openObjectById(objectTypeKey: string, objectId: string, applicationKey = application.key) {
    if (activeRoute.kind === "models") return;
    navigate({
      kind: "detail",
      applicationKey,
      objectTypeKey,
      objectId,
      workspaceKey: activeRoute.workspaceKey,
      workspaceDraftId,
    });
  }

  function backToCollection() {
    if (activeRoute.kind === "models") return;
    const remembered = lastCollection();
    if (remembered?.workspaceKey === activeRoute.workspaceKey && remembered.workspaceDraftId === workspaceDraftId) {
      navigate(remembered);
      return;
    }
    const matchingView = application.views.find(
      (view) => activeRoute.kind === "detail" && view.objectTypeKey === activeRoute.objectTypeKey,
    );
    navigate({
      ...viewRoute(application, matchingView?.key ?? application.defaultView, activeRoute.workspaceKey),
      workspaceDraftId,
    });
  }

  function goHome() {
    navigate({
      ...defaultRoute(activeModel),
      workspaceDraftId,
      workspaceKey:
        activeRoute.kind === "models" ? (lastCollection()?.workspaceKey ?? "default") : activeRoute.workspaceKey,
    });
  }

  function changeWorkspace(workspaceKey: string) {
    if (activeRoute.kind === "models") return;
    rememberWorkspace(workspaceKey);
    if (activeRoute.kind === "detail") {
      const matchingView = application.views.find((view) => view.objectTypeKey === activeRoute.objectTypeKey);
      const remembered = lastCollection(application.key);
      navigate(
        remembered && remembered.viewKey === matchingView?.key
          ? { ...remembered, workspaceKey, workspaceDraftId: undefined, cursors: undefined }
          : viewRoute(application, matchingView?.key ?? application.defaultView, workspaceKey),
      );
    } else if (activeRoute.kind === "drafts") {
      navigate({ ...activeRoute, workspaceKey });
    } else {
      navigate({ ...activeRoute, workspaceKey, workspaceDraftId: undefined, cursors: undefined });
    }
    setRefreshToken((value) => value + 1);
  }

  return (
    <AppShell
      model={model}
      application={application}
      activeRoute={activeRoute}
      refreshToken={refreshToken}
      onNavigate={navigate}
      onSelectApplication={selectApplication}
      onChangeWorkspace={changeWorkspace}
      workspace={workspace}
      onWorkspaceResolved={setWorkspace}
      onHome={goHome}
      onOpenObject={openObject}
    >
      {message && <Notice tone="success">{message}</Notice>}
      {data.draft && (
        <DraftActions
          readOnly={readOnly}
          onExit={(result) => {
            setMessage(result);
            navigate({ ...viewRoute(application, application.defaultView, data.draft!.workspaceKey) });
            setRefreshToken((value) => value + 1);
          }}
        />
      )}
      {activeRoute.kind === "models" ? (
        <ModelWorkbench
          route={activeRoute}
          onRouteChange={(next) => navigate(next)}
          onActiveModelChange={reloadModel}
        />
      ) : activeRoute.kind === "drafts" ? (
        <WorkspaceDrafts
          workspaceKey={activeRoute.workspaceKey}
          readOnly={readOnly}
          onOpen={(id) =>
            navigate({
              ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
              workspaceDraftId: id,
            })
          }
        />
      ) : activeRoute.kind === "list" ? (
        <CollectionView
          key={`${application.key}:${activeRoute.viewKey}:${activeRoute.workspaceKey}`}
          model={model}
          application={application}
          view={application.views.find((view) => view.key === activeRoute.viewKey) ?? application.views[0]}
          workspaceKey={activeRoute.workspaceKey}
          readOnly={readOnly}
          onChanged={() => setRefreshToken((value) => value + 1)}
          query={activeRoute}
          onQueryChange={(query: CollectionQueryState) => navigate({ ...activeRoute, ...query })}
          onOpen={openObject}
        />
      ) : (
        <ObjectDetail
          key={`${application.key}:${activeRoute.objectTypeKey}:${activeRoute.objectId}:${activeRoute.workspaceKey}`}
          model={model}
          application={application}
          objectTypeKey={activeRoute.objectTypeKey}
          objectId={activeRoute.objectId}
          workspaceKey={activeRoute.workspaceKey}
          readOnly={readOnly}
          onChanged={() => setRefreshToken((value) => value + 1)}
          onOpen={openObjectById}
          onBack={backToCollection}
        />
      )}
    </AppShell>
  );
}
