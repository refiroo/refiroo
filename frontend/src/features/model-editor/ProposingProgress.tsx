/**
 * The editor while the engine proposes (the user, 2026-10-28: "nothing told me I should wait for the
 * AI"). A Notice (A6-1's reference) at the top of the editor with an indeterminate native `progress`
 * (the job page's) names the phase in plain words, says editing is paused until the proposals are
 * applied (so nothing changed meanwhile can make them stale) and offers Stop. After the run,
 * `assistantOutcomeText` says what the AI assistant did.
 */

import type { Inference } from "@/types";
import { Notice } from "@/ui/Notice";
import { useSystem } from "@/features/settings/useSystem";

export type ProposingPhase = "profiling" | "reading" | "assistant" | "applying";

/** The phase in words; `model` names the assistant's model when the instance knows it. */
export function phaseText(phase: ProposingPhase, model?: string | null): string {
  switch (phase) {
    case "profiling":
      return "Reading the workbook…";
    case "reading":
      return "Finding the model in every sheet…";
    case "assistant":
      return `Asking ${model ? `the AI assistant (${model})` : "the AI assistant"} for clearer names. A model run on your own machine can take a few minutes.`;
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
  // Read only while asking the assistant: the model is named in the sentence.
  const { system } = useSystem();
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
      <p className="proposing-phase">{phaseText(phase, system?.ai?.model)}</p>
      <progress aria-label="Proposing" className="proposing-progress" />
      <p className="muted">Editing is paused until the proposals are applied, so nothing you change is lost.</p>
    </Notice>
  );
}

/** What the AI assistant did, once the inference ended; `undefined` when it was not asked. */
export function assistantOutcomeText(
  outcome: Inference["assistantOutcome"],
): { tone: "success" | "warning"; text: string } | undefined {
  if (!outcome) return undefined;
  const who = `The AI assistant${outcome.model ? ` (${outcome.model})` : ""}`;
  if (outcome.failure) return { tone: "warning", text: `${who} could not help: ${outcome.failure}` };
  if (outcome.suggested === 0) return { tone: "success", text: `${who} found the names good as they are.` };
  const names = `${outcome.offered} clearer ${outcome.offered === 1 ? "name" : "names"}`;
  const left = outcome.suggested - outcome.offered;
  return {
    tone: "success",
    text: `${who} suggested ${names}${
      left > 0 ? `; ${left} ${left === 1 ? "was" : "were"} left out (below the confidence floor or the same name)` : ""
    }.`,
  };
}
