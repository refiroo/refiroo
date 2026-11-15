/**
/**
 * Settings › Model (Track U U3, U-D10 as revised 2026-10-06; 0.11 M5, D50; 0.11 M6): the page opens
 * with the list of models (EntityList): the default workspace's model, the others in use, the rest,
 * and the drafts of models not installed yet. A model in the address opens in a card under a bar
 * (Back to all models) with tabs: where it runs, its releases, its drafts and its structure; a
 * release or draft opens in the card under a bar that leads back to the tab it came from.
 * Activation goes into one workspace through one dialog (D51).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted, plural } from "@/lib/count";
import { newestFirst } from "@/model/newestFirst";
import type {
  HeldAnywhere,
  CapabilitiesResponse,
  ModelDraft,
  ModelRelease,
  ModelReleaseSummary,
  ModelTab,
  RouteState,
  SettingsRoute,
  Workspace,
  WorkspaceModelActivation,
} from "@/types";
import { ActivateDialog } from "@/features/model-admin/ActivateDialog";
import { CreateDraftDialog, type CreateDraftSeed } from "@/features/model-admin/CreateDraftDialog";
import { MigrationPage } from "@/features/model-admin/MigrationPage";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";
import { MODEL_TAB_LABELS, ModelDetail, ModelNamePage, runningWorkspaces } from "@/features/model-admin/ModelPage";
import { settingsHead } from "@/ui/settingsNavigation";
import { releasesByModel, type ModelLine } from "@/features/model-admin/modelLines";
import { EntityList, type EntityGroup, type EntityRow } from "@/ui/EntityList";
import { Icon } from "@/ui/Icon";
import { StatusPill } from "@/ui/StatusPill";
import { changeReviewFor } from "@/routing/routes";
import { Trail, TrailLink, crumbs } from "@/ui/Trail";
import { EmptyState } from "@/ui/EmptyState";
import { SearchField } from "@/ui/SearchField";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsPanel, SettingsTile, SettingsTools } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { Notice } from "@/ui/Notice";
import { allWorkspaces } from "@/api/allWorkspaces";
import { everyPage } from "@/lib/everyPage";
import { fetchHeldAnywhere } from "@/state/permissions";

type ModelsRoute = Extract<SettingsRoute, { page: "model" }>;

const MODEL: ModelsRoute = { kind: "settings", page: "model" };

function appendUnique<T extends { id: string }>(current: T[], incoming: T[]) {
  const ids = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !ids.has(item.id))];
}

/**
 * Every installed release, oldest first (releases are few: one line per model's versions); with
 * `usable`, those that may be chosen (0.12 MR1).
 */
const allReleases = (usable = false) => everyPage((cursor) => api.modelReleases({ cursor, pageSize: 500, usable }));

/** Every draft, newest first; a draft is shown under the model it was started from (M6). */
const allDrafts = () => everyPage((cursor) => api.modelDrafts({ cursor }));

export function ModelWorkbench({
  route,
  onRouteChange,
  onActiveModelChange,
  onOpenWorkspace,
  onReturnToWorkspace,
  onReturnToTask,
  onOpenChangeSet,
  onOpenApplication,
  onOpenChangeSetReview,
}: {
  route: ModelsRoute;
  onRouteChange: (route: ModelsRoute) => void;
  /** Opens a workspace in Settings › Workspaces, from the workspaces a model runs in (M6). */
  onOpenWorkspace?: (workspaceKey: string) => void;
  /** A migration opened from a workspace goes back to its data (0.16 WM1). */
  onReturnToWorkspace?: (workspaceKey: string) => void;
  /** A migration an assistant task proposed goes back to its proposal (0.16 AP12). */
  onReturnToTask?: (taskId: string) => void;
  /** A change set moved onto its workspace's release (0.11 V3): open it. */
  onOpenChangeSet?: (workspaceKey: string, changeSetId: string) => void;
  /** The way back to a change set from a migration its banner started. */
  onOpenChangeSetReview?: (route: Extract<RouteState, { kind: "changeSetChanges" }>) => void;
  /** A migration that published a change set is done: open the application it came from. */
  onOpenApplication?: (workspaceKey: string, applicationKey: string) => void;
  /** A workspace's model changed: the shell forgets the model it held for it (D49). */
  onActiveModelChange?: (workspaceKey: string) => Promise<unknown>;
}) {
  const toast = useToast();
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  // What the person may do here (0.12 Z5, D323): drafts with Model authoring; installing (at the
  // instance), activating and migrating (in a workspace) with Model release.
  const [held, setHeld] = useState<HeldAnywhere[]>([]);
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  // The releases an activation may choose: active, of a schema this version reads (0.12 MR1).
  const [usableIds, setUsableIds] = useState<Set<string>>(new Set());
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [defaultWorkspaceKey, setDefaultWorkspaceKey] = useState("");
  const [activating, setActivating] = useState<{ workspaceKey?: string; releaseId?: string }>();
  const [error, setError] = useState("");
  const [creating, setCreating] = useState<CreateDraftSeed>();
  const [createReleaseId, setCreateReleaseId] = useState("");
  const newDraftButtonRef = useRef<HTMLButtonElement>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!capabilities?.modelAdmin.manageDrafts || !route.draftId || drafts.some((item) => item.id === route.draftId))
      return;
    let cancelled = false;
    api
      .modelDraft(route.draftId)
      .then((draft) => {
        if (!cancelled) setDrafts((items) => appendUnique(items, [draft]));
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [capabilities?.modelAdmin.manageDrafts, route.draftId]);

  async function load() {
    setError("");
    try {
      const [groups, caps, installed, usable, activeWorkspaces, state] = await Promise.all([
        // The person's groups, as the page keeps them: a failed read offers nothing.
        fetchHeldAnywhere().catch(() => []),
        api.capabilities(),
        allReleases(),
        allReleases(true),
        // Workspaces are few (ADR-042); retired ones keep their release and take no activation.
        allWorkspaces({ status: "active" }),
        api.workspaceRuntimeState(),
      ]);
      // The drafts first, so the page never shows a model's count before its drafts arrived.
      const authors = groups.some((group) => group.key === "model-authoring");
      const loadedDrafts = caps.modelAdmin.manageDrafts && authors ? await allDrafts() : [];
      setHeld(groups);
      setDrafts(loadedDrafts);
      setCapabilities(caps);
      setReleases(installed);
      setUsableIds(new Set(usable.map((release) => release.id)));
      setWorkspaces(activeWorkspaces);
      setDefaultWorkspaceKey(state.defaultWorkspaceKey);
      const defaultRelease = activeWorkspaces.find((item) => item.key === state.defaultWorkspaceKey)?.model.releaseId;
      setCreateReleaseId((current) => current || defaultRelease || "");
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function startFromRelease(release: ModelRelease) {
    setCreating({ name: `${release.name} draft`, releaseId: release.id });
  }

  async function reloadDraft(id: string) {
    const loaded = await api.modelDraft(id);
    setDrafts((items) => items.map((item) => (item.id === id ? loaded : item)));
  }

  function updateDraft(updated: ModelDraft) {
    setDrafts((items) => items.map((item) => (item.id === updated.id ? updated : item)));
  }

  function installed(releaseId: string) {
    void load().then(() => {
      toast("The draft was installed as a release. No workspace runs it until you activate it in one.");
      onRouteChange({ ...MODEL, releaseId });
    });
  }

  function activated(result: WorkspaceModelActivation, workspace: Workspace) {
    setActivating(undefined);
    const left = result.changeSetsLeftBehind.length;
    void Promise.all([load(), onActiveModelChange?.(workspace.key)]).then(() => {
      toast(
        `${workspace.label} now runs ${result.releaseName} ${result.releaseVersion}.` +
          (left ? ` ${left} open change ${plural(left, "set stays", "sets stay")} on the release it ran before.` : ""),
      );
    });
  }

  const head = settingsHead("model");
  const selectedDraft = route.draftId ? drafts.find((item) => item.id === route.draftId) : undefined;
  const models = releasesByModel(releases);
  const modelOfRelease = new Map(releases.map((release) => [release.id, release.key]));
  /** The model a draft was started from; none for a draft of a new model. */
  const modelOfDraft = (draft: ModelDraft) =>
    draft.baseReleaseId ? modelOfRelease.get(draft.baseReleaseId) : undefined;
  const newModelDrafts = drafts.filter((draft) => !modelOfDraft(draft));
  const releaseGroup = held.find((group) => group.key === "model-release");
  const releasesIn = (workspaceKey: string) =>
    Boolean(
      releaseGroup && (releaseGroup.instance || releaseGroup.workspaces.some((item) => item.key === workspaceKey)),
    );
  const activatable = workspaces.filter((item) => releasesIn(item.key));
  const canActivate = Boolean(capabilities?.modelAdmin.activate) && activatable.length > 0;
  // A migration is model administration and a background job both (D14).
  const canMigrate = canActivate && Boolean(capabilities?.integrationJobs.createJobs);
  const canManageDrafts =
    Boolean(capabilities?.modelAdmin.manageDrafts) && held.some((group) => group.key === "model-authoring");
  const canInstall = Boolean(capabilities?.modelAdmin.install) && Boolean(releaseGroup?.instance);
  // The order of the list: the default workspace's model, the other models in use, then the rest.
  const defaultModelKey = workspaces.find((item) => item.key === defaultWorkspaceKey)?.model.releaseKey;
  const inUse = (model: ModelLine) => runningWorkspaces(workspaces, model.releases).length > 0;
  const ordered = [...models].sort(
    (a, b) =>
      Number(b.key === defaultModelKey) - Number(a.key === defaultModelKey) || Number(inUse(b)) - Number(inUse(a)),
  );
  // The model the card shows: the address's, or the one the shown release or draft belongs to.
  const selectedModelKey =
    route.modelKey ??
    (route.releaseId ? modelOfRelease.get(route.releaseId) : selectedDraft ? modelOfDraft(selectedDraft) : undefined);
  const shownModel = models.find((model) => model.key === selectedModelKey);
  const listing = !route.modelKey && !route.releaseId && !route.draftId;
  const draftSchema = (draft: ModelDraft) =>
    typeof draft.model.schemaVersion === "string" ? draft.model.schemaVersion : "—";
  const newestDraft = (items: ModelDraft[]) =>
    items.length ? String(newestFirst(items, "updatedAt")[0].version) : "—";
  const listFacts = (releases: string, latest: string, draft: string, schema: string) => [
    { label: "Releases", value: releases },
    { label: "Latest", value: latest, mono: true },
    { label: "Draft", value: draft, mono: true },
    { label: "Schema", value: schema, mono: true },
  ];
  const modelRow = (model: ModelLine, isDefault: boolean): EntityRow => {
    const running = runningWorkspaces(workspaces, model.releases).length;
    return {
      key: `model:${model.key}`,
      title: model.name,
      subtitle: model.key,
      subtitleMono: true,
      // As the Workspaces list: aligned columns, the same four in every group; the newest release
      // first, and the model's newest open draft.
      facts: listFacts(
        String(model.releases.length),
        model.releases[0].version,
        newestDraft(drafts.filter((draft) => modelOfDraft(draft) === model.key)),
        model.releases[0].schemaVersion,
      ),
      lead: <SettingsTile icon="model" hue={head.hue} />,
      pill: isDefault ? (
        <StatusPill tone="success">Runs the default workspace</StatusPill>
      ) : running ? (
        <StatusPill tone="neutral">{counted(running, "workspace")}</StatusPill>
      ) : model.releases.every((release) => release.status === "retired") ? (
        <StatusPill tone="warning">Retired</StatusPill>
      ) : undefined,
      onOpen: () => onRouteChange({ ...MODEL, modelKey: model.key }),
    };
  };
  const draftRow = (draft: ModelDraft): EntityRow => ({
    key: `draft:${draft.id}`,
    title: draft.name,
    subtitle: "Not installed yet",
    facts: listFacts("—", "—", String(draft.version), draftSchema(draft)),
    lead: <SettingsTile icon="list" hue={head.hue} />,
    pill: <StatusPill tone="draft">Draft</StatusPill>,
    onOpen: () => onRouteChange({ ...MODEL, draftId: draft.id }),
  });
  // The list's groups, in the order the list always had: the default workspace's model, the others
  // in use, the rest, then the drafts of models not installed yet. The search filters by name and key.
  const listGroups = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const matches = (name: string, key: string) => !needle || `${name} ${key}`.toLowerCase().includes(needle);
    const shown = ordered.filter((model) => matches(model.name, model.key));
    // A model all of whose releases are retired and that no workspace runs goes last (0.12 MR1).
    const retired = (m: ModelLine) => !inUse(m) && m.releases.every((release) => release.status === "retired");
    const groups: [string, string, EntityRow[]][] = [
      ["default", "Default workspace", shown.filter((m) => m.key === defaultModelKey).map((m) => modelRow(m, true))],
      ["in-use", "In use", shown.filter((m) => m.key !== defaultModelKey && inUse(m)).map((m) => modelRow(m, false))],
      [
        "not-in-use",
        "Not in use",
        shown.filter((m) => m.key !== defaultModelKey && !inUse(m) && !retired(m)).map((m) => modelRow(m, false)),
      ],
      [
        "drafts",
        "Drafts without an installed model",
        canManageDrafts ? newModelDrafts.filter((draft) => matches(draft.name, draft.id)).map(draftRow) : [],
      ],
      [
        "retired",
        "Retired",
        shown.filter((m) => m.key !== defaultModelKey && retired(m)).map((m) => modelRow(m, false)),
      ],
    ];
    return groups.map(([key, title, rows]): EntityGroup => ({ key, title, count: rows.length, rows }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, releases, workspaces, drafts, defaultWorkspaceKey, canManageDrafts]);
  // The tab Back returns to: the one the release or draft was opened from.
  const originTab: ModelTab = route.modelTab ?? (route.releaseId ? "releases" : "drafts");
  const headerLabel = shownModel?.name ?? (route.draftId ? (selectedDraft?.name ?? "Draft") : "Model");
  const toList = () => onRouteChange(MODEL);
  // The one bar over an opened release or draft: "Models › Test › Releases › 0.9.12".
  const trailBar = (last: string) =>
    shownModel ? (
      <Trail
        items={crumbs(
          <TrailLink onClick={toList}>Models</TrailLink>,
          <TrailLink onClick={() => onRouteChange({ ...MODEL, modelKey: shownModel.key })}>
            {shownModel.name}
          </TrailLink>,
          <TrailLink onClick={() => onRouteChange({ ...MODEL, modelKey: shownModel.key, modelTab: originTab })}>
            {MODEL_TAB_LABELS[originTab]}
          </TrailLink>,
          last,
        )}
      />
    ) : (
      <Trail
        items={crumbs(<TrailLink onClick={toList}>Models</TrailLink>, "Drafts without an installed model", last)}
      />
    );
  if (route.migrationJobId) {
    const task = route.journey?.kind === "aiTask" ? route.journey : undefined;
    const changeSetJourney = route.journey?.kind === "changeSet" ? route.journey : undefined;
    return (
      <MigrationPage
        key={route.migrationJobId}
        jobId={route.migrationJobId}
        workspaces={workspaces}
        releases={releases}
        onOpenJob={(jobId) =>
          onRouteChange({ ...MODEL, migrationJobId: jobId, forWorkspace: route.forWorkspace, journey: route.journey })
        }
        onBackToProposal={task ? () => onReturnToTask?.(task.taskId) : undefined}
        openApplication={
          changeSetJourney
            ? {
                applicationKey: changeSetJourney.applicationKey,
                onOpen: () => onOpenApplication?.(changeSetJourney.workspaceKey, changeSetJourney.applicationKey),
              }
            : undefined
        }
        onBackToChangeSet={
          changeSetJourney
            ? () =>
                onOpenChangeSetReview?.(
                  changeReviewFor(
                    changeSetJourney.applicationKey,
                    changeSetJourney.workspaceKey,
                    changeSetJourney.changeSetId,
                  ),
                )
            : undefined
        }
        onReturnToWorkspace={route.forWorkspace ? () => onReturnToWorkspace?.(route.forWorkspace!) : undefined}
        onBack={() => onRouteChange(MODEL)}
        onMigrated={(workspaceKey) => Promise.all([load(), onActiveModelChange?.(workspaceKey)])}
        onOpenChangeSet={onOpenChangeSet}
      />
    );
  }
  const dialogs = (
    <>
      {activating && (
        <ActivateDialog
          workspaces={activatable}
          releases={releases.filter((release) => usableIds.has(release.id))}
          workspaceKey={activating.workspaceKey}
          releaseId={activating.releaseId}
          canMigrate={canMigrate}
          onClose={() => setActivating(undefined)}
          onActivated={activated}
          onMigrationStarted={(jobId) => {
            setActivating(undefined);
            onRouteChange({ ...MODEL, migrationJobId: jobId });
          }}
        />
      )}
      {creating && (
        <CreateDraftDialog
          releases={releases}
          seed={creating}
          onClose={() => setCreating(undefined)}
          onCreated={(draft) => {
            setDrafts((items) => [draft, ...items]);
            setCreating(undefined);
            onRouteChange({ ...MODEL, draftId: draft.id, editor: {} });
          }}
        />
      )}
    </>
  );
  const failure = error && (
    <div className="inline-state error-notice" role="alert">
      <span>{error}</span>
      <button className="secondary" onClick={load}>
        Retry
      </button>
    </div>
  );

  const readOnly = capabilities && !canManageDrafts && (
    <Notice>
      Model mutations are disabled. Installed releases remain available for read-only inspection and export.
    </Notice>
  );

  // An opened model, release or draft is a page of its own, under its bar (PP-D61).
  if (!listing) {
    const pageTrail = shownModel ? (
      <Trail items={crumbs(<TrailLink onClick={toList}>Models</TrailLink>, shownModel.name)} />
    ) : (
      <Trail items={crumbs(<TrailLink onClick={toList}>Models</TrailLink>)} />
    );
    return (
      <>
        {!capabilities ? (
          <ModelNamePage trail={pageTrail} label={headerLabel}>
            {failure}
            {!error && <Skeleton label="Loading the model" lines={4} />}
          </ModelNamePage>
        ) : selectedDraft ? (
          <ModelDraftEditor
            trail={trailBar(selectedDraft.name)}
            modelName={shownModel?.name}
            draft={selectedDraft}
            canInstall={canInstall}
            onSaved={updateDraft}
            onReload={() => reloadDraft(selectedDraft.id)}
            onInstalled={installed}
            onOpenEditor={() => onRouteChange({ ...MODEL, draftId: selectedDraft.id, editor: {} })}
            onDeleted={() => {
              setDrafts((items) => items.filter((item) => item.id !== selectedDraft.id));
              toast(`Draft ${selectedDraft.name} was deleted.`);
              onRouteChange(shownModel ? { ...MODEL, modelKey: shownModel.key, modelTab: originTab } : MODEL);
            }}
          />
        ) : route.draftId ? (
          <ModelNamePage trail={trailBar(headerLabel)} label={headerLabel}>
            {failure}
            {!error && <Skeleton label="Loading the draft" lines={4} />}
          </ModelNamePage>
        ) : route.releaseId ? (
          <ModelReleaseDetail
            key={route.releaseId}
            trail={trailBar(releases.find((item) => item.id === route.releaseId)?.version ?? route.releaseId)}
            notice={readOnly}
            releaseId={route.releaseId}
            workspaces={workspaces}
            canManageDrafts={canManageDrafts}
            canActivate={canActivate}
            canInstall={canInstall}
            isDefault={workspaces.some(
              (item) => item.key === defaultWorkspaceKey && item.model.releaseId === route.releaseId,
            )}
            onCreateDraft={startFromRelease}
            onActivate={(releaseId) => setActivating({ releaseId })}
            onStatusChanged={(release) => {
              void load();
              toast(
                release.status === "retired"
                  ? `${release.name} ${release.version} is retired. It is no longer offered where a model is chosen.`
                  : `${release.name} ${release.version} is offered again.`,
              );
            }}
            onDeleted={(release) => {
              void load().then(() => {
                toast(`${release.name} ${release.version} was deleted.`);
                const left = releases.some((item) => item.key === release.key && item.id !== release.id);
                onRouteChange(left ? { ...MODEL, modelKey: release.key, modelTab: "releases" } : MODEL);
              });
            }}
          />
        ) : shownModel ? (
          <ModelDetail
            key={shownModel.key}
            trail={pageTrail}
            notice={readOnly}
            model={shownModel}
            drafts={drafts.filter((draft) => modelOfDraft(draft) === shownModel.key)}
            workspaces={workspaces}
            defaultWorkspaceKey={defaultWorkspaceKey}
            canManageDrafts={canManageDrafts}
            canActivate={canActivate}
            activatesIn={releasesIn}
            tab={route.modelTab}
            onTab={(modelTab) => onRouteChange({ ...MODEL, modelKey: shownModel.key, modelTab })}
            onActivate={(workspaceKey) => setActivating({ workspaceKey })}
            onNewDraft={(release) => setCreating({ name: `${release.name} draft`, releaseId: release.id })}
            onOpenRelease={(releaseId, modelTab) => onRouteChange({ ...MODEL, releaseId, modelTab })}
            onOpenDraft={(draftId, modelTab) => onRouteChange({ ...MODEL, draftId, modelTab })}
            onOpenWorkspace={(workspaceKey) => onOpenWorkspace?.(workspaceKey)}
          />
        ) : (
          <ModelNamePage trail={pageTrail} label={headerLabel}>
            <EmptyState>No installed release has the model key {route.modelKey}.</EmptyState>
          </ModelNamePage>
        )}
        {dialogs}
      </>
    );
  }
  return (
    <SettingsLayout
      {...head}
      title="Model"
      description="Each workspace runs a model of its own. Changing one workspace's model leaves the others as they are. Releases are installed once for the instance and never change."
      actions={
        canManageDrafts && (
          <>
            <button
              className="secondary"
              onClick={() => setCreating({ name: "", releaseId: createReleaseId, workbook: true })}
            >
              <Icon name="table" /> New from a workbook
            </button>
            <button
              ref={newDraftButtonRef}
              className="primary"
              onClick={() => setCreating({ name: "", releaseId: createReleaseId })}
            >
              <Icon name="plus" /> New draft
            </button>
          </>
        )
      }
    >
      {failure}
      {!capabilities && !error && <Skeleton label="Loading the model catalogue" lines={3} />}
      {readOnly}
      {capabilities && (
        <>
          <SettingsTools
            count={counted(
              listGroups.reduce((total, group) => total + group.rows.length, 0),
              "model",
            )}
          >
            <SearchField
              type="search"
              label="Search models"
              placeholder="Name or key"
              value={search}
              onChange={setSearch}
              clearOnEscape
            />
          </SettingsTools>
          <SettingsPanel>
            <EntityList
              label="models"
              groups={listGroups}
              empty={search.trim() ? `No model matches “${search.trim()}”` : "No model is installed yet."}
            />
          </SettingsPanel>
        </>
      )}
      {dialogs}
    </SettingsLayout>
  );
}
