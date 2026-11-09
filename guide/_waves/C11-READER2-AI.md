# C11 reader 2, assistant: a fresh reader works with an assistant (DOC11)

Read `guide/AGENTS.md` for the rules on files and progress only. For this wave you are not a writer: you
are a reader who has never used refiroo and has only its built guide. You change no page.

## Why

DOC11 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "DOC11: Fresh-reader check"): a person who has not used
refiroo completes each journey; where they get stuck is recorded and fixed. Wave C11-READER2 did every
journey but "Work with an assistant", which waited until the assistant work was finished. It is finished
now, and the installation runs it. This wave does that journey.

## What you have

- **The built guide only**, as your reading: the HTML under `guide/dist/` (start at
  `guide/dist/journeys/work-with-an-assistant/index.html`; links starting with `/docs/` are paths under
  `guide/dist/`) and its pictures (`guide/dist/screens/`). The same guide is served at
  http://localhost:8480/docs. Open nothing else in the repository: no Markdown sources, no code, no `docs/`
  folder, no notes of other waves. Needing a source to understand a step is a finding.
- **A running installation**, http://localhost:8480, rebuilt from the current code, with an AI provider
  configured. The guide's example data is in the workspace `graubuenden`. The people to sign in as are in
  `guide/reference/.env`: the administrator (`GUIDE_ADMIN_USERNAME`, `GUIDE_ADMIN_PASSWORD`) and the role
  accounts (`GUIDE_<ROLE>_USERNAME` and `_PASSWORD`). Read only the lines you need; never print or write a
  secret into a file.
- **The network** to that installation, for the guide's requests.
- **A browser** you drive with Playwright: the endpoint and an example are at the end of this prompt. Click
  what the page says, type what it says, look at what appears (screenshot into your notes folder when the
  words and the screen might differ). 1280 px wide unless the page says otherwise.

## The rules of the doing

- Follow the journey "Work with an assistant" start to end, every path, including the guides each path
  sends you to: AI proposals and targets for unmapped values, loading a workbook with the assistant (use
  the workbooks the guide offers for download), reviewing its design, continuing and discarding a task,
  changing records and changing a model with the assistant, asking a list in words, explaining a period,
  reaching refiroo from an assistant (connect as the page says; your own terminal is the outside
  assistant), reusing a checked layout, stopping AI.
- AI is allowed in this wave: start the assistant tasks and proposals the pages describe. Each assistant
  task costs real tokens, so run each path once, as the page says, and not again unless a retry is the
  step being described. A task may take up to about 15 minutes: wait for it as a person would, following
  it on the screen the page names. For each task record its number, how long it took, and the usage the
  screens show (tokens, cost) if they show it.
- Work in workspaces of your own (make them as the guide shows; names starting `reader-ai`). In
  `graubuenden` you may read, and start change sets there only where a page's steps need that workspace;
  never publish, activate a model release, install a model, or delete records there.
- Do not change the installation's AI settings or run host commands; read those steps and mark them "not
  run (host)". If the provider check fails, record it and stop the AI paths: that is the installation's
  setup, not the guide.
- Record, do not fix. Write each path's findings before starting the next. Record everything you create
  (workspaces, drafts, tasks, change sets, clients, connections) so it can be removed afterwards; revoke or
  deactivate any outside-assistant connection you made when you finish.

## Continuing (2026-11-09, second continuation)

Two earlier runs of this wave are recorded in `_waves/progress/C11-READER2-AI.md`,
`_coverage/notes/C11-READER2-AI/findings.md` and `report.md`; read them first and do not redo finished
paths. The installation was rebuilt again with fixes for findings 13 and 14 and for the task heading of
finding 7. Finding 12 was your setup: the installation redirected to your registered return address with a
code, and nothing listened there. An assistant that signs in this way listens on its return address, so do
as the assistant would: listen on the loopback port you register (a small local listener of your own
inside the sandbox) and exchange the code as the page describes.

Do, once each, as the pages write them: Stop then Go on as it was; the partial move of a type through its
prepared steps (activation, publication and final removal); the personal sign-in and consent through to a
working token, a call, and signing out or revoking as the page says. Record whether findings 7, 12, 13 and
14 still happen, add new findings numbered on, update `report.md` (paths, tasks with durations and usage,
created objects) and finish. Leave no registration or client active.

## What to record

In `_coverage/notes/C11-READER2-AI/findings.md`, one numbered item per place you got stuck, were misled, or
where the product did something other than the page says: the page (its `/docs/...` address) and the step;
what you did; what happened (status and the part of the body that matters, or what the screen showed, with
the screenshot's file name); how bad it is (blocks the reader / costs time / small). Per path also: completed
end to end or not and why, and what worked well (briefly). At the end: the assistant tasks with their
durations and usage, and the list of things you created.

## Files you may edit

- `_coverage/notes/C11-READER2-AI/**` (findings, screenshots, your small scripts)
- `_waves/progress/C11-READER2-AI.md`

## Report

`_coverage/notes/C11-READER2-AI/report.md`: the findings ranked by how badly they block a reader; per path
completed or not; the steps not run; the assistant tasks with durations and usage; what you created.
