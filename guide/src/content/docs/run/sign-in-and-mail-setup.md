---
title: Set up sign-in and mail
description: Prepare public addresses, credentials and mail delivery for administrators.
reader: operator
---

Set the installation's stable HTTPS address before configuring sign-in or mail. Browser tasks for
people, groups, providers and clients belong to administrators; use [Sign-in](/docs/administer/sign-in/),
[People and groups](/docs/administer/people-and-groups/) and [Clients](/docs/administer/clients/).

## Public address and session settings

`PUBLIC_URL` is the token issuer and external origin, defaulting to `http://localhost:8000` for
local use. Set it explicitly in production. `CORS_ORIGINS` defaults to `http://localhost:5173`;
Compose supplies `PUBLIC_URL` instead. Each listed origin allows the browser's sign-in return at
`/signed-in`. Serve the browser at that origin's root and keep browser and engine on one site.

| Setting | Default | When to change it |
| --- | --- | --- |
| `ACCESS_TOKEN_MINUTES` | `60` | Shorten the access-token lifetime to meet policy. Deactivation still takes effect on the next request. |
| `SESSION_IDLE_HOURS` | `12` | Shorten how long a session lasts without renewal. Working browsers renew it. |
| `SESSION_DAYS` | `14` | Maximum session lifetime before a fresh sign-in. |
| `PASSWORD_RESET_HOURS` | `24` | Lifetime of a single-use password reset link. |
| `PASSWORD_MIN_LENGTH` | `15` | Leave at 15 in production. Development can lower it to 1; common passwords remain refused. |
| `TOKEN_SIGNING_KEY_DAYS` | `30` | Automatic signing-key rotation age. |

Apply environment changes by recreating the engine. A public host change signs people out,
requires new passkeys for that host, and needs provider callback addresses to be registered again.

## API authentication

There is no switch to disable authentication. Requests without access tokens return
`401 AUTHENTICATION_REQUIRED`. Invalid, expired, wrong-audience or deactivated-identity tokens
return `401 TOKEN_INVALID` with a reason. Insufficient roles return `403 FORBIDDEN`, naming the
action, the action groups that permit it and the workspace. Role changes apply on the next request.

The public exceptions are `/health`, `/health/live`, `/openapi.json`, `/docs` and its files,
including `/docs/api`, and the OAuth discovery, public keys, token, revocation and sign-in/password
routes. Public documentation is not permission to read workspace data.

A server-created administrator initially holds Security administrator, Data owner, Model
administrator, Workspace administrator, Integration administrator and Operator at the whole
instance. Once setup is complete, arrange narrower responsibilities and remove unnecessary
bootstrap grants. Use [Command-line tools](/docs/run/command-line/) to create the first identities.
For monitoring, create a dedicated client with `--role operator`.

A client uses OAuth client credentials. For a local development engine, with credentials already
loaded securely in your shell:

```bash
curl --fail -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
  http://localhost:8000/oauth/token
curl --fail -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/v1/workspaces
```

Set `ACCESS_TOKEN` securely from the token response before the second command. Use the public
HTTPS origin outside development. The default scope, `management`, serves `/api/v1` and `/metrics`;
`scope=consumer` requests access for `/api/consumer` instead. These tokens are not interchangeable.
On expiry or a refusal caused by signing-key retirement, the client fetches another token with its
unchanged credentials. See [Signing in and tokens](/docs/integrate/signing-in-and-tokens/) and the
[API reference](/docs/api) for integration details.

## Browser sessions and throttling

Browser sign-in uses the OAuth authorization-code flow with PKCE. Access tokens stay in page
memory. The `oauth_refresh` session cookie is `HttpOnly`, `SameSite=Strict` and scoped to `/oauth`;
it is `Secure` when `PUBLIC_URL` uses HTTPS. Each renewal replaces its refresh token. Presenting
an already-used refresh token ends that session as a suspected copied credential.

If `VITE_API_URL` separates the frontend and engine, both must share a site, such as
`refiroo.example.org` and `api.refiroo.example.org`. Unrelated domains cannot share this strict
cookie even when CORS permits requests. Outside applications can use the engine's
`/oauth/authorize` page; it cannot be framed. Its passkey script is served by the engine itself.

The first five failed attempts for a username and twenty for a caller address incur no delay.
Subsequent attempts wait 1 second, then 2, 4 and so on, up to 15 minutes after the last failure.
A correct password is not checked during a wait. Success clears the username count; counts lapse
after 24 hours. Wrong current passwords, passkey proofs and client secrets also count against
throttling. Logs identify failures with `sign_in_failed`, username and caller address.
Trust forwarded caller addresses only from the actual proxy, or everyone shares its address limit.
At most 2,000 unfinished provider sign-ins can be open per provider. Further starts show HTTP 429
until starts expire after ten minutes.

Password links prefer the Mail settings' application address, then the first `CORS_ORIGINS`
entry. If neither is available, they use the engine's `/oauth/password` page; older links can
also point there. A newer reset link replaces the previous one. Using it ends all sessions.
Changing a password from Account instead preserves the current browser session and ends the others.

## Prepare a sign-in provider

Register refiroo as an OpenID Connect web application with your organisation's provider. The
administrator chooses the provider key and configures its issuer and secret in Settings.
Register the exact callback `<PUBLIC_URL>/oauth/providers/<key>/callback`. If provider sign-out is
enabled, also register `<PUBLIC_URL>/oauth/providers/<key>/signed-out`.

Allow outbound HTTPS from the engine to the issuer's discovery and key endpoints. Certificates
must be trusted. Plain HTTP is accepted only for a loopback provider; link-local destinations are
refused. An issuer mismatch, TLS error or unreachable provider prevents saving it as enabled and
returns a reason. Resolve that reason rather than weakening certificate verification.

The client secret is write only and sealed with `SECRETS_ENCRYPTION_KEY`. Changing issuer requires
supplying the new issuer's secret in the same save. Once people have signed in through that provider,
its issuer cannot change; add another provider instead. Keep a tested local recovery administrator.
A provider's removal of a person does not end their existing refiroo session immediately: deactivate
leavers in refiroo too. Disabling the provider ends its sessions.

## Provider registration details

The requested OpenID Connect scopes are `openid profile email`. Example issuers are
`https://login.microsoftonline.com/<tenant-id>/v2.0` for Entra ID,
`https://accounts.google.com` for Google and `https://<host>/realms/<realm>` for Keycloak.
Use the issuer stated by that registration, including its tenant or realm.

Provider sign-out requires `end_session_endpoint` in discovery. Register the exact signed-out
address displayed by refiroo in the provider's post-logout redirect configuration. The engine keeps
the sign-in ID token sealed for that session only when provider sign-out is enabled.

For a failed provider sign-in, Security events record the reason and detail: `issuer` or `nonce`
means the token did not belong to this sign-in, `exchange` means code exchange failed (check secret
and callback), `browser` means the flow started in another browser, and `deactivated` identifies a
disabled person. Give the reason to the responsible administrator without copying tokens or secrets.

## Prepare SMTP delivery

Arrange an SMTP server and a sender address. A security administrator saves these on **Settings › Integration › Mail**:

1. In **Mail server**, enter **Server** and **Port**, then choose **Connection** (STARTTLS or TLS
   for an authenticated server).
2. Enter **User name** and **Password** if required, **From address** and the public **Application
   address** used for links. Choose **Save**. A save refusal leaves the existing settings intact;
   use the refusal table below before trying again.
3. Under **Test message**, enter **Send to** and choose **Send test message**. **Sent** means the
   SMTP server accepted it; confirm arrival in the recipient's mailbox as well.
4. Inspect **Messages** for later delivery attempts and **Last problem**. **Stop sending** ends
   retries for a waiting message, but its one-time link remains valid until expiry.
The SMTP password is a secret, sealed in the database and never shown. Changing host or port needs
the password again in the same save (`MAIL_PASSWORD_REQUIRED`).

Use STARTTLS, usually port 587, or TLS, usually 465. Unencrypted delivery is only for a trusted relay
without a login: the engine refuses sending credentials without encryption. Supply your internal
CA to the engine's trust store or `SSL_CERT_FILE` when needed. Check that the mail application
address is the public address; if empty, links use the first `CORS_ORIGINS` entry.

Configure SPF and DKIM for the sender's domain at your mail provider. refiroo does neither.
A successful SMTP test does not prove delivery to the recipient's inbox; check junk folders and
mail-provider logs too.

Mail is queued in the database and sent in the background. Transient failures retry after 30 seconds,
doubling to at most one hour, for up to 24 hours. Permanent recipient refusal fails immediately.
Finished messages stay for 30 days; message text containing links is erased after sending or failure.
The Mail page reports connection, TLS, login and address failures; Operations shows `mailSender`.
Removing mail settings stops sending; waiting messages fail once their retry window ends.

## Read mail refusals

| Message | What to do |
| --- | --- |
| `422 MAIL_INSECURE_LOGIN` | Choose TLS or STARTTLS before supplying a username, or remove the login for a trusted unencrypted relay. The settings were not saved. See [Save mail settings in the API reference](/docs/api) (`PUT /api/v1/mail-settings`). |
| `409 MAIL_NOT_SET_UP` | A security administrator must save SMTP settings before a test or a request that queues mail can run. Removing settings also refuses further mail requests; queued messages remain pending until delivery can resume or their retry window ends. See [Mail settings and test operations](/docs/api). |
| `422 MAIL_PASSWORD_REQUIRED` | Supply a password for a new login, or enter it again when changing host or port. A stored password is never forwarded to a new server automatically. |
| `409 VERSION_CONFLICT` | Another administrator changed the settings. Reload, review their changes and save again. |

## Inbox mail and digests

The same sender delivers inbox notices and digests. People choose them in **Settings › General › Notification email**;
clients receive no mail. These choices do not need AI or another server setting. Immediate notices
are mailed only after a person opts in and while the notice is less than 24 hours old, preventing
an old backlog after a long outage. The inbox retains notices even when their mail is off.

Digests are scheduled for 07:00 daily, or Monday at 07:00 weekly, in the person's saved time zone.
Daylight-saving changes keep that local time. Several engine processes still queue one digest.
After downtime the sender queues one digest rather than one per missed morning. Nothing unread
means no message. If mail is not configured, the due time stays put until it is configured.
Outbox entries distinguish `notice` and `digest`; use the Mail page to inspect waiting, sent and
failed messages. An authorised administrator can stop a waiting message. Browser choices and
following a workspace are described in [Notifications](/docs/use/notifications-settings/).

Every process runs a mail sender. Database leases prevent two senders delivering the same queued
message. Notice messages contain the event kind and application link, without record, change-set
or person content; their message text is protected and erased like password-link mail.

## Verify the whole sign-in path

Before handing setup to the access administrator, you need the permanent HTTPS origin, an enabled
local recovery administrator, provider-registration rights if using one, and direct outbound access
from the engine to that provider. A provider's token-exchange endpoint and signing-key endpoint
must be reachable as well as discovery. Its configuration and SMTP settings live in the database;
they are not additional `.env` settings. Environment/session settings above are non-secret and
all need engine recreation after a change.

1. Check public readiness, then fetch the advertised OAuth metadata:

   ```bash
   curl --fail https://refiroo.example.org/.well-known/oauth-authorization-server
   ```

   Expect JSON advertising the public issuer and endpoint addresses under the same intended
   origin. If the issuer is a development or internal name, correct `PUBLIC_URL`, recreate the
   engine and recheck before registering callbacks.
2. Sign in using the local recovery account at the public origin. With a provider configured,
   sign out and test provider sign-in in a fresh browser session too. Confirm the resulting person
   can open only the intended workspaces; proof of identity alone grants no roles.
3. Verify callback and optional signed-out addresses against those displayed on the provider page.
   `SIGN_IN_PROVIDER_IN_USE` means the saved issuer already identifies people; create a different
   provider rather than trying to change those identities in place.
4. Before disabling ordinary local sign-in, verify provider sign-in and the recovery account.
   If all administrators lose access, run the server-side recovery command:

   ```bash
   docker compose run --rm engine python -m app.cli.create_admin    \
     --username recovery-operator --name "Recovery administrator"
   ```

   Expect the password prompts and `Created administrator 'recovery-operator' (...)`.
   This creates another privileged person who keeps local sign-in. Complete required second-factor
   setup on first use. Once access is recovered, review and narrow temporary recovery grants.

Repeated login failures are slowed per username and caller address. Check forwarded-address trust
if many different users appear to share a throttle. A correct password does not bypass a wait
already in force. Do not reset passwords or disable second factors just to work around a proxy
that supplies one address for everyone.

## Diagnose mail without exposing message links

You need Security administration to save/test mail, a sender allowed by the SMTP service and a
recipient whose mailbox you can inspect. In the reference installation the engine connects directly
from its network to that host and port. A successful TCP connection alone does not prove TLS,
credentials or sender permissions.

| Exact message fragment | Cause and next step |
| --- | --- |
| `Mail is not set up` | Save SMTP settings before testing or requesting mail. |
| `A user name needs a password` | Supply the login password in the same save. |
| `Could not connect to` | Check DNS, routing, server port and whether SMTP is listening. The message names the host and underlying reason. |
| `The TLS handshake with` and `failed:` | Check TLS/STARTTLS mode, trusted CA chain, hostname and expiry. |
| `would not start TLS:` | Use a port/service that supports STARTTLS, or the provider's direct TLS port with TLS mode. |
| `refused the login of` | Correct the SMTP account and password; check whether the provider requires an application credential. |
| `refused the address:` | Check the recipient and the SMTP service's policy; a permanent refusal is not retried. |
| `refused the from address` | Authorise the configured sender address with the SMTP service. |
| `did not accept the message:` | Read the SMTP reason and inspect the sender's limits or policy. |
| `closed the connection:` | Check the server log, connection policy and network path; transient failures retry in the background. |

If a new host or port save is refused as `MAIL_PASSWORD_REQUIRED`, re-enter the password in that
same save. To undo a mistaken change, save the prior server details and password again with the
current settings version; reloading first avoids overwriting another administrator. Removing mail
settings stops sending and eventually expires queued attempts, but does not roll back notices in
the inbox or invalidate links already issued. Keep one-time reset links out of diagnostic reports.

After SMTP accepts the test, confirm receipt and open its public link from the recipient's network.
For password reset, use a test person and complete the single-use reset, then sign in; this checks
link address and expiry as well as delivery. For digests, inspect the person's saved time zone and
notification choices before changing the server clock: delivery is due at that person's 07:00.

![Mail settings before setup, with blank server fields and Send test message unavailable](/docs/screens/admin-mail-settings.png)

*Above: mail is not set up on the reference instance. The test becomes available after
server settings are saved; this picture does not show a successful test or delivered digest.*
