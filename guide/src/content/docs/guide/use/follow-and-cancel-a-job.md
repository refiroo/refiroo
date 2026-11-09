---
title: Follow and cancel a job
description: Read a background operation’s progress and results, or stop remaining work.
reader: steward
---

Follow work after leaving its collection or import dialog. See [Jobs](/docs/use/jobs/) for
states, access and retention.

1. Open **View job** in the starting notification, or go to **Settings › Data operations › Jobs**
   and open the job; a group of related jobs opens first, and its jobs under it. Check **Workspace**
   and **Requested by** before acting.
2. Read **State** and progress. A preview waiting for confirmation has not written its proposed
   changes. Review the items before choosing **Load the file** for an import or **Apply** for
   a bulk preview. A running job updates while the page stays open.
3. To stop remaining work, use **Cancel job**, **Cancel import** for a waiting import,
   or **Cancel preview** for a waiting batch preview.
   Read the confirmation, then choose **Stop the job** for running work or **Discard the
   import** / **Discard the preview** for a waiting preview. From the Jobs list, choose **Cancel
   job** in its confirmation. **Keep the job**, **Keep the preview** or **Keep the import**
   dismisses that confirmation.
4. Wait for the state to settle. **Cancel requested** is still pending. Already committed
   chunks remain applied: inspect the final counts rather than assuming cancellation undoes them.
5. For an export that completed, read **The file** and choose **Download**. For an import or
   batch, read refused and unprocessed items and their reasons. Fix the source and preview
   again before retrying work.

If the job failed, read **Why it failed**. Loss of the requester's permissions can stop a job;
a changed change set can stop its next chunk. Expired previews require a fresh preview.
Retained results and files disappear after their retention; download what you need in time.
