/**
 * The move editor's status (0.11 X4, asked by the user on 2026-10-19): one line under the figures
 * saying what is happening and what comes next, so nobody has to hover Start the move… to learn why
 * it waits. A dry run checking (what it checks, and that Start waits for it), a dry run ready (what
 * would load, what does not move), one with nothing to move, the copy or move loading (with its
 * progress), done (what was copied or moved, where, and that publishing makes it live, with the
 * change sets to review), and a failed load.
 */

import { count, counted, plural } from "@/lib/count";
import type { Job, MoveSummary } from "@/types";
import { Notice } from "@/ui/Notice";
import { figuresOf, modeWords, movesAnything } from "@/model/moveRun";

/** How far a job is, when it says: "1,200 of 2,000 items". */
function progressText(job: Job, verb: string): string {
  const { total, processed } = job.progress;
  return total ? ` ${count(processed)} of ${count(total)} items ${verb}.` : "";
}

export function MoveStatus({
  job,
  checking,
  mode,
  what,
  sourceLabel,
  targetLabel,
  mappingVersion,
  changeSetName,
  onOpenTarget,
  onOpenSource,
  onReport,
}: {
  job?: Job;
  checking: boolean;
  mode: "copy" | "move";
  /** What moves, in words: "every mapped type (19)", "the whole workspace". */
  what: string;
  sourceLabel: string;
  targetLabel: string;
  mappingVersion: number;
  /** The name given to the change set when the move was started. */
  changeSetName?: string;
  onOpenTarget: (changeSetId: string) => void;
  onOpenSource: (changeSetId: string) => void;
  onReport: () => void;
}) {
  const summary: MoveSummary | undefined = job?.move ?? undefined;
  const moving = mode === "move";
  const w = modeWords(mode);
  const named = changeSetName ? `the change set “${changeSetName}”` : "a new change set";

  if (checking && job)
    return (
      <Notice tone="info" title={`Dry run in progress: ${what} of ${sourceLabel}, as ${targetLabel} would take it`}>
        Every record and relationship is checked against {targetLabel}&apos;s rules under mapping version{" "}
        {mappingVersion}; nothing changes in either workspace.{progressText(job, "checked")} Start the {w.verb}… is
        available once the dry run has finished, and every change to the mapping or to the selection runs it again.
      </Notice>
    );

  if (job?.confirmedAt && (job.state === "queued" || job.state === "running")) {
    const loading = summary ? figuresOf(summary) : undefined;
    return (
      <Notice
        tone="info"
        title={`${w.ing} ${loading ? counted(loading.create + loading.update, "record") : "the records"} into ${named} of workspace ${targetLabel}…`}
      >
        The records go into a change set for review; nothing is published, and the live data of both workspaces stays as
        it is.{moving ? ` Then a change set of workspace ${sourceLabel} deleting them is opened.` : ""}
        {progressText(job, "loaded")} You can leave this page; the {w.verb} carries on.
      </Notice>
    );
  }

  if (job?.confirmedAt && job.state === "completed" && summary) {
    const done = figuresOf(summary);
    const moved = counted(done.create + done.update, "record");
    return (
      <Notice
        tone="success"
        title={
          moving
            ? `Move complete: ${moved} moved into ${named} of workspace ${targetLabel}, their deletions into a change set of workspace ${sourceLabel}`
            : `Copy complete: ${moved} copied into ${named} of workspace ${targetLabel}`
        }
        focusOnMount
        actions={
          <>
            {summary.targetChangeSetId && (
              <button type="button" className="secondary" onClick={() => onOpenTarget(summary.targetChangeSetId!)}>
                Review the change set
              </button>
            )}
            {summary.sourceChangeSetId && (
              <button type="button" className="secondary" onClick={() => onOpenSource(summary.sourceChangeSetId!)}>
                Review the deletions
              </button>
            )}
          </>
        }
      >
        Nothing is live yet: review the change set and publish it in workspace {targetLabel} to make the records live
        there.
        {summary.sourceChangeSetId
          ? ` The deletions in workspace ${sourceLabel} (${count(summary.source?.deleted ?? 0)} deleted, ${count(summary.source?.kept ?? 0)} kept with their reason) can be published only after the copy.`
          : moving
            ? ` Nothing was deleted in ${sourceLabel}: every record copied stays there, each with its reason.`
            : ""}
      </Notice>
    );
  }

  if (job?.confirmedAt && job.state === "failed")
    return (
      <Notice tone="error" title={`The ${w.verb} did not complete`}>
        {job.error?.message ?? "It stopped."} Nothing was published, and the live data of both workspaces is as it was.
      </Notice>
    );

  if (job?.state === "awaiting_confirmation" && summary) {
    const ready = figuresOf(summary);
    if (!movesAnything(summary))
      return (
        <Notice tone="warning" title={`Nothing to ${w.verb}`}>
          No record of {what} would be created or updated in workspace {targetLabel}. Map more of the source, or change
          the selection; the dry run runs again after each change.
        </Notice>
      );
    const cannot = ready.cannot + ready.dropped;
    return (
      <Notice
        tone="info"
        title={`Dry run ready: ${counted(ready.create + ready.update, "record")} to ${w.verb} into workspace ${targetLabel}`}
        actions={
          cannot ? (
            <button type="button" className="secondary" onClick={onReport}>
              {w.whatCannot}
            </button>
          ) : undefined
        }
      >
        {cannot
          ? `${count(cannot)} ${plural(cannot, "item")} cannot be ${w.past}, each with its reason. `
          : `Every selected record and relationship can be ${w.past}. `}
        {w.Verb} with Start the {w.verb}…: the records go into a new change set of workspace {targetLabel} for review
        {moving
          ? `, and a change set of workspace ${sourceLabel} deleting them, which publishes only after the copy`
          : ""}
        .
      </Notice>
    );
  }
  return null;
}
