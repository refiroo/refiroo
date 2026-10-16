/**
 * Settings › Model (Track U U3, U-D10 as revised 2026-10-06; 0.11 M5, D50): each workspace runs a
 * model of its own. Without a selection the page shows the workspaces with the model and release
 * each runs, the installed releases grouped by model with the workspaces running each, and the
 * drafts. A release or draft opens beside the catalogue, grouped by model. Activation goes into one
 * workspace through one dialog, from a workspace or from a release (D51). Below 760px the catalogue
 * and the selection take turns.
 */

import { useEffect, useRef, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type {
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
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { Icon } from "@/ui/Icon";
import { EmptyState } from "@/ui/EmptyState";
import { RuledList, RuledListItem } from "@/ui/RuledList";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
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

/** The installed releases by model (`release.key`), each model named by its newest release. */
export function releasesByModel(releases: ModelReleaseSummary[]) {
  const models = new Map<string, ModelReleaseSummary[]>();
  for (const release of releases) models.set(release.key, [...(models.get(release.key) ?? []), release]);
  return [...models].map(([key, items]) => {
    const newestFirst = [...items].sort((a, b) => b.installedAt.localeCompare(a.installedAt));
    return { key, name: newestFirst[0].name, releases: newestFirst };
  });
}

/** A release installed after the one the workspace runs, of the same model: worth activating. */
function newerRelease(workspace: Workspace, releases: ModelReleaseSummary[]) {
  const running = releases.find((item) => item.id === workspace.model.releaseId);
  if (!running) return undefined;
  return releases
    .filter((item) => item.key === running.key && item.installedAt > running.installedAt)
    .sort((a, b) => b.installedAt.localeCompare(a.installedAt))[0];
}

export function ModelWorkbench({
  route,
  onRouteChange,
  onActiveModelChange,
}: {
  route: ModelsRoute;
  onRouteChange: (route: ModelsRoute) => void;
  /** A workspace's model changed: the shell forgets the model it held for it (D49). */
  onActiveModelChange?: (workspaceKey: string) => Promise<unknown>;
}) {
  const toast = useToast();
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [draftCursor, setDraftCursor] = useState<string | null>();
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
      const [caps, installed, workspacePage, state] = await Promise.all([
        api.capabilities(),
        allReleases(),
        // Workspaces are few (ADR-042); retired ones keep their release and take no activation.
        api.workspaces({ status: "active", pageSize: 100 }),
        api.workspaceRuntimeState(),
      ]);
      setCapabilities(caps);
      setReleases(installed);
      setWorkspaces(workspacePage.items);
      setDefaultWorkspaceKey(state.defaultWorkspaceKey);
      const defaultRelease = workspacePage.items.find((item) => item.key === state.defaultWorkspaceKey)?.model
        .releaseId;
      setCreateReleaseId((current) => current || defaultRelease || "");
      if (caps.modelAdmin.manageDrafts) {
        const draftPage = await api.modelDrafts();
        setDrafts(draftPage.items);
        setDraftCursor(draftPage.nextCursor);
      } else {
        setDrafts([]);
        setDraftCursor(null);
      }
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function moreDrafts() {
    if (!draftCursor) return;
    try {
      const page = await api.modelDrafts({ cursor: draftCursor });
      setDrafts((items) => appendUnique(items, page.items));
      setDraftCursor(page.nextCursor);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

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
  const shownReleaseId = route.draftId ? undefined : route.releaseId;
  const selected = Boolean(route.releaseId || route.draftId);
  const models = releasesByModel(releases);
  const runBy = (release: ModelReleaseSummary) => {
    const keys = workspaces.filter((item) => item.model.releaseId === release.id).map((item) => item.label);
    return keys.length ? `Run by ${keys.join(", ")}` : "Run by no workspace";
  };
  const canActivate = Boolean(capabilities?.modelAdmin.activate);
  const catalogue = (
    <nav className="model-catalogue" aria-label="Model catalogue">
      {models.map((model) => (
        <section key={model.key}>
          <h2 className="nav-label">
            {model.name} <span>{model.key}</span>
          </h2>
          {model.releases.map((release) => (
            <CatalogueEntry
              key={release.id}
              icon="model"
              title={release.version}
              subtitle={runBy(release)}
              current={shownReleaseId === release.id}
              onSelect={() => onRouteChange({ ...MODEL, releaseId: release.id })}
            />
          ))}
        </section>
      ))}
      {capabilities?.modelAdmin.manageDrafts && (
        <section>
          <h2 className="nav-label">
            Drafts <span>{drafts.length}</span>
          </h2>
          {drafts.length ? (
            drafts.map((draft) => (
              <CatalogueEntry
                key={draft.id}
                icon="list"
                title={draft.name}
                subtitle={`Version ${draft.version} · ${formatServerTime(draft.updatedAt)}`}
                current={route.draftId === draft.id}
                onSelect={() => onRouteChange({ ...MODEL, draftId: draft.id })}
              />
            ))
          ) : (
            <EmptyState>No drafts yet.</EmptyState>
          )}
          {draftCursor && (
            <button className="load-more" onClick={moreDrafts}>
              Load more drafts
            </button>
          )}
        </section>
      )}
    </nav>
  );
  return (
    <SettingsLayout
      eyebrow="Administration"
      title="Model"
      description="Each workspace runs a model of its own. Activating a release changes one workspace; the others keep theirs. Releases are installed once for the instance and never change."
      actions={
        capabilities?.modelAdmin.manageDrafts && (
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
      {capabilities && !capabilities.modelAdmin.manageDrafts && (
        <Notice>
          Model mutations are disabled. Installed releases remain available for read-only inspection and export.
        </Notice>
      )}
      {capabilities && !selected ? (
        <ModelOverview
          workspaces={workspaces}
          releases={releases}
          drafts={capabilities.modelAdmin.manageDrafts ? drafts : undefined}
          moreDrafts={draftCursor ? moreDrafts : undefined}
          defaultWorkspaceKey={defaultWorkspaceKey}
          canActivate={canActivate}
          runBy={runBy}
          onActivate={(workspaceKey) => setActivating({ workspaceKey })}
          onOpen={onRouteChange}
        />
      ) : (
        capabilities && (
          <CatalogueLayout
            catalogue={catalogue}
            hasSelection={selected}
            backLabel="Workspaces, releases and drafts"
            onBack={() => onRouteChange(MODEL)}
          >
            {selectedDraft ? (
              <ModelDraftEditor
                draft={selectedDraft}
                canInstall={!!capabilities.modelAdmin.install}
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
            ) : shownReleaseId ? (
              <ModelReleaseDetail
                key={shownReleaseId}
                releaseId={shownReleaseId}
                workspaces={workspaces}
                canManageDrafts={!!capabilities.modelAdmin.manageDrafts}
                canActivate={canActivate}
                onCreateDraft={startFromRelease}
                onActivate={(releaseId) => setActivating({ releaseId })}
              />
            ) : (
              <div className="panel-state">Loading the draft…</div>
            )}
          </CatalogueLayout>
        )
      )}
      {activating && (
        <ActivateDialog
          workspaces={workspaces}
          releases={releases}
          workspaceKey={activating.workspaceKey}
          releaseId={activating.releaseId}
          onClose={() => setActivating(undefined)}
          onActivated={activated}
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

/** The page without a selection: the workspaces and their models, the releases by model, the drafts (D50). */
function ModelOverview({
  workspaces,
  releases,
  drafts,
  moreDrafts,
  defaultWorkspaceKey,
  canActivate,
  runBy,
  onActivate,
  onOpen,
}: {
  workspaces: Workspace[];
  releases: ModelReleaseSummary[];
  /** Absent where drafts cannot be managed. */
  drafts?: ModelDraft[];
  moreDrafts?: () => void;
  defaultWorkspaceKey: string;
  canActivate: boolean;
  runBy: (release: ModelReleaseSummary) => string;
  onActivate: (workspaceKey: string) => void;
  onOpen: (route: ModelsRoute) => void;
}) {
  return (
    <>
      <Section title="Workspaces and their models">
        <SettingsTable
          label="Workspaces and their models"
          columns={["Workspace", "Model", "Release", "Schema", "Since", ...(canActivate ? ["Actions"] : [])]}
        >
          {workspaces.map((workspace) => {
            const newer = newerRelease(workspace, releases);
            return (
              <tr key={workspace.key}>
                <th scope="row">
                  {workspace.label}
                  {workspace.key === defaultWorkspaceKey && <span className="muted"> · default</span>}
                </th>
                <td data-label="Model">{workspace.model.releaseName}</td>
                <td data-label="Release">
                  <span className="mono">{workspace.model.releaseVersion}</span>{" "}
                  {newer && (
                    <StatusPill tone="neutral" marker={false}>
                      {newer.version} installed
                    </StatusPill>
                  )}
                </td>
                <td data-label="Schema">
                  <span className="mono">{workspace.model.schemaVersion}</span>
                </td>
                <td data-label="Since">{formatServerTime(workspace.model.updatedAt)}</td>
                {canActivate && (
                  <td data-label="Actions">
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Activate a release in ${workspace.label}`}
                      onClick={() => onActivate(workspace.key)}
                    >
                      Activate a release…
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </SettingsTable>
      </Section>
      <Section
        title="Installed releases"
        description="A model is the line of releases sharing one key. Each release is installed once for the instance and never changes."
      >
        <div className="model-release-groups">
          {releasesByModel(releases).map((model) => (
            <div key={model.key} className="model-release-group">
              <h3>
                {model.name} <span className="mono muted">{model.key}</span>
              </h3>
              <RuledList label={`Releases of ${model.name}`}>
                {model.releases.map((release) => (
                  <RuledListItem
                    key={release.id}
                    title={<span className="mono">{release.version}</span>}
                    meta={`Schema ${release.schemaVersion} · ${runBy(release)}`}
                    actions={
                      <button
                        type="button"
                        className="secondary"
                        aria-label={`Open ${model.name} ${release.version}`}
                        onClick={() => onOpen({ ...MODEL, releaseId: release.id })}
                      >
                        Open
                      </button>
                    }
                  />
                ))}
              </RuledList>
            </div>
          ))}
        </div>
      </Section>
      {drafts && (
        <Section title="Drafts">
          {drafts.length ? (
            <RuledList label="Drafts">
              {drafts.map((draft) => (
                <RuledListItem
                  key={draft.id}
                  title={draft.name}
                  meta={`Version ${draft.version} · ${formatServerTime(draft.updatedAt)}`}
                  actions={
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Open draft ${draft.name}`}
                      onClick={() => onOpen({ ...MODEL, draftId: draft.id })}
                    >
                      Open
                    </button>
                  }
                />
              ))}
            </RuledList>
          ) : (
            <EmptyState>No drafts yet.</EmptyState>
          )}
          {moreDrafts && (
            <button className="load-more" onClick={moreDrafts}>
              Load more drafts
            </button>
          )}
        </Section>
      )}
    </>
  );
}
