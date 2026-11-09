---
title: Jobs
description: Follow background work, distinguish completion from success and cancel safely.
reader: integrator
---

Bulk writes, imports and exports are jobs. Migrations, moves and model checks also use jobs. Keep the job ID returned when you submit work, then use the [jobs operations](/docs/api/?api=management#tag/jobs) to follow progress and outcomes.

## State and result answer different questions

| State | What to do |
| --- | --- |
| Queued | Work is stored and waiting. |
| Running | Follow progress and committed outcomes. |
| Awaiting confirmation | Inspect the preview, then confirm or cancel. |
| Completed | Read the result and item outcomes; completion can include refusals. |
| Failed | Read the job-level cause and reconcile already committed work. |
| Cancelled | Read what committed before cancellation took effect. |
| Expired | The summary remains, but detailed outcomes, files and replay keys have been removed. |

A completed job's result distinguishes all applied, partly applied and none applied. An unchanged item is applied without a data write. A job-level failure is different from a completed job containing rejected items.

Follow progress through the job's Server-Sent Events (SSE) operation, which reports changes as they commit, or reread the job. Page item outcomes separately. Import rows gather source-row results; other job kinds can offer their own row reports. `JOB_HAS_NO_ROWS` means that kind has no row report: use its items or linked subject.

## Cancellation and restart

A cancellation request returns promptly. The worker stops at a safe boundary; it does not undo earlier independent chunks. An atomic batch rolls back its transaction on cancellation. A waiting preview cancels immediately without applying changes. One-step checks and the final loading step of a move check cancellation again before committing that step.

Background processing commits changes and their checkpoint together. After a restart, work resumes from the first uncommitted item rather than repeating committed items. Independent work normally commits in chunks of 500 items; ordinary writes wait for a chunk rather than an entire large import. An export restarts its entire snapshot read after a worker crash; it does not resume a partial output file. Do not infer failure merely because a worker restarted.

A changed model, retired workspace or lost change-set version claim can fail the remaining work. Earlier chunks stay committed. `JOB_FAILED` includes a diagnostic reference for an unexpected failure; `MODEL_RELEASE_CHANGED` and `CHANGE_SET_VERSION_CONFLICT` require reviewing the new context.

## Access and retention

Jobs run as their requester. Access is checked when submitted, confirmed and as work proceeds. Revoked rights or a deactivated requester can fail the job with `FORBIDDEN`; confirmation can be refused while the preview keeps waiting. The requester can read, follow, cancel and confirm their own job. Other callers need the action group that starts that kind in its workspace. See [Security for integrators](/docs/integrate/security-model-for-integrators/).

Default retention is seven days. Download output and retain the source reconciliation record before expiry. A completed export alone offers its file; cancelled, failed and expired exports have no usable partial output. A deployment with job creation disabled keeps job reads available but does not expose creation or cancellation operations.

| Refusal | Recovery |
| --- | --- |
| `JOB_NOT_FOUND` | Check the ID and instance. |
| `JOB_FINISHED` | Read the final result; cancellation is too late. |
| `JOB_EXPIRED` | Start a new reviewed request; the old preview cannot be confirmed. |
| `JOB_NOT_AWAITING_CONFIRMATION` | Read current state; confirm only a waiting preview. |
| `JOB_NOT_COMPLETED` | Wait before requesting output. |
| `JOB_HAS_NO_OUTPUT` | Use the kind's outcomes or subject rather than a file. |
| `JOB_OUTPUT_MISSING` | Ask the operator to investigate lost job storage. |

Operators can inspect these same jobs in Settings › Data operations › Jobs, including state, result, counts, cancellation and current limits. For browser tasks, follow [Importing and exporting data](/docs/use/importing-and-exporting/).

## A job’s context and limits

A batch claims the change set’s version once for the job. Each independent chunk that changes data advances that version. If another writer changes it between chunks, the remaining work fails with `CHANGE_SET_VERSION_CONFLICT`; the completed response reports the version the job reached. A live release change at an inline batch’s commit refuses the request with `MODEL_RELEASE_CHANGED` and saves neither changes nor job. In the background, earlier committed chunks remain applied.

The [capabilities document](/docs/api/?api=management#tag/model) reports job limits. Defaults are seven days’ retention, 1,000 items and 5 MB inline, 10,000 atomic items, 1,000,000 background items, 50 MB for a background JSON batch and 200 MB for an uploaded file. `BATCH_TOO_LARGE` details name the setting, maximum and submitted items or bytes; select another supported mode or split the input. An import can expand rows into several items, so row count is not an item count.

Operators control `INTEGRATION_JOBS_ENABLED`, `JOB_CHUNK_ITEMS` (default 500) and `JOB_LEASE_SECONDS` (default 120). With job execution disabled, stored jobs remain readable, but creation, cancellation and background processing stop. Expiry processing also stops while that worker capability is disabled. Finished jobs normally expire during hourly cleanup: summaries remain, detailed outcomes, files and idempotency keys do not. Operators store uploaded and exported files under `JOB_FILE_DIR`, default `var/job-files`; use the job’s output operation rather than a filesystem path.

The named limits are `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`, `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES` and `ATOMIC_JOB_MAX_ITEMS`, with retention in `JOB_RETENTION_DAYS`. Use the returned `expiresAt` as the deadline for retaining outcomes; an expired job’s item collection reads as an empty page while its summary remains. Finished work reports processed equal to total, including unprocessed outcomes; that does not mean every item applied.

## AI jobs

A mapping-target proposal runs as `aiProposal`; an assistant task uses `aiTask` jobs for its work and `dryRun` jobs for checks. The job completes a step, while the task can still wait for a person. Use the [jobs operations](/docs/api/?api=management#tag/jobs) to list by kind, and the [AI operations](/docs/api/?api=management#tag/ai) to inspect the linked task or proposal. Cancelling a mapping proposal keeps the mappings already prepared; stopping an assistant turn follows the task-specific recovery described in [Assistant tasks](/docs/integrate/assistant-tasks/). AI needs the requester's Use AI proposals rights as well as the write permissions; requests can send data and incur service charges. [About AI](/docs/run/ai/) explains what is sent and retained.

## Reconnect a progress stream

The [job events operation](/docs/api/?api=management#tag/jobs) sends `event: job` with the current job immediately, then sends a new job snapshot when committed state changes. Comment lines every 15 seconds keep an idle connection open. They are not progress and need no acknowledgement. The stream ends after `completed`, `failed`, `cancelled` or `expired`; awaiting confirmation is still waiting, not a final execution result.

A lost stream does not cancel the job. Reconnect with a valid management token to receive its current snapshot, or read the job directly. There is no event-ID replay sequence for this stream; use paged item and row outcomes for reconciliation rather than counting SSE messages. Multiple intermediate progress snapshots may pass while disconnected.

Keep job IDs, source-row references, final outcomes and downloaded exports in your integration's reconciliation storage before expiry. Restoring refiroo itself, including its job files, is an [operator backup and restore task](/docs/run/backup-and-restore/). An export of records is not a backup of jobs, profiles, credentials or history. If a restore predates a submitted job, reconcile the actual data before submitting it again; do not assume a replay key survived.
