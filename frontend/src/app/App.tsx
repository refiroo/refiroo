import { useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { bulkSelectionFor } from "@/features/objects/SelectionBar";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import {
  changeReviewFor,
  defaultRoute,
  HOME,
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
import { InstanceProductContext, useLoadInstanceProduct } from "./instanceProduct";
import { WorkspaceDataProvider, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ProposeDialog, ownChangeSetText, useOwnChangeSet } from "@/features/workspaces/Proposal";
import { holds, recordWrites } from "@/features/security/permissions";
import { permissionLine } from "@/features/security/permissionText";
import { useMe } from "./useMe";
import { NoWorkspace } from "./NoWorkspace";
import { HomePage } from "@/features/home/HomePage";
import { ChangesPage } from "@/features/changes/ChangesPage";
import { NotificationsPage } from "@/features/inbox/NotificationsPage";
import { continueAddressFor, rememberContinueAddress } from "@/features/home/continueAddress";
import { ChangeSetActions, ChangeSets } from "@/features/workspaces/ChangeSets";
import { ChangeSetReview } from "@/features/workspaces/ChangeSetReview";
import { PublicationBanner, Publications } from "@/features/workspaces/Publications";
import { NavigationGroupPage } from "@/features/objects/NavigationGroupPage";
import { NotInModel } from "@/features/workspaces/NotInModel";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { Card } from "@/ui/Card";
import { ToastProvider, useToast } from "@/ui/Toast";
import { onModelReleaseChanged } from "@/api/expectedRelease";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { JobNotificationsProvider, useJobEnded, useJobNotifications } from "@/features/jobs/JobNotifications";
import { ExportDialog, type ExportStart } from "@/features/jobs/ExportDialog";
import { ImportDialog, type ImportStart } from "@/features/jobs/ImportDialog";
import { LoadWorkbookDialog, type LoadWorkbookStart } from "@/features/ai-tasks/LoadWorkbookDialog";
import { useWorkspaceAssistantOffer } from "@/features/settings/useWorkspaceAiOffer";
import { BrandMascot } from "@/ui/ProductMark";
import { useCapabilities } from "@/features/settings/useSystem";

export default function App() {
  const router = useRouter();
  const { model, route, error } = router;
  // The workspace shown last, kept above the per-workspace content so a switch can say what changed.
  const shownWorkspaceRef = useRef<Workspace | undefined>(undefined);
  const product = useLoadInstanceProduct(router.defaultWorkspaceKey);
  if (!model || !route)
    return (
      <div className="center-message">
        <BrandMascot />
        {error || "Loading the model…"}
      </div>
    );
  // Nothing to browse (0.12 Z5, D326): Settings open; the application's place says so.
  if (router.noWorkspace && !isSettingsRoute(route))
    return (
      <InstanceProductContext.Provider value={product}>
        <NoWorkspace model={model} onNavigate={router.navigate} />
      </InstanceProductContext.Provider>
    );
  // Toasts and the notifications about this tab's jobs live above every page (0.9 J1u).
  return (
    <InstanceProductContext.Provider value={product}>
      <ToastProvider>
        <JobNotificationsProvider model={model} onNavigate={router.navigate}>
          {isSettingsRoute(route) ? (
            // Settings are not workspace data: their own shell, and no workspace or data context (U3).
            <SettingsArea router={router} model={model} route={route} />
          ) : route.kind === "home" ? (
            // Home spans the workspaces the person may browse, each on its own model (0.12 HM1).
            <HomePage model={model} onNavigate={router.navigate} />
          ) : route.kind === "changes" ? (
            // One person's changes span workspaces too, each named from its own model (0.12 Z6).
            <ChangesPage model={model} route={route} onNavigate={router.navigate} />
          ) : route.kind === "notifications" ? (
            // The person's notices span workspaces too (0.12 NT1).
            <NotificationsPage model={model} onNavigate={router.navigate} />
          ) : (
            <WorkspaceDataProvider
              key={`${route.workspaceKey}:${routeChangeSetId(route) ?? routePublicationId(route) ?? "live"}`}
              changeSetId={routeChangeSetId(route)}
              publicationId={routePublicationId(route)}
              workspaceKey={route.workspaceKey}
              model={model}
            >
              <AppContent router={router} route={route} shownWorkspaceRef={shownWorkspaceRef} />
            </WorkspaceDataProvider>
          )}
        </JobNotificationsProvider>
      </ToastProvider>
    </InstanceProductContext.Provider>
  );
}

/**
 * What a switch to `next` changed about the model, for its toast (0.11 M5, D47); nothing when the
 * two workspaces run the same release.
 */
/**
 * The toast for a data write refused because its workspace or change set now runs another release
 * than the page was built on (0.11 M6a, D66); the form shows the refusal itself.
 */
export async function releaseChangedText(refusal: ApiError, read = false): Promise<string> {
  const details = (refusal.details ?? {}) as { workspaceKey?: string; changeSetId?: string; currentReleaseId?: string };
  const [workspace, release] = await Promise.all([
    details.workspaceKey ? api.workspace(details.workspaceKey).catch(() => undefined) : undefined,
    details.currentReleaseId ? api.modelRelease(details.currentReleaseId).catch(() => undefined) : undefined,
  ]);
  const runs = release ? `${release.name} ${release.version}` : "another model release";
  const subject = details.changeSetId
    ? "This change set now uses"
    : `${workspace?.label ?? details.workspaceKey ?? "This workspace"} now runs`;
  return `${subject} ${runs}. ${read ? "Reload to see it." : "Nothing was saved."}`;
}

/** The record a proposal edits, or the type it adds one of (0.12 Z5, D324). */
interface ProposalTarget {
  applicationKey: string;
  objectTypeKey: string;
  objectId?: string;
}

export function modelChangeText(previous: Workspace, next: Workspace): string | undefined {
  if (previous.key === next.key || previous.model.releaseId === next.model.releaseId) return undefined;
  const runs = `${next.label} runs ${next.model.releaseName} ${next.model.releaseVersion}`;
  return previous.model.releaseKey === next.model.releaseKey
    ? `${runs}, another release of the model ${previous.label} runs (${previous.model.releaseVersion}).`
    : `${runs}, a different model from ${previous.label}'s: its applications and navigation are shown.`;
}

function AppContent({
  router,
  route,
  shownWorkspaceRef,
}: {
  router: Router;
  route: ApplicationRoute;
  shownWorkspaceRef: RefObject<Workspace | undefined>;
}) {
  const { model: currentModel, error, navigate, replaceRoute, lastCollection, rememberWorkspace, problem } = router;
  const data = useWorkspaceData();
  const toast = useToast();
  // A write built on a release the workspace no longer runs, or a read the release changed under
  // (0.11 N1): say so once, with Reload (M6a, D66).
  useEffect(
    () =>
      onModelReleaseChanged((refusal, read) => {
        releaseChangedText(refusal, read).then((text) =>
          toast(text, { tone: "info", actions: [{ label: "Reload", href: window.location.href }] }),
        );
      }),
    [toast],
  );
  const model = data.model ?? currentModel;
  const [refreshToken, setRefreshToken] = useState(0);
  // Writes made in the collection beside an open record; the record's own writes do not count.
  const [collectionWrites, setCollectionWrites] = useState(0);
  // Export is offered while the deployment lets jobs be created (0.9 J1u, D57).
  const { capabilities } = useCapabilities();
  const notifications = useJobNotifications();
  const [exportStart, setExportStart] = useState<ExportStart>();
  // What the shown collection would export: the workspace ⋯ menu's Export keeps it (0.16 WM1).
  const collectionExport = useRef<() => ExportStart>(undefined);
  const [importStart, setImportStart] = useState<ImportStart>();
  // The AI assistant loads a workbook where a provider is set and the person may use it (0.16 AP6a).
  const aiOffer = useWorkspaceAssistantOffer();
  const [workbookStart, setWorkbookStart] = useState<LoadWorkbookStart>();
  const importTrigger = useRef<HTMLElement | null>(null);
  // The page's data Import was opened on, kept for the ordinary import chosen from the assistant's dialog.
  const importContext = useRef<ImportStart["context"]>(undefined);
  // Closing either dialog returns focus to the control that opened Import: a dialog that replaced the
  // other has no opener of its own to return to.
  function closeImport() {
    setImportStart(undefined);
    setWorkbookStart(undefined);
    const trigger = importTrigger.current;
    // The menu item Import was chosen from is gone: the workspace menu's button stands for it.
    window.setTimeout(
      () =>
        (trigger?.isConnected
          ? trigger
          : document.querySelector<HTMLElement>(".workspace-actions .menu-trigger")
        )?.focus(),
      0,
    );
  }
  // An import or a bulk change (0.9 K2) this tab started that wrote into the data shown reloads it,
  // and a change set's version. A bulk change may end after failing part way, its chunks applied.
  useJobEnded((job) => {
    if (job.workspaceKey !== route.workspaceKey) return;
    // An AI proposal job that stopped part way keeps what it proposed (0.16 AP2).
    const wrote =
      job.kind === "import"
        ? job.state === "completed"
        : job.kind === "aiProposal"
          ? (job.aiProposal?.proposed ?? 0) > 0
          : job.kind === "batch" && job.counts.applied > 0;
    if (!wrote) return;
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
  // What the person may do here (0.12 Z5): record writes of this context, and in live data without
  // Edit live but with Work in change sets, a proposal through their own change set (D324).
  const writes = useRecordWrites();
  const permissions = data.permissions;
  const me = useMe();
  const inLive = !routeChangeSetId(route) && !routePublicationId(route);
  const workspaceActive = workspace?.key === route.workspaceKey && workspace.status === "active";
  const proposals = recordWrites(permissions, "change-sets");
  const proposing = inLive && workspaceActive && !writes.any && proposals.any;
  const own = useOwnChangeSet(route.workspaceKey, me?.id, proposing, refreshToken);
  const [proposal, setProposal] = useState<ProposalTarget>();
  useEffect(() => {
    if (!workspace) return;
    const previous = shownWorkspaceRef.current;
    shownWorkspaceRef.current = workspace;
    const text = previous && modelChangeText(previous, workspace);
    if (text) toast(text);
  }, [workspace, shownWorkspaceRef, toast]);
  const inspectorWidth = useLocalNumberPreference(
    `rdm:layout:inspector-width:v1:${route.applicationKey}:${route.kind === "detail" ? (route.collectionOrigin?.viewKey ?? "record") : "record"}`,
    480,
    360,
    720,
  );

  // The change set was published or discarded while open: its page becomes the live data.
  const changeSetGone = data.changeSetGone;
  useEffect(() => {
    if (!changeSetGone || !model) return;
    const selected = applicationFor(model, route.applicationKey) ?? model.applications[0];
    toast("This change set is no longer open. Showing live data.");
    navigate({ ...viewRoute(selected, selected.defaultView, route.workspaceKey) });
    setRefreshToken((value) => value + 1);
  }, [changeSetGone, model, route, navigate, toast]);

  const previousPin = useRef(data.changeSet?.modelReleaseId);
  useEffect(() => {
    const pin = data.changeSet?.modelReleaseId;
    if (pin && previousPin.current && pin !== previousPin.current && model) {
      const selected = applicationFor(model, route.applicationKey) ?? model.applications[0];
      navigate({ ...viewRoute(selected, selected.defaultView, route.workspaceKey), changeSetId: data.changeSet!.id });
    }
    previousPin.current = pin;
  }, [data.changeSet, model, route, navigate]);

  // Where Home's "Continue where you left off" leads (0.12 HM1, D334): the last data address opened.
  const changeSetName = data.changeSet?.name;
  useEffect(() => {
    if (!me || !model || workspace?.key !== route.workspaceKey || !applicationFor(model, route.applicationKey)) return;
    rememberContinueAddress(me.id, continueAddressFor(model, route, workspace.label, changeSetName));
  }, [me, model, route, workspace, changeSetName]);

  if (!model)
    return (
      <div className="center-message">
        <BrandMascot />
        {error || "Loading the model…"}
      </div>
    );
  const requested = applicationFor(model, route.applicationKey);
  const application = requested ?? model.applications[0];
  const activeRoute: ApplicationRoute =
    data.changeSet &&
    (!requested ||
      (route.kind === "list" && !application.views.some((view) => view.key === route.viewKey)) ||
      (route.kind === "detail" && !model.objectTypes.some((type) => type.key === route.objectTypeKey)))
      ? { ...viewRoute(application, application.defaultView, route.workspaceKey), changeSetId: data.changeSet.id }
      : route;
  const changeSetId = routeChangeSetId(activeRoute);
  const publicationId = routePublicationId(activeRoute);
  // The data shown cannot be written whoever reads it: a publication, a retired workspace.
  const contextReadOnly =
    Boolean(publicationId) || workspace?.key !== activeRoute.workspaceKey || workspace?.status !== "active";
  // And the person may write no record here (0.12 Z5, D323): every write affordance is left out.
  const readOnly = contextReadOnly || !writes.any;
  // Import loads into the data the page shows, so it is offered where that data can be written (D89)
  // and the person holds Bulk and import, which every import needs (Z5, D323).
  const onImport =
    capabilities?.integrationJobs.createJobs && !contextReadOnly && holds(permissions, "bulk")
      ? () => {
          importTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
          const context = {
            workspaceKey: activeRoute.workspaceKey,
            ...(data.changeSet
              ? { changeSet: { id: data.changeSet.id, name: data.changeSet.name, version: data.changeSet.version } }
              : {}),
          };
          // Where the assistant is offered it is the way in; the ordinary import is chosen from its dialog.
          if (aiOffer?.assistant) {
            importContext.current = context;
            setWorkbookStart({ workspaceKey: context.workspaceKey });
            return;
          }
          setImportStart({ context });
        }
      : undefined;

  const exportFromMenu =
    capabilities?.integrationJobs.createJobs && application
      ? () =>
          setExportStart(
            collectionExport.current?.() ?? {
              workspaceKey: activeRoute.workspaceKey,
              changeSetId,
              publicationId,
              objectTypeKeys: application.objectTypeKeys,
              selected: application.objectTypeKeys,
            },
          )
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
    navigate(HOME);
  }

  function changeWorkspace(workspaceKey: string) {
    // The page goes along where the other model has it; where not, its start opens: nothing was asked for.
    const carry = (next: Parameters<typeof navigate>[0]) => navigate(next, false, true);
    let changed: boolean;
    if (activeRoute.kind === "detail") {
      const matchingView = application.views.find(
        (view) => view.type === "table" && view.objectTypeKey === activeRoute.objectTypeKey,
      );
      const remembered = lastCollection(application.key);
      changed = carry(
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
      changed = carry({ ...activeRoute, workspaceKey });
    } else if (activeRoute.kind === "group") {
      changed = carry({ ...activeRoute, workspaceKey, changeSetId: undefined, publicationId: undefined });
    } else if (activeRoute.kind === "changeSetChanges") {
      // A change set belongs to one workspace; another workspace opens its live data.
      changed = carry(viewRoute(application, application.defaultView, workspaceKey));
    } else {
      changed = carry({
        ...activeRoute,
        workspaceKey,
        changeSetId: undefined,
        publicationId: undefined,
        anchor: undefined,
        parentObjectId: undefined,
        parentObjectTypeKey: undefined,
      });
    }
    // The other workspace's page mounts afresh under its own data provider, so nothing here reloads:
    // a reload would read the old workspace again while the other's model loads (0.11 M6, D58).
    if (changed) rememberWorkspace(workspaceKey);
  }

  const collection =
    activeRoute.kind === "list"
      ? activeRoute
      : activeRoute.kind === "detail"
        ? activeRoute.collectionOrigin
        : undefined;
  const collectionApplication = collection ? applicationFor(model, collection.applicationKey) : undefined;
  const collectionView = collection
    ? (collectionApplication?.views.find((view) => view.key === collection.viewKey) ?? collectionApplication?.views[0])
    : undefined;
  // Records are selected for a bulk change where the data can be written and jobs created (K1,
  // D105), by someone holding Bulk and import for the collection's records (Z5, D323).
  const bulkWrites = recordWrites(permissions, "bulk");
  const bulkSelection = bulkSelectionFor(
    capabilities,
    contextReadOnly ||
      !collectionApplication ||
      !(collectionView && "objectTypeKey" in collectionView && collectionView.objectTypeKey
        ? bulkWrites.permits(collectionApplication.key, collectionView.objectTypeKey)
        : bulkWrites.any),
  );

  /** Edit a record, or add one, through the person's own change set (D324). */
  function propose(target: ProposalTarget) {
    if (own.changeSet) openProposal(own.changeSet.id, target);
    else setProposal(target);
  }

  function openProposal(id: string, target: ProposalTarget) {
    if (target.objectId)
      navigate({
        kind: "detail",
        applicationKey: target.applicationKey,
        objectTypeKey: target.objectTypeKey,
        objectId: target.objectId,
        actionRequest: { action: "edit", key: ++actionSequence.current },
        workspaceKey: activeRoute.workspaceKey,
        changeSetId: id,
      });
    else if (collection)
      navigate({
        ...collection,
        anchor: undefined,
        changeSetId: id,
        createRequest: { key: ++actionSequence.current },
      });
  }
  const proposeIn = (applicationKey: string, objectTypeKey: string) =>
    proposing && proposals.permits(applicationKey, objectTypeKey)
      ? (objectId?: string) => propose({ applicationKey, objectTypeKey, objectId })
      : undefined;
  const permissionNote = data.changeSet
    ? permissionLine(model, {
        context: "changeSet",
        workspaceLabel: workspace?.label ?? activeRoute.workspaceKey,
        writes: permissions ? writes : undefined,
        proposing: false,
        publishes: holds(permissions, "publish"),
      })
    : !publicationId && !contextReadOnly
      ? permissionLine(model, {
          context: "live",
          workspaceLabel: workspace?.label ?? activeRoute.workspaceKey,
          writes: permissions ? writes : undefined,
          proposing,
          publishes: holds(permissions, "publish"),
        })
      : undefined;
  const ownText = proposing ? ownChangeSetText(own) : undefined;
  const ownChangeSet = ownText && own.changeSet && (
    <button
      type="button"
      className="secondary"
      onClick={() =>
        navigate({
          ...viewRoute(application, application.defaultView, activeRoute.workspaceKey),
          changeSetId: own.changeSet!.id,
        })
      }
    >
      {ownText}
    </button>
  );
  const hasDetail = activeRoute.kind === "detail";
  const inspector = hasDetail && Boolean(collection) && activeRoute.fullPage === false;
  // A table view's page is fitted to the window and only its rows scroll (0.12 LS1, D371).
  const fillPage = activeRoute.kind === "list" && !problem && collectionView?.type === "table";
  // The change set's or publication's own bar sits in the shell's data-context band once loaded.
  const contextActions =
    data.loadingError || contextLoading ? undefined : data.changeSet ? (
      <ChangeSetActions
        readOnly={contextReadOnly}
        reviewing={activeRoute.kind === "changeSetChanges"}
        onReview={() => navigate(changeReviewFor(application.key, data.changeSet!.workspaceKey, data.changeSet!.id))}
        onExit={(result) => {
          // A confirmation of leaving the change set, shown once (reported 2026-10-15: a page notice
          // stayed on every page until a reload).
          toast(result);
          navigate({ ...viewRoute(application, application.defaultView, data.changeSet!.workspaceKey) });
          setRefreshToken((value) => value + 1);
        }}
        canMigrate={Boolean(capabilities?.modelAdmin.activate && capabilities?.integrationJobs.createJobs)}
        canMove={Boolean(capabilities?.integrationJobs.createJobs)}
        onMigrationStarted={(jobId) => navigate({ kind: "settings", page: "model", migrationJobId: jobId })}
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
      nothingCurrent={Boolean(problem)}
      fill={fillPage}
      refreshToken={refreshToken}
      onChanged={() => setRefreshToken((value) => value + 1)}
      onNavigate={navigate}
      onSelectApplication={selectApplication}
      onChangeWorkspace={changeWorkspace}
      workspace={workspace}
      onWorkspaceResolved={setWorkspace}
      onHome={goHome}
      onImport={onImport}
      onExport={exportFromMenu}
      onOpenObject={(item) => openObject(item, undefined, "hierarchy")}
      contextActions={contextActions}
      permissionNote={permissionNote}
      ownChangeSet={ownChangeSet}
    >
      {problem ? (
        <NotInModel
          key={`${problem.kind}:${problem.workspaceKey}`}
          problem={problem}
          model={model}
          workspace={workspace?.key === activeRoute.workspaceKey ? workspace : undefined}
          startRoute={defaultRoute(model, activeRoute.workspaceKey)}
          onNavigate={navigate}
        />
      ) : data.loadingError ? (
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
                if (anchor !== activeRoute.anchor) replaceRoute({ ...activeRoute, anchor }, { silent: true });
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
              onDecided={(result) => {
                // The approved change set is gone, as after publishing from its bar.
                toast(result);
                navigate({ ...viewRoute(application, application.defaultView, activeRoute.workspaceKey) });
                setRefreshToken((value) => value + 1);
              }}
            />
          ) : activeRoute.kind === "changeSets" ? (
            <ChangeSets
              workspaceKey={activeRoute.workspaceKey}
              readOnly={contextReadOnly}
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
              readOnly={contextReadOnly}
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
                    view={collectionView!}
                    workspaceKey={collection.workspaceKey}
                    readOnly={readOnly}
                    onPropose={proposeIn}
                    createRequest={activeRoute.kind === "list" ? activeRoute.createRequest?.key : undefined}
                    refreshToken={refreshToken}
                    selectedId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
                    selectedObjectTypeKey={activeRoute.kind === "detail" ? activeRoute.objectTypeKey : undefined}
                    onChanged={() => {
                      setRefreshToken((value) => value + 1);
                      setCollectionWrites((value) => value + 1);
                    }}
                    query={collection}
                    onExportContext={(read) => {
                      collectionExport.current = read;
                    }}
                    bulkSelection={bulkSelection}
                    fill={fillPage}
                    onQueryChange={(query: CollectionQueryState) =>
                      navigate(
                        activeRoute.kind === "detail"
                          ? { ...activeRoute, collectionOrigin: { ...collection, ...query } }
                          : { ...collection, ...query },
                      )
                    }
                    onAnchorChange={(anchor) => {
                      if (anchor === collection.anchor) return;
                      // Silent: the address follows the reader without drawing the list again.
                      replaceRoute(
                        activeRoute.kind === "detail"
                          ? { ...activeRoute, collectionOrigin: { ...collection, anchor } }
                          : { ...collection, anchor },
                        { silent: true },
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
                    onShowProposed={(changeSetId) =>
                      navigate({
                        ...collection,
                        changeSetId,
                        publicationId: undefined,
                        mappingState: undefined,
                        mappingProposed: true,
                        anchor: undefined,
                      })
                    }
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
                    onPropose={proposeIn}
                    refreshToken={collectionWrites}
                    onChanged={() => setRefreshToken((value) => value + 1)}
                    onOpen={openObjectById}
                    onOpenChanges={navigate}
                    onTypeChanged={(objectTypeKey) => navigate({ ...activeRoute, objectTypeKey }, true)}
                    onOtherApplication={(applicationKey) => navigate({ ...activeRoute, applicationKey }, true)}
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
      {proposal && (
        <ProposeDialog
          workspaceKey={activeRoute.workspaceKey}
          workspaceLabel={workspace?.label ?? activeRoute.workspaceKey}
          personName={me?.name}
          onClose={() => setProposal(undefined)}
          onStarted={(changeSet) => {
            setProposal(undefined);
            openProposal(changeSet.id, proposal);
          }}
        />
      )}
      {importStart && (
        <ImportDialog
          model={model}
          start={importStart}
          onClose={closeImport}
          onStarted={(job) => {
            setImportStart(undefined);
            // The preview is the screen the user came for: its page opens at once (D91).
            notifications.follow(job, { announce: false });
            navigate({ kind: "settings", page: "jobs", jobId: job.id });
          }}
        />
      )}
      {workbookStart && aiOffer?.assistant && (
        <LoadWorkbookDialog
          start={workbookStart}
          onClose={closeImport}
          onImportManually={(file) => {
            // The person chose the ordinary import: its dialog takes this one's place with the same data.
            setImportStart({ context: importContext.current, ...(file ? { file } : {}) });
            setWorkbookStart(undefined);
          }}
          onStarted={(task) => {
            setWorkbookStart(undefined);
            navigate({ kind: "settings", page: "ai-tasks", taskId: task.id });
          }}
        />
      )}
    </AppShell>
  );
}
