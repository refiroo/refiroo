import type { Job } from "@/types";
import { formatServerTime } from "@/lib/dates";
import { principalName } from "@/ui/ActorName";
import { RouteLink } from "@/ui/RouteLink";
import { StatusPill } from "@/ui/StatusPill";
import { RESULT, STATE, kindOf } from "@/features/jobs/jobText";
import { count } from "./limits";

/** A job's row in the Jobs table: the flat list, and a group's jobs, which leave out the workspace. */
export function JobRow({
  job,
  workspace,
  link,
  onCancel,
}: {
  job: Job;
  /** The workspace's name; left out (with its cell) in a group, whose jobs share one. */
  workspace?: string;
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
          {kindOf(job)}
          <code>{job.id}</code>
        </RouteLink>
      </th>
      {workspace !== undefined && (
        <td data-label="Workspace">
          {workspace}
          {job.changeSetId && " (change set)"}
        </td>
      )}
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
      <td data-label="Requested by">{job.requestedBy ? principalName(job.requestedBy) : ""}</td>
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

export const JOB_COLUMNS = ["Job", "State", "Items", "Requested by", "Created", "Finished", "Actions"];
