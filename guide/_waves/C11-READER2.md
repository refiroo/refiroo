# C11 reader 2: a fresh reader does what the guide says (DOC11)

Read `guide/AGENTS.md` for the rules on files and progress only. For this wave you are not a writer: you
are a reader who has never used refiroo and has only its built guide. You change no page.

## Why

DOC11 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "DOC11: Fresh-reader check"): a person who has not used
refiroo completes each tutorial and tries the quick start and the production checklist; where they get
stuck is recorded and fixed. The first reading (wave C11-READER, 2026-11-06) could not reach the
installation and had no browser, so it judged every step from the words. This time you **do** the steps:
the requests in a terminal and the screens in a real browser. Many pages changed since that reading.

## What you have

- **The built guide only**, as your reading: the HTML under `guide/dist/` (start at
  `guide/dist/index.html`; links starting with `/docs/` are paths under `guide/dist/`) and its pictures
  (`guide/dist/screens/`). The same guide is served at http://localhost:8480/docs. Open nothing else in the
  repository: no Markdown sources, no code, no `docs/` folder, no notes of earlier waves. Needing a source
  to understand a step is a finding.
- **A running installation**, http://localhost:8480, with the guide's example data in the workspace
  `graubuenden`. The people to sign in as are in `guide/reference/.env`: the administrator
  (`GUIDE_ADMIN_USERNAME`, `GUIDE_ADMIN_PASSWORD`) and the role accounts (`GUIDE_<ROLE>_USERNAME` and
  `_PASSWORD`, for example the approver and the contributor), and the consumer client
  (`GUIDE_CONSUMER_CLIENT_ID`, `_SECRET`). Read only the lines you need; never print or write a secret
  into a file.
- **The network** to that installation, for the guide's requests (curl, or the language the page uses).
- **A browser** you drive with Playwright: the endpoint and an example are at the end of this prompt.
  Click what the page says to click, type what it says to type, and look at what appears (take a
  screenshot into your notes folder and look at it when the words and the screen might differ). Use the
  width the page talks about; 1280 px otherwise.

## The rules of the doing

- Follow each step as written, in order, as a newcomer would. Where you have to guess, guess as a
  newcomer would, then record that you had to.
- Do your writing work in a workspace of your own where the guide shows how to make one (call it
  `reader`); in `graubuenden` you may read, start change sets and edit inside them, and submit them for
  approval, but do not publish, activate a model release, install a model, or delete records there.
  Record everything you create (workspaces, people, groups, clients, change sets, drafts), so it can be
  removed afterwards.
- Do not run installation or host commands (`docker`, `docker compose`, package installs, the engine's
  command-line tools, backups, restores, upgrades) and do not change the installation's settings: those
  are rehearsed separately on a clean host. Read those steps and judge them; mark them "not run (host)".
- Do not start assistant tasks or AI proposals, and skip the journey "Work with an assistant": it is read
  in a later wave. Mark AI steps elsewhere "not run (AI)".
- Record, do not fix. Write each journey's findings before starting the next.

## Continuing (2026-11-08, after a usage-limit stop)

An earlier run of this wave stopped at the usage limit. Read `_waves/progress/C11-READER2.md` and
`_coverage/notes/C11-READER2/findings.md` first and continue where they end; do not redo finished units.
Findings 2 and 3 were the installation's setup, not the guide: the approver, the contributor and the
consumer client in `guide/reference/.env` have been made again and sign in now. Mark both findings
"setup, fixed" and do the steps they blocked with the supplied accounts: the contributor's and approver's
paths in "Change with approval" (including the second-person refusal), and the consumer sequence with the
supplied client (`/docs/guide/integrate/get-a-token/` onward). Then the units not yet done: "Receive
notices", "Run the service", and what is left of "Integrate a system" and "Manage access".

## What to follow

1. The quick start: from the guide's home page, the way an operator installs and first opens refiroo
   (`run/overview`, `run/install-with-compose`): read, and do the browser part (first sign-in, adding a
   person) on the running installation.
2. Every journey under `/docs/journeys/` except "Work with an assistant", start to end, every path,
   including the guides each path sends you to.
3. The production checklist (`/docs/run/production-checklist/`): do what can be checked on the running
   installation from outside (headers, health, sign-in, what the screens show), read the rest.

## What to record

In `_coverage/notes/C11-READER2/findings.md`, one numbered item per place you got stuck, were misled, or
where the product did something other than the page says: the page (its `/docs/...` address) and the step;
what you did; what happened (the response's status and the part of the body that matters, or what the
screen showed, with the screenshot's file name); how bad it is (blocks the reader / costs time / small).
Per journey, also: the paths completed end to end, what worked well (briefly), and the steps not run and
why. At the end: the list of things you created on the installation.

## Files you may edit

- `_coverage/notes/C11-READER2/**` (findings, screenshots, your small scripts)
- `_waves/progress/C11-READER2.md`

## Report

The findings, ranked by how badly they block a reader; per journey the paths completed; the steps not
run; what you created on the installation.
