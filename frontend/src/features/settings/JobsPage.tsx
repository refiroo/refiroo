/**
 * Settings › Data operations › Jobs (Track U U4; under Data operations since 0.10 A5c): the jobs of every workspace, newest first
 * (`GET /jobs`), with their state and outcome counts, and a cancel for a queued or running job while
 * jobs can be created (`POST /jobs/{id}/cancel`, J24.2); then the job limits from `GET /capabilities`
 * (the change feed's retention is on Consumer APIs). Each job opens its own page, and New export starts an export
 * of any types of a workspace (0.9 J1u, D57, D62). New import loads a file into a workspace's live
 * data or one of its change sets, and opens the import's page (0.9 J4, D89, D91).
 *
 * Related jobs are grouped (0.13 JG): an assistant task's jobs, with those its session queued, and a
 * model draft's are one row each (`GET /jobs?grouped=true`), opened in the same view under the shared
 * trail bar (`JobGroupView`). A switch shows the flat list as before; the choice is kept in the browser.
 */

import { useEffect, useState } from "react";
import { ExportDialog } from "@/features/jobs/ExportDialog";
import { ImportDialog } from "@/features/jobs/ImportDialog";
import { JobPage } from "@/features/jobs/JobPage";
import { useJobNotifications } from "@/features/jobs/JobNotifications";
import { routePath } from "@/routing/routes";
import { api } from "@/api/client";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useAddressTab } from "@/lib/hooks/useAddressTab";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import type { EngineModel, Job, JobGroupRow, RouteState, SettingsRoute } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { FilterChip, LogFoot, SettingRow, SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { ORIGIN, STATE, cancellable, kindOf } from "@/features/jobs/jobText";
import { count, jobLimitItems } from "./limits";
import { useWorkspaceLabels } from "@/features/security/GrantsSection";
import { useCapabilities } from "./useSystem";
import { useHoldsGroup } from "@/app/useMe";
import { OriginName } from "@/features/jobs/OriginName";
import { JobGroupView } from "./JobGroupView";
import { JOB_COLUMNS, JobRow } from "./JobRow";
import { JOBS, groupRoute, jobRoute } from "./jobRoutes";
import { settingsHead } from "./navigation";
import { useJobCancel } from "./useJobCancel";

type View = "grouped" | "all";
const VIEW_KEY = "refiroo.jobs.view";
const isView = (value: unknown): value is View => value === "grouped" || value === "all";

export function JobsPage({
  model,
  route,
  onNavigate,
}: {
  model: EngineModel;
  route: Extract<SettingsRoute, { page: "jobs" }>;
  onNavigate: (route: RouteState) => void;
}) {
  const { capabilities } = useCapabilities();
  const canCancel = capabilities?.integrationJobs.createJobs ?? false;
  const { jobId, group, state } = route;

  // Esc goes up one level: from a job to the group it was opened from, from a group to the list.
  useEffect(() => {
    const up = jobId ? (group ? groupRoute(group, state) : JOBS) : group ? JOBS : undefined;
    if (!up) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable]")) return;
      if (document.querySelector('[role="dialog"], [role="alertdialog"]')) return;
      onNavigate(up);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [jobId, group, state, onNavigate]);

  if (jobId)
    return (
      <JobPage
        key={jobId}
        model={model}
        jobId={jobId}
        canCancel={canCancel}
        jobsHref={routePath(JOBS)}
        onJobs={() => onNavigate(JOBS)}
        fromGroup={group && { kind: group.kind, onOpen: () => onNavigate(groupRoute(group, state)) }}
        onNavigate={onNavigate}
      />
    );
  if (group)
    return (
      <JobGroupView
        key={`${group.kind}:${group.id}`}
        origin={group}
        state={state}
        canCancel={canCancel}
        onNavigate={onNavigate}
      />
    );
  return <JobList model={model} onNavigate={onNavigate} />;
}

function JobList({ model, onNavigate }: { model: EngineModel; onNavigate: (route: RouteState) => void }) {
  const notifications = useJobNotifications();
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const imports = useHoldsGroup("bulk");
  const { capabilities, error: capabilityError, retry: retryCapabilities } = useCapabilities();
  const [view, setView] = useState<View>(() => readLocalPreference(VIEW_KEY, "grouped", isView));
  const [token, setToken] = useState(0);
  const [tab, setTab] = useAddressTab(["jobs", "limits"]);
  const canCancel = capabilities?.integrationJobs.createJobs ?? false;
  const choose = (next: View) => {
    setView(next);
    writeLocalPreference(VIEW_KEY, next);
  };
  const List = view === "grouped" ? GroupedJobs : FlatJobs;

  return (
    <SettingsLayout
      {...settingsHead("jobs")}
      title="Jobs"
      description="Bulk writes, imports and exports run as jobs. Jobs that belong together, an assistant task's or a model draft's, are grouped; open a group to see its jobs. Finished jobs are kept for the retention on the Limits tab."
      actions={
        canCancel && (
          <>
            {/* An import needs Bulk and import somewhere (0.12 Z5, D323). */}
            {imports && (
              <button type="button" className="secondary" onClick={() => setImporting(true)}>
                New import
              </button>
            )}
            <button type="button" className="primary" onClick={() => setExporting(true)}>
              New export
            </button>
          </>
        )
      }
    >
      <Tabs
        label="Jobs"
        selected={tab}
        onChange={setTab}
        tabs={[
          {
            id: "jobs",
            label: "Jobs",
            content: (
              <SettingsGroup
                stacked
                title="Jobs"
                tools={
                  <>
                    <span className="filter-chips" role="group" aria-label="List">
                      <FilterChip selected={view === "grouped"} onSelect={() => choose("grouped")}>
                        Grouped
                      </FilterChip>
                      <FilterChip selected={view === "all"} onSelect={() => choose("all")}>
                        All jobs
                      </FilterChip>
                    </span>
                    <button type="button" className="secondary" onClick={() => setToken((value) => value + 1)}>
                      Refresh
                    </button>
                  </>
                }
              >
                <SettingsPanel>
                  <List token={token} canCancel={canCancel} onNavigate={onNavigate} />
                </SettingsPanel>
              </SettingsGroup>
            ),
          },
          {
            id: "limits",
            label: "Limits",
            content: (
              <SettingsGroup
                title="Limits"
                description="Deployment settings, shown on Deployment with the variables that set them."
              >
                {capabilityError ? (
                  <InlineError message={capabilityError} onRetry={retryCapabilities} />
                ) : !capabilities ? (
                  <Skeleton label="Loading the limits" lines={4} />
                ) : (
                  <SettingsPanel>
                    {jobLimitItems(capabilities).map((item, at) => (
                      <SettingRow key={at} fact name={item.term}>
                        {item.value}
                      </SettingRow>
                    ))}
                  </SettingsPanel>
                )}
              </SettingsGroup>
            ),
          },
        ]}
      />
      {exporting && (
        <ExportDialog
          model={model}
          start={{ objectTypeKeys: model.objectTypes.map((type) => type.key), selected: [] }}
          onClose={() => setExporting(false)}
          onStarted={(job) => {
            setExporting(false);
            notifications.follow(job);
            setToken((value) => value + 1);
          }}
        />
      )}
      {importing && (
        <ImportDialog
          model={model}
          start={{}}
          onClose={() => setImporting(false)}
          onStarted={(job) => {
            setImporting(false);
            notifications.follow(job, { announce: false });
            // The preview is the screen the user came for: its page opens at once (D91).
            onNavigate({ ...JOBS, jobId: job.id });
          }}
        />
      )}
    </SettingsLayout>
  );
}

const NO_JOBS = (
  <SettingsEmpty icon="activity" hue={settingsHead("jobs").hue}>
    No jobs yet. A job is created by an import or an export, or when a batch is submitted to{" "}
    <code>POST /api/v1/batches</code>.
  </SettingsEmpty>
);

type ListProps = { token: number; canCancel: boolean; onNavigate: (route: RouteState) => void };

/** Every job, newest first, as the list was before grouping. */
function FlatJobs({ token, canCancel, onNavigate }: ListProps) {
  const feed = useCursorFeed((cursor) => api.jobs(cursor), [token]);
  const labels = useWorkspaceLabels();
  const cancel = useJobCancel({
    onCancelled: (updated) => feed.setItems((items) => items.map((item) => (item.id === updated.id ? updated : item))),
    onFinishedFirst: feed.reload,
  });
  const open = (job: Job) => {
    const next = jobRoute(job.id);
    return { href: routePath(next), onNavigate: () => onNavigate(next) };
  };
  return (
    <>
      {cancel.ui}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && feed.items.length === 0 ? (
        <Skeleton label="Loading jobs" lines={5} />
      ) : feed.items.length === 0 ? (
        NO_JOBS
      ) : (
        <SettingsTable label="Jobs" columns={["Job", "Workspace", ...JOB_COLUMNS.slice(1)]}>
          {feed.items.map((job) => (
            <JobRow
              key={job.id}
              job={job}
              workspace={labels.get(job.workspaceKey) ?? job.workspaceKey}
              link={open(job)}
              onCancel={canCancel && cancellable(job) ? () => cancel.ask(job) : undefined}
            />
          ))}
        </SettingsTable>
      )}
      {feed.items.length > 0 && !feed.error && (
        <LogFoot
          shown={feed.items.length}
          noun="jobs"
          onMore={feed.hasMore ? feed.loadMore : undefined}
          loading={feed.loading}
        />
      )}
    </>
  );
}

/** One row per assistant task or model draft, and one per job of neither, newest activity first. */
function GroupedJobs({ token, canCancel, onNavigate }: ListProps) {
  const feed = useCursorFeed((cursor) => api.jobGroups(cursor), [token]);
  const labels = useWorkspaceLabels();
  const cancel = useJobCancel({
    onCancelled: (updated) =>
      feed.setItems((items) => items.map((item) => (item.job.id === updated.id ? { ...item, job: updated } : item))),
    onFinishedFirst: feed.reload,
  });
  return (
    <>
      {cancel.ui}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && feed.items.length === 0 ? (
        <Skeleton label="Loading jobs" lines={5} />
      ) : feed.items.length === 0 ? (
        NO_JOBS
      ) : (
        <SettingsTable label="Jobs" columns={["Job or group", "Workspace", "Jobs", "State", "Latest", "Actions"]}>
          {feed.items.map((row) => (
            <GroupedRow
              key={row.group ? `${row.group.origin.kind}:${row.group.origin.id}` : row.job.id}
              row={row}
              workspace={labels.get(row.job.workspaceKey) ?? row.job.workspaceKey}
              onNavigate={onNavigate}
              onCancel={canCancel && cancellable(row.job) ? () => cancel.ask(row.job) : undefined}
            />
          ))}
        </SettingsTable>
      )}
      {feed.items.length > 0 && !feed.error && (
        <LogFoot
          shown={feed.items.length}
          noun="jobs"
          onMore={feed.hasMore ? feed.loadMore : undefined}
          loading={feed.loading}
        />
      )}
    </>
  );
}

function GroupedRow({
  row,
  workspace,
  onNavigate,
  onCancel,
}: {
  row: JobGroupRow;
  workspace: string;
  onNavigate: (route: RouteState) => void;
  onCancel?: () => void;
}) {
  const { job, group } = row;
  if (!group) {
    const next = jobRoute(job.id);
    const state = STATE[job.state];
    return (
      <tr>
        <th scope="row">
          <RouteLink className="job-group-name" href={routePath(next)} onNavigate={() => onNavigate(next)}>
            <span className="job-group-chevron" aria-hidden="true" />
            <span className="job-name">
              {kindOf(job)}
              <code>{job.id}</code>
            </span>
          </RouteLink>
        </th>
        <td data-label="Workspace">{workspace}</td>
        <td data-label="Jobs">1 job</td>
        <td data-label="State">
          <span className="job-state">
            <StatusPill tone={job.result === "partial" ? "warning" : state.tone}>{state.label}</StatusPill>
            {job.cancelRequestedAt && job.state !== "cancelled" && <span>Cancel requested</span>}
          </span>
        </td>
        <td data-label="Latest" className="when" title={formatServerTime(job.createdAt)}>
          {formatServerDayTime(job.createdAt)}
        </td>
        <td data-label="Actions">
          {onCancel && (
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
          )}
        </td>
      </tr>
    );
  }
  const next = groupRoute({ kind: group.origin.kind, id: group.origin.id });
  const open = () => onNavigate(next);
  return (
    <tr
      className="job-group-row"
      onClick={(event) => {
        if (!(event.target instanceof Element && event.target.closest("a, button"))) open();
      }}
    >
      <th scope="row">
        <RouteLink className="job-group-name" href={routePath(next)} onNavigate={open}>
          <span className="job-group-chevron" aria-hidden="true">
            <Icon name="chevron-right" size={14} />
          </span>
          <span className="job-name">
            <span className="job-kind-tag">{ORIGIN[group.origin.kind].label}</span>
            <OriginName name={group.origin.name} />
          </span>
        </RouteLink>
      </th>
      <td data-label="Workspace">{workspace}</td>
      <td data-label="Jobs">
        {count(group.jobs)} {group.jobs === 1 ? "job" : "jobs"}
      </td>
      <td data-label="State">
        <span className="job-group-states">
          {(["running", "queued", "awaiting_confirmation", "failed", "completed", "cancelled", "expired"] as const)
            .filter((value) => group.states[value] > 0)
            .map((value) => (
              <StatusPill key={value} tone={STATE[value].tone}>
                {count(group.states[value])} {STATE[value].label.toLowerCase()}
              </StatusPill>
            ))}
        </span>
      </td>
      <td data-label="Latest" className="when" title={formatServerTime(group.latestAt)}>
        {formatServerDayTime(group.latestAt)}
      </td>
      <td data-label="Actions" />
    </tr>
  );
}
