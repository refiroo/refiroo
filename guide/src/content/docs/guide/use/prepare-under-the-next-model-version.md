---
title: Prepare under the next model version
description: Coordinate a proposal’s model release with the workspace before publishing.
reader: steward
---

A change set can use an installed release while Live still uses another. Coordinate this
with a model administrator. See [Change sets](/docs/use/change-sets/) and
[Migrations](/docs/model/migrations/) for the reviewed conversion process.

1. When creating a change set, choose **Model version** if a choice is offered. The starting
   records must fit it. A refusal leaves Live unchanged; inspect the named incompatibilities.
2. In an editable change set, use **More change set actions › Change model version** to choose
   a **Target release** where the existing content fits without a conversion. Resolve unsaved
   input before switching. Wait for the new model to load before editing further.
3. If the releases differ, read **This change set uses a different model version**. Ordinary
   publication needs matching releases. **Move this change set to …** instead previews
   converting your proposal to the workspace's release, with no change to Live.
4. Review converted values, changed types, removals and items requiring a fix. Resolve refusals
   and explicitly accept losses before confirming **Move change set**. If the review is stale,
   choose **Preview again**. This move needs background jobs and suitable change-set rights.
5. The alternative **Move … to … and publish…** previews moving the workspace to the proposal's
   release. It needs model-release and publication rights and follows the same approval policy
   as publication. Have the responsible model administrator review it. **Migrate and publish**
   changes the workspace and publishes together, or does neither.

A submitted change set is frozen, including release changes. Its submitter or an authorised
approver must withdraw the request before editing. A changed model reload clears obsolete list
positions and can open another declared view if the old page disappeared. If the release change
succeeded but refreshing failed, reload and check the pinned release before saving; repeating
the move blindly is not recovery.
