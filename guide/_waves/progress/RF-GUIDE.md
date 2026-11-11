
## 2026-11-11T22:38:14+01:00 — Webhook destinations

Finished `run/webhook-delivery.md`, `integrate/consumer-events-and-webhooks.md`, `administer/webhooks.md`, `guide/administer/create-a-webhook.md` and the webhook row in `run/configure.md`. Covers default refusal, the operator override, localhost HTTP, repeated DNS checks, delivery reasons and the upgrade effect; checked against `webhook_urls.py`, `webhook_client.py` and `config.py`. No steering file was present. No uncertainty in these rules.

## 2026-11-11T22:39:11+01:00 — Assistant sessions

Finished `run/ai.md` and `run/set-up-ai.md`: task-local transcripts, randomly named folders, the session-user pool and exhaustion recovery, the exact passed-variable list, Compose sandbox enforcement and the remaining credential/network limits. Checked `agent.py`, `backend/Dockerfile` and `compose.yml`; no steering file was present. These are source-verified instructions, not a new live assistant test.

## 2026-11-11T22:40:11+01:00 — Storage and upgrade pages

Finished storage corrections in `run/overview.md`, `run/backup-and-restore.md`, `run/background-jobs.md`, `run/install-with-compose.md` and `run/upgrades.md`. Removed the current shared-transcript mount, kept backup optionality precise, and added the existing-task/new-session transition, obsolete-volume cleanup and private-receiver upgrade checks. Checked Compose, Dockerfile, agent folder migration and OPERATIONS; no steering file was present. No live upgrade or volume removal was performed.

## 2026-11-11T22:40:51+01:00 — Build and proxy configuration

Finished build/proxy updates in `run/https.md`, `run/configure.md`, `run/overview.md`, `run/install-with-compose.md` and `run/upgrades.md`. Describes private forwarded-address defaults, per-surface content security policies, and how base-image, Claude Code, Python and npm pins move; checked Dockerfiles, Compose, nginx snippets and OPERATIONS. `run/developer-instance.md` already correctly leaves the host sandbox unset and was left unchanged. No steering file was present; no deployment was changed.

## 2026-11-11T22:41:26+01:00 — CSV files

Finished `guide/use/export-records.md`, `guide/use/import-a-file.md` and `use/importing-and-exporting.md`. Explains the single added quote, all triggering characters, leading-quote preservation and unchanged round trips; checked `_csv_text`, `_bind_table_layout`, `_guarded_positions` and `_unquoted`. Clarified that unquoting applies to exported layouts with no profile, not arbitrary profile imports; XLSX is unchanged. No steering file was present.

## 2026-11-11T22:41:45+01:00 — Password recovery

Finished `administer/sign-in.md`, `administer/mail.md` and `guide/administer/help-someone-who-lost-a-device.md`. Distinguishes self-requested and administrator link replacement, and explains the clean address bar and reload recovery. Checked `resets.py`, `mail/links.py` and `oauth.password_page`: the reload cookie lasts one hour even when the underlying link lasts longer, so the pages say to reopen the original link afterwards. No steering file was present.

## 2026-11-11T22:42:06+01:00 — Security checklist

Finished `run/security-checklist.md`: current forwarding defaults, per-surface policies, webhook defaults, assistant isolation and remaining limits, pinned builds and CSV protection. Reused the source checks recorded above and linked to each owning procedure. No steering file was present. This is an operator checklist, not a claim of deployment acceptance.

## 2026-11-11T22:43:09+01:00 — Final source review

Reviewed all changed passages and checked every existing screenshot reference in the assigned pages: all referenced image files exist, and no new picture is needed for these corrections. Added the actual Claude Code default version and retained the constraints file comment header without assuming its line count. No steering file was present. The first isolated build passed (257 pages, 4.42 seconds), with one `/404` route-conflict warning; final wording polish is followed by another build.

## 2026-11-11T22:43:38+01:00 — Completed validation

Final `GUIDE_OUT=_build/RF-GUIDE npm run build` passed: 257 pages in 4.26 seconds. Scoped `git diff --check` passed, and all 22 local links in added lines resolve to built pages and section IDs. All existing screenshot files referenced by the 21 assigned pages are present; no new screenshots or image references were added. The build reports a `/404` route-conflict warning; no application defect was established. Twenty content pages changed and `run/developer-instance.md` was checked and left unchanged. No application tests, live deployment, assistant session, CSV round trip or password reset were run; behavior was checked in source. No commits or Git state-changing commands were used.

## 2026-11-11T23:48:23+01:00 — Resume: assistant isolation

Finished `run/ai.md`: corrected per-turn user allocation, permission-controlled task folders, reset ordering and failure handling, init-process requirements and the third isolation limit. Checked the current `agent.py`, `refiroo-session-reset`, Dockerfile, Compose and OPERATIONS; no steering file was present. This corrects the earlier assistant description.

## 2026-11-11T23:48:42+01:00 — Setup and security follow-through

Finished `run/set-up-ai.md` and `run/security-checklist.md`: carried through per-turn users, permission gates, reset failures, init and all three limits. Added actionable reset-failure recovery using the source error message. No steering file was present; no live assistant test was run.

## 2026-11-11T23:49:14+01:00 — Upgrade follow-through

Finished `run/upgrades.md`: added per-turn users, closed idle task folders, reset and init requirements, with recovery and limits links. Checked the other assigned storage, configuration, developer and deployment pages; their current volume, host-sandbox, forwarded-address and build-pin wording remains correct and was left. No steering file was present.

## 2026-11-11T23:50:02+01:00 — Password reload clarification

Finished `administer/sign-in.md`, `administer/mail.md` and `guide/administer/help-someone-who-lost-a-device.md`: removed the earlier blanket one-hour reload limit. `ResetPasswordScreen.tsx` retains the token in history state; only the engine standalone page uses a 60-minute cookie. Both clear the address bar and support reload; the pages retain original-link recovery advice. Rechecked CSV quoting and webhook refusals against their source and left those pages as written. No steering file was present.

## 2026-11-11T23:50:44+01:00 — Resumed wave complete

Final `GUIDE_OUT=_build/RF-GUIDE npm run build` passed (257 pages); its bounded log is under `_coverage/notes/RF-GUIDE/build.log`. Scoped `git diff --check` passed, all 10 added local links resolve including section anchors, and every referenced screenshot in the 21 assigned pages exists. No new pictures are needed. The build still warns of the `/404` route conflict, outside this wave. Twenty content pages differ from HEAD; `run/developer-instance.md` was checked and left. Source checks establish the documented behavior; no live deployment, assistant, CSV or password tests were performed. No Git state-changing commands or commits were used.
