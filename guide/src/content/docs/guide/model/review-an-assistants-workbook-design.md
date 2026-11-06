---
title: Review the assistant's workbook design
description: Check the proposed types, source coverage and record changes before accepting an assistant's load.
reader: model-admin
---

Use this task when a workbook needs a new or extended model. The assistant proposes how its
sheets, columns and records fit the workspace. You review that design before anything is
installed or loaded. For the manual editor route, use
[Start a draft from a workbook](/docs/guide/model/start-a-draft-from-a-workbook/).

You need **Use AI proposals**, **Bulk and import** and **Work in change sets** in the workspace.
Model changes also need **Model authoring**, **Model release** in the workspace and permission
to install model releases at instance level. The assistant and job creation must be enabled.

The whole file, your words and the workspace's model go to Claude Code. It reads workspace
records as needed. Assistant turns may incur charges; tasks and files normally remain for
90 days, and session files and transcripts remain while the task can continue. See
[About AI in refiroo](/docs/run/ai/) for the full account of permissions, costs, retention
and data leaving the instance.

## Give the file and its purpose

1. Open the intended workspace and its **⋯** menu beside the workspace selector. Choose
   **Import**. With the assistant enabled, **Load a workbook** opens first.
2. Choose an XLSX or CSV **Workbook**. Check **Into** names the intended workspace.
3. In **Tell the assistant about this file (optional)**, explain whether this updates existing
   records or adds something new. Say which column identifies a record and how new types
   should relate to the existing ones, if you know. A stable key matters more than a row number.
   A list of records not yet held needs a key too; otherwise a later load can create them again.
4. Read what is sent, then choose **Read the workbook**. **Import without the assistant…**
   uses the manual import instead. **Cancel** sends nothing.
5. Wait on the task page. The bar below the top bar shows the current stage and next action.
   It follows you into the model editor and change set. **Stop** ends the current turn;
   it does not discard the task.

*Example: a file of stop names in several languages may extend the existing stop model with
related name records. Check that those names attach to the existing stops and that each
language column is accounted for.*

## Review the model before accepting

1. Read **The assistant’s proposal**, including each type's fields, relationships and record
   counts. The assistant can reuse the current model, extend it or propose a new one. Do not
   assume each sheet should become a separate type.
2. Read **Checks**, especially **Needs attention**. These can identify records already held
   that should be reused, columns that group rows, translations left out, a relationship not
   visible from its other end, and filled cells no source reads. A warning about new records
   beside existing records can mean an intended update failed to find its records.
3. Read **Columns left out** and the questions with their assumed answers. Check every
   intentional omission. Conflicting workbook names or values are not automatically errors
   to normalise: explain whether they are intended.
4. Open **Show the model change**. Choose **Open in the model editor** to inspect the draft's
   types and source mappings, or edit them. The draft belongs to this task; a second task
   cannot write it while this task holds it. **Close** in the editor returns to the task.
5. Answer the questions or use **Tell the assistant what to change** under **Correct the model**.
   The same session revises the design and rereads your editor changes. Check the new proposal
   and its row counts again.

![Workbook proposal with type counts, the row check and an expanded table of model changes](/docs/screens/model-assistant-workbook-proposal.png)

*Above: the reference workbook proposal adds types and relationships, adds Step-free access
and Remark to Stop, and makes FSO number and System key optional. The expanded table shows
these changes.*

A wide sheet with repeated groups of columns may need rows arranged differently for loading.
The assistant can prepare a working copy in the shape its import needs. Review the resulting
fields and record counts: one source row need not mean one output record. This does not edit
your original workbook.

## Check the records and accept

1. Review **The check of every row**. Distinguish new, changed, unchanged, refused and skipped
   rows. A row skipped for an empty key is not a successfully loaded record. Inspect the sheet,
   row examples and reasons for refusals; correct a mapping or tell the assistant what is wrong.
2. If the page says **The check from before the draft's last change**, it does not cover the
   current draft. Have the assistant continue and check again before loading. The engine
   refuses a load based on a stale check.
3. Verify that each source's key finds the same records in next month's file. The assistant can
   use several columns together when one is insufficient. Check that blank key components,
   duplicate combinations or an unsuitable name do not turn updates into new records.
4. Choose **Accept the model** when the design and treatment of the rows are right. Before
   acceptance, nothing is installed or loaded. For an ordinary workbook design, acceptance
   lets the session install the release without activating it and prepare a change set.
   The records are not live until publication. Check which release the workspace runs before
   publishing; activate the required release through the normal release checks. A whole-type or partial reshape instead follows
   [the model-move steps](/docs/guide/model/change-a-model-with-the-assistant/).
5. On the loaded page, read the actual counts and what was not loaded. Choose
   **Review the change set**, inspect its changes, and submit for approval and publish under
   the workspace's rules. The assistant does not approve or publish.

If the engine cannot apply the proposal, its reason appears on the page. Tell the assistant
what to change rather than accepting an unusable design. A failed turn can **Try again as it was**;
a stopped one can **Go on as it was**. If a required permission is lost, the page names what
is needed and offers a link to copy for the person who can load.

## Keep the layout, or correct a load

The loaded page says when a reusable import profile was saved and offers **Open the profile**.
A suitable profile lets the next file of the same layout load without the assistant or AI cost.
The engine can also recognise an already saved layout before starting a session. Its load
confirmation can install and activate a changed model before importing; review that confirmation
even though this path makes no assistant call. Sheets left
out by the earlier profile may stay left out; a new sheet needs another assistant reading.

A load made only through record changes, or with a sheet that has no key, may not produce a
reusable profile. The page says why it was not saved; that does not undo the load. If a saved
layout no longer fits, **Read it with the assistant** starts its reading. Before loading a
saved layout, **Back to the proposal** and the words box let you reconsider it.

![Loaded task with 86 new records, a saved profile, change-set review and correction actions](/docs/screens/model-assistant-workbook-loaded.png)

*Above: the reference workbook task has prepared 86 new records in a change set and saved a
profile. Live data is unchanged until publication.*

For a wrong load that is not published, enter a correction and choose **Discard and load again**.
Confirm only after reading that this removes the entire change set, including manual edits
in it. **Discard the change set** ends the task instead. A stopped load discards the change
set it was making and returns to the accepted proposal. Once published, the task offers new
work; it cannot discard that publication through this correction flow.
