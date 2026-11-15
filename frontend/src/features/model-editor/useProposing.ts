/**
 * Proposing as a surface of the draft needs it (SR4): the inference of `useInference`, and what
 * follows when it completes, the same for the model editor and the workbook canvas. Nothing open to
 * propose: the surface says so and proposing ends. Otherwise the open proposals are applied as
 * steps, one each (D89), a toast says how many, and proposing ends whatever the outcome; a refusal
 * is said in the surface's words, the draft having changed meanwhile (`INFERENCE_STALE`) in its own.
 *
 * A surface keeps what is its own: its wording, what it does with an applied answer (the editor
 * shows the first type it added and the History tab), and how the work is run (the editor under
 * `guarded`, the canvas around its busy state).
 */

import { useEffect, useRef } from "react";
import { api } from "@/api/client";
import { isApiError } from "@/api/errors";
import { useInference, type DraftInference } from "@/features/model-editor/useInference";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import { counted } from "@/lib/count";
import type { ModelDraftStep } from "@/types/modelAdmin";
import { useToast } from "@/ui/Toast";
import type { Inference } from "@/types";

export interface ProposingSurface {
  /** Sends the apply as one step at the draft's version (the surface's `useDraftEditing`). */
  step: DraftEditing["step"];
  /** Says a refusal in the surface's notice. */
  say: (notice: { tone: "error"; text: string }) => void;
  /** The completed inference has nothing open: the surface says so in its words. */
  nothingNew: (done: Inference) => void;
  /** What the surface says when the draft changed while the workbook was read. */
  staleText: string;
  /** What the surface says for any other refusal. */
  refusal: (cause: unknown) => string;
  /** Runs the apply: `guarded` for the editor, the busy state for the canvas. Runs it directly when absent. */
  around?: (work: () => Promise<void>) => Promise<unknown> | void;
  /** The apply went through (not held back as stale): what the surface shows of the answer. */
  onApplied?: (answer: ModelDraftStep) => void;
}

export function useProposing(draftId: string, version: number | undefined, surface: ProposingSurface): DraftInference {
  const toast = useToast();
  // The surface's closures change every render; the completed inference reads the latest.
  const latest = useRef(surface);
  const settle = useRef<() => void>(() => undefined);
  const inference = useInference(draftId, version, (done) => {
    const now = latest.current;
    if (!done.counts.open) {
      settle.current();
      now.nothingNew(done);
      return;
    }
    const apply = async () => {
      try {
        let answer: ModelDraftStep | undefined;
        const outcome = await now.step(async (at) => {
          answer = await api.applyProposals(draftId, at);
          return answer;
        }, true);
        if (outcome === "applied" && answer) {
          now.onApplied?.(answer);
          toast(`${counted(done.counts.open, "proposal")} applied, one step each.`);
        }
      } catch (cause) {
        now.say({ tone: "error", text: isApiError(cause, "INFERENCE_STALE") ? now.staleText : now.refusal(cause) });
      } finally {
        settle.current();
      }
    };
    if (now.around) void now.around(apply);
    else void apply();
  });
  useEffect(() => {
    latest.current = surface;
    settle.current = inference.settled;
  });
  return inference;
}
