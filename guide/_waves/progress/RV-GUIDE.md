
- 2026-11-09T21:58:42+01:00 — `model/types-attributes-relations.md`. Extended relationship concepts with carried value types, directed pairs, view surfaces and consumer exposure. No steering file present.

- 2026-11-09T21:58:42+01:00 — `guide/model/add-a-relationship.md`. Expanded Carries steps with direction, typed values and next steps for views and consumer APIs. No steering file present.

- 2026-11-09T21:59:13+01:00 — `guide/model/add-a-relationships-table.md`, `sidebar/model.mjs`. Added creation, directed ends, columns, layout changes and activation. Source confirms filters/sort/page size are derived defaults, not separate dialog fields; documented that distinction. No steering file present.

- 2026-11-09T22:00:07+01:00 — `use/relationships.md`. Documented carried-value columns after record fields, Display, no sorting by these columns and links to dedicated tables. No steering file present.

- 2026-11-09T22:00:07+01:00 — `use/records.md`. Clarified the panel columns without changing the record page instructions elsewhere. No steering file present.

- 2026-11-09T22:00:07+01:00 — `use/relation-matrices.md`. Replaced outdated direct-form behavior with cell tables, inline edits, filters, row unlinking, empty/read-only states and values on link/create. No steering file present.

- 2026-11-09T22:00:07+01:00 — `guide/use/fill-in-a-relation-matrix.md`. Revised populated-cell steps for table editing, keyboard actions and inline unlink confirmation; added carried values to create/link steps. Existing screenshots and captions retained as required. No steering file present.

- 2026-11-09T22:01:21+01:00 — `use/relationship-tables.md`, `guide/use/change-relationship-values-in-bulk.md`, `sidebar/use.mjs`. Added both layouts, row/column filters, selection, previews, all-or-none writes, proposed/read-only states and limits. JSON exclusions and the different rows-layout controls follow the code. No steering file present.

- 2026-11-09T22:02:42+01:00 — `model/consumer-apis.md`. Added carried values in related blocks, picker groups, typed nulls, per-connection filtering/XREF and event watch behavior. No steering file present.

- 2026-11-09T22:02:42+01:00 — `guide/model/define-a-consumer-api.md`. Extended related-field and matching steps and watch choices, with a screenshot request. Kept consumer examples free of source syntax for model administrators. No steering file present.

- 2026-11-09T22:04:10+01:00 — `integrate/consumer-apis.md`. Preserved earlier content and added a compiler-validated illustrative stops v2 declaration with full object/list/XREF/Resolve answers, typed values, validation, publication/date semantics and event/webhook bodies. No live HTTP capture is claimed; the reference model carries none. No steering file present.

- 2026-11-09T22:05:12+01:00 — `integrate/relationships-and-their-values.md`, `integrate/reading-business-objects.md`, `sidebar/integrate.mjs`. Added a separate management home to preserve the existing consumer-read page: edge/grid reads, paging, filters, versions, PATCH replacement versus batch merge and atomic refusals. Linked it from reading and navigation. No steering file present.

- 2026-11-09T22:05:58+01:00 — `guide/integrate/submit-a-bulk-change.md`. Added grid preview/apply, ID versus all-matching selection, exceptions, typed operators, linkMissing, change sets, limits and refusal recovery, plus known-ID atomic batch steps. Existing job guide remains intact and its distinct behavior is explicit. No steering file present.

- 2026-11-09T22:06:41+01:00 — Reviewed matrix descriptions and the new model guide against source labels. Corrected the full Relationships table kind label and removed remaining old Edit-action wording. No steering file present.

- 2026-11-09T22:08:42+01:00 — `_waves/screens-wanted/RV-GUIDE.md`, final source review. Recorded seven missing screenshots and their required states; preserved existing images. Found a model-editor edge case: selecting a carried JSON field also generates a forbidden JSON sort; compiler reproduction saved in notes, a reader workaround added to the model guide, no application code changed. Matrix refusals now quote “only one may count”. No steering file present.

- 2026-11-09T22:09:19+01:00 — Final validation and handoff. `GUIDE_OUT=_build/RV-GUIDE npm run build` passes (257 pages, 4.19 s); terms/brand pass; coverage passes (911 entries, zero uncovered), with only its generated report redirected to this wave's notes. Consumer model, 11 JSON fences and grid request forms validate. Final link check has nine missing-image references for seven requested captures; no page/anchor failures. No steering file appeared, no application/reference data changes were made, and no service was started. Detailed qualifications and the JSON-sort editor issue are in `_coverage/notes/RV-GUIDE/review.md`.
