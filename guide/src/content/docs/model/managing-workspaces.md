---
title: Managing workspaces
description: Create and manage independent datasets and choose which model each runs.
reader: model-admin
---

Manage datasets under **Settings › Workspaces**. You need **Workspace administration** for
workspace changes; reading data, changing models and granting access need their own permissions.
For everyday navigation, see [Workspaces](/docs/use/workspaces/).

## Find a workspace


Where your access permits it, **Manage workspaces** or **Settings**, **Workspaces** opens the
workspace list. It shows the model and release of each workspace and marks the default.

![Workspace management listing each workspace and its model release](/docs/screens/use-workspaces-manage.png)

*Above: Graubünden and Default run different models. This capture only views the list.*

Open a workspace row to inspect **Overview**, **Access**, **Approval** and **Activity**.
**Open workspace** returns to its data; **Activity** shows [history across records](/docs/use/history/).
The other actions require administrative permissions: **New workspace**, **Edit model**,
**Copy or move data…**, **Rename…** and **Retire…** change the workspace or its configuration.
Opening the page does not perform them.

![A workspace detail with its actions and Overview, Access, Approval and Activity tabs](/docs/screens/use-workspaces-detail.png)

*Above: Graubünden's Overview shows its key, model, applications and default status.*

A retired workspace remains readable but refuses changes. Open it through workspace management,
rather than the active workspace selector. The default workspace cannot be retired or deleted;
an administrator must make another workspace the default first.

## Create or rename a workspace

1. Open **Settings › Workspaces**. Search the list before creating another dataset. Active
   workspaces appear first, then retired ones.
2. Choose **New workspace**. Complete its name and key. The key forms its address; choose it
   carefully. Use the default workspace's model, or choose another usable installed release.
3. Confirm creation and check the new workspace's **Overview**, model and applications. It has
   its own data; creation copies no records from the default workspace. Read any refusal before
   retrying. Cancel leaves the list unchanged.
4. To change its displayed name later, choose **Rename…**, enter the new name and save.
   Renaming does not change its key or create a new dataset.

## Retire, reactivate, make default or delete

- **Retire…** asks for confirmation. It removes the workspace from the active selector and
  refuses writes, keeping data, change sets, publications and history readable. Open it from
  this list later. **Reactivate** makes it available for work again.
- **Set as default** chooses the default destination. It neither copies data nor changes the
  models of other workspaces. Check the Default mark after the action.
- **Delete…** is only for an empty, never-published workspace with no change sets or webhook
  subscriptions. A workspace ever published can only be retired, even after its data is removed.
  The screen explains what prevents deletion. Confirm only after checking the name and key.

The default workspace cannot be retired or deleted. Make another active workspace the default
first. If another administrator changed the workspace or default while the page was open, review
the refreshed state and repeat only the action still needed.

## Tabs and model changes

**Overview** shows the workspace's facts and its model's applications; each application opens
in this workspace. **Access** lists grants for people, groups and clients. **Approval** holds
[publication policies](/docs/administer/approval-policies/). **Activity** lists changes newest
first, grouped by day, with filters; see [History](/docs/use/history/). Only tabs your access allows
are shown.

**Edit model** opens the saved draft for the workspace, reopening it on later visits. It needs
Model authoring, Model release and Browse, and an active workspace. Check **Applies to**, then
use **Apply to this workspace…** after editing. The confirmation lists model changes, data
compatibility, open change sets left behind and other workspaces left unchanged. If records must
move, review the separate preview before confirming. Follow
[Install and activate a release](/docs/guide/model/install-and-activate-a-release/).
**Copy or move data…** starts [a copy or move](/docs/guide/model/move-records-to-another-model/).

Workspace administration can also be switched off by the deployment. The page then stays read
only and names the setting; ask the operator to enable it if administration is needed.

## Workspace tasks

[Create a workspace](/docs/guide/model/create-a-workspace/),
[Edit its model](/docs/guide/model/edit-a-workspaces-model/),
[Make it the default](/docs/guide/model/make-a-workspace-the-default/) and
[Retire or delete it](/docs/guide/model/retire-or-delete-a-workspace/) give the steps.
To choose an installed release, use [Change a workspace's model](/docs/guide/model/change-a-workspaces-model/).

**Cannot be opened** on a workspace whose model language is unsupported needs the offered
model-language repair or operator help; see [Model language versions](/docs/model/model-language-versions/). A missing application
bookmark can instead mean **Not in this model**: open a collection declared by this workspace.
**Rename…** changes the displayed name, with the permanent key retained. A stale save asks you
to review newer state; it does not silently overwrite another administrator's edit.

## Permanent keys and changes made at the same time

A workspace key has at most 160 characters, using lowercase letters and digits separated by
single hyphens. Leading and trailing spaces are removed. Its key cannot be changed after
creation, and a retired workspace still reserves its key. Change **Name** to rename the dataset.

Retirement waits for a write already in progress to finish. Once retirement succeeds, later
live and change-set writes are refused. If two administrators change the default from the same
starting state, one succeeds and the other must refresh and review the new default.
