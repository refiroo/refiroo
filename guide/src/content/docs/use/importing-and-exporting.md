---
title: Importing and exporting
description: Choose a file for editing or exchange, preview its changes and load it safely.
reader: steward
---

Export data to read or edit outside refiroo, then import it with a preview. Export needs
**Browse** in the workspace. Import needs **Bulk and import** and permission to write the
target record types in Live or a change set. The deployment must allow new jobs. Publications
and retired workspaces can be exported but cannot receive an import.

Use [Export records](/docs/guide/use/export-records/),
[Edit in Excel and import back](/docs/guide/use/edit-in-excel-and-import-back/), or
[Import a file](/docs/guide/use/import-a-file/).

## What an export contains

Open **Workspace actions** and choose **Export**. From a collection it carries that type,
context, filters, parent scope and displayed columns. **Text search is not included.** Check
the scope rather than assuming that only the searched names are exported. From another page,
choose the application's types; from **Settings › Data operations › Jobs** an export can choose
types in a workspace. **Valid on** optionally limits the export by business date. The browser's
ordinary lists have no equivalent business-date selector.

**Kind of file** offers **Technical** and, from a suitable collection, **For people**.
Technical exports offer **Excel (XLSX)**, **CSV** and **JSON Lines**. Choose **Between exported
records**, **All their relationships** or **None** for relationships. All their relationships
can refer to records outside the chosen record scope. Everything is read at one instant.
The job's file summary records its scope, counts, size and checksum. Failed or cancelled exports
have no downloadable file. Downloads remain subject to job and file retention.

## A workbook for people

**For people** makes an Excel workbook shaped by your table: visible columns in their order,
readable labels and typed cells. **Advanced: columns and sheets** changes the columns, their
order, which field a relationship column shows and which relationships get separate sheets.
Related records are exported in full, even where the browser showed only a few chips.
Record identity and versions are held in hidden columns. Keep those columns and the workbook's
saved import information when editing. Cells choosing a single record offer dropdowns from
sheets of eligible records.

Columns marked **(not imported)** are for reading. An ambiguous or overlong relationship cell
becomes a read-only summary pointing to its sheet. Several owned records for one parent also
form a summary rather than an editable single value. Edit the appropriate sheet instead.

When imported with **Profile: None**, the workbook is read as exported. An untouched workbook
changes nothing; changed names, fields and added rows are loaded as edits. A record changed by
someone else since export is refused unless you deliberately choose the overwrite option.
A main-sheet relationship list replaces that whole set; connections still chosen keep their
identity and values. A relationship sheet adds or updates connections, but omitting a row does
not remove one.

**Blank ordinary field and owned-record cells leave values unchanged.** To clear such a value,
use refiroo's field editor. **An empty cell replacing a relationship set empties that set**,
where its rules permit it. Check the preview carefully when clearing a relationship list.
A required connection still cannot be cleared.

An owned-record relationship can use **Columns per parent** to make a workbook for filling in.
Each chosen parent contributes columns for its owned record's fields. Filling an empty column
creates that record under its parent and connects it to the row's record. See
[Add a language with a workbook](/docs/guide/use/add-a-language-with-a-workbook/) for the generic
steps and an example. Excel permits at most 16,384 columns; a wider layout fails when the export
job runs. Reduce parents or fields and export again.

## Read a file through a profile

An import profile tells refiroo how sheets and columns become records, names, fields, parents
and relationships, and which values identify existing records. Choose a stored profile for a
CSV or workbook that was not exported by refiroo. Profile setup belongs to
[Workbook onboarding](/docs/model/workbook-onboarding/); a steward can
[load its next version](/docs/guide/use/load-the-next-version-of-a-workbook/).

A missing or ambiguous related name is refused. Parents can be resolved from existing records
or the same file, and are loaded before children. Repeated keys with compatible filled cells,
in one sheet or several sheets of the file, combine into one record; conflicting filled values refuse all contributing rows. Blank cells
do not conflict with another row's supplied value. A profile without a stable key warns that
later uploads may create new records instead of finding earlier ones.

A profile can keep or delete records missing from the next file. Deletion of missing records
is allowed only in a change set, so review those removals before publication. A profile must
still fit the workspace's model; ask its model administrator to fix named problems.

## Preview and load

The import always previews first in the browser. Choose whether to **Load the rows that can
load** or **Load nothing unless every row loads**, and whether found records may be updated.
The preview reports creations, updates, unchanged and refused rows. Its column report shows
empty, converted, mapped and refused cells, and found, missing or ambiguous record matches.
A large file may be sampled; the page says how much was tried. Loading checks the whole file
against current data, so the final result can differ.

**Load the file** confirms; **Cancel import** ends the preview without writes. Expired previews
cannot load. Correct refused rows in the original file and resend the whole file: already
loaded rows should preview unchanged when their data and matching choices are unchanged.
Refused rows are listed on the job page; there is no download of just the refused rows.

For an export from another workspace, **Load them as this workspace's own** creates separate
records with stable identities derived for the destination. Parents and relationships stay
together; resending the file finds those copies. They do not stay linked to the originals.
**Refuse them** instead reports the source workspace on the refused rows.

Read [Jobs](/docs/use/jobs/) for progress, cancellation, access and retention.

## Read the preview's evidence

**The preview** counts **Created**, **Updated**, **Unchanged**, **Deleted**, **Refused items**
and **Rows**. **A sample** means only part of the file was tried. In **Rows in the preview**,
choose **All rows**, **Refused** or **Not loaded**. Read **Outcome** and **Why, or what it does**
for the individual rows; a refused cell gives its column and reason.

**How the file was read** explains each sheet and column:

| Count | What to check |
| --- | --- |
| Bound to | The field, name, parent or relationship receiving this column. |
| Cells and Empty | Whether the expected rows supplied anything to read. |
| Read and Value-mapped | Values successfully read or translated through the profile's value choices. |
| Refused | Cells that could not be used; correct their stated cause before loading. |
| Found, Not found and Ambiguous | Whether a name or key identified exactly one existing record. |

A **Check** marker calls attention to a column. The **Read as exported** summary identifies a
workbook using its saved import information. **This import** records the chosen file, profile
and load policy. After confirmation, **The result** reports **Applied items**, **Refused items**
and **Not loaded**. Read that result even when the preview looked right.

![Import preview with one refused Height cell, 115 unchanged rows and per-column reading counts](/docs/screens/import-preview-columns.png)

*Above: one row in the reference Stops workbook is refused because Height (m) contains
“not a number”. The column counts show 115 height values read and one refused; the preview
has written nothing.*

## Profiles and recurring keys

In **Settings › Data operations › Import profiles**, **Valid** means the profile fits its
model; **Needs a fix** means a named problem must be resolved. Neither guarantees that every
row in the next file is valid. **Not loaded yet** means no retained last load is shown.
**Load more profiles** continues the catalogue. If there are no profiles, ask a model
administrator to prepare one through [Workbook onboarding](/docs/model/workbook-onboarding/).

**Last load** offers **Open the change set review** while its work is proposed, or
**Open the load's job** for the retained operation. A load can be missing here because it has
passed retention. Uploading the next file checks it without changing records. Accepting a
column rename or ignoring a new column changes the profile used for subsequent checks; review
those decisions with its owner. See [Load the next version of a workbook](/docs/guide/use/load-the-next-version-of-a-workbook/).

A matching key may combine several columns. Every component must be present and identify at
most one stored record. Fill incomplete keys or ask the profile owner to resolve ambiguous
combinations. Changing only a display name need not create a new record when a stable key still
finds the original.

An export uses one consistent reading of the data. If its worker restarts after a crash, it
starts the export again rather than appending new data to half of an old file. Follow the job
until it has a completed file. Home itself has no Import or Export action; open an application
or use Jobs. A record's History is a list of changes, not an earlier-state viewer, and offers
no restore or undo. See [History](/docs/use/history/).

## What the next file can change

A profile belongs to one model. Use it in a workspace running that model; a different model
needs its own suitable profile. A file carrying records from another workspace with a
different model cannot load them as counterparts: those rows are refused while other valid
rows can load under the chosen load policy.

The next-version check can recognise a renamed header when its column stays in the same
position and holds the same values. **Accept** saves that rename; **Ignore** saves the decision
not to load a new column. Each decision checks the file again before loading.

For a lookup allowing one related record, a changed value in the next file switches the
connection to the newly named record. Missing records are kept unless the profile says to
delete them. That deletion also removes their connections, but refuses a record that others
depend on. Review the refused items and the change set before publishing.

## File refusals and completion notices

A preview can refuse all rows participating in a parent cycle, rather than loading either
record into an invalid hierarchy. If the file cannot be read or does not fit the profile,
loading changes nothing. Correct the file or ask the profile owner to repair its mapping.

The tab that starts an import reports when its preview is ready and when loading finishes,
unless you already have that job open. A collection reloads after an import started in this
tab loads into it. For exports, the completion notice offers **Download** and the job page;
a failed or cancelled export instead reports that state. Keep the tab open for these notices,
or return to **Jobs** to inspect the result later.

A stored upload used by an import profile is visible to its uploader and to people allowed
to import in its workspace. Treat the file as shared with those workers when choosing what
to upload. Losing a write permission can stop a job at its next step; review its applied counts
before asking an authorised colleague to continue the work.

## Let the assistant prepare the import

When the assistant is enabled and you have the required access, **Import…** in the workspace
menu first opens **Load a workbook**. Give it one XLSX or CSV file, instructions, or both.
It proposes the model and load for review rather than publishing records. **Import without
the assistant…** opens the ordinary manual import. See
[Loading with the assistant](/docs/use/loading-with-the-assistant/) and
[Load a workbook with the assistant](/docs/guide/use/load-a-workbook-with-the-assistant/).
The whole file and your words go to Claude Code, turns can incur costs, and task files are
retained; [AI and your data](/docs/use/ai-and-your-data/) explains those rules.

## Remove an uploaded file or an import profile

Open **Settings › Data operations › Import profiles** and select the profile. People with
**Bulk and import** are offered the deletion buttons; without that access the buttons are absent.
Deleting either item does not undo a load or remove records already loaded into a workspace.

- **Delete the file…** asks **Delete <file name>?**. **Delete the file** removes that upload,
  its stored cells and the analysis of its sheets and columns. A check still reading it is
  asked to stop. The import profile stays. Upload the file again before checking or loading it.
- **Delete the profile…** asks **Delete the profile <profile name>?**. **Delete the profile**
  removes the saved instructions for reading the workbook and returns you to the profile list.
  Loading the workbook again needs a new profile saved by installing a model draft that holds it;
  ask a model administrator to prepare this through [Workbook onboarding](/docs/model/workbook-onboarding/).

Choose **Cancel** in either confirmation to keep the item. A refusal stays in the confirmation
with its reason. If someone changed the file or profile since you opened it, cancel, reload the
page and inspect the latest version before trying again. There is no undo button for either
deletion. Keep the original workbook outside refiroo if you need to upload it later.

![Import profile showing separate buttons to delete its uploaded file and the profile](/docs/screens/use-import-profile-delete-actions.png)

## Default file and preview limits

An import normally accepts a file of up to 200 MiB. Its preview tries at most 10,000 items;
**Load nothing unless every row loads** normally allows at most 10,000 items. Your operator
can change these limits. Read **Limits** on Jobs and the limit reported by the import form.
If a file exceeds the limit, split or reduce it, or agree a suitable limit with the operator.
If splitting a recurring workbook whose profile deletes missing records, ask its owner first:
each part could otherwise treat records in the other parts as missing.

Jobs and their downloadable files are normally retained for seven days. Download an export
before its **Kept until** time. A retained import profile can outlive its last load's job;
**Last load** is not an archive of every workbook loaded through it.

![Confirmation to remove an import profile while retaining previously loaded records](/docs/screens/use-import-profile-delete-confirm.png)
