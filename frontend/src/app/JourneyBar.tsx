/**
 * The bar of a user journey (an import with the assistant, and any later process of steps over
 * several pages), right below the top bar and across the full width. It shows the steps with where
 * the person is, one sentence of what to do now, the button that does it, Stop while a job runs and
 * the way back to the journey's home page from any other page of it. It is generic: a journey
 * supplies the steps, the sentence and the actions. On a phone the steps collapse to "Step 3 of 6:
 * Check" (CSS), with the sentence and the buttons below. The bar's height is published in
 * `--journey-height`, which the editor's height and the sticky data band leave room for.
 */

import { useLayoutEffect, useState } from "react";
import { Icon } from "@/ui/Icon";

export type JourneyStepStatus = "done" | "current" | "todo" | "failed";

export interface JourneyBarStep {
  key: string;
  label: string;
  status: JourneyStepStatus;
}

export interface JourneyBarButton {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

const STATUS_WORDS: Record<JourneyStepStatus, string> = {
  done: "done",
  current: "now",
  todo: "to do",
  failed: "failed",
};

export function JourneyBar({
  label,
  steps,
  sentence,
  primary,
  back,
  stop,
}: {
  /** The navigation landmark's name, such as "Import with the assistant". */
  label: string;
  steps: JourneyBarStep[];
  /** One line of what to do now. */
  sentence: string;
  primary?: JourneyBarButton;
  /** Shown on a page that is not the journey's home page. */
  back?: JourneyBarButton;
  stop?: JourneyBarButton;
}) {
  const [bar, setBar] = useState<HTMLElement | null>(null);
  useLayoutEffect(() => (bar ? publishJourneyHeight(bar) : undefined), [bar]);
  const at = steps.findIndex((step) => step.status === "current" || step.status === "failed");
  const position = at >= 0 ? at : Math.max(0, steps.map((step) => step.status).lastIndexOf("done"));
  const shown = steps[position];
  return (
    <nav ref={setBar} className="journey-bar" aria-label={label}>
      <ol className="journey-steps">
        {steps.map((step) => (
          <li
            key={step.key}
            className={`journey-step journey-${step.status}`}
            aria-current={step.status === "current" || step.status === "failed" ? "step" : undefined}
          >
            <span className="journey-marker" aria-hidden="true">
              {step.status === "done" ? (
                <Icon name="check" size={12} />
              ) : step.status === "failed" ? (
                <Icon name="state-conflict" size={12} />
              ) : (
                <span className="journey-dot" />
              )}
            </span>
            {step.label}
            <span className="visually-hidden"> ({STATUS_WORDS[step.status]})</span>
          </li>
        ))}
      </ol>
      {shown && (
        <p className="journey-summary">
          Step {position + 1} of {steps.length}: {shown.label}
        </p>
      )}
      <div className="journey-now">
        <p className="journey-sentence" role="status">
          {sentence}
        </p>
        <div className="journey-actions wrap-row">
          {stop && (
            <button type="button" className="secondary" disabled={stop.disabled} onClick={stop.onClick}>
              {stop.label}
            </button>
          )}
          {back && (
            <button type="button" className="secondary" disabled={back.disabled} onClick={back.onClick}>
              {back.label}
            </button>
          )}
          {primary && (
            <button type="button" className="primary" disabled={primary.disabled} onClick={primary.onClick}>
              {primary.label}
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}

function publishJourneyHeight(bar: HTMLElement) {
  const root = document.documentElement;
  const publish = () =>
    root.style.setProperty("--journey-height", `${Math.round(bar.getBoundingClientRect().height)}px`);
  publish();
  const observer = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(publish);
  observer?.observe(bar);
  return () => {
    observer?.disconnect();
    root.style.removeProperty("--journey-height");
  };
}
