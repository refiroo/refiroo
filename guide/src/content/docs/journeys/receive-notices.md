---
title: Receive notices
description: Connect outgoing mail setup with personal email choices, digests and workspace following.
reader: steward
---

Use these journeys to hear about work that needs attention without continually opening each
proposal or job. Administrators provide outgoing mail; each person chooses email for their own
inbox. Inbox notices and workspace following also work without mail. These features do not require
an assistant or AI configuration.

## Send mail

A security administrator connects the instance to an outgoing mail server so people can receive
account links and the notices they choose. Start with [Mail](/docs/administer/mail/), then
[set up mail](/docs/guide/administer/set-up-mail/) and send a test message. Check that it reaches
the intended mailbox and that its application link points to the address people can open.
The server accepting a message does not prove it reached the inbox.

Ordinary messages wait for background delivery. Inspect waiting, sent and failed entries on the
Mail page; temporary failures retry, while permanent failures or exhausted retries need attention.
The reason distinguishes connection, secure connection, login and recipient problems. Correct the
cause with the mail administrator or operator. [Sign-in and mail setup](/docs/run/sign-in-and-mail-setup/)
explains the operator's part. Removing settings stops sending but does not immediately erase the
waiting queue. Stopping an individual message does not revoke a password link already created.

For a person receiving a new-account or reset link, follow it once to set a password and then sign
in. An expired or used link needs a fresh one; an existing second factor remains required.
Read [Account](/docs/use/account/) for personal sign-in security. For optional inbox email,
continue with the next journey.

## Notification digests and following a workspace

A person starts with [Inbox and approvals](/docs/use/inbox-and-approvals/) to understand the
notices and the work they open. Then read [Notification settings](/docs/use/notifications-settings/)
and [set up email notices](/docs/guide/use/set-up-email-notices/). Email starts off. Where mail
is configured and the account has an address, enable it and choose **At once**, **Digest** or
**Off** for each kind. These preferences do not remove notices from the inbox.

A digest can come every morning or on Mondays at 07:00 in the browser's time zone. Check the
saved zone and next digest time. It counts eligible unread, unhandled notices and lists the newest
50 with links; an empty digest is not sent. Reading or handling a notice before delivery can remove
it from the message. The email contains kinds, times, counts and links rather than record, workspace,
file or people's names. Digest notices do not use immediate mail's 24-hour cutoff.

To hear about another person's publication, [follow a workspace](/docs/guide/use/follow-a-workspace/)
from its Home card. Following needs Browse and adds inbox notices; email copies depend on your
choices above. Your own publications do not send you follower notices. Open a notice to inspect
its publication where it is still available and you still have access. The notice can remain after
its destination is no longer openable.

Stop following from Home or notification settings when no longer needed. Losing Browse or account
deactivation pauses notices while keeping the choice, so they can resume if access returns.
If email does not arrive, check the inbox, address, mail availability and saved choices before
assuming publication or approval failed. A refused settings change keeps the previous preferences.
