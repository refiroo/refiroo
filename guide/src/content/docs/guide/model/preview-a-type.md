---
title: Preview a type
description: Check a draft record page and table without changing live records.
reader: model-admin
---

Use preview to check a draft's appearance before applying it. You need **Model authoring**.
See [Record pages and tables](/docs/model/record-pages-and-tables/) for what preview reads.

1. Select the type in the model pane and choose **Preview**. A type listed in several applications
   is previewed in the application whose row you selected; when none is selected, in the one
   that holds the workspace's records of the type. Choose the application in the band to switch.
   If **The draft has … issues, so
   it cannot be previewed** appears, choose **Show issues**, fix the errors and return.
2. Choose **Workspace** and **Record**. The record's live values are drawn using the draft's
   definition. Check that the workspace is the one whose records you intend to inspect.
3. Use **Show an empty record** to see unfilled fields, especially for a new type. No value
   in a preview does not itself mean that the field or type is invalid.
4. Inspect **Record page** and **Table**, including long labels and records with missing optional
   values. Controls that would change data are disabled. Previewing does not save a record.
5. Choose **Edit layout** to change the draft's presentation, or **Back to definition** to
   return to the selected type. Review Issues after layout changes.

![Draft type preview over a selected live record](/docs/screens/model-type-preview.png)

Preview shows individual screens. The separate activation check decides whether all stored data
fits the release; a good-looking preview does not replace it.
