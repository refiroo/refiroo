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
| [PL0](PLAIN_PATH_PLAN.md#pl0-the-principles-as-reference-rules) | — | The principles as reference rules in UI acceptance. **Delivered 2026-11-12** (UI acceptance §1, row "Plain path") |
| [PL1](PLAIN_PATH_PLAN.md#pl1-change-sets-in-two-clicks) | PL0 | Start with a name; Publish checks, then confirms in plain words. **Delivered 2026-11-12** (frontend; its browser runner not written) |
| [PL2](PLAIN_PATH_PLAN.md#pl2-plain-add-and-edit) | PL0 | Parent as a sentence, required first, inline errors. **Delivered 2026-11-12** (frontend; its browser runner not written) |
| [PL3](PLAIN_PATH_PLAN.md#pl3-the-workspace-page) | PL0, WM1 | **Delivered 2026-11-12 by SH1 and UX1**, except what needs PL4 (Import a workbook…, Home's administrator primary). A page for each workspace, with search across it. **Edit model:** WM1 (0.16) delivers it in the workspace ⋯ menu and as a button on the workspace's page in Settings › Workspaces; both stay, and this page adds a button running the same action (the user, 2026-10-31) |
| [PL3b](#pl3b-the-workbook-canvas) | PL0 | The workbook beside the live result; every drop applies at once **Delivered 2026-11-12** (guide screenshots open) |
| [PL4](PLAIN_PATH_PLAN.md#pl4-new-workspace-from-a-workbook) | PL3, PL3b | The file and a name, what refiroo found, Create workspace. **Delivered 2026-11-12** without PL3b: Adjust opens today's model editor on the draft (PP-D44 to PP-D47); not tried in a browser |
| [PL5](PLAIN_PATH_PLAN.md#pl5-plain-words-and-identifiers) | PL0 | One list of replacements; Settings index; Back to the workspace. **Delivered 2026-11-12** (the list is in PLAIN_PATH_PLAN.md) |
| [PL6](PLAIN_PATH_PLAN.md#pl6-collection-import-and-export-and-your-changes) | PL0 | Import file-first; Export for people; draft steps grouped. **Delivered 2026-11-12** (its import runner not run) |
| [NG1](#ng1-views-in-navigation-groups) | — | A navigation group places a view of its own, not only a whole collection. Relation matrices are built (0.13 NG); left: the other view kinds, Move to group… on their rows and the canvas's group drop |
| [SM1](#sm1-account-security-messages) | — | Mail when a person's sign-in changes: password, second factor, passkey |
| [EM1](#em1-the-e-mail-is-the-sign-in-name) | — | The e-mail address is required, unique and the name a person signs in with; the separate username is gone |
| [EX1](#ex1-export-says-what-it-exports) | — | Export follows what is exported: a view gives a workbook shaped as the view, a type, an application or a workspace a sheet per type; every file says what it holds and imports back. Takes over PL6's "Export for people" |
| [MC1](#mc1-reuse-or-create-in-any-matrix-cell) | — | A filled matrix cell offers Link existing and Create wherever the model allows more than one record per cell; a user guide page with examples |
| [CA1](#ca1-the-parent-carries-fields-and-related-blocks) | — | A consumer API's parent serves any field and related blocks of its own, a related block may be served only on request (`include`), and an On related filter may narrow a parent block |
| [RF1](#rf1-review-findings) | — | Three engine defects from the project review of 2026-11-11: approve and publish lock in one order, a re-read never cancels a confirmed import, a failed file cleanup no longer keeps background work off |
| [SA1](#sa1-sign-in-managed-by-an-administrator) | EM1 | A person whose sign-in an administrator manages cannot change their own password, second factor or passkeys, and sees and ends only their own session |
| [RF2](#rf2-review-findings-engine) | RF1 | The engine findings of the review that need no new decision: CSV exports a spreadsheet cannot run, set-based placing of matrix cells, the provider first sign-in race, reset links |
| [RF3](#rf3-review-findings-frontend) | RF1 | The frontend findings: the reset token leaves the address bar, one search box, no lost events on reconnect, pages loaded when opened |
| [RF4](#rf4-review-findings-build-and-deployment) | RF1 | The build and deployment findings: pinned versions, a content security policy, CI permissions, safe forwarding defaults |
| [RF5](#rf5-assistant-sessions-in-a-container) | RF1 | An assistant session in a container reads only its own task, and holds no more of the provider's credentials than it needs (plan first) |
| [RF6](#rf6-webhook-addresses-on-private-ranges) | RF1 | A webhook address on a loopback or private range is refused unless an instance setting allows it |
| [RF7](#rf7-clean-test-output) | — | A passing test run has no errors or warnings in its output, frontend and backend: each is fixed at its cause, and from now on fails the run |
| [SH1](#sh1-one-frame-one-location-line) | — | The frame says where you are once: a page for each workspace with a search across it, a one-row context band, one line above a record, Settings by task with Back to the workspace, tables whose names are never cut. Takes over PL3 (except what needs PL4), the band of PL1, the record header of PL2 and the Settings part of PL5 **Delivered 2026-11-12** |
| [UX1](#ux1-themes-with-their-frames-and-one-way-to-edit) | SH1 | Four themes, each light and dark, that carry look, frame and density (Current, Hearth, Studio, Instrument); every component drawn from the theme base; one way to edit, pick, confirm and open a record in all of them; the search on ⌘K; Home as the hub **Delivered 2026-11-12** |
| [UX2](#ux2-one-field-saves-when-it-is-left) | UX1 | One field edited in place has no form: the value becomes its input and leaving it saves, told with the remove icon's toast and Undo (PP-D68) **Delivered 2026-11-12** |
| [MT1](#mt1-the-e-mail-template) | — | One e-mail template for the instance, Markdown with a logo, edited by the Operator role; every mail the engine sends is wrapped in it. **Delivered 2026-11-12** |
| [ST1](#st1-settings-as-one-family) | UX1 | Every Settings page drawn from one set of parts: one header, groups with their panels of rows, one list, one opened item, one log. **Delivered 2026-11-12** (guide screenshots not retaken) |
| [CE1](#ce1-the-canvas-edits-the-whole-model) | PL3b, UX2 | The canvas shows the whole model and does what the model editor does, on the same draft. **Delivered 2026-11-12** (approved the same day; guide screenshots open) |
| [R](#r-build-acceptance-and-release) | all | Full review since 0.16, the gates, the release |

**Order.** SH1 was added by the user on 2026-11-12 and is delivered next, at their request; PL1, PL2, PL3 and PL5
then hold only what SH1 leaves them. PL0, PL1, PL2, PL3, NG1, PL3b, PL4, PL5, PL6, SM1, R. EM1 was added by the user on 2026-11-11 and
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
| PP-D33 | **The context band no longer repeats the workspace and the application on desktop** (SH1). It keeps the context pill, its one sentence and the Live · Change sets · Publications switch. Why: the sidebar and the top bar already say both, and the band was a second and third statement of the same place. Cost: the band of [ADR-039](DECISIONS.md) and Track U's U2 changes; the phone band keeps both, since there it is the only place that shows them | **Approved by the user 2026-11-12** |
| PP-D34 | **A record's ID and version sit under Details, and Copy ID is also in the record's ⋯ menu** (SH1, as PL2 scoped it). Replaces the ID with Copy under the title, added at the user's request on 2026-10-07. Why: identifiers are out of the common pages (principle 6). Cost: one more click to copy an ID | **Approved by the user 2026-11-12** |
| PP-D35 | **Browse records is folded by default,** remembered per browser once opened, and its own search box is gone: the top bar search finds a record across the workspace (SH1). [ADR-040](DECISIONS.md) kept the sidebar with Browse records in it; it stays, closed. Cost: whoever uses the tree opens it once | **Approved by the user 2026-11-12** |
| PP-D36 | **A change set opened from the change set list lands on its changes,** with "See the data with these changes" leading to the lists; a person's own open change set still opens on the data from Continue and from the band (SH1). Why: opening one silently switched the whole application into it. Cost: one more click to edit in another person's change set | **Approved by the user 2026-11-12** |
| PP-D37 | **A page is titled by the selected sidebar entry, and a view is a tab under it** (SH1). A view placed in a navigation group on its own (NG1) is its own sidebar entry and is titled by its own name. Settings opens on an index by task with About last, and an opened item's own name is the page title. Cost: two title rules, by what the sidebar entry is | **Approved by the user 2026-11-12** |
| PP-D38 | **The app has themes that carry look, frame and density together** (UX1): Current (today's, kept as the reference), Hearth, Studio and Instrument, each in light and dark, chosen on Settings › Appearance; Website purple stays. A theme is a token set, an arrangement of the frame's parts and a density. Why: the user wants good-looking options and keeps today's. Cost: every component reads tokens only, and each frame arrangement is checked at phone width | **Decided by the user 2026-11-12** |
| PP-D39 | **The frame is one component with named parts** (operator, areas, applications, lists, search, data context, account), and a theme places them: top bar and sidebar (Current, Hearth, Website purple), one sidebar and a raised page (Studio), an icon rail, a list panel and a status line (Instrument). Pages do not know their frame. This extends [ADR-040](DECISIONS.md)'s frame; the data context keeps its colours and meaning (ADR-039) and is shown once in each arrangement | **Decided by the user 2026-11-12** (the arrangements are the approved prototype's) |
| PP-D40 | **One way for the small interactions, in every theme** (UX1): one value is changed where it stands (Enter saves, Esc cancels); a yes or no is a switch that saves itself; several are picked in a list under the value; a form opens as a side sheet beside the page; at most one confirmation, only for what cannot be undone, naming what is lost; a saved change offers Undo; one word per action (Save, Add ‹thing›, Delete ‹thing›, Publish, Cancel). Why: the code inventory of 2026-11-12 found about 112 dialog and edit sites built in different ways, 61 of them a dialog for one or two controls | **Decided by the user 2026-11-12** |
| PP-D41 | **A row opens beside its list first** (a peek with the record's main facts, editable), with the full page one step further; on a phone the row opens the page. **One search on ⌘K** finds records across workspaces, lists and actions, and replaces the per-panel search boxes of a record page. **Home is the hub:** the search, what needs the person, and workspace cards that say what is in them | **Decided by the user 2026-11-12** (as in the approved prototype) |
| PP-D42 | **One e-mail template per instance, in Markdown with a logo, edited by the Operator role** (MT1). It wraps the content of every mail when the mail is queued; without a saved template the engine's own layout is used, so nothing changes until an operator saves one. Why: the user asked for it. Cost: a second place that decides how a mail looks | **Decided by the user 2026-11-12** (the request); the details below are planning defaults |
| PP-D43 | **MT1's details:** the action is `mail-template.manage` in the Operations group (the Mail page's own action is the security administrator's, which Operator does not hold); placeholders are `{{content}}` (exactly once), `{{product_name}}`, `{{instance_url}}`, `{{recipient_name}}`, `{{logo}}`; the logo travels inline in the mail; Markdown is rendered by `markdown-it-py` with raw HTML and images off and links limited to http, https and mailto; template changes are not in the security audit | Planning default (the user was away; open to change) |
| PP-D44 | **One route makes a workspace from a workbook's draft** (PL4): `POST /api/v1/workspaces/from-workbook` installs the draft as a release, creates the workspace on it and queues the workbook as an import job into its live data, in one transaction up to the job; it answers 202 with the workspace, the release and the job. Its declared action is Workspace administration at the instance; the route also needs Install a model (or Model release) and Bulk and import held at the instance, since the new workspace has no grants yet (refusal `403 FORBIDDEN` naming the missing action). Why: the separate steps each need a group, and an integrator gets the whole step too | Planning default (the user was away; open to change) |
| PP-D45 | **A clash never refuses the step** (PL4): a release version another model holds becomes the next free version (written into the draft), and a profile key another model's profile holds becomes a free key; a draft's profile starts under a key no stored profile holds, so the clash does not arise for a new one. Why: the person cannot resolve either, and the plan said a clash never reaches them | Planning default |
| PP-D46 | **The sheet makes the draft itself, and Cancel removes it** (PL4): the file becomes an empty model named for the workspace with the workbook uploaded, read, its "new application" proposals applied and every row dry run; "What refiroo found" reads that dry run. Cancel deletes the draft; Adjust keeps it and opens today's editor on it (the canvas, PL3b, replaces that target when built). After Create the draft is the new workspace's own, so Edit model reopens it | Planning default |
| PP-D47 | **The load is the existing import job** (PL4): `independent` and records found updated, as the load into a change set; a refused row is reported and the rest load. The new workspace's page shows its progress and what did not load, with the rows on the job's page; nothing about it is kept beyond that page load. The entry is shown only to a person holding Workspace administration, Model authoring, Install a model or Model release and Bulk and import at the instance, with workspace, model and integration administration on (hidden, never disabled) | Planning default |
| PP-D48 | **The shape of the three readings** (PL3b). On a source: `unpivot: {columns, nameColumn, valueColumn}`, `fillDown: [columns]` and `headings: {column, into}`. They apply in the order headings, fillDown, unpivot and add their new columns (`nameColumn`, `valueColumn`, `into`) at the end of the table, where bindings name them like any header. An unpivoted cell that is empty makes no row; a row whose listed cells are all empty gives none; the rows keep their sheet row number. A heading is a row whose only filled cell is in `column`, so a data row holds a value in another column (the same rule as a heading in any grouped list). A name the table has is `COLUMN_CLASH`. Why: one place reads them, so the import, the dry run, the profile check and a saved profile cannot differ; the rows stream through the reader, Python holds no set, and every row is read. Cost: a data row that holds only its name and sits among headings reads as a heading | Planning default (decided at delivery) |
| PP-D49 | **Six operation kinds, not three with `null` to clear** (PL3b): `setUnpivot`, `clearUnpivot`, `setFillDown`, `clearFillDown`, `setHeadingRows`, `clearHeadingRows`. Why: a required parameter that may be `null` is refused as missing by the operation registry's own rule, and an omitted parameter clearing a reading by accident is worse than one more kind. A clear unmaps the bindings of the columns it removes (as other steps do), so its undo restores them | Planning default |
| PP-D50 | **A column a reading is lost from follows the profile as other columns do** (PL3b): when the next file lacks a column a reading names, the reading and the bindings of the columns it added leave the source that is read; a renamed column is followed under its new header. Why: the profile check already follows renames and missing columns for bindings; a reading that kept naming a gone column would fail the whole load | Planning default |
| PP-D51 | **Join candidates compare trimmed text, case as written, over every row** (PL3b, PP-D8): a candidate is a column holding at least one value of the dropped column (a named column is always answered); they are ordered by the dropped column's rows matched, then its distinct values matched, then column order; two at the top of both figures are a tie (`tie`, `tied`, `best: null`). The route sits with the draft's other whole-file reads (`inference/list`), is answered and stores nothing, and needs Model authoring at the instance. Why: the import matches names by their text; one ordering keeps the answer the same for the same file | Planning default |
| PP-D52 | **No new engine route for the rest of the gesture table** (PL3b, PP-D4, PP-D5): a sheet's table proposal is `inference/list`; a parent and child, a filter with its attribute and an unmapped column as a list each compose from existing operations in one request, tried through the API in J58.1. The filter's attribute is added with `features.filterable`, which the model needs before a view may filter by it. Why: a route that only repeats a request a client can send is an option no integrator's journey needs | Planning default |
| PP-D53 | **The canvas journey is J58** (PL3b). J51 was taken by "Reach the engine from an assistant" (0.16 AG1); the next free number is used | Planning default |
| PP-D54 | **Card positions are the draft's own, read and merged by key** (PL3b): `canvas_json` on the draft (migration `20261202_01`), `GET` and `PATCH /model-drafts/{id}/canvas`, at most 500 cards, keys of 1 to 200 characters, coordinates within plus or minus 1,000,000, `null` removes a card. They do not change the draft's version or `updatedAt`, are not in its history, an undo step or a release, and are served with the draft's permission (Model authoring). A merge, not a replacement: two editors moving different cards do not overwrite each other. Why: the user's rule (2026-10-31) that positions never change the model; a move that bumped the version would conflict with every operations request | Planning default |
| PP-D55 | **An assistant's design must carry the profile it was checked by** (PL3b): when the session's last check read the workbook through a profile and the draft stores none, or a different one, the task fails with a plain reason ("the assistant checked the workbook through a profile it sent with the check and stored none on the model draft…"), and the person is asked to give the assistant other words. Proven by a unit test on the finishing logic (`profile_not_stored`); no AI session was run. Why: accepting would otherwise offer a design whose check no stored profile reproduces, and the load would have no profile | Planning default |
| PP-D60 | **Every Settings page has one shape** (ST1): the header (group, title, one or two sentences, the page's one main action at the title's right), then groups; a group says what it is about on the left and holds its controls in panels of rows on the right; a group holding a table takes the full width with its heading above. It replaces the three layouts of today (the full-width ruled sections, Account's centred column of cards, Notification email's narrower centred column) and the bare forms. Why: the user asked for one style, more readable; help text gets one place and a line stays short at any width. Cost: every Settings page's markup moves onto the shared parts; at 2560px a settings page leaves the right half empty, as a form should | **Approved by the user 2026-11-12** |
| PP-D61 | **Every list in Settings is a full-width list, and a row opens the item as its own page** (ST1), as Workspaces and Model do since SH1: People, Groups, Clients, Sign-in, Import profiles and Webhooks give up the narrow list beside the item. Why: the 260px list cuts names and roles ("Data owner; Model administrator; and…"), the item is squeezed beside it, and Settings has two kinds of list today. Cost: going from one person to the next passes through the list; six pages and their browser runners change. The other choice is to keep the list beside the item on those six and only restyle it | **Approved by the user 2026-11-12** |
| PP-D62 | **A page holding settings and a log keeps the log on a tab** (ST1): Mail (Server, Messages), AI (Settings, Calls), Agent access (Access, Calls), Jobs (Jobs, Limits); the tab is in the address. Why: Mail is 4,500px tall today with the form above a table. Cost: the log is one click further | **Approved by the user 2026-11-12** |
| PP-D63 | **Where actions sit** (ST1): the page's one main action in the header; a group's own action (Add role) under the group's description; an opened item shows at most two actions and keeps the rest in a ⋯ menu with what cannot be undone last. Why: a person's page has five buttons in a row today, and main buttons sit in five different places. Cost: Deactivate and Sign out everywhere are one click further | **Approved by the user 2026-11-12** |
| PP-D64 | **One shape for a log** (ST1): the time first and in one wording ("today, 16:34", the full date and time on hover), numbers right-aligned with thousands separators, a duration in seconds and minutes, the state as chips above the table, "n of m" with Show more below. Why: today the logs word time in two ways, a cost wraps into two lines and Load more has four labels. Cost: the second of an event shows only on hover | **Approved by the user 2026-11-12** |
| PP-D65 | **The Settings index lists every page with one line saying what it is for** (ST1), in a panel per group. Why: today the index is link words only. Cost: 24 short texts to keep true | **Approved by the user 2026-11-12** |
| PP-D66 | **Deployment's settings read as rows:** the setting's name with what it controls under it, its value, and the default only where the value differs, with where the value came from (ST1). Why: five columns of capitals are the least readable page of Settings. Cost: the default is not shown for a setting left at its default | **Approved by the user 2026-11-12** |
| PP-D67 | **Colour is part of every Settings page** (ST1; the user, 2026-11-12: "this is not a boring application, it is a kind of joy to use it"). Each Settings group has a hue of its own (the app's hues, as the application tiles use), shown on the index, on a tile beside each page's title and on the tiles of its rows; a person has their hue on their initials and their page's header; a role keeps its coloured chip wherever it is named; activity stays a line by day with a coloured marker per kind, never a grey table; a log marks each kind and each total with its colour. Why: the first mock-up had flattened the colour today's pages carry. Cost: a hue per group and per kind to keep consistent in five themes, light and dark | **Approved by the user 2026-11-12** |
| PP-D68 | **One field edited in place saves when it is left** (UX2; the user, 2026-11-12: "an inline editor option starts which is an input field … clicks away and that focus change is the save, with the same notification like for the remove value icon. There is no 'No value' checkbox and open/cancel buttons"). This replaces PP-D40's "Enter saves, Esc cancels" for one value: the value becomes its control with no Cancel and Save buttons; leaving it saves, as Enter does (in a text of several lines Enter is a new line; Ctrl or Cmd with Enter saves), a choice or a tick saves as it is made, Escape puts the old value back; an input left as it was opened saves nothing and says nothing; a saved value is told "‹Field› saved" with Undo; an optional field left empty is the value removed, told "‹Field› removed" with Undo as the remove icon tells it; a required one left empty is refused under the field. A refusal keeps the field open with the reason under it and the input kept; leaving it again saves only once the input changed, and Cancel and Save again stand under the reason. Forms of several fields are unchanged. Cost: "Cleared" (a stored null) and "Empty text" can no longer be set from the interface, only through the API; a save started by leaving the field no longer holds the person on the page, so a refusal that arrives after they opened another page is told in a toast | **Decided by the user 2026-11-12** |
| PP-D69 | **A dialog opens in the middle of the window again** (the user, 2026-11-12: "all these editing dialogs are on top right corner instead of the center of the screen, for all themes, all pages. Can you please fix"). The side sheet of PP-D40 is withdrawn: every dialog drawn by `ui/Modal` (forms, the matrix cell's dialog, bulk changes, import, a new change set, a workspace from a workbook, Settings and model editor forms, confirmations) is centred across and down the window at every width above the phone's, in every theme and frame arrangement, with the widths it had before UX1 (580px, compact 520px, wide 860px, a width of its own where it names one) and never taller than the window. A long form scrolls inside the dialog and its buttons stay at the dialog's foot. The phone keeps its full-width dialog. What is not a dialog keeps its place: a record opened beside its list, a popover under its control, menus, toasts. The rest of PP-D40 stands. Why: a sheet as tall as its form put a short form in the window's top right corner, far from the cell or row that opened it. Cost: the dialog covers the middle of the page again, behind the dimmed, blurred backdrop it had before UX1; the guide's screenshots taken with a sheet are retaken | **Decided by the user 2026-11-12** |
| PP-D70 | **Several columns onto a field** (PL3b, PP-D6): `setUnpivot` plus the bindings of its two new columns in one request. The field decides what each becomes: on the name, the headers name the records; on an attribute, the cells fill it; on a parent or a relationship, the headers find the records there; what the field does not take becomes a new attribute (a card drop: both). A wide column the source read as something else is unmapped first. Why: every drop is one request and one undo step | Planning default |
| PP-D71 | **A join is the starting list's first source against the other list's name column** (PL3b, PP-D8): its name binding, else the column of its key. Columns the source already reads are not candidates, left-out ones are. One best column is bound (`missing: create` only by name) in the link's request; a tie is asked in a popover (the drop closed changes nothing); none, or a join that cannot be read, makes the link only and says so | Planning default |
| PP-D72 | **A column on Filters:** a new attribute is made `filterable` and mapped, and the engine's own placement on attaching adds it to the table view's filters (an `insertViewItem` refused as already listed); an attribute that exists is made filterable with `setAttributeTypeFeatures` and added with `insertViewItem`, the editor's own list operation, not `setViewProperty`. A draft the model cannot compile shows no filters and says so | Planning default (found in the browser run) |
| PP-D73 | **A column's suggested value type needs every filled cell** (PL3b): the profile counts cells readable as each type and every cell reads as text, so the canvas took text for any column; it now follows the editor's rule. A column of numbers with one word is text until the person makes it a number | Fix |
| PP-D74 | **Only Create workspace… is gated by permission** (PL3b): by the PL4 conditions (`startsFromWorkbook`), hidden otherwise; Load into an existing workspace… and Apply to this workspace… are the editor's own actions and follow its conditions. A draft with a workspace gets Apply as the main finish | Planning default |
| PP-D75 | **On a phone the board is one column** (PL3b): drags are off, stored places are ignored, Connect asks through a chooser and every menu does the drags' work | Planning default |
| PP-D76 | **Refused rows are corrected by value map only for "no record matches" with a column named** (PL3b); other reasons show the engine's words and the rows. The toolbar's Undo takes the last step, so a refusal for dependants arises only after another editor's step; it is asked as in the editor (one shared dialog) | Planning default |
| PP-D83 | **A column on the empty board is built from existing operations, not the inference** (PL3b, PP-D52): a new list named for the column, a relationship from the list that reads the sheet filled by the column (`missing: create`; a column already read as an attribute goes through `convertAttributeToListType`), and a source of its own that reads the column as the list's name with `key: name`, so a blank cell is skipped and Connect can find the column that names its parent. One request (`columnAsListOperations`). Tried against the inference's one-column list proposal on a plain repeated column: it adds a source to a list that exists already and makes no new list and no link. Why: the gesture is "its distinct values as a list, linked back" and the proposal is not that. Cost: the list's plural is the same word as its name; a column read as a name, parent or relationship is refused with a sentence | Planning default (decided at delivery) |
| PP-D84 | **Drops that would repeat something change nothing and say so** (PL3b): a column that already fills a field of the list dropped on its card, and a sheet a list already reads dropped on the board (every block read). A left-out column dropped back on its list takes the field it had. Two lists that read the same sheet join by the other list's own column when the join route names none (it leaves the dropped column out of its own table); a column that already links to the other list as a relationship becomes its parent link. Why: each of these made a second field or list beside the first, or left a hierarchy with nothing filling it | Fix |
| PP-D85 | **Create workspace… on the canvas lands on the workspace's own page**, as PL4's sheet does, because that page holds the load's progress and result; before it landed on the application's first view and the result was never shown. The toolbar hides what an empty board cannot finish: Create workspace…, Load into an existing workspace… (no list a sheet loads) and Tidy (fewer than two cards); Apply to this workspace… stays, since it applies model changes without a workbook | Fix |
| PP-D77 | **Two structured views of one draft** (CE1): `MODEL_AUTHORING.md` principle 7 no longer rules out canvas-first authoring. Every change stays an operation, card positions never enter the model or a release, record layouts are still never positioned by pixels. | Approved by the user, 2026-11-12 |
| PP-D78 | **Consumer APIs on the canvas** (CE1): the editor's Consumer APIs tab is shown on the canvas as it is. Security stays in Settings. | Approved by the user, 2026-11-12 |
| PP-D79 | **Record and view layout stay in the editor's preview** (CE1), opened inside the canvas page; one implementation, lifted out of the editor's own state. | Approved by the user, 2026-11-12 |
| PP-D80 | **A draft opens in the view the person used last** (CE1); from a workbook flow it opens on the canvas. | Approved by the user, 2026-11-12 |
| PP-D81 | **Folded cards and the chosen scope are kept on the draft** (CE1), with the card positions (`canvas` gains `folded` and `scope`); zoom stays in the browser. | Approved by the user, 2026-11-12 |
| PP-D82 | **What a load does with records no row names gets a place in the interface** (CE1): `setMissing` on a source's panel in both views, with a confirmation for Delete. | Approved by the user, 2026-11-12 |
| PP-D83 | **The canvas document's new parts** (CE1, PP-D81): `folded` is sent as a map merged by key (`{"<cardKey>": true \| false \| null}`, as positions are, so two editors folding different cards do not overwrite each other) and answered as the sorted list of folded keys; `scope` (`model`, `changed`, `workbook`; `null` the default) is replaced; a part left out stays. Up to 500 folded cards as 500 placed. Stored as one document `{"positions", "folded", "scope"}` in `canvas_json` with no migration: the positions-only document written before is read as such | Planning default |
| PP-D84 | **The last view is remembered per draft** (CE1, PP-D80): `rdm:model-draft:view:v1` holds a map of draft to `editor` or `canvas` in this browser (the sixty used last), written when a person is on a view, however they got there. A draft opens on the canvas from a workbook flow, else on its last view, else on the editor. The switch replaces the editor's Open as canvas link and is shown for every draft | Planning default |
| PP-D85 | **One entry to what a target can do** (CE1, PP-D3): `operationsFor(target, outline)` stays the only function that decides which operations an element has, and `operationTargetKinds()` lists every operation of the table with its target kind, for the canvas's parity test. The editor's steps, refusals, operation dialogs, notices, source dialogs and the draft's action set are shared hooks (`useDraftEditing`, `useSourceDialogs`, `useDraftActions`), not copies | Planning default |
| PP-D86 | **`setMissing` is on the list's panel, as a choice of two** (CE1, PP-D82): `MissingRecords` shows Report them or Delete them where the list's key is shown; it is hidden for a source with no key or one that loads no records of its own, where the engine refuses Delete; Delete asks once in the plain confirmation, saying a load deletes in its change set every record of the type no row names. The engine needed no change | Planning default |

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
| A sheet onto empty space | A new list, its columns as fields | `addObjectType`, `addAttributeType`, `attachAttribute`, `addSource`, `mapColumn` in one request; `inference/list` answers with list rules | Nothing: `POST …/inference/list` answers a sheet's rectangle at once |
| A column onto a list or field | A new or mapped field | `addAttributeType`, `attachAttribute`, `mapColumn` (the frontend helper `mapOperations` composes them) | The drop without the dialog (a client change, no engine work) |
| A column onto empty space | Its distinct values as a list, linked back | `convertAttributeToListType`, for a mapped attribute | Nothing: for an unmapped column it follows `addAttributeType`, `attachAttribute` and `mapColumn` in the same request (tried in J58.1) |
| A card's Connect handle or a sheet onto a field | A relationship, drawn as a dashed line | `allowRelation`, a `relation` binding by `mapColumn` | `POST …/join-candidates`, whole set (PP-D8, delivered) |
| A card's Connect handle onto another card | Parent and child, drawn as a solid line | `setContainment`; a `parent` binding or fixed `Source.parent` | Nothing: `addObjectType`, `setContainment` and `mapColumn` with a `parent` binding are one request (J58.1); the parent column is found by the join route |
| Several columns onto one field | Translations, flags or a wide sheet as rows | Translations by `relatedRecord`; flags by `relationFlags` | `setUnpivot` and `clearUnpivot` (PP-D6, delivered) |
| A column onto a list's filter box | A filter on the list | `setViewProperty` with `filterFields`, table views, for an attribute already there | Nothing: `addAttributeType` (with `features.filterable`), `attachAttribute`, `mapColumn` and `setViewProperty` are one request (J58.1) |
| A list onto a group or New group | A navigation group | `addNavigationGroup`, `placeCollection`, `setNavigationGroup` | Nothing |
| A field back onto the workbook | The column left out | The inverse operations, `ignoreColumn` and `ignoreSheet` | Nothing |
| An attribute onto another object type's card | The attribute moves there | `moveAttribute` (the editor's Move to…) | Nothing |
| An attribute up or down within its card | Its position | `setAttributeBinding` with `position` (the editor's Move up / Move down) | Nothing |

**Actions on the sheet preview:** click the row that holds the headers (`headerRow`, with rebinding through
`setSource`, exists); mark a column as repeated by blanks (`setFillDown`), or a row as a heading (`setHeadingRows`, PP-D7). Side-by-side tables are
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

**Engine and API, delivered 2026-11-12** (the canvas UI is built separately and calls these): items 1, 2, 4 and 5 above
(the readings in the profile, the reader, the dry run and the import; the six operation kinds; the whole-set join route;
card positions on the draft; the check that an assistant's design carries its profile). Item 3 and the other "To add"
entries needed nothing new (PP-D52): the table above says which composes today, and J58.1 sends each as one request.
`docs/API.md`, the reference text, the contract test, `docs/testing/API_JOURNEYS.md`, `USER_JOURNEYS.md` (J58),
`CURRENT_FUNCTIONALITY.md` and `CHANGELOG.md` are updated. **Measured once** (no AI): a drop of seven operations
(`addObjectType` twice, `setContainment`, `addSource`, `mapColumn` twice) on a draft with 200 rows 0.06 and 0.12 s, with
2,000 rows 0.27 and 0.06 s (two configurations); the dry run's job over every row 0.23 and 0.39 s at 200 records, 1.55 and
1.61 s at 2,000; a join comparison 0.02 to 0.06 s; one reading operation 0.04 to 0.08 s. **Before and after:** a read-only
inventory of the development database (21 stored import profiles and 19 drafts' profiles, 977 sources) found none using a
reading, the same named columns for every source, and the table returned unchanged for every source, so no stored profile
reads a file differently; no workbook of the user's was loaded again. **Not done:** the canvas UI and its guide pages (the
facts a guide page needs are in the engine's report); J50's stand-in session now stores its profile on the draft; those
tests also fail at teardown on an unclosed-file warning that is independent of this change.

**Canvas, delivered 2026-11-12:** the page, board, workbook pane and popovers (`frontend/src/features/workbook-canvas/`): joins over
every row with a tie asked, several columns read as rows, the sheet preview with a pressable header row, fill down and heading
rows from the column menu, a column onto a list's Filters, the reasons for refused rows with a value-map correction, Proposed on
cards, fields and columns, one chooser for many lists, keyboard paths (arrow keys move a card 16px, Escape cancels a carry,
Connect by Enter, columns by Shift and the arrows), the phone's single column, Create workspace…, Apply, Load into an existing
workspace…, Open as canvas in the editor and PL4's Adjust. The editor shares `useDraftSteps`, `DependantsDialog`,
`useEditorWorkspace` and `stillProposed`. Decisions PP-D70 to PP-D76. **Tried:** `frontend/e2e/pl3b-workbook-canvas.mjs` (real
workbook, drops to the dry run's count, Connect with a tied join, unpivot, undo, a refused row, an invalid draft, keyboard,
Create workspace sheet, 390px, axe, no 5xx) passes; component and model tests pass. **Not done or not seen:** the value map
correction and Apply/Load dialogs are covered by component tests only, not in the browser; no real-file smoke on the user's
samples; no before/after inventory (the canvas changes no reader); the guide how-to and screenshots (Codex).

**Door check (ADR-032):** the new profile readings change only how rows are read. Identity, attribute storage,
history, bulk APIs, `match` and mapping coverage are not affected.

**Measure once:** a drop and its dry run at 200 and 2,000 records, reported with AI, job and overhead shown
apart where relevant. Known figures: an editor step at 2,000 records about 1.4 s; dry runs of 19,453 items about
7 s and 40,107 items 22.2 s; a large workspace's step about 3.5 minutes (`POSTGRESQL_BUDGETS.md`). The last is
why PP-D9 stands. Volume runs only if these basics give a reason.

**Tests:** journeys through the API on two model configurations (J58; J51 was taken, PP-D53): a flat sheet shaped into a hierarchy with
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

### Contract for the canvas (engine and API)

_Written 2026-11-12 before the build; kept current by the delivery. All routes need `model.author` at the instance, like the
other draft routes. Operations go through `POST /api/v1/model-drafts/{id}/operations` as today._

**Six operation kinds** (profile readings, PP-D6 and PP-D7; they change the draft's profile only, are undoable and named
`source:<id>`). Each takes `source` (the source's id). A reading applies to the rows of the source's table in this order:
`headings`, `fillDown`, `unpivot`. A row of a wide table whose listed cells are all empty gives no row.

| Kind | Parameters | Effect |
| --- | --- | --- |
| `setUnpivot` | `source`, `columns` (header names, 2 or more), `nameColumn`, `valueColumn` | Each row becomes one row per listed column whose cell is filled, with the column's header in `nameColumn` and the cell in `valueColumn`. Both are new columns a binding can name (`mapColumn` with `column: "<nameColumn>"`). Replaces an earlier unpivot. |
| `clearUnpivot` | `source` | Takes it away; bindings of its two columns become unmapped entries. |
| `setFillDown` | `source`, `columns` (header names) | An empty cell in a listed column takes the value of the nearest filled cell above it in that column. |
| `clearFillDown` | `source` | Takes it away. |
| `setHeadingRows` | `source`, `column` (header name), `into` | A row whose only filled cell is in `column` is a heading, not a record: its text is the value of the new column `into` on every row beneath it until the next heading. Bind `into` as a parent (`mapColumn`, `parent`, `missing: create`). |
| `clearHeadingRows` | `source` | Takes it away; the binding of `into` becomes an unmapped entry. |

Refusals by code, as for every operation: `unknownElement` (the source, or a column the file lacks), `invalidValue` (fewer
than two unpivot columns, a column listed twice, `nameColumn` equal to `valueColumn`, a column in both `unpivot` and `fillDown`),
`keyTaken` (a new column name the table already has), `missingParameter`. A `clear…` of a reading the source lacks is `unknownElement`. A filter on a column needs its attribute added with `features.filterable`; a heading is a row whose only filled cell is in `column`, so a data row holds a value elsewhere. In the saved profile the three are
`unpivot: {columns, nameColumn, valueColumn}`, `fillDown: [..]` and `headings: {column, into}` on the source, read by
`POST /imports`, the dry run and the profile check alike.

**Join candidates** (PP-D8): `POST /api/v1/model-drafts/{draftId}/join-candidates`, answered at once, nothing stored.
Request: `column` (the dropped column: `{sheet, column | letter, headerRow?, block?}`) and `against` (what it is compared
with: `{sheet, headerRow?, block?, column? | letter?}`; without a column, every column of that table). Header row and block
default as for a source. Response 200:
`{column: {sheet, letter, header, rows, distinct}, candidates: [{sheet, letter, header, rows, distinct, matchedValues, matchedRows, share, unique}], best: letter | null, tie: bool, tied: [letter]}`.
`matchedRows` counts the dropped column's filled rows whose trimmed text is found in the candidate; `share` is `matchedRows`
over `column.rows`; `unique` says the candidate's filled cells are all different (a list to link to). Candidates with no
match are left out unless named in `against`; they are ordered by `matchedRows`, then `matchedValues`, then column order. `tie`
is true when two or more candidates share the top `matchedRows` and `matchedValues`; `tied` lists them and `best` is `null`:
the client asks. Errors: `404 SOURCE_FILE_NOT_FOUND`, `409 SOURCE_FILE_PROFILE_NOT_READY`, `404 SOURCE_SHEET_NOT_FOUND`,
`422 COLUMN_NOT_FOUND` (a header or letter the table lacks), `422 INVALID_RANGE`, `403 FORBIDDEN`.

**Canvas positions** (PP-D54): `GET /api/v1/model-drafts/{draftId}/canvas` answers `{positions: {"<cardKey>": {x, y}}}`; `PATCH`
with `{positions: {"<cardKey>": {x, y} | null}}` merges them (`null` removes a card) and answers the same. A key is 1 to 200
characters, at most 500 cards (`422 INVALID_CANVAS`, nothing changes), `x` and `y` finite numbers within plus or minus 1,000,000 (a malformed body is `422 REQUEST_VALIDATION_ERROR`). They
are the draft's own, not part of its version, its history, an undo step or a release; a write does not change `expectedVersion`.

**Gestures that need nothing new** (PP-D53): every other row of the table above is one operations request today (see the
state note below).

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
- Website (its own repository): the early-access form and the sign-up lookups have no rate limit. (The demo
  account and the demo's deploy by username were covered by SA1 and the website's demo tooling, 2026-11-11.)

_The user asked on 2026-11-11 to fix these._ They are packages RF2 to RF5 below; webhook addresses on loopback
and private ranges are RF6 (the user's decision of 2026-11-11, which replaces C-D101's rule); the website items are delivered in the
website's repository.

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

## RF2: Review findings, engine

_Added by the user on 2026-11-11_ ("fix them"), from the list under RF1. No new product decision is needed for
these; each choice made in delivery is recorded here.

- **A CSV export holds no value a spreadsheet runs as a formula.** A text value starting with `=`, `+`, `-`,
  `@`, a tab or a carriage return is written so a spreadsheet shows it as text; numbers are untouched; a file
  the engine reads back gives the original value.
- **Placing new matrix cells in an import is set work.** `imports/places.py` reads whole record sets once per
  column; it reads them once for the import, in PostgreSQL.
- **Two first sign-ins through a provider at once** create one person and both succeed; an address the
  provider has not verified is not matched to an existing person.
- **An anonymous forgotten-password request does not cancel a reset link an administrator made.**
- **Tests and docs:** one journey case per behaviour through the API; CHANGELOG; API.md where a contract is named.
- **Delivered 2026-11-11.** `engine/jobs/exports.py` (`_csv_text`, `_csv_cell`: the quote is added by PostgreSQL in the
  `COPY`); `engine/imports/places.py` (`PlaceReads`, used by `imports/binding.py`); `engine/identity/provider_sign_in.py`
  (`_identity`, the creation in a savepoint); `engine/identity/resets.py`, `engine/mail/links.py` and migration
  `20261130_01` (`password_reset_links.requested`). Four journey cases: `test_j27_export` (formula text),
  `test_j39_provider_sign_in` (two first sign-ins at once; fails without the fix), `test_j46_reset_by_mail` (an ask
  leaves an administrator's link valid). Checks run: `test_j27_export_views`, `test_j27_export`,
  `test_j46_reset_by_mail`, `test_j39_provider_sign_in` (94 passed, then the formula case
  corrected, 2 passed), then `test_foreign_keys`, `test_startup`, `test_schema_drift`, `test_j46_mail`,
  `test_j39_managed_sign_in`, `test_j39_sign_in` (78 and 48 passed); Ruff on the changed files. `test_startup` expects
  the new head. The contract lock is not affected (no route, schema or description changed).
  **Decisions made in delivery:**
  - The quote is added to text only: a name, a path, the `~` names and attributes of type `text` or `longText`.
    Integers, decimals, booleans, dates, date-times and JSON are never prefixed, so a negative number stays a number.
    No journey case holds a negative number (the generated models allow none); the rule is in the SQL.
  - **The export escapes unambiguously and the import reverses it** (the coordinator, 2026-11-11, replacing an earlier
    "not stripped"). The export prefixes one quote to a text matching `^'*[=+\-@\t\r]`; the CSV table-layout import
    (`imports/binding._unquoted`, CSV only, the name and `text`/`longText` columns) strips exactly one quote from a
    value matching `^'+[=+\-@\t\r]`. Every engine-written file round-trips exactly, a real `'=x` included; a
    hand-made `=x` stays `=x` and a hand-made `'=x` becomes `=x`. XLSX writes every text as a text cell and is not
    affected.
  - **After review:** `use_link` deletes the person's other links on success; turning `signInManaged` on deletes
    the `requested` links and `use_link`/`link_user` refuse a requested link of a managed person (`410`, no new
    code); an administrator's link still works. Journey cases in `test_j46_reset_by_mail` and
    `test_j39_managed_sign_in`.
  - Placing reads once per import: the records of a set of types, the cell counts of every container and the
    containers in use are each one statement kept in `PlaceReads`; the walk from a container up to its column
    record stays in Python over the records once read.
  - Provider first sign-in: a savepoint around the creation and a re-read by subject, not an advisory lock, so the
    same person and two persons with one address are both handled (the second then gets `email_taken`).
  - **`email_verified` is not added.** D363 and D377 already settle matching: a person is found by provider and
    `sub`, never by e-mail, and an address another person holds is refused, not matched. Not changed. Left as it is:
    the created person and each later sign-in take the token's `email` without looking at `email_verified`.
  - A link made by a forgotten-password ask is marked (`requested`) and an ask replaces only such links; an
    administrator's link, with or without `send`, replaces every earlier one as before, and a person may then hold
    an administrator's link and one of their own. The route text of `POST /users/{id}/password-reset` and the
    management reference still say a newer link replaces an older one for an administrator's, which stays true.

## RF3: Review findings, frontend

_Added by the user on 2026-11-11._

- **The reset token leaves the address bar** once the page has read it, and is not kept in history.
- **One search box:** the copies beside `ui/SearchField` use it; behaviour and look stay as they are.
- **The event stream loses no event during a reconnect:** it resumes from the last event it saw.
- **Pages load when opened:** routes are split so the first load does not carry every page.
- **Checks:** Vitest for the changed components; the browser runners of the changed pages; the production build.
- **Delivered 2026-11-11.** Reset token: `ResetPasswordScreen.tsx` (`takeResetToken`, `forgetResetToken`; `main.tsx`
  passes the token) replaces the address and keeps the token in the history entry's state; the engine's
  `GET /oauth/password` (`routers/oauth.py`, `RESET_COOKIE`) answers a valid token with `303` and a `Lax` cookie.
  Decisions: a reload shows the page while the state or cookie lasts (cookie 60 minutes), else the link-gone or ask
  page; `Lax` because a mailed link is a cross-site navigation. Search: ten copies use `ui/SearchField` (new props
  `type`, `autoFocus`, `disabled`); left as they are, with their own classes and look: `RecordChecklist`,
  `FieldMenu`, the matrix cell filter. Stream: `api/eventStream.ts` resumes with `Last-Event-ID` if a stream sends
  `id:` (the engine's send none and offer no cursor), dispatches `reconnected`, and `useInbox` reads again on it;
  the job stream resends the whole job on connecting. Splitting: `App.tsx` lazy routes with a `Skeleton` fallback,
  `main.tsx` lazy `App`; entry 2,108.8 kB (600.7 kB gzip) before, 208.7 kB (65.7 kB gzip) after, with the
  application chunk 677 kB and Settings 898 kB loaded when needed. Checks: `npm run build`; Vitest over sign-in,
  event stream, inbox, `ui`, security, objects and app (84 files, 642 tests); `tests/journeys/test_j39_sign_in.py`
  and `test_j46_mail.py` (54 passed); `test:browser:reset` (24 checks, gained the address and reload check),
  `test:browser:sign-in` (36 checks), `test:browser:lb`. `docs/API.md` still describes `GET /oauth/password?token=`
  as the page itself and needs the redirect named.

## RF4: Review findings, build and deployment

_Added by the user on 2026-11-11._

- **Pinned versions:** Claude Code is installed at a named version; base images are pinned by digest; the
  backend image installs from a lock file.
- **A content security policy** beyond `frame-ancestors`, checked in the browser on the app, the sign-in
  pages, the guide and the API reference.
- **`ci.yml` has a `permissions` block** granting what its jobs need and no more.
- **`AI_AGENT_SANDBOX=container`** is set where the image runs the assistant; forwarded headers are trusted
  from the proxy only, not from every address.
- **Docs:** OPERATIONS and the deployment notes; CHANGELOG.

- **Delivered 2026-11-11.** Done: Claude Code pinned
  (`ARG CLAUDE_CODE_VERSION=2.1.295`, the version installed on the development machine; the newest was 2.1.322);
  every base image pinned by digest (Dockerfiles, `compose.yml`, `compose.acme.yml`, CI's postgres service);
  `backend/constraints.txt` made with `uv pip compile --universal` (runtime and dev extra), used by the image and by
  CI (`.dockerignore` lets it into the build); `permissions: contents: read` in `ci.yml` (`images.yml` and
  `images-cleanup.yml` already had theirs); `AI_AGENT_SANDBOX=container` in the image `ENV` and in `compose.yml`;
  `FORWARDED_ALLOW_IPS` is the private ranges (overridable from `.env`), not `*`. The application's policy is
  `frontend/nginx/snippets/csp-app.inc.template`, sent on the application's own locations only; the engine's
  locations keep `frame-ancestors 'none'` and the engine's own policies (sign-in pages, guide, API reference)
  apply unchanged. Checks run: `docker build -f backend/Dockerfile` succeeded, `claude --version` in the image
  prints 2.1.295, `AI_AGENT_SANDBOX` is `container` in it, `pip check` is clean; `docker compose config` parses
  (also with `compose.acme.yml`). `npm run test:deployment` (it builds both images, serves the policy from nginx and, as extended, opens the
  application signed out and in, the engine's sign-in page, the guide with its search and the API reference,
  light and dark, failing on any console policy violation) passed with 12 checks on its third run: the first
  showed a font embedded as inline data refused, the second the component library's style element refused; each
  was followed by one change to the policy. The backend header tests were not run, as no backend code changed. Decisions made in
  delivery: (1) the theme script moved out of `index.html` into `public/theme-init.js`, so scripts need no
  `'unsafe-inline'`; (2) styles are `style-src 'self' 'unsafe-inline'` and fonts `font-src 'self' data:`: the deployment
  runner showed the component library adds a style element when the signed-in application starts, and the
  build embeds a font as inline data; scripts stay without `'unsafe-inline'`; (3) the policy
  is a file, not a setting (no existing settings pattern covers web's nginx); (4) the engine's pages keep their
  own policies rather than one policy in `web`, since a second, stricter one in `web` would apply on top;
  (5) the compose default for `FORWARDED_ALLOW_IPS` is the three private ranges, as `compose.acme.yml` already
  uses for `web`; (6) constraints cover the dev extra too, so CI and the image share one file.

## RF5: Assistant sessions in a container

_Added by the user on 2026-11-11._ Plan shown and approved by the user the same day, without a provider relay.

- **Outcome:** a session started for one task cannot read another task's folder or transcript, whoever asks
  it to; a session cannot read another running session's environment; the session's environment holds no
  provider credential beyond what Claude Code needs to run.
- **Revised 2026-11-11 after the independent review.** The first design made a task's random folder name the
  barrier between tasks. The review showed that does not hold: the engine followed links a session planted
  and could be made to open the tasks' folder to every session user; one session user served every task of an
  engine process, so a process or a start-up file left by one task ran beside the next; and the names show in
  process arguments once Claude Code runs tools. Permissions are the barrier now; the mechanism below
  replaces the first one and serves the same Outcome.
- **A gate per task:** each task has a folder only the engine can enter outside a turn. For a turn it is
  opened to the one session user that runs it, through that user's own group, and closed when the turn ends
  and at every engine start. Another session user cannot enter it, whatever names it knows. The folder keeps
  a random name under a folder session users cannot list.
- **What the engine creates, the session cannot replace:** the task's working folder, its Claude Code folder
  and the engine's log are made once, at the task's creation, inside the gate, where a session has no write
  right. Afterwards the engine does not change modes or write there by following a path a session controls,
  and what it reads from the session's folder is opened as a plain file, never through a link.
- **A reset around every turn:** before and after a turn the engine runs one fixed command as the session
  user (never as root): it ends every process of that user, empties that user's home, and makes what the
  session wrote readable for the next turn, which another session user may run. The sudo rule names the
  Claude Code binary and this command only.
- **A pool of session users** (build argument, default 8), each with a group of its own; two sessions running
  at once are different users.
- **Nothing secret on the command line** the engine builds: the prompt goes in on standard input.
- **A named list of passed variables** in place of the `ANTHROPIC_*`, `CLAUDE_*`, `AWS_*` and `NODE_*`
  patterns, in the engine and in the sudo rule: the provider's key or subscription token, its base address
  and model settings, the Bedrock names only when Bedrock is on.
- **Upgrade:** existing tasks' folders are moved into the new layout at the first start; the new name is
  stored before the folder is moved, so a clean-up running beside it cannot remove it.
- **Not covered (known limits, in OPERATIONS):** the provider's key or token still reaches the session, since
  Claude Code calls the provider itself; nothing limits where a session connects. A relay in the engine that
  keeps the key from the session was offered and left out by the user's choice of 2026-11-11.
- **Checks:** unit tests for the command, the environment and the folders; one try in the built image where a
  session user cannot list the tasks' folder, cannot read another task's folder or transcript, and cannot
  read another session user's process environment; one real assistant turn in the container, with its tokens
  and cost reported, to show a session still works and resumes. OPERATIONS, CHANGELOG.
- **Delivered 2026-11-11.** **The first design was replaced after the independent review**, which showed it did not
  hold (the engine followed links a session planted, one session user served every task of a process, folder names
  showed in process arguments, a resume under another user could not read a 0600 transcript, a sweep could remove a
  folder mid-move, an orphan group outlived an engine crash, and the engine reopened the log by path); the first
  design's code was rewritten, and its container try and its first real turn were discarded with it. Code:
  `engine/tasks/agent.py` (gate, reset, pool, safe file access, folders, sweep, `_Progress`), `design_job.py`
  (`run_turns` gives the folder its name first), `backend/refiroo-session-reset` (new), `backend/Dockerfile`,
  `.dockerignore`, `compose.yml`, OPERATIONS, CHANGELOG. Checks: `tests/unit/engine/tasks/test_agent.py`, 35 tests
  (planted links at `work/tmp`, `claude/sessions`, `workbook.xlsx` and `proposal.json` not followed; the gate opened
  for the turn's group and closed; idle gates closed unless a turn holds the user; the reset before and after a turn
  and a failing one failing the turn; the name committed before the move; the sweep; `_Progress` through its
  descriptor; the sudoers names and its two commands), run with `--noconftest` as the shared test server was busy;
  `ruff` on the changed files. **Container try** in the built image (own tag), as two pool users: while `assistant-1`
  ran a turn, `assistant-2` could neither list nor traverse the task's folder by its full path (`Permission denied`);
  after the turn the gate was 0700 and `assistant-1` could not enter either; a process left behind with `setsid`, a
  `.bashrc` in the user's home and a file in `/tmp` were gone after the turn; a `work/tmp` link to `../..` planted
  during a turn was replaced by a folder at the next turn and `data/assistant` stayed 2710; the second turn under
  `assistant-2` read and appended the transcript `assistant-1` wrote (mode 0660 after the reset); no process argument
  held the folder's path, the prompt or a token. **Real turn and resume** (the reference instance's subscription token,
  passed through the environment, with the user's approval): a workbook task reached `checked` as `assistant-1` (54 s,
  real proposal); after an engine restart, with `assistant-1` held, the correction resumed the same session as
  `assistant-2` (same session ID in both stream logs, no error; 24 s); discarding the task left no folder and empty
  homes. Tokens and cost are in the AI usage log of the 0.16 plan.
  Decisions in delivery: (1) the pool is found from the system's users named `assistant-<n>` that are members of
  `assistant`; (2) a pool user's lock is held per turn, not for the process's life, so the gate and the reset belong
  to one turn, and any free user runs the next turn (the transcript is readable to all after the reset); (3) the
  engine's writes into `work/` after creation are `workbook.xlsx`, `model.json` and `openapi.json` (at `start`, and
  again when a session starts anew) and the scratch folder `work/tmp`; all through a directory descriptor with
  `O_NOFOLLOW`, replacing what is there, and it removes `proposal.json` the same way; (4) it reads only
  `proposal.json` from `work/`, as a regular file of at most 8 MiB; (5) the reset's marker line, not its exit
  status, is the proof it ran (it ends every process of its user, and so itself); a reset that does not finish
  before a turn fails the turn with a note, after a turn it is logged; (6) a folder no task names is removed by the
  sweep only after an hour; (7) the session's ID stays on the command line for `_stop_earlier`; (8) transcripts of
  tasks begun before the upgrade are not moved: such a task starts a new session, with its files; (9) the words go
  to standard input in a container only, as the journey tests' scripted commands read them as the last argument;
  (10) the model variables passed are `ANTHROPIC_MODEL` and the three `ANTHROPIC_DEFAULT_*_MODEL`.
  **After the second review** (no defect found in links, log, locks, sudoers, sweep or upgrade; one serious in the
  reset's order, three low): the script now ends the user's processes first, repeatedly until none is left, then
  cleans (home, `/tmp`, `/var/tmp`, `/dev/shm`), then the group chmod when folders are given, then ends processes
  again, and exits non-zero with a message if any remain (`kill -9 -1` spares the calling process, confirmed, so
  the marker and the exit status are both the proof; `kill -0 -1` cannot tell whether others exist, so the script
  scans `/proc`); the engine resets before opening the gate and, after a turn, resets with the gate still open and
  then closes it, and a failed pre-turn reset opens no gate; `_close_idle_gates` re-reads the gate through its
  descriptor once the user's lock is held; the task's folders go to the reset on standard input, not its
  command line; `compose.yml` has `init: true` (the coordinator's) as a reaper. Container try: a session left a
  loop rewriting `~/.bashrc` and a continuously forking process (42, then 86 live processes) plus files in `/tmp`,
  `/dev/shm` and the home; after the turn 0 live processes, home 0 entries, none of the uid's files in the scratch
  folders, gate 0700, reset and close in 0.1 s; run directly, the script printed the marker and exited 0, with a
  bad path it exited 2. 36 unit tests (`--noconftest`; the shared test server was busy). The try used an image built
  before the script's last edit, the repo's script copied in. Known limit added: isolation between tasks inside
  one container rests on Unix permissions and the reset around each turn, reviewed twice with defects found each
  time; a container per session is the stronger form and is not built.
  **After the third review** (rework sound, two plausible weaknesses): a turn that holds its user's lock closes every other
  gate open for that user's group before it opens its own (`_close_gates_of`; a gate left open by a killed engine could
  otherwise face the next task's session); the reset also removes the user's SysV shm, semaphores and message queues
  (`/proc/sysvipc` with `ipcrm`, present in the image) and its files in `/run/lock`, `/dev/mqueue` and `/var/mail`
  (the image's world-writable folders are `/tmp`, `/var/tmp`, `/run/lock`; `/dev/shm` and `/dev/mqueue` are memory
  file systems). Try in an image built from the tree, with `--init`: planted files in each place, a POSIX queue and ids
  in all three SysV kinds were all gone after a turn's reset, a stale gate was 0700 while the new turn's was 0710, no
  zombies. `/var/mail/assistant-1` (made by root for the test; a session user cannot write there) stays. 37 unit tests
  (`--noconftest`, the shared test server being busy).
  **After the check of the last fixes:** the reset's clean-up hid every failure (`2>/dev/null || true`), so a folder the
  session made unreadable (also one nested in another) stayed with its files while the marker printed; it now makes
  the user's own folders usable again (repeating, bounded) before it deletes, passes `find` only existing places,
  checks afterwards that nothing of the user is left in them or in the home, and fails on a failing `ipcrm` or
  listing; and `_close_gates_of` raises when a stale gate cannot be closed, failing the turn. Try in a built image
  with `--init`: unreadable folders (one nested) in `/tmp` and the home were removed, exit 0 and the marker; a
  uid-owned file the user cannot remove (`/var/mail`) gave `rm: cannot remove ... Permission denied`, exit 1, no
  marker. 38 unit tests (`--noconftest`, the shared test server being busy).
  Not verified: Claude Code's other folders in a very long real session; the reset under many concurrent turns;
  the container's first process does not collect orphans that a session leaves (zombies stay until the container
  restarts; `docker run --init` or an init in the image would collect them).

## RF6: Webhook addresses on private ranges

_Decided by the user on 2026-11-11_ ("Refuse by default"), replacing the rule of C-D101, which allowed every
address but link-local ones.

- **The rule:** a webhook address that names, or resolves to, a loopback, private, unique-local or otherwise
  non-public address is refused, when a subscription is created or changed and again at each delivery (the
  name may resolve differently later), unless the instance setting that allows private addresses is on. The
  setting is off by default. Link-local addresses stay refused whatever the setting says.
- **Existing subscriptions** on such addresses stop delivering until the setting is on; the delivery log says why.
- **Tests and docs:** journey cases through the API (refused by default; allowed with the setting; a delivery
  to a name that now resolves privately is refused and logged); API.md, the settings reference, OPERATIONS,
  CHANGELOG; the guide pages on webhooks (a Codex wave).
- **Delivered 2026-11-11.** One rule, `address_refusal` in `engine/events/webhook_urls.py` (every non-public
  address via `ipaddress`, IPv4-mapped included; link-local always), used by `check_webhook_url` (create and
  edit; a name is resolved and every address checked, an unresolvable name passes) and by the delivery client
  (`post`, every resolved address checked, connection to a checked address, no second resolution; redirects
  were never followed). Setting `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` (off) in `config.py`, the catalogue,
  `.env.example`, OPERATIONS, API_JOURNEYS. A refused delivery is an `address` attempt in the log; no new code.
  Checks: unit tests of the rule, the URL check and the client; journey cases J30.6 (refused by default;
  accepted with the setting, link-local never) and J30.9 (a name that now resolves privately is refused,
  logged, and delivered once the setting is on); the J30 delivery, log, acceptance and J42 files with the
  harness's receivers given the setting; `test_api_journeys`, `test_reference_webhooks`: 176 passed after one
  rerun (the first run's database failures were collisions with another session's run).
  Decisions in delivery: a sign-in provider's requests (`exchange` with no `private_allowed`) keep their own
  rule; at delivery one refused address among several refuses the attempt; unspecified addresses follow the
  setting, as the brief listed them; a name that does not resolve at subscription time is accepted.
  **After review:** NAT64 `64:ff9b::/96` is judged by its embedded IPv4 address (the simpler rule would have let a
  link-local one through under the setting); the local-use `64:ff9b:1::/48` is refused unless the setting is on,
  its embedding place varying. The author's refusal says the host resolves to a non-public address without
  naming it; the delivery log named it before RF6 and still does. The subscription check's DNS lookup now runs
  before the row lock for an edit's new URL and for the stored URL of an edit or a resume (re-checked if the
  stored URL changed meanwhile).

## RF7: Clean test output

_Added by the user on 2026-11-12._ A passing run with errors or warnings in its output is not accepted. Applies
to the frontend and the backend: each message is fixed at its cause, and from now on such output fails the run.

- **Frontend.**
  - **Delivered 2026-11-12.** All ten items of the brief, frontend only: the workspace page (`/workspace`,
`WorkspacePage`, search over the cross-type lookup in `WorkspaceSearch`, which the top bar shares); the top bar's
search, More (`fittingCount`, the current application kept) and "← Back to ‹workspace›" in Settings (never a workspace
just deleted; in the drawer on a phone); the one-row band (PP-D33; a change set's row is its name, change count, state
and Details, the description once on the review page); the record's one line and Details with Copy ID (PP-D34);
Settings' index by task with the same groups in its menu and one `ui/Trail` in place of `Breadcrumbs` and `TrailBar`;
page titles by sidebar entry (`pageTitle`, PP-D37); Browse records folded and remembered, its search gone (PP-D35); a
change set from the list landing on its changes with "See the data with these changes" (PP-D36); `DataTable`'s
`foldColumns` ("Columns · n of m", the phone layout's own toggle; real content widths, filling the container) on record
lists and relationship tables, the model list's fact columns sized by their values, the model page's draft rows and
Home's cards (tile, name and Follow on one row, the model and roles under it); the four defects (the inspector's top
offset now includes the band, the version overlap, initials from letters only, the description once). CHANGELOG, ADR-039
and ADR-040 notes, UI_MODEL, UI acceptance (three reference patterns and rows SH1-1 to SH1-7) and CURRENT_FUNCTIONALITY
are updated. Focused Vitest, format, lint and the production build ran. **Built and confirmed in a browser** on the
developer instance at 1280px, light and dark, and at 375px: the workspace page and its search with the keyboard, the
record's line and Details, More, the band, the change set landing, the Settings index and Back, the folding and its
fill, and Home's cards. **Not run:** the e2e, accessibility and visual runners (R), whose old phrases were updated
by edit only; the first-paint timing of the fold (not measurable in a hidden pane); the side inspector case of the
clipped title. The top bar's search is left out of the phone bar (the workspace page carries it there). The guide pages
are not changed.

## UX1: Themes with their frames, and one way to edit

_Added by the user on 2026-11-12, after the SH1 review: the interface was built screen by screen and its parts
disagree. A code inventory of that day counted about 112 dialog and in-place edit sites (63 dialogs, 41
confirmations), 61 dialogs holding one or two controls, three ways to set a yes or no, five dialog widths and
more than twenty labels for the main button. The user approved a prototype in three variations and asked for all
of them as themes beside today's, with the prototype's behaviour in every theme (PP-D38 to PP-D41). The
proposal, the prototype, the inventory and captures are kept outside the repository._

**Scope, in the order it is built.**

1. **Theme base.** Token sets for each theme in light and dark, held to the same contrast minimums as today's
   (`tokens.test.ts`); type sizes, corners, shadows, control height and motion as tokens, so no stylesheet writes
   a size or a corner of its own; the display typefaces self-hosted. The choice on Settings › Appearance, applied
   before the first paint.
2. **Frames** (PP-D39), each also at phone width.
3. **The interaction components** (PP-D40): the value that becomes its field, the switch, the list under a
   value, the side sheet, the confirmation with its rule, the toast with Undo. The shared dialog becomes the side
   sheet, the shared in-place form becomes the value-as-field, and the model editor's operation dialog opens one-
   and two-control operations under their control, so most sites move with their component.
4. **The remaining sites**, one by one: the single-value dialogs outside the model editor, and each confirmation
   judged on whether it should exist.
5. **Row peek, the ⌘K search, Home** (PP-D41).

**State, 2026-11-12 (night).** Built, and seen in a browser on the developer instance (1440px, phone width, and
a list, a record and the workspace page at 1920 or 2560px; light and dark):

- Steps 1 and 2 whole: the five themes, the theme base, the two side-column frames.
- Step 3: the side sheet (as tall as its form; withdrawn the same day by PP-D69, dialogs are centred again), the value as its field, the self-saving switch in a record's
  details, Undo after an attribute save, the confirmation's plain tone, and the model editor's 42 one- and
  two-control operations opening under their control (`ui/AnchoredPopover`).
- Step 4 in Settings and security: names and a group's description changed where they stand
  (`ui/TextInPlace`), the harmless switch without a confirmation, one word per action in every remaining form.
- The record area: removing a relationship or an optional value without a confirmation, with Undo; a small
  related panel's tools folded behind one menu; unified sheet footers; and the delete dialog asking once: it
  reads the new read-only `deletion-impact` route (J04.7, reference text, contract lock, security oracle) when
  it opens and deletes under the impact's token.
- Step 5: a table row opening beside its list; ⌘K; lists found by the top bar's search; Home's search across
  workspaces; the workspace's page redrawn with the person's shelf.

Decided on the way, by the rule, and open to the user: a multi-pick in the model editor says "Apply"; removal
confirmations there still say "Remove ‹thing›"; "Sign out everywhere", "Block" (agent access), "Turn off"
(local sign-in) and "Undo steps" keep a red button; "Require a second factor" and a workspace's Retire keep
their confirmation although each can be undone. The shelf is kept in the browser, not in the account.

Not built: actions that do something (as opposed to records, lists and places) in the search; pinning a single
record to the shelf; a pick-several popover for the related-records sheet. Not run: the e2e, accessibility and
visual runners (about sixty were edited to the new texts and steps, none was run), and the guide's screenshots,
which still show the earlier interface (the lists are in `guide/_coverage/notes/UX1-GUIDE/report.md`).

Checks on 2026-11-12: every frontend test directory (about 1,900 tests) and the production build; the token
contrast tests for every theme; the backend journeys for the two engine additions (J46.12, J04.7), the contract
lock and the reference completeness tests. The guide was brought in line by Codex in three waves (73, 2 and a
few pages; 13.8 million, 0.37 million and 0.30 million tokens, almost all cached input) and passes `npm run
verify`.

**State, 2026-11-12 (morning).** Tried by hand in a browser on the developer instance (Studio theme, 1440px):
moving a shelf tile by dragging, dropping an application's list onto the shelf, Undo after a switch, after a
removed value and after a removed relationship; all work. One defect found and fixed: in a record opened beside
its list the row's controls reached 6px past the card, which clipped the remove button and let the card scroll
sideways (`styles/record-area.css`). PL4 was tried end to end with a sample workbook (the sheet at 1440px and
390px, Create workspace, the load's result on the new workspace's page). The security sweep passes again (a
route missing from its list; an assertion that predated the consumer routes' 404). Codex added PL4 to the guide
in two waves (0.72 million and 0.32 million tokens, almost all cached input); `npm run verify` passes.

Browser runners: 34 of the edited ones were run one at a time with the repository's harness; 30 pass (most
after their steps were brought to the new interface), and two product changes came out of them: Expand to full
page replaces the history entry so Back returns to the list (`app/App.tsx`), and a page's actions wrap at phone
width (`styles/interactions.css`; Settings › Workspaces scrolled sideways at 390px with its two buttons). `k1-selection`
passes again: its last step accepts a list already read whole. Still failing: `k2b-bulk-delete` and
`k3-bulk-relations`, which press Cmd+A expecting "All 60 matching selected"; a list of a few hundred rows is read
whole a moment after it opens (`useCursorWindow`, unchanged since 0.11), and the selection is then by name, so
their all-matching path is not reached; they need more rows than the window holds (600) to be reliable. Also
failing: `wp13c-ui-states` (the "Ambiguous" mapping facet, in code this release did not change). Fixed afterwards: a change set's dialog (Change model version, Submit) stays open when the window crosses the
phone width; `DataContextBand` mounted the change set's actions in one place on a phone and another above it,
and now mounts them once in a holder it moves between the two (tried at 1440px, 390px and back; the band checked
in Current and Website purple).

A second pass ran 14 more runners: `a4-relation-matrix`, `k6-relationship-filters`,
`k7-relationship-candidates`, `b4-hierarchy-acceptance`, `authoring-mg-migration`, `ua9-tree-selection`,
`k5-relation-columns` and `rv-relationship-values` pass (the last three after their steps were brought to the
new interface). Failing with stale steps not yet brought in line: `b3-tree-lens` and `c4-restructuring` (the
Move dialog's button), `workspace-m6-checkpoint` (a page title), `s6-sidebar-tree` (a tree item in the volume
explorer, cause not looked at), `s5-continuous-lists` (a panel's name); `a5-matrix-acceptance` was patched
(Enter in the cell sheet's field no longer submits; Tab to Save) and not rerun. To look at: a wide table's
"Columns · n of m" also folds relationship attribute columns on a record's panels. Not run at all: `i3*`, `i4*`,
`ag*`, `c5*`, `s7*`, `sc07*`, `sc15*`, `security-r*`, `authoring-t1*`, `authoring-r*`, `workspace-r*`,
`workspace-x*`, the remaining `wp9-*`, and the AI and Docker ones.

Found at the end and not acted on: `b3-tree-lens` waits for a button named exactly "Move", while
`TreeMoveDialog` still says "Move to ‹name›" or "Move to the top level" once a target is chosen, so either the
dialog was not brought to the one-word rule (PP-D40) or the runner's step is wrong; `c4-restructuring` waits for
"Apply to the change set" in the restructuring plan's dialog, whose button text was not looked up. The rerun of
`a5-matrix-acceptance` did not finish before the time limit and was stopped.

A third pass (2026-11-12, early morning, runner files only): `a5-matrix-acceptance` (the cell sheet now asks for a place
by radio, nothing preselected; the submit is "Add translation"), `b3-tree-lens` (Move confirm reads "Move to the top
level"), `c4-restructuring` (apply button is "Save"; the review page's h1 is "Changes in this change set"),
`workspace-m6-checkpoint` (h1 is the type's plural name), `wp9-navigation`, `wp9-change-sets`, `wp9-publications` and
`wp9-authoring` pass. `c5-restructuring-acceptance` had its review heading patched the same way and was not run.
`s5-continuous-lists` is still failing at stale steps, one per run (about three minutes each): a record's panel is now
named "vol-item-cites-group (reverse)" and its search box "Search vol-item-cites-group (reverse)" (both patched); the next
stop is the Name column header's `aria-sort` in that panel (line 581), not yet looked at. `s6-sidebar-tree` fails at
the "Group 000457" tree item (line 151) after the first-root-page check passes; cause not found (the row may lie beyond
the first page of the folded tree). Not run (stop time): `i3*`, `i4*`, `c5*`, `s7*`, `sc07*`, `sc15*`, `security-r*`,
`authoring-t1*`, `authoring-r*`, `workspace-r*`, `workspace-x*`, `ag*`.

A fourth pass (2026-11-12, 07:30 to 08:20, runner files only): pass: `c5-restructuring-acceptance` (the hierarchy tree is
found as `.tree-lens` tree; Publish is reached by Tab, then by Shift+Tab, because a volume change set lists hundreds of
rows with a tab stop each), `ag1-agent-access`, `ag3-assistant-change`, `ag4-ask-in-words`, `i3-sign-in-providers`,
`i4-sign-in` (a passkey's name is drawn twice, a hidden label and the name), `sc07-mapping-acceptance` and
`sc15-model-version-acceptance` (page h1 is the type's plural name; the candidate's list name is the tab),
`security-r-acceptance` (the gear lands on the Settings index, not About), `authoring-r-acceptance`,
`workspace-r-acceptance`, `workspace-x4`, `workspace-x5-checkpoint`. Failing: `s7-volume-acceptance` at the deep
node's change set context: a record opened from the top bar's search lands on the live record (the address has
no `changeSetId`); the search is by design a live cross-type lookup, so the runner's assertion "the record keeps its
context" needs the owner's decision (live passes up to there). `authoring-t1-designer` fails at line 682: after
extending, the old consumer version `v{n}` still answers 200 where the runner expects 404 (cause not looked at;
the backend has uncommitted consumer-API changes). `s6-sidebar-tree`: the explorer's own search is gone, so the runner
scrolls the root group to reach "Group 000457" and "Group 000396" (the heavy group), steps the sidebar by 500
pixels with a wait per step (the later groups follow the heavy branch, which scrolls past an unloaded tail), and
the collapse check no longer expects the tree to fall to under ten rows; the live context now passes to its end,
the second context (change set) stops at `reveal` of "Group 000457" (not found after 3 x 40 scroll steps; cause not
looked at, the run takes 130 s). `s5-continuous-lists`: stale steps patched (Columns toggle opened; default sort
column is the related record's, no longer "Name"); the next stop is line 588: the relationship panel no longer has a
"Relationship" column (columns are Name, vol-group, Code, Rank, Valid from, Valid until), so "sort by relationship"
by its header cannot be done; a replacement path or a decision is needed. Not run: `i3-real-provider` (Docker).

Fixed after the fourth pass: a record opened from the top bar's search inside a change set or a publication
stays in it (`app/TopBar.tsx` `dataContext`; SH1 had dropped it, found by `s7-volume-acceptance`, which passes
again). The search itself still looks in live data, so a record that exists only in the change set is not
found. For the user to decide: a relationship panel no longer has a "Relationship" column to sort by
(`s5-continuous-lists`); `authoring-t1-designer` expects an old consumer API version to answer 404 after the
model is extended and gets 200, in the consumer routes another session is changing.

A fifth pass (2026-11-12, 08:26 to 08:45, runner files only): `k2b-bulk-delete` passes: the runner holds back the
list's follow-up page requests (`cursor=`, by `page.route`) until the bar has said "All 60 matching selected", then
releases them, so Cmd+A takes the all-matching path whatever the background read does; every assertion kept.
`k3-bulk-relations` takes the same hold and now passes its Cmd+A step (line 245); it then stops at a different stale step,
line 412: a record's "Kept by" panel no longer has a button named "Change Kept by: …" (the panel's held value is edited and
removed in place; the Remove step was already brought to the new names by another session), not yet patched.
`wp13c-ui-states`: the "Ambiguous" facet is absent by design since 6578416b (2026-11-05, "several targets are Mapped
where cardinality allows"): `MappingGridView` shows it only where a source holds at most one target
(`sourceHoldsOne`), and the runner's mapping relationship is many-to-many. Runner fixed: the filtered-empty state is
reached with the search ("No results match this search"), and the inverse lens' h1 is the type's plural name ("Master
values"). The next stop is line 417, the version-mismatch step, which waits for the text "Model rdm-starter 0.10.1-wp13c"
on the change set's page and does not find it (not looked at). `s6-sidebar-tree`: the change set context now passes
`reveal`; the one that fails is History (a publication). The product defect: in a publication the explorer tree's first
root page is read without `publicationId` (live data) and every later page with it, so the server answers 422
INVALID_CURSOR for each follow-up and the tree stays at the first 50 groups ("Group 000000" to "Group 000049" of 1,000).
Cause: while `WorkspaceDataProvider` loads the publication it serves the live client (`WorkspaceDataContext.tsx`,
the `!loaded` branch), the tree's `useCursorWindow` in `RecordTree.tsx` (group list) keys its first read on
application, workspace, type, parent, search, sort and page size, not on the client, so it is not read again once the
publication client arrives. A person sees: in a publication's history view, the sidebar tree lists the first 50 groups
and nothing beyond, and scrolling loads no more (the live first page, not the publication's). The runner is correct; no
product edit made.

Fixed after the fifth pass:
- In a publication's view the sidebar tree stopped at its first 50 rows: a group that began reading while the
  publication was still loading read live data, and its following pages, read in the publication, were refused.
  The group now reads again when the publication is there (`features/objects/RecordTree.tsx`). Giving the page
  the publication's client before the publication is loaded was tried and withdrawn: it read a publication whose
  model schema is unsupported under the current model, which `App.test` guards against.
- At phone width a row opened the record's reduced view with Expand to full page hidden, so its relationships
  needed an extra step; a phone now opens the record's own page (`app/App.tsx`).
`s6-sidebar-tree`, `k3-bulk-relations` and `wp13c-ui-states` pass again (their stale steps brought in line),
and `ua8-record-in-place` and `wp9-navigation` were rerun after the phone change. `s5-continuous-lists` passes
too: its panel never had a Relationship column in the runner's model (`showRelationshipColumn` decides, and that
code did not change), so the sort check uses a column the panel has; the mapping grid's reads are recorded from
its first one; a small panel's folded tools are opened before its sort menu is used. No decision on the
Relationship column is needed. `authoring-t1-designer` passes as well: the
consumer API has kept the version before since 0.13 DF3 (`earlierVersions`), so its expectation of 404 was
stale; it now checks that the earlier version is still served as it was. All 65 runners run pass.

Screenshots, retaken afterwards (2026-11-12, reference instance rebuilt from the current code): 169 of the 319 screens in
`guide/_waves/*.screens.json` were retaken, with 32 matching `-dark.png` files. Stale steps were fixed for the record
inspector and full page, side sheets, Undo notices, the Appearance themes, the model editor (now on the draft
`3c20ac54…`) and the settings sheets. 150 were not retaken, mostly because the reference instance no longer holds the state
they show: the approval scenario (APPROVALS, 17 of 18), the workbook-load and publication screens of USE2 (16), the old model
drafts and releases (12 in MODEL, 5 in NEW-PAGES), the empty states of Groups, Sign-in and Agent access, the missing
Bonaduz translation, the Ambiguous mapping filter, a grouped model-draft line in history, and a change set that still uses
model 1.0.0 while live is 1.8.1 (so Publish is refused). Of C10's 96 screens only the 9 listed ones were run: the whole-file
run reaches the AI-driven screens, which I stopped.

PL3b, real-file try (2026-11-12, one of the user's sample workbooks: a flat sheet of regions, operators and
locations, 31 rows). It found three defects, fixed the same day:
- PL4's dialog stopped with the engine's "No proposal of the draft's inference is open" when the inference read
  no list from the workbook, and left its draft behind. It now says that refiroo found no list by itself and
  offers Adjust as the one way on; Create workspace is not shown then; a reading that fails removes its draft
  (`features/workspaces/fromWorkbook.ts`, `NewFromWorkbook.tsx`).
- On a draft with no application yet, a sheet dropped on the board was refused with "'applicationKey' is
  required". The first list now brings its application in the same request, named for the draft
  (`canvasModel.ts` `withApplication`).
- A sheet dropped on the board went through the one-list inference and made the wrong lists. The drop now does what
  the plan's table says, "a new list, its columns as fields" (`sheetAsListOperations`).

**PL3b close-out (2026-11-12, later).** Unit tests now cover `withApplication`, `sheetAsListOperations`,
`columnAsListOperations`, `dropPlace`, `sameSheetJoin`, the drop on a left-out column, `lookAtWorkbook` (no open
proposal returns without a dry run; a failed reading deletes its draft) and the dialog's no-list text. A card made
by a drop is placed at the drop point, at least 16px in from the board's edge (`dropPlace`, tried in the browser).
Decisions PP-D83 to PP-D85. **Tried in the browser** (`pl3b-workbook-canvas.mjs`, 25 checks, also without the file
variable): a refusal that names a column corrected through the refused-rows dialog and the value map (2 refused to
1); Create workspace… for real and the load's result on the workspace page; Apply to this workspace… and Load into an
existing workspace… walked to their confirmation; a column on the empty board; a drop that would repeat something.
The runner has an optional real-file mode (`PL3B_REAL_FILE`, and `PL3B_REAL_PLAN` for a JSON list of gestures kept
with the file, never in the repository): New workspace from a workbook, what the dialog says, Adjust, the gestures,
the count, Create workspace…, the load's result.

Three real samples, by shape (nothing of their contents is recorded):
- **Sample 1, a flat sheet that repeats its upper levels on every row** (30 rows, three levels). The dialog found no
  list. A sheet drop made one list (23 load, 7 refused: "A new record needs a name, and the row has none", the rows
  whose lowest level is blank); two columns dropped on the board made the upper levels; Connect with the join found
  the parent column (before the fix it said "no column of the workbook was found that names the ... records" twice:
  the engine leaves a dropped column out of its own table, and the lists that came from a column had no source).
  Create workspace…: 45 rows load, 7 refused, 68 records created. The 7 cannot be corrected on the canvas (a blank
  name has no value to map).
- **Sample 2, a wide sheet (106 columns, 400 rows) with its header on row 2.** The dialog read a different sheet by
  itself (200 rows, all load). A drop of the wide sheet is refused, with or without the header row pressed first,
  with "Sheet '<sheet>' has no column '<header>'" where the header ends in a space. Engine defect, not fixed here
  (below). Columns dropped on the board and the create worked on the proposed model (222 rows load; 3,055 created,
  37 updated, 176 unchanged, every row loaded). Reading several columns as rows was not tried on it for that reason.
- **Sample 3, a workbook of many small sheets, one with a side note column** (12 sheets). The dialog read eleven lists
  (146 rows, all load). A sheet dropped again made a second list beside the one that reads it (now refused with
  "<list> already reads <sheet>: its card is on the board"); a header in CamelCase read as one lowercase word (now
  split into words). Create workspace…: 185 rows load, 190 created, 2 updated, every row loaded. No sheet had two
  tables side by side, so the side-by-side case was **not tried on a real file**.

**Engine defect left, described:** `POST /api/v1/model-drafts/{id}/operations` with `mapColumn` naming a column
whose header ends in a space, on a source whose `headerRow` is 2, answers "Sheet 'X' has no column 'Y'"
(`engine/model/authoring/mapping.py` `_column`: the name is compared with the sheet's headers and, for a moved
header row, with `sheet.row(headerRow).values()`); the cause in the reader is not confirmed. The whole request is
refused, so no list is made. The source-columns read lists the header with its space.

**Fixed 2026-11-12:** the cause was in `_column`, which compared the header as the profile lists it (with its space) with the trimmed headers the import's reader uses; a header is now matched by its text with surrounding whitespace not significant and saved trimmed, on any header row (J58.1 in `test_j58_workbook_canvas`).

**Facts a guide how-to for the canvas needs** (Codex): the entry (New workspace from a workbook, then Adjust); the
board with Proposed cards; a sheet dropped makes a list named for the sheet (its name: the text column with all
different cells, else the most different values; every other column a field of the type its cells read as); a
column on the card (a field; the same column again changes nothing); a column on the empty board (a list of its
values, linked back); Connect with the join and the question when two columns tie; several columns read as rows
(Year and Value named at the drop); fill down and heading rows from the column menu; a column on Filters; the
header row pressed in the sheet preview; the count strip and the refused rows by reason with the value map
correction; Undo and Redo; Create workspace… and where it lands (the workspace page with the load's result); Apply to
this workspace…; Load into an existing workspace…. Screenshots for a guide: the board after three sheet drops, the
tie question, Read as rows, the refused-rows dialog with the wrong values, the value map, the workspace page after
the load, the Apply and Load dialogs (the runner writes them into its temporary folder).

**Still not done:** the side-by-side case on a real file; a wide sheet read as rows on a real file (blocked by the
engine defect); blank lowest-level rows of a flat hierarchy have no way out on the canvas (they stay refused); Undo and
Redo are shown on an empty board; the guide how-to and screenshots (Codex); no before/after inventory (the canvas
changes no reader).

Screenshots, second retake (2026-11-12, afternoon, reference instance rebuilt from the current code with `reference.sh update`):
292 of the 319 screens in `guide/_waves/*.screens.json` were retaken (the Settings pages, the centred dialogs, the in-place
editing ones and the frame), with 42 `-dark.png` files, and 18 new canvas pictures were made in a new `CANVAS.screens.json`.
States were restored through the public API and the UI steps of the screens, never in the database, by `guide/tools/screen-states.py`
(run from a screen by `{"state": ...}`; `{draft:...}`, `{release:...}`, `{cs:...}` and `{job:...}` in an address look an ID up;
`"setup": true` makes a recipe that takes no picture): the December change set moved to the current model release, a fresh
"Correct Thusis Sued abbreviation" change set that the publication screens publish, a fresh approval scenario (approval on with
the second-person rule, because a person who may approve publishes at once otherwise), the Bonaduz name translation deleted and
loaded again, the Groups list emptied and rebuilt, a "Guide draft" and a throwaway draft made and deleted by the screens,
the deliberate `ghost-field` issue, the workbook draft made through New from a workbook, the "Guide workbook test" workspace
and its workbook load, and a fresh export job. Not retaken: admin-agent-access (agent access is on in this instance),
admin-mail-settings (mail is set up with a real provider), mapping-grid-filter-ambiguous (the facet is absent by design),
run-jobs (needs a held-open database lock), admin-local-signin-off (would turn local sign-in off), admin-agent-block,
contributor-propose-change (the contributor's session opens inside a change set), and the screens that need an AI or assistant
request: use-ask-filters, use-ask-partial, use-history-explained, use-record-history-explained, model-account-facts,
use-mapping-proposal-result, use-mapping-proposed, admin-ai-test-answered, run-ai-provider-calls, use-assistant-stopped,
model-assistant-whole-type-move, model-migration-stale, import-preview-columns, admin-ai-test-failed,
model-account-provider-failure. admin-signin shows the existing provider (its empty state would unlink a person).
`npm run verify` and `npm run check:links` pass.

Not done: PL3b, the workbook canvas (PL4's Adjust opens today's model editor). The guide's screenshots were not
retaken: the reference instance could not be rebuilt because Docker on the developer machine hung on every pull
from Docker Hub (three attempts); the list stays in `guide/_coverage/notes/UX1-GUIDE/report.md`.

**API:** Undo re-saves the previous value under the record's version. One engine addition was needed and built:
the read-only deletion impact of a record (`GET …/deletion-impact`), so the delete dialog can show what is lost
before it asks. **Tests:** token contrast for every theme; unit for each interaction component;
browser tries of every theme at 1440, 1920, 2560 and phone width, light and dark.

**Instrument's type, 2026-11-12 (the user: "adjust the fonts for better readability on the instrument theme").**
Measured on Home, a workspace's page, two lists, a record, a side sheet, three Settings pages and the model
editor: the theme set Instrument Sans half a pixel under the other themes, so 18% of its text was below 12px and
about half at 12.5px or less; contrast was not the cause. Changed in `frontend/tools/gen_themes.py` only for
Instrument: text in Inter (a new bundled face, `@fontsource-variable/inter` 5.3.0, OFL-1.1), titles kept in
Instrument Sans, codes in JetBrains Mono; small text and table cells at 12 to 13px, running text 13.5px, nothing
under 11px (3% of the text is now below 12px: the uppercase section labels). Colours, frame, corners, control
and row height are as they were; the other themes' generated tokens are byte for byte the same. One rule in
`styles/frames.css` lets a long name in Instrument's list panel shorten instead of widening the panel's content.
No decision number: the choice of Inter is open to the user. Checked in a browser at 1440 (light and dark), 2560
and 390; `tokens.test.ts`, `tsc -b` and the production build pass. Before and after captures are kept outside
the repository. Not done: `THIRD_PARTY_NOTICES.md` is not regenerated (it also lacks UX1's two display faces;
R's check will stop on it), and the guide's theme row still says a theme changes the "title typeface" without
naming Instrument's text face.

**Hearth's titles, 2026-11-12 (the user: Hearth's Appearance page "looks a bit off"; then "Fraunces").** The
cause was the title face: Instrument Serif is narrow and has one light weight, so a 32px title looked thinner
than the 16px sans section headings under it; removing its tight spacing and matching its letter height to the
sans changed almost nothing. The user chose Fraunces from two mocked-up replacements (the other was
Newsreader). Changed in `gen_themes.py` for Hearth only: `--font-display` Fraunces, weight 500, tracking
-0.015em; three token lines differ, nothing else. `@fontsource-variable/fraunces` 5.3.0 replaces
`@fontsource/instrument-serif`, which nothing uses any more. On a phone Hearth's `--text-2xl` is 23px (the face
is wider; `styles/frames.css`). Checked in a browser at 1440 (light and dark), 2560 and 390; the token tests
and the bundle pass; `tsc -b` stopped on a workbook-canvas test another session was editing. Hearth's body text
was left as it is: it is Current's face at Current's sizes.

## UX2: One field saves when it is left

_Added by the user on 2026-11-12, with a capture of a list cell being edited (an input, a "No value" tick, Cancel
and Save): "When the user clicks on the edit icon then literally an inline editor option starts which is an input
field. The user types something into the input field, then clicks away and that focus change is the save, with the
same notification like for the remove value icon. There is no 'No value' checkbox and open/cancel buttons. When it
is a single field, with any data type, the inline editing should behave like this."_ Decision PP-D68, which changes
PP-D40's rule for one value. No engine change: the attribute routes already take and clear a value with the record's
version.

**One component.** `InlineEditForm` in `ui/EditInPlace.tsx` is the field every single-value editor stands in, and it
holds the whole behaviour: leaving saves, Enter saves, a choice or a tick saves, Escape cancels, an untouched input
closes, a refused input is not sent again until it changes. Its users pass only their control and their save:

| Where | Component | Saves through |
| --- | --- | --- |
| A record's details, its header's title and subtitle, a list's value cell, a relation matrix cell's record fields | `features/objects/EditableField` over `panels/InlineAttributeEditor` | the attribute routes and the record update, with the record's version |
| A relationship's value in a relationships table and a matrix cell's table | `features/objects/relations/RelationValueCell` | the relationship update, with its version |
| Names and short texts in Settings (a client, a group, a workspace, a passkey) | `ui/TextInPlace` | the page's own call |
| The model editor's names and table cells | `features/model-editor/EditableText`, `EditableCell` | one draft step |

**What each value type does** (the model has eight; it has no choice-list or link type of its own):

| Type | Control | Saved when |
| --- | --- | --- |
| Text | one-line input | the field is left, or Enter |
| Long text | text area | the field is left, or Ctrl/Cmd+Enter (Enter is a new line) |
| Whole number, decimal | number input | the field is left, or Enter; something that is not a number is refused under the field |
| Date, date and time | the browser's date control | the field is left, or Enter (the control changes with every part typed, so a change alone does not save) |
| Yes or no | in a record's details and a matrix cell's table the switch, unchanged; in a list's cell a tick | the tick or the switch is pressed |
| JSON | text area | the field is left, or Ctrl/Cmd+Enter; text that is not JSON is refused under the field |
| A choice (the model editor's cells: cardinality, value type, yes or no) | a select | the choice is made |

**Other rules.** Another field can be opened while one is open: the first saves as it is left (no field is disabled
meanwhile), and each closes only itself. A list's value cell shows one toast, the field's own "‹Field› saved" with
Undo; the second toast naming where it was saved is gone for value cells (the context band says Live or the change
set). Undo of a value set for the first time takes it out again. Focus returns to the value only when the person
did not take it elsewhere. A one-line field keeps the height of the row it stands in, in a record's details and in
a list.

**Two saves of one record never cross.** Leaving a field saves it, so the next field of the same record can be
saved while the first is on its way: `InlineAttributeEditor` gives each record one write at a time, and the second
writes against the version the first made. A press outside the field saves at the press (not after it), so a click
that opens another field, with a mouse or a finger, cannot take the first field off the page unsaved.

**Delivered 2026-11-12.** Unit tests: `ui/EditInPlace.test` (new), `InlineAttributeEditor.test` (rewritten), and
the in-place steps of the record, relationship, Settings and model-editor tests. Browser runners passing with real
keyboard and pointer: `ua8-record-in-place`, `authoring-a9-cells` (both models), `rv-relationship-values`,
`wp9-authoring`, `wp9-change-sets`, `a4-relation-matrix`, `i3-sign-in-providers`, `i4-sign-in`,
`workspace-m6-checkpoint`, `authoring-a4a-model-editor`; types exercised there: text, long text, whole number,
date, JSON, yes or no, a relationship's text and number. Tried in the dev app at 1440 and 390, light and dark: a
list's cell, the record beside its list, the record page and its title. `tsc -b` and the production build pass.
Guide text by Codex (wave `UX2-GUIDE`, 22 pages).

**Not done or not verified.** The in-place steps of `w4-workspace-admin`, `s5-continuous-lists` and
`workspace-r-acceptance` are changed, but those runners stop on steps that are not in-place edits (the workspace
page's heading, a pending list request, a keyboard path to a menu item), so w4's rename step was never reached.
`k2-bulk-change`, `u3-settings` and `sp1-security` have no in-place step and fail on other steps. Decimal and
date-and-time were not exercised in a browser (unit tests only). Focus returning to the value after Enter was
checked in the runners, not in the dev app's hidden pane. Three guide screenshots still show the old form:
`stop-edit-field.png`, `save-conflict.png`, `model-type-required-edit.png`. The guide's `npm run verify` stops on
11 workbook-canvas inventory entries, which are the canvas's own.

## MT1: The e-mail template

_Added by the user on 2026-11-12._ One e-mail template per instance, held in a one-row table and edited by the
Operator role through `mail-template.manage` in the Operations group, wraps the content of every queued mail when
it is queued; the logo travels inline and is attached when sent. Without a saved template the engine's existing
layout is used, so nothing changes until an operator saves one (PP-D42, PP-D43).

**Delivered 2026-11-12:** the engine (`engine/mail/mail_template.py`, migration `20261201_01`), seven routes with
their reference text and examples, journey tests J46.12 on two configurations, and the Settings page with a live,
sandboxed preview. Seen in a browser in one theme at 1440px. Not done: the security audit of template changes;
a look in a real mail client; `THIRD_PARTY_NOTICES.md`, which is generated at release.

## ST1: Settings as one family

_Added by the user on 2026-11-12: "redesign the settings pages, since all of them are a bit different style …
more readable, more lovely." Numbers PP-D48 to PP-D59 are left to the workbook canvas, which is planned at the
same time._

**What differs today** (25 pages and their opened items, captured at 1440px on the developer instance; the
captures and the full list are kept outside the repository):

- **Layout:** most pages are full-width ruled sections; Account is a centred 888px column of cards; Notification
  email a centred 730px column; Mail a 720px form on the left; Appearance 420px controls on the left.
- **Lists:** a narrow list beside the item (People, Groups, Clients, Sign-in, Import profiles, Webhooks), a
  full-width list whose row opens a page (Workspaces, Model), plain tables (Jobs, Signing keys), a matrix (Roles).
- **The main action:** in the header (People), in a section's heading (Passkeys, Agent clients), inside a card
  (Account), under a form at the right (Mail) or at the left (E-mail template).
- **An opened item:** a person has an avatar, a label, pills and five buttons in a row; a workspace a trail inside
  its card, a pill at the right, four buttons, then tabs; a job a trail above a page title.
- **Nothing to show:** a card saying "Choose a person.", text in the list, `EmptyState` with an action, a bare
  sentence; loading is a skeleton on some pages and a sentence on others.
- **Help text:** under the title, under a section's heading, under a field, in a card's foot, under a table.
- **Logs:** "yesterday, 04:05 PM" on Mail and AI, "11/12/2026, 5:32:26 AM" on Jobs; Load more in four wordings;
  a cost wrapping into two lines; filters as a segmented control on one page and a select on another.

**Scope** (PP-D60 to PP-D67; the mock-up shows the five patterns in every theme, light and dark, at 390, 1440
and 2560px):

1. **The parts,** each one component with its styles in one new stylesheet, tokens only: the page (`ui/SettingsLayout`
   keeps its name and gains tabs), the group, the panel and its row (a value, a switch, a choice, a fact, a
   field set with one Save), the list with its tools, the opened item's header, the log table, the index.
2. **Every page moved onto them:** the index, Appearance, Account, Notification email, Workspaces and a
   workspace, Model with its releases and drafts, Import profiles, Copy and move, People, Groups, Roles,
   Sign-in, Signing keys, Clients, Agent access, Consumer APIs, Webhooks, API reference, Jobs and a job,
   Operations, Deployment, Mail, E-mail template, AI, About. The model editor, the move editor and an
   assistant task's page are not Settings pages in this sense and keep their layout.
3. **Kept as they are:** the frame and its three arrangements, the Settings rail and its groups, what each
   person is shown by permission (hidden, never disabled), the name edited where it stands, the side sheet, the
   one confirmation, the words of the actions, every route and every capability.

**Tests:** the changed directories' unit tests; the settings browser runners brought in line and run one at a
time (`u3-settings`, `sp1-security`, `sp2-clients`, `z5-permissions`, `w4-workspace-admin`,
`i3-sign-in-providers`, `i4-sign-in`, `u5-webhooks`, `ag1-agent-access`); every page looked at in the five
themes, light and dark, at 390, 1440, 1920 and 2560px, and its real task tried. No backend change.

**State, 2026-11-12: delivered.** The parts (`ui/SettingsLayout`, `ui/SettingsParts`, `styles/settings-family.css`),
the navigation's colour, glyph and line per page, and every page of the scope moved onto them; one person's changes
(`/changes?actorId=…`) was added to the scope at the user's remark and got a way back as its first line.

- **Checked:** 870 unit tests of the changed areas; the Vite production build; the eleven browser runners
  `u3-settings`, `sp1-security`, `sp2-clients`, `z5-permissions`, `w4-workspace-admin`, `i3-sign-in-providers`,
  `i4-sign-in`, `u5-webhooks`, `ag1-agent-access`, `m1-mail`, `u4-integration`, one at a time, all passing after
  stale steps were brought in line (no product change came out of them, no axe finding); every page captured in
  Current, Studio dark and Instrument light at 390 and 1440px and in Current at 1920 and 2560px, and eight pages in
  the other seven theme and mode combinations (404 captures, each with its title, none scrolling sideways; about
  twenty looked at); ten real tasks tried on the developer instance with a temporary administrator, since
  deactivated (the index to People, a row to a person and back, the search, a group created and deleted, the mail
  switch, table density, Mail's Messages tab kept over a reload, Show more on AI's calls, a workspace's menu and
  tabs, a person's changes and Back).
- **Not passing, from other work:** `npx tsc -b` (and so `npm run build`) stops on one error in
  `features/workbook-canvas/canvasModel.test.ts`; the guide's `npm run verify` builds, and its term, inventory and
  link checks pass, but its coverage check lists eleven menu entries of the workbook canvas.
- **Guide:** Codex brought 44 pages in line in one wave (3.39 million tokens, 3.23 million of them cached input).
  88 screenshots that show a Settings page are listed for a retake in
  `guide/_coverage/notes/ST1-GUIDE/report.md`; none was retaken. Some guide pages still name old Settings groups in
  their paths ("Settings › Data operations › Jobs"), and some alternative texts describe the old layout.
- **Differs from the decisions:** the People list has no Groups column (the people list of the API has no group
  data); "n of m" is shown only where the engine gives a total (Mail's messages), otherwise "n"; Jobs, Signing keys
  and Agent access keep their name column first; Import profiles reads further rows on scroll, without Show more;
  a tab's place in the address is kept by a small hook (`lib/hooks/useAddressTab`), because the router rewrites
  the address on load.
- **Left as found:** on Settings › Model the list's column headings do not line up with their values; an opened
  group's or workspace's heading is read out as "Edit Name: …" (the name's editor is the heading); a default
  workspace's Retire is disabled with its reason, as before; in Website purple dark the group colours are close to
  each other; Webhooks' list and an opened webhook were seen only in the runner, since webhooks are off on the
  developer instance.
- **An accident on the way:** an edit of `styles/shell.css` (untracked) removed more than the old index rules; the
  rules the code uses were put back from their original text. About twenty lines of that file are unaccounted for.

## CE1: The canvas edits the whole model

**Requested by the user on 2026-11-12 ("lets make the canvas a full model editor too, plan it as a
package") and approved the same day with its six decisions as proposed ("yes, the above is good"), for 0.17:

**Journey.** A model administrator opens any model draft, with or without a workbook, as a board of its lists.
They add a list and its fields by hand, rename where the name stands, connect lists, set a relationship's rule,
arrange the navigation, open a list's tables and record page, define what integrations read, look at the issues
and the history, and install the model: everything the model editor does, on the same draft, without leaving
the canvas. The model editor stays and shows the same draft as lists and trees.

**The mechanism (whole, not in slices).** The canvas does not get a second set of model operations. Every thing
on the board is a target of the editor's own operation table (`features/model-editor/operations.ts`, 107
operations over 79 public operation kinds): a card is a type, a field row an attribute or a relationship, a
line a relationship, a group a navigation group, a frame an application. Its menu is the editor's
`OperationsMenu`, its forms the editor's `OperationDialog`, its side panel the editor's `ElementPanel`. Parity
is therefore reuse, and it is held by a test: every operation of the table must be reachable on the canvas for
its target.

**Scope.**
- **The whole model on the board.** A switch: Whole model, Changed in this draft, From the workbook. Lists stand
  in a frame per application; a released list nothing changed is drawn quieter. Find a list or a field and the
  board centres on it. Zoom, Fit, and a card folded to its top bar, for models of many lists.
- **By hand.** The editor's own Add menu in the header (Application…, Object type…, Attribute type…, Relation type…,
  group); the editor's New attribute button at the foot of every card; names of object types and attributes changed
  where they stand, saved when the field is left (UX2). An attribute row dragged onto another object type's card moves
  there (`moveAttribute`, the editor's Move to…), and up or down within its card changes its position
  (`setAttributeBinding` with `position`, the editor's Move up / Move down; Alt+ArrowUp / Alt+ArrowDown on a focused row). A draft without a workbook folds the workbook pane away and offers Add a workbook… there.
- **Inspector** (right side, tabs): the selected list, field or line in the editor's panels (definition, fields
  with their required, unique, read-only, value type, bounds, help text; relationships with their rule, the
  fields a relationship carries, which records may be chosen); **Navigation** (groups: add, rename, fold,
  order, remove; entries; the default view); **Views** (a list's table, tree, relation matrix and mapping grid
  views, and its record page, in the editor's own preview and layout editing: one implementation, shown in the
  canvas page); **Consumer APIs** (the editor's own tab).
- **Issues and History** in a drawer: the editor's list of issues, each leading to its card or field; the steps,
  with undo of chosen steps and what a refused undo depends on.
- **The draft's actions**: Install and activate…, Apply to this workspace…, Load into a change set…, Add a
  workbook…, Open as JSON, Delete draft…, as in the editor.
- **The import profile at parity**: the editor's column panel on a selected column (every binding kind, split,
  the readings, match, default), list adjustment, the key conflict notice.
- **One draft, two views**: a switch Editor | Canvas at the top of both; each remembers its last selection.
- **Every gesture by menu and keyboard**; at phone width the menus do the work and the board is one column
  (PP-D10, PP-D75).

**Decisions, approved 2026-11-12** (PP-D77 to PP-D82, in this order):
1. **The authoring principle changes.** `MODEL_AUTHORING.md` principle 7 says "Structured, not canvas-first,
   not pixels" and lists canvas-first model authoring as not in scope. *Proposed:* the principle becomes "two
   structured views of one draft": every change stays an operation, card positions never enter the model or a
   release, record layouts are still never positioned by pixels; "canvas-first model authoring" leaves the
   not-in-scope list. *Why:* the request is exactly this. *Cost:* the document and the guide change; the
   editor's rules (operations only, stable keys, lifecycle) are untouched.
2. **Consumer APIs on the canvas.** The PL3b plan says consumer APIs stay in their own page. *Proposed:* the
   canvas shows the editor's Consumer APIs tab as it is (reuse, no new design). *Why:* "fully capable" includes
   what integrations read. *Cost:* small; the alternative is a link to the editor's tab. Security stays in
   Settings.
3. **What stays out of the board itself.** Record layout and view layout are edited in the editor's preview,
   opened inside the canvas page, not drawn as cards. *Why:* the plan's rule "the preview's existing layout
   editing, not a second implementation". *Cost:* the preview has to be lifted out of the editor's own state
   (the largest single piece of work).
4. **Which view opens.** *Proposed:* a draft opens in the view the person used last; from a workbook flow it
   opens on the canvas. *Cost:* a per-person preference.
5. **Folded cards and the chosen scope** are kept with the card positions on the draft (the `canvas` document
   gains `folded` and `scope`); zoom stays in the browser. *Why:* a large model is arranged once, for everyone
   who opens the draft. *Cost:* a small addition to the canvas route; positions stay outside the draft's
   version.
6. **What a load does with records no row names** (`setMissing`: report or delete) has no place in the editor
   or the canvas today. *Proposed:* it gets one on a source's panel, in both views, with a confirmation for
   Delete. *Why:* the API has it and the interface is one client. *Cost:* a destructive choice appears in the
   interface; the alternative is to leave it to the API and say so.

**API.** No new operation kind is expected: the 79 exist. The canvas document gains `folded` and `scope`
(decision 5). Anything a gesture needs that the engine lacks is added to the engine first (PP-D5).

**Door check (ADR-032).** No reader, identity, storage or history change; the canvas sends the operations the
editor sends.

**Tests** (about a quarter of the work). Unit: the parity table (every operation reachable for its target);
scope and frames; add by hand; find and centre. Component: inspector on each kind of selection; drawer.
Browser, one runner on two configurations: a model built from nothing on the canvas and installed; a released
model opened whole, a list renamed, a field added, a relationship's rule set, a table view and a record panel
changed, a consumer API field added, an issue followed, a chosen step undone; keyboard only; 390px; axe; no
5xx. **Before and after on the user's model:** opening it on the canvas, moving cards, Tidy and folding change
neither the draft's version nor its model (checked by the outline before and after). Looked at by the main
session at 1440, 1920, 2560 and phone width, in the five themes.

**Documentation.** The canvas how-to grows into "Edit a model on the canvas" beside "Edit a model in the
editor", by Codex, with screenshots from the reference instance; `MODEL_AUTHORING.md`, `UI_MODEL.md`,
`UI_ACCEPTANCE.md`, `CURRENT_FUNCTIONALITY.md`.

**Order of delivery, one package.** The shared pieces lifted from the editor (preview and layout editing, the
element panel's selection, the source column panel); the board for the whole model; by hand; inspector and
drawer; the draft's actions; tests; guide. PL3b's open items are closed first, since CE1 builds on that page.

**Against the release's Outcome.** The Outcome asks for a workbook shaped by dragging on one screen, short
everyday journeys, and no capability removed with today's full controls one step away. CE1 goes beyond it: the
Outcome does not ask for the canvas to edit a whole model. It removes nothing and keeps the editor, so it does
not contradict the Outcome, but it widens 0.17; the user approved it for 0.17 on 2026-11-12.

**Note, 2026-11-12: the editor's concepts, words and design.** "+ New list" (with its quick-name card, the double click on the
board and the N key) and the "New field…" row are withdrawn at the user's word ("I did not ask for a new list button. If there is a
button needed to add new objects, applications, whatsoever, that already has a concept in the model editor with namings and
design"): the canvas header shows the editor's Add menu (`AddMenu`, one component, used by both views), a card shows the editor's
New attribute button, and the canvas says object type and attribute where the editor does (the editor has no "list" of records
of a type and no "field" of a type; a sheet's table is still a list). A newly made object type is selected and the board
centred on it. An attribute dragged onto another card, and up or down in its own card, were in the user's request of 2026-10-30
("drag & drop literally everything") and in the approved mock-up, and had been left out of the gesture table by mistake;
they are delivered (PL3b's table has the two rows). "Suggest…" is the editor's "Propose again…" in More actions.

**Said plainly.** After CE1 the canvas can do what the editor does. It is not faster than the editor for
everything: long attribute tables and consumer API definitions read better as lists, which is why the editor
stays. Security and the workspace's own settings stay where they are.

**Shared pieces, delivered 2026-11-12** (first part of CE1; the canvas side mounts them). All in
`frontend/src/features/model-editor/`; none reads `ModelEditor` state, and `ModelEditor` itself uses each of them.
- `useDraftEditing(draftId, { selection?, onSelect?, onAnswer?, onUndone? })` returns `DraftEditing`: `outline`, `steps`
  (`useDraftSteps`: `draft`, `reload`, `latestVersion`, `loadError`), `run(operations)` (throws a refusal, for a dialog that says
  it), `runGuarded(operations)`, `guarded(action)`, `step(send)`, `undo(steps?)`, `redo()`, `operate(operation, target, preset?)` (the
  one start of an operation: direct, flip, Move to…, or the operation form under the control that started it), `dialog` /
  `openDialog` / `closeDialog` (operation, move, dependants), `notice` / `setNotice`, `stale` / `clearStale`, `working`,
  `setPaused(boolean)` (editing waits while the engine proposes), `menuOpen` / `setMenuOpen`, `anchor()`, `draftId`. A selection and
  `onSelect` make the selection follow a key a step changed.
- `DraftEditingDialogs({ editing, busy? })` draws what `editing.dialog` holds; `DraftEditingNotices({ editing, busy?,
  onOpenApplication? })` draws the held step (Apply mine again / Discard mine) and the last notice. Render both once per page.
- `useSourceDialogs(editing, source)` returns `{ openMap(sheet, header, target?), openValueMap(use, header), openRows(rows),
  openList("adjust" | "load", sheet, block), dialogs }`: Map to…, a value map, the dry run's rows, Adjust list… / Load as a list….
  `source` is `useDraftSource(draftId, outline?.version)`.
- `useDraftActions({ editing, source, forWorkspace?, workspaceKey, proposing?, onActivated, onOpenWorkspace?, onNavigate,
  onOpenChangeSet, onShowIssues })` returns `{ has(id), label(id), open(id), items(ids), dialogs }` for the ids `apply | install | load
  | workbook | json | delete`: Apply only with `forWorkspace`, Load only with a workbook, Delete not while proposing, all but `json`
  disabled while proposing; `items(ids)` are `ActionMenu` items. `draftJsonRoute(draftId)` is the JSON route.
- `DraftPreview({ editing, mode: "preview" | "layout", objectTypeKey, applicationKey?, onApplication?, activeModel, workspaceKey,
  onShowIssues, actions })`: the type's preview and layout editor (`TypePreview` with `layout.ts`, one step per change); a layout
  form opens in `DraftEditingDialogs`. `actions` is the band's buttons (Edit layout, Back, Undo/Redo).
- Already props-only and mountable as they are, given the hook's `run` / `operate`: `ElementPanel` (`outline`, `selection`: an
  `EditorSelection`, `tab`, `onTab`, `menuOpen`, `onMenuOpenChange`, `canDrag`, `onOperation`, `onSelect`, `run`, `onPreview`,
  `proposed?`), `OperationsMenu` (`label`, `target`: an `OperationTarget`, `outline`, `onOperation`), `RelationshipMatrix`
  (`outline`, `onOperation`), `IssuesAndHistory` (`outline`, `tab`, `onTab`, `history`, `onSelect`, `onUndoStep`, `profile?`, `dryRun?`,
  `onUseProfileKey?`, `onGoToProfileKey?`, `onRemovePanel?`), `ConsumerApiPane` / `ConsumerApiPanel` (`draftId`, `outline`,
  `selection`, `onSelect`, `menuOpen`, `onMenuOpenChange`, `onOperation`, `run`), `ColumnPanel` (`sheet`, `header`, `source`,
  `outline`, `busy`, `run`, `onMap`, `onValueMap`, `onRows`, `proposed?`), `ListPanel` (as before, and `onSetMissing?`), `DraftMigrationNotice`,
  `UseFreeKey` / `freeKeyOf` (the profile key conflict) and the dialogs `InstallDialog`, `ApplyDialog`, `LoadDialog`,
  `AddWorkbookDialog`, `AdjustListDialog`, `MoveToDialog`, `DependantsDialog`.
- `operationsFor(target, outline)` (existing, the one entry: which operations an element has) and `operationTargetKinds()` (every
  operation id with its target kind) in `operations.ts`.
- `DraftViewSwitch({ draftId, view: "editor" | "canvas", onChange })` (pressed current view; records the view being on),
  `draftOpensOn(draftId, { fromWorkbook? })`, `draftViewRoute(draftId, view, { forWorkspace?, journey? })`, `lastDraftView`,
  `rememberDraftView`, key `DRAFT_VIEW_KEY`. The editor mounts the switch in its bar in place of Open as canvas; the canvas page
  mounts the same one with `view="canvas"`.
- `MissingRecords({ source, outline, busy?, run })` (the `setMissing` choice, hidden where it means nothing) and `lists.ts`
  `missingOf`, `canSetMissing`, `setMissingOperation`; the editor shows it in `ListPanel`; the canvas mounts it on its list panel.
- API: `PATCH /model-drafts/{id}/canvas` takes `folded` and `scope` (PP-D83); client `api.arrangeCanvas(draftId, { positions?,
  folded?, scope? })`, types `Canvas` (`folded?`, `scope?`), `CanvasUpdate`, `CanvasScope`.
Decisions PP-D83 to PP-D86. **Not done in this part:** the canvas side (board for the whole model, by hand, inspector, drawer,
parity test, its browser runner), the guide, `UI_MODEL.md`, `UI_ACCEPTANCE.md`, `CURRENT_FUNCTIONALITY.md`.
`frontend/e2e/pl3b-workbook-canvas.mjs` clicks the editor's "Open as canvas" link, which the switch replaced: it presses
Canvas now.

**Canvas side, delivered 2026-11-12.** `frontend/src/features/workbook-canvas/`: `WorkbookCanvas` on `useDraftEditing`,
`useSourceDialogs`, `useDraftActions` and `useDraftHistory` (new, shared with `ModelEditor`); `BoardCard` (memoised card with
fold, in-place names, New attribute), `CanvasBoard` (frames, zoom, find-and-centre, line popover), `LinePopover`,
`CanvasInspector` (Inspector, Navigation, Views, Consumer APIs), `CanvasDrawer`, `CanvasFind`, `useCanvasDocument` (positions, folds,
scope), `canvasView.ts` (zoom, find, by-hand operations built by the editor's table, targets), `canvasSurfaces.ts`; the selection is
in the route (`CanvasSelection`: `element`, `key`, `field`, `application`, `sheet`, `block`); `OperationsMenu` gained `extra`.
**Run:** vitest `workbook-canvas`, `model-editor`, `routing`, `styles` pass (new: `canvasView.test`, `parity.test`, `CanvasEditor.test`,
scope/frames cases in `canvasModel.test`, route cases); `tsc -b` (apart from other sessions' files in `features/security`), build,
eslint and prettier; `ce1-canvas-editor.mjs` (18 checks, two configurations, axe, 390px, no 5xx) and `pl3b-workbook-canvas.mjs` pass.
**Decided at delivery** (recommendation): a list's plural follows its new name only while it was the name's own plural; the card's mark
pill stands in its foot, not its bar (the bar is too narrow beside Connect); a released list nothing changed is quieter by a sunken
face and fainter border, not by opacity (contrast); an issue about a relationship links to the matrix, which names no pair, so the board
selects the relationship the first such issue is about; on a phone the inspector stands under the board, not under the selected card;
Connect onto a navigation group by dragging works while the Navigation tab is open, the card's menu does it otherwise.
**Not done or not seen:** no look in a browser at 1920, 2560 or the five themes (only 1440 and 390 in the light theme, by screenshot);
no 60-card board was timed; Consumer API and layout editing in the canvas were walked in the runner on the starter model only;
the guide page "Edit a model on the canvas" (Codex) and `MODEL_AUTHORING.md` principle 7 (PP-D77) are not written here.

**One issues drawer, 2026-11-12** (the user: the canvas's issues part was basic and misbehaved beside the editor's). The editor's
drawer is now `IssuesDrawer` (with `useIssuesDrawer`, `issueCountOf`) in `features/model-editor/`, and both pages mount it; the
canvas's own foot bar (`CanvasDrawer`, its counts, first issue and last step) and the strip's "n to fix" are gone. Its link passes
the issue's element, so on the canvas an issue about a relationship selects and centres that relationship's own line (a parent's
line for a containment) instead of the first relationship issue's; this replaces the decision above.

**Last defects, 2026-11-12.** (1) `placed` reads a stored layout apart (`apart` in `canvasModel.ts`: in reading order a card whose box
overlaps a settled one goes below it, same x); `WorkbookCanvas` writes the moved places back once after a pause through the canvas
save, never as a step. (2) A refused attribute move (the engine's `alreadyAttached`) shows in the canvas notice in `refusalText`'s
words and changes nothing (component test; it already worked through `act`). (3) An attribute type, relation type or group made from
the Add menu is selected (panel held by the page: `panel`/`onPanel` on the inspector; group: Navigation tab) and said in a toast with
Undo. (4) `ce1-canvas-editor.mjs` gained the three items (23 checks); the attribute drags use Playwright `dragTo`.
Captures for review (two drafts, five schemes, light and dark, 1440, 1920, 2560, 390, plus inspector, line popover, issues drawer and

**CE1, review of the captures (2026-11-12, main session).** The captures in
object type names were cut short on every model without a workbook, because the source-column cell of every row
took a fixed share of the row; it now takes only what its text needs (at most 96px), cards are 320px wide, and a
name that is still too long shows in full on hover. Seen and left as they are: dashed relationship lines crossing
cards on a model of several applications, and long column headers cut in the source column.

**CE1, the readings in the editor (2026-11-12).** The three import-profile readings of PL3b (`setUnpivot`,
`setFillDown`, `setHeadingRows`, with their `clear` kinds) can now be set in the model editor as well as on the canvas
(PP-D77, the parity rule). The column panel offers fill blanks, headings and read-as-rows with their Stop entries, the list
panel read-as-rows, and the source pane marks a column a reading is on. The builders moved from `canvasModel.ts` to
`model-editor/readings.ts` and the questions from `CanvasAsks.tsx` to `model-editor/ReadingAsks.tsx`; the canvas imports
them, so each exists once. The editor's read-as-rows asks which object type the new columns are added to (the list's own at first), as the
canvas's drop target does. Component tests only; not run in a browser.

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
