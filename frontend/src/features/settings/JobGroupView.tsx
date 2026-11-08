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
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { JobGroup, JobGroupRow, JobState, RouteState } from "@/types";
import { Card } from "@/ui/Card";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { TrailBar, TrailLink } from "@/ui/TrailBar";
import { routePath } from "@/routing/routes";
import { ORIGIN, STATE, cancellable } from "@/features/jobs/jobText";
import { useWorkspaceLabels } from "@/features/security/GrantsSection";
import { JOB_COLUMNS, JobRow } from "./JobRow";
import { JOBS, groupRoute, jobRoute } from "./jobRoutes";
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
  const bar = (
    <TrailBar
      back={{ label: "‹ Jobs", onClick: toList }}
      trail={[<TrailLink onClick={toList}>Jobs</TrailLink>, name ? `${kindLabel}: ${name}` : kindLabel]}
    />
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
      <SettingsLayout trail={bar} eyebrow="Data operations" title="Jobs">
        <InlineError message={summaryError} onRetry={() => setToken((value) => value + 1)} />
      </SettingsLayout>
    );
  if (group === undefined)
    return (
      <SettingsLayout trail={bar} eyebrow="Data operations" title="Jobs">
        <Skeleton label="Loading the jobs" lines={5} />
      </SettingsLayout>
    );
  if (group === null || !loaded)
    return (
      <SettingsLayout trail={bar} eyebrow="Data operations" title="Jobs">
        <EmptyState>
          This group has no jobs you can see. Its task or draft may have been removed, or its jobs have expired.
        </EmptyState>
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
    <SettingsLayout trail={bar} eyebrow={`${kindLabel} · ${workspace}`} title={<OriginName name={group.origin.name} />}>
      <Card as="section" aria-label="Summary of the group" className="job-group-summary">
        <div className="job-group-summary-head">
          <p>
            {group.jobs} {group.jobs === 1 ? "job" : "jobs"}, the latest at {formatServerTime(group.latestAt)}.
          </p>
          {canOpen && (
            <button type="button" className="primary" onClick={openOwner}>
              {ORIGIN[origin.kind].open}
            </button>
          )}
        </div>
        <div className="segmented" role="group" aria-label="Show jobs in state">
          {chips.map((chip) => (
            <button
              key={chip.key ?? "all"}
              type="button"
              aria-pressed={chip.key === state}
              onClick={() => onNavigate(groupRoute(origin, chip.key))}
            >
              {chip.label} <strong>{chip.count}</strong>
            </button>
          ))}
        </div>
      </Card>
      <Section
        title="Jobs"
        actions={
          <button type="button" className="secondary" disabled={feed.loading} onClick={() => setToken((v) => v + 1)}>
            Refresh
          </button>
        }
      >
        {cancel.ui}
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && feed.items.length === 0 ? (
          <Skeleton label="Loading jobs" lines={5} />
        ) : feed.items.length === 0 ? (
          <EmptyState>No jobs in this state.</EmptyState>
        ) : (
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
        )}
        {feed.hasMore && !feed.error && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more jobs
          </button>
        )}
      </Section>
    </SettingsLayout>
  );
}
