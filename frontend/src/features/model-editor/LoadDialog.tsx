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
import { freeKeyOf, setProfileKey, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";
import {
  freeVersionOf,
  setReleaseVersion,
  UseFreeVersion,
  versionTakenText,
  type FreeVersion,
} from "@/features/model-editor/ReleaseVersionConflict";
import type { DraftProfile, DryRun, Job, ModelCompilation, ModelDraftOutline, ModelRelease } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { isFinal, useJobStream } from "@/state/useJobStream";
import {
  ChangeSetFields,
  changeSetName,
  loadIntoChangeSet,
  LoadProgress,
  LoadStep,
  stepState,
} from "@/ui/ChangeSetLoad";
import { activationRefusal, ReleaseIdentityFields, useReleaseIdentity } from "@/features/model-editor/InstallDialog";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { dryRunLabel } from "@/features/model-editor/DryRunPanel";

type Stage = "ready" | "installing" | "opening" | "loading" | "done" | "stopped";
const ORDER: Stage[] = ["installing", "opening", "loading", "done"];

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
  /** The release was activated into `workspaceKey`, the workspace the file loads into. */
  onActivated: (release: ModelRelease, workspaceKey: string) => Promise<void>;
  onOpenReview: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
  onClose: () => void;
}) {
  const file = profile.sourceFile?.name ?? "the workbook";
  const [compilation, setCompilation] = useState<ModelCompilation>();
  const [activeId, setActiveId] = useState<string>();
  const [loadError, setLoadError] = useState("");
  const identity = useReleaseIdentity(outline);
  const [name, setName] = useState(() => changeSetName(file));
  const [workspace, setWorkspace] = useState(dryRun?.workspaceKey ?? defaultWorkspace);
  const [stage, setStage] = useState<Stage>("ready");
  const [error, setError] = useState("");
  // The profile's key belongs to another model: the key the engine found free.
  const [freeKey, setFreeKey] = useState<string>();
  // The release version is taken by another release of the model: the one the engine found free.
  const [freeVersion, setFreeVersion] = useState<FreeVersion>();
  const [job, setJob] = useState<Job>();
  const [changeSetId, setChangeSetId] = useState<string>();

  useEffect(() => {
    let cancelled = false;
    api
      .compileModelDraft(draftId, outline.version)
      .then((compiled) => {
        if (!cancelled) setCompilation(compiled);
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

  // The release the workspace loaded into runs now (0.11 M5): the draft activates there if it differs.
  useEffect(() => {
    let cancelled = false;
    api
      .workspaceModel(workspace)
      .then((state) => !cancelled && setActiveId(state.releaseId))
      .catch((cause) => !cancelled && setLoadError(errorMessage(cause)));
    return () => {
      cancelled = true;
    };
  }, [workspace]);

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
      setFreeKey(undefined);
      setFreeVersion(undefined);
      const release = await api.installModelDraft(draftId, latestVersion());
      if (!release.importProfile) {
        setStage("stopped");
        setError(
          `${release.name} ${release.version} is installed, but the profile does not hold against it and was not saved. The Issues list says why.`,
        );
        return;
      }
      // The release runs in the workspace the file loads into (0.11 M1), activated there.
      if (!release.workspaces.includes(workspace)) {
        try {
          await api.activateWorkspaceModel(release.id, await api.workspaceModel(workspace));
        } catch (cause) {
          setStage("stopped");
          setFreeKey(freeKeyOf(cause));
          setError(`${release.name} ${release.version} is installed but not active: ${activationRefusal(cause)}`);
          return;
        }
        await onActivated(release, workspace);
      }
      setStage("opening");
      setJob(
        await loadIntoChangeSet({
          workspace,
          name,
          profileKey: release.importProfile.key,
          sourceFileId: profile.sourceFile?.id ?? "",
          onOpened: (changeSet) => {
            setChangeSetId(changeSet.id);
            setStage("loading");
          },
        }),
      );
    } catch (cause) {
      const free = freeKeyOf(cause);
      const taken = freeVersionOf(cause);
      setFreeKey(free);
      setFreeVersion(taken);
      // A key or version to change is a step to take here, then load again: the dialog is not over.
      setStage(free || taken ? "ready" : "stopped");
      setError(taken ? versionTakenText(taken) : errorMessage(cause));
    }
  }

  const working = stage === "installing" || stage === "opening" || stage === "loading";
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
            <LoadStep number={1} state={stepState(ORDER, stage, 0)}>
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
                  {profile.profile
                    ? "The profile has problems an import would refuse: each is in the Issues list."
                    : "Nothing is mapped yet: map the workbook's columns onto the model first."}
                </Notice>
              )}
            </LoadStep>
            <LoadStep number={2} state={stepState(ORDER, stage, 1)} fields>
              <strong>Open a change set</strong>
              <ChangeSetFields
                name={name}
                onName={setName}
                workspace={workspace}
                onWorkspace={setWorkspace}
                onError={setLoadError}
                disabled={stage !== "ready"}
              />
            </LoadStep>
            <LoadStep number={3} state={stepState(ORDER, stage, 2)}>
              <strong>Load the rows</strong>
              <p className="muted">The stored file through the saved profile; records found are updated.</p>
              <LoadProgress job={job} stage={stage} />
            </LoadStep>
          </ol>
        )}
        {error && (
          <Notice
            tone="error"
            title={
              freeKey ? "The profile's key belongs to another model" : freeVersion ? "The version is taken" : "Stopped"
            }
            focusOnMount
            actions={
              (freeKey || freeVersion) && (
                <>
                  {freeKey && (
                    <UseFreeKey
                      freeKey={freeKey}
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
