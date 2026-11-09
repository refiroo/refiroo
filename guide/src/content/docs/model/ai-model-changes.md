---
title: Model changes with the assistant
description: Review a model proposed from words or a workbook, and understand how its records move.
reader: model-admin
---

Describe the model you need in words and the assistant proposes a draft for you to review.
You can attach a workbook, but a file is not required. The assistant can add fields, types,
relationships and applications, or propose moving records between types. These are model
capabilities available to any application.

Start with [Change a model with the assistant](/docs/guide/model/change-a-model-with-the-assistant/).
For a file that needs a model and a load, follow
[Review the assistant's workbook design](/docs/guide/model/review-an-assistants-workbook-design/).
The [model editor](/docs/model/the-model-editor/) remains available for direct edits.

## Availability and your data

The built-in assistant uses Claude Code. It is available only when your operator has enabled it
and allows the data it needs to be sent. Your words and the workspace's model go to Claude Code,
with the whole workbook if attached. The assistant reads workspace records as needed, within
your permissions. This is more than sending a few sample rows.

**Change this model…** is offered in an active workspace when you hold **Use AI proposals**,
**Bulk and import**, **Work in change sets**, **Model authoring** and **Model release**, and job
creation is enabled. Installing a changed model also needs **Model release** at instance level.
If the offer is missing, ask your administrator to check these rights and the assistant setup.
The separate AI provider used for explanations does not enable this assistant.

Assistant turns can incur Claude Code usage charges. refiroo records who asked, the outcome,
tokens and cost when reported. Tasks and workbooks normally remain for 90 days after completion
or the last change. Session files and transcripts remain while the task can continue; cleanup
follows publication, discard, confirmed migration or expiry. These are separate from optional
logging of request content. See [About AI in refiroo](/docs/run/ai/) for the full explanation of
access, billing, data leaving the instance and retention, including the provider's own policies.

## Review the proposal before accepting

**The assistant’s proposal** describes the types it would add or change and any records it
would move. Read the counts and **Checks**, not only the summary. The assistant's wording can
be wrong. The engine checks the draft and the data against its rules; that does not establish
that the proposed design means what you intended.

Answer the questions or use **Tell the assistant what to change**. You can also choose
**Open in the model editor** and edit the draft directly. The same assistant reads those edits
when it continues. A second assistant task cannot take over a draft another task holds.

For a workbook load, **What the load does** shows new and matched records, new relationships,
refused items and rows read. Open a type's row for example records with their source cells,
read any **One name twice in one type** finding, and expand **Where each part of the file goes**
to review how the file is used. The assistant reads the file, model and workspace records and
prepares records and relationships for the engine to check; it writes no import profile.

**Accept and load to change set** lets the engine install the changed model and load exactly those checked
records and relationships into a new change set as one batch. No assistant turn runs, and nothing
is activated or published. A draft changed after the check is checked again first; any refusal
then prevents installation and loading. If changed data causes a refusal during the batch, none
of the batch is loaded and the change set is discarded. A release installed before that failure
can remain installed. Correct the proposal in words, review the new check and accept again.
An assistant load saves no profile for the next file; send that file to the assistant again.

Model-only and record-move proposals keep **Accept the model**. A whole-type move still needs
migration confirmation. A partial move still needs publication. Loading an already saved layout
is a separate path: its confirmation can install and activate a model change before importing.
Read the confirmation for the path you are using.

## Only the model changes

When the request changes the model alone, such as adding a view without changing records,
acceptance installs the release and ends with a migration that moves no type. Review
**Preview the migration** and confirm it with **Model release** to put the workspace on the
new model. No change set is created and every record stays as it is.

## Every record of a type moves

A whole type becoming another type, two types merging, or a type moving into another application
can use a migration. The proposal lists what each type becomes and how many records it holds.
Accepting installs the proposed release but moves no record. **Preview the migration** opens
the existing migration review with the proposed choices filled in.

Someone with **Model release** confirms that migration. It changes live data and the workspace's
release together, keeping record IDs, values, relationships and history for the accepted type
moves. There is no change set to submit for approval in this path. Inspect every conversion,
removal and refusal in the [migration preview](/docs/guide/model/migrate-a-workspace/).

## Only some records move

For a split based on a field value, the proposal describes what acceptance prepares: a
release holding the old types beside the new ones, a change set moving the selected records,
and the final release removing the emptied types. The removal note says which records move
and where they go. After accepting, complete the prepared steps:

1. Activate the release holding the new types beside the old. No record moves yet.
2. Review and publish the change set, following the workspace's approval rules. The records
   change type and keep their IDs.
3. Activate the final release, removing the emptied types. If someone has added records to an
   old type meanwhile, activation is refused until that is resolved.

The task shows the next available step and marks completed steps **Done**. If the old types
remain in the accepted model, it shows **Two steps are yours** instead: no final removal is needed.
A whole-type move and a partial move need separate tasks. Splitting thousands of top-level
records can be slow because those records are prepared one at a time.

## Stop, correct or discard

**Stop** ends the current turn. A stopped correction returns to the last proposal, with a
warning if it already changed the draft. A stopped load discards the change set it was making
and returns to the accepted proposal. Before any proposal exists, the stopped task still takes
words telling the assistant how to continue.

A failed task shows its reason. Use **Tell the assistant how to go on**, or **Try again as it was**.
A stopped task offers **Go on as it was**. **Discard this task** ends it and removes its draft;
if it has a loaded change set, that is discarded too. Discard does not reverse a confirmed
migration or an already published change.

For a loaded change set that is wrong, **Discard and load again** removes that change set,
including your manual edits in it. For a workbook load, the assistant then revises the proposal
and checks its records again. Review it and choose **Accept and load to change set** to prepare the replacement
change set. Review the discard confirmation carefully. Once published, the task offers new work through **Change this model…** or
**Ask about these records…**, subject to your current permissions.
