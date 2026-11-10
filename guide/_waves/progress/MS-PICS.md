## 2026-11-10T13:50:37+01:00 — guide/src/content/docs/administer/mail.md

Added the three Microsoft 365 screenshots at the requested points, with captions identifying example values and unsaved forms. Updated the retry paragraph and failure-table wording without assigning a cause to retried rejections; labels checked against MailPage.tsx, mailText.ts and the supplied pictures. No steering file was present; no uncertainties for this unit.

## 2026-11-10T13:50:52+01:00 — guide/src/content/docs/run/sign-in-and-mail-setup.md

Added the managed-identity screenshot beside the explanation of the selected entry’s Entra setup fold, with an operator-focused caption. Removed the unsupported explanation for HTTP 409 in the rejected-message row, retaining that it is retried. No steering file was present; no uncertainties for this unit.

## 2026-11-10T13:51:17+01:00 — validation complete

Reviewed the final diff for both pages. GUIDE_OUT=_build/MS-PICS npm run build passed (257 pages, 3.53 seconds); npm run check passed terms and brand checks; GUIDE_OUT=_build/MS-PICS npm run check:links passed (75,806 local links and sources). The build warned about competing /404 routes. The wave wrapper and coverage command were not run because they write outside the allowed files (run reports and the shared uncovered inventory); their non-writing static/link checks ran directly. No steering file was present, no further page issues were identified, and no additional screenshots are needed.

