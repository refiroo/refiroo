/** How a notice of the inbox reads and where it leads (0.12 A2): the one copy of its wording. */

import { KIND } from "@/features/jobs/jobText";
import { changeReviewFor } from "@/routing/routes";
import type { Notification, NotificationKind, RouteState } from "@/types";

export interface NoticeText {
  title: string;
  /** The second line's parts before the time, such as the change set, the comment and who. */
  detail: string[];
}

/** Each kind of notice in the engine's words (`engine/notifications/kinds.py`), for the Kind filter. */
export const KIND_LABELS: Record<NotificationKind, string> = {
  "change-set.submitted": "A change set is waiting for your approval",
  "change-set.approved": "A change set you submitted was approved",
  "change-set.sent-back": "A change set you submitted was sent back",
  "job.completed": "A job you started has finished",
  "job.failed": "A job you started has failed",
  "job.awaiting-confirmation": "A job you started is waiting for your confirmation",
  "change-set.published": "A change set was published in a workspace you follow",
};

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
    case "change-set.published":
      return { title: `Published: ${quoted(changeSetName)}`, detail: [...by] };
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
  // A publication consumed its change set: an approval and a followed publication lead nowhere.
  if (notification.kind === "change-set.approved" || notification.kind === "change-set.published" || !applicationKey) {
    return undefined;
  }
  return changeReviewFor(applicationKey, notification.workspaceKey, notification.subject.id);
}
