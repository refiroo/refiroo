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
import { LeftBehindChangeSets, MigrationReasons, openChangeSets } from "@/features/model-admin/ActivateDialog";
import { ImpactSummary } from "@/features/model-admin/ImpactSummary";
import {
  activationRefusal,
  ConsumerContracts,
  ReleaseIdentityFields,
  summarizeChanges,
  useReleaseIdentity,
} from "@/features/model-editor/InstallDialog";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { freeKeyOf, setProfileKey, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";
import { useCapabilities } from "@/features/settings/useSystem";
import { workspaceModelLabel } from "@/features/workspaces/WorkspaceSelector";
import type { ChangeSet, ModelCompilation, ModelDraftOutline, ModelRelease, Workspace } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";

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
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [changeSets, setChangeSets] = useState<ChangeSet[]>();
  const [loadError, setLoadError] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [freeKey, setFreeKey] = useState<string>();
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
    Promise.all([api.workspaces({ status: "active", pageSize: 100 }), openChangeSets(workspaceKey)])
      .then(([page, open]) => {
        if (!active) return;
        setWorkspaces(page.items);
        setChangeSets(open);
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspaceKey]);

  const workspace = workspaces?.find((item) => item.key === workspaceKey);
  const label = workspace?.label ?? workspaceKey;
  const others = (workspaces ?? []).filter((item) => item.key !== workspaceKey);
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
  const offered = ready && (!moves || canMigrate);

  async function apply() {
    if (!workspace) return;
    setPending(true);
    setError("");
    setFreeKey(undefined);
    try {
      let release = installed;
      if (!release) {
        if (modelChanged && identity.changed && (await run([identity.operation])) === "stale") {
          setError("The draft changed since the dialog opened. Check it, then apply again.");
          return;
        }
        release = await api.installModelDraft(draftId, latestVersion());
      }
      const state = await api.workspaceModel(workspaceKey);
      if (moves) {
        const job = await api.startWorkspaceMigration(workspaceKey, {
          targetReleaseId: release.id,
          expectedVersion: state.version,
        });
        onMigrationStarted(job.id);
        return;
      }
      try {
        await api.activateWorkspaceModel(release.id, state);
      } catch (cause) {
        setInstalled(release);
        setError(
          `${release.name} ${release.version} is installed, but ${label} did not change: ${activationRefusal(cause)}`,
        );
        return;
      }
      await onApplied(release, workspace);
    } catch (cause) {
      setFreeKey(freeKeyOf(cause));
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const loading = !loadError && (!compilation || !workspaces || !changeSets);
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
                {errors.length} {errors.length === 1 ? "issue stops" : "issues stop"} this step.{" "}
                {onShowIssues ? (
                  <button type="button" className="link-button" onClick={onShowIssues}>
                    Show {errors.length === 1 ? "it" : "each"} in the Issues list
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
                {moves ? (
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
                {others.length > 0 && (
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
              freeKey && (
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
