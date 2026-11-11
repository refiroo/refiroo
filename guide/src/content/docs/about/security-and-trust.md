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

Local accounts support TOTP authenticator codes and WebAuthn passkeys. An organisation's OpenID Connect sign-in provider brings its own sign-in policy. Repeated failed local sign-ins are slowed, and the failure message does not reveal whether the e-mail address or the password was wrong. People can inspect and end their sessions on [Account](/docs/use/account/).

Passwords are stored as hashes. Secrets that refiroo must use again, such as provider credentials and webhook signing keys, are encrypted in storage with an operator-managed key. Secrets are not ordinary reference-data fields and are not included in activity records. Protecting the encryption key and backups remains an operator responsibility; changing a key requires the documented recovery procedure.

For a public installation, refiroo provides [automatic HTTPS](/docs/run/https/): Caddy obtains a Let's Encrypt or ZeroSSL certificate and renews it before it expires. You do not need to buy a certificate, install certificate files or renew it by hand. The operator points the public name's DNS at the host, keeps port 443 reachable from the internet (port 80 is optional for redirects) and preserves the certificate storage volume. An organisation can instead use its own certificates or an existing HTTPS proxy.

Production installations also need protected database access and controlled operator credentials. See [Secrets and keys](/docs/run/secrets-and-keys/) and the [Security checklist](/docs/run/security-checklist/).

## Know who changed what

Data history names the person or client responsible, including the requester behind a job. Security activity separately records sign-ins, changes to people and clients, role grants and group membership. A security administrator can inspect that activity; data history remains limited to workspaces the reader may browse.

Attribution uses the person's or client's current name, even after deactivation. Older data changes without attribution show **Before sign-in**. History can expose names and previous reference-data values to authorised readers, so access and retention need to match your organisation's policy. See [History](/docs/use/history/) and [Audit](/docs/administer/audit/).

## Sharing creates another trust boundary

A webhook sends data to the configured receiver. Deliveries are signed so the receiver can verify their origin; signing does not encrypt their content. Production receivers use HTTPS. Operators and integration administrators must choose appropriate receivers and protect their signing keys.

Files and consumer APIs also disclose the data their reader is allowed to obtain. Grant only the access each integration needs. See [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) and [Clients](/docs/administer/clients/).

## AI help stays under your control

AI is optional. Your operator can enable a provider for proposed mapping targets, questions turned
into list filters and explanations of changes. The built-in assistant uses Claude Code to prepare
models and records from your words or a workbook. These are enabled separately. External assistants
can connect through the Model Context Protocol (MCP) when agent access is enabled.

Built-in AI actions need **Use AI proposals**, as well as the permissions for the work itself.
The Data steward, Data owner, Model administrator, Workspace administrator and Integration
administrator roles include that permission. Access still depends on the workspace grant.
An external assistant uses its person's or client's grants, limited to reading and preparing
change sets; it cannot approve or publish, even when that person can.

### What may leave the instance

The operator chooses a send level for built-in AI help:

| Level | Information allowed to be sent |
| --- | --- |
| structure | Model names, field names, headers, types and counts, without stored record values. Your question is still sent. |
| samples | Also sample values within the operator's limit. A question in words can send a whole related list of at most 50 record names, including ancestor names, regardless of that sample limit. |
| values | The record values the task needs. This is required for mapping targets and the built-in assistant. |

The assistant receives your words, the workspace's model and the whole workbook if you attach one,
and reads records as needed within your access. A model-change explanation sends differences and
counts without record values. A history explanation includes names of records, people, change sets
and files only at values. Read the disclosure beside the action before asking.

An outside provider receives this information under your organisation's agreement with it. A
provider hosted inside your organisation can keep its requests there. Send levels do not govern
what an external MCP assistant does with permitted data after reading it. Check its service and
retention policy separately. [AI and your data](/docs/use/ai-and-your-data/) explains each feature's
information, access and limits.

### Review the proposal and its evidence

AI can misunderstand instructions, and text in reference data can mislead an assistant. Inspect
the proposed records, relationships and model, not just its explanation. Proposed mappings and
loads wait in a change set for your correction, approval and publication. The built-in assistant
cannot activate, approve or publish. A whole-type model migration has a different review: a person's
explicit migration confirmation changes live data and its model together.

Questions in words become editable filters rather than record changes. Explanations cite facts
computed by refiroo; follow those references before deciding. The explanation can be wrong, and
does not certify that a change is safe. If the provider fails, model and history facts remain
available. See [Work with an assistant](/docs/journeys/work-with-an-assistant/) for the complete paths.

A matching saved workbook layout can be loaded without an assistant session. That ordinary loading
path can also activate a changed draft when the requester has **Model release** permission. Review
the shown next steps rather than assuming every task ends in the same kind of proposal. See
[Loading with the assistant](/docs/use/loading-with-the-assistant/).

### Costs and retained information

Requests and assistant turns can incur charges or consume a subscription allowance, including
failed or discarded work. Operations staff can inspect who asked, the purpose, outcome, tokens
and reported cost on **Settings › Administration › AI**. An absent cost is not proof of free use.
A saved workbook layout that fits the next file can avoid another assistant session.

Call records are kept. Request and answer text is absent from the call log by default; an
operator can enable it for a limited period, normally seven days. This does not remove the
separate assistant task: its instructions, proposal, checks and workbook normally remain for
90 days after completion or the last change. Session files and transcripts remain while the task
can continue, including after a stop or failure and while a loaded change set awaits publication.
They are cleaned up when finished work is next checked, or on expiry. Published data and history
remain. The provider's retention is separate. [Running AI](/docs/run/ai/) explains configuration,
retention and billing in full.

External assistant calls have a separate record of the caller, tool, argument names and outcome,
without argument values. You can end a personal assistant's session from your account. A security
administrator can block an assistant or deactivate its client; access stops on its next call.
See [Agent access](/docs/administer/agent-access/).

Report suspected vulnerabilities privately to **security@refiroo.org**, or use the repository's private reporting option described in its [security policy](https://github.com/refiroo/refiroo/blob/main/SECURITY.md).
