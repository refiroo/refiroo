# R13-GAPS: the 18 capabilities the real coverage check found undocumented

Read `guide/AGENTS.md`. The coverage check (`guide/tools/check.mjs coverage`, over `guide/tools/inventory.py`'s
inventory) now fails on 18 entries listed in `guide/_coverage/inventory/uncovered.md`. The release requirement is
full documentation of every capability at working depth, so each is documented, not excluded. Do not edit
`_coverage/exclusions.md`, the inventory or the tools.

**How an entry counts as covered** (so your text satisfies it without breaking the writing rules):

- A management operation counts when a page links its API tag: `/docs/api/?api=management#tag/system` or
  `/docs/api/?api=management#tag/source%20files` (exactly these spellings), or names its method and path in code
  style, such as `GET /api/v1/system/readiness`. Link the tag where the operations are discussed and name the
  operations in code style where an integrator or operator needs the path.
- A model-feature or screen entry counts when its key or one of its labels stands on a page as a whole word.
  Where a key is not something its reader should meet in the text (the `route:` discriminators and the view
  configuration names on a page for browser users), put it in an HTML comment at the end of the page in the
  form the repository already uses: `<!-- Inventory trace: reader-facing controls are explained above.` followed
  by the keys, one per line, and `-->` (see the end of `src/content/docs/model/applications-and-views.md`).
  The visible text must still explain the capability fully in the reader's own words.

Every capability below is documented in the visible text at working depth: what it does, the exact labels,
fields, parameters, states and answers, what the reader then sees, and what can go wrong. Take facts from the code
(references given; the code wins over any page). People who work in the browser see screens, never JSON, paths or
internal names; integrators and operators get concepts and sequences with links to `/docs/api`. Use the guide's
reference world for examples. Prefer extending the pages named; add no new page unless you cannot avoid it (if you
do, add it to `sidebar/` GROUPS as the sidebar check requires). Fix any statement on those pages that the code
contradicts and say so in your report.

## 1. System operations (operators): `src/content/docs/run/monitoring.md`

The four read-only operations of tag `system` that the Operations page and `/metrics` are built on. All need the
**Operations** access (`operations.read`, at the instance); sign-in alone is not enough. Source:
`backend/app/management/routers/system.py` (the four routes, from line 122), answer shapes in
`backend/app/management/schemas/system.py` (`ProcessResponse`, `WorkspaceReadinessResponse`, `SystemSummary`,
`BackupRehearsalResponse` and the classes they use), figures built in `backend/app/management/projections/operations.py`.
The existing paragraph "JSON equivalents for processes, workspace readiness and instance totals ..." in
`monitoring.md` is the place to grow: replace it with a section **Read the same figures as JSON** (a heading of
your choice) covering:

- `GET /api/v1/system/processes`: every engine process on the database as it last reported itself, in ID order;
  paged (`pageSize` default 100, at most 500, with the page's links); the asking process writes its own row first,
  so its figures are current and the others' are as of their last heartbeat. Per process: id (`host:pid:random`),
  host, pid, engine version, started and heartbeat times, `state` `live` or `silent` (silent: no report for three
  `PROCESS_HEARTBEAT_SECONDS`; a stopped process leaves the list, one that died stays listed silent for a day),
  `ready`, background `threads`, connection `pool`, `unavailableReleases` and `counters`. Name the sub-fields as the
  schema has them and tie each to what the Operations page shows under **Engine processes**.
- `GET /api/v1/system/readiness`: each active workspace in key order (paged as above) with the release it runs
  (`null` for none), `state` `served` or `unavailable`, and `unavailableIn`: the live processes that cannot serve
  it with `reason` `unsupportedSchema`, `invalid` or `notLoaded`. Tie to the **Workspaces** table and **Not served by**.
- `GET /api/v1/system/summary`: the figures counted now (processes live and silent; workspaces served and
  unavailable; jobs queued, running or awaiting confirmation by kind and state, a combination with none left out;
  webhook subscriptions active, failing and suspended): the same figures as the instance gauges of `/metrics`, as
  JSON; not paged.
- `GET /api/v1/system/backup-rehearsals`: the backups restored into a separate database and checked with
  `python -m app.cli.restore_check`, newest first (`pageSize` default 20, at most 200): `passed` or `failed`, the
  backup name, `dataAsOf`, revision before and after, engine version, host, the failure's `code` and message, and
  per workspace of the copy its release, `served` or `unavailable` (with the reason) and the counts (records,
  relationships, open change sets, publications, and the instance's live records when checked). This is what the
  **Last backup rehearsal** panel reads. Also add one sentence and a link in
  `src/content/docs/run/backup-and-restore.md` (section "Rehearse in a separate database", after the paragraph about
  the **Last backup rehearsal** panel) saying the same results are readable as JSON.

Say how an operator or a monitoring system would use them (a token with the Operator grant; the page is paged; it is
read only) and link `/docs/api/?api=management#tag/system` for the field-level reference. Keep what the page already
says; add no new claims about `/metrics`.

## 2. Source files (people in the browser and integrators)

Sources: `backend/app/management/routers/source_files.py`, `backend/app/management/schemas/sources.py`,
`backend/app/engine/sources/store.py`, `backend/app/engine/authorization/visibility.py` (`may_use_source_file`,
`visible_source_files`), `backend/app/management/projections/source_files.py`. A source file is the XLSX or CSV
workbook that a model draft or an import profile owns; storing one starts a profile job that reads its sheets,
blocks, columns and cells so a person (or a client) can see what is in the file before binding it.

**Browser side** (find the screens in `frontend/src/features/` by searching for the workbook source pane, "New
from a workbook" and the import profile page; take labels exactly as shown): add to
`src/content/docs/model/workbook-onboarding.md` (section "Source file and draft") and
`src/content/docs/use/importing-and-exporting.md` (sections "Read a file through a profile" and "Remove an uploaded
file or an import profile") what the reader sees of a file once it is stored: that reading the file is a job, that
the sheets, the header row and the lists (blocks) of each sheet, the columns with their statistics (filled,
distinct, a possible key, values, placeholders, overlaps with other columns and with records in the workspace) and
the cells of a range are what the source pane shows, what a newer file does to the earlier one (it is superseded and
deleted after the job retention period), who may use a profile's file (its uploader and holders of Bulk and import
in its workspace) and what refuses a file (too large, not XLSX or CSV, the profile not finished yet). Only what the
screens show; no API names in these two pages.

**Integrator side:** add a section **Source files and their profile** to
`src/content/docs/integrate/files-imports-and-exports.md` (before "Prepare and diagnose a file" or inside it, your
call) that explains the sequence and names each operation in code style, linking
`/docs/api/?api=management#tag/source%20files` and not repeating field lists:

1. `POST /api/v1/source-files`: multipart, `file` plus a `request` JSON form field with the owner (`draftId` or
   `profileKey`), `format`, `csv` delimiter and `workspaceKey` (the records the profile compares the columns with);
   answers 201 with the file and its profile job (kind `profile`); refused `413 IMPORT_TOO_LARGE` over
   `IMPORT_MAX_BYTES`, `422 UNSUPPORTED_FILE_FORMAT`, `404` for an unknown owner or workspace. Needs
   `source-files.manage`; a profile's file needs Bulk and import in the workspace named. The write operations exist
   only with `INTEGRATION_JOBS_ENABLED`.
2. `GET /api/v1/source-files` (filters `draftId`, `profileKey`, `pageSize` default 50, at most 500, newest first; a
   profile's files only where the caller may use them) and `GET /api/v1/source-files/{source_file_id}` (the file:
   name, format, bytes, SHA-256, owner, workspace, delimiter, upload time, `supersededAt`, `version`, and the
   profile's `state` with its job id and error).
3. The profile, readable once its state is `completed` (`409 SOURCE_FILE_PROFILE_NOT_READY` until then): `GET
   /api/v1/source-files/{source_file_id}/profile/sheets`, then `.../profile/sheets/{sheet}/columns`, then
   `.../profile/sheets/{sheet}/cells?range=A3:C12` (`422 INVALID_RANGE`, `404 SOURCE_SHEET_NOT_FOUND`). Explain what
   each answers (sheets with rows, header row, `laidOut`, blocks with range, header row and note; columns with
   statistics; cell rows by column letter with staged text and value type) and how a client uses the sheets'
   `headerRow` and block as an import profile source's `headerRow` and `block`.
4. `DELETE /api/v1/source-files/{source_file_id}?expectedVersion=N`: removes the file, its staged cells and its
   profile; `409 VERSION_CONFLICT` at another version. A file that belongs to an assistant task is not served here
   (`404 SOURCE_FILE_NOT_FOUND`); it is read through its task.

## 3. A relationships table's columns and grouping (model administrators)

Source: `backend/app/models/schema.py` (`RelationTableViewConfig`, its docstring and fields around line 255) and
the editor's side in `frontend/src/features/model-editor/relationTableView.ts` and `operations.ts` (search
`relationTable`, `tableFields`, `LAYOUT_OPTIONS`; actions "Add a view…", **Layout…**, **Remove relationships
table**). Pages: `src/content/docs/model/applications-and-views.md` (its "Views" table lists four view kinds and
leaves out **Relationships table**; its sentence about **Add a view…** and "table layouts are arranged from the
type's Preview" must be corrected: the editor offers **Relationships table: each relationship in a row, with its own
attributes**) and `src/content/docs/model/json-view.md` where the configuration names belong for a specialist. Link
the existing guide `src/content/docs/guide/model/add-a-relationships-table.md` and, from there, add nothing that
repeats it; read it, and correct it where the code disagrees.

Cover as screens: the fields of the dialog (**Relationships**, **Columns of the from record**, **Columns of the to
record**, **Attributes of the relationship**, **Layout**, **Head the rows by**, **Name**) and what each stores:
`fromColumns` and `toColumns` (each `name` or a scalar attribute of that end's type; at least one each; the order is
the column order), `attributeColumns` (attribute types the binding declares), `groupBy` (`from`, `to` or none: heads
the rows by that record; ignored by the grid layout) and `layout` (rows or grid: each from record once, a column
group per to record). How filters and sorts follow from the columns (`from:`, `to:`, `relation:` fields; a JSON
attribute may be a column but not a filter or a sort), the first sort is `from:name`, page size, and the rules the
model's validation applies (`application_rules._check_relation_table_view`): quote the refusals' wording from the
code. In `json-view.md` (a specialist's page) name `fromColumns`, `toColumns`, `attributeColumns` and `groupBy`
with the rules; on `applications-and-views.md` put the four keys in the Inventory trace comment as
`applications[].views[].config.fromColumns` and so on (the comment already exists there; extend it).

## 4. Set a sunset day on an earlier contract version (model administrators)

Source: `frontend/src/features/model-editor/operations.ts` (`consumer-version-sunset`, from line 2688:
label **Set sunset day…**, dialog title **Sunset of version N**, field **Sunset day**, its hint; its sibling
`consumer-version-stop`, **Stop serving**, with its confirmation), `backend/app/engine/model/authoring/consumer.py`
(`set_consumer_api_sunset`: `YYYY-MM-DD`, empty takes it back, the engine serves the version until it is removed
whatever the day, a refused value is restored). The existing text in `src/content/docs/model/consumer-apis.md`
(around line 251) and `src/content/docs/guide/model/stop-serving-an-earlier-contract-version.md` (step 3 under
"Announce the end date") says the row's **Sunset day** is edited in place and saved; the screen instead offers a
row action **Set sunset day…** that opens a dialog **Sunset of version N** (find in the editor's components how the
action is reached from the row of **Earlier versions**, and how the result is shown). Correct both pages to the
real steps and labels, keeping their other content, and add the dialog's field hint, what an empty value does and
what a refused value looks like.

## 5. Related jobs of an assistant task or a model draft (stewards)

Source: `frontend/src/features/settings/JobGroupView.tsx`, `frontend/src/features/jobs/jobText.ts` (`ORIGIN`:
**Assistant task** with **Open the task**, **Model draft** with **Open the draft**), `frontend/src/features/jobs/JobPage.tsx`
(the trail `‹ Assistant task: <name>`), `frontend/src/types/ui.ts` (the group's kind `aiTask` or `modelDraft`),
`frontend/src/features/jobs/OriginName.tsx` (an assistant task is named after its workbook). `src/content/docs/use/jobs.md`
already has a paragraph on grouped jobs. Extend it to full working depth, one subsection **Jobs grouped under a task
or a draft** with the screen as the reader meets it: the grouped row and its counts, the page of one group (its
eyebrow, the **Summary of the group**, the state buttons with counts, the table of jobs), **Open the task** and
**Open the draft** and when they are offered (when the reader may open them), the trail from a job back to its
group, Esc, and the remembered **Grouped** or **All jobs** choice. Do not write the internal names in the visible
text; put `route:aiTask` and `route:modelDraft` in an Inventory trace comment at the end of `use/jobs.md`.
If `use/loading-with-the-assistant.md` or `model/issues-and-dry-run.md` already says where a task's or draft's jobs
are found, add one link to that subsection rather than repeating it.

## Files you may edit

- `src/content/docs/run/monitoring.md`
- `src/content/docs/run/backup-and-restore.md`
- `src/content/docs/model/workbook-onboarding.md`
- `src/content/docs/use/importing-and-exporting.md`
- `src/content/docs/integrate/files-imports-and-exports.md`
- `src/content/docs/model/applications-and-views.md`
- `src/content/docs/model/json-view.md`
- `src/content/docs/guide/model/add-a-relationships-table.md`
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/stop-serving-an-earlier-contract-version.md`
- `src/content/docs/use/jobs.md`
- `src/content/docs/use/loading-with-the-assistant.md`
- `src/content/docs/model/issues-and-dry-run.md`
- `_coverage/notes/R13-GAPS/**`
- `_waves/progress/R13-GAPS.md`

## Report

Per entry: the page and heading where it is now documented, how it is covered (tag link, path, key or trace
comment), statements on existing pages you corrected, anything you could not verify in the code, screenshots wanted
(listed as AGENTS.md rule 8 says), and anything in refiroo that looks wrong.
