---
title: Set an approval policy
description: Require reviewed publication in a workspace and decide whether a second person must approve.
reader: access-admin
---

You need **Workspace administration** to change the policy. Someone with
**Security administration** grants the approver roles. Read
[Approval policies](/docs/administer/approval-policies/) for the effect on publication and Live edits.

## Establish approvers

1. Open **Settings › Workspaces**, select the intended workspace and choose **Access**.
   Check who holds a role with **Approve publications** there, directly, through a group
   or across the instance. Data owner is the predefined role with that action group.
2. If approval rights are missing, have the access administrator
   [grant a role](/docs/guide/administer/grant-a-role/) before requiring approval.
   Data steward can publish but cannot approve someone else's submission.
3. If submitters must never decide their own work, arrange another approver for every
   submitter who is also an approver. One person holding several roles is still one person.

## Save the policy

1. Open the workspace's **Approval** tab. Read the count of people or clients that can approve.
2. Tick **Changes need approval before they are published** to require reviewed publication.
   Leaving it off allows people with Publish to publish directly.
3. To require a different decision maker, also tick
   **The person who submitted a change set cannot approve it**. It is available only with
   the first setting on. Without it, someone permitted to publish and approve their own
   work can publish in one step.
4. Read any warning about missing approvers. The form can still save even if requests
   would have nobody to decide them; correct the grants before relying on the policy.
5. Choose **Save approval policy**. Wait for **Approval policy saved.** The checkboxes
   alone do not save the change.

![Workspace Approval tab showing both policy choices and Save approval policy](/docs/screens/admin-approval.png)

*Above: Graubünden requires approval, allows a submitter with approval rights to decide
their own work, and has two qualifying people or clients. Rita Approver is fictional.*

## Check the result

Ask a person preparing work to submit a change set and an authorised approver to find it
on Home or in their notices. Follow
[Approve a change set](/docs/guide/use/approve-a-change-set/) for the complete review task.
With the second-person rule on, a submitter's own review says a second person must decide.

If saving reports that the policy changed meanwhile, choose **Reload the policy**, inspect
the current values and apply the intended change again. Other failures show their reason;
check it before retrying. To stop requiring approval, clear the first setting and save.
That also clears the second-person setting. This policy governs change-set publication;
it does not remove any grants that allow direct edits to Live.

A saved policy also applies to the next decision on work already waiting. It does not
decide those requests automatically. With the second-person rule on, the submitter cannot
send their own submission back; they can withdraw it, or another approver can decide it.
