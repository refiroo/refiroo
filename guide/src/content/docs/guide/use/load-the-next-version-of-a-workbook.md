---
title: Load the next version of a workbook
description: Check a recurring workbook against its profile and stage its differences in a change set.
reader: steward
---

Use a saved import profile to recognise a recurring workbook. This differs from creating a
model from a new workbook; that task belongs to
[Workbook onboarding](/docs/model/workbook-onboarding/).

1. Open **Settings › Data operations › Import profiles**. Select the profile and read its
   **Last load**: file, destination, row counts and whether its change set was published.
2. If your permissions offer **Upload the next version…**, choose it and upload the newer
   workbook. Wait while it is checked. Nothing is written by this check.
3. Review new, missing and renamed columns, new values, changed names and missing records.
   Choose **Accept** on a **Renamed** row only where the proposed column really replaces the old one.
   Choose **Ignore** on a **New** row to leave that column out. Ask the profile's model administrator to
   fix ambiguous bindings or model problems; do not guess which field a column represents.
4. Check the missing-record choice. Keeping missing records leaves them; deleting them stages
   removals and is allowed only in a change set. A missing key means reliable recurring
   matching is not available: resolve it before relying on repeated uploads.
5. When the report allows loading, choose **Load into a change set…** and review the destination
   and proposed changes in its dialog. Loading creates a new change set containing differences.
6. Choose **Open the change set review** from the completed load or **Last load**. Review
   additions, corrections and removals before publishing or submitting for approval.

If the file could not be read or the profile could not be saved, correct the displayed cause
and check again. Missing controls can reflect your access; ask the responsible model
administrator. See [Importing and exporting](/docs/use/importing-and-exporting/) for row refusals.

![Import profile after a next-version check, with Accept and Ignore beside column differences, Needs a fix and disabled Load into a change set.](/docs/screens/import-profile-next-version.png)

The pictured profile still **Needs a fix**, so **Load into a change set…** is disabled. Resolve
the reported problems before loading.

In **Load … into a change set**, check the proposed name and workspace before choosing
**Load**. The steps **Open a change set** and **Load the rows** show what is happening.
The suggested name starts with **Load**, the file name and a date. If loading fails after the
change set was opened, inspect that change set and the load's job before starting again;
do not assume the first proposal disappeared.

## A profile saved by the assistant

An [assistant load](/docs/use/loading-with-the-assistant/#the-next-file-and-the-saved-profile)
can leave a saved profile. Follow the steps above to reuse it. If you start through **Import…**,
a fitting saved layout also lets refiroo prepare the file without an assistant session or AI
cost. You still review the proposal and row check. **The saved layout does not fit this file**
offers **Read it with the assistant**. That sends the file and instructions to Claude Code,
can incur costs and keeps task files; see [AI and your data](/docs/use/ai-and-your-data/).
A new sheet or changed layout needs review, not an assumption that the previous mapping fits.
