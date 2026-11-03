---
title: Help someone who lost a device
description: Restore sign-in after a lost authenticator or passkey device and end unsafe sessions.
reader: access-admin
---

You need **Security administration** to change another person's sign-in methods.
Confirm the person's identity through your organisation's recovery process before removing
protection. A password reset alone does not bypass a second factor. See
[Sign-in and second factors](/docs/administer/sign-in/) for how the methods work.

## Check the remaining ways in

1. Ask whether they have another registered passkey, a working authenticator app or a saved
   recovery code. On the sign-in screen, **Use a recovery code instead** lets an app user
   use one of their unused codes.
2. If they can sign in, have them open **Account** to replace the lost method and manage
   their sessions. A person with only passkeys has no app recovery codes; another passkey
   may still work. See [Your account](/docs/use/account/).
3. If they use the organisation's provider, recover the provider's factor there. Removing
   a refiroo authenticator does not reset a factor managed by the provider.

## Remove a lost local authenticator

1. Open **Settings › Security › People**, search for the person and select them.
   Check their name, username and sign-in method.
2. Under **Sign-in**, choose **Remove second factor…** beside
   **Second factor: authenticator app**. This button appears only when an app is set up.
3. Read the confirmation, then choose **Remove second factor**. Their app and its recovery
   codes stop working. **Cancel** leaves the factor in place. The change is recorded in activity.
4. If a second factor is required, they set up a new app at their next password sign-in
   before a session starts. Otherwise, ask them to set it up again on **Account** and save new recovery codes.

## Remove a lost passkey

1. On the same person's page, find the named passkey under **Sign-in**. Compare its added
   and last-used times with the person to identify the lost device's registration.
2. Choose **Remove passkey…** for that entry. Check the name in the confirmation and choose
   **Remove passkey**. That registration can no longer sign them in; other passkeys remain.
3. Have them use another available sign-in method and register a replacement on Account.
   If they also lost their password, use the password procedure below. An app still set up
   remains a required step; remove a lost app separately if necessary.

![Person's page with password status and account recovery actions](/docs/screens/admin-person-admin.png)

*Above: Guide Admin has a password but no authenticator app or passkey configured in this
capture, so the removal buttons described above are absent.*

## Reset a forgotten password and end sessions

1. With the intended person still selected, choose **Reset password** if they need a new
   local password. It makes a link at once; there is no confirmation first.
2. Copy and pass on the link in **Pass on the password link** before choosing **I have copied it**.
   If available, use **Mail it to …** and check the sent-to message. A newer link replaces
   the previous one; give them the newest link. Read its expiry.
3. Have them open it and set a new password. Using it ends their refiroo sessions everywhere.
   A configured second factor remains in force. If the link expired or was used, make another.
4. If the lost device may still hold a signed-in session, choose **Sign out everywhere**
   on the person's page and confirm. Every refiroo session ends at its next request.
   They can sign in again with their remaining or replacement methods. This does not sign
   other browsers out of the organisation's provider.

![Password-link dialog with one-time link and expiry](/docs/screens/admin-person-reset-password.png)

*Above: fictional Rita Approver's reset dialog. The captured link was not used.*

If an action fails, read the message and reload the person's page to check its state before
retrying. If no administrator can sign in, ask the operator to use the
[server recovery procedure](/docs/run/sign-in-and-mail-setup/).
Do not turn off the requirement merely because one person needs a replacement factor.
