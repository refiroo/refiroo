import { useState } from "react";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { defaultRoute, viewRoute } from "@/routing/routes";
import { applicationFor } from "@/model/lookup";
import type { ApplicationDefinition, CollectionQueryState, ObjectItem, Workspace } from "@/types";
import { AppShell } from "./AppShell";
import { useRouter } from "./useRouter";

export default function App() {
  const { model, error, route, navigate, lastCollection, rememberWorkspace, reloadModel } = useRouter();
  const [refreshToken, setRefreshToken] = useState(0);
  const [workspace, setWorkspace] = useState<Workspace>();

  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requested = route.kind === "models" ? undefined : applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute = route;
  // Aliased because the handlers below are hoisted function declarations, which TypeScript types
  // from the declaration rather than from the narrowing performed by the guard above.
  const activeModel = model;

  function selectApplication(selected: ApplicationDefinition) {
    const workspaceKey =
      activeRoute.kind === "models" ? (lastCollection()?.workspaceKey ?? "default") : activeRoute.workspaceKey;
    const remembered = lastCollection(selected.key);
    navigate(remembered ? { ...remembered, workspaceKey } : viewRoute(selected, selected.defaultView, workspaceKey));
  }

  function openObject(item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) {
    navigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      workspaceKey: item.workspaceKey,
    });
  }

  function openObjectById(objectTypeKey: string, objectId: string, applicationKey = application.key) {
    if (activeRoute.kind === "models") return;
    navigate({ kind: "detail", applicationKey, objectTypeKey, objectId, workspaceKey: activeRoute.workspaceKey });
  }

  function backToCollection() {
    if (activeRoute.kind === "models") return;
    const remembered = lastCollection(application.key);
    if (remembered) {
      navigate(remembered);
      return;
    }
    const matchingView = application.views.find(
      (view) => activeRoute.kind === "detail" && view.objectTypeKey === activeRoute.objectTypeKey,
    );
    navigate(viewRoute(application, matchingView?.key ?? application.defaultView, activeRoute.workspaceKey));
  }

  function goHome() {
    navigate({
      ...defaultRoute(activeModel),
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
          ? { ...remembered, workspaceKey }
          : viewRoute(application, matchingView?.key ?? application.defaultView, workspaceKey),
      );
    } else {
      navigate({ ...activeRoute, workspaceKey });
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
      {activeRoute.kind === "models" ? (
        <ModelWorkbench
          route={activeRoute}
          onRouteChange={(next) => navigate(next)}
          onActiveModelChange={reloadModel}
        />
      ) : activeRoute.kind === "list" ? (
        <CollectionView
          key={`${application.key}:${activeRoute.viewKey}:${activeRoute.workspaceKey}`}
          model={model}
          application={application}
          view={application.views.find((view) => view.key === activeRoute.viewKey) ?? application.views[0]}
          workspaceKey={activeRoute.workspaceKey}
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
          onOpen={openObjectById}
          onBack={backToCollection}
        />
      )}
    </AppShell>
  );
}
