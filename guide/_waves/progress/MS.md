## 2026-11-10T11:08:46+01:00 — administer/mail.md

Finished `guide/src/content/docs/administer/mail.md`: added the Microsoft 365 method, Entra preparation, form fields, sealed credentials, renewal, Sent Items and bounces, and extended the existing failure table. Checked form labels and mail settings/Graph/sender code; HTTP 409 is retried despite the wave’s blanket statement about other refusals. No steer file existed; no corrections to apply.

## 2026-11-10T11:09:57+01:00 — run/sign-in-and-mail-setup.md

Finished `guide/src/content/docs/run/sign-in-and-mail-setup.md`: added full Entra preparation, national-cloud addresses, credential storage/resealing and renewal, plus refusal kinds and safe diagnostics. Existing sign-in and SMTP examples are unchanged; the source supports HTTP 409 retries, so the operator table names that exception. No steer file existed; no corrections to apply.

## 2026-11-10T11:11:06+01:00 — final checks and evidence

Completed checks for both pages: `GUIDE_OUT=_build/MS npm run build` passed (257 pages, 3.51 s; /404 route conflict warning), static terms/brand checks and built-site links passed, and the scoped diff has no whitespace errors. Existing code examples and screenshot references are unchanged; evidence, retained passages, missing Microsoft 365 form/certificate pictures and the HTTP 409 exception are recorded in `guide/_coverage/notes/MS/checks.md`. No steer file existed; no corrections to apply. No live Microsoft tenant or mail delivery was tested.

