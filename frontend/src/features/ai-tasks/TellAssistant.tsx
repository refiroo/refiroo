/**
 * The words box of an assistant task (0.16 AP13, AP-D54): one place where the person tells the
 * assistant something, wherever a task can go on: the proposal, the load stage, a task that stopped
 * or failed, a loaded change set not yet published, a reshaping step. The words go to the same
 * session. The label, the line under it and the buttons are the state's; the box is one.
 */

import { useState, type ReactNode } from "react";
import { FormField } from "@/ui/FormField";

export function TellAssistant({
  label,
  hint,
  placeholder,
  sendLabel = "Send to the assistant",
  primary = false,
  rows = 3,
  pending,
  anchor,
  hideSend = false,
  onSend,
  children,
}: {
  label: string;
  /** A line under the label: what the words do. */
  hint?: ReactNode;
  placeholder?: string;
  sendLabel?: string;
  /** The send button is the page's main action (a task that stopped), else a secondary one. */
  primary?: boolean;
  rows?: number;
  pending: boolean;
  /** An id the journey bar scrolls to. */
  anchor?: string;
  /** The assistant cannot be told now: the box is left out and only the buttons stay. */
  hideSend?: boolean;
  onSend: (words: string) => void;
  /** More buttons beside Send. */
  children?: ReactNode;
}) {
  const [words, setWords] = useState("");
  const empty = words.trim() === "";
  if (hideSend)
    return children ? (
      <div className="task-actions" id={anchor}>
        {children}
      </div>
    ) : null;
  return (
    <div className="task-tell" id={anchor} tabIndex={anchor ? -1 : undefined}>
      <FormField label={label} help={hint}>
        {(control) => (
          <textarea
            {...control}
            rows={rows}
            maxLength={2000}
            value={words}
            placeholder={placeholder}
            onChange={(event) => setWords(event.target.value)}
          />
        )}
      </FormField>
      <div className="task-actions">
        <button
          type="button"
          className={primary ? "primary" : "secondary"}
          disabled={empty || pending}
          onClick={() => onSend(words.trim())}
        >
          {sendLabel}
        </button>
        {children}
      </div>
    </div>
  );
}
