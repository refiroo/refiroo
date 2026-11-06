# C11 reader: a fresh reader follows the guide (DOC11, the weaker check)

Read `guide/AGENTS.md` for the rules on files and progress only. For this wave you are not a writer: you
are a reader who has never used refiroo and has only its built guide. You change no page.

## Why

DOC11 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "DOC11: Fresh-reader check"): a person who has not used
refiroo completes each tutorial and tries the quick start and the production checklist; where they get
stuck is recorded and fixed. No outside reader is available, so a fresh session given only the built
guide does it; this is recorded as the weaker check.

## The rules of the reading

- Read only the built guide: the HTML under `guide/dist/` (start at `guide/dist/index.html`; follow its
  links, which start with `/docs/`, as paths under `guide/dist/`), and the pictures it shows
  (`guide/dist/screens/`). Open nothing else in the repository: no Markdown sources, no code, no `docs/`,
  no notes of earlier waves. If you catch yourself needing a source to understand a step, that is a
  finding.
- You have a running installation to try things on: http://localhost:8480, signed in as the
  administrator with the user name and password that `GUIDE_ADMIN_USERNAME` and `GUIDE_ADMIN_PASSWORD`
  in `guide/reference/.env` hold (read those two lines only; never print or write a secret). Run the
  guide's API commands (curl) against it where a page asks you to. You cannot click in a browser: for
  steps in the browser, judge from the page's words and its pictures whether a newcomer could do them.
- Do not run installation commands (`docker compose`, package installs, changes to a host), do not
  change settings of the installation, do not publish or activate anything in the workspace
  `graubuenden`. Where a page asks for that, read the step and judge it; mark it "not run".
- Record, do not fix.

## What to follow

1. The quick start: from the guide's home page, the way an operator installs and first opens refiroo
   (`run/overview`, `run/install-with-compose`).
2. Every journey under `/docs/journeys/` (the guide's tutorials), start to end.
3. The production checklist (`/docs/run/production-checklist/`).

## What to record

In `_coverage/notes/C11-READER/findings.md`, one numbered item per place you got stuck or were misled:
the page (its `/docs/...` address) and the step; what you tried; what happened or what was unclear; how
bad it is (blocks the reader / costs time / small). Also list what worked well, briefly, per journey, and
which steps you could not run and why. Write each journey's findings before starting the next.

## Files you may edit

- `_coverage/notes/C11-READER/**`
- `_waves/progress/C11-READER.md`

## Report

The findings, ranked by how badly they block a reader, and the list of steps not run.
