/** The mail routes Settings › Mail reads and writes (0.12 M1): the SMTP connection and the outbox. */

import { request } from "@/api/client";
import type { MailMessagePage, MailSettings, MailSettingsUpdate, MailStatus } from "@/types";

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const mail = {
  settings: () => request<MailSettings>("/api/v1/mail-settings"),
  /** Replaces the settings; `expectedVersion` is absent for the first save. */
  saveSettings: (body: MailSettingsUpdate) => request<MailSettings>("/api/v1/mail-settings", json("PUT", body)),
  /** Mail is no longer sent; messages waiting stay and fail after 24 hours. */
  removeSettings: () => request<void>("/api/v1/mail-settings", { method: "DELETE" }),
  /** Sent at once; `422 MAIL_SEND_FAILED` names what failed in `details.kind`. */
  sendTest: (to: string) => request<{ sentTo: string }>("/api/v1/mail-settings/test", json("POST", { to })),
  /** Messages, newest first; a message's text is never answered. */
  messages: (options: { status?: MailStatus; cursor?: string } = {}) => {
    const search = new URLSearchParams({ pageSize: "50" });
    if (options.status) search.set("status", options.status);
    if (options.cursor) search.set("cursor", options.cursor);
    return request<MailMessagePage>(`/api/v1/mail-outbox?${search}`);
  },
};
