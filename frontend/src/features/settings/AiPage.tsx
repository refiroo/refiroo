/**
 * Settings › Administration › AI (0.16 AP1, AP-D38): the assistant (`AI_AGENT_COMMAND`) and the AI
 * provider (`AI_PROVIDER`), each of which people review the proposals of. Both are set in the server's
 * environment and read at start, so nothing here changes them; the page shows what is set, what may
 * be sent, a test request of the provider and every call made.
 */

import { useEffect, useState } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { AiCall, AiStatus } from "@/types";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { failureSentence, PURPOSE, sendLevelText } from "./aiText";

const number = (value: number) => value.toLocaleString("en");

export function AiPage() {
  const [status, setStatus] = useState<AiStatus>();
  const [error, setError] = useState("");
  // Bumped whenever a call may have been made, so the totals and the list are read again.
  const [refresh, setRefresh] = useState(0);

  function load() {
    ai.status().then(
      (loaded) => {
        setStatus(loaded);
        setError("");
      },
      (cause) => setError(errorMessage(cause)),
    );
  }
  useEffect(load, [refresh]);

  return (
    <SettingsLayout
      eyebrow="Administration"
      title="AI"
      description="The assistant and the AI provider the application asks for proposals that people then review, keep, edit or remove. They are set in the server's environment (the AI_ settings) and read when the server starts; nothing here changes them. The key is never shown."
    >
      {error ? (
        <InlineError message={error} onRetry={load} />
      ) : !status ? (
        <Skeleton label="Loading the AI settings" lines={6} />
      ) : !status.configured && !status.assistant ? (
        <Notice tone="info" title="Neither the assistant nor an AI provider is set up">
          Nothing is sent anywhere and no AI action is offered. Set <code>AI_AGENT_COMMAND</code> (the assistant) or{" "}
          <code>AI_PROVIDER</code> (and its key) in the server&apos;s environment and restart it.
        </Notice>
      ) : (
        <>
          <SwitchesSection status={status} />
          <SettingsSection status={status} />
          {status.configured && <FeaturesSection status={status} />}
          {status.configured && <TestSection onCalled={() => setRefresh((n) => n + 1)} />}
          <CallsSection status={status} refresh={refresh} />
        </>
      )}
    </SettingsLayout>
  );
}

/** The two switches (AP-D38): the assistant needs no provider, and the provider needs no assistant. */
function SwitchesSection({ status }: { status: AiStatus }) {
  return (
    <Section title="What is switched on">
      <DescriptionList
        items={[
          {
            term: "Assistant",
            value: (
              <>
                {status.assistant ? "On" : "Not set"} (<code>AI_AGENT_COMMAND</code>)
                <div className="admin-hint">
                  {status.assistant
                    ? "Reads workbooks and words, up to a change set. It sends what the send level below allows and needs no provider."
                    : "Loading a workbook with the assistant is not offered."}
                </div>
              </>
            ),
          },
          {
            term: "Provider",
            value: (
              <>
                {status.configured ? `On: ${status.provider ?? "set"}` : "Not set"} (<code>AI_PROVIDER</code>)
                <div className="admin-hint">
                  {status.configured
                    ? "Asked for mapping targets, search and summaries."
                    : "Mapping targets, search and summaries are not offered."}
                </div>
              </>
            ),
          },
        ]}
      />
    </Section>
  );
}

function SettingsSection({ status }: { status: AiStatus }) {
  return (
    <Section title="Settings">
      <DescriptionList
        items={[
          ...(status.configured
            ? [
                { term: "Model", value: status.model ?? "The provider's own" },
                { term: "Endpoint", value: status.endpoint ?? "The provider's own" },
                { term: "Key", value: status.keySet ? "Set" : "Not set" },
              ]
            : []),
          { term: "What may be sent", value: sendLevelText(status.sendLevel, status.sampleValues) },
          ...(status.configured
            ? [{ term: "Confidence floor", value: `${Math.round(status.minConfidence * 100)}%` }]
            : []),
          {
            term: "Content kept",
            value: status.logContent ? `For ${status.logContentDays} days` : "No",
          },
          ...(status.configured ? [{ term: "Timeout", value: `${status.timeoutSeconds} seconds` }] : []),
        ]}
      />
    </Section>
  );
}

function FeaturesSection({ status }: { status: AiStatus }) {
  return (
    <Section
      title="What the AI provider is asked"
      description="Each feature needs a level of what may be sent. One that needs more than is allowed is not offered."
    >
      <ul className="capability-groups">
        {status.features.map((feature) => (
          <li key={feature.purpose}>
            <div className="capability-group-header">
              <strong>{feature.name}</strong>
              <StatusPill tone={feature.available ? "success" : "neutral"}>
                {feature.available ? "Available" : "Unavailable"}
              </StatusPill>
            </div>
            {!feature.available && (
              <p className="section-description">
                It needs a higher level of what may be sent: {sendLevelText(feature.needs, status.sampleValues)}.
              </p>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function TestSection({ onCalled }: { onCalled: () => void }) {
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string }>();

  async function test() {
    setPending(true);
    setResult(undefined);
    try {
      const call = await ai.test();
      setResult(
        call.outcome === "answered"
          ? { ok: true, text: `Answered in ${number(call.durationMs)} ms by ${call.model ?? call.provider}.` }
          : { ok: false, text: failureSentence(call) },
      );
    } catch (cause) {
      setResult({ ok: false, text: errorMessage(cause) });
    } finally {
      setPending(false);
      onCalled();
    }
  }

  return (
    <Section
      title="Test request"
      description="A small request that sends none of your data. It shows whether the AI provider answers, and it is listed below."
    >
      <div className="settings-filter-bar">
        <button type="button" className="secondary" disabled={pending} onClick={() => void test()}>
          {pending ? "Sending…" : "Send a test request"}
        </button>
      </div>
      {result &&
        (result.ok ? (
          <Notice tone="success" title="The AI provider answered">
            {result.text}
          </Notice>
        ) : (
          <Notice tone="error" title="The test request failed">
            {result.text}
          </Notice>
        ))}
    </Section>
  );
}

function CallsSection({ status, refresh }: { status: AiStatus; refresh: number }) {
  const { totals } = status;
  const feed = useCursorFeed((cursor) => ai.calls({ cursor }), [refresh]);
  return (
    <Section
      title="Calls"
      description="Every request made to the AI provider and every assistant session's turn, newest first."
    >
      <p className="section-description">
        Last {totals.days} days: {number(totals.calls)} {totals.calls === 1 ? "call" : "calls"}, {number(totals.failed)}{" "}
        failed; {number(totals.tokensIn)} tokens in, {number(totals.tokensOut)} out
        {totals.costUsd > 0 && `; $${totals.costUsd.toFixed(2)}`}.
      </p>
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading calls" lines={4} />
      ) : !feed.items.length ? (
        <EmptyState>
          No call has been made yet. A test request, a request for mapping targets or an assistant session appears here.
        </EmptyState>
      ) : (
        <SettingsTable
          label="Calls"
          columns={["When", "What for", "Asked by", "Model", "Outcome", "Tokens in / out", "Cost", "Duration"]}
        >
          {feed.items.map((call) => (
            <CallRow key={call.id} call={call} />
          ))}
        </SettingsTable>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more calls
        </button>
      )}
    </Section>
  );
}

function CallRow({ call }: { call: AiCall }) {
  return (
    <tr>
      <th scope="row">{formatServerDayTime(call.startedAt)}</th>
      <td data-label="What for">{PURPOSE[call.purpose] ?? call.purpose}</td>
      <td data-label="Asked by">{call.requestedBy?.name ?? "—"}</td>
      <td data-label="Model">{call.model ?? "—"}</td>
      <td data-label="Outcome">
        <StatusPill tone={call.outcome === "answered" ? "success" : "error"}>
          {call.outcome === "answered" ? "Answered" : "Failed"}
        </StatusPill>
        {call.outcome === "failed" && <div className="admin-hint">{failureSentence(call)}</div>}
        {call.content && (
          <details className="ai-call-content">
            <summary>Show what was sent and answered</summary>
            <pre className="mono" tabIndex={0} aria-label="What was sent and answered">
              {JSON.stringify(call.content, null, 2)}
            </pre>
          </details>
        )}
      </td>
      <td data-label="Tokens in / out">
        {call.tokensIn === null && call.tokensOut === null ? "—" : `${call.tokensIn ?? "—"} / ${call.tokensOut ?? "—"}`}
      </td>
      <td data-label="Cost">{call.costUsd == null ? "—" : `$${call.costUsd.toFixed(2)}`}</td>
      <td data-label="Duration">{number(call.durationMs)} ms</td>
    </tr>
  );
}
