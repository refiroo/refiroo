# C5-RUN report

Audited all 21 non-AI operator pages. Updated 17 existing pages; no new page was needed.
The existing sidebar registers all 23 run pages, including the two excluded AI pages, in the
required groups, so it was left unchanged. No commits or state-changing git commands were run.

## Pages changed

- `guide/src/content/docs/run/overview.md`
- `guide/src/content/docs/run/install-with-compose.md`
- `guide/src/content/docs/run/developer-instance.md`
- `guide/src/content/docs/run/database.md`
- `guide/src/content/docs/run/several-processes.md`
- `guide/src/content/docs/run/configure.md`
- `guide/src/content/docs/run/sign-in-and-mail-setup.md`
- `guide/src/content/docs/run/health-and-startup-checks.md`
- `guide/src/content/docs/run/monitoring.md`
- `guide/src/content/docs/run/background-jobs.md`
- `guide/src/content/docs/run/webhook-delivery.md`
- `guide/src/content/docs/run/command-line.md`
- `guide/src/content/docs/run/troubleshooting.md`
- `guide/src/content/docs/run/backup-and-restore.md`
- `guide/src/content/docs/run/upgrades.md`
- `guide/src/content/docs/run/model-releases-and-rollback.md`
- `guide/src/content/docs/run/security-checklist.md`

Checked without changes: `https.md`, `secrets-and-keys.md`, `licence-and-source.md` and
`production-checklist.md`. The two AI pages were not edited.

Changes correct image paths and Compose recovery configuration, add About/Deployment/Operations
fields and states, explain failure-policy and lease recovery, complete mail and digest operation,
cover webhook logs and resends, distinguish session/provider cookies, and add startup and
pinned-model recovery. The CLI catalogue now warns that database preparation can migrate even
before a release dry-run. Removed the run section's links to two unwritten administrator guides.

## Coverage

All 254 rows reconciled: **150 covered**, **36 not for readers**, **68 after 0.16**.
No empty, partial or uncovered entries remain. Existing 58 AI deferrals were retained; ten wrongly
routed AI screen/assistant/summary/provenance items were classified as deferred after checking their
cited evidence. One provider-test-strategy item was excluded as internal. Exact row destinations
and reasons are in `coverage-resolution.json`. The ledger's relative page links were corrected and
all resolve. No other section's ledger or pages were edited.

## Screens

All four required requests are in `guide/_waves/screens-wanted/C5-RUN.md`:

- `run-jobs`: still missing; Jobs list showing states and the workspace/item/requester/date columns.
- `run-deployment`: now supplied and inspected. Shows the intended settings, but the reference
  instance uses older image paths; the page caption distinguishes them from current defaults.
  A refreshed capture of the current image would remove that discrepancy.
- `run-operations`: now supplied and inspected; shows workspace and expanded process state.
  An uncropped footer including Metrics would complete the requested monitoring addresses.
- `run-backup-rehearsal`: now supplied and inspected, but shows **No backup has been rehearsed**.
  Page alt text now matches. The requested **Passed** result with restored workspace counts is
  still outstanding and needs a replacement capture plus matching alt text.

## Validation

`GUIDE_OUT=_build/C5-RUN npm run verify` ran after the final page edits.

- Build **passed**: 200 pages, 2.89 seconds; the shared `dist` directory was not used for this build.
- Terms and brand **passed** across 199 content pages.
- Link check **failed** with 20 missing targets: one in Run (`run-jobs.png`), and 19 outside this
  wave (other screenshots plus two links to the unwritten administrator Webhooks page).
  Those outside targets cannot be fixed within this assignment's allowed files.
- Checked 254 unique ledger IDs and resolvable destinations, 23 sidebar registrations, operator
  front matter on all 21 assigned pages, and all Run Markdown page-link destinations.

The exact output is in `verify-final.log`. The full verify command is therefore **not green**.
Concurrent screenshot work reduced missing targets between checks; counts above are the final
build snapshot. No operational commands, migration, restore, deployment image build or live
installation check was executed. The procedures were checked against source, not runtime-tested.

## Issues and uncertainty

- `backend/Dockerfile` copies the guide configuration but does not copy `guide/sidebar/`, which
  the configuration imports. This appears to block its guide/image build; not reproduced because
  image builds and code edits are outside this documentation task. Report to the deployment owner.
- The excluded AI pages still mention `/data/assistant` and `/data/assistant-claude`, while the
  current Dockerfile uses `/opt/refiroo/rdm-engine/data/...`. Left unchanged for the AI wave.
- The supplied reference screenshots reflect an older running image. Current image defaults are
  documented from the repository code. Successful restore evidence remains to be captured.

No steering file was present at any completed unit. Progress was appended throughout under
`guide/_waves/progress/C5-RUN.md`. All working notes are under this wave's permitted notes folder.
