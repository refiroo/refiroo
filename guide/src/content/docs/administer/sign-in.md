---
title: Sign-in and second factors
description: Choose local or provider sign-in, require a second factor and understand browser sessions.
reader: access-admin
---

Open **Settings › Security › Sign-in** to choose how people prove who they are.
You need **Security administration**. Sign-in establishes identity; [roles and grants](/docs/administer/roles-and-grants/)
decide what that identity may do afterwards.

![Sign-in catalogue with Local accounts on and no providers](/docs/screens/admin-signin.png)

*Above: local accounts are on and no organisation provider is configured in the reference instance.*

## Local accounts

With **Local accounts** on, people can use their refiroo username and password.
They manage their password, passkeys and authenticator app on their own
[Account](/docs/use/account/) page. Passwords normally need 15–128 characters. The operator can change the minimum. A password equal to the username or a common password is refused with a reason.
Repeated failed sign-ins are delayed, rather than permanently locking the account;
the sign-in screen says how long to wait. Slowdown starts after five failed attempts for an account or twenty from an address. Waits double up to fifteen minutes; repeatedly retrying does not bypass them.

**Keeps local sign-in** on a person's page lets them retain this route when local sign-in
is off for everyone else. They use **Sign in with a local administrator account** on the
sign-in page. Keep a working recovery administrator before changing organisation sign-in.
Clients are unaffected by turning local sign-in off.

**Turn off…** is offered only after an enabled provider has successfully signed someone in.
Read and confirm the warning. People without the retained local route then use a provider.
**Turn on** restores local sign-in. The last active person keeping local sign-in cannot be
deactivated or lose it while local sign-in is off.

## The organisation's provider

A provider uses OpenID Connect and brings its own multi-factor sign-in. refiroo still
starts its own session. People are matched by their provider identity, never by e-mail alone.
See [People and groups](/docs/administer/people-and-groups/) for linking an existing person
and for provider-controlled membership.

To add a provider in the browser:

1. Choose **New provider**. Enter **Name on the sign-in button**; the button reads
   “Continue with” followed by that name. Enter a **Key**, which cannot change once saved.
2. With your organisation's sign-in administrator, enter **Issuer**, **Client ID** and
   **Client secret** from its application registration. The issuer must match exactly.
   The secret is saved securely and is never shown again. Changing an unused issuer requires the secret again; a secret is not silently carried to a different provider endpoint.
3. Set **Groups claim** only if the provider supplies group memberships. Empty means its
   groups are not used. Ask the sign-in administrator for the correct field name.
4. Leave **Offer it on the sign-in page now** selected to enable it, then choose **Save provider**.
   An enabled provider is checked when saved. If discovery, connection or certificate checks
   fail, read the reason and correct the provider details with the operator.
5. Open the saved provider's page and copy its **Redirect address** under
   **Address to register with the provider**. Have that address registered with the provider.
   Prove a complete sign-in before turning local sign-in off.

![New sign-in provider with identity, registration and groups fields](/docs/screens/admin-signin-provider-new.png)

*Above: the reference instance's New sign-in provider dialog is open and has not been saved.*

Once anyone has used a provider, its issuer cannot change. Add another provider and link
people instead. Disabling a provider ends sessions it started. Removing someone in the
provider alone does not end an already open refiroo session; deactivate leavers in refiroo too.

On the provider page, **Sign people out of … too** also signs the current browser out of
the provider. It is off by default and can sign the person out of other organisation
applications in that browser. It needs provider support and registration of the displayed
**Sign-out address**. **Sign out everywhere** ends refiroo sessions only.

Server address, HTTPS and recovery setup belong with the operator. See the
[Run refiroo sign-in instructions](/docs/run/sign-in-and-mail-setup/).

## Second factors and passkeys

A local password must be set before a person adds an authenticator app or passkey. A provider-only account cannot add local factors. Adding or removing a passkey on Account requires proof with a password, authenticator code or recovery code; knowing an account’s name is insufficient. A person can register up to 25 passkeys.

An authenticator app adds a six-digit code after the password. Setup includes confirmation
with a code and ten recovery codes shown once. Each recovery code works once. A phone's
clock must be correct; if valid-looking codes fail, check its automatic time setting.

A passkey uses a fingerprint, face, device PIN or security key. It can sign someone in alone,
or supply the second step after a password. It meets the second-factor requirement.
A passkey belongs to the site's address; a change of host requires people to register new passkeys.

![Local accounts settings with the second-factor requirement](/docs/screens/admin-signin-local.png)

*Above: Local accounts is on in the reference instance; Require a second factor with a password is unchecked.*

**Require a second factor with a password** applies to everyone using local passwords,
including recovery administrators. Someone with neither an authenticator app nor a passkey
must set up an app on the sign-in page before a session starts. Provider sign-ins use the
provider's own checks, and clients are not asked for a second factor.
This is the browser's administrative policy control; there are no separate session-duration
or passkey-policy settings here. Follow [Require a second factor](/docs/guide/administer/require-a-second-factor/).

## Sessions and help

A session renews while the person works. By default it ends after 12 hours without renewal
or 14 days overall; the operator can change these limits. Once it ends, the person signs in
again and returns to the requested page.

Only the person's own **Account › Where you’re signed in** lists individual sessions.
Administrators have **Sign out everywhere** on the person's page, with confirmation.
Deactivation and using a password-reset link also end their sessions. Changing one's own
password keeps the current browser signed in and ends the others.

![Account with sign-in methods and the beginning of the session list](/docs/screens/admin-account-sessions.png)

*Above: Guide Admin's own Account page. The reference account's many sessions include automated
capture sessions; this is not an administrator's list of other people's browsers.*

If someone loses a device, a remaining passkey or recovery code may let them sign in.
Otherwise an administrator can remove the lost authenticator factor or passkey from the
person's page. A password reset does not bypass a second factor. Follow
[Help someone who lost a device](/docs/guide/administer/help-someone-who-lost-a-device/).

When mail is configured, the sign-in page offers a forgotten-password link for local accounts.
A person can request recovery there rather than asking an administrator to make a link. If it
is absent, use the administrator's reset procedure. The account-side password, session, passkey
and recovery-code tasks are on [Your account](/docs/use/account/).

## Help with the sign-in screen

The screen shows the refiroo mark and **Reference data that stays in step.** People enter **Username** and **Password**, then **Sign in**; **Signing in…** means it is waiting for an answer. Provider buttons say **Continue with …**. **Sign in with a passkey** uses a registered passkey and the device’s own confirmation.

The next step depends on the methods available. **Enter your code** asks for an app code. **Confirm it is you** also offers **Use a passkey**. **Use a recovery code instead** opens **Use a recovery code**; **Use the app’s code** returns to the app. **Set up a second factor** shows the setup image and key, followed by **Confirm and continue** and **Keep your recovery codes**. Ask the person to store the codes before continuing. They can start again if the sign-in attempt has expired.

**Your session ended. Sign in again to return to where you were.** calls for a fresh sign-in, not a password reset. **Signing in is not possible right now** with **Try again** can mean a service or connection failure. If the message says this site’s address is not accepted, give the operator the browser address and message so they can correct deployment access. Do not change a person’s password to repair a service failure.

Expired or invalid proof of access is refused before an operation runs. The browser normally renews a session automatically; if it cannot, sign in again. For an external system, have the integration owner follow [Signing in and tokens](/docs/integrate/signing-in-and-tokens/).

With no mail server, the screen instead says **Forgotten your password? Ask a security administrator for a reset link.** With mail, the person requests a one-time link, enters **New password** and **Type it again**, then chooses **Set password**. **Your password is set. You were signed out everywhere.** leads back to **Sign in**. The request gives the same answer for known, unknown, provider-only and deactivated accounts; mail is sent only for a qualifying local account. An app or recovery code is still required afterwards when configured. See [Mail](/docs/administer/mail/#password-links).

For the administrator’s tasks, follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/), [Link a provider sign-in](/docs/guide/administer/link-a-provider-person/) and [Turn off local sign-in](/docs/guide/administer/turn-off-local-sign-in/). On the provider catalogue, **No provider yet: people sign in with a password.** describes an empty list, not a connection failure. Saved provider details include separate Enable, Disable and Delete actions; disabling or deleting one ends the sessions it started.
