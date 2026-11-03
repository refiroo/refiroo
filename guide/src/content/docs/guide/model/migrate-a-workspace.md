---
title: Migrate a workspace
description: Review every converted or removed item and confirm a model switch with accepted loss.
reader: model-admin
---

Start from an activation check that says the data needs migration. You need **Model release**
in the workspace, with model administration and jobs enabled. See [Migrations](/docs/model/migrations/).

1. Choose **Preview the migration…**. Check the workspace and target release. The page says
   **Nothing has changed yet**. Wait for every record to be checked, or **Cancel the preview**.
   Leaving the page keeps the preview job running.
2. Under **What … no longer has**, review each missing type or field. Select **Became …** only
   for its genuine replacement. Type mappings retain record IDs and history. **Not kept**
   removes the type's records and relationships or the field's values. Each choice previews again.
3. Open each outcome: **Converted**, **Type changed**, **Removed** and **Must be fixed**.
   Read the item lists, including before and after values. These count items, not just records.
4. Fix every blocking item in the named workspace or change set. Required values, required
   relationships, parent placement, uniqueness and publication conflicts cannot be waived by
   accepting loss. Choose **Preview again** and review the refreshed lists.
5. If **Removed** contains items, inspect them. While **Must be fixed** contains blocking
   items, the acceptance checkbox is hidden and the migration button is disabled. Resolve
   those items first, then tick **I accept that …** to accept the listed removal.
   Choose **Cancel** to keep the current data.
6. Check the final action. **Migrate … to …** changes the workspace. **Move change set** changes
   only the named change set onto the workspace's current release. **Migrate and publish** also
   publishes the named change set and needs publication permission and any required approval.
7. Confirm only the reviewed action. If a stale notice appears, **Close** or **Preview again**;
   nothing was migrated by that refusal. Review the new result before another confirmation.
8. Read the success counts and destination. For a workspace migration, inspect its applications
   and arrange to move or discard old change sets. For a change-set move, choose **Open the
   change set** and review and validate it. For migration and publication, inspect the named publication.

![Migration preview with outcomes and choices for missing types and fields](/docs/screens/model-migration-review.png)

![Removed items in a blocked migration preview, with three items to fix and the migration button disabled](/docs/screens/model-migration-loss-confirm.png)

A failed execution leaves data and the release switch unapplied together. Read **Not migrated**
or **Not moved**, correct its cause and preview again. History retains removed content, but
migration has no automatic reverse button.
