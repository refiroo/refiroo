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

Follow progress through the job's server-sent event operation, which reports changes as they commit, or reread the job. Page item outcomes separately. Import rows gather source-row results; other job kinds can offer their own row reports. `JOB_HAS_NO_ROWS` means that kind has no row report: use its items or linked subject.

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
