import { useEffect, useRef, useState, type CSSProperties } from "react";
import { bulkSelectionFor } from "@/features/objects/SelectionBar";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import {
  changeReviewFor,
  defaultRoute,
  isSettingsRoute,
  routeChangeSetId,
  routePublicationId,
  viewRoute,
} from "@/routing/routes";
import { applicationFor } from "@/model/lookup";
import type { ApplicationDefinition, ApplicationRoute, CollectionQueryState, ObjectItem, Workspace } from "@/types";
import { AppShell } from "./AppShell";
import { SettingsArea } from "./SettingsArea";
import { useRouter, type Router } from "./useRouter";
import { WorkspaceDataProvider, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ChangeSetActions, ChangeSets } from "@/features/workspaces/ChangeSets";
import { ChangeSetReview } from "@/features/workspaces/ChangeSetReview";
import { PublicationBanner, Publications } from "@/features/workspaces/Publications";
import { NavigationGroupPage } from "@/features/objects/NavigationGroupPage";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { Card } from "@/ui/Card";
import { ToastProvider } from "@/ui/Toast";
import { JobNotificationsProvider, useJobEnded, useJobNotifications } from "@/features/jobs/JobNotifications";
import { ExportDialog, type ExportStart } from "@/features/jobs/ExportDialog";
import { ImportDialog, type ImportStart } from "@/features/jobs/ImportDialog";
import { useCapabilities } from "@/features/settings/useSystem";

export default function App() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const { model, route, error } = router;
  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  // Toasts and the notifications about this tab's jobs live above every page (0.9 J1u).
  return (
    <ToastProvider>
      <JobNotificationsProvider model={model} onNavigate={router.navigate}>
        {isSettingsRoute(route) ? (
          // Settings are not workspace data: their own shell, and no workspace or data context (U3).
          <SettingsArea router={router} model={model} route={route} />
        ) : (
          <WorkspaceDataProvider
            key={`${route.workspaceKey}:${routeChangeSetId(route) ?? routePublicationId(route) ?? "live"}`}
            changeSetId={routeChangeSetId(route)}
            publicationId={routePublicationId(route)}
            workspaceKey={route.workspaceKey}
            model={model}
          >
            <AppContent router={router} route={route} message={message} setMessage={setMessage} />
          </WorkspaceDataProvider>
        )}
      </JobNotificationsProvider>
    </ToastProvider>
  );
}

function AppContent({
  router,
  route,
  message,
  setMessage,
}: {
  router: Router;
  route: ApplicationRoute;
  message: string;
  setMessage: (message: string) => void;
}) {
  const { model: currentModel, error, navigate, replaceRoute, lastCollection, rememberWorkspace } = router;
  const data = useWorkspaceData();
  const model = data.model ?? currentModel;
  const [refreshToken, setRefreshToken] = useState(0);
  // Writes made in the collection beside an open record; the record's own writes do not count.
  const [collectionWrites, setCollectionWrites] = useState(0);
  // Export is offered while the deployment lets jobs be created (0.9 J1u, D57).
  const { capabilities } = useCapabilities();
  const notifications = useJobNotifications();
  const [exportStart, setExportStart] = useState<ExportStart>();
  const onExport = capabilities?.integrationJobs.createJobs ? setExportStart : undefined;
  const [importStart, setImportStart] = useState<ImportStart>();
  // An import or a bulk change (0.9 K2) this tab started that wrote into the data shown reloads it,
  // and a change set's version. A bulk change may end after failing part way, its chunks applied.
  useJobEnded((job) => {
    if (job.workspaceKey !== route.workspaceKey) return;
    if (job.kind === "import" ? job.state !== "completed" : job.kind !== "batch" || job.counts.applied === 0) return;
    if ((job.changeSetId ?? undefined) !== routeChangeSetId(route)) return;
    setRefreshToken((value) => value + 1);
    data.refresh?.().catch(() => undefined);
  });
  const contextLoading =
    !data.model &&
    !data.loadingError &&
    !!(
      route &&
      (routeChangeSetId(route) || ((route.kind === "list" || route.kind === "detail") && route.publicationId))
    );
  const [workspace, setWorkspace] = useState<Workspace>();
  const actionSequence = useRef(0);
  const inspectorWidth = useLocalNumberPreference(
    `rdm:layout:inspector-width:v1:${route.applicationKey}:${route.kind === "detail" ? (route.collectionOrigin?.viewKey ?? "record") : "record"}`,
    480,
    360,
    720,
  );

  const previousPin = useRef(data.changeSet?.modelReleaseId);
  useEffect(() => {
    const pin = data.changeSet?.modelReleaseId;
    if (pin && previousPin.current && pin !== previousPin.current && model) {
      const selected = applicationFor(model, route.applicationKey) ?? model.applications[0];
      navigate({ ...viewRoute(selected, selected.defaultView, route.workspaceKey), changeSetId: data.changeSet!.id });
    }
    previousPin.current = pin;
  }, [data.changeSet, model, route, navigate]);

  if (!model) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requested = applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute: ApplicationRoute =
    data.changeSet &&
    (!requested ||
      (route.kind === "list" && !application.views.some((view) => view.key === route.viewKey)) ||
      (route.kind === "detail" && !model.objectTypes.some((type) => type.key === route.objectTypeKey)))
      ? { ...viewRoute(application, application.defaultView, route.workspaceKey), changeSetId: data.changeSet.id }
      : route;
  // Aliased because the handlers below are hoisted function declarations, which TypeScript types
  // from the declaration rather than from the narrowing performed by the guard above.
  const activeModel = model;

  const changeSetId = routeChangeSetId(activeRoute);
  const publicationId = routePublicationId(activeRoute);
  const readOnly =
    Boolean(publicationId) || workspace?.key !== activeRoute.workspaceKey || workspace?.status !== "active";
  // Records are selected for a bulk change where the data can be written and jobs created (K1, D105).
  const bulkSelection = bulkSelectionFor(capabilities, readOnly);
  // Import loads into the data the page shows, so it is offered where that data can be written (D89).
  const onImport =
    capabilities?.integrationJobs.createJobs && !readOnly
      ? () =>
          setImportStart({
            context: {
              workspaceKey: activeRoute.workspaceKey,
              ...(data.changeSet
                ? { changeSet: { id: data.changeSet.id, name: data.changeSet.name, version: data.changeSet.version } }
                : {}),
            },
          })
      : undefined;

  function selectApplication(selected: ApplicationDefinition) {
    const workspaceKey = activeRoute.workspaceKey;
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
      workspaceKey: activeRoute.workspaceKey,
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
      workspaceKey: activeRoute.workspaceKey,
    });
  }

  function changeWorkspace(workspaceKey: string) {
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
    } else if (activeRoute.kind === "group") {
      changed = navigate({ ...activeRoute, workspaceKey, changeSetId: undefined, publicationId: undefined });
    } else if (activeRoute.kind === "changeSetChanges") {
      // A change set belongs to one workspace; another workspace opens its live data.
      changed = navigate(viewRoute(application, application.defaultView, workspaceKey));
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
  // The change set's or publication's own bar sits in the shell's data-context band once loaded.
  const contextActions =
    data.loadingError || contextLoading ? undefined : data.changeSet ? (
      <ChangeSetActions
        readOnly={readOnly}
        reviewing={activeRoute.kind === "changeSetChanges"}
        onReview={() => navigate(changeReviewFor(application.key, data.changeSet!.workspaceKey, data.changeSet!.id))}
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
    ) : data.publication ? (
      <PublicationBanner
        onExit={() =>
          navigate({
            kind: "publications",
            applicationKey: application.key,
            workspaceKey: data.publication!.workspaceKey,
          })
        }
      />
    ) : undefined;
  return (
    <AppShell
      model={model}
      application={application}
      activeRoute={activeRoute}
      refreshToken={refreshToken}
      onChanged={() => setRefreshToken((value) => value + 1)}
      onNavigate={navigate}
      onSelectApplication={selectApplication}
      onChangeWorkspace={changeWorkspace}
      workspace={workspace}
      onWorkspaceResolved={setWorkspace}
      onHome={goHome}
      onOpenObject={(item) => openObject(item, undefined, "hierarchy")}
      contextActions={contextActions}
    >
      {message && <Notice tone="success">{message}</Notice>}
      {data.loadingError ? (
        <Card flush className="panel">
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
                      ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
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
        </Card>
      ) : contextLoading ? (
        <Card flush className="panel">
          <p>Loading {route && routeChangeSetId(route) ? "change set" : "publication"}…</p>
        </Card>
      ) : (
        <>
          {activeRoute.kind === "changeSetChanges" ? (
            <ChangeSetReview
              model={model}
              route={activeRoute}
              refreshToken={refreshToken}
              onRouteChange={(next) => navigate(next)}
              onAnchorChange={(anchor) => {
                if (anchor !== activeRoute.anchor) replaceRoute({ ...activeRoute, anchor });
              }}
              onOpenRecord={(change) =>
                navigate({
                  kind: "detail",
                  applicationKey: change.applicationKey,
                  objectTypeKey: change.objectTypeKey,
                  objectId: change.objectId,
                  workspaceKey: activeRoute.workspaceKey,
                  changeSetId: activeRoute.changeSetId,
                })
              }
              onBack={() =>
                navigate({
                  ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
                  changeSetId: activeRoute.changeSetId,
                })
              }
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
          ) : activeRoute.kind === "group" ? (
            <NavigationGroupPage
              key={`${application.key}:${activeRoute.groupKey}`}
              model={model}
              application={application}
              groupKey={activeRoute.groupKey}
              onOpenCollection={(viewKey) =>
                navigate({
                  ...viewRoute(application, viewKey, activeRoute.workspaceKey),
                  changeSetId,
                  publicationId,
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
                    onExport={onExport}
                    onImport={onImport}
                    bulkSelection={bulkSelection}
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
                    onReviewChanges={
                      data.changeSet
                        ? () =>
                            navigate(
                              changeReviewFor(
                                collectionApplication.key,
                                data.changeSet!.workspaceKey,
                                data.changeSet!.id,
                              ),
                            )
                        : undefined
                    }
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
                    onTypeChanged={(objectTypeKey) => navigate({ ...activeRoute, objectTypeKey }, true)}
                    showBackToList={activeRoute.collectionOrigin !== null}
                    onBack={backToCollection}
                  />
                </>
              )}
            </div>
          )}
        </>
      )}
      {exportStart && (
        <ExportDialog
          model={model}
          start={exportStart}
          onClose={() => setExportStart(undefined)}
          onStarted={(job) => {
            setExportStart(undefined);
            notifications.follow(job);
          }}
        />
      )}
      {importStart && (
        <ImportDialog
          model={model}
          start={importStart}
          onClose={() => setImportStart(undefined)}
          onStarted={(job) => {
            setImportStart(undefined);
            // The preview is the screen the user came for: its page opens at once (D91).
            notifications.follow(job, { announce: false });
            navigate({ kind: "settings", page: "jobs", jobId: job.id });
          }}
        />
      )}
    </AppShell>
  );
}
