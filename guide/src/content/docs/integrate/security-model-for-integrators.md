---
title: Security for integrators
description: Understand permissions, narrowed writes and the identity recorded for API work.
reader: integrator
---

Give each system its own [client](/docs/administer/clients/) and grant only the work it needs. Authentication establishes the caller; the audience selects an interface; grants decide what that caller can do. A valid token alone is not permission to read or write data.

## Management roles and workspace scope

A management role contains action groups, such as Browse, Bulk and import, Work in change sets, Publish or Feed. Use the [security catalogue and grant operations](/docs/api/?api=management#tag/security) to discover and administer them. A grant can apply at the instance or to one workspace. An instance grant applies to present and future workspaces.

Browse permits reading throughout its workspace. Application and record-type narrowing limits writes, not reads; data that must be hidden from some readers needs a separate workspace. Collections show only resources the caller may access. A direct request for a named resource outside that access is refused.

A narrowed write grant applies to the action group used by the operation. A Bulk and import allowance does not imply permission to edit live individually or publish. Several grants for the same action can add their allowed types together. A relationship write is allowed when either endpoint's type is allowed. Cascading deletion must also be allowed for the records and relationships it removes; publishing must be allowed for the types the change set affects, including the live records it replaces or deletes.

A single write or publication is refused as a whole. A batch or import reports refusals per item according to its failure policy. Previews show the same permission refusals as execution. See [Bulk writes](/docs/integrate/writing-in-bulk/) and [Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/).

`FORBIDDEN` identifies the missing action and workspace, and names refused record types where applicable. Ask the administrator to review that grant; renewing the same token does not add permissions. A grant that refers to applications or types removed by a model release is stale and allows nothing until corrected. Deployment capabilities also apply: a role cannot enable an operation the deployment has disabled.

## Consumer API access

Consumer data routes accept clients only. Each client needs a grant for the named API in each workspace it reads. A management role, including Security administrator, does not replace this grant. Use a token with the consumer audience; the wrong audience is refused as `TOKEN_INVALID`. The API index accepts a consumer token and lists the APIs granted in that workspace, or a management token with Browse and lists all its APIs. Each definition’s OpenAPI document is public and needs no token. See [Consumer APIs](/docs/integrate/consumer-apis/), [Get a token](/docs/guide/integrate/get-a-token/) and [Roles and grants](/docs/administer/roles-and-grants/).

## Jobs and changing access

Permissions and active state are checked on requests and at each job step. A job runs as its original requester, even when someone else can inspect or confirm it. Revoking that requester's permission or deactivating them can stop a running job at its next step. Confirmation checks the requester again; refusal leaves the job waiting. Inspect committed chunks before deciding how to recover a partially applied job.

The requester can read, follow, cancel and confirm their own job. Other callers need the action group for that job kind in its workspace. See [Jobs](/docs/integrate/jobs/) for state and recovery. A write without an identified requester fails closed with `WRITER_UNKNOWN`; report it with its request reference as an engine problem.

## Trace who did the work

Read [record history](/docs/api/?api=management#tag/objects) for changes to one record and the [changes operations](/docs/api/?api=management#tag/changes) for visible changes across workspaces. The actor identifies the person or client. The cause identifies work applied by a job or publication. A recorded channel identifies how work reached the engine where supplied; it does not confer permission. Job changes name their requester; applied publication changes name the publisher. Names reflect the identity's current name. Engine work is distinguished from older entries with no recorded actor.

The history of a record can include changed values. The raw change feed identifies changed fields without their values, and consumer record events omit actor identity. Choose the appropriate interface for an audit export rather than inferring authorship from a consumer event.

Security administrators can read [security events](/docs/api/?api=management#tag/security) for sign-in outcomes and changes to people, groups, roles, grants, clients and signing keys. They contain no passwords, secrets or keys. Security administration does not grant Browse over every workspace's data history. See [Who changed what](/docs/administer/audit/) for the browser views.

## Correct access-administration refusals

| Refusal | Recovery |
| --- | --- |
| `GRANT_NOT_FOUND` or `ROLE_NOT_FOUND` | Read the current grants or roles and use the intended existing identity. |
| `GRANT_SCOPE_INVALID` | Correct the combination of role or consumer API and scope using the grant operation's schema. |
| `GRANT_SCOPE_UNKNOWN` | Choose applications, types or an API present in that workspace's model. |
| `ROLE_NAME_TAKEN` | Choose a distinct name. |
| `ROLE_PREDEFINED` | Copy the predefined role into a custom role before editing. |
| `ROLE_IN_USE` | Reassign or remove its grants before deleting the custom role. |
| `LAST_SECURITY_ADMINISTRATOR` | Retain an active person with instance Security administration. A client does not satisfy this safeguard. |

Model-draft history refusals such as `INVALID_OPERATION`, `NOTHING_TO_APPLY`, `NOTHING_TO_UNDO`, `NOTHING_TO_REDO` and `OPERATION_HAS_DEPENDANTS` belong to [Model and release operations](/docs/integrate/model-and-release-operations/).

For leaked credentials, coordinate [client-secret rotation](/docs/administer/clients/#secrets-and-rotation) with the administrator. Webhook signing keys have a separate lifecycle and can be rotated with zero overlap for immediate replacement; see [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/#verify-before-accepting).

## Automate access administration

A client holding Security administration can manage people, groups and roles through the [security operations](/docs/api/?api=management#tag/security). Discover the current resources and versions, make the intended change, then reread access where needed. Keep administrative credentials separate from the client that loads or consumes data. For the corresponding browser tasks, see [People and groups](/docs/administer/people-and-groups/), [Roles and grants](/docs/administer/roles-and-grants/) and [Sign-in](/docs/administer/sign-in/).

| Refusal | Recovery |
| --- | --- |
| `ACTION_GROUP_UNKNOWN` | Read the action catalogue and choose a known group. |
| `USER_NOT_FOUND`, `GROUP_NOT_FOUND` or `GROUP_MEMBER_NOT_FOUND` | Refresh the people, groups or membership before changing it. |
| `USERNAME_TAKEN` or `GROUP_NAME_TAKEN` | Choose an unused username or group name. |
| `GROUP_FROM_PROVIDER` | Change membership in the sign-in provider; it is synchronized at sign-in. |
| `GROUP_CLAIM_TAKEN` | Use the existing group for that provider claim or choose a different claim. |
| `SIGN_IN_PROVIDER_NOT_FOUND` or `SIGN_IN_PROVIDER_KEY_TAKEN` | Select an existing provider or give the new one a distinct key. |
| `SIGN_IN_PROVIDER_IN_USE` | Add another provider instead of changing the issuer people already use. |
| `SIGN_IN_PROVIDER_SECRET_REQUIRED` | Supply the new provider's client secret when changing issuer. |
| `SIGN_IN_PROVIDER_UNREACHABLE` | Check the provider address and reported connection or metadata failure. |
| `NO_WORKING_PROVIDER` | Complete a successful sign-in through an enabled provider before disabling local sign-in. |
| `LAST_LOCAL_ADMINISTRATOR` | Retain another permitted local administrator or restore local sign-in before removing this one. |
| `LOCAL_SIGN_IN_OFF` | Use the configured provider; local passwords are restricted to administrators retained for recovery. |

Linking identities moves a provider sign-in between people; it is not a way to merge arbitrary access. `IDENTITY_NOT_FOUND` or `NO_IDENTITY_TO_LINK` requires the source's existing provider identity. `IDENTITY_PROVIDER_TAKEN` means the target already has that provider. `LINK_SAME_PERSON` requires two different people. `LINK_TARGET_DEACTIVATED` requires activating the intended target first. `PERSON_HAS_ACCESS` requires reviewing and removing the source's own access or choosing the opposite linking direction, as the refusal explains.

## Keep person-only flows separate

Client credentials do not create a person's password, second factor or browser session. Person-only operations refuse a client as `NOT_A_PERSON`. A browser integration acting for a person uses the [sign-in operations](/docs/api/?api=management#tag/oauth) and the person's [security operations](/docs/api/?api=management#tag/security); see [Signing in and tokens](/docs/integrate/signing-in-and-tokens/#browser-sessions).

| Refusal | Recovery |
| --- | --- |
| `PASSWORD_INCORRECT` | Ask the person for their current password again. |
| `PASSWORD_REJECTED` | Choose a password satisfying the reason returned. |
| `SIGN_IN_SLOWED` | Respect the returned wait interval; repeated attempts do not speed recovery. |
| `PROOF_REQUIRED` | Obtain the person's required password or authenticator proof. |
| `CODE_INCORRECT` | Obtain a fresh valid code; used codes cannot be replayed. |
| `SECOND_FACTOR_EXISTS` | Read the existing enrollment instead of starting another. |
| `SECOND_FACTOR_NOT_FOUND` | Start or refresh the enrollment appropriate to the operation. |
| `SECOND_FACTOR_REQUIRED` | Set up another permitted factor before removing the last required one. |
| `PASSWORD_REQUIRED` | Passkeys require a local password account; a provider-only account cannot enroll one. |
| `PASSKEY_NOT_FOUND` or `SESSION_NOT_FOUND` | Refresh the person's current keys or open sessions. |
| `TOO_MANY_PASSKEYS` | Remove an unused key before adding another. |

## Mail administration failures

Use the [mail operations](/docs/api/?api=management#tag/mail) with the required administrative permission; [Sign-in and mail setup](/docs/run/sign-in-and-mail-setup/) explains deployment preparation. `MAIL_PASSWORD_REQUIRED` means resend the password after a host or port change. `MAIL_SEND_FAILED` requires correcting the reported test-delivery failure. `NO_EMAIL` needs an address on the person, or a securely passed link where that operation offers one. `MESSAGE_BEING_SENT` needs a short wait; `MESSAGE_NOT_WAITING` means a message is no longer queued to stop. `NOT_FOUND` on a message requires refreshing the queue and selecting an existing message. Message text is not available through the administration API.

`ROUTE_NOT_DECLARED` means an operation lacks an engine permission declaration. Like `WRITER_UNKNOWN`, it fails closed and needs investigation using the request reference; adding a broader grant cannot repair it.

## Distinguish a role from the action it grants

Use the [action catalogue](/docs/api/?api=management#tag/security) and caller permissions to discover effective rights. Browse includes exports and model-aware queries, but Feed is separate. Bulk and import permits batches and file loads; Copy and move additionally needs Browse at the source and, for a move, Work in change sets there. Model authoring and release permissions are separate from workspace data writes. Operations permits configuration, detailed health and metrics; a metrics scraper uses its own client with that permission.

Application and record-type narrowing combine as alternatives within a grant. Grants for the same action add together, and any unnarrowed grant allows all types for that action in its scope. A type change needs permission for both the type left and the type taken. Migrations and publication withdrawals are not type-narrowed. Shared open change sets can be edited by authorised collaborators; creation does not make them private.

Jobs continue to act for the original requester. A refusal after that requester loses access includes their identity in `requestedBy`; another administrator confirming the job does not replace that identity. A source file is available to its uploader and the appropriate Bulk and import holders, rather than every signed-in client. Check the operation’s declared action instead of inferring access from ownership.
