/**
 * One job's page (0.9 J1u, D62, `/settings/jobs/{jobId}`): its state and progress as they change,
 * its error, Cancel while it can be cancelled, and for a completed export what the file holds and
 * Download. The page follows the job's event stream while it is shown; nothing is polled.
 */

import { useEffect, useState } from "react";
import { api, jobOutputUrl } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import type { EngineModel, Job } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { count } from "@/features/settings/limits";
import { jobTitle } from "./JobNotifications";
import { RESULT, STATE, cancellable, fileSize } from "./jobText";
import { isFinal, useJobStream } from "./useJobStream";

const FORMAT_NAMES = { jsonl: "JSON Lines", csv: "CSV", xlsx: "Excel (XLSX)" } as const;

export function JobPage({
  model,
  jobId,
  canCancel,
  jobsHref,
  onJobs,
}: {
  model: EngineModel;
  jobId: string;
  canCancel: boolean;
  jobsHref: string;
  onJobs: () => void;
}) {
  const [job, setJob] = useState<Job>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [cancelError, setCancelError] = useState("");

  useEffect(() => {
    let current = true;
    api
      .job(jobId)
      .then((loaded) => current && setJob(loaded))
      .catch((cause) => current && setError(errorMessage(cause)));
    return () => {
      current = false;
    };
  }, [jobId, attempt]);
  // While the job runs, its changes arrive over its stream.
  useJobStream(job && !isFinal(job) ? jobId : undefined, setJob);

  async function cancel() {
    setPending(true);
    setCancelError("");
    try {
      setJob(await api.cancelJob(jobId));
      setConfirming(false);
    } catch (cause) {
      setCancelError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const back = (
    <RouteLink href={jobsHref} onNavigate={onJobs}>
      Jobs and feed
    </RouteLink>
  );
  if (error) {
    return (
      <SettingsLayout eyebrow={back} title="Job">
        <InlineError
          message={error}
          onRetry={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}
        />
      </SettingsLayout>
    );
  }
  if (!job) {
    return (
      <SettingsLayout eyebrow={back} title="Job">
        <Skeleton label="Loading the job" lines={6} />
      </SettingsLayout>
    );
  }

  const state = STATE[job.state];
  const output = job.output;
  return (
    <SettingsLayout
      eyebrow={back}
      title={jobTitle(model, job)}
      description={<code>{job.id}</code>}
      actions={
        <>
          {output && (
            <a className="primary" href={jobOutputUrl(job.id)} download>
              Download
            </a>
          )}
          {canCancel && cancellable(job) && (
            <button type="button" className="secondary" onClick={() => setConfirming(true)}>
              Cancel job
            </button>
          )}
        </>
      }
    >
      <Section title="State">
        <p className="job-state">
          <StatusPill tone={job.result === "partial" ? "warning" : state.tone}>{state.label}</StatusPill>
          {job.result && <span>{RESULT[job.result]}</span>}
          {job.cancelRequestedAt && job.state !== "cancelled" && <span>Cancel requested</span>}
        </p>
        {!isFinal(job) && (
          <ProgressLine processed={job.progress.processed} total={job.progress.total} kind={job.kind} />
        )}
        {job.error && (
          <Notice tone="error" title={job.state === "failed" ? "Why it failed" : "What stopped it"}>
            {job.error.message}
          </Notice>
        )}
        <DescriptionList className="compact" items={times(job)} />
      </Section>
      {output && (
        <Section title="The file" description="Everything in it was read at one instant.">
          <DescriptionList
            className="compact"
            items={[
              { term: "Format", value: FORMAT_NAMES[output.format] },
              { term: "Size", value: fileSize(output.bytes) },
              {
                term: "Data",
                value: output.context.changeSetId
                  ? `Change set, version ${output.context.changeSetVersion}`
                  : output.context.publicationId
                    ? "A publication"
                    : "Live data",
              },
              ...(output.feedPosition !== null
                ? [{ term: "Change feed position", value: count(output.feedPosition) }]
                : []),
              ...(output.asOf ? [{ term: "Valid on", value: output.asOf }] : []),
              { term: "Checksum (SHA-256)", value: <code className="job-checksum">{output.sha256}</code> },
            ]}
          />
          <SettingsTable label="Exported records and relationships" columns={["Type", "Count"]}>
            {[
              ...Object.entries(output.counts.records).map(([key, value]) => (
                <tr key={`record:${key}`}>
                  <th scope="row">{model.objectTypes.find((type) => type.key === key)?.pluralName ?? key}</th>
                  <td data-label="Count">{count(value)}</td>
                </tr>
              )),
              ...Object.entries(output.counts.relations).map(([key, value]) => (
                <tr key={`relation:${key}`}>
                  <th scope="row">{model.relationTypes.find((type) => type.key === key)?.name ?? key}</th>
                  <td data-label="Count">{count(value)}</td>
                </tr>
              )),
            ]}
          </SettingsTable>
        </Section>
      )}
      {confirming && (
        <ConfirmDialog
          title="Cancel this job?"
          confirmLabel="Cancel job"
          dismissLabel="Keep the job"
          pending={pending}
          error={cancelError}
          onCancel={() => {
            setConfirming(false);
            setCancelError("");
          }}
          onConfirm={cancel}
        >
          <p>
            {job.kind === "export"
              ? "The export stops at its next check and leaves no file."
              : "The job stops at its next chunk; chunks already committed stay applied."}
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

function ProgressLine({ processed, total, kind }: { processed: number; total: number | null; kind: Job["kind"] }) {
  const unit = kind === "export" ? "rows written" : "items processed";
  return (
    <div className="job-progress">
      <progress value={total ? processed : undefined} max={total ?? undefined} aria-label="Progress" />
      <span>
        {count(processed)}
        {total !== null && ` of ${count(total)}`} {unit}
      </span>
    </div>
  );
}

function times(job: Job): DescriptionItem[] {
  return [
    { term: "Workspace", value: <code>{job.workspaceKey}</code> },
    { term: "Created", value: formatServerTime(job.createdAt) },
    ...(job.startedAt ? [{ term: "Started", value: formatServerTime(job.startedAt) }] : []),
    ...(job.finishedAt ? [{ term: "Finished", value: formatServerTime(job.finishedAt) }] : []),
    { term: "Kept until", value: formatServerTime(job.expiresAt) },
  ];
}
