/** The inbox (0.12 A2): notices of requests waiting for approval, decisions and finished jobs. */

export type NotificationKind =
  | "change-set.submitted"
  | "change-set.approved"
  | "change-set.sent-back"
  | "job.completed"
  | "job.failed"
  | "job.awaiting-confirmation";

export interface NotificationActor {
  kind: string;
  id: string;
  name: string;
}

/** What a notice is worded from; a change set's fields and a job's are never both present. */
export interface NotificationDetails {
  changeSetName?: string;
  version?: number;
  comment?: string | null;
  actor?: NotificationActor | null;
  publicationId?: string;
  jobKind?: string;
  state?: string;
}

export interface Notification {
  id: string;
  kind: NotificationKind;
  workspaceKey: string;
  subject: { kind: "change-set" | "job"; id: string };
  details: NotificationDetails;
  read: boolean;
  readAt: string | null;
  createdAt: string;
}

export interface NotificationPage {
  items: Notification[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  unreadCount: number;
}

export interface NotificationsReadResult {
  marked: number;
  unreadCount: number;
}
