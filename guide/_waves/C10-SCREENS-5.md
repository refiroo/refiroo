# C10, fifth round: every picture the guide still lacks

Read `guide/AGENTS.md`, `guide/tools/CODEX_TOOL.md` (Screenshots) and `_waves/C10-SCREENS.md` (how this wave works).
This round writes recipes, captions and a fixture list; no new page text beyond captions and restored image references.

## What changed since the fourth round (facts, checked 2026-11-05)

- **The owner has authorised any state the pictures need on the reference instance.** This replaces every earlier
  "do not create / do not enable / do not confirm" limit in `C10.data-changes.md`, `C10.screens.json` and
  `screens-wanted/C10-LATER.md`, for the reference instance only: registering and blocking a fictional assistant,
  creating fictional people, groups, clients and grants, a fictional sign-in provider, webhook subscriptions and a
  receiver, extra assistant tasks, activating releases or migrating in a workspace made for the purpose, a deliberate
  provider failure. Still never: real people's data, another organisation's data, secrets on a screen.
  Prefer a separate workspace made for a picture over changing Graubünden's published data.
- `MCP_ENABLED` and `AI_AGENT_API_URL` are on; the Agent access page works. Taken this round and accepted:
  `admin-agent-access-enabled`, `integrate-agent-access-connect`, `admin-agent-new-client`, `admin-agent-register`,
  `admin-agent-calls`. Look at them and fix their captions if they say something the images do not show.
- Fixtures already made by Claude (`C10.data-changes.md`, "Fifth capture"): agent client **Stops checker (guide)**
  (Data steward in Graubünden) with five real MCP calls, one refused; registered assistant **Guide example
  assistant** (not blocked).
- The Jobs list shows the workspace **key** (`graubuenden`), not its name: select jobs by their recorded address.
  The one workbook task is job `/settings/jobs/67d62b49-304d-489c-9d35-87cd714446ed`, state failed.
- The assistant could not run shell commands in a container (product defect, being fixed now: in container mode the
  session runs without Claude Code's permission prompts). Write the assistant recipes for a working assistant. A new
  task may be started; for the "stopped" picture start a task and stop it with the page's Stop control, waiting for
  the stopped state (stopping is asynchronous: wait up to 300000 ms).

## What to cover

1. Every image a page references whose file is missing (run `npm run check:links` in `guide/`; 15 today):
   the assistant chain (stopped, proposal, workbook proposal, loaded, reload, words-only change), the whole-type and
   partial model moves, history with an assistant's preparation (an MCP change set by **Stops checker (guide)**,
   submitted, then published by a person, gives that history), the mapping proposals grid (a proposal that offers
   targets: choose codes that do match stops), the failed provider test and the failed account request (Claude
   breaks the provider on purpose for those two captures and restores it), blocking **Guide example assistant**.
2. The 15 pictures deferred in `screens-wanted/C10-LATER.md`: restore each image reference on its page (where the
   page removed it, put it back where it belongs, with a caption) and write its recipe and fixture. For
   `notification-email-digest` the file now exists: check its caption against the image.

## Fixtures

Recipes can only drive the browser. Put fixture work the browser can do into setup entries (`c10-setup-…`) before
the pictures that need them. Write everything else into `_coverage/notes/C10-SCREENS/fifth-round-fixtures.md` for
Claude, one numbered item each, precise enough to do without guessing: what to create, through which API path or
setting (from `backend/app/` and `docs/OPERATIONS.md`), which values, and which recipe needs it. Containers (a test
OpenID Connect provider, a webhook receiver) run in the reference Docker project `refiroo-guide-ref`
(`guide/reference/compose.override.yml`), never as side servers: name the image and the settings it needs.

## Files you may edit

- `_waves/C10.screens.json`
- `_waves/C10.data-changes.md`
- `_waves/screens-wanted/C10-LATER.md`
- `src/content/docs/**/*.md`
- `_coverage/notes/C10-SCREENS/**` (working notes)
- `_coverage/notes/C10-SCREENS-5/**`
- `_waves/progress/C10-SCREENS-5.md`

## Report

The recipes added or changed in manifest order, the fixture list's items, captions changed, and anything unsure.
