---
title: Import a file
description: Choose a file, review its preview and load the rows you approve.
reader: steward
---

Load into Live or a change set after checking exactly what the file means. See
[Importing and exporting](/docs/use/importing-and-exporting/) for file and profile rules.

If **Load a workbook** opens because the assistant is enabled, choose **Import without the
assistant…** to reach the manual import form used below. That manual path does not send the
file to an AI assistant.

1. Open the intended workspace and collection. Choose **Workspace actions › Import**. To
   choose another destination, open **Settings › This instance › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**, or drop the file onto that field. The chooser accepts Excel workbooks, CSV and supported technical export
   files. After choosing the file, check **Profile**: refiroo selects it when exactly one valid profile fits. You may choose **None** or another fitting profile. A JSON Lines file takes none; CSV offers profiles with CSV settings or one source; a workbook offers any valid profile for this workspace's model. Invalid profiles and other models' profiles are omitted. Use **None** for a file exported by refiroo. Read any profile problems before continuing. For an exported CSV,
   keep the protective single quotes added to formula-like text. With **None**, import removes
   exactly one such quote from names and text fields; an unchanged export changes nothing.
   XLSX is unaffected. See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
3. Open **Options**. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report, **How the file is read** where shown, and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.

## Check how the file is read

1. In the preview, open **How the file is read** where offered. Each matrix or relationship
   column shows **Matched by**, **Values matched** and **New records go into**. For a workbook
   exported by refiroo, the file records the matching field. When a file does not record it,
   refiroo compares its values with existing records and marks its choice **Guessed**. Read
   any note about an uncertain choice; do not assume a high match count proves it is right.
2. Check each column's field against what its values mean. Where a selector is offered under
   **Matched by**, choose the intended field. This starts a new preview of the same file;
   wait for it and review its counts and refusals again. Nothing is loaded by either preview.
3. For a link matrix with value sheets, check how many rows update existing records and how
   many are new. The main columns also report values found on value sheets and new values.
   An unselected value-sheet row can still create or update a record; review it too.
4. Check **New records go into**. A proposed or rule-defined missing group says
   **will create … under …**. Confirming the load creates that group with its records.
   If there is no suitable place, follow the reason and prepare the place in the app before
   previewing again. You do not need a model change to accept a proposed group.
5. When using a stored profile, choose **Save these fields in the profile** if this reading
   should apply to later files. Saving the reading does not load the file. Review all changes
   and refused rows, then choose **Load the file** only when the preview is right.

For the workbook editing rules, see
[Edit in Excel and import back](/docs/guide/use/edit-in-excel-and-import-back/#edit-the-value-sheets-of-a-link-matrix).

A malformed file or invalid profile changes nothing. Ask a model administrator about profile
rules you cannot fix. A profile deleting records absent from the file must load into a change
set. An expired preview needs a new import preview, rather than another confirmation attempt.
