---
title: Install and activate a release
description: Review a draft, choose one workspace and confirm installation and activation safely.
reader: model-admin
---

Apply a checked model to one workspace. You need model authoring to prepare the draft and
**Model release** in the target workspace; creating a new workspace also needs **Workspace
administration**. Read [Releases](/docs/model/releases/) and
[fix draft issues](/docs/guide/model/fix-issues-before-installing/) before confirming.

## Install from the editor

1. Open the draft and choose **Install and activate…**. Read the confirmation; opening it alone
   installs nothing.
2. Check **Release key**, **Version** and **Name**. Keep the key when releasing another version of
   the same model. Choose a version not already used for different definitions. The draft's edit
   number is not this version.
3. Under **Activate into**, choose **An existing workspace** and select it, or **A new workspace**
   and complete its details. Read the workspace name carefully: another workspace may run another
   model. The choice affects this target alone.
4. Review **What changes against** the base release, **Valid**, stored-data compatibility and
   **Consumer APIs**. Resolve blocking issues before continuing. A different-model workspace may
   be checked only when activation is attempted; its selection is not a promise its records fit.
5. Confirm with **Install … and activate in …**, or **Install … and create …** for a new workspace.
   Wait for the outcome. **Cancel** leaves the draft saved without installing or activating it.

![Install and activate confirmation with release identity, workspace and compatibility checks](/docs/screens/model-install-dialog.png)

*Above: Guide draft proposes release 1.0.1 for Graubünden, adding Step-free access and Inspected by.
The captured dialog was cancelled: neither installation nor activation happened.*

A successful installation fixes the release's content; the draft continues as the next editable
version. If the result says **Installed, not active**, keep the installed release and resolve the
reported activation problem. Do not assume installation was undone.

## Apply from a workspace

1. On **Settings**, **Workspaces**, open the intended workspace and choose **Edit model**.
   Confirm **Applies to** in the editor header, make the changes and choose **Apply to this workspace…**.
2. Read the workspace's current model, **What changes in the model**, data compatibility and
   **Consumer APIs**. Expand **Becomes release** to review the release identity where shown.
3. Read **Change sets left on** the old version. They stay pinned to that release and cannot be
   published until moved to the new one or discarded. Check **Not changed** for the other workspaces.
4. If **Your records stay as they are** is shown, confirm **Apply to** the named workspace when ready.
   If **Some records must move first** appears, choose **Preview what happens to the records…**
   and review that separate migration before confirming it. Opening the preview is not applying.

![Workspace apply dialog showing changes, compatible data and change sets left behind](/docs/screens/model-workspace-apply-dialog.png)

*Above: applying Guide draft to Graubünden leaves Default unchanged and names December 2026 timetable
change as remaining on release 1.0.0. The dialog was cancelled.*

## Activate an already installed release

1. Open **Settings**, **Model**, choose the model, then **Releases** and the intended version.
2. Check its identity, workspace use and installation details. Use **Create draft from release**
   if its definitions need changing; the release itself is immutable.
3. Choose **Activate in a workspace…**, select the target and read its compatibility result and
   change sets left behind. A release can be activated only when that workspace's existing data fits.
4. Confirm **Activate** with the displayed version and workspace when ready. If activation is
   refused, correct the named issue and recheck. A stale-state refusal needs a refreshed workspace
   state and another review, not repeated confirmation of the old result.

![Installed release page with workspace use and activation and draft actions](/docs/screens/model-release-detail.png)

*Above: release 1.0.0 of the Graubünden model is immutable and already run by Graubünden.*

![Activation dialog checking one selected workspace and listing other workspaces unchanged](/docs/screens/model-release-activate-dialog.png)

*Above: the selected target is Default, which runs RDM Starter Model; Graubünden stays unchanged.
The captured activation was cancelled.*

After success, open the target workspace and check its applications and a changed type's page.
Other workspaces keep their models. If an already open page says its model changed, reload it
before editing records. Review any left-behind change sets through the
[change-set process](/docs/use/change-sets/) before their next publication.

## Read the activation result

| Result | Next action |
| --- | --- |
| Compatible with the workspace's data | Review the named workspace and confirm activation when ready. |
| A migration is needed | Open **Preview the migration…**, review conversions, removals and items to fix, then confirm only an acceptable result. |
| A different model | Review this destination carefully; compatibility is checked when activation is attempted. |
| A consumer API needs a higher contract version | Coordinate the contract change and raise its version in a draft before rechecking. |
| Could not be checked | Read the failure, correct its cause and check again; it is not a successful compatibility result. |

The install dialog says **Comparing with the base release** where the draft has one. That
comparison can differ from the target workspace's current release; read the separate data and
consumer checks too. Cancelling a preview changes nothing. After a stale preview, review a fresh
one instead of confirming the old counts.
