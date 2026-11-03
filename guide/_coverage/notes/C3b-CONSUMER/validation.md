# Validation and remaining work

- `GUIDE_OUT=_build/C3b-CONSUMER npm run verify` in guide/: build passed (200 built pages, 2.98 s); terminology and brand checks passed (199 content pages). Links failed with 34 problems in this build snapshot.
- One failure belongs to this wave: required placeholder `/docs/screens/model-consumer-active-documents.png`. Capture requested in the wave screens-wanted file. Image creation is outside the permitted file list.
- Other 33 failures belong to other pages: missing screenshots, missing webhook/mail guide targets, and an Integrate lookup anchor. See verify.log. No out-of-scope files were edited to silence them.
- No broken text link or anchor from these three pages was reported. Coverage anchors resolve in the built pages.
- Reference model compiled successfully; generated OpenAPI, object schema and synthetic example are retained in these notes. Full Chur illustration and generated example validate against the schema. Every JSON fence in the three assigned pages parses.
- Existing fields, filters, operations, schema and example screenshots were inspected. No live browser/API requests, backend test suite or application changes were part of this writing task. No server or database was started.
- No confirmed application defect found. The shared coverage row C3964 includes obsolete schema-0.8 transition history; its coverage now marks that part as retired, following the current journey catalogue.

## Coverage scope

23 consumer rows refined. No consumer row remains uncovered. Nine other model rows remain open in the shared file and were left untouched: C1650 (migration impact summary, belongs on model/migrations); C1781, C1782, C1789 (model task evidence awaiting reconciliation); C1871, C1872, C1874 (release/AI evidence awaiting reconciliation); C1950 (model editor review evidence awaiting reconciliation); C2168 (workbook profile evidence awaiting reconciliation). Their destination pages are outside this wave. Post-0.16 AI material remains unchanged.

## Source manifest supplement

Read USER_JOURNEYS J25 and J33.13/J33.14, CURRENT_FUNCTIONALITY F23 and editor/document passages, the glossary's terminology/lifecycle sections, and targeted consumer operations/grants material in OPERATIONS and PRODUCT. Some initial combined search/read outputs were truncated; payload examples rely on later targeted code reads and generated documents, not missing output. No broad product or architecture documents were loaded in full.
