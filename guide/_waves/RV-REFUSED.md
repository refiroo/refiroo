# RV-REFUSED guide: a refused grid change names its relationships

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

`test:browser:rv` found (2026-11-10) that the relationships grid's **Change relationship values** dialog listed
the engine's refusal messages without saying which relationship each belonged to (two identical lines for two
pairs). Fixed in the product (CHANGELOG, Unreleased, "Fixed (a refused grid change names its relationships, 0.13 FX)").
Check the pages below against it. The code wins: `frontend/src/features/objects/RelationGridChangeDialog.tsx`
(`refusalLines`), `frontend/src/features/objects/RelationGridView.tsx`, `backend/app/engine/records/relation_batch.py`
(`decide_relation_values`), `docs/API.md` ("Relationships grid (RG)" and the batch route), `../CHANGELOG.md`.

## What the product does now (check each point in the code)

- In the dialog, the preview's refusals ("N would be refused, so nothing can be changed yet") and the notice
  after a refused Apply ("Nothing was changed") each list one line per refused relationship, written as the two
  records' names as the grid shows them, an arrow, then the engine's message: "Stop A → Operator B: …". The same
  relationship refused for the same reason appears once, and the number in the title counts those lines. When a
  record's name is not known to the dialog (a row the grid has not read), the line is the message alone.
- The API's refused items (a dry run's `refused`, and `details.items` of `RELATION_BATCH_REFUSED` from
  `POST /relations/batch` and `POST /relations/grid-change`) of an existing relationship now carry
  `fromObjectId` and `toObjectId` beside `index`, `relationId`, `code`, `message` and `details`; an item for a
  new link carried them already, with `relationId` null.

## What to do

- Fix each passage that no longer matches, in its page. Keep each page's voice and structure; change what is
  wrong or missing, not what is right. Candidates: `guide/use/change-relationship-values-in-bulk.md` (the step
  that reads every refusal, and "Nothing was changed"), `use/relationship-tables.md` ("A refused write …"),
  `guide/integrate/submit-a-bulk-change.md` (the refusal paragraph and the step that reconciles `details.items`).
- No new pages; no new pictures. A picture that no longer matches: list it in the report (name and page).
- A point the guide cannot describe honestly: list it in the report with the evidence.

## Files you may edit

- `src/content/docs/guide/use/change-relationship-values-in-bulk.md`
- `src/content/docs/use/relationship-tables.md`
- `src/content/docs/guide/integrate/submit-a-bulk-change.md`
- `_waves/progress/RV-REFUSED.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures
that no longer match, and any product point the guide cannot describe honestly.
