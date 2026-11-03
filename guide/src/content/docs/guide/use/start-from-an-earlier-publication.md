---
title: Start from an earlier publication
description: Use a retained snapshot as a proposal’s starting point without restoring it over Live.
reader: steward
---

Start a proposal from known published data. This is not a rollback. Read
[Publications](/docs/use/publications/) and [Change sets](/docs/use/change-sets/).

1. Open **Publications** in the intended workspace. Find the snapshot by its number, date
   and model version; open it first if you need to verify its content.
2. On its row, open **More actions** and choose **Start a change set from this publication**.
   You need Work in change sets; Browse alone cannot create it.
3. Give the change set a name and confirm the creation form. Open it and check that its
   source names the intended publication and its model release.
4. Make the changes you intend. **Review changes** compares them with this source snapshot.
   It does not describe all differences between that old snapshot and today's Live.
5. Validate and publish or submit as usual. Only changes made in this change set are merged
   into current Live. Newer untouched Live work survives; conflicts prevent publication.

If the proposal's release differs from the workspace's, coordinate with a model administrator
and follow [Prepare under the next model version](/docs/guide/use/prepare-under-the-next-model-version/).
Withdrawing a publication or starting from it never restores its records over Live.
