---
title: Jobs and limits
description: Read job progress, understand cancellation and find the deployment’s batch and retention limits.
reader: access-admin
---

Open **Settings › Data operations › Jobs** to see bulk writes, imports and exports across the workspaces available to you. The list is newest first and shows the job, workspace, state, item counts, requester, creation and finish times. Select a job for its details. This page also shows the deployment limits; it does not edit them.

For the person carrying out an import or export, see [Jobs](/docs/use/jobs/).

## Who can see and stop work

A requester can see their own job and cancel it while cancellation is available. Other people need the action group for the job’s kind in its workspace. The job and file lists do not expose everyone’s work simply because Jobs is visible in Settings. Security administration does not imply access to job data.

Jobs keep their requester’s permissions. Deactivating the requester or removing a required grant can fail the job at its next step. A role or group change does not wait for the person to sign in again. The requester can still inspect and cancel their own job while their active identity remains permitted to use refiroo.

**New import** needs **Bulk and import**; **New export** needs the corresponding data access. These controls also depend on the operator enabling job creation. Job reads remain available when new jobs are disabled.

## Progress and cancellation

Use **Refresh** for current progress and **Load more jobs** for older entries. **Items** distinguishes processed, applied, rejected and unprocessed items. Completion alone does not mean every item was applied; read the result and rejected-item details.

For a queued or running job, **Cancel** asks **Cancel this job?** Choose **Stop the job**, or **Keep the job** to leave it running. Cancellation is taken at the next chunk. Already committed chunks stay applied; an atomic job rolls back completely. Items not yet reached remain unprocessed. If the job finished before cancellation arrived, the page refreshes and explains its final state.

![Jobs list showing states, progress counts, requesters and available cancellation](/docs/screens/jobs-list.png)

## Limits

The **Limits** section displays the current values. Use these values when planning a large import; do not assume another deployment has the same settings.

| Limit | Meaning |
| --- | --- |
| Inline batch | Maximum items and size for a batch handled in one request. |
| Atomic batch | Maximum items in a job whose changes succeed or roll back together. |
| Background batch | Maximum items and file size for background work. |
| Chunk | Items processed together at each step of a non-atomic job. |
| Import file | Maximum uploaded file size. |
| Preview | Maximum items shown in an import preview. |
| Jobs kept | How long finished jobs are retained. |

A preview is not proof that every item in a larger file is valid. Inspect the completed job’s outcome. Download needed results before retention removes the job or its files.

The operator changes these limits in the deployment configuration and restarts the service. **Settings › Administration › Deployment** shows their sources and meanings to people with **Operations**. See [Deployment pages](/docs/administer/deployment-pages/). Change-feed retention is shown on **Consumer APIs**, separately from job retention.
