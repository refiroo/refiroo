---
title: Migrations
description: Review conversions, renamed definitions and removals before switching a workspace’s model.
reader: model-admin
---

Use a migration when a workspace's records do not fit a selected model release unchanged.
The preview checks every record and lists conversions, type changes, removals and items that must
be fixed. Nothing changes until you confirm. You need **Model release** in the workspace;
background jobs and model administration must be available. Publication also needs the normal
data permissions and any required approval.

Start with [Change a workspace’s model](/docs/guide/model/change-a-workspaces-model/), then
[Migrate a workspace](/docs/guide/model/migrate-a-workspace/).

## What the preview means

| Outcome | What to review |
| --- | --- |
| Converted | Values changed to the target definition's value type. Inspect before and after. |
| Type changed | Records kept under a new type, with their IDs and history. |
| Removed | Records, values or relationships lost if you explicitly accept removal. |
| Must be fixed | Items blocking confirmation, such as missing required values or relationships, duplicate unique values or invalid parents. |

For each missing type or field, **Became …** says which target definition replaces it.
**Not kept** removes that type's records and relationships, or that field's values. Choices are
not merely labels: each starts a new preview. The page explains what is kept and what is removed.
Do not accept removal until you have inspected its individual items. While any item
**Must be fixed**, confirmation stays disabled and the loss-acceptance checkbox is hidden.
After those blockers are resolved, a preview with removals offers the acceptance checkbox.

![Migration review with missing-element choices and outcome counts](/docs/screens/model-migration-review.png)

The data conversion and workspace release switch succeed together. A failed execution does not
leave half a migration. A model release installed before this flow can remain installed even
when migration fails. Record history keeps what was removed; that is an audit trail, not an undo button.
Open change sets stay on their previous release until moved or discarded. Publications remain fixed.

## Cancellation, waiting and stale results

**Cancel the preview** stops a running preview; **Cancel** leaves a reviewed one unapplied.
The preview may briefly make writes to the live records it checks wait. Let it finish or cancel
before retrying a waiting edit. Leaving the page alone does not stop its background job.

Confirmation is bound to the reviewed workspace and data versions. After an intervening edit,
publication or model change, a stale-review notice asks for **Preview again**. Nothing was
migrated by the refused confirmation. Review every refreshed outcome before confirming again.
**Not migrated** and **Something went wrong** require reading the failure and correcting its
cause; they are not successful migration results.

## Change sets on another release

A change set can move to **the release its workspace currently runs**. **Move this change set
to …** opens the same review for its content. The page says nothing live changes. Confirmation
converts its content and updates its base and release together against current live records.
Conflicting authored records, relationships or mapping sets block the move. Open the resulting
change set, review it and validate before publishing normally.

Alternatively, **Move … to … and publish…** migrates the workspace to the change set's release
and publishes that change set in one step. The review explicitly says **Then publishes …** and
the confirmation says **Migrate and publish**. Required approval and publication conflicts still
apply; neither migration nor publication succeeds alone. Review the named publication afterwards.

Jobs retain the actual counts and item outcomes, with refused items prominent. Open only links
your permissions allow and compare the actual result with the preview. For moving data between
two workspaces instead, see [Model mappings](/docs/model/model-mappings/).

Value conversion uses supported source and target value-type pairs. A value that has no valid
conversion is listed as a loss; the preview does not invent a conversion for every pair of types.
Inspect those items before accepting removal. Activation can also suspend the selected workspace's
consumer subscriptions that its new contract no longer serves; other workspaces' subscriptions
are unaffected. Coordinate changed contracts with their owners before confirming.
