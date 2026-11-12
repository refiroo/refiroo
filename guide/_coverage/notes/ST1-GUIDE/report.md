# ST1-GUIDE: wrap-up (added by the delivering session)

- Wave: `guide/_waves/ST1-GUIDE.md`, run `ST1-GUIDE/2026-11-12T10-20-11Z`, Codex (gpt-6.1-sol), one turn, 7m15s. Tokens: in 3,376,209 (cached 3,232,640), out 16,352 (reasoning 2,515), total 3,392,561. No usage limit hit.
- Pages: 72 assigned, 44 changed, 28 unchanged (per page below).
- `npm run verify` in `guide/`: build (257 pages), check (terms, brand, sidebar) and inventory passed; `check:links` passed on its own (257 pages). `check:coverage` FAILED with 11 uncovered inventory entries: `menu:ModelEditor.tsx:canvas` and ten `menu:WorkbookCanvas.tsx:*` entries. They are the same 11 entries as in `_coverage/notes/UX2-GUIDE/before-uncovered.md` (recorded before this wave): another session's workbook-canvas work, not caused by this wave. Left as is.
- Outdated screenshots: 88 files (table at the end of this report, with the pages that use them). Not retaken. Docker reference instance untouched.

# ST1-GUIDE report

All 72 assigned pages checked: 44 edited, 28 unchanged. No commits or git state changes. Screenshot files and their Markdown references were preserved.

## Validation

`GUIDE_OUT=_build/ST1-GUIDE npm run build` in `guide/` passed (257 pages, first run 4.83 seconds). Final rebuild after the last wording correction passed: 257 page(s) built in 4.61s. Output is recorded in `build.log`. The build reports a `/404` route-priority warning and completes successfully. No browser runtime or image-by-image visual acceptance was performed.

## Differences, uncertainties and possible problems

- Import profiles has no **Load more profiles** or **Show more** button. `ImportProfilesPage.tsx` supplies `onEnd` to `EntityList.tsx`, whose intersection observer loads more on scroll. The page now says to scroll.
- The brief and changelog generalise log footers as “n of m”. `LogFoot` only shows a total when supplied. AI Calls, Agent access, Jobs, Signing keys and Changes pass no total and show “n calls”, “n jobs”, “n changes”, etc. In particular a person’s Changes does not show “n of m changes”. No promise of a total was added.
- The brief and changelog generalise logs as time first with totals above. Jobs still starts with **Job** or **Job or group**, with **Created**/**Finished** or **Latest** later. Signing keys starts with **Key ID**. Agent client and registration tables start with the name. Their prose was not changed to claim otherwise.
- `ModelReleaseDetail.tsx` heads the comparison **Changes in this release** and the readiness check **Workspaces running** followed by the model key. **Release history** and **Activation check** remain explanatory text, not those section headings. Affected prose was corrected.
- Older pages still name **Settings › Data operations › Jobs** or **Import profiles**. `navigation.ts` places Jobs under **This instance** and Import profiles under **Workspaces and models**. These group names predate ST1; the brief says no route changed and requests only ST1 corrections. They need a separate navigation correction.
- Some existing screenshot alt text describes the old layout (“no person selected”, profile deletion “buttons”). The assignment forbids changing screenshot references, so their full Markdown was preserved.
- Another wave changed `use/workspaces.md` from “sheet” to “dialog” during this run. This wave made no edit to that page, reports it as no change and preserved the other edit.
- No runtime defect was established. The broad log-layout claims above differ from the delivered code. Screenshot recapture and browser verification remain outstanding.

## Per-page changes

Paths are relative to `guide/src/content/docs/`. Old and new blocks retain the affected paragraph or step when a sentence spans lines; unchanged surrounding words provide context.

### administer/clients.md

Old:

> You need **Security administration** to manage **Settings › Connections › Clients**.
> Use **Search clients** (**Name**) to search the list, which separates **Active** and **Deactivated** clients and shows
> when a client last authenticated, or **No token yet** when it has not.

New:

> You need **Security administration** to manage **Settings › Connections › Clients**.
> Use **Search clients** (**Name**) to search the list, which separates **Active** and **Deactivated** clients and shows
> when a client last authenticated, or **No token yet** when it has not. Open a row for the client’s page; **← Clients** on its first line returns to the list.

Old:

> **Deactivate** asks for confirmation. The client cannot authenticate again and its existing
> access is refused at the next request. Its grants and name remain for history. It is never
> deleted. Use **Restore** from the Deactivated list to reactivate it after reviewing those grants.
> 
> **See changes** opens its data changes in workspaces you may read. **Recent activity**
> shows security events; **Webhooks it created** lists subscriptions you administer.
> A failed section offers **Retry**. Treat a load failure as unavailable information, not an empty list.
> See [Who changed what](/docs/administer/audit/) for the distinction between data and security history.

New:

> **More actions › Deactivate** asks for confirmation. The client cannot authenticate again and its existing
> access is refused at the next request. Its grants and name remain for history. It is never
> deleted. Open the client from the Deactivated list and use **Restore** to reactivate it after reviewing those grants.
> 
> **More actions › See changes** opens its data changes in workspaces you may read. **Recent activity**
> shows security events; **Webhooks it created** lists subscriptions you administer.
> A failed section offers **Retry**. Treat a load failure as unavailable information, not an empty list.
> See [Who changed what](/docs/administer/audit/) for the distinction between data and security history.

### administer/permissions-reference.md

No change.

### administer/api-reference-and-consumer-api-pages.md

No change.

### administer/signing-keys.md

No change.

### administer/sign-in.md

Old:

> For the administrator’s tasks, follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/), [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) and [Turn off local sign-in](/docs/guide/administer/turn-off-local-sign-in/). On the provider catalogue, **No provider yet: people sign in with a password.** describes an empty list, not a connection failure. Saved provider details include separate Enable, Disable and Delete actions; disabling or deleting one ends the sessions it started.

New:

> For the administrator’s tasks, follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/), [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) and [Turn off local sign-in](/docs/guide/administer/turn-off-local-sign-in/). Open a provider’s row for its own page; **← Sign-in** on the first line returns to the list. On the provider catalogue, **No provider yet: people sign in with a password.** describes an empty list, not a connection failure. Saved provider details include separate Enable, Disable and Delete actions; disabling or deleting one ends the sessions it started.

Old:

> Turning local sign-in off or changing the second-factor requirement changes subsequent
> sign-ins; it does not sign out existing sessions. Use **Sign out everywhere** on a person's
> page when their existing sessions must end. Turning the requirement off leaves registered
> apps, recovery codes and passkeys in place.

New:

> Turning local sign-in off or changing the second-factor requirement changes subsequent
> sign-ins; it does not sign out existing sessions. Use **More actions › Sign out everywhere** on a person's
> page when their existing sessions must end. Turning the requirement off leaves registered
> apps, recovery codes and passkeys in place.

### administer/webhooks.md

Old:

> The catalogue shows **Active**, **Retrying** or **Suspended**. Select a webhook for **Configuration** and **Deliveries**. Configuration shows its destination, source, events, filters, creator, delivery progress, signing-key dates and any failure or suspension findings.

New:

> The catalogue shows **Active**, **Retrying** or **Suspended**. Open a webhook’s row for its own page with **Configuration** and **Deliveries** tabs. **← Webhooks** on the first line returns to the list. Configuration shows its destination, source, events, filters, creator, delivery progress, signing-key dates and any failure or suspension findings.

Old:

> **Rotate key…** replaces that webhook’s key. An overlap of **1 hour**, **24 hours** or **7 days** lets the receiver switch while both keys work. **Stop it now** is for a leaked key: deliveries use the replacement alone and may be refused until the receiver has it. Follow [Rotate a webhook key](/docs/guide/administer/rotate-a-webhook-key/).

New:

> **More actions › Rotate key…** replaces that webhook’s key. An overlap of **1 hour**, **24 hours** or **7 days** lets the receiver switch while both keys work. **Stop it now** is for a leaked key: deliveries use the replacement alone and may be refused until the receiver has it. Follow [Rotate a webhook key](/docs/guide/administer/rotate-a-webhook-key/).

Old:

> **Delete…** asks **Delete this webhook?** Confirm **Delete webhook** to stop sending and discard its signing key, or choose **Keep the webhook**. A replacement is a new subscription with a new position and key. A workspace with subscriptions cannot be deleted until they are removed.

New:

> **More actions › Delete…** asks **Delete this webhook?** Confirm **Delete webhook** to stop sending and discard its signing key, or choose **Keep the webhook**. A replacement is a new subscription with a new position and key. A workspace with subscriptions cannot be deleted until they are removed.

Old:

> 
> For temporarily stopping delivery use **Suspend**; for removing the destination use
> **Delete…**. Deletion has no undo and a new subscription does not restore the old delivery
> position. An installation restore needs its database and secret storage, through the
> operator's [backup and restore procedure](/docs/run/backup-and-restore/). Coordinate a
> restore with receivers: returning to an older acknowledged position can repeat deliveries.

New:

> 
> For temporarily stopping delivery use **Suspend**; for removing the destination use
> **More actions › Delete…**. Deletion has no undo and a new subscription does not restore the old delivery
> position. An installation restore needs its database and secret storage, through the
> operator's [backup and restore procedure](/docs/run/backup-and-restore/). Coordinate a
> restore with receivers: returning to an older acknowledged position can repeat deliveries.

### administer/roles-and-grants.md

No change.

### administer/audit.md

Old:

> Open **Settings › People and access › People** or **Settings › Connections › Clients**, select the identity and choose
> **See changes**. You can also follow a person's name from history where it is offered.
> The page shows newest first, grouped by day, across the workspaces you may read.

New:

> Open **Settings › People and access › People** or **Settings › Connections › Clients**, open the identity’s row and choose
> **More actions › See changes**. **← Back** on the first line returns to the previous page. You can also follow a person's name from history where it is offered.
> The page shows newest first, grouped by day, across the workspaces you may read.

Old:

> Filter by **Workspace**, **What** and **Period**. What offers **Everything**, **Records**,
> **Relationships**, **Change sets**, **Publications** and **Model**. Period offers **Any time**,
> **Last 24 hours**, **Last 7 days** and **Last 30 days**. **Load more** retrieves older results.

New:

> Filter by **Workspace**, **What** and **Period**. What offers **Everything**, **Records**,
> **Relationships**, **Change sets**, **Publications** and **Model**. Period offers **Any time**,
> **Last 24 hours**, **Last 7 days** and **Last 30 days**. **Show more** retrieves older results.

### administer/deployment-pages.md

Old:

> **Database** shows **Migration revision**, useful to the operator when checking an upgrade. The configuration tables show **Setting**, **Value**, **Default**, **Source** and **What it controls**. **Source** distinguishes **Environment** from **Default**. Secrets show only **Set** or **Not set**; the page does not reveal their values.

New:

> **Database** shows **Migration revision**, useful to the operator when checking an upgrade. Each configuration row shows the setting’s name and what it controls, its value and source; the default appears only when the value differs. **Source** distinguishes **Environment** from **Default**. Secrets show only **Set** or **Not set**; the page does not reveal their values.

Old:

> Under **Last backup rehearsal**, **Show earlier rehearsals** expands older recorded
> results. **Load more rehearsals** reads more; **Hide earlier rehearsals** folds them
> away. Give the operator the failed rehearsal's reason and the affected workspace checks,
> rather than assuming a newer backup fixes the cause. **How to rehearse a restore** is
> operator guidance; use the [restore runbook](/docs/run/backup-and-restore/) with them.

New:

> Under **Last backup rehearsal**, **Show earlier rehearsals (n)** expands older recorded
> results, with the count shown in the button. **Show more** reads more; **Hide earlier rehearsals** folds them
> away. Give the operator the failed rehearsal's reason and the affected workspace checks,
> rather than assuming a newer backup fixes the cause. **How to rehearse a restore** is
> operator guidance; use the [restore runbook](/docs/run/backup-and-restore/) with them.

### administer/mail.md

Old:

> Under **Send mail through**, choose **SMTP server** or **Microsoft 365**. One method is used at a time. Saving one replaces the other method’s saved fields and credentials. There is no automatic fallback to the other method.

New:

> On the **Server** tab, under **Send mail through**, choose **SMTP server** or **Microsoft 365**. One method is used at a time. Saving one replaces the other method’s saved fields and credentials. There is no automatic fallback to the other method.

Old:

> Ordinary messages wait in an outbox and are sent in the background. Under **Messages**, filter **State** to **All**, **Waiting**, **Sent** or **Failed**. Counts show each state. **Refresh** reads the current list; **Load more messages** reads older entries. Columns show **To**, **Message**, **State**, **Tries**, **Last problem**, **Queued** and **Actions**. A waiting row also shows **Next try**; finished rows show their finish time.

New:

> Ordinary messages wait in an outbox and are sent in the background. On the **Messages** tab, filter **State** to **All**, **Waiting**, **Sent** or **Failed**. Counts show each state. **Refresh** reads the current list; **Show more** reads older entries. Columns show **Queued**, **To**, **Message**, **State**, **Tries**, **Last problem** and **Actions**. A waiting row also shows **Next try**; finished rows show their finish time.

### administer/agent-access.md

Old:

> The operator enables agent access and restarts the server. **Agent access is off** means assistants cannot connect; this page cannot switch it on. When enabled, **How to connect** shows **Address**, a copy control and **Limit**, the number of calls each person or client can make per minute.

New:

> The operator enables agent access and restarts the server. **Agent access is off** means assistants cannot connect; this page cannot switch it on. When enabled, the **Access** tab’s **How to connect** shows **Address**, a copy control and **Limit**, the number of calls each person or client can make per minute.

Old:

> **Block** prevents new sign-ins and ends existing sessions on their next call. **Restore** permits new sign-ins but does not revive sessions that ended. For a system's assistant, open its agent client and use **Deactivate** instead. A person can end only their own assistant session through their account. If a permission was revoked, the next call is checked against the remaining grants.

New:

> **Block** prevents new sign-ins and ends existing sessions on their next call. **Restore** permits new sign-ins but does not revive sessions that ended. For a system's assistant, open its agent client and use **More actions › Deactivate** instead. A person can end only their own assistant session through their account. If a permission was revoked, the next call is checked against the remaining grants.

Old:

> **Calls** shows **When**, **Who**, **Through**, **Tool**, **Arguments** and **Outcome**, newest first. **Arguments** contains names only, never the supplied values. Outcomes are **Answered**, **Refused**, **Limit reached** and **Failed**. **Load more** reads older calls. The client list also shows **Last used** and **Calls, 30 days**.

New:

> The **Calls** tab shows **When**, **Who**, **Through**, **Tool**, **Arguments** and **Outcome**, newest first. **Arguments** contains names only, never the supplied values. Outcomes are **Answered**, **Refused**, **Limit reached** and **Failed**. **Show more** reads older calls. The client list also shows **Last used** and **Calls, 30 days**.

### administer/people-and-groups.md

Old:

> Use **Search people** (**Name or e-mail**) to find a person. The list also shows their roles. **Active** and **Deactivated** show
> separate lists and counts. Select someone to see their sign-in methods, roles, groups and recent activity.
> A person has one identity in refiroo and can hold different roles in different workspaces.

New:

> Use **Search people** (**Name or e-mail**) to find a person. The list also shows their roles. **Active** and **Deactivated** show
> separate lists and counts. Open a person’s row to see their own page with sign-in methods, roles, groups and recent activity. The first line, **← People**, returns to the list.
> A person has one identity in refiroo and can hold different roles in different workspaces.

Old:

> For an existing local account, open the newly created provider person's page and choose
> **Link to an existing person…**. Select the existing person and confirm the named link.
> The provider sign-in and provider memberships move to the existing person, whose roles
> and history continue. The new person is deactivated and their sessions end. Linking is refused if that new person
> already has a password, direct roles or local group memberships; resolve those before retrying.
> Follow [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) for the complete task. **Unlink…** removes a mistaken provider link, removes memberships in that provider’s groups and ends sessions started through it. Their next provider sign-in creates a separate person again. Direct roles and local group memberships on the remaining person stay in place.

New:

> For an existing local account, open the newly created provider person's page and choose
> **More actions › Link to an existing person…**. Select the existing person and confirm the named link.
> The provider sign-in and provider memberships move to the existing person, whose roles
> and history continue. The new person is deactivated and their sessions end. Linking is refused if that new person
> already has a password, direct roles or local group memberships; resolve those before retrying.
> Follow [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) for the complete task. **Unlink…** removes a mistaken provider link, removes memberships in that provider’s groups and ends sessions started through it. Their next provider sign-in creates a separate person again. Direct roles and local group memberships on the remaining person stay in place.

Old:

> You can still make a password link for the account holder to choose a password, remove an
> authenticator app or passkey, and use **Sign out everywhere** on their People page. Follow
> [Help someone who lost a device](/docs/guide/administer/help-someone-who-lost-a-device/).
> Clearing the checkbox lets the person manage their own sign-in again.

New:

> You can still make a password link for the account holder to choose a password, remove an
> authenticator app or passkey, and use **More actions › Sign out everywhere** on their People page. Follow
> [Help someone who lost a device](/docs/guide/administer/help-someone-who-lost-a-device/).
> Clearing the checkbox lets the person manage their own sign-in again.

Old:

> Select a group's name or description where it stands, edit it, then leave the field or press
> Enter to save. Escape puts the old text back; an unchanged input saves nothing. The save notice
> offers **Undo**. A refusal keeps the input and reason open with **Cancel** and **Save again**. **Delete group** asks for confirmation,
> then removes its memberships and grants. It does not delete people or their direct roles.
> Follow [Manage a group](/docs/guide/administer/manage-a-group/).

New:

> Open a group’s row; **← Groups** on its page returns to the list. Select its name or description where it stands, edit it, then leave the field or press
> Enter to save. Escape puts the old text back; an unchanged input saves nothing. The save notice
> offers **Undo**. A refusal keeps the input and reason open with **Cancel** and **Save again**. **Delete group** asks for confirmation,
> then removes its memberships and grants. It does not delete people or their direct roles.
> Follow [Manage a group](/docs/guide/administer/manage-a-group/).

Old:

> Choose **Deactivate** on the person's page and confirm. Their next request is refused and
> they cannot sign in. Their roles and groups remain, and history retains their name.
> Their records, change sets and publications are not deleted. Queued or running jobs lose
> the right to continue at their next permission check. Another authorised person can deal
> with the remaining work.

New:

> Choose **More actions › Deactivate** on the person's page and confirm. Their next request is refused and
> they cannot sign in. Their roles and groups remain, and history retains their name.
> Their records, change sets and publications are not deleted. Queued or running jobs lose
> the right to continue at their next permission check. Another authorised person can deal
> with the remaining work.

Old:

> **Sign out everywhere** instead ends all their refiroo sessions after confirmation but
> allows them to sign in again. Use deactivation when they must no longer have access.
> For a provider leaver, deactivate them in refiroo too: an existing refiroo session does not
> recheck provider membership on every request.

New:

> **More actions › Sign out everywhere** instead ends all their refiroo sessions after confirmation but
> allows them to sign in again. Use deactivation when they must no longer have access.
> For a provider leaver, deactivate them in refiroo too: an existing refiroo session does not
> recheck provider membership on every request.

Old:

> The person's **Recent activity** is grouped by day and can be narrowed to **Signing in**,
> **Roles and groups** or **Account**. It starts with ten entries, then reads 20 more at a time;
> **Show fewer** shortens it. **See changes** instead opens their data changes in workspaces you
> may browse. [Who changed what](/docs/administer/audit/) explains which view answers which question.

New:

> The person's **Recent activity** is grouped by day and can be narrowed to **Signing in**,
> **Roles and groups** or **Account**. It starts with ten entries, then reads 20 more at a time;
> **Show fewer** shortens it. **More actions › See changes** instead opens their data changes in workspaces you
> may browse. [Who changed what](/docs/administer/audit/) explains which view answers which question.

### administer/approval-policies.md

No change.

### administer/jobs-and-limits.md

Old:

> Use **Refresh** for current progress and **Load more jobs** for older entries. **Items** distinguishes processed, applied, rejected and unprocessed items. Completion alone does not mean every item was applied; read the result and rejected-item details.

New:

> Use **Refresh** for current progress and **Show more** for older entries. **Items** distinguishes processed, applied, rejected and unprocessed items. Completion alone does not mean every item was applied; read the result and rejected-item details.

Old:

> The **Limits** section displays the current values. Use these values when planning a large import; do not assume another deployment has the same settings.

New:

> The **Limits** tab displays the current values. Use these values when planning a large import; do not assume another deployment has the same settings.

### administer/ai.md

Old:

> Under **What is switched on**, **Assistant** shows whether the built-in Claude Code assistant is on. It reads a workbook or instructions, proposes changes and prepares a change set after the person accepts. It needs no AI provider configured on this page.

New:

> On the **Settings** tab, under **What is switched on**, **Assistant** shows whether the built-in Claude Code assistant is on. It reads a workbook or instructions, proposes changes and prepares a change set after the person accepts. It needs no AI provider configured on this page.

Old:

> **Calls** lists provider requests and each built-in assistant turn, newest first. Its columns show **When**, **What for**, **Asked by**, **Model**, **Outcome**, **Tokens in / out**, **Cost** and **Duration**. **Answered** means a response arrived, not that its suggestion is correct. **Failed** includes the reason. Use **Load more calls** to read older entries.

New:

> The **Calls** tab lists provider requests and each built-in assistant turn, newest first. Its columns show **When**, **What for**, **Asked by**, **Model**, **Outcome**, **Tokens in / out**, **Cost** and **Duration**. **Answered** means a response arrived, not that its suggestion is correct. **Failed** includes the reason. Use **Show more** to read older entries.

### guide/administer/rotate-a-client-secret.md

Old:

> 1. Open **Settings › Connections › Clients** and select the intended client. Check its name
>    and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
>    and **Last used**, so you can distinguish the current secret from a previous one.
> 2. Choose **Rotate secret…**. Select how long the current secret should keep working:
>    **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
> 3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
>    next tries to authenticate with the old secret until it has the replacement.
> 4. Choose **Rotate secret**. **Cancel** leaves the secrets unchanged. If creation fails,
>    read **No new secret was made**, reload the client and check its current secrets before retrying.

New:

> 1. Open **Settings › Connections › Clients** and open the intended client’s row. Check its name
>    and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
>    and **Last used**, so you can distinguish the current secret from a previous one.
> 2. Choose **Rotate secret…**. Select how long the current secret should keep working:
>    **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
> 3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
>    next tries to authenticate with the old secret until it has the replacement.
> 4. Choose **Rotate secret**. **Cancel** leaves the secrets unchanged. If creation fails,
>    read **No new secret was made**, reload the client and check its current secrets before retrying.

Old:

> 1. Open the client and choose **Deactivate**. Confirm the deactivation. Its requests are
>    refused from their next request, including requests using access already issued. Its
>    name, ID and grants remain.
> 2. In **Deactivated**, select the same client and choose **Rotate secret…**. The dialog
>    explains that the new secret takes effect when you restore the client. Rotation does
>    not restore it.
> 3. Choose **Stop it now**, then **Rotate secret**. This ends every older still-valid
>    secret immediately. Copy the replacement from **New secret for …** and store it before
>    choosing **I have copied it**. Have the integration owner configure the replacement.
> 4. Review the retained grants and the lifetime of access issued before deactivation with
>    the integration owner. Restoring the client can allow that earlier access again if it
>    has not expired; replacing a secret does not revoke it.
> 5. When the client is safe to use, choose **Restore**. It takes effect immediately. Have
>    the integration owner prove fresh authentication with the new secret and the intended
>    operation, then check **Last used**.

New:

> 1. Open the client and choose **More actions › Deactivate**. Confirm the deactivation. Its requests are
>    refused from their next request, including requests using access already issued. Its
>    name, ID and grants remain.
> 2. In **Deactivated**, open the same client’s row and choose **Rotate secret…**. The dialog
>    explains that the new secret takes effect when you restore the client. Rotation does
>    not restore it.
> 3. Choose **Stop it now**, then **Rotate secret**. This ends every older still-valid
>    secret immediately. Copy the replacement from **New secret for …** and store it before
>    choosing **I have copied it**. Have the integration owner configure the replacement.
> 4. Review the retained grants and the lifetime of access issued before deactivation with
>    the integration owner. Restoring the client can allow that earlier access again if it
>    has not expired; replacing a secret does not revoke it.
> 5. When the client is safe to use, choose **Restore**. It takes effect immediately. Have
>    the integration owner prove fresh authentication with the new secret and the intended
>    operation, then check **Last used**.

### guide/administer/create-a-webhook.md

No change.

### guide/administer/require-a-second-factor.md

Old:

> Changing this policy does not end existing sessions. To require a particular person to
> sign in again, open their People page and use **Sign out everywhere**, then check their
> next password sign-in. Do not treat an already open session as a test of the new policy.

New:

> Changing this policy does not end existing sessions. To require a particular person to
> sign in again, open their People page and use **More actions › Sign out everywhere**, then check their
> next password sign-in. Do not treat an already open session as a test of the new policy.

### guide/administer/link-a-provider-person.md

Old:

> 1. Confirm the person’s identity through your organisation’s process. Identify the existing account whose roles and history should continue, and the new person created by provider sign-in. Check e-mail addresses and sign-in methods as well as names.
> 2. Open **Settings › People and access › People** and select the new provider person. Do this before giving that new person a password, direct roles or local group memberships; those additions make linking unsafe and are refused.
> 3. Choose **Link to an existing person…**. In **Link this sign-in to an existing person**, search **Person** and select the existing active account. Read the sentence naming what moves and which person remains.
> 4. Choose **Link to …** with the intended person’s name. **Cancel** leaves the accounts separate. If **Not linked** appears, read the reason. Check the target is active and the source has no password, direct roles or local groups; resolve the conflict rather than linking to someone else to bypass it.
> 5. Check the existing person’s **Sign-in** section and groups. The provider identities and provider memberships move to this person. Their original roles and history continue. The newly created person is deactivated and their sessions end; it is not deleted.
> 6. Ask the person to sign in again through **Continue with …** and check they reach the existing account and intended workspace. Provider group roles apply alongside direct and local-group roles.

New:

> 1. Confirm the person’s identity through your organisation’s process. Identify the existing account whose roles and history should continue, and the new person created by provider sign-in. Check e-mail addresses and sign-in methods as well as names.
> 2. Open **Settings › People and access › People** and open the new provider person’s row. Do this before giving that new person a password, direct roles or local group memberships; those additions make linking unsafe and are refused.
> 3. Choose **More actions › Link to an existing person…**. In **Link this sign-in to an existing person**, search **Person** and select the existing active account. Read the sentence naming what moves and which person remains.
> 4. Choose **Link to …** with the intended person’s name. **Cancel** leaves the accounts separate. If **Not linked** appears, read the reason. Check the target is active and the source has no password, direct roles or local groups; resolve the conflict rather than linking to someone else to bypass it.
> 5. Check the existing person’s **Sign-in** section and groups. The provider identities and provider memberships move to this person. Their original roles and history continue. The newly created person is deactivated and their sessions end; it is not deleted.
> 6. Ask the person to sign in again through **Continue with …** and check they reach the existing account and intended workspace. Provider group roles apply alongside direct and local-group roles.

### guide/administer/set-up-mail.md

Old:

> 1. Open **Settings › This instance › Mail**. If nothing is saved, **Mail is not set up** explains that password links must be passed on by an administrator.
> 2. Under **Mail server**, enter **Server** and **Port**. Choose **Connection**: STARTTLS usually uses 587; TLS usually uses 465. Choose **None: not encrypted (a relay on a trusted network)** only for an approved relay without login.
> 3. Enter **User name** and **Password** if the server requires a login. Save is unavailable for a login over an unencrypted connection. A saved password is never displayed; enter it again when changing server or port.
> 4. Enter **From address**, approved by the mail administrator. Enter **Application address** if links should use a different address from the displayed default. Recipients must be able to reach it.
> 5. Choose **Save**. Wait for **Mail settings saved. Send a test message to try them.** Saving alone does not prove the mail server works. **Cancel** restores the saved values.

New:

> 1. Open **Settings › This instance › Mail** and the **Server** tab. If nothing is saved, **Mail is not set up** explains that password links must be passed on by an administrator.
> 2. Under **Mail server**, enter **Server** and **Port**. Choose **Connection**: STARTTLS usually uses 587; TLS usually uses 465. Choose **None: not encrypted (a relay on a trusted network)** only for an approved relay without login.
> 3. Enter **User name** and **Password** if the server requires a login. Save is unavailable for a login over an unencrypted connection. A saved password is never displayed; enter it again when changing server or port.
> 4. Enter **From address**, approved by the mail administrator. Enter **Application address** if links should use a different address from the displayed default. Recipients must be able to reach it.
> 5. Choose **Save**. Wait for **Mail settings saved. Send a test message to try them.** Saving alone does not prove the mail server works. **Cancel** restores the saved values.

### guide/administer/manage-a-group.md

Old:

> 1. Open **Settings › People and access › Groups**. Use **Search groups** (**Group name**) first to see whether the
>    intended group already exists. Choose a result to manage it, or **New group** to create one.
> 2. Enter **Name** and **Description (optional)**. The description can explain who belongs
>    and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
> 3. Choose **Add group**. The group opens with its roles and members. **Cancel** closes
>    without creating it. If saving fails, read **Not saved**, correct the problem and retry.

New:

> 1. Open **Settings › People and access › Groups**. Use **Search groups** (**Group name**) first to see whether the
>    intended group already exists. Open a result’s row to manage it on its own page, or choose **New group** to create one. **← Groups** returns to the list.
> 2. Enter **Name** and **Description (optional)**. The description can explain who belongs
>    and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
> 3. Choose **Add group**. The group opens with its roles and members. **Cancel** closes
>    without creating it. If saving fails, read **Not saved**, correct the problem and retry.

Old:

> 1. Find the group by name and select it. Select its name or description where it stands,
>    edit it, then leave the field or press Enter to save. Escape puts the old text back;
>    an unchanged input saves nothing. The save notice offers **Undo**. If refused, read the
>    reason under the input, then correct it and choose **Save again**, or **Cancel** to abandon
>    the edit. This does not change who belongs or the group's grants.
> 2. To remove a local member, use their row’s **Remove**. For several, tick their rows, or use **Select every member shown**, and
>    choose **Remove … from the group**. **Clear** clears the selection without removing anyone. Check the resulting list. Their direct roles and
>    roles from other groups remain.
> 3. To remove the whole group, choose **Delete group** and read the confirmation. Confirm
>    **Delete group** only if its memberships and all its grants should be removed.
>    The people remain and keep their direct grants.

New:

> 1. Find the group by name and open its row. Select its name or description where it stands,
>    edit it, then leave the field or press Enter to save. Escape puts the old text back;
>    an unchanged input saves nothing. The save notice offers **Undo**. If refused, read the
>    reason under the input, then correct it and choose **Save again**, or **Cancel** to abandon
>    the edit. This does not change who belongs or the group's grants.
> 2. To remove a local member, use their row’s **Remove**. For several, tick their rows, or use **Select every member shown**, and
>    choose **Remove … from the group**. **Clear** clears the selection without removing anyone. Check the resulting list. Their direct roles and
>    roles from other groups remain.
> 3. To remove the whole group, choose **Delete group** and read the confirmation. Confirm
>    **Delete group** only if its memberships and all its grants should be removed.
>    The people remain and keep their direct grants.

### guide/administer/create-a-client.md

No change.

### guide/administer/grant-a-consumer-api-to-a-client.md

Old:

> 1. Open **Settings › Connections › Clients**, find the intended system with **Search clients** and select it. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
> 2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
> 3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
> 4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
> 5. Read the sentence describing what the client may read and choose **Add grant**, or **Add N grants** for several. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
> 6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
> 7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.

New:

> 1. Open **Settings › Connections › Clients**, find the intended system with **Search clients** and open its row. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
> 2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
> 3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
> 4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
> 5. Read the sentence describing what the client may read and choose **Add grant**, or **Add N grants** for several. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
> 6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
> 7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.

### guide/administer/rotate-signing-keys.md

No change.

### guide/administer/manage-agent-access.md

Old:

> 1. Open **Settings › Connections › Agent access**. If it says **Agent access is off**, ask the operator to enable it and restart the server. The page cannot switch it on.
> 2. Under **How to connect**, copy **Address** and give it to the person connecting their MCP assistant. Use the address shown rather than constructing one from the browser's current page.
> 3. Ask the person to add that address in their assistant. It opens this instance's sign-in page, naming the assistant and where it returns. They should check those details before signing in. The name is what the assistant says about itself.
> 4. After sign-in, the assistant uses the person's existing grants, limited to reading and preparing changes. It does not need a new Agent role. Under **Assistants people sign in with**, check its **Returns to**, **Signed in now** and **Last used**.

New:

> 1. Open **Settings › Connections › Agent access**. If it says **Agent access is off**, ask the operator to enable it and restart the server. The page cannot switch it on.
> 2. On the **Access** tab, under **How to connect**, copy **Address** and give it to the person connecting their MCP assistant. Use the address shown rather than constructing one from the browser's current page.
> 3. Ask the person to add that address in their assistant. It opens this instance's sign-in page, naming the assistant and where it returns. They should check those details before signing in. The name is what the assistant says about itself.
> 4. After sign-in, the assistant uses the person's existing grants, limited to reading and preparing changes. It does not need a new Agent role. Under **Assistants people sign in with**, check its **Returns to**, **Signed in now** and **Last used**.

Old:

> 1. On **Agent access**, under **Agent clients**, choose **New agent client**. This is different from **New client** on the ordinary Clients page.
> 2. Enter **Name**, then choose **Add agent client**. The dialog **Copy the client's secret** shows **Client ID** and the secret once. Give these to the responsible integrator through your organisation's secure handover method. Choose **I have copied it** only after keeping what they need; the secret cannot be shown again.
> 3. Open the new client's name under **Agent clients**. Its normal client detail page opens. In **Access**, use **Grant access** to grant only the required role and workspaces. The **Agent** role gives Browse and Work in change sets; a custom role can provide a smaller set. A consumer API grant alone allows only that API's lookup tool and information about the connection's access.
> 4. Ask the integrator to configure the system's assistant with this client and the copied connection address. The [integration instructions](/docs/integrate/assistants-and-agents/) explain the connection details.
> 5. Return to **Agent access**. Check **Access**, **Last used** and **Calls, 30 days** on its row, then inspect **Calls** for the result. A new client has no access until you grant it.

New:

> 1. On **Agent access**, under **Agent clients**, choose **New agent client**. This is different from **New client** on the ordinary Clients page.
> 2. Enter **Name**, then choose **Add agent client**. The dialog **Copy the client's secret** shows **Client ID** and the secret once. Give these to the responsible integrator through your organisation's secure handover method. Choose **I have copied it** only after keeping what they need; the secret cannot be shown again.
> 3. Open the new client's name under **Agent clients**. Its normal client detail page opens. In **Access**, use **Grant access** to grant only the required role and workspaces. The **Agent** role gives Browse and Work in change sets; a custom role can provide a smaller set. A consumer API grant alone allows only that API's lookup tool and information about the connection's access.
> 4. Ask the integrator to configure the system's assistant with this client and the copied connection address. The [integration instructions](/docs/integrate/assistants-and-agents/) explain the connection details.
> 5. Return to **Agent access**. Check **Access**, **Last used** and **Calls, 30 days** on its row, then open the **Calls** tab for the result. A new client has no access until you grant it.

Old:

> For a lost secret, use [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/). To stop a system's assistant, open its client and choose **Deactivate**, then confirm. Its next request is refused. Restoring a client does not widen its grants.

New:

> For a lost secret, use [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/). To stop a system's assistant, open its client and choose **More actions › Deactivate**, then confirm. Its next request is refused. Restoring a client does not widen its grants.

Old:

> Read **Calls**, newest first. **Who** is the person or client; **Through** identifies the assistant or says **Its own client**. **Tool** is the operation it asked for and **Arguments** lists names only, never values. **Outcome** says **Answered**, **Refused**, **Limit reached** or **Failed**. Choose **Load more** for older calls.

New:

> Open the **Calls** tab, newest first. **Who** is the person or client; **Through** identifies the assistant or says **Its own client**. **Tool** is the operation it asked for and **Arguments** lists names only, never values. **Outcome** says **Answered**, **Refused**, **Limit reached** or **Failed**. Choose **Show more** for older calls.

### guide/administer/add-a-person.md

No change.

### guide/administer/find-out-why-a-webhook-paused.md

Old:

> 1. Open **Settings › Connections › Webhooks** and select the intended receiver. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
> 2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
> 3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
> 4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save**. If another person changed the webhook, review the reloaded configuration before saving again.
> 5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.

New:

> 1. Open **Settings › Connections › Webhooks** and open the intended receiver’s row. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
> 2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
> 3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
> 4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save**. If another person changed the webhook, review the reloaded configuration before saving again.
> 5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.

### guide/administer/set-an-approval-policy.md

No change.

### guide/administer/narrow-a-grant-to-record-types.md

Old:

> 1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
> 2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
> 3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
> 4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
> 5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Add grant**.
> 6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.

New:

> 1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and open the recipient’s row. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
> 2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
> 3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
> 4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
> 5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Add grant**.
> 6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.

### guide/administer/check-the-ai-provider.md

Old:

> 1. Open **Settings › This instance › AI**. Under **What is switched on**, check **Provider**. If neither feature is configured, the page says **Neither the assistant nor an AI provider is set up**. If only the assistant is on, there is no provider test button. Ask the operator to configure a provider if your task needs one.
> 2. Read **Settings**. Check **Model**, **Endpoint**, whether **Key** is set, and **What may be sent**. The secret is never displayed. A provider hosted outside your organisation receives the data allowed for each feature; make sure that arrangement is acceptable before inviting people to use it.
> 3. Read **What the AI provider is asked**. Each feature says **Available** or **Unavailable**. An unavailable feature needs more information than the configured send level permits; a successful connection test cannot make it available. Review the data policy with the operator rather than assuming the test failed.
> 4. Under **Test request**, choose **Send a test request**. The button says **Sending…** while it waits. The fixed request contains none of your reference data, and makes a call recorded below.
> 5. On success, **The AI provider answered** shows how long the answer took and which model answered. On failure, **The test request failed** gives the reason. This does not prove that suggestions are correct or that the built-in assistant works.

New:

> 1. Open **Settings › This instance › AI**. On the **Settings** tab, under **What is switched on**, check **Provider**. If neither feature is configured, the page says **Neither the assistant nor an AI provider is set up**. If only the assistant is on, there is no provider test button. Ask the operator to configure a provider if your task needs one.
> 2. Read **Settings**. Check **Model**, **Endpoint**, whether **Key** is set, and **What may be sent**. The secret is never displayed. A provider hosted outside your organisation receives the data allowed for each feature; make sure that arrangement is acceptable before inviting people to use it.
> 3. Read **What the AI provider is asked**. Each feature says **Available** or **Unavailable**. An unavailable feature needs more information than the configured send level permits; a successful connection test cannot make it available. Review the data policy with the operator rather than assuming the test failed.
> 4. Under **Test request**, choose **Send a test request**. The button says **Sending…** while it waits. The fixed request contains none of your reference data, and makes a call recorded on the **Calls** tab.
> 5. On success, **The AI provider answered** shows how long the answer took and which model answered. On failure, **The test request failed** gives the reason. This does not prove that suggestions are correct or that the built-in assistant works.

Old:

> In **Calls**, find the newest **Test request** row. Check **Asked by**, **Model**, **Outcome**, **Tokens in / out**, **Cost** and **Duration**. A failed row gives its reason. **Load more calls** opens older entries when available; the totals cover the last 30 days.

New:

> On the **Calls** tab, find the newest **Test request** row. Check **Asked by**, **Model**, **Outcome**, **Tokens in / out**, **Cost** and **Duration**. A failed row gives its reason. **Show more** opens older entries when available; the totals cover the last 30 days.

### guide/administer/find-who-changed-something.md

Old:

> 1. Open **Settings › People and access › People** or **Settings › Connections › Clients**. Search and select the identity.
>    Check their e-mail address or client ID if similar names exist. For a deactivated identity,
>    use the **Deactivated** list.
> 2. Choose **See changes**. The page names that person or client and lists their visible
>    changes, newest first, grouped by day. It can cover several workspaces.
> 3. Set **Workspace** to the relevant workspace, or keep **All workspaces**.
>    Under **What**, choose **Records**, **Relationships**, **Change sets**, **Publications**
>    or **Model**, or keep **Everything**.
> 4. Choose **Period**: **Last 24 hours**, **Last 7 days**, **Last 30 days** or **Any time**.
>    If no result matches, widen the filters. Use **Load more** to retrieve older entries.
> 5. Read the action, subject, changed-field summary, time and workspace. Open a linked title
>    to inspect the surviving subject. Use the record's own History for the changed values;
>    the person's Changes page is a summary.

New:

> 1. Open **Settings › People and access › People** or **Settings › Connections › Clients**. Search and open the identity’s row.
>    Check their e-mail address or client ID if similar names exist. For a deactivated identity,
>    use the **Deactivated** list.
> 2. Choose **More actions › See changes**. The page names that person or client and lists their visible
>    changes, newest first, grouped by day. It can cover several workspaces. **← Back** on the first line returns to the previous page.
> 3. Set **Workspace** to the relevant workspace, or keep **All workspaces**.
>    Under **What**, choose **Records**, **Relationships**, **Change sets**, **Publications**
>    or **Model**, or keep **Everything**.
> 4. Choose **Period**: **Last 24 hours**, **Last 7 days**, **Last 30 days** or **Any time**.
>    If no result matches, widen the filters. Use **Show more** to retrieve older entries.
> 5. Read the action, subject, changed-field summary, time and workspace. Open a linked title
>    to inspect the surviving subject. Use the record's own History for the changed values;
>    the person's Changes page is a summary.

### guide/administer/help-someone-who-lost-a-device.md

Old:

> 1. Open **Settings › People and access › People**, search for the person and select them.
>    Check their name, e-mail address and sign-in method.
> 2. Under **Sign-in**, choose **Remove second factor…** beside
>    **Second factor: authenticator app**. This button appears only when an app is set up.
> 3. Read the confirmation, then choose **Remove second factor**. Their app and its recovery
>    codes stop working. **Cancel** leaves the factor in place. The change is recorded in activity.
> 4. For someone who manages their own sign-in, a required second factor means setting up a
>    new app at their next password sign-in if no passkey remains. Otherwise, ask them to set
>    it up again on **Account** and save new recovery codes. An administrator-managed account
>    cannot set up a replacement. With no remaining factor, it signs in with the password
>    alone even if the instance requires a second factor.

New:

> 1. Open **Settings › People and access › People**, search for the person and open their row.
>    Check their name, e-mail address and sign-in method.
> 2. Under **Sign-in**, choose **Remove second factor…** beside
>    **Second factor: authenticator app**. This button appears only when an app is set up.
> 3. Read the confirmation, then choose **Remove second factor**. Their app and its recovery
>    codes stop working. **Cancel** leaves the factor in place. The change is recorded in activity.
> 4. For someone who manages their own sign-in, a required second factor means setting up a
>    new app at their next password sign-in if no passkey remains. Otherwise, ask them to set
>    it up again on **Account** and save new recovery codes. An administrator-managed account
>    cannot set up a replacement. With no remaining factor, it signs in with the password
>    alone even if the instance requires a second factor.

Old:

> 1. With the intended person still selected, choose **Reset password** if they need a new
>    local password. It makes a link at once; there is no confirmation first.
> 2. Copy and pass on the link in **Pass on the password link** before choosing **I have copied it**.
>    If available, use **Mail it to …** and check the sent-to message. A new administrator link replaces
>    every earlier password link for that person; give them the newest administrator link.
>    A later **Forgotten your password?** request does not cancel this administrator link.
>    Read its expiry.
> 3. Have them open it and set a new password. The secret part of the link leaves the address
>    bar before the form appears. They can reload the page in the same browser without losing
>    the link. If the form no longer opens, reopen the original link while it is valid. Using it ends their refiroo
>    sessions everywhere. A configured second factor remains in force. If the link expired,
>    was replaced or was used, make another.
> 4. If the lost device may still hold a signed-in session, choose **Sign out everywhere**
>    on the person's page and confirm. Every refiroo session ends at its next request.
>    They can sign in again with their remaining or replacement methods. This does not sign
>    other browsers out of the organisation's provider.

New:

> 1. With the intended person’s page still open, choose **Reset password** if they need a new
>    local password. It makes a link at once; there is no confirmation first.
> 2. Copy and pass on the link in **Pass on the password link** before choosing **I have copied it**.
>    If available, use **Mail it to …** and check the sent-to message. A new administrator link replaces
>    every earlier password link for that person; give them the newest administrator link.
>    A later **Forgotten your password?** request does not cancel this administrator link.
>    Read its expiry.
> 3. Have them open it and set a new password. The secret part of the link leaves the address
>    bar before the form appears. They can reload the page in the same browser without losing
>    the link. If the form no longer opens, reopen the original link while it is valid. Using it ends their refiroo
>    sessions everywhere. A configured second factor remains in force. If the link expired,
>    was replaced or was used, make another.
> 4. If the lost device may still hold a signed-in session, choose **More actions › Sign out everywhere**
>    on the person's page and confirm. Every refiroo session ends at its next request.
>    They can sign in again with their remaining or replacement methods. This does not sign
>    other browsers out of the organisation's provider.

### guide/administer/turn-off-local-sign-in.md

Old:

> 1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
> 2. Open **Settings › People and access › People** and select the recovery administrator. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
> 3. If needed, turn **Keeps local sign-in** on. It saves immediately and offers **Undo**; turning it off asks for confirmation. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
> 4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.

New:

> 1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
> 2. Open **Settings › People and access › People** and open the recovery administrator’s row. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
> 3. If needed, turn **Keeps local sign-in** on. It saves immediately and offers **Undo**; turning it off asks for confirmation. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
> 4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.

### guide/administer/grant-a-role.md

Old:

> 1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient.
>    Choose **Grant** in their roles or access section. The recipient is already chosen.
> 2. Alternatively, open **Settings › Workspaces**, select the workspace and choose **Access**,
>    then **Grant**. Choose **Who** by searching for the person, group or client by name.
>    Check the kind as well as the name before selecting them.
> 3. For a client, choose **Roles** under **What** if you are granting management access.
>    **Consumer APIs** is a separate kind of grant; see [Create a client](/docs/guide/administer/create-a-client/).

New:

> 1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and open the recipient’s row.
>    Choose **Grant** in their roles or access section. The recipient is already chosen.
> 2. Alternatively, open **Settings › Workspaces**, select the workspace and choose **Access**,
>    then **Grant**. Choose **Who** by searching for the person, group or client by name.
>    Check the kind as well as the name before selecting them.
> 3. For a client, choose **Roles** under **What** if you are granting management access.
>    **Consumer APIs** is a separate kind of grant; see [Create a client](/docs/guide/administer/create-a-client/).

### guide/administer/create-a-custom-role.md

No change.

### guide/administer/add-a-sign-in-provider.md

No change.

### guide/administer/rotate-a-webhook-key.md

Old:

> 1. Open **Settings › Connections › Webhooks**, select the intended webhook and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
> 2. Choose **Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
> 3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
> 4. Choose **Rotate key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
> 5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
> 6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
> 7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).

New:

> 1. Open **Settings › Connections › Webhooks**, open the intended webhook’s row and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
> 2. Choose **More actions › Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
> 3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
> 4. Choose **Rotate key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
> 5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
> 6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
> 7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).

### use/account.md

Old:

> The account card shows your name, e-mail address, how you signed in and when.
> These details help you check that you are using the intended account. **Sign out** on the card
> ends the current browser's sign-in.

New:

> The **You** panel shows your name, e-mail address, how you signed in and when.
> These details help you check that you are using the intended account. **Sign out** in that panel
> ends the current browser's sign-in.

### use/notifications-settings.md

No change.

### use/jobs.md

Old:

> A job is work refiroo runs in the background, such as an import, export or change to many
> records. Open **Settings › Data operations › Jobs** to find the jobs you may see across
> workspaces, newest first. In **All jobs**, the list shows **Workspace**, **State**, **Items**, **Requested by**,
> **Created**, **Finished** and **Actions**. Open a job to read its progress and results.

New:

> A job is work refiroo runs in the background, such as an import, export or change to many
> records. Open **Settings › Data operations › Jobs** to find the jobs you may see across
> workspaces, newest first. On the **Jobs** tab, in **All jobs**, the list shows **Workspace**, **State**, **Items**, **Requested by**,
> **Created**, **Finished** and **Actions**. Open a job to read its progress and results.

Old:

> 1. The heading names the workbook or draft. Above it, **Assistant task** or **Model draft**
>    and the workspace identify the group; **‹ Jobs** returns to the main list.
> 2. **Summary of the group** gives the job count and latest time. **All** shows the total;
>    state buttons show non-zero counts for **Running**, **Queued**, **Awaiting confirmation**,
>    **Failed**, **Completed**, **Cancelled** or **Expired**. Select one to narrow the table;
>    select **All** to restore every visible job. The selected state stays in the page's address.
> 3. The **Jobs** table shows **Job**, **State**, **Items**, **Requested by**, **Created**,
>    **Finished** and **Actions**. Inspect processed, applied, rejected and unprocessed counts.
>    **Refresh** reads again; **Load more jobs** continues the list. **Cancel** is offered
>    for queued or running work where cancellation is available; it opens a confirmation.
> 4. **Open the task** or **Open the draft** opens the owning work. The button appears only
>    after refiroo has confirmed you can read that task or draft. Seeing a group's jobs does
>    not itself grant access to its owner; a missing button is not a stopped job.
> 5. Open a job to inspect its result. When opened from the group, its trail includes
>    **‹ Assistant task: [name]** or **‹ Model draft: [name]**. Use that link to return to
>    the group with the state choice preserved, or **Jobs** to return to the main list.

New:

> 1. The heading names the workbook or draft. Above it, **Assistant task** or **Model draft**
>    and the workspace identify the group; **Jobs** in the first line returns to the main list.
> 2. **Summary of the group** gives the job count and latest time. **All** shows the total;
>    state buttons show non-zero counts for **Running**, **Queued**, **Awaiting confirmation**,
>    **Failed**, **Completed**, **Cancelled** or **Expired**. Select one to narrow the table;
>    select **All** to restore every visible job. The selected state stays in the page's address.
> 3. The **Jobs** table shows **Job**, **State**, **Items**, **Requested by**, **Created**,
>    **Finished** and **Actions**. Inspect processed, applied, rejected and unprocessed counts.
>    **Refresh** reads again; **Show more** continues the list. **Cancel** is offered
>    for queued or running work where cancellation is available; it opens a confirmation.
> 4. **Open the task** or **Open the draft** opens the owning work. The button appears only
>    after refiroo has confirmed you can read that task or draft. Seeing a group's jobs does
>    not itself grant access to its owner; a missing button is not a stopped job.
> 5. Open a job to inspect its result. When opened from the group, its trail includes
>    **‹ Assistant task: [name]** or **‹ Model draft: [name]**. Use that link to return to
>    the group with the state choice preserved, or **Jobs** to return to the main list.

Old:

> An expired preview cannot be confirmed, even if a stale page still says it is waiting.
> Start a new preview. The **Kept until** fact tells you when the job's retained results expire.
> The list's **Limits** describes this deployment's batch, job and retention limits; do not rely
> on a universal file size or item count.

New:

> An expired preview cannot be confirmed, even if a stale page still says it is waiting.
> Start a new preview. The **Kept until** fact tells you when the job's retained results expire.
> The **Limits** tab describes this deployment's batch, job and retention limits; do not rely
> on a universal file size or item count.

Old:

> The list distinguishes **Batch**, **Import**, **Export**, **Workbook for people**, **Profile**,
> **Profile check**, **Dry run**, **Inference**, **Mapping proposal**, **Migration** and **Move**.
> Some belong to model-administration tasks; their pages link to that work. **Refresh** reloads
> the list and **Load more jobs** continues it. **New export** starts a file; **New import**
> appears when your permissions allow importing.

New:

> The list distinguishes **Batch**, **Import**, **Export**, **Workbook for people**, **Profile**,
> **Profile check**, **Dry run**, **Inference**, **Mapping proposal**, **Migration** and **Move**.
> Some belong to model-administration tasks; their pages link to that work. **Refresh** reloads
> the list and **Show more** continues it. **New export** starts a file; **New import**
> appears when your permissions allow importing.

### use/importing-and-exporting.md

Old:

> In **Settings › Data operations › Import profiles**, **Valid** means the profile fits its
> model; **Needs a fix** means a named problem must be resolved. Neither guarantees that every
> row in the next file is valid. **Not loaded yet** means no retained last load is shown.
> **Load more profiles** continues the catalogue. If there are no profiles, ask a model
> administrator to prepare one through [Workbook onboarding](/docs/model/workbook-onboarding/).

New:

> In **Settings › Data operations › Import profiles**, **Valid** means the profile fits its
> model; **Needs a fix** means a named problem must be resolved. Neither guarantees that every
> row in the next file is valid. **Not loaded yet** means no retained last load is shown.
> Scroll to the end of the catalogue to read more profiles. If there are no profiles, ask a model
> administrator to prepare one through [Workbook onboarding](/docs/model/workbook-onboarding/).

Old:

> Open **Settings › Data operations › Import profiles** and select the profile. People with
> **Bulk and import** are offered the deletion buttons; without that access the buttons are absent.
> Deleting either item does not undo a load or remove records already loaded into a workspace.
> 
> - **Delete the file…** asks **Delete <file name>?**. **Delete the file** removes that upload,
>   its stored cells and the analysis of its sheets and columns. This analysis is not the saved
>   import profile that maps the columns. A check still reading it is
>   asked to stop. The import profile stays. Upload the file again before checking or loading it.
> - **Delete the profile…** asks **Delete the profile <profile name>?**. **Delete the profile**
>   removes the saved instructions for reading the workbook and returns you to the profile list.
>   Loading the workbook again needs a new profile saved by installing a model draft that holds it;
>   ask a model administrator to prepare this through [Workbook onboarding](/docs/model/workbook-onboarding/).

New:

> Open **Settings › Data operations › Import profiles** and open the profile’s row. **← Import profiles** on the first line returns to the list. People with
> **Bulk and import** find the deletion actions under **More actions**; without that access the actions are absent.
> Deleting either item does not undo a load or remove records already loaded into a workspace.
> 
> - **More actions › Delete the file…** asks **Delete <file name>?**. **Delete the file** removes that upload,
>   its stored cells and the analysis of its sheets and columns. This analysis is not the saved
>   import profile that maps the columns. A check still reading it is
>   asked to stop. The import profile stays. Upload the file again before checking or loading it.
> - **More actions › Delete the profile…** asks **Delete the profile <profile name>?**. **Delete the profile**
>   removes the saved instructions for reading the workbook and returns you to the profile list.
>   Loading the workbook again needs a new profile saved by installing a model draft that holds it;
>   ask a model administrator to prepare this through [Workbook onboarding](/docs/model/workbook-onboarding/).

### use/workspaces.md

No change.

### guide/use/set-up-email-notices.md

No change.

### guide/use/follow-and-cancel-a-job.md

Old:

> 1. Open **View job** in the starting notification, or go to **Settings › This instance › Jobs**
>    and open the job; a group of related jobs opens first, and its jobs under it. Check **Workspace**
>    and **Requested by** before acting.
> 2. Read **State** and progress. A preview waiting for confirmation has not written its proposed
>    changes. Review the items before choosing **Load the file** for an import or **Apply** for
>    a bulk preview. A running job updates while the page stays open.
> 3. To stop remaining work, use **Cancel job**, **Cancel import** for a waiting import,
>    or **Cancel preview** for a waiting batch preview.
>    Read the confirmation, then choose **Stop the job** for running work or **Discard the
>    import** / **Discard the preview** for a waiting preview. From the Jobs list, choose **Cancel
>    job** in its confirmation. **Keep the job**, **Keep the preview** or **Keep the import**
>    dismisses that confirmation.
> 4. Wait for the state to settle. **Cancel requested** is still pending. Already committed
>    chunks remain applied: inspect the final counts rather than assuming cancellation undoes them.
> 5. For an export that completed, read **The file** and choose **Download**. For an import or
>    batch, read refused and unprocessed items and their reasons. Fix the source and preview
>    again before retrying work.

New:

> 1. Open **View job** in the starting notification, or go to **Settings › This instance › Jobs**
>    and open the **Jobs** tab, then the job; a group of related jobs opens first, and its jobs under it. Check **Workspace**
>    and **Requested by** before acting.
> 2. Read **State** and progress. A preview waiting for confirmation has not written its proposed
>    changes. Review the items before choosing **Load the file** for an import or **Apply** for
>    a bulk preview. A running job updates while the page stays open.
> 3. To stop remaining work, use **Cancel job**, **Cancel import** for a waiting import,
>    or **Cancel preview** for a waiting batch preview.
>    Read the confirmation, then choose **Stop the job** for running work or **Discard the
>    import** / **Discard the preview** for a waiting preview. From the Jobs list, choose **Cancel
>    job** in its confirmation. **Keep the job**, **Keep the preview** or **Keep the import**
>    dismisses that confirmation.
> 4. Wait for the state to settle. **Cancel requested** is still pending. Already committed
>    chunks remain applied: inspect the final counts rather than assuming cancellation undoes them.
> 5. For an export that completed, read **The file** and choose **Download**. For an import or
>    batch, read refused and unprocessed items and their reasons. Fix the source and preview
>    again before retrying work.

### guide/use/import-a-file.md

No change.

### guide/use/load-the-next-version-of-a-workbook.md

Old:

> 1. Open **Settings › Workspaces and models › Import profiles**. Select the profile and read its
>    **Last load**: file, destination, row counts and whether its change set was published.
> 2. If your permissions offer **Upload the next version…**, choose it and upload the newer
>    workbook. Choose the intended comparison workspace and wait while it is checked.
>    The profile is checked and saved against that workspace’s model. Nothing is loaded
>    into its records by this check.
> 3. Review new, missing and renamed columns, new values, changed names and missing records.
>    Choose **Accept** on a **Renamed** row only where the proposed column really replaces the old one.
>    Choose **Ignore** on a **New** row to leave that column out. Ask the profile's model administrator to
>    fix ambiguous bindings or model problems; do not guess which field a column represents.
> 4. Check the missing-record choice. Keeping missing records leaves them; deleting them stages
>    removals and is allowed only in a change set. A missing key means reliable recurring
>    matching is not available: resolve it before relying on repeated uploads.
> 5. When the report allows loading, choose **Load into a change set…** and review the destination
>    and proposed changes in its dialog. Loading creates a new change set containing differences.
> 6. Choose **Open the change set review** from the completed load or **Last load**. Review
>    additions, corrections and removals before publishing or submitting for approval.

New:

> 1. Open **Settings › Workspaces and models › Import profiles**. Open the profile’s row and read its
>    **Last load**: file, destination, row counts and whether its change set was published.
> 2. If your permissions offer **Upload the next version…**, choose it and upload the newer
>    workbook. Choose the intended comparison workspace and wait while it is checked.
>    The profile is checked and saved against that workspace’s model. Nothing is loaded
>    into its records by this check.
> 3. Review new, missing and renamed columns, new values, changed names and missing records.
>    Choose **Accept** on a **Renamed** row only where the proposed column really replaces the old one.
>    Choose **Ignore** on a **New** row to leave that column out. Ask the profile's model administrator to
>    fix ambiguous bindings or model problems; do not guess which field a column represents.
> 4. Check the missing-record choice. Keeping missing records leaves them; deleting them stages
>    removals and is allowed only in a change set. A missing key means reliable recurring
>    matching is not available: resolve it before relying on repeated uploads.
> 5. When the report allows loading, choose **Load into a change set…** and review the destination
>    and proposed changes in its dialog. Loading creates a new change set containing differences.
> 6. Choose **Open the change set review** from the completed load or **Last load**. Review
>    additions, corrections and removals before publishing or submitting for approval.

Old:

> 1. On the profile page, choose **Delete the file…** beside the upload and load actions.
> 2. Read **Delete <file name>?**. It removes the upload and its stored analysis, stops a check
>    still reading it, and keeps the profile and already loaded records.
> 3. Choose **Delete the file** to continue or **Cancel** to keep it. After deletion, upload a
>    file again to check it. A failed deletion leaves its reason in the dialog; resolve that
>    cause before retrying.
> 
> To stop reusing the profile itself, choose **Delete the profile…** and confirm **Delete the
> profile**. Read [what each deletion keeps](/docs/use/importing-and-exporting/#remove-an-uploaded-file-or-an-import-profile)
> before confirming; deleting a profile does not reverse its earlier loads.

New:

> 1. On the profile page, choose **More actions › Delete the file…**.
> 2. Read **Delete <file name>?**. It removes the upload and its stored analysis, stops a check
>    still reading it, and keeps the profile and already loaded records.
> 3. Choose **Delete the file** to continue or **Cancel** to keep it. After deletion, upload a
>    file again to check it. A failed deletion leaves its reason in the dialog; resolve that
>    cause before retrying.
> 
> To stop reusing the profile itself, choose **More actions › Delete the profile…** and confirm **Delete the
> profile**. Read [what each deletion keeps](/docs/use/importing-and-exporting/#remove-an-uploaded-file-or-an-import-profile)
> before confirming; deleting a profile does not reverse its earlier loads.

### guide/use/open-a-retired-or-unavailable-workspace.md

No change.

### model/managing-workspaces.md

Old:

> Open a workspace row to inspect **Overview**, **Access**, **Approval** and **Activity**.
> **Open workspace** returns to its data; **Activity** shows [history across records](/docs/use/history/).
> The other actions require administrative permissions: **New workspace**, **Edit model**,
> **Copy or move data…** and **Retire…** change the workspace or its configuration.
> Opening the page does not perform them.

New:

> Open a workspace row to inspect **Overview**, **Access**, **Approval** and **Activity**. **← Workspaces** on the first line returns to the list.
> **Open workspace** returns to its data; **Activity** shows [history across records](/docs/use/history/).
> The other actions require administrative permissions: **New workspace**, **Edit model**,
> **More actions › Copy or move data…** and **More actions › Retire…** change the workspace or its configuration.
> Opening the page does not perform them.

Old:

> - **Retire…** asks for confirmation. It removes the workspace from the active selector and
>   refuses writes, keeping data, change sets, publications and history readable. Open it from
>   this list later. **Reactivate** makes it available for work again.
> - **Set as default** chooses the default destination. It neither copies data nor changes the
>   models of other workspaces. Check the Default mark after the action.
> - **Delete…** is only for an empty, never-published workspace with no change sets or webhook
>   subscriptions. A workspace ever published can only be retired, even after its data is removed.
>   The screen explains what prevents deletion. Confirm only after checking the name and key.

New:

> - **More actions › Retire…** asks for confirmation. It removes the workspace from the active selector and
>   refuses writes, keeping data, change sets, publications and history readable. Open it from
>   this list later. **More actions › Reactivate** makes it available for work again.
> - **More actions › Set as default** chooses the default destination. It neither copies data nor changes the
>   models of other workspaces. Check the Default mark after the action.
> - **More actions › Delete…** is only for an empty, never-published workspace with no change sets or webhook
>   subscriptions. A workspace ever published can only be retired, even after its data is removed.
>   The screen explains what prevents deletion. Confirm only after checking the name and key.

Old:

> **Edit model** opens the saved draft for the workspace, reopening it on later visits. It needs
> Model authoring, Model release and Browse, and an active workspace. Check **Applies to**, then
> use **Apply to this workspace…** after editing. The confirmation lists model changes, data
> compatibility, open change sets left behind and other workspaces left unchanged. If records must
> move, review the separate preview before confirming. Follow
> [Install and activate a release](/docs/guide/model/install-and-activate-a-release/).
> **Copy or move data…** starts [a copy or move](/docs/guide/model/move-records-to-another-model/).

New:

> **Edit model** opens the saved draft for the workspace, reopening it on later visits. It needs
> Model authoring, Model release and Browse, and an active workspace. Check **Applies to**, then
> use **Apply to this workspace…** after editing. The confirmation lists model changes, data
> compatibility, open change sets left behind and other workspaces left unchanged. If records must
> move, review the separate preview before confirming. Follow
> [Install and activate a release](/docs/guide/model/install-and-activate-a-release/).
> **More actions › Copy or move data…** starts [a copy or move](/docs/guide/model/move-records-to-another-model/).

### model/releases.md

Old:

> Open a release to inspect its counts and workspace use, **Create draft from release**, or
> **Activate in a workspace…**. **Structure** on the model’s page is read-only and initially selects the newest release;
> its Release picker can show another version.

New:

> Open a release to inspect its counts and workspace use, **Create draft from release**, or
> **Activate in a workspace…**. The header shows up to two actions; any remaining action is under **More actions**. **Structure** on the model’s page is read-only and initially selects the newest release;
> its Release picker can show another version.

Old:

> A release can be **Retired** to stop it being chosen for new work. Workspaces and change sets
> already on it keep working. On the release page, **Retire…** asks for confirmation; **Bring back**
> makes a retired release available again. The default workspace's release cannot be retired.
> These controls need installation permission.

New:

> A release can be **Retired** to stop it being chosen for new work. Workspaces and change sets
> already on it keep working. On the release page, **More actions › Retire…** asks for confirmation; **More actions › Bring back**
> makes a retired release available again. The default workspace's release cannot be retired.
> These controls need installation permission.

Old:

> The page marks **Runs this release** for a workspace using it and **Run by no workspace** when
> none does. Under **Technical details**, **Release ID** and **Content hash** each have **Copy**;
> these identify a release and its exact content, rather than its displayed version alone.
> **Export JSON** downloads the immutable model document for a specialist model author.
> 
> **Activation check** checks each workspace running this model separately. Read the workspace name
> and result; a successful check for one workspace says nothing about another's data. A failed
> check is not compatibility. The confirmation checks again when you activate.
> 
> **Retire…** removes a release from new choices without changing workspaces already running it.
> **Bring back** makes it available again. A release never run and with no records, change sets or
> publications made under it can offer **Delete…** with confirmation. Retirement preserves the
> release; deletion removes an unused one. A model with all releases retired and no running
> workspace appears under Retired.

New:

> The page marks **Runs this release** for a workspace using it and **Run by no workspace** when
> none does. Under **Technical details**, **Release ID** and **Content hash** each have **Copy**;
> these identify a release and its exact content, rather than its displayed version alone.
> **Export JSON**, in the header or under **More actions**, downloads the immutable model document for a specialist model author.
> 
> Under **Workspaces running** followed by the model’s key, the activation check reads each workspace’s data separately. Read the workspace name
> and result; a successful check for one workspace says nothing about another's data. A failed
> check is not compatibility. The confirmation checks again when you activate.
> 
> **More actions › Retire…** removes a release from new choices without changing workspaces already running it.
> **More actions › Bring back** makes it available again. A release never run and with no records, change sets or
> publications made under it can offer **More actions › Delete…** with confirmation. Retirement preserves the
> release; deletion removes an unused one. A model with all releases retired and no running
> workspace appears under Retired.

Old:

> The release page's **Activation check** covers workspaces running this model. A workspace running
> another model is checked separately when selected as a destination. **Historical release** means
> this deployment cannot interpret its model language for the usual comparison and activation checks;
> its metadata and raw export remain readable.

New:

> The release page’s activation check under **Workspaces running** covers workspaces running this model. A workspace running
> another model is checked separately when selected as a destination. **Historical release** means
> this deployment cannot interpret its model language for the usual comparison and activation checks;
> its metadata and raw export remain readable.

### model/models.md

No change.

### model/workbook-onboarding.md

No change.

### guide/model/create-a-workspace.md

No change.

### guide/model/retire-or-delete-a-workspace.md

Old:

> 1. Open the workspace and check its name, key and default status. The default cannot be
>    retired or deleted; [make another workspace default](/docs/guide/model/make-a-workspace-the-default/) first.
> 2. To keep the data but stop changes, choose **Retire…**. Read the confirmation and choose
>    **Retire workspace**, or cancel. It leaves the active selector and becomes read-only.
>    Records, change sets, publications and history remain readable through workspace management.
> 3. To resume work later, open the retired workspace in this list and choose **Reactivate**.
>    Check the active state. Reactivation does not change its model release. Retirement also
>    suspends its active webhook subscriptions; ask their administrator to resume them separately
>    after reactivation.
> 4. Use **Delete…** only for an empty workspace that has never been published and has no change
>    sets or webhook subscriptions. Read the page's explanation of anything preventing deletion.
>    Even an emptied workspace with past publications must be retired instead.
> 5. If eligible and no longer needed, read the deletion confirmation's name and key, then
>    choose **Delete workspace**. Cancel preserves it. Do not treat deletion as reversible retirement.

New:

> 1. Open the workspace and check its name, key and default status. The default cannot be
>    retired or deleted; [make another workspace default](/docs/guide/model/make-a-workspace-the-default/) first.
> 2. To keep the data but stop changes, choose **More actions › Retire…**. Read the confirmation and choose
>    **Retire workspace**, or cancel. It leaves the active selector and becomes read-only.
>    Records, change sets, publications and history remain readable through workspace management.
> 3. To resume work later, open the retired workspace in this list and choose **More actions › Reactivate**.
>    Check the active state. Reactivation does not change its model release. Retirement also
>    suspends its active webhook subscriptions; ask their administrator to resume them separately
>    after reactivation.
> 4. Use **More actions › Delete…** only for an empty workspace that has never been published and has no change
>    sets or webhook subscriptions. Read the page's explanation of anything preventing deletion.
>    Even an emptied workspace with past publications must be retired instead.
> 5. If eligible and no longer needed, read the deletion confirmation's name and key, then
>    choose **Delete workspace**. Cancel preserves it. Do not treat deletion as reversible retirement.

### guide/model/retire-or-delete-a-release.md

Old:

> 1. Check its version, workspace use and whether it runs the default workspace. **Retire…**
>    stops new selection but keeps existing users on the release. The default workspace's release
>    cannot be retired; move that workspace to another usable release first if appropriate.
> 2. Choose **Retire…**, read the named release and confirm. Cancel keeps it available. Check
>    the **Retired** state afterwards. Workspaces and change sets already using it keep working.
> 3. To offer it again, choose **Bring back** and check that it is available. A model with every
>    release retired and no running workspace appears under **Retired** in the model list.
> 4. Use **Delete…** only for a release with no remaining use or references. **Run by no workspace**
>    alone does not prove it is deletable: records, publications, change sets, profiles or mappings
>    can still refer to it. Read the confirmation and any refusal before proceeding.
> 5. Confirm deletion only when the named unused release is no longer needed. Deleting its release
>    does not delete editable drafts. If refused, retain it or retire it; do not delete history to
>    force a release removal.

New:

> 1. Check its version, workspace use and whether it runs the default workspace. **Retire…**
>    stops new selection but keeps existing users on the release. The default workspace's release
>    cannot be retired; move that workspace to another usable release first if appropriate.
> 2. Choose **More actions › Retire…**, read the named release and confirm. Cancel keeps it available. Check
>    the **Retired** state afterwards. Workspaces and change sets already using it keep working.
> 3. To offer it again, choose **More actions › Bring back** and check that it is available. A model with every
>    release retired and no running workspace appears under **Retired** in the model list.
> 4. Use **More actions › Delete…** only for a release with no remaining use or references. **Run by no workspace**
>    alone does not prove it is deletable: records, publications, change sets, profiles or mappings
>    can still refer to it. Read the confirmation and any refusal before proceeding.
> 5. Confirm deletion only when the named unused release is no longer needed. Deleting its release
>    does not delete editable drafts. If refused, retain it or retire it; do not delete history to
>    force a release removal.

### guide/model/make-a-workspace-the-default.md

Old:

> 1. Open **Settings › Workspaces**, then the active workspace you want as the default.
>    Read its name, permanent key and model in **Overview**.
> 2. Choose **Set as default**. Check the success notice and **Default** mark afterwards.
>    The previous default remains a separate workspace with its own records and model.
> 3. If another administrator changed the default while your page was open, read the notice,
>    reload the state and choose again only if your intended change is still correct.
> 4. Inspect new-workspace creation choices when relevant: **The default workspace’s model**
>    now refers to this workspace's release. Existing workspaces keep their selected releases.

New:

> 1. Open **Settings › Workspaces**, then the active workspace you want as the default.
>    Read its name, permanent key and model in **Overview**.
> 2. Choose **More actions › Set as default**. Check the success notice and **Default** mark afterwards.
>    The previous default remains a separate workspace with its own records and model.
> 3. If another administrator changed the default while your page was open, read the notice,
>    reload the state and choose again only if your intended change is still correct.
> 4. Inspect new-workspace creation choices when relevant: **The default workspace’s model**
>    now refers to this workspace's release. Existing workspaces keep their selected releases.

### guide/model/compare-releases.md

Old:

> 1. In **Release history**, find **Changes in this release**. Read **Before** and **After**;
>    After is the open release. The suggested predecessor comes from activation history or the
>    earlier installed release. It is not necessarily the workspace you currently have open.
> 2. Use **Compare with** to choose another baseline. A comparison may cross model families,
>    so check both names and versions rather than assuming they share a lineage.
> 3. Read the changes table's **Kind**, **Path**, **Before** and **After**. These describe model
>    definitions, not a history of record edits. Inspect removals as well as additions.
> 4. **No semantic changes** means the two documents define the same model. **No earlier release**
>    means no predecessor is available; select another baseline if offered.
> 5. If **Comparison unavailable** names an unsupported model language, choose another release.
>    Its metadata and **Export JSON** remain available for specialist inspection. A loading or
>    failed comparison is not an empty comparison.

New:

> 1. Find **Changes in this release**. Read **Before** and **After**;
>    After is the open release. The suggested predecessor comes from activation history or the
>    earlier installed release. It is not necessarily the workspace you currently have open.
> 2. Use **Compare with** to choose another baseline. A comparison may cross model families,
>    so check both names and versions rather than assuming they share a lineage.
> 3. Read the changes table's **Kind**, **Path**, **Before** and **After**. These describe model
>    definitions, not a history of record edits. Inspect removals as well as additions.
> 4. **No semantic changes** means the two documents define the same model. **No earlier release**
>    means no predecessor is available; select another baseline if offered.
> 5. If **Comparison unavailable** names an unsupported model language, choose another release.
>    Its metadata and **Export JSON** remain available for specialist inspection. A loading or
>    failed comparison is not an empty comparison.

Old:

> The separate **Activation check** reads each workspace's data. A small or empty comparison alone
> does not establish that activation in a chosen workspace is safe.

New:

> The separate activation check under **Workspaces running** reads each workspace’s data. A small or empty comparison alone
> does not establish that activation in a chosen workspace is safe.

### guide/model/export-a-release.md

Old:

> 1. Open **Settings › Model**, the model's **Releases**, then the intended version. Check its
>    name, version and **Immutable release** state rather than opening a similarly named draft.
> 2. Choose **Export JSON** and keep the downloaded document. The installed release is unchanged.
>    Export is also available for historical definitions the current editor cannot interpret.
> 3. If you need to identify it precisely, open **Technical details**. Use **Copy** beside
>    **Release ID** and **Content hash**. The hash identifies the content; the displayed version
>    is a human-facing release label.
> 4. To edit a copy, use **Create draft from release** or the draft creation dialog's **Import
>    JSON** option. Importing a document does not activate it. For data backup, use the operator's
>    backup procedure instead of treating this file as a workspace export.

New:

> 1. Open **Settings › Model**, the model's **Releases**, then the intended version. Check its
>    name, version and **Immutable release** state rather than opening a similarly named draft.
> 2. Choose **Export JSON** in the header, or under **More actions** if it is not shown there, and keep the downloaded document. The installed release is unchanged.
>    Export is also available for historical definitions the current editor cannot interpret.
> 3. If you need to identify it precisely, open **Technical details**. Use **Copy** beside
>    **Release ID** and **Content hash**. The hash identifies the content; the displayed version
>    is a human-facing release label.
> 4. To edit a copy, use **Create draft from release** or the draft creation dialog's **Import
>    JSON** option. Importing a document does not activate it. For data backup, use the operator's
>    backup procedure instead of treating this file as a workspace export.

### guide/model/change-a-workspaces-model.md

No change.

### guide/model/delete-a-draft.md

No change.

### run/ai.md

Old:

> Open **Settings › This instance › AI** to see which switches are on, the send level and, when a
> provider is configured, its model, endpoint, whether a key is set, and the features available.
> The key itself is never shown. This page displays settings; change them in the environment.
> 
> **Calls** lists provider requests and assistant turns, newest first: who asked, what for, the model,
> outcome, tokens, cost when reported, and duration. A failed call includes a failure message.
> **Load more calls** reads older entries. With no entries, the page says **No call has been made yet.**
> When content logging is on and has not expired, expand **Show what was sent and answered** on a row.
> Treat that content as sensitive.

New:

> Open **Settings › This instance › AI**, then its **Settings** tab, to see which switches are on, the send level and, when a
> provider is configured, its model, endpoint, whether a key is set, and the features available.
> The key itself is never shown. This page displays settings; change them in the environment.
> 
> The **Calls** tab lists provider requests and assistant turns, newest first: who asked, what for, the model,
> outcome, tokens, cost when reported, and duration. A failed call includes a failure message.
> **Show more** reads older entries. With no entries, the page says **No call has been made yet.**
> When content logging is on and has not expired, expand **Show what was sent and answered** on a row.
> Treat that content as sensitive.

### run/set-up-ai.md

Old:

> 1. With **Operations** access, open **Settings › This instance › AI**. Under **What is switched on**,
>    check **Assistant** and **Provider** against what you enabled. **Assistant: On** means the command
>    is set; it does not prove a session can authenticate. Check **What may be sent** too.
> 2. If a provider is configured, select **Send a test request**. Success shows **The AI provider
>    answered** and a new **Calls** entry. The request contains none of your reference data. With
>    only the assistant enabled, this button is absent.
> 3. To test the assistant independently, use an active workspace and a person with **Use AI proposals**,
>    **Work in change sets**, **Bulk and import**, and permission to create jobs there. The model-change
>    test also needs **Model authoring** and **Model release** access. Open the workspace's
>    **⋯** menu and choose **Change this model…**. Enter a small proposed change in **What should
>    change?**, then select **Ask the assistant**. Wait until the task presents its proposal, then
>    read it without applying it. Reaching the proposal checks that the assistant can reach the
>    engine's API as well as authenticate with Claude Code. This exercises a real session and sends
>    the instructions, model and any records it needs.
> 4. Return to **Settings › This instance › AI**. The session's turn should appear in **Calls** with
>    its outcome, tokens and any reported cost. Review or discard the test task when finished.

New:

> 1. With **Operations** access, open **Settings › This instance › AI** and its **Settings** tab. Under **What is switched on**,
>    check **Assistant** and **Provider** against what you enabled. **Assistant: On** means the command
>    is set; it does not prove a session can authenticate. Check **What may be sent** too.
> 2. If a provider is configured, select **Send a test request**. Success shows **The AI provider
>    answered** and a new entry on the **Calls** tab. The request contains none of your reference data. With
>    only the assistant enabled, this button is absent.
> 3. To test the assistant independently, use an active workspace and a person with **Use AI proposals**,
>    **Work in change sets**, **Bulk and import**, and permission to create jobs there. The model-change
>    test also needs **Model authoring** and **Model release** access. Open the workspace's
>    **⋯** menu and choose **Change this model…**. Enter a small proposed change in **What should
>    change?**, then select **Ask the assistant**. Wait until the task presents its proposal, then
>    read it without applying it. Reaching the proposal checks that the assistant can reach the
>    engine's API as well as authenticate with Claude Code. This exercises a real session and sends
>    the instructions, model and any records it needs.
> 4. Return to **Settings › This instance › AI**. Open the **Calls** tab; the session's turn should appear there with
>    its outcome, tokens and any reported cost. Review or discard the test task when finished.

### run/webhook-delivery.md

No change.

### run/background-jobs.md

Old:

> Tasks use `AI_TASK_RETENTION_DAYS` (90 by default), separately from ordinary job retention. Session
> folders, logs and transcripts stay while a task can continue; the next read after publication,
> discard or confirmed migration removes them, and expiry also cleans them. In the shipped image,
> each task has a randomly named folder under `/opt/refiroo/rdm-engine/data/assistant`, with
> working files in `work`, Claude Code configuration and transcripts in `claude`, and turn logs
> inside the same task folder. Session users cannot list the parent folder to find other tasks.
> Compose persists this in the single `assistant` volume across container replacement, until normal
> cleanup. Backups may omit it; losing it loses open tasks’ folders and session logs, not records.
> After upgrading from the earlier shared-transcript layout, existing files are kept but the next
> turn starts a new session. See [Upgrades](/docs/run/upgrades/#volumes-and-open-assistant-tasks).
> **Calls** on **Settings › This instance › AI** keeps turn outcomes and usage separately. See
> [AI retention and recovery](/docs/run/ai/#what-is-kept) before maintenance or a retry.

New:

> Tasks use `AI_TASK_RETENTION_DAYS` (90 by default), separately from ordinary job retention. Session
> folders, logs and transcripts stay while a task can continue; the next read after publication,
> discard or confirmed migration removes them, and expiry also cleans them. In the shipped image,
> each task has a randomly named folder under `/opt/refiroo/rdm-engine/data/assistant`, with
> working files in `work`, Claude Code configuration and transcripts in `claude`, and turn logs
> inside the same task folder. Session users cannot list the parent folder to find other tasks.
> Compose persists this in the single `assistant` volume across container replacement, until normal
> cleanup. Backups may omit it; losing it loses open tasks’ folders and session logs, not records.
> After upgrading from the earlier shared-transcript layout, existing files are kept but the next
> turn starts a new session. See [Upgrades](/docs/run/upgrades/#volumes-and-open-assistant-tasks).
> The **Calls** tab on **Settings › This instance › AI** keeps turn outcomes and usage separately. See
> [AI retention and recovery](/docs/run/ai/#what-is-kept) before maintenance or a retry.

### run/sign-in-and-mail-setup.md

Old:

> Arrange an SMTP server and a sender address. A security administrator saves these on **Settings › This instance › Mail**:
> 
> 1. Choose **SMTP server** under **Send mail through**. In **Mail server**, enter **Server** and **Port**, then choose **Connection** (STARTTLS or TLS
>    for an authenticated server).
> 2. Enter **User name** and **Password** if required, **From address** and the public **Application
>    address** used for links. Choose **Save**. A save refusal leaves the existing settings intact;
>    use the refusal table below before trying again.
> 3. Under **Test message**, enter **Send to** and choose **Send test message**. **Sent** means the
>    SMTP server accepted it; confirm arrival in the recipient's mailbox as well.
> 4. Inspect **Messages** for later delivery attempts and **Last problem**. **Stop sending** ends
>    retries for a waiting message, but its one-time link remains valid until expiry.
> The SMTP password is a secret, sealed in the database and never shown. Changing host or port needs
> the password again in the same save (`MAIL_PASSWORD_REQUIRED`).

New:

> Arrange an SMTP server and a sender address. A security administrator saves these on the **Server** tab of **Settings › This instance › Mail**:
> 
> 1. Choose **SMTP server** under **Send mail through**. In **Mail server**, enter **Server** and **Port**, then choose **Connection** (STARTTLS or TLS
>    for an authenticated server).
> 2. Enter **User name** and **Password** if required, **From address** and the public **Application
>    address** used for links. Choose **Save**. A save refusal leaves the existing settings intact;
>    use the refusal table below before trying again.
> 3. Under **Test message**, enter **Send to** and choose **Send test message**. **Sent** means the
>    SMTP server accepted it; confirm arrival in the recipient's mailbox as well.
> 4. Open the **Messages** tab for later delivery attempts and **Last problem**. **Stop sending** ends
>    retries for a waiting message, but its one-time link remains valid until expiry.
> The SMTP password is a secret, sealed in the database and never shown. Changing host or port needs
> the password again in the same save (`MAIL_PASSWORD_REQUIRED`).

Old:

> On **Settings › This instance › Mail**, choose **Microsoft 365** under **Send mail through**.
> Enter **Tenant ID** and **Application (client) ID**, choose **Client secret** or **Certificate**
> under **Sign in with**, and enter the prepared value or PEM text. Set **Sending mailbox** to the
> mailbox above and **Application address** to the public address recipients use to open refiroo.
> An empty application address uses the default displayed below the field.

New:

> On the **Server** tab of **Settings › This instance › Mail**, choose **Microsoft 365** under **Send mail through**.
> Enter **Tenant ID** and **Application (client) ID**, choose **Client secret** or **Certificate**
> under **Sign in with**, and enter the prepared value or PEM text. Set **Sending mailbox** to the
> mailbox above and **Application address** to the public address recipients use to open refiroo.
> An empty application address uses the default displayed below the field.

Old:

>    The group must hold the sending mailbox. RBAC for Applications is another way to restrict it.
>    Without a restriction, the role allows sending as any mailbox in the tenant. Allow time for
>    a changed policy to apply before testing.
> 4. On **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – this
>    tenant** under **Sign in with**. Leave **Identity client ID** empty for the system-assigned
>    identity, or enter the user-assigned identity’s client ID. Do not supply a tenant or application
>    ID; this choice neither asks for nor accepts them. Enter **Sending mailbox** and **Application
>    address**, then save and test as described below.

New:

>    The group must hold the sending mailbox. RBAC for Applications is another way to restrict it.
>    Without a restriction, the role allows sending as any mailbox in the tenant. Allow time for
>    a changed policy to apply before testing.
> 4. On the **Server** tab of **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – this
>    tenant** under **Sign in with**. Leave **Identity client ID** empty for the system-assigned
>    identity, or enter the user-assigned identity’s client ID. Do not supply a tenant or application
>    ID; this choice neither asks for nor accepts them. Enter **Sending mailbox** and **Application
>    address**, then save and test as described below.

Old:

>    Confirm that the app has the **Mail.Send** application permission in that tenant.
> 4. In the customer’s Exchange Online tenant, restrict the app to the sending mailbox with an
>    application access policy, using `-AppId <the app's client ID>`, or RBAC for Applications.
>    For an application access policy, use a mail-enabled security group holding that mailbox.
>    Allow time for the restriction to apply.
> 5. On **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – hosted
>    in another tenant** under **Sign in with**. Enter the customer’s **Tenant ID**, the multitenant
>    app’s **Application (client) ID** and the user-assigned **Identity client ID**. All three are
>    required. Enter **Sending mailbox** and **Application address**, then save and test below.

New:

>    Confirm that the app has the **Mail.Send** application permission in that tenant.
> 4. In the customer’s Exchange Online tenant, restrict the app to the sending mailbox with an
>    application access policy, using `-AppId <the app's client ID>`, or RBAC for Applications.
>    For an application access policy, use a mail-enabled security group holding that mailbox.
>    Allow time for the restriction to apply.
> 5. On the **Server** tab of **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – hosted
>    in another tenant** under **Sign in with**. Enter the customer’s **Tenant ID**, the multitenant
>    app’s **Application (client) ID** and the user-assigned **Identity client ID**. All three are
>    required. Enter **Sending mailbox** and **Application address**, then save and test below.

### run/configure.md

Old:

> With Operations access, open **Settings › This instance › Deployment**. **Capability groups**
> shows what this deployment serves. **Database** shows the migration revision. Each settings table
> shows **Setting**, **Value**, **Default**, **Source** and **What it controls**.
> **Environment** means explicitly supplied; **Default** means the engine chose its default.
> Secrets show only **Set** or **Not set**, and the database address hides its password.
> This page is read only. At the top it names the API address used by this browser. Normally that
> is the address you opened; `VITE_API_URL` can select another engine when building the frontend.
> Changing that build setting requires rebuilding the frontend, rather than restarting the engine.
> 
> The groups are **Model administration**, **Workspace administration**, **Integration jobs** and
> **Webhook subscriptions**, each with **On** or **Off**, its switching setting and applicable limits.
> Below **Database › Migration revision**, the tables are **Runtime**, **Capability settings**,
> **Batch and job limits**, **Webhook subscriptions** and **AI proposals**. The warning
> **Cursors do not survive a restart** means no stable `RDM_CURSOR_SIGNING_KEY` was supplied.
> Set one shared key and recreate all processes; clients must restart lists using old cursors.

New:

> With Operations access, open **Settings › This instance › Deployment**. **Capability groups**
> shows what this deployment serves. **Database** shows the migration revision. Each setting has a row with its name, what it controls, its value and source; the default appears only when the value differs.
> **Environment** means explicitly supplied; **Default** means the engine chose its default.
> Secrets show only **Set** or **Not set**, and the database address hides its password.
> This page is read only. At the top it names the API address used by this browser. Normally that
> is the address you opened; `VITE_API_URL` can select another engine when building the frontend.
> Changing that build setting requires rebuilding the frontend, rather than restarting the engine.
> 
> The groups are **Model administration**, **Workspace administration**, **Integration jobs** and
> **Webhook subscriptions**, each with **On** or **Off**, its switching setting and applicable limits.
> Below **Database › Migration revision**, the settings are grouped under **Runtime**, **Capability settings**,
> **Batch and job limits**, **Webhook subscriptions** and **AI proposals**. The warning
> **Cursors do not survive a restart** means no stable `RDM_CURSOR_SIGNING_KEY` was supplied.
> Set one shared key and recreate all processes; clients must restart lists using old cursors.

### run/production-checklist.md

No change.

### guide/integrate/connect-an-assistant.md

Old:

> Ask a security administrator for the **Address** under **Settings › Connections › Agent access › How to connect**. It ends in `/mcp`. If the page says **Agent access is off**, an operator must enable `MCP_ENABLED` and restart the engine. [Set up AI](/docs/run/set-up-ai/#4-enable-external-agent-access-if-needed) covers that deployment step.

New:

> Ask a security administrator for the **Address** under **Settings › Connections › Agent access**, on the **Access** tab under **How to connect**. It ends in `/mcp`. If the page says **Agent access is off**, an operator must enable `MCP_ENABLED` and restart the engine. [Set up AI](/docs/run/set-up-ai/#4-enable-external-agent-access-if-needed) covers that deployment step.

Old:

> On **Agent access**, administrators can inspect **Last used**, **Calls, 30 days** and the **Calls** outcomes. Use the request reference when reporting a failed call, rather than sending credentials or reference-data values.

New:

> On **Agent access**, administrators can inspect **Last used**, **Calls, 30 days** and the outcomes on the **Calls** tab. Use the request reference when reporting a failed call, rather than sending credentials or reference-data values.

### guide/integrate/subscribe-a-webhook-and-verify-it.md

No change.

### integrate/consumer-events-and-webhooks.md

No change.

### journeys/manage-access.md

No change.

### journeys/work-with-an-assistant.md

Old:

> With **Operations**, open **Settings › This instance › AI** to inspect which help is on and
> what may be sent. [Check the AI provider](/docs/guide/administer/check-the-ai-provider/) leads
> through **Send a test request**, which contains no reference data, then the call records and
> 30-day totals. A refused key, unreachable service or unreadable answer is recorded as a failure.
> An absent provider does not disable an independently enabled built-in assistant. Neither enabled
> means no built-in AI action and nothing sent by those features.

New:

> With **Operations**, open **Settings › This instance › AI**, then its **Settings** tab, to inspect which help is on and
> what may be sent. [Check the AI provider](/docs/guide/administer/check-the-ai-provider/) leads
> through **Send a test request**, which contains no reference data, then the call records and
> 30-day totals. A refused key, unreachable service or unreadable answer is recorded as a failure.
> An absent provider does not disable an independently enabled built-in assistant. Neither enabled
> means no built-in AI action and nothing sent by those features.

### journeys/shape-a-model.md

No change.

## Outdated Settings screenshots and recapture candidates

No screenshot was changed, renamed or rereferenced. Each row lists its filename, screen/state and every assigned page referencing it. Keep the state and controls named in the existing alt text visible, using the current Settings layout.

Visually inspected and confirmed outdated: `admin-people.png` (split list and empty selection), `admin-client.png` (split list and header actions), `admin-ai-test-answered.png` (settings/test/calls together), `use-import-file-delete-confirm.png` (old split-page background and deletion buttons).

The remaining entries are recapture candidates identified from their documented Settings surface and the changed source; each has not been visually inspected. A dialog can remain correct while its background shows the old page. AI test results and Calls now need separate tab captures; retain filenames until the screenshot owner decides how to replace them.

| Screenshot | Screen/state to retain | Referencing pages |
| --- | --- | --- |
| `admin-about.png` | About with engine and active model release details | `administer/deployment-pages.md` |
| `admin-account-sessions.png` | Account with sign-in methods and the beginning of the session list | `administer/sign-in.md` |
| `admin-agent-access-enabled.png` | Enabled Agent access with connection information and empty client and assistant sections | `administer/agent-access.md` |
| `admin-agent-access.png` | Agent access is off, with instructions for the operator | `administer/agent-access.md` |
| `admin-agent-block.png` | Confirmation to block an assistant with its affected session count | `guide/administer/manage-agent-access.md` |
| `admin-agent-calls.png` | Calls by Stops checker (guide), with answered and refused outcomes and argument names only | `administer/agent-access.md` |
| `admin-agent-new-client.png` | New agent client dialog with its Name field and creation action | `guide/administer/manage-agent-access.md` |
| `admin-agent-register.png` | Register an assistant dialog showing Name and Return addresses | `guide/administer/manage-agent-access.md` |
| `admin-ai-calls.png` | Answered AI provider calls with token counts, duration and unreported costs | `administer/ai.md` |
| `admin-ai-settings.png` | AI settings showing the assistant and provider on, the send level and available features | `administer/ai.md` |
| `admin-ai-test-answered.png` | AI provider test result with the answered notice and the recorded test call | `guide/administer/check-the-ai-provider.md` |
| `admin-ai-test-failed.png` | Failed AI provider test showing its reason and failed call | `guide/administer/check-the-ai-provider.md` |
| `admin-api-reference.png` | API reference Sources table with the management interface and a consumer interface | `administer/api-reference-and-consumer-api-pages.md` |
| `admin-approval.png` | Workspace Approval tab with approval required and second-person rule off | `administer/approval-policies.md`; `guide/administer/set-an-approval-policy.md` |
| `admin-audit-person.png` | A person's Changes page with workspace, kind and period filters | `administer/audit.md`; `guide/administer/find-who-changed-something.md` |
| `admin-client-inactive-rotate.png` | Rotate secret for a deactivated client, with the recovery note and Stop it now selected | `administer/clients.md`; `guide/administer/rotate-a-client-secret.md` |
| `admin-client-new.png` | New client dialog with Name and Create and show its secret | `guide/administer/create-a-client.md` |
| `admin-client-rotate.png` | Rotate secret dialog with overlap choices and Make a new secret | `guide/administer/rotate-a-client-secret.md` |
| `admin-client.png` | Client detail with ID, secrets and a workspace consumer grant | `administer/clients.md`; `guide/administer/create-a-client.md` |
| `admin-clients.png` | Clients catalogue with one active client and no selection | `administer/clients.md` |
| `admin-consumer-apis.png` | Consumer APIs with an interface’s version, copy controls and operation descriptions | `administer/api-reference-and-consumer-api-pages.md` |
| `admin-grant-consumer-api.png` | Consumer API grant grid with API rows and workspace columns | `guide/administer/grant-a-consumer-api-to-a-client.md` |
| `admin-grant-dialog.png` | Grant dialog with role selection and workspace or whole-instance scope | `guide/administer/grant-a-role.md` |
| `admin-grant-narrowed.png` | Grant dialog limited to one role and workspace with record-type narrowing | `guide/administer/narrow-a-grant-to-record-types.md` |
| `admin-grants-person.png` | A person's roles showing scope, restrictions and source | `administer/roles-and-grants.md`; `administer/audit.md`; `guide/administer/find-who-changed-something.md`; `guide/administer/grant-a-role.md` |
| `admin-grants-workspace.png` | Workspace Access tab showing people and their grants | `administer/roles-and-grants.md` |
| `admin-group-members.png` | Local group with two fictional members selected and controls to add or remove members | `guide/administer/manage-a-group.md` |
| `admin-group-new.png` | New group dialog with Name and optional Description | `guide/administer/manage-a-group.md` |
| `admin-groups.png` | Groups list with no groups and a New group button | `administer/people-and-groups.md`; `guide/administer/manage-a-group.md` |
| `admin-local-signin-off.png` | Local accounts after turning ordinary password sign-in off, with Turn on available | `guide/administer/turn-off-local-sign-in.md` |
| `admin-mail-microsoft365-entra.png` | The Microsoft 365 mail form with Managed identity – this tenant selected and What to set up in Microsoft Entra expanded. | `administer/mail.md`; `run/sign-in-and-mail-setup.md` |
| `admin-mail-microsoft365-menu.png` | The Microsoft 365 mail form with the Sign in with menu open to show its four choices. | `administer/mail.md` |
| `admin-mail-microsoft365-secret.png` | The Microsoft 365 mail form with Client secret selected and example IDs, a masked secret and a sending mailbox entered. | `administer/mail.md` |
| `admin-mail-settings.png` | Mail server form before configuration, with Test message unavailable | `administer/mail.md`; `guide/administer/set-up-mail.md`; `run/sign-in-and-mail-setup.md` |
| `admin-people.png` | People list with Active and Deactivated filters and no person selected | `administer/people-and-groups.md` |
| `admin-person-admin.png` | Person's page with password status and account recovery actions | `guide/administer/help-someone-who-lost-a-device.md` |
| `admin-person-link-provider.png` | Provider sign-in linking dialog with the fictional existing target person selected | `guide/administer/link-a-provider-person.md` |
| `admin-person-reset-password.png` | One-time password-link dialog with copy control, expiry and acknowledgement | `guide/administer/add-a-person.md`; `guide/administer/help-someone-who-lost-a-device.md` |
| `admin-person-rita.png` | Person detail with sign-in methods and workspace role | `administer/people-and-groups.md` |
| `admin-person-second-factor.png` | Fictional person’s Sign-in section with an authenticator, named passkey and removal controls | `guide/administer/help-someone-who-lost-a-device.md` |
| `admin-role-new.png` | New role dialog with Name and Start from | `administer/roles-and-grants.md`; `guide/administer/create-a-custom-role.md` |
| `admin-roles.png` | Roles matrix comparing predefined roles by action group | `administer/roles-and-grants.md` |
| `admin-signin-local.png` | Local accounts settings with the second-factor requirement | `administer/sign-in.md`; `guide/administer/require-a-second-factor.md` |
| `admin-signin-provider-new.png` | New sign-in provider with identity, registration and groups fields | `administer/sign-in.md`; `guide/administer/add-a-sign-in-provider.md` |
| `admin-signin-provider.png` | Saved fictional OpenID Connect provider with redirect address, settings and signing-out choices | `guide/administer/add-a-sign-in-provider.md` |
| `admin-signin.png` | Sign-in catalogue with Local accounts on and no providers | `administer/sign-in.md` |
| `admin-signing-keys-retire.png` | Confirmation for immediate retirement of the current signing key | `guide/administer/rotate-signing-keys.md` |
| `admin-signing-keys.png` | Signing keys with a current Signing key and a replaced key still verifying | `administer/signing-keys.md`; `guide/administer/rotate-signing-keys.md` |
| `admin-webhook-deliveries.png` | Retrying webhook delivery with its attempts and receiver response | `administer/webhooks.md` |
| `admin-webhook-new.png` | The New webhook dialog with its source, event and delivery choices | `administer/webhooks.md`; `guide/administer/create-a-webhook.md` |
| `admin-webhook-resume.png` | Resume dialog for the fictional webhook suspended by an administrator, with continuation choices | `guide/administer/find-out-why-a-webhook-paused.md` |
| `admin-webhook-rotate.png` | Webhook key rotation dialog with overlap choices, before making a key | `guide/administer/rotate-a-webhook-key.md` |
| `admin-webhook-workspace-events.png` | New webhook with Workspace events selected and all three change-set events | `administer/webhooks.md`; `guide/administer/create-a-webhook.md` |
| `import-profile-next-version.png` | Import profile after a next-version check, with Accept and Ignore beside column differences, Needs a fix and disabled Load into a change set. | `guide/use/load-the-next-version-of-a-workbook.md` |
| `integrate-agent-access-connect.png` | Agent access enabled, showing the connection address and connection instructions | `guide/integrate/connect-an-assistant.md` |
| `job-results-and-file.png` | Completed export with state, retention, counts, file details and Download | `use/jobs.md` |
| `jobs-list.png` | Jobs list showing states, progress counts, requesters and available cancellation | `administer/jobs-and-limits.md` |
| `model-drafts.png` | Drafts listed separately with their base release and date | `model/releases.md` |
| `model-list.png` | Model list with releases, latest versions, draft counts and workspace use | `model/models.md` |
| `model-overview.png` | Model overview showing its newest release and the workspace running it | `model/models.md` |
| `model-release-compare.png` | Release history with baseline selector and semantic before and after changes | `guide/model/compare-releases.md` |
| `model-release-detail.png` | Immutable release with export and draft creation actions | `guide/model/export-a-release.md` |
| `model-releases.png` | Installed versions on a model's Releases tab | `model/releases.md` |
| `model-structure.png` | Read-only model structure with application and type counts | `model/releases.md` |
| `model-workspace-model.png` | Workspace overview identifying its model and applications | `model/releases.md` |
| `model-workspace-other-model.png` | A second workspace overview with a different model and applications | `model/releases.md` |
| `model-workspaces-list.png` | Workspaces listed with the model and release each runs | `model/models.md` |
| `notification-email-digest.png` | Notification email for an account without an email address or followed workspaces | `use/notifications-settings.md` |
| `release-retire-dialog.png` | Release retirement confirmation | `guide/model/retire-or-delete-a-release.md` |
| `release-technical-details.png` | Technical details identifying the release and its content hash | `guide/model/export-a-release.md` |
| `run-ai-provider-calls.png` | AI provider test result and recorded calls | `run/ai.md` |
| `run-ai-settings.png` | AI settings showing the assistant and provider on and the permitted send level | `run/ai.md` |
| `run-deployment.png` | Deployment showing capability states, limits and setting sources | `administer/deployment-pages.md`; `run/configure.md` |
| `run-jobs.png` | Jobs with queued, running and completed work | `run/background-jobs.md` |
| `run-operations.png` | Operations with workspace readiness, engine processes and backup rehearsal | `administer/deployment-pages.md` |
| `use-account-permissions.png` | Account permissions grouped by workspace and instance-wide responsibilities | `use/account.md` |
| `use-account-sessions.png` | Signed-in sessions with last activity, sign-in times and individual Sign out buttons | `use/account.md` |
| `use-account.png` | Account with identity, password, passkeys and authenticator setup | `use/account.md` |
| `use-import-file-delete-confirm.png` | Delete an uploaded workbook while keeping its import profile and loaded records | `guide/use/load-the-next-version-of-a-workbook.md` |
| `use-import-profile-delete-actions.png` | Import profile showing separate buttons to delete its uploaded file and the profile | `use/importing-and-exporting.md` |
| `use-import-profile-delete-confirm.png` | Confirmation to remove an import profile while retaining previously loaded records | `use/importing-and-exporting.md` |
| `use-notification-email-digest-settings.png` | Enabled notification email with delivery choices, digest frequency, time zone and next digest | `use/notifications-settings.md`; `guide/use/set-up-email-notices.md` |
| `use-workspace-default.png` | Workspace management showing the Default mark | `guide/model/make-a-workspace-the-default.md` |
| `use-workspaces-detail.png` | A workspace detail with its actions and Overview, Access, Approval and Activity tabs | `model/managing-workspaces.md` |
| `use-workspaces-manage.png` | Workspace management listing each workspace and its model release | `model/managing-workspaces.md` |
| `workspace-cannot-open.png` | Unavailable example workspace with its model-language reason, recovery review and other workspaces | `guide/use/open-a-retired-or-unavailable-workspace.md` |
| `workspace-retire-dialog.png` | Retire workspace confirmation | `guide/model/retire-or-delete-a-workspace.md` |
| `workspaces-new-dialog.png` | New workspace dialog showing name, key and model choice | `guide/model/create-a-workspace.md` |

Global account/workspace menus, record screens and workbook editor dialogs are not listed just because they show the surrounding application frame; changes there belong to other waves.
