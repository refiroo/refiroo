---
title: Loading with the assistant
description: Understand assistant proposals, row checks, saved layouts and the steps from acceptance to publication.
reader: steward
---

Give the assistant a workbook, instructions about existing records, or both. It prepares work
for you to review. Use [Load a workbook with the assistant](/docs/guide/use/load-a-workbook-with-the-assistant/)
for a file, or [Change records with the assistant](/docs/guide/use/change-records-with-the-assistant/)
for instructions alone. A task is the saved work you return to as it proposes, checks and loads.

## Access and information sent

The built-in assistant must be enabled by your operator. It uses Claude Code, independently
of the AI provider used by Search / Ask and mapping suggestions. It needs the send level values,
**Use AI proposals**, **Bulk and import**, **Work in change sets** and enabled background jobs.
Model changes also need the model permissions; installing a new release needs **Model release**
at instance level. Retired workspaces and publications cannot receive imports.

Claude Code receives your words, the workspace's model and the whole file, if supplied. It can
read the workspace records it needs, within your permissions and their application and type
restrictions. It never approves, publishes or activates a model. Turns can incur charges or
consume a subscription allowance. Tasks, workbooks and session transcripts are retained while
the work can continue and then cleaned up; the normal task retention is 90 days. Read
[AI and your data](/docs/use/ai-and-your-data/) for costs, sending and retention before starting.

## What the assistant prepares

The dialog takes one XLSX or CSV file, within the deployment's import size limit. Instructions
are limited to 4,000 characters. Without a file, instructions are required. Images and documents
are not data files for this task. You cannot attach several files, schedule a task or transfer
its session to a colleague. Its requester and the workspace's administrators can read it.

When no saved layout fits, one session examines the file and current model, prepares a model
draft if needed, and checks every row against the proposed model. It chooses a key for each
source so the next file finds the same records. A key can combine columns when no single column
identifies a record. An empty key can skip a row; an ambiguous key cannot identify which record
to update. A combination key belongs to the import layout; it does not make that combination
unique throughout refiroo.

The same instructions can produce different proposed structures on separate runs; inspect each
proposal rather than assuming it repeats a previous design. An update can leave the model unchanged and prepare only record changes. Instructions can also
ask for relationships or a model change. The assistant is limited to capabilities refiroo supports;
its notes explain when it cannot complete a request. A turn that runs beyond the session limit (30 minutes unless the operator changed it) is stopped like your Stop,
and the task goes back to where you can tell the assistant to go on or try again. While other tasks hold the assistant, the page says how many are ahead.

## Review the proposal

**The assistant’s proposal** says what it understood and lists the types it adds, changes or
loads, with attributes and record counts. For a proposal with a model draft, **Show the model
change** expands **The model: what changes**, including changes such as a field becoming optional.
A words-only task that needs no model change says **No change to the model.** It has no model
draft, model-change detail or model editor button.
**The check of every row** distinguishes new, changed, unchanged, refused and skipped rows;
relationships have their own count. Skipped for an empty key differs from refused by a rule.
An empty cell that loses no value is not itself a skipped record.

Under **Checks**, read every **Needs attention** item. The engine checks for types holding
records that the proposal leaves out, filled cells no source reads, and new records beside
records already held. The last can mean an intended update failed to match its records and
would create duplicates. It is a warning, not an automatic block: resolve it before accepting.
**Columns left out** tells you what is deliberately omitted.

![Workbook proposal with formatted notes, assumed answers and the start of the type summary](/docs/screens/use-assistant-proposal.png)

**Questions** shows the answers the assistant assumed, only for what a person decides. Keep every choice and the answers are recorded without another turn; change a choice and use **Answer and
design again**. **Tell the assistant what to change** followed by **Send to the assistant**
continues the same session with your correction. When there is a draft, **Open in the model
editor** lets you edit it directly; the session reads it again before continuing. It cannot change a draft
held by another assistant task and must use its own. Close in the editor returns to the task. The draft’s history records who asked for the
assistant’s model steps; it does not mark every model element as Proposed.

If **The check from before the draft's last change** appears, those figures do not cover the
current draft. Ask the assistant to check the edited model again. Load refuses a stale check;
do not treat old figures as a successful check of your edit. Concurrent task changes reload the
latest state and ask you to check before trying again.

## Accepting, loading and publishing

For a words-only task with no model change, **Accept** prepares a new change set on the
workspace’s current release. It installs and activates nothing. A proposal with a model draft
uses **Accept the model**: the session installs the necessary release without activating it
and prepares the load in a new change set. Neither action publishes records. A task with nothing
to load reports why and can be corrected; an empty change set is not reported as a successful load.

The result names the change set and its counts. **Review the change set** opens its normal
review. Check the actual rows and relationships, validate, then submit for approval or publish
as your access and the workspace's policy allow. If the load uses a release the workspace does
not yet run, a model administrator must activate the compatible release before publication.
The assistant does not take that step. A second-person approval rule still applies to the
person who asked for the work.

The saved-layout path has its own **What the load would do** check and load button. Read
**What confirming does, in this order**: when that path changes the model, **Activate the model
and load** explicitly activates it as your confirmed action before loading the change set.
A subsequent load failure does not undo that model activation. A record load always waits
for publication to reach Live.

A task's bar below the top bar names the current step and next action. It follows you into
the model editor and change-set review opened from the task. You can leave while a turn works
and return through its entry under **Settings › Jobs**; its completion is announced.

## The next file and the saved profile

When the completed imports have usable keys, refiroo saves a profile and offers **Open the
profile**. The next file with that layout can use it without the assistant or AI cost.
If no new profile was saved, the page says why: for example, a source has no key, the changes
were made without a repeatable file import, or a profile already exists. The prepared load
still stands. Do not assume it is repeatable without that saved profile.

A fitting saved profile takes the engine's own path: you still review its proposal and row
check, but no assistant session starts. Sheets also present in the earlier file but deliberately
left out by the profile do not prevent reuse. A new sheet needs the assistant to review it. After the earlier task and its file expire,
a sheet the profile left out can also require a new session because that comparison is no
longer available. A saved layout can ask its unresolved file-value questions again on each repeat.
If **The saved layout does not fit this file** appears, **Read it with the assistant** starts
a session on that task and file. The saved-layout check also offers **Back to the proposal**
and a correction box. See [Load the next version of a workbook](/docs/guide/use/load-the-next-version-of-a-workbook/).

## A model change that moves records

The workspace menu's **Change this model…** asks what should change, with an optional workbook.
It additionally needs **Model authoring** and **Model release**. The proposal says what becomes
what and shows existing record counts. Review the model in the
[model editor](/docs/model/the-model-editor/) if you need to inspect its structure.
For the model administrator’s full task, follow
[Change a model with the assistant](/docs/guide/model/change-a-model-with-the-assistant/).

For whole types becoming other types, acceptance installs a release but moves no records.
**Preview the migration** opens the migration with the proposed choices. You can go **Back to
the proposal**. A person with Model release confirms it: the records move live with their IDs,
values, relationships and history. There is no change set or its approval step for that migration.

A whole-type move and a partial move need separate tasks.

For part of a type moving, the task normally shows **Three steps are yours**: activate a release
holding old and new types, review and publish the change set under the usual approval rules,
then activate the final release to remove the emptied types. If old types remain in the final
model, it shows **Two steps are yours** instead. The first activation moves no records; publishing
moves them. A remaining record in a type being removed blocks the final activation. Each step
appears when it is ready; someone with Model release performs activation. A large split can be
slow because the records are changed individually. See [Model migrations](/docs/model/migrations/).
If the task expires before the final activation, the installed release remains available under
Settings › Model so an administrator can complete the step.

## Stop, correct or end a task

Follow [Continue or correct an assistant task](/docs/guide/use/continue-an-assistant-task/) for the
buttons. These states need different decisions:

| What you see | How to continue |
| --- | --- |
| Working on it or Loading | **Stop** ends the turn. You can also leave the page while it runs. |
| A stopped correction with an earlier proposal | The last proposal returns with a note. The draft may already contain changes from the stopped turn: inspect it before continuing. Stop does not rewind the draft. |
| A stopped load | The change set being loaded is discarded and its jobs stopped. Return to the accepted proposal and tell the assistant how to continue. |
| The assistant stopped or You stopped the assistant | Read the task's notes. Use the words box, **Try again as it was** or **Go on as it was**, open the draft, or **Discard this task**. Even a session that never started can be tried again with corrected words. |
| The engine could not apply this proposal | Read the reason above the correction box, then tell the assistant what to change. |
| A loaded change set that is wrong | Use **Not what you wanted? Tell the assistant** and **Discard and load again**. Confirmation removes that entire change set, including hand edits, before the same session loads again. |
| A load you want to abandon | **Discard the change set** ends the task and removes that prepared work. Live records are unchanged. |
| A refused migration or activation | Read the engine's reason on the task and tell the assistant what to change. |
| Your access no longer permits the next step | The page names the permission needed and lets you copy the task link for a workspace administrator. |
| Published | The task confirms publication and offers **Change this model…** and **Ask about these records…** where your access allows. Start new work to correct published data. |
| Discarded | The session has ended. Use **Start again** in the journey bar or return to the workspace. |
| Expired or unknown task | The page explains it is not kept or does not exist and offers **Go to the workspaces**. |

The newest three task notes are shown; older notes are folded. **Discard this proposal** removes
the proposal and its draft; closing the proposal keeps it for later. Discarding a loaded task
also discards its change set. Unused model releases installed by a session are retired at its
end; releases still in use are kept. Published changes and their assistant origin remain in
[history](/docs/use/history/#work-prepared-by-an-assistant) after the task expires.
