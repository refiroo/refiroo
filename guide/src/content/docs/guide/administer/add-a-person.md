---
title: Add a person
description: Create a local account, pass on its first-password link and grant access.
reader: access-admin
---

Use this guide for someone who signs in with a refiroo password. You need
**Security administration**. For ordinary password sign-in, local sign-in must be on. Creating an account alone does not give it the retained recovery route when local sign-in is off. For someone using your organisation's
provider, first sign-in creates their person instead; see
[People and groups](/docs/administer/people-and-groups/) for that route and linking existing accounts.

## Create the account

1. Open **Settings › Security › People**. Check the Active list or search by name, username
   or e-mail to avoid creating another account for the same person. Check **Deactivated**
   too; **Restore** reactivates an existing person with their retained roles and groups.
2. Choose **New person**. Enter **Username**, the sign-in name without spaces. It cannot
   change later. Use up to 150 characters, with a dot, dash or underscore instead of spaces.
3. Enter **Name**, the display name used in lists and history, up to 200 characters.
   Enter **E-mail (optional)** if you have it. An e-mail address is not required for a local account.
4. Choose **Create and make a password link**. **Cancel** leaves the person uncreated.
   If a field is refused, correct the named problem and submit again.

![New person dialog with Username, Name and optional E-mail](/docs/screens/admin-person-new.png)

*Above: the reference instance's empty New person dialog, opened but not saved.*

## Pass on the password link

1. When **Pass on the password link** opens, copy the link using its copy control.
   Give it to the intended person through your agreed private channel. They choose their own password.
2. Read the expiry shown in the dialog. The link works once and a newer link replaces it.
   Choose **I have copied it** only after saving or passing it on; it is not shown again.
3. With mail configured and an address on the person, creation also queues the link for mail. The dialog reports that outcome. **Mail it to …** is available to make and mail a replacement.
   Mailing makes a replacement link, also shown in the dialog. Use that newest link rather
   than the earlier copy. Check the dialog's sent-to message; do not assume mail was sent.
4. If the person was created but no link dialog appeared, open their page and choose
   **Make a password link** (or **Reset password** once a password is set). Do not create them again. This click makes the link
   immediately, with no confirmation before it.

![One-time password-link dialog with copy control, expiry and acknowledgement](/docs/screens/admin-person-reset-password.png)

*Above: a reset link for fictional Rita Approver, not a newly created person. Creation uses
the same link dialog. Its example address is not one to reuse.*

## Give them access and check the result

1. On their page, inspect **Roles**. A new person has none. Follow
   [Grant a role](/docs/guide/administer/grant-a-role/) for the intended workspace, or add them
   to a [group](/docs/guide/administer/manage-a-group/) that holds the required roles.
2. Ask them to open the link and set a password. A rejected password gives a reason;
   they must choose another. An expired, replaced or used link needs a new **Reset password** link.
3. Ask them to sign in and check the expected workspace and actions. If the instance requires
   a second factor, they set one up before their session starts. If the workspace is missing,
   review the grant's workspace and whether its role includes Browse.

Creating a person does not send them data or grant access automatically. Keep the username
stable; use **Edit…** for later name or e-mail corrections.

For delivery problems, check [Mail › Messages](/docs/administer/mail/#messages-and-retries). A queued message can still fail; the one-time dialog is not proof of receipt.
