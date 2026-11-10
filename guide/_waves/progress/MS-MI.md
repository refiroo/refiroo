
- 2026-11-10T11:45:17+01:00 — Finished `guide/src/content/docs/administer/mail.md`: documented the four Sign in with choices, conditional fields, folded sections, credential replacement and managed identity refusals. No MS-MI steering file was present; preserved the existing screenshot, Sent Items, bounces, retries and removal text.

- 2026-11-10T11:46:14+01:00 — Finished `guide/src/content/docs/run/sign-in-and-mail-setup.md`: added same-tenant and hosted-tenant identity setup, copied role-assignment commands and federated credential JSON/placeholders from Operations, explained host token discovery, storage, cloud audiences and AKS limits, and extended refusals. No MS-MI steering file was present; preserved existing examples. Azure/Entra commands were checked against repository instructions, not run against a live tenant.

- 2026-11-10T11:47:18+01:00 — Finished review and validation of both assigned pages; `GUIDE_OUT=_build/MS-MI npm run build`, terms/brand checks and built-site links all passed. Recorded source evidence, seven shared screenshot requests, the stale Operations labels and preserved unknown-mailbox retry contradiction in `guide/_coverage/notes/MS-MI/report.md`; no MS-MI steering file was present.

- 2026-11-10T11:48:40+01:00 — Applied the user’s mailbox-not-found correction to `guide/src/content/docs/administer/mail.md`: the retry paragraph and sender-refusal row now say the message waits and retries as with SMTP, with correction, save and test before its 24-hour window ends. No MS-MI steering file was present.

- 2026-11-10T11:48:40+01:00 — Applied the same correction to `guide/src/content/docs/run/sign-in-and-mail-setup.md`, in the Microsoft 365 sender row and the Microsoft 365 has no mailbox diagnostic row; removed the instruction to repeat the original task. The rejected row still correctly distinguishes immediate failure from retryable HTTP 409; the user reports Operations labels corrected, superseding the earlier mismatch note. No MS-MI steering file was present.

- 2026-11-10T11:48:52+01:00 — Validated the corrections: targeted search confirms all four passages describe retryable mailbox-not-found behavior; scoped `git diff --check` passed and `GUIDE_OUT=_build/MS-MI npm run build` passed (257 pages). Only the two assigned pages and this progress file were edited; existing screenshots and examples are unchanged.
