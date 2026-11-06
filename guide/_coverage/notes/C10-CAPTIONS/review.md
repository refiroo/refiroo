# C10 caption review

All 33 supplied images were visually checked against every exact filename reference and nearby prose. Existing accurate references were left unchanged. No new pages or screenshots were created.

| Image | Pages under src/content/docs | Finding |
| --- | --- | --- |
| `model-account-provider-failure.png` | `guide/model/explain-a-model-change.md` | Matches: provider unreachable, facts retained, Try again; migration remains available. |
| `use-assistant-words.png` | `guide/use/change-records-with-the-assistant.md` | Updated: No change to the model, Accept, one Abbreviation update, correction box; no draft or model editor. |
| `model-migration-stale.png` | `guide/model/migrate-a-workspace.md` | Matches: workspace changed after preview, nothing migrated, Close and Preview again. |
| `model-assistant-workbook-proposal.png` | `guide/model/review-an-assistants-workbook-design.md` | Updated: types and counts, row check, expanded table of actual model changes. Questions and columns left out are not in this viewport. Summary says three stop attributes but list and table name two. |
| `use-assistant-proposal.png` | `journeys/work-with-an-assistant.md`, `use/loading-with-the-assistant.md` | Updated both references: formatted notes and assumed answers, then start of type summary. Separate Checks and Questions sections are outside the capture. |
| `admin-ai-test-failed.png` | `guide/administer/check-the-ai-provider.md` | Matches: unreachable provider failure and failed Test request call. |
| `model-assistant-partial-move.png` | `guide/model/change-a-model-with-the-assistant.md` | Matches: 116 records changed in change set; three personal steps, first Done, review Next. |
| `model-assistant-whole-type-move.png` | `guide/model/change-a-model-with-the-assistant.md` | Matches: installed model, no records moved, 116 Stop records become Guide stop, Preview the migration. |
| `admin-agent-block.png` | `guide/administer/manage-agent-access.md` | Matches: block confirmation names assistant and zero sessions, restore does not revive sessions. |
| `model-language-raise-review.png` | `guide/model/raise-a-model-language-version.md` | Matches: schema 0.9 to 0.10, zero consumer APIs rewritten, named returning workspace, unchanged records/change sets/publications. |
| `workspace-cannot-open.png` | `guide/use/open-a-retired-or-unavailable-workspace.md` | Matches: old schema language reason, Bring it up to date, other workspaces. |
| `use-history-assistant.png` | `use/history.md` | Updated: expanded update attributed to Guide Admin and prepared by Stops checker (guide), followed by client update. No separate publication event is visible. |
| `run-jobs.png` | `run/background-jobs.md` | Matches: queued/running/completed jobs and import awaiting confirmation; existing caption makes no claim of a missing state. |
| `import-preview-columns.png` | `use/importing-and-exporting.md` | Updated: 116 rows, 115 unchanged, one refused Height cell; per-column reading counts and import profile. |
| `admin-local-signin-off.png` | `guide/administer/turn-off-local-sign-in.md` | Matches: Local accounts Off, Turn on, second-factor option, success notice. |
| `admin-signin-provider.png` | `guide/administer/add-a-sign-in-provider.md` | Matches: saved enabled fictional OpenID Connect provider, return addresses, sign-out and settings. |
| `admin-person-link-provider.png` | `guide/administer/link-a-provider-person.md` | Matches: linking dialog with existing target selected and account/history consequences. |
| `use-assistant-reload.png` | `guide/use/continue-an-assistant-task.md` | Matches: discard and reload confirmation removes loaded work and manual edits. |
| `model-assistant-workbook-loaded.png` | `guide/model/review-an-assistants-workbook-design.md` | Updated: 86 new records, saved profile, review and correction actions. No excluded sheets or columns are shown. |
| `use-assistant-loaded.png` | `guide/use/load-a-workbook-with-the-assistant.md` | Matches: same loaded workbook result, named change set and saved profile. |
| `use-mapping-proposed.png` | `use/mapping-grids.md` | Matches: change set, Proposed filter, two mapped targets with AI confidence and reasons. |
| `admin-person-second-factor.png` | `guide/administer/help-someone-who-lost-a-device.md` | Matches: authenticator app, named passkey and removal actions. |
| `use-assistant-stopped.png` | `guide/use/continue-an-assistant-task.md` | Updated: stopped before proposal, words box, Go on as it was, discard and return actions; not a failed provider turn. |
| `admin-webhook-deliveries.png` | `administer/webhooks.md` | Matches: Retrying, two attempts with 503, saved request and response, resend action. |
| `admin-webhook-rotate.png` | `guide/administer/rotate-a-webhook-key.md` | Matches: overlap options with 24 hours selected, no new key yet. |
| `admin-webhook-resume.png` | `guide/administer/find-out-why-a-webhook-paused.md` | Matches: administratively suspended webhook and continuation choices, first unacknowledged selected. |
| `admin-group-members.png` | `guide/administer/manage-a-group.md` | Matches: two selected fictional members, add/remove actions, no roles yet. |
| `admin-agent-access-enabled.png` | `administer/agent-access.md` | Matches: connection information with empty client, assistant and call sections. |
| `integrate-agent-access-connect.png` | `guide/integrate/connect-an-assistant.md` | Matches: connection address, identity options and Claude Code command. |
| `admin-agent-new-client.png` | `guide/administer/manage-agent-access.md` | Matches: Name and creation action, no access until granted. |
| `admin-agent-register.png` | `guide/administer/manage-agent-access.md` | Matches: Name and Return addresses with localhost example. |
| `admin-agent-calls.png` | `administer/agent-access.md` | Matches: client calls with answered/refused outcomes, argument names only. |
| `notification-email-digest.png` | `use/notifications-settings.md` | Moved beside missing-address explanation and captioned empty state: no email address or followed workspaces. Does not show digest controls or a delivered digest. |

## Behaviour evidence

- Read guide/AGENTS.md first, then _waves/C10-CAPTIONS.md; no steering or previous progress existed.
- Read the four words-task pages in full and reviewed all attached-image references with nearby prose, including the relevant model guides in full.
- Frontend ModelProposal: no draft plus modelUnchanged selects Accept, shows No change to the model, hides model disclosure and editor, and says acceptance prepares an unpublished change set.
- Backend agent._without_model_change and _unchanged_landed: words-only task without source file, no moves and no draft produces checked proposal, no row check, no outline or checks.
- CHANGELOG Unreleased, Fixed (the assistant in a container): unchanged-model words task installs and activates nothing and uses current live release; formatted notes and model comparison include optional attributes.
- Remaining Accept the model references are workbook/model-only pages or explicitly qualified branches in the four updated words-task pages.

## Image limitations and possible product issue

- The workbook proposal summary says three stop attributes; the type outline and expanded model-change table show Step-free access and Remark (two). The caption names the visible table changes without repeating that inconsistent count.
- The history image supports update attribution but does not demonstrate the separate publication step. Surrounding publication rules were retained.
- The notification image supports the missing-address empty state, not digest configuration. It was moved beside that explanation. No new picture was requested or created.
- Proposal and loaded workbook images show different tasks/runs and counts; captions describe each independently.

## Validation

- `GUIDE_OUT=_build/C10-CAPTIONS npm run build` in guide/: passed, 247 pages, 4.01 seconds.
- Build warnings: unsupported caddyfile highlighting in run/https.md falls back to txt; duplicate /404 route. Neither is in a page changed by this wave.
- All 33 referenced screenshot source files exist; all 34 references reviewed.
- `git diff --check` for the eight pages edited by this wave: passed.
- A broader read-only whitespace check across guide docs found an existing extra blank line at EOF in run/background-jobs.md:205. This wave did not edit that file; left intact.
- No application tests run for this documentation-only wave. No new pictures are needed to support the corrected captions; these captures do not demonstrate digest controls or a separate history publication event.
- No commits or state-changing git commands. Existing working-tree content was preserved.
