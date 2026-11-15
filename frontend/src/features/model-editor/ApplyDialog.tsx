/**
 * Apply a workspace's draft to it (0.16 WM1): one confirmed step over the existing installation, then
 * activation or a migration. It says what changes in the model and what happens to the records, in
 * the activation dialog's words. Where records must move the release is installed and the migration
 * page takes over; nothing changes in the workspace until that page's confirmation.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { counted, plural } from "@/lib/count";
import { LeftBehindChangeSets, MigrationReasons, openChangeSets } from "@/ui/ActivationParts";
import { ImpactSummary } from "@/ui/ImpactSummary";
import {
  activationRefusal,
  ConsumerContracts,
  ReleaseIdentityFields,
  summarizeChanges,
  useReleaseIdentity,
} from "@/features/model-editor/InstallDialog";
import { DraftMigrationNotice, proposalOf, useDraftMigration } from "@/features/model-editor/DraftMigration";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { freeKeyOf, setProfileKey, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";
import {
  freeVersionOf,
  setReleaseVersion,
  UseFreeVersion,
  versionTakenText,
  type FreeVersion,
} from "@/features/model-editor/ReleaseVersionConflict";
import { useCapabilities } from "@/state/useSystem";
import { workspaceModelLabel } from "@/ui/WorkspaceSelector";
import type { ChangeSet, ModelCompilation, ModelDraftOutline, ModelRelease, Workspace } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { allWorkspaces } from "@/api/allWorkspaces";

export function ApplyDialog({
  draftId,
  outline,
  run,
  latestVersion,
  workspaceKey,
  onApplied,
  onMigrationStarted,
  onClose,
  onShowIssues,
}: {
  draftId: string;
  outline: ModelDraftOutline;
  run: RunStep;
  /** The draft's version now, after any step this dialog ran. */
  latestVersion: () => number;
  workspaceKey: string;
  onApplied: (release: ModelRelease, workspace: Workspace) => Promise<void>;
  /** The release is installed and the migration's preview started: its job. */
  onMigrationStarted: (jobId: string) => void;
  onClose: () => void;
  /** Closes the dialog and opens the editor's Issues tab; without it the issues are only named. */
  onShowIssues?: () => void;
}) {
  const [compilation, setCompilation] = useState<ModelCompilation>();
  // The workspace applied to, read by its key, and the other active ones, every page of them.
  const [target, setTarget] = useState<Workspace>();
  const [others, setOthers] = useState<Workspace[]>();
  const [changeSets, setChangeSets] = useState<ChangeSet[]>();
  const [loadError, setLoadError] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [freeKey, setFreeKey] = useState<string>();
  // The release version is taken by another release of the model: the one the engine found free.
  const [freeVersion, setFreeVersion] = useState<FreeVersion>();
  // Installed, and the activation refused: Try again repeats the activation alone.
  const [installed, setInstalled] = useState<ModelRelease>();
  const identity = useReleaseIdentity(outline);
  const { capabilities } = useCapabilities();

  useEffect(() => {
    let active = true;
    api
      .compileModelDraft(draftId, outline.version)
      .then((result) => active && setCompilation(result))
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [draftId, outline.version]);

  useEffect(() => {
    let active = true;
    // Every other active workspace, in list order: the "Not changed" line names them all.
    const otherWorkspaces = async () =>
      (await allWorkspaces({ status: "active" })).filter((item) => item.key !== workspaceKey);
    Promise.all([api.workspace(workspaceKey), otherWorkspaces(), openChangeSets(workspaceKey)])
      .then(([own, rest, open]) => {
        if (!active) return;
        setTarget(own);
        setOthers(rest);
        setChangeSets(open);
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspaceKey]);

  const workspace = target;
  const label = workspace?.label ?? workspaceKey;
  const leftBehind = (changeSets ?? []).filter((item) => item.modelReleaseId === workspace?.model.releaseId);
  const lines = compilation ? summarizeChanges(compilation.changes, outline) : [];
  const errors = compilation?.diagnostics.filter((item) => item.severity === "error") ?? [];
  const modelChanged = Boolean(compilation && compilation.changes.length > 0);
  // Nothing new against the base, and the base is what runs here. A base that does not run here is
  // a release an earlier Apply installed, which still has to reach the workspace.
  const nothing = compilation?.valid && !modelChanged && outline.baseReleaseId === workspace?.model.releaseId;
  const contractsBreak = compilation?.consumerContracts?.classification === "version_required";
  const check = compilation?.compatibility.workspaces.find((item) => item.workspaceKey === workspaceKey);
  const moves = check?.classification === "migration_required";
  const canMigrate = Boolean(capabilities?.modelAdmin.activate && capabilities?.integrationJobs.createJobs);
  const ready = compilation?.valid && !nothing && !contractsBreak && workspace && (!modelChanged || identity.complete);
  // The migration the draft states for this workspace (0.13 MG), read while the data must move.
  const {
    migration,
    error: migrationError,
    pending: migrationPending,
  } = useDraftMigration(draftId, workspaceKey, Boolean(compilation?.valid && moves), outline.version);
  // Starting the migration without the draft's mappings would move the data wrongly: wait for them.
  const offered = ready && (!moves || (canMigrate && !migrationPending && !migrationError));

  async function apply() {
    if (!workspace || !offered) return;
    setPending(true);
    setError("");
    setFreeKey(undefined);
    setFreeVersion(undefined);
    try {
      let release = installed;
      if (!release) {
        if (modelChanged && identity.changed && (await run([identity.operation])) === "stale") {
          setError("The draft changed since the dialog opened. Check it, then apply again.");
          return;
        }
        release = await api.installModelDraft(draftId, latestVersion());
        // Installed: whatever follows fails, a retry never installs again.
        setInstalled(release);
      }
      const state = await api.workspaceModel(workspaceKey);
      if (moves) {
        const job = await api.startWorkspaceMigration(workspaceKey, {
          targetReleaseId: release.id,
          expectedVersion: state.version,
          ...proposalOf(migration, draftId),
        });
        onMigrationStarted(job.id);
        return;
      }
      try {
        await api.activateWorkspaceModel(release.id, state);
      } catch (cause) {
        setError(
          `${release.name} ${release.version} is installed, but ${label} did not change: ${activationRefusal(cause)}`,
        );
        return;
      }
      await onApplied(release, workspace);
    } catch (cause) {
      const taken = freeVersionOf(cause);
      setFreeKey(freeKeyOf(cause));
      setFreeVersion(taken);
      setError(taken ? versionTakenText(taken) : errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const loading = !loadError && (!compilation || !target || !others || !changeSets);
  return (
    <Modal
      title={`Apply to ${label}`}
      eyebrow="Workspace model"
      description={
        workspace ? `${label} runs ${workspaceModelLabel(workspace)}. Only its data is checked and changed.` : undefined
      }
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body install-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending && offered) void apply();
        }}
      >
        {loadError && <Notice tone="error">{loadError}</Notice>}
        {loading && <Skeleton lines={3} label={`Checking ${label}'s data`} />}
        {!loading && compilation && workspace && (
          <>
            {!compilation.valid && (
              <Notice tone="error" title="Not valid">
                {counted(errors.length, "issue stops", "issues stop")} this step.{" "}
                {onShowIssues ? (
                  <button type="button" className="link-button" onClick={onShowIssues}>
                    Show {plural(errors.length, "it", "each")} in the Issues list
                  </button>
                ) : (
                  "Each is in the Issues list."
                )}
              </Notice>
            )}
            {nothing && (
              <Notice tone="info" title="Nothing to apply yet">
                This draft matches what {label} runs.
              </Notice>
            )}
            {compilation.valid && !nothing && (
              <>
                <section aria-labelledby="apply-changes">
                  <h3 id="apply-changes" className="install-heading">
                    What changes in the model
                  </h3>
                  {lines.length ? (
                    <dl className="install-changes">
                      {lines.map((line) => (
                        <div key={line.label}>
                          <dt>{line.label}</dt>
                          <dd>{line.names.join(", ")}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p className="muted">Nothing new: this draft's release has not reached {label} yet.</p>
                  )}
                </section>
                {moves && migrationError && (
                  <Notice tone="error" title="The migration could not be read">
                    {migrationError} Close this dialog and open it again.
                  </Notice>
                )}
                {moves && migration ? (
                  <>
                    <DraftMigrationNotice
                      migration={migration}
                      outline={outline}
                      label={label}
                      reasons={(check?.diagnostics ?? []).map((item) => item.message).join(" ")}
                    />
                    <p className="muted">
                      {canMigrate
                        ? "Nothing changes yet. The next page lists every conversion and loss, and you confirm there."
                        : "Migrating needs model administration and background jobs, which this deployment does not run."}
                    </p>
                  </>
                ) : moves ? (
                  <Notice tone="warning" title="Some records must move first">
                    <p>
                      {label}'s data does not fit the changed model as it is.{" "}
                      {canMigrate
                        ? "Nothing changes yet. The next page lists every conversion and loss, and you confirm there."
                        : "Migrating needs model administration and background jobs, which this deployment does not run."}
                    </p>
                    <MigrationReasons diagnostics={check?.diagnostics ?? []} />
                  </Notice>
                ) : (
                  <Notice tone="success" title="Your records stay as they are">
                    No record, value or relationship of {label} needs to move.
                  </Notice>
                )}
                <ImpactSummary
                  key={`${draftId}:${outline.version}`}
                  workspaceKey={workspaceKey}
                  ask={(signal) => ai.explainDraft(draftId, { workspaceKey, expectedVersion: latestVersion() }, signal)}
                />
                {compilation.consumerContracts && (
                  <ConsumerContracts
                    outline={outline}
                    diagnostics={compilation.consumerContracts.diagnostics}
                    run={run}
                    pending={pending}
                  />
                )}
                {!moves && (
                  <LeftBehindChangeSets
                    workspaceLabel={label}
                    version={workspace.model.releaseVersion}
                    changeSets={leftBehind}
                  />
                )}
                {others && others.length > 0 && (
                  <p className="muted">
                    Not changed: {others.map((item) => `${item.label} (${workspaceModelLabel(item)})`).join(", ")}.
                  </p>
                )}
                {modelChanged && !installed && (
                  <details>
                    <summary>
                      Becomes release {identity.name} {identity.version}
                    </summary>
                    <ReleaseIdentityFields identity={identity} outline={outline} />
                  </details>
                )}
              </>
            )}
          </>
        )}
        {error && (
          <Notice
            tone="error"
            title="Not applied"
            focusOnMount
            actions={
              (freeKey || freeVersion) && (
                <>
                  {freeKey && (
                    <UseFreeKey
                      freeKey={freeKey}
                      disabled={pending}
                      onUse={() =>
                        void run([setProfileKey(freeKey)]).then((outcome) => {
                          if (outcome === "applied") {
                            setError("");
                            setFreeKey(undefined);
                          }
                        })
                      }
                    />
                  )}
                  {freeVersion && (
                    <UseFreeVersion
                      version={freeVersion.free}
                      disabled={pending}
                      onUse={() => {
                        identity.setVersion(freeVersion.free);
                        void run([setReleaseVersion(identity, freeVersion.free)]).then((outcome) => {
                          if (outcome === "applied") {
                            setError("");
                            setFreeVersion(undefined);
                          }
                        });
                      }}
                    />
                  )}
                </>
              )
            }
          >
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            {offered ? "Cancel" : "Close"}
          </button>
          {offered && (
            <button type="submit" className="primary" disabled={pending}>
              {pending
                ? "Applying…"
                : installed
                  ? "Try again"
                  : moves
                    ? "Preview what happens to the records…"
                    : `Apply to ${label}`}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
