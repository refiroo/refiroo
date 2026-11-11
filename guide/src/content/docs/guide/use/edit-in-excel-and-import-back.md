---
title: Edit in Excel and import back
description: Export a readable workbook and preview only the changes you intend to load.
reader: steward
---

Use an Excel (XLSX) workbook when you want to edit a view or a collection outside refiroo. Read
[Importing and exporting](/docs/use/importing-and-exporting/#a-workbook-for-people) before clearing cells.

If **Load a workbook** opens because the assistant is enabled, choose **Import without the
assistant…** to reach the manual import form used below. That manual path does not send the
file to an AI assistant.

1. In the collection, open **Workspace actions › Export**. Keep **What** on **This view**
   to take its search, supported filters and layout, or select the type, application or workspace.
   Choose **For editing in a spreadsheet**. For a link matrix, choose **What each cell lists**:
   **Name** or a text field identifying its records. For a table, check **Advanced: columns
   and sheets**. Choose **Start export** and download the completed file.
2. Open it in Excel. Read the second sheet, **About this export**, for the file’s source and
   load-back rules. Keep its hidden identity and version columns and saved import information.
   Edit the names or ordinary values you intend to change; leave **(not imported)** columns
   alone. Read summary cells on their referenced sheet.
3. Follow the rules for the layout you exported, below. In an ordinary table workbook,
   review relationship lists carefully: the edited list replaces the whole set.
   An empty replacement cell clears it if allowed. In a matrix workbook, clearing a cell
   changes nothing. Blank ordinary field or owned-record cells
   leave values unchanged. Removing a relationship-sheet row does not delete the connection.
4. Back in the intended Live or change-set context, choose **Workspace actions › Import** and
   select the workbook. Leave **Profile** at **None** so refiroo reads its saved layout.
5. Keep **Only if unchanged since the export** unless you have reviewed a deliberate overwrite.
   **Update them anyway** deliberately replaces values from the file even where a record
   or relationship changed since export. Review the current data first: this choice ignores
   the workbook’s saved version checks.
   Choose the refusal policy and **Preview**. The job page identifies it as **Read as exported …**.
6. Review **How the file is read**: the field each column is matched by, the values matched,
   value-sheet counts and where new records go. Change **Matched by** where needed; this runs
   the preview again without loading records. See
   [Check how the file is read](/docs/guide/use/import-a-file/#check-how-the-file-is-read).
   Review creations, updates, unchanged rows and refusals. An untouched workbook should change
   nothing. With **Only if unchanged since the export**, a record edited by another person
   since export is refused. Reconcile those rows
   with the current records before retrying, or export a fresh workbook.
7. Choose **Load the file** when the preview is right. Inspect the final results; execution
   checks current data again. Correct refused rows in the file and resend it to preview again.

In a change set this prepares proposals for review and publication; it does not change Live.
Use **Cancel import** if the preview includes unexpected changes.

## Edit a matrix workbook

The main matrix sheet loads only its cells. Row names and identifying fields help you find
the right row; editing them here does not change those records. Value sheets, where present,
load their records separately as described below.

- In a matrix showing record fields, edit the intended field under the intended column.
  Filling an empty cell creates a record only when the view permits creation. The preview
  shows where it goes, including a group that **will be created**. If no suitable place can
  be found, the refusal names the column: choose or prepare a group by creating the first
  cell in the app, then preview the file again. There is no value sheet for this layout.
- A cell holding several records is shown joined and is not loaded back in this field layout.
  Open the cell in refiroo to edit the individual records.
- In a matrix showing links, choose a record from the cell's dropdown. A non-empty list
  replaces the links within that row and column: records added are linked, records left out
  are unlinked. Other columns are unaffected. A value found neither in that column's value
  sheet nor in existing records creates a record only if the view also permits creation. It supplies the name and, when different,
  the selected text field; other required fields still need values. Otherwise choose an
  existing record. Names containing a semicolon appear with a comma instead; keep that form
  when editing.
- An empty or cleared matrix cell changes nothing. To remove every value or every link in a
  cell, use refiroo.

### Edit the value sheets of a link matrix

1. Open **Values ·** followed by the column name. Each row holds a record's name and fields,
   its group for reading, and hidden identity and version columns. Keep those hidden columns.
   Fields marked **(not imported)** are for reading.
2. Where the view permits editing or creation, edit existing records on that sheet. The hidden
   identity updates the same record, even if you change its name. Its other connections see
   those record changes too. With only Link existing and Unlink enabled, value sheets are
   for reading and their edits do not load.
3. Where the view permits creation, add a row without an identity for a new record and fill
   its required fields. The group column does not choose where it goes: check the import
   preview. A row not selected in any main-sheet cell is still created or updated.
4. In a main-sheet cell, use the chosen field's value from the value sheet. If you rename a
   record there, its old main-sheet value still identifies it unless another value-sheet row
   now uses that value. The same new value in both sheets identifies one new record. Two
   records with the same chosen value make the reference ambiguous; correct the values or
   the selected matching field in the preview.
5. Preview the workbook in refiroo. A spreadsheet cannot synchronise the main sheet's text
   and value-sheet records itself; import resolves them together. Review both value-sheet
   counts and main-sheet connections before choosing **Load the file**.

For example, a translation matrix workbook can fill missing names under language columns.
A mapping matrix workbook can link an existing code instead. Both create connections; reuse
keeps the existing record's identity. In a change set, connected systems see the accepted
changes after publication, according to what they are allowed to read.

## Edit other view workbooks

A relationships table exported as rows lets you edit connection values or add a row connecting
two named records. Removing a row does not delete its connection. In its grid layout, **Linked**
is Yes or No: Yes can add a missing connection, and No does not remove an existing one.
A table column showing a relationship that owns its records is for reading; edit the owned
records on their own sheet or in the app. Follow the file's **About this export** instructions.

A tree or a wider type selection has one sheet per type, with parents identified by name.
Keep the hidden columns where names alone would be ambiguous. A mapping grid uses a
relationship column for the target. See
[Workbook layouts](/docs/use/importing-and-exporting/#workbook-layouts) for the differences.
