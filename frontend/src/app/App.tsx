import { useEffect, useRef, useState, type CSSProperties } from "react";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { defaultRoute, isAdminRoute, viewRoute } from "@/routing/routes";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";
import { applicationFor } from "@/model/lookup";
import type { ApplicationDefinition, CollectionQueryState, ObjectItem, Workspace } from "@/types";
import { AppShell } from "./AppShell";
import { useRouter, type Router } from "./useRouter";
import { WorkspaceDataProvider, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ChangeSetActions, ChangeSets } from "@/features/workspaces/ChangeSets";
import { PublicationBanner, Publications } from "@/features/workspaces/Publications";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";

export default function App() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const { model, route, error } = router;
  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const changeSetId = route.kind === "list" || route.kind === "detail" ? route.changeSetId : undefined;
  const publicationId = route.kind === "list" || route.kind === "detail" ? route.publicationId : undefined;
  return (
    <WorkspaceDataProvider
      key={`${isAdminRoute(route) ? route.kind : route.workspaceKey}:${changeSetId ?? publicationId ?? "live"}`}
      changeSetId={changeSetId}
      publicationId={publicationId}
      workspaceKey={isAdminRoute(route) ? "" : route.workspaceKey}
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
  const {
    model: currentModel,
    error,
    route,
    navigate,
    replaceRoute,
    lastCollection,
    rememberWorkspace,
    reloadModel,
    defaultWorkspaceKey,
    defaultWorkspaceChanged,
  } = router;
  const data = useWorkspaceData();
  const model = data.model ?? currentModel;
  const [refreshToken, setRefreshToken] = useState(0);
  // Writes made in the collection beside an open record; the record's own writes do not count.
  const [collectionWrites, setCollectionWrites] = useState(0);
  const contextLoading =
    !data.model &&
    !data.loadingError &&
    !!(route && (route.kind === "list" || route.kind === "detail") && (route.changeSetId || route.publicationId));
  const [workspace, setWorkspace] = useState<Workspace>();
  const actionSequence = useRef(0);
  const inspectorWidth = useLocalNumberPreference(
    `rdm:layout:inspector-width:v1:${route && !isAdminRoute(route) ? route.applicationKey : "record"}:${route?.kind === "detail" ? (route.collectionOrigin?.viewKey ?? "record") : "record"}`,
    480,
    360,
    720,
  );

  const previousPin = useRef(data.changeSet?.modelReleaseId);
  useEffect(() => {
    const pin = data.changeSet?.modelReleaseId;
    if (pin && previousPin.current && pin !== previousPin.current && model && route && !isAdminRoute(route)) {
      const selected = applicationFor(model, route.applicationKey) ?? model.applications[0];
      navigate({ ...viewRoute(selected, selected.defaultView, route.workspaceKey), changeSetId: data.changeSet!.id });
    }
    previousPin.current = pin;
  }, [data.changeSet, model, route, navigate]);

  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requested = isAdminRoute(route) ? undefined : applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute =
    data.changeSet &&
    !isAdminRoute(route) &&
    (!requested ||
      (route.kind === "list" && !application.views.some((view) => view.key === route.viewKey)) ||
      (route.kind === "detail" && !model.objectTypes.some((type) => type.key === route.objectTypeKey)))
      ? { ...viewRoute(application, application.defaultView, route.workspaceKey), changeSetId: data.changeSet.id }
      : route;
  // Aliased because the handlers below are hoisted function declarations, which TypeScript types
  // from the declaration rather than from the narrowing performed by the guard above.
  const activeModel = model;

  const changeSetId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.changeSetId : undefined;
  const publicationId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.publicationId : undefined;
  const readOnly =
    Boolean(publicationId) ||
    workspace?.key !== (isAdminRoute(activeRoute) ? "" : activeRoute.workspaceKey) ||
    workspace?.status !== "active";

  function selectApplication(selected: ApplicationDefinition) {
    const workspaceKey = isAdminRoute(activeRoute)
      ? (lastCollection()?.workspaceKey ?? defaultWorkspaceKey)
      : activeRoute.workspaceKey;
    const remembered = lastCollection(selected.key);
    const sameContext =
      remembered?.workspaceKey === workspaceKey &&
      remembered?.changeSetId === changeSetId &&
      remembered?.publicationId === publicationId;
    navigate(
      remembered
        ? {
            ...remembered,
            workspaceKey,
            changeSetId,
            publicationId,
            anchor: sameContext ? remembered.anchor : undefined,
            parentObjectId: sameContext ? remembered.parentObjectId : undefined,
            parentObjectTypeKey: sameContext ? remembered.parentObjectTypeKey : undefined,
          }
        : { ...viewRoute(selected, selected.defaultView, workspaceKey), changeSetId, publicationId },
    );
  }

  function openObject(
    item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">,
    action?: "edit" | "delete",
    source?: "hierarchy" | "beside",
  ) {
    navigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      ...(source === "hierarchy" ? { collectionOrigin: null } : {}),
      ...(source === "beside" ? { fullPage: false } : {}),
      ...(action ? { actionRequest: { action, key: ++actionSequence.current } } : {}),
      workspaceKey: isAdminRoute(activeRoute) ? item.workspaceKey : activeRoute.workspaceKey,
      changeSetId,
      publicationId,
    });
  }

  function openObjectById(
    objectTypeKey: string,
    objectId: string,
    applicationKey = application.key,
    action?: "edit" | "delete",
  ) {
    if (isAdminRoute(activeRoute)) return;
    navigate({
      kind: "detail",
      applicationKey,
      objectTypeKey,
      objectId,
      ...(action ? { actionRequest: { action, key: ++actionSequence.current } } : {}),
      fullPage: activeRoute.kind === "detail" ? activeRoute.fullPage : undefined,
      workspaceKey: activeRoute.workspaceKey,
      changeSetId,
      publicationId,
    });
  }

  function backToCollection() {
    if (isAdminRoute(activeRoute)) return;
    const remembered = activeRoute.kind === "detail" ? activeRoute.collectionOrigin : undefined;
    if (
      remembered?.workspaceKey === activeRoute.workspaceKey &&
      remembered.changeSetId === changeSetId &&
      remembered.publicationId === publicationId
    ) {
      navigate(remembered);
      return;
    }
    const matchingView = application.views.find(
      (view) =>
        activeRoute.kind === "detail" && view.type === "table" && view.objectTypeKey === activeRoute.objectTypeKey,
    );
    navigate({
      ...viewRoute(application, matchingView?.key ?? application.defaultView, activeRoute.workspaceKey),
      changeSetId,
      publicationId,
    });
  }

  function goHome() {
    navigate({
      ...defaultRoute(activeModel),
      changeSetId,
      publicationId,
      workspaceKey: isAdminRoute(activeRoute)
        ? (lastCollection()?.workspaceKey ?? defaultWorkspaceKey)
        : activeRoute.workspaceKey,
    });
  }

  function changeWorkspace(workspaceKey: string) {
    if (isAdminRoute(activeRoute)) return;
    let changed: boolean;
    if (activeRoute.kind === "detail") {
      const matchingView = application.views.find(
        (view) => view.type === "table" && view.objectTypeKey === activeRoute.objectTypeKey,
      );
      const remembered = lastCollection(application.key);
      changed = navigate(
        remembered && remembered.viewKey === matchingView?.key
          ? {
              ...remembered,
              workspaceKey,
              changeSetId: undefined,
              publicationId: undefined,
              anchor: undefined,
              parentObjectId: undefined,
              parentObjectTypeKey: undefined,
            }
          : viewRoute(application, matchingView?.key ?? application.defaultView, workspaceKey),
      );
    } else if (activeRoute.kind === "changeSets" || activeRoute.kind === "publications") {
      changed = navigate({ ...activeRoute, workspaceKey });
    } else {
      changed = navigate({
        ...activeRoute,
        workspaceKey,
        changeSetId: undefined,
        publicationId: undefined,
        anchor: undefined,
        parentObjectId: undefined,
        parentObjectTypeKey: undefined,
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
      {data.loadingError ? (
        <div className="surface panel">
          <Notice
            tone="error"
            title="Could not load this content"
            actions={
              <>
                {data.retryLoading && (
                  <button type="button" className="secondary" onClick={data.retryLoading}>
                    Retry
                  </button>
                )}
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    navigate({
                      ...viewRoute(
                        application,
                        application.defaultView,
                        isAdminRoute(activeRoute) ? defaultWorkspaceKey : activeRoute.workspaceKey,
                      ),
                    })
                  }
                >
                  Return to Live
                </button>
              </>
            }
          >
            {data.loadingError}
          </Notice>
        </div>
      ) : contextLoading ? (
        <div className="surface panel">
          <p>
            Loading{" "}
            {route && (route.kind === "list" || route.kind === "detail") && route.changeSetId
              ? "change set"
              : "publication"}
            …
          </p>
        </div>
      ) : (
        <>
          {data.changeSet && (
            <ChangeSetActions
              readOnly={readOnly}
              onExit={(result) => {
                setMessage(result);
                navigate({ ...viewRoute(application, application.defaultView, data.changeSet!.workspaceKey) });
                setRefreshToken((value) => value + 1);
              }}
              onModelChanged={async () => {
                if (data.reloadChangeSetModel) {
                  await data.reloadChangeSetModel();
                  setRefreshToken((value) => value + 1);
                }
              }}
            />
          )}
          {data.publication && (
            <PublicationBanner
              onExit={() =>
                navigate({
                  kind: "publications",
                  applicationKey: application.key,
                  workspaceKey: data.publication!.workspaceKey,
                })
              }
            />
          )}
          {activeRoute.kind === "models" ? (
            <ModelWorkbench
              route={activeRoute}
              onRouteChange={(next) => navigate(next)}
              onActiveModelChange={reloadModel}
            />
          ) : activeRoute.kind === "workspaces" ? (
            <WorkspaceAdmin
              route={activeRoute}
              onRouteChange={(next) => navigate(next)}
              onDefaultChanged={defaultWorkspaceChanged}
              onWorkspaceDeleted={(workspaceKey) => {
                // Leaving the screen returns to the remembered collection; never to a deleted workspace.
                if (lastCollection()?.workspaceKey === workspaceKey) rememberWorkspace(defaultWorkspaceKey);
              }}
              onOpenWorkspace={(workspaceKey) => {
                if (navigate(viewRoute(application, application.defaultView, workspaceKey))) {
                  rememberWorkspace(workspaceKey);
                  setRefreshToken((value) => value + 1);
                }
              }}
            />
          ) : activeRoute.kind === "changeSets" ? (
            <ChangeSets
              workspaceKey={activeRoute.workspaceKey}
              readOnly={readOnly}
              onOpen={(id) =>
                navigate({
                  ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
                  changeSetId: id,
                })
              }
            />
          ) : activeRoute.kind === "publications" ? (
            <Publications
              workspaceKey={activeRoute.workspaceKey}
              readOnly={readOnly}
              onOpen={(id) =>
                navigate({
                  ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
                  publicationId: id,
                })
              }
              onChangeSetCreated={(id) =>
                navigate({
                  ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
                  changeSetId: id,
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
                    key={`${collection.applicationKey}:${collection.viewKey}:${collection.workspaceKey}:${changeSetId ?? publicationId ?? "live"}:${data.changeSet?.modelReleaseId ?? ""}`}
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
                    selectedObjectTypeKey={activeRoute.kind === "detail" ? activeRoute.objectTypeKey : undefined}
                    onChanged={() => {
                      setRefreshToken((value) => value + 1);
                      setCollectionWrites((value) => value + 1);
                    }}
                    query={collection}
                    onQueryChange={(query: CollectionQueryState) =>
                      navigate(
                        activeRoute.kind === "detail"
                          ? { ...activeRoute, collectionOrigin: { ...collection, ...query } }
                          : { ...collection, ...query },
                      )
                    }
                    onAnchorChange={(anchor) => {
                      if (anchor === collection.anchor) return;
                      replaceRoute(
                        activeRoute.kind === "detail"
                          ? { ...activeRoute, collectionOrigin: { ...collection, anchor } }
                          : { ...collection, anchor },
                      );
                    }}
                    onViewChange={(viewKey) => {
                      const next = viewRoute(collectionApplication, viewKey, collection.workspaceKey);
                      navigate({
                        ...next,
                        changeSetId: collection.changeSetId,
                        publicationId: collection.publicationId,
                        search: collection.search,
                        parentObjectId: collection.parentObjectId,
                        parentObjectTypeKey: collection.parentObjectTypeKey,
                      });
                    }}
                    onOpen={(item, action, options) => openObject(item, action, options?.beside ? "beside" : undefined)}
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
                    key={`${application.key}:${activeRoute.objectTypeKey}:${activeRoute.objectId}:${activeRoute.workspaceKey}:${activeRoute.actionRequest?.key ?? 0}:${data.changeSet?.modelReleaseId ?? ""}`}
                    model={model}
                    application={application}
                    objectTypeKey={activeRoute.objectTypeKey}
                    objectId={activeRoute.objectId}
                    workspaceKey={activeRoute.workspaceKey}
                    inspector={inspector}
                    initialAction={activeRoute.actionRequest?.action}
                    onExpand={inspector ? () => navigate({ ...activeRoute, fullPage: true }) : undefined}
                    readOnly={readOnly}
                    refreshToken={collectionWrites}
                    onChanged={() => setRefreshToken((value) => value + 1)}
                    onOpen={openObjectById}
                    showBackToList={activeRoute.collectionOrigin !== null}
                    onBack={backToCollection}
                  />
                </>
              )}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
