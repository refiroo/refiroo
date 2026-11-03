---
title: Mail
description: Set up outgoing mail, understand delivery states and help people receive account links and notices.
reader: access-admin
---

Use **Settings › Integration › Mail** to connect refiroo to your organisation’s mail server. You need **Security administration** for the whole instance. Mail carries password links and, when people choose them, inbox notices and digests. It never sends a password or an authenticator code.

Without a saved server, nothing is sent. Administrators can still copy a new person’s password link and pass it on. Follow [Set up mail](/docs/guide/administer/set-up-mail/) to configure and test delivery.

## Mail server

**Server** and **Port** identify the outgoing mail service. **Connection** offers:

| Choice | When to use it |
| --- | --- |
| STARTTLS (usually port 587) | The server upgrades the connection to encryption before login. |
| TLS (usually port 465) | The connection is encrypted from the start. |
| None: not encrypted (a relay on a trusted network) | Only for a relay that requires no login. |

Both encrypted choices verify the server’s certificate and name. refiroo refuses to send a login without encryption. If the certificate is not trusted, ask the operator to install the organisation’s trusted certificate authority; do not switch off encryption to bypass the failure.

Leave **User name** empty for a relay without login. Otherwise supply **Password**. The saved password is kept sealed and never displayed again. Leave it blank to keep it on an unchanged server; enter it again when changing the server or port. The operator handles changes to the server’s secret storage; see [Configure refiroo](/docs/run/configure/).

**From address** is the sender. **Application address** is where links in messages lead. Empty uses the default address displayed below the field. Check that people receiving mail can reach it. Changes to mail settings are recorded as security events.

![Mail server form before configuration, with Test message unavailable](/docs/screens/admin-mail-settings.png)

## Test a saved configuration

**Send test message** uses the saved settings immediately and includes the address links point to. **Sent** means the server accepted the message, not that it reached the inbox. Check the mailbox and junk folder too.

The failure heading distinguishes an unreachable server, a failed secure connection, a refused login, a refused recipient or sender, and a rejected message. Use that reason with the mail administrator to correct the relevant setting, save and test again.

## Messages and retries

Ordinary messages wait in an outbox and are sent in the background. Under **Messages**, filter **State** to **All**, **Waiting**, **Sent** or **Failed**. Counts show each state. **Refresh** reads the current list; **Load more messages** reads older entries. Columns show **To**, **Message**, **State**, **Tries**, **Last problem**, **Queued** and **Actions**. A waiting row also shows **Next try**; finished rows show their finish time.

| State | Meaning and next step |
| --- | --- |
| Waiting | Not yet sent, or waiting to retry. Check the next try and last problem. |
| Sent | Accepted by the mail server. Ask the recipient to check their mailbox. |
| Failed | Delivery stopped. Correct the cause and make a fresh password link if needed. |

A temporary failure retries after 30 seconds, then doubles the wait up to one hour. A permanently refused recipient fails immediately. Other messages give up after 24 hours. Finished entries are kept for 30 days. Waiting message text is sealed, never shown in this list, and erased after sending or failure.

**Stop sending** is available for waiting messages. Confirm **Stop sending**, or choose **Keep trying**. Stopping marks the message failed and erases its text. It does not invalidate the link already made; make a new password link to replace that link. If sending finished before your action arrived, the list refreshes to its final state.

With a state selected and no matching messages, the list says **No message is in this state.** With **All** selected and no messages yet, it explains that new-person links and password resets appear here when sent.

**Remove settings…** asks **Remove the mail settings?** Choose **Remove them** to stop sending and delete the saved password. Waiting messages remain and fail after their 24-hour window unless settings are saved again in time. **Cancel** in the form discards unsaved edits.

## Password links

With mail set up and an e-mail address on the person, **New person** and **Reset password** also mail the link. The administrator still sees it once for copying. Read whether it was mailed; queued delivery can fail later. Follow [Add a person](/docs/guide/administer/add-a-person/).

The sign-in page offers **Forgotten your password?** when mail is configured. People enter **Username or e-mail address** and choose **Mail me a link**. The answer is the same whether or not an account matches, and repeated requests are slowed. The one-use link opens **Choose a new password**; using it ends all sessions. An existing second factor remains required. An expired or already used link needs a fresh request.

## Notices and digests

Each person controls their own delivery under **Settings › General › Notification email › Email**. **Email me when something arrives in my inbox** uses the address shown there. Without an e-mail address, or for a client, the page explains there is nothing to choose. Administrators do not choose these preferences for others.

Under **How each kind reaches me**, a person chooses **At once**, **Digest**, or **Off** for each kind. Immediate notices are plain text, sent once while under 24 hours old, and contain no record or change-set content. Turning mail on does not send a backlog of old notices.

Choosing Digest for the first kind starts a daily digest in the browser’s time zone. **The digest** offers its frequency and shows the zone and **Next digest**. Digests arrive at 07:00 daily or on Mondays; there is no mail when nothing unread remains, and notices already read are left out. **Workspaces I follow** lists followed workspaces with **Stop following**. Following is chosen from a workspace. See [Inbox and approvals](/docs/use/inbox-and-approvals/) for the person’s notices and tasks.

After downtime, only one digest is sent, rather than one for each missed morning. Without saved
mail settings, the due time waits until mail is set up. Daylight-saving changes preserve 07:00 in
the person's saved time zone; it is not the engine server's clock zone.
