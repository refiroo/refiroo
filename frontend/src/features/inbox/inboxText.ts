/** How a notice of the inbox reads and where it leads (0.12 A2): the one copy of its wording. */

import { KIND } from "@/features/jobs/jobText";
import { changeReviewFor } from "@/routing/routes";
import type { Notification, RouteState } from "@/types";

export interface NoticeText {
  title: string;
  /** The second line's parts before the time, such as the change set, the comment and who. */
  detail: string[];
}

const quoted = (name: string | undefined) => (name ? `‘${name}’` : "a change set");

/** A job kind as the jobs list names it; one the browser does not know reads as it came. */
function jobKind(notification: Notification): string {
  const kind = notification.details.jobKind ?? "";
  return (KIND as Record<string, string>)[kind] ?? (kind ? kind[0].toUpperCase() + kind.slice(1) : "Job");
}

export function noticeText(notification: Notification): NoticeText {
  const { changeSetName, comment, actor } = notification.details;
  const from = actor?.name ? [`From ${actor.name}`] : [];
  const by = actor?.name ? [`By ${actor.name}`] : [];
  const you = ["Started by you"];
  switch (notification.kind) {
    case "change-set.submitted":
      return { title: "Waiting for your approval", detail: [quoted(changeSetName), ...from] };
    case "change-set.approved":
      return { title: `Approved: ${quoted(changeSetName)}`, detail: [...(comment ? [comment] : []), ...by] };
    case "change-set.sent-back":
      return { title: `Sent back: ${quoted(changeSetName)}`, detail: [...(comment ? [comment] : []), ...by] };
    case "job.completed":
      return { title: `${jobKind(notification)} finished`, detail: you };
    case "job.failed":
      return { title: `${jobKind(notification)} failed`, detail: you };
    case "job.awaiting-confirmation":
      return { title: `${jobKind(notification)} ready to review`, detail: you };
    default:
      return { title: "Notification", detail: [] };
  }
}

/**
 * Where a notice leads: a job's page, or the review of a change set that still stands. Approval
 * publishes and deletes the change set, so that notice leads nowhere. A change set's review is an
 * application's page, which a notice does not name: the application open now, else the first.
 */
export function noticeRoute(notification: Notification, applicationKey: string | undefined): RouteState | undefined {
  if (notification.subject.kind === "job") return { kind: "settings", page: "jobs", jobId: notification.subject.id };
  if (notification.kind === "change-set.approved" || !applicationKey) return undefined;
  return changeReviewFor(applicationKey, notification.workspaceKey, notification.subject.id);
}
