# C10 captions: the new pictures and the words-only proposal

Read `guide/AGENTS.md`. Readers: the guide's readers (people who use, model and administer refiroo).

## Why

Rounds 5 to 8 of C10 took the pictures listed below on the reference instance; every image is attached
to this turn. A caption or the sentence around an image must say only what the image shows, in the
page's words. The product also changed while the pictures were taken (the facts; the code wins:
`backend/app/engine/tasks/agent.py`, `frontend/src/features/ai-tasks/ModelProposal.tsx`, `CHANGELOG.md`
[Unreleased], "Fixed (the assistant in a container)"):

- **A words-only assistant task that needs no model change** now ends in a proposal without a model draft.
  The task page says "No change to the model.", says accepting prepares a change set and publishes
  nothing, and its button reads **Accept** (not "Accept the model"); "Show the model change" and the
  model editor button are not shown. On Accept the session makes the change set on the workspace's
  current release and installs nothing. With a model change, everything stays as before.
- "The model: what changes" on a proposal now lists what really changes (for example "FSO number becomes
  optional"), and the assistant's summary and notes show as formatted text.

## What to do

1. Check every attached image against each page that references it (grep `src/content/docs` for its
   name). Fix the caption (alt text and any caption line) and the nearest sentence when they say
   something the image does not show, or miss what a reader needs to see in it. Keep the rest of the
   page as it is.
2. Fix these lines for the words-only behaviour, without losing what they say for a task with a model
   change:
   - `guide/use/change-records-with-the-assistant.md`: step 5 ("Accept the model") and step 4's
     "inspect Show the model change".
   - `guide/use/continue-an-assistant-task.md` around line 19.
   - `use/loading-with-the-assistant.md` around line 77 ("Accept the model", and "install the necessary
     release": a words task with no model change installs nothing).
   - `journeys/work-with-an-assistant.md` around line 68.
   - Anything else under `src/content/docs/` a grep for "Accept the model" finds that a words-only task
     reaches. Pages only about workbook or model tasks stay.
3. No new pages, no new pictures, no other edits.

## Files you may edit

- `src/content/docs/**/*.md`
- `src/content/docs/**/*.mdx`
- `_coverage/notes/C10-CAPTIONS/**`
- `_waves/progress/C10-CAPTIONS.md`

## Report

Per page: what you changed and why. Any image that shows something wrong for its page (say what), and
anything unsure.
