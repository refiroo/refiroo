---
title: Security, audit and privacy
description: How refiroo controls access, records activity and protects credentials.
reader: evaluator
---

Governed changes need a record of who changed what. refiroo requires people and systems to sign in before accessing reference data, checks permissions on each operation and records changes in history. Review comments can explain why a proposed change was approved or sent back. See [What refiroo is](/docs/about/what-is-refiroo/) for the overview.

## Access is checked by the service

Hiding an editing control is only a convenience. The service enforces roles and workspace grants on browser actions, file loads and API operations. Background jobs recheck the requester's rights as they run. A deactivated person or client loses access on the next request; ending a browser session also ends its use.

Public documentation, contract documents, sign-in services and health checks have deliberate exceptions to data authentication. Their availability does not make reference data public. See [Who can do what](/docs/about/people-and-access/) and [Sign-in](/docs/administer/sign-in/).

## Sign-in and credentials

Local accounts support second factors and passkeys. An organisation's sign-in provider brings its own sign-in policy. Repeated failed local sign-ins are slowed, and the failure message does not reveal whether a username or password was wrong. People can inspect and end their sessions on [Account](/docs/use/account/).

Passwords are stored as hashes. Secrets that refiroo must use again, such as provider credentials and webhook signing keys, are encrypted in storage with an operator-managed key. Secrets are not ordinary reference-data fields and are not included in activity records. Protecting the encryption key and backups remains an operator responsibility; changing a key requires the documented recovery procedure.

Production installations need HTTPS, protected database access and controlled operator credentials. These are deployment responsibilities, not guarantees made merely by installing the software. See [Secrets and keys](/docs/run/secrets-and-keys/) and the [Security checklist](/docs/run/security-checklist/).

## Know who changed what

Data history names the person or client responsible, including the requester behind a job. Security activity separately records sign-ins, changes to people and clients, role grants and group membership. A security administrator can inspect that activity; data history remains limited to workspaces the reader may browse.

Attribution uses the person's or client's current name, even after deactivation. Older data changes without attribution show **Before sign-in**. History can expose names and previous reference-data values to authorised readers, so access and retention need to match your organisation's policy. See [History](/docs/use/history/) and [Audit](/docs/administer/audit/).

## Sharing creates another trust boundary

A webhook sends data to the configured receiver. Deliveries are signed so the receiver can verify their origin; signing does not encrypt their content. Production receivers use HTTPS. Operators and integration administrators must choose appropriate receivers and protect their signing keys.

Files and consumer APIs also disclose the data their reader is allowed to obtain. Grant only the access each integration needs. See [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) and [Clients](/docs/administer/clients/).

Report suspected vulnerabilities privately to **security@refiroo.org**, or use the repository's private reporting option described in its [security policy](https://github.com/refiroo/refiroo/blob/main/SECURITY.md).
