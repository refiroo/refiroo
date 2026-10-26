/** Mail settings and the outbox (0.12 M1, D419). */

import type { PageNavigation } from "@/types/runtime";

export type MailSecurity = "tls" | "starttls" | "none";
export type MailStatus = "pending" | "sent" | "failed";

export interface MailCounts {
  pending: number;
  sent: number;
  failed: number;
}

/** The SMTP connection mail is sent through; never its password. Unsaved: `configured` is false. */
export interface MailSettings {
  configured: boolean;
  host: string | null;
  port: number | null;
  security: MailSecurity | null;
  username: string | null;
  passwordSet: boolean;
  fromAddress: string | null;
  /** Where the links in mail point: the saved address, or the first browser origin. */
  applicationUrl: string;
  applicationUrlIsDefault: boolean;
  outbox: MailCounts;
  version: number | null;
  updatedAt: string | null;
}

export interface MailSettingsUpdate {
  expectedVersion?: number;
  host: string;
  port: number;
  security: MailSecurity;
  username: string | null;
  /** Write-only: omitted, the saved one is kept. */
  password?: string;
  fromAddress: string;
  applicationUrl: string | null;
}

/** Why a message or a test failed, by what failed. */
export type MailFailureKind =
  "connection" | "tls" | "login" | "recipient" | "sender" | "rejected" | "not_set_up" | "unreadable" | "expired";

export interface MailMessage {
  id: string;
  kind: string;
  to: string;
  subject: string;
  status: MailStatus;
  attempts: number;
  lastError: string | null;
  lastErrorKind: MailFailureKind | null;
  createdAt: string;
  nextAttemptAt: string | null;
  finishedAt: string | null;
}

export interface MailMessagePage extends PageNavigation {
  items: MailMessage[];
}
