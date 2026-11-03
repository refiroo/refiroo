---
title: Manage an assistant's access
description: Connect an assistant, create an agent client, register or block an assistant and review its calls.
reader: access-admin
---

Use **Settings › Security › Agent access** with **Security administration** across the instance. Read [Agent access](/docs/administer/agent-access/) first for permissions, data sent, call retention and the limits on prepared changes. External assistants may send permitted data to their own provider and incur charges there; refiroo's built-in AI send levels do not control them.

## Connect a person's assistant

1. Open **Settings › Security › Agent access**. If it says **Agent access is off**, ask the operator to enable it and restart the server. The page cannot switch it on.
2. Under **How to connect**, copy **Address** and give it to the person connecting their MCP assistant. Use the address shown rather than constructing one from the browser's current page.
3. Ask the person to add that address in their assistant. It opens this instance's sign-in page, naming the assistant and where it returns. They should check those details before signing in. The name is what the assistant says about itself.
4. After sign-in, the assistant uses the person's existing grants, limited to reading and preparing changes. It does not need a new Agent role. Under **Assistants people sign in with**, check its **Returns to**, **Signed in now** and **Last used**.

If sign-in cannot register the assistant, use the registration steps below or ask the operator to check the allowed return hosts. If it connects but has no useful tools, review the person's workspace grants. **Browse** allows reads; **Work in change sets** allows preparation. Neither gives publication through the assistant.

A person stops their own connection under **Settings › Account**, in **Where you’re signed in**. The session name includes **(assistant)**. **Sign out** on that session ends its access. For all users of one assistant, block it below.

## Create a client for a system's assistant

1. On **Agent access**, under **Agent clients**, choose **New agent client**. This is different from **New client** on the ordinary Clients page.
2. Enter **Name**, then choose **Create and show its secret**. The dialog **Copy the client's secret** shows **Client ID** and the secret once. Give these to the responsible integrator through your organisation's secure handover method. Choose **I have copied it** only after keeping what they need; the secret cannot be shown again.
3. Open the new client's name under **Agent clients**. Its normal client detail page opens. In **Access**, use **Grant access** to grant only the required role and workspaces. The **Agent** role gives Browse and Work in change sets; a custom role can provide a smaller set. A consumer API grant alone allows only that API's lookup tool and information about the connection's access.
4. Ask the integrator to configure the system's assistant with this client and the copied connection address. The [integration instructions](/docs/integrate/assistants-and-agents/) explain the connection details.
5. Return to **Agent access**. Check **Access**, **Last used** and **Calls, 30 days** on its row, then inspect **Calls** for the result. A new client has no access until you grant it.

![New agent client dialog with its Name field and creation action](/docs/screens/admin-agent-new-client.png)

For a lost secret, use [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/). To stop a system's assistant, open its client and choose **Deactivate**, then confirm. Its next request is refused. Restoring a client does not widen its grants.

## Register an assistant for people

Use this when self-registration is off or its return host is not allowed. Registration does not give the assistant its own workspace access: each person still signs in and works through their own grants.

1. Under **Assistants people sign in with**, choose **Register an assistant**.
2. Enter **Name**, the name people see on the sign-in page. Under **Return addresses**, enter the exact addresses supplied by the assistant's administrator, one per line. They must use HTTPS, or HTTP loopback addresses on the same computer. Enter at most ten addresses, each at most 2,000 characters, without a fragment.
3. Choose **Register**. The assistant appears in the list and people can sign in with it. If **The assistant was not registered** appears, correct the reported problem and try again.

![Register an assistant dialog showing Name and Return addresses](/docs/screens/admin-agent-register.png)

## Block or restore an assistant

1. Find it under **Assistants people sign in with**. Check the name and **Returns to** so you block the intended one.
2. Choose **Block**. The confirmation names the assistant and how many sessions end. Confirm with **Block**.
3. The row shows **Blocked**. No one can sign in with it, and existing sessions end on their next call.
4. To allow it again, choose **Restore**. People can sign in again; ended sessions stay ended.

![Confirmation to block an assistant with its affected session count](/docs/screens/admin-agent-block.png)

Use client deactivation for a system's assistant, and account sign-out for one person's session. Blocking an assistant registration affects all people signed in through that registration.

## Investigate a call

Read **Calls**, newest first. **Who** is the person or client; **Through** identifies the assistant or says **Its own client**. **Tool** is the operation it asked for and **Arguments** lists names only, never values. **Outcome** says **Answered**, **Refused**, **Limit reached** or **Failed**. Choose **Load more** for older calls.

For **Refused**, inspect the caller's grants and the work it requested. An assistant cannot reach a colleague's change set or approve or publish, even when its person can. A submitted change set is frozen to it; a person must deal with the review. For **Limit reached**, allow the wait requested by the service before another attempt. For **Failed**, ask the integrator or operator to investigate the reported failure; the call list does not contain the assistant's conversation.

Calls normally remain for 90 days. The client row's 30-day count is a reporting window. Check actual data changes in [the audit and history](/docs/administer/audit/), and review prepared changes through [the normal approval process](/docs/administer/approval-policies/).
