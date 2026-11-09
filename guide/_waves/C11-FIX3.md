# C11 fix 3: what the fresh reader found in "Work with an assistant"

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

DOC11 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "DOC11: Fresh-reader check"): a reader followed the
journey "Work with an assistant" in a real browser on the reference installation, with real assistant
tasks (wave C11-READER2-AI, 2026-11-09). Their findings are in `_coverage/notes/C11-READER2-AI/findings.md`
(numbered 1–15) and `_coverage/notes/C11-READER2-AI/report.md`.

## Already fixed in the product (bring the pages in line)

The product defects the reader found are fixed in the code now. The entries are under "### Fixed (found by
the fresh-reader check of the assistant journey, 0.13 DOC11)" in `../CHANGELOG.md`. Read them all and check
each one against the code (`backend/app/engine/tasks/`, `frontend/src/features/ai-tasks/`, the code wins):

- **Stop and continuing:** Stop shows "You stopped the assistant", with "Go on as it was". A message asking
  for a correlation ID now shows it. Going on after an early Stop starts the session again with the
  person's words.
- **Corrections:** "Discard and load again" produces a revised load. A failed turn leaves no empty change
  set.
- **Failed jobs:** a failed job reaches its task at once.
- **Relationship counts:** the workbook check counts the links of new records to their parents, so the
  checked and loaded relationship counts agree.
- **Task names:** a words task is named "Change with the assistant" until its proposal exists. After that it
  is "Change records" when the model does not change, and "Change this model" when it does.
- **Model summary:** with no workbook, the summary says "No change to the model", or "No type, attribute or
  relationship changes" for a draft that changes only views or layout.
- **Partial move:** the proposal describes the steps accepting prepares. Accepting prepares a release with
  the old types beside the new ones, a change set that moves the records, and the final release. The
  removal note says the records move, not that they are deleted. The engine finds the final release itself.
- **"Accept the model" in the journey bar:** it takes you to the page's Accept button.

The implementer named these guide sentences as now wrong or incomplete:

- `guide/use/load-a-workbook-with-the-assistant.md`: the counts list ("…new relationships, refused items and
  rows read") should say that new relationships include the links of new records to their parents, and the
  loaded counts equal the checked counts.
- `guide/use/change-records-with-the-assistant.md` and `guide/model/review-an-assistants-workbook-design.md`:
  what "Show the model change" says for a task with no workbook.
- `guide/model/change-a-model-with-the-assistant.md`, "Finish a partial move": what the proposal says and
  what accepting prepares.
- Any page naming a words task's heading.

## What to do

- Fix every reader finding that the pages can fix, in the page where the reader got stuck: 1 (the workbook
  load's publication offers a combined migrate-and-publish, not a separate activation first), 3 (the
  button reads "Accept and load to change set"), 5 (where the example workbook is offered on the assistant
  route), 11 (the contradiction on whether an assistant load leaves a saved import profile: the code decides),
  and the sentences above. Check each fix against the product: the code wins.
- Finding 12 was the reader's setup: an assistant that signs in listens on its registered return address.
  If `guide/integrate/connect-an-assistant` does not say so plainly, add one sentence.
- A finding that is still a product defect: list it in the report with the evidence; do not work around it.
- A finding you judge wrong: say why.
- No new pages unless a finding cannot be fixed without one; no new pictures. A picture that no longer
  matches the product after these fixes: list it in the report.

## Files you may edit

- `src/content/docs/**/*.md`
- `src/content/docs/**/*.mdx`
- `_coverage/notes/C11-FIX3/**`
- `_waves/progress/C11-FIX3.md`

## Report

Per finding (C11-READER2-AI 1–15) and per sentence named above: fixed (page and what changed), a product
defect (evidence), or not changed (why). Then the pictures that no longer match.
