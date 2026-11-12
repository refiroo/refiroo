# mail

Mail carries a new person's welcome link, a password reset link, a test message and, if a person chooses it, copies of their inbox notices. It is set up once for the instance, with an SMTP server or Microsoft 365; saving replaces what was saved. A message is queued in the outbox, sent by a background worker and retried for 24 hours; its text is never answered and is erased once the message is finished. Each person chooses how their inbox is mailed. An Operator's e-mail template, Markdown with a logo, wraps every message; without one the engine's layout is used.

1. Set up: `PUT /api/v1/mail-settings`, then `POST /api/v1/mail-settings/test`.
2. Watch: `GET /api/v1/mail-outbox`; `POST .../stop` ends a message that is still waiting.
3. Brand it: `PUT /api/v1/mail-template`, then `POST /api/v1/mail-template/preview`.

## DELETE /api/v1/mail-settings

Title: Remove the mail settings

Removes the settings, so no mail is sent and what needs mail answers `409 MAIL_NOT_SET_UP`. Messages already waiting stay in the outbox and fail after 24 hours; stop them sooner with `POST /api/v1/mail-outbox/{message_id}/stop`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 MAIL_NOT_SET_UP: no settings are saved

## GET /api/v1/mail-settings

Title: Read the mail settings

Reads how mail is sent, the address links in mail point to and how many messages wait, were sent or failed. Without saved settings `configured` is false and no mail is sent. A password, client secret or certificate is never answered; a certificate shows as its thumbprint and expiry.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance

## PUT /api/v1/mail-settings

Title: Save the mail settings

Saves the settings, replacing what was saved. The first save omits `expectedVersion`; later ones send the saved `version`. Saving one method clears the other's fields. `password`, `clientSecret` and `certificate` are sealed; when omitted the saved one is kept, except for another host, port, tenant, application or token address. Nothing is sent: try the settings with `POST /api/v1/mail-settings/test`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 VERSION_CONFLICT: `expectedVersion` is not the saved version
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or belongs to the other method
- 422 MAIL_INSECURE_LOGIN: a login with `security` `none`
- 422 MAIL_PASSWORD_REQUIRED: a user name with no password to keep
- 422 MAIL_CREDENTIAL_REQUIRED: Microsoft 365 with no secret or certificate to keep
- 422 MAIL_CERTIFICATE_INVALID: the certificate cannot be read or used

## POST /api/v1/mail-settings/test

Title: Send a test message

Sends a test message to `to` through the saved settings now, with either method. The message shows the address links will point to. A failure is answered with what failed in `details.kind`: `connection`, `tls`, `login`, `recipient`, `sender` or `rejected`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 MAIL_NOT_SET_UP: no settings are saved
- 422 REQUEST_VALIDATION_ERROR: `to` is not an address
- 422 MAIL_SEND_FAILED: the server did not take the message

## GET /api/v1/mail-outbox

Title: List the messages in the outbox

Lists the messages waiting, sent or given up on, newest first; a failed one says why. Finished messages are kept for 30 days. The text of a message is never answered, because it holds a one-time link.

### Parameters

- status: Only messages in this status.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/mail-outbox/{message_id}/stop

Title: Stop a message

Stops a message that is still waiting for its next try: it fails at once with "Stopped by an administrator" and its text is erased. Stopping does not revoke the link in it, which works until it expires.

### Parameters

- message_id: The message's ID.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 NOT_FOUND: no message has this ID
- 409 MESSAGE_NOT_WAITING: it was sent or failed already
- 409 MESSAGE_BEING_SENT: a sender holds it; try again

## GET /api/v1/me/notification-mail

Title: Read my notice mail

Reads whether the caller is mailed when something arrives in their inbox, and how each kind of notice and the digest are set. `available` is false where it cannot work and `reason` says why; a client has no mail.

## PUT /api/v1/me/notification-mail

Title: Change my notice mail

Switches mail for the caller's inbox on or off, sets the digest's frequency and time zone, and how each kind of notice is mailed: `now`, `digest` or `off`. Send any of `enabled`, `kinds` and `digest`; nothing changes if a part is refused. Only notices made after switching on are mailed, and only the mail changes: the inbox keeps every notice.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 409 MAIL_NOT_SET_UP: switching on needs mail set up
- 409 NO_EMAIL: switching on needs an address on the person
- 422 REQUEST_VALIDATION_ERROR: the body holds none of the fields
- 422 UNKNOWN_NOTICE_KIND: a key in `kinds` is not a kind
- 422 UNKNOWN_TIME_ZONE: `digest.timeZone` is not a time zone
- 422 DIGEST_NOT_SET: a kind goes in the digest and none is set

## GET /api/v1/mail-template

Title: Read the e-mail template

Reads the template that wraps every message the engine sends: Markdown with placeholders, and the logo as a data URL. Without a saved template `saved` is false, `markdown` is the default and the engine's own layout is used.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## PUT /api/v1/mail-template

Title: Save the e-mail template

Saves the Markdown, replacing what was saved; the first save omits `expectedVersion`, later ones send the saved `version`. The logo stays. `{{content}}`, where the message's own heading, text and button go, must appear exactly once; the other placeholders are `{{product_name}}`, `{{instance_url}}`, `{{recipient_name}}` and `{{logo}}`. Raw HTML in the Markdown is shown as text, images are not drawn and a link is kept only for http, https and mailto.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 409 VERSION_CONFLICT: `expectedVersion` is not the saved version
- 422 REQUEST_VALIDATION_ERROR: `markdown` is empty
- 422 MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER: a `{{name}}` that is not a placeholder
- 422 MAIL_TEMPLATE_CONTENT_REQUIRED: `{{content}}` is missing or appears twice
- 422 MAIL_TEMPLATE_TOO_LONG: over 20,000 characters

## DELETE /api/v1/mail-template

Title: Reset the e-mail template to the default

Deletes the saved Markdown and the logo, so the engine's own layout is used again. Repeating it changes nothing.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## PUT /api/v1/mail-template/logo

Title: Upload the e-mail logo

Uploads the image that `{{logo}}` shows, sent inline in each message; without one the refiroo mark is used. Send `multipart/form-data` with the image as `file` and, once a template is saved, its `version` as `expectedVersion`. With no template saved, the default Markdown is saved with the logo.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 409 VERSION_CONFLICT: `expectedVersion` is not the saved version
- 413 MAIL_LOGO_TOO_LARGE: over 512 KB
- 422 MAIL_LOGO_UNSUPPORTED: not a PNG, JPEG or SVG image
- 422 MAIL_LOGO_UNSAFE: an SVG that holds script or an external object

## DELETE /api/v1/mail-template/logo

Title: Remove the e-mail logo

Removes the uploaded logo, so `{{logo}}` shows the refiroo mark again.

### Parameters

- expectedVersion: The template's saved `version`.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 409 MAIL_TEMPLATE_NOT_SAVED: no template is saved, so there is no logo
- 409 VERSION_CONFLICT: `expectedVersion` is not the saved version

## POST /api/v1/mail-template/preview

Title: Preview the e-mail template

Renders a draft Markdown around a sample message with sample values, and answers the HTML (the logo inline as a data URL) and the plain text. Nothing is saved or sent. The draft is checked like a save.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 422 MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER: a `{{name}}` that is not a placeholder
- 422 MAIL_TEMPLATE_CONTENT_REQUIRED: `{{content}}` is missing or appears twice

## POST /api/v1/mail-template/test

Title: Send a test of the e-mail template to me

Sends the saved template around a sample message to the caller's own address through the saved mail settings now. A failure is answered as for `POST /api/v1/mail-settings/test`.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 403 NOT_A_PERSON: the caller is a client
- 409 NO_EMAIL: the person has no address
- 409 MAIL_NOT_SET_UP: no mail settings are saved
- 422 MAIL_SEND_FAILED: the server did not take the message

## Schemas

### MailSettingsResponse

How mail is sent; never a password, client secret or certificate. Without saved settings `configured` is false, `method` and the connection fields are null and no mail is sent. With `smtp` the SMTP fields are set; with `microsoft365` the Microsoft 365 ones (`fromAddress` is the sending mailbox; a managed identity stores no secret), and a certificate is answered by its thumbprint (SHA-1, as the Entra portal shows it) and expiry. `applicationUrl` is where the links in mail point: the saved address, or the first browser origin while `applicationUrlIsDefault`.

- configured: True when settings are saved; false means no mail is sent.
- method: `smtp` or `microsoft365`; null when not configured.
- host: SMTP: the server's host name.
- port: SMTP: the server's port.
- security: SMTP: `tls` (encrypted from the first byte), `starttls` (upgraded after the greeting) or `none`.
- username: SMTP: the login's user name; null when there is none.
- tenantId: Microsoft 365: the Entra tenant ID or domain; null for a direct managed identity.
- clientId: Microsoft 365: the application's client ID; null for a direct managed identity.
- certificateExpiresAt: Microsoft 365: when the saved certificate expires; null without one.
- authorityUrl: Microsoft 365: where tokens are issued.
- graphUrl: Microsoft 365: the Graph address.
- fromAddress: The address mail is sent from; with Microsoft 365, the sending mailbox.
- applicationUrl: Where the links in mail point: the saved address, or the first browser origin while `applicationUrlIsDefault`.
- applicationUrlIsDefault: True while no address is saved.
- outbox: How many messages wait, were sent or failed.
- updatedAt: When the settings were last saved; null until then.

### MailSettingsUpdate

How mail is sent, replacing what was saved. `expectedVersion` is the saved version, absent when none is saved yet. `method` is `smtp` (`host`, `port`, `security` and optionally a login) or `microsoft365` (`tenantId`, `clientId` and a `clientSecret` or a `certificate` or a managed identity: `identityMode` `direct` or `federated` with `identityClientId`); the other method's fields must be absent, and saving replaces the other method's saved fields. `password`, `clientSecret` and `certificate` omitted keep the saved one (the same method and the same server or application); a `username` of null removes the login and with it the password. `certificate` is PEM text holding the private key (not encrypted) and the certificate. `fromAddress` is the sending mailbox with Microsoft 365. `applicationUrl` null means the first browser origin (`CORS_ORIGINS`).

- method: `smtp` (the default) or `microsoft365`. The other method's fields must be absent.
- expectedVersion: The saved `version`; omit it on the first save.
- host: SMTP: the server's host name, without scheme or path.
- port: SMTP: the server's port, 1 to 65535.
- username: SMTP: the login's user name; null removes the login and its password.
- fromAddress: The address mail is sent from; with Microsoft 365, the sending mailbox.
- applicationUrl: Where links in mail point, such as `https://refiroo.example.org`; null means the first browser origin.

### MailCounts

- pending: Messages waiting for a try.
- sent: Messages sent.
- failed: Messages given up on or stopped.

### MailTest

- to: The address to send the test message to.

### MailTestResponse

- sentTo: The address the server accepted the message for.

### MailMessageResponse

- id: The message's ID.
- kind: `activation`, `password-reset`, `test`, `notice`, `digest` or `security` (a change to the person's sign-in).
- to: The address it is sent to.
- subject: Its subject.
- status: `pending`, `sent` or `failed`.
- attempts: How many times it was tried.
- lastErrorKind: What failed last: `connection`, `tls`, `login`, `recipient`, `sender`, `rejected`, `not_set_up`, `unreadable`, `expired` or `stopped`; null when nothing failed.
- createdAt: When it was queued.

### NoticeMailResponse

Whether the caller is mailed when something arrives in their inbox; off until the person switches it on. `available` is false where it cannot work, and `reason` says why: `mail-not-set-up`, `no-email` (the person has no address) or `not-a-person` (a client has no mail).

- enabled: True when the caller is mailed their inbox notices.
- available: False where mail cannot work for the caller.
- reason: Why not: `mail-not-set-up`, `no-email` or `not-a-person`.

### NoticeMailUpdate

- enabled: True switches notice mail on, false off.
- digest: The digest's frequency and time zone.

### DigestUpdate

- every: `daily` or `weekly`.

### DigestResponse

The caller's digest: how often it comes, the time zone 07:00 is read in and when the next is due. `nextAt` is the next send time while mail is switched on, otherwise null.

- nextAt: When the next digest is due; null while mail is off.

### MailMessagePage

Messages, newest first.

### MailTemplateResponse

The e-mail template. Without a saved one (`saved` false) `markdown` is the default.

- markdown: The template: Markdown with `{{placeholders}}`.
- defaultMarkdown: The shipped default; `DELETE /api/v1/mail-template` restores it.
- saved: True when a template is saved; false means the engine's own layout is used.
- placeholders: The placeholders a template may use; `content` is required exactly once.
- logoType: `image/png`, `image/jpeg` or `image/svg+xml`; null while the refiroo mark is used.
- logoDataUrl: The uploaded logo as a data URL, for a thumbnail; null when none.
- logoMaxBytes: The largest logo accepted, in bytes.
- version: Null until saved; send it as `expectedVersion`.
- updatedAt: When the template was last changed; null until saved.

### MailTemplateUpdate

- markdown: The template's Markdown.
- expectedVersion: The saved `version`; omitted on the first save.

### MailTemplatePreview

- markdown: The draft Markdown to render.

### MailTemplatePreviewResponse

The draft rendered around a sample message.

- html: The whole HTML document, the logo inline as a data URL.
- text: The plain-text alternative.
