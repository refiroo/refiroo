# security

Who may do what is decided by roles. A role is a set of action groups (Browse, Edit live, Publish and so on); a grant gives a role to a person, a group or a client, for the whole instance or one workspace, where it may narrow writes to applications and record types. People sign in with a password or an OpenID Connect provider and may add a second factor; clients sign in through the `oauth` operations. All but those under `/api/v1/me` need Security administration at the instance.

1. Give access: make the person (`POST /api/v1/users`), add them to a group, and grant the group a role (`POST /api/v1/grants`).
2. Check it: `GET /api/v1/workspaces/{workspace_key}/access` says who can do what in a workspace, and `GET /api/v1/security-events` says who changed it.

## GET /api/v1/me

Title: Read who I am

Tells who the token belongs to, a person or a client, and for a person how they signed in. Use it after signing in to show the caller and to learn the `sessionId` that `GET /api/v1/me/sessions` marks as current.

## GET /api/v1/me/permissions

Title: Read what I may do in a workspace

Lists the action groups the caller holds in a workspace, each with its narrowing and the grants it comes from. Use it to decide what to offer; the server checks every request again.

### Parameters

- workspaceKey: The workspace; the default workspace without it.

### Errors

- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace

## GET /api/v1/me/action-groups

Title: List the action groups I hold anywhere

Lists every action group the caller holds at the instance or in any workspace, in the catalogue's order. Use it to decide which settings pages to show: a page is offered to whoever holds its group somewhere.

## GET /api/v1/me/grants

Title: List my grants

Lists the grants that give the caller their roles: their own and, for a person, those of their groups, whose `principal` is then the group.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/me/sessions

Title: List my sessions

Lists the caller's open sessions, the one the request was made in marked `current`. A person whose sign-in an administrator manages sees only the current one.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 NOT_A_PERSON: the caller is a client, which has no sessions
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## DELETE /api/v1/me/sessions/{session_id}

Title: Sign out one of my sessions

Ends one of the caller's sessions: its tokens are refused from the next request and it renews no more. A person whose sign-in an administrator manages can end only the session they are in.

### Parameters

- session_id: The session's `id`, from `GET /api/v1/me/sessions`.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: the sign-in is managed and this is another session
- 404 SESSION_NOT_FOUND: no open session of the caller has this ID

## DELETE /api/v1/me/sessions

Title: Sign out everywhere

Ends all the caller's sessions, the current one included; they sign in again to continue. Use `DELETE /api/v1/users/{user_id}/sessions` to do the same for another person.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in

## POST /api/v1/me/password

Title: Change my password

Changes the caller's password and ends every other session. A wrong current password counts like a wrong sign-in, so repeated tries are slowed.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 422 PASSWORD_INCORRECT: `currentPassword` is wrong
- 422 PASSWORD_REJECTED: `newPassword` breaks the password rules; `details.reason` says which
- 429 SIGN_IN_SLOWED: too many wrong passwords; wait `details.waitSeconds`

## GET /api/v1/me/second-factor

Title: Read my second factor

Says whether the caller has an authenticator app, how many recovery codes are left and how many passkeys they have, and whether the instance requires a second factor with a password.

### Errors

- 403 NOT_A_PERSON: the caller is a client

## POST /api/v1/me/second-factor

Title: Start setting up an authenticator app

Makes a secret for an authenticator app and answers it once, as a key, an `otpauth://` address and a QR code. The app works after `POST /api/v1/me/second-factor/confirmation`; starting again before that replaces the secret.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 409 SECOND_FACTOR_EXISTS: an app is already confirmed
- 409 PASSWORD_REQUIRED: the person has no password

## POST /api/v1/me/second-factor/confirmation

Title: Confirm the authenticator app

Switches the second factor on with a code the app shows, and answers ten recovery codes once. Keep them: each signs in once when the app is not at hand.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 404 SECOND_FACTOR_NOT_FOUND: no secret waits to be confirmed
- 422 CODE_INCORRECT: the code is wrong or was used already
- 429 SIGN_IN_SLOWED: too many wrong codes; wait `details.waitSeconds`

## POST /api/v1/me/second-factor/recovery-codes

Title: Make new recovery codes

Replaces the recovery codes with ten new ones, answered once; the old ones stop working. `code` is a code from the app or an unused recovery code.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 404 SECOND_FACTOR_NOT_FOUND: no authenticator app is set up
- 422 CODE_INCORRECT: the code is wrong or was used already
- 429 SIGN_IN_SLOWED: too many wrong codes; wait `details.waitSeconds`

## DELETE /api/v1/me/second-factor

Title: Remove my authenticator app

Removes the caller's authenticator app and recovery codes, proved with a code from the app or a recovery code. While the instance requires a second factor, it is refused unless the caller has a passkey; an administrator can still remove it with `DELETE /api/v1/users/{user_id}/second-factor`.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 404 SECOND_FACTOR_NOT_FOUND: no authenticator app is set up
- 409 SECOND_FACTOR_REQUIRED: the instance requires one and the caller has no passkey
- 422 CODE_INCORRECT: the code is wrong or was used already
- 429 SIGN_IN_SLOWED: too many wrong codes; wait `details.waitSeconds`

## GET /api/v1/me/passkeys

Title: List my passkeys

Lists the caller's passkeys by the names they gave them, never the credential. A passkey is added in a browser on the engine's own page, `/oauth/passkeys/new`, so no operation adds one.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## PATCH /api/v1/me/passkeys/{passkey_id}

Title: Rename my passkey

Renames one of the caller's passkeys, so they can tell their devices apart.

### Parameters

- passkey_id: The passkey's `id`.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 404 PASSKEY_NOT_FOUND: the caller has no passkey with this ID

## DELETE /api/v1/me/passkeys/{passkey_id}

Title: Remove my passkey

Removes one of the caller's passkeys. `proof` in the body is their password, or a code from the app or a recovery code, so a stolen session cannot strip a person's passkeys; a person with neither a password nor an app sends none.

### Parameters

- passkey_id: The passkey's `id`.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 403 SIGN_IN_MANAGED: an administrator manages the sign-in
- 404 PASSKEY_NOT_FOUND: the caller has no passkey with this ID
- 409 SECOND_FACTOR_REQUIRED: required, and this is the last passkey with no app
- 422 PROOF_REQUIRED: no `proof` was sent
- 422 CODE_INCORRECT: the proof is wrong
- 429 SIGN_IN_SLOWED: too many wrong proofs; wait `details.waitSeconds`

## GET /api/v1/action-groups

Title: List the action groups

Lists the action groups roles are made of, each with its actions and the operations that declare them. Use it to build a role editor, or to see which group an operation needs.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance

## GET /api/v1/roles

Title: List roles

Lists the predefined roles first, then the custom ones in the order they were made.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/roles

Title: Create a role

Creates a custom role from `actionGroups`, or from the groups of the role named in `copiedFrom`; its `key` is made from its name. The role does nothing until a grant gives it.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 ROLE_NOT_FOUND: `copiedFrom` names no role
- 409 ROLE_NAME_TAKEN: another role has this name, ignoring case
- 422 ACTION_GROUP_UNKNOWN: an action group does not exist
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## GET /api/v1/roles/{role_key}

Title: Get a role

Reads one role with the number of grants that give it.

### Parameters

- role_key: The role's `key`, for example `reader`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 ROLE_NOT_FOUND: no role has this key

## PATCH /api/v1/roles/{role_key}

Title: Change a role

Changes a custom role's name, description or action groups. Its holders gain or lose the groups at their next request. A predefined role cannot change; copy it with `copiedFrom`.

### Parameters

- role_key: The role's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 ROLE_NOT_FOUND: no role has this key
- 409 ROLE_PREDEFINED: the role is predefined
- 409 ROLE_NAME_TAKEN: another role has this name
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 LAST_SECURITY_ADMINISTRATOR: it would leave no active person with Security administration
- 422 ACTION_GROUP_UNKNOWN: an action group does not exist
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## DELETE /api/v1/roles/{role_key}

Title: Delete a role

Deletes a custom role that no grant gives. Remove its grants first, or change the role instead.

### Parameters

- role_key: The role's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 ROLE_NOT_FOUND: no role has this key
- 409 ROLE_PREDEFINED: the role is predefined
- 409 ROLE_IN_USE: a grant gives it; `details.grants` counts them

## GET /api/v1/users

Title: List people

Lists people in the order they were made, each with the roles they hold, directly or through a group, and where. A person is never deleted, so deactivated people are listed too.

### Parameters

- q: Part of the name or e-mail address, ignoring case.
- active: `true` for active people only, `false` for deactivated ones.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/users

Title: Create a person

Creates a person with no password; their e-mail address is the name they sign in with. Give them a way in with `POST /api/v1/users/{user_id}/password-reset`, and access with `POST /api/v1/grants` or a group.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 EMAIL_TAKEN: another person has this address, ignoring case
- 422 REQUEST_VALIDATION_ERROR: the name or address is invalid

## GET /api/v1/users/{user_id}

Title: Get a person

Reads one person with their roles, provider identities, second factor and passkey count. Read it before changing the person: it gives the `version` to send.

### Parameters

- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID

## PATCH /api/v1/users/{user_id}

Title: Change a person

Changes a person's name or address, deactivates them with `active: false` or restores them. Deactivating ends their sessions and refuses their tokens from the next request. A person is never deleted.

### Parameters

- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 EMAIL_TAKEN: another person has this address
- 409 LAST_SECURITY_ADMINISTRATOR: deactivating would leave no active Security administrator
- 409 LAST_LOCAL_ADMINISTRATOR: the last person who keeps password sign-in while it is off
- 422 EMAIL_REQUIRED: an active person needs an address
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/users/{user_id}/password-reset

Title: Make a password link

Makes a one-time link that sets the person's password, answered this once and valid for the operator's `PASSWORD_RESET_HOURS`. It replaces any earlier link, and using it ends the person's sessions. With `send: true` it is also mailed to their address.

### Parameters

- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 409 LOCAL_SIGN_IN_OFF: password sign-in is off for this person
- 409 MAIL_NOT_SET_UP: `send` is true and mail is not set up
- 409 NO_EMAIL: `send` is true and the person has no address

## POST /api/v1/users/{user_id}/identities

Title: Link a provider identity to a person

Moves the provider identities and provider-group memberships of `fromUserId`, the person a provider sign-in made, onto this person, and deactivates that person. Use it when someone who already has an account first signs in through a provider.

### Parameters

- user_id: The person who keeps the identities.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: either ID names no person
- 409 VERSION_CONFLICT: `expectedVersion` is not the person's current version
- 409 LINK_TARGET_DEACTIVATED: the person who keeps the identities is deactivated
- 409 PERSON_HAS_ACCESS: `fromUserId` has a password, roles or local groups
- 409 NO_IDENTITY_TO_LINK: `fromUserId` has no provider identity
- 409 IDENTITY_PROVIDER_TAKEN: the person already signs in with one of those providers
- 422 LINK_SAME_PERSON: `fromUserId` is this person

## DELETE /api/v1/users/{user_id}/identities/{provider}

Title: Unlink a provider identity

Removes the person's identity at a provider, their memberships in its groups and the sessions it started. Their next sign-in through that provider makes a new person.

### Parameters

- user_id: The person's `id`.
- provider: The provider's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 404 IDENTITY_NOT_FOUND: the person has no identity at this provider

## DELETE /api/v1/users/{user_id}/second-factor

Title: Remove a person's second factor

Removes a person's authenticator app and recovery codes, for someone who lost the phone and the codes. When the instance requires a second factor they set one up again at their next sign-in.

### Parameters

- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 404 SECOND_FACTOR_NOT_FOUND: the person has no authenticator app

## GET /api/v1/users/{user_id}/passkeys

Title: List a person's passkeys

Lists a person's passkeys by the names they gave them, never the credential.

### Parameters

- user_id: The person's `id`.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## DELETE /api/v1/users/{user_id}/passkeys/{passkey_id}

Title: Remove a person's passkey

Removes a passkey of a person who lost the device. It needs no proof and is not refused when the instance requires a second factor; a security event records it.

### Parameters

- user_id: The person's `id`.
- passkey_id: The passkey's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 404 PASSKEY_NOT_FOUND: the person has no passkey with this ID

## DELETE /api/v1/users/{user_id}/sessions

Title: Sign a person out everywhere

Ends all of a person's sessions: their tokens are refused from the next request. It does not deactivate the person; they can sign in again.

### Parameters

- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID

## GET /api/v1/users/{user_id}/grants

Title: List a person's grants

Lists the grants that apply to a person: those made to them and those of their groups, a group's naming the group.

### Parameters

- user_id: The person's `id`.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 USER_NOT_FOUND: no person has this ID
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/groups

Title: List groups

Lists groups in the order they were made, with their member counts.

### Parameters

- q: Part of the name, ignoring case.
- memberId: Only the groups this person belongs to.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/groups

Title: Create a group

Creates a group of people; a grant to it applies to its members. With `source` it stands for a provider's group ahead of its members' sign-ins, and its members come from those sign-ins alone.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 SIGN_IN_PROVIDER_NOT_FOUND: `source.provider` names no provider
- 409 GROUP_NAME_TAKEN: another group has this name, ignoring case
- 409 GROUP_CLAIM_TAKEN: the provider's claim value has a group already
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## GET /api/v1/groups/{group_id}

Title: Get a group

Reads one group. Read it before changing it: it gives the `version` to send.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID

## PATCH /api/v1/groups/{group_id}

Title: Change a group

Changes a group's name or description. Its members and grants stay.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 GROUP_NAME_TAKEN: another group has this name
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## DELETE /api/v1/groups/{group_id}

Title: Delete a group

Deletes a group with its memberships and its grants; its members lose what the group gave them at their next request.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 409 LAST_SECURITY_ADMINISTRATOR: it would leave no active person with Security administration

## GET /api/v1/groups/{group_id}/members

Title: List a group's members

Lists the people in a group in the order they were made.

### Parameters

- group_id: The group's `id`.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/groups/{group_id}/members

Title: Add a person to a group

Adds one person; adding someone already in the group changes nothing. A provider group's members come from sign-ins and cannot be changed here. To add many, use `POST /api/v1/groups/{group_id}/members/batch`.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 404 USER_NOT_FOUND: `userId` names no person
- 409 GROUP_FROM_PROVIDER: the group's members come from its provider

## POST /api/v1/groups/{group_id}/members/batch

Title: Add several people to a group

Adds up to 500 people in one transaction, by ID or by e-mail address as pasted, in any case. Each input answers what it did; with `dryRun` it answers what it would do and changes nothing. A deactivated person is not added.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 409 GROUP_FROM_PROVIDER: the group's members come from its provider
- 422 REQUEST_VALIDATION_ERROR: more than 500 inputs, or a field is invalid

## POST /api/v1/groups/{group_id}/members/removal

Title: Remove several people from a group

Takes up to 500 people out in one transaction. It is refused whole when it would leave no active Security administrator.

### Parameters

- group_id: The group's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 409 GROUP_FROM_PROVIDER: the group's members come from its provider
- 409 LAST_SECURITY_ADMINISTRATOR: it would leave no active person with Security administration
- 422 REQUEST_VALIDATION_ERROR: no or more than 500 IDs

## DELETE /api/v1/groups/{group_id}/members/{user_id}

Title: Remove a person from a group

Takes one person out of a group; the group's grants stop applying to them at their next request.

### Parameters

- group_id: The group's `id`.
- user_id: The person's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GROUP_NOT_FOUND: no group has this ID
- 404 USER_NOT_FOUND: no person has this ID
- 404 GROUP_MEMBER_NOT_FOUND: the person is not in the group
- 409 GROUP_FROM_PROVIDER: the group's members come from its provider
- 409 LAST_SECURITY_ADMINISTRATOR: it would leave no active person with Security administration

## GET /api/v1/grants

Title: List grants

Lists grants in the order they were made. The filters combine.

### Parameters

- principalId: A person's, client's or group's `id`.
- workspaceKey: Only the grants made in this workspace; instance grants are not shown.
- roleKey: Only the grants of this role.
- consumerApi: Only the grants of this consumer API.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/grants

Title: Create a grant

Gives a role to a person, a client or a group, at the instance or in one workspace (never both), from the principal's next request. In a workspace it may narrow writes to applications and record types of its model. Instead of `role`, `consumerApi` lets a client read a consumer API in one workspace.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 ROLE_NOT_FOUND: `role` names no role
- 404 USER_NOT_FOUND: the principal is a person who does not exist
- 404 CLIENT_NOT_FOUND: the principal is a client that does not exist
- 404 GROUP_NOT_FOUND: the principal is a group that does not exist
- 404 WORKSPACE_NOT_FOUND: `scope.workspaceKey` names no workspace
- 422 GRANT_SCOPE_INVALID: the scope or the role cannot be granted there
- 422 GRANT_SCOPE_UNKNOWN: the workspace's model lacks an application, type or API
- 422 CONSUMER_API_CLIENTS_ONLY: `consumerApi` for a person or a group
- 422 REQUEST_VALIDATION_ERROR: neither or both of `role` and `consumerApi`

## DELETE /api/v1/grants/{grant_id}

Title: Remove a grant

Removes a grant; it stops applying on the principal's next request.

### Parameters

- grant_id: The grant's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 GRANT_NOT_FOUND: no grant has this ID
- 409 LAST_SECURITY_ADMINISTRATOR: it would leave no active person with Security administration

## GET /api/v1/workspaces/{workspace_key}/grant-options

Title: List what a grant in a workspace can name

Lists the applications, record types and consumer APIs of the workspace's model, by key and name, for building a grant. A Security administrator holds no data rights, so this read needs none.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 503 MODEL_REGISTRY_UNAVAILABLE: the workspace runs no installed release

## GET /api/v1/workspaces/{workspace_key}/access

Title: List who has access to a workspace

Lists every grant that applies in the workspace, made there or at the instance; a grant to a group names the group. Use it to review who can do what.

### Parameters

- workspace_key: The workspace's key.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/clients

Title: List clients

Lists clients in the order they were made. Clients made for assistant tasks are left out unless `kind=session`.

### Parameters

- q: Part of the name, ignoring case.
- active: `true` for active clients only, `false` for deactivated ones.
- kind: `api`, `agent` or `session`.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/clients

Title: Create a client

Creates a client for a program and answers its first secret once; it is never shown again. The client has no access until a grant gives it a role. Use `kind: agent` for an assistant that connects to `/mcp`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## GET /api/v1/clients/{client_id}

Title: Get a client

Reads one client with its valid secrets, never their values, and the roles and consumer APIs it holds.

### Parameters

- client_id: The client's `id`, which is its OAuth `client_id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 CLIENT_NOT_FOUND: no client has this ID

## PATCH /api/v1/clients/{client_id}

Title: Change a client

Renames a client, or deactivates it with `active: false`: it obtains no token and the tokens it holds are refused from the next request. A client is never deleted.

### Parameters

- client_id: The client's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 CLIENT_NOT_FOUND: no client has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/clients/{client_id}/secrets

Title: Add a client secret

Adds a secret and answers it once. The client's other secrets stay valid for `overlapHours`, so the program using it can switch without a gap; `0` stops them at once.

### Parameters

- client_id: The client's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 CLIENT_NOT_FOUND: no client has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 CLIENT_HAS_NO_SECRETS: the client belongs to an assistant task
- 422 REQUEST_VALIDATION_ERROR: `overlapHours` is outside 0 to 168

## DELETE /api/v1/clients/{client_id}/secrets/{secret_id}

Title: Stop a client secret

Stops one secret at once, before its overlap ends, and answers the client. It does not check that another secret is left: a client without a valid secret cannot sign in.

### Parameters

- client_id: The client's `id`.
- secret_id: The secret's `id`, from the client's `secrets`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 CLIENT_NOT_FOUND: no client has this ID
- 404 CLIENT_SECRET_NOT_FOUND: the client has no secret with this ID

## GET /api/v1/token-signing-keys

Title: List token signing keys

Lists the keys that sign access tokens, newest first, with their state. Never a private key; the public keys are at `GET /oauth/jwks`.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/token-signing-keys/rotation

Title: Rotate the token signing key

Makes a new signing key for the tokens issued from now on and answers it. The previous key keeps verifying the tokens it signed until they expire; with `immediate: true`, after a leak, it does not, and their holders obtain new tokens.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance

## GET /api/v1/security-events

Title: List security events

Lists changes to people, groups, roles, grants, clients, signing keys and sign-in settings, and sign-ins, newest first, each naming who made it. Events never hold a password, secret, link or key.

### Parameters

- principalId: A person's, client's or group's `id`: the events they made or that are about them.
- aggregateType: Only events of this kind; repeat it for several.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/sign-in-providers

Title: List sign-in providers

Lists the OpenID Connect providers people sign in with, in the order they were made. Never a secret.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/sign-in-providers

Title: Connect a sign-in provider

Connects an OpenID Connect provider; people then sign in with its button. An enabled provider is read first: its discovery document must name this issuer and it must publish keys. Register `redirectUri` with the provider; the answer says it.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 SIGN_IN_PROVIDER_KEY_TAKEN: another provider has this key, or it is reserved
- 422 SIGN_IN_PROVIDER_UNREACHABLE: the provider cannot be used; `details.reason` says why
- 422 REQUEST_VALIDATION_ERROR: a field is invalid, or `key` has a bad form

## GET /api/v1/sign-in-providers/local

Title: Read local sign-in

Says whether people sign in with a password, whether a password needs a second factor, and how many people keep password sign-in while it is off.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance

## PATCH /api/v1/sign-in-providers/local

Title: Change local sign-in

Turns password sign-in off or on and requires a second factor with a password or not. While it is off, only the people who keep it, made on the server, sign in with a password; clients are not affected. Providers' sign-ins are never asked for a second factor.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 NO_WORKING_PROVIDER: no enabled provider has signed anyone in yet
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## GET /api/v1/sign-in-providers/{key}

Title: Get a sign-in provider

Reads one provider with the addresses to register with it and how many people have signed in with it.

### Parameters

- key: The provider's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 SIGN_IN_PROVIDER_NOT_FOUND: no provider has this key

## PATCH /api/v1/sign-in-providers/{key}

Title: Change a sign-in provider

Changes a provider's settings; a new `clientSecret` replaces the saved one. Enabling it, or changing an enabled provider's issuer, reads it first. Disabling it ends the sessions it started. The key never changes.

### Parameters

- key: The provider's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 SIGN_IN_PROVIDER_NOT_FOUND: no provider has this key
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 SIGN_IN_PROVIDER_IN_USE: the issuer changes after people signed in
- 422 SIGN_IN_PROVIDER_SECRET_REQUIRED: the issuer changes without a new `clientSecret`
- 422 SIGN_IN_PROVIDER_UNREACHABLE: the provider cannot be used; `details.reason` says why
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## DELETE /api/v1/sign-in-providers/{key}

Title: Delete a sign-in provider

Deletes a provider nobody has signed in with, with the groups made for it. Otherwise disable it with `PATCH`.

### Parameters

- key: The provider's `key`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 SIGN_IN_PROVIDER_NOT_FOUND: no provider has this key
- 409 SIGN_IN_PROVIDER_IN_USE: people have signed in with it

## Schemas

### ActionGroupList

- items: Every action group, in the catalogue's order.

### ActionGroupResponse

- key: The group's key, which `holding` filters and `GET /api/v1/me/permissions` use.
- name: The group's name, as the interface shows it.
- description: What holding the group lets a caller do.
- actions: The actions the group allows. An operation declares one of them.

### ActionResponse

- key: The action's key, as an operation's `x-action` names it.
- description: What the action covers.
- operations: The operations that declare this action.

### OperationRef

- method: The HTTP method.
- path: The route, as the document names it.

### RoleResponse

- key: The role's key; made from its name, never changed.
- name: The role's name.
- description: What the role is for; null if none.
- predefined: A predefined role is read-only; copy it to change it.
- actionGroups: The keys of the action groups the role holds.
- grants: How many grants give this role.
- version: Rises by one with every change; send it as `expectedVersion`.
- createdAt: When the role was made.
- updatedAt: When the role last changed.

### RoleCreate

- name: The role's name, unique ignoring case; its key is made from it.
- description: What the role is for.
- actionGroups: The keys of the action groups the role holds. Leave it out when copying.
- copiedFrom: The key of a role whose action groups to start from; not with `actionGroups`.

### RoleUpdate

- expectedVersion: The role's `version`.
- name: A new name.
- description: A new description.
- actionGroups: The role's new action groups, replacing the old ones.

### GroupResponse

- id: The group's ID.
- name: The group's name.
- description: What the group is for; null if none.
- members: How many people are in it.
- version: Rises by one with every change; send it as `expectedVersion`.
- createdAt: When the group was made.
- updatedAt: When the group last changed.

### GroupCreate

- name: The group's name, unique ignoring case.
- description: What the group is for.
- source: Makes a provider group; see `GroupSource`.

### GroupSource

A provider group: the provider's key and the value of its groups claim that the group stands for.

- provider: The key of the sign-in provider.
- claimValue: The value of the provider's groups claim this group stands for; one group per value.

### GroupSourceResponse

A provider group's provider and the value of its groups claim that the group stands for.

- provider: The sign-in provider.
- claimValue: The value of the provider's groups claim the group stands for.

### GroupUpdate

- expectedVersion: The group's `version`.
- name: A new name.
- description: A new description.

### GroupMemberResponse

- id: The person's ID.
- email: The person's e-mail address; null for a deactivated person.
- name: The person's name.
- active: False once the person is deactivated.
- seenAt: In a provider group, when a sign-in last named them in it; null otherwise.

### GroupMemberAdd

- userId: The person's ID.

### GroupMembersAdd

Several people added to a group at once: by their IDs, or by e-mail addresses as pasted, in any case. `dryRun` answers what would happen and changes nothing.

- userIds: People's IDs, up to 500 together with `identifiers`.
- identifiers: E-mail addresses as pasted, in any case, up to 500 together with `userIds`.
- dryRun: Answer what would happen and change nothing.

### GroupMembersRemove

Several people taken out of a group at once.

- userIds: People's IDs, 1 to 500.

### GroupMemberOutcome

What adding or removing one of several people did, or would do.

- input: The person's ID, or the e-mail address as sent.
- outcome: `added`, `toAdd` (a dry run's `added`), `alreadyMember`, `deactivated` (not added), `notFound`, `removed` or `notMember`.
- member: The person the input names; null where nobody has it.

### GroupMembersResult

- items: What each input did, in the order sent: IDs first, then addresses.
- changed: How many people were added or removed; 0 for a dry run.

### GrantCreate

- principal: Who receives the grant.
- role: The role's key. Send this or `consumerApi`.
- consumerApi: A consumer API's key, granted to a client to read in one workspace; never narrowed.
- scope: Where the grant applies.

### GrantPrincipal

- kind: `user`, `client` or `group`.
- id: The principal's ID.

### GrantScope

Where a grant applies: the instance (`instance: true`), or one workspace, optionally narrowing writes to applications and record types of its model.

- instance: `true` for the whole instance, every workspace included; then no `workspaceKey` and no narrowing.
- workspaceKey: The workspace the grant applies in; not with `instance`.
- applications: Narrows the writes of the role's groups to these applications' keys; empty: not narrowed.
- recordTypes: Narrows the writes of the role's groups to these record types' keys; empty: not narrowed.

### GrantResponse

- id: The grant's ID.
- principal: Who holds it.
- role: The role; null for a consumer API grant.
- consumerApi: The consumer API the grant lets its holder read; null for a role grant.
- scope: Where it applies.
- stale: The narrowing names an application or record type the workspace's model no longer has, or the consumer API is no longer declared; those allow nothing.
- createdAt: When the grant was made.

### GrantPrincipalResponse

- kind: `user`, `client` or `group`.
- id: The principal's ID.
- name: The principal's name.

### GrantRoleResponse

- key: The role's key.
- name: The role's name.

### GrantScopeResponse

- instance: True for the whole instance, every workspace included.
- workspaceKey: The workspace the grant applies in; null for an instance grant.
- applications: Writes are narrowed to these applications' keys; empty: not narrowed.
- recordTypes: Writes are narrowed to these record types' keys; empty: not narrowed.
- applicationNames: The applications' names in the workspace's model, in the order of `applications`; a key the model no longer has is given as it is.
- recordTypeNames: The record types' names in the workspace's model, in the order of `recordTypes`.
- missingApplications: Applications of the narrowing that the workspace's model no longer has.
- missingRecordTypes: Record types of the narrowing that the workspace's model no longer has.

### GrantConsumerApiResponse

- key: The consumer API's key.
- name: The API's name in the workspace's model; null when it no longer declares it.

### GrantOption

- key: The key to put in a grant's scope or `consumerApi`.
- name: The name in the workspace's model.

### GrantOptionsResponse

What a grant in a workspace can name, from the workspace's model.

- applications: Applications a grant may narrow to.
- recordTypes: Record types a grant may narrow to.
- consumerApis: Consumer APIs a grant may name.

### PermissionsResponse

- workspaceKey: The workspace the answer is for.
- workspaceLabel: The workspace's label.
- roles: The roles that apply in the workspace, from grants there or at the instance.
- actionGroups: The action groups the caller holds in the workspace, from grants there or at the instance.

### HeldGroup

- key: The action group's key.
- name: The action group's name.
- applications: Writes are narrowed to these applications' keys; empty: not narrowed.
- recordTypes: Writes are narrowed to these record types' keys; empty: not narrowed.
- stale: The narrowing names an application or record type the workspace's model no longer has, which allows nothing.
- sources: The grants that give the group.

### PermissionSource

- grantId: The grant's ID.
- role: The role it gives.
- scope: `workspace`, or `instance` for a grant covering every workspace.
- group: The group the grant reaches the caller through; null for a direct grant.

### HeldAnywhere

An action group the caller holds somewhere.

- key: The action group's key.
- name: The action group's name.
- instance: Held at the instance, so in every workspace.
- workspaces: The workspaces it is held in; empty when held at the instance.

### HeldWorkspace

- key: The workspace's key.
- label: The workspace's label.

### HeldAnywhereList

- items: The groups the caller holds, in the catalogue's order.

### MeResponse

- id: The person's or client's ID.
- kind: `user` or `client`.
- name: The person's or client's name.
- email: The person's e-mail address; null for a client.
- lastSignInAt: A person's last sign-in, or when a client last obtained a token.
- signedInWith: For a person, `password` or the key of the provider they signed in with; null for a client.
- signInProvider: The provider of this session; null for a password sign-in.
- sessionId: A person's current session; null for a client.
- signInManaged: An administrator manages the person's sign-in, so they cannot change their own password, second factor, passkeys or other sessions; always false for a client.

### SessionResponse

- id: The session's ID.
- current: The session the request's token was issued in.
- signedInWith: `password`, or the key of the provider the person signed in with.
- application: The assistant the session was started for; null for a browser.
- userAgent: The browser that signed in, as it named itself.
- createdAt: When the session started.
- lastUsedAt: When the session was last renewed.
- endsAt: When it ends unless renewed sooner, or at the latest.

### PasswordChange

A signed-in person's new password, with the current one.

- currentPassword: The caller's present password.
- newPassword: The new password; the operator's length rules apply, and a common password or the e-mail address is refused.

### PasswordResetRequest

Asks for a one-time password link; with `send` it is also mailed to the person's address.

- send: Also mail the link to the person's address.

### PasswordResetLinkResponse

A one-time link that sets a person's password, answered this once.

- url: The link to pass on; it sets the password once.
- expiresAt: When the link stops working.
- sentTo: The address the link was queued for when `send` was true; otherwise null.

### MySecondFactorResponse

The caller's second factor.

- enabled: An authenticator app is set up and confirmed.
- confirmedAt: When it was confirmed; null without one.
- recoveryCodesLeft: How many recovery codes are unused.
- passkeys: How many passkeys the caller has.
- required: The instance requires a second factor with a password: the last one cannot be removed.

### SecondFactorEnrolment

What the caller needs to set an authenticator app up, answered once.

- secret: The key to type into the app, in base32.
- otpauthUri: The address a QR code carries, in the Key URI Format.
- qrSvg: The QR code as an inline SVG, ready to show.

### SecondFactorCode

A code from the authenticator app, or a recovery code.

- code: A six-digit code from the app, or a recovery code.

### RecoveryCodesResponse

Ten one-time recovery codes, answered once.

- recoveryCodes: Ten one-time codes, answered this once.

### SecondFactorSummary

A person's authenticator app, as an administrator reads it.

- method: Always `authenticator-app`.
- confirmedAt: When the app was confirmed.
- recoveryCodesLeft: How many recovery codes are unused.

### PasskeyResponse

A passkey by the name its person gave it; never the credential.

- id: The passkey's ID.
- name: The name the person gave it.
- createdAt: When it was added.
- lastUsedAt: When it last signed the person in; null if never.

### PasskeyRename

A passkey's name, as the person tells their passkeys apart.

- name: The new name, 1 to 100 characters.

### PasskeyRemoval

- proof: The person's password, or a code from the app or a recovery code. Leave it out only for a person with neither a password nor an app.

### UserResponse

- id: The person's ID.
- name: The person's name.
- email: The e-mail address the person signs in with; null only for a deactivated person.
- active: False once deactivated; a person is never deleted.
- hasPassword: Whether the person has set a password; never the password.
- version: Rises by one with every change; send it as `expectedVersion`.
- createdAt: When the person was made.
- updatedAt: When the person last changed.
- lastSignInAt: The last sign-in; null if never.
- roles: The roles the person holds, directly or through a group, and where.
- identities: The providers the person signs in with.
- localKept: The person signs in with a password while local sign-in is off; set for administrators made on the server.
- secondFactor: Their authenticator app; null without one.
- passkeys: How many passkeys they have.
- signInManaged: An administrator manages the person's sign-in, so they cannot change their own password, second factor, passkeys or other sessions.

### UserCreate

A person, named by the e-mail they sign in with. They have no password until they set one with a password link.

- name: The person's name.
- email: The e-mail address the person signs in with; unique ignoring case.
- signInManaged: An administrator manages the person's sign-in; see `UserResponse`.

### UserUpdate

A change to a person, with the version read. `active: false` deactivates the person (a person is never deleted) and `active: true` restores them.

- expectedVersion: The person's `version`.
- name: A new name.
- email: A new address; null only while deactivating.
- active: `false` deactivates and ends their sessions; `true` restores.
- localKept: Whether the person keeps signing in with a password while local sign-in is off.
- signInManaged: Whether an administrator manages the person's sign-in.

### UserRole

A role the person holds, directly or through a group.

- key: The role's key.
- name: The role's name.
- instance: Held for the whole instance; then no workspaces are named.
- workspaces: The workspaces it is held in.

### UserRoleWorkspace

- key: The workspace's key.
- label: The workspace's label.

### UserIdentityResponse

How a sign-in provider knows the person: the provider and the ID token's subject.

- provider: The provider.
- subject: The person's ID at the provider, the ID token's `sub`.

### IdentityLink

Moves the provider identities of the person `fromUserId` onto this person. `expectedVersion` is this person's.

- expectedVersion: The version of the person who keeps the identities.
- fromUserId: The ID of the person a provider sign-in made, whose identities move.

### SignInProviderRef

- key: The provider's key.
- name: The provider's name.

### SignInProviderResponse

An OpenID Connect provider people sign in with; never its secret.

- key: The provider's key, used in its addresses; fixed.
- name: The name the sign-in button shows.
- issuer: The provider's issuer address.
- clientId: The client ID the provider gave this engine.
- clientSecretSet: A client secret is saved; it is never answered.
- groupsClaim: The ID token claim that lists the person's groups; null: groups are not used.
- enabled: Whether the sign-in page offers it.
- signOutOfProvider: Signing out of the engine also signs the person out of the provider.
- emailsTrusted: The provider's e-mail addresses are taken as it sends them. False: an address is taken only when the ID token says `email_verified: true`; a first sign-in without that is refused. An address the token says is not verified is never taken.
- redirectUri: The address to register with the provider as the sign-in's return address.
- signedOutUri: The address to register for returning from the provider's sign-out.
- people: How many people have signed in with it.
- lastSignInAt: When someone last signed in with it; null if never.
- version: Rises by one with every change; send it as `expectedVersion`.
- createdAt: When the provider was connected.
- updatedAt: When it last changed.

### SignInProviderCreate

An OpenID Connect provider; an enabled one is checked when it is saved.

- key: Lower case letters, digits and hyphens, starting with a letter; up to 63 characters. Fixed once saved.
- name: The name the sign-in button shows.
- issuer: The provider's issuer address. Plain `http` is accepted only for a loopback host.
- clientId: The client ID the provider gave this engine.
- clientSecret: The client secret. It is sealed and never answered.
- groupsClaim: The ID token claim that lists the person's groups.
- enabled: Whether the sign-in page offers it; an enabled provider is read when saved.
- signOutOfProvider: Also sign the person out of the provider; needs its `end_session_endpoint`.
- emailsTrusted: Trust the e-mail addresses the provider sends; default false. Turn it on only when people cannot set their own address at the provider.

### SignInProviderUpdate

- expectedVersion: The provider's `version`.
- name: A new button name.
- issuer: A new issuer; needs a new `clientSecret`, and is refused once someone has signed in.
- clientId: A new client ID.
- clientSecret: A new client secret, replacing the saved one.
- groupsClaim: A new groups claim; an empty text stops using groups.
- enabled: Turn the provider on or off; turning it off ends its sessions.
- signOutOfProvider: Whether signing out also signs the person out of the provider.
- emailsTrusted: Whether the provider's e-mail addresses are trusted as sent.

### LocalSignInResponse

Whether people sign in with a password.

- enabled: False: only the people who keep local sign-in use a password.
- secondFactorRequired: A password alone does not sign anyone in: a person without an authenticator app sets one up on the sign-in page.
- keptPeople: Active people who keep local sign-in while it is off.
- version: Rises by one with every change; send it as `expectedVersion`.
- updatedAt: When it last changed.

### LocalSignInUpdate

Switches local sign-in on or off, and says whether a password needs a second factor.

- expectedVersion: The setting's `version`.
- enabled: `false` turns password sign-in off for everyone but the people who keep it.
- secondFactorRequired: Require a second factor with a password.

### ClientResponse

- id: The client's ID, which is its OAuth `client_id`.
- name: The client's name.
- active: False once deactivated; a client is never deleted.
- kind: `api` for management and consumer tokens; `agent` for agent tokens only, for `/mcp`; `session`, an assistant task's own client with no secret.
- version: Rises by one with every change; send it as `expectedVersion`.
- createdAt: When the client was made.
- updatedAt: When it last changed.
- lastUsedAt: When the client last obtained a token.
- secrets: The client's valid secrets.
- roles: The roles the client holds and where.
- consumerApis: The consumer APIs the client is granted, with their workspaces.
- createdBy: Who made it; null when made on the server.

### ClientWithSecret

- id: The client's ID, which is its OAuth `client_id`.
- name: The client's name.
- active: False once deactivated.
- version: Rises by one with every change.
- createdAt: When the client was made.
- updatedAt: When it last changed.
- secrets: The client's valid secrets, the new one included.
- kind: `api`, or `agent` for an agent client.
- roles: The roles the client holds and where.
- consumerApis: The consumer APIs the client is granted, with their workspaces.
- createdBy: Who made it; null when made on the server.
- secretId: The ID of the secret just made.
- secret: The `client_secret` just made. It is answered this once.

### ClientCreate

- name: The client's name.
- kind: `api` (the default) or `agent`.

### ClientUpdate

- expectedVersion: The client's `version`.
- name: A new name.
- active: `false` deactivates the client at once.

### ClientSecretCreate

- expectedVersion: The client's `version`.
- overlapHours: How long the client's other secrets stay valid, 0 to 168; 24 by default.

### ClientSecretInfo

- id: The secret's ID.
- createdAt: When the secret was made.
- expiresAt: The end of its overlap after a newer secret was added; null while it has none.
- lastUsedAt: When it last signed the client in; null if never.
- hint: Its last four characters, to tell secrets apart; null for an older secret.

### ClientConsumerApi

- key: The consumer API's key.
- workspaces: The workspaces it is granted in.

### SigningKeyResponse

- kid: The key's ID, as it appears in a token's header and in `GET /oauth/jwks`.
- state: `current` signs new tokens; `verifying` still accepts the tokens it signed; `retired` accepts none.
- createdAt: When the key was made.
- rotatedAt: When a newer key replaced it; null while current.
- retiredAt: When it stopped verifying; null while it still does.

### SigningKeyRotation

Replaces the token signing key; `immediate` refuses the old key's tokens at once.

- immediate: `true` stops the previous key verifying at once, for a leaked key.

### SecurityEventResponse

A change to access, or a sign-in. `aggregateId` is the person's, group's or client's ID, the role's key, the grant's ID, the key's `kid`, a sign-in provider's key (`local` for local sign-in) or, for a sign-in, the person's ID (`unknown` for an address nobody has). `details` holds what changed (`changedFields` and the new values for an update; the principal, role and scope for a grant; the e-mail address and the caller's address for a sign-in), never a password, secret, link or key. `actor` is who made it; a failed sign-in names nobody.

- id: The event's ID.
- aggregateType: What the event is about.
- aggregateId: The person's, group's or client's ID, the role's or provider's key (`local` for local sign-in), the grant's ID or the key's `kid`; for a sign-in, the person's ID, or `unknown` for an address nobody has.
- action: What happened, for example `created`, `updated`, `deleted`, `secret-added` or `failed`.
- version: The version of the thing after the change.
- occurredAt: When it happened.
- actor: Who made it; null for a failed sign-in.
- details: What changed: `changedFields` and the new values of an update, the principal, role and scope of a grant, the address of a sign-in. Never a password, secret, link or key.

### ClientPage

Clients in the order they were created.

### GrantPage

Grants in the order they were made.

### GroupMemberPage

A group's members in the order they were added.

### GroupPage

Groups in the order they were created.

### PasskeyPage

A person's passkeys in the order they were made.

### RolePage

Roles: the predefined ones first, then custom ones as created.

### SecurityEventPage

Security events, newest first.

### SessionPage

A person's open sessions in the order they started.

### SignInProviderPage

Sign-in providers in the order they were created.

### SigningKeyPage

Token signing keys, newest first.

### UserPage

People in the order they were created.
