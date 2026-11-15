/**
 * The editor while the engine proposes (the user, 2026-10-28: "nothing told me I should wait for the
 * AI"). A Notice (A6-1's reference) at the top of the editor with an indeterminate native `progress`
 * (the job page's) names the phase in plain words, says editing is paused until the proposals are
 * applied (so nothing changed meanwhile can make them stale) and offers Stop.
 */

import { JobProgress } from "@/ui/JobProgress";
import { Notice } from "@/ui/Notice";

export type ProposingPhase = "profiling" | "reading" | "applying";

/** The phase in words. */
export function phaseText(phase: ProposingPhase): string {
  switch (phase) {
    case "profiling":
      return "Reading the workbook…";
    case "reading":
      return "Finding the model in every sheet…";
    case "applying":
      return "Applying the proposals, one step each…";
  }
}

export function ProposingProgress({
  phase,
  onStop,
  stopping = false,
}: {
  phase: ProposingPhase;
  onStop: () => void;
  stopping?: boolean;
}) {
  return (
    <Notice
      tone="info"
      title="Proposing from the workbook"
      actions={
        phase !== "applying" && (
          <button type="button" className="secondary" disabled={stopping} onClick={onStop}>
            Stop
          </button>
        )
      }
    >
      <p className="proposing-phase">{phaseText(phase)}</p>
      <JobProgress label="Proposing" className="proposing-progress" />
      <p className="muted">Editing is paused until the proposals are applied, so nothing you change is lost.</p>
    </Notice>
  );
}
