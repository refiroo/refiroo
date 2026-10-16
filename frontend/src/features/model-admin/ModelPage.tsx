/**
 * A model selected in Settings › Model (0.11 M6): a card like a workspace's in Settings › Workspaces.
 * Its name and key, the facts (where it runs, its newest release), its actions, then its releases,
 * newest first, each with the workspaces running it named on it, and the drafts started from its
 * releases, each with how far behind its release is. A row opens the release or draft in this card.
 */

import { formatServerDate } from "@/lib/dates";
import { routePath } from "@/routing/routes";
import type { ModelDraft, ModelReleaseSummary, Workspace } from "@/types";
import { OpenableRow } from "@/ui/OpenableRow";
import { RouteLink } from "@/ui/RouteLink";
import { StatusPill } from "@/ui/StatusPill";
import type { ModelLine } from "@/features/model-admin/modelLines";

const releaseHref = (releaseId: string) => routePath({ kind: "settings", page: "model", releaseId });
const draftHref = (draftId: string) => routePath({ kind: "settings", page: "model", draftId });
const workspaceHref = (workspaceKey: string) => routePath({ kind: "settings", page: "workspaces", workspaceKey });

/** The workspaces running one of `releases`. */
export function runningWorkspaces(workspaces: Workspace[], releases: ModelReleaseSummary[]) {
  const ids = new Set(releases.map((release) => release.id));
  return workspaces.filter((workspace) => ids.has(workspace.model.releaseId));
}

export function ModelDetail({
  model,
  drafts,
  workspaces,
  defaultWorkspaceKey,
  canManageDrafts,
  canActivate,
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
  onActivate: (workspaceKey: string) => void;
  onNewDraft: (release: ModelReleaseSummary) => void;
  onOpenRelease: (releaseId: string) => void;
  onOpenDraft: (draftId: string) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
}) {
  const [newest] = model.releases;
  // The default workspace first: it is the one most people work in.
  const running = runningWorkspaces(workspaces, model.releases).sort(
    (a, b) => Number(b.key === defaultWorkspaceKey) - Number(a.key === defaultWorkspaceKey),
  );
  const behind = (draft: ModelDraft) => model.releases.findIndex((release) => release.id === draft.baseReleaseId);

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
      {canManageDrafts && (
        <div className="model-actions">
          <button type="button" className="secondary" onClick={() => onNewDraft(newest)}>
            New draft from {newest.version}
          </button>
        </div>
      )}

      <section className="model-detail-section" aria-labelledby="model-running-heading">
        <h3 id="model-running-heading">
          Running in <span className="muted">{running.length}</span>
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
                  {canActivate ? (
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

      <section className="model-detail-section" aria-labelledby="model-releases-heading">
        <h3 id="model-releases-heading">
          Releases <span className="muted">{model.releases.length}</span>
        </h3>
        <ul className="model-rows" aria-label={`Releases of ${model.name}`}>
          {model.releases.map((release) => {
            const by = running.filter((workspace) => workspace.model.releaseId === release.id);
            const open = () => onOpenRelease(release.id);
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

      {canManageDrafts && drafts.length > 0 && (
        <section className="model-detail-section" aria-labelledby="model-drafts-heading">
          <h3 id="model-drafts-heading">
            Drafts <span className="muted">{drafts.length}</span>
          </h3>
          <ul className="model-rows" aria-label={`Drafts of ${model.name}`}>
            {drafts.map((draft) => {
              const index = behind(draft);
              const open = () => onOpenDraft(draft.id);
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
      )}
    </div>
  );
}
