# Model authoring and spreadsheet onboarding (Product 0.10)

Status: design direction accepted 2026-09-29 ([ADR-035](DECISIONS.md#adr-035--model-authoring-is-an-editor-of-operations-on-a-model-draft-a-spreadsheet-is-one-way-to-start-it)).
Decisions are listed at the end (A-D1 to A-D3 decided; A-D11 and A-D12 open but non-blocking; the others open). The packages, sequence and acceptance are in the provisional
[Base 0.10 plan](BASE_0_10_IMPLEMENTATION_PLAN.md); the
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
- **Source file.** An uploaded workbook or CSV file, stored as a 0.9 job file (D12) with its checksum,
  and its **profile**: sheets, header rows, blocks, columns and their statistics.
- **Import profile.** The declarative mapping from a source file's sheets and columns to model elements.
  It is what the 0.9 import job executes, and it replaces the per-upload script.
- **Inference.** Detects patterns in a source profile and proposes operations. Its proposals are
  offered, not applied; accepting one applies its operations.
- **Pinned decision.** An element the administrator has changed or confirmed. Re-running inference, or
  profiling a new version of the workbook, never overrides a pinned decision; it reports disagreements.
- **Dry run.** The 0.9 import preview, run on the source file with the current draft and profile. It
  writes nothing.

## The editor

### Starting points

- **From a workbook:** upload, confirm the sheets and blocks to use, and inference fills the editor with
  a proposal. Choose whether the proposal extends the active model (matching columns to existing types
  and attributes first) or starts a new application.
- **From a model:** open a draft of the active release, or an empty one. No source file; the preview
  uses existing records instead of rows.
- **From a saved profile:** upload the next version of a workbook to its profile. Only differences and
  new issues need attention.

### Layout

Three synchronized panes and a preview:

- **Source.** The sheet or block with its header row, each column marked mapped, unmapped, ignored or
  with issues, and its statistics (filled, distinct, value types, candidate key, overlap with other
  columns).
- **Mapping.** Each column linked to the model element it feeds: attribute, parent, relation, lookup,
  translation, system mapping or ignored, with the transformation applied (split on a delimiter,
  unpivot, value map). Selecting a column highlights its target, and the reverse.
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
- **Draft-only:** allowed while every element it touches is absent from the base release; otherwise it
  becomes a migration.
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
| Mapping | Split a column on a delimiter; unpivot columns into records | Yes | Additive |
| Mapping | Ignore a column or a sheet | Yes | Additive |
| Values | Map values: variants to one value, placeholders to empty | Yes | Additive |
| Values | Add values found in the data to a list | Yes | Additive |
| Views | Add, reorder, show or hide views, panels, columns, filters and fields | — | Additive |

Once a release is installed, a draft-only operation on a released element is recorded as a migration
request with its impact (records, values and relationships affected), not applied. Type changes of
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
        { "column": "Duration", "relation": {
            "relationTypeKey": "has-duration", "objectTypeKey": "duration",
            "matchBy": { "field": "name" }, "valueMap": "duration-values" } },
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
  "valueMaps": { "duration-values": { "N/A": null } }
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
| Reference to another sheet | Values that resolve to another sheet's key, with the rate shown | A relation between the two types |
| Multi-valued cell | A delimiter that splits most filled cells into known values | A many-valued relation |
| Flag columns | Several true/false or Y/N columns that name members of one set | One relation to a list whose values are the column names |
| Translations, one row per language | A language column and a key repeated once per language | Translations of the named fields |
| Translations, one column per language | Column pairs with language suffixes or language names | Translations of the named fields |
| External IDs | A GUID or foreign-code column per external system | System mappings with the value as external ID |
| Placeholder values | `N/A`, `?`, `TBC`, `-` and empty-looking text | A value map to empty, with the count |
| Name drift | One ID or code with different names in different rows or files | A value map, or a warning to resolve |
| Model description sheet | Columns such as field code, field type and lookup target | Attributes and relations of the described type, read before the lookup sheets it names |
| List blocks | Several header-and-values blocks on one sheet, separated by empty columns or rows | One source per block, confirmed by the administrator |

**Inference is deterministic first.** Profiling computes types, uniqueness, fill rates, delimiters and
value overlap between columns and sheets; the patterns are rules over those statistics. An optional
assistant (A-D5) may suggest names and meanings of columns ("Ctry" probably means country) as
proposals. Neither ever applies an operation that the administrator did not accept, and every
accepted operation passes the same validation.

## Lists as object types

A list of values (durations, resources, roles, statuses) becomes an object type of its own, created by
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

The preview pane edits them in place:

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
      "collections": ["duration", "resource", "room"], "collapsed": true }
  ]
}
```

- A group is a labelled, collapsible sidebar section. Collections in no group stay at the top level in
  their current order, so a model without the declaration looks as it does today.
- A group also opens as a page listing its collections, with a search over their names: the place to
  maintain lists.
- Groups are presentation only. They change no API, data or record validation and carry no
  permissions, so regrouping never needs a migration; in the editor it is an additive operation.
- Validation: each entry is a collection of the application (a view source type), a collection is in
  at most one group, group keys are unique within the application.
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
  retire or delete them is a profile option (A-D7).
- Matching across files (the model-description workbook and the flat table naming the same records)
  uses IDs or codes, never names alone; differing names are drift to resolve.

## API outline

Routes are fixed when their packages are written; the outline shows the resources:

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
| A1 | Import profile contract, executed by the 0.9 import job; XLSX and several sheets; the acceptance workbook loaded by a hand-written profile. Delivered inside 0.9 Track J | 0.9 B, J |
| A2 | Operation API on model drafts: the catalogue's additive and draft-only operations, history, undo, version checks | — |
| A3 | Source profiling and the dry-run summary after each operation | A1 |
| A4 | Editor: model pane, relationship matrix, preview with generated views and panels, layout editing; the navigation group contract, its validation, sidebar sections and group page | A2 |
| A5 | Editor with a source file: source and mapping panes, mapping operations, profiles saved and re-run | A3, A4 |
| A6 | Inference: the table patterns of the catalogue; extending an existing model | A5 |
| A7 | Model description sheets and matching across files | A6 |
| A8 | List blocks in sheets laid out for reading | A6 |
| R | Acceptance | All |

A1 and A2 can proceed in parallel. A7 and A8 may move to a 0.10.x release if R is not in reach. The
migration class of operations is enabled in 1.0, on the 0.11 migration boundary.

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
| A-D4 | File formats | XLSX, CSV and JSON Lines. No legacy `.xls` (convert first). Values as stored, formulas not evaluated |
| A-D5 | Optional assistant | Off by default and pluggable. It receives headers and a bounded sample only when configured; its output is proposals |
| A-D6 | Keys of new elements | Generated from labels, editable until the element is installed |
| A-D7 | Records missing from a new version | Reported; retire or delete only when the profile says so, in a change set |
| A-D8 | Install and activate from the editor | One confirmed step running both, refused on any diagnostic, with the compatibility check shown |
| A-D9 | Sheets laid out for reading (A8) | Blocks detected and proposed; the administrator confirms each block. Colour and formatting carry no meaning |
| A-D10 | XLSX reader | `openpyxl` (MIT), read-only mode, values not formulas; licence recorded in LICENSING_TODO |
| A-D11 | Nested navigation groups | **Open, non-blocking.** One level in 0.10; nesting only when a real model needs it beyond a group page and search |
| A-D12 | Record counts on the group page | **Open, non-blocking.** None in 0.10; later only as a bounded read, since a count per collection on every page view has a cost |

## Not in scope

- Canvas-first model authoring and pixel layouts ([TODO.md](TODO.md)).
- General ETL: formulas, joins other than key lookup, scripting, scheduled pulls from external sources.
- Live links to online spreadsheets.
- Migration-class operations before 1.0.
