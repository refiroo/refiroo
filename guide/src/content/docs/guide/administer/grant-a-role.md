---
title: Grant a role
description: Grant a role to a person, group or client, choose its reach and check inherited access.
reader: access-admin
---

You need **Security administration**. Choose a role for the actual task using
[Roles and grants](/docs/administer/roles-and-grants/); administrative roles do not automatically
allow reading or editing data.

## Open the grant dialog

1. Open **Settings › Security › People**, **Groups** or **Clients** and select the recipient.
   Choose **Grant** in their roles or access section. The recipient is already chosen.
2. Alternatively, open **Settings › Workspaces**, select the workspace and choose **Access**,
   then **Grant**. Choose **Who** by searching for the person, group or client by name.
   Check the kind as well as the name before selecting them.
3. For a client, choose **Roles** under **What** if you are granting management access.
   **Consumer APIs** is a separate kind of grant; see [Create a client](/docs/guide/administer/create-a-client/).

![Grant dialog with role selection and workspace or whole-instance scope](/docs/screens/admin-grant-dialog.png)

*Above: the dialog for fictional Rita Approver has no role selected and is open but unsaved.
Check the selected workspace's displayed name rather than assuming the default is the one intended.*

## Choose what and where

1. Tick the role or roles. Read **May** beside each role to check its action groups.
   More than one role adds those permissions together.
2. Under **Where**, choose **Workspaces** and use **Add workspace** to select the intended
   workspaces. Remove any initially selected workspace that should not receive this grant.
3. Choose **The whole instance** only for access that should apply to every workspace,
   including future workspaces. Roles greyed out for workspace grants require this reach.
4. If one role is selected in one workspace and narrowing is offered, review
   **Narrow what they may change**. Keep **Everything in …** for all permitted writes there,
   or choose **Only these applications and record types** and add the intended entries.
   This never restricts reading. To narrow several grants, make them one role and workspace at a time.
5. Read the summary in **Grant access** and choose **Grant**. **Cancel** before submitting makes no grants. Closing after some were saved does not undo those grants. If several grants are
   attempted and some fail, the dialog lists the failures and says whether the others were
   made. Successful grants remain. Failed choices stay selected with their reasons; correct them and use **Try again**.

## Verify or remove access

1. Check the recipient's table: **Where**, the role, any **Narrowed to (writes)** entries
   and **Through**. For a person, group membership can supply additional roles.
2. Open the workspace's **Access** tab to see the combined result. Use the search and
   **Role** or **Kind** filters to locate the recipient. Whole-instance grants are marked there.
3. To remove a direct grant, choose its **Remove** and follow any confirmation shown.
   For an inherited role, change the group's grant or the person's membership at its source.
   Removing one grant does not cancel another grant that allows the same work.
4. Ask the recipient to check the next action in that workspace. Changes apply on the
   next request. If they still have wider access, inspect direct grants, all groups and
   whole-instance grants before concluding removal failed.

![Person's roles showing direct grants for every workspace](/docs/screens/admin-grants-person.png)

*Above: Guide Admin's six grants are direct. A group-supplied role would identify its source in Through.*

The last active Security administrator cannot be removed. If a refusal says the recipient
or grant changed meanwhile, reload and review the current state before choosing again.

For the complete narrowing task, follow [Narrow a grant to record types](/docs/guide/administer/narrow-a-grant-to-record-types/). For clients reading a declared interface, use [Grant a consumer API to a client](/docs/guide/administer/grant-a-consumer-api-to-a-client/) instead of adding a management role.
