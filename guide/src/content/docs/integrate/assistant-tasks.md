---
title: Assistant tasks
description: Submit a workbook or instructions, review the checked proposal and hand changes to a person for publication.
reader: integrator
---

Use an assistant task when a client needs to submit a workbook or instructions and let a person review the proposed model and data changes. The built-in assistant runs a Claude Code session through refiroo's API. It can prepare a model draft, check the file and load a change set. A person takes the final activation, migration or publication steps.

This is separate from [external assistants over MCP](/docs/integrate/assistants-and-agents/). The task API needs `AI_AGENT_COMMAND`, not `AI_PROVIDER` or `MCP_ENABLED`. Use the [AI task operations](/docs/api/?api=management#tag/ai) for request schemas and individual actions. The sequence below explains how to build a client around them.

## Before submitting

The deployment must allow integration jobs. The requester needs **Use AI proposals** and **Bulk and import** in the workspace. Loading a change set also needs **Work in change sets**. Model work requires the corresponding model permissions; permission to ask for AI does not supply them. Tasks are visible to their requester and workspace administrators. Other callers receive `AI_TASK_NOT_FOUND`.

Tasks require send level `values`. The session receives the instructions, workbook if supplied, workspace model and OpenAPI document, and can read records as needed. It uses Claude Code's configured credentials and incurs that service's charges. Each turn records tokens and any reported cost in refiroo; a missing cost is not a free turn. Tasks and workbooks normally remain for 90 days, and session files and transcripts remain while work can continue. Call-content logging is separate. Read [About AI](/docs/run/ai/) for the full data, cost and retention policy, and ask the operator to [set up the assistant](/docs/run/set-up-ai/) if it is unavailable.

The session's dedicated client has no more access than the requester and cannot approve, publish or activate a release. It is a client of kind `session`, not an agent client. It has no reusable secret and is omitted from ordinary client lists unless `kind=session` is requested. Narrowed type and application permissions remain in force.

## 1. Submit and follow the task

Send `POST /api/v1/ai/tasks` as multipart form data. Include the workspace and instructions in the JSON `request` part, and optionally an XLSX or CSV `file`. Words alone can request work on stored records; neither a file nor nonblank words gives `AI_TASK_NEEDS_WORDS`. The [create operation](/docs/api/?api=management#tag/ai) defines the fields and upload refusals.

Keep the returned task ID, version and job ID. A `202` means work was accepted, not reviewed or published. Follow the [job](/docs/integrate/jobs/) and reread the task for the proposal. The job kind is `aiTask`; task state and job state are separate. A worker restart ends an earlier still-running session before resuming, so two sessions do not work in the same task folder.

The [task response](/docs/api/?api=management#tag/ai) returns the original `words` uncut
and, beside them, `title`: a short title the assistant writes with its first answer. It is
`null` until then and for a task that ends before an answer. Name a words-only task by
`title` when present; otherwise use `words`, shortened at a word boundary with “…” if needed.
Keep the full request visible with the proposal. A workbook task keeps its file name, and
the assistant’s draft is named `Assistant: <title>` once the title arrives.

| Task state | Client behavior |
| --- | --- |
| `reading` | The file is being read or the session is starting. |
| `checking` | A session turn or dry run is working. While `ahead` is a number the task's job still waits for the assistant's worker: show how many tasks are ahead, not the work. |
| `checked` | Present the proposal for a person's review. |
| `loading` | Follow the engine loading checked items or a saved layout into a change set. |
| `loaded` | Inspect the result and show the next human action. This does not mean live data changed. |
| `failed` or `stopped` | Show the task's notes and offer continuation or discard. |
| `cancelled` | The task was discarded. Start a new task for new work. |

Do not use the legacy `read` state as a step: the response schema includes it, but current tasks do not enter it. Use `phase` for progress while a job runs. Reread before every action and claim the current `expectedVersion`; on `VERSION_CONFLICT`, present the new task rather than replaying a stale decision.

## 2. Show what the proposal actually changes

At `checked`, present the summary, the outline per type, the questions and assumed answers, and the engine's checks. Link the `draftId` to the model editor. A person can edit that draft, and the next session turn rereads it.

For a workbook the assistant reads the file, model and workspace records itself, changes the
model draft where needed, and turns the file into batch items. It submits those items to the
[draft dry-run operation](/docs/api/?api=management#tag/model%20administration). The engine checks every
item against the draft's model in a transaction it rolls back. No record changes are saved by
that check and the assistant writes no import profile. The set must fit both the background
and atomic batch limits; see [Writing in bulk](/docs/integrate/writing-in-bulk/) and the
[API reference](/docs/api/?api=management#tag/model%20administration) for the limits and refusals.

Present `design.load` as **What the load does**: new records, existing records matched, new
relationships, refused items and rows read. Show its type table with changed counts and linked
types, expandable example records with typed values, relationships and source-cell references,
and the engine's findings of repeated names within a type, including their parents. Offer the
file-part ranges as secondary detail. These examples help review the proposal; they are not
the complete load. Questions concern only choices the file and the person's words leave open.

For these tasks, `design.itemsLoad` is true, `check.mode` is `items` and `check.sheets` is empty.
Use `design.load` for examples and source cells; do not request sheet changes when no sheet
sources exist. Tasks recorded with a profile and saved-layout checks keep per-sheet figures.
For those checks only, page the [checked-change operation](/docs/api/?api=management#tag/ai)
using a source number from `check.sheets`. An unknown source returns `AI_TASK_TABLE_UNKNOWN`;
before any check the operation returns `AI_TASK_STATE`.

`check.draftChanged` means the check predates an edit and does not describe the current draft.
For an items proposal, acceptance checks every item again first. If any is refused, the task
fails before installation or loading. A person can also ask for a revised proposal and check
before accepting. Saved-layout checks retain their stale-check refusal.

The person can answer the questions or give a correction in words. A correction starts another turn and another check; answers that all keep the assumed choices start nothing and leave the task `checked`, and any other answer starts a turn. Neither accepts the proposal. A draft held by another assistant task cannot be written by this session (`AI_TASK_DRAFT_HELD`). Use a draft of this task's own instead of trying to share it.

## 3. Accept, then hand over the result

Send the [acceptance action](/docs/api/?api=management#tag/ai) only after the person reviews the
proposal. For an items proposal, label it **Accept and load to change set**. The engine installs a release if
the model changed, opens a change set over current live data, and loads exactly the stored,
checked items as one atomic batch. No assistant turn runs. Without a model change, the change
set uses the workspace's current release. The engine neither activates nor publishes.

If the data changed and the batch refuses an item, none of the batch is written: its change set
is discarded and the task becomes `failed`, with notes naming refused records and their source
cells. A release installed before the refusal can remain installed. A correction or retry
returns to the assistant for a revised proposal and items check, followed by a new acceptance.
A successful items result includes the change set, counts, and `importJobId` naming the `batch`
job, whose `parameters.taskId` associates it with the task. An items load saves no import profile.

A proposal's `design.removals` lists what the person's words explicitly ask to remove: `kind` (`objectType`, `application`, `attribute` or `relationType`), `key`, `words`, the engine's counts `records`, `values` and `relationships`, and a plain `text` sentence to show before acceptance. A migration that would lose anything outside those removals is never offered: the task fails with a warning note naming the loss per type, and no data is changed.

Words-only tasks without a model change keep their **Accept** step: the session prepares a
nonempty change set on the current release. Model-only and record-move tasks keep **Accept the
model** and their migration or staged-move endings. Show the result according to what it contains:

| Result | Person's next action |
| --- | --- |
| `changeSetId` | Review the records and relationships, then publish under the workspace's approval policy. |
| `migration` | Preview and confirm the migration using its release and its mappings: `typeMappings` (with `toApplicationKey` for a type that moves to another application), `relationTypeMappings`, `splits` and `listConversions`, as the draft's migration states them joined with the assistant's moves. Whole-type moves change live data; a model-only change has no type moves and changes only the running model. No change set is created. |
| `changeSetId` with a distinct `thenReleaseId` | Activate the release holding both shapes, review and publish the change set, then activate the final release. |

When `thenReleaseId` equals `changeSetReleaseId`, the model keeps the old types alongside the new ones. There is no final removal step. Do not show an activation with nothing to do. A whole-type migration is confirmed by someone holding Model release; it does not use the change-set approval policy. A partial move uses that policy when its change set is published.

Link to [Model and release operations](/docs/integrate/model-and-release-operations/), [Move records between models](/docs/guide/integrate/move-records-between-models/) and [Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/) for these human-controlled boundaries. Never infer publication from `loaded` or assume every loaded task has `changeSetId`.

Proposed rows carry AI origin, the task and who requested them. Later edits record who edited them; publication preserves origin in history while the publishing person is the actor. This survives task expiry. MCP's `channel: mcp` identifies the other interface and is not the task's provenance marker.

## Repeated layouts can avoid a session

If a stored import profile fits the workbook as well as the engine's reading, refiroo prepares its proposal without starting Claude Code. This path has no assistant-session cost. Review its questions and check as usual, then use the saved-layout load action. That action can install and activate a changed draft when the requester holds Model release; the session path above never activates. Use the [task operations](/docs/api/?api=management#tag/ai) to distinguish these paths.

A workbook loaded from the assistant's checked items returns no reusable profile. Submit the
next file of the same layout to the assistant again. Reuse without a session requires an
import profile saved separately; an earlier assistant load is not enough. See
[Files, imports and exports](/docs/integrate/files-imports-and-exports/) for profile-based loading.

## Stop, correct or discard

Use the [task continuation and cancellation actions](/docs/api/?api=management#tag/ai), not a second create request, to continue the same task.

- A stopped or failed task can take correction words or retry from where the session was. The task's `canTell` tells the client when it can accept words.
- Stopping an active turn does not discard the task. It returns to the last proposal, or becomes `stopped` when none exists. A stopped load discards the change set it was creating and returns to the accepted proposal. Inspect warnings if the stopped turn already edited the draft.
- Correcting a loaded task before publication discards its change set, including people's edits. For an items load, the assistant then revises the proposal and checks the items again; present that proposal for another acceptance before loading. Obtain the person's decision with the discard consequence visible before sending the correction.
- Discarding a loaded, unpublished task also discards its change set. A published or discarded set cannot be corrected through that old session; start new work.
- A saved-layout proposal can return from its load stage to the proposal. It can also be read with the assistant if the saved design no longer fits.

A loaded, failed or stopped task can keep its session files while it can continue. Publication, change-set discard, confirmed migration, task discard or expiry ends the session; the next task read or expiry sweep cleans its folder, logs and transcript and deactivates the client. Installed releases that nothing uses are retired rather than deleted; pre-existing releases are left alone. See [retention](/docs/run/ai/#what-is-kept) for operational details.

## Recover from a refusal

| Refusal | What to do |
| --- | --- |
| `AI_NOT_CONFIGURED` | Ask the operator to configure `AI_AGENT_COMMAND`; a provider alone cannot run tasks. |
| `AI_SEND_LEVEL_TOO_LOW` | The task requires `values`; lowering a request cannot override the instance ceiling. Use a manual import if sending values is not allowed. |
| `AI_TASK_NOT_FOUND` | Check task ID, retention and requester or workspace-administrator access. |
| `AI_TASK_STATE` | Reread state and result; use only an action allowed now. |
| `VERSION_CONFLICT` | Reread and review the current proposal before sending its version. |
| `AI_TASK_CHECK_STALE` | The saved-layout draft changed after its check; obtain a new checked proposal. |
| `AI_TASK_NOTHING_TO_LOAD` | Correct the design so the saved-layout load has something to import. |
| `AI_TASK_DRAFT_HELD` | Have the session use its own draft. |
| `AI_ASSISTANT_ROLE_CHANGED` | Ask a security administrator to restore the assistant role's required groups as the message explains. |

The task's notes explain a session failure; the call record can provide a diagnostic reference. A turn over the session limit (`AI_AGENT_TIMEOUT_SECONDS`, 30 minutes) is stopped as a person's Stop is: the task returns to its last point with a note, and the person can continue or try again. Provider-call timeouts are separate from this session limit. Fix credentials or reachability with the operator, then continue the task rather than treating a failed turn as a successful load.

Use the proposal and acceptance actions for assistant tasks. A `/plan` action and a task `plan` are not available; the changes read selects by `source`, not `table`. Use ordinary import profiles for deterministic loading without a session.
