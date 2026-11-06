# C11 fresh-reader findings

This is the weaker DOC11 check: an agent reading the built guide, without browser clicks. Sources are only `guide/dist/index.html`, linked built HTML and its pictures; the wave and guide instructions, own progress/notes and steering are administrative exceptions. No source Markdown, application code, other wave notes or project documents were consulted. No pages are changed.

## Ranked outcome

- **Blocks execution:** finding 1, the assigned reference service refuses connections. This is an environment limitation, not an established documentation defect.
- **Costs time:** finding 2, a staged-correction verification step directs the reader to History that the linked page says is absent in that context; finding 3, no acquisition path for the illustrated workbook/repeat-upload exercise in the pages followed.
- **Small:** finding 4, unexplained Not Found panel in client pictures; finding 5, notification settings label mismatch and unconfigured-mail picture labelled configured.

All 8 journey pages / 56 named paths, the quick start and the production checklist received a reading check. This is not successful completion of their browser/API/operational tasks. Primary guides were followed; optional related guides were not recursively exhausted. Twelve pictures were visually inspected; the remainder received existence checks only. No fresh-reader human trial, browser interaction or production acceptance took place.

## Numbered findings

1. **Blocks live verification — environment, not a demonstrated guide defect.** `/docs/run/install-with-compose/`, step 5, health probes: substituted the assigned origin `http://localhost:8480` for the example origin and ran both `/health/live` and `/health`. Both curl requests returned connection refused (curl 7, HTTP 000). Cannot sign in or carry out subsequent live API sequences while the assigned installation is unavailable. Did not start or configure it: installation actions are prohibited by this wave. Owner notified while reading continues.

## Completed units and steps not run

### Quick start: home → What you run → Deploy to production with Docker

Read `/docs/`, `/docs/run/overview/` and `/docs/run/install-with-compose/` from beginning to end. The home page gives a direct operator route. The installation guide specifies prerequisites, expected output, private repository access, settings and secret handling, permanent origin, HTTPS, administrator creation, first sign-in, backups and upgrade/recovery. The Compose overlay warning and distinction between liveness and readiness are particularly helpful. No confirmed documentation blocker in these instructions on reading alone.

**Run:** two local health curl probes, both refused as finding 1.

**Not run:** installation steps 1–5 (tool installation/checks on the target host, DNS/firewall, clone/tag checkout, optional GitHub App, credentials/helper, settings, HTTPS and startup); step 6 (CLI administrator creation and browser sign-in/adding people); step 7 (stop, backup, restart and restore rehearsal); step 8 (upgrade). Host/install/settings changes are forbidden, and browser clicking is unavailable. Read all commands, expected responses and recovery instructions; did not execute them. No production HTTPS validation is possible against the assigned HTTP origin.

2. **Costs time — checking a staged correction sends the reader to a missing panel.** `/docs/guide/use/correct-a-record/`, “Change one value”, step 2 explicitly permits a change set; the final “See who changed what” section then says to scroll to History without changing context. I followed that route on paper and consulted its linked `/docs/use/history/`, which says the record History panel is absent inside change sets and publications, and directs readers to Review changes or Live instead. A newcomer checking the correction just staged would look for a panel the documentation says is absent. The task guide needs that context distinction at its verification step. Browser reproduction was unavailable; this is an inconsistency between built pages.

### Look after data — all 12 paths

Read `/docs/journeys/look-after-data/` and the task guides for opening an application; finding, correcting, adding and deleting records; relating records; tree browsing and single/multiple moves; restructuring; replacing related-record sets; filling a relation matrix; bulk value/relationship/deletion changes; jobs; record/workspace/personal history and identity audit. Read linked explanations of Home, workspaces, applications, records, relationships, hierarchies, mapping grids, relation matrices, bulk changes and history where needed. One large extraction was truncated; the affected record/history/hierarchy pages were reread in smaller groups. No application sources were used.

**Worked well:** list search/filter examples identify their result; selectors distinguish typing from selecting; deletion explains dependent versus surviving records; hierarchy moves distinguish parent-only moves from type changes; matrix guidance distinguishes None, Inactive, History only and Conflict, and warns about omitted columns. Error paths preserve newer work rather than telling the reader to retry blindly. Inspected `new-record-required-connections.png` and `replace-related-records.png`: fields, parent/required owner, checked set and disabled Save are legible and match their task steps.

**Not run:** every browser action in these 12 paths, including record reads, saves, creation/deletion, connection changes, moves, restructuring, matrix edits, bulk jobs and history inspection (no browser clicking permitted). Restructuring’s final publish is also forbidden in `graubuenden`. Judged from words and selected pictures only; remaining pictures were inventoried from HTML but not visually inspected. No claim of end-to-end task completion. Finding 2 affects the staged-correction verification route. The generic instructions otherwise let a reader choose an appropriate collection/type; they do not provide a single fixed exercise state for every action.

### Change with approval — all 6 paths

Read `/docs/journeys/change-with-approval/`; all linked task guides for preparation/publication, concurrent Live work, browsing/withdrawing publications, starting from history, review, preparing under a different model release, proposing and approval; and the built Change sets, Publications and Inbox and approvals explanations.

**Worked well:** the approval guide takes both people through submission, second-person refusal, send-back, correction, resubmission, publication and notices. The pictures `appr-own-approval.png` and `appr-decision-panel.png` visibly distinguish the submitter's missing decision panel from the approver's controls. Withdrawal, discarding and rollback are carefully distinguished; the concurrent-work guide explicitly says there is no automatic rebase and gives a new-change-set recovery route. No new blocker found on this reading.

**Not run:** all browser actions: starting/editing/reviewing/validating proposals, concurrent corrections, submission/withdrawal/send-back/resubmission, publication browsing/withdrawal, choosing/changing releases, conversion previews and migrations. No browser clicking is available; publishing/approval-and-publish or model activation in `graubuenden` is forbidden independently. Second-person work also requires a second account; no impersonation or account creation attempted. Only the two named pictures were inspected visually for this unit.

### Work with an assistant — all 8 paths

Read `/docs/journeys/work-with-an-assistant/` and the linked guides for provider checks, mapping proposals, workbook/words-only tasks, continuing/correcting tasks, model/workbook proposal review, connecting an external assistant, asking a list and explaining history. Read the built AI and your data and Assistants and agents explanations, including the read/paging tools and change-preparation sequence.

**Worked well:** distinguishes provider, built-in Claude Code and external MCP; explains data leaving the instance, paid calls and retention before actions. Words-only changes include a concrete stop/field/value request and distinguish Accept from Accept the model. Recovery warns that reload discards hand edits. Inspected `use-assistant-words.png` (No change to the model, Accept and correction input are visible) and `use-ask-filters.png` (the Height (m) at least 1000 pill and a 1,657-record total are visible). The written error/partial-answer route preserves the earlier list until the reader explicitly accepts supported filters. No new blocker found on reading.

**Not run:** all browser actions and all provider/assistant calls, including test request, proposal jobs, workbook upload, Accept/load/reload, Ask, explanation, MCP client registration/sign-in/tools/revocation and reviewing/publishing its changes. Browser clicking is unavailable; the assigned service was unavailable; enabling/configuring providers or agent access would change settings and is forbidden. No external AI request or billed task was initiated. The `claude mcp add` command was read only: it would change a local assistant configuration. Activation/publication and whole-type live migration confirmations were read, not executed. Most screenshots were not visually inspected beyond the two named above.

3. **Costs time — the workbook example cannot be reproduced from the reading path.** `/docs/journeys/shape-a-model/`, “Onboard a workbook”, then `/docs/guide/model/start-a-draft-from-a-workbook/`, “Start the draft”, step 2. The guide asks me to choose a workbook and captions name `Haltestellen_Busbetrieb_Nord.xlsx`; I looked for a way to obtain that example in the task guide, its linked Workbook onboarding page and The example data page. None of those pages supplies a download link or instructions to create that workbook (nor a subsequent-version file for the next-upload exercise). I could bring my own file, but could not reproduce the illustrated sources, counts and known refusals using the built guide alone. This is a reproducibility gap for a newcomer tutorial, rather than a claim that uploading one's own workbook fails. I did not inspect repository samples to bridge it.

### Shape a model — all 10 paths

Read `/docs/journeys/shape-a-model/` and its guides for creating drafts, install/activation, comparing/exporting releases, workspace creation/default/retirement/deletion, consumer declaration/documents, editor history, workbook onboarding/column mapping/list ranges/dry run/load/repeat upload, workspace model edit/switch/migration, cross-model copy/move and model-change explanations. Read the editor and the linked Models, Releases, Managing workspaces, Workbook onboarding, Migrations and Model mappings explanations; followed editor links for adding types/fields, relationships and applications/views. Reopened the editor and workbook explanation separately where an earlier combined extraction was truncated. Other editor capabilities linked as optional side tasks were not all read recursively.

**Worked well:** distinguishes drafts, release versions, activation and record publication. Load instructions report earlier stages that may have succeeded before a later failure. Copy/move explicitly puts target publication before source deletion. Preview loss and blockers are visible in `model-migration-loss-confirm.png`, which I inspected: three blockers, 8,921 removed items and disabled migration. `use-wb-dialog.png` clearly shows four proposal choices, comparison workspace and starting release. The workbook guide accounts for refused rows separately from successful loading. These two pictures support the text; most others were not visually inspected.

**Not run:** every browser step in these 10 paths, including draft/editor writes, validation, generated-document downloads, release installation/activation, workspace administration, workbook upload and dry runs, loads, profile reuse, migration previews/confirmations, copy/move and publication. Browser clicks are unavailable; settings changes and activation/publication in `graubuenden` are prohibited. Example workbook acquisition is additionally blocked as finding 3. Provider-written model explanations were not requested. No records, models or workspaces were changed.

### Integrate a system — all 11 paths

Read `/docs/journeys/integrate-a-system/` and its primary task guides for tokens, complete/resumable reads, business dates, bounded batches, initial load/change feed, supplier files, consumer object/list reads, resolution and webhook subscription/verification. Read the linked authentication/discovery/API-reference and consumer-contract/object/lookup/event explanations, including complete reference request/response examples. The large combined consumer-page output was truncated; lookup was reread separately with its final response and outcomes visible. This is a sequence review; runtime management operation schemas at `/docs/api` could not be inspected because the service is unavailable and there is no static `guide/dist/api/index.html`. The guide explicitly explains that the engine serves that reference, so this is not recorded as a broken static-page defect.

**Worked well:** consumer examples explicitly distinguish a bare object, list `items`, lookup `results` and ordered resolution outcomes. They show an actual found/not-found pair, typed values and decimal string encoding. Snapshot and business date are separate; cursors and ETags must come from the reader's own response. Events distinguish `position` from `stateAt` and require a lasting cursor even on sparse pages. Webhook recovery explains reset before baseline rebuilding.

**Run locally:** copied the public webhook request and Python verifier from the built HTML's Copy-button content. The 516-byte sample verifies with `guide-example-only` and its displayed clock; a changed byte and a stale clock are rejected; a valid second comma-separated signature is accepted; Content-Length matches. See `webhook-check.md`. Initial extraction errors were in my HTML reader (line boundaries), corrected without editing the example. These checks do not prove live delivery or rotation.

**Not run:** credential exchange, caller/capability/model discovery, management paging/filter/date reads, inline/background batch execution/preview/confirmation/cancellation/replay, export baseline/download/change-feed recovery, file preview/import/export/retry, consumer index/OpenAPI/object/list/conditional GET/XREF/resolve/publication/event reads and full cursor traversal. The assigned service refuses connections; another health attempt here still returned curl 7, HTTP 000. Administrator credentials were not read because there was no reachable sign-in service; no secrets or tokens were written or printed. Client creation/grants, webhook subscription/signing-key rotation/reset/manual resend and receiver deployment were also not run: they need settings changes or external installation. The webhook guide's illustrative name-change/publish test was not run. Browser import/export/Excel round-trip and job inspection were read as alternatives, not clicked. No live API sequence can be claimed complete.

4. **Small — client screenshots retain an unexplained failed panel.** `/docs/guide/administer/create-a-client/`, “Grant access”, screenshot `admin-client.png`; also visible in `admin-client-rotate.png` on `/docs/guide/administer/rotate-a-client-secret/`. The latter picture, inspected directly, shows “Webhooks it created” → “Could not load this content” → “Not Found” with Retry behind the rotation dialog. The creation guide correctly calls it a load error, but supplies no explanation of whether this is an expected disabled feature or a problem needing attention. It distracts from proving the new client's state. This is a screenshot anomaly, not a live-reproduced application defect.

### Manage access — all 5 paths

Read `/docs/journeys/manage-access/` and its sign-in/account, person/group, grants and narrowed writes, client/consumer grants, secret/signing-key/webhook rotation, lost-device help and security-checklist routes. Reused the token guide and authentication reading from the integration unit. Inspected `admin-grant-narrowed.png` and `admin-client-rotate.png`: the one-workspace/one-role choice and “Reading is never narrowed” warning are visible, as are rotation overlap choices.

**Worked well:** new people and clients start with no access; effective grants combine rather than subtract. Narrowing writes never promises hidden records. Secret rotation explicitly verifies fresh authentication and distinguishes it from token-signing-key rotation. Normal Start a new key acts immediately, clearly stated before the action. Recovery keeps the last administrator and second-factor constraints visible. Finding 4 is the only new concern.

**Run:** unauthenticated local root HEAD, `/metrics` and `/api/v1/workspaces` curl requests from the linked security checklist, adapted to the assigned HTTP origin; all refused connections (curl 7), so no header, metrics-isolation or authentication-boundary assertion passed.

**Not run:** all sign-in/account/device/passkey/TOTP/recovery/session actions; people/groups/roles/grants/client creation and deactivation; permitted/refused client operations; credential rotations/overlap expiry; provider setup and narrow-access browser checks. Browser clicking is unavailable, service unreachable and installation settings must not change. `docker compose ps` was not run as this wave's installation commands are prohibited; no production HTTPS or network boundary was tested. No mail/password link or secret was created or used.

### Run the service — both paths

Read `/docs/journeys/run-the-service/` and the full built database, configuration, health/startup, troubleshooting, monitoring, backup/restore, upgrade, several-process and licence/source pages; reused the quick start. Also read Background jobs for the recovery handoff. No source code, host settings or project documents were consulted.

**Worked well:** distinguishes initial maintenance refusal (repair then restart) from a running database outage (repair connectivity, workers recover). Overall readiness can hide one failed workspace, so Operations is part of the check. Backup pairs database and files while writers are stopped, uses a separate scratch restore, records bounded evidence, and preserves the original host during recovery. Configuration explains recreation versus restart and read-only Deployment settings. No new documentation blocker found on reading.

**Not run:** installation, Docker/SQL/database inspection, startup/refusal injection, stopping/recreating workers, configuration edits, metrics-client/scraper setup, backup/archive/copy/restore/rehearsal/cleanup, database/model upgrades, interruption tests, production sign-in, workspace Operations, file download or source publication. Installation/host/settings commands are forbidden and browser clicks unavailable. Health requests already failed in finding 1; no new state change was attempted to repair the assigned environment. Did not intentionally break a database or installation to exercise recovery. Operations and backup screenshots were identified in HTML, not visually inspected in this unit.

5. **Small — operator mail guidance names a different settings destination.** `/docs/run/sign-in-and-mail-setup/`, “Inbox mail and digests”, first paragraph says people choose preferences in `Settings › Notifications`. Following its Notifications link actually opens `/docs/use/notifications-settings/`, which says `Settings › Notification email`. The linked page resolves the ambiguity, but a newcomer looking for the named settings entry can lose time. Its mail picture's alt text also calls the SMTP server configured, while the same `admin-mail-settings.png` shows “Mail is not set up”, blank fields and a disabled test. No configured-mail or delivered-digest picture is provided on these routes.

### Receive notices — both paths

Read `/docs/journeys/receive-notices/`, Mail, Set up mail, operator sign-in/mail setup, Notification settings, Set up email notices and Follow a workspace. Reused the inbox/approval and Account reading. Inspected `admin-mail-settings.png` and `notification-email-digest.png`: both depict unavailable prerequisites, rather than a configured/delivered example. This bounds visual evidence but the text supplies the missing steps.

**Worked well:** SMTP acceptance is distinguished from actual mailbox receipt. Password-link mail, inbox notices and personal email preferences remain separate. Digests explain the fixed 07:00 local-time schedule, no empty message, last 50 entries, unread/handled eligibility and no 24-hour cutoff. Following another person's publication works without mail and retains its choice across lost access. Finding 5 is a small navigation/caption inconsistency.

**Not run:** SMTP settings/save/test, actual mailbox/link receipt, queue/retry/stop/removal, password reset, email preference saves, daily/weekly digest delivery, following/unfollowing and another person's publication/notice. These require browser clicks, settings changes, mail infrastructure or publication; none is available/permitted in this wave. No messages were sent to anyone. Did not change the clock or installation to manufacture a digest. The operator OAuth-metadata curl is a read and remains to be tried in the final checklist unit; credential curl requires a client that this wave must not create.

### Production checklist — all 12 opening items and 5 execution groups

Read `/docs/run/production-checklist/` from start through the evidence table and traffic-opening decision. Followed the HTTPS, secrets and webhook-delivery owning pages in full and reused the already read database, configuration, access, mail, monitoring, storage, backup and upgrade routes.

**Worked well:** names prerequisites and actual outcomes rather than relying on a healthy container. It separates traffic readiness from each workspace's state, database rehearsal from file/public-sign-in recovery, and persistence from capacity. It says to keep failed evidence, repeat the affected checks and leave writers closed after failure. No new documentation blocker found on reading.

**Run/attempted:** assigned-origin health probes, public root HEAD, public metrics and unauthenticated workspace request are recorded above; OAuth metadata was also attempted here and refused (curl 7). No TLS or response-body claim is possible from HTTP 000. The public demonstration webhook verifier passed offline; it does not replace real receiver verification.

**Not run, by checklist group:**

1. Compose validation/state and public HTTP→HTTPS redirect/TLS/headers/health/metrics assertions: no installation commands, no public HTTPS target, local endpoint unreachable.
2. SQL version/collation/extensions/revision, Deployment values and every workspace/process on Operations: no Docker/SQL installation inspection or browser clicking; service unavailable.
3. Local/provider/test-person/second-factor/recovery access tests, mail/reset delivery and digest timing: browser work, settings changes and mail prerequisites unavailable/prohibited.
4. Storage checks, workbook preview/import, export/download across restart, lease takeover, webhook change/delivery/deduplication: requires installation commands, live service, browser or configuration changes; publication/activation in `graubuenden` forbidden. Only offline sample signature behavior was exercised.
5. Real private metrics scrape, correlated logs/alerts, consistent backup, database/file restore, rehearsal and replacement-host sign-in: infrastructure/host operations forbidden and no suitable production boundary supplied.

**Decision:** production acceptance was not attempted and cannot be inferred from this weaker reading check. No changes were made to the installation or to guide pages.

## Final validation and scope

- `GUIDE_OUT=_build/C11-READER npm run build` in `guide/`: **passed**, exit 0, 247 pages, reported 3.86 seconds. Output retained as `build.log` under this wave's notes. Did not run a plain build or replace `guide/dist/`.
- Built-guide link/reference check: **passed**, 182 selected pages (home, quick start, checklist and journey roots plus their immediate content links), 2,369 static links and 213 distinct picture references; no missing static pages, anchors or referenced pictures. Runtime API links (137 occurrences) excluded, external destinations not fetched. This is a mechanical check and does not mean every selected page or picture was read/visually inspected. Evidence: `link-check.json`; script: `check_links.py`.
- Offline webhook demonstration: **passed**, five recorded checks; no real signing credential, delivery or endpoint used. Evidence: `webhook-check.md`.
- Live checks: local liveness/readiness, root HEAD, metrics, unauthenticated workspace collection and OAuth metadata all refused connections. No HTTP response was obtained. No administrator credential lines were needed/read. The owner was notified; service was not repaired or started by this wave.
- Writes confined to this wave's notes/progress and the explicitly requested isolated build output (plus build-managed generated artifacts). No page/source/configuration edits, commits or state-changing git commands. No servers, database clones or background services were started; the build process exited.
- Steering file was absent before every unit and before this final record. No steering corrections were received/applied.

The per-unit entries above are the detailed list of steps not run and their reasons. No confirmed runtime application defect is claimed; the client picture's failed panel is evidence to investigate, not a reproduced current failure.
