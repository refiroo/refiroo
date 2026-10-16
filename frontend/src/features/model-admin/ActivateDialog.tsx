/**
 * Activating a release into one workspace (0.11 M5, D51), the approved mock-up's dialog. It opens
 * from a workspace (the workspace fixed, a release chosen) or from a release (the release fixed, a
 * workspace chosen). Before anything changes it shows the check of that workspace's data against
 * the release (D52), the workspace's open change sets that would stay on the release it runs now
 * (D26), and the workspaces it leaves as they are. When the data does not fit, it says a migration
 * is needed and offers no activation.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { activationRefusal } from "@/features/model-editor/InstallDialog";
import { workspaceModelLabel } from "@/features/workspaces/WorkspaceSelector";
import { releasesByModel } from "@/features/model-admin/modelLines";
import type {
  ChangeSet,
  ModelDiagnostic,
  ModelReleaseDiff,
  ModelReleaseSummary,
  Workspace,
  WorkspaceModelActivation,
} from "@/types";
import { Modal } from "@/ui/Modal";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { StatusPill } from "@/ui/StatusPill";
import { SelectField } from "@/ui/Selection";
import { Skeleton } from "@/ui/Skeleton";

type Check =
  | { key: string; state: "ready"; diff: ModelReleaseDiff; leftBehind: ChangeSet[] }
  | { key: string; state: "error"; message: string };

/** Every open change set of the workspace, page by page (a workspace holds few). */
async function openChangeSets(workspaceKey: string): Promise<ChangeSet[]> {
  const found: ChangeSet[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.changeSets(workspaceKey, cursor);
    found.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return found;
}

/** The candidate releases by model, the workspace's own model first, each newest first (M6). */
function groupedCandidates(candidates: ModelReleaseSummary[], ownModelKey: string | undefined) {
  const models = releasesByModel(candidates);
  return [
    ...models.filter((model) => model.key === ownModelKey),
    ...models.filter((model) => model.key !== ownModelKey),
  ];
}

export function ActivateDialog({
  workspaces,
  releases,
  workspaceKey: fixedWorkspace,
  releaseId: fixedRelease,
  onClose,
  onActivated,
}: {
  /** The active workspaces, with the release each runs. */
  workspaces: Workspace[];
  releases: ModelReleaseSummary[];
  /** Opened from a workspace: that workspace, a release to choose. */
  workspaceKey?: string;
  /** Opened from a release: that release, a workspace to choose. */
  releaseId?: string;
  onClose: () => void;
  onActivated: (result: WorkspaceModelActivation, workspace: Workspace) => void;
}) {
  const candidatesFor = (workspace: Workspace | undefined) =>
    releases.filter((release) => release.id !== workspace?.model.releaseId);
  const [workspaceKey, setWorkspaceKey] = useState(
    () => fixedWorkspace ?? workspaces.find((item) => item.model.releaseId !== fixedRelease)?.key ?? "",
  );
  const workspace = workspaces.find((item) => item.key === workspaceKey);
  const [releaseId, setReleaseId] = useState(() => {
    if (fixedRelease) return fixedRelease;
    const current = workspaces.find((item) => item.key === fixedWorkspace);
    const choices = candidatesFor(current);
    // The newest other release of the workspace's own model, as the mock-up proposes it; for
    // another model nothing is chosen for the user (M6).
    const own = choices
      .filter((item) => item.key === current?.model.releaseKey)
      .sort((a, b) => b.installedAt.localeCompare(a.installedAt))[0];
    return own?.id ?? "";
  });
  const release = releases.find((item) => item.id === releaseId);
  const groups = groupedCandidates(candidatesFor(workspace), workspace?.model.releaseKey);
  // A workspace whose own model has no other release: said first, so the list does not look empty.
  const ownWithNoOther = !fixedRelease && !groups.some((model) => model.key === workspace?.model.releaseKey);
  // The models whose releases are shown: the workspace's own, and the chosen release's (M6).
  const [opened, setOpened] = useState<Set<string>>(
    () =>
      new Set(
        [
          workspaces.find((item) => item.key === fixedWorkspace)?.model.releaseKey,
          releases.find((item) => item.id === fixedRelease)?.key,
        ].filter((key): key is string => Boolean(key)),
      ),
  );
  const [check, setCheck] = useState<Check>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const checkKey = `${workspaceKey}:${releaseId}`;
  useEffect(() => {
    if (!workspace || !releaseId) return;
    let active = true;
    Promise.all([
      api.modelReleaseDiff(releaseId, workspace.model.releaseId, workspace.key),
      openChangeSets(workspace.key),
    ])
      .then(([diff, changeSets]) => {
        if (!active) return;
        const leftBehind = changeSets.filter((item) => item.modelReleaseId === workspace.model.releaseId);
        setCheck({ key: checkKey, state: "ready", diff, leftBehind });
      })
      .catch((cause) => active && setCheck({ key: checkKey, state: "error", message: errorMessage(cause) }));
    return () => {
      active = false;
    };
  }, [checkKey, releaseId, workspace]);

  const current = check?.key === checkKey ? check : undefined;
  const compatibility = current?.state === "ready" ? current.diff.compatibility : undefined;
  const contractsBreak =
    current?.state === "ready" && current.diff.consumerContracts?.classification === "version_required";
  const fits = compatibility?.classification === "compatible" && !contractsBreak;
  const sameModel = release?.key === workspace?.model.releaseKey;
  const others = workspaces.filter((item) => item.key !== workspaceKey);

  async function activate() {
    if (!workspace || !release) return;
    setPending(true);
    setError("");
    try {
      const result = await api.activateWorkspaceModel(release.id, { ...workspace.model, workspaceKey: workspace.key });
      onActivated(result, workspace);
    } catch (cause) {
      setError(activationRefusal(cause));
    } finally {
      setPending(false);
    }
  }

  const title = fixedWorkspace
    ? `Change the model of ${workspace?.label ?? fixedWorkspace}`
    : `Activate ${release ? `${release.name} ${release.version}` : "the release"} in a workspace`;
  return (
    <Modal
      title={title}
      eyebrow="Workspace model"
      description={
        workspace
          ? `${workspace.label} runs ${workspaceModelLabel(workspace)}. Only its data is checked and changed.`
          : undefined
      }
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body activate-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (fits && !pending) void activate();
        }}
      >
        {fixedRelease ? (
          <SelectField
            label="Workspace"
            value={workspaceKey}
            onChange={setWorkspaceKey}
            options={workspaces
              .filter((item) => item.model.releaseId !== fixedRelease)
              .map((item) => ({ id: item.key, label: item.label, description: workspaceModelLabel(item) }))}
          />
        ) : (
          <fieldset className="activate-releases">
            <legend>Release</legend>
            {ownWithNoOther && workspace && (
              <p className="activate-release-group activate-release-own">
                <span className="activate-release-head is-static">
                  {workspace.model.releaseName}
                  <StatusPill tone="neutral" marker={false}>
                    This workspace's model
                  </StatusPill>
                  <span className="activate-release-count">no other release</span>
                </span>
              </p>
            )}
            {groups.map((model) => {
              const open = opened.has(model.key);
              const own = model.key === workspace?.model.releaseKey;
              return (
                <fieldset key={model.key} className="activate-release-group">
                  <legend>
                    <button
                      type="button"
                      className="activate-release-head"
                      aria-expanded={open}
                      onClick={() =>
                        setOpened((keys) => {
                          const next = new Set(keys);
                          if (open) next.delete(model.key);
                          else next.add(model.key);
                          return next;
                        })
                      }
                    >
                      <Icon name={open ? "chevron-down" : "chevron-right"} />
                      {model.name}
                      {own && (
                        <StatusPill tone="neutral" marker={false}>
                          This workspace's model
                        </StatusPill>
                      )}
                      <span className="activate-release-count">
                        {model.releases.length} {model.releases.length === 1 ? "release" : "releases"}
                      </span>
                    </button>
                  </legend>
                  {open &&
                    model.releases.map((item, index) => {
                      const by = workspaces.filter((other) => other.model.releaseId === item.id);
                      return (
                        <label
                          key={item.id}
                          className={`activate-release-option${item.id === releaseId ? " selected" : ""}`}
                        >
                          <input
                            type="radio"
                            name="activate-release"
                            checked={item.id === releaseId}
                            onChange={() => setReleaseId(item.id)}
                          />
                          <span className="mono">{item.version}</span>
                          <small>
                            schema {item.schemaVersion}
                            {index === 0 ? " · newest" : ""}
                          </small>
                          {by.length > 0 && (
                            <StatusPill tone="success" marker={false}>
                              {by.map((other) => other.label).join(", ")}
                            </StatusPill>
                          )}
                        </label>
                      );
                    })}
                </fieldset>
              );
            })}
          </fieldset>
        )}
        {workspace && release && !current && <Skeleton lines={2} label={`Checking ${workspace.label}'s data`} />}
        {current?.state === "error" && (
          <Notice tone="error" title="Could not be checked">
            {current.message}
          </Notice>
        )}
        {current?.state === "ready" && workspace && release && (
          <>
            {compatibility?.classification === "compatible" ? (
              <Notice tone="success" title={`Compatible with ${workspace.label}'s data`}>
                No record, value or relationship of {workspace.label} needs a migration.
              </Notice>
            ) : (
              <Notice tone="warning" title={sameModel ? "A migration is needed" : "A different model"}>
                <p>
                  {workspace.label}'s data does not fit {release.name} {release.version} as it is, so it cannot be
                  activated there. Migrating a workspace's data to another release is not available yet.
                </p>
                <MigrationReasons diagnostics={compatibility?.diagnostics ?? []} />
              </Notice>
            )}
            {contractsBreak && (
              <Notice tone="warning" title="A consumer API needs a higher contract version">
                {current.diff.consumerContracts?.diagnostics.map((item) => item.message).join(" ")}
              </Notice>
            )}
            {fits && (
              <section aria-labelledby="activate-left-behind" className="activate-left-behind">
                <h3 id="activate-left-behind" className="install-heading">
                  Change sets left on {workspace.model.releaseVersion}
                </h3>
                {current.leftBehind.length ? (
                  <>
                    <p className="muted">
                      These open change sets of {workspace.label} stay pinned to the release it runs now. They cannot be
                      published until each is moved to the new release or discarded.
                    </p>
                    <ul>
                      {current.leftBehind.map((item) => (
                        <li key={item.id}>
                          {item.name ?? "Unnamed change set"} · version {item.version}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="muted">None: {workspace.label} has no open change set.</p>
                )}
              </section>
            )}
            {others.length > 0 && (
              <p className="muted">
                Not changed: {others.map((item) => `${item.label} (${workspaceModelLabel(item)})`).join(", ")}.
              </p>
            )}
          </>
        )}
        {error && (
          <Notice tone="error" title="Not activated">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          {fits && workspace && release && (
            <button type="submit" className="primary" disabled={pending}>
              {pending ? "Activating…" : `Activate ${release.version} in ${workspace.label}`}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}

/** The first reasons the data does not fit, in plain words; the release's page lists every one. */
const REASONS_SHOWN = 5;

function MigrationReasons({ diagnostics }: { diagnostics: ModelDiagnostic[] }) {
  if (!diagnostics.length) return null;
  const more = diagnostics.length - REASONS_SHOWN;
  return (
    <ul className="migration-reasons">
      {diagnostics.slice(0, REASONS_SHOWN).map((item, index) => (
        <li key={`${item.path}:${index}`}>{item.message}</li>
      ))}
      {more > 0 && (
        <li>
          And {more} more {more === 1 ? "reason" : "reasons"}, listed on the release's page.
        </li>
      )}
    </ul>
  );
}
