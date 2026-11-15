/**
 * Load a stored profile's latest file into a new change set (0.10 A5c, D85): the editor's load
 * without the model step (D81), since a stored profile holds against the active release already. A
 * change set named after the file in the workspace the check ran in, the import of the stored file
 * through the profile, the job followed until it ends; then Open the change set review, which lists
 * only what the file changes.
 */

import { useState } from "react";
import { errorMessage } from "@/api/errors";
import type { SourceFile } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { isFinal, useFollowedJob } from "@/state/useFollowedJob";
import {
  ChangeSetFields,
  changeSetName,
  loadIntoChangeSet,
  LoadProgress,
  LoadStep,
  stepState,
} from "@/ui/ChangeSetLoad";

type Stage = "ready" | "opening" | "loading" | "done" | "stopped";
const ORDER: Stage[] = ["opening", "loading", "done"];

export function ProfileLoadDialog({
  profileKey,
  file,
  defaultWorkspace,
  summary,
  onOpenReview,
  onClose,
}: {
  profileKey: string;
  file: SourceFile;
  defaultWorkspace: string;
  /** What the check says the load does, in a sentence. */
  summary: string;
  onOpenReview: (target: { workspaceKey: string; changeSetId: string }) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(() => changeSetName(file.name));
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [stage, setStage] = useState<Stage>("ready");
  const [error, setError] = useState("");
  const { job, setJob } = useFollowedJob(undefined, {
    done: isFinal,
    onFinal: (next) => setStage(next.state === "completed" ? "done" : "stopped"),
  });
  const [changeSetId, setChangeSetId] = useState<string>();

  async function load() {
    setError("");
    try {
      setStage("opening");
      setJob(
        await loadIntoChangeSet({
          workspace,
          name,
          profileKey,
          sourceFileId: file.id,
          onOpened: (changeSet) => {
            setChangeSetId(changeSet.id);
            setStage("loading");
          },
        }),
      );
    } catch (cause) {
      setStage("stopped");
      setError(errorMessage(cause));
    }
  }

  const working = stage === "opening" || stage === "loading";
  return (
    <Modal
      title={`Load ${file.name} into a change set`}
      eyebrow="Workspaces and models"
      description={summary}
      busy={working}
      onClose={onClose}
    >
      <form
        className="dialog-body load-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (stage === "ready" && workspace && name.trim()) void load();
        }}
      >
        <ol className="load-steps">
          <LoadStep number={1} state={stepState(ORDER, stage, 0)} fields>
            <strong>Open a change set</strong>
            <ChangeSetFields
              name={name}
              onName={setName}
              workspace={workspace}
              onWorkspace={setWorkspace}
              onError={setError}
              disabled={stage !== "ready"}
            />
          </LoadStep>
          <LoadStep number={2} state={stepState(ORDER, stage, 1)}>
            <strong>Load the rows</strong>
            <p className="muted">The stored file through the profile; records found are updated.</p>
            <LoadProgress job={job} stage={stage} />
          </LoadStep>
        </ol>
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
              onClick={() => onOpenReview({ workspaceKey: workspace, changeSetId })}
            >
              Open the change set review
            </button>
          ) : (
            <button type="submit" className="primary" disabled={stage !== "ready" || !workspace || !name.trim()}>
              {stage === "opening" ? "Opening the change set…" : stage === "loading" ? "Loading…" : "Load"}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
