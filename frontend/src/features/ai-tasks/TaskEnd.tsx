/**
 * A task that stopped, failed or was discarded (0.16 AP13, boards 1, 6 and the phone): why, from the task's
 * own notes, and the way on on the page itself. A task the assistant stopped or the person stopped takes words
 * (the same session goes on, or starts again when it never ran), goes on as it was, or is discarded; a discarded
 * one says so.
 */

import type { AiTask } from "@/types";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { TaskNotes } from "./TaskNotes";
import { TellAssistant } from "./TellAssistant";

export function TaskEnd({
  task,
  pending,
  onTell,
  onGoOn,
  onDiscard,
  onOpenEditor,
  onBack,
}: {
  task: AiTask;
  pending: boolean;
  /** The person's words go to the assistant; the same session goes on. */
  onTell: (words: string) => void;
  /** Go on as it was, with no words. */
  onGoOn: () => void;
  onDiscard: () => void;
  onOpenEditor?: (draftId: string) => void;
  onBack: () => void;
}) {
  const failed = task.state === "failed";
  const discarded = task.state === "cancelled";
  const title = failed ? "The assistant stopped" : discarded ? "Discarded" : "You stopped the assistant";
  const reasons = task.notes.filter((note) => note.kind !== "note" || note.text.trim());
  return (
    <Section title={title}>
      {reasons.length > 0 ? (
        <TaskNotes notes={reasons} />
      ) : (
        <Notice tone={failed ? "error" : "info"}>
          {failed
            ? "The assistant could not finish."
            : discarded
              ? "This task was discarded. Nothing it began is kept."
              : "You stopped it, and nothing was changed."}
        </Notice>
      )}
      {!discarded && (
        <p className="task-reason">
          Nothing was installed or loaded
          {task.draftId ? ". Your draft and the assistant's work so far are kept." : "."}
        </p>
      )}
      {!discarded && task.canTell && (
        <TellAssistant
          label="Tell the assistant how to go on"
          hint="The same assistant continues from where it stopped, with your words."
          primary
          anchor="journey-tell"
          pending={pending}
          onSend={onTell}
        >
          <button type="button" className="secondary" disabled={pending} onClick={onGoOn}>
            {failed ? "Try again as it was" : "Go on as it was"}
          </button>
          {task.draftId && onOpenEditor && (
            <button type="button" className="secondary" onClick={() => onOpenEditor(task.draftId!)}>
              Open the draft in the editor
            </button>
          )}
        </TellAssistant>
      )}
      <div className="task-actions">
        {!discarded && (
          <button type="button" className="secondary" disabled={pending} onClick={onDiscard}>
            Discard this task
          </button>
        )}
        <button type="button" className="secondary" onClick={onBack}>
          Back to the workspace
        </button>
      </div>
      {!discarded && <p className="admin-hint">Discarding ends the task and removes its draft.</p>}
    </Section>
  );
}
