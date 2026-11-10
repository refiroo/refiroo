# MS guide: mail through Microsoft 365 (Microsoft Graph)

Read `guide/AGENTS.md`. Readers: the access administrator (`administer/mail.md`) and the operator
(`run/sign-in-and-mail-setup.md`), as each page names.

## Why

Package MS (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "MS: Mail through Microsoft 365 (Graph)") added a second way to
send mail beside SMTP. Microsoft is retiring basic authentication for SMTP AUTH in Exchange Online, and an organisation
on Microsoft 365 often cannot give refiroo a user name and password for it. The code wins: `backend/app/engine/mail/graph.py`,
`transport.py`, `settings.py`, `sender.py`, `backend/app/models/commands.py` (`MailSettingsUpdate`),
`backend/app/management/schemas/mail.py`, `frontend/src/features/settings/MailPage.tsx`, `docs/API.md` ("Mail"),
`docs/OPERATIONS.md` ("Sending through Microsoft 365 (Graph)"), `../CHANGELOG.md` (Unreleased, 0.13 MS).

## What the product does now (check each point in the code)

- **Two methods, one at a time.** At the top of the form on Settings › Integration › Mail, **Send mail through**
  chooses **SMTP server** (everything the pages say today) or **Microsoft 365**. Saving one method replaces the other's
  saved fields (server, port, login, or the Microsoft 365 fields). There is no fallback from one to the other.
- **Microsoft 365 fields:** **Tenant ID** (the directory ID or the tenant's domain name), **Application (client) ID**,
  **Credential** (**Client secret** or **Certificate**), then **Client secret** (the secret's value) or **Certificate**
  (the private key, not password-protected and RSA, and the certificate, together as PEM text), **Sending mailbox**
  (the label of the from address: mail is sent as this mailbox), **Application address** (as for SMTP), and two
  optional addresses, **Token address** (default `https://login.microsoftonline.com`) and **Graph address**
  (default `https://graph.microsoft.com`), which are changed together for a national cloud.
- **Sealed, never shown.** The client secret and the certificate with its key are sealed with `SECRETS_ENCRYPTION_KEY`
  like the SMTP password and never shown again. For a certificate the page shows its thumbprint (SHA-1, as the Entra
  portal shows it) and when it expires; a certificate that has expired is refused on saving, and one that expires later
  makes mail fail with a refused login after that date, so it is renewed before. Leaving the secret or certificate empty
  keeps the saved one only while the tenant ID, the application ID and the token address are unchanged; otherwise it is
  asked for again (`MAIL_CREDENTIAL_REQUIRED`). A certificate that cannot be used is `MAIL_CERTIFICATE_INVALID` (not PEM,
  no private key or an encrypted one, not RSA, no certificate that belongs to the key, expired).
- **The box "Set this up in Microsoft Entra first"** on the page lists four steps: register an application and copy its
  tenant ID and application (client) ID; give it a client secret or upload a certificate to it; add the `Mail.Send`
  application permission of Microsoft Graph and grant admin consent; limit the application to the sending mailbox with
  an application access policy (or RBAC for Applications), because without one the application can send as any mailbox
  in the tenant. The operator page carries the longer version (`docs/OPERATIONS.md`, "Sending through Microsoft 365
  (Graph)", points 1 to 5): the Entra admin center's App registrations; the secret's *Value* is shown once and expires;
  the certificate's public part is uploaded to the registration; `New-ApplicationAccessPolicy` in Exchange Online
  PowerShell restricted to a mail-enabled security group holding the mailbox, or RBAC for Applications; a policy can
  take some time to apply; the sending mailbox must be a licensed user or a shared mailbox of the tenant.
- **Send test message** works for both methods and answers in the same way: sent, or a heading and a sentence saying
  what failed.
- **How it sends.** The engine asks Microsoft for a token with the client-credentials grant (plain HTTP, no Microsoft
  library; a certificate signs an assertion, RS256) and keeps the token in the process until shortly before it
  expires. It sends each message with Microsoft Graph's `sendMail` as the sending mailbox, with the same message as
  SMTP sends: plain text, HTML and the embedded brand images, so mail looks the same through both. **Microsoft saves
  such a message in the mailbox's Sent Items; the engine cannot turn that off.**
- **Failures, in the kinds the guide already names.** A refused token (wrong or expired secret, a certificate not
  registered on the application, an unknown application or tenant), missing `Mail.Send` consent, or a mailbox the
  application may not use is **the login was refused**: the same for every waiting message, so they share it; the
  sentence says what to change; the settings may be fixed while messages wait. Microsoft out of reach, busy (HTTP
  429) or failing (5xx) is **the server could not be reached**: the message waits at least as long as Microsoft asked
  (`Retry-After`) and no less than the usual wait (30 seconds, doubling, an hour at most). A mailbox Microsoft does not
  know fails the message at once as **the server refused the from address** (kind `sender`); with SMTP the same kind
  leaves the message waiting, here it does not. Any other refusal fails the message at once. The 24-hour limit and the
  outbox are unchanged. The secret, the token and Microsoft's own text never appear in a message, the outbox or the log.
- **A bad recipient is not noticed at sending (MS-D2).** Microsoft accepts the message (`202`) and reports an address
  that does not exist later, as a bounce to the sending mailbox, as an SMTP relay does. refiroo does not read
  bounces and shows the message as **Sent**; the administrator finds the bounce in the mailbox, which also receives
  replies. This is the same for SMTP.
- **Reseal.** Changing `SECRETS_ENCRYPTION_KEY` re-seals the client secret and the certificate as well; the operator
  tool lists them as "Microsoft 365 client secret" and "Microsoft 365 certificate".
- **API.** `GET/PUT /mail-settings` carry `method` (`smtp` or `microsoft365`), `tenantId`, `clientId`, `clientSecret`
  (write-only; the answer has `clientSecretSet`), `certificate` (write-only; the answer has `certificateThumbprint`
  and `certificateExpiresAt`), `authorityUrl`, `graphUrl`. A request that carries the other method's fields is a
  request validation error naming the field. New error codes: `MAIL_CREDENTIAL_REQUIRED`, `MAIL_CERTIFICATE_INVALID`
  (both `422`, `details.field`). Link to `/docs/api`, do not repeat the reference.

## What to do

- `src/content/docs/administer/mail.md`: the page opens with "Use Settings › Integration › Mail to connect refiroo to
  your organisation's mail server". Say once, near the top, that refiroo sends through an SMTP server or through
  Microsoft 365 and that one is used at a time. Keep **Mail server** for SMTP. Add a section **Send through Microsoft
  365** (after Mail server) with the fields, the credential choice, the certificate's thumbprint and expiry, what is
  set up in Entra (short list, link to the operator page for the full steps), Sent Items, and that bounces go to the
  sending mailbox and are not read. In the section on failures, add what the Microsoft 365 failures mean for the
  administrator and what to do (the table or list the page already has: extend it, do not rewrite it). Where the page
  says "the password is kept sealed", say the same for the secret and the certificate key. Do not change the existing
  screenshot or its caption; say in the report that a picture of the Microsoft 365 form is missing.
- `src/content/docs/run/sign-in-and-mail-setup.md`: next to "Prepare SMTP delivery", add **Prepare Microsoft 365
  delivery** for the operator: the Entra steps in full (the five points above), the two addresses and national clouds,
  where the secrets live and that `SECRETS_ENCRYPTION_KEY` re-seals them, the renewal of a secret or certificate before
  it expires. Extend "Read mail refusals" with the new codes (`MAIL_CREDENTIAL_REQUIRED`, `MAIL_CERTIFICATE_INVALID`)
  and the Microsoft 365 meaning of the failure kinds, and "Diagnose mail without exposing message links" only where a
  Microsoft 365 step differs. Do not alter an existing example; if an example is needed for the new API fields, take it
  from `docs/API.md` and mark any secret as a placeholder.
- No new pages. The word "SMTP" stays where a sentence is about SMTP only.

## Files you may edit

- `src/content/docs/administer/mail.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
- `_waves/progress/MS.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures that are
missing or no longer match, and anything in the points above that you could not support from the code.
