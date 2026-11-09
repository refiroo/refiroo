# RV-GUIDE: values stored on a relationship, everywhere they show

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md` (its rules on depth, sources, screenshots and the
sidebar apply; the coverage-file rule applies only if a coverage file lists these items). The code wins over
this brief, and a fact that no source supports is not written.

**The capability.** A relation type's binding can carry attributes of its own (`attributeTypeKeys`): values
that belong to the relationship between two records, not to either record (for example, on the link
between a person and a site: "since", "role there", "primary"). 0.13 makes them visible and editable
everywhere relationships appear, and readable through consumer APIs. This is one of the product's strongest
features; document it fully, at working depth, for each reader, in the pages' own style.

**Never name the example model of the development data** (its operators, timetables, locations, drivers or
its types). Use only the guide's own example data and examples already on the pages, or neutral ones.

## What to document (check every statement in the sources)

1. **Model** (readers: modellers). A relationship can carry attributes: where the editor sets them (the
   relation's binding, "carries"), which value types, that they are part of the binding's direction, how they
   reach the views and consumer APIs. Pages: `model/types-attributes-relations.md`,
   `guide/model/add-a-relationship.md` (a step for adding attributes to the relationship).
2. **Record page** (users). The Relationships panel shows the relationship's attributes as columns after
   the related record's, listed under "Attributes of the relationship" in Display; no sorting by them.
   Page: `use/relationships.md` (and `use/records.md` only if it describes the panel's columns).
3. **Relation matrix cell** (users). The cell dialog is a table: one row per linked record, the record's
   columns, then the tinted group "Attributes of the relationship"; every value edits where it stands
   (yes/no values are a checkbox that saves on one click; other values open a small editor over the cell,
   Enter saves, Esc cancels, a click outside closes an unchanged one); Open and Unlink per row, Unlink asks
   in the row; filter box; Link existing / Create; empty cell; read-only and publication cells; a stale save
   shows what someone else saved; "only one may count" refusals and "Open the … already here". Linking or
   creating in a cell takes the relationship's values. Pages: `use/relation-matrices.md`,
   `guide/use/fill-in-a-relation-matrix.md`.
4. **Relationships table view** (users and modellers) — new pages:
   - `use/relationship-tables.md` (concept, "About relationships tables"): the view type `relationTable`
     ("Relationships table") over one binding; its two layouts: **one row per relationship** (both records'
     columns and the attributes; filters, sort, group headings with counts, paging, cells edit in place,
     ticked rows set together) and **grid** (each `from` record once per row; each related `to` record a
     column group "<name> · n of m linked" with the relationship's attributes under it; not-linked groups
     hatched with + Link; both header rows stay while scrolling). Grid controls: the from type's own toolbar
     (the same search, filter bar and operators as that type's main view, plus every relationship attribute
     as a filter, matching a row when a relationship to a shown column record matches), the column-records
     menu (the to type's own toolbar plus a pick list, at most 50 groups shown, with the total), Display
     (fields and attributes shown; the name stays), choices kept in the page address and not shared with the
     main view; editing in place (yes/no one click); live, in a change set (marked as proposed) and in a
     publication (read-only). Who may edit.
   - `guide/use/change-relationship-values-in-bulk.md` (task): filter the grid, tick rows or "Select all N
     matching" (and untick exceptions), **Change relationship values**, choose the attribute, where (all
     shown or one), the value or Clear, read the preview (would change / already / not linked, "Also link
     them"), refusals and why Apply stays off, Apply; all or nothing; in a change set; size limit and what to
     do. Also the rows layout's ticked-rows change if it differs.
   - `guide/model/add-a-relationships-table.md` (task): add the view in the editor (the relationships-table
     step and its fields: relation, direction ends, columns, attribute columns, filters, sort, page size,
     **Layout**), change the layout later (**Layout…**), install as usual.
5. **Consumer APIs** (integrators and modellers). A related block publishes a relationship's value with
   the source `relation:<attribute>` in `object.related.<name>.fields` (null when none), in objects, lists,
   XREF and resolve answers, publication and `asOf` reads; its schema type; the refusals (`INVALID_REFERENCE`)
   and where the source is allowed; `matchOn` of `onRelated` filters and XREF `alsoMatchThrough.firstOf`
   may name it (an item matches through that relationship only; XREF reads text); the editor's group
   "Attributes of the relationship" in the field and matchOn pickers; events report a change of the
   relationship's values. Pages: `model/consumer-apis.md`, `guide/model/define-a-consumer-api.md`,
   `integrate/consumer-apis.md` (check what RA already wrote there and complete it; do not repeat).
6. **Management API** (integrators): reading and changing relationships' values — `PATCH /relations/{id}`
   (`attributes`, `expectedVersion`), `POST /relations/batch` (all or none, `RELATION_BATCH_REFUSED`), the
   edge list `GET /workspaces/{key}/relations` (`fromObjectId`, `toObjectId`, `sort`, `filter.<ref>.eq`,
   `seek`, `relationVersion`, `groupCounts`), the grid read `GET /workspaces/{key}/relation-grid` and the
   bulk change `POST /relations/grid-change` (selection, `allMatching` + `exceptObjectIds`, filters with
   operators, `dryRun`, `linkMissing`, change sets, 413/422 refusals). Page: `integrate/reading-business-objects.md`
   for reads and `guide/integrate/submit-a-bulk-change.md` for the bulk change, or one new page
   `integrate/relationships-and-their-values.md` if those pages cannot hold it without reorganising
   (then add it to `sidebar/integrate.mjs`). Request and response examples must match `docs/API.md` and
   the code.

Add the new pages to `sidebar/use.mjs` and `sidebar/model.mjs` next to the related entries ("About
relation matrices", "About relationships", "Add a relation matrix"). Link the pages to each other where a
reader would look next. Screens: reference existing ones only where they show the right state; for each
screen still needed (matrix cell table with an editor open, the grid with two header rows, the Change
relationship values dialog with its preview, the editor's Layout field, the consumer API field picker's
group), insert the image line and list it in `_waves/screens-wanted/RV-GUIDE.md`.

**What stays as it was:** every section not about this capability, existing screenshots and captions,
headings and order of existing sections.

**Sources:**

- `docs/API.md`, `docs/UI_MODEL.md`, `docs/APPLICATION_MODEL.md`, `docs/MODEL_AUTHORING.md`,
  `docs/CONSUMER_API.md`, `docs/product-functionality/CURRENT_FUNCTIONALITY.md`, `CHANGELOG.md` (blocks 0.13 RA
  and RV), `docs/BASE_0_13_IMPLEMENTATION_PLAN.md` (sections RA and RV, decisions RV-D…)
- `frontend/src/features/objects/RelationMatrixCellDialog.tsx`, `RelationMatrixCellTable.tsx`,
  `RelationTableView.tsx`, `RelationTableLayout.tsx`, `RelationGridView.tsx`, `RelationGridRow.tsx`,
  `RelationGridChangeDialog.tsx`, `RelationGridLocations.tsx`, `relations/` (labels exactly as shown),
  `frontend/src/ui/FlagCell.tsx`, `ui/FloatingCellEditor.tsx`, `ui/TableDisplay.tsx`
- `frontend/src/features/model-editor/relationTableView.ts`, `operations.ts` (the relationships-table step and
  Layout…), the consumer editor's field pickers (`frontend/src/features/model-editor/consumer*.ts*`)
- `backend/app/models/schema.py` (`RelationTableViewConfig`), `backend/app/engine/reads/relation_grid.py`,
  `relation_table.py`, `backend/app/engine/records/relation_grid_change.py`, `relation_batch.py`,
  `backend/app/management/routers/relations.py`, `mapping.py`, `backend/app/engine/reads/consumer_objects.py`,
  `backend/app/engine/model/validation/consumer_api_rules.py`

## Files you may edit

- `src/content/docs/model/types-attributes-relations.md`
- `src/content/docs/guide/model/add-a-relationship.md`
- `src/content/docs/guide/model/add-a-relationships-table.md` (new)
- `src/content/docs/use/relationships.md`
- `src/content/docs/use/records.md`
- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/guide/use/fill-in-a-relation-matrix.md`
- `src/content/docs/use/relationship-tables.md` (new)
- `src/content/docs/guide/use/change-relationship-values-in-bulk.md` (new)
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/integrate/consumer-apis.md`
- `src/content/docs/integrate/reading-business-objects.md`
- `src/content/docs/guide/integrate/submit-a-bulk-change.md`
- `src/content/docs/integrate/relationships-and-their-values.md` (new, only if needed)
- `sidebar/use.mjs`
- `sidebar/model.mjs`
- `sidebar/integrate.mjs`
- `_waves/screens-wanted/RV-GUIDE.md`
- `_coverage/notes/RV-GUIDE/**` (working notes)

## Report

As `COMPLETE-COMMON.md` says: pages changed and added, what each now covers, every statement above you could
not confirm in the sources, and the screens wanted.
