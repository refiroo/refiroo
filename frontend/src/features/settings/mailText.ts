/** Words for Settings › Mail (0.12 M1): the security choices, a message's state and a failure. */

import type { MailFailureKind, MailMessage, MailSecurity, MailStatus } from "@/types";
import type { StatusTone } from "@/ui/StatusPill";

/** How the connection is secured, with the port that usually goes with it. */
export const MAIL_SECURITY: readonly { value: MailSecurity; label: string; port: number }[] = [
  { value: "starttls", label: "STARTTLS (usually port 587)", port: 587 },
  { value: "tls", label: "TLS (usually port 465)", port: 465 },
  { value: "none", label: "None: not encrypted (a relay on a trusted network)", port: 25 },
];

export const portFor = (security: MailSecurity) => MAIL_SECURITY.find((item) => item.value === security)!.port;

export const MESSAGE_STATE: Record<MailStatus, { label: string; tone: StatusTone }> = {
  pending: { label: "Waiting", tone: "warning" },
  sent: { label: "Sent", tone: "success" },
  failed: { label: "Failed", tone: "error" },
};

const MESSAGE_KIND: Record<string, string> = {
  activation: "Account link",
  "password-reset": "Password reset",
  notification: "Inbox notice",
};

export const messageKind = (message: Pick<MailMessage, "kind">) => MESSAGE_KIND[message.kind] ?? message.kind;

/** What a failed test message says went wrong, as a heading above the server's own sentence. */
const FAILURE_TITLE: Partial<Record<MailFailureKind, string>> = {
  connection: "The server could not be reached",
  tls: "The secure connection failed",
  login: "The login was refused",
  recipient: "The server refused the address",
  sender: "The server refused the from address",
  rejected: "The server did not accept the message",
};

export const failureTitle = (kind: unknown) =>
  (typeof kind === "string" && FAILURE_TITLE[kind as MailFailureKind]) || "The test message was not sent";
