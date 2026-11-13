/**
 * What changed in a period, in words (0.16 AO2, the approved mock-up): above a workspace's Activity and on a
 * record's History. The person picks a period and presses Explain this period; nothing is sent before. The engine
 * counted the facts in the database over every live change of the period and the provider only words them; each
 * statement leads, by a number, to the facts it rests on, and a fact leads to the changes it counted, a change set
 * or a job. The account itself is the shared `ui/AiAccount`, as the account of a model change uses.
 */

import { useId, useState } from "react";
import { ai } from "@/api/aiClient";
import { useHistoryAccountOffer } from "@/features/settings/useWorkspaceAiOffer";
import { changeReviewFor, routePath } from "@/routing/routes";
import type { HistoryAccount, HistoryFact, RouteState } from "@/types";
import { AiAccount, useAccountRequest } from "@/ui/AiAccount";
import { RouteLink } from "@/ui/RouteLink";

/** What a fact asks the surface to narrow to: its changes, over the account's period. */
export interface ShownFact {
  fact: HistoryFact;
  since: string;
  until: string;
}

type Preset = "7" | "30" | "dates";

const PRESETS: { value: Preset; label: string }[] = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "dates", label: "Choose dates" },
];

const DAY = 24 * 60 * 60 * 1000;

const shortDay = (iso: string | number) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });

/** The period an account is of, as people read it: the last day is the one before `until`, which is not included. */
export function periodLabel(since: string, until: string) {
  return `${shortDay(since)} to ${shortDay(new Date(until).getTime() - 1)}`;
}

/** A date input's day at the start of the day where the person is. */
const startOf = (day: string) => new Date(`${day}T00:00:00`);

export function WhatChanged({
  workspaceKey,
  record,
  application,
  onShow,
  onNavigate,
  headingLevel = 3,
}: {
  workspaceKey: string;
  /** One record's account instead of the workspace's. */
  record?: { objectTypeKey: string; objectId: string };
  /** An application of the workspace, to open a change set. */
  application?: string;
  /** Narrows the surface to what a fact counted (**Show them**). */
  onShow: (shown: ShownFact) => void;
  onNavigate: (route: RouteState) => void;
  /** The heading's level: under a page's own heading (h1) with no heading between, 2. */
  headingLevel?: 2 | 3;
}) {
  const Heading = `h${headingLevel}` as const;
  const offer = useHistoryAccountOffer(workspaceKey);
  const [preset, setPreset] = useState<Preset>(record ? "30" : "7");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const prefix = useId();
  const heading = `${prefix}-heading`;
  const dates = preset === "dates";
  const invalid = dates && (!from || !to || startOf(from) > startOf(to));

  const request = useAccountRequest<HistoryAccount>((signal) => {
    const now = Date.now();
    const since = dates ? startOf(from) : new Date(now - Number(preset) * DAY);
    const until = dates ? new Date(startOf(to).getTime() + DAY) : new Date(now);
    const body = {
      since: since.toISOString(),
      until: until.toISOString(),
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
    return record
      ? ai.explainRecordHistory(record.objectTypeKey, record.objectId, body, signal)
      : ai.explainWorkspaceHistory(workspaceKey, body, signal);
  });
  if (!offer) return null;
  const { current, explain, reset } = request;
  const provider = offer.provider ?? "the AI provider";
  const where = record ? "record" : "workspace";

  const names = offer.sendLevel === "values";
  const line = names
    ? `Sends ${provider} the counts of what changed, by type, field and source, with the names of records, people and change sets. Nothing is sent until you press the button.`
    : `At the send level "${offer.sendLevel}": sends ${provider} the counts of what changed, by type, field and source. No names of records, people, change sets or files. Nothing is sent until you press the button.`;
  const done = current.state === "done" ? current.summary : undefined;

  const lead = (fact: HistoryFact) => {
    const link = fact.link;
    if (!link) return null;
    if (link.kind === "changes" || link.kind === "history") {
      return (
        <button
          type="button"
          className="link-button"
          onClick={() => done && onShow({ fact, since: done.since, until: done.until })}
        >
          {fact.count === 1 ? "Show it" : "Show them"}
        </button>
      );
    }
    if (link.kind === "job" && link.id) {
      const target: RouteState = { kind: "settings", page: "jobs", jobId: link.id };
      return (
        <RouteLink href={routePath(target)} onNavigate={() => onNavigate(target)}>
          Open the job
        </RouteLink>
      );
    }
    if (link.kind === "changeSet" && link.id && application) {
      const target = changeReviewFor(application, workspaceKey, link.id);
      return (
        <RouteLink href={routePath(target)} onNavigate={() => onNavigate(target)}>
          Open the change set
        </RouteLink>
      );
    }
    return null;
  };

  return (
    <section className="impact-summary what-changed" aria-labelledby={heading}>
      <div className="what-changed-head">
        <Heading id={heading} className="install-heading">
          What changed
        </Heading>
        <div className="what-changed-controls">
          <label htmlFor={`${prefix}-period`}>Period</label>
          <select
            id={`${prefix}-period`}
            value={preset}
            onChange={(event) => {
              setPreset(event.target.value as Preset);
              reset();
            }}
          >
            {PRESETS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          {dates && (
            <>
              <label htmlFor={`${prefix}-from`}>From</label>
              <input
                id={`${prefix}-from`}
                type="date"
                value={from}
                max={to || undefined}
                onChange={(event) => {
                  setFrom(event.target.value);
                  reset();
                }}
              />
              <label htmlFor={`${prefix}-to`}>To, included</label>
              <input
                id={`${prefix}-to`}
                type="date"
                value={to}
                min={from || undefined}
                onChange={(event) => {
                  setTo(event.target.value);
                  reset();
                }}
              />
            </>
          )}
          <button
            type="button"
            className="secondary"
            disabled={invalid || current.state === "asking"}
            onClick={() => void explain()}
          >
            {current.state === "idle" || current.state === "error" ? "Explain this period" : "Explain again"}
          </button>
        </div>
      </div>
      <AiAccount
        current={current}
        provider={provider}
        prefix={prefix}
        onExplain={() => void explain()}
        askingLabel="Writing the account"
        errorTitle="The account could not be asked for"
        renderFact={lead}
        factsHeadingLevel={headingLevel === 2 ? 3 : 4}
        factsNote={done ? `${periodLabel(done.since, done.until)}, live data` : undefined}
        emptyFacts={
          done && (
            <p className="muted">
              Nothing changed in this {where} between {periodLabel(done.since, done.until)}. Nothing was sent to the AI.
            </p>
          )
        }
        idle={
          <>
            <p className="muted">{line}</p>
            {invalid && <p className="muted">Pick a first day that is not after the last.</p>}
          </>
        }
      />
    </section>
  );
}
