# CA1 guide validation

- All six assigned pages completed; the worked example has one short addition only.
- New examples use a neutral illustrative catalogue. Existing reference captures are unchanged.
- Checked controls in ConsumerApis.tsx, consumer.ts and operations.ts; schema and expansion; parent and projection validation; output contracts and breaking-change checks; consumer object composition, request/include validation, filters and resolve; generated OpenAPI; event dependency planning; relevant docs/API.md and docs/CONSUMER_API.md sections and the CA1 changelog entry.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/CA1-GUIDE/check_examples.py` passes. It compiles the new declaration against a minimal matching model without a database and checks GET include enums and optional properties in the object and parent. It saves `catalogue-openapi.json` as evidence.
- `GUIDE_OUT=_build/CA1-GUIDE npm run build` in guide/ passes after the final page edit: 257 pages, 3.53 seconds. Build output is in build.log.
- Scoped `git diff --check` passes. All six pages have the required front matter; all 28 JSON fenced blocks parse. All six new section anchors exist in the built HTML.
- No browser, live HTTP, event delivery or screenshot capture was run. Request/answer additions are illustrative and source-checked, not captured. Broader pre-existing page content was left outside this wave's review.

## Parent attribute types

The generated OpenAPI describes a parent attribute in its declared value type, or null when the record's parent has no value or its type does not bind the attribute. The catalogue's named `isApproved` output reads the `approved` attribute and is boolean or null. Only the built-in `objectType` and `code` parent fields remain string-or-null. The integrator page and saved generated OpenAPI reflect the corrected behavior in `consumer_openapi.py`, `_fields`.

## Pictures still needed

1. `model-consumer-parent-fields.png`: Fields tab, parent enabled, Parent output name and selected attribute fields visible; Parent's related records shows Via, Fields and Served with an On request block.
2. `model-consumer-include.png`: Operations tab, Include section visible with both an object block and a `parent.<block>` choice, matching the Served selections.

All other screenshot files referenced by these six pages exist. No steer file was present at any unit boundary.

2026-11-11T15:15:48+00:00 — Rechecked the corrected parent attribute schema with check_examples.py and regenerated catalogue-openapi.json; boolean-or-null assertion passes. Rebuilt with `GUIDE_OUT=_build/CA1-GUIDE npm run build`; build passes. Screenshot references are unchanged.

2026-11-11T16:48:45+00:00 — Parent fields now use explicit output names and sources. Updated the catalogue declaration and response examples to publish approved as isApproved, documented full-form sources/defaults and short-list camelCase naming, and refreshed the generated schema. Compiler/OpenAPI checks, 28 JSON blocks, coverage, scoped whitespace and `GUIDE_OUT=_build/CA1-GUIDE npm run build` pass. No live HTTP checks were run; screenshot references are unchanged.
