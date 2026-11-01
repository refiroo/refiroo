/**
 * The account of what a model change does, beside the check of a workspace's data (0.16 AO1, the approved
 * mock-up). Nothing is sent until the person asks: the line says what goes. The engine wrote the facts; the
 * provider only words them, and each statement leads, by a number, to the facts it rests on. When the
 * provider fails the facts stand alone. The component is used by the activation dialog and by Apply, which
 * pass what to ask and a `key` that changes with each new check, so a new check clears the account.
 */

import { useId, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import { useImpactSummaryOffer } from "@/features/settings/useWorkspaceAiOffer";
import type { ImpactSummary as Summary } from "@/types";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";

/** The facts listed before "Show the other …". */
const FACTS_SHOWN = 10;

type State =
  { state: "idle" } | { state: "asking" } | { state: "done"; summary: Summary } | { state: "error"; message: string };

export function ImpactSummary({
  workspaceKey,
  ask,
}: {
  workspaceKey: string;
  /** Asks for the account; aborted when the dialog closes or another check starts. */
  ask: (signal: AbortSignal) => Promise<Summary>;
}) {
  const offer = useImpactSummaryOffer(workspaceKey);
  const [current, setCurrent] = useState<State>({ state: "idle" });
  const [all, setAll] = useState(false);
  const controller = useRef<AbortController>(undefined);
  const prefix = useId();
  const heading = `${prefix}-heading`;
  if (!offer) return null;
  const provider = offer.provider ?? "the AI provider";

  async function explain() {
    controller.current?.abort();
    const abort = (controller.current = new AbortController());
    setCurrent({ state: "asking" });
    try {
      const summary = await ask(abort.signal);
      if (!abort.signal.aborted) setCurrent({ state: "done", summary });
    } catch (cause) {
      if (!abort.signal.aborted) setCurrent({ state: "error", message: errorMessage(cause) });
    }
  }

  return (
    <section className="impact-summary" aria-labelledby={heading}>
      <h3 id={heading} className="install-heading">
        What this change does
      </h3>
      {current.state === "idle" && (
        <div className="impact-ask">
          <p className="muted">The model's changes and record counts go to {provider}. No record value is sent.</p>
          <button type="button" className="secondary" onClick={() => void explain()}>
            Explain this change
          </button>
        </div>
      )}
      {current.state === "asking" && <Skeleton lines={3} label="Writing the account" />}
      {current.state === "error" && (
        <Notice
          tone="error"
          title="The account could not be asked for"
          actions={
            <button type="button" className="secondary" onClick={() => void explain()}>
              Try again
            </button>
          }
        >
          {current.message}
        </Notice>
      )}
      {current.state === "done" && (
        <Account
          summary={current.summary}
          provider={provider}
          prefix={prefix}
          all={all}
          onShowAll={() => setAll(true)}
          onTryAgain={() => void explain()}
        />
      )}
    </section>
  );
}

function Account({
  summary,
  provider,
  prefix,
  all,
  onShowAll,
  onTryAgain,
}: {
  summary: Summary;
  provider: string;
  prefix: string;
  all: boolean;
  onShowAll: () => void;
  onTryAgain: () => void;
}) {
  const { facts, statements, removedStatements: removed, failure } = summary;
  const number = new Map(facts.map((fact, index) => [fact.id, index + 1]));
  const shown = all ? facts : facts.slice(0, FACTS_SHOWN);

  /** Opens the list when the fact is below the fold, then puts the reader on its line. */
  function show(factId: string) {
    const index = facts.findIndex((fact) => fact.id === factId);
    if (index < 0) return;
    if (index >= FACTS_SHOWN) onShowAll();
    window.setTimeout(() => {
      const line = document.getElementById(`${prefix}-${factId}`);
      line?.focus();
      line?.scrollIntoView?.({ block: "nearest" });
    }, 0);
  }

  /** What a citation of "the rest of a kind" leads to: the first fact of that kind. */
  const target = (id: string) =>
    id.startsWith("more-") ? facts.find((fact) => fact.kind === id.slice(5))?.id : number.has(id) ? id : undefined;

  return (
    <>
      {failure && (
        <Notice
          tone="warning"
          title="The account could not be written"
          actions={
            <button type="button" className="secondary" onClick={onTryAgain}>
              Try again
            </button>
          }
        >
          {failure}. The facts below do not depend on it.
        </Notice>
      )}
      {!failure && statements.length === 0 && (
        <Notice
          tone="info"
          actions={
            <button type="button" className="secondary" onClick={onTryAgain}>
              Try again
            </button>
          }
        >
          {facts.length === 0
            ? "This change has no difference to describe."
            : "No statement it wrote cited a fact, so none is shown. The facts below are the account."}
        </Notice>
      )}
      {statements.length > 0 && (
        <>
          <ul className="impact-statements">
            {statements.map((statement, index) => (
              <li key={index}>
                {statement.text}{" "}
                {statement.factIds.map((id) => {
                  const found = target(id);
                  const label = id.startsWith("more-") ? `the other ${id.slice(5)} facts` : String(number.get(id));
                  return (
                    <button
                      key={id}
                      type="button"
                      className="link-button impact-cite"
                      aria-label={`Fact ${label}`}
                      onClick={() => found && show(found)}
                    >
                      {id.startsWith("more-") ? "+" : label}
                    </button>
                  );
                })}
              </li>
            ))}
          </ul>
          <p className="muted impact-note">
            {removed > 0 && `${removed} ${removed === 1 ? "statement" : "statements"} removed: no source. `}
            Written by AI from the facts below, by {provider}. It can be wrong: each number leads to the fact it rests
            on.
          </p>
        </>
      )}
      {facts.length > 0 && (
        <>
          <h4 className="impact-facts-heading">The facts ({facts.length}, all of them)</h4>
          <ol className="impact-facts">
            {shown.map((fact) => (
              <li key={fact.id} id={`${prefix}-${fact.id}`} tabIndex={-1} data-kind={fact.kind}>
                {fact.text}
              </li>
            ))}
          </ol>
          {!all && facts.length > FACTS_SHOWN && (
            <button type="button" className="secondary" onClick={onShowAll}>
              Show the other {facts.length - FACTS_SHOWN}
            </button>
          )}
        </>
      )}
    </>
  );
}
