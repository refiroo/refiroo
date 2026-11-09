# RV-GUIDE-FIX: the reference model now carries relationship values

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`, then `_waves/RV-GUIDE.md` (the wave that wrote the
relationship-attribute pages). The code and the running reference instance win over every page.

**What changed since RV-GUIDE.** The guide's reference model (`guide/samples/model.json`, release
`guide-reference-swiss` 1.8.1, workspace `graubuenden`, loaded by `samples/load.py` with
`samples/data/reference/relation-values.json`) now has:
- attribute types `local-name` (text), `is-primary` (Yes/no), `inspected-on` (date), `confirmed` (Yes/no),
  `mapping-note` (text);
- "Operated by" (Stop → Operator) carries `local-name`, `is-primary`, `inspected-on`; "Maps to" (System code →
  Municipality, the binding of the `municipalities-by-system` matrix) carries `confirmed`, `mapping-note`;
- in the Network application, the view `stop-operators` (relationships table, grid layout) and
  `stop-operators-rows` (rows layout, grouped by the operator);
- the Stops API's `operator` related block also returns `localName` (`relation:local-name`) and `isPrimary`
  (`relation:is-primary`), null where a relationship has no value. This stays in the reference contract
  (decision: it demonstrates the feature; an added field is a compatible change).
The seven screenshots in `public/screens/` (see `_waves/RV-GUIDE.screens.json`, each `shows` field) were
taken from that state.

**Do:**
1. Remove every statement that the reference model has no relationship attributes, no `stop-operators` view
   or no `is-primary`, and every "illustrative/extension" framing that is now real. Use the real reference
   names and values (read them from `samples/model.json` and `samples/data/reference/relation-values.json`, and
   from the running reference instance). Known places: `integrate/consumer-apis.md` (around "the shipped
   reference model has no…", the `stops v2` extension, the worked "Tschamut-Selva" values),
   `integrate/submit-a-bulk-change.md` (around lines 61 and 144), `integrate/relationships-and-their-values.md`,
   `use/relationship-tables.md`, and any other RV-GUIDE page saying so.
2. Refresh captured Stops API response bodies that now lack `localName` and `isPrimary` in the `operator`
   block: `integrate/reading-business-objects.md`, `integrate/looking-up-and-resolving.md`,
   `integrate/consumer-events-and-webhooks.md`, `integrate/consumer-apis.md`, `examples/the-consumer-api.md`.
   Capture real answers with `node guide/tools/live-requests.mjs` (see `tools/CODEX_TOOL.md`, "Live requests";
   add the requests you need to a new `_waves/RV-GUIDE-FIX.requests.json`) and copy them exactly; never invent
   a body.
3. Captions and text next to the seven new screenshots must say what the image shows (the `shows` fields):
   the record-page screen is the Rhätische Bahn operator's "Stops operated" panel; the matrix cell shows one
   code with Confirmed ticked and the Note editor open (not several records); the grid screen has 2 stops
   ticked with the selection bar; the change preview reads "Would change 6, Already Yes 4, Not linked to the
   operator 10"; the Layout and the field-picker screens show the choices as an open list.
Keep everything else as it is.

## Files you may edit

- `src/content/docs/integrate/consumer-apis.md`
- `src/content/docs/integrate/submit-a-bulk-change.md`
- `src/content/docs/guide/integrate/submit-a-bulk-change.md`
- `src/content/docs/integrate/relationships-and-their-values.md`
- `src/content/docs/integrate/reading-business-objects.md`
- `src/content/docs/integrate/looking-up-and-resolving.md`
- `src/content/docs/integrate/consumer-events-and-webhooks.md`
- `src/content/docs/examples/the-consumer-api.md`
- `src/content/docs/use/relationship-tables.md`
- `src/content/docs/use/relationships.md`
- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/guide/use/fill-in-a-relation-matrix.md`
- `src/content/docs/guide/use/change-relationship-values-in-bulk.md`
- `src/content/docs/guide/model/add-a-relationships-table.md`
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/model/types-attributes-relations.md`
- `_waves/RV-GUIDE-FIX.requests.json`
- `_coverage/live/**`
- `_coverage/notes/RV-GUIDE-FIX/**`

## Report

Pages changed, each statement corrected, the requests captured, and anything you could not confirm.
