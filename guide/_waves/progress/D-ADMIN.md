# D-ADMIN progress

- 2026-11-07T15:29:08+01:00 — Finished `administer/permissions-reference.md`; linked it from the sidebar and roles page. Covers every action group, its actions and predefined roles, job permissions, hidden controls and the assistant ceiling. No D-ADMIN steering file exists.

- 2026-11-07T15:29:51+01:00 — Finished `administer/people-and-groups.md` and `guide/administer/link-a-provider-person.md`; reviewed add-person and manage-group guides. Added unlink consequences, membership failure recovery and deletion/restore limits. No steering file present.

- 2026-11-07T15:30:25+01:00 — Finished `administer/sign-in.md` and `guide/administer/require-a-second-factor.md`; reviewed all four sign-in/recovery guides. Added credential replacement, exact refusal recovery and existing-session effects. Provider-specific credential lifetime is set outside refiroo. No steering file present.

- 2026-11-07T15:30:57+01:00 — Finished `administer/clients.md`, `guide/administer/rotate-a-client-secret.md` and `administer/signing-keys.md`; reviewed their remaining guides. Added renewal ownership, repeated-rotation effects and restore boundaries. No steering file present.

- 2026-11-07T15:31:38+01:00 — Finished `administer/approval-policies.md` and `guide/administer/set-an-approval-policy.md`; reviewed audit and find-author pages. Clarified current policy on waiting work, retained history and that a submitter cannot send back their own work under the second-person rule. No steering file present.

- 2026-11-07T15:32:08+01:00 — Finished `administer/mail.md` and `guide/administer/set-up-mail.md`. Added the exact test headings and save refusals, credential replacement and recovery of links queued before a site-address change. No steering file present.

- 2026-11-07T15:33:09+01:00 — Finished `administer/webhooks.md` and `guide/administer/rotate-a-webhook-key.md`; reviewed create/paused guides. Added edit effects, exact format names, destination limits and repeated-key rotation. Found no browser creation choice for Workspace events subscriptions; recorded that limitation with source references. No steering file present.

- 2026-11-07T15:34:27+01:00 — Finished `administer/ai.md`, `administer/agent-access.md` and `guide/administer/manage-agent-access.md`; reviewed provider-check guide. Added shutoff/restore limits and corrected registration expiry and call-error visibility. Recorded the Values display mismatch as a product defect. No steering file present.

- 2026-11-07T15:35:13+01:00 — Finished `administer/jobs-and-limits.md` and `administer/deployment-pages.md`; reviewed API reference/Consumer APIs. Corrected cancellation labels and clarified that expired jobs keep summaries while details/files expire. Added earlier rehearsal and refresh-failure guidance. No steering file present.

- 2026-11-07T15:36:05+01:00 — Finished the inventory mapping in `_waves/coverage/administer.md`, per-page depth ledger and `_waves/screens-wanted/D-ADMIN.md`. All 172 current administer inventory entries have homes; no new exclusions or missing screenshot files. Proceeding to isolated build and checks. No steering file present.

- 2026-11-07T15:38:04+01:00 — Final review corrected `administer/clients.md` and `guide/administer/rotate-a-client-secret.md`: inactive clients have no browser rotation button, and restoring can permit still-unexpired earlier access. The procedure now keeps compromised clients inactive and hands replacement to the integration owner. First isolated verify passed; all 62 permissions, 11 screens and 99 management operations are covered. No steering file present.

- 2026-11-07T15:39:22+01:00 — Completed D-ADMIN. Final `GUIDE_OUT=_build/D-ADMIN npm run verify` passed (248 pages; 70,269 links/sources); coverage is 172/172 for administer, with 113 unrelated global gaps. Saved `_coverage/notes/D-ADMIN/report.md` with per-page word counts, source-backed screen gaps and verification limits. No screenshots requested and no steering file present.
