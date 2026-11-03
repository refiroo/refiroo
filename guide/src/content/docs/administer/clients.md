---
title: Clients for other systems
description: Give a system its own identity, grant its access and manage its secrets.
reader: access-admin
---

A **client** is the identity of a system that calls refiroo without a person signing in.
Use one for an unattended import, a data consumer, a monitoring system or another integration.
Its work carries its own name in history. People using the browser sign in as themselves.

You need **Security administration** to manage **Settings › Security › Clients**.
Use **Search clients** (**Name**) to search the list, which separates **Active** and **Deactivated** clients and shows
when a client last authenticated, or **No token yet** when it has not.

![Clients catalogue with one active client and no selection](/docs/screens/admin-clients.png)

*Above: Stops reader (guide) is the reference instance's client for reading stop data.*

## Identity and access

A client has a stable **Client ID**, a display name and a secret. **Rename…** changes the name
without changing its ID or requiring the system to be reconfigured. The dialog explains **The client ID does not change, so the system using it needs nothing new.** Choose **Save** to keep the new name. **New client** asks for **Name**. **Create and show its secret** opens **Copy the client's secret**. Store the ID and secret securely before **I have copied it**; the secret is shown once. A new client starts
with no access. Follow [Create a client](/docs/guide/administer/create-a-client/) to create
it, save its one-time secret and grant what it needs.

![Client detail with ID, secrets and a workspace consumer grant](/docs/screens/admin-client.png)

*Above: Stops reader (guide) has a Consumer API grant in Graubünden. The webhooks section
shows a load error on this capture; it does not show that the client has no webhooks.*

A **Role** grant permits management operations, using the same roles and write restrictions
as people. A **Consumer API** grant permits reading one declared API in one workspace.
Both kinds can be needed. A role alone, even Security administrator, does not grant consumer
data access. Consumer grants must be made separately for each API and workspace.

The **Access** table shows where each grant applies and any write restriction. **Grant**
opens the access dialog. **Remove** takes away that grant; any other applicable grants
continue. If the model removes a granted consumer API, the stale grant no longer permits
access. Replace it with a grant for the intended current API.

Follow [Grant a consumer API to a client](/docs/guide/administer/grant-a-consumer-api-to-a-client/) for the grid and its partial-success handling. Give the integration team the ID, secret and agreed access. The
[integration authentication guide](/docs/integrate/signing-in-and-tokens/) describes how their system signs in
and uses the granted interfaces.

## Secrets and rotation

The full secret is shown only when created. Copy it before closing the dialog; the client
page later identifies it by its last four characters. The **Secrets** table shows **Secret**, **Created**,
**Valid until** and **Last used**. **No end** means no expiry is currently set; **Not yet**
means the secret has not been used.

**Rotate secret…** opens **Rotate the secret of …**. **Make a new secret** makes the replacement with a chosen overlap: **1 hour**, **24 hours**,
**7 days**, or **Stop it now**. During an overlap the system can switch without interruption;
after it, the previous secret no longer works. **End now** in the Secrets table ends a
previous secret's overlap early. Its accessible label, **End the secret ending … now**, identifies the last four characters; it acts immediately. **No valid secret: rotate to make one.** means there is no usable secret left. Use the recorded ending and last-use times to check the handover.
Follow [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/).

## Ending access and tracing work

**Deactivate** asks for confirmation. The client cannot authenticate again and its existing
access is refused at the next request. Its grants and name remain for history. It is never
deleted. Use **Restore** from the Deactivated list to reactivate it after reviewing those grants.

**See changes** opens its data changes in workspaces you may read. **Recent activity**
shows security events; **Webhooks it created** lists subscriptions you administer.
A failed section offers **Retry**. Treat a load failure as unavailable information, not an empty list.
See [Who changed what](/docs/administer/audit/) for the distinction between data and security history.

Consumer API grants are for clients only. People use their browser roles to read records;
there is no corresponding grant to a person. In the Grant dialog, choose the consumer APIs
and workspaces in the grid, check the existing grants and confirm the intended additions.
The available APIs come from each workspace's own model.

The client’s header identifies who created it. **Webhooks it created** lists **Webhook**, **Workspace**, **Consumer API** and **State** for someone who also administers those subscriptions; it is not a grant of webhook management. Follow a webhook to its [configuration and deliveries](/docs/administer/webhooks/).

**Recent activity** has **All**, **Signing in**, **Roles and groups** and **Account** filters, grouped by day. It starts with ten entries, then loads twenty more, with **Show fewer** to shorten the list. Its security events contain no secret. Data changes remain in **See changes**, limited to workspaces the viewer may read.

Rotation and ending an old secret stop that secret being used for a new sign-in. They do not themselves cancel access already issued. For immediate refusal of an unsafe client’s requests, **Deactivate** is the relevant action. Check retained grants before **Restore**, which acts immediately. Clients are deactivated and restored rather than deleted.

## Clients for assistants

Create an external assistant's client with **New agent client** under **Settings › Security › Agent access**. Its grants are restricted to reading and preparing changes through that connection; it cannot approve, publish or write live data. It is distinct from an ordinary integration client. Follow [Manage an assistant's access](/docs/guide/administer/manage-agent-access/).

The built-in assistant instead has a dedicated client for each task, managed by refiroo and omitted from the normal client list. You do not create a secret for that session client. See [AI settings and access](/docs/administer/ai/) for its permissions, costs and retention.
