# Base 0.17 implementation plan

**Status:** Planned 2026-10-31 at the user's request. The plan and the canvas mock-up were approved by the user
on 2026-10-31; PP-D1 was decided on 2026-11-03. Nothing of PL0 to PL6 and SM1 is built yet. NG1 was added by the user
on 2026-11-05; its relation-matrix part was built in 0.13 on 2026-11-09
([0.13 NG](BASE_0_13_IMPLEMENTATION_PLAN.md#ng-relation-matrices-in-navigation-groups)), and what is left of it is the
other view kinds; its decisions PP-D11–PP-D13 are open for them.

**Target:** Product 0.17.0, [the plain path](ROADMAP.md#product-release-017--the-plain-path).

**Depends on:** 0.16 released, with WM1 (see [PP-D2](#decisions)). The findings, principles and the detail of
PL0–PL2 and PL3–PL6 stay in [PLAIN_PATH_PLAN.md](PLAIN_PATH_PLAN.md) and are not repeated here. PL3b's full
scope is in this plan.

## Why

refiroo can do almost everything a steward or model administrator needs, but the everyday journeys are long
and show every capability at once ([the review](PLAIN_PATH_PLAN.md#why)). Import is what a new person meets
first. Today a drag in the model editor only opens a form: a column's drop opens the Map dialog and a move opens
the Move dialog (`ModelEditor.tsx`, `drop`).

## Outcome

- **A workbook becomes a workspace in one go,** and a person shapes its model by dragging on one screen beside
  the live result, with or without AI: columns, sheets, hierarchies, a list dropped on a field for a
  relationship, filters and navigation groups, in a very easy way.
- **The everyday journeys are short:** a change set starts with a name and publishes with one main action, a
  form asks required fields first, each workspace has a page, and plain words replace identifiers.
- **No capability is removed;** today's full controls stay one step away, and every drop is available through
  the API.

"A few words and a workbook" stays the route to a model and an import (0.16). The canvas is where a person
corrects that result, and the way to import when no provider is configured.

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [PL0](PLAIN_PATH_PLAN.md#pl0-the-principles-as-reference-rules) | — | The principles as reference rules in UI acceptance |
| [PL1](PLAIN_PATH_PLAN.md#pl1-change-sets-in-two-clicks) | PL0 | Start with a name; Publish checks, then confirms in plain words |
| [PL2](PLAIN_PATH_PLAN.md#pl2-plain-add-and-edit) | PL0 | Parent as a sentence, required first, inline errors |
| [PL3](PLAIN_PATH_PLAN.md#pl3-the-workspace-page) | PL0, WM1 | A page for each workspace, with search across it. **Edit model:** WM1 (0.16) delivers it in the workspace ⋯ menu and as a button on the workspace's page in Settings › Workspaces; both stay, and this page adds a button running the same action (the user, 2026-10-31) |
| [PL3b](#pl3b-the-workbook-canvas) | PL0 | The workbook beside the live result; every drop applies at once |
| [PL4](PLAIN_PATH_PLAN.md#pl4-new-workspace-from-a-workbook) | PL3, PL3b | The file and a name, what refiroo found, Create workspace |
| [PL5](PLAIN_PATH_PLAN.md#pl5-plain-words-and-identifiers) | PL0 | One list of replacements; Settings index; Back to the workspace |
| [PL6](PLAIN_PATH_PLAN.md#pl6-collection-import-and-export-and-your-changes) | PL0 | Import file-first; Export for people; draft steps grouped |
| [NG1](#ng1-views-in-navigation-groups) | — | A navigation group places a view of its own, not only a whole collection. Relation matrices are built (0.13 NG); left: the other view kinds, Move to group… on their rows and the canvas's group drop |
| [SM1](#sm1-account-security-messages) | — | Mail when a person's sign-in changes: password, second factor, passkey |
| [EM1](#em1-the-e-mail-is-the-sign-in-name) | — | The e-mail address is required, unique and the name a person signs in with; the separate username is gone |
| [EX1](#ex1-export-says-what-it-exports) | — | Export follows what is exported: a view gives a workbook shaped as the view, a type, an application or a workspace a sheet per type; every file says what it holds and imports back. Takes over PL6's "Export for people" |
| [MC1](#mc1-reuse-or-create-in-any-matrix-cell) | — | A filled matrix cell offers Link existing and Create wherever the model allows more than one record per cell; a user guide page with examples |
| [CA1](#ca1-the-parent-carries-fields-and-related-blocks) | — | A consumer API's parent serves any field and related blocks of its own, a related block may be served only on request (`include`), and an On related filter may narrow a parent block |
| [RF1](#rf1-review-findings) | — | Three engine defects from the project review of 2026-11-11: approve and publish lock in one order, a re-read never cancels a confirmed import, a failed file cleanup no longer keeps background work off |
| [SA1](#sa1-sign-in-managed-by-an-administrator) | EM1 | A person whose sign-in an administrator manages cannot change their own password, second factor or passkeys, and sees and ends only their own session |
| [R](#r-build-acceptance-and-release) | all | Full review since 0.16, the gates, the release |

**Order.** PL0, PL1, PL2, PL3, NG1, PL3b, PL4, PL5, PL6, SM1, R. EM1 was added by the user on 2026-11-11 and
delivered first, at their request; nothing else depends on it. NG1 comes before PL3b so the canvas's group drops
place views from the start. EX1 was added by the user on 2026-11-11 after exporting a relation matrix gave the
whole application's technical tables, and is delivered next, at their request. PL1 and PL2 are the cheapest fixes on the most frequent
paths. PL3 gives PL4 its place, and PL3b is where PL4's Adjust leads. Each UI package shows its mock-up with its
plan for one approval and is then delivered whole.

## Decisions

| ID | Decision | State |
| --- | --- | --- |
| PP-D1 | **Where a new workspace's first load goes.** Straight into live data (recommended: the workspace is new, nobody relies on it, and a change set adds a review of everything) or into a change set first. A load into an existing workspace keeps going into a change set. | **Decided by the user 2026-11-03: live data** |
| PP-D2 | **WM1 stays in 0.16.** PL3 and PL4 rely on it. Delivered 2026-10-31, as planned in [the 0.16 plan](BASE_0_16_IMPLEMENTATION_PLAN.md#wm1-change-a-workspaces-model-from-the-workspace). | Planning default |
| PP-D3 | **The canvas is a view of the model draft,** opened by PL4 and by an assistant's result, on the existing draft, operations, undo and dry run. There is no second store and no second dialect. Today's editor is reachable from it and edits the same draft. Shared pieces are extracted from the editor, never copied. | Planning default |
| PP-D4 | **A drop applies at once, as one operation request and one undo step,** as `MapColumnDialog` already does with several operations in one request. No dialog opens; a small panel on the item takes changes. A drop the engine refuses changes nothing and says why in place. | Follows the user's request |
| PP-D5 | **Every drop is reachable without AI and through the API.** Whatever a gesture needs that the engine lacks is added to the engine and API first, generically. | AGENTS.md |
| PP-D6 | **Wide sheets become a profile reading,** not a task-only step: `unpivot` on a source (the columns, the field naming each row, the field taking the value), read by the import path. It works for any import and repeats from the saved profile. The assistant's former `unpivots` is gone and its SQL derived sheets are task design only, so neither serves a person or a saved profile. | Approved with this plan, 2026-10-31 |
| PP-D7 | **Rows grouped under a heading become a profile reading too:** `fillDown` for columns repeated by blanks, and a heading row read as the parent of the rows beneath it. Neither exists today. | Approved with this plan, 2026-10-31 |
| PP-D8 | **The join is found over every row.** A list dropped on a field compares the two columns in PostgreSQL over the whole set. The stored overlaps of the profile (first 1,000 distinct values, best five) stay a hint only. When two candidates tie, the panel asks; nothing is guessed silently. | Rule: checks cover the whole set |
| PP-D9 | **The canvas never waits for a check.** The existing dry-run job runs after each step and a newer run cancels the older; the count reads "Checking…" until it answers, and the person may keep dropping. | Planning default |
| PP-D10 | **Phone:** the canvas works by the ⋯ menu at 390px; dragging is a desktop and tablet fast path. | Planning default |
| PP-D11 | **A view placed in a group leaves its collection** (recommended: it shows once, in the group; otherwise the sidebar shows it twice) or also stays as one of its collection's views. | Open. 0.13 NG built the second for relation matrices (the matrix stays among its row type's views); not put to the user |
| PP-D12 | **One ordered member list per group,** each member a collection or a view (recommended: the sidebar order is the declared order, mixing both), or `views` beside `collections` with collections first. The first changes the shape of `collections`; pre-1.0 allows it. | Open. 0.13 NG built the first (`{ "view": "<key>" }` beside collection keys in `collections`); not put to the user |
| PP-D13 | **Schema version:** the new member in schema 0.10 (recommended: additive, refused nowhere today) or a new schema version. | Open. 0.13 NG built schema 0.10, additive; not put to the user |
| PP-D14 | **The e-mail is the sign-in name** (EM1): required for an active person, unique ignoring case; the username is removed. | **Approved by the user 2026-11-11** |
| PP-D15 | **A provider's person needs an `email` claim;** an address another person holds refuses the first sign-in, and an administrator resolves it. Matching stays by `sub` (D363). | **Approved by the user 2026-11-11** |
| PP-D16 | **A deactivated person may have no e-mail,** so the address can be freed; reactivating needs one. | Planning default |
| PP-D17 | **The migration stops on an active person without an address or on a shared address,** naming them; nothing is invented. | Planning default |
| PP-D18 | **An export can name a view** (EX1): `POST /exports` takes `view` (application, view key and the page's state: search, filters, parent, columns shown), and the engine derives the workbook from the view's definition. Every list view kind has a layout: `table`, `tree`, `relationMatrix`, `mappingGrid`, `relationTable` (rows and `grid`). Why: the file must reflect what the person looked at, and an integrator gets the same file the UI gets (API first). Cost: one layout per view kind; the dialog stops building view-specific requests itself | **Approved by the user 2026-11-11** |
| PP-D19 | **A matrix's file loads back only its cells,** as the view edits only cells, by the matrix's `cellActions`. **Create matrices** (`create`, `edit`): a column group per column record with the cell fields; an edited cell changes its record under its version, a filled empty cell creates the cell record under the column's container with the row's relationship, a cleared cell changes nothing (D183), a cell holding several records is written joined and `not loaded` (D195). **Link matrices** (`link`, `unlink`): one column per column record listing the linked cell records by name and display field, `"; "` between them, with a list of the records the view may link in that column (D196, a warning, as a cell may hold several); an edited cell's list becomes that cell's links, adding and removing within that row and column only, under the row's set version (D186); a filled empty cell links; a cleared cell changes nothing. **A matrix allowing both** (`link` and `create`): a name in a cell that finds no record the column may link creates one under the column's container (PP-D20), shown as new in the import's preview before anything is written; without a container it is refused, naming the column. The About sheet's "New records go into" part is written exactly when the view allows `create`. A matrix with neither is written read-only. The row's columns are for orientation (`(not imported)`). Why: the view's own actions decide what the file may do; one rule for every model's matrices. Cost: removing every link or record of a cell stays in the app | **Approved by the user 2026-11-11** |
| PP-D20 | **Where a new cell record goes is chosen in the Export dialog,** per column record, from the matrix's containers read (D13), preselected with the container holding most of the exported cells of that column, none otherwise; the choice is fixed in the file's profile and listed in the file. A column with none refuses its filled empty cells, naming the column. Why: a profile's parent is fixed, not read from a cell; D13 keeps no model default and nothing is guessed. Cost: changing the container means exporting again | **Approved by the user 2026-11-11** |
| PP-D21 | **A type, an application or a workspace exported for editing gives a sheet per type** (each the type's people sheet: its fields and its relationships by name, parent by name), parents' types before their children's, one hidden profile with a source per sheet; a tree view gives the same for its types. Technical stays the format for systems and full copies. Why: one sheet mixing every type's columns (today's `Records`) is not for people; the profile already reads several sources. Cost: the people layout's one-type limit goes | **Approved by the user 2026-11-11** |
| PP-D22 | **Every XLSX export has an "About this export" sheet, the second sheet, written by one writer in one style:** a title and one sentence, then the same sections for every layout: What was exported (application, view or scope, workspace, context: live, change set, publication or date, search and filters, time, job), What it holds (rows, columns, counts), How it loads back (per edit), and the layout's own part where it has one (a matrix's containers); the technical import ignores it. CSV and JSONL stay as they are (the job's `output` describes them). Why: the user could not tell what the file held. Cost: none beyond the sheet | **Approved by the user 2026-11-11** |
| PP-D23 | **A filled matrix cell offers Create as well as Link existing** (MC1), each where the view's `cellActions` hold it, unless the cell may hold only one record: the binding's `uniqueToAncestorTypeKey` is the column type read `outgoing` (the cell's conflict rule), or the cardinality lets the row hold one. There Create stays for an empty, inactive or history-only cell, as since 0.8 A4. Why: many is the default (`cardinality` many-to-many); a mapping cell normally holds several records, and the user expects to reuse one or create one. Cost: none in the engine, whose uniqueness checks already refuse what the model forbids | **Approved by the user 2026-11-11** |
| PP-D24 | **A new cell record goes where the relationship's candidate rules allow** (MC1, EX1). A matrix offers, preselects or uses only containers under the column where a record created there meets the binding's candidate criteria at the cell end (for example `ancestor:<type>.name eq "<value>"`). When the criteria fix one ancestor exactly by equalities, the model lets that ancestor type sit under the column, and it does not exist yet, creating a cell creates that ancestor with those values and the record in one change, in the cell dialog and on import alike. Criteria that do not fix one place create nothing: the matching containers are offered, and the place is then the container under the column that already holds cells of this view (the one holding most; none on a tie); a container holding no cells is never preselected or used automatically, even as the only one, and stays choosable in the cell dialog under "Other groups (not used in this view)"; where there is none, the cell says so in plain words. Why: the model already states the place; the dialog ignored it, preselected a wrong group and saving failed with the relationship's model message (the user, 2026-11-11). Cost: one generic derivation from candidate criteria, shared by the cell dialog, the containers read and the import binding | **Approved by the user 2026-11-11** |
| PP-D25 | **A matrix export asks which field of the cell record fills the cells** (EX1), not a container. The choices are the cell type's identifying fields (name and its unique or display attributes); the file records the choice, so the import reads it without guessing; a value matching two records in a column is refused by name. The container choice leaves the dialog: it follows PP-D24, and where nothing could be chosen nothing is shown. `newCellContainers` is replaced by the derived place; the API takes the field (`cellField`) | **Approved by the user 2026-11-11** |
| PP-D26 | **An import guesses how a matrix or relationship column is read, without AI, and shows it before anything is written** (EX1). For a file that does not record its reading, each column is compared with each identifying field of that column's existing records; the field matching every non-empty cell, each to one record, is chosen. The preview gets a section "How the file is read": per column the field chosen, the cells matched, a choice to change it (the preview runs again), and where new records go, marked "will be created" when PP-D24 creates the place. The choice can be saved into the profile. Nothing is written before the person confirms | **Approved by the user 2026-11-11** |
| PP-D27 | **A link matrix export has a value sheet per column** (EX1). Each column's records (those the column offers: its place and the records linked in it) are listed as full rows, every field plus the group and a hidden ID; edits there load back as updates by ID, a new row creates a record in the column's place. The main sheet's cells list the field chosen in "What each cell lists", which offers every text field (default Name); its dropdowns read the value sheet's column, so a renamed or added row shows in them. A spreadsheet cannot sync two ways without macros, so the import does it: a main-sheet value naming a value-sheet row (by its name in the file) is that record, the same name typed in both is one record, and a name found in neither is a new record in the column's place with only that field. A value-sheet row picked nowhere is still created. A create matrix (cells hold the record's own fields) has no value sheet. Checked in Excel and Numbers before it is built further | **Approved by the user 2026-11-11** |
| PP-D28 | **No container in use: refiroo proposes one and asks** (MC1, EX1). Where neither the model's rules nor the data give a column's place (PP-D24), the place proposed is a new container under the column, of the type other columns use, named as the containers this view uses in other columns are named (the most common name). The cell dialog says so and creates the container and the record on one OK, the name editable; the import preview shows "will create group … under …" and confirming the import is the OK. No model rule is added for it | **Approved by the user 2026-11-11** |
| PP-D29 | **The parent serves what the object can** (CA1): its `fields` take any source `object.fields` takes (attributes, `ancestor:`), beside the four built-in ones, and it has `related` blocks of its own, written like the object's. One level: the parent has no parent. Why: an integrator needs the parent's IDs and its system values in one answer. Cost: a parent block repeats on every child row | **Approved by the user 2026-11-11** |
| PP-D30 | **A related block is served always or on request** (CA1), on the object and on the parent alike. An on-request block is served only when the request names it in `include` (`include=parent.systemVariants`, repeated or comma-separated); OpenAPI lists the names as an enum and the block as an optional property; an unknown name is `400` naming the valid ones. Default: always, so every existing definition answers as before. Why: default answers stay small; the shape stays typed | **Approved by the user 2026-11-11** |
| PP-D31 | **An On related filter may name a parent block** (`onRelated: "parent.systemVariants"`) and narrows it as it narrows the object's; `keepOnlyMatching` drops the results whose parent has no match. Its parameter name is the author's, as for every filter. Why: one filtering mechanism, no query language inside `include` | **Approved by the user 2026-11-11** |
| PP-D32 | **A filter on an on-request block is accepted without `include`:** `keepOnlyMatching` still narrows the results; the block is not served. Surfaces without a request (events, deliveries) leave on-request blocks out. | Planning default (recommended in the discussion, 2026-11-11) |

## PL3b: The workbook canvas

**Journey:** a person opens a workbook and sees its sheets on the left, the result in the middle with its sample
values, and the navigation on the right, already filled and marked Proposed by the inference or the assistant.
They drag until it reads as the business does, watching the count of rows that load or are refused, then
continue to the import.

sample rows. It computes its counts on those rows but is not connected to the engine.

### Gestures and what each one uses

Checked against the code on 2026-10-31.

| Drag | Result | The engine today | To add |
| --- | --- | --- | --- |
| A sheet onto empty space | A new list, its columns as fields | `addObjectType`, `addAttributeType`, `attachAttribute`, `addSource`, `mapColumn` in one request; `inference/list` answers with list rules | A table-shaped proposal for one sheet, answered at once |
| A column onto a list or field | A new or mapped field | Yes, `mapOperations` | The drop without the dialog |
| A column onto empty space | Its distinct values as a list, linked back | `convertAttributeToListType`, for a mapped attribute | The same for an unmapped column, as one request |
| A card's Connect handle or a sheet onto a field | A relationship, drawn as a dashed line | `allowRelation`, a `relation` binding by `mapColumn` | Whole-set join candidates (PP-D8) |
| A card's Connect handle onto another card | Parent and child, drawn as a solid line | `setContainment`; a `parent` binding or fixed `Source.parent` | Both in one request, with the parent column found as for a join |
| Several columns onto one field | Translations, flags or a wide sheet as rows | Translations by `relatedRecord`; flags by `relationFlags` | `unpivot` (PP-D6) |
| A column onto a list's filter box | A filter on the list | `setViewProperty` with `filterFields`, table views, for an attribute already there | The attribute added first, in one request |
| A list onto a group or New group | A navigation group | `addNavigationGroup`, `placeCollection`, `setNavigationGroup` | Nothing |
| A field back onto the workbook | The column left out | The inverse operations and `ignore` | Nothing |

**Actions on the sheet preview:** click the row that holds the headers (`headerRow`, with rebinding through
`setSource`, exists); mark a column as repeated by blanks, or a row as a heading (PP-D7). Side-by-side tables are
found already (`block`, `sources/layout.py`) and appear as separate tables.

**Placing and connecting (the user, 2026-10-31):** the board is a free surface. A card is placed anywhere by its
top bar, which never changes the model, so a card moved near another cannot link them by accident. Connecting is
its own gesture, the Connect handle, and every connection is a visible line with a × that removes it. Tidy
arranges the cards to use the board's width. Positions belong to the draft's canvas, are readable through the
API, and are not part of the model release.

**Also on the canvas**
- **Refusals:** the count covers every row; a click opens the rows by reason. A wrong value is corrected by
  dropping it on the right one (`setValueMap`).
- **Undo and redo:** the existing routes, shared by model and profile. A step a later step depends on cannot be
  undone alone; the toolbar then says what it depends on.
- **Field order and layout:** the preview's existing layout editing, not a second implementation.
- **Without dragging:** every gesture has a menu and keyboard path (MODEL_AUTHORING).
- **Suggest…:** where a provider is configured, an assistant's proposal lands as Proposed cards. With none, it
  is not shown.

### Engine and API work

1. The `unpivot`, `fillDown` and heading-row readings in the import profile, the reader, the dry run and the
   import, in PostgreSQL over the whole set; `docs/API.md` updated.
2. A route returning whole-set join candidates between two sources or columns.
3. A table-shaped proposal for one sheet, answered at once without the inference job.
4. The operation requests of the table above; a one-step route only where a client cannot compose them.
5. **An assistant's result must carry its profile.** The session can pass a dry run with the profile sent inline,
   and `tasks/agent.py` does not check that `draft.profile_json` was stored. Not proven in a run; PL3b tries it
   once, and if the profile can be missing, the task fails with a plain reason unless it is stored.

**Door check (ADR-032):** the new profile readings change only how rows are read. Identity, attribute storage,
history, bulk APIs, `match` and mapping coverage are not affected.

**Measure once:** a drop and its dry run at 200 and 2,000 records, reported with AI, job and overhead shown
apart where relevant. Known figures: an editor step at 2,000 records about 1.4 s; dry runs of 19,453 items about
7 s and 40,107 items 22.2 s; a large workspace's step about 3.5 minutes (`POSTGRESQL_BUDGETS.md`). The last is
why PP-D9 stands. Volume runs only if these basics give a reason.

**Tests:** journeys through the API on two model configurations (J51): a flat sheet shaped into a hierarchy with
its relationship, filter and group, then loaded; a wide sheet by `unpivot` and grouped rows by `fillDown`, each
repeated from the saved profile; a tied join asked rather than guessed; a caller without the groups refused by
code. Browser: a real sample workbook from drops to import, including undo, a refused row corrected and an
invalid draft; each gesture by keyboard; 390px; axe; no 5xx. Real-file smoke on the user's samples: a flat
hierarchy, a wide sheet with its header on row 2, and a workbook with side-by-side lists. **Before and after:**
an inventory diff on the user's model, since the profile reader changes.

**Documentation (the user, 2026-10-31: required, part of being finished):** the guide explains the canvas for
a person who has never seen it: a how-to in "Model your domain" ([0.13 plan](BASE_0_13_IMPLEMENTATION_PLAN.md#5-model-your-domain))
covering placing cards, making lists, connecting (hierarchy and relationship), filters and groups, reading
refused rows, wide sheets and grouped rows, repeating a load from the saved profile, and doing it all without
dragging and through the API, with screenshots. PL3b updates these pages in the same change, by the rule in the
[documentation plan](DOCUMENTATION_PLAN.md#timing). If the guide does not exist yet when PL3b is delivered, the
text goes in with PL3b as the seed in `MODEL_AUTHORING.md` and `PRODUCT.md`, and DOC writes it from there.

**Said plainly:** the canvas builds a new model, or a new version of a draft's. Reshaping records already in a
workspace stays with restructuring and WM1. Consumer APIs and security stay in their own pages.

## NG1: Views in navigation groups

_Added by the user on 2026-11-05._ **Part built in 0.13 (2026-11-09, [0.13 NG](BASE_0_13_IMPLEMENTATION_PLAN.md#ng-relation-matrices-in-navigation-groups)).**
A group's `collections` takes `{ "view": "<relation matrix view key>" }` beside collection keys, in one order; validation, the
`placeCollection` operation with `view` (place, move, take out), the cascade on a view's removal or new key, the outline, the
sidebar and group page entries, the group's panel in the editor with **Add to group…** and **Move to group…** on a relation
matrix's row in **Views**, and a collection's opening view (`navigation.opens`, `setCollectionOpening`) exist. **What is left**
for 0.17 is the rest of the section below for every other view kind (a table, a tree, a mapping grid, a relationships table, a
record page's view): their members in the model, the operation, the sidebar and the group page, **Move to group…** on their rows,
the decision PP-D11 for them, and PL3b's group drop placing a view. The text below is the original plan, read against that.

Today (before 0.13 NG) a navigation group names only collections
(`NavigationGroupDefinition.collections`, `models/schema.py`): a view appears in the sidebar under its source
collection, a relation matrix under its row type (`viewSourceObjectTypeKey`, `frontend/src/model/collections.ts`).
A matrix therefore enters a group only with every other view of its row type. NG1 lets a group place a view itself,
for any view kind, in the model, the API, the sidebar and the editor.

- **Model and validation:** a group member may name a view of the application (shape by PP-D12, version by
  PP-D13). `_check_navigation` (`validation/application_rules.py`) refuses a view the application does not
  declare (`INVALID_REFERENCE`) and a view in a second group (`INVALID_MODEL`), at the member's pointer, as for
  collections.
- **Authoring:** an operation places a view in a group or takes it out, as `placeCollection` does for a
  collection; renaming or removing a view updates or drops its group member (`authoring/references.py`,
  `authoring/cascade.py`). Workbook inference keeps producing collection members.
- **Sidebar:** `navigationSections` places grouped views as their own entries and, by PP-D11, leaves them out of
  their collection's views; the group page (`NavigationGroupPage.tsx`) lists them. A record page's child
  collections and the application's default view keep working when they involve a grouped view.
- **Editor:** **Move to group…** on a view's row in **Views**, and the group's members list shows views
  (`operations.ts`, `ElementPanel.tsx`). PL3b's group drop accepts a view the same way.
- **Tests and docs:** journey tests through the API for the refusals, the cascade on view removal and the
  move; the guide pages on navigation groups and relation matrices updated with their screens.

## SM1: Account security messages

_Added by the user on 2026-11-03,_ after the branded mail templates. Today a person gets mail only to activate
an account or reset a password. SM1 sends a message when their sign-in changes, so a change they did not make
is noticed: the password was changed or reset (`identity/resets.py`), a second factor was added or removed
(`identity/second_factor.py`), a passkey was added or removed (`identity/passkeys.py`). Each message says what
changed and when, and what to do if it was not them, in the shared branded layout with its plain-text part, and
carries no secret, code or link that signs in (D421). It is queued in the same transaction as the change, as
activation is. The exact list of events and whether a person can switch these messages off are settled in
SM1's plan.

## EM1: The e-mail is the sign-in name

_Added by the user on 2026-11-11,_ to make signing in easy, also with an external provider. Today a person
has a username (required, unique ignoring case) and an optional e-mail that is not unique; they sign in with
the username; a provider's person gets a username from `preferred_username`, else `email`, else
`<provider key>-<sub>` (D363). After EM1 the e-mail is the only name a person has for signing in.

- **The person:** `email` is required for an active person and unique ignoring case; the `username` column,
  its index and every API field named after it are gone (pre-1.0). A deactivated person may have no e-mail,
  so history keeps them and their address can be freed; reactivating one needs an e-mail (`422`). Who acted
  is resolved by the person's ID and name, as before; past security events keep the username they recorded.
- **Signing in:** the password page, the API's password step, the reset request, the failed-sign-in counter
  (per e-mail, case folded) and the password rule that refuses a password containing the account name all use
  the e-mail. Where a standard names a parameter or claim (`username` in an OAuth grant, `preferred_username`
  in a token the engine issues), the standard name stays and carries the e-mail.
- **A provider's person:** still found only by provider and `sub`, never by e-mail (D363 stands). The first
  sign-in needs an `email` claim; without one it is refused, and the message names the missing claim and that
  the provider's administrator adds it. An e-mail already held by another person refuses the first sign-in
  (`email_taken`), and the message says a security administrator resolves it; OPERATIONS gives the steps
  (deactivate the old person and clear their e-mail, or change it). At later sign-ins the e-mail is refreshed
  from the token as before, unless another person holds the new one; then the stored e-mail stays and the
  sign-in succeeds.
- **The migration:** an active person without an e-mail whose username is an address takes it as the e-mail.
  If an active person still has none, or two people share one ignoring case, the migration stops and names
  them, so an operator fixes them first; nothing is invented. On dev every active person has an e-mail
  (checked 2026-11-11: 3 active, 3 with an e-mail; the 4 without are deactivated).
- **Everywhere else:** `POST /users` takes `{name, email}`; adding members takes an ID or an e-mail; the CLI
  that creates the first administrator takes `--email`; the Users pages, the New person dialog and the member
  pickers show and ask for the e-mail; the MCP tools and the OpenAPI document follow.
- **Decisions:** PP-D14 (the e-mail is the sign-in name; the username is removed) and PP-D15 (a provider's
  person needs an `email` claim; an address already taken refuses the first sign-in) were approved by the user on
  2026-11-11. PP-D16 (a deactivated person may have no e-mail) and PP-D17 (the migration stops on a missing or
  shared address rather than inventing one) are planning defaults.
- **Tests and docs:** journey tests through the API for local sign-in by e-mail, the uniqueness refusal, a
  provider's first sign-in without the claim and with a taken address; API.md, OPERATIONS, DECISIONS (D363
  amended), the guide sentences that name the username, CHANGELOG.

## EX1: Export says what it exports

**Why.** The user exported a relation matrix (a row type against languages, a translation in each cell) to edit
translations and import them back, and got the technical tables of every type in the application: one `Records`
sheet of 3,300 records with every type's columns, one `Relationships` sheet, nothing saying what was exported.
Cause: only the table view hands its state to Export (`CollectionView`, `onExportContext`); every other view
leaves the dialog on "the application's types, Technical". The people workbook's columns per parent (0.9 J6a)
would have given the shape, but they read only an owning relationship (one required binding, `_sheet_plan` in
`engine/jobs/people.py`), and a translation relationship bound from several types is not one.

**What exporting means, by what is exported:**

| From | The file | Loads back |
| --- | --- | --- |
| A table view | Today's people workbook with the view's columns, filters, search and parent | As today (D183) |
| A relation matrix | One row per row record (the view's row columns); a create matrix: a column group per column record with the view's cell fields and hidden cell IDs and versions; a link matrix: a column per column record listing the linked records; hidden record ID and set version | The cells, by the view's actions (PP-D19, PP-D20) |
| A relationships table | One row per relationship: both records' view columns and the relationship's attributes; hidden IDs and version | Attribute edits; a row without IDs adds a relationship by names (D187) |
| A relationships grid | One row per `from` record, a column group per related record shown: Linked (Yes/No) and the relationship's attributes | Attributes; Yes on an unlinked pair links it; No removes nothing |
| A mapping grid | One row per source record, the view's source columns and the mapped target by its display field | The mapping column, as a people relation column |
| A tree | A sheet per type of the tree, parent by name | As the type sheets below |
| A type, an application, a workspace | For editing: a sheet per type (PP-D21). Technical: today's tables | For editing: every sheet; technical: as today |

Every XLSX file has "About this export" (PP-D22). The engine derives each layout from the view's definition
(PP-D18); views of the same kind in other models get the same file.

**The dialog** (mock-up; one dialog for every page, `ExportDialog`):

```
Export
What
 (•) This view: Names in every language        200 rows × 8 columns, from change set “…”
 ( ) The type: every record and field
 ( ) The application: every type, a sheet each
 ( ) The whole workspace
Format          (•) For editing in a spreadsheet, imports back    ( ) Technical, for systems
New records in a column go into            (matrix with Add only)
 Arabic   [Group A ▾]   …   German   [None: choose a group ▾]
                                                        [Cancel] [Export]
```

"This view" is the first choice on every view; on a page without a view the dialog opens on the application.
Technical is offered for a type, an application and a workspace, and for a table view as today.

a create matrix, and `sample-matrix-export-links.xlsx`, a link matrix, each with its About sheet, approved before the build.

**Engine and API.** `ExportRequest.view` (PP-D18) beside today's `scope`, refused `INVALID_EXPORT_LAYOUT` with a
pointer where the view is unknown, not a list view, or its state names a field it does not declare;
`people` accepts several types (PP-D21); the matrix's containers as `view.newCellContainers` (column record ID
to container ID, checked against the containers read). The written profile reads every layout back through the
existing import; whatever a layout needs that the profile cannot express is added to the profile generically.
Reads stay set work in PostgreSQL, one statement per sheet part as today; checks cover every row.

**Frontend.** Every list view hands its state to the shell as `CollectionView` does, through one hook, not a
copy per view; `ExportDialog` gains What, the format choice and the containers, and drops its view-specific
request building. PL6 keeps import file-first and Your changes.

**Tests (a quarter of the package at most):** API journeys on generated models: a matrix exported from a
change set, a cell edited, an empty cell filled, a cell cleared, a column without a container, imported back
into the change set with each outcome; a relationships grid and a mapping grid round trip; an application
exported for editing and imported back unchanged (every row `unchanged`); the technical XLSX with its About sheet
imported back unchanged; the refusals. Vitest for the dialog's choices per view kind. One browser runner: export
from a matrix and a tree, 1440px and 390px, axe. A real-file try on the user's matrix, opened in Numbers.

## MC1: Reuse or create in any matrix cell

**Why.** The user, 2026-11-11, on a link-and-create matrix in dev: a cell already holding two linked records showed
neither a way to link another existing record nor to create a new one, though the view allows both. Create is shown
only for an empty, inactive or history-only cell (`createButton` in `RelationMatrixCellDialog.tsx`, the rule since 0.8
A4, kept by 0.13 RV). Link existing should show in a filled cell by the code and its tests; the user does not see it
on their page, and the cause is being checked on the page itself.

**Scope.**
- The cell dialog, filled cell, by PP-D23:

```
Booked · SystemX                                     [Filter …]  [Link existing value]  [+ Create value]
  Name          Code   Active   Default mapping
  Booked        BKD    Yes      Yes                                         Unlink
  Confirmed     CNF    Yes      No                                          Unlink
```

  Where the cell may hold one record, a filled cell keeps today's dialog. A created record goes into a container the
  person picks, as for an empty cell (D13). Link lists the candidates with the reason any cannot be linked, as today.
- The export follows the same rule (EX1, PP-D19: a matrix allowing both).
- Whatever makes Link existing missing on the user's page, found on that page and fixed.
- **The user guide** (a Codex wave, `guide/_waves/MC1-GUIDE.md`, after the build, the code winning): how a matrix cell
  is filled, by example. A translation matrix: create, one per language. A mapping matrix: reuse a record already
  linked elsewhere, or create one. A matrix that allows one per cell: what the dialog shows, and the conflict a change
  set can hold. What each action does to relationships: a link is a relationship, an unlink removes the relationship,
  never the record, and a record created in a cell sits in its container and is listed there too. What a consumer API
  sees: the new record and relationship once the change set is published, the same record ID under every row that
  reuses it, and an unlink as a removed relationship in the feed. Where the actions are set (the model editor, the
  view's Change…, "What people can do in a cell") and why the editor may not offer one. The export of such a view
  (EX1). Pages: `use/fill-in-a-relation-matrix.md`, `model/add-a-relation-matrix.md` and the integrator page that
  explains relationships in the consumer API, extended rather than duplicated.

**Tests.** Vitest for the dialog: a filled cell in a many-allowed matrix offers both, a one-per-cell matrix offers Link
only; the existing browser runner `a4-relation-matrix` extended by one step (create in a filled cell), 1440px and
390px, axe. A try on the user's view in dev.

**Extension: the place and the reading (the user, 2026-11-11, PP-D24 to PP-D26).** On a link-and-create matrix in dev a
column whose system had one group of another kind preselected that group, Create failed with the relationship's candidate
message, and the export offered that group for new cells. Built here and in EX1: containers follow the candidate rules,
a missing exactly-named container is created with the record (cell dialog and import), the export's container choice is
replaced by the cell field choice, and the import shows and lets the person change how each column is read. The guide wave
`MC1-GUIDE` is rerun on the result.

**Delivery record (code part).** `createButton` in `RelationMatrixCellDialog.tsx` now also shows in a filled cell unless
`binding.scoped` (uniqueness scope is the column, read outgoing) or the binding's cardinality lets the row's end hold one
(`one-to-one`, or `many-to-one` read outgoing / `one-to-many` read incoming, the `_HOLDS_ONE` table). The page response and
the model already carry the binding and its cardinality, so no API, OpenAPI or backend change. Checks: Vitest
`RelationMatrixView.test.tsx` 34 passed (one new: many-allowed filled cell offers both buttons, scope-of-column filled cell
only Link); `vitest related` 8 files, 186 passed; `tsc -b` clean; `npm run lint` 0 errors; `npm run build` ok; browser runner
`a4-relation-matrix.mjs` one new step (create in a filled cell, 1440px and 390px, axe 0 violations, no horizontal scroll)
passed, 11 checks. The guide wave and the Link-existing-missing check on the user's page are outside this part.


**Delivery record (2026-11-11).** Built: `ExportRequest.view`; `engine/jobs/export_views.py` (view to scope, layout and
state predicates), `matrix_sheets.py`, `grid_sheets.py`, `view_sheets.py`, `about.py`; `people.py` as a sheet per type
(parent by name or hidden ID); `xlsx.py` About sheet, group rows, soft lists; `engine/reads/matrix_read.py` (the matrix read moved
out of the management projection); profile `relatedRecord.idColumn` and `relation.within`; the dialog and one
`useViewExport` hook in the view host. Decided by recommendation: a cleared or empty matrix cell changes nothing; the About
sheet is not in `output.sheets`; a column left out of `newCellContainers` gets the container with most of its cells (the dialog
preselects the matrix's `suggestedContainerId`, none otherwise); a relationships table's search matches either end, its
`relation:` filters are not carried (the dialog says so); a record is written in its own application; a name or label holding
`;` is read as a comma in a link cell; a required relationship set that is empty and stays empty is unchanged. Checks: `jobs`
group 750 passed (2 `test_batch_statements` failures, also at HEAD); J27 export-views journeys (create, link, link and
create, rows and grid, table and mapping, tree, change set, technical, refusals), unit, contract, Vitest, `test:browser:ex1`
(matrix, tree, application, 390px, axe) green. Tries on dev (stops, own change set): type-translations matrix edited, filled,
refused for German by name; classes-by-system edited; the Translations application 5,000 rows and the technical file 10,000 items
all unchanged. The dialog's count line ("200 rows × 8 columns, from change set …" for a table, matrix or grid; records for a tree or mapping grid) is delivered, taken from the page's own totals; no API change.

**Delivery record (extension, PP-D24 to PP-D26, 2026-11-11).** Built: `engine/model/candidate_places.py` (`derive_place`, `identifying_fields`),
`candidate_place_filters` in `engine/reads/model_query.py` (the ancestor part of `candidate_ids`, one evaluator), `container_rows` and
`derived_place` in `engine/reads/matrix_read.py`; the containers read filtered by the criteria with `derivedPlace` (`suggestedContainerId`
removed); `ExportView.cellField` (`newCellContainers` removed; `matrix_sheets.py` lists by the field, the profile records
`within.field`, a create matrix reads back through `relatedRecord.under`); `engine/imports/places.py` (`resolve_place`: containers by
`meets_criteria`, else the derived place), binding: places resolved before the rows, a new place as a virtual context record and a
phase-0 item, `import_scope_values` and `_guess_fields` (one statement over distinct values), the report column `reading`;
`engine/imports/reread.py` and `POST /jobs/{jobId}/reread`; the dialog's atomic batch (`createObjectInNewPlace`), the export dialog's
"What each cell lists", the preview section "How the file is read". Decided by recommendation: identifying fields are the name, the display
attribute and unique text attributes (the existing `is_identifying` stays the stricter rule for replacing sets); a place is derived only
directly under the column type and only when every value its type requires is among the criteria; own-field criteria are left to the write;
`cellField` applies to a link matrix, the export is refused where a linked record has no value in the field; a value creates a record only
when the field is the name; a column with several matching containers or none gives the plain refusal; the guess applies to a matrix column
whose profile records neither `within.field` nor a label attribute (an older file keeps its label reading), other relationship columns show
their recorded field with the same choice but no counts; rereading cancels the first preview and keeps the stored profile's key so the choice
can be saved by `PUT /import-profiles/{key}`. Follow-up, PP-D24 by evidence (2026-11-11): `choose_container` (`candidate_places.py`) picks, among the containers meeting the criteria, the one the criteria fix when it is the only one, else the one already holding cells of the view (most; none on a tie); a container with none is never the default. The containers read gives each container's `cellCount`, lists used containers first and `defaultContainerId` follows the rule; the import (`places.py`) counts the cell-type records under each container the same way and refuses a new cell with a plain `message` (also `newRecords.message` in the preview); the dialog preselects nothing for an unused group and lists it under "Other groups (not used in this view)". Cells counted are the cell-type records directly under a container, whether or not linked. Checks: `test_j27_export_views` 29 passed (new: busiest group wins, unused sole group and a tie not used), `test_relation_matrix_writes` containers assertions follow the rule, Vitest dialog "Other groups", `a4-relation-matrix` chooses the unused English group. Earlier checks: `test_j27_export_views` 28 passed (new: containers filtered and the place created in a
batch, the import creating the place, the field round trip with refusals, guess and override); unit `test_candidate_places`; contract lock
re-baselined; Vitest `ExportDialog`, `RelationMatrixView`, `JobPage`; `ex1-export` and `a4-relation-matrix` browser runners (1440px, 390px,
axe 0). Dev tries: see the report of the package.

**Delivery record (value sheets and a proposed container, PP-D27 and PP-D28, 2026-11-11).** Built: `engine/jobs/matrix_sheets.py`
(`_ValueSheet`, `_ValueField`, `_value_fields`, `_value_sheet`: a table sheet per column of the records the column offers and those linked
in it, as full rows with the group and a hidden ID and version; `chosen` is `cellField` or the name; the dropdowns are soft lists over a
defined name per column), `engine/jobs/xlsx.py` (`PlainSheet.table`, `Workbook.define`: an Excel table in place of the sheet filter, a
workbook-level defined name over a table column), `engine/model/candidate_places.py` (`identifying_fields` is every text field, not only the unique
ones; `propose_place`, `DerivedPlace.proposed`), `models/imports.py` and `engine/imports/profiles.py` (`Source.under`: `SourceUnder`),
`engine/imports/binding.py` (a value-sheet row without an ID takes the column's place as its parent; `_resolve_place` shared with the
other place users; `import_value_rows` and `_value_rows`: each row by every field, set-wise; a main-sheet value finds a value-sheet row
first; any recorded field creates a record, named by the value and holding it in the field when that is not the name; the place's
first-row union includes value-sheet rows; reading counts `_value_sheet_counts` and `_value_sheet_reading`; `newRecords.typeName` and
`under`; a new place takes its column record's application), `engine/imports/places.py` (`_proposal`: the proposal where the rules and the
data give no place, one statement over the containers the view uses in other columns), `engine/reads/matrix_read.py`
(`proposed_place`, `column_application`, `container_applications`), the containers projection and schema (`derivedPlace.proposed` and
`applicationKey`, each container's `applicationKey`), the job schema's additive reading fields; the dialog (`RelationMatrixCellDialog`: a
plain sentence, the name editable, one OK through `createObjectInNewPlace`, "Use an existing group instead"; the cell and the group are
created in the application of their parent), the preview ("Value sheet" rows, "will create group … under …"), the export field list. Decided by
recommendation (the coordinator accepted the first two): a created record takes the value as its name, plus the attribute when the
field is not the name; link-only views get a value sheet for the dropdowns and for reading, with new rows only where the view has
`create` (a view with `edit` only edits by ID); the value sheet carries a hidden version beside the ID, so an edit is refused when the
record changed; a view's default `cellField` is the name (the older `name (display field)` label is no longer written; an older file
still reads); the sheet's group column is for reading; a renamed record is found by its new value and by its old one unless another
row of the sheet holds it now, and a record the sheet does not list keeps matching by its stored values (two records holding one code
stay ambiguous); a proposed container is dropped where its type asks for a value (the dialog could not fill it) or a container so
named would fail the binding's ancestor criteria; a tie among names goes to the first in order; types are counted by containers
in use under other columns. Checks: `test_j27_export_views` 34 passed (new: `J27.27` value sheets by ID, new rows, a name typed twice, a name
in neither place, a row picked nowhere; `J27.28` the proposed container by the dialog's batch; the proposal in the busiest-group test and the
create-matrix test; the code-field test now creates a record for an unknown code), unit `test_candidate_places` (7), `test_xlsx` (32), `jobs`,
`imports`, `model` unit directories, `test_boundaries`, `test_relation_matrix_writes` and `test_openapi_contract` (re-baselined, additive)
green; `test_api_journeys` fails on `hideEmptyColumns` (not this work). Vitest `RelationMatrixView` (the proposal, an existing group
instead), `JobPage` (value sheet and "will create group … under …"), `exportRequest` (the field list); `tsc -b`, eslint and `npm run build` clean;
`test:browser:ex1` (value sheets in the file, "Value sheet" in the reading, axe 0) and `test:browser:a4` (a column with no group where the
starter's group type needs a code: no proposal, the plain message, 1440px and 390px, axe 0) passed; their screenshots were not looked at.
Dev tries (a developer workspace, in a change set, discarded): a link-and-create matrix exported for two columns, imported unchanged (24
unchanged), then with a value renamed, a value-sheet row added and picked in a cell, and a new name typed in a cell: 3 updated, 2 created, 0
refused; the renamed record kept its ID, the added row is one record in the column's place with its code, the typed name is a record with no
other value, live data untouched. A create-and-edit matrix whose column had one unused group: the proposal was the group type the other columns use, named
as theirs, `proposed` and `willBeCreated`; the dialog's batch created the group and the cell (applied, the group then offered with one cell); an import of a typed
value previewed "will create … under …" and created it on confirm. The dialog creates the cell in its parent's application: a type
that several applications list was refused (`PARENT_WRONG_SCOPE`) when the dialog took the first application listing it, for a new group and for

## CA1: The parent carries fields and related blocks

_Added by the user on 2026-11-11,_ after an XREF answer gave the parent only its type, ID, code and name, while
the integrator needed the parent's master ID and its external ID in one system. Mock-up approved the same day
(the consumer API editor with a Parent section, a Served column and a parent block in the On related filter):

- **Model:** `object.parent` (the `ParentSpec` form) takes `fields` as `object.fields` does, the four built-in
  names still allowed, and `related` as `object.related` does; a parent of the parent is refused. Every related
  block, on the object and on the parent, takes `served`: `always` (default) or `onRequest`. An `onRelated`
  filter may name `parent.<block>`. Validation names the authored pointer on every refusal; the short tuple form
  of `parent` stays.
- **Reads:** get by ID, lists, XREF, resolve and batch items serve the parent's fields and its always-blocks, and
  the on-request blocks the request names in `include`; filters narrow parent blocks as object blocks (PP-D31,
  PP-D32). The work is set-based in PostgreSQL, as the object's blocks are; no per-row queries.
- **Contract:** the OpenAPI document gives the parent's schema its fields and blocks, `include` as an enum per
  endpoint, and the new filter parameters; the contract check classifies adding them as compatible.
- **Editor:** per the mock-up. Fields tab: a Parent section (output name, fields from the parent types'
  attributes, the parent's related table with the Served column, Add related). Types and related: the Served
  column on the object's blocks. Filters: the On related block picker lists the parent's blocks. Existing
  editor components are reused (EditorTable, the field and via pickers), never copied.
- **Decisions:** PP-D29 to PP-D31 approved by the user on 2026-11-11; PP-D32 is a planning default.
- **Tests and docs:** journey tests through the consumer API (a parent field, an on-request parent block with
  and without `include`, its filter, `keepOnlyMatching`, an unknown `include`); editor unit tests; API.md,
  CONSUMER_API.md, the API reference text, the guide pages on consumer APIs (a Codex wave), CHANGELOG.

## RF1: Review findings

_Added by the user on 2026-11-11,_ after a review of the whole project (backend, frontend, website, deployment)
that read the code and ran nothing. The user chose three confirmed engine defects for this package. Nothing
else depends on it.

- **RF1-F1, approve and publish lock in one order.** `change_sets/approvals.decide` locked the change set and
  then the workspace, while `apply_publication` locks the workspace and then the change set (ARCHITECTURE,
  publishing). An approval beside a publish or a change-set move of the same change set could end in
  PostgreSQL's deadlock error, which nothing handles. A decision that publishes takes the workspace's lock
  first, through the one function publishing uses.
- **RF1-F2, a re-read never touches a confirmed import.** `imports/reread.reread_import` checked the waiting
  preview without a lock and cancelled it after the new preview was committed, so an import confirmed in
  between was cancelled partway, or a finished one left a stray preview. The re-read replaces a preview that
  still waits in one transaction, or is refused with `JOB_NOT_AWAITING_CONFIRMATION` and creates nothing.
- **RF1-F3, a failed file cleanup does not keep background work off.** `ModelThreads.start` marked itself
  started before the job-file cleanup; a failure there left the job worker, exporter, assistant, listener,
  deriver and dispatcher unstarted until a restart. The failure is logged and the threads start; the cleanup
  runs again at the next start.
- **Tests and docs:** one regression test per finding; CHANGELOG. No guide page describes these behaviours.
- **Delivered 2026-11-11.** Checks run: `tests/test_pg3_concurrency.py`, `tests/test_startup.py`,
  `tests/journeys/test_j42_approvals.py` and `tests/journeys/test_j27_export_views.py`, 88 passed; Ruff on the
  changed files. The F1 test fails without the fix. The F2 test covers the refusal and that a confirmed job
  gets no cancel request; the two requests racing each other are not exercised by a test.

**Found by the same review, not in this package and not scheduled** (the user decides whether and where each
goes):

- Engine: an assistant session in a container can read other tasks' folders and transcripts on its requester's
  plain request, not only when steered by a workbook (the limit recorded in OPERATIONS, `AI_AGENT_SANDBOX`);
  the provider's credentials reach the session's environment; webhook addresses may name loopback and private
  ranges; a CSV export writes values a spreadsheet reads as formulas; placing new matrix cells in an import
  reads whole record sets once per column; two first sign-ins through a provider at once give an internal
  error.
- Deployment: the engine image installs Claude Code without a version, base images are pinned by tag, the
  backend has no lock file; the content security policy holds only `frame-ancestors`; `ci.yml` has no
  `permissions` block; `AI_AGENT_SANDBOX=container` is not set in the image or the compose file.
- Frontend: the reset token stays in the address bar; search boxes copied beside `ui/SearchField`; the event
  stream loses events during a reconnect; no code splitting.
- Website (its own repository): the public demo account can change its own password and owns its workspaces;
  the demo's deploy still creates people by username; the early-access form and the sign-up lookups have no
  rate limit.

## SA1: Sign-in managed by an administrator

_Added by the user on 2026-11-11,_ from the project review (RF1): an account several people share by a known
password can be taken from all of them by one, who changes the password, enrols a second factor or signs the
others out. Plan approved by the user the same day, with the session limits included.

- **The switch:** a person has `signInManaged` (default off), read on `GET /me` and on the person, set only
  by who may administer people, through the API and the person form on the People page. Any shared, kiosk or
  training account uses it; nothing names a use.
- **While it is on, for that person:** changing the own password, enrolling, confirming or removing a second
  factor, new recovery codes, and registering, renaming or removing a passkey are refused with
  `403 SIGN_IN_MANAGED`. A forgotten-password request for the address answers as for any address and sends
  nothing. `GET /me/sessions` lists only the session of the request; ending another session or all sessions is
  refused with the same code; ending the own session (signing out) works. An administrator's reset link still
  sets the password, and an administrator still removes a second factor.
- **UI:** the account page hides the password, second factor, passkey and other-session parts for such a
  person and says in one line that an administrator manages the sign-in (hidden, not disabled: Z5 D323). The
  person form gets one checkbox in its existing pattern. No new surface.
- **Not covered:** wrong passwords sent for the account's name still slow its sign-in for everyone
  (`SIGN_IN_SLOWED` counts per account name for every account); changing that weakens the protection against
  guessing and is left as it is.
- **Journey cases (given / when / then):**
  1. A managed person signed in / changes the own password with the right current one / `403 SIGN_IN_MANAGED`,
     and the old password still signs in.
  2. A managed person / starts a second factor or a passkey registration / `403 SIGN_IN_MANAGED`, nothing enrolled.
  3. A managed person with two sessions / lists sessions from one / only that one; ending the other or all is
     refused and the other session still works; signing out the own one works.
  4. A forgotten-password request for a managed person's address / the public answer / the same as for any
     address, and no mail is queued.
  5. An administrator / switches it on and off, and sets a managed person's password by a reset link / allowed;
     a person without the right to administer people cannot set the switch.
  6. A person without the switch / the same own-account actions / as before.
- **Docs:** API.md, CURRENT_FUNCTIONALITY, the journey catalogue and API inventory, CHANGELOG; the guide pages
  on the account and on People (a Codex wave).
- **Delivered 2026-11-11.** One rule in `engine/identity/managed.py`; migration `20261129_01`; the person form's
  checkbox and the account page's one line; six journey cases in `tests/journeys/test_j39_managed_sign_in.py`
  (J39.12), 12 passed on two configurations. Checks run: the identity, sign-in, second-factor, passkey, reset-by-mail
  and startup tests and the contract group's modules (224 passed; `test_api_journeys` lists no
  `hideEmptyColumns`, from the list browsing work, not this package); two Vitest files; the frontend build; the Account and People browser runners. The
  guide pages on the account and on People still describe the earlier behaviour (a Codex wave).
  **Decision, confirmed 2026-11-11:** a managed person without a second factor is not asked to set one up, even
  where the instance requires one, because enrolling is refused.

## R: Build acceptance and release

Starts with the full review of every change since 0.16; the contract lock marked additive (the new profile
fields and routes); documentation (PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, API, MODEL_AUTHORING, journeys,
CHANGELOG); each heavy run announced, one at a time.

## Exit gate

- A real workbook is shaped on the canvas without a dialog and without AI, every row checked, and becomes a
  workspace in one confirmed step.
- A flat sheet becomes a hierarchy, a list dropped on a field becomes a relationship, a wide sheet becomes rows,
  and rows under headings get their parents; each repeats next month from the saved profile.
- With a provider, an assistant's result opens on the same canvas and can be corrected there.
- Every drag has a menu and keyboard path, and everything a drop does is available through the API.
- A change set publishes from one main action; a form asks required fields first; a workspace has its page and
  its search; identifiers are out of the common pages.
- No capability is removed.
- The user has judged the canvas on their own workbooks.
