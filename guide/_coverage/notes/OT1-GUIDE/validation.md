# OT1-GUIDE validation

All 14 assigned pages were updated. Both supplied screenshots were visually reviewed; their existing paths are reused with captions describing the current states. No new screenshots are requested.

Source checks:
- `backend/app/engine/model/consumer_contract.py`: `type_holds_sources`, `type_holds_block`, `parent_blocks_held`, `object_outputs`, `_type_output_changes`.
- `backend/app/engine/reads/consumer_objects.py`: composition checks held outputs and parent blocks before returning them.
- `backend/app/engine/model/consumer_openapi.py`: per-type schemas, required properties, objectType discriminator and generated named examples (list limited to its own type).
- `backend/app/engine/model/consumer_examples.py` and `authoring/consumer_documents.py`: schema-derived placeholders, selected type and All types schema, unknown public-type error.
- `frontend/src/features/model-editor/ConsumerApis.tsx`: shared type state, searchable menu, copy/download and tab descriptions.

Checks:
- `GUIDE_OUT=_build/OT1-GUIDE npm run build`: passed; final prose build produced 259 pages in 3.80 seconds. Astro warns of a /404 route conflict; it does not fail the build. Build output is isolated as requested.
- `npm run check`: terms, branding and sidebar passed across 259 pages.
- `GUIDE_OUT=_build/OT1-GUIDE npm run check:links`: passed on the final built output, checking 77,247 local links and sources.
- Parsed all 32 fenced JSON blocks in the assigned pages and checked all 13 full Stop objects omit fsoNumber and sboid; all referenced screenshot files exist.
- Final whitespace review removed one trailing space introduced when splitting a paragraph. No rendered text changed.

Scope and limitations: documentation and source inspection only; no API requests, browser runner, application tests or reference-instance recapture were performed. Other examples and declaration sources were preserved. No unresolved product discrepancy was identified in the inspected paths. No git state-changing command or commit was made.
