---
title: People and groups
description: Manage the people who sign in, their group memberships and what happens when access ends.
reader: access-admin
---

Use **Settings › Security › People** to manage people, and **Groups** to give several
people the same roles. You need **Security administration**, held by the predefined
Security administrator role. That role manages access; it does not itself allow reading workspace data.

## People and their sign-in

Use **Search people** (**Name, username or e-mail**) to find a person. The list also shows their roles. **Active** and **Deactivated** show
separate lists and counts. Select someone to see their sign-in methods, roles, groups and recent activity.
A person has one identity in refiroo and can hold different roles in different workspaces.

![People list with Active and Deactivated filters and no person selected](/docs/screens/admin-people.png)

*Above: Guide Admin and fictional person Rita Approver are active in the reference instance.*

A local account uses a username and password. **New person** creates the person and makes
a one-time link for them to choose a password. If mail is configured and they have an e-mail address, it is also queued for mailing. It grants no roles. The username cannot
change; **Edit…** changes the display name and optional e-mail address. Follow
[Add a person](/docs/guide/administer/add-a-person/).

A person signing in through the organisation's provider is created on their first sign-in.
Their name and e-mail follow the provider on subsequent sign-ins. An e-mail match alone
does not join that sign-in to an existing account. Roles come from grants to the person
or to their provider groups; first sign-in does not automatically grant access to data.

For an existing local account, open the newly created provider person's page and choose
**Link to an existing person…**. Select the existing person and confirm the named link.
The provider sign-in and provider memberships move to the existing person, whose roles
and history continue. The new person is deactivated and their sessions end. Linking is refused if that new person
already has a password, direct roles or local group memberships; resolve those before retrying.
Follow [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) for the complete task. **Unlink…** removes a mistaken provider link. Their next provider sign-in creates a separate person again.

## A person's page

![Person detail with sign-in methods and workspace role](/docs/screens/admin-person-rita.png)

*Above: fictional Rita Approver holds Data owner directly in Graubünden and is not in a group.*

**Roles** shows where each role applies, any write restriction and whether it comes directly
or through a group. **Groups** shows memberships. These are separate sources of access:
removing a direct role does not remove the same role inherited from a group.
See [Roles and grants](/docs/administer/roles-and-grants/).

**Password: Set** means the person has a local password; **Not set yet** means they do not. **Make a password link** is offered before a password is set; afterwards **Reset password** makes a new link. Both act immediately, without a confirmation first.
The next dialog shows it once, its expiry and whether it was mailed. A newer link replaces
the previous one. Using it signs the person out everywhere; making it does not itself do so.
It does not remove an authenticator app or passkey. For device problems, follow
[Help someone who lost a device](/docs/guide/administer/help-someone-who-lost-a-device/).

**Keeps local sign-in** preserves a password sign-in route even when local sign-in is off
for everyone else. Reserve it for people responsible for recovery if the provider fails.
Changing it asks for confirmation. The last active person keeping local sign-in cannot
lose that route while local sign-in is off. See [Sign-in](/docs/administer/sign-in/).

## Groups

A role granted to a group applies to every member. Leaving the group removes that source
of access on the next request. Other group and direct grants continue to apply.

![Groups list with no groups and a New group button](/docs/screens/admin-groups.png)

*Above: no groups have been created in the reference instance.*

Local group membership is managed here. A provider group's membership is updated when
each person signs in through that provider. Its **Members seen** list contains only people
who have signed in; it is not the provider's full membership list. Change those memberships
in the provider, and grant the group's roles in refiroo. You can create a provider group
ahead of first sign-in when a provider is configured to supply groups.

**Rename…** changes a group's name and description. **Delete group** asks for confirmation,
then removes its memberships and grants. It does not delete people or their direct roles.
Follow [Manage a group](/docs/guide/administer/manage-a-group/).

## When someone leaves

Choose **Deactivate** on the person's page and confirm. Their next request is refused and
they cannot sign in. Their roles and groups remain, and history retains their name.
Their records, change sets and publications are not deleted. Queued or running jobs lose
the right to continue at their next permission check. Another authorised person can deal
with the remaining work.

To restore access, find them under **Deactivated** and choose **Restore**. Review retained
roles and groups before restoring them. People are never deleted.

**Sign out everywhere** instead ends all their refiroo sessions after confirmation but
allows them to sign in again. Use deactivation when they must no longer have access.
For a provider leaver, deactivate them in refiroo too: an existing refiroo session does not
recheck provider membership on every request.

refiroo refuses changes that would remove the last active person holding Security administration, including access through a group. A client with that role does not replace a human recovery administrator.
If another administrator changed a person while the page was open, the current details
are reloaded with a warning. Review them and choose the action again.

The person's **Recent activity** is grouped by day and can be narrowed to **Signing in**,
**Roles and groups** or **Account**. It starts with ten entries, then reads 20 more at a time;
**Show fewer** shortens it. **See changes** instead opens their data changes in workspaces you
may browse. [Who changed what](/docs/administer/audit/) explains which view answers which question.

For several group members at once, use **Search and tick** or **Paste a list** and check the
usernames and email addresses before adding. Unmatched lines need correcting. Several ticked
members can be removed together. Provider groups are shown under their provider; change their
membership there rather than in the local member controls.

## Edit details and memberships

**Edit…** opens the named person’s form with **Name** and **E-mail (optional)**. Choose **Save** or **Cancel**. The username stays fixed. Provider-supplied name and e-mail follow the provider at sign-in.

Under **Groups**, **Add to a group** opens a picker; choose the intended local group and **Add to the group**. A group chip’s remove control removes that local membership immediately. **Not in any group.** means there are no memberships shown. Provider memberships are managed at the provider.

On the Groups list, **Search groups** searches **Group name**. Entries show the source and member count; a provider group’s count is people seen signing in. **No groups yet.** and no match for a search are different states: clear the search before creating a duplicate.

Removing several selected local members is all-or-nothing. If it would remove the last active human Security administrator, nobody in that removal is removed. Arrange another administrator before retrying. Adding several members instead reports each result, so check which people actually joined.

For outgoing messages and forgotten-password recovery, see [Mail](/docs/administer/mail/). For retained recovery accounts, follow [Turn off local sign-in](/docs/guide/administer/turn-off-local-sign-in/).
