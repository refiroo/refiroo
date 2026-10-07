/**
 * Settings › Integration › Jobs and feed (Track U U4): the jobs of every workspace, newest first
 * (`GET /jobs`), with their state and outcome counts, and a cancel for a queued or running job while
 * jobs can be created (`POST /jobs/{id}/cancel`, J24.2); then the job limits and the change feed's
 * retention from `GET /capabilities`. Each job opens its own page, and New export starts an export
 * of any types of a workspace (0.9 J1u, D57, D62).
 */

import { useState } from "react";
import { ExportDialog } from "@/features/jobs/ExportDialog";
import { JobPage } from "@/features/jobs/JobPage";
import { useJobNotifications } from "@/features/jobs/JobNotifications";
import { routePath } from "@/routing/routes";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { EngineModel, Job, RouteState, SettingsRoute } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { KIND, RESULT, STATE, cancellable } from "@/features/jobs/jobText";
import { count, jobLimitItems } from "./limits";
import { useCapabilities } from "./useSystem";

const JOBS: Extract<SettingsRoute, { page: "jobs" }> = { kind: "settings", page: "jobs" };

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
  if (route.jobId)
    return (
      <JobPage
        key={route.jobId}
        model={model}
        jobId={route.jobId}
        canCancel={capabilities?.integrationJobs.createJobs ?? false}
        jobsHref={routePath(JOBS)}
        onJobs={() => onNavigate(JOBS)}
      />
    );
  return <JobList model={model} onNavigate={onNavigate} />;
}

function JobList({ model, onNavigate }: { model: EngineModel; onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => api.jobs(cursor), []);
  const notifications = useJobNotifications();
  const [exporting, setExporting] = useState(false);
  const { capabilities, error: capabilityError, retry: retryCapabilities } = useCapabilities();
  const [cancelling, setCancelling] = useState<Job>();
  const [pending, setPending] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [notice, setNotice] = useState("");
  const canCancel = capabilities?.integrationJobs.createJobs ?? false;
  const open = (job: Job) => {
    const next: RouteState = { ...JOBS, jobId: job.id };
    return { href: routePath(next), onNavigate: () => onNavigate(next) };
  };

  async function cancel() {
    if (!cancelling) return;
    setPending(true);
    setCancelError("");
    try {
      const updated = await api.cancelJob(cancelling.id);
      feed.setItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setCancelling(undefined);
    } catch (cause) {
      if (isApiError(cause) && cause.status === 409) {
        // The job finished before the request reached it: say so, and show where it ended.
        setCancelling(undefined);
        setNotice(errorMessage(cause));
        feed.reload();
      } else {
        setCancelError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <SettingsLayout
      eyebrow="Integration"
      title="Jobs and feed"
      description="Bulk writes and exports run as jobs. Jobs of every workspace are listed newest first; finished jobs are kept for the retention below."
      actions={
        canCancel && (
          <button type="button" className="primary" onClick={() => setExporting(true)}>
            New export
          </button>
        )
      }
    >
      <Section
        title="Jobs"
        actions={
          <button type="button" className="secondary" disabled={feed.loading} onClick={feed.reload}>
            Refresh
          </button>
        }
      >
        {notice && (
          <Notice
            tone="warning"
            actions={
              <button type="button" className="secondary" onClick={() => setNotice("")}>
                Dismiss
              </button>
            }
          >
            {notice}
          </Notice>
        )}
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && feed.items.length === 0 ? (
          <Skeleton label="Loading jobs" lines={5} />
        ) : feed.items.length === 0 ? (
          <EmptyState>
            No jobs yet. A job is created by an export, or when a batch is submitted to{" "}
            <code>POST /api/v1/batches</code>.
          </EmptyState>
        ) : (
          <SettingsTable
            label="Jobs"
            columns={["Job", "Workspace", "State", "Items", "Created", "Finished", "Actions"]}
          >
            {feed.items.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                link={open(job)}
                onCancel={canCancel && cancellable(job) ? () => setCancelling(job) : undefined}
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
      <Section title="Limits" description="Deployment settings, shown on Deployment with the variables that set them.">
        {capabilityError ? (
          <InlineError message={capabilityError} onRetry={retryCapabilities} />
        ) : !capabilities ? (
          <Skeleton label="Loading the limits" lines={4} />
        ) : (
          <DescriptionList className="compact" items={jobLimitItems(capabilities)} />
        )}
      </Section>
      {exporting && (
        <ExportDialog
          model={model}
          start={{ objectTypeKeys: model.objectTypes.map((type) => type.key), selected: [] }}
          onClose={() => setExporting(false)}
          onStarted={(job) => {
            setExporting(false);
            notifications.follow(job);
            feed.setItems((items) => [job, ...items]);
          }}
        />
      )}
      {cancelling && (
        <ConfirmDialog
          title="Cancel this job?"
          confirmLabel="Cancel job"
          dismissLabel="Keep the job"
          pending={pending}
          error={cancelError}
          onCancel={() => {
            setCancelling(undefined);
            setCancelError("");
          }}
          onConfirm={cancel}
        >
          <p>
            The job stops at its next chunk. Items it has not reached are left unprocessed; chunks already committed
            stay applied, and an atomic job is rolled back completely.
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

function JobRow({
  job,
  link,
  onCancel,
}: {
  job: Job;
  link: { href: string; onNavigate: () => void };
  onCancel?: () => void;
}) {
  const state = STATE[job.state];
  const { applied, rejected, unprocessed } = job.counts;
  const total = job.progress.total;
  return (
    <tr>
      <th scope="row">
        <RouteLink className="job-name" {...link}>
          {KIND[job.kind]}
          <code>{job.id}</code>
        </RouteLink>
      </th>
      <td data-label="Workspace">
        <code>{job.workspaceKey}</code>
        {job.changeSetId && " (change set)"}
      </td>
      <td data-label="State">
        <span className="job-state">
          <StatusPill tone={job.result === "partial" ? "warning" : state.tone}>{state.label}</StatusPill>
          {job.result && <span>{RESULT[job.result]}</span>}
          {job.cancelRequestedAt && job.state !== "cancelled" && <span>Cancel requested</span>}
          {job.error && <span>{job.error.message}</span>}
        </span>
      </td>
      <td data-label="Items">
        {count(job.progress.processed)}
        {total !== null && ` of ${count(total)}`} processed: {count(applied)} applied, {count(rejected)} rejected,{" "}
        {count(unprocessed)} unprocessed
      </td>
      <td data-label="Created">{formatServerTime(job.createdAt)}</td>
      <td data-label="Finished">{job.finishedAt ? formatServerTime(job.finishedAt) : ""}</td>
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
