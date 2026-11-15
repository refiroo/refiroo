/**
 * Install and activate from the editor (0.10 A4a, A-D8, D18, D42): one confirmed step running the
 * existing installation and activation. It shows the release identity, its version proposed from
 * the base release and editable, the differences from the base release, validity and the
 * compatibility with stored data. A changed identity is a `setRelease` step first. A refused
 * activation leaves the installed release, and the dialog says so.
 *
 * Each consumer API is shown checked against what the active release's consumers read (0.10 A4c,
 * D58): one that needs a higher contract version offers the step that raises it, and activation
 * waits until none does, as the server would refuse it.
 *
 * The release is activated into one workspace (0.11 M5, D15, D55): an existing one, the editor's
 * first, or a new one created on it. No other workspace changes.
 */

import { freeKeyOf, setProfileKey, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";
import {
  freeVersionOf,
  setReleaseVersion,
  UseFreeVersion,
  versionTakenText,
  type FreeVersion,
} from "@/features/model-editor/ReleaseVersionConflict";
import { useEffect, useState } from "react";
import {
  activationRefusal,
  ActivationVerdict,
  ConsumerContracts,
  ReleaseIdentityFields,
  summarizeChanges,
  useReleaseIdentity,
} from "@/ui/ActivationParts";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted, plural } from "@/lib/count";
import type { ModelCompilation, ModelDraftOutline, ModelRelease, Workspace } from "@/types";
import { useCapabilities } from "@/state/useSystem";
import { NewWorkspaceFields, useNewWorkspaceIdentity } from "@/ui/NewWorkspaceFields";
import { workspaceModelLabel } from "@/ui/WorkspaceSelector";
import { SelectField } from "@/ui/Selection";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { DraftMigrationNotice, proposalOf, useDraftMigration } from "@/features/model-editor/DraftMigration";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { allWorkspaces } from "@/api/allWorkspaces";

type Outcome = { kind: "installed"; release: ModelRelease; reason: string } | { kind: "active"; release: ModelRelease };

/** Where the release is activated: an existing workspace, or a new one created on it (D55). */
type Into = { kind: "existing"; workspaceKey: string } | { kind: "new" };

export function InstallDialog({
  draftId,
  outline,
  run,
  latestVersion,
  workspaceKey: editorWorkspace,
  onActivated,
  onInstalledOnly,
  onMigrationStarted,
  onClose,
  onShowIssues,
}: {
  draftId: string;
  outline: ModelDraftOutline;
  run: RunStep;
  /** The draft's version now, after any step this dialog ran. */
  latestVersion: () => number;
  /** The editor's workspace (D55), offered first. */
  workspaceKey: string;
  /** The release is active in `workspace`. */
  onActivated: (release: ModelRelease, workspace: Pick<Workspace, "key" | "label">) => Promise<void>;
  onInstalledOnly: () => void;
  /** The release is installed and its migration previewed with the draft's mappings (0.13 MG): show it. */
  onMigrationStarted?: (jobId: string) => void;
  onClose: () => void;
  /** Closes the dialog and opens the editor's Issues tab; without it the issues are only named. */
  onShowIssues?: () => void;
}) {
  const [compilation, setCompilation] = useState<ModelCompilation>();
  const [loadError, setLoadError] = useState("");
  const identity = useReleaseIdentity(outline);
  const version = identity.version;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  // The profile's key belongs to another model: the key the engine found free.
  const [freeKey, setFreeKey] = useState<string>();
  // The release version is taken by another release of the model: the one the engine found free.
  const [freeVersion, setFreeVersion] = useState<FreeVersion>();
  const [outcome, setOutcome] = useState<Outcome>();
  const { capabilities } = useCapabilities();
  const canCreate = Boolean(capabilities?.workspaceAdmin.manageWorkspaces);
  const canMigrate = Boolean(capabilities?.modelAdmin.activate && capabilities?.integrationJobs.createJobs);
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [chosenInto, setInto] = useState<Into>();
  const newWorkspace = useNewWorkspaceIdentity();

  useEffect(() => {
    let cancelled = false;
    allWorkspaces({ status: "active" })
      .then((items) => !cancelled && setWorkspaces(items))
      .catch((cause) => !cancelled && setLoadError(errorMessage(cause)));
    return () => {
      cancelled = true;
    };
  }, []);

  // Proposed until chosen: the editor's workspace when it runs the draft's model; a new workspace for
  // a model no workspace runs, where workspaces may be created; else the editor's workspace.
  const modelKey = outline.release.key;
  const runsModel = workspaces?.some((item) => item.model.releaseKey === modelKey);
  const editorRuns = workspaces?.find((item) => item.key === editorWorkspace)?.model.releaseKey === modelKey;
  const into: Into =
    chosenInto ??
    (!editorRuns && !runsModel && canCreate ? { kind: "new" } : { kind: "existing", workspaceKey: editorWorkspace });
  const target = into.kind === "existing" ? workspaces?.find((item) => item.key === into.workspaceKey) : undefined;

  useEffect(() => {
    let cancelled = false;
    api
      .compileModelDraft(draftId, outline.version)
      .then((result) => {
        if (!cancelled) setCompilation(result);
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, outline.version]);

  const contractsBreak = compilation?.consumerContracts?.classification === "version_required";
  // The chosen workspace's own check when it runs the draft's model (D25); none for another model.
  const checked =
    into.kind === "existing"
      ? compilation?.compatibility.workspaces.find((item) => item.workspaceKey === into.workspaceKey)
      : undefined;
  const moves = checked?.classification === "migration_required";
  // The migration the draft states for that workspace (0.13 MG), read while it needs one.
  const {
    migration,
    error: migrationError,
    pending: migrationPending,
  } = useDraftMigration(
    draftId,
    into.kind === "existing" ? into.workspaceKey : undefined,
    Boolean(compilation?.valid && moves),
    outline.version,
  );
  const migrates = Boolean(moves && canMigrate && onMigrationStarted);
  // Starting the migration without the draft's mappings would move the data wrongly: wait for them.
  const mappingsMissing = migrates && (migrationPending || Boolean(migrationError));
  const blocked =
    mappingsMissing ||
    !compilation?.valid ||
    contractsBreak ||
    !identity.complete ||
    (into.kind === "new" ? !newWorkspace.complete : !target);

  async function confirm() {
    if (mappingsMissing) return;
    setPending(true);
    setError("");
    setFreeVersion(undefined);
    try {
      if (identity.changed) {
        const outcome = await run([identity.operation]);
        if (outcome === "stale") {
          onClose();
          return;
        }
      }
      const release = await api.installModelDraft(draftId, latestVersion());
      let workspace: Pick<Workspace, "key" | "label">;
      try {
        if (into.kind === "new") {
          workspace = await api.createWorkspace({
            key: newWorkspace.key.trim(),
            label: newWorkspace.label.trim(),
            modelReleaseId: release.id,
          });
        } else {
          const state = await api.workspaceModel(into.workspaceKey);
          if (migrates) {
            // The data must move first: preview the migration the draft states (0.13 MG).
            const job = await api.startWorkspaceMigration(into.workspaceKey, {
              targetReleaseId: release.id,
              expectedVersion: state.version,
              ...proposalOf(migration, draftId),
            });
            onMigrationStarted?.(job.id);
            return;
          }
          await api.activateWorkspaceModel(release.id, state);
          workspace = target!;
        }
      } catch (cause) {
        setOutcome({ kind: "installed", release, reason: activationRefusal(cause) });
        onInstalledOnly();
        return;
      }
      setOutcome({ kind: "active", release });
      await onActivated(release, workspace);
    } catch (cause) {
      const taken = freeVersionOf(cause);
      setFreeKey(freeKeyOf(cause));
      setFreeVersion(taken);
      setError(taken ? versionTakenText(taken) : errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  if (outcome?.kind === "installed")
    return (
      <Modal title="Installed, not active" eyebrow="Install and activate" size="compact" onClose={onClose}>
        <div className="dialog-body">
          <Notice
            tone="warning"
            title={`${outcome.release.name} ${outcome.release.version} is installed but not active`}
          >
            {outcome.reason} No workspace's model changed. Activate the release later from Settings › Model.
          </Notice>
          <div className="dialog-actions">
            <button type="button" className="primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </Modal>
    );

  const lines = compilation ? summarizeChanges(compilation.changes, outline) : [];
  const errors = compilation?.diagnostics.filter((item) => item.severity === "error") ?? [];
  const compatible = checked?.classification === "compatible";
  const others = (workspaces ?? []).filter((item) => into.kind === "new" || item.key !== into.workspaceKey);
  return (
    <Modal
      title="Install and activate"
      eyebrow="Release the draft"
      description="Creates an immutable release from this draft, then activates it in one workspace. This draft continues as the next version."
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body install-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending && !blocked) void confirm();
        }}
      >
        <ReleaseIdentityFields identity={identity} outline={outline} />
        <fieldset className="model-choice">
          <legend>Activate into</legend>
          <label className="checkbox">
            <input
              type="radio"
              name="activate-into"
              checked={into.kind === "existing"}
              onChange={() => setInto({ kind: "existing", workspaceKey: editorWorkspace })}
            />
            <span>An existing workspace</span>
          </label>
          {into.kind === "existing" && workspaces && (
            <SelectField
              label="Workspace"
              value={into.workspaceKey}
              onChange={(key) => setInto({ kind: "existing", workspaceKey: key })}
              options={[...workspaces]
                .sort((a, b) => Number(b.key === editorWorkspace) - Number(a.key === editorWorkspace))
                .map((item) => ({
                  id: item.key,
                  label: item.label,
                  description: workspaceModelLabel(item),
                  mark:
                    item.model.releaseKey === modelKey ? undefined : { label: "Other model", tone: "warning" as const },
                }))}
            />
          )}
          {canCreate && (
            <label className="checkbox">
              <input
                type="radio"
                name="activate-into"
                checked={into.kind === "new"}
                onChange={() => setInto({ kind: "new" })}
              />
              <span>A new workspace</span>
            </label>
          )}
          {into.kind === "new" && <NewWorkspaceFields identity={newWorkspace} qualified />}
          {others.length > 0 && (
            <small className="field-description">
              Only that workspace changes. {others.map((item) => item.label).join(", ")} keep their models.
            </small>
          )}
        </fieldset>
        {loadError && <Notice tone="error">{loadError}</Notice>}
        {!compilation && !loadError && <Skeleton lines={3} label="Comparing with the base release" />}
        {compilation && (
          <>
            <section aria-labelledby="install-changes">
              <h3 id="install-changes" className="install-heading">
                {outline.baseRelease?.version
                  ? `What changes against ${outline.baseRelease.version}`
                  : "What the release holds"}
              </h3>
              {compilation.valid ? (
                lines.length ? (
                  <dl className="install-changes">
                    {lines.map((line) => (
                      <div key={line.label}>
                        <dt>{line.label}</dt>
                        <dd>{line.names.join(", ")}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="muted">No model element changes.</p>
                )
              ) : null}
            </section>
            <div className="install-verdicts">
              {compilation.valid ? (
                <Notice tone="success" title="Valid">
                  No issues.
                </Notice>
              ) : (
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
              {compilation.valid &&
                (into.kind === "new" ? (
                  <Notice tone="success" title="A new workspace">
                    It starts empty on this release, so no data needs a migration.
                  </Notice>
                ) : compatible ? (
                  <Notice tone="success" title="Compatible with stored data">
                    No record, value or relationship of {target?.label ?? into.workspaceKey} needs a migration.
                  </Notice>
                ) : checked ? (
                  <>
                    {migrationError && (
                      <Notice tone="error" title="The migration could not be read">
                        {migrationError} Close this dialog and open it again.
                      </Notice>
                    )}
                    {migration ? (
                      <DraftMigrationNotice
                        migration={migration}
                        outline={outline}
                        label={target?.label ?? into.workspaceKey}
                        reasons={checked.diagnostics.map((item) => item.message).join(" ")}
                      />
                    ) : (
                      <ActivationVerdict>
                        {checked.diagnostics.map((item) => item.message).join(" ")} The release would be installed but
                        not activated.
                      </ActivationVerdict>
                    )}
                  </>
                ) : (
                  <Notice tone="info" title="Checked when activated">
                    {target?.label ?? into.workspaceKey} runs another model. Its data is checked against this release
                    first; if records have no place in it, the release is installed but not activated.
                  </Notice>
                ))}
            </div>
            {compilation.valid && compilation.consumerContracts && (
              <ConsumerContracts
                outline={outline}
                diagnostics={compilation.consumerContracts.diagnostics}
                run={run}
                pending={pending}
              />
            )}
          </>
        )}
        {error && (
          <Notice
            tone="error"
            title="Not installed"
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
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || blocked}>
            {pending
              ? "Installing…"
              : into.kind === "new"
                ? `Install ${version.trim()} and create ${newWorkspace.label.trim() || "the workspace"}`
                : migrates
                  ? `Install ${version.trim()} and preview the migration…`
                  : `Install ${version.trim()} and activate in ${target?.label ?? into.workspaceKey}`}
          </button>
        </div>
      </form>
    </Modal>
  );
}
