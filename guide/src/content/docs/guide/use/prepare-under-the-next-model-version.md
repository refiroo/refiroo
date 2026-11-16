---
title: Prepare under the next model version
description: Coordinate a proposal’s model release with the workspace before publishing.
reader: steward
---

A change set can use an installed release while Live still uses another. Coordinate this
with a model administrator. See [Change sets](/docs/use/change-sets/) and
[Migrations](/docs/model/migrations/) for the reviewed conversion process.

1. When creating a change set, open **Options**, then choose **Model version** if your Model release access and the available releases offer a choice. The starting
   records must fit it. A refusal leaves Live unchanged; inspect the named incompatibilities.
2. In an editable change set, use **More change set actions › Change model version** to choose
   a **Target release** where the existing content fits without a conversion. Resolve unsaved
   input before switching. Wait for the new model to load before editing further.
3. If the releases differ, read **This change set cannot be published yet**. The **This change set**
   and **Live data** chips show the two model versions. The bar has no **Publish** or **Submit for
   publication** until they match. In the **Update the change set** card, **Update change set**
   previews converting your proposal to the workspace's release, with no change to Live.
4. Review converted values, changed types, removals and items requiring a fix. Resolve refusals
   and explicitly accept losses before confirming **Move change set**. If the review is stale,
   choose **Preview again**. This move needs background jobs and suitable change-set rights.
   It does not publish: choose **Open the change set to publish it**, then publish as usual.
5. In the **Move the workspace back** card, **Move workspace and publish** previews moving the workspace to the proposal's
   release. It needs model-release and publication rights and follows the same approval policy
   as publication. Have the responsible model administrator review it. **Migrate and publish**
   changes the workspace and publishes together, or does neither.

Only the cards available to you appear. Each card's direction chip shows the move from one
version to the other. If the work is no longer needed, **Discard change set** on the banner
opens a confirmation. Someone who can only view the change set sees the explanation and
version chips, without cards or a discard button.

![A change set under another model version, with two version chips, two action cards and Discard change set](/docs/screens/change-set-model-banner.png)

*Above: the Graubünden reference data in a change set on version 1.8.1 while Live uses 1.8.2.
Compare the two version chips and the directions on the cards. The bar above has no Publish
button; Discard change set is below the cards. No action has been chosen.*

A submitted change set is frozen, including release changes. Its submitter or an authorised
approver must withdraw the request before editing. A changed model reload clears obsolete list
positions and can open another declared view if the old page disappeared. If the release change
succeeded but refreshing failed, reload and check the pinned release before saving; repeating
the move blindly is not recovery.
