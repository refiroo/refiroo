---
title: Make a workspace the default
description: Select the default destination without changing other workspaces’ models or data.
reader: model-admin
---

You need **Workspace administration** and the deployment must allow workspace changes.
See [Managing workspaces](/docs/model/managing-workspaces/) for the default workspace's role.

1. Open **Settings › Workspaces**, then the active workspace you want as the default.
   Read its name, permanent key and model in **Overview**.
2. Choose **More actions › Set as default**. Check the success notice and **Default** mark afterwards.
   The previous default remains a separate workspace with its own records and model.
3. If another administrator changed the default while your page was open, read the notice,
   reload the state and choose again only if your intended change is still correct.
4. Inspect new-workspace creation choices when relevant: **The default workspace’s model**
   now refers to this workspace's release. Existing workspaces keep their selected releases.

![The workspace named Default open on RDM Master with an empty Domains collection](/docs/screens/use-workspace-default.png)

Making a workspace default copies no records and grants no access. The default cannot be retired
or deleted. To take it out of use later, first select another active default.
