# RV-REFUSED progress

## 2026-11-10T15:03:18+01:00 — bulk-change browser guide

Finished `guide/src/content/docs/guide/use/change-relationship-values-in-bulk.md`: preview and refused Apply now explain record-pair labels, duplicate suppression, missing-name fallback and the five-line display limit. Checked the existing preview picture; it shows no refusal and still matches. No steering file exists; no corrections to apply. The wave says every refusal is listed, but the code shows only the first five; documented the code.

## 2026-11-10T15:03:33+01:00 — relationships tables

Finished `guide/src/content/docs/use/relationship-tables.md`: the refused-write passage explains pair names, message-only fallback, repeated-reason suppression and the five-line limit specifically for the grid bulk dialog. Kept single-cell and rows-layout behavior unchanged; both existing table/grid pictures still match the passages they illustrate. No steering file exists; no corrections to apply. No additional uncertainty.

## 2026-11-10T15:04:00+01:00 — bulk-change integration guide

Finished `guide/src/content/docs/guide/integrate/submit-a-bulk-change.md`: grid dry runs and refused applies reconcile pairs using endpoint IDs; direct batches also use those IDs when the relationship exists, falling back to index and relationship ID when absent. Kept the atomicity, status codes, limits, version rules and request/preview examples unchanged. No steering file exists; no corrections to apply. `docs/API.md` omits the new endpoint IDs and the named changelog entry is absent in this checkout; the verified implementation is the source for these edits.

## 2026-11-10T15:04:24+01:00 — validation complete

Reviewed the final diff of all three assigned pages. `GUIDE_OUT=_build/RV-REFUSED npm run build` passed: 257 pages, 3.60 seconds; it warned of competing `/404` routes. `git diff --check` for the three pages passed. No steering file exists; no corrections to apply. No pictures need replacement or addition. Remaining evidence limits: checked source and existing pictures, not a running refusal scenario; the UI displays only five refusal lines, the API prose omits the new endpoint fields, and the wave's named changelog entry is absent. No application code, other pages or commits changed by this wave.
