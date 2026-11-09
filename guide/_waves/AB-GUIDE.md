# AB guide: the assistant loads a file as one checked batch

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

Package AB (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "AB: The assistant loads a file as one checked batch",
including its "Built (2026-11-09), AB." paragraph) changed how an assistant task loads a workbook. The pages
below still describe the old way (a load profile on the draft, a check per sheet, "Accept the model", the
session loading after acceptance, a saved profile for the next file). Bring them in line with the product.
The code wins: `backend/app/engine/tasks/agent.py` (prompt `agent/15`), `backend/app/engine/tasks/items_load.py`,
`backend/app/engine/sources/dry_run.py`, `backend/app/engine/sources/items_summary.py`,
`frontend/src/features/ai-tasks/DesignLoad.tsx`, `ModelProposal.tsx`, `DesignView.tsx`, `docs/API.md`
(the draft dry run with `items`), `../CHANGELOG.md` (Unreleased, 0.13 AB).

## What the product does now (check each point in the code)

- The assistant reads the workbook itself, reads the model and the workspace's records, changes the draft
  model where the file needs it, and turns the file into records and relationships (items). The engine
  checks every item against the draft's model, writing nothing (a draft dry run with `items`). The
  assistant writes no load profile.
- The proposal shows **What the load does**: records new, existing records matched, relationships new,
  refused, rows read; a table per type whose rows open to example records with the cells they come from;
  the engine's finding of a name that appears more than once in one type; a folded "Where each part of
  the file goes". It replaces "Where each sheet goes" for these tasks.
- **Accept and load**: the engine installs the model (when it changes), makes a change set and loads
  exactly the checked items into it, all or nothing. No assistant turn runs. Nothing is published: the
  person reviews and publishes the change set. If the draft changed after the check, the engine checks
  again first. If an item is refused at that point (the data moved), nothing is written and the task
  says which records and why; the person's words go back to the assistant as a correction of the proposal.
- Tasks that only change the model end with a migration that moves no type (AQ item 9); tasks that move
  whole types keep their migration ending. Their pages keep "Accept the model" where the product still
  shows it: check `ModelProposal.tsx` for which proposals show which button.
- A load by the assistant saves no import profile: the next file of the same layout goes to the
  assistant again. Loading a file with a saved import profile (no assistant) is unchanged.
- Questions: the assistant asks only what the file and the words leave open, in the person's terms.

## Passages known to be wrong (found by the builder; check the whole page around each)

- `guide/use/load-a-workbook-with-the-assistant.md`: step 4 "The check of every row" (now "What the load
  does"); step 6 "Accept the model" and "the session installs any necessary release…" (now "Accept and
  load", run by the engine); the saved-profile text (about lines 44–58: "Open the profile", the next file
  loads without the assistant).
- `guide/model/review-an-assistants-workbook-design.md`: "Check the records and accept" (about line 72);
  the "Accept the model" step (about line 83); "Keep the layout, or correct a load" (about lines 98–115);
  the step about "The check from before the draft's last change" and the stale-check refusal (accept now
  checks again instead).
- `guide/use/continue-an-assistant-task.md`: "Correct a proposal" and "Correct a load before
  publication"; the "Accept the model" step.
- `guide/use/change-records-with-the-assistant.md`, `guide/model/change-a-model-with-the-assistant.md`:
  the "Accept the model" and "session loads" wording now applies only to model-only and move tasks.
- `guide/model/load-a-workbook-into-a-change-set.md`: "model and profile" and saved-profile loading: check
  what it says about the assistant's loads.
- `integrate/assistant-tasks.md`: "Show what the proposal actually changes" (about line 41: dry-run figures
  per sheet; there is now `design.load` and an empty `check.sheets`); the accept step; "Repeated layouts can
  avoid a session" (about line 67, `result.profileKey` after a session load: session loads save none now).
- `use/loading-with-the-assistant.md`, `model/ai-model-changes.md`, `journeys/work-with-an-assistant.md`:
  read them for the same points.

## What to do

- Fix each passage in its page, so a reader following the page gets what the product does. Keep each
  page's voice and structure; change what is wrong, not what is right.
- No new pages; no new pictures. A picture that shows the old "Where each sheet goes" or "Accept the
  model" for a workbook load: list it in the report (name and page).
- A point where the product does something the guide cannot honestly describe: list it in the report
  with the evidence; do not write around it.

## Files you may edit

- `src/content/docs/guide/use/load-a-workbook-with-the-assistant.md`
- `src/content/docs/guide/model/review-an-assistants-workbook-design.md`
- `src/content/docs/guide/use/continue-an-assistant-task.md`
- `src/content/docs/guide/use/change-records-with-the-assistant.md`
- `src/content/docs/guide/model/change-a-model-with-the-assistant.md`
- `src/content/docs/guide/model/load-a-workbook-into-a-change-set.md`
- `src/content/docs/integrate/assistant-tasks.md`
- `src/content/docs/use/loading-with-the-assistant.md`
- `src/content/docs/model/ai-model-changes.md`
- `src/content/docs/journeys/work-with-an-assistant.md`
- `_waves/progress/AB-GUIDE.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the
pictures that no longer match, and any product point the guide cannot describe honestly.
