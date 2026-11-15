/**
 * What the AI accounts share (0.16 AO1, AO2): a request made only when the person asks, and the account the
 * engine's facts and the provider's statements make. The engine wrote the facts; the provider only words them,
 * and each statement leads, by a number, to the facts it rests on. When the provider fails the facts stand alone.
 * A surface brings its own question, its own line saying what is sent and what a fact adds to its line
 * (`renderFact`); this is the rest.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";

/** The facts listed before "Show the other …". */
const FACTS_SHOWN = 10;

export interface AccountFact {
  id: string;
  kind: string;
  text: string;
}

/** The part of an account the shared view reads. */
export interface AccountContent<F extends AccountFact = AccountFact> {
  facts: F[];
  /** Each cites the facts it rests on: a fact's id, or `more-<kind>` for the facts of a kind the provider was not sent. */
  statements: { text: string; factIds: string[] }[];
  /** Statements dropped because they cited no fact that exists. */
  removedStatements: number;
  failure: string | null;
}

export type AccountState<S> =
  { state: "idle" } | { state: "asking" } | { state: "done"; summary: S } | { state: "error"; message: string };

/**
 * The request: `explain` asks (aborting one still going), `reset` forgets the account. A request still going
 * is aborted when the surface goes.
 */
export function useAccountRequest<S>(ask: (signal: AbortSignal) => Promise<S>) {
  const [current, setCurrent] = useState<AccountState<S>>({ state: "idle" });
  const controller = useRef<AbortController>(undefined);
  useEffect(() => () => controller.current?.abort(), []);

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

  function reset() {
    controller.current?.abort();
    setCurrent({ state: "idle" });
  }

  return { current, explain, reset };
}

/** The states after the question: waiting, refused, and the account. `idle` is the surface's own. */
export function AiAccount<F extends AccountFact, S extends AccountContent<F>>({
  current,
  idle,
  provider,
  prefix,
  onExplain,
  askingLabel,
  errorTitle,
  renderFact,
  factsNote,
  emptyFacts,
  factsHeadingLevel = 4,
}: {
  current: AccountState<S>;
  idle: ReactNode;
  provider: string;
  /** Prefixes the fact lines' ids, so a surface with two accounts keeps them apart. */
  prefix: string;
  onExplain: () => void;
  askingLabel: string;
  errorTitle: string;
  /** What a fact's line adds after its text: where it leads. */
  renderFact?: (fact: F) => ReactNode;
  /** Follows "The facts (n, all of them)" in the facts' heading. */
  factsNote?: string;
  /** Replaces the account when the facts are none; the surface says so itself. */
  emptyFacts?: ReactNode;
  /** The facts' heading level: one below the surface's own heading. */
  factsHeadingLevel?: 3 | 4;
}) {
  if (current.state === "idle") return <>{idle}</>;
  if (current.state === "asking") return <Skeleton lines={3} label={askingLabel} />;
  if (current.state === "error")
    return (
      <Notice
        tone="error"
        title={errorTitle}
        actions={
          <button type="button" className="secondary" onClick={onExplain}>
            Try again
          </button>
        }
      >
        {current.message}
      </Notice>
    );
  if (emptyFacts && current.summary.facts.length === 0 && !current.summary.failure) return <>{emptyFacts}</>;
  return (
    <Account
      summary={current.summary}
      provider={provider}
      prefix={prefix}
      onTryAgain={onExplain}
      renderFact={renderFact}
      factsNote={factsNote}
      factsHeadingLevel={factsHeadingLevel}
    />
  );
}

function Account<F extends AccountFact>({
  summary,
  provider,
  prefix,
  onTryAgain,
  renderFact,
  factsNote,
  factsHeadingLevel,
}: {
  summary: AccountContent<F>;
  provider: string;
  prefix: string;
  onTryAgain: () => void;
  renderFact?: (fact: F) => ReactNode;
  factsNote?: string;
  factsHeadingLevel: 3 | 4;
}) {
  const FactsHeading = `h${factsHeadingLevel}` as const;
  const [all, setAll] = useState(false);
  const { facts, statements, removedStatements: removed, failure } = summary;
  const number = new Map(facts.map((fact, index) => [fact.id, index + 1]));
  const shown = all ? facts : facts.slice(0, FACTS_SHOWN);
  const onShowAll = () => setAll(true);

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
            {removed > 0 && `${counted(removed, "statement")} removed: no source. `}
            Written by AI from the facts below, by {provider}. It can be wrong: each number leads to the fact it rests
            on.
          </p>
        </>
      )}
      {facts.length > 0 && (
        <>
          <FactsHeading className="impact-facts-heading">
            The facts ({facts.length}, all of them){factsNote ? `, ${factsNote}` : ""}
          </FactsHeading>
          <ol className="impact-facts">
            {shown.map((fact) => (
              <li key={fact.id} id={`${prefix}-${fact.id}`} tabIndex={-1} data-kind={fact.kind}>
                {fact.text}
                {renderFact && <> {renderFact(fact)}</>}
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
