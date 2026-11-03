---
title: Change a model with the assistant
description: Describe a model change, review the proposal and complete a migration or a staged record move.
reader: model-admin
---

Use this task to change the structure of an active workspace from words. Read
[Model changes with the assistant](/docs/model/ai-model-changes/) for permissions and the two
ways records can move. You need the assistant enabled, permission to send the data it needs,
and the rights to author, install and release the model and work in change sets.

Your words, the model and any whole workbook you attach go to Claude Code; it can read workspace
records as needed. Turns can cost money, and tasks, files and session transcripts are kept for
the configured retention periods. [About AI in refiroo](/docs/run/ai/) explains access, costs
and retention in full. Check your organisation's policy before sending a file.

## Describe and review

1. Open the intended workspace. Open its **⋯** menu beside the workspace selector and choose
   **Change this model…**. Check the workspace named in **Change this model**.
2. Enter **What should change?**. Say which types or fields change and what should happen to
   existing records. The field allows up to 4,000 characters. Use **A workbook (optional)**
   to attach an XLSX or CSV file when it helps explain the change.
3. Read the disclosure of what is sent. Choose **Ask the assistant**, or **Cancel** to leave
   without starting a task. Wait on the task page; **Stop** pauses the work without discarding
   the task.
4. Read **The assistant’s proposal**. Check every type it adds or changes, **Checks**, questions
   and the records that move. For a whole-type move, check both the destination type and the
   number of records. Do not accept merely because the summary sounds plausible.
5. Answer questions and use **Tell the assistant what to change** for corrections. Choose
   **Open in the model editor** to inspect or edit the draft directly. Return to the task;
   the assistant rereads the draft when it continues. If a check predates your edit, ask for a
   correction and wait for a current check before loading.
6. Choose **Accept the model** only when the proposed structure and treatment of records are
   right. **Discard this proposal** removes the proposal and its draft instead. **Close** keeps
   the proposal for later.

*Example: a model for transport stops might split a general stop type by a field that distinguishes
bus and rail stops. The instruction should say whether the old type remains and which values
select each new type. These choices belong to the model, not to a built-in transport feature.*

![Change this model dialog with the workspace, instruction and optional workbook](/docs/screens/model-assistant-change-dialog.png)

## Finish a whole-type move

1. Under **Move the records to the new model**, review the list of what becomes what.
   Accepting has installed a release; nothing has moved yet.
2. Choose **Preview the migration**. The migration page opens with the assistant's type choices.
   Follow [Migrate a workspace](/docs/guide/model/migrate-a-workspace/) to inspect converted,
   removed and blocked items. **Back to the proposal** returns to the task.
3. If a mapping is wrong or the engine refuses it, return to the task and use
   **Tell the assistant what to change**. The assistant can revise the model before confirmation.
4. Confirm only the reviewed migration, with **Model release** in this workspace. This changes
   live records and the running release together. There is no change set or separate change-set
   approval for this path. Return to the task to see that the workspace runs the new model.

![Accepted whole-type move with record counts and Preview the migration](/docs/screens/model-assistant-whole-type-move.png)

## Finish a partial move

The task shows **Three steps are yours**, with **Next** beside the available step.

1. Under **1. Add the new types to the workspace**, choose **Open the release**. Activate the
   release holding both the old and new shapes in the intended workspace. No records move.
2. Return to the task. Under **2. Review and publish the change set**, choose
   **Review the change set**. Inspect its record changes and validation, then submit for approval
   and publish according to the workspace's rules. Publication moves the selected records.
3. Return to the task. Under **3. Remove the emptied types**, choose **Open the release** and
   activate the final release. This removes the old types only when they are empty. If new
   records were added to one meanwhile, resolve them and check again.

If the accepted model keeps the old types, **Two steps are yours** omits the removal step.
Someone without **Model release** is told that a holder of that right must activate the release.
A split of thousands of top-level records can take time; avoid starting a duplicate task while
it is working.

![Partial move showing the three steps, with the first complete and review next](/docs/screens/model-assistant-partial-move.png)

## If you cannot continue

Read the reason on the task. A refused migration or next activation is also reported there.
Tell the assistant how to correct the proposal; an explanation cannot waive an engine rule.
After a failure, **Try again as it was** continues without a new instruction. A stopped task
can **Go on as it was**. See [Stop, correct or discard](/docs/model/ai-model-changes/#stop-correct-or-discard)
for what is kept or removed at each stage.

If an action disappears because your permissions changed, ask an administrator to restore the
needed right or give the task link to the person named by the page. An expired or missing task
leads back to the workspaces; start a new task if its proposal is no longer kept. A confirmed
migration has no automatic undo; inspect its history before planning a further model change.
