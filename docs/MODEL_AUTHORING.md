# Model authoring and spreadsheet onboarding (Product 0.10)

Status: design direction accepted 2026-09-29 ([ADR-035](DECISIONS.md#adr-035--model-authoring-is-an-editor-of-operations-on-a-model-draft-a-spreadsheet-is-one-way-to-start-it)).
Decisions are listed at the end (A-D1 to A-D3 decided; A-D4 and A-D10 taken by 0.9 J2; A-D5 to A-D9 decided in 0.10 A0; A-D11 and A-D12 open but non-blocking). The packages, sequence and acceptance are in the
[Base 0.10 plan](BASE_0_10_IMPLEMENTATION_PLAN.md) (2026-10-11, the designer first); the
[roadmap](ROADMAP.md#product-release-010--model-authoring-and-spreadsheet-onboarding) places the
release after 0.9, whose import jobs (Track J) this design builds on.

## Product outcome

An administrator turns reference data that arrives in spreadsheets into a working application without
writing a model file or an import script. One editor serves both halves: it proposes a model and an
import mapping from the uploaded workbook, and the administrator renames, remaps and reorganizes both
freely, seeing the effect on the real rows after every change. The saved mapping loads the next
version of the same workbook as an upsert, reviewed in a change set.

The same editor, opened without a workbook, is the structured model designer planned for 1.0
([US-P05](product-functionality/USER_STORIES.md#us-p05--design-a-model-with-structured-tools)).

## Why

Reference data reaches the RDM mostly as spreadsheets of every size. Relationships between items are
flattened into single cells, repeated columns and several sheets. In the source system this engine
comes from, every upload is a small development project: someone aligns the model JSON by hand (with
LLM help), then writes a Python script that reads the workbook, matches it to the model and calls the
API. Uploading new reference data therefore needs both model engineering and importer engineering.

Three sample workbooks from that system (kept outside the repository) show the shapes this has to
handle. They are described here by shape only:

- **A flat table that packs structure into columns.** One row per record, with the parent repeated on
  every row together with its sort order and external ID, a lookup stored as text, a code and name pair
  that is really a separate list, several true/false columns and a text column that together express
  one relationship, external-system IDs, and a second sheet with one row per record and language.
- **A workbook that describes a model.** One sheet lists field code, field type and lookup target; every
  lookup has a sheet of its own with IDs and names. Some IDs are placeholders, some values are still to
  be decided, and names drift from the same IDs in the flat table.
- **A sheet laid out for reading.** Dozens of small lists placed side by side under section and group
  headers, some with a column per language, some with Y/N availability flags per list item, and notes
  such as "multiple answers" that are really cardinality.

The source system's model also shows the workarounds its limits forced: one generic "reference value"
type holding several unrelated lists, with each picklist filtered by the parent's *name*; a separate
relation type per target type and per direction; and a hand-written UI template per object type. The
engine already avoids the last two (one relation type with forward and reverse semantics and several
allowed pairs; generic detail panels). This design removes the reason for the first (A-D1).

## Principles

1. **Generic.** Patterns, operations and the editor know object types, attributes, relations, views and
   panels, never a domain. The translation, mapping and hierarchy patterns produce the same model
   structures as any hand-written model.
2. **An editor, not a wizard.** Inference writes a first draft. Everything after that is editing, and
   anything inference proposed can be renamed, remapped, split, merged, moved or removed.
3. **Every change is an operation.** The editor never writes model JSON directly. Each edit is an
   operation applied on the server to a model draft and its import profiles, validated by the same
   validators installation uses, and recorded in the draft's history.
4. **Feedback on real data.** After each operation the engine re-runs the import dry run on the
   uploaded rows and reports what changed: records, values, conflicts, unresolved references.
5. **The model lifecycle does not change.** The editor produces a model draft; installation creates an
   immutable release; activation selects it after the compatibility check. The editor offers install
   and activate as one confirmed step, and both still happen.
6. **Data arrives through the 0.9 import job, in a change set by default.** An onboarding load is
   reviewed on the existing change set review screen before it is published. A recurring load may
   target live data, as any 0.9 import may.
7. **Structured, not canvas-first, not pixels.** The editor shows structure as lists, trees and the
   relationship matrix. Drag and drop is a fast path; every drag has a menu and keyboard equivalent.
   Layout editing selects, orders and shows generic components; it never positions pixels
   ([UI_MODEL.md](UI_MODEL.md)).
8. **Stable keys.** Keys are free to change until an element is part of an installed release. After
   that, only its labels change freely; renaming its key is a migration.
9. **Not a general ETL tool.** Transformations are limited to the reference-data shapes below. A
   workbook that needs formulas, joins beyond key lookup or procedural logic uses the 0.9 bulk API
   directly.

## Concepts

- **Authoring draft.** A model draft (the existing `/model-drafts` resource) together with the import
  profiles and source files attached to it. Model and profiles change together, so a renamed type or a
  moved attribute never leaves a profile pointing at something that no longer exists.
- **Operation.** One typed edit: rename, remap, move, split, merge and so on (see the catalogue). Applied
  with the draft's expected version, validated, then appended to the draft's operation history.
- **Source file.** An uploaded workbook or CSV file, a resource of its own owned by a draft or a
  profile and kept in the job file directory (0.10 plan D5), with its checksum, and its **profile**: sheets, header rows, blocks, columns and their statistics.
- **Import profile.** The declarative mapping from a source file's sheets and columns to model elements.
  It is what the 0.9 import job executes, and it replaces the per-upload script.
- **Inference.** Detects patterns in a source profile and proposes operations. Asked for, it writes
  its proposals into the draft as steps of the history, one per proposal (0.10 A6, D89, D94); after
  that everything is editing, and each proposal can be undone, changed or replaced by its
  alternative.
- **Pinned decision.** An element the administrator has changed: any step other than a proposal's
  makes it theirs, for good. Re-running inference, or profiling a new version of the workbook, never
  overrides it; it reports disagreements. What is still the engine's (as a proposal step left it)
  may be revised by a later inference, each revision a step that can be undone (D92).
- **Dry run.** The 0.9 import preview, run on the source file with the current draft and profile. It
  writes nothing.

## The editor

### Starting points

- **From a workbook:** upload, confirm the sheets and blocks to use, and inference fills the editor with
  a proposal. Choose whether the proposal extends the active model (matching columns to existing types
  and attributes first) or starts a new application. As built (A5b): **New from a workbook** on
  Settings › Model creates a draft of the active release (an empty model is a choice) with the
  workbook, and an open draft takes one from its ⋯ menu. Since A6 it asks what to propose (a new
  application added to the model the draft starts from, a new model, additions to the model, or
  nothing). **A new model** is the same application in a draft that starts empty, without the active
  model's applications; the editor opens with the proposals applied,
  one step each; what is still as proposed is marked Proposed, with Proposed because in the centre
  (the finding, its evidence, its alternatives as steps); ⋯ › Propose again… reads the workbook
  again (D92, D94). Until 0.11, installing and activating a new model replaces the active model for
  every workspace. **From 0.11 (D15, ADR-042)** each workspace runs a model of its own: a new model is
  installed and activated into one workspace the user chooses or creates in the same step, never into
  every workspace, and installing and activating from the editor names the target workspace(s); a
  draft's compatibility is shown for each workspace running its model (D25). As built (M3): through
  the API, a new model is installed and a workspace created on it (`POST /workspaces` with
  `modelReleaseId`) or activated into one workspace. In the browser (M5, D55) the editor previews
  the records of a workspace running the draft's model (the one the user came from when it does,
  else the first that does; none for a new model, whose preview shows empty records), and **Install
  and activate** asks **Activate into**: an existing workspace (the editor's first; others marked
  Other model) or a new workspace, named in the dialog and created on the release. A new model no
  workspace runs proposes a new workspace. A draft is
  compared with its base release, or without one with the newest installed release of its own model
  (`release.key`), or with nothing when it is a new model: then every element is new, no consumer
  contract needs a higher version and no data is affected (D37). Its profile is saved at installation
  only when no other model's profile holds its key (D36).
- **From a model:** open a draft of the active release, or an empty one. No source file; the preview
  uses existing records instead of rows.
- **From a saved profile:** upload the next version of a workbook to its profile. Only differences and
  new issues need attention.

### Layout

As built (0.10 A4a–A4c, and A5's D84): a resizable model pane, the centre showing the selected
element (or the preview), and a drawer below with Issues, History and, with a workbook, the dry
run. A workbook adds a source pane left of the model pane; a selected column's mapping shows in the
centre, as a selected type's definition does. At 390px the panes are tabs. The panes as first
designed:

- **Source.** The sheet or block with its header row, each column marked mapped, unmapped, ignored or
  with issues, and its statistics (filled, distinct, value types, candidate key, overlap with other
  columns).
- **Mapping.** Each column linked to the model element it feeds: attribute, parent, relation, lookup,
  translation, system mapping or ignored, with the transformation applied (split on a delimiter,
  flag columns, value map). Selecting a column highlights its target, and the reverse.
- **Model.** The structure being built or changed: applications, object types in their containment
  tree, each type's attributes, and the relationship matrix of allowed relation types between types.
  Elements show whether they are new, changed or already released.
- **Preview.** A record rendered by the real generic renderers from the current draft and a sample row:
  its detail panels, its picklists with the candidates they would offer, its table row. This is where
  layout editing happens (see [Views and layouts](#views-and-layouts)).

### Editing

- Drag a column onto an attribute, a type or an empty area (a new attribute or type); drag an attribute
  to another type; drag a type under another parent. Each has a menu action and a keyboard path, as
  the tree lens's Move to… does for its drag (0.8 B5).
- Context menus carry the operation catalogue for the selected element.
- **After every operation the dry-run summary updates**, with the difference from the previous one:
  "Category: 14 records (was 0); `sort_order` moved from Type, 200 values → 14, 0 conflicts" or
  "2 codes have two different names". Each figure links to the rows behind it.
- Undo and redo apply the inverse operation; the history lists every operation with its author and
  time, and any point of the history can be viewed.
- Issues form one list: validation errors (block install), dry-run rejections (block a clean import),
  and warnings such as a mapped value drift. Each issue links to the pane and element it concerns.

### Concurrency

The draft keeps its version. Every operation carries the version it was made against, and a stale one
is refused with `409` and the newer version's operations, which the editor replays or asks about. Two
administrators can open the same draft; they see each other's operations when they refresh or on the
next operation.

## Operation catalogue

Each operation changes the model draft, the attached profiles, or both. Its **class** decides when it
is allowed:

- **Additive:** always allowed.
- **Draft-only:** allowed while every element it touches is absent from the base release or no record,
  value or relationship holds it; otherwise it becomes a migration. Activation checks the data again.
  An element's key is stricter: fixed once released, held or not.
- **Migration:** changes released structure that existing data depends on. Shown with its impact and
  blocked until the 0.11 migration boundary exists (see [Delivery](#delivery)); never hidden.

| Group | Operation | Profile effect | Class |
| --- | --- | --- | --- |
| Names | Rename an element's label or translation of its label | — | Additive |
| Names | Change an element's key | Follows | Draft-only |
| Types | Add an object type, application, attribute type or relation type | — | Additive |
| Types | Remove a type or attribute | Its columns become unmapped | Draft-only |
| Types | Split a type (some attributes to a new type related to it) | Columns follow their attributes | Draft-only |
| Types | Merge two types, or two lists that hold the same values | Columns and value maps merge | Draft-only |
| Types | Turn a list into an object type, or an attribute's value set into a list type | Column becomes a lookup | Draft-only |
| Attributes | Move an attribute to another type (parent or related) | Column follows | Draft-only |
| Attributes | Attach an existing global attribute type instead of a new one | Column follows | Draft-only |
| Attributes | Change value type, required, unique | Conversion added or removed | Draft-only |
| Structure | Change containment (the parent type of a type) | Parent column follows | Draft-only |
| Structure | Allow a relation between two types, or remove it | — | Additive / Draft-only |
| Structure | Change cardinality or required on a relation | — | Draft-only |
| Mapping | Map a column to an attribute, parent, relation, lookup, translation or system mapping | Yes | Additive |
| Mapping | Change how a column is read: text, lookup, relation, flag of a relation | Yes | Additive |
| Mapping | Split a column on a delimiter; flag columns of one relation; a column per related record (a language) | Yes | Additive |
| Mapping | Ignore a column or a sheet | Yes | Additive |
| Values | Map values: variants to one value, placeholders to empty | Yes | Additive |
| Values | Add values found in the data to a list: the load creates the records a lookup names that do not exist (0.10 A5, D77) | Yes | Additive |
| Views | Add, reorder, show or hide views, panels, columns, filters and fields | — | Additive |
| Views | Add a relationships table over a declared binding (`addView` of type `relationTable`; the editor's **Add a relationships table…**, 0.13 RV, J33.20): its columns, the binding's attributes as columns, filters and sorts that follow, how rows are headed | — | Additive |

Once a release is installed, a draft-only operation on a released element that data holds is recorded
as a migration request with its impact (records, values and relationships affected), not applied. Type changes of
existing records already have an engine operation in change sets (ADR-034); the 0.11 migration
boundary is where model-level changes reuse it.

## Import profile

The profile is the contract between the editor and the 0.9 import job. Its exact JSON was fixed by
0.9 J2 (2026-10-07): [API.md](API.md#import-profiles) holds it and
[INTEGRATION_API §J3](INTEGRATION_API.md#j3-import-profile) what changed from this outline (each source
names its application; translations and system mappings are profiles of one `relatedRecord`
binding; profiles are instance-wide). This is the outline as first written:

```json
{
  "key": "service-catalogue",
  "modelReleaseKey": "...",
  "sources": [
    {
      "sheet": "Services",
      "headerRow": 1,
      "objectTypeKey": "service",
      "upsertKey": { "attributeTypeKey": "code" },
      "columns": [
        { "column": "Service_Code", "attributeTypeKey": "code" },
        { "column": "Service_Name", "field": "name" },
        { "column": "Category", "parent": {
            "objectTypeKey": "category", "matchBy": { "field": "name" } } },
        { "column": "Unit", "relation": {
            "relationTypeKey": "has-unit", "objectTypeKey": "unit",
            "matchBy": { "field": "name" }, "valueMap": "unit-values" } },
        { "columns": ["Room_A", "Room_B"], "relationFlags": {
            "relationTypeKey": "uses-room", "objectTypeKey": "room",
            "targets": { "Room_A": "room-a", "Room_B": "room-b" } } },
        { "column": "Other_Rooms", "relation": {
            "relationTypeKey": "uses-room", "objectTypeKey": "room",
            "matchBy": { "field": "name" }, "split": ";" } },
        { "column": "CRM ID", "systemMapping": { "systemKey": "crm", "as": "externalId" } }
      ]
    },
    {
      "sheet": "Translations",
      "translations": { "matchBy": { "attributeTypeKey": "code", "column": "Service_Code" },
        "languageColumn": "Language", "fields": { "Service_Name": "name" } }
    }
  ],
  "valueMaps": { "unit-values": { "N/A": null } }
}
```

(Keys and column names above are illustrative.)

- **Sources** are sheets, or blocks of a sheet, each loading one object type. The job orders them by
  their references: a source whose parent or relation targets are loaded by another source runs after
  it, and references within one load resolve by the match keys, not by row order.
- **Column bindings** are the only transformations: to a field or attribute (typed conversion through
  the attribute registry), to a parent or relation by a match key (optionally split on a delimiter),
  a set of flag columns to one relation, to translations (a column per language, or a row per
  language), to a system mapping, or ignored.
- **Value maps** are named and reusable across columns.
- **Upsert keys** are the 0.9 upsert keys (D2): the public ID or one unique attribute.
- **Outcomes** are 0.9 item outcomes, reported per row with the sheet and row number.
- A profile names the model release it was checked against. Running it against another release re-checks
  every binding and refuses with the path of each binding that no longer resolves.

## Pattern catalogue

Inference recognises these shapes. Each proposes model operations and profile bindings, shows its
evidence, and offers the alternatives when the evidence is not decisive.

| Pattern | Evidence | Proposal |
| --- | --- | --- |
| Key column | Unique, fully filled, code-like | The upsert key; a unique attribute |
| Code and name pair | Two columns that vary together | A list type with code and name, or the record's own code and name |
| Repeated parent | Low-cardinality column(s) whose values group rows, with columns that are constant per group (sort order, ID) | A parent type holding those columns; containment |
| Level columns | Level 1, 2, 3 columns, or a parent-code column referring to the key column | A recursive or multi-type hierarchy |
| Text lookup | A low-cardinality text column | A list type and a relation, or a plain attribute (asked) |
| Reference to another sheet | Values that resolve to another sheet's key, with the rate shown | A relation between the two types; `many-to-one` when each row names one record that many rows share |
| Multi-valued cell | A delimiter that splits most filled cells into known values | A many-valued relation |
| Flag columns | Several true/false or Y/N columns that name members of one set | One relation to a list whose values are the column names |
| Translations, one row per language | A language column and a key repeated once per language | Translations of the named fields |
| Translations, one column per language | Column pairs with language suffixes or language names | Translations of the named fields |
| External IDs | A GUID or foreign-code column per external system | System mappings with the value as external ID |
| Placeholder values | `N/A`, `?`, `TBC`, `-` and empty-looking text | A value map to empty, with the count |
| Name drift | One ID or code with different names in different rows or files | A value map, or a warning to resolve |
| Model description sheet | Columns such as field code, field type and lookup target | Attributes and relations of the described type, read before the lookup sheets it names |
| List blocks | Several header-and-values blocks on one sheet, separated by empty columns or rows | One source per block, confirmed by the administrator |

**The rules as built (0.10 A6a, D90; revised in A6b on real workbooks, D99–D103).** Each pattern is a fixed rule over the profile's statistics
(A3) and the facts between columns, asked of the staged cells; the thresholds are fixed so a test
names what a rule finds. The rules run per sheet in this order, each claiming the columns it
explains:

- **Translations, one row per language:** a sheet without a key, holding a column of two or more
  language codes (ISO 639-1) or English language names, and a column of which at least 90% of the
  distinct values are another sheet's keys, once per language; the column named as that sheet's name
  column holds the translated names.
- **Key column and name:** the key is the leftmost candidate key that is text without spaces, or
  integers, and not a GUID; without one, a GUID filled and different on every row (D99: a list of an
  ID and a name). The name is the first other text column, neither a lookup nor code-like, filled on
  at least 95% of the rows (a header holding the word "name" first); a text key that would leave the
  rows without a name, beside such a GUID, becomes the name and the GUID the key.
- **Translations found by their values (D100):** claimed here, before the rules below read the
  columns, and proposed after what they translate. A column translates a base column whose values
  repeat when it has between 80% and 125% as many distinct values, one value per base value and one
  base value per value (80% of each: translators split and merge a few), and at most half its rows
  the same as the base's. The k-th translation of every base is in the k-th language, named by a
  language word of its header when it has one, else "Language k" for the administrator to name. A
  base that is a type's name (the row's, a code and name pair's list, a repeated parent with a key)
  gets translations of that type; another base leaves its translations attributes.
- **Flag columns:** the columns of a sheet whose every cell is one word of the same `y/n`,
  `yes/no`, `x`/empty, `true/false` or `1/0`, adjacent or not, form one set (D101); a multi-valued
  column beside one of them joins it (D97). A lone yes/no column is a yes/no attribute reading its
  words through a value map.
- **Code and name pair:** a code-like column (short text without spaces, holding letters and digits)
  and a text column with at most 1.5 names per code, each name with one code in at least 98% of its
  groups. **Name drift:** a code of such a pair with two or more names; the proposal maps each less
  frequent name to the code's most frequent one.
- **Level columns:** headers differing only by a number (Level 1, Level 2, …), or a column of which at
  least 90% of the values are the sheet's own keys.
- **Repeated parent:** a text column with at most a third as many distinct values as rows, grouping
  other columns that are constant within at least 98% of its groups; a dependent with one value per
  group that is a GUID or code-like is the parent's key. Text averaging more than 60 characters is
  sentences, a shared description: never a parent, a pair's name or a lookup, and read as long text
  (D102). A row type has one parent (D99): the first such column; a further one is a list the row
  refers to. The parent is optional (the type may also stand at the top) when some rows leave the
  parent column empty, and always for a parent code column, whose empty rows are the top.
- **Multi-valued cell:** a delimiter in at least 10% of the cells whose parts are at least 80% values
  found whole in the column.
- **Reference to another sheet:** at least 90% of a column's distinct values among another sheet's
  keys, or its names (matched by name).
- **Translations, one column per language:** headers that are the name column's with a language
  suffix (`Name (de)`, `Name FR`).
- **Text lookup:** text with at most 50 distinct values that are at most 20% of its filled cells.
- **External IDs:** every cell a GUID. Every remaining column is an **attribute** of the value type
  its cells read as, unique when it is a candidate key; **placeholders** (D70) follow the lookup or
  attribute holding them; a **navigation group** gathers two or more lists one sheet proposes.

Columns of different sheets with one header and value type share one attribute type, a unique one
only when no value appears in both (D98). In extend mode a sheet maps to an existing type when at
least 50% of its key's values are that type's unique values or names in the workspace, or when its
name is the type's (names folded for case, accents, punctuation and a final plural `s`), and a column
to an attribute of the same name its cells fit (95%), a global attribute type before a new one (D91).
A sheet of several blocks is read by its main table when one block is clearly the table (at least
three columns and 60% of the sheet's cells), as a source limited to that block's columns; the other
blocks are named in the inference's warnings, and a sheet where no block is the table is read list
by list (below). A second
column with a header an earlier column of the sheet has is left out with a warning, since a column
is bound by its header. Names come from the headers and sheet names written as words (D103:
underscores and joined capitals split, a header in capitals sentence-cased); a row type is named
after its key column's header without a final code word ("Type Code" → Type), else after its
sheet; a navigation group after the row type. A few English words are the patterns' own ("Has …",
"Language", "Translation"); every name is the administrator's to change.

**A model description, as built (0.10 A7, D107–D109).** Read before every rule above; neither the
description nor the sheets its targets name are read by them. A sheet is a description when it holds
a **field column** (text, filled and different on every row), a **type column** (at least 80% of its
cells field-type words) and a **target column** (at least half its cells naming another sheet,
folded as names are), found by their values, never their headers. The type words are English:
`lookup`, `list`, `reference`, `select` (one record of the target); `multi`, `multiple`,
`multi-select`, `multi-lookup` (several); `flag`, `yes/no`, `boolean`, `checkbox` (a member of the
target's flag set, a yes/no attribute without a target); `text`, `string`; `long text`,
`description`; `number`, `integer`; `decimal`; `date`. A word outside the list makes its field a
text attribute, with a warning. It proposes the **described type**, named after the description
sheet (the description does not name the type it describes), the sheet ignored; per target a
**list**, read from the target's sheet by its ID (the key column rule) and name, a placeholder ID
skipped (its value map sends it to empty and the source skips rows without a key); a target sheet
holding only placeholders is a **list to be defined** (the list, no source, its sheet ignored, a
warning); a target without a sheet is a list with no source. Per lookup or multi field a relation
named after the field to its list, per plain field an attribute of its type, and per flag target one
relation to its list, whose records a later file's flag columns create. The placeholder words gain
`tbc`, `to be defined`, `to be decided` and `to be confirmed`.

**Matching across files, as built (0.10 A7, D106, D111, D112).** Two workbooks meet through the
stored model and records: the description workbook is installed and loaded, and the flat table comes
as additions to the model. Added to D91: a sheet maps to an existing type when at least half of the
type's attribute and relation names (two at least) are its headers; a list any proposal would add
under an existing type's name (or plural, folded) is that type; a code column whose values are at
least half a stored unique attribute's values relates by that attribute, before any match by name;
a relation already allowed between the two types is reused. What differs is reported, not scored:
**missing IDs** (a matched column's values no stored record holds, with their rows), refused by the
load, with creating them on load as the alternative; and **name drift** (a code whose name in the
file differs from the stored record's), with the stored names standing and loading the file's names
as the alternative. A file uploaded without a workspace is compared with the default workspace's
records.

**Lists in the editor, as built (0.10 A8b, D122–D128).** The source pane shows a sheet laid out for
reading as its lists under their innermost titles, each with its range, rows, note and status
(Proposed, Loaded, Not loaded), and opens the selected list to its columns; the centre shows a list
with the cells around it. **Adjust list…** sets the rows and columns a list loads (one `setSource`;
its columns keep their bindings on their letters, and it may take the new header's name); **Don't
load this list** removes its source and, when nothing else loads, relates to or contains it, its
list type, in one step; **Load as a list…** reads a rectangle the inference left out as A8a reads a
list, and the result is the administrator's.

**Lists laid out for reading, as built (0.10 A8a, D115–D119).** A sheet where no block is the table
(or that is one block of at most two columns holding several lists one under another), with at most 2,000 rows with a cell, is read list by
list by its profile. Each run of columns between empty columns is split at empty rows; a row whose
cells average more than 60 characters is prose and no part of a list. A one-row part directly above
another (at most one empty row between) is that list's header, unless it is one cell over lists
beside it that start on the same row with nothing such above them, which makes it their title.
Lists side by side share the header row most of them start on, with one-cell rows above it as
titles. A one-row part left over is a title when it is one cell, else a header with no values. A
list's titles are the nearest title above it whose columns reach it (a title reaches to the next
title on its row) and those on the rows directly above that one. Its **note** is the first row under
its header when a cell of it is a note word (English, folded): `multiple answer(s)`, `multiple
choice`, `multi-select`, `several` (many); `single answer`, `single choice`, `one answer` (one);
`free field`, `free text` (no list); without one, in a list with yes/no columns, a first row naming
something and answering none of them while every later row answers one is a **second header row**
(0.10 A8c, D144), read and skipped as a note. Colour, bold and merged cells are not read. Each list proposes
a list type named after its header, a source on its block keyed by name (D117), its first column
the name; within the list a column of yes/no words is a yes/no attribute (two or more a flag set), a
text column filled on 80% of the rows its names fill is their translation (a language word of its
header, else "Language k"; D118: the rule sees a second text per item, only a header says which
language), a column holding only its header is reported and not read, any other an attribute. The
note row is skipped and the note becomes the type's description; a free field or a header with no
values proposes nothing and is a warning. The lists under one innermost title, two or more, are a
navigation group named after it.

**Lists of one shape as one list, as built (0.10 A8c, D140–D143).** Three lists or more of a sheet
under one innermost title, or all under none, whose columns after the name have the same kinds in
order, are a run: their headers may be values (the categories of one list of items) or names of
separate lists, and the shape cannot tell which, so each stays a list of its own and carries the
alternative "Read these N lists as one list under their headers". Taken, it replaces them in one
step by a list named after the title (else the sheet) contained in a parent list "… category",
loaded by one source per former list fixed to its header, which the load creates as a record of the
parent list. A source keyed by name finds a row's record among its parent's children, so a name
under two headers is two records. The category's name in another language (a translation column's
header) is not read, and a second header row is skipped, not stored on the category.

**Inference is deterministic first.** Profiling computes types, uniqueness, fill rates, delimiters and
value overlap between columns and sheets; the patterns are rules over those statistics. The
inference never applies an operation that the administrator did not accept, and every accepted
operation passes the same validation.

## Lists as object types

A list of values (units, sizes, colours, statuses) becomes an object type of its own, created by
inference or by one operation. This replaces the pattern of one generic "reference value" type holding
several lists and picklists filtered by the parent's name: the relation binding itself limits a picklist
to the right list, with no filter configuration and no string match, and each list can carry its own
attributes, translations and mappings.

The cost is the number of types: a single workbook can hold 40 small lists. The editor makes them
cheap to create, and declared navigation groups keep them out of the way (A-D1, A-D2; see
[Navigation groups](#navigation-groups)). Scoping a shared list type to one of its
records from the model is rejected: the model would reference runtime data, which startup validation
cannot check.

## Views and layouts

A new type gets a working default from the model alone: a table view with its key, name and mapped
attributes; detail panels for attributes, children, relations, translations and system mappings as its
bindings allow; picklists limited by the relation bindings. The administrator never writes view or panel
JSON for the normal case.

The editor's preview shows them as the record screen will, and its layout editor edits them in place
(0.10 A4b: the preview opens in the editor's centre from a type's header, the layout editor over the
whole editor, each marked by a band of its own):

- reorder panels within the `main` and `side` regions, show or hide them, choose their columns and
  default sort;
- choose a table view's columns, filters and default sort;
- reorder and group fields;
- choose a field's editor among those the registry declares for its value type, when there is more
  than one (a later registry extension adds variants only after two real cases, per AGENTS.md).

## Navigation groups

Today the sidebar lists one collection per source type, flat, in view order (ADR-029). With dozens of
list types the application's main work areas disappear among them. ADR-029 deferred explicit
navigation composition until a real model showed source-type grouping to be insufficient; spreadsheet
models are that case (A-D2).

An application may declare navigation groups:

```json
"navigation": {
  "groups": [
    { "key": "calendar-lists", "label": "Calendar lists",
      "collections": ["unit", "size", "colour"], "collapsed": true }
  ]
}
```

- A group is a labelled, collapsible sidebar section. Collections in no group stay at the top level in
  their current order, so a model without the declaration looks as it does today.
- A group also opens as a page listing its collections, with a search over their names: the place to
  maintain lists.
- Groups are presentation only. They change no API, data or record validation and carry no
  permissions, so regrouping never needs a migration; in the editor it is an additive operation.
- Validation: each entry is a collection of the application (a view source type) or a relation matrix
  view of it (`{ "view": key }`, which then has an entry of its own in the sidebar), a collection or a
  matrix is in at most one group, group keys are unique within the application. `navigation.opens`
  names, per collection, the view its entry opens on.
- The field is optional and arrives in 0.10's first schema language version; existing models stay
  valid unchanged.
- Inference proposes groups from the workbook's structure (sheet names, section headers above blocks,
  types used only as picklists); the administrator renames, merges and regroups them like any other
  element.

Groups have one level, and the group page shows no record counts. Both are non-blocking open items
(A-D11, A-D12).

## Recurring loads and reconciliation

- Uploading a new version to a saved profile profiles it, checks every binding and runs the dry run.
  New columns, missing columns, new list values and name drift are reported before anything loads.
- The load runs as a 0.9 import job keyed by the profile's upsert keys, into a new change set by default.
  The change set review screen shows what the new version changes: added, changed and removed records,
  and relationship changes.
- Records missing from the new version are reported, never deleted by default. Whether a load may
  delete them, in a change set only, is a profile option (A-D7; records have no retired state, so
  0.10 A5's D82 leaves "retire" out). A deleted record goes with its own relationships; one other
  records depend on is refused for a person to decide (D104).
- A lookup onto a relation a record holds one of replaces it, so a value changed in the next version
  switches the record rather than adding a second one (D105).
- The differences are a check job on the profile's next file, read from Settings › Import profiles (D83,
  D85); a renamed column is accepted there, which updates the profile.
- Matching across files (the model-description workbook and the flat table naming the same records)
  uses IDs or codes, never names alone; differing names are drift to resolve.

## API outline

The design is in [API.md § Model authoring](API.md#model-authoring-product-010-designed) (0.10 A0,
2026-10-11), with [ADR-041](DECISIONS.md#adr-041--model-drafts-change-through-recorded-operations); it differs from
this outline in three places: undo and redo are routes of their own, a source file is a resource
owned by a draft or a profile rather than a job file (plan D5), and install and activate stay the two
existing routes. The outline as first written:

- `POST /api/v1/model-drafts/{draftId}/operations` — apply operations at `expectedVersion`; returns the new
  draft version, diagnostics and the dry-run summary of every attached source file.
- `GET /api/v1/model-drafts/{draftId}/operations` — the operation history, cursor-paged.
- `POST /api/v1/source-files` — upload a workbook or CSV (0.9 job file storage, D12 and D13 limits).
- `GET /api/v1/source-files/{id}/profile` — sheets, blocks and column statistics, paged by sheet and
  column.
- `POST /api/v1/model-drafts/{draftId}/inferences` — propose operations for a source file; applies nothing.
- `/api/v1/import-profiles` — create, read, update (optimistic version) and delete profiles;
  `POST …/{id}/dry-run` with a source file.
- The load itself is a 0.9 import job naming the profile and the source file.

Existing `PATCH /model-drafts/{id}` with a whole model stays for the JSON workbench; applying an operation
to a draft changed by a whole-model patch works on the patched model.

## Delivery

| Package | Delivers | Depends on |
| --- | --- | --- |
| A1 | Import profile contract, executed by the 0.9 import job; XLSX and several sheets. **Delivered by 0.9 J2 and J3** | 0.9 B, J |
| N1 | The navigation group contract (schema 0.10), its validation, sidebar sections and group page | — |
| A2 | Operation API on model drafts: the catalogue's additive and draft-only model operations, history, undo, version checks, default views for new types | N1 |
| A4a | Editor: model pane, relationship matrix, issues, history, install and activate | A2 |
| A4b | Editor: preview with generated views and panels, layout editing | A4a |
| A4c | Editor: consumer API definitions by operations, their schema and message example, the contract at activation | A4b |
| T1 | The designer checked on its own (US-P05); released as 0.10.0-alpha.1 | A4c |
| A3 | Source profiling and the dry-run summary after each operation | A1 |
| A5 | Editor with a source file: source and mapping panes, mapping operations, the profile side of model operations, profiles saved and re-run | A3, T1 |
| A6 | Inference: the table patterns of the catalogue; extending an existing model | A5 |
| A7 | Model description sheets and matching across files | A6 |
| A8 | List blocks in sheets laid out for reading | A6 |
| R | Acceptance | All |

The designer line (N1 to T1) comes before the spreadsheet line (A3 onward), at the user's request
(plan D11); A3 has no dependency on the editor and may fill a gap. A7 and A8 may move to a 0.10.x
release if R is not in reach. The migration class of operations was refused in 0.10 and enabled in
0.13 (package MG), on the 0.11 migration boundary: the editor applies such a step and marks it as
needing a migration, the draft states the migration it implies, and the workspace migration carries it.

## Exit gate

- The flat-table shape (with its translation sheet) becomes an installed application and a reviewed
  change set without writing JSON or code, and every inference was changeable before loading.
- A second, differently shaped workbook (the model-description shape) does the same.
- Loading the next version of the first workbook through its saved profile shows only its differences
  in the change set review.
- Renaming, moving, splitting and merging elements in the editor keeps the profiles valid, and the dry
  run reflects each operation.
- Every drag has a keyboard path; the editor passes the accessibility and visual gates at desktop and
  narrow widths.
- The same journeys work on the starter model, extending it, and on a new application.
- No runtime or editor branch on an application, object-type, attribute or relation key.

Acceptance fixtures in the repository are synthetic workbooks with the same shapes as the private samples;
the samples themselves stay outside the repository.

## Composable domains check (ADR-032)

- **Identity:** profiles upsert by the public ID or a unique attribute (0.9 D2); a later retired-ID
  redirect applies to profile loads as to any upsert.
- **Provenance:** a profile load is an import job, recorded on its audit entries (0.9); a value-source
  field stays additive. The profile key is the natural source name.
- **Audit/history:** operations on a model draft have their own history; data changes use the existing
  audit. No new data history.
- **Inbound flow:** a profile is the file form of keyed inbound upsert; recurring feeds and one-off loads
  use it alike.
- **Matching and review:** name drift and cross-file matching are reported, not scored. A later
  similarity vocabulary may power suggestions without changing the profile.
- **Value types:** conversions go through the attribute registry; a new value type brings its own
  conversion.
- **`match` declaration and mapping coverage:** not affected.

## Open decisions

The recommendation is the planning default.

| # | Question | Recommendation |
| --- | --- | --- |
| A-D1 | Lists: one type per list, or scoping a shared list type | **Decided 2026-09-29:** one type per list. Scoping from the model would reference runtime data |
| A-D2 | Navigation with many small list types | **Decided 2026-09-29:** model-declared navigation groups on the application ([Navigation groups](#navigation-groups)); not a container record type, a separate application or automatic grouping. One level, no record counts on the group page (A-D11, A-D12); optional field in 0.10's first schema language version |
| A-D3 | Where profiles live | **Decided 2026-09-29:** stored resources that name a model release and are re-checked on use; not part of the model release, so a changed mapping needs no model release |
| A-D4 | File formats | **Taken by 0.9 J2 (D64–D74):** XLSX, CSV and JSON Lines. No legacy `.xls` (convert first). Values as stored, formulas not evaluated |
| A-D5 | Optional assistant | **Decided 2026-10-11 (0.10 A0):** off by default and pluggable. It receives headers and a bounded sample only when configured; its output is proposals. Only its interface is in 0.10 (A6) |
| A-D6 | Keys of new elements | **Decided 2026-10-11 (0.10 A0):** generated from labels (lower-case, hyphen-separated ASCII, accents dropped, `-2`, `-3` on a clash), editable until the element is released, that is, in the draft's base release (plan D17) |
| A-D7 | Records missing from a new version | **Decided 2026-10-11 (0.10 A0):** reported; retire or delete only when the profile says so, in a change set |
| A-D8 | Install and activate from the editor | **Decided 2026-10-11 (0.10 A0):** one confirmed step running both, refused on any diagnostic, with the compatibility check and the release version (plan D18) shown |
| A-D9 | Sheets laid out for reading (A8) | **Decided 2026-10-11 (0.10 A0):** blocks detected and proposed; the administrator confirms each block. Colour and formatting carry no meaning |
| A-D10 | XLSX reader | **Taken by 0.9 J2:** `openpyxl` (MIT), read-only mode, values not formulas; licence recorded in LICENSING_TODO |
| A-D11 | Nested navigation groups | **Open, non-blocking.** One level in 0.10; nesting only when a real model needs it beyond a group page and search |
| A-D12 | Record counts on the group page | **Open, non-blocking.** None in 0.10; later only as a bounded read, since a count per collection on every page view has a cost |

## Not in scope

- Canvas-first model authoring and pixel layouts ([TODO.md](TODO.md)).
- General ETL: formulas, joins other than key lookup, scripting, scheduled pulls from external sources.
- Live links to online spreadsheets.
- Migration-class operations in 0.10 (enabled in 0.13, MG).
