/**
 * Settings › Administration › AI (0.16 AP1, AP-D38): the assistant (`AI_AGENT_COMMAND`) and the AI
 * provider (`AI_PROVIDER`), each of which people review the proposals of. Both are set in the server's
 * environment and read at start, so nothing here changes them; the page shows what is set, what may
 * be sent and a test request of the provider on one tab, and every call made on the other (0.17 ST1, PP-D62).
 */

import { useEffect, useState } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { count, plural } from "@/lib/count";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { formatDuration } from "@/lib/duration";
import { useAddressTab } from "@/lib/hooks/useAddressTab";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { Hue } from "@/model/hues";
import type { AiCall, AiStatus } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  Kind,
  LogFoot,
  LogTotals,
  SettingRow,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
} from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { failureSentence, PURPOSE, sendLevelText } from "@/lib/aiText";
import { settingsHead } from "@/ui/settingsNavigation";

/** One hue per kind of call, kept by the kind so a kind keeps its colour. */
const KIND_HUE: Record<AiCall["purpose"], Hue> = {
  connectionTest: 5,
  mappingTarget: 1,
  queryTranslation: 2,
  impactSummary: 3,
  historyAccount: 4,
  workbookLoad: 7,
  assistantSession: 6,
  modelNames: 8,
};

export function AiPage() {
  const [status, setStatus] = useState<AiStatus>();
  const [error, setError] = useState("");
  // Bumped whenever a call may have been made, so the totals and the list are read again.
  const [refresh, setRefresh] = useState(0);
  const [tab, setTab] = useAddressTab(["settings", "calls"]);
  const head = settingsHead("ai");

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
      {...head}
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
        <Tabs
          label="AI"
          selected={tab}
          onChange={setTab}
          tabs={[
            {
              id: "settings",
              label: "Settings",
              content: (
                <>
                  <SwitchesSection status={status} hue={head.hue} />
                  <SettingsSection status={status} />
                  {status.configured && <FeaturesSection status={status} />}
                  {status.configured && <TestSection onCalled={() => setRefresh((n) => n + 1)} />}
                </>
              ),
            },
            { id: "calls", label: "Calls", content: <CallsSection status={status} refresh={refresh} /> },
          ]}
        />
      )}
    </SettingsLayout>
  );
}

/** The two switches (AP-D38): the assistant needs no provider, and the provider needs no assistant. */
function SwitchesSection({ status, hue }: { status: AiStatus; hue: Hue }) {
  return (
    <SettingsGroup title="What is switched on">
      <SettingsPanel>
        <SettingRow
          lead={<SettingsTile icon="bot" hue={hue} />}
          name="Assistant"
          help={
            status.assistant
              ? "Reads workbooks and words, up to a change set. It sends what the send level below allows and needs no provider."
              : "Loading a workbook with the assistant is not offered."
          }
        >
          {status.assistant ? "On" : "Not set"} (<code>AI_AGENT_COMMAND</code>)
        </SettingRow>
        <SettingRow
          lead={<SettingsTile icon="sparkle" hue={hue} />}
          name="Provider"
          help={
            status.configured
              ? "Asked for mapping targets, search and summaries."
              : "Mapping targets, search and summaries are not offered."
          }
        >
          {status.configured ? `On: ${status.provider ?? "set"}` : "Not set"} (<code>AI_PROVIDER</code>)
        </SettingRow>
      </SettingsPanel>
    </SettingsGroup>
  );
}

function SettingsSection({ status }: { status: AiStatus }) {
  const facts: { name: string; value: string }[] = [
    ...(status.configured
      ? [
          { name: "Model", value: status.model ?? "The provider's own" },
          { name: "Endpoint", value: status.endpoint ?? "The provider's own" },
          { name: "Key", value: status.keySet ? "Set" : "Not set" },
        ]
      : []),
    { name: "What may be sent", value: sendLevelText(status.sendLevel, status.sampleValues) },
    ...(status.configured ? [{ name: "Confidence floor", value: `${Math.round(status.minConfidence * 100)}%` }] : []),
    { name: "Content kept", value: status.logContent ? `For ${status.logContentDays} days` : "No" },
    ...(status.configured ? [{ name: "Timeout", value: `${status.timeoutSeconds} seconds` }] : []),
  ];
  return (
    <SettingsGroup title="Settings">
      <SettingsPanel>
        {facts.map((fact) => (
          <SettingRow key={fact.name} fact name={fact.name}>
            {fact.value}
          </SettingRow>
        ))}
      </SettingsPanel>
    </SettingsGroup>
  );
}

function FeaturesSection({ status }: { status: AiStatus }) {
  return (
    <SettingsGroup
      title="What the AI provider is asked"
      description="Each feature needs a level of what may be sent. One that needs more than is allowed is not offered."
    >
      <SettingsPanel>
        {status.features.map((feature) => (
          <SettingRow
            key={feature.purpose}
            lead={<SettingsTile icon="sparkle" hue={KIND_HUE[feature.purpose]} />}
            name={feature.name}
            help={
              feature.available
                ? undefined
                : `It needs a higher level of what may be sent: ${sendLevelText(feature.needs, status.sampleValues)}.`
            }
          >
            <StatusPill tone={feature.available ? "success" : "neutral"}>
              {feature.available ? "Available" : "Unavailable"}
            </StatusPill>
          </SettingRow>
        ))}
      </SettingsPanel>
    </SettingsGroup>
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
          ? { ok: true, text: `Answered in ${formatDuration(call.durationMs)} by ${call.model ?? call.provider}.` }
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
    <SettingsGroup
      title="Test request"
      description="A small request that sends none of your data. It shows whether the AI provider answers, and it is listed on the Calls tab."
    >
      <SettingsPanel>
        <SettingRow name="Ask the AI provider now" help="One request, answered or failed in a moment.">
          <button type="button" className="secondary" disabled={pending} onClick={() => void test()}>
            {pending ? "Sending…" : "Send a test request"}
          </button>
        </SettingRow>
      </SettingsPanel>
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
    </SettingsGroup>
  );
}

function CallsSection({ status, refresh }: { status: AiStatus; refresh: number }) {
  const { totals } = status;
  const feed = useCursorFeed((cursor) => ai.calls({ cursor }), [refresh]);
  return (
    <>
      <SettingsGroup stacked title={`Last ${totals.days} days`}>
        <LogTotals
          label={`Totals of the last ${totals.days} days`}
          totals={[
            { key: "calls", value: count(totals.calls), name: plural(totals.calls, "call"), hue: 6 },
            { key: "failed", value: count(totals.failed), name: "failed", bad: true },
            { key: "in", value: count(totals.tokensIn), name: "tokens in", hue: 2 },
            { key: "out", value: count(totals.tokensOut), name: "tokens out", hue: 1 },
            {
              key: "cost",
              value: totals.costUsd > 0 ? `$${totals.costUsd.toFixed(2)}` : "—",
              name: "at the provider's prices",
              hue: 4,
            },
          ]}
        />
      </SettingsGroup>
      <SettingsGroup
        stacked
        title="Calls"
        description="Every request made to the AI provider and every assistant session's turn, newest first."
      >
        <SettingsPanel>
          {feed.error ? (
            <InlineError message={feed.error} onRetry={feed.retry} />
          ) : feed.loading && !feed.items.length ? (
            <Skeleton label="Loading calls" lines={4} />
          ) : !feed.items.length ? (
            <SettingsEmpty icon="sparkle" hue={settingsHead("ai").hue}>
              No call has been made yet. A test request, a request for mapping targets or an assistant session appears
              here.
            </SettingsEmpty>
          ) : (
            <>
              <SettingsTable
                label="Calls"
                columns={[
                  "When",
                  "What for",
                  "Asked by",
                  "Outcome",
                  { num: "Tokens in" },
                  { num: "Out" },
                  { num: "Cost" },
                  { num: "Took" },
                ]}
              >
                {feed.items.map((call) => (
                  <CallRow key={call.id} call={call} />
                ))}
              </SettingsTable>
              <LogFoot
                shown={feed.items.length}
                noun="calls"
                onMore={feed.hasMore && !feed.error ? feed.loadMore : undefined}
                loading={feed.loading}
              />
            </>
          )}
        </SettingsPanel>
      </SettingsGroup>
    </>
  );
}

function CallRow({ call }: { call: AiCall }) {
  return (
    <tr>
      <th scope="row" className="when" title={formatServerTime(call.startedAt)}>
        {formatServerDayTime(call.startedAt)}
      </th>
      <td data-label="What for">
        <Kind hue={KIND_HUE[call.purpose]}>{PURPOSE[call.purpose] ?? call.purpose}</Kind>
        {call.model && <span className="why">{call.model}</span>}
      </td>
      <td data-label="Asked by">{call.requestedBy?.name ?? "—"}</td>
      <td data-label="Outcome">
        <StatusPill tone={call.outcome === "answered" ? "success" : "error"}>
          {call.outcome === "answered" ? "Answered" : "Failed"}
        </StatusPill>
        {call.outcome === "failed" && <span className="why">{failureSentence(call)}</span>}
        {call.content && (
          <details className="ai-call-content">
            <summary>Show what was sent and answered</summary>
            <pre className="mono" tabIndex={0} aria-label="What was sent and answered">
              {JSON.stringify(call.content, null, 2)}
            </pre>
          </details>
        )}
      </td>
      <td data-label="Tokens in" className="num">
        {call.tokensIn === null ? "—" : count(call.tokensIn)}
      </td>
      <td data-label="Out" className="num">
        {call.tokensOut === null ? "—" : count(call.tokensOut)}
      </td>
      <td data-label="Cost" className="num">
        {call.costUsd == null ? "—" : `$${call.costUsd.toFixed(2)}`}
      </td>
      <td data-label="Took" className="num">
        {formatDuration(call.durationMs)}
      </td>
    </tr>
  );
}
