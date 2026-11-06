---
title: Raise a model language version
description: Review and reopen a workspace whose model uses an older supported conversion path.
reader: model-admin
---

Use this task when a workspace says **Cannot be opened** because its model language is older
than this refiroo version reads. It changes the stored definition format, not the records.
You need permission to install models at the instance level. See
[Model language versions](/docs/model/model-language-versions/).

1. Open the affected workspace and read why it cannot open. A model written by a newer refiroo
   version needs that version; this repair is only offered for an older, raisable definition.
2. Under **Bring it up to date**, choose **Review the change…**. If the page says the model
   cannot be brought up to date automatically, ask the operator or a specialist model author.
3. Wait for the preview, then inspect **Schema language**, **Consumer APIs rewritten**,
   **Workspaces that return** and **Records, change sets, publications: unchanged**.
   Review every named workspace because they share this stored release.
4. Choose **Raise and reopen** only after reviewing that scope, or **Cancel** to leave it.
   This special recovery edits the stored release in place. It is an exception to ordinary
   immutable releases, available before the first stable release.
5. If **The change could not be made** appears, read the diagnostic. An invalid result or one
   equal to another release is refused. **Try again** rereads a failed preview. If the release
   changed after review, inspect the new preview before confirming.
6. After success, reopen the workspace and check its applications. Its records, history, change
   sets and publications stay as they were. This did not migrate or publish its data.

![Model language recovery preview with affected workspaces and unchanged records, change sets and publications](/docs/screens/model-language-raise-review.png)

If no workspace is available, the operator may need the offline procedure in
[Model releases and rollback](/docs/run/model-releases-and-rollback/).
