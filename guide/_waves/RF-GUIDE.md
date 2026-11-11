# RF guide: what the review packages RF2 to RF6 changed

Read `guide/AGENTS.md`. Readers: operators (the `run/` pages), administrators, integrators, and people who export and
import files.

## Why

Five 0.17 packages are built (plan `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, sections RF2 to RF6, each with a
"Delivered 2026-11-11" record and its decisions; CHANGELOG, Unreleased, the RF2 to RF6 entries; `docs/OPERATIONS.md`;
`docs/API.md`; `docs/CONSUMER_API.md`). Several guide pages now describe the earlier behaviour. The code wins over the
plan wherever they differ. Work page by page; where a page already says the right thing, leave it.

## What the product does now (check each point in the code)

**Webhook addresses (RF6).** Code: `backend/app/engine/events/webhook_urls.py`, `webhook_client.py`, the setting
`WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` in `backend/app/config.py`.
- A webhook address that is, or whose name resolves to, a loopback, private, unique-local, 100.64/10 or other non-public
  address is refused when a subscription is created or changed and again at every delivery, unless the instance setting
  `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` is on. It is off by default. Link-local addresses are always refused.
- Plain HTTP to a localhost receiver needs the setting on.
- A refused delivery shows in the delivery log as an `address` attempt with a reason.
- After the upgrade, existing subscriptions on private addresses stop delivering until the setting is on.
- The address is checked at each attempt and the connection goes to the checked address.

**The assistant in a container (RF5), as finally built — the first wave described an earlier design; correct it.**
Code: `backend/app/engine/tasks/agent.py`, `backend/refiroo-session-reset`, `backend/Dockerfile`, `compose.yml`; text:
`docs/OPERATIONS.md`, the `AI_AGENT_SANDBOX` row and the assistant sections (read them again: they changed).
- Permissions keep tasks apart, not folder names. Each task's folder can be entered only by the engine outside a turn; for a
  turn it is opened to the one session user that runs it and closed afterwards and at every engine start.
- Around every turn the engine runs a fixed reset as that session user (never as root): it ends that user's processes,
  empties its home and temporary places, and makes what the session wrote usable by the next turn, which another session
  user may run. A reset that fails before a turn fails the turn.
- The image holds a pool of session users (build argument `ASSISTANT_USERS`, default 8), taken per turn. With none free, a
  new task fails with a note that names the argument.
- A task's Claude Code transcript lies inside the task's own folder. The `assistant-claude` folder and volume no longer
  exist. `compose.yml` runs the engine with an init process (`init: true`).
- Only named variables reach a session; the Bedrock names only when Bedrock is on.
- The limits OPERATIONS states remain and must be stated plainly, as OPERATIONS words them (there are three).
- After the upgrade, a task begun before it starts a new session; its files are kept.

**Build and deployment (RF4).** Text: `docs/OPERATIONS.md`, "Pinned versions (0.17 RF4)" and "Content security policy
(0.17 RF4)"; files `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yml`, `compose.acme.yml`,
`backend/constraints.txt`, `frontend/nginx/snippets/`.
- Claude Code is installed at a named version (build argument `CLAUDE_CODE_VERSION`); base images are pinned by digest;
  the backend installs from `backend/constraints.txt`. Say how each is moved, as OPERATIONS does.
- The application is served with a content security policy; the sign-in pages, the guide and the API reference keep
  the engine's own policies. Describe it at the level OPERATIONS does; do not paste a policy the code does not send.
- `FORWARDED_ALLOW_IPS` in `compose.yml` trusts private network ranges by default instead of every address; behind
  another proxy it is set in `.env`.

**Files (RF2).** Code: `backend/app/engine/jobs/exports.py` (`_csv_text`), `backend/app/engine/imports/binding.py`
(`_unquoted`).
- In a CSV export, a text that starts with `=`, `+`, `-`, `@`, a tab or a carriage return (also after leading single
  quotes) is written with one leading single quote, so a spreadsheet shows it as text. A CSV import removes exactly one
  such quote. An unchanged export sent back changes nothing. XLSX files are not affected.

**Passwords (RF2, RF3).** Code: `backend/app/engine/identity/resets.py`, `backend/app/engine/mail/links.py`,
`backend/app/management/routers/oauth.py` (`password_page`).
- A forgotten-password request no longer cancels a link an administrator made; an administrator's link still replaces
  every earlier link.
- Opening a password link no longer leaves the token in the address bar; reloading the page before setting the password
  still works while the link is valid.

## What to do

- Extend or correct the pages that own each topic; no new pages. Known wrong text, to start from:
  `run/webhook-delivery.md` (near "Private addresses are permitted" and the loopback sentence),
  `integrate/consumer-events-and-webhooks.md` ("including private networks", two places),
  `administer/webhooks.md` (the URL row), `guide/administer/create-a-webhook.md` (the plain HTTP sentence),
  `run/configure.md` (add the setting's row, with its upgrade effect).
- For the assistant, build and deployment points, check every page in the list below that names `AI_AGENT_SANDBOX`, the
  assistant's folders or volumes, forwarded addresses or the security checklist, and correct what no longer holds.
- Neutral examples only. Never the example model or its types.
- Pictures: take none; list in the report each picture the text calls for that is not taken yet. Do not add an image
  reference to a picture that does not exist.
- Keep everything else on these pages as it is.

## Files you may edit

- `src/content/docs/run/webhook-delivery.md`
- `src/content/docs/integrate/consumer-events-and-webhooks.md`
- `src/content/docs/administer/webhooks.md`
- `src/content/docs/guide/administer/create-a-webhook.md`
- `src/content/docs/run/configure.md`
- `src/content/docs/run/overview.md`
- `src/content/docs/run/backup-and-restore.md`
- `src/content/docs/run/upgrades.md`
- `src/content/docs/run/developer-instance.md`
- `src/content/docs/run/background-jobs.md`
- `src/content/docs/run/set-up-ai.md`
- `src/content/docs/run/ai.md`
- `src/content/docs/run/install-with-compose.md`
- `src/content/docs/run/https.md`
- `src/content/docs/run/security-checklist.md`
- `src/content/docs/guide/use/export-records.md`
- `src/content/docs/guide/use/import-a-file.md`
- `src/content/docs/use/importing-and-exporting.md`
- `src/content/docs/administer/sign-in.md`
- `src/content/docs/administer/mail.md`
- `src/content/docs/guide/administer/help-someone-who-lost-a-device.md`
- `_waves/progress/RF-GUIDE.md`

## Report

Per page: what changed and why (one line each), what you checked and left, pictures needed, and any point the guide cannot
describe honestly.
