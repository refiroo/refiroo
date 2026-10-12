/**
 * Load the draft's workbook into a change set (0.10 A5b, D81): one confirmed dialog over three
 * existing routes, no combined one. First the model: installed, which saves the draft's profile as
 * an instance profile (D80), and activated when the release is not the active one, with a new
 * version when the model changed (D18). Then a new change set named after the file, and the import
 * of the stored file through that profile (`independent`, records found updated). The job is
 * followed until it ends; then Open the change set review. Live loads stay the API's (principle 6).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { DraftProfile, DryRun, Job, ModelCompilation, ModelDraftOutline, ModelRelease, Workspace } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { importRequest } from "@/features/jobs/importRequest";
import { activationRefusal, ReleaseIdentityFields, useReleaseIdentity } from "@/features/model-editor/InstallDialog";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { dryRunLabel } from "@/features/model-editor/DryRunPanel";

type Stage = "ready" | "installing" | "opening" | "loading" | "done" | "stopped";

/** A change set's name for a file: "Load items.xlsx (2026-10-12)". */
export function changeSetName(file: string, today = new Date()): string {
  return `Load ${file} (${today.toISOString().slice(0, 10)})`;
}

export function LoadDialog({
  draftId,
  outline,
  profile,
  dryRun,
  defaultWorkspace,
  run,
  latestVersion,
  onActivated,
  onOpenReview,
  onClose,
}: {
  draftId: string;
  outline: ModelDraftOutline;
  profile: DraftProfile;
  dryRun: DryRun | undefined;
  defaultWorkspace: string;
  run: RunStep;
  latestVersion: () => number;
  /** The active model changed: reload it before the review opens. */
  onActivated: (release: ModelRelease) => Promise<void>;
  onOpenReview: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
  onClose: () => void;
}) {
  const file = profile.sourceFile?.name ?? "the workbook";
  const [compilation, setCompilation] = useState<ModelCompilation>();
  const [activeId, setActiveId] = useState<string>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loadError, setLoadError] = useState("");
  const identity = useReleaseIdentity(outline);
  const [name, setName] = useState(() => changeSetName(file));
  const [workspace, setWorkspace] = useState(dryRun?.workspaceKey ?? defaultWorkspace);
  const [stage, setStage] = useState<Stage>("ready");
  const [error, setError] = useState("");
  const [job, setJob] = useState<Job>();
  const [changeSetId, setChangeSetId] = useState<string>();

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.compileModelDraft(draftId, outline.version), api.modelRuntimeState(), api.workspaces()])
      .then(([compiled, state, page]) => {
        if (cancelled) return;
        setCompilation(compiled);
        setActiveId(state.activeReleaseId);
        setWorkspaces(page.items);
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
    // The model is read once, when the dialog opens: a step taken here moves the version on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftId]);

  useJobStream(job && !isFinal(job) ? job.id : undefined, (next) => {
    setJob(next);
    if (isFinal(next)) setStage(next.state === "completed" ? "done" : "stopped");
  });

  // The model changed against its base release, or its release is not the active one: install and
  // activate first. Otherwise installing finds the same release and only saves the profile.
  const modelChanged = Boolean(compilation && compilation.changes.length > 0);
  const activates = modelChanged || (activeId !== undefined && outline.baseReleaseId !== activeId);
  const contractsBreak = compilation?.consumerContracts?.classification === "version_required";
  const blocked =
    !compilation?.valid ||
    contractsBreak ||
    !profile.valid ||
    !workspace ||
    !name.trim() ||
    (modelChanged && !identity.complete);
  const applicationKey = profile.profile?.sources.find((item) => item.columns.length > 0)?.applicationKey ?? "";

  async function load() {
    setError("");
    try {
      setStage("installing");
      if (modelChanged && identity.changed) {
        if ((await run([identity.operation])) === "stale") {
          setStage("ready");
          setError("The draft changed since the dialog opened. Check it, then load again.");
          return;
        }
      }
      const release = await api.installModelDraft(draftId, latestVersion());
      if (!release.importProfile) {
        setStage("stopped");
        setError(
          `${release.name} ${release.version} is installed, but the profile does not hold against it and was not saved. The Issues list says why.`,
        );
        return;
      }
      if (!release.active) {
        try {
          await api.activateModelRelease(release.id, await api.modelRuntimeState());
        } catch (cause) {
          setStage("stopped");
          setError(`${release.name} ${release.version} is installed but not active: ${activationRefusal(cause)}`);
          return;
        }
        await onActivated(release);
      }
      setStage("opening");
      const changeSet = await api.createChangeSet(workspace, name.trim());
      setChangeSetId(changeSet.id);
      setStage("loading");
      const request = importRequest(
        { workspaceKey: workspace, changeSet: { id: changeSet.id, name: changeSet.name, version: changeSet.version } },
        release.importProfile.key,
        "independent",
        "overwrite",
      );
      setJob(
        await api.startImportOfSourceFile(
          { ...request, stage: "execute", sourceFileId: profile.sourceFile?.id ?? "" },
          crypto.randomUUID(),
        ),
      );
    } catch (cause) {
      setStage("stopped");
      setError(errorMessage(cause));
    }
  }

  const step = (index: number) => {
    const order: Stage[] = ["installing", "opening", "loading", "done"];
    const at = stage === "ready" ? -1 : stage === "stopped" ? order.length : order.indexOf(stage);
    return `load-step-number${at > index ? " done" : at === index ? " now" : ""}`;
  };
  const working = stage === "installing" || stage === "opening" || stage === "loading";
  const counts = job?.counts;
  return (
    <Modal
      title={`Load ${file} into a change set`}
      eyebrow="Load the workbook"
      description={
        dryRun?.summary ? `The dry run of draft version ${dryRun.draftVersion}: ${dryRunLabel(dryRun)}.` : undefined
      }
      busy={working}
      onClose={onClose}
    >
      <form
        className="dialog-body load-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (stage === "ready" && !blocked) void load();
        }}
      >
        {loadError && <Notice tone="error">{loadError}</Notice>}
        {!compilation && !loadError && <Skeleton lines={3} label="Comparing the draft with the active model" />}
        {compilation && (
          <ol className="load-steps">
            <li>
              <span className={step(0)} aria-hidden="true">
                1
              </span>
              <div>
                <strong>{activates ? "Install and activate the model" : "Keep the active model"}</strong>
                <p className="muted">
                  {!compilation.valid
                    ? "The draft has errors: each is in the Issues list."
                    : modelChanged
                      ? "The draft changed the model: it is installed as a new release and activated. The profile is saved with it."
                      : activates
                        ? "The draft's release is installed but not active: it is activated. The profile is saved with it."
                        : "The model is unchanged. The profile is saved as the instance's import profile."}
                </p>
                {modelChanged && stage === "ready" && <ReleaseIdentityFields identity={identity} outline={outline} />}
                {contractsBreak && (
                  <Notice tone="warning">
                    A consumer API needs a higher contract version: raise it in Install and activate first.
                  </Notice>
                )}
                {!profile.valid && (
                  <Notice tone="warning">
                    The profile has problems an import would refuse: each is in the Issues list.
                  </Notice>
                )}
              </div>
            </li>
            <li>
              <span className={step(1)} aria-hidden="true">
                2
              </span>
              <div className="load-step-fields">
                <strong>Open a change set</strong>
                <FormField label="Change set name">
                  {(control) => (
                    <input
                      {...control}
                      value={name}
                      disabled={stage !== "ready"}
                      onChange={(event) => setName(event.target.value)}
                    />
                  )}
                </FormField>
                <FormField label="Workspace">
                  {(control) => (
                    <select
                      {...control}
                      value={workspace}
                      disabled={stage !== "ready"}
                      onChange={(event) => setWorkspace(event.target.value)}
                    >
                      {workspaces.map((item) => (
                        <option key={item.key} value={item.key}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  )}
                </FormField>
              </div>
            </li>
            <li>
              <span className={step(2)} aria-hidden="true">
                3
              </span>
              <div>
                <strong>Load the rows</strong>
                <p className="muted">The stored file through the saved profile; records found are updated.</p>
                {job && stage === "loading" && (
                  <p role="status">
                    Loading · {job.progress.processed.toLocaleString()}
                    {job.progress.total ? ` of ${job.progress.total.toLocaleString()}` : ""} items
                  </p>
                )}
                {stage === "done" && counts && (
                  <Notice tone={counts.rejected ? "warning" : "success"} title="Loaded into the change set">
                    Records and relationships: {counts.created} created, {counts.updated} updated, {counts.unchanged}{" "}
                    unchanged{counts.rejected ? `; ${counts.rejected} refused` : ""}. Nothing is live until the change
                    set is published.
                  </Notice>
                )}
                {stage === "stopped" && job && job.state !== "completed" && (
                  <Notice tone="error" title="The load did not finish">
                    {job.error?.message ?? `The job ended ${job.state}.`}
                  </Notice>
                )}
              </div>
            </li>
          </ol>
        )}
        {error && (
          <Notice tone="error" title="Stopped" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={working}>
            {stage === "done" || stage === "stopped" ? "Close" : "Cancel"}
          </button>
          {stage === "done" && changeSetId ? (
            <button
              type="button"
              className="primary"
              autoFocus
              onClick={() => onOpenReview({ applicationKey, workspaceKey: workspace, changeSetId })}
            >
              Open the change set review
            </button>
          ) : (
            <button type="submit" className="primary" disabled={stage !== "ready" || blocked}>
              {stage === "installing"
                ? "Installing…"
                : stage === "opening"
                  ? "Opening the change set…"
                  : stage === "loading"
                    ? "Loading…"
                    : activates
                      ? "Install, activate and load"
                      : "Load"}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
