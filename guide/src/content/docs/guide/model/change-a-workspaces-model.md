---
title: Change a workspace’s model
description: Choose an installed release and read its data and consumer compatibility checks.
reader: model-admin
---

Choose an installed release for one workspace with **Model release** there. The release must
be usable on this instance. See [Releases](/docs/model/releases/) and [Migrations](/docs/model/migrations/).

1. Open **Settings › Model**, select the model and its **Overview**. Beside the workspace choose
   **Change model…**. Alternatively open a release and choose **Activate in a workspace…**.
2. Check **Workspace** and its current model. Under **Release**, choose the target version.
   Expand another model only if you intend to replace the workspace's definitions with it.
3. Wait for the check and read its result:

   | Result | What to do |
   | --- | --- |
   | Compatible with the workspace's data | No record, value or relationship needs migration. Review the destination before activating. |
   | A migration is needed | The same model's definitions require data changes. Use the offered migration preview. |
   | A different model | The different model does not fit the data unchanged. Review its reasons and the migration preview where available. |
   | A consumer API needs a higher contract version | Correct or version the named contract in a draft before activating. |
   | Could not be checked | Correct the stated failure and check again. This is not a compatible result. |

4. Read the listed open change sets left on the old release and other workspaces left unchanged.
   If compatible, confirm activation. If conversion is needed, use **Preview the migration…**
   and follow [Migrate a workspace](/docs/guide/model/migrate-a-workspace/).
5. After success, reopen the workspace and inspect its applications. Reload a page reporting a
   model change before editing. A bookmark to a missing application or type shows **Not in this
   model**; choose a collection declared by this workspace's current model.

![Activation dialog selecting a release for one workspace](/docs/screens/model-release-activate-dialog.png)

**Not activated** means the switch failed. Read why, refresh the workspace and check again.
Choosing an older version runs the same checks; it does not restore older record values.
