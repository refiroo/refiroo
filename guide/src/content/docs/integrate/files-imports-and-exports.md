---
title: Files, imports and exports
description: Exchange files with checked profiles, authoritative execution and a usable synchronization baseline.
reader: integrator
---

Use an export to hand a defined dataset to another system, and an import to bind a supplied file to the model. Both run as [jobs](/docs/integrate/jobs/). Follow [Exchange a supplier file](/docs/guide/integrate/exchange-a-supplier-file/) or [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/).

## Export a defined scope

The [export operation](/docs/api/?api=management#tag/exports) selects one workspace and context: live, a change set or a publication. Choose types and their criteria, optionally a subtree and business date, and whether to include relationships. JSON Lines, CSV and Excel workbook formats serve different recipients; choose the layout before requesting the file.

An export reads one database snapshot. Its job output records counts, context, model release, format, size and checksum. A live export also records the feed position matching that snapshot. **Keep that position from the job metadata**, not by looking for a position inside the file. It is the checkpoint for following changes after loading the baseline. If its worker crashes, an export restarts its whole snapshot read rather than appending to an incomplete file. Only a completed job serves output; failed, cancelled and expired work cannot be used as a partial baseline.

JSON Lines exports contain repeatable upserts and relationship ensure operations. Sending an untouched export back to its workspace changes nothing. Edited records carry version claims, protecting changes made since export. CSV and the normal workbook layout use the export's table contract. History is not transferred, and importing is not a database restore.

## Export a declared view

Use [Create export](/docs/api/?api=management#tag/exports/POST/api/v1/exports) with `view`
instead of `scope` when the recipient needs a declared view's layout. Name its application and
view and supply the supported state that narrowed it. The engine derives the selection and
workbook from the model. `format: "xlsx"` and `layout: "people"` produce the editing workbook;
a table view also supports the technical layout. Other view kinds do not.

Carry the view's search, row criteria and parent scope where supported. A relationships table
can also narrow its target records; a matrix can name column records and cell state. State
that the view kind cannot read is refused as `INVALID_EXPORT_LAYOUT`, with the request pointer.
A filter on a relationship's own values is not carried by the browser export; the dialog
reports that omission. The [export operation](/docs/api/?api=management#tag/exports) defines
which state each view accepts. Keep this selection with the job rather than recreating it
from whichever browser page is open later.

For a link matrix, `view.cellField` chooses the name or a bound text field used to list records
in cells; the default is `name`. The file records the reading for import. A field unsupported
by the view is `INVALID_EXPORT_LAYOUT`; missing values on linked records refuse the export. A workbook
export holding a text over a cell's 32,767 characters fails with `EXPORT_TEXT_TOO_LONG`, naming the sheet, record and
field; a `;` inside a listed name is written as `,`.
There is no export container map. Use the
[matrix container read](/docs/api/?api=management#tag/relation-matrix) when building a cell
creation client: eligible containers carry `cellCount`, and `defaultContainerId` gives the
rule-fixed place or the busiest used container. Without a rule-fixed place, an unused
container is never selected and ties give no default.
`derivedPlace` describes a rule-fixed or proposed group, including `proposed` and
`willBeCreated`. Follow the operation reference for the full response.

Placement first applies the binding's ancestor candidate rules. Rules identifying one missing
group cause it to be created with the cell record. Otherwise existing use of this view supplies
the place. When neither decides, a compatible group can be proposed from the type and name
used under other columns, without changing the model. A browser client allows its name to be
edited and sends group, record and connection in one atomic batch. Import derives the place
at reading time and reports any group it would create before confirmation. A missing place
refuses the new record with a reason rather than choosing an unused group arbitrarily.

A type, application or workspace exported with the people layout has one sheet per type,
parents first, with parents and relationships by name. Leave `people` options out for this
multi-type layout; those options describe a single type's workbook. All XLSX layouts include
**About this export** as the second sheet, explaining the context, selection, counts,
relationships, load-back rules and where new matrix records go. Import ignores that sheet.
The job output lists data sheets separately and identifies the exported view.

See [Workbook layouts](/docs/use/importing-and-exporting/#workbook-layouts) for the file shapes
and [Export records](/docs/guide/use/export-records/) for the browser sequence.

## Import with a profile

Use the [import and import-profile operations](/docs/api/?api=management#tag/imports) for supplier CSV and workbooks. A profile maps sheets and columns to model types, names, typed attributes, parents, relationships and related owned records. It can use value maps for placeholders, split relationship lists, flags and selected reference values. The binding handles generic model structures, including records owned through relationships. Bind a parent once, as a fixed value or a column (`PARENT_BOUND_TWICE` otherwise). Creating missing named parents or related records needs name matching (`CREATE_NEEDS_NAME_MATCH` otherwise).

A source can change how its sheet is read before columns are bound. The same readings apply
to imports, draft dry runs and profile checks, and remain in a saved profile for the next file.
They apply in this order:

1. `headings` reads a row whose only filled cell is in its chosen column as a heading,
   rather than a record. Its text fills an added column on following rows until the next
   heading; rows before the first heading have no heading value. Bind the added column as
   the parent when headings name parents.
2. `fillDown` fills blanks in selected columns from the nearest filled cell above in each
   column. A blank before any filled cell stays empty.
3. `unpivot` reads a wide sheet as rows. Each filled cell in the selected columns produces
   a row with the column header and cell value in two added columns. Empty cells produce
   no row; if all selected cells are empty, the original row produces none. The resulting
   rows keep their original sheet row number.

Bindings name the added columns like other headers. New names must not clash with the table
or each other, and a column cannot be both filled down and unpivoted. Column headers are
matched without surrounding spaces. See the [import profile reference](/docs/api/?api=management#tag/imports)
for the member shapes and validation rules, and
[draft operations](/docs/integrate/model-and-release-operations/#edit-a-workbooks-reading) for changing them.

On the next-version check, accepted renames carry the readings to the new headers. Missing
columns are removed from `fillDown` and `unpivot`; fill-down ends if no columns remain, and
unpivot ends if fewer than two remain. A missing heading column removes its heading reading.
Bindings of added columns that disappear are removed from the effective reading too. Inspect
the check before loading rather than assuming the earlier layout still fits.

A source's `missing` choice concerns keyed records of its object type that no row names:
`report` (the default) keeps and reports them; `delete` stages their removal in a change set.
Deletion needs a keyed source loading its own records, and cannot run against live data.
Set the choice through the draft's `setMissing` operation; this differs from creating a
missing parent or related record during name matching.

Profiles are versioned instance resources associated with a model. Saving and using a profile checks its references against the chosen workspace's model. Check it again after changing releases. A profile belonging to another model is refused as `IMPORT_PROFILE_MODEL_MISMATCH`; do not repurpose its key silently.

Choose a repeatable key: public ID, an attribute key, an allowed stored-unique or compound key, or a name key. A name key with a parent identifies children under that parent. Ambiguous existing names are `AMBIGUOUS_NAME_KEY`; ambiguous compound or stored keys need correction rather than a guessed match. A compound key must have every component bound and filled, and must identify at most one existing record. `KEY_NOT_BOUND`, `MISSING_RECORD_KEY` and `KEY_AMBIGUOUS` require fixing the profile, filling the key or disambiguating existing combinations; a configured skip rule can omit rows with an empty key (a key cell that cannot be read is refused, not skipped). Without a key, each row creates a record again on the next load.

Matching reads existing records and records loaded by the same file. Parents load before children, and relationships follow their records. Profiles can explicitly create missing named references where configured. Repeated keys merge compatible filled values, whether the rows are in one source or several; conflicting non-empty values reject the contributing rows as `DUPLICATE_KEY_IN_FILE`.

Imports without a profile accept JSON Lines batch items or refiroo's exported table and workbook layouts. A profile normally permits updating found records; without a profile the default protects changed records unless versions or explicit overwrite permit the update. Choose this deliberately rather than relying on a supplier's intent.

## Preview before applying

A preview binds the file and tries changes without committing them. For matrix and relationship
columns, inspect `reading` in the binding report: recorded or guessed matching field, match
and ambiguity evidence, alternative readings and the place for new records. Value-sheet
readings add update/new-row counts; link columns report values from value sheets and values
creating records. A place with `willBeCreated` names the group and its column parent.

To change a field, use [Read an import again](/docs/api/?api=management#tag/imports) through
`POST /jobs/{jobId}/reread` while the job awaits confirmation. This previews the same file
with the changed reading and cancels the original preview; neither writes records. Follow
the new job, review it and confirm that job. To keep the reading in a stored profile, save
the new job's resolved profile definition through the
[profile operations](/docs/api/?api=management#tag/imports), with the profile's current version.
The API reference defines reading indexes, requests and refusals. Read the proposed counts, every refused row and its failing cells, and the per-column report: empty, converted, value-mapped, resolved, not found, ambiguous or refused. The preview tries items independently to expose problems even for atomic policy; its result explains what that chosen policy would allow.

Large previews can be samples, by default up to 10,000 items. Read their coverage before treating the preview as complete. Confirmation binds the stored file again against current data and executes the chosen policy. Preview success does not guarantee execution success. Confirmation is idempotent; cancelling a waiting preview ends it immediately. An expired preview cannot be confirmed.

Correct refused rows in the source and send the file again; correctly keyed rows already applied become unchanged. Row outcomes are paged, not supplied as a downloadable refused-row file. A profile configured to delete records missing from the file requires a change set (`MISSING_DELETE_NEEDS_CHANGE_SET`), so the removed records can be reviewed. Missing-record deletion removes their relationships but refuses to silently remove surviving descendants or required dependants; resolve those dependencies before confirming another preview.

## Workbooks for people

A table-view people workbook follows the table's columns, labels and order, with hidden record IDs, versions and its import profile. Relationship summaries can be marked as not imported. Separate relationship sheets add or change relationships without removing omitted ones. Main-sheet columns configured as relationship lists replace those sets.

Blank attribute cells leave stored values alone. A blank **replacing relationship-set cell clears the set**, if the model allows it; do not assume every blank is ignored. An owned-record column left empty makes no change. Columns grouped by parent can create or update those owned records when filled. Cells naming records use dropdowns from a reference sheet (warning-style where a cell may name several); invalid choices still face the model's rules on import. A name several records share resolves to the record the row is already related to by that relationship, so an unchanged file imports back unchanged. Keep hidden identity and version columns intact when editing a round trip.

These table rules differ from matrix workbooks. The main matrix sheet imports only its
cells, leaving row labels alone; value sheets load records separately. In a record-field matrix, hidden cell IDs and versions identify the record;
a cell holding several records is marked not loaded and skipped. A link matrix has dropdowns
and reads a non-empty list as the connections within that row and column only. It preserves
other columns and checks the row's relationship-set version. Names containing `;` are written
and matched with a comma instead. When creation is also enabled, an unknown name can create a
record in its derived or proposed place. A link matrix also exports a value sheet per column,
with its eligible and linked records' fields, group for reading, and hidden IDs and versions.
With Edit or Create enabled, a row with an ID updates that record; a row without one creates
where Create is enabled. With only Link and Unlink enabled, these sheets do not load.

A main-cell value matching the column's value-sheet row names that record. A renamed row is
found by its new value and its old value unless another row now holds it. The same new value
in both sheets is one record. A value in neither the file nor existing records creates one
where allowed, supplying the name and selected field only. A value-sheet row no cell chooses
still creates or updates. Ambiguous values are refused as `REFERENCE_AMBIGUOUS`. Import
resolves the sheets together; spreadsheet text does not synchronise itself. A record-field
matrix has no value sheets.

Clearing a matrix cell changes nothing. Removing every value or link in a cell and editing
several-record field cells remain browser tasks; link-layout records can be edited on value sheets. An ordinary table column
representing a required owning relationship is read-only; edit its dependent records on their
own sheet. In a relationships-table grid, Yes on a missing pair links it, while No does not
remove an existing connection. Read the workbook's About sheet before choosing overwrite or
assuming blank cells delete anything.

For browser controls, see [Importing and exporting](/docs/use/importing-and-exporting/) and [Jobs](/docs/use/jobs/). An integration can request the same layout through the export API without reproducing the browser workflow.

## Load into another workspace

Record IDs are unique across the instance. An export's IDs still identify the original workspace's records. Explicitly choose counterparts to load them as the target workspace's own records. Derived IDs depend on the source ID and target workspace; repeating the load finds the same counterparts. Parent and endpoint references translate too, and outcomes retain the source ID.

Counterparts work only between workspaces running the same model. `COUNTERPARTS_ACROSS_MODELS` requires a [model-to-model move](/docs/guide/integrate/move-records-between-models/). No continuing synchronization relationship is created by the counterpart load. Relationship IDs are not translated. Source version claims are ignored for counterpart upsert, update and ensure-relationship operations; deletes still claim the target counterpart's version. A missing counterpart reference requires loading its owning file first.

## Recover from file refusals

`IMPORT_FILE_MISSING`, `IMPORT_FILE_UNREADABLE`, `IMPORT_FILE_MISMATCH` and `UNSUPPORTED_FILE_FORMAT` require the expected readable file and layout. CSV is UTF-8 with supported quoting; workbook formulas use their cached values rather than being calculated. `IMPORT_TOO_LARGE` and `IMPORT_TOO_MANY_ITEMS` require splitting below the configured upload and job limits (defaults 200 MB and 1,000,000 items).

`INVALID_IMPORT_PROFILE` requires fixing the reported binding paths; `IMPORT_PROFILE_NOT_FOUND` or `IMPORT_PROFILE_EXISTS` requires the intended profile key; `VERSION_CONFLICT` requires reading its latest version. `PROFILE_CHECK_NOT_FOUND` requires a current check, while `SOURCE_FILE_PROFILE_NOT_READY` means finish preparing its profile. `SOURCE_FILE_MISSING`, `SOURCE_FILE_NOT_FOUND` and `SOURCE_SHEET_NOT_FOUND` require the intended stored file and sheet. `MISSING_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `PARENT_NOT_FOUND` and `INVALID_ATTRIBUTE_VALUE` require correcting the named source cells. `INVALID_EXPORT_LAYOUT` requires a supported layout and consistent column choices. Refusals name paths or cells so a client can present the cause beside the source data.

## Source files and their profile

A source file is an XLSX or CSV workbook owned by a model draft or saved import profile.
Uploading stores it and queues a job of kind `profile` to analyse its sheets, columns and cells;
that analysis is separate from the import profile's mapping instructions. Use the
[source-file operations](/docs/api/?api=management#tag/source%20files) in this order:

1. `POST /api/v1/source-files` sends multipart `file` and a `request` JSON form field.
   In that request, `owner` names exactly one `draftId` or `profileKey`; `format` can declare
   XLSX or CSV, `csv` supplies the delimiter, and `workspaceKey` selects records for column
   comparisons. Without a workspace, columns are compared only with each other. A 201 answer
   contains the stored file and its profile job. A newer file supersedes the owner's previous
   one (for a profile, within the same workspace); it is deleted `JOB_RETENTION_DAYS` after
   replacement. Uploads over `IMPORT_MAX_BYTES` return `413 IMPORT_TOO_LARGE`; unsupported
   formats return `422 UNSUPPORTED_FILE_FORMAT`; an unknown owner or workspace returns 404.
2. `GET /api/v1/source-files` lists newest first, optionally filtered by `draftId` or
   `profileKey`. `pageSize` defaults to 50, at most 500; follow the returned page links.
   `GET /api/v1/source-files/{source_file_id}` reads one file, including its name, format,
   byte size, SHA-256, owner, comparison workspace, delimiter, upload time, `supersededAt`
   and `version`. Its `profile` reports the job ID, state and any error. Wait for `completed`;
   queued, running, failed, cancelled or expired analysis is not ready for use.
3. `GET /api/v1/source-files/{source_file_id}/profile/sheets` returns sheets in workbook
   order, their row counts and `headerRow`. `laidOut` identifies a sheet arranged as lists;
   its blocks give ranges, headers, titles and any note. Use a sheet's `headerRow` and the
   intended block to set an import profile source's `headerRow` and `block`, rather than
   assuming all sheets are one table starting on row 1.
4. `GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/columns` returns
   columns in block and column order, with filled/distinct counts, candidate-key evidence,
   possible value types, frequent values, placeholders, delimiters and overlaps with other
   columns or workspace records. Read the reported limits before treating overlap evidence
   as exhaustive. `GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/cells?range=A100:C120`
   returns filled rows of the rectangle in row order, with cells by column letter. Each cell
   has staged text as used for matching and its value type. These reads are paged: sheets
   default to 50, columns and cell rows to 100, each at most 500. Until profiling completes,
   they return `409 SOURCE_FILE_PROFILE_NOT_READY`. An unknown sheet returns
   `404 SOURCE_SHEET_NOT_FOUND`; a malformed, empty or out-of-sheet range returns `422 INVALID_RANGE`.
5. `DELETE /api/v1/source-files/{source_file_id}?expectedVersion=N` removes the file,
   staged cells and analysis, returning 204. It leaves the saved import profile and previously
   loaded records. Read the current version first; `409 VERSION_CONFLICT` means another version
   is current and needs inspection before retrying.

These operations require `source-files.manage`. A profile's upload also requires **Bulk and
import** in the named workspace. Its files are readable by their uploader and holders of
that workspace's Bulk and import grant (at the instance for files naming no workspace),
subject to the operation's permission check. Listings filter visibility accordingly.
Upload and delete routes exist only with `INTEGRATION_JOBS_ENABLED`; reads remain registered.
An assistant task's workbook is read through its task, not here: direct access returns
`404 SOURCE_FILE_NOT_FOUND`.

## Prepare and diagnose a file

Send an import as multipart form data with the file and its request description; the [import operation](/docs/api/?api=management#tag/imports) defines the request. Use a stored profile, an inline profile or a supported profile-free layout. Unreadable files, missing declared sheets or columns and unresolved bindings fail validation before execution. With atomic policy, a rejected bound row prevents the file’s writes.

A preview binds every row, even when only a sample of items is tried. Items run in execution order, with records before relationships; a row counts as previewed only when all its items were tried. Read row coverage alongside item coverage. After a confirmation refusal, the preview can remain waiting: correct the named context or access problem rather than treating the file as executed. Waiting previews expire from the end of their preview, using job retention.

| Format | File preparation |
| --- | --- |
| CSV | UTF-8, optional byte-order mark, RFC 4180 quoting and a header row. The default separator is a comma; declare another delimiter in the profile where needed. |
| XLSX | One or more sheets. Supply actual values or formula cached values; refiroo does not calculate formulas. Dates can be date cells or ISO 8601 text. Excel text escapes are decoded. |
| JSON Lines | One batch item per line, with no profile. Exported lines use upserts followed by relationship ensures so they can be read back. |
| Exported table | CSV or XLSX with the exported identity, type and field columns; no profile is needed. Keep the field-key headers intact, including `#` attribute columns. `~` summary columns are ignored on import. |

An empty or whitespace-only attribute cell leaves the attribute out of the write; it does not clear a stored value. Other text is kept as supplied. A value map can change how a particular source cell is interpreted. Conversion uses the target attribute’s declared type; a failure identifies its column as `INVALID_ATTRIBUTE_VALUE`. Replacing relationship cells have their separate empty-set behavior described above.

Profiles can read a bounded sheet block with a header row, ignore columns, bind fixed references and flags, or write only relationships and related records for an existing main record. A related-record binding finds the related record through its relationship and parent. Translated names and system mappings use this same generic binding. Profile source dependencies must be acyclic. Ambiguous reference matches reject the row; a profile’s match field need not itself be a unique attribute.

A row’s result reflects its worst item outcome and identifies every failing cell. Read individual item outcomes when one row produced several records or relationships. Every bound import has a binding report, including an execution without a preview. Use those reports to correct the source or profile, then rerun with stable keys.

Export manifests include a SHA-256 checksum. Choose whether relationships require both ends in scope or include all edges of selected records. The latter can refer to records outside the exported selection; ensure the destination already has those records or load them separately. Business-date exports filter only types with a declared period and identify the types dated.

## Use the assistant to prepare a load

The [assistant task API](/docs/integrate/assistant-tasks/) accepts a workbook or instructions, proposes a model draft and checks every row before a person accepts it. A session load prepares a change set for review; it cannot publish or activate. A matching saved profile can avoid a session and its cost. The assistant requires Use AI proposals, Bulk and import and send level `values`; the workbook and needed records can leave the instance for Claude Code. Read [AI data, costs and retention](/docs/run/ai/) before submitting. Use the [AI task operations](/docs/api/?api=management#tag/ai) for this sequence; the ordinary import API remains available.

## Access, profile changes and retirement

The client needs **Bulk and import** to submit imports and manage profiles, and **Browse** to create exports in the selected workspace. Jobs retain the requester's access boundary; check the current [security rules](/docs/integrate/security-model-for-integrators/) before sharing job IDs or implementing confirmation for another person.

To change a saved profile, read it, edit its definition, and save with its current version through the [profile operations](/docs/api/?api=management#tag/imports). Recheck it under the intended workspace's current release and preview a representative file. A profile change does not repair records loaded by an earlier job. Already submitted imports keep the resolved profile stored with that job; changing the catalogue entry is not a way to edit a waiting preview. Use the reread operation for a matching-field change; cancel and submit a new request for other profile changes.

To retire an exchange, stop its schedule, cancel any queued work or waiting previews you intend to abandon, and retain the required outcome records and output files. Delete an unused profile with its current version claim through the profile operation. This removes the saved mapping, not the records it previously loaded. Uploaded and exported job files follow [job retention](/docs/integrate/jobs/); do not use those temporary files as the only archive of a supplier exchange. Preserve original supplier files and profile definitions in the integration's own controlled storage. The instance's database and file storage are covered by [operator backup and restore](/docs/run/backup-and-restore/).
