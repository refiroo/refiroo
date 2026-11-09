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
   choose another destination, open **Settings › Data operations › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**. The chooser accepts Excel workbooks, CSV and supported technical export
   files. Choose the stored **Profile** for an ordinary workbook or CSV, or **None** for a
   file exported by refiroo. Read any profile problems before continuing.
3. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.

A malformed file or invalid profile changes nothing. Ask a model administrator about profile
rules you cannot fix. A profile deleting records absent from the file must load into a change
set. An expired preview needs a new import preview, rather than another confirmation attempt.
