# RV-GUIDE-FIX report

15 pages changed. All paths below are relative to `guide/src/content/docs/`.

| Page | Statements corrected |
| --- | --- |
| `integrate/consumer-apis.md` | The reference model carries relationship attributes and the v1 operator block exposes localName and isPrimary. Replaced the hypothetical small v2 declaration and fictional FO contact values, object/list/XREF/Resolve/event bodies and webhook body with the actual v1 declaration, captured Palüds (B) object and links to captured existing examples. Tschamut-Selva has null values; Palüds (B) has Station office and true. Clarified that relationship-value filters and lookup rules are available but not declared in this reference contract. Kept the accurate limitation that the reference event watches main fields only. The side-by-side object table now reflects HTTP captures. |
| `integrate/reading-business-objects.md` | Refreshed the complete object and both list bodies, including localName and isPrimary; refreshed matching GET/conditional ETags and verified 304. |
| `integrate/looking-up-and-resolving.md` | Refreshed complete XREF page, crosswalk answer and Resolve body to include the current operator block. |
| `integrate/consumer-events-and-webhooks.md` | Refreshed the complete full event, including operator relationship outputs, event metadata and stateAt/headPosition 8986; corrected the surrounding position explanation. Existing separate identity-webhook example is unchanged. |
| `examples/the-consumer-api.md` | Corrected the Stops declaration excerpt and refreshed object, two lists, XREF, Resolve and identity event bodies. Updated GET/conditional ETags and the event-head explanation. |
| `guide/integrate/submit-a-bulk-change.md` | stop-operators and is-primary exist in the reference model. Named all three carried fields, replaced extension framing and confirmed the exact one-change preview with a live dry run. |
| `use/relationship-tables.md` | The reference connection actually carries the inspection date, Local name and Primary contact. Added captions describing the filtered rows and counted operator groups, and the grid with two stops selected, selection bar, linked counts and + Link. |
| `use/relationships.md` | The new screenshot shows the Rhätische Bahn operator's Stops operated panel, filtered to Chur W, with Chur West's Customer counter value and the Display groups; it is not a stop record's operator panel. |
| `use/relation-matrices.md` | The new cell screenshot contains one Schmitten (GR) code Q65399, Confirmed ticked and the Note editor open, rather than several records. |
| `guide/use/fill-in-a-relation-matrix.md` | Added the same precise single-code cell caption and explained that the values belong to its municipality connection. |
| `guide/use/change-relationship-values-in-bulk.md` | Caption names 10 selected stops, All 2 shown operators, Primary contact Yes, Would change 6, Already Yes 4, Not linked to the operator 10, Also link them unticked and six existing connections to change. |
| `guide/model/add-a-relationships-table.md` | Caption describes the unapplied Stop-to-Operator dialog and Layout as an open list with both choices and Grid selected. |
| `model/consumer-apis.md` | Replaced worked-extension wording with reference-example wording. Caption describes the unapplied operatorLinks field picker, its open source list and all three relationship choices, with Primary contact selected. |
| `guide/model/define-a-consumer-api.md` | Added the same precise open-list field-picker caption, including direction, output names and source groups. |
| `model/types-attributes-relations.md` | Replaced optional-addition framing with the actual Operated by and Maps to pairs and their five named carried attributes. |

## Captures

`guide/_waves/RV-GUIDE-FIX.requests.json` lists 20 requests, all captured successfully with `node guide/tools/live-requests.mjs`: four object reads (Tschamut-Selva twice, its operator and Palüds (B)), four list reads, three XREF/crosswalk reads, two Resolve reads, two event reads, the consumer index and generated OpenAPI, one grid-change dry run and two conditional reads returning 304. Files have the unique `rv-guide-fix--` prefix under `guide/_coverage/live/`.

The runner requires its write flag for the grid-change route, but the only such request had dryRun true. No apply, subscription write or webhook delivery was sent. Fifteen complete JSON bodies on the pages were checked for parsed equality with their live captures. All seven supplied screenshots were visually inspected; none is missing or needs replacement.

## Validation and limits

`GUIDE_OUT=_build/RV-GUIDE-FIX npm run verify` passed in guide/: build, terms, brand, coverage and links (257 built pages, 0 uncovered coverage rows). An initial build invocation from the repository root failed because that directory has no package.json; the correctly located build passed. Astro emitted a duplicate /404 route warning; it did not fail the build and was not investigated in this scoped correction.

The listed `integrate/submit-a-bulk-change.md` does not exist; the actual task page is `guide/integrate/submit-a-bulk-change.md`, which was corrected. `integrate/relationships-and-their-values.md` was read and contains none of the obsolete reference-model claims, so it needed no change. No outstanding uncertainty about the requested corrections remains. Mutating API behavior, relationship-triggered event delivery and model activation were not exercised. The reference event's main-fields-only watch remains explicitly documented.

No steering file existed at any unit boundary. No commits or git state changes were made.
