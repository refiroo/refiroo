# C3b source checks

Read guide/AGENTS.md first, then the wave, COMPLETE-COMMON and C6 steering. The wave explicitly permits labelled consumer request/response examples on browser-facing model pages. No wave-specific steering file or previous progress existed at start.

- Existing three assigned pages read in full. Coverage read by consumer-related rows; the initial combined output was truncated, so later checks use targeted rows.
- guide/samples/model.json consumerApis block: stops v1 exposes stop, municipality, operator, mode; fields, related blocks, five lists and filters; custom stops-changed watches code/name/validFrom/validTo; per-type events are not enabled. No field defaults declared.
- guide/samples/README.md and reference data: Chur stop 745c1a52-8405-4158-8f3b-b9e9c8b979be, stop number 8509000, code ch:1:sloid:9000, parent Chur, district Plessur, operator SBB; no translation records for this stop. Municipality translations must not be attributed to the stop.
- frontend/src/features/model-editor/ConsumerApis.tsx: field and document labels; generated Message example uses values from types, never live records. Screens inspected: fields, operations, filters; existing screenshots show actual Stops API declaration.
- frontend/src/features/settings/ConsumerApisPage.tsx: Settings / Integration / Consumer APIs shows active release, Base URL, OpenAPI document, routes; no draft document tabs.
- backend/app/consumer/router.py: declared routes, workspace and grant checks, version resolution; consumer data needs consumer token and a grant; OpenAPI document does not need authentication.
- backend/app/engine/reads/consumer_objects.py: shared object and related cardinalities, defaults then null, parent/path shape. consumer_lists.py: items envelope; consumer_xref.py: results envelope or bare object plus matchScore with expect=one. consumer_resolve.py: per-item outcomes/counts. consumer_events.py: event items and payload choices.
- Tests inspected: journeys/test_j28_consumer_read.py shared object assertions, test_j30_consumer_events.py event fields and watched changes. Further checks recorded with later units.

Examples are source-derived illustrations, not captured live API responses. No reference instance or backend tests run for this writing task.

Offline verification: compiled the reference model and generated current OpenAPI, object schema and message example using backend/.venv/bin/python with bytecode writes disabled. Full Chur illustration and generated example both validate with Draft202012Validator. All model-page JSON fences parse. The generated example chooses Mode and placeholder stopNumber 1; it demonstrates schema shape, not realistic data. Scoped stops list generated municipality parameter explicitly takes object IDs; all-stops ordinary municipality filter accepts FSO number. No API request was executed.
