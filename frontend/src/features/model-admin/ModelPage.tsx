/**
 * A model selected in Settings › Model (0.11 M6): a card like a workspace's in Settings › Workspaces.
 * Its name and key, its actions, then tabs: Overview (the facts and where it runs),
 * Releases (newest first, each with the workspaces running it named on it), Drafts (those started
 * from its releases, each with how far behind its release is) and Structure. A row opens the release
 * or draft in this card, under a bar that leads back to the tab it was opened from.
 */

import type { ReactNode } from "react";
import { formatServerDate } from "@/lib/dates";
import { routePath } from "@/routing/routes";
import type { ModelDraft, ModelReleaseSummary, ModelTab, Workspace } from "@/types";
import { OpenableRow } from "@/ui/OpenableRow";
import { RouteLink } from "@/ui/RouteLink";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs, type TabDefinition } from "@/ui/Tabs";
import { ModelStructure } from "@/features/model-admin/ModelStructure";
import type { ModelLine } from "@/features/model-admin/modelLines";

const releaseHref = (releaseId: string) => routePath({ kind: "settings", page: "model", releaseId });
const draftHref = (draftId: string) => routePath({ kind: "settings", page: "model", draftId });
const workspaceHref = (workspaceKey: string) => routePath({ kind: "settings", page: "workspaces", workspaceKey });

/** The workspaces running one of `releases`. */
export function runningWorkspaces(workspaces: Workspace[], releases: ModelReleaseSummary[]) {
  const ids = new Set(releases.map((release) => release.id));
  return workspaces.filter((workspace) => ids.has(workspace.model.releaseId));
}

export const MODEL_TAB_LABELS: Record<ModelTab, string> = {
  overview: "Overview",
  releases: "Releases",
  drafts: "Drafts",
  structure: "Structure",
};

const MODEL_TAB_ORDER: readonly ModelTab[] = ["overview", "releases", "drafts", "structure"];

/** The header of a model's card without the model's own content: the model's name under "Model". */
export function ModelNameHeader({ label }: { label: string }) {
  return (
    <header className="model-detail-header">
      <div>
        <p className="eyebrow">Model</p>
        <h2>{label}</h2>
      </div>
    </header>
  );
}

export function ModelDetail({
  model,
  drafts,
  workspaces,
  defaultWorkspaceKey,
  canManageDrafts,
  canActivate,
  activatesIn,
  tab,
  onTab,
  onActivate,
  onNewDraft,
  onOpenRelease,
  onOpenDraft,
  onOpenWorkspace,
}: {
  model: ModelLine;
  /** The drafts started from one of the model's releases, newest first. */
  drafts: ModelDraft[];
  workspaces: Workspace[];
  defaultWorkspaceKey: string;
  canManageDrafts: boolean;
  canActivate: boolean;
  /** Whether the person may change the model of this workspace (0.12 Z5, D323). */
  activatesIn?: (workspaceKey: string) => boolean;
  /** The tab the address names; one that is not available shows Overview. */
  tab?: ModelTab;
  onTab: (tab: ModelTab) => void;
  onActivate: (workspaceKey: string) => void;
  onNewDraft: (release: ModelReleaseSummary) => void;
  /** `from` is the tab the row was in, so that Back returns to it. */
  onOpenRelease: (releaseId: string, from: ModelTab) => void;
  onOpenDraft: (draftId: string, from: ModelTab) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
}) {
  const [newest] = model.releases;
  // The default workspace first: it is the one most people work in.
  const running = runningWorkspaces(workspaces, model.releases).sort(
    (a, b) => Number(b.key === defaultWorkspaceKey) - Number(a.key === defaultWorkspaceKey),
  );
  const behind = (draft: ModelDraft) => model.releases.findIndex((release) => release.id === draft.baseReleaseId);
  const showDrafts = canManageDrafts && drafts.length > 0;
  const available: Record<ModelTab, boolean> = { overview: true, releases: true, drafts: showDrafts, structure: true };
  const selected = tab && available[tab] ? tab : "overview";
  const counts: Partial<Record<ModelTab, number>> = { releases: model.releases.length, drafts: drafts.length };

  const content: Record<ModelTab, ReactNode> = {
    overview: (
      <>
        <dl className="release-metadata">
          <div>
            <dt>Newest release</dt>
            <dd>
              <span className="mono">{newest.version}</span> · schema {newest.schemaVersion}
            </dd>
          </div>
          <div>
            <dt>Installed</dt>
            <dd>{formatServerDate(newest.installedAt)}</dd>
          </div>
        </dl>
        <section className="model-detail-section" aria-labelledby="model-running-heading">
          <h3 id="model-running-heading">
            Running in{" "}
            <span className="muted">
              {running.length} {running.length === 1 ? "workspace" : "workspaces"}
            </span>
          </h3>
          {running.length ? (
            <ul className="model-rows" aria-label={`Workspaces running ${model.name}`}>
              {running.map((workspace) => {
                const open = () => onOpenWorkspace(workspace.key);
                return (
                  <OpenableRow key={workspace.key} as="li" className="model-row" onOpen={open}>
                    <RouteLink className="row-title" href={workspaceHref(workspace.key)} onNavigate={open}>
                      {workspace.label}
                    </RouteLink>
                    <span className="mono">{workspace.model.releaseVersion}</span>
                    {canActivate && (activatesIn?.(workspace.key) ?? true) ? (
                      <button
                        type="button"
                        className="secondary"
                        aria-label={`Change the model of ${workspace.label}`}
                        onClick={() => onActivate(workspace.key)}
                      >
                        Change model…
                      </button>
                    ) : (
                      <span />
                    )}
                  </OpenableRow>
                );
              })}
            </ul>
          ) : (
            <p className="muted">No workspace runs this model.</p>
          )}
        </section>
      </>
    ),
    releases: (
      <section className="model-detail-section" aria-labelledby="model-releases-heading">
        <h3 id="model-releases-heading">
          Releases <span className="muted">{model.releases.length}</span>
        </h3>
        <ul className="model-rows" aria-label={`Releases of ${model.name}`}>
          {model.releases.map((release) => {
            const by = running.filter((workspace) => workspace.model.releaseId === release.id);
            const open = () => onOpenRelease(release.id, selected);
            return (
              <OpenableRow key={release.id} as="li" className="model-row" onOpen={open}>
                <RouteLink
                  className="row-title mono"
                  href={releaseHref(release.id)}
                  onNavigate={open}
                  aria-label={`${model.name} ${release.version}`}
                >
                  {release.version}
                </RouteLink>
                <span className="model-row-marks">
                  {by.map((workspace) => (
                    <StatusPill key={workspace.key} tone="success" marker={false}>
                      {workspace.label}
                    </StatusPill>
                  ))}
                </span>
                <span className="muted">
                  schema {release.schemaVersion} · {formatServerDate(release.installedAt)}
                </span>
              </OpenableRow>
            );
          })}
        </ul>
      </section>
    ),
    drafts: (
      <section className="model-detail-section" aria-labelledby="model-drafts-heading">
        <h3 id="model-drafts-heading">
          Drafts <span className="muted">{drafts.length}</span>
        </h3>
        <ul className="model-rows" aria-label={`Drafts of ${model.name}`}>
          {drafts.map((draft) => {
            const index = behind(draft);
            const open = () => onOpenDraft(draft.id, selected);
            return (
              <OpenableRow key={draft.id} as="li" className="model-row" onOpen={open}>
                <RouteLink className="row-title" href={draftHref(draft.id)} onNavigate={open}>
                  {draft.name}
                </RouteLink>
                <span className="model-row-marks">
                  {index > 0 && (
                    <StatusPill tone="warning" marker={false}>
                      {index} {index === 1 ? "release" : "releases"} behind
                    </StatusPill>
                  )}
                </span>
                <span className="muted">
                  from <span className="mono">{model.releases[index]?.version}</span> ·{" "}
                  {formatServerDate(draft.updatedAt)}
                </span>
              </OpenableRow>
            );
          })}
        </ul>
      </section>
    ),
    structure: <ModelStructure releases={model.releases} />,
  };
  const tabs: TabDefinition[] = MODEL_TAB_ORDER.filter((item) => available[item]).map((item) => ({
    id: item,
    label: counts[item] === undefined ? MODEL_TAB_LABELS[item] : `${MODEL_TAB_LABELS[item]} (${counts[item]})`,
    content: <div className="workspace-tab-panel">{content[item]}</div>,
  }));

  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Model</p>
          <h2>{model.name}</h2>
          <p>{model.key}</p>
        </div>
        <StatusPill tone={running.length ? "success" : "neutral"}>
          {running.length ? "In use" : "Not in use"}
        </StatusPill>
      </header>
      {canManageDrafts && (
        <div className="model-actions">
          <button type="button" className="secondary" onClick={() => onNewDraft(newest)}>
            New draft from {newest.version}
          </button>
        </div>
      )}
      <div className="workspace-tabs">
        <Tabs label="Model" tabs={tabs} selected={selected} keepVisited onChange={(id) => onTab(id as ModelTab)} />
      </div>
    </div>
  );
}
