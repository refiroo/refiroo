/**
 * A group of related jobs opened in the Jobs page (0.13 JG): under the shared trail bar, a summary
 * of what the group is with its states as filters, and the group's jobs. The group and the filter
 * are in the address (`/settings/jobs/groups/{aiTask|modelDraft}/{id}?state=failed`).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { OriginName } from "@/features/jobs/OriginName";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { JobGroup, JobGroupRow, JobState, RouteState } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  FilterChip,
  ItemHeader,
  LogFoot,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
} from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { Trail, TrailLink, crumbs } from "@/ui/Trail";
import { routePath } from "@/routing/routes";
import { ORIGIN, STATE, cancellable } from "@/ui/jobText";
import { useWorkspaceLabels } from "@/features/security/GrantsSection";
import { JOB_COLUMNS, JobRow } from "./JobRow";
import { JOBS, groupRoute, jobRoute } from "./jobRoutes";
import { settingsHead } from "@/ui/settingsNavigation";
import { useJobCancel } from "./useJobCancel";

type Origin = NonNullable<Extract<RouteState, { page: "jobs" }>["group"]>;

/** The states a group's chips offer, in the order a person looks for trouble first. */
const CHIP_ORDER: JobState[] = [
  "running",
  "queued",
  "awaiting_confirmation",
  "failed",
  "completed",
  "cancelled",
  "expired",
];

/**
 * Whether the person may open what the group belongs to. The engine decides, so it is asked: the
 * button is offered once the task or the draft has been read, and never shown disabled.
 */
function useCanOpen(origin: Origin): boolean {
  const [allowed, setAllowed] = useState<{ key: string; value: boolean }>();
  const key = `${origin.kind}:${origin.id}`;
  useEffect(() => {
    let current = true;
    const read = origin.kind === "aiTask" ? ai.task(origin.id) : api.modelDraft(origin.id);
    read.then(
      () => current && setAllowed({ key, value: true }),
      () => current && setAllowed({ key, value: false }),
    );
    return () => {
      current = false;
    };
  }, [key, origin.kind, origin.id]);
  return allowed?.key === key && allowed.value;
}

export function JobGroupView({
  origin,
  state,
  canCancel,
  onNavigate,
}: {
  origin: Origin;
  state?: JobState;
  canCancel: boolean;
  onNavigate: (route: RouteState) => void;
}) {
  const labels = useWorkspaceLabels();
  const [token, setToken] = useState(0);
  const [summary, setSummary] = useState<{ row: JobGroupRow | null; token: number; key: string }>();
  const [summaryError, setSummaryError] = useState("");
  const key = `${origin.kind}:${origin.id}`;
  const canOpen = useCanOpen(origin);

  useEffect(() => {
    let current = true;
    api
      .jobGroups(undefined, { origin: key })
      .then((page) => {
        if (!current) return;
        setSummaryError("");
        setSummary({ row: page.items[0] ?? null, token, key });
      })
      .catch((cause) => current && setSummaryError(errorMessage(cause)));
    return () => {
      current = false;
    };
  }, [key, token]);

  const feed = useCursorFeed((cursor) => api.jobs(cursor, { origin: key, state }), [key, state, token]);
  const cancel = useJobCancel({
    onCancelled: (updated) => {
      feed.setItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setToken((value) => value + 1);
    },
    onFinishedFirst: () => setToken((value) => value + 1),
  });

  const loaded = summary?.key === key ? summary.row : undefined;
  const group: JobGroup | null | undefined = loaded === undefined ? undefined : (loaded?.group ?? null);
  const name = group?.origin.name;
  const kindLabel = ORIGIN[origin.kind].label;
  const toList = () => onNavigate(JOBS);
  const head = settingsHead("jobs");
  const bar = (
    <Trail items={crumbs(<TrailLink onClick={toList}>Jobs</TrailLink>, name ? `${kindLabel}: ${name}` : kindLabel)} />
  );
  const open = (jobId: string) => {
    const next = jobRoute(jobId, { group: origin, state });
    return { href: routePath(next), onNavigate: () => onNavigate(next) };
  };
  const openOwner = () =>
    onNavigate(
      origin.kind === "aiTask"
        ? { kind: "settings", page: "ai-tasks", taskId: origin.id }
        : { kind: "settings", page: "model", draftId: origin.id },
    );

  if (summaryError)
    return (
      <SettingsLayout trail={bar} {...head} title="Jobs">
        <InlineError message={summaryError} onRetry={() => setToken((value) => value + 1)} />
      </SettingsLayout>
    );
  if (group === undefined)
    return (
      <SettingsLayout trail={bar} {...head} title="Jobs">
        <Skeleton label="Loading the jobs" lines={5} />
      </SettingsLayout>
    );
  if (group === null || !loaded)
    return (
      <SettingsLayout trail={bar} {...head} title="Jobs">
        <SettingsPanel>
          <SettingsEmpty icon="activity" hue={head.hue}>
            This group has no jobs you can see. Its task or draft may have been removed, or its jobs have expired.
          </SettingsEmpty>
        </SettingsPanel>
      </SettingsLayout>
    );

  const chips: { key: JobState | undefined; label: string; count: number }[] = [
    { key: undefined, label: "All", count: group.jobs },
    ...CHIP_ORDER.filter((value) => group.states[value] > 0).map((value) => ({
      key: value,
      label: STATE[value].label,
      count: group.states[value],
    })),
  ];
  const workspace = labels.get(loaded.job.workspaceKey) ?? loaded.job.workspaceKey;

  return (
    <SettingsLayout
      trail={bar}
      header={
        <ItemHeader
          hue={head.hue}
          lead={<SettingsTile icon={head.icon} hue={head.hue} size={48} />}
          title={
            <h1>
              <OriginName name={group.origin.name} />
            </h1>
          }
          meta={
            <>
              <span>{kindLabel}</span>
              <span>{workspace}</span>
              <span title={formatServerTime(group.latestAt)}>
                {counted(group.jobs, "job")}, the latest {formatServerDayTime(group.latestAt)}
              </span>
            </>
          }
          actions={
            canOpen && (
              <button type="button" className="primary" onClick={openOwner}>
                {ORIGIN[origin.kind].open}
              </button>
            )
          }
        />
      }
    >
      <SettingsGroup
        stacked
        title="Jobs"
        tools={
          <>
            <span className="filter-chips" role="group" aria-label="Show jobs in state">
              {chips.map((chip) => (
                <FilterChip
                  key={chip.key ?? "all"}
                  selected={chip.key === state}
                  onSelect={() => onNavigate(groupRoute(origin, chip.key))}
                >
                  {chip.label} <strong>{chip.count}</strong>
                </FilterChip>
              ))}
            </span>
            <button type="button" className="secondary" disabled={feed.loading} onClick={() => setToken((v) => v + 1)}>
              Refresh
            </button>
          </>
        }
      >
        {cancel.ui}
        <SettingsPanel>
          {feed.error ? (
            <InlineError message={feed.error} onRetry={feed.retry} />
          ) : feed.loading && feed.items.length === 0 ? (
            <Skeleton label="Loading jobs" lines={5} />
          ) : feed.items.length === 0 ? (
            <SettingsEmpty icon="activity" hue={head.hue}>
              No jobs in this state.
            </SettingsEmpty>
          ) : (
            <>
              <SettingsTable label="Jobs in this group" columns={JOB_COLUMNS}>
                {feed.items.map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    link={open(job.id)}
                    onCancel={canCancel && cancellable(job) ? () => cancel.ask(job) : undefined}
                  />
                ))}
              </SettingsTable>
              <LogFoot
                shown={feed.items.length}
                total={!feed.hasMore ? undefined : (chips.find((chip) => chip.key === state)?.count ?? undefined)}
                noun="jobs"
                onMore={feed.hasMore ? feed.loadMore : undefined}
                loading={feed.loading}
              />
            </>
          )}
        </SettingsPanel>
      </SettingsGroup>
    </SettingsLayout>
  );
}
