---
title: Prepare and publish a change set
description: Prepare related changes, review and validate them, then publish them together.
reader: steward
---

Prepare changes away from Live, review them and publish them together. See
[Change sets](/docs/use/change-sets/) for how starting data, live work and publications fit together.

For changes beyond fields, follow [Relate records](/docs/guide/use/relate-records/),
[Arrange records in a tree](/docs/guide/use/arrange-records-in-a-tree/),
[Map codes between systems](/docs/guide/use/map-codes-between-systems/) or
[Fill in a relation matrix](/docs/guide/use/fill-in-a-relation-matrix/).


## Start or open a change set

1. Open an application in the current workspace. Check **Workspace** in the sidebar, then
   choose **Change sets** at the top. The list identifies existing change sets by name and
   shows their versions, starting data and creators.
2. To continue existing work, find its name and choose **Open change set**. **Changes in this
   change set** opens first. Choose **See the data with these changes** to reach its lists,
   and check the name in the band before editing. Opening a change set does not publish it.
3. To start separate work, choose **New change set**. Enter a **Name**
   that helps other people recognise the work. **Options** shows the starting point, today's live data. A **Model version** choice appears there when you have Model release access and another release is available. Keep the workspace's version for ordinary corrections; coordinate a different choice with a model administrator.
4. Choose **Start change set**. The new set opens with a copy of the current live data.
   If creation is refused, read the message and resolve the named problem before retrying.
   Choose **Cancel** if you do not intend to create it.

![The change-set list with controls to open existing work or start a new set](/docs/screens/change-sets-list.png)

*Above: Network in the Graubünden workspace lists December 2026 timetable change. Open change set continues that work; New change set starts a separate proposal.*

If creation controls are unavailable, check your access with a workspace administrator. Opening
and reading an existing set does not itself give permission to change or publish it.

## Make the changes

1. Check the orange **Change set** band. It names the intended set, its number of changes
   and state. Open **Details** for its creator, creation time, version and model. If the band
   says **Live**, open your change set
   before making staged corrections.
2. Choose a collection and find a record. [Correct its fields](/docs/guide/use/correct-a-record/)
   and save using the ordinary record controls. Check that the saved values appear in the
   change set, then repeat for the other records in your proposal.
3. If you switch applications or inspect **Live**, check the banner again before the next edit.
   Return to the named change set to continue preparing it. Later live corrections do not
   refresh its starting copy.
4. If a save is refused, read the message and review the current record or change-set version
   before retrying. If the band says **waits for approval**, open **Details** for the submission
   and withdraw the request before editing.

![An open change set with its name, context banner and preparation controls](/docs/screens/change-set-open.png)

*Above: December 2026 timetable change is open over Stops in Network. The orange banner shows 11 changes and offers Details, Review changes, Publish and a menu for further actions.*

## Review and validate

1. Choose **Review changes** in the banner. On **Records**, inspect every intended addition,
   change or removal. Expand a row with its arrow to compare the before and after values.
   Check names and paths to confirm that you changed the intended records.
2. Choose **Relationships** and review the connection changes too. If a long review is hard to
   inspect, use **Filter** to narrow it, then remove the restriction to check the remaining work.
   An empty filtered review does not mean the whole proposal is empty.
3. Choose **See the data with these changes** to correct anything unexpected. Save those corrections and
   review again before proceeding.
4. Open **More change set actions** (⋯) and choose **Validate now**. If problems are reported, use the named records and reasons
   to correct them in the change set, then validate again. Do not proceed while problems remain.
5. Check for **Change set validation passed**. You can also go straight to **Publish**, which validates the current proposal before asking for confirmation. After further edits, the next publication attempt checks them again.

![The record review with changed fields, record paths and a Relationships tab](/docs/screens/change-set-review.png)

*Above: the timetable change's Records tab lists stops with Changed: Valid to (exclusive).
The arrows open the differences; Relationships provides a separate connection review.*

If publication remains unavailable after validation, read the banner for a model-version or
approval requirement and check your permissions. If **Submit for publication** is offered,
follow [Approve a change set](/docs/guide/use/approve-a-change-set/#submit-your-work). Submission leaves
the proposal waiting for a decision; it does not make the changes live.

## Publish

These steps apply when **Publish** is offered. When approval is needed, the banner
instead offers **Submit for publication**. Follow [Approve a change set](/docs/guide/use/approve-a-change-set/)
for submission, corrections and the approver's decision. See
[Inbox and approvals](/docs/use/inbox-and-approvals/) for the rules and notices.

1. Choose **Publish**. refiroo checks the proposal first. If it fails, nothing is published; use the reported problems and record links to correct it. A passed check opens **Publish this change set?**.
2. Read the confirmation. It names how many records and relationships become live, explains that unrelated live changes stay, and that a conflicting live edit publishes nothing. Follow **Review changes** if you need another look. Choose **Cancel** if you are
   not ready; the change set stays available for preparation.
3. To apply the reviewed changes, choose **Publish** in the confirmation. Wait for
   the result. Success is reported as **Published as Publication** followed by its number.
   Check the changed records in **Live** and find the resulting snapshot under **Publications**.
4. If publication is refused, read the reported reason. For conflicts, compare the named records
   with **Live** and agree which corrections are needed before changing the proposal. Review
   and validate the revised work before attempting publication again. A conflict or failed
   check publishes nothing; the proposed work remains available.

![The publication confirmation after validation has passed](/docs/screens/change-set-publish-confirm.png)

*Above: December 2026 timetable change has passed validation and its confirmation is open.
No publication has been confirmed in this screenshot; Cancel leaves it unpublished.*

An intervening live edit can still prevent publication after validation. See
[Publishing and intervening live work](/docs/use/change-sets/#publishing-and-intervening-live-work)
for what conflicts and what is preserved. A refusal needs review before another attempt.

## Discard work you no longer need

1. Open the change set and check all its proposed changes, including work by colleagues.
   If it is waiting for approval, its submitter or an approver must **Withdraw request** first.
2. Open **More change set actions** and choose **Discard**.
3. Read **Discard this change set?**. **Discard change set** removes all staged work in it.
   Choose **Cancel** to keep it. Live records and existing publications stay unchanged.
4. If the action fails, read its reason and refresh the change set before trying again.
   There is no undo for discarded work; a fresh change set does not recover those edits.
