# Handover: the refiroo documentation (0.13), 2026-11-05

For the session that continues the documentation work. It says what exists, how the work is done and
where things stand; what to do next is for that session to judge with the user.

## What is being built

refiroo's product documentation, served by the engine at `/docs` (the API reference is `/docs/api`), built
with Astro 7 + Starlight from `guide/`. Readers and sections (settled by the user, not to be reorganised):
About refiroo, User journeys, Use refiroo, Example applications, Model your data, Administer access, Run
refiroo, Integrate. Documentation pages explain a capability; guides (`guide/<section>/`) take the reader
through one task and sit under their documentation page in the sidebar. Applications (the starter model's,
the Graubünden example's) are examples, never features. 0.13 is the documentation release
(`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "Restarted 2026-11-02"; `docs/ROADMAP.md` "Product release 0.13").

The user's standing view: completeness comes from the product's own record, not from topic lists; the
structure stays and is completed; the docs must carry the full, correct content of the sources, name the
concrete technologies, and work when followed (a guide that does not lead to a working result is wrong).

## How the work is done

- **Codex writes every page.** Claude writes no page text (memory "Codex writes guide prose"); Claude writes
  briefs ("waves"), mechanism and checks. Codex's guidance: `guide/AGENTS.md` (rules 1–12, incl. rule 3's
  consumer-API exception and rule 6 "Name the concrete things"); shared rules for completion waves:
  `guide/_waves/COMPLETE-COMMON.md` (its "After 0.16" paragraph is outdated: the AI pages are now written).
- **The Codex tool:** `guide/tools/codex-wave.mjs` (`run`, `check`, `reply`, `status`; doc:
  `guide/tools/CODEX_TOOL.md`). A wave is `guide/_waves/<NAME>.md` with a "Files you may edit" list. Several
  waves may run at once (one lock per wave, `_waves/runs/.lock-<NAME>`; each builds into
  `guide/_build/<NAME>` via `GUIDE_OUT`, never into `dist/`). The prompt makes Codex save each unit before the
  next, keep notes under `guide/_coverage/notes/<NAME>/`, write progress to `_waves/progress/<NAME>.md` and
  read `_waves/steer/<NAME>.md` before each unit (how the user or Claude steers a running wave).
- **Usage limits:** `run --wait-on-limit --max-restarts 30` waits for Codex's limit (retries at most every 20
  min, 30 min when no time is named) and starts a fresh run that continues from the files. Never `reply` to
  a long session to finish a big task (a reply turn once lost its whole reading on compaction). If Codex is
  out, wait and continue; never take over the writing. `guide/tools/codex-chain.sh WAVE [WAVE…]` runs waves
  in order with that waiting, then `check`; logs `_waves/runs/chain-<WAVE>.log`. Start chains with
  `run_in_background`, not `&` (you get no notification otherwise).
- **Per-section files** so waves do not clash: sidebar `guide/sidebar/<section>.mjs` (imported by
  `astro.config.mjs`; a page not listed is not shown), coverage `guide/_waves/coverage/<section>.md`
  (split from `_waves/COVERAGE.md` by `guide/tools/split-coverage.py`), screenshots wanted
  `_waves/screens-wanted/<WAVE>.md`.
- **Screenshots:** `guide/tools/screens.mjs --file <X>.screens.json [--only a,b]` captures from the reference
  instance into `guide/public/screens/<name>.png`; a page shows an image as soon as the file of its name
  exists. `"as": "<role>"` signs in as `GUIDE_<ROLE>_*` (admin, approver, contributor exist); a `waitFor`
  step takes `"timeout"` in ms (AI work: 300000). Codex cannot reach the instance from its sandbox: it writes
  recipes (`_waves/C10.screens.json`), Claude captures, then a `reply` turn sends the log and images back
  for review and fixes. State changes on the instance are recorded in `_waves/C10.data-changes.md`.
- **Live examples:** `guide/tools/live-requests.mjs --file <X>.requests.json` runs request examples against
  the reference instance (admin through the normal sign-in, the consumer client by its credentials; only
  reads unless `--allow-writes`), saving responses to `guide/_coverage/live/`. C12 used it to check the
  pages' examples (`_waves/reconcile/C12-LIVE.md`).
- **Publishing locally:** `guide/tools/publish-loop.sh` rebuilds `dist/` every 5 minutes while waves run; the
  dev engine serves `guide/dist` at `/docs`. `cd guide && npm run verify` = build + terms + brand + links.
- **Brand marking:** every standalone "refiroo" in prose is wrapped by the build (`guide/tools/rehype-brand.mjs`,
  a Sätteri hast plugin; `@astrojs/markdown-satteri` declared in `guide/package.json`). Sidebar starts folded
  except About (`astro.config.mjs`).

## The reference instance

Docker project `refiroo-guide-ref` (`guide/reference/reference.sh up|start|stop|load|status`;
http://localhost:8480; README `guide/reference/README.md`). Settings only from `guide/reference/.env`
(git-ignored; `export` does not reach the engine); `reference.sh start` applies changed settings without a
rebuild, `up` rebuilds the image (with the current guide). `guide/reference/compose.override.yml` mounts
`backend/devtools` so `AI_PROVIDER=devtools.claude_code_provider:provider` (the development provider, on
the user's Claude subscription, logs to `backend/devtools/usage.jsonl`) works there. Its `.env` now has the
assistant (`CLAUDE_CODE_OAUTH_TOKEN`, `AI_AGENT_COMMAND`, `AI_AGENT_SANDBOX`, `AI_SEND_LEVEL`), the provider
(`AI_PROVIDER`, `AI_MODEL`), webhooks (`CONSUMER_SUBSCRIPTIONS_ENABLED`), and — added by the user after the
last session's diagnosis — `AI_AGENT_API_URL` and `MCP_ENABLED`. Docker was not running at handover. Accounts:
`guide` (admin), `rita.approver`, `guide.contributor` (given Contributor in Graubünden on 2026-11-03).
Docker start may put Portainer on port 8000 (memory: user runs `docker stop portainer`).

## Where things stand

- **Written:** 247 pages. Record built and reconciled: `PROMISES.md`, `BEHAVIOUR-RULES.md`, the coverage files
  (every non-AI row covered or reasoned), reconciliation ledgers per source document in `_waves/reconcile/`
  (R-OPS, R-MODEL, R-CONSUMER, R-FUNCTIONALITY, C12-LIVE, C13-AI-*). The AI pages (C13-AI-USE, -MODEL,
  -ADMIN, -RUN, -INTEGRATE, -REST) are written; their coverage rows are resolved. Last session's additions:
  automatic HTTPS presented as a feature (C7c); `run/install-with-compose.md` became "Deploy to production
  with Docker" step by step (C5d, requested via session rdm-engine-6d).
- **Screenshots:** most pages have real pictures. `npm run check:links` reports **37 missing images**, all AI,
  agent-access and mail screens requested by the C13 waves; recipes are in `_waves/C10.screens.json`, the
  last capture log `_waves/runs/screens-C10g.log`, Codex's notes `guide/_coverage/notes/C10-SCREENS/`. Why
  they failed: the assistant task stopped at once with "internal error": inside the engine container the
  session fetched `openapi.json` from `PUBLIC_URL` (http://localhost:8480) → connection refused
  (`backend/app/engine/tasks/agent.py` `_api_url`, default `PUBLIC_URL`). The fix is `AI_AGENT_API_URL`
  (e.g. http://127.0.0.1:8000, the engine inside its container), now in the instance's `.env`; agent-access
  screens needed `MCP_ENABLED`. Deferred with reasons: `_waves/screens-wanted/C10-LATER.md` (webhook
  deliveries need a receiver; no side servers may be started).
- **Not yet in the docs:** `AI_AGENT_API_URL` for Compose installations (`run/set-up-ai.md` and the deployment
  page do not say to set it; the guide is wrong there).
- **Unconfirmed, held off the pages until the user confirms from their VM:** that the GitHub App token script
  prints `ghs_…`; that port 443 alone gets the Let's Encrypt certificate (TLS-ALPN). If 443 alone works,
  `run/https.md`, the deployment page, `compose.acme.yml`, `caddy/Caddyfile` comments and `docs/OPERATIONS.md`
  "Automatic HTTPS" say 80 and 443 today.
- **0.13 plan steps 5 and 6** (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`): AI pages now written (step 5, minus
  pictures); step 6 open: publication (DOC12, public site per release), release R (the fresh-reader check ran 2026-11-06 in its weaker form, see below)
  with its full review since 0.12 (memory "Release needs full review"). `docs/ROADMAP.md`'s 0.13 delivery
  scope still lists items the restart removed (the `docs` test group, generated references with checks,
  "seven tutorials"): the user has not decided whether to update the roadmap or deliver them.
- **Product findings from the waves' reports** (nothing changed in the product): consumer API version
  serving vs the compatibility commitment; an outdated encryption-setting name on the disabled Webhooks
  screen; a refused restore check can print a credential-bearing database URL; raising a model release
  prints internal numeric release IDs. More are in the waves' reports under `guide/_coverage/notes/`.
- **AI use** for screenshots on 2026-11-04: 8 calls through the subscription, about $0.12 at API prices
  (`backend/devtools/usage.jsonl`). Report each try's use (memory "AI tries").

## Git

Committed up to 38fed932 (`main`, ahead of `origin/main`, nothing pushed). Uncommitted at handover, this
work: the C7c/C5d pages and sidebar label, the C10 round-4 files and new pictures, `guide/tools/CODEX_TOOL.md`,
`guide/tools/screens.mjs`, this handover, and this work's CHANGELOG entry ("Added (documentation: production
deployment and AI)"). Other sessions have uncommitted changes in the same checkout (e.g.
`.github/workflows/ci.yml`, `docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, parts of `CHANGELOG.md`): commit only
this work's hunks; "can we commit …?" means commit now (memory). Report what is uncommitted and why, in
groups (this work in progress / this work ready / others'). The scratch files `backend/devtools/usage.jsonl`,
`frontend/e2e/zz-scratch-hint.mjs`, `frontend/results.txt` are deliberately left out.

## What went wrong before, briefly

Pages written from short topic lists missed most of the product; work held in a long Codex session was lost
on a usage limit; a warning ("it will likely run out") was taken as an instruction for afterwards instead of
a design requirement; "stop" was read literally and the night was lost; a question was answered with
analysis when the user asked to commit; a guide step that did not work was defended instead of fixed. Read
the user for intent, verify in the code before answering, and keep turns short.

## State on 2026-11-06

- Every image the pages reference exists (`npm run check:links`: 0 missing); captions checked by Codex
  (wave C10-CAPTIONS). Fixtures and IDs: `C10.data-changes.md`, Fifth to Eighth capture.
- Fresh-reader check (DOC11), weaker form: waves C11-READER (record only, built guide only) and C11-FIX.
  Findings: `_coverage/notes/C11-READER/findings.md`. Codex's sandbox has no network, so the reader could
  not reach http://localhost:8480: API and browser steps were judged, not run. A run with network access
  (or an outside reader) is still the stronger check.
- Product fixes made while taking pictures (CHANGELOG [Unreleased], "Fixed (the assistant in a
  container)"): permission bypass and no read block in a container, Compose's `AI_AGENT_API_URL`, the
  assistant volumes, "what changes" from model to model, formatted assistant text, words-only proposals
  without a draft (prompt `agent/8`), the web image's build.
- Open product findings, not fixed: the Jobs list shows the workspace key, not its name; the assistant is
  far over the import time limit (a whole-type move took 1,245 s); the client webhook panel shows "Not
  Found" when webhooks are off (`ClientsPage.tsx`); "Cancel import" opens a dialog whose button has the
  same name; the assistant's closing note speaks in file terms (`proposal.json`, `draftId`); the
  notification picture shows no digest controls.
- The reference instance's assistant runs Claude Code on the owner's subscription
  (`CLAUDE_CODE_OAUTH_TOKEN` in `reference/.env`): every assistant task counts against their weekly
  limit. Run picture tasks one at a time, one try each, with short agents that do not poll.
