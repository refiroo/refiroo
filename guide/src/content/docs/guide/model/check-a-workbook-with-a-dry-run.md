---
title: Check a workbook with a dry run
description: Read each source’s predicted changes and inspect refused rows before loading.
reader: model-admin
---

A dry run reads every mapped row without writing records. Model validity and row acceptance
are separate checks. Open a workbook draft with **Model authoring** and see
[Issues and dry runs](/docs/model/issues-and-dry-run/) for the different results.

1. Expand **Issues, history and dry run**. Resolve blocking **Issues** in the model or profile
   first, then choose **Dry run**.
2. Check the draft version and comparison workspace. Wait for **Checking…** to finish.
   **Checked** is a completed check; **Failed** or **Stopped** is not. Read any failure and
   correct its cause before retrying or making the next mapping change.
3. Open each source tab. Read records created or updated, values, relationships, related
   records created and refused rows. These are different units, so do not add them as a row total.
4. Select a figure to inspect the rows behind it. Open the refused-row figure to read sheet,
   row number and reason. Correct an unresolved reference, wrong type or missing required value
   at its source or in the mapping. A valid draft can still refuse source rows.
5. After editing, wait for the new check. **was** compares with the previous result; it is not
   a count from an actual import. Use the result for the current draft version.
6. Account for every source and any remaining refusal before
   [loading into a change set](/docs/guide/model/load-a-workbook-into-a-change-set/).

![Dry run showing per-source predicted records, values and relationships](/docs/screens/use-wb-dry-run.png)

![Refused workbook rows with their sheet positions and reasons](/docs/screens/use-wb-dry-refused.png)

The eventual load can meet newer records or different workspace data. Review its actual result
and change set too; a dry run is neither an import nor a publication.
