/**
 * Load a workbook with the AI assistant (0.16 AP6a): the file, the workspace it goes into and a few
 * words about it. The assistant reads the whole workbook against the workspace's records and
 * prepares the load; nothing changes until the person confirms it on the task's page. The dialog
 * says what is sent, then opens that page.
 */

import { useState, type FormEvent } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage, isApiError } from "@/api/errors";
import { bytes } from "@/ui/limits";
import { WorkspaceField } from "@/ui/WorkspaceField";
import type { AiTask } from "@/types";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

/** What the dialog starts with: the workspace of the page it was opened from, and optionally a file. */
export interface LoadWorkbookStart {
  workspaceKey?: string;
  file?: File;
  /** The words to start with, as when a task is started again. */
  words?: string;
  /**
   * "Change this model…" (0.16 AP12): the workspace is fixed, the words come first and are required, the
   * workbook is optional. `workspaceLabel` names the workspace in the dialog.
   */
  changeModel?: boolean;
  workspaceLabel?: string;
}

const ACCEPT = ".xlsx,.csv";

/** What leaves the server, in one line: the session is given the file itself (AP8). */
export const SENT_WITH_WORKBOOK =
  "Sent to Claude Code: the whole workbook, your words and the workspace's model. It reads the workspace's records as it needs them.";

/** What leaves the server for an instruction without a workbook. */
export const SENT_WITH_WORDS =
  "Sent to Claude Code: your words and the workspace's model. It reads the workspace's records as it needs them.";

export function LoadWorkbookDialog({
  start,
  onClose,
  onStarted,
  onImportManually,
}: {
  start: LoadWorkbookStart;
  onClose: () => void;
  onStarted: (task: AiTask) => void;
  /** Closes this dialog and opens the ordinary import with the file chosen so far, whatever its kind. */
  onImportManually?: (file: File | undefined) => void;
}) {
  const [file, setFile] = useState<File | undefined>(start.file);
  const [workspaceKey, setWorkspaceKey] = useState(start.workspaceKey ?? "");
  const [words, setWords] = useState(start.words ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [wordsError, setWordsError] = useState("");
  const changing = !!start.changeModel;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = words.trim();
    if ((changing ? !trimmed : !file && !trimmed) || !workspaceKey || pending) return;
    setPending(true);
    setError("");
    setWordsError("");
    try {
      onStarted(await ai.createTask(file, { workspaceKey, ...(trimmed ? { words: trimmed } : {}) }));
    } catch (cause) {
      if (isApiError(cause, "AI_TASK_NEEDS_WORDS")) setWordsError(errorMessage(cause));
      else setError(errorMessage(cause));
      setPending(false);
    }
  }

  const workbookField = (
    <FormField
      label={changing ? "A workbook (optional)" : "Workbook"}
      help={file ? `${file.name} · ${bytes(file.size)}` : "XLSX or CSV."}
    >
      {(control) => (
        <FileField control={control} accept={ACCEPT} disabled={pending} onFile={(chosen) => setFile(chosen)} />
      )}
    </FormField>
  );
  const wordsField = (
    <FormField
      label={changing ? "What should change?" : "Tell the assistant about this file (optional)"}
      help={file || changing ? undefined : "Required without a workbook."}
      error={wordsError || undefined}
    >
      {(control) => (
        <textarea
          {...control}
          rows={changing ? 4 : 3}
          maxLength={4000}
          value={words}
          disabled={pending}
          onChange={(event) => {
            setWords(event.target.value);
            setWordsError("");
          }}
        />
      )}
    </FormField>
  );
  const ready = changing ? !!words.trim() : !!file || !!words.trim();
  return (
    <Modal title={changing ? "Change this model" : "Load a workbook"} size="wide" busy={pending} onClose={onClose}>
      <form className="dialog-form" onSubmit={(event) => void submit(event)}>
        {changing ? (
          <p>
            Say what should change in the model of <strong>{start.workspaceLabel ?? start.workspaceKey}</strong>. The
            assistant proposes it and says what happens to the records. Nothing changes until you confirm.
          </p>
        ) : (
          <>
            <p>
              The AI assistant reads the whole workbook against the workspace&apos;s model and records, tells you what
              each sheet is, and prepares the load. Nothing changes until you confirm.
            </p>
            <p className="admin-hint">
              Without a workbook, your words are the whole instruction: &ldquo;Ask the assistant&rdquo; designs from
              them at once.
            </p>
          </>
        )}
        {changing ? (
          <>
            {wordsField}
            {workbookField}
          </>
        ) : (
          <>
            {workbookField}
            <WorkspaceField
              label="Into"
              holding="ai-proposals"
              value={workspaceKey}
              disabled={pending}
              onChange={setWorkspaceKey}
              onError={setError}
            />
            {wordsField}
          </>
        )}
        <p className="admin-hint">{file || (!changing && !words.trim()) ? SENT_WITH_WORKBOOK : SENT_WITH_WORDS}</p>
        {error && (
          <Notice tone="error" title="The workbook was not sent" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          {onImportManually && !changing && (
            <>
              <button type="button" className="secondary" disabled={pending} onClick={() => onImportManually(file)}>
                Import without the assistant…
              </button>
              <span className="dialog-actions-spacer" />
            </>
          )}
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !ready || !workspaceKey}>
            {pending ? "Sending…" : file && !changing ? "Read the workbook" : "Ask the assistant"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
