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

If a history read fails, retry it. If no entries match, remove the person, kind or
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

## Authors, causes and destinations

Deactivated people and clients remain named using their current names. Changes made by refiroo
itself say **the engine**. For a job, the author is the person or client who requested it;
for publication changes, it is the person who published. A relationship entry identifies
the record at the other end. Publication and type-change entries may keep only the changed
values, so their earlier values can be unavailable.

The person's **Changes** page offers the last 24 hours, 7 days or 30 days and includes live
and change-set work, publications and permitted model work. Titles open the affected item
while it still exists; a deleted item has no current record to open.

A change set names its creator and the people who edited it. A publication names who
published and withdrew it. A job names its requester both in the list and on its page.
These names describe different responsibilities; the person publishing need not have prepared
every change.
