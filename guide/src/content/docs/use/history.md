---
title: History
description: Find what changed on a record, across a workspace or in one person’s work.
reader: steward
---

Use history to find who changed data and when. Start from a record for one item's past,
a workspace for activity across records, or Home for your own work.
Follow [See who changed what](/docs/guide/use/see-who-changed-what/) for the steps.

## A record's History

On a record page, **History** shows the newest entries first. **All**, **Values**,
**Relationships** and **Moves** select kinds of event. **By** narrows the entries to one person;
**Anyone** removes that restriction. Expand an entry with its arrow to see recorded details,
including previous values where available.

![A record's History with event kinds, author and time](/docs/screens/use-history-stop-changed.png)

*Above: Thusis Süd records the Abbreviation change and the later update applied by publication.
The details panel shows the current abbreviation, THSD.*

Creation, field changes, relationship changes and moves are different events. A successful Live
save appears in history; a refused save is not a saved correction. Work prepared in a change set
and work applied by publication have different contexts. Read the cause alongside the person
and time rather than assuming two lines mean two direct live edits.

History names the person or client responsible, using their current name. Earlier events recorded
before sign-in was recorded read **Before sign-in**. Renaming a person does not mean another person performed
the old action. Read access is limited to workspaces you may browse.

## Activity across a workspace

Where your access opens workspace management, choose **Settings**, **Workspaces**, the workspace,
then **Activity**. Its **What** choices are **Everything**, **Records**, **Relationships**,
**Change sets** and **Publications**. Entries identify the action, person and time, and can also
name its change set or publication context.

![Workspace Activity with kind filters and changes across records](/docs/screens/use-history-activity.png)

*Above: Graubünden's Activity shows the creation and validation of the correction change set,
the record update and Publication 1, newest first.*

## A person's changes

On [Home](/docs/use/home/), **Your recent changes** gives a short list. **See all your changes**
opens **Your changes**. Choose **Workspace**, **What** and **Period** to narrow it. A person's
linked name can also lead to their changes, within the workspaces you may read.

![Your changes filtered by workspace with What and Period choices](/docs/screens/use-history-changes.png)

*Above: Guide Admin's changes in Graubünden include the published correction and earlier work.*

These lists help locate an action; they do not undo it. To correct current data, follow
[Correct a record](/docs/guide/use/correct-a-record/). To read the saved result of a publish,
[browse a publication](/docs/guide/use/browse-a-publication/).

## Explaining a period

Where AI is configured and you hold Use AI proposals, **What changed** offers **Explain this period**
on a workspace's Activity or a record's History. Choose the period and read what is sent before
requesting an explanation. Nothing is sent until you choose that action. The explanation covers
live changes, with links to the facts behind its counts; open change-set edits are not counted
as live changes. AI wording can be wrong, so inspect those facts. An empty period sends nothing;
if the explanation fails, the counted facts can still be read.

If an ordinary history read fails, retry it. If no entries match, remove the person, kind or
period filters. A filtered empty list does not prove that the record has never changed.

## Reading more and the limits of the list

History groups entries under day headings. It starts with the ten newest; **Load older history** reads
20 more and **Show fewer** shortens it again. Jobs are named as the cause of their changes;
changes applied by publication name that publication. A system's author name is marked **client**.
Where an earlier value was not recorded, the expanded entry says so rather than reconstructing it.

The person's **Changes** page helps find actions across workspaces. It shows no field values
and cannot be exported; open a record's History for values. It leaves out model-to-model mapping
operations. Older changes without a workspace are visible only to someone who reads every
workspace. Entries recorded before named sign-in say **Before sign-in**. Model-administration
entries also require Model authoring access.

## Empty results and continuing the list

**No history recorded yet.** means there are no retained record events. **No change matches.**
means the filters found none: remove **By** or the event-kind filter before concluding the
record never changed. **Show all history** clears a narrowed history. **Loading history…**
is still a pending read.

The person's Changes list groups actions by day and reads across workspaces you may browse.
**Load more** reads the next entries. **No change matches these filters.** calls for loosening
the filters; **You have not changed anything in the workspaces you can read yet.** describes
an empty personal list. A different person's page can be headed **Changes by …**. These activity
lists help locate changes without exposing the record's full before/after values.
