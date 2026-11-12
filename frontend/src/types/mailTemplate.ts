/** The e-mail template an operator edits (Settings › E-mail template): Markdown with placeholders and a logo. */

/** The template as `GET /mail-template` answers it; without a saved one `saved` is false and `markdown` is the default. */
export interface MailTemplate {
  markdown: string;
  defaultMarkdown: string;
  saved: boolean;
  /** The placeholders a template may use; `content` is required exactly once. */
  placeholders: string[];
  logoType: "image/png" | "image/jpeg" | "image/svg+xml" | null;
  /** The uploaded logo as a data URL, for a thumbnail. */
  logoDataUrl: string | null;
  logoMaxBytes: number;
  version: number | null;
  updatedAt: string | null;
}

/** A draft rendered around a sample message with sample values: nothing was saved or sent. */
export interface MailTemplatePreview {
  html: string;
  text: string;
}
