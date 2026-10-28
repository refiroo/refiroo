/**
 * The mark of a change the AI assistant proposed and nobody has changed since (0.16 AP2), with its
 * reason: on a mapping grid's target (a short pill, the reason folded under "why?" on a phone) and
 * on a record's history entry (the full sentence). One component for both (U-D14); the editor's
 * Proposed because uses `aiOriginSentence` for the same words.
 */

import { useMediaQuery, PHONE_WIDTH } from "@/lib/hooks/useMediaQuery";
import type { AiOrigin } from "@/types";
import { StatusPill } from "@/ui/StatusPill";

const percent = (origin: Pick<AiOrigin, "confidence">) => `${Math.round(origin.confidence * 100)}%`;

/** "Proposed by the AI assistant (model), 86% confident". */
export function aiOriginLead(origin: Pick<AiOrigin, "model" | "confidence">): string {
  return `Proposed by the AI assistant${origin.model ? ` (${origin.model})` : ""}, ${percent(origin)} confident`;
}

/** The lead and the reason as one sentence, as Proposed because says it. */
export function aiOriginSentence(origin: Pick<AiOrigin, "model" | "confidence" | "reason">): string {
  return `${aiOriginLead(origin)}. ${origin.reason}`;
}

export function AiOriginMark({
  origin,
  variant,
  askedBy,
}: {
  origin: AiOrigin;
  /** `target` on a grid's target, `history` on a history entry. */
  variant: "target" | "history";
  /** Who asked for it, when known (history). */
  askedBy?: string;
}) {
  const phone = useMediaQuery(PHONE_WIDTH);
  const reason = (
    <>
      {origin.reason}
      {askedBy && ` Asked for by ${askedBy}.`}
    </>
  );
  if (variant === "history")
    return (
      <span className="ai-origin ai-origin-history">
        <StatusPill tone="proposed" className="mark-pill">
          {aiOriginLead(origin)}
        </StatusPill>
        <span className="ai-origin-reason">{reason}</span>
      </span>
    );
  return (
    <span className="ai-origin">
      <StatusPill tone="proposed" className="mark-pill">
        {`Proposed by the AI · ${percent(origin)}`}
      </StatusPill>
      {phone ? (
        <details className="ai-origin-fold">
          <summary>Why?</summary>
          <span className="ai-origin-reason">{reason}</span>
        </details>
      ) : (
        <span className="ai-origin-reason">{reason}</span>
      )}
    </span>
  );
}
