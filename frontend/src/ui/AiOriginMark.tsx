/**
 * The mark of a change the AI assistant proposed and nobody has changed since (0.16 AP2), with its
 * reason: on a mapping grid's target (a short pill, the reason folded under "why?" on a phone) and
 * on a record's history entry (the full sentence). One component for both (U-D14); the editor's
 * Proposed because uses `aiOriginSentence` for the same words. A session's change has no confidence
 * or reason (0.16 AP9), so it says who asked and who edited instead. A change an outside assistant
 * prepared through MCP (kind "agent", 0.16 AG3) is marked by the same component: "Prepared by an
 * assistant" with the name it gave itself, who asked for it (not when that is the client itself) and
 * who edited it; on a history entry a note says the name is the assistant's own.
 */

import { useMediaQuery, PHONE_WIDTH } from "@/lib/hooks/useMediaQuery";
import type { AiOrigin, ChangeOrigin } from "@/types";
import { StatusPill } from "@/ui/StatusPill";

const percent = (confidence: number) => `${Math.round(confidence * 100)}%`;

/** "Proposed by the AI assistant (model), 86% confident". */
export function aiOriginLead(origin: Pick<AiOrigin, "model" | "confidence">): string {
  const sure = origin.confidence == null ? "" : `, ${percent(origin.confidence)} confident`;
  return `Proposed by the AI assistant${origin.model ? ` (${origin.model})` : ""}${sure}`;
}

/** The lead and the reason as one sentence, as Proposed because says it. */
export function aiOriginSentence(origin: Pick<AiOrigin, "model" | "confidence" | "reason">): string {
  return origin.reason ? `${aiOriginLead(origin)}. ${origin.reason}` : `${aiOriginLead(origin)}.`;
}

export function AiOriginMark({
  origin,
  variant,
  askedBy,
}: {
  origin: ChangeOrigin;
  /** `target` on a grid's target, `history` on a history entry. */
  variant: "target" | "history";
  /** Who asked for it, when known (history). */
  askedBy?: string;
}) {
  const phone = useMediaQuery(PHONE_WIDTH);
  const agent = origin.kind === "agent";
  const asker = origin.proposedByName ?? askedBy;
  // A client acting for itself is named as the assistant already: no "Asked for by" then.
  const asked = agent && asker === origin.application ? undefined : asker;
  const reason = (
    <>
      {!agent && origin.reason}
      {asked && `${!agent && origin.reason ? " " : ""}Asked for by ${asked}.`}
      {origin.editedByName && `${(!agent && origin.reason) || asked ? " " : ""}Edited by ${origin.editedByName}.`}
      {agent &&
        variant === "history" &&
        `${asked || origin.editedByName ? " " : ""}(the name is the one the assistant gave itself)`}
    </>
  );
  const lead = agent ? `Prepared by an assistant: ${origin.application}` : aiOriginLead(origin);
  const shortLead = agent
    ? "Prepared by an assistant"
    : origin.confidence == null
      ? "Proposed by the AI"
      : `Proposed by the AI · ${percent(origin.confidence)}`;
  if (variant === "history")
    return (
      <span className="ai-origin ai-origin-history">
        <StatusPill tone="proposed" className="mark-pill">
          {lead}
        </StatusPill>
        <span className="ai-origin-reason">{reason}</span>
      </span>
    );
  return (
    <span className="ai-origin">
      <StatusPill tone="proposed" className="mark-pill">
        {shortLead}
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
