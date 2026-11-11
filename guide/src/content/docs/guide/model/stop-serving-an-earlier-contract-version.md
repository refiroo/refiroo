---
title: Stop serving an earlier contract version
description: Announce an earlier consumer contract’s end, remove it in a draft and activate the change.
reader: model-admin
---

Use this task after consuming teams have moved off an earlier version. You need **Model authoring**
to edit and **Model release** in each workspace where you activate the change. Stopping a version
removes its reads without deleting records or stopping the other versions. Read
[Earlier versions](/docs/model/consumer-apis/#keep-an-earlier-version-available) before starting.

## Announce the end date

1. Open a draft based on the workspace’s active release. Select **Consumer APIs**, the API,
   then **Types and related**. In **Earlier versions**, check **Version** and **Superseded**
   to identify the version you intend to retire. This table does not stop the current version;
   [raise it first](/docs/guide/model/raise-a-contract-version/) if it needs a replacement.
2. Agree a notice period with every consuming team, including owners of webhook receivers.
   You choose that period; refiroo does not enforce a minimum for your consumer contracts.
3. Select that row's **Sunset day** value or its pencil. In **Sunset day (YYYY-MM-DD)**,
   enter the agreed calendar date and choose **Save**. Clear it and save to withdraw the
   announcement; the table shows a dash when no day is set. A date that is not a valid
   calendar day stays in the form with **Not saved** and the reason; the previously saved
   value remains unchanged. Correct it and save, or **Cancel**. The date announces the end
   in the response's Sunset header after activation; the version stays served until you
   stop it explicitly, whatever the day.
4. Review and [install and activate](/docs/guide/model/install-and-activate-a-release/) the
   announcement in the intended workspaces. Integrators then see the planned end date in
   the contract’s documents and responses. The date alone never turns the version off.

![Earlier versions with Superseded, Sunset day and Stop serving](/docs/screens/model-consumer-earlier-versions.png)

## Remove the version when consumers are ready

1. Open a new draft from the release that still serves the earlier version. Check the API
   and the intended row in **Earlier versions** again.
2. Choose that row’s **Stop serving**. Read the confirmation naming the version and warning
   that its consumers lose access once the draft is active. Choose **Cancel** to keep the
   row, or confirm **Stop serving** to remove it from this draft. Live workspaces are unchanged.
3. If you removed the wrong row, choose **Undo** or use the draft’s **History** to undo that
   saved step. Check that the version and its sunset day are back before continuing.
4. Review **Issues**, then open **Install and activate…**. Its Consumer APIs list names the API
   and says it **stops serving version …** and its consumers get `CONTRACT_VERSION_NOT_FOUND`,
   not **Compatible**; the activation dialog of each workspace says the same. Confirm that
   this is the removal you agreed. A finding that a kept version changed needs repair;
   raising the current version again does not repair it.
5. Install and activate the release in each intended workspace. Installation alone does
   not stop reads. Check each workspace’s active release; a workspace left on the old
   release keeps serving the version.
6. Ask the integration administrator to review affected webhooks with their receiver owners.
   A webhook whose accepted version stopped is suspended. Resuming accepts the current
   version after its events and filters pass validation; the receiver must be ready for
   that shape. Follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).

An earlier version’s reads and change feed stop after activation. Keeping an older release
installed or an older publication does not keep that route available. Other served versions
continue reading the same stored data.

## Restore service after activation

Draft **Undo** alone cannot change a live workspace. Prepare a release that retains the original
definition and its model sources again, review its compatibility against the workspace, then
activate it. Do not reuse the earlier number for a different contract. Check suspended webhooks
separately; a restored route does not itself resume delivery. If the required source fields or
relationships have been removed, restore them too or agree a different recovery with the consumers.
