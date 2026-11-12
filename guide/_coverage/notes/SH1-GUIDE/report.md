# SH1-GUIDE report

Reviewed 218 assigned pages: 87 changed, 131 no change. Only SH1 wording was changed; front matter, section structure and screenshot filenames are preserved.

## Per-page old and new text

Passages below reproduce the changed sentences with their surrounding paragraph where needed to keep the context exact. Unchanged sentences within a quoted paragraph are retained for context. Paths are relative to the repository root.


### `guide/src/content/docs/about/security-and-trust.md`


Old:

```markdown
Requests and assistant turns can incur charges or consume a subscription allowance, including
failed or discarded work. Operations staff can inspect who asked, the purpose, outcome, tokens
and reported cost on **Settings › Administration › AI**. An absent cost is not proof of free use.
A saved workbook layout that fits the next file can avoid another assistant session.
```


New:

```markdown
Requests and assistant turns can incur charges or consume a subscription allowance, including
failed or discarded work. Operations staff can inspect who asked, the purpose, outcome, tokens
and reported cost on **Settings › This instance › AI**. An absent cost is not proof of free use.
A saved workbook layout that fits the next file can avoid another assistant session.
```


### `guide/src/content/docs/administer/agent-access.md`


Old:

```markdown
Use **Settings › Security › Agent access** to manage assistants that connect to refiroo through the **Model Context Protocol (MCP)**. You need **Security administration** across the instance. The page shows how to connect, agent clients for systems, assistants people sign in with and the calls they made.
```


New:

```markdown
Use **Settings › Connections › Agent access** to manage assistants that connect to refiroo through the **Model Context Protocol (MCP)**. You need **Security administration** across the instance. The page shows how to connect, agent clients for systems, assistants people sign in with and the calls they made.
```


### `guide/src/content/docs/administer/ai.md`


Old:

```markdown
Use **Settings › Administration › AI** to check the AI features available in your instance and review their use. You need **Operations** across the instance to open this page and send a test request. The predefined **Operator** role holds it.
```


New:

```markdown
Use **Settings › This instance › AI** to check the AI features available in your instance and review their use. You need **Operations** across the instance to open this page and send a test request. The predefined **Operator** role holds it.
```


### `guide/src/content/docs/administer/api-reference-and-consumer-api-pages.md`


Old:

```markdown
Use **Settings › Integration › API reference** to find the interactive reference for refiroo’s interfaces. Use **Consumer APIs** to inspect the read interfaces declared by the active model. These pages are read-only: neither changes a definition nor grants access.
```


New:

```markdown
Use **Settings › Connections › API reference** to find the interactive reference for refiroo’s interfaces. Use **Consumer APIs** to inspect the read interfaces declared by the active model. These pages are read-only: neither changes a definition nor grants access.
```


### `guide/src/content/docs/administer/approval-policies.md`


No change.


### `guide/src/content/docs/administer/audit.md`


Old:

```markdown
Open **Settings › Security › People** or **Clients**, select the identity and choose
**See changes**. You can also follow a person's name from history where it is offered.
The page shows newest first, grouped by day, across the workspaces you may read.
```


New:

```markdown
Open **Settings › People and access › People** or **Settings › Connections › Clients**, select the identity and choose
**See changes**. You can also follow a person's name from history where it is offered.
The page shows newest first, grouped by day, across the workspaces you may read.
```


### `guide/src/content/docs/administer/clients.md`


Old:

```markdown
You need **Security administration** to manage **Settings › Security › Clients**.
Use **Search clients** (**Name**) to search the list, which separates **Active** and **Deactivated** clients and shows
when a client last authenticated, or **No token yet** when it has not.
```


New:

```markdown
You need **Security administration** to manage **Settings › Connections › Clients**.
Use **Search clients** (**Name**) to search the list, which separates **Active** and **Deactivated** clients and shows
when a client last authenticated, or **No token yet** when it has not.
```


Old:

```markdown
Create an external assistant's client with **New agent client** under **Settings › Security › Agent access**. Its grants are restricted to reading and preparing changes through that connection; it cannot approve, publish or write live data. It is distinct from an ordinary integration client. Follow [Manage an assistant's access](/docs/guide/administer/manage-agent-access/).
```


New:

```markdown
Create an external assistant's client with **New agent client** under **Settings › Connections › Agent access**. Its grants are restricted to reading and preparing changes through that connection; it cannot approve, publish or write live data. It is distinct from an ordinary integration client. Follow [Manage an assistant's access](/docs/guide/administer/manage-agent-access/).
```


### `guide/src/content/docs/administer/deployment-pages.md`


Old:

```markdown
Use these Settings pages to identify the installation and discuss a problem with its operator. **General › About** is available to signed-in people. **Administration › Deployment** and **Operations** need **Operations**, held by the predefined Operator role. Security administrator alone does not provide it.
```


New:

```markdown
Use these Settings pages to identify the installation and discuss a problem with its operator. **This instance › About** is available to signed-in people. **This instance › Deployment** and **Operations** need **Operations**, held by the predefined Operator role. Security administrator alone does not provide it.
```


### `guide/src/content/docs/administer/jobs-and-limits.md`


Old:

```markdown
Open **Settings › Data operations › Jobs** to see bulk writes, imports and exports across the workspaces available to you. The list is newest first and shows the job, workspace, state, item counts, requester, creation and finish times. Select a job for its details. This page also shows the deployment limits; it does not edit them.
```


New:

```markdown
Open **Settings › This instance › Jobs** to see bulk writes, imports and exports across the workspaces available to you. The list is newest first and shows the job, workspace, state, item counts, requester, creation and finish times. Select a job for its details. This page also shows the deployment limits; it does not edit them.
```


Old:

```markdown
The operator changes these limits in the deployment configuration and restarts the service. **Settings › Administration › Deployment** shows their sources and meanings to people with **Operations**. See [Deployment pages](/docs/administer/deployment-pages/). Change-feed retention is shown on **Consumer APIs**, separately from job retention.
```


New:

```markdown
The operator changes these limits in the deployment configuration and restarts the service. **Settings › This instance › Deployment** shows their sources and meanings to people with **Operations**. See [Deployment pages](/docs/administer/deployment-pages/). Change-feed retention is shown on **Consumer APIs**, separately from job retention.
```


### `guide/src/content/docs/administer/mail.md`


Old:

```markdown
Use **Settings › Integration › Mail** to connect refiroo to your organisation’s mail server. You need **Security administration** for the whole instance. Mail carries password links and, when people choose them, inbox notices and digests. It never sends a password or an authenticator code.
```


New:

```markdown
Use **Settings › This instance › Mail** to connect refiroo to your organisation’s mail server. You need **Security administration** for the whole instance. Mail carries password links and, when people choose them, inbox notices and digests. It never sends a password or an authenticator code.
```


Old:

```markdown
Each person controls their own delivery under **Settings › General › Notification email › Email**. **Email me when something arrives in my inbox** uses the address shown there. Without an e-mail address, or for a client, the page explains there is nothing to choose. Administrators do not choose these preferences for others.
```


New:

```markdown
Each person controls their own delivery under **Settings › You › Notification email › Email**. **Email me when something arrives in my inbox** uses the address shown there. Without an e-mail address, or for a client, the page explains there is nothing to choose. Administrators do not choose these preferences for others.
```


### `guide/src/content/docs/administer/people-and-groups.md`


Old:

```markdown
Use **Settings › Security › People** to manage people, and **Groups** to give several
people the same roles. You need **Security administration**, held by the predefined
Security administrator role. That role manages access; it does not itself allow reading workspace data.
```


New:

```markdown
Use **Settings › People and access › People** to manage people, and **Groups** to give several
people the same roles. You need **Security administration**, held by the predefined
Security administrator role. That role manages access; it does not itself allow reading workspace data.
```


### `guide/src/content/docs/administer/permissions-reference.md`


Old:

```markdown
Use this reference when choosing a role or checking why someone cannot complete a task.
Open **Settings › Security › Roles** with **Security administration** to compare the
matrix or create a custom role. Roles select whole action groups, not individual actions.
[Roles and grants](/docs/administer/roles-and-grants/) explains where grants apply and
how direct and group access combine. Follow [Create a custom role](/docs/guide/administer/create-a-custom-role/)
to put the groups together.
```


New:

```markdown
Use this reference when choosing a role or checking why someone cannot complete a task.
Open **Settings › People and access › Roles** with **Security administration** to compare the
matrix or create a custom role. Roles select whole action groups, not individual actions.
[Roles and grants](/docs/administer/roles-and-grants/) explains where grants apply and
how direct and group access combine. Follow [Create a custom role](/docs/guide/administer/create-a-custom-role/)
to put the groups together.
```


### `guide/src/content/docs/administer/roles-and-grants.md`


Old:

```markdown
Open **Security › Roles** to compare roles by action group. The predefined roles cannot
be edited. The following table lists their action groups; the descriptions below explain them.
```


New:

```markdown
Open **People and access › Roles** to compare roles by action group. The predefined roles cannot
be edited. The following table lists their action groups; the descriptions below explain them.
```


### `guide/src/content/docs/administer/sign-in.md`


Old:

```markdown
Open **Settings › Security › Sign-in** to choose how people prove who they are.
You need **Security administration**. Sign-in establishes identity; [roles and grants](/docs/administer/roles-and-grants/)
decide what that identity may do afterwards.
```


New:

```markdown
Open **Settings › People and access › Sign-in** to choose how people prove who they are.
You need **Security administration**. Sign-in establishes identity; [roles and grants](/docs/administer/roles-and-grants/)
decide what that identity may do afterwards.
```


### `guide/src/content/docs/administer/signing-keys.md`


Old:

```markdown
Open **Settings › Security › Signing keys** with **Security administration**.
The list shows **Key ID**, **State**, **Created**, **Replaced** and **Retired**.
**No key yet: one is made with the first token.** means the instance has not needed a signing key yet. You do not need to create or delete a row to clear that state. The current key is **Signing**. A replaced key shows **Verifying until** with the end time
while it still accepts access it signed. A retired key no longer does so.
```


New:

```markdown
Open **Settings › People and access › Signing keys** with **Security administration**.
The list shows **Key ID**, **State**, **Created**, **Replaced** and **Retired**.
**No key yet: one is made with the first token.** means the instance has not needed a signing key yet. You do not need to create or delete a row to clear that state. The current key is **Signing**. A replaced key shows **Verifying until** with the end time
while it still accepts access it signed. A retired key no longer does so.
```


### `guide/src/content/docs/administer/webhooks.md`


Old:

```markdown
Use **Settings › Integration › Webhooks** to send a consumer API’s declared record events or the workspace’s change-set events to another system. You need **Integration administration** in the source workspace. Security administration alone does not grant it. The operator must also enable webhooks in the deployment.
```


New:

```markdown
Use **Settings › Connections › Webhooks** to send a consumer API’s declared record events or the workspace’s change-set events to another system. You need **Integration administration** in the source workspace. Security administration alone does not grant it. The operator must also enable webhooks in the deployment.
```


### `guide/src/content/docs/examples/the-consumer-api.md`


Old:

```markdown
In the browser, **Settings › Integration › Consumer APIs** lists the selected workspace's contracts
and their documents. For the reference example, the authenticated index is
`/api/consumer?workspace=graubuenden`; its entry points to
`/api/consumer/stops/v1/openapi.json?workspace=graubuenden`.
The starter instead uses the key `rdm` in a workspace running that model. Always inspect the intended
workspace: installing a release alone does not activate it there.
```


New:

```markdown
In the browser, **Settings › Connections › Consumer APIs** lists the selected workspace's contracts
and their documents. For the reference example, the authenticated index is
`/api/consumer?workspace=graubuenden`; its entry points to
`/api/consumer/stops/v1/openapi.json?workspace=graubuenden`.
The starter instead uses the key `rdm` in a workspace running that model. Always inspect the intended
workspace: installing a release alone does not activate it there.
```


### `guide/src/content/docs/guide/administer/add-a-person.md`


Old:

```markdown
1. Open **Settings › Security › People**. Check the Active list or search by name
   or e-mail to avoid creating another account for the same person. Check **Deactivated**
   too; **Restore** reactivates an existing person with their retained roles and groups.
2. Choose **New person**. Enter **Name**, the display name used in lists and history, up to 200 characters.
3. Enter **E-mail**, the address they sign in with. Another person cannot have the same address.
4. Leave **An administrator manages this person’s sign-in** unticked for someone who manages
   their own password and sign-in methods. Tick it for an account whose sign-in you look after,
   such as a shared reception account or an account on a training machine. Its help text explains
   that they cannot change their password, second factor or passkeys, or sign out other browsers.
   Only someone with **Security administration** can set this option. It is off by default.
   Wrong passwords entered for a shared account's e-mail address slow sign-in for everyone
   using it. See [People and groups](/docs/administer/people-and-groups/#sign-in-managed-by-an-administrator)
   for the limits and recovery options.
5. Choose **Create and make a password link**. **Cancel** leaves the person uncreated.
   If a field is refused, correct the named problem and submit again.
```


New:

```markdown
1. Open **Settings › People and access › People**. Check the Active list or search by name
   or e-mail to avoid creating another account for the same person. Check **Deactivated**
   too; **Restore** reactivates an existing person with their retained roles and groups.
2. Choose **New person**. Enter **Name**, the display name used in lists and history, up to 200 characters.
3. Enter **E-mail**, the address they sign in with. Another person cannot have the same address.
4. Leave **An administrator manages this person’s sign-in** unticked for someone who manages
   their own password and sign-in methods. Tick it for an account whose sign-in you look after,
   such as a shared reception account or an account on a training machine. Its help text explains
   that they cannot change their password, second factor or passkeys, or sign out other browsers.
   Only someone with **Security administration** can set this option. It is off by default.
   Wrong passwords entered for a shared account's e-mail address slow sign-in for everyone
   using it. See [People and groups](/docs/administer/people-and-groups/#sign-in-managed-by-an-administrator)
   for the limits and recovery options.
5. Choose **Create and make a password link**. **Cancel** leaves the person uncreated.
   If a field is refused, correct the named problem and submit again.
```


### `guide/src/content/docs/guide/administer/add-a-sign-in-provider.md`


Old:

```markdown
1. Open **Settings › Security › Sign-in** and choose **New provider**. The catalogue keeps **Local accounts** separate from **Providers**.
2. Enter **Name on the sign-in button**. People see **Continue with** followed by that name. Check the suggested **Key**: it forms part of the registered address and cannot change after saving. The names password, passkey and local are reserved; choose a distinct key.
3. Enter **Issuer**, **Client ID** and **Client secret** from the sign-in administrator’s registration. The issuer must match the provider exactly. The saved secret is kept sealed and never shown again.
4. If the provider supplies groups, enter **Groups claim**, using the field name supplied by its administrator. Empty means provider groups are not used. You can [create provider groups and grant their roles](/docs/guide/administer/manage-a-group/#use-a-provider-group) before anyone signs in.
5. Keep **Offer it on the sign-in page now** selected if it should be enabled, then choose **Save provider**. It shows **Checking and saving…** while checking an enabled provider. If **The provider was not saved** appears, correct the stated issuer, connectivity, certificate or registration problem with the sign-in administrator. **Cancel** leaves it uncreated.
```


New:

```markdown
1. Open **Settings › People and access › Sign-in** and choose **New provider**. The catalogue keeps **Local accounts** separate from **Providers**.
2. Enter **Name on the sign-in button**. People see **Continue with** followed by that name. Check the suggested **Key**: it forms part of the registered address and cannot change after saving. The names password, passkey and local are reserved; choose a distinct key.
3. Enter **Issuer**, **Client ID** and **Client secret** from the sign-in administrator’s registration. The issuer must match the provider exactly. The saved secret is kept sealed and never shown again.
4. If the provider supplies groups, enter **Groups claim**, using the field name supplied by its administrator. Empty means provider groups are not used. You can [create provider groups and grant their roles](/docs/guide/administer/manage-a-group/#use-a-provider-group) before anyone signs in.
5. Keep **Offer it on the sign-in page now** selected if it should be enabled, then choose **Save provider**. It shows **Checking and saving…** while checking an enabled provider. If **The provider was not saved** appears, correct the stated issuer, connectivity, certificate or registration problem with the sign-in administrator. **Cancel** leaves it uncreated.
```


### `guide/src/content/docs/guide/administer/check-the-ai-provider.md`


Old:

```markdown
1. Open **Settings › Administration › AI**. Under **What is switched on**, check **Provider**. If neither feature is configured, the page says **Neither the assistant nor an AI provider is set up**. If only the assistant is on, there is no provider test button. Ask the operator to configure a provider if your task needs one.
2. Read **Settings**. Check **Model**, **Endpoint**, whether **Key** is set, and **What may be sent**. The secret is never displayed. A provider hosted outside your organisation receives the data allowed for each feature; make sure that arrangement is acceptable before inviting people to use it.
3. Read **What the AI provider is asked**. Each feature says **Available** or **Unavailable**. An unavailable feature needs more information than the configured send level permits; a successful connection test cannot make it available. Review the data policy with the operator rather than assuming the test failed.
4. Under **Test request**, choose **Send a test request**. The button says **Sending…** while it waits. The fixed request contains none of your reference data, and makes a call recorded below.
5. On success, **The AI provider answered** shows how long the answer took and which model answered. On failure, **The test request failed** gives the reason. This does not prove that suggestions are correct or that the built-in assistant works.
```


New:

```markdown
1. Open **Settings › This instance › AI**. Under **What is switched on**, check **Provider**. If neither feature is configured, the page says **Neither the assistant nor an AI provider is set up**. If only the assistant is on, there is no provider test button. Ask the operator to configure a provider if your task needs one.
2. Read **Settings**. Check **Model**, **Endpoint**, whether **Key** is set, and **What may be sent**. The secret is never displayed. A provider hosted outside your organisation receives the data allowed for each feature; make sure that arrangement is acceptable before inviting people to use it.
3. Read **What the AI provider is asked**. Each feature says **Available** or **Unavailable**. An unavailable feature needs more information than the configured send level permits; a successful connection test cannot make it available. Review the data policy with the operator rather than assuming the test failed.
4. Under **Test request**, choose **Send a test request**. The button says **Sending…** while it waits. The fixed request contains none of your reference data, and makes a call recorded below.
5. On success, **The AI provider answered** shows how long the answer took and which model answered. On failure, **The test request failed** gives the reason. This does not prove that suggestions are correct or that the built-in assistant works.
```


### `guide/src/content/docs/guide/administer/create-a-client.md`


Old:

```markdown
1. Open **Settings › Security › Clients**. Search by **Name** to check whether the system
   already has a client. Check **Deactivated** as well before creating a duplicate.
2. Choose **New client**. Enter **Name**, a name people can recognise in access lists and
   history. Choose **Create and show its secret**. **Cancel** creates nothing.
3. In **Copy the client's secret**, copy **Client secret** and **Client ID** into the
   integration's agreed secure store. The full secret is shown once; after closing, only
   its last four characters identify it. Choose **I have copied it** after saving both.
4. If creation is refused, read the message and correct the problem. If the client exists
   but its one-time secret was lost, rotate its secret instead of creating it again.
```


New:

```markdown
1. Open **Settings › Connections › Clients**. Search by **Name** to check whether the system
   already has a client. Check **Deactivated** as well before creating a duplicate.
2. Choose **New client**. Enter **Name**, a name people can recognise in access lists and
   history. Choose **Create and show its secret**. **Cancel** creates nothing.
3. In **Copy the client's secret**, copy **Client secret** and **Client ID** into the
   integration's agreed secure store. The full secret is shown once; after closing, only
   its last four characters identify it. Choose **I have copied it** after saving both.
4. If creation is refused, read the message and correct the problem. If the client exists
   but its one-time secret was lost, rotate its secret instead of creating it again.
```


### `guide/src/content/docs/guide/administer/create-a-custom-role.md`


Old:

```markdown
1. Open **Settings › Security › Roles**. Read the matrix first: each column is a role and each row is an action group. A predefined role cannot be edited or deleted.
2. Choose **New role**. Enter **Name**, then choose **Start from**. **Nothing** creates an empty role; selecting an existing role copies its action groups. It does not change the source role or keep the two linked.
3. Choose **Create role**. The new role appears in the matrix with its editing controls. If **The role was not created** appears, correct the stated problem. **Cancel** closes without creating it.
4. Tick the action groups it needs. Set the name and optional description, then choose **Save role**. An empty role permits nothing. Administrative groups do not imply Browse; add Browse only if the responsibility needs workspace data.
5. Follow [Grant a role](/docs/guide/administer/grant-a-role/) to give it to a person, group or client in the intended scope. Roles containing only instance responsibilities must be granted for **The whole instance**.
6. Check the recipient’s effective access, including other direct and group grants. Their own **Account › What you can do** shows the result. Changes apply on the next request.
```


New:

```markdown
1. Open **Settings › People and access › Roles**. Read the matrix first: each column is a role and each row is an action group. A predefined role cannot be edited or deleted.
2. Choose **New role**. Enter **Name**, then choose **Start from**. **Nothing** creates an empty role; selecting an existing role copies its action groups. It does not change the source role or keep the two linked.
3. Choose **Create role**. The new role appears in the matrix with its editing controls. If **The role was not created** appears, correct the stated problem. **Cancel** closes without creating it.
4. Tick the action groups it needs. Set the name and optional description, then choose **Save role**. An empty role permits nothing. Administrative groups do not imply Browse; add Browse only if the responsibility needs workspace data.
5. Follow [Grant a role](/docs/guide/administer/grant-a-role/) to give it to a person, group or client in the intended scope. Roles containing only instance responsibilities must be granted for **The whole instance**.
6. Check the recipient’s effective access, including other direct and group grants. Their own **Account › What you can do** shows the result. Changes apply on the next request.
```


### `guide/src/content/docs/guide/administer/create-a-webhook.md`


Old:

```markdown
1. Open **Settings › Integration › Webhooks** and choose **New webhook**. If webhooks are off, ask the operator to enable them. Workspace events need no consumer API declaration.
2. In **Webhook**, enter a readable **Name** and the receiver’s **URL**. Use its final HTTPS address; redirects are not followed. Private and localhost receivers need the operator to allow private destinations on this instance. Plain HTTP is accepted only for a localhost receiver when the operator has allowed private destinations. Link-local destinations are always refused. If the address is refused, ask the operator to review it before trying again.
3. In **Source › Events from**, choose **Consumer API** for declared record changes, or **Workspace events** for change-set steps. If no consumer API declares events, only **Workspace events** is offered. For a consumer source, select **Consumer API** too.
4. Select **Workspace**. The list offers active workspaces where you hold Integration administration. Check the source and workspace carefully: they cannot be changed after creation.
5. Under **Events**, keep **All events**, or select **Chosen events**, then **Choose events** and the required entries. At least one event is required. For workspace events the choices are **change-set.submitted** (submitted for approval), **change-set.approved** (approved and published), and **change-set.sent-back** (returned to its author). **All events (3)** selects all three.
6. For a consumer source, under **Filters**, leave none to receive every event of the chosen kinds, or choose **Add filter**. Enter each value and press Enter. Several values for one filter are alternatives. If there are no declared filters, none can be added here. Workspace events have no **Consumer API** selector, **Filters** or **Content** choices.
```


New:

```markdown
1. Open **Settings › Connections › Webhooks** and choose **New webhook**. If webhooks are off, ask the operator to enable them. Workspace events need no consumer API declaration.
2. In **Webhook**, enter a readable **Name** and the receiver’s **URL**. Use its final HTTPS address; redirects are not followed. Private and localhost receivers need the operator to allow private destinations on this instance. Plain HTTP is accepted only for a localhost receiver when the operator has allowed private destinations. Link-local destinations are always refused. If the address is refused, ask the operator to review it before trying again.
3. In **Source › Events from**, choose **Consumer API** for declared record changes, or **Workspace events** for change-set steps. If no consumer API declares events, only **Workspace events** is offered. For a consumer source, select **Consumer API** too.
4. Select **Workspace**. The list offers active workspaces where you hold Integration administration. Check the source and workspace carefully: they cannot be changed after creation.
5. Under **Events**, keep **All events**, or select **Chosen events**, then **Choose events** and the required entries. At least one event is required. For workspace events the choices are **change-set.submitted** (submitted for approval), **change-set.approved** (approved and published), and **change-set.sent-back** (returned to its author). **All events (3)** selects all three.
6. For a consumer source, under **Filters**, leave none to receive every event of the chosen kinds, or choose **Add filter**. Enter each value and press Enter. Several values for one filter are alternatives. If there are no declared filters, none can be added here. Workspace events have no **Consumer API** selector, **Filters** or **Content** choices.
```


### `guide/src/content/docs/guide/administer/find-out-why-a-webhook-paused.md`


Old:

```markdown
1. Open **Settings › Integration › Webhooks** and select the intended receiver. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save changes**. If another person changed the webhook, review the reloaded configuration before saving again.
5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.
```


New:

```markdown
1. Open **Settings › Connections › Webhooks** and select the intended receiver. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save changes**. If another person changed the webhook, review the reloaded configuration before saving again.
5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.
```


### `guide/src/content/docs/guide/administer/find-who-changed-something.md`


Old:

```markdown
1. Open **Settings › Security › People** or **Clients**. Search and select the identity.
   Check their e-mail address or client ID if similar names exist. For a deactivated identity,
   use the **Deactivated** list.
2. Choose **See changes**. The page names that person or client and lists their visible
   changes, newest first, grouped by day. It can cover several workspaces.
3. Set **Workspace** to the relevant workspace, or keep **All workspaces**.
   Under **What**, choose **Records**, **Relationships**, **Change sets**, **Publications**
   or **Model**, or keep **Everything**.
4. Choose **Period**: **Last 24 hours**, **Last 7 days**, **Last 30 days** or **Any time**.
   If no result matches, widen the filters. Use **Load more** to retrieve older entries.
5. Read the action, subject, changed-field summary, time and workspace. Open a linked title
   to inspect the surviving subject. Use the record's own History for the changed values;
   the person's Changes page is a summary.
```


New:

```markdown
1. Open **Settings › People and access › People** or **Settings › Connections › Clients**. Search and select the identity.
   Check their e-mail address or client ID if similar names exist. For a deactivated identity,
   use the **Deactivated** list.
2. Choose **See changes**. The page names that person or client and lists their visible
   changes, newest first, grouped by day. It can cover several workspaces.
3. Set **Workspace** to the relevant workspace, or keep **All workspaces**.
   Under **What**, choose **Records**, **Relationships**, **Change sets**, **Publications**
   or **Model**, or keep **Everything**.
4. Choose **Period**: **Last 24 hours**, **Last 7 days**, **Last 30 days** or **Any time**.
   If no result matches, widen the filters. Use **Load more** to retrieve older entries.
5. Read the action, subject, changed-field summary, time and workspace. Open a linked title
   to inspect the surviving subject. Use the record's own History for the changed values;
   the person's Changes page is a summary.
```


### `guide/src/content/docs/guide/administer/grant-a-consumer-api-to-a-client.md`


Old:

```markdown
1. Open **Settings › Security › Clients**, find the intended system with **Search clients** and select it. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
5. Read the sentence describing what the client may read and choose **Grant**. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.
```


New:

```markdown
1. Open **Settings › Connections › Clients**, find the intended system with **Search clients** and select it. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
5. Read the sentence describing what the client may read and choose **Grant**. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.
```


### `guide/src/content/docs/guide/administer/grant-a-role.md`


Old:

```markdown
1. Open **Settings › Security › People**, **Groups** or **Clients** and select the recipient.
   Choose **Grant** in their roles or access section. The recipient is already chosen.
2. Alternatively, open **Settings › Workspaces**, select the workspace and choose **Access**,
   then **Grant**. Choose **Who** by searching for the person, group or client by name.
   Check the kind as well as the name before selecting them.
3. For a client, choose **Roles** under **What** if you are granting management access.
   **Consumer APIs** is a separate kind of grant; see [Create a client](/docs/guide/administer/create-a-client/).
```


New:

```markdown
1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient.
   Choose **Grant** in their roles or access section. The recipient is already chosen.
2. Alternatively, open **Settings › Workspaces**, select the workspace and choose **Access**,
   then **Grant**. Choose **Who** by searching for the person, group or client by name.
   Check the kind as well as the name before selecting them.
3. For a client, choose **Roles** under **What** if you are granting management access.
   **Consumer APIs** is a separate kind of grant; see [Create a client](/docs/guide/administer/create-a-client/).
```


### `guide/src/content/docs/guide/administer/help-someone-who-lost-a-device.md`


Old:

```markdown
1. Open **Settings › Security › People**, search for the person and select them.
   Check their name, e-mail address and sign-in method.
2. Under **Sign-in**, choose **Remove second factor…** beside
   **Second factor: authenticator app**. This button appears only when an app is set up.
3. Read the confirmation, then choose **Remove second factor**. Their app and its recovery
   codes stop working. **Cancel** leaves the factor in place. The change is recorded in activity.
4. For someone who manages their own sign-in, a required second factor means setting up a
   new app at their next password sign-in if no passkey remains. Otherwise, ask them to set
   it up again on **Account** and save new recovery codes. An administrator-managed account
   cannot set up a replacement. With no remaining factor, it signs in with the password
   alone even if the instance requires a second factor.
```


New:

```markdown
1. Open **Settings › People and access › People**, search for the person and select them.
   Check their name, e-mail address and sign-in method.
2. Under **Sign-in**, choose **Remove second factor…** beside
   **Second factor: authenticator app**. This button appears only when an app is set up.
3. Read the confirmation, then choose **Remove second factor**. Their app and its recovery
   codes stop working. **Cancel** leaves the factor in place. The change is recorded in activity.
4. For someone who manages their own sign-in, a required second factor means setting up a
   new app at their next password sign-in if no passkey remains. Otherwise, ask them to set
   it up again on **Account** and save new recovery codes. An administrator-managed account
   cannot set up a replacement. With no remaining factor, it signs in with the password
   alone even if the instance requires a second factor.
```


### `guide/src/content/docs/guide/administer/link-a-provider-person.md`


Old:

```markdown
1. Confirm the person’s identity through your organisation’s process. Identify the existing account whose roles and history should continue, and the new person created by provider sign-in. Check e-mail addresses and sign-in methods as well as names.
2. Open **Settings › Security › People** and select the new provider person. Do this before giving that new person a password, direct roles or local group memberships; those additions make linking unsafe and are refused.
3. Choose **Link to an existing person…**. In **Link this sign-in to an existing person**, search **Person** and select the existing active account. Read the sentence naming what moves and which person remains.
4. Choose **Link to …** with the intended person’s name. **Cancel** leaves the accounts separate. If **Not linked** appears, read the reason. Check the target is active and the source has no password, direct roles or local groups; resolve the conflict rather than linking to someone else to bypass it.
5. Check the existing person’s **Sign-in** section and groups. The provider identities and provider memberships move to this person. Their original roles and history continue. The newly created person is deactivated and their sessions end; it is not deleted.
6. Ask the person to sign in again through **Continue with …** and check they reach the existing account and intended workspace. Provider group roles apply alongside direct and local-group roles.
```


New:

```markdown
1. Confirm the person’s identity through your organisation’s process. Identify the existing account whose roles and history should continue, and the new person created by provider sign-in. Check e-mail addresses and sign-in methods as well as names.
2. Open **Settings › People and access › People** and select the new provider person. Do this before giving that new person a password, direct roles or local group memberships; those additions make linking unsafe and are refused.
3. Choose **Link to an existing person…**. In **Link this sign-in to an existing person**, search **Person** and select the existing active account. Read the sentence naming what moves and which person remains.
4. Choose **Link to …** with the intended person’s name. **Cancel** leaves the accounts separate. If **Not linked** appears, read the reason. Check the target is active and the source has no password, direct roles or local groups; resolve the conflict rather than linking to someone else to bypass it.
5. Check the existing person’s **Sign-in** section and groups. The provider identities and provider memberships move to this person. Their original roles and history continue. The newly created person is deactivated and their sessions end; it is not deleted.
6. Ask the person to sign in again through **Continue with …** and check they reach the existing account and intended workspace. Provider group roles apply alongside direct and local-group roles.
```


### `guide/src/content/docs/guide/administer/manage-a-group.md`


Old:

```markdown
1. Open **Settings › Security › Groups**. Use **Search groups** (**Group name**) first to see whether the
   intended group already exists. Choose a result to manage it, or **New group** to create one.
2. Enter **Name** and **Description (optional)**. The description can explain who belongs
   and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
3. Choose **Create group**. The group opens with its roles and members. **Cancel** closes
   without creating it. If saving fails, read **Not saved**, correct the problem and retry.
```


New:

```markdown
1. Open **Settings › People and access › Groups**. Use **Search groups** (**Group name**) first to see whether the
   intended group already exists. Choose a result to manage it, or **New group** to create one.
2. Enter **Name** and **Description (optional)**. The description can explain who belongs
   and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
3. Choose **Create group**. The group opens with its roles and members. **Cancel** closes
   without creating it. If saving fails, read **Not saved**, correct the problem and retry.
```


### `guide/src/content/docs/guide/administer/manage-agent-access.md`


Old:

```markdown
Use **Settings › Security › Agent access** with **Security administration** across the instance. Read [Agent access](/docs/administer/agent-access/) first for permissions, data sent, call retention and the limits on prepared changes. External assistants may send permitted data to their own provider and incur charges there; refiroo's built-in AI send levels do not control them.
```


New:

```markdown
Use **Settings › Connections › Agent access** with **Security administration** across the instance. Read [Agent access](/docs/administer/agent-access/) first for permissions, data sent, call retention and the limits on prepared changes. External assistants may send permitted data to their own provider and incur charges there; refiroo's built-in AI send levels do not control them.
```


Old:

```markdown
1. Open **Settings › Security › Agent access**. If it says **Agent access is off**, ask the operator to enable it and restart the server. The page cannot switch it on.
2. Under **How to connect**, copy **Address** and give it to the person connecting their MCP assistant. Use the address shown rather than constructing one from the browser's current page.
3. Ask the person to add that address in their assistant. It opens this instance's sign-in page, naming the assistant and where it returns. They should check those details before signing in. The name is what the assistant says about itself.
4. After sign-in, the assistant uses the person's existing grants, limited to reading and preparing changes. It does not need a new Agent role. Under **Assistants people sign in with**, check its **Returns to**, **Signed in now** and **Last used**.
```


New:

```markdown
1. Open **Settings › Connections › Agent access**. If it says **Agent access is off**, ask the operator to enable it and restart the server. The page cannot switch it on.
2. Under **How to connect**, copy **Address** and give it to the person connecting their MCP assistant. Use the address shown rather than constructing one from the browser's current page.
3. Ask the person to add that address in their assistant. It opens this instance's sign-in page, naming the assistant and where it returns. They should check those details before signing in. The name is what the assistant says about itself.
4. After sign-in, the assistant uses the person's existing grants, limited to reading and preparing changes. It does not need a new Agent role. Under **Assistants people sign in with**, check its **Returns to**, **Signed in now** and **Last used**.
```


### `guide/src/content/docs/guide/administer/narrow-a-grant-to-record-types.md`


Old:

```markdown
1. Open **Settings › Security › People**, **Groups** or **Clients** and select the recipient. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Grant**.
6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.
```


New:

```markdown
1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Grant**.
6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.
```


### `guide/src/content/docs/guide/administer/require-a-second-factor.md`


Old:

```markdown
1. Open **Settings › Security › Sign-in** and select **Local accounts**.
   Under **Second factor**, find **Require a second factor with a password**.
2. Tick it. The **Require a second factor?** confirmation explains that people without a
   factor must set up an app on the sign-in page before a session starts. The administrator-managed
   accounts described above are exempt from that setup.
3. Choose **Require it** to apply the policy. **Cancel** leaves it unchanged.
   Wait for the setting to show as checked. There is no separate Save button.
4. At the next password sign-in, check that someone with a factor is asked for the second
   step. Someone who manages their own sign-in and has neither an app nor a passkey must complete setup and save the recovery
   codes before continuing. A registered passkey also meets the requirement. For a managed
   account with no factor, check that password sign-in continues without setup.
```


New:

```markdown
1. Open **Settings › People and access › Sign-in** and select **Local accounts**.
   Under **Second factor**, find **Require a second factor with a password**.
2. Tick it. The **Require a second factor?** confirmation explains that people without a
   factor must set up an app on the sign-in page before a session starts. The administrator-managed
   accounts described above are exempt from that setup.
3. Choose **Require it** to apply the policy. **Cancel** leaves it unchanged.
   Wait for the setting to show as checked. There is no separate Save button.
4. At the next password sign-in, check that someone with a factor is asked for the second
   step. Someone who manages their own sign-in and has neither an app nor a passkey must complete setup and save the recovery
   codes before continuing. A registered passkey also meets the requirement. For a managed
   account with no factor, check that password sign-in continues without setup.
```


### `guide/src/content/docs/guide/administer/rotate-a-client-secret.md`


Old:

```markdown
1. Open **Settings › Security › Clients** and select the intended client. Check its name
   and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
   and **Last used**, so you can distinguish the current secret from a previous one.
2. Choose **Rotate secret…**. Select how long the current secret should keep working:
   **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
   next tries to authenticate with the old secret until it has the replacement.
4. Choose **Make a new secret**. **Cancel** leaves the secrets unchanged. If creation fails,
   read **No new secret was made**, reload the client and check its current secrets before retrying.
```


New:

```markdown
1. Open **Settings › Connections › Clients** and select the intended client. Check its name
   and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
   and **Last used**, so you can distinguish the current secret from a previous one.
2. Choose **Rotate secret…**. Select how long the current secret should keep working:
   **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
   next tries to authenticate with the old secret until it has the replacement.
4. Choose **Make a new secret**. **Cancel** leaves the secrets unchanged. If creation fails,
   read **No new secret was made**, reload the client and check its current secrets before retrying.
```


### `guide/src/content/docs/guide/administer/rotate-a-webhook-key.md`


Old:

```markdown
1. Open **Settings › Integration › Webhooks**, select the intended webhook and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
2. Choose **Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
4. Choose **Make a new key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).
```


New:

```markdown
1. Open **Settings › Connections › Webhooks**, select the intended webhook and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
2. Choose **Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
4. Choose **Make a new key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).
```


### `guide/src/content/docs/guide/administer/rotate-signing-keys.md`


Old:

```markdown
1. Open **Settings › Security › Signing keys**. Note the key marked **Signing** and its
   **Created** time. A previously replaced key may still show **Verifying until**.
2. Choose **Start a new key** when ready. **This acts immediately, without a dialog.**
   It is not a preview or the start of a confirmation sequence.
3. Check that a new row is **Signing** and the previous key has a replacement time and a
   verification deadline. Existing access continues until it expires. People and clients
   move to the replacement through normal renewal; no secret handover is needed.
```


New:

```markdown
1. Open **Settings › People and access › Signing keys**. Note the key marked **Signing** and its
   **Created** time. A previously replaced key may still show **Verifying until**.
2. Choose **Start a new key** when ready. **This acts immediately, without a dialog.**
   It is not a preview or the start of a confirmation sequence.
3. Check that a new row is **Signing** and the previous key has a replacement time and a
   verification deadline. Existing access continues until it expires. People and clients
   move to the replacement through normal renewal; no secret handover is needed.
```


### `guide/src/content/docs/guide/administer/set-an-approval-policy.md`


No change.


### `guide/src/content/docs/guide/administer/set-up-mail.md`


Old:

```markdown
1. Open **Settings › Integration › Mail**. If nothing is saved, **Mail is not set up** explains that password links must be passed on by an administrator.
2. Under **Mail server**, enter **Server** and **Port**. Choose **Connection**: STARTTLS usually uses 587; TLS usually uses 465. Choose **None: not encrypted (a relay on a trusted network)** only for an approved relay without login.
3. Enter **User name** and **Password** if the server requires a login. Save is unavailable for a login over an unencrypted connection. A saved password is never displayed; enter it again when changing server or port.
4. Enter **From address**, approved by the mail administrator. Enter **Application address** if links should use a different address from the displayed default. Recipients must be able to reach it.
5. Choose **Save**. Wait for **Mail settings saved. Send a test message to try them.** Saving alone does not prove the mail server works. **Cancel** restores the saved values.
```


New:

```markdown
1. Open **Settings › This instance › Mail**. If nothing is saved, **Mail is not set up** explains that password links must be passed on by an administrator.
2. Under **Mail server**, enter **Server** and **Port**. Choose **Connection**: STARTTLS usually uses 587; TLS usually uses 465. Choose **None: not encrypted (a relay on a trusted network)** only for an approved relay without login.
3. Enter **User name** and **Password** if the server requires a login. Save is unavailable for a login over an unencrypted connection. A saved password is never displayed; enter it again when changing server or port.
4. Enter **From address**, approved by the mail administrator. Enter **Application address** if links should use a different address from the displayed default. Recipients must be able to reach it.
5. Choose **Save**. Wait for **Mail settings saved. Send a test message to try them.** Saving alone does not prove the mail server works. **Cancel** restores the saved values.
```


Old:

```markdown
Removing the mail settings stops sending; waiting messages remain until their delivery window ends. Use **Remove settings…**, read the warning and confirm **Remove them** only when that is intended. People choose their own notice mail and digests under **Settings › General › Notification email**; configuring a server does not opt them in.
```


New:

```markdown
Removing the mail settings stops sending; waiting messages remain until their delivery window ends. Use **Remove settings…**, read the warning and confirm **Remove them** only when that is intended. People choose their own notice mail and digests under **Settings › You › Notification email**; configuring a server does not opt them in.
```


### `guide/src/content/docs/guide/administer/turn-off-local-sign-in.md`


Old:

```markdown
1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
2. Open **Settings › Security › People** and select the recovery administrator. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
3. If needed, turn **Keeps local sign-in** on. Read the named confirmation and choose **Keep local sign-in**. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.
```


New:

```markdown
1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
2. Open **Settings › People and access › People** and select the recovery administrator. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
3. If needed, turn **Keeps local sign-in** on. Read the named confirmation and choose **Keep local sign-in**. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.
```


Old:

```markdown
1. Open **Settings › Security › Sign-in** and select **Local accounts**. **Turn off…** appears only after an enabled provider has successfully signed someone in. If absent, complete that proof first.
2. Choose **Turn off…**. Read **Turn local sign-in off?**, including which providers are offered and how many people keep password sign-in.
3. Choose **Turn off**, or **Cancel** to leave it enabled. Wait until Local accounts shows **Off**. If **Not changed** appears or details changed meanwhile, review the saved state before trying again.
4. In a separate browser session, check provider sign-in. Check the recovery account through **Sign in with a local administrator account**. Ordinary local accounts no longer sign in with a password.
```


New:

```markdown
1. Open **Settings › People and access › Sign-in** and select **Local accounts**. **Turn off…** appears only after an enabled provider has successfully signed someone in. If absent, complete that proof first.
2. Choose **Turn off…**. Read **Turn local sign-in off?**, including which providers are offered and how many people keep password sign-in.
3. Choose **Turn off**, or **Cancel** to leave it enabled. Wait until Local accounts shows **Off**. If **Not changed** appears or details changed meanwhile, review the saved state before trying again.
4. In a separate browser session, check provider sign-in. Check the recovery account through **Sign in with a local administrator account**. Ordinary local accounts no longer sign in with a password.
```


### `guide/src/content/docs/guide/integrate/connect-an-assistant.md`


Old:

```markdown
Ask a security administrator for the **Address** under **Settings › Security › Agent access › How to connect**. It ends in `/mcp`. If the page says **Agent access is off**, an operator must enable `MCP_ENABLED` and restart the engine. [Set up AI](/docs/run/set-up-ai/#4-enable-external-agent-access-if-needed) covers that deployment step.
```


New:

```markdown
Ask a security administrator for the **Address** under **Settings › Connections › Agent access › How to connect**. It ends in `/mcp`. If the page says **Agent access is off**, an operator must enable `MCP_ENABLED` and restart the engine. [Set up AI](/docs/run/set-up-ai/#4-enable-external-agent-access-if-needed) covers that deployment step.
```


### `guide/src/content/docs/guide/integrate/exchange-a-supplier-file.md`


No change.


### `guide/src/content/docs/guide/integrate/get-a-token.md`


No change.


### `guide/src/content/docs/guide/integrate/load-then-follow-changes.md`


No change.


### `guide/src/content/docs/guide/integrate/move-records-between-models.md`


No change.


### `guide/src/content/docs/guide/integrate/read-a-collection-completely-and-resume.md`


No change.


### `guide/src/content/docs/guide/integrate/read-as-of-a-date.md`


No change.


### `guide/src/content/docs/guide/integrate/read-through-a-consumer-api.md`


No change.


### `guide/src/content/docs/guide/integrate/resolve-a-file-of-codes.md`


No change.


### `guide/src/content/docs/guide/integrate/submit-a-bulk-change.md`


No change.


### `guide/src/content/docs/guide/integrate/subscribe-a-webhook-and-verify-it.md`


Old:

```markdown
1. Confirm with the operator that webhook subscriptions are enabled. Obtain Integration administration in the intended workspace. Inspect the contract's Events operation and choose the events and filters. For the reference model, inspect [stops Events](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events). Do not assume another model has that event.
2. Prepare an HTTPS receiver that retains raw request bytes, verifies signatures before handling data and acknowledges durably accepted work within 10 seconds. Make event handling repeatable by event ID. Accept both selected formats and batch sizes only as agreed; allow an oversized single object beyond the normal 1 MiB batch boundary.
3. Create the subscription through the [subscription operation](/docs/api/?api=management#tag/consumer%20subscriptions), selecting the workspace, contract, event names, receiver, filters, representation and batching. Supply `contractVersion` to select a served earlier version; omitting it selects the current version. Read [Earlier-contract subscriptions](/docs/integrate/consumer-events-and-webhooks/#keep-a-receiver-on-an-earlier-contract) before choosing. Save the one-time signing secret directly to protected receiver configuration. For browser setup, open **Settings › Integration › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
4. Verify a delivery using its timestamp plus a dot plus the raw body bytes, with HMAC-SHA256 keyed by the secret exactly as issued. Reject stale timestamps and compare each comma-separated signature in constant time. Accept if one supported signature verifies. Return a 2xx after storing the work safely.
5. Inspect the [delivery log](/docs/api/?api=management#tag/consumer%20subscriptions). Check successful acknowledgment and your local deduplication record. A timeout can cause repeat delivery even if your receiver processed the first request. Automatic retries can contain newer object values for the same event.
6. Rotate the signing key with an overlap, install the new secret in the receiver, verify it works and let the old key end. Keep multi-signature support: it is needed during rotation and on retries.
7. If delivery pauses, read its reason before resuming. Correct the receiver or filter and continue from the first unacknowledged event. If events expired, follow the recovery choices below. Reset skips the undelivered range; a publication older than the reset is insufficient on its own.
```


New:

```markdown
1. Confirm with the operator that webhook subscriptions are enabled. Obtain Integration administration in the intended workspace. Inspect the contract's Events operation and choose the events and filters. For the reference model, inspect [stops Events](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events). Do not assume another model has that event.
2. Prepare an HTTPS receiver that retains raw request bytes, verifies signatures before handling data and acknowledges durably accepted work within 10 seconds. Make event handling repeatable by event ID. Accept both selected formats and batch sizes only as agreed; allow an oversized single object beyond the normal 1 MiB batch boundary.
3. Create the subscription through the [subscription operation](/docs/api/?api=management#tag/consumer%20subscriptions), selecting the workspace, contract, event names, receiver, filters, representation and batching. Supply `contractVersion` to select a served earlier version; omitting it selects the current version. Read [Earlier-contract subscriptions](/docs/integrate/consumer-events-and-webhooks/#keep-a-receiver-on-an-earlier-contract) before choosing. Save the one-time signing secret directly to protected receiver configuration. For browser setup, open **Settings › Connections › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
4. Verify a delivery using its timestamp plus a dot plus the raw body bytes, with HMAC-SHA256 keyed by the secret exactly as issued. Reject stale timestamps and compare each comma-separated signature in constant time. Accept if one supported signature verifies. Return a 2xx after storing the work safely.
5. Inspect the [delivery log](/docs/api/?api=management#tag/consumer%20subscriptions). Check successful acknowledgment and your local deduplication record. A timeout can cause repeat delivery even if your receiver processed the first request. Automatic retries can contain newer object values for the same event.
6. Rotate the signing key with an overlap, install the new secret in the receiver, verify it works and let the old key end. Keep multi-signature support: it is needed during rotation and on retries.
7. If delivery pauses, read its reason before resuming. Correct the receiver or filter and continue from the first unacknowledged event. If events expired, follow the recovery choices below. Reset skips the undelivered range; a publication older than the reset is insufficient on its own.
```


### `guide/src/content/docs/guide/model/add-a-record-type-and-fields.md`


No change.


### `guide/src/content/docs/guide/model/add-a-relation-matrix.md`


No change.


### `guide/src/content/docs/guide/model/add-a-relationship.md`


No change.


### `guide/src/content/docs/guide/model/add-a-relationships-table.md`


No change.


### `guide/src/content/docs/guide/model/add-a-view.md`


No change.


### `guide/src/content/docs/guide/model/arrange-applications-and-views.md`


No change.


### `guide/src/content/docs/guide/model/change-a-model-with-the-assistant.md`


No change.


### `guide/src/content/docs/guide/model/change-a-workspaces-model.md`


No change.


### `guide/src/content/docs/guide/model/check-a-workbook-with-a-dry-run.md`


No change.


### `guide/src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`


No change.


### `guide/src/content/docs/guide/model/choose-what-moves.md`


No change.


### `guide/src/content/docs/guide/model/compare-releases.md`


No change.


### `guide/src/content/docs/guide/model/create-a-model-draft.md`


No change.


### `guide/src/content/docs/guide/model/create-a-workspace.md`


No change.


### `guide/src/content/docs/guide/model/define-a-consumer-api.md`


No change.


### `guide/src/content/docs/guide/model/delete-a-draft.md`


No change.


### `guide/src/content/docs/guide/model/delete-a-model-mapping.md`


Old:

```markdown
1. Open **Settings**, **Data operations**, **Copy and move**. Find the mapping under **Mappings**;
   check **From model**, **To model**, **Version** and **Updated**.
2. Choose its **Delete…**. The confirmation asks **Delete the mapping …?** and names both models.
3. Read the warning: copies and moves already made remain; new work needs a new mapping.
   Choose **Cancel** to keep it, or **Delete the mapping** to remove it. There is no Undo here.
4. Wait for the row to disappear. If deletion fails, read the message in the dialog. If another
   editor changed the mapping, refresh and review its new version before deciding again.
```


New:

```markdown
1. Open **Settings**, **Workspaces and models**, **Copy and move**. Find the mapping under **Mappings**;
   check **From model**, **To model**, **Version** and **Updated**.
2. Choose its **Delete…**. The confirmation asks **Delete the mapping …?** and names both models.
3. Read the warning: copies and moves already made remain; new work needs a new mapping.
   Choose **Cancel** to keep it, or **Delete the mapping** to remove it. There is no Undo here.
4. Wait for the row to disappear. If deletion fails, read the message in the dialog. If another
   editor changed the mapping, refresh and review its new version before deciding again.
```


### `guide/src/content/docs/guide/model/edit-a-draft-as-json.md`


No change.


### `guide/src/content/docs/guide/model/edit-a-mapping-row.md`


No change.


### `guide/src/content/docs/guide/model/edit-a-record-page.md`


Old:

```markdown
1. In **Record page**, choose **Header and breadcrumbs…**.
2. Select **Title of the record** from Name or an attached field. **Line under the title**
   adds a second field; choose **None** to remove it.
3. Choose **Show the type’s name in the header** as needed. Set **Breadcrumbs start with the
   application**, **Breadcrumbs name the type** and **Breadcrumbs name the records above it**
   independently. These change this page’s context, not a record’s parent or name.
4. Apply and inspect the preview with a record that has parents. Undo restores the saved step.
```


New:

```markdown
1. In **Record page**, choose **Header and breadcrumbs…**.
2. Select **Title of the record** from Name or an attached field. **Line under the title**
   adds a second field; choose **None** to remove it.
3. Choose **Show the type’s name in the header** as needed. **Breadcrumbs name the type**
   also shows the type in the header; **Breadcrumbs name the records above it** shows parents
   in the line above the title. That line starts with the list link when opened from a list,
   without an application entry. These choices do not change a record’s parent or name.
4. Apply and inspect the preview with a record that has parents. Undo restores the saved step.
```


### `guide/src/content/docs/guide/model/edit-a-workspaces-model.md`


No change.


### `guide/src/content/docs/guide/model/explain-a-model-change.md`


No change.


### `guide/src/content/docs/guide/model/export-a-release.md`


No change.


### `guide/src/content/docs/guide/model/find-your-way-around-the-editor.md`


No change.


### `guide/src/content/docs/guide/model/fix-issues-before-installing.md`


No change.


### `guide/src/content/docs/guide/model/group-collections-in-navigation.md`


No change.


### `guide/src/content/docs/guide/model/install-and-activate-a-release.md`


No change.


### `guide/src/content/docs/guide/model/load-a-workbook-into-a-change-set.md`


No change.


### `guide/src/content/docs/guide/model/make-a-workspace-the-default.md`


No change.


### `guide/src/content/docs/guide/model/map-a-column.md`


No change.


### `guide/src/content/docs/guide/model/migrate-a-workspace.md`


No change.


### `guide/src/content/docs/guide/model/move-records-to-another-model.md`


No change.


### `guide/src/content/docs/guide/model/preview-a-type.md`


No change.


### `guide/src/content/docs/guide/model/propose-again-with-a-newer-workbook.md`


No change.


### `guide/src/content/docs/guide/model/raise-a-contract-version.md`


No change.


### `guide/src/content/docs/guide/model/raise-a-model-language-version.md`


No change.


### `guide/src/content/docs/guide/model/read-lists-in-a-sheet.md`


No change.


### `guide/src/content/docs/guide/model/remove-an-element.md`


No change.


### `guide/src/content/docs/guide/model/rename-or-re-key-an-element.md`


No change.


### `guide/src/content/docs/guide/model/retire-or-delete-a-release.md`


No change.


### `guide/src/content/docs/guide/model/retire-or-delete-a-workspace.md`


No change.


### `guide/src/content/docs/guide/model/reuse-and-change-attributes.md`


No change.


### `guide/src/content/docs/guide/model/review-an-assistants-workbook-design.md`


No change.


### `guide/src/content/docs/guide/model/see-a-consumer-apis-documents.md`


Old:

```markdown
1. After the release is installed and activated, open **Settings › Integration › Consumer APIs**.
   This read-only page names the active release. Use **Open the release** to check it is
   the release you intended; it does not provide the draft's Schema and Message example tabs.
2. Find the API's section and version. Use **Base URL** and **OpenAPI document** to copy
   its addresses or open the document. The **Route** / **What it does** table lists its
   operations; a route description opens that operation in the API reference.
3. Give the integrator the active API's base address and operation document, the workspace
   they should read, and the agreed contract version. Ask the security administrator to
   confirm the client has this API's grant in that workspace. A model release does not
   create grants, and a role alone does not open consumer data.
```


New:

```markdown
1. After the release is installed and activated, open **Settings › Connections › Consumer APIs**.
   This read-only page names the active release. Use **Open the release** to check it is
   the release you intended; it does not provide the draft's Schema and Message example tabs.
2. Find the API's section and version. Use **Base URL** and **OpenAPI document** to copy
   its addresses or open the document. The **Route** / **What it does** table lists its
   operations; a route description opens that operation in the API reference.
3. Give the integrator the active API's base address and operation document, the workspace
   they should read, and the agreed contract version. Ask the security administrator to
   confirm the client has this API's grant in that workspace. A model release does not
   create grants, and a role alone does not open consumer data.
```


### `guide/src/content/docs/guide/model/split-merge-and-move-types.md`


No change.


### `guide/src/content/docs/guide/model/start-a-draft-from-a-workbook.md`


No change.


### `guide/src/content/docs/guide/model/stop-serving-an-earlier-contract-version.md`


No change.


### `guide/src/content/docs/guide/model/turn-an-attribute-into-a-list.md`


No change.


### `guide/src/content/docs/guide/model/undo-and-review-the-draft-history.md`


No change.


### `guide/src/content/docs/guide/model/work-on-a-draft-with-others.md`


No change.


### `guide/src/content/docs/guide/use/add-a-language-with-a-workbook.md`


No change.


### `guide/src/content/docs/guide/use/add-a-record.md`


No change.


### `guide/src/content/docs/guide/use/approve-a-change-set.md`


Old:

```markdown
1. [Prepare the change set](/docs/guide/use/prepare-and-publish-a-change-set/), then check its
   workspace, name and version in the banner. Review the proposed records and relationships.
2. Choose **Submit for publication** where offered. The dialog explains that refiroo validates
   the change set and that it cannot be edited while it waits. Add a comment if the approver
   needs context, then choose **Submit**. **Cancel** leaves it unsubmitted.
3. If validation fails, fix the reported problems and submit again. Success says
   **Submitted for publication. It waits for approval.** The approvers receive a notice.
4. Check that the banner now says **Waiting for approval** and shows the submitted version,
   your name and your comment. To change your proposal while it waits, choose **Withdraw request** first. The proposed work
   stays in the change set and becomes editable. After correction, submit a new request.
```


New:

```markdown
1. [Prepare the change set](/docs/guide/use/prepare-and-publish-a-change-set/), then check its
   workspace in the sidebar and name in the band. Open **Details** for its version.
   Review the proposed records and relationships.
2. Choose **Submit for publication** where offered. The dialog explains that refiroo validates
   the change set and that it cannot be edited while it waits. Add a comment if the approver
   needs context, then choose **Submit**. **Cancel** leaves it unsubmitted.
3. If validation fails, fix the reported problems and submit again. Success says
   **Submitted for publication. It waits for approval.** The approvers receive a notice.
4. Check that the band now says **waits for approval**. Open **Details** for the submitted
   version and your name; read your comment in the review’s **Decision** panel. To change your proposal while it waits, choose **Withdraw request** first. The proposed work
   stays in the change set and becomes editable. After correction, submit a new request.
```


Old:

```markdown
1. Open the returned change set from your notice or the change-set list. The notice says
   **Sent back** and names the request; its detail includes the reason and approver.
2. Read the reason in the change-set banner. The request is no longer waiting and the change
   set is editable again. Inspect and correct the affected records and relationships.
3. Review the whole result, then choose **Submit for publication** again. In **Comment (optional)**,
   explain what you corrected or add the context the approver requested. Choose **Submit**.
   The change set is validated again and waits for a new decision. **Cancel** leaves it editable.
```


New:

```markdown
1. Open the returned change set from your notice or the change-set list. The notice says
   **Sent back** and names the request; its detail includes the reason and approver.
2. Read the reason in the notice below the change-set band. The request is no longer waiting
   and the change set is editable again. From **Changes in this change set**, choose **See the
   data with these changes** to inspect and correct the affected records and relationships.
3. Review the whole result, then choose **Submit for publication** again. In **Comment (optional)**,
   explain what you corrected or add the context the approver requested. Choose **Submit**.
   The change set is validated again and waits for a new decision. **Cancel** leaves it editable.
```


### `guide/src/content/docs/guide/use/arrange-records-in-a-tree.md`


No change.


### `guide/src/content/docs/guide/use/ask-a-list-in-words.md`


No change.


### `guide/src/content/docs/guide/use/browse-a-publication.md`


No change.


### `guide/src/content/docs/guide/use/change-how-refiroo-looks.md`


Old:

```markdown
1. Open **All settings** from your account menu, then **Appearance** under **General**.
   On a phone, open **Settings: …** to reach the settings navigation.
2. Under **Theme**, choose **Normal** or **Website purple** for the colours. Under **Light
   or dark**, choose **System**, **Light** or **Dark**. System follows the device. Both themes
   work in either mode. The page changes immediately; there is no Save button.
3. Under **Table density**, choose **Comfortable** for more space or **Compact** for more
   rows. If one table does not change, open its **Display** menu: its own density overrides
   this default. Choose Default there to use the browser preference again.
4. Under **Type colours**, choose **B: magenta and olive** or **A: plum and gold**. Read the
   record-type labels as well as colours when identifying records.
5. Under **Edit pencil**, choose **On hover and focus** or **Always, faintly**. On a touch
   screen, editable fields show their pencils regardless of this choice.
```


New:

```markdown
1. Open **All settings** from your account menu, then **Appearance** under **You**.
   On a phone, open **Settings: …** to reach the settings navigation.
2. Under **Theme**, choose **Normal** or **Website purple** for the colours. Under **Light
   or dark**, choose **System**, **Light** or **Dark**. System follows the device. Both themes
   work in either mode. The page changes immediately; there is no Save button.
3. Under **Table density**, choose **Comfortable** for more space or **Compact** for more
   rows. If one table does not change, open its **Display** menu: its own density overrides
   this default. Choose Default there to use the browser preference again.
4. Under **Type colours**, choose **B: magenta and olive** or **A: plum and gold**. Read the
   record-type labels as well as colours when identifying records.
5. Under **Edit pencil**, choose **On hover and focus** or **Always, faintly**. On a touch
   screen, editable fields show their pencils regardless of this choice.
```


### `guide/src/content/docs/guide/use/change-records-with-the-assistant.md`


No change.


### `guide/src/content/docs/guide/use/change-relationship-values-in-bulk.md`


No change.


### `guide/src/content/docs/guide/use/change-relationships-of-many-records.md`


No change.


### `guide/src/content/docs/guide/use/change-values-of-many-records.md`


No change.


### `guide/src/content/docs/guide/use/continue-a-long-list.md`


Old:

```markdown
1. Open a collection and check its workspace and context. Search, filter and sort before
   choosing a position: a different condition changes which records occupy that position.
2. Scroll the rows inside the table. The footer shows your range and the full matching total.
   Scroll back up to read earlier rows; where an append-style list offers **Show earlier records**,
   choose it to read the preceding group.
3. To reach a numbered page, enter the number in **Page** and press Enter. Check the range after
   it loads. Use **Go to start** or **Go to end** for either end. With the list focused,
   Ctrl+Home and Ctrl+End reach those ends too.
4. Where **Go to** is offered, enter a value for the current sort and submit it. This seeks the
   value's place in that ordering; it does not add a filter. Check nearby names and identifying
   fields if there is no exact match.
5. Open a record. Use **Back to list** to return with your search, filters, sort and position.
   Save or share the address if you need to return later. Changes to the underlying data can
   change the records at that position.
```


New:

```markdown
1. Open a collection and check its workspace and context. Search, filter and sort before
   choosing a position: a different condition changes which records occupy that position.
2. Scroll the rows inside the table. The footer shows your range and the full matching total.
   Scroll back up to read earlier rows; where an append-style list offers **Show earlier records**,
   choose it to read the preceding group.
3. To reach a numbered page, enter the number in **Page** and press Enter. Check the range after
   it loads. Use **Go to start** or **Go to end** for either end. With the list focused,
   Ctrl+Home and Ctrl+End reach those ends too.
4. Where **Go to** is offered, enter a value for the current sort and submit it. This seeks the
   value's place in that ordering; it does not add a filter. Check nearby names and identifying
   fields if there is no exact match.
5. Open a record. Choose **←** and the list’s name above the title to return with your search, filters, sort and position.
   Save or share the address if you need to return later. Changes to the underlying data can
   change the records at that position.
```


### `guide/src/content/docs/guide/use/continue-an-assistant-task.md`


No change.


### `guide/src/content/docs/guide/use/continue-live-work-while-a-change-set-is-open.md`


No change.


### `guide/src/content/docs/guide/use/copy-or-move-records.md`


Old:

```markdown
1. Open **Settings › Data operations › Copy and move**. Check **Recent copies and moves**
   for an existing operation before choosing **New copy or move…**.
2. Choose **From workspace** and **To workspace**. Check their model names and releases.
   Under **Mapping**, select the agreed saved mapping. If none fits, stop and have its owner
   prepare one; **A new mapping, proposed** is a suggestion requiring design review.
3. Choose **Open the editor**. Select **Copy** to retain the source, or **Move** to prepare
   source deletions as well. Nothing has reached Live in either workspace.
4. Beside **What to copy** or **What to move**, choose **Change…**. Choose the intended scope,
   fill its types, filters or starting record, then choose **Dry run this selection**.
   Wait for the check of all selected items.
5. Inspect creates, updates, omissions, **Values not carried** and **What cannot be copied**
   or **What cannot move**. Open the reasons and affected records. Ask the mapping owner to
   correct unexpected losses, required values or placement problems before proceeding.
6. Choose **Start the copy…** or **Start the move…**. Read the confirmation and enter
   **Name of the change set of workspace …** for the destination. Choose **Start the copy**
   or **Start the move** to load the proposal; **Cancel** keeps the work unstarted.
7. Read the actual result and refused or kept records. Choose **Review the change set** for
   the destination. Review records and relationships, correct problems, validate, and
   [publish or submit for approval](/docs/guide/use/prepare-and-publish-a-change-set/).
8. For Move, publish that destination first. Then choose **Review the deletions** and inspect
   the source proposal. Check which records were kept and why. Publish or obtain approval
   there separately. Publishing the copy has not itself deleted the originals.
```


New:

```markdown
1. Open **Settings › Workspaces and models › Copy and move**. Check **Recent copies and moves**
   for an existing operation before choosing **New copy or move…**.
2. Choose **From workspace** and **To workspace**. Check their model names and releases.
   Under **Mapping**, select the agreed saved mapping. If none fits, stop and have its owner
   prepare one; **A new mapping, proposed** is a suggestion requiring design review.
3. Choose **Open the editor**. Select **Copy** to retain the source, or **Move** to prepare
   source deletions as well. Nothing has reached Live in either workspace.
4. Beside **What to copy** or **What to move**, choose **Change…**. Choose the intended scope,
   fill its types, filters or starting record, then choose **Dry run this selection**.
   Wait for the check of all selected items.
5. Inspect creates, updates, omissions, **Values not carried** and **What cannot be copied**
   or **What cannot move**. Open the reasons and affected records. Ask the mapping owner to
   correct unexpected losses, required values or placement problems before proceeding.
6. Choose **Start the copy…** or **Start the move…**. Read the confirmation and enter
   **Name of the change set of workspace …** for the destination. Choose **Start the copy**
   or **Start the move** to load the proposal; **Cancel** keeps the work unstarted.
7. Read the actual result and refused or kept records. Choose **Review the change set** for
   the destination. Review records and relationships, correct problems, validate, and
   [publish or submit for approval](/docs/guide/use/prepare-and-publish-a-change-set/).
8. For Move, publish that destination first. Then choose **Review the deletions** and inspect
   the source proposal. Check which records were kept and why. Publish or obtain approval
   there separately. Publishing the copy has not itself deleted the originals.
```


### `guide/src/content/docs/guide/use/correct-a-record.md`


Old:

```markdown
1. Open the **…** menu beside the record version in the heading and choose **Edit record**.
   The **Edit object** form opens with the current values.
2. Correct the fields you need. **Name** identifies the record; the other fields describe it.
   Check each field's label rather than assuming similarly named fields change together.
3. Leave **Parent** selected as it is unless you intend to move the record. To move it, search
   for and select the intended parent, checking its path to distinguish matching names.
4. Scroll through the form and choose **Save changes**. On success, the form closes and the
   record page shows the result. If a message identifies an invalid or missing value, correct
   it and save again. Choose **Cancel** to leave without saving the form.
```


New:

```markdown
1. Open the **…** menu in the record’s header and choose **Edit record**.
   The record’s ID and version are under **Details**.
   The **Edit object** form opens with the current values.
2. Correct the fields you need. **Name** identifies the record; the other fields describe it.
   Check each field's label rather than assuming similarly named fields change together.
3. Leave **Parent** selected as it is unless you intend to move the record. To move it, search
   for and select the intended parent, checking its path to distinguish matching names.
4. Scroll through the form and choose **Save changes**. On success, the form closes and the
   record page shows the result. If a message identifies an invalid or missing value, correct
   it and save again. Choose **Cancel** to leave without saving the form.
```


### `guide/src/content/docs/guide/use/delete-a-record.md`


No change.


### `guide/src/content/docs/guide/use/delete-many-records.md`


No change.


### `guide/src/content/docs/guide/use/edit-in-excel-and-import-back.md`


No change.


### `guide/src/content/docs/guide/use/explain-a-period-in-history.md`


No change.


### `guide/src/content/docs/guide/use/export-records.md`


Old:

```markdown
1. Open the intended view in the current workspace and **Live**, change set or publication.
   Set its search, filters, parent scope and chosen columns before opening Export.
2. Open **Workspace actions › Export**. Under **What**, the first choice is **This view**
   followed by its name. Keep it to export the view with its search and supported filters.
   Read the count line and context: a matrix reports rows × columns; a tree or mapping grid
   reports records. Counts are shown when the page knows them. This includes matching rows
   beyond those currently on screen.
3. To take a wider selection, choose **The type**, **The application** or **The whole workspace**.
   These choices select whole types rather than the current view's narrowed rows. Check
   **Record types** and **Where** where offered. You can also start an export from
   **Settings › Data operations › Jobs**.
4. Choose **Kind of file**. **For editing in a spreadsheet** makes an Excel (XLSX) workbook
   shaped for the chosen view or types. **Technical** is offered for a table view, a type,
   an application or the workspace; it offers **Excel (XLSX)**, **CSV** or **JSON Lines**
   under **Format**. A matrix, tree, mapping grid or relationships table exports its view
   as a workbook for editing. In CSV, text that could start a spreadsheet formula receives
   one extra leading single quote, even when single quotes already precede the formula character.
   Keep it if you return the CSV; import reads back the original text. XLSX is unaffected.
   See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
5. Read any notice about filters not carried into the file. A filter on a relationship's own
   values is not carried. The file can therefore include connections that filter hid.
   For a table workbook, **Advanced: columns and sheets** adjusts its columns and related sheets.
6. For a matrix listing linked records, check **What each cell lists**. Under **Each linked
   record is listed by its**, keep **Name** or choose a text field of those records. Choose a
   field whose values distinguish the records in each column. The file records this choice
   so import reads the cells the same way. If linked records have no value in that field,
   the export is refused; fill those values or choose another field.
   Each column also gets a value sheet with its records and fields. New records use the
   relationship's rules and existing groups when imported; there is no group choice in Export.
7. Where offered, choose **Relationships**: **Between exported records**, **All their
   relationships**, or **None**. Use **Valid on** only when you need a business-date extract.
   Check the selection and context, then choose **Start export**.
8. Open **View job** from the notification to follow progress. When completed, choose
   **Download** before retention ends. Failed or cancelled exports have no file; correct
   the stated reason and start another export.
9. In an XLSX file, read the second sheet, **About this export**. It explains the source,
   counts, relationships, what loads back and, for a creating matrix, where new records go.
   Check it before editing: a matrix workbook loads its cells, not changes to its row labels.
```


New:

```markdown
1. Open the intended view in the current workspace and **Live**, change set or publication.
   Set its search, filters, parent scope and chosen columns before opening Export.
2. Open **Workspace actions › Export**. Under **What**, the first choice is **This view**
   followed by its name. Keep it to export the view with its search and supported filters.
   Read the count line and context: a matrix reports rows × columns; a tree or mapping grid
   reports records. Counts are shown when the page knows them. This includes matching rows
   beyond those currently on screen.
3. To take a wider selection, choose **The type**, **The application** or **The whole workspace**.
   These choices select whole types rather than the current view's narrowed rows. Check
   **Record types** and **Where** where offered. You can also start an export from
   **Settings › This instance › Jobs**.
4. Choose **Kind of file**. **For editing in a spreadsheet** makes an Excel (XLSX) workbook
   shaped for the chosen view or types. **Technical** is offered for a table view, a type,
   an application or the workspace; it offers **Excel (XLSX)**, **CSV** or **JSON Lines**
   under **Format**. A matrix, tree, mapping grid or relationships table exports its view
   as a workbook for editing. In CSV, text that could start a spreadsheet formula receives
   one extra leading single quote, even when single quotes already precede the formula character.
   Keep it if you return the CSV; import reads back the original text. XLSX is unaffected.
   See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
5. Read any notice about filters not carried into the file. A filter on a relationship's own
   values is not carried. The file can therefore include connections that filter hid.
   For a table workbook, **Advanced: columns and sheets** adjusts its columns and related sheets.
6. For a matrix listing linked records, check **What each cell lists**. Under **Each linked
   record is listed by its**, keep **Name** or choose a text field of those records. Choose a
   field whose values distinguish the records in each column. The file records this choice
   so import reads the cells the same way. If linked records have no value in that field,
   the export is refused; fill those values or choose another field.
   Each column also gets a value sheet with its records and fields. New records use the
   relationship's rules and existing groups when imported; there is no group choice in Export.
7. Where offered, choose **Relationships**: **Between exported records**, **All their
   relationships**, or **None**. Use **Valid on** only when you need a business-date extract.
   Check the selection and context, then choose **Start export**.
8. Open **View job** from the notification to follow progress. When completed, choose
   **Download** before retention ends. Failed or cancelled exports have no file; correct
   the stated reason and start another export.
9. In an XLSX file, read the second sheet, **About this export**. It explains the source,
   counts, relationships, what loads back and, for a creating matrix, where new records go.
   Check it before editing: a matrix workbook loads its cells, not changes to its row labels.
```


### `guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md`


No change.


### `guide/src/content/docs/guide/use/find-records.md`


Old:

```markdown
1. On Home, find the workspace you need under **Your workspaces**. Choose an application on
   its card. The application opens with that workspace selected.
2. Check **Workspace** in the sidebar. If it names a different workspace, select the intended
   one before searching: a record with the same name elsewhere may hold different data.
3. Choose the collection you need under **Collections**. In an application with more than
   ten sidebar entries, type part of its name in **Find a list** to narrow the entries across
   all groups. Choose a result, or press **Enter** to open the first match. **Esc** clears
   the box and restores the groups' previous folds. If **No list matches** appears, shorten
   or clear the text. This finds list names, not records; see
   [Applications](/docs/use/applications/#find-a-list-in-the-sidebar) for the sidebar's counts
   and groups. The collection's heading identifies the list. Available collections and their
   labels depend on your workspace's model.
4. Choose **Live** at the top to search current data. Check the green **Live** banner. To
   inspect proposed or previously published data, open that change set or publication instead;
   check the context before interpreting the results.
```


New:

```markdown
1. On Home, find the workspace you need under **Your workspaces**. Choose its name or tile
   to open its page, then choose an application. An application link on its card opens it directly.
2. Check **Workspace** in the sidebar. If it names a different workspace, select the intended
   one before searching: a record with the same name elsewhere may hold different data.
3. Choose the collection you need under **Collections**. In an application with more than
   ten sidebar entries, type part of its name in **Find a list** to narrow the entries across
   all groups. Choose a result, or press **Enter** to open the first match. **Esc** clears
   the box and restores the groups' previous folds. If **No list matches** appears, shorten
   or clear the text. This finds list names, not records; see
   [Applications](/docs/use/applications/#find-a-list-in-the-sidebar) for the sidebar's counts
   and groups. The collection's heading identifies the list. Available collections and their
   labels depend on your workspace's model.
4. Choose **Live** at the top to search current data. Check the green **Live** banner. To
   inspect proposed or previously published data, open that change set or publication instead;
   check the context before interpreting the results.
```


Old:

```markdown
1. Type all or part of the record's name in the search box above the list. Wait for the results
   to update. Use a shorter part of the name if you are unsure of its spelling.
2. Check the result names and identifying fields before opening one. Several records may have
   similar names; a number, date or related record can distinguish them.
3. If the record is missing, check the workspace, application and context first. Clear filters
   that may exclude it. Clear the search text to see the list without that search. If the list
   reports a loading failure, use its retry control rather than treating it as an empty result.
```


New:

```markdown
1. To search names across the workspace, use **Find any record** in the top bar or **Find a
   record** on the workspace’s page. Check the list and path beside a result; use the arrow
   keys and Enter to open one in **Live**. To stay in a change set or publication, or search
   just this collection, type all or part of the record’s name in the search box above the list. Wait for the results
   to update. Use a shorter part of the name if you are unsure of its spelling.
2. Check the result names and identifying fields before opening one. Several records may have
   similar names; a number, date or related record can distinguish them.
3. If the record is missing, check the workspace, application and context first. Clear filters
   that may exclude it. Clear the search text to see the list without that search. If the list
   reports a loading failure, use its retry control rather than treating it as an empty result.
```


Old:

```markdown
1. Choose the result's name. Its page opens with a heading and identifying fields. Check the
   path above the heading to confirm its place in the hierarchy, especially if names repeat.
2. Read the fields in the heading and details panels. The labels depend on the record type.
   An unset value differs from zero or No; see [Records](/docs/use/records/#what-a-record-holds)
   if you need to interpret a field.
3. Read the relationship sections for connected records. Scroll down to find further sections.
   **No relationships yet** means that section has no connections. If a panel reports an error,
   retry that panel; the error does not mean there are no related records.
4. Choose **Back to list** when finished. Your search, filters, sort and position are preserved,
   so you can inspect the next result. To make a correction, follow
   [Correct a record](/docs/guide/use/correct-a-record/).
```


New:

```markdown
1. Choose the result's name. Its page opens with a heading and identifying fields. Check the
   path above the heading to confirm its place in the hierarchy, especially if names repeat.
2. Read the fields in the heading and details panels. The labels depend on the record type.
   An unset value differs from zero or No; see [Records](/docs/use/records/#what-a-record-holds)
   if you need to interpret a field.
3. Read the relationship sections for connected records. Scroll down to find further sections.
   **No relationships yet** means that section has no connections. If a panel reports an error,
   retry that panel; the error does not mean there are no related records.
4. Choose **←** and the list’s name above the title when finished. Your search, filters, sort and position are preserved,
   so you can inspect the next result. To make a correction, follow
   [Correct a record](/docs/guide/use/correct-a-record/).
```


Old:

```markdown
1. Scroll inside the list to read more records. The header and footer stay in view, including
   the range and total. Use the footer's page field to jump to a page, **Go to** to seek a
   sorted value where offered, or **Go to start** and **Go to end** for the ends of the list.
2. In a related-record column, read the chips. **+N more** counts records that do not fit on
   the line; widen the column to see more, or open the row's record to inspect the full
   relationship table. The count itself is not an expand button.
3. A column that holds only one related record can sort by that record's name, with missing
   connections last. Columns holding several related records or showing their fields do not
   sort. Use a relationship filter rather than trying to filter a chip column.
4. Use **Display** to change shown columns. A one-line value ending in an ellipsis can be read
   in full on hover, focus or long press. Return with **Back to list** after inspecting a record;
   the address preserves search, filters, the single sort and your position.
```


New:

```markdown
1. Scroll inside the list to read more records. The header and footer stay in view, including
   the range and total. Use the footer's page field to jump to a page, **Go to** to seek a
   sorted value where offered, or **Go to start** and **Go to end** for the ends of the list.
2. In a related-record column, read the chips. **+N more** counts records that do not fit on
   the line; widen the column to see more, or open the row's record to inspect the full
   relationship table. The count itself is not an expand button.
3. A column that holds only one related record can sort by that record's name, with missing
   connections last. Columns holding several related records or showing their fields do not
   sort. Use a relationship filter rather than trying to filter a chip column.
4. Use **Display** to change shown columns. A one-line value ending in an ellipsis can be read
   in full on hover, focus or long press. If columns have folded, choose **Columns · n of m**
   to show them all. Return using **←** and the list’s name above the title after inspecting a record;
   the address preserves search, filters, the single sort and your position.
```


### `guide/src/content/docs/guide/use/follow-a-workspace.md`


No change.


### `guide/src/content/docs/guide/use/follow-and-cancel-a-job.md`


Old:

```markdown
1. Open **View job** in the starting notification, or go to **Settings › Data operations › Jobs**
   and open the job; a group of related jobs opens first, and its jobs under it. Check **Workspace**
   and **Requested by** before acting.
2. Read **State** and progress. A preview waiting for confirmation has not written its proposed
   changes. Review the items before choosing **Load the file** for an import or **Apply** for
   a bulk preview. A running job updates while the page stays open.
3. To stop remaining work, use **Cancel job**, **Cancel import** for a waiting import,
   or **Cancel preview** for a waiting batch preview.
   Read the confirmation, then choose **Stop the job** for running work or **Discard the
   import** / **Discard the preview** for a waiting preview. From the Jobs list, choose **Cancel
   job** in its confirmation. **Keep the job**, **Keep the preview** or **Keep the import**
   dismisses that confirmation.
4. Wait for the state to settle. **Cancel requested** is still pending. Already committed
   chunks remain applied: inspect the final counts rather than assuming cancellation undoes them.
5. For an export that completed, read **The file** and choose **Download**. For an import or
   batch, read refused and unprocessed items and their reasons. Fix the source and preview
   again before retrying work.
```


New:

```markdown
1. Open **View job** in the starting notification, or go to **Settings › This instance › Jobs**
   and open the job; a group of related jobs opens first, and its jobs under it. Check **Workspace**
   and **Requested by** before acting.
2. Read **State** and progress. A preview waiting for confirmation has not written its proposed
   changes. Review the items before choosing **Load the file** for an import or **Apply** for
   a bulk preview. A running job updates while the page stays open.
3. To stop remaining work, use **Cancel job**, **Cancel import** for a waiting import,
   or **Cancel preview** for a waiting batch preview.
   Read the confirmation, then choose **Stop the job** for running work or **Discard the
   import** / **Discard the preview** for a waiting preview. From the Jobs list, choose **Cancel
   job** in its confirmation. **Keep the job**, **Keep the preview** or **Keep the import**
   dismisses that confirmation.
4. Wait for the state to settle. **Cancel requested** is still pending. Already committed
   chunks remain applied: inspect the final counts rather than assuming cancellation undoes them.
5. For an export that completed, read **The file** and choose **Download**. For an import or
   batch, read refused and unprocessed items and their reasons. Fix the source and preview
   again before retrying work.
```


### `guide/src/content/docs/guide/use/import-a-file.md`


Old:

```markdown
1. Open the intended workspace and collection. Choose **Workspace actions › Import**. To
   choose another destination, open **Settings › Data operations › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**. The chooser accepts Excel workbooks, CSV and supported technical export
   files. Choose the stored **Profile** for an ordinary workbook or CSV, or **None** for a
   file exported by refiroo. Read any profile problems before continuing. For an exported CSV,
   keep the protective single quotes added to formula-like text. With **None**, import removes
   exactly one such quote from names and text fields; an unchanged export changes nothing.
   XLSX is unaffected. See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
3. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report, **How the file is read** where shown, and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.
```


New:

```markdown
1. Open the intended workspace and collection. Choose **Workspace actions › Import**. To
   choose another destination, open **Settings › This instance › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**. The chooser accepts Excel workbooks, CSV and supported technical export
   files. Choose the stored **Profile** for an ordinary workbook or CSV, or **None** for a
   file exported by refiroo. Read any profile problems before continuing. For an exported CSV,
   keep the protective single quotes added to formula-like text. With **None**, import removes
   exactly one such quote from names and text fields; an unchanged export changes nothing.
   XLSX is unaffected. See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
3. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report, **How the file is read** where shown, and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.
```


### `guide/src/content/docs/guide/use/load-a-workbook-with-the-assistant.md`


No change.


### `guide/src/content/docs/guide/use/load-the-next-version-of-a-workbook.md`


Old:

```markdown
1. Open **Settings › Data operations › Import profiles**. Select the profile and read its
   **Last load**: file, destination, row counts and whether its change set was published.
2. If your permissions offer **Upload the next version…**, choose it and upload the newer
   workbook. Choose the intended comparison workspace and wait while it is checked.
   The profile is checked and saved against that workspace’s model. Nothing is loaded
   into its records by this check.
3. Review new, missing and renamed columns, new values, changed names and missing records.
   Choose **Accept** on a **Renamed** row only where the proposed column really replaces the old one.
   Choose **Ignore** on a **New** row to leave that column out. Ask the profile's model administrator to
   fix ambiguous bindings or model problems; do not guess which field a column represents.
4. Check the missing-record choice. Keeping missing records leaves them; deleting them stages
   removals and is allowed only in a change set. A missing key means reliable recurring
   matching is not available: resolve it before relying on repeated uploads.
5. When the report allows loading, choose **Load into a change set…** and review the destination
   and proposed changes in its dialog. Loading creates a new change set containing differences.
6. Choose **Open the change set review** from the completed load or **Last load**. Review
   additions, corrections and removals before publishing or submitting for approval.
```


New:

```markdown
1. Open **Settings › Workspaces and models › Import profiles**. Select the profile and read its
   **Last load**: file, destination, row counts and whether its change set was published.
2. If your permissions offer **Upload the next version…**, choose it and upload the newer
   workbook. Choose the intended comparison workspace and wait while it is checked.
   The profile is checked and saved against that workspace’s model. Nothing is loaded
   into its records by this check.
3. Review new, missing and renamed columns, new values, changed names and missing records.
   Choose **Accept** on a **Renamed** row only where the proposed column really replaces the old one.
   Choose **Ignore** on a **New** row to leave that column out. Ask the profile's model administrator to
   fix ambiguous bindings or model problems; do not guess which field a column represents.
4. Check the missing-record choice. Keeping missing records leaves them; deleting them stages
   removals and is allowed only in a change set. A missing key means reliable recurring
   matching is not available: resolve it before relying on repeated uploads.
5. When the report allows loading, choose **Load into a change set…** and review the destination
   and proposed changes in its dialog. Loading creates a new change set containing differences.
6. Choose **Open the change set review** from the completed load or **Last load**. Review
   additions, corrections and removals before publishing or submitting for approval.
```


### `guide/src/content/docs/guide/use/map-codes-between-systems.md`


No change.


### `guide/src/content/docs/guide/use/move-several-records-together.md`


No change.


### `guide/src/content/docs/guide/use/open-a-retired-or-unavailable-workspace.md`


No change.


### `guide/src/content/docs/guide/use/open-an-application.md`


Old:

```markdown
1. Select the refiroo name in the top bar to open Home. Under **Your workspaces**, find the
   intended workspace. Check the model name and release on its card; similar workspace names
   do not guarantee the same data or structure.
2. Choose an application button on that card. Its default view opens in that workspace.
   The application names come from the model.
3. Check **Workspace** in the sidebar and the context banner above the records. Choose **Live**
   for current data, or open the intended change set or publication. A publication is read-only;
   Live saves apply immediately.
```


New:

```markdown
1. Select the refiroo name in the top bar to open Home. Under **Your workspaces**, find the
   intended workspace. Check the model name and release on its card; similar workspace names
   do not guarantee the same data or structure.
2. Choose the workspace’s name or tile to open its page, then choose an application. Its
   default view opens in that workspace. The application names come from the model. An
   application link on the Home card opens that application directly.
3. Check **Workspace** in the sidebar and the context banner above the records. Choose **Live**
   for current data, or open the intended change set or publication. A publication is read-only;
   Live saves apply immediately.
```


Old:

```markdown
1. Select an application in the top bar. Read its sidebar collections; switching applications
   can change which collections are offered. If a collection group is folded, expand it.
2. Choose the collection you need. Check the page heading and description.
3. If tabs appear below the heading, choose the view that suits your task. A table helps
   [find records](/docs/guide/use/find-records/); a tree helps
   [arrange records](/docs/guide/use/arrange-records-in-a-tree/); a mapping grid helps
   [map records](/docs/guide/use/map-codes-between-systems/); a relation matrix helps
   [check coverage](/docs/guide/use/fill-in-a-relation-matrix/).
4. Check the banner again before changing anything. Opening an application or changing a view
   does not itself save a data change.
```


New:

```markdown
1. Select an application in the top bar, using **More** if it does not fit. On a phone,
   choose it in the band beneath the top bar. Read its sidebar collections; switching applications
   can change which collections are offered. If a collection group is folded, expand it.
2. Choose the collection you need. Check the page heading and description.
3. If tabs appear below the heading, choose the view that suits your task. A table helps
   [find records](/docs/guide/use/find-records/); a tree helps
   [arrange records](/docs/guide/use/arrange-records-in-a-tree/); a mapping grid helps
   [map records](/docs/guide/use/map-codes-between-systems/); a relation matrix helps
   [check coverage](/docs/guide/use/fill-in-a-relation-matrix/).
4. Check the banner again before changing anything. Opening an application or changing a view
   does not itself save a data change.
```


### `guide/src/content/docs/guide/use/prepare-and-publish-a-change-set.md`


Old:

```markdown
1. Open an application in the current workspace. Check **Workspace** in the sidebar, then
   choose **Change sets** at the top. The list identifies existing change sets by name and
   shows their versions, starting data and creators.
2. To continue existing work, find its name and choose **Open change set**. Check the name in
   the banner before editing. Opening a change set does not publish it.
3. To start separate work, choose **Start from current live data**. Enter a **Change set name**
   that helps other people recognise the work. If **Model version** appears, keep the active
   version for ordinary data corrections; coordinate a different choice with a model administrator.
4. Choose **Create change set**. The new set opens with a copy of the current live data.
   If creation is refused, read the message and resolve the named problem before retrying.
   Choose **Cancel** if you do not intend to create it.
```


New:

```markdown
1. Open an application in the current workspace. Check **Workspace** in the sidebar, then
   choose **Change sets** at the top. The list identifies existing change sets by name and
   shows their versions, starting data and creators.
2. To continue existing work, find its name and choose **Open change set**. **Changes in this
   change set** opens first. Choose **See the data with these changes** to reach its lists,
   and check the name in the band before editing. Opening a change set does not publish it.
3. To start separate work, choose **Start from current live data**. Enter a **Change set name**
   that helps other people recognise the work. If **Model version** appears, keep the active
   version for ordinary data corrections; coordinate a different choice with a model administrator.
4. Choose **Create change set**. The new set opens with a copy of the current live data.
   If creation is refused, read the message and resolve the named problem before retrying.
   Choose **Cancel** if you do not intend to create it.
```


Old:

```markdown
1. Check the orange **Change set** banner. It must name the intended set and say **Edits stay in
   this change set until it is published**. If the banner says **Live**, open your change set
   before making staged corrections.
2. Choose a collection and find a record. [Correct its fields](/docs/guide/use/correct-a-record/)
   and save using the ordinary record controls. Check that the saved values appear in the
   change set, then repeat for the other records in your proposal.
3. If you switch applications or inspect **Live**, check the banner again before the next edit.
   Return to the named change set to continue preparing it. Later live corrections do not
   refresh its starting copy.
4. If a save is refused, read the message and review the current record or change-set version
   before retrying. If the set is **Waiting for approval**, follow the banner's instruction to
   withdraw the request before editing.
```


New:

```markdown
1. Check the orange **Change set** band. It names the intended set, its number of changes
   and state. Open **Details** for its creator, creation time, version and model. If the band
   says **Live**, open your change set
   before making staged corrections.
2. Choose a collection and find a record. [Correct its fields](/docs/guide/use/correct-a-record/)
   and save using the ordinary record controls. Check that the saved values appear in the
   change set, then repeat for the other records in your proposal.
3. If you switch applications or inspect **Live**, check the banner again before the next edit.
   Return to the named change set to continue preparing it. Later live corrections do not
   refresh its starting copy.
4. If a save is refused, read the message and review the current record or change-set version
   before retrying. If the band says **waits for approval**, open **Details** for the submission
   and withdraw the request before editing.
```


Old:

```markdown
1. Choose **Review changes** in the banner. On **Records**, inspect every intended addition,
   change or removal. Expand a row with its arrow to compare the before and after values.
   Check names and paths to confirm that you changed the intended records.
2. Choose **Relationships** and review the connection changes too. If a long review is hard to
   inspect, use **Filter** to narrow it, then remove the restriction to check the remaining work.
   An empty filtered review does not mean the whole proposal is empty.
3. Choose **Back to change set** to correct anything unexpected. Save those corrections and
   review again before proceeding.
4. Choose **Validate change set**. If problems are reported, use the named records and reasons
   to correct them in the change set, then validate again. Do not proceed while problems remain.
5. Check for **Change set validation passed**. In the direct publication flow, this enables
   **Publish change set**. Validate again after any further edits.
```


New:

```markdown
1. Choose **Review changes** in the banner. On **Records**, inspect every intended addition,
   change or removal. Expand a row with its arrow to compare the before and after values.
   Check names and paths to confirm that you changed the intended records.
2. Choose **Relationships** and review the connection changes too. If a long review is hard to
   inspect, use **Filter** to narrow it, then remove the restriction to check the remaining work.
   An empty filtered review does not mean the whole proposal is empty.
3. Choose **See the data with these changes** to correct anything unexpected. Save those corrections and
   review again before proceeding.
4. Choose **Validate change set**. If problems are reported, use the named records and reasons
   to correct them in the change set, then validate again. Do not proceed while problems remain.
5. Check for **Change set validation passed**. In the direct publication flow, this enables
   **Publish change set**. Validate again after any further edits.
```


### `guide/src/content/docs/guide/use/prepare-under-the-next-model-version.md`


No change.


### `guide/src/content/docs/guide/use/propose-a-change.md`


No change.


### `guide/src/content/docs/guide/use/propose-targets.md`


No change.


### `guide/src/content/docs/guide/use/relate-records.md`


No change.


### `guide/src/content/docs/guide/use/replace-a-records-related-records.md`


No change.


### `guide/src/content/docs/guide/use/reshape-a-hierarchy.md`


No change.


### `guide/src/content/docs/guide/use/review-what-a-change-set-changes.md`


Old:

```markdown
1. Open the change set and choose **Review changes** in its amber strip. Confirm the name
   and source. If it started from a publication, the earlier values come from that publication,
   not today's Live.
2. Under **Records**, filter by change kind or record type. Open a row to read before/after
   values and paths. A moved record names both parents. A type-change filter can match either
   its old or new type, so check the difference itself.
3. Open **Relationships** and inspect additions, changes and removals separately. A record
   review alone does not account for every changed connection.
4. Scroll or jump through the lists. The address retains the tab, filters and position so
   you can return to the same part of the review.
5. Return to editing for corrections, then choose **Validate change set**. Resolve its named
   problems and validate the new version again before publishing or submitting.
```


New:

```markdown
1. From **Change sets**, choose **Open change set** to open **Changes in this change set**.
   If you are already browsing its data, choose **Review changes** in the amber band. Confirm
   its name; open **Details** for its source. If it started from a publication, the earlier values come from that publication,
   not today's Live.
2. Under **Records**, filter by change kind or record type. Open a row to read before/after
   values and paths. A moved record names both parents. A type-change filter can match either
   its old or new type, so check the difference itself.
3. Open **Relationships** and inspect additions, changes and removals separately. A record
   review alone does not account for every changed connection.
4. Scroll or jump through the lists. The address retains the tab, filters and position so
   you can return to the same part of the review.
5. Choose **See the data with these changes** to return to editing for corrections, then
   choose **Validate change set**. Resolve its named
   problems and validate the new version again before publishing or submitting.
```


### `guide/src/content/docs/guide/use/see-who-changed-what.md`


No change.


### `guide/src/content/docs/guide/use/set-up-email-notices.md`


No change.


### `guide/src/content/docs/guide/use/start-from-an-earlier-publication.md`


No change.


### `guide/src/content/docs/guide/use/stop-offering-a-value.md`


No change.


### `guide/src/content/docs/guide/use/switch-workspace.md`


Old:

```markdown
1. Select the refiroo name in the top bar.
2. Under **Your workspaces**, check the destination card's model and release.
3. Choose an application button on that card. Check the sidebar and banner in the page that opens.
   Continue with [Open an application](/docs/guide/use/open-an-application/).
```


New:

```markdown
1. Select the refiroo name in the top bar.
2. Under **Your workspaces**, check the destination card's model and release.
3. Choose the workspace’s name or tile to open its page, then choose an application.
   Check the sidebar and banner in the application that opens.
   Continue with [Open an application](/docs/guide/use/open-an-application/).
```


### `guide/src/content/docs/guide/use/withdraw-a-publication.md`


No change.


### `guide/src/content/docs/integrate/api-reference.md`


Old:

```markdown
In the browser, **Settings › Integration › API reference** lists the sources, versions and OpenAPI document links. Select a source name to open its reference. You can also open the [management source](/docs/api/?api=management), or discover consumer sources through the [API index](/docs/api/?api=management). See [Discovering the model](/docs/integrate/discovering-the-model/) for selecting a contract programmatically.
```


New:

```markdown
In the browser, **Settings › Connections › API reference** lists the sources, versions and OpenAPI document links. Select a source name to open its reference. You can also open the [management source](/docs/api/?api=management), or discover consumer sources through the [API index](/docs/api/?api=management). See [Discovering the model](/docs/integrate/discovering-the-model/) for selecting a contract programmatically.
```


### `guide/src/content/docs/integrate/assistant-tasks.md`


No change.


### `guide/src/content/docs/integrate/assistants-and-agents.md`


Old:

```markdown
Security administrators inspect **Settings › Security › Agent access** and the [agent-access operations](/docs/api/?api=management#tag/agent-access). They show **How to connect**, **Agent clients**, registered assistants and **Calls**. Call records keep identity, tool, argument names, outcome, duration and request reference for `MCP_CALLS_DAYS`, default 90; they do not keep argument values. Read calls are not separate entries in the data audit trail. Data writes use the ordinary audit trail with their channel.
```


New:

```markdown
Security administrators inspect **Settings › Connections › Agent access** and the [agent-access operations](/docs/api/?api=management#tag/agent-access). They show **How to connect**, **Agent clients**, registered assistants and **Calls**. Call records keep identity, tool, argument names, outcome, duration and request reference for `MCP_CALLS_DAYS`, default 90; they do not keep argument values. Read calls are not separate entries in the data audit trail. Data writes use the ordinary audit trail with their channel.
```


### `guide/src/content/docs/integrate/business-dates.md`


No change.


### `guide/src/content/docs/integrate/changes-approvals-and-publication.md`


No change.


### `guide/src/content/docs/integrate/compatibility.md`


No change.


### `guide/src/content/docs/integrate/consumer-apis.md`


Old:

```markdown
In the browser, **Settings › Integration › Consumer APIs** lists the declared APIs, and **API reference** opens their interactive documents. Both describe the selected workspace's model; they do not make a contract available in another workspace. The [reference stops source](/docs/api/?api=consumer-stops-v1) is a pointer to this example's instance contract.
```


New:

```markdown
In the browser, **Settings › Connections › Consumer APIs** lists the declared APIs, and **API reference** opens their interactive documents. Both describe the selected workspace's model; they do not make a contract available in another workspace. The [reference stops source](/docs/api/?api=consumer-stops-v1) is a pointer to this example's instance contract.
```


### `guide/src/content/docs/integrate/consumer-events-and-webhooks.md`


Old:

```markdown
The [consumer subscription operations](/docs/api/?api=management#tag/consumer%20subscriptions) require Integration administration in the workspace and the deployment's webhook capability. It is off by default. Subscriptions are runtime configuration, not model content. In the browser, administrators manage subscriptions under **Settings › Integration › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
```


New:

```markdown
The [consumer subscription operations](/docs/api/?api=management#tag/consumer%20subscriptions) require Integration administration in the workspace and the deployment's webhook capability. It is off by default. Subscriptions are runtime configuration, not model content. In the browser, administrators manage subscriptions under **Settings › Connections › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
```


### `guide/src/content/docs/integrate/discovering-the-model.md`


Old:

```markdown
**Settings › Integration › Consumer APIs** is a read-only catalogue for people with Browse. It shows the contract's name, version, base address, OpenAPI document, exposed types, lists and events. **Open the release** and **Open model** lead to the declaring model; they do not grant permission to edit it. Its **Change feed** section describes retention. Use the [consumer reading pages](/docs/integrate/consumer-apis/) for explanations and complete example exchanges, the [model administrator's page](/docs/model/consumer-apis/) for designing the declaration, and [The API reference](/docs/integrate/api-reference/) for trying operations.
```


New:

```markdown
**Settings › Connections › Consumer APIs** is a read-only catalogue for people with Browse. It shows the contract's name, version, base address, OpenAPI document, exposed types, lists and events. **Open the release** and **Open model** lead to the declaring model; they do not grant permission to edit it. Its **Change feed** section describes retention. Use the [consumer reading pages](/docs/integrate/consumer-apis/) for explanations and complete example exchanges, the [model administrator's page](/docs/model/consumer-apis/) for designing the declaration, and [The API reference](/docs/integrate/api-reference/) for trying operations.
```


### `guide/src/content/docs/integrate/files-imports-and-exports.md`


No change.


### `guide/src/content/docs/integrate/following-changes.md`


No change.


### `guide/src/content/docs/integrate/identifiers-paging-and-errors.md`


No change.


### `guide/src/content/docs/integrate/jobs.md`


Old:

```markdown
Operators can inspect these same jobs in Settings › Data operations › Jobs, including state, result, counts, cancellation and current limits. For browser tasks, follow [Importing and exporting data](/docs/use/importing-and-exporting/).
```


New:

```markdown
Operators can inspect these same jobs in Settings › This instance › Jobs, including state, result, counts, cancellation and current limits. For browser tasks, follow [Importing and exporting data](/docs/use/importing-and-exporting/).
```


### `guide/src/content/docs/integrate/looking-up-and-resolving.md`


No change.


### `guide/src/content/docs/integrate/model-and-release-operations.md`


No change.


### `guide/src/content/docs/integrate/overview.md`


No change.


### `guide/src/content/docs/integrate/reading-business-objects.md`


No change.


### `guide/src/content/docs/integrate/reading-records.md`


No change.


### `guide/src/content/docs/integrate/relationships-and-their-values.md`


No change.


### `guide/src/content/docs/integrate/security-model-for-integrators.md`


No change.


### `guide/src/content/docs/integrate/signing-in-and-tokens.md`


No change.


### `guide/src/content/docs/integrate/versions-and-conflicts.md`


No change.


### `guide/src/content/docs/integrate/workspaces-contexts-and-models.md`


No change.


### `guide/src/content/docs/integrate/writing-in-bulk.md`


No change.


### `guide/src/content/docs/journeys/work-with-an-assistant.md`


Old:

```markdown
With **Operations**, open **Settings › Administration › AI** to inspect which help is on and
what may be sent. [Check the AI provider](/docs/guide/administer/check-the-ai-provider/) leads
through **Send a test request**, which contains no reference data, then the call records and
30-day totals. A refused key, unreachable service or unreadable answer is recorded as a failure.
An absent provider does not disable an independently enabled built-in assistant. Neither enabled
means no built-in AI action and nothing sent by those features.
```


New:

```markdown
With **Operations**, open **Settings › This instance › AI** to inspect which help is on and
what may be sent. [Check the AI provider](/docs/guide/administer/check-the-ai-provider/) leads
through **Send a test request**, which contains no reference data, then the call records and
30-day totals. A refused key, unreachable service or unreadable answer is recorded as a failure.
An absent provider does not disable an independently enabled built-in assistant. Neither enabled
means no built-in AI action and nothing sent by those features.
```


Old:

```markdown
An integrator connects an MCP-capable assistant once the operator enables agent access. Follow
[Connect an assistant](/docs/guide/integrate/connect-an-assistant/). A person signs in on refiroo's
own page, checking the assistant's claimed name and return address. An unattended system uses
an agent client created under **Settings › Security › Agent access**.
```


New:

```markdown
An integrator connects an MCP-capable assistant once the operator enables agent access. Follow
[Connect an assistant](/docs/guide/integrate/connect-an-assistant/). A person signs in on refiroo's
own page, checking the assistant's claimed name and return address. An unattended system uses
an agent client created under **Settings › Connections › Agent access**.
```


### `guide/src/content/docs/model/ai-model-changes.md`


No change.


### `guide/src/content/docs/model/applications-and-views.md`


No change.


### `guide/src/content/docs/model/consumer-apis.md`


No change.


### `guide/src/content/docs/model/issues-and-dry-run.md`


No change.


### `guide/src/content/docs/model/json-view.md`


No change.


### `guide/src/content/docs/model/managing-workspaces.md`


No change.


### `guide/src/content/docs/model/migrations.md`


No change.


### `guide/src/content/docs/model/model-change-accounts.md`


No change.


### `guide/src/content/docs/model/model-language-versions.md`


No change.


### `guide/src/content/docs/model/model-mappings.md`


Old:

```markdown
**Settings › Data operations › Copy and move** lists saved Mappings with their source and target
models, version and updated time. **Recent copies and moves** lists workspace pairs, Copy or Move,
state, change sets and creation time. **Load more mappings** reads older mappings.
```


New:

```markdown
**Settings › Workspaces and models › Copy and move** lists saved Mappings with their source and target
models, version and updated time. **Recent copies and moves** lists workspace pairs, Copy or Move,
state, change sets and creation time. **Load more mappings** reads older mappings.
```


### `guide/src/content/docs/model/models.md`


No change.


### `guide/src/content/docs/model/record-pages-and-tables.md`


Old:

```markdown
List panels can read 1–100 rows per page. A reading size limits a page of results, not the
whole collection. The record header normally shows the name and type; a declared title or
subtitle field can supply other context. Breadcrumbs can include the application, type and
ancestors. In **Record page**, choose **Header and breadcrumbs…** to set the title, optional
line under it, type label and each breadcrumb part. This page-specific header does not change
the type’s shared Display attribute.
```


New:

```markdown
List panels can read 1–100 rows per page. A reading size limits a page of results, not the
whole collection. The record header normally shows the name and type; a declared title or
subtitle field can supply other context. The line above the title holds the list link, when
opened from a list, and the ancestors the model shows; it has no application entry. In **Record
page**, choose **Header and breadcrumbs…** to set the title, optional line under it, type label
and whether ancestors appear. Either type-name choice places the type in the header. This page-specific header does not change
the type’s shared Display attribute.
```


### `guide/src/content/docs/model/releases.md`


No change.


### `guide/src/content/docs/model/the-model-editor.md`


No change.


### `guide/src/content/docs/model/types-attributes-relations.md`


No change.


### `guide/src/content/docs/model/workbook-onboarding.md`


No change.


### `guide/src/content/docs/model/workbook-proposals.md`


No change.


### `guide/src/content/docs/run/ai.md`


Old:

```markdown
Other permissions still matter: AI access alone does not grant permission to import, edit a model
or work in a change set. People without the action group are not offered AI actions. Operators need
**Operations** to inspect **Settings › Administration › AI** and send a provider test request.

External MCP assistants act within their person's or client's permissions, restricted to browsing
and work in change sets. They cannot approve, publish or write directly to live data. Security
administrators manage them on **Settings › Security › Agent access**.
```


New:

```markdown
Other permissions still matter: AI access alone does not grant permission to import, edit a model
or work in a change set. People without the action group are not offered AI actions. Operators need
**Operations** to inspect **Settings › This instance › AI** and send a provider test request.

External MCP assistants act within their person's or client's permissions, restricted to browsing
and work in change sets. They cannot approve, publish or write directly to live data. Security
administrators manage them on **Settings › Connections › Agent access**.
```


Old:

```markdown
Open **Settings › Administration › AI** to see which switches are on, the send level and, when a
provider is configured, its model, endpoint, whether a key is set, and the features available.
The key itself is never shown. This page displays settings; change them in the environment.
```


New:

```markdown
Open **Settings › This instance › AI** to see which switches are on, the send level and, when a
provider is configured, its model, endpoint, whether a key is set, and the features available.
The key itself is never shown. This page displays settings; change them in the environment.
```


Old:

```markdown
Set these in the engine's environment, then recreate the Compose container or restart the host
service. **Settings › Administration › AI** displays them; it does not edit them.
```


New:

```markdown
Set these in the engine's environment, then recreate the Compose container or restart the host
service. **Settings › This instance › AI** displays them; it does not edit them.
```


Old:

```markdown
`MCP_ENABLED` enables MCP Streamable HTTP, protocol `2025-11-25`, at `/mcp`. The shipped web proxy
passes `/mcp` and `/.well-known/`; forward both when supplying your own proxy, and keep `PUBLIC_URL`
consistent with the public HTTPS address. With the switch off the endpoints return 404 and no agent
token is issued. **Settings › Security › Agent access** then says **Agent access is off**.
```


New:

```markdown
`MCP_ENABLED` enables MCP Streamable HTTP, protocol `2025-11-25`, at `/mcp`. The shipped web proxy
passes `/mcp` and `/.well-known/`; forward both when supplying your own proxy, and keep `PUBLIC_URL`
consistent with the public HTTPS address. With the switch off the endpoints return 404 and no agent
token is issued. **Settings › Connections › Agent access** then says **Agent access is off**.
```


### `guide/src/content/docs/run/background-jobs.md`


Old:

```markdown
Background workers run inside each engine process. `INTEGRATION_JOBS_ENABLED=true`, the default,
enables creating and running jobs. Turning it off keeps job reads available but stops workers and
job mutations. Work also needs a healthy model. Check **Settings › Data operations › Jobs** for job
state and outcomes, and **Operations** for worker health. Permissions determine which jobs a person
may inspect or cancel; see [Jobs](/docs/use/jobs/).
```


New:

```markdown
Background workers run inside each engine process. `INTEGRATION_JOBS_ENABLED=true`, the default,
enables creating and running jobs. Turning it off keeps job reads available but stops workers and
job mutations. Work also needs a healthy model. Check **Settings › This instance › Jobs** for job
state and outcomes, and **Operations** for worker health. Permissions determine which jobs a person
may inspect or cancel; see [Jobs](/docs/use/jobs/).
```


Old:

```markdown
Tasks use `AI_TASK_RETENTION_DAYS` (90 by default), separately from ordinary job retention. Session
folders, logs and transcripts stay while a task can continue; the next read after publication,
discard or confirmed migration removes them, and expiry also cleans them. In the shipped image,
each task has a randomly named folder under `/opt/refiroo/rdm-engine/data/assistant`, with
working files in `work`, Claude Code configuration and transcripts in `claude`, and turn logs
inside the same task folder. Session users cannot list the parent folder to find other tasks.
Compose persists this in the single `assistant` volume across container replacement, until normal
cleanup. Backups may omit it; losing it loses open tasks’ folders and session logs, not records.
After upgrading from the earlier shared-transcript layout, existing files are kept but the next
turn starts a new session. See [Upgrades](/docs/run/upgrades/#volumes-and-open-assistant-tasks).
**Calls** on **Settings › Administration › AI** keeps turn outcomes and usage separately. See
[AI retention and recovery](/docs/run/ai/#what-is-kept) before maintenance or a retry.
```


New:

```markdown
Tasks use `AI_TASK_RETENTION_DAYS` (90 by default), separately from ordinary job retention. Session
folders, logs and transcripts stay while a task can continue; the next read after publication,
discard or confirmed migration removes them, and expiry also cleans them. In the shipped image,
each task has a randomly named folder under `/opt/refiroo/rdm-engine/data/assistant`, with
working files in `work`, Claude Code configuration and transcripts in `claude`, and turn logs
inside the same task folder. Session users cannot list the parent folder to find other tasks.
Compose persists this in the single `assistant` volume across container replacement, until normal
cleanup. Backups may omit it; losing it loses open tasks’ folders and session logs, not records.
After upgrading from the earlier shared-transcript layout, existing files are kept but the next
turn starts a new session. See [Upgrades](/docs/run/upgrades/#volumes-and-open-assistant-tasks).
**Calls** on **Settings › This instance › AI** keeps turn outcomes and usage separately. See
[AI retention and recovery](/docs/run/ai/#what-is-kept) before maintenance or a retry.
```


### `guide/src/content/docs/run/backup-and-restore.md`


Old:

```markdown
Open **Settings › Administration › Operations › Last backup rehearsal**. Before the first check,
**No backup has been rehearsed** means no result has been recorded. After a check it shows **Passed**
or **Failed**, the backup name when supplied, the copy's revision and the workspace results.
**Records**, **Relationships**, **Open change sets** and **Publications** count the restored copy;
**Live now** compares the current instance. Different counts alone do not fail the check.
The same results are readable as JSON through the [backup rehearsal operation](/docs/run/monitoring/#backup-rehearsals), with its [API reference](/docs/api/?api=management#tag/system).
```


New:

```markdown
Open **Settings › This instance › Operations › Last backup rehearsal**. Before the first check,
**No backup has been rehearsed** means no result has been recorded. After a check it shows **Passed**
or **Failed**, the backup name when supplied, the copy's revision and the workspace results.
**Records**, **Relationships**, **Open change sets** and **Publications** count the restored copy;
**Live now** compares the current instance. Different counts alone do not fail the check.
The same results are readable as JSON through the [backup rehearsal operation](/docs/run/monitoring/#backup-rehearsals), with its [API reference](/docs/api/?api=management#tag/system).
```


### `guide/src/content/docs/run/command-line.md`


No change.


### `guide/src/content/docs/run/configure.md`


Old:

```markdown
With Operations access, open **Settings › Administration › Deployment**. **Capability groups**
shows what this deployment serves. **Database** shows the migration revision. Each settings table
shows **Setting**, **Value**, **Default**, **Source** and **What it controls**.
**Environment** means explicitly supplied; **Default** means the engine chose its default.
Secrets show only **Set** or **Not set**, and the database address hides its password.
This page is read only. At the top it names the API address used by this browser. Normally that
is the address you opened; `VITE_API_URL` can select another engine when building the frontend.
Changing that build setting requires rebuilding the frontend, rather than restarting the engine.
```


New:

```markdown
With Operations access, open **Settings › This instance › Deployment**. **Capability groups**
shows what this deployment serves. **Database** shows the migration revision. Each settings table
shows **Setting**, **Value**, **Default**, **Source** and **What it controls**.
**Environment** means explicitly supplied; **Default** means the engine chose its default.
Secrets show only **Set** or **Not set**, and the database address hides its password.
This page is read only. At the top it names the API address used by this browser. Normally that
is the address you opened; `VITE_API_URL` can select another engine when building the frontend.
Changing that build setting requires rebuilding the frontend, rather than restarting the engine.
```


Old:

```markdown
To identify versions, open **Settings › General › About**. **Engine** lists **Engine version**,
**Management API**, **Schema languages**, **Licence** and **Source code** (opens in a new tab).
**Active model release** lists **Name**, **Key**, **Version**, **Schema language** and **Activated**.
**Activated** is when that release was selected, not when it was installed. **Open release** opens
its page in Settings › Model; access there still requires model-authoring or model-release permission.
Use the account menu to enter Settings and **Back to {application}** to return to the application.
```


New:

```markdown
To identify versions, open **Settings › This instance › About**. **Engine** lists **Engine version**,
**Management API**, **Schema languages**, **Licence** and **Source code** (opens in a new tab).
**Active model release** lists **Name**, **Key**, **Version**, **Schema language** and **Activated**.
**Activated** is when that release was selected, not when it was installed. **Open release** opens
its page in Settings › Model; access there still requires model-authoring or model-release permission.
Use the account menu to enter Settings and **Back to {application}** to return to the application.
```


### `guide/src/content/docs/run/database.md`


No change.


### `guide/src/content/docs/run/developer-instance.md`


No change.


### `guide/src/content/docs/run/health-and-startup-checks.md`


Old:

```markdown
Use your public host. Probes reveal only `ok` or `unhealthy`; authenticated operators get the detail
on **Settings › Administration › Operations**. A ready installation can still have an unavailable
workspace. Inspect that page's workspace rows, not just the probe.
```


New:

```markdown
Use your public host. Probes reveal only `ok` or `unhealthy`; authenticated operators get the detail
on **Settings › This instance › Operations**. A ready installation can still have an unavailable
workspace. Inspect that page's workspace rows, not just the probe.
```


### `guide/src/content/docs/run/https.md`


No change.


### `guide/src/content/docs/run/install-with-compose.md`


Old:

```markdown
Add other people through **Settings › Security › People**:
```


New:

```markdown
Add other people through **Settings › People and access › People**:
```


### `guide/src/content/docs/run/licence-and-source.md`


Old:

```markdown
Check the source link in **Settings › General › About** and the account menu. It must lead
to the source of that running build. The authenticated system-information operation
`GET /api/v1/system` also reports it as `engine.sourceCode`, alongside engine version and licence;
see the [API reference](/docs/api).
```


New:

```markdown
Check the source link in **Settings › This instance › About** and the account menu. It must lead
to the source of that running build. The authenticated system-information operation
`GET /api/v1/system` also reports it as `engine.sourceCode`, alongside engine version and licence;
see the [API reference](/docs/api).
```


### `guide/src/content/docs/run/model-releases-and-rollback.md`


No change.


### `guide/src/content/docs/run/monitoring.md`


Old:

```markdown
Start with **Settings › Administration › Operations**, available with Operations access. It shows
workspaces served or unavailable, live and silent processes, jobs, and webhook subscription states.
Below the totals are workspace failures, process threads and pool use, the latest backup rehearsal,
and probe addresses. It refreshes every 15 seconds while visible; **Refresh** reads again immediately.
A failed refresh preserves the previous figures and says when they were read.
```


New:

```markdown
Start with **Settings › This instance › Operations**, available with Operations access. It shows
workspaces served or unavailable, live and silent processes, jobs, and webhook subscription states.
Below the totals are workspace failures, process threads and pool use, the latest backup rehearsal,
and probe addresses. It refreshes every 15 seconds while visible; **Refresh** reads again immediately.
A failed refresh preserves the previous figures and says when they were read.
```


Old:

```markdown
**Settings › Administration › AI** needs Operations access and lists each provider call and
assistant turn with its purpose, requester, outcome, tokens, reported cost and duration. Totals
cover 30 days. This is usage evidence, not a billing statement. **Send a test request** checks only
the provider and sends no reference data; test a real assistant task separately. Read the failure
sentence before retrying; a provider failure leaves ordinary work available.

For external assistants, a security administrator uses **Settings › Security › Agent access**.
Its separate call list shows answered, refused, limited and failed calls, including argument names
but never values. Use its request identifier when tracing a failure. See [AI and agent settings](/docs/run/ai/)
for send policy, cost, retention and revocation. Logging provider content is optional and can retain
sensitive reference data; do not enable it merely to collect call counts.
```


New:

```markdown
**Settings › This instance › AI** needs Operations access and lists each provider call and
assistant turn with its purpose, requester, outcome, tokens, reported cost and duration. Totals
cover 30 days. This is usage evidence, not a billing statement. **Send a test request** checks only
the provider and sends no reference data; test a real assistant task separately. Read the failure
sentence before retrying; a provider failure leaves ordinary work available.

For external assistants, a security administrator uses **Settings › Connections › Agent access**.
Its separate call list shows answered, refused, limited and failed calls, including argument names
but never values. Use its request identifier when tracing a failure. See [AI and agent settings](/docs/run/ai/)
for send policy, cost, retention and revocation. Logging provider content is optional and can retain
sensitive reference data; do not enable it merely to collect call counts.
```


### `guide/src/content/docs/run/overview.md`


No change.


### `guide/src/content/docs/run/production-checklist.md`


Old:

```markdown
1. **Use the reference installation.** Build the intended source version with
   [Docker Compose](/docs/run/install-with-compose/). Keep only the entry web service public.
   PostgreSQL 17 must use ICU root `und` and the required extensions.
2. **Fix the public address and choose HTTPS.** Set the permanent HTTPS `PUBLIC_URL`, matching
   browser origins and provider callbacks. For a public name, choose [automatic HTTPS](/docs/run/https/)
   with `compose.acme.yml`: Caddy obtains and renews the certificate. Confirm DNS points here,
   TCP 443 is reachable from the internet and the `caddy-data` volume is preserved. Port 80 is
   optional for HTTP redirects; TLS-ALPN issuance and renewal work on 443 alone.
   Alternatively, supply your organisation's certificates or use its HTTPS balancer. Check
   certificate trust and renewal, plus HTTP redirection if port 80 is open. If behind a balancer, check its trusted address
   range and forwarded headers.
3. **Protect secrets.** Store the database password, sealing key and stable cursor key outside
   version control and images. Keep the same keys across processes. Associate each backup with
   its sealing key: [Secrets and keys](/docs/run/secrets-and-keys/).
4. **Confirm effective settings.** Read **Settings › Administration › Deployment**. Verify capability
   switches, limits, retention and migration revision. Recreate containers after environment
   changes; restarting alone does not apply them.
5. **Check access.** Test the first administrator, provider sign-in if used, appropriate grants,
   second-factor policy and a local recovery account. Reduce broad setup grants. Follow the
   [security checklist](/docs/run/security-checklist/).
6. **Test mail if needed.** Confirm the public link address, SMTP TLS and credentials, SPF/DKIM,
   a test message and actual receipt: [Sign-in and mail](/docs/run/sign-in-and-mail-setup/).
7. **Check readiness per workspace.** Require `/health` 200 and inspect every active workspace and
   process on **Operations**. Use `/health/live` for liveness so a database outage does not cause
   restart loops.
8. **Set monitoring.** Collect bounded/rotated logs, authenticate private metrics scrapes and alert
   on unavailable workspaces, silent processes, failed workers and growing queues. Verify that a
   reported request ID leads to its log: [Monitoring](/docs/run/monitoring/).
9. **Protect files and capacity.** Persist job files, share them if several instances run, and
   budget connections across all processes. Exercise a representative import/export and check
   disk retention. Use the [database growth checks](/docs/run/database/#watch-database-growth) and
   set external log/metric retention; job retention does not bound all storage. Production CPU, memory, throughput and recovery sizing are **not measured**
   for your workload; collect your own evidence.
10. **Check integrations.** Confirm receiver trust, signature verification, event deduplication,
    retry recovery and re-sync procedures if using [webhooks](/docs/run/webhook-delivery/).
    Review [AI send policy](/docs/run/ai/) separately before enabling AI or agents.
11. **Prove recovery.** Back up the database and source files, restore into a separate database,
    and inspect the recorded rehearsal on Operations. Keep the matching application and private
    configuration: [Back up and restore](/docs/run/backup-and-restore/).
12. **Prepare upgrades and support.** Record the cutover and restore plan, the expected model schema,
    support diagnostics and corresponding source URL for a modified build. See
    [Upgrades](/docs/run/upgrades/) and [Licence and source](/docs/run/licence-and-source/).
```


New:

```markdown
1. **Use the reference installation.** Build the intended source version with
   [Docker Compose](/docs/run/install-with-compose/). Keep only the entry web service public.
   PostgreSQL 17 must use ICU root `und` and the required extensions.
2. **Fix the public address and choose HTTPS.** Set the permanent HTTPS `PUBLIC_URL`, matching
   browser origins and provider callbacks. For a public name, choose [automatic HTTPS](/docs/run/https/)
   with `compose.acme.yml`: Caddy obtains and renews the certificate. Confirm DNS points here,
   TCP 443 is reachable from the internet and the `caddy-data` volume is preserved. Port 80 is
   optional for HTTP redirects; TLS-ALPN issuance and renewal work on 443 alone.
   Alternatively, supply your organisation's certificates or use its HTTPS balancer. Check
   certificate trust and renewal, plus HTTP redirection if port 80 is open. If behind a balancer, check its trusted address
   range and forwarded headers.
3. **Protect secrets.** Store the database password, sealing key and stable cursor key outside
   version control and images. Keep the same keys across processes. Associate each backup with
   its sealing key: [Secrets and keys](/docs/run/secrets-and-keys/).
4. **Confirm effective settings.** Read **Settings › This instance › Deployment**. Verify capability
   switches, limits, retention and migration revision. Recreate containers after environment
   changes; restarting alone does not apply them.
5. **Check access.** Test the first administrator, provider sign-in if used, appropriate grants,
   second-factor policy and a local recovery account. Reduce broad setup grants. Follow the
   [security checklist](/docs/run/security-checklist/).
6. **Test mail if needed.** Confirm the public link address, SMTP TLS and credentials, SPF/DKIM,
   a test message and actual receipt: [Sign-in and mail](/docs/run/sign-in-and-mail-setup/).
7. **Check readiness per workspace.** Require `/health` 200 and inspect every active workspace and
   process on **Operations**. Use `/health/live` for liveness so a database outage does not cause
   restart loops.
8. **Set monitoring.** Collect bounded/rotated logs, authenticate private metrics scrapes and alert
   on unavailable workspaces, silent processes, failed workers and growing queues. Verify that a
   reported request ID leads to its log: [Monitoring](/docs/run/monitoring/).
9. **Protect files and capacity.** Persist job files, share them if several instances run, and
   budget connections across all processes. Exercise a representative import/export and check
   disk retention. Use the [database growth checks](/docs/run/database/#watch-database-growth) and
   set external log/metric retention; job retention does not bound all storage. Production CPU, memory, throughput and recovery sizing are **not measured**
   for your workload; collect your own evidence.
10. **Check integrations.** Confirm receiver trust, signature verification, event deduplication,
    retry recovery and re-sync procedures if using [webhooks](/docs/run/webhook-delivery/).
    Review [AI send policy](/docs/run/ai/) separately before enabling AI or agents.
11. **Prove recovery.** Back up the database and source files, restore into a separate database,
    and inspect the recorded rehearsal on Operations. Keep the matching application and private
    configuration: [Back up and restore](/docs/run/backup-and-restore/).
12. **Prepare upgrades and support.** Record the cutover and restore plan, the expected model schema,
    support diagnostics and corresponding source URL for a modified build. See
    [Upgrades](/docs/run/upgrades/) and [Licence and source](/docs/run/licence-and-source/).
```


### `guide/src/content/docs/run/secrets-and-keys.md`


No change.


### `guide/src/content/docs/run/security-checklist.md`


No change.


### `guide/src/content/docs/run/set-up-ai.md`


Old:

```markdown
This is optional and does not enable or authenticate the built-in assistant. The shipped web image
already forwards `/mcp` and `/.well-known/`; another reverse proxy must forward them too. After
restart, a security administrator can open **Settings › Security › Agent access** to register and
manage assistants and agent clients. Their grants determine the data they can reach.
```


New:

```markdown
This is optional and does not enable or authenticate the built-in assistant. The shipped web image
already forwards `/mcp` and `/.well-known/`; another reverse proxy must forward them too. After
restart, a security administrator can open **Settings › Connections › Agent access** to register and
manage assistants and agent clients. Their grants determine the data they can reach.
```


Old:

```markdown
1. With **Operations** access, open **Settings › Administration › AI**. Under **What is switched on**,
   check **Assistant** and **Provider** against what you enabled. **Assistant: On** means the command
   is set; it does not prove a session can authenticate. Check **What may be sent** too.
2. If a provider is configured, select **Send a test request**. Success shows **The AI provider
   answered** and a new **Calls** entry. The request contains none of your reference data. With
   only the assistant enabled, this button is absent.
3. To test the assistant independently, use an active workspace and a person with **Use AI proposals**,
   **Work in change sets**, **Bulk and import**, and permission to create jobs there. The model-change
   test also needs **Model authoring** and **Model release** access. Open the workspace's
   **⋯** menu and choose **Change this model…**. Enter a small proposed change in **What should
   change?**, then select **Ask the assistant**. Wait until the task presents its proposal, then
   read it without applying it. Reaching the proposal checks that the assistant can reach the
   engine's API as well as authenticate with Claude Code. This exercises a real session and sends
   the instructions, model and any records it needs.
4. Return to **Settings › Administration › AI**. The session's turn should appear in **Calls** with
   its outcome, tokens and any reported cost. Review or discard the test task when finished.
```


New:

```markdown
1. With **Operations** access, open **Settings › This instance › AI**. Under **What is switched on**,
   check **Assistant** and **Provider** against what you enabled. **Assistant: On** means the command
   is set; it does not prove a session can authenticate. Check **What may be sent** too.
2. If a provider is configured, select **Send a test request**. Success shows **The AI provider
   answered** and a new **Calls** entry. The request contains none of your reference data. With
   only the assistant enabled, this button is absent.
3. To test the assistant independently, use an active workspace and a person with **Use AI proposals**,
   **Work in change sets**, **Bulk and import**, and permission to create jobs there. The model-change
   test also needs **Model authoring** and **Model release** access. Open the workspace's
   **⋯** menu and choose **Change this model…**. Enter a small proposed change in **What should
   change?**, then select **Ask the assistant**. Wait until the task presents its proposal, then
   read it without applying it. Reaching the proposal checks that the assistant can reach the
   engine's API as well as authenticate with Claude Code. This exercises a real session and sends
   the instructions, model and any records it needs.
4. Return to **Settings › This instance › AI**. The session's turn should appear in **Calls** with
   its outcome, tokens and any reported cost. Review or discard the test task when finished.
```


### `guide/src/content/docs/run/several-processes.md`


Old:

```markdown
Open **Settings › Administration › Operations** with Operations access. It lists live and silent
processes, their readiness, threads, connections and workspace failures. Reports arrive every
`PROCESS_HEARTBEAT_SECONDS` (default 15); three missed intervals mark a process silent.
A clean stop removes the row; a dead process's row ages out after a day.
```


New:

```markdown
Open **Settings › This instance › Operations** with Operations access. It lists live and silent
processes, their readiness, threads, connections and workspace failures. Reports arrive every
`PROCESS_HEARTBEAT_SECONDS` (default 15); three missed intervals mark a process silent.
A clean stop removes the row; a dead process's row ages out after a day.
```


### `guide/src/content/docs/run/sign-in-and-mail-setup.md`


Old:

```markdown
Arrange an SMTP server and a sender address. A security administrator saves these on **Settings › Integration › Mail**:
```


New:

```markdown
Arrange an SMTP server and a sender address. A security administrator saves these on **Settings › This instance › Mail**:
```


Old:

```markdown
On **Settings › Integration › Mail**, choose **Microsoft 365** under **Send mail through**.
Enter **Tenant ID** and **Application (client) ID**, choose **Client secret** or **Certificate**
under **Sign in with**, and enter the prepared value or PEM text. Set **Sending mailbox** to the
mailbox above and **Application address** to the public address recipients use to open refiroo.
An empty application address uses the default displayed below the field.
```


New:

```markdown
On **Settings › This instance › Mail**, choose **Microsoft 365** under **Send mail through**.
Enter **Tenant ID** and **Application (client) ID**, choose **Client secret** or **Certificate**
under **Sign in with**, and enter the prepared value or PEM text. Set **Sending mailbox** to the
mailbox above and **Application address** to the public address recipients use to open refiroo.
An empty application address uses the default displayed below the field.
```


Old:

```markdown
   The group must hold the sending mailbox. RBAC for Applications is another way to restrict it.
   Without a restriction, the role allows sending as any mailbox in the tenant. Allow time for
   a changed policy to apply before testing.
4. On **Settings › Integration › Mail**, choose **Microsoft 365**, then **Managed identity – this
   tenant** under **Sign in with**. Leave **Identity client ID** empty for the system-assigned
   identity, or enter the user-assigned identity’s client ID. Do not supply a tenant or application
   ID; this choice neither asks for nor accepts them. Enter **Sending mailbox** and **Application
   address**, then save and test as described below.
```


New:

```markdown
   The group must hold the sending mailbox. RBAC for Applications is another way to restrict it.
   Without a restriction, the role allows sending as any mailbox in the tenant. Allow time for
   a changed policy to apply before testing.
4. On **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – this
   tenant** under **Sign in with**. Leave **Identity client ID** empty for the system-assigned
   identity, or enter the user-assigned identity’s client ID. Do not supply a tenant or application
   ID; this choice neither asks for nor accepts them. Enter **Sending mailbox** and **Application
   address**, then save and test as described below.
```


Old:

```markdown
   Confirm that the app has the **Mail.Send** application permission in that tenant.
4. In the customer’s Exchange Online tenant, restrict the app to the sending mailbox with an
   application access policy, using `-AppId <the app's client ID>`, or RBAC for Applications.
   For an application access policy, use a mail-enabled security group holding that mailbox.
   Allow time for the restriction to apply.
5. On **Settings › Integration › Mail**, choose **Microsoft 365**, then **Managed identity – hosted
   in another tenant** under **Sign in with**. Enter the customer’s **Tenant ID**, the multitenant
   app’s **Application (client) ID** and the user-assigned **Identity client ID**. All three are
   required. Enter **Sending mailbox** and **Application address**, then save and test below.
```


New:

```markdown
   Confirm that the app has the **Mail.Send** application permission in that tenant.
4. In the customer’s Exchange Online tenant, restrict the app to the sending mailbox with an
   application access policy, using `-AppId <the app's client ID>`, or RBAC for Applications.
   For an application access policy, use a mail-enabled security group holding that mailbox.
   Allow time for the restriction to apply.
5. On **Settings › This instance › Mail**, choose **Microsoft 365**, then **Managed identity – hosted
   in another tenant** under **Sign in with**. Enter the customer’s **Tenant ID**, the multitenant
   app’s **Application (client) ID** and the user-assigned **Identity client ID**. All three are
   required. Enter **Sending mailbox** and **Application address**, then save and test below.
```


Old:

```markdown
The same sender delivers inbox notices and digests. People choose them in **Settings › General › Notification email**;
clients receive no mail. These choices do not need AI or another server setting. Immediate notices
are mailed only after a person opts in and while the notice is less than 24 hours old, preventing
an old backlog after a long outage. The inbox retains notices even when their mail is off.
```


New:

```markdown
The same sender delivers inbox notices and digests. People choose them in **Settings › You › Notification email**;
clients receive no mail. These choices do not need AI or another server setting. Immediate notices
are mailed only after a person opts in and while the notice is less than 24 hours old, preventing
an old backlog after a long outage. The inbox retains notices even when their mail is off.
```


### `guide/src/content/docs/run/troubleshooting.md`


Old:

```markdown
If liveness answers but readiness does not, investigate the database or model readiness. Restarting
a healthy process repeatedly does not restore its database. With Operations access, open
**Settings › Administration › Operations** for workspace and process detail.
```


New:

```markdown
If liveness answers but readiness does not, investigate the database or model readiness. Restarting
a healthy process repeatedly does not restore its database. With Operations access, open
**Settings › This instance › Operations** for workspace and process detail.
```


### `guide/src/content/docs/run/upgrades.md`


Old:

```markdown
5. Check **Settings › Administration › Deployment › Database › Migration revision** against the
   migrated version, then `/health` and **Settings › Administration › Operations**. Check every active workspace,
   not only overall readiness. Verify sign-in and a representative read before reopening writers.
```


New:

```markdown
5. Check **Settings › This instance › Deployment › Database › Migration revision** against the
   migrated version, then `/health` and **Settings › This instance › Operations**. Check every active workspace,
   not only overall readiness. Verify sign-in and a representative read before reopening writers.
```


### `guide/src/content/docs/run/webhook-delivery.md`


Old:

```markdown
An administrator or integration owner manages subscriptions on **Settings › Integration › Webhooks**.
Use [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for the integration sequence and the
[API reference](/docs/api) for operations. Receivers need a consumer API that declares events.
```


New:

```markdown
An administrator or integration owner manages subscriptions on **Settings › Connections › Webhooks**.
Use [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for the integration sequence and the
[API reference](/docs/api) for operations. Receivers need a consumer API that declares events.
```


Old:

```markdown
Subscription management requires Integration administration for its workspace; an Operator role
alone does not grant it. On **Settings › Integration › Webhooks**, open the subscription by name.
Check the address, consumer API, workspace, selected events, filter tags and request format against
the receiver's configuration. The **Configuration** tab shows its state, suspension reason and
recovery advice. Authorised owners can edit, suspend, resume, rotate its key or delete it there.
Read current state before an edit: a version conflict requires reloading and reviewing the other
administrator's change.
```


New:

```markdown
Subscription management requires Integration administration for its workspace; an Operator role
alone does not grant it. On **Settings › Connections › Webhooks**, open the subscription by name.
Check the address, consumer API, workspace, selected events, filter tags and request format against
the receiver's configuration. The **Configuration** tab shows its state, suspension reason and
recovery advice. Authorised owners can edit, suspend, resume, rotate its key or delete it there.
Read current state before an edit: a version conflict requires reloading and reviewing the other
administrator's change.
```


### `guide/src/content/docs/use/applications.md`


Old:

```markdown
Open an application to reach the records and views you need in the current workspace.
Follow [Open an application](/docs/guide/use/open-an-application/) for the steps.
```


New:

```markdown
Open an application to reach the records and views you need in the current workspace.
Choose a workspace’s name or tile on Home to open its page: it offers record search, applications,
your waiting change sets and the five latest changes. **Edit model** and the workspace’s **⋯**
menu offer the actions and Settings pages your access allows.
Follow [Open an application](/docs/guide/use/open-an-application/) for the steps.
```


Old:

```markdown
Choose an application in the top bar, then a collection in the sidebar. A collection can have
several views, shown as tabs. Changing tabs changes how you inspect the records; it does not
copy them. The model can choose which view opens when you select a collection in the
sidebar or on a group page. That choice may differ from the application's starting view;
use the tabs to switch to another view when needed. **Browse records** offers another route to individual records through their hierarchy.
```


New:

```markdown
Choose an application in the top bar, then a collection in the sidebar. A collection can have
several views, shown as tabs under the list’s title. Changing tabs changes how you inspect the records; it does not
copy them. The model can choose which view opens when you select a collection in the
sidebar or on a group page. That choice may differ from the application's starting view;
use the tabs to switch to another view when needed. **Browse records** offers another route to individual records through their hierarchy. Open it to browse; it starts folded and remembers your choice in this browser.
```


Old:

```markdown
The banner identifies **Live**, a **Change set**, or a publication. Live edits apply immediately;
a change set holds proposed changes; a publication is read-only. Check that context before editing.
Your roles determine which actions are offered. A declared view does not grant permission to
change its records. See [Record permissions](/docs/use/records/#who-may-read-and-change-records).
```


New:

```markdown
The banner identifies **Live**, a **Change set**, or a publication. Live edits apply immediately;
a change set holds proposed changes; a publication is read-only. On a computer the band shows
only this data context, its explanation or change-set summary and the **Live · Change sets ·
Publications** switch. On a phone it also shows the workspace and application. Check the context before editing.
Your roles determine which actions are offered. A declared view does not grant permission to
change its records. See [Record permissions](/docs/use/records/#who-may-read-and-change-records).
```


Old:

```markdown
On a wide screen, each application has a coloured tile in the top bar. The open application
is underlined; hovering over its tab shows the model's description. The product mark returns
to **Home**, and the gear opens **Settings**. On a phone, choose the application from the band
beneath the top bar instead. See [Appearance and devices](/docs/use/appearance-and-devices/).
```


New:

```markdown
On a wide screen, each application has a coloured tile in the top bar. The open application
is underlined; hovering over its tab shows the model's description. The product mark returns
to **Home**, and the gear opens **Settings**. Applications that do not fit are under **More**.
Settings opens an index grouped by task. Inside Settings, **← Back to** followed by the workspace’s
name returns to its page. On a phone, choose the application from the band
beneath the top bar instead. See [Appearance and devices](/docs/use/appearance-and-devices/).
```


Old:

```markdown
**Find a record**, under **Browse records**, searches records instead. The group page's
**Find a collection or matrix** searches only that group's entries.

```


New:

```markdown
**Find any record** in the top bar searches record names across the workspace instead. Results
are grouped by record type and show each record’s place. Use the arrow keys to choose a result and
Enter to open it. Workspace search opens the record in **Live**; use a collection’s own search
to stay in a change set or publication. **Browse records** has no search box of its own. The group page's
**Find a collection or matrix** searches only that group's entries.

```


### `guide/src/content/docs/use/change-sets.md`


Old:

```markdown
A change set starts from a copy of data at a particular moment. Its source is shown alongside
its name, version and model release.
```


New:

```markdown
A change set starts from a copy of data at a particular moment. Its source is shown alongside
its name, version and model release in the change-set list; inside it, open **Details** in the
band to read its source, creator, creation time, version and model.
```


Old:

```markdown
The orange **Change set** banner names the change set and says **Edits stay in this change set
until it is published**. The green **Live** banner says that edits apply immediately in the
workspace. Check this context before saving. The ordinary record controls work in either context;
their destination is different. See
[Make the changes](/docs/guide/use/prepare-and-publish-a-change-set/#make-the-changes) and
[Correct a record](/docs/guide/use/correct-a-record/).
```


New:

```markdown
The orange **Change set** band shows its name, number of changes and state in one row on a
computer. Edits stay in this change set until it is published. The green **Live** banner says that edits apply immediately in the
workspace. Check this context before saving. The ordinary record controls work in either context;
their destination is different. See
[Make the changes](/docs/guide/use/prepare-and-publish-a-change-set/#make-the-changes) and
[Correct a record](/docs/guide/use/correct-a-record/).
```


Old:

```markdown
**Review changes** compares the change set with its starting data. **Records** shows additions,
changes and removals, including moves and type changes where applicable. A row identifies the
record and its path; expanding it shows the before and after details. **Relationships** shows
changes to connections. Filters help narrow the review to a kind of change or a type.
```


New:

```markdown
Opening a change set from the list opens **Changes in this change set**, which compares it
with its starting data. Choose **See the data with these changes** to browse or edit its lists.
A newly created change set, or your own open change set from Home’s **Continue where you left off**,
opens on the data. From there, **Review changes** in the band opens the comparison. **Records** shows additions,
changes and removals, including moves and type changes where applicable. A row identifies the
record and its path; expanding it shows the before and after details. **Relationships** shows
changes to connections. Filters help narrow the review to a kind of change or a type.
```


### `guide/src/content/docs/use/hierarchies.md`


Old:

```markdown
The model defines which types may contain which others and which types may stand at the top
without a parent. A type label grouping records in a tree is navigation, not another record.
A tree view shows the roots and types chosen by the model; it need not show every record in the
workspace. The sidebar's **Browse records** tree is another route to records.
```


New:

```markdown
The model defines which types may contain which others and which types may stand at the top
without a parent. A type label grouping records in a tree is navigation, not another record.
A tree view shows the roots and types chosen by the model; it need not show every record in the
workspace. The sidebar’s **Browse records** tree is another route to records. Open its folded
heading to browse; your choice is remembered in this browser. Use **Find any record** in the
top bar to search names across the workspace.
```


Old:

```markdown
A tree view opens a record beside the list, with **Expand to full page** for its full page.
An explorer-tree record opens without a collection behind it. A table record instead offers
**Back to list**. **Resize navigation rail** changes the rail width; see
[Appearance and devices](/docs/use/appearance-and-devices/) for keyboard resizing.
```


New:

```markdown
A tree view opens a record beside the list, with **Expand to full page** for its full page.
An explorer-tree record opens without a collection behind it. A table record instead offers
**←** and the list’s name in the line above its title, followed by its parents where shown. **Resize navigation rail** changes the rail width; see
[Appearance and devices](/docs/use/appearance-and-devices/) for keyboard resizing.
```


### `guide/src/content/docs/use/history.md`


Old:

```markdown
Where your access opens workspace management, choose **Settings**, **Workspaces**, the workspace,
then **Activity**. Its **What** choices are **Everything**, **Records**, **Relationships**,
**Change sets** and **Publications**. Entries identify the action, person and time, and can also
name its change set or publication context.
```


New:

```markdown
The workspace’s page shows its five **Latest changes**. For more activity, where your access
opens workspace management, choose **Settings**, **Workspaces**, the workspace,
then **Activity**. Its **What** choices are **Everything**, **Records**, **Relationships**,
**Change sets** and **Publications**. Entries identify the action, person and time, and can also
name its change set or publication context.
```


### `guide/src/content/docs/use/inbox-and-approvals.md`


Old:

```markdown
**Submit for publication** validates the change set and records its submitted version. An optional
comment gives the approver context. Submission does not change Live. The banner shows
**Waiting for approval**, the submitter, version and comment. The proposal cannot be edited while
it waits. **Withdraw request** ends the request and keeps the proposed work for editing; the
submitter or an authorised approver can withdraw it.
```


New:

```markdown
**Submit for publication** validates the change set and records its submitted version. An optional
comment gives the approver context. Submission does not change Live. The band says **waits for approval**. Open **Details** for the submitter and submitted version,
and the review’s **Decision** panel for the comment. The proposal cannot be edited while
it waits. **Withdraw request** ends the request and keeps the proposed work for editing; the
submitter or an authorised approver can withdraw it.
```


Old:

```markdown
*Above: Guide Admin submitted Guide approval example in Graubünden. Version 2 proposes a height
correction to Davos Platz; the banner keeps the submission comment visible.*
```


New:

```markdown
*Above: Guide Admin submitted Guide approval example in Graubünden. Version 2 proposes a height
correction to Davos Platz; this earlier view keeps the submission comment in the banner.
In the current frame, read the comment in the review’s **Decision** panel.*
```


### `guide/src/content/docs/use/lists-and-filters.md`


Old:

```markdown
**Display** chooses the shown columns and table density. Resizing a column changes how much
fits. Rows stay on one line; an ellipsis marks a cut value. Hover, focus or long press to read
it in full. A related-record column shows coloured chips and **+N more** when some do not fit.
That count is not a button: widen the column or open the record to see all its connections.
A column with at most one related record can sort by its name. Multi-record columns and columns
showing a related record's field do not sort; use a relationship filter to narrow them.
```


New:

```markdown
**Display** chooses the shown columns and table density. Resizing a column changes how much
fits. The name column stays whole; columns that do not fit fold behind **Columns · n of m**.
Choose it to show all columns, scrolling sideways if needed. Other values stay on one line; an ellipsis marks a cut value. Hover, focus or long press to read
it in full. A related-record column shows coloured chips and **+N more** when some do not fit.
That count is not a button: widen the column or open the record to see all its connections.
A column with at most one related record can sort by its name. Multi-record columns and columns
showing a related record's field do not sort; use a relationship filter to narrow them.
```


Old:

```markdown
The rows scroll inside the table while its headings and footer remain visible. The footer
shows the current range and total, page entry and start/end controls. Where available,
**Go to** seeks a value in the selected sort. The address keeps your search, filters, sort and
position, including when you return with **Back to list**. These controls also work in change
sets and publications.
```


New:

```markdown
The rows scroll inside the table while its headings and footer remain visible. The footer
shows the current range and total, page entry and start/end controls. Where available,
**Go to** seeks a value in the selected sort. The address keeps your search, filters, sort and
position, including when you return using **←** and the list’s name above a record’s title. These controls also work in change
sets and publications.
```


Old:

```markdown
There are no named saved searches, saved filters or saved views. Keep the page address instead.
There is no multi-column sort, grouping or aggregation in the list, and no cross-collection
search page. The explorer's search can find records across its types; a collection's search
stays within that collection. See [Appearance and devices](/docs/use/appearance-and-devices/)
for local keyboard commands.
```


New:

```markdown
There are no named saved searches, saved filters or saved views. Keep the page address instead.
There is no multi-column sort, grouping or aggregation in the list, and no cross-collection
search page. **Find any record** in the top bar searches record names across the workspace;
a collection’s search stays within that collection. See [Appearance and devices](/docs/use/appearance-and-devices/)
for local keyboard commands.
```


Old:

```markdown
Choose a row to open its record; a related-record chip opens that connected record instead.
The record heading takes focus when the page opens. **Back to list** returns to the saved
conditions and position. A failed panel can be retried without clearing the rest of the record.
For field and relationship edits from table cells, see [Records](/docs/use/records/#edit-a-value-or-create-a-record).
To select results for an action, see [Changing many records](/docs/use/changing-many-records/).
```


New:

```markdown
Choose a row to open its record; a related-record chip opens that connected record instead.
The record heading takes focus when the page opens. Choose **←** and the list’s name above
the title to return to the saved conditions and position. A failed panel can be retried without clearing the rest of the record.
For field and relationship edits from table cells, see [Records](/docs/use/records/#edit-a-value-or-create-a-record).
To select results for an action, see [Changing many records](/docs/use/changing-many-records/).
```


### `guide/src/content/docs/use/records.md`


Old:

```markdown
*Above: Chur Wiesental is a Stop in the Network application of the Graubünden workspace.
Stop details holds its number, abbreviation and other fields; Modes and Operator show connected
records. The heading shows its ID and version.*
```


New:

```markdown
*Above: Chur Wiesental is a Stop in the Network application of the Graubünden workspace.
Stop details holds its number, abbreviation and other fields; Modes and Operator show connected
records. This earlier view shows the ID and version directly in the heading; open **Details**
in the current header to see them.*
```


Old:

```markdown
A **parent** gives a record its place in a hierarchy. Some types can stand at the top; others
need a parent of an allowed type. The path on a record's page shows its ancestors. A parent is
more than an ordinary connection: changing it moves the record in the hierarchy and keeps the
parent connection consistent. An invalid parent or a move that creates a cycle is refused.
```


New:

```markdown
A **parent** gives a record its place in a hierarchy. Some types can stand at the top; others
need a parent of an allowed type. The line above a record’s title starts with **←** and the list’s name when you opened it from
a list, followed by its ancestors where the model shows them. Choose the list’s name to return. A parent is
more than an ordinary connection: changing it moves the record in the hierarchy and keeps the
parent connection consistent. An invalid parent or a move that creates a cycle is refused.
```


Old:

```markdown
The version beside a record's heading protects it from being overwritten by an older edit.
When you save, refiroo checks the version you read. If someone else saved a change first, your
save is refused, even if you changed a different field on the same record. Their saved change
remains in place.
```


New:

```markdown
The version under **Details** in a record’s header protects it from being overwritten by an older edit.
When you save, refiroo checks the version you read. If someone else saved a change first, your
save is refused, even if you changed a different field on the same record. Their saved change
remains in place.
```


Old:

```markdown
The header's title and subtitle edit the same way. An empty subtitle offers **Add**.
The header also has the record's ID with a copy button. Use **Edit record** in the **⋯** menu
for the form containing all fields. A new record form saves its fields, allowed parent and
required relationships together: complete all required choices before choosing **Create**.
A refusal leaves the invalid record uncreated; correct the named field or connection.
```


New:

```markdown
The header's title and subtitle edit the same way. An empty subtitle offers **Add**.
Open **Details** in the header for the record’s ID, its copy button and version.
**Copy ID** is also in the record’s **⋯** menu. Use **Edit record** in the **⋯** menu
for the form containing all fields. A new record form saves its fields, allowed parent and
required relationships together: complete all required choices before choosing **Create**.
A refusal leaves the invalid record uncreated; correct the named field or connection.
```


Old:

```markdown
A Contributor sees **Propose a change** on a record and **Propose a new …** on a collection.
The first use asks for a change-set name, then opens your proposal for editing. Later uses
continue your newest change set. The band names it and its change count and says who publishes.
A Reader's band says **You can read this workspace** and whom to ask. With narrowed write
permissions, controls appear only on the allowed record types and the band names those types.
```


New:

```markdown
A Contributor sees **Propose a change** on a record and **Propose a new …** on a collection.
The first use asks for a change-set name, then opens your proposal for editing. Later uses
continue your newest change set. The band names it, its change count and state. Open **Details**
for who started it, when, its version and model.
A Reader's band says **You can read this workspace** and whom to ask. With narrowed write
permissions, controls appear only on the allowed record types and the Live band names those types.
```


## Screenshots with the outdated frame

All 289 referenced screenshots retain the earlier top bar and/or Settings navigation, data band, record trail or header. The six contact sheets in this notes directory were visually inspected for the frame; this is not a new browser acceptance run. Dialog captures also include the earlier frame in their backgrounds. The screenshot files and every screenshot reference were left unchanged.

For replacement captures, retain each page’s existing screen and data state, with the current frame visible: workspace-wide search and folded Browse records on application pages; one context row and Details in a change set; the list/ancestor trail and Details on records; task groups and the workspace return link in Settings; one-line roles on Home.


- `admin-about.png`

- `admin-account-sessions.png`

- `admin-agent-access-enabled.png`

- `admin-agent-access.png`

- `admin-agent-block.png`

- `admin-agent-calls.png`

- `admin-agent-new-client.png`

- `admin-agent-register.png`

- `admin-ai-calls.png`

- `admin-ai-settings.png`

- `admin-ai-test-answered.png`

- `admin-ai-test-failed.png`

- `admin-api-reference.png`

- `admin-approval.png`

- `admin-audit-person.png`

- `admin-client-inactive-rotate.png`

- `admin-client-new.png`

- `admin-client-rotate.png`

- `admin-client.png`

- `admin-clients.png`

- `admin-consumer-apis.png`

- `admin-grant-consumer-api.png`

- `admin-grant-dialog.png`

- `admin-grant-narrowed.png`

- `admin-grants-person.png`

- `admin-grants-workspace.png`

- `admin-group-members.png`

- `admin-group-new.png`

- `admin-groups.png`

- `admin-local-signin-off.png`

- `admin-mail-microsoft365-entra.png`

- `admin-mail-microsoft365-menu.png`

- `admin-mail-microsoft365-secret.png`

- `admin-mail-settings.png`

- `admin-people.png`

- `admin-person-admin.png`

- `admin-person-link-provider.png`

- `admin-person-reset-password.png`

- `admin-person-rita.png`

- `admin-person-second-factor.png`

- `admin-role-new.png`

- `admin-roles.png`

- `admin-signin-local.png`

- `admin-signin-provider-new.png`

- `admin-signin-provider.png`

- `admin-signin.png`

- `admin-signing-keys-retire.png`

- `admin-signing-keys.png`

- `admin-webhook-deliveries.png`

- `admin-webhook-new.png`

- `admin-webhook-resume.png`

- `admin-webhook-rotate.png`

- `admin-webhook-workspace-events.png`

- `app-navigation-matrix-entry.png`

- `app-network.png`

- `app-systems.png`

- `appr-activity.png`

- `appr-approve.png`

- `appr-approved-notice.png`

- `appr-decision-panel.png`

- `appr-home-waiting.png`

- `appr-inbox-notice.png`

- `appr-own-approval.png`

- `appr-publication.png`

- `appr-resubmit.png`

- `appr-send-back-reason.png`

- `appr-sent-back-notice.png`

- `appr-sent-back.png`

- `appr-submitted.png`

- `bulk-delete-impact.png`

- `change-set-open.png`

- `change-set-publish-confirm.png`

- `change-set-review.png`

- `change-sets-list.png`

- `contributor-propose-change.png`

- `export-for-people.png`

- `hierarchy-restructure-plan.png`

- `home.png`

- `import-profile-next-version.png`

- `integrate-agent-access-connect.png`

- `jobs-list.png`

- `list-filter-pills.png`

- `list-position-and-seek.png`

- `mapping-grid-map-dialog.png`

- `matrix-cell-editor.png`

- `matrix-cell-relationship-table-editor.png`

- `matrix-filter-panel.png`

- `matrix-missing-name-add.png`

- `matrix-missing-name-cell.png`

- `matrix-missing-name.png`

- `matrix-municipalities-by-system.png`

- `matrix-operator-names.png`

- `model-account-before-request.png`

- `model-account-facts.png`

- `model-account-provider-failure.png`

- `model-add-mapping-grid.png`

- `model-add-panel-relationship.png`

- `model-add-relationships-table-layout.png`

- `model-add-tree-view.png`

- `model-application-groups.png`

- `model-application-panel.png`

- `model-apply-migration.png`

- `model-assistant-change-dialog.png`

- `model-assistant-partial-move.png`

- `model-assistant-whole-type-move.png`

- `model-assistant-workbook-loaded.png`

- `model-assistant-workbook-proposal.png`

- `model-attribute-attach-existing.png`

- `model-attribute-list-type-dialog.png`

- `model-attribute-menu.png`

- `model-attribute-settings.png`

- `model-conflict-editor.png`

- `model-consumer-active-documents.png`

- `model-consumer-add-dialog.png`

- `model-consumer-add-field.png`

- `model-consumer-add-filter.png`

- `model-consumer-earlier-versions.png`

- `model-consumer-include.png`

- `model-consumer-parent-fields.png`

- `model-consumer-relationship-field-picker.png`

- `model-consumer-tab-example.png`

- `model-consumer-tab-fields.png`

- `model-consumer-tab-filters.png`

- `model-consumer-tab-schema.png`

- `model-consumer-tab-types.png`

- `model-delete-mapping.png`

- `model-draft-json.png`

- `model-draft-new-dialog.png`

- `model-drafts.png`

- `model-editor-application.png`

- `model-editor-overview.png`

- `model-editor-systems-views.png`

- `model-field-added.png`

- `model-field-dialog.png`

- `model-group-add-entries-dialog.png`

- `model-group-menu.png`

- `model-header-breadcrumbs.png`

- `model-hierarchy-dialog.png`

- `model-history-undo-dependants.png`

- `model-history-undone.png`

- `model-history.png`

- `model-install-dialog.png`

- `model-install-key-change.png`

- `model-install-migration.png`

- `model-issues-error.png`

- `model-issues-none.png`

- `model-json-newer-version.png`

- `model-json-syntax-error.png`

- `model-json-workbench-actions.png`

- `model-language-raise-review.png`

- `model-layout-panel-menu.png`

- `model-layout-record.png`

- `model-layout-sort-dialog.png`

- `model-layout-table-tab.png`

- `model-list.png`

- `model-mapping-dry-run.png`

- `model-mapping-evidence.png`

- `model-mapping-proposed.png`

- `model-mapping-selection-dialog.png`

- `model-mapping-why.png`

- `model-matrix-pair.png`

- `model-matrix-view-dialog.png`

- `model-matrix.png`

- `model-migration-created.png`

- `model-migration-loss-confirm.png`

- `model-migration-loss.png`

- `model-migration-proposed.png`

- `model-migration-review.png`

- `model-migration-stale.png`

- `model-more-actions.png`

- `model-move-needs-migration.png`

- `model-moves-list.png`

- `model-moves-new-dialog.png`

- `model-navigation-group-panel.png`

- `model-overview.png`

- `model-panel-columns-where-it-sits.png`

- `model-panel-settings.png`

- `model-relation-added.png`

- `model-relation-carries.png`

- `model-relation-dialog.png`

- `model-relations.png`

- `model-release-activate-dialog.png`

- `model-release-compare.png`

- `model-release-detail.png`

- `model-releases.png`

- `model-stop-page-relationship-panels.png`

- `model-structure.png`

- `model-table-columns-related-fields.png`

- `model-table-menu-size.png`

- `model-type-change-key-dialog.png`

- `model-type-fields.png`

- `model-type-merge-dialog.png`

- `model-type-move-to-dialog.png`

- `model-type-preview.png`

- `model-type-remove-confirm.png`

- `model-type-rename-dialog.png`

- `model-type-required-edit.png`

- `model-type-settings.png`

- `model-type-split-dialog.png`

- `model-view-matrix-dialog.png`

- `model-workbook-list-range.png`

- `model-workbook-map-column.png`

- `model-workbook-value-map.png`

- `model-workspace-apply-dialog.png`

- `model-workspace-edit-model.png`

- `model-workspace-model.png`

- `model-workspace-other-model.png`

- `model-workspaces-list.png`

- `moves-set-default.png`

- `new-record-required-connections.png`

- `record-delete-impact.png`

- `relationship-delete-confirm.png`

- `relationship-picker-mode.png`

- `relationship-picker-operator.png`

- `relationships-grid-change-preview.png`

- `relationships-stop.png`

- `release-retire-dialog.png`

- `release-technical-details.png`

- `replace-related-records.png`

- `run-ai-provider-calls.png`

- `run-ai-settings.png`

- `run-backup-rehearsal.png`

- `run-deployment.png`

- `run-jobs.png`

- `run-operations.png`

- `save-conflict.png`

- `settings-notifications.png`

- `stop-add-translation.png`

- `stop-details.png`

- `stop-edit-field.png`

- `stop-edit-record.png`

- `stop-history.png`

- `stop-relationships.png`

- `stops-filter-menu.png`

- `stops-filtered-sorted.png`

- `stops-search-chur.png`

- `tree-geography-chur.png`

- `tree-modes.png`

- `tree-move-dialog.png`

- `use-appearance-themes.png`

- `use-approval-policy.png`

- `use-ask-filters.png`

- `use-assistant-loaded.png`

- `use-assistant-proposal.png`

- `use-assistant-reload.png`

- `use-assistant-stopped.png`

- `use-assistant-words.png`

- `use-assistant-workbook.png`

- `use-history-activity.png`

- `use-history-assistant.png`

- `use-history-changes.png`

- `use-history-explained.png`

- `use-history-stop-changed.png`

- `use-import-file-delete-confirm.png`

- `use-inbox-panel.png`

- `use-mapping-proposal-result.png`

- `use-move-review-change-sets.png`

- `use-notification-email-digest-settings.png`

- `use-notification-job.png`

- `use-notifications-page.png`

- `use-pub-list.png`

- `use-pub-snapshot.png`

- `use-record-history-explained.png`

- `use-wb-delete-draft.png`

- `use-wb-dialog.png`

- `use-wb-draft-menu.png`

- `use-wb-dry-refused.png`

- `use-wb-dry-run-names.png`

- `use-wb-dry-run.png`

- `use-wb-editor.png`

- `use-wb-evidence.png`

- `use-wb-history.png`

- `use-wb-issues.png`

- `use-wb-model-list.png`

- `use-wb-source-namen.png`

- `use-workspace-default.png`

- `use-workspaces-detail.png`

- `use-workspaces-manage.png`

- `wbload-dialog.png`

- `wbload-finished.png`

- `wbload-records.png`

- `wbload-review.png`

- `wbload-running.png`

- `workbook-columns-per-parent.png`

- `workspace-cannot-open.png`

- `workspace-retire-dialog.png`

- `workspace-switcher.png`

- `workspaces-home.png`

- `workspaces-new-dialog.png`


## Facts checked against code, exceptions and limits

- Fact 1 describes search groups as lists. `WorkspaceSearch.tsx`, `groupByType`, groups by record type and uses its plural name; a view-defined list is not the grouping key. The guide says record type. Paths show the application and ancestors.
- Fact 6 says there is no separate Back to list button. This holds on a loaded record page. `ObjectDetail.tsx` retains that button in the **Object unavailable** error state, so the recovery instruction in `use/records.md` remains correct.
- The comparison page is **Changes in this change set** and its return action is **See the data with these changes**. **Review changes** remains the button in the change-set band and in publication confirmation; those button instructions were retained.
- Workspace-wide search opens a detail route without a change-set or publication identifier (`TopBar.tsx` and `WorkspacePage.tsx`), so it opens Live. The new search instructions explain this. Collection search is the way to keep a snapshot context.
- The full tree view still has **Find a record** (`TreeView.tsx`); the sidebar tree does not (`Explorer.tsx`). The tree-view guide remains unchanged.
- The model preview retains its own application chooser in a band (`TypePreview.tsx`). Its preview instruction remains unchanged. This is separate from the application’s data-context band.
- `SettingsLayout.tsx` accepts an optional trail; the Settings index has a header without one. The guide describes the workspace return link without asserting that every Settings page has a trail.
- **Breadcrumbs start with the application** is no longer offered in the model editor (`layout.ts`). The stored compatibility setting remains but draws nothing. Both affected editor explanations were corrected.
- iOS **Settings › General › About › Certificate Trust Settings** in `run/developer-instance.md` is an operating-system path, not a refiroo Settings path; it remains unchanged. GitHub repository Settings and literal command output were likewise retained.
- No unrelated product defect was investigated or changed. No live reference-instance browser journey was run; existing screenshot review and source inspection establish only the documentation corrections. A contact-sheet attempt through Chrome was refused by the local execution environment; the inspected sheets were then generated locally with AppKit without changing source screenshots.

## Validation

- `GUIDE_OUT=_build/SH1-GUIDE npm run build` in `guide/`: passes; final run recorded in `build-final.log`.
- The build reports a `/404` route conflict warning. It still exits successfully; no route configuration was changed in this wave.
- `git diff --check -- guide/src/content/docs`: passes.
- All 218 assigned pages retain their front matter and section headings. Every screenshot URL and its order are identical to the pre-edit snapshot.
- No code, test, screenshot, other wave file, or application configuration was edited; no commit or state-changing git command was run.
