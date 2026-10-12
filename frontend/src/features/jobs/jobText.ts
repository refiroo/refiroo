/** How a job is named in the browser: its kind, state and result (one copy for the jobs list, the
 * job page and the notifications, U-D14). */

import type { Job } from "@/types";
import type { StatusTone } from "@/ui/StatusPill";

export const KIND: Record<Job["kind"], string> = {
  batch: "Batch",
  import: "Import",
  export: "Export",
  profile: "Profile",
  dryRun: "Dry run",
};

/** Whether a job is an export of a workbook for people (0.9 J6). */
export const forPeople = (job: Job) => job.kind === "export" && job.parameters.layout === "people";

/** A job's kind as the jobs list names it: an export of a workbook for people reads so. */
export const kindOf = (job: Job) => (forPeople(job) ? "Workbook for people" : KIND[job.kind]);

export const STATE: Record<Job["state"], { label: string; tone: StatusTone }> = {
  queued: { label: "Queued", tone: "draft" },
  running: { label: "Running", tone: "draft" },
  awaiting_confirmation: { label: "Awaiting confirmation", tone: "draft" },
  completed: { label: "Completed", tone: "success" },
  failed: { label: "Failed", tone: "error" },
  cancelled: { label: "Cancelled", tone: "neutral" },
  expired: { label: "Expired", tone: "neutral" },
};

export const RESULT: Record<NonNullable<Job["result"]>, string> = {
  applied: "Every item applied",
  partial: "Partly applied",
  rejected: "Nothing applied",
};

export const cancellable = (job: Job) => (job.state === "queued" || job.state === "running") && !job.cancelRequestedAt;

/** A file size as people read it: 5.7 KB, 209.6 MB. */
export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}
