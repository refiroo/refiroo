import type { ReactNode } from "react";

export type StatusTone = "live" | "changeSet" | "publication" | "draft" | "success" | "warning" | "error" | "neutral";

const TONE_CLASS: Record<StatusTone, string> = {
  live: "tone-live",
  changeSet: "tone-change-set",
  publication: "tone-publication",
  draft: "tone-draft",
  success: "tone-success",
  warning: "tone-warning",
  error: "tone-error",
  neutral: "tone-neutral",
};

/**
 * A state or a data context as a pill: a marker and text in the tone's colours (ADR-039). The text
 * always names the state, so the colour is never the only signal. Values are not states: a plain
 * value is written as text, not as a pill.
 */
export function StatusPill({
  tone,
  children,
  marker = true,
  className,
}: {
  tone: StatusTone;
  children: ReactNode;
  /** The dot before the text; off for compact uses such as a version. */
  marker?: boolean;
  className?: string;
}) {
  return (
    <span className={["status-pill", TONE_CLASS[tone], className].filter(Boolean).join(" ")}>
      {marker && <span className="status-pill-marker" aria-hidden="true" />}
      {children}
    </span>
  );
}
