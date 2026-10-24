/**
 * Settings › Model (Track U U3, U-D10 as revised 2026-10-06; 0.11 M5, D50; 0.11 M6): laid out as
 * Settings › Workspaces is. The list holds the models, the default workspace's first, then the others
 * in use, then the rest, and the drafts of models not installed yet. The card beside it shows the
 * selected model (without a selection the default workspace's): where it runs, its releases and its
 * drafts; a release or draft opens in the card. Activation goes into one workspace through one
 * dialog (D51). Below 760px the list and the card take turns.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type {
  HeldAnywhere,
  CapabilitiesResponse,
  ModelDraft,
  ModelRelease,
  ModelReleaseSummary,
  SettingsRoute,
  Workspace,
  WorkspaceModelActivation,
} from "@/types";
import { CapabilityStatus } from "@/features/administration/CapabilityStatus";
import { ActivateDialog } from "@/features/model-admin/ActivateDialog";
import { CreateDraftDialog, type CreateDraftSeed } from "@/features/model-admin/CreateDraftDialog";
import { MigrationPage } from "@/features/model-admin/MigrationPage";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";
import { ModelDetail, runningWorkspaces } from "@/features/model-admin/ModelPage";
import { releasesByModel, type ModelLine } from "@/features/model-admin/modelLines";
import { Icon } from "@/ui/Icon";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { EmptyState } from "@/ui/EmptyState";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { Notice } from "@/ui/Notice";

type ModelsRoute = Extract<SettingsRoute, { page: "model" }>;

const MODEL: ModelsRoute = { kind: "settings", page: "model" };

function appendUnique<T extends { id: string }>(current: T[], incoming: T[]) {
  const ids = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !ids.has(item.id))];
}

/** Every installed release, oldest first (releases are few: one line per model's versions). */
async function allReleases() {
  const items: ModelReleaseSummary[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.modelReleases({ cursor, pageSize: 500 });
    items.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items;
}

/** Every draft, newest first; a draft is shown under the model it was started from (M6). */
async function allDrafts() {
  const items: ModelDraft[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.modelDrafts({ cursor });
    items.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items;
}

export function ModelWorkbench({
  route,
  onRouteChange,
  onActiveModelChange,
  onOpenWorkspace,
  onOpenChangeSet,
}: {
  route: ModelsRoute;
  onRouteChange: (route: ModelsRoute) => void;
  /** Opens a workspace in Settings › Workspaces, from the workspaces a model runs in (M6). */
  onOpenWorkspace?: (workspaceKey: string) => void;
  /** A change set moved onto its workspace's release (0.11 V3): open it. */
  onOpenChangeSet?: (workspaceKey: string, changeSetId: string) => void;
  /** A workspace's model changed: the shell forgets the model it held for it (D49). */
  onActiveModelChange?: (workspaceKey: string) => Promise<unknown>;
}) {
  const toast = useToast();
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  // What the person may do here (0.12 Z5, D323): drafts with Model authoring; installing (at the
  // instance), activating and migrating (in a workspace) with Model release.
  const [held, setHeld] = useState<HeldAnywhere[]>([]);
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [defaultWorkspaceKey, setDefaultWorkspaceKey] = useState("");
  const [activating, setActivating] = useState<{ workspaceKey?: string; releaseId?: string }>();
  const [error, setError] = useState("");
  const [creating, setCreating] = useState<CreateDraftSeed>();
  const [createReleaseId, setCreateReleaseId] = useState("");
  const newDraftButtonRef = useRef<HTMLButtonElement>(null);

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
      const [groups, caps, installed, workspacePage, state] = await Promise.all([
        api.myActionGroups().then(
          (list) => list.items,
          () => [],
        ),
        api.capabilities(),
        allReleases(),
        // Workspaces are few (ADR-042); retired ones keep their release and take no activation.
        api.workspaces({ status: "active", pageSize: 100 }),
        api.workspaceRuntimeState(),
      ]);
      // The drafts first, so the page never shows a model's count before its drafts arrived.
      const authors = groups.some((group) => group.key === "model-authoring");
      const loadedDrafts = caps.modelAdmin.manageDrafts && authors ? await allDrafts() : [];
      setHeld(groups);
      setDrafts(loadedDrafts);
      setCapabilities(caps);
      setReleases(installed);
      setWorkspaces(workspacePage.items);
      setDefaultWorkspaceKey(state.defaultWorkspaceKey);
      const defaultRelease = workspacePage.items.find((item) => item.key === state.defaultWorkspaceKey)?.model
        .releaseId;
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
          (left ? ` ${left} open change ${left === 1 ? "set stays" : "sets stay"} on the release it ran before.` : ""),
      );
    });
  }

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
  // The model the list marks and the card shows: the address's, the shown release's or draft's, or
  // without a selection the default workspace's.
  const selectedModelKey =
    route.modelKey ??
    (route.releaseId
      ? modelOfRelease.get(route.releaseId)
      : selectedDraft
        ? modelOfDraft(selectedDraft)
        : route.draftId
          ? undefined
          : (defaultModelKey ?? ordered[0]?.key));
  const shownModel = models.find((model) => model.key === selectedModelKey);
  const catalogue = (
    <nav className="model-catalogue" aria-label="Model catalogue">
      <section>
        <h2 className="nav-label">
          Models <span>{models.length + (canManageDrafts ? newModelDrafts.length : 0)}</span>
        </h2>
        {ordered.map((model) => {
          const running = runningWorkspaces(workspaces, model.releases).map((workspace) => workspace.label);
          return (
            <CatalogueEntry
              key={model.key}
              icon="model"
              title={model.name}
              subtitle={`${model.releases[0].version} · ${running.length ? `in ${running.join(", ")}` : "in no workspace"}`}
              current={selectedModelKey === model.key && !(route.draftId && !selectedDraft)}
              onSelect={() => onRouteChange({ ...MODEL, modelKey: model.key })}
              pill={model.key === defaultModelKey && <StatusPill tone="success">Default</StatusPill>}
            />
          );
        })}
        {canManageDrafts &&
          newModelDrafts.map((draft) => (
            <CatalogueEntry
              key={draft.id}
              icon="list"
              title={draft.name}
              subtitle={`Not installed yet · draft version ${draft.version}`}
              current={route.draftId === draft.id}
              onSelect={() => onRouteChange({ ...MODEL, draftId: draft.id })}
            />
          ))}
      </section>
    </nav>
  );
  if (route.migrationJobId) {
    return (
      <MigrationPage
        key={route.migrationJobId}
        jobId={route.migrationJobId}
        workspaces={workspaces}
        releases={releases}
        onOpenJob={(jobId) => onRouteChange({ ...MODEL, migrationJobId: jobId })}
        onBack={() => onRouteChange(MODEL)}
        onMigrated={(workspaceKey) => Promise.all([load(), onActiveModelChange?.(workspaceKey)])}
        onOpenChangeSet={onOpenChangeSet}
      />
    );
  }
  return (
    <SettingsLayout
      eyebrow="Administration"
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
      {error && (
        <div className="inline-state error-notice" role="alert">
          <span>{error}</span>
          <button className="secondary" onClick={load}>
            Retry
          </button>
        </div>
      )}
      {!capabilities && !error && <div className="panel-state">Loading model catalogue…</div>}
      {capabilities && <CapabilityStatus capabilities={capabilities} />}
      {capabilities && !canManageDrafts && (
        <Notice>
          Model mutations are disabled. Installed releases remain available for read-only inspection and export.
        </Notice>
      )}
      {capabilities && (
        <CatalogueLayout
          catalogue={catalogue}
          hasSelection={Boolean(route.modelKey || route.releaseId || route.draftId)}
          backLabel="All models"
          onBack={() => onRouteChange(MODEL)}
        >
          {selectedDraft ? (
            <ModelDraftEditor
              draft={selectedDraft}
              canInstall={canInstall}
              onSaved={updateDraft}
              onReload={() => reloadDraft(selectedDraft.id)}
              onInstalled={installed}
              onOpenEditor={() => onRouteChange({ ...MODEL, draftId: selectedDraft.id, editor: {} })}
              onDeleted={() => {
                setDrafts((items) => items.filter((item) => item.id !== selectedDraft.id));
                toast(`Draft ${selectedDraft.name} was deleted.`);
                onRouteChange(MODEL);
              }}
            />
          ) : route.draftId ? (
            <div className="panel-state">Loading the draft…</div>
          ) : route.releaseId ? (
            <ModelReleaseDetail
              key={route.releaseId}
              releaseId={route.releaseId}
              workspaces={workspaces}
              canManageDrafts={canManageDrafts}
              canActivate={canActivate}
              onCreateDraft={startFromRelease}
              onActivate={(releaseId) => setActivating({ releaseId })}
            />
          ) : shownModel ? (
            <ModelDetail
              key={shownModel.key}
              model={shownModel}
              drafts={drafts.filter((draft) => modelOfDraft(draft) === shownModel.key)}
              workspaces={workspaces}
              defaultWorkspaceKey={defaultWorkspaceKey}
              canManageDrafts={canManageDrafts}
              canActivate={canActivate}
              activatesIn={releasesIn}
              onActivate={(workspaceKey) => setActivating({ workspaceKey })}
              onNewDraft={(release) => setCreating({ name: `${release.name} draft`, releaseId: release.id })}
              onOpenRelease={(releaseId) => onRouteChange({ ...MODEL, releaseId })}
              onOpenDraft={(draftId) => onRouteChange({ ...MODEL, draftId })}
              onOpenWorkspace={(workspaceKey) => onOpenWorkspace?.(workspaceKey)}
            />
          ) : route.modelKey ? (
            <EmptyState>No installed release has the model key {route.modelKey}.</EmptyState>
          ) : (
            <div className="panel-state">No model is installed yet.</div>
          )}
        </CatalogueLayout>
      )}
      {activating && (
        <ActivateDialog
          workspaces={activatable}
          releases={releases}
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
    </SettingsLayout>
  );
}
