---
title: Edit in Excel and import back
description: Export a readable workbook and preview only the changes you intend to load.
reader: steward
---

Use a workbook for people when you want to edit a collection outside refiroo. Read
[Importing and exporting](/docs/use/importing-and-exporting/#a-workbook-for-people) before clearing cells.

1. In the collection, open **Workspace actions › Export**. Choose **For people**, check its
   scope and **Advanced: columns and sheets**, then **Start export**. Download the completed file.
2. Open it in Excel. Keep its hidden identity and version columns and saved import information.
   Edit the names or ordinary values you intend to change; leave **(not imported)** columns
   alone. Read summary cells on their referenced sheet.
3. Review relationship lists especially carefully: the edited list replaces the whole set.
   An empty replacement cell clears it if allowed. Blank ordinary field or owned-record cells
   leave values unchanged. Removing a relationship-sheet row does not delete the connection.
4. Back in the intended Live or change-set context, choose **Workspace actions › Import** and
   select the workbook. Leave **Profile** at **None** so refiroo reads its saved layout.
5. Keep **Only if unchanged since the export** unless you have reviewed a deliberate overwrite.
   Choose the refusal policy and **Preview**. The job page identifies it as **Read as exported …**.
6. Review creations, updates, unchanged rows and refusals. An untouched workbook should change
   nothing. With **Only if unchanged since the export**, a record edited by another person
   since export is refused. Reconcile those rows
   with the current records before retrying, or export a fresh workbook.
   **Update them anyway** deliberately replaces values from the file even where a record
   or relationship changed since export. Review the current data first: this choice ignores
   the workbook’s saved version checks.
7. Choose **Load the file** when the preview is right. Inspect the final results; execution
   checks current data again. Correct refused rows in the file and resend it to preview again.

In a change set this prepares proposals for review and publication; it does not change Live.
Use **Cancel import** if the preview includes unexpected changes.
