# ALT-ASSIST: the alt text and caption of the retaken picture `use-assistant-proposal`

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

DOC10 retook `use-assistant-proposal` on 2026-11-10 from the reference instance (a checked workbook proposal,
nothing accepted). Two pages still describe the old picture as "formatted notes, assumed answers and the start of
the type summary". The picture now shows something else. The picture is `public/screens/use-assistant-proposal.png`;
look at it before you write.

## What the picture shows now

The workbook proposal of the reference data (the file Haltestellen_Busbetrieb_Nord.xlsx), scrolled down:

- At the top, the task's progress bar with **Model proposal** as the current step, and the button
  **Accept and load to change set** pinned beside the sentence "Read the proposed model. Correct it in words, or
  accept it; nothing is loaded before."
- The end of the list of types the proposal adds or changes (the last lines are Tariff network and Tariff zone),
  the line "Nothing is installed or loaded before you accept." and the button **Show the model change** (folded).
- **What the load does**: the sentence "The engine checked every record and relationship below against the model and
  your data, writing nothing. Accepting loads exactly this.", five figures (168 records new, 0 existing records
  matched, 290 relationships new with links to parents, 0 refused, 106 rows read from 28 sheets), and a table per
  type with the columns Type, New, Matched, Changed, Refused and Linked to, one folded row per type (Platform,
  Stop, System code, Name translation, Line, Municipality, Tariff zone, System, Tariff network). Under the table, a
  line of the new relationships by name, and the folded **Where each part of the file goes**.
- **Questions**: the assistant's assumed answer, marked, with the other choices beside it.
- The bar that says what **Accept and load to change set** does (the engine installs the model and loads exactly the
  records above into a new change set; no assistant turn; nothing published), with **Give the assistant other words**.
- The assistant's own notes are not in this picture's frame. A note is shown as formatted text: paragraphs, lists,
  bold, code and, since 0.13 FX, a markdown table as a table (`frontend/src/ui/AssistantText.tsx`). Do not
  describe notes as visible in this picture.

The second picture of the same task, `model-assistant-workbook-proposal` (on `guide/model/review-an-assistants-workbook-design.md`,
not yours to edit), shows the proposal text, the opened **The model: what changes** table (marked Proposed) and
the start of **What the load does**.

## What to do

1. In `src/content/docs/use/loading-with-the-assistant.md` (the picture near line 71 and the text around it) and
   `src/content/docs/journeys/work-with-an-assistant.md` (the picture near line 67 and its caption), replace the
   alt text and the italic caption so they say only what the picture shows (above), in the pages' own words and
   style. Keep alt text one sentence, the caption two or three. Name the figures only if the page's text already
   does; the example's figures may change on a retake.
2. Check the sentence before and after each picture: if one claims the picture shows "formatted notes" or
   "assumed answers" as its main content, fix it. Change nothing else on either page.
3. Check against the product: `frontend/src/features/ai-tasks/ModelProposal.tsx`, `DesignView.tsx` (the labels:
   "What the load does", "Where each part of the file goes", "Show the model change") and the picture itself.
   The code wins; the picture is the evidence for what is visible.

## Files you may edit

- `src/content/docs/use/loading-with-the-assistant.md`
- `src/content/docs/journeys/work-with-an-assistant.md`
- `_waves/progress/ALT-ASSIST.md`

## Checks

Run `npm run build` in `guide/`; it must pass. `node tools/codex-wave.mjs check ALT-ASSIST` runs `npm run verify` and
the link check.

## Report

The two alt texts and captions as written, any sentence changed beside them, and anything on either page that looked
wrong (listed, not fixed).
