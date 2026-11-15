/** The e-mail template routes Settings › E-mail template reads and writes. */

import { json, request } from "@/api/client";
import type { MailTemplate, MailTemplatePreview } from "@/types";

export const mailTemplate = {
  get: () => request<MailTemplate>("/api/v1/mail-template"),
  /** Saves the Markdown; `expectedVersion` is absent for the first save. `422 MAIL_TEMPLATE_*` names what is wrong. */
  save: (markdown: string, expectedVersion: number | null) =>
    request<MailTemplate>("/api/v1/mail-template", json("PUT", { markdown, expectedVersion })),
  /** Back to the default: the saved Markdown and the logo are deleted. */
  reset: () => request<void>("/api/v1/mail-template", { method: "DELETE" }),
  /** A PNG, JPEG or SVG image; `422 MAIL_LOGO_UNSUPPORTED`, `422 MAIL_LOGO_UNSAFE`, `413 MAIL_LOGO_TOO_LARGE`. */
  uploadLogo: (file: File, expectedVersion: number | null) => {
    const form = new FormData();
    form.append("file", file);
    if (expectedVersion !== null) form.append("expectedVersion", String(expectedVersion));
    return request<MailTemplate>("/api/v1/mail-template/logo", { method: "PUT", body: form });
  },
  removeLogo: (expectedVersion: number | null) => {
    const search = expectedVersion === null ? "" : `?expectedVersion=${expectedVersion}`;
    return request<MailTemplate>(`/api/v1/mail-template/logo${search}`, { method: "DELETE" });
  },
  /** Renders a draft with sample values; nothing is saved. Aborted by `signal`. */
  preview: (markdown: string, signal?: AbortSignal) =>
    request<MailTemplatePreview>("/api/v1/mail-template/preview", { ...json("POST", { markdown }), signal }),
  /** Mails the saved template to the caller's own address. */
  sendTest: () => request<{ sentTo: string }>("/api/v1/mail-template/test", json("POST", {})),
};
