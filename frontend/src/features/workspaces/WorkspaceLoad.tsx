/**
 * The load of a workspace made from a workbook (0.17 PL4), on the workspace's own page: its progress while the
 * job runs, then what loaded and what did not. It stays until dismissed; the rows that did not load are on the
 * job's page, one step further.
 */

import { useState } from "react";
import { count, counted } from "@/lib/count";
import { isFinal, useFollowedJob } from "@/state/useFollowedJob";
import { forgetWorkspaceLoad, workspaceLoadOf } from "@/features/workspaces/fromWorkbook";
import type { RouteState } from "@/types";
import { Notice } from "@/ui/Notice";

export function WorkspaceLoad({
  workspaceKey,
  onNavigate,
}: {
  workspaceKey: string;
  onNavigate: (route: RouteState) => void;
}) {
  const remembered = workspaceLoadOf(workspaceKey);
  const [dismissed, setDismissed] = useState(false);
  const jobId = remembered?.jobId;
  // Followed until it is final: a load has no preview to wait for.
  const { job, error } = useFollowedJob(jobId, { done: isFinal });
  if (!remembered || dismissed) return null;

  const dismiss = (
    <button
      type="button"
      className="secondary"
      onClick={() => {
        forgetWorkspaceLoad(workspaceKey);
        setDismissed(true);
      }}
    >
      Dismiss
    </button>
  );
  const counts = job?.counts;
  const refused = counts?.rejected ?? 0;
  const openRows = (
    <button
      type="button"
      className="secondary"
      onClick={() => onNavigate({ kind: "settings", page: "jobs", jobId: remembered.jobId })}
    >
      See the rows
    </button>
  );
  if (error)
    return (
      <Notice tone="error" title={`Loading ${remembered.file}`} actions={dismiss}>
        {error}
      </Notice>
    );
  if (!job || !isFinal(job))
    return (
      <section className="fw-load" aria-label={`Loading ${remembered.file}`}>
        <p role="status">
          Loading {remembered.file}
          {job ? ` · ${count(job.progress.processed)}` : ""}
          {job?.progress.total ? ` of ${count(job.progress.total)}` : ""}
          {job ? " items" : "…"}
        </p>
      </section>
    );
  if (job.state !== "completed")
    return (
      <Notice tone="error" title={`${remembered.file} did not finish loading`} actions={dismiss}>
        {job.error?.message ?? `The load ended ${job.state}.`}
      </Notice>
    );
  return (
    <Notice
      tone={refused ? "warning" : "success"}
      title={`${remembered.file} is loaded`}
      actions={
        <>
          {refused > 0 && openRows}
          {dismiss}
        </>
      }
    >
      {counts
        ? `${count(counts.created)} created, ${count(counts.updated)} updated, ${count(counts.unchanged)} unchanged`
        : "Loaded"}
      {refused > 0 ? `; ${counted(refused, "row did", "rows did")} not load.` : "; every row loaded."}
    </Notice>
  );
}
