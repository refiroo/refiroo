import { useRef, useState, type CSSProperties } from "react";
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
import { HistoricalRevisionBanner, WorkspaceHistory } from "@/features/workspaces/WorkspaceHistory";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";

export default function App() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const { model, route, error } = router;
  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const draftId = route.kind === "list" || route.kind === "detail" ? route.workspaceDraftId : undefined;
  const revisionId = route.kind === "list" || route.kind === "detail" ? route.workspaceRevisionId : undefined;
  return (
    <WorkspaceDataProvider
      key={`${route.kind === "models" ? "models" : route.workspaceKey}:${draftId ?? revisionId ?? "live"}`}
      draftId={draftId}
      revisionId={revisionId}
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
  const actionSequence = useRef(0);
  const inspectorWidth = useLocalNumberPreference(
    `rdm:layout:inspector-width:v1:${route && route.kind !== "models" ? route.applicationKey : "record"}:${route?.kind === "detail" ? (route.collectionOrigin?.viewKey ?? "record") : "record"}`,
    480,
    360,
    720,
  );

  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requested = route.kind === "models" ? undefined : applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute = route;
  // Aliased because the handlers below are hoisted function declarations, which TypeScript types
  // from the declaration rather than from the narrowing performed by the guard above.
  const activeModel = model;

  const workspaceDraftId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceDraftId : undefined;
  const workspaceRevisionId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceRevisionId : undefined;
  const readOnly =
    Boolean(workspaceRevisionId) ||
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
            workspaceRevisionId,
            cursors:
              remembered.workspaceKey === workspaceKey &&
              remembered.workspaceDraftId === workspaceDraftId &&
              remembered.workspaceRevisionId === workspaceRevisionId
                ? remembered.cursors
                : undefined,
          }
        : { ...viewRoute(selected, selected.defaultView, workspaceKey), workspaceDraftId, workspaceRevisionId },
    );
  }

  function openObject(
    item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">,
    action?: "edit" | "delete",
    source?: "hierarchy",
  ) {
    navigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      ...(source === "hierarchy" ? { collectionOrigin: null } : {}),
      ...(action ? { actionRequest: { action, key: ++actionSequence.current } } : {}),
      workspaceKey: activeRoute.kind === "models" ? item.workspaceKey : activeRoute.workspaceKey,
      workspaceDraftId,
      workspaceRevisionId,
    });
  }

  function openObjectById(
    objectTypeKey: string,
    objectId: string,
    applicationKey = application.key,
    action?: "edit" | "delete",
  ) {
    if (activeRoute.kind === "models") return;
    navigate({
      kind: "detail",
      applicationKey,
      objectTypeKey,
      objectId,
      ...(action ? { actionRequest: { action, key: ++actionSequence.current } } : {}),
      fullPage: activeRoute.kind === "detail" ? activeRoute.fullPage : undefined,
      workspaceKey: activeRoute.workspaceKey,
      workspaceDraftId,
      workspaceRevisionId,
    });
  }

  function backToCollection() {
    if (activeRoute.kind === "models") return;
    const remembered = activeRoute.kind === "detail" ? activeRoute.collectionOrigin : undefined;
    if (
      remembered?.workspaceKey === activeRoute.workspaceKey &&
      remembered.workspaceDraftId === workspaceDraftId &&
      remembered.workspaceRevisionId === workspaceRevisionId
    ) {
      navigate(remembered);
      return;
    }
    const matchingView = application.views.find(
      (view) => activeRoute.kind === "detail" && view.objectTypeKey === activeRoute.objectTypeKey,
    );
    navigate({
      ...viewRoute(application, matchingView?.key ?? application.defaultView, activeRoute.workspaceKey),
      workspaceDraftId,
      workspaceRevisionId,
    });
  }

  function goHome() {
    navigate({
      ...defaultRoute(activeModel),
      workspaceDraftId,
      workspaceRevisionId,
      workspaceKey:
        activeRoute.kind === "models" ? (lastCollection()?.workspaceKey ?? "default") : activeRoute.workspaceKey,
    });
  }

  function changeWorkspace(workspaceKey: string) {
    if (activeRoute.kind === "models") return;
    let changed: boolean;
    if (activeRoute.kind === "detail") {
      const matchingView = application.views.find((view) => view.objectTypeKey === activeRoute.objectTypeKey);
      const remembered = lastCollection(application.key);
      changed = navigate(
        remembered && remembered.viewKey === matchingView?.key
          ? {
              ...remembered,
              workspaceKey,
              workspaceDraftId: undefined,
              workspaceRevisionId: undefined,
              cursors: undefined,
            }
          : viewRoute(application, matchingView?.key ?? application.defaultView, workspaceKey),
      );
    } else if (activeRoute.kind === "drafts" || activeRoute.kind === "history") {
      changed = navigate({ ...activeRoute, workspaceKey });
    } else {
      changed = navigate({
        ...activeRoute,
        workspaceKey,
        workspaceDraftId: undefined,
        workspaceRevisionId: undefined,
        cursors: undefined,
      });
    }
    if (changed) {
      rememberWorkspace(workspaceKey);
      setRefreshToken((value) => value + 1);
    }
  }

  const collection =
    activeRoute.kind === "list"
      ? activeRoute
      : activeRoute.kind === "detail"
        ? activeRoute.collectionOrigin
        : undefined;
  const collectionApplication = collection ? applicationFor(model, collection.applicationKey) : undefined;
  const hasDetail = activeRoute.kind === "detail";
  const inspector = hasDetail && Boolean(collection) && activeRoute.fullPage === false;
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
      onOpenObject={(item) => openObject(item, undefined, "hierarchy")}
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
      {data.revision && (
        <HistoricalRevisionBanner
          onExit={() =>
            navigate({ kind: "history", applicationKey: application.key, workspaceKey: data.revision!.workspaceKey })
          }
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
      ) : activeRoute.kind === "history" ? (
        <WorkspaceHistory
          workspaceKey={activeRoute.workspaceKey}
          readOnly={readOnly}
          onOpen={(id) =>
            navigate({
              ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
              workspaceRevisionId: id,
            })
          }
          onDraftCreated={(id) =>
            navigate({
              ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
              workspaceDraftId: id,
            })
          }
        />
      ) : (
        <div
          className={`record-workspace${inspector ? " has-inspector" : ""}${hasDetail ? " has-record" : ""}`}
          style={{ "--inspector-width": `${inspectorWidth.value}px` } as CSSProperties}
        >
          {collection && collectionApplication && (
            <div className="record-collection" hidden={hasDetail && !inspector}>
              <CollectionView
                key={`${collection.applicationKey}:${collection.viewKey}:${collection.workspaceKey}:${workspaceDraftId ?? workspaceRevisionId ?? "live"}`}
                model={model}
                application={collectionApplication}
                view={
                  collectionApplication.views.find((view) => view.key === collection.viewKey) ??
                  collectionApplication.views[0]
                }
                workspaceKey={collection.workspaceKey}
                readOnly={readOnly}
                refreshToken={refreshToken}
                selectedId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
                onChanged={() => setRefreshToken((value) => value + 1)}
                query={collection}
                onQueryChange={(query: CollectionQueryState) =>
                  navigate(
                    activeRoute.kind === "detail"
                      ? { ...activeRoute, collectionOrigin: { ...collection, ...query } }
                      : { ...collection, ...query },
                  )
                }
                onOpen={openObject}
              />
            </div>
          )}
          {activeRoute.kind === "detail" && (
            <>
              {inspector && (
                <ResizeHandle
                  className="inspector-resizer"
                  label="Resize record inspector"
                  value={inspectorWidth.value}
                  min={360}
                  max={720}
                  direction={-1}
                  onChange={inspectorWidth.change}
                  onReset={inspectorWidth.reset}
                />
              )}
              <ObjectDetail
                key={`${application.key}:${activeRoute.objectTypeKey}:${activeRoute.objectId}:${activeRoute.workspaceKey}:${activeRoute.actionRequest?.key ?? 0}`}
                model={model}
                application={application}
                objectTypeKey={activeRoute.objectTypeKey}
                objectId={activeRoute.objectId}
                workspaceKey={activeRoute.workspaceKey}
                inspector={inspector}
                initialAction={activeRoute.actionRequest?.action}
                onExpand={inspector ? () => navigate({ ...activeRoute, fullPage: true }) : undefined}
                readOnly={readOnly}
                onChanged={() => setRefreshToken((value) => value + 1)}
                onOpen={openObjectById}
                showBackToList={activeRoute.collectionOrigin !== null}
                onBack={backToCollection}
              />
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
