/**
 * One job's page (0.9 J1u, D62, `/settings/jobs/{jobId}`): its state and progress as they change,
 * its error, Cancel while it can be cancelled, and for a completed export what the file holds and
 * Download. The page follows the job's event stream while it is shown; nothing is polled.
 *
 * An import's page is the import screen (0.9 J4, D91): its file and profile, the preview with Load
 * the file and Cancel import while it waits, the binding report and the rows; after loading, the
 * result. A waiting preview is not followed (`isResting`); confirming it follows it again.
 *
 * A batch's page (0.9 K2) shows its preview with Apply and Cancel preview while it waits, its result
 * once applied, and its items' outcomes, each linked to its record where it names one.
 *
 * A move's page (0.16) says what it did, by type and item by item, and a migration's what it
 * converted, changed and removed; any other job with nothing of its own to list says what it
 * belongs to and links to it where the caller can open it (`JobProduced`).
 */

import { JobProgress } from "@/ui/JobProgress";
import { count } from "@/lib/count";
import { countedType, relationTypeFor, typeName } from "@/model/lookup";
import { useWorkspaceModel } from "@/model/workspaceModels";
import { useState } from "react";
import { api, jobOutputUrl } from "@/api/client";
import { downloadFrom } from "@/api/download";
import { DownloadLink } from "@/ui/DownloadLink";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { routePath } from "@/routing/routes";
import type { EngineModel, Job, JobItemOutcome, RouteState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Trail, TrailLink, crumbs } from "@/ui/Trail";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { principalName } from "@/ui/ActorName";
import { StatusPill } from "@/ui/StatusPill";
import { useWorkspaceLabels } from "@/features/security/GrantsSection";
import { jobTitle, useJobNotifications } from "@/ui/JobNotifications";
import {
  BindingReportSection,
  ImportFacts,
  ImportNotices,
  ImportPreviewSection,
  ImportReadingSection,
  ImportResultSection,
  ImportRowsSection,
} from "@/ui/ImportOutcome";
import { BatchDeletionSection, BatchItemsSection, BatchPreviewSection, BatchResultSection } from "@/ui/BatchOutcome";
import { JobProduced } from "./JobProduced";
import { MigrationOutcome } from "./MigrationOutcome";
import { MoveOutcome } from "./MoveOutcome";
import { ORIGIN, RESULT, STATE, cancellable, fileSize } from "@/ui/jobText";
import { isResting, useFollowedJob } from "@/state/useFollowedJob";
import { useSubjectSeen } from "@/state/useInbox";

const FORMAT_NAMES = { jsonl: "JSON Lines", csv: "CSV", xlsx: "Excel (XLSX)" } as const;

export function JobPage({
  model: shownModel,
  jobId,
  canCancel,
  jobsHref,
  onJobs,
  fromGroup,
  onNavigate,
}: {
  model: EngineModel;
  jobId: string;
  canCancel: boolean;
  jobsHref: string;
  onJobs: () => void;
  /** The group of related jobs the job was opened from (0.13 JG): the trail keeps it. */
  fromGroup?: { kind: NonNullable<Job["origin"]>["kind"]; onOpen: () => void };
  /** Opens a record a batch's outcome names. */
  onNavigate?: (route: RouteState) => void;
}) {
  const { job, setJob, error, reload } = useFollowedJob(jobId);
  // A job is named and read under its own workspace's model (0.11 D49).
  const model = useWorkspaceModel(job?.workspaceKey, shownModel);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const notifications = useJobNotifications();
  const labels = useWorkspaceLabels();

  // While the job runs, its changes arrive over its stream; a waiting preview is not followed.
  // The person is looking at the job: its notices are read, and one made while here (0.12 NT1).
  useSubjectSeen(jobId);

  async function confirm() {
    setPending(true);
    setConfirmError("");
    try {
      const confirmed = await api.confirmJob(jobId);
      setJob(confirmed);
      // Followed from here on, so its end is announced wherever the user goes.
      notifications.follow(confirmed, { announce: false });
    } catch (cause) {
      // The job keeps waiting; the refusal says why (a change set changed, the model changed).
      setConfirmError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

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

  const back = (page: string) => {
    if (fromGroup) {
      const group = job?.origin ? `${ORIGIN[job.origin.kind].label}: ${job.origin.name}` : ORIGIN[fromGroup.kind].label;
      return (
        <Trail
          items={crumbs(
            <TrailLink onClick={onJobs}>Jobs</TrailLink>,
            <TrailLink onClick={fromGroup.onOpen}>{group}</TrailLink>,
            page,
          )}
        />
      );
    }
    return (
      <Trail
        items={[
          {
            key: "list",
            content: (
              <RouteLink href={jobsHref} onNavigate={onJobs}>
                Jobs
              </RouteLink>
            ),
          },
          { key: "page", content: page, current: true },
        ]}
      />
    );
  };
  if (error) {
    return (
      <SettingsLayout trail={back("Job")} title="Job">
        <InlineError message={error} onRetry={reload} />
      </SettingsLayout>
    );
  }
  if (!job) {
    return (
      <SettingsLayout trail={back("Job")} title="Job">
        <Skeleton label="Loading the job" lines={6} />
      </SettingsLayout>
    );
  }

  const state = STATE[job.state];
  const output = job.output;
  const waiting = job.state === "awaiting_confirmation";
  const imported = job.kind === "import";
  const batch = job.kind === "batch";
  const waitingName = imported ? "import" : "preview";
  return (
    <SettingsLayout
      trail={back(jobTitle(model, job))}
      title={jobTitle(model, job)}
      description={<code>{job.id}</code>}
      actions={
        <>
          {output && (
            <DownloadLink
              className="primary"
              href={jobOutputUrl(job.id)}
              save={() => downloadFrom(jobOutputUrl(job.id), `export-${job.id}`)}
            >
              Download
            </DownloadLink>
          )}
          {canCancel && waiting && (
            <button type="button" className="primary" disabled={pending} onClick={() => void confirm()}>
              {pending && !confirming ? (imported ? "Loading…" : "Applying…") : imported ? "Load the file" : "Apply"}
            </button>
          )}
          {canCancel && (cancellable(job) || waiting) && (
            <button type="button" className="secondary" onClick={() => setConfirming(true)}>
              {waiting ? `Cancel ${waitingName}` : "Cancel job"}
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
        {!isResting(job) && (
          <ProgressLine
            processed={job.progress.processed}
            total={job.progress.total}
            kind={job.kind}
            stage={job.stage}
          />
        )}
        {job.error && (
          <Notice tone="error" title={job.state === "failed" ? "Why it failed" : "What stopped it"}>
            {job.error.message}
            <ErrorProblems details={job.error.details} />
          </Notice>
        )}
        {confirmError && (
          <Notice tone="error" title={imported ? "The file was not loaded" : "The change was not applied"} focusOnMount>
            {confirmError}{" "}
            {imported
              ? "The preview keeps waiting: cancel it and import the file again to preview the data as it is now."
              : "The preview keeps waiting: cancel it and make the change again to preview the data as it is now."}
          </Notice>
        )}
        {!imported && <DescriptionList className="compact" items={times(job, labels)} />}
        {imported && <ImportNotices job={job} />}
      </Section>
      {/* A job with neither items nor rows says what it belongs to, where the caller can open it. */}
      <JobProduced job={job} onNavigate={onNavigate} />
      {job.kind === "move" && job.move && (
        <MoveOutcome job={job} summary={job.move} model={model} onNavigate={onNavigate} />
      )}
      {job.kind === "migration" && job.migration && (
        <MigrationOutcome job={job} summary={job.migration} model={model} />
      )}
      {imported && (
        // What to act on first: the result or the preview, then the rows; how it was read, then its facts.
        <>
          {job.confirmedAt ? <ImportResultSection job={job} /> : <ImportPreviewSection job={job} />}
          {!job.confirmedAt && job.state === "awaiting_confirmation" && (
            <ImportReadingSection job={job} onNavigate={onNavigate} />
          )}
          {isResting(job) && (job.preview || job.bindingReport) && <ImportRowsSection key={job.state} job={job} />}
          {job.confirmedAt && <ImportPreviewSection job={job} />}
          <BindingReportSection model={model} job={job} />
          <Section title="This import">
            <ImportFacts job={job} />
            <DescriptionList className="compact" items={times(job, labels)} />
          </Section>
        </>
      )}
      {batch && (
        <>
          {job.preview && !job.confirmedAt ? <BatchPreviewSection job={job} /> : <BatchResultSection job={job} />}
          {job.preview && !job.confirmedAt && (
            <BatchDeletionSection job={job} typeName={(key, records) => countedType(model, key, records)} />
          )}
          {isResting(job) && (
            <BatchItemsSection
              key={job.state}
              job={job}
              label={(outcome) => recordLink(model, job, outcome, onNavigate)}
            />
          )}
          {job.confirmedAt && <BatchPreviewSection job={job} />}
          {job.confirmedAt && (
            <BatchDeletionSection job={job} typeName={(key, records) => countedType(model, key, records)} />
          )}
        </>
      )}
      {output && (
        <Section title="The file" description="Everything in it was read at one instant.">
          <DescriptionList
            className="compact"
            items={[
              {
                term: "Format",
                value:
                  output.layout === "people"
                    ? `${FORMAT_NAMES[output.format]}, a workbook for people`
                    : FORMAT_NAMES[output.format],
              },
              ...(output.sheets?.length ? [{ term: "Sheets", value: output.sheets.join(", ") }] : []),
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
                  <th scope="row">{typeName(model, key, { plural: true })}</th>
                  <td data-label="Count">{count(value)}</td>
                </tr>
              )),
              ...Object.entries(output.counts.relations).map(([key, value]) => (
                <tr key={`relation:${key}`}>
                  <th scope="row">{relationTypeFor(model, key)?.name ?? key}</th>
                  <td data-label="Count">{count(value)}</td>
                </tr>
              )),
            ]}
          </SettingsTable>
        </Section>
      )}
      {confirming && (
        <ConfirmDialog
          title={waiting ? `Cancel this ${waitingName}?` : "Cancel this job?"}
          confirmLabel={waiting ? `Discard the ${waitingName}` : "Stop the job"}
          dismissLabel={waiting ? `Keep the ${waitingName}` : "Keep the job"}
          pending={pending}
          error={cancelError}
          onCancel={() => {
            setConfirming(false);
            setCancelError("");
          }}
          onConfirm={cancel}
        >
          <p>
            {waiting
              ? "Nothing was written and nothing will be. The preview stays readable until the job expires."
              : job.kind === "export"
                ? "The export stops at its next check and leaves no file."
                : "The job stops at its next chunk; chunks already committed stay applied."}
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

/**
 * An outcome's name, linked to its record where the outcome names one that still stands: in the
 * first application that shows its type, in the job's workspace or change set.
 */
function recordLink(
  model: EngineModel,
  job: Job,
  outcome: JobItemOutcome,
  onNavigate: ((route: RouteState) => void) | undefined,
) {
  const name = outcome.ref ?? `Item ${count(outcome.index + 1)}`;
  const objectTypeKey = outcome.objectTypeKey;
  const application = objectTypeKey && model.applications.find((item) => item.objectTypeKeys.includes(objectTypeKey));
  // A deleted record, or one gone with another item's, has nothing left to open (0.9 K2b).
  const gone = outcome.action === "deleted" || outcome.deletedWithItem !== undefined;
  if (!onNavigate || !outcome.id || !objectTypeKey || !application || gone) return name;
  const route: RouteState = {
    kind: "detail",
    applicationKey: application.key,
    objectTypeKey,
    objectId: outcome.id,
    workspaceKey: job.workspaceKey,
    ...(job.changeSetId ? { changeSetId: job.changeSetId } : {}),
  };
  return (
    <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
      {name}
    </RouteLink>
  );
}

/** The problems a job's error lists (`details.problems`), each at its path: a file that does not fit. */
function ErrorProblems({ details }: { details: unknown }) {
  const problems = (details as { problems?: { path?: string; message?: string }[] } | undefined)?.problems;
  if (!Array.isArray(problems) || !problems.length) return null;
  return (
    <ul className="field-problems">
      {problems.map((problem, position) => (
        <li key={position}>
          {problem.message}
          {problem.path && <> ({problem.path})</>}
        </li>
      ))}
    </ul>
  );
}

/** An import's stages as people read them (0.9 J3: binding, previewing, applying). */
const STAGES: Record<string, string> = {
  binding: "Reading the file",
  previewing: "Previewing",
  applying: "Loading",
};

function ProgressLine({
  processed,
  total,
  kind,
  stage,
}: {
  processed: number;
  total: number | null;
  kind: Job["kind"];
  stage: string | null;
}) {
  const unit = kind === "export" ? "rows written" : "items processed";
  // A batch is previewed too (0.9 K2); it applies rather than loads.
  const step =
    kind === "import" && stage
      ? STAGES[stage]
      : kind === "batch" && stage === "previewing"
        ? STAGES.previewing
        : undefined;
  return (
    <JobProgress processed={processed} total={total}>
      {step && `${step}: `}
      {count(processed)}
      {total !== null && ` of ${count(total)}`} {unit}
    </JobProgress>
  );
}

const when = (value: string) => <span title={formatServerTime(value)}>{formatServerDayTime(value)}</span>;

function times(job: Job, labels: ReadonlyMap<string, string>): DescriptionItem[] {
  return [
    { term: "Workspace", value: labels.get(job.workspaceKey) ?? job.workspaceKey },
    ...(job.requestedBy ? [{ term: "Requested by", value: principalName(job.requestedBy) }] : []),
    { term: "Created", value: when(job.createdAt) },
    ...(job.startedAt ? [{ term: "Started", value: when(job.startedAt) }] : []),
    ...(job.finishedAt ? [{ term: "Finished", value: when(job.finishedAt) }] : []),
    { term: "Kept until", value: when(job.expiresAt) },
  ];
}
