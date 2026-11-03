---
title: Manage a group
description: Create a group, add or remove members and grant shared access.
reader: access-admin
---

Use a group when several people need the same roles. You need **Security administration**.
See [People and groups](/docs/administer/people-and-groups/) for how local and provider groups differ.

## Create a local group

1. Open **Settings › Security › Groups**. Use **Search groups** (**Group name**) first to see whether the
   intended group already exists. Choose a result to manage it, or **New group** to create one.
2. Enter **Name** and **Description (optional)**. The description can explain who belongs
   and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
3. Choose **Create group**. The group opens with its roles and members. **Cancel** closes
   without creating it. If saving fails, read **Not saved**, correct the problem and retry.

![Empty Groups list with search and New group](/docs/screens/admin-groups.png)

*Above: the reference instance has no groups yet.*

![New group dialog with Name and optional Description](/docs/screens/admin-group-new.png)

*Above: no provider supplies groups on the reference instance, so the dialog shows the local fields only.*

## Add people and shared roles

1. On the group's page choose **Add members**. In **Search and tick**, search by name,
   username or e-mail and tick the intended people. Already-present and deactivated people
   cannot be selected for addition.
2. For a longer list, choose **Paste a list**. Enter **Usernames or e-mail addresses**,
   one per line or separated by commas or semicolons, up to 500. Choose **Check the list**
   (or **Check … lines** when a count appears). Review the results before adding. Resolve
   unmatched or ambiguous entries rather than choosing someone by guesswork.
3. Review the selected people and choose **Add members**, or the button showing the number
   to add. Check the resulting Members list and success message. A person deactivated while
   the dialog was open can be left out; read the reported count.
4. Choose **Grant** in the group's roles section. Follow
   [Grant a role](/docs/guide/administer/grant-a-role/) to select roles and workspaces.
   Every member receives that source of access; adding members alone grants nothing if the group has no roles.
5. Open a member's People page to check that the role appears as coming through this group.
   The access applies on their next request; they do not need a new account.

## Change or remove membership

1. Find the group by name and select it. Choose **Rename…** to change its name or description,
   then **Save**. This does not change who belongs or the group's grants.
2. To remove a local member, use their row’s **Remove**. For several, tick their rows, or use **Select every member shown**, and
   choose **Remove … from the group**. **Clear** clears the selection without removing anyone. Check the resulting list. Their direct roles and
   roles from other groups remain.
3. To remove the whole group, choose **Delete group** and read the confirmation. Confirm
   **Delete group** only if its memberships and all its grants should be removed.
   The people remain and keep their direct grants.

A change that would leave no active person holding Security administration is refused, including a grant through this group. Removing several members is all-or-nothing: if one removal would lose the last administrator, none of the selected members is removed. Establish another
administrator before removing that membership or deleting that group. If details changed
while you were working, reload and review the current members and grants before retrying.

## Use a provider group

When a configured sign-in provider supplies groups, **New group** offers **From a sign-in provider**.
Choose it, select **Provider** and enter **Claim value** exactly as supplied by the sign-in
administrator. This is the provider's group identifier, which need not be its readable name.
Create the group and grant roles before anyone signs in if access must be ready on their first visit.

A provider group's page shows **Members seen**. Membership is updated at each person's
provider sign-in; people who have not signed in are absent from this list. Make membership
changes in the provider, not with local Add or Remove controls. The group name can be
made readable in refiroo without changing the provider's identifier.

For a provider group, **Members seen** can be empty even when the provider has members who have not signed in yet. Its roles can already be granted. Local group deletion and bulk removal do not change membership at the provider.
