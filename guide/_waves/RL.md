# RL: record pages and related columns in the model editor

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`. Reader: model administrators in the browser.
Package RL of 0.13 is delivered (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, section "RL: Record pages and
related columns in the model editor"). Three pages describe what it changed. Rewrite them from the sources
below; the code wins over the plan, and a fact that no source supports is not written.

**Pages:**

- `src/content/docs/guide/model/edit-a-record-page.md` (guide: Edit layout › Record page, now with Add panel…)
- `src/content/docs/guide/model/choose-table-columns-filters-and-sort.md` (guide: the table's Columns… now unfolds a relationship into fields of its records)
- `src/content/docs/model/record-pages-and-tables.md` (concept: the page a type gets, how panels and columns read relationships)

**What is new, as the delivered code does it** (check each statement in the files named under Sources):

1. **One rule for the page a type gets.** The same rule makes the page a new type gets, the page
   **Declare its page** writes, the page a newly allowed relationship adds to, and the page refiroo draws
   for a type whose application declares none. Side: a **Details** panel with the type's fields and, when
   the type has a parent, **Hierarchy**. Main: one panel for the contained types (titled with their plural
   name), then one relations panel for each relationship the type holds, in each direction, in the order
   the model lists them; containment is not one of them (the hierarchy shows it). A panel's title is the
   relationship's name read from this type: its name where the type is at the `from` end, its reverse name
   where it is at the `to` end. Its columns: Name; the parent type the related records sit under, when
   all the related types sit under one (for example System for system codes, Language for translations);
   up to four of the related type's fields; and the record's type when the panel lists several types. The
   relationship column is not shown, since the title says it. A panel that lists one type with a parent
   column is sorted by that column.
2. **A new relationship gets its own panel** on the declared pages of both its types, and a column and a
   filter for it on both types' tables; removing the relationship, or undoing it, takes them away again.
   A page someone wrote by hand is never rewritten: the rule applies to a new page, a new relationship and
   the undeclared page. A model that wants the new panels on an existing page uses Add panel…
3. **Add panel…** is a button beside **New field group** at the foot of the Main region in Edit layout ›
   Record page. The dialog "Add panel" asks: **What the panel shows**: Related records, Contained records
   (offered only for a type that contains types its application lists) or Fields (a field group, as New
   field group). For Related records: **Relationship**, a list of the type's relationships in both
   directions, named as read from the type, with "(on the page)" after those a panel already lists, and a
   line under it naming the columns the panel will get ("Columns: Name, System, External code,
   Description. Change them afterwards with the panel's Columns…."). For Contained records: the contained
   types to show. **Region**: Main or Side. **Title**: filled from the choice and changeable. Apply adds the
   panel as one step in the draft (undone with Undo). The panel is built by the server, so every client gets the
   same one. Its columns are changed afterwards with the panel's **Columns…**.
4. **The table's Columns… dialog.** Each relationship in the list (for example Served by mode, Has name
   translation) has a disclosure "Fields of <relationship>" under it. Opened, it lists the fields of the
   records at the other end (their attributes) and, under headings "Where they sit · <type>" (for example
   Language), the name and the attributes of each type those records can sit under. A checked field is a
   column of its own, headed with the relationship and the field ("Has name translation · Language code");
   each cell shows the related record's value, "—" where it has none. Such a column does not sort. The
   relationship itself stays a column of its own. **Filters…** still offers only the relationship, not its
   fields. A field that holds JSON is not offered.
5. **A panel's Columns… dialog** (Record page, the panel's menu › Columns…) now also offers, under the
   heading **Where it sits**, a column for each type the listed records can stand under (headed with that
   type's name, showing the ancestor's name) and **Type** when the panel lists several types. A field of an
   ancestor (`ancestor:<type>.<field>`) is not a panel column; it is only a table's related column (item 4).
6. **Draft operation `addPanel`** (API): `applicationKey`, `detail`, `show` (`relations` with `relation`
   and `direction`, or `children` with `objectTypeKeys`), `region`, `title`, optional `key`; undone by
   `removeViewItem`; refused for a relationship the type does not hold in that direction
   (`unknownElement`), a contained type the application does not list or the type does not contain
   (`invalidValue`) and a given `key` the page already uses (`keyTaken`).

**What stays as it was:** moving, hiding, renaming and removing panels, field groups, a panel's Sort, the
table's Filters… and Default sort, and the rule that a relationship's own fields (stored on the link) cannot
be columns.

**Sources:**

- `docs/BASE_0_13_IMPLEMENTATION_PLAN.md` section "RL" (the plan; its "Delivered" note says where the code differs)
- `CHANGELOG.md` [Unreleased], "record pages and related columns in the model editor"
- `docs/API.md` (the draft operations table, `addPanel`; "A type without a detail page")
- `docs/APPLICATION_MODEL.md` (panels, columns, `related:<key>.<field>`)
- `frontend/src/features/model-editor/layout.ts` (`addPanelSpec`, `tableColumnsSpec`, `panelColumnsSpec`,
  `relatedFieldChoices`, `whereItSits`), `OperationDialog.tsx` (`CheckboxList`), `TypePreview.tsx` (the buttons)
- `frontend/src/model/defaults.ts` (the page rule in the browser), `backend/app/engine/model/authoring/layout.py`
  (`detail_page`, `relations_panel`, `place_relation`) and `kinds.py` (`addPanel`)
- `prototypes/record-layout-editor/index.html` (the approved mock-up; its labels are illustrative, the code's labels win)
- the example model the guide uses, `samples/model.json`, type Stop, for examples: its relationships are
  Served by mode, Operated by, Is represented by system code and Has name translation; the system codes
  sit under System and the translations under Language.

Keep each page in its kind's template. The concept page says what the page rule is and why (one rule, so
the page a type gets never depends on where it came from); the guides take one task step by step with the
buttons as shown. Link the guides and the concept page to each other. Do not describe AI features. Add
screens the pages need to `_waves/screens-wanted/RL.md` (name, page, the screen and its state, what must be
visible): Add panel… with a relationship chosen, the table's Columns… with Has name translation unfolded,
a panel's Columns… with Where it sits, and the Stop record page with a panel per relationship.

## Files you may edit

- `src/content/docs/guide/model/edit-a-record-page.md`
- `src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`
- `src/content/docs/model/record-pages-and-tables.md`
- `_waves/screens-wanted/RL.md`
- `_coverage/notes/RL/**` (working notes)

## Report

As `COMPLETE-COMMON.md` says. Also list each statement above you could not confirm in the sources, and
anything on the three pages that no longer matches the product and that you could not fix inside the allowed files.
