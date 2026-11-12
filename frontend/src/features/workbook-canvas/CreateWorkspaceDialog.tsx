/**
 * Create workspace… on the canvas (0.17 PL3b): the draft the canvas shaped becomes a new workspace,
 * through the one route New from a workbook ends with (PL4): the model is installed, the workspace is
 * created and the draft's workbook is loaded into it, every row. The sheet asks only for the name.
 */

import { useState, type FormEvent } from "react";
import { errorMessage } from "@/api/errors";
import { createWorkspaceFromDraft, ProblemList, problemsOf } from "@/features/workspaces/NewFromWorkbook";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export function CreateWorkspaceDialog({
  draftId,
  latestVersion,
  fileName,
  initialName,
  figures,
  onCreated,
  onClose,
}: {
  draftId: string;
  latestVersion: () => number;
  fileName: string;
  initialName: string;
  /** What the last check said, so the sheet states what will load before anything is created. */
  figures?: { loads: number; refused: number };
  onCreated: (workspaceKey: string) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(initialName);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [problems, setProblems] = useState<string[]>([]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || working) return;
    setWorking(true);
    setError("");
    setProblems([]);
    try {
      onCreated(await createWorkspaceFromDraft({ id: draftId, version: latestVersion() }, name.trim(), fileName));
    } catch (cause) {
      setError(errorMessage(cause));
      setProblems(problemsOf(cause));
      setWorking(false);
    }
  }

  return (
    <Modal
      title="Create workspace"
      eyebrow="New workspace"
      description={`The model on the canvas and ${fileName}, loaded into a workspace of its own.`}
      busy={working}
      size="compact"
      onClose={onClose}
    >
      <form className="dialog-body" onSubmit={(event) => void create(event)}>
        <label>
          Name
          <input
            required
            autoFocus
            maxLength={300}
            value={name}
            disabled={working}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        {figures && (
          <p className="muted">
            {figures.loads.toLocaleString("en-US")} rows load
            {figures.refused > 0 ? `; ${figures.refused.toLocaleString("en-US")} are refused and stay out` : ""}.
          </p>
        )}
        {error && (
          <Notice tone="error" title="The workspace was not created">
            {error}
            <ProblemList problems={problems} />
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={working} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={working || !name.trim()}>
            {working ? "Creating…" : "Create workspace"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
