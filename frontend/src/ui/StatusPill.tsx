import type { ReactNode } from "react";

export type StatusTone =
  "live" | "changeSet" | "publication" | "draft" | "proposed" | "success" | "warning" | "error" | "neutral" | "plain";

/** `compact` is a 22 px line of 12 px text (a count or a role on a card); `small` a 12 px tag in a toolbar or note. */
export type StatusSize = "default" | "compact" | "small";

const TONE_CLASS: Record<StatusTone, string> = {
  live: "tone-live",
  changeSet: "tone-change-set",
  publication: "tone-publication",
  draft: "tone-draft",
  proposed: "tone-proposed",
  success: "tone-success",
  warning: "tone-warning",
  error: "tone-error",
  neutral: "tone-neutral",
  plain: "tone-plain",
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
  size = "default",
  className,
}: {
  tone: StatusTone;
  children: ReactNode;
  /** The dot before the text; off for compact uses such as a version. */
  marker?: boolean;
  size?: StatusSize;
  className?: string;
}) {
  return (
    <span
      className={["status-pill", TONE_CLASS[tone], size !== "default" && `status-pill-${size}`, className]
        .filter(Boolean)
        .join(" ")}
    >
      {marker && <span className="status-pill-marker" aria-hidden="true" />}
      {children}
    </span>
  );
}
