/**
 * Load a workbook with the AI assistant (0.16 AP6a): the file, the workspace it goes into and a few
 * words about it. The assistant reads the whole workbook against the workspace's records and
 * prepares the load; nothing changes until the person confirms it on the task's page. The dialog
 * says what is sent, then opens that page.
 */

import { useState, type FormEvent } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage, isApiError } from "@/api/errors";
import { bytes } from "@/features/settings/limits";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import type { AiSystemInfo, AiTask } from "@/types";
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
}

const ACCEPT = ".xlsx,.csv";

/** What leaves the server, in one line: the provider and model, and what the assistant is given. */
export function sentForWorkbookLoad(offer: Pick<AiSystemInfo, "provider" | "model">): string {
  const to = offer.provider ?? "the AI provider";
  const who = offer.model ? `${to} (${offer.model})` : to;
  return `Sent to ${who}: the sheets' names, headers, counts and values, and the workspace's matching records, as the assistant asks for them.`;
}

/** What leaves the server for an instruction without a workbook. */
export function sentForInstruction(offer: Pick<AiSystemInfo, "provider" | "model">): string {
  const to = offer.provider ?? "the AI provider";
  const who = offer.model ? `${to} (${offer.model})` : to;
  return `Sent to ${who}: your words, the model's names, and the workspace's matching records, as the assistant asks for them.`;
}

export function LoadWorkbookDialog({
  start,
  offer,
  onClose,
  onStarted,
  onImportManually,
}: {
  start: LoadWorkbookStart;
  offer: AiSystemInfo;
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = words.trim();
    if ((!file && !trimmed) || !workspaceKey || pending) return;
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

  return (
    <Modal title="Load a workbook" size="wide" busy={pending} onClose={onClose}>
      <form className="dialog-form" onSubmit={(event) => void submit(event)}>
        <p>
          The AI assistant reads the whole workbook against the workspace&apos;s model and records, tells you what each
          sheet is, and prepares the load. Nothing changes until you confirm.
        </p>
        <p className="admin-hint">
          Without a workbook, your words are the whole instruction: &ldquo;Ask the assistant&rdquo; designs from them at
          once.
        </p>
        <FormField label="Workbook" help={file ? `${file.name} · ${bytes(file.size)}` : "XLSX or CSV."}>
          {(control) => (
            <FileField control={control} accept={ACCEPT} disabled={pending} onFile={(chosen) => setFile(chosen)} />
          )}
        </FormField>
        <WorkspaceField
          label="Into"
          holding="ai-proposals"
          value={workspaceKey}
          disabled={pending}
          onChange={setWorkspaceKey}
          onError={setError}
        />
        <FormField
          label="Tell the assistant about this file (optional)"
          help={file ? undefined : "Required without a workbook."}
          error={wordsError || undefined}
        >
          {(control) => (
            <textarea
              {...control}
              rows={3}
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
        <p className="admin-hint">{file || !words.trim() ? sentForWorkbookLoad(offer) : sentForInstruction(offer)}</p>
        {error && (
          <Notice tone="error" title="The workbook was not sent" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          {onImportManually && (
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
          <button className="primary" disabled={pending || (!file && !words.trim()) || !workspaceKey}>
            {pending ? "Sending…" : file ? "Read the workbook" : "Ask the assistant"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
