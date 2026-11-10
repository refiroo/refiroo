/** Mail settings and the outbox (0.12 M1, D419). */

import type { PageNavigation } from "@/types/runtime";

export type MailSecurity = "tls" | "starttls" | "none";
export type MailStatus = "pending" | "sent" | "failed";

export interface MailCounts {
  pending: number;
  sent: number;
  failed: number;
}

export type MailMethod = "smtp" | "microsoft365";
/** Microsoft 365's credential (0.13 MS-D5): a client secret, a certificate or a managed identity. */
export type MailCredential = "secret" | "certificate" | "managedIdentity";
/** A managed identity in the organisation's tenant, or as an app's federated credential. */
export type MailIdentityMode = "direct" | "federated";

/** How mail is sent (0.13 MS: SMTP or Microsoft 365); never a password, secret or certificate.
 * Unsaved: `configured` is false and `method` is null. */
export interface MailSettings {
  configured: boolean;
  method: MailMethod | null;
  host: string | null;
  port: number | null;
  security: MailSecurity | null;
  username: string | null;
  passwordSet: boolean;
  /** Microsoft 365 only. */
  credential: MailCredential | null;
  identityMode: MailIdentityMode | null;
  /** The user-assigned identity's client ID; null for the host's system-assigned one. */
  identityClientId: string | null;
  tenantId: string | null;
  clientId: string | null;
  clientSecretSet: boolean;
  /** The saved certificate's SHA-1 thumbprint and expiry; null with a client secret. */
  certificateThumbprint: string | null;
  certificateExpiresAt: string | null;
  /** Where Microsoft issues tokens and the Graph address: the defaults unless changed. */
  authorityUrl: string | null;
  graphUrl: string | null;
  /** With Microsoft 365 the sending mailbox. */
  fromAddress: string | null;
  /** Where the links in mail point: the saved address, or the first browser origin. */
  applicationUrl: string;
  applicationUrlIsDefault: boolean;
  outbox: MailCounts;
  version: number | null;
  updatedAt: string | null;
}

/** One method's fields only: the engine refuses the other's, and replaces them on a switch. */
export type MailSettingsUpdate = {
  expectedVersion?: number;
  fromAddress: string;
  applicationUrl: string | null;
} & (
  | {
      method: "smtp";
      host: string;
      port: number;
      security: MailSecurity;
      username: string | null;
      /** Write-only: omitted, the saved one is kept. */
      password?: string;
    }
  | {
      method: "microsoft365";
      /** Not sent with a direct managed identity. */
      tenantId?: string;
      clientId?: string;
      /** Write-only; one of the two, omitted: the saved credential is kept. */
      clientSecret?: string;
      certificate?: string;
      /** A managed identity stores no secret: send these instead of a secret or certificate. */
      identityMode?: MailIdentityMode;
      identityClientId?: string;
      authorityUrl?: string;
      graphUrl?: string;
    }
);

/** Why a message or a test failed, by what failed. */
export type MailFailureKind =
  | "connection"
  | "tls"
  | "login"
  | "recipient"
  | "sender"
  | "rejected"
  | "not_set_up"
  | "unreadable"
  | "expired"
  | "stopped";

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
