# agent-access

Agent access lets an assistant, a program speaking the Model Context Protocol, reach the instance at `/mcp`. The operator switches it on with `MCP_ENABLED`. A person's assistant works with that person's grants cut down to Browse and Work in change sets; an agent client, made with `kind: agent`, works with its own. You use these operations to see the settings, the agent clients and the assistants, to review every call, and to register, block or restore an assistant. Reading needs `agent-access.read` and changing `agent-access.write`, both in Security administration.

1. Connect a program: `POST /api/v1/clients` with `kind: agent`, give it a role with `POST /api/v1/grants`, then `POST /oauth/token` with `scope=agent`.
2. Review use: `GET /api/v1/agent-access/calls`, and `POST /api/v1/agent-access/applications/{application_id}/block` for an assistant that should stop.

## GET /api/v1/agent-access

Title: Read agent access

Says whether assistants can reach the instance and where, under which limits, and how many calls the last 30 days held. The settings are the operator's, read when the engine started; they are not changed here. It answers while agent access is off.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance

## GET /api/v1/agent-access/clients

Title: List agent clients

Lists the clients of kind `agent` in the order they were made, each with its calls of the last 30 days. Make one with `POST /api/v1/clients`; change or deactivate it with the client operations.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/agent-access/applications

Title: List assistants

Lists the assistants people sign in with, in the order they were registered: what each says of itself, where it returns and how many people have an open session for it.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/agent-access/applications

Title: Register an assistant

Registers an assistant: people can sign in with it whether or not self-registration is on, and it may return to any HTTPS address named here, or to a loopback address on any port. Assistants that register themselves use `POST /oauth/register`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 AGENT_APPLICATION_INVALID: an address is not HTTPS or loopback, or over 10
- 422 REQUEST_VALIDATION_ERROR: `name` or `redirectUris` is missing or invalid

## POST /api/v1/agent-access/applications/{application_id}/block

Title: Block an assistant

Stops an assistant: no one signs in with it any more and its open sessions end, so it stops at its next call. Blocking a blocked assistant changes nothing. Undo it with `restore`; the sessions it ended stay ended.

### Parameters

- application_id: The assistant's `id`, from `GET /api/v1/agent-access/applications`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 AGENT_APPLICATION_NOT_FOUND: no assistant has this ID

## POST /api/v1/agent-access/applications/{application_id}/restore

Title: Restore an assistant

Lets people sign in with a blocked assistant again; they sign in anew, since the sessions the block ended stay ended. Restoring an assistant that is not blocked changes nothing.

### Parameters

- application_id: The assistant's `id`.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 404 AGENT_APPLICATION_NOT_FOUND: no assistant has this ID

## GET /api/v1/agent-access/calls

Title: List agent calls

Lists each call an assistant or agent client made through `/mcp`, newest first, with the names of its arguments and never their values. Calls are kept for the operator's `MCP_CALLS_DAYS`. Listing tools counts as a call.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Security administration at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## Schemas

### AgentAccessStatus

- enabled: Whether assistants can reach the instance at `/mcp` (`MCP_ENABLED`).
- url: The address an assistant connects to.
- ratePerMinute: Calls a minute one caller may make; more answer `limited` (`MCP_RATE_PER_MINUTE`).
- openRegistration: Whether an assistant may register itself with `POST /oauth/register` (`MCP_OPEN_REGISTRATION`).
- redirectHosts: HTTPS hosts a self-registered assistant may return to, besides this computer (`MCP_REDIRECT_HOSTS`).
- callsDays: Days a call's record is kept (`MCP_CALLS_DAYS`).
- calls30Days: Calls recorded in the last 30 days.
- lastCallAt: When the last call was made; null if none is kept.

### AgentClientResponse

- id: The client's ID, which is its OAuth `client_id`.
- name: The client's name.
- active: False once deactivated.
- kind: Always `agent`.
- version: Rises by one with every change.
- createdAt: When the client was made.
- updatedAt: When it last changed.
- secrets: The client's valid secrets.
- roles: The roles the client holds and where.
- consumerApis: The consumer APIs the client is granted, with their workspaces.
- createdBy: Who made it; null when made on the server.
- calls30Days: Its calls in the last 30 days.
- lastCallAt: Its last call; null if none is kept.

### AgentApplicationCreate

- name: What the assistant is called, up to 200 characters.
- redirectUris: Exact HTTPS addresses, or a loopback address (`localhost`, `127.0.0.1` or `::1`) on any port; 1 to 10.

### AgentApplicationResponse

- id: The assistant's OAuth `client_id`.
- name: What the assistant says of itself.
- source: `registered` if it registered itself, `administrator` if an administrator did.
- returnsTo: Where a sign-in may return, as the host a person reads; a loopback address reads `this computer (localhost)`.
- blocked: A blocked assistant signs no one in.
- signedIn: People with an open session for it; always 0 in the answer of `POST`, which registers a new assistant.
- createdAt: When it was registered.
- lastUsedAt: When someone last signed in with it or renewed; null if never.

### AgentCallResponse

- id: The call's ID.
- occurredAt: When the call was made.
- principal: The person's or client's name.
- principalKind: `user` for a person's assistant, `client` for an agent client.
- principalId: The person's or client's ID.
- application: The assistant; null for a client's own calls.
- tool: The tool, or `tools/list` for listing them.
- arguments: The names of the call's arguments, never their values.
- outcome: `answered`; `refused` (not allowed or invalid); `limited` (over the rate limit); `failed` (an error).
- durationMs: How long it took, in milliseconds.
- requestId: The request's ID, as the engine's log names it; null if none.

### AgentApplicationPage

The assistants people sign in with, in the order they were registered.

### AgentCallPage

Tool calls, newest first.

### AgentClientPage

Agent clients in the order they were created.
