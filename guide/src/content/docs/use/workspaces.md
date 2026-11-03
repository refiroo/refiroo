---
title: Workspaces
description: Choose the right dataset and understand its model, access and workspace management.
reader: steward
---

A **workspace** holds its own reference data, change sets and publications. Before editing,
check the workspace name and its model release. Follow [Switch workspace](/docs/guide/use/switch-workspace/)
to open another dataset.

## Each workspace runs its own model

Two workspaces can run the same model and hold different records. They can also run different
models, with different applications, types, fields and views. Changing one workspace's model
does not change another workspace's model. Switching workspaces copies and moves nothing.

[Home](/docs/use/home/) shows the workspaces you may browse, their models and releases, and their
application buttons. **Default** marks the instance's default workspace; it does not mean other
workspaces share its data. The workspace called Default need not be the default workspace.

![Home with workspace cards, model names, releases and application buttons](/docs/screens/use-home.png)

*Above: Graubünden is marked Default. The workspace named Default runs a different model.*

Within an application, **Workspace** in the sidebar names the dataset. The text beneath names its
model and release. The banner above the records identifies **Live**, a [change set](/docs/use/change-sets/)
or a [publication](/docs/use/publications/). Those are contexts within a workspace.

## Switching and access

The selector offers workspaces you may browse. **Other model** identifies a different model;
**Other release** identifies a different release of the same model. After switching, check the
applications and views again. The former view may not exist in the destination.
With only one available workspace, its name appears without a selector.

You need **Browse** access to read data, and the appropriate editing permissions to change it.
Reader can browse; Contributor can prepare changes in change sets; Data steward and Data owner
can also change Live. Custom grants can narrow writes to particular applications or record types.
See [What you can do](/docs/use/account/#what-you-can-do) for your own access.

If no workspace is offered, ask an administrator for access. A loading failure does not mean
there are no workspaces: retry the failed read first.

## Workspace administration

A retired workspace remains readable but refuses changes. Where your access permits it, open it
from **Settings › Workspaces**, rather than the active workspace selector. Creating, renaming,
retiring and deleting workspaces are described in
[Managing workspaces](/docs/model/managing-workspaces/).

## When a destination cannot open

The selector searches workspace labels; the page address keeps the workspace's key. Switching
can show a toast explaining that the destination runs another model or release.
**Not in this model** means the address names an application, collection or record type this
workspace lacks. Use the offered workspaces whose models contain it, or choose an available
application here. An unknown workspace or a release that cannot be served has its own explanation.
Read that reason and ask the operator to restore a supported release where needed; retrying a
record edit cannot make an unavailable model readable. Other workspaces can still be used.

## Refresh after the model changes

If the workspace changed release while your page was open, the message can say **… now runs ….
Nothing was saved.** or **Reload to see it.** Choose **Reload**, then review the current form
and context before editing. A stale screen must not overwrite data under a different model.

**Manage workspaces**, beside or inside the selector, opens its Settings entry where permitted.
Its **Applications · …** links open the workspace's applications. Loading the catalogue or an
individual workspace is distinct from an empty result; wait or retry the error.
Creating, renaming, setting the default, retiring, reactivating and deleting are administration
tasks. Their controls and deployment availability belong to
[Managing workspaces](/docs/model/managing-workspaces/). **Capability groups** is an operator
status panel, not a setting a steward changes to gain access.

To open retired or unreadable data, follow
[Open a retired or unavailable workspace](/docs/guide/use/open-a-retired-or-unavailable-workspace/).
To read activity across workspaces, use [History](/docs/use/history/).

A retired workspace is marked **Retired · read only**. In Settings its **Overview** shows the
model, creation and last-change facts, and **Open workspace** leads to its start page. Wait
while **Loading workspace catalogue…** or **Loading workspace…** is shown; an error is not an
empty catalogue.

A missing model element can say **No other workspace's model has it.** Choose **Go back** or
the offered workspace start page, then choose a collection present in that model. If another
workspace is offered, its **Open in …** action changes the workspace as well as the page;
check the destination before making changes.

## Actions for this workspace

![Workspace menu offering Import, Export and Edit model beside the selected workspace](/docs/screens/workspace-actions-menu.png)

*Above: the menu for Graubünden while reading the Stops collection in Network. Its actions
apply to this workspace and the data context being viewed.*


The **⋯** menu beside the workspace selector offers **Import…**, **Export…** and **Edit model**
when your permissions and the current context allow them. Export starts from what the current
page shows; check the chosen columns, filters and data context in its dialog. See
[Importing and exporting](/docs/use/importing-and-exporting/) for what the file includes.

**Edit model** opens the workspace's model draft, returning to that draft on later visits.
It changes the structure rather than an individual record. Ask a model administrator when you
need that change; see [Models](/docs/model/models/). Applying a model shows its effect before
confirmation. If records must move, the migration preview must be confirmed before they move.

The workspace's Settings page offers **Overview**, **Access**, **Approval** and **Activity**
according to your permissions. Overview links to its applications; Activity shows changes newest
first, grouped by day. Access and Approval describe who can work here and how publication is
approved. They do not grant editing rights simply because you can read the workspace.
