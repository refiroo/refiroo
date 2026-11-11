# CA1 guide progress

2026-11-11T15:06:39+00:00 — Finished `guide/src/content/docs/model/consumer-apis.md`. Explains parent values and related blocks, Served, filter effects, compatibility and child event updates; adds a Parent screenshot request. Checked editor and engine code; ancestor sources need specialist editing. No steer file exists.

2026-11-11T15:07:09+00:00 — Finished `guide/src/content/docs/guide/model/define-a-consumer-api.md`. Added the parent task, exact control locations, Served and Include review, parent filters, compatibility and notification consequences. Ancestor selection is described as specialist-only; screenshots still needed. No steer file exists.

2026-11-11T15:08:03+00:00 — Finished `guide/src/content/docs/integrate/consumer-apis.md`. Added an illustrative catalogue declaration and the parent/source, include, filter, OpenAPI, event and versioning rules; corrected the existing summary and reserved-name list. Checked against schema, expansion, validation, composition, OpenAPI and event code; requests are illustrative rather than captured. No steer file exists.

2026-11-11T15:08:41+00:00 — Finished `guide/src/content/docs/integrate/reading-business-objects.md`. Added complete illustrative object reads with absent and included object/parent blocks, plus a parent-filtered list request, empty/null rules and UNKNOWN_INCLUDE recovery. Saved include choices with the read checkpoint; source-checked examples await the final consistency check. No steer file exists.

2026-11-11T15:09:20+00:00 — Finished `guide/src/content/docs/integrate/looking-up-and-resolving.md`. Added XREF includes and a complete illustrative Resolve request/answer showing inherited includes, an empty per-item override, typed parent values and item rejection recovery. Checked router parsing and engine resolution; examples are not live captures. No steer file exists.

2026-11-11T15:09:42+00:00 — Finished `guide/src/content/docs/examples/the-consumer-api.md`. Added one short explanation beside the existing parent answer, linking to optional parent values and blocks without changing the captured example. Checked guide/samples/model.json: the parent selects four built-ins and related blocks default to always. No steer file exists.

2026-11-11T15:11:27+00:00 — Finished consistency review of the authoring pages and integrator declaration. Corrected the existing parent-control location and exact checkbox wording; the illustrative declaration compiles and generated OpenAPI confirms optional blocks and include names. Generated OpenAPI evidence is saved under guide/_coverage/notes/CA1-GUIDE/; parent attribute types were refreshed after the code correction recorded below. No steer file exists.

2026-11-11T15:12:35+00:00 — Finished final validation of all six pages. Isolated guide build passes (257 pages, 3.53 s); catalogue compilation, generated include enums and optional properties, all 28 JSON blocks, new built anchors and scoped whitespace checks pass. Two screenshots remain; no live HTTP/browser/event checks were run. Parent attribute typing documentation and evidence were refreshed after the code correction recorded below. No steer file exists.

2026-11-11T15:15:48+00:00 — Updated `guide/src/content/docs/integrate/consumer-apis.md` after the OpenAPI fix: parent attributes use their declared value type or null when missing or unbound. Removed the outdated limitation from progress and validation notes, regenerated catalogue OpenAPI evidence, and checked the boolean-or-null schema. The isolated guide build passes; both screenshot references are unchanged. No steer file exists.

2026-11-11T15:16:44+00:00 — Updated `guide/src/content/docs/guide/model/define-a-consumer-api.md` to name the consumer API ⋯ menu entry **Add related to the parent…** alongside the Parent section’s **Add related** button in one sentence. Both open the same dialog; screenshot references are unchanged. No steer file exists.

2026-11-11T15:16:58+00:00 — Validation passes: `node tools/check.mjs coverage` reports zero uncovered entries across 257 pages; `GUIDE_OUT=_build/CA1-GUIDE npm run build` also passes.

2026-11-11T16:48:02+00:00 — Updated `guide/src/content/docs/model/consumer-apis.md`. Corrected parent output naming, the editable name/source rows, table display and short-list camelCase rule. No steer file exists.

2026-11-11T16:48:02+00:00 — Updated `guide/src/content/docs/guide/model/define-a-consumer-api.md`. Replaced attribute-key wording with editable public names and sources, table display and short-list behavior; preserved the menu/button sentence and screenshots. No steer file exists.

2026-11-11T16:48:02+00:00 — Updated `guide/src/content/docs/integrate/consumer-apis.md`. Updated both summaries, full named-field declaration, ordered sources/defaults, authored error path and list-form camelCase rule. No steer file exists.

2026-11-11T16:48:02+00:00 — Updated `guide/src/content/docs/integrate/reading-business-objects.md`. Changed the illustrative parent answers to isApproved, explicitly linked to the stored approved source. No steer file exists.

2026-11-11T16:48:02+00:00 — Updated `guide/src/content/docs/integrate/looking-up-and-resolving.md`. Changed the illustrative parent answers to isApproved, explicitly linked to the stored approved source. No steer file exists.

2026-11-11T16:48:45+00:00 — Finished validation of the named parent-field corrections across five pages. The full catalogue declaration compiles and generated OpenAPI exposes isApproved as boolean-or-null; all 28 JSON blocks parse, coverage reports zero uncovered entries, scoped whitespace checks and the isolated guide build pass. Refreshed working evidence; the worked example and both screenshot references remain unchanged.

