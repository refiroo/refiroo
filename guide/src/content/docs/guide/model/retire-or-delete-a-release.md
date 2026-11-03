---
title: Retire or delete a release
description: Stop offering a release for new use or remove an unused release with confirmation.
reader: model-admin
---

Open **Settings › Model**, then the model's **Releases** and the release. These lifecycle
changes need installation permission. See [Releases](/docs/model/releases/).

1. Check its version, workspace use and whether it runs the default workspace. **Retire…**
   stops new selection but keeps existing users on the release. The default workspace's release
   cannot be retired; move that workspace to another usable release first if appropriate.
2. Choose **Retire…**, read the named release and confirm. Cancel keeps it available. Check
   the **Retired** state afterwards. Workspaces and change sets already using it keep working.
3. To offer it again, choose **Bring back** and check that it is available. A model with every
   release retired and no running workspace appears under **Retired** in the model list.
4. Use **Delete…** only for a release with no remaining use or references. **Run by no workspace**
   alone does not prove it is deletable: records, publications, change sets, profiles or mappings
   can still refer to it. Read the confirmation and any refusal before proceeding.
5. Confirm deletion only when the named unused release is no longer needed. Deleting its release
   does not delete editable drafts. If refused, retain it or retire it; do not delete history to
   force a release removal.

![Release retirement confirmation](/docs/screens/release-retire-dialog.png)

If the release changed state elsewhere, reload it and review the current state before retrying.
Retirement is reversible; deletion is not the same operation.
