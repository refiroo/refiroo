## Identifiers and keys

Records, relationships, change sets, publications, jobs and installed model releases are identified by an `id`, a UUID the engine assigns; use it in addresses and requests exactly as returned. The model's own things (applications, object types, attribute types, relation types) have an `id` and a `key`, a short lower case name that is stable across releases of the model; addresses and requests name them by `key`. A workspace is named by its `key` alone. Keys are compared exactly, including case.

## Workspace, change set, publication and date

Reads and writes of records work in one context, named by a query parameter (or a body field on writes): `workspaceKey` for live data (the default workspace when none is named), `changeSetId` for the work in progress of a change set, or `publicationId` for a published state. `changeSetId` and `publicationId` cannot be combined (`MUTUALLY_EXCLUSIVE_CONTEXT`), and a `workspaceKey` sent with either must be that context's workspace (`WORKSPACE_CONTEXT_MISMATCH`). A write that names a change set changes the change set; one that does not changes live data, and needs a role that allows editing live data. `asOf=YYYY-MM-DD` on the operations that take it keeps the records whose type's validity period includes that date; it never selects a publication.

## Versions and concurrent changes

A thing that can be changed carries a `version`, which rises by one with every change. To change or delete it, send the version you read as `expectedVersion`; if somebody changed it since, the answer is `409 VERSION_CONFLICT` (or a more specific code) and nothing is changed. Read the current state, decide whether the change is still wanted, and send it again with the new version. Relationship sets and change sets have their own claims; the operations that take them say so.

## Paging

Every list returns `items` followed by `nextCursor`, `prevCursor` and `anchor`, and pages with `pageSize` (its default and maximum are the operation's). Select a page with at most one of `cursor`, `from=end` (the last page) or `position` (a zero-based row); two at once answer `CONFLICTING_PAGE_PARAMETERS`. To read a whole list, follow `nextCursor` until it is `null`: a cursor never repeats or skips a row while the data changes, and it is only valid with the filters it came from (`INVALID_CURSOR`). `position` is for jumps, such as a scrollbar; rows can shift between two position reads. `includeTotal=true` adds `totalCount` and `startIndex`; without it they are left out. Keep `anchor` to reopen a page.

### Fields of every page

- items: The rows of this page, in list order.
- nextCursor: Send it as `cursor` to read the page after this one; `null` at the end of the list.
- prevCursor: Send it as `cursor` to read the page before this one; `null` at the start.
- anchor: Send it as `cursor` to reopen this page from its first row; `null` for an empty page.
- totalCount: The rows that match the filters, in all; present only with `includeTotal=true`.
- startIndex: The matching rows before this page's first row; present only with `includeTotal=true`.

## Ordering

Every list has a stable order, named in the operation (workspaces by key, records by name unless `sort` says otherwise). Where an operation takes `sort`, it names one field, with `-` in front for descending. The order is total, so two reads of unchanged data answer in the same order.

## Retrying a write

A single write is not repeated by the engine: if the answer is lost, read the thing before sending it again. Operations that start a job (`POST /api/v1/batches`, imports) take an `Idempotency-Key` header of 1 to 200 printable characters, scoped to the route and the workspace. Sending the same key with the same request returns the first job's answer again, with `Idempotent-Replayed: true`, and runs nothing; the same key with another request answers `422 IDEMPOTENCY_KEY_REUSED`, and while the first job is still queued or running `409 IDEMPOTENCY_IN_PROGRESS` with `Retry-After`. A key lives as long as its job.

## Optional surfaces

Some operations exist only while the operator has switched their surface on. `GET /api/v1/capabilities` says which are on and the setting that controls each: `MODEL_ADMIN_MUTATIONS_ENABLED` (installing and editing models; off by default), `WORKSPACE_ADMIN_MUTATIONS_ENABLED` (creating, changing and deleting workspaces; on by default), `INTEGRATION_JOBS_ENABLED` (batches, imports, exports and other jobs, with their limits; on by default), `CONSUMER_SUBSCRIPTIONS_ENABLED` (webhook subscriptions; off by default). `GET /api/v1/system` says whether an AI provider is configured and whether assistant access (`MCP_ENABLED`) is on. A request for an operation that is not there answers `405 HTTP_ERROR`; ask the operator to change the setting, not the client.

## Authentication

Every operation needs `Authorization: Bearer <token>`. A program gets its token from `POST /oauth/token` with `grant_type=client_credentials`, the client's ID and secret as HTTP Basic credentials and `scope=management`. The answer's `expires_in` says how many seconds the token lasts (3,600 unless the operator changed it); ask for a new one before then. A person's application sends the token of the person's sign-in session.

A token is for one API: a `consumer` token is refused here. A valid token says who is calling, not what they may do. Roles decide that, and a missing right answers `403 FORBIDDEN`. Each operation's `x-action` names the action it needs.

## Errors

Every refusal has the same body:

```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "Workspace version has changed",
    "details": { "currentVersion": 3 }
  }
}
```

Act on `code`; it is stable. `message` is for a person reading a log and can be reworded. `details` is present for some codes, and the catalogue says what it holds; for `REQUEST_VALIDATION_ERROR` it lists each wrong value with `loc` and `msg`. The `/oauth/...` endpoints answer in OAuth's own form instead. Each operation lists the codes it can answer with, linked to the catalogue below.

### Errors every operation can return

- 401 AUTHENTICATION_REQUIRED
- 401 TOKEN_INVALID
- 422 UNKNOWN_PARAMETER
- 500 INTERNAL_ERROR
- 503 DATABASE_UNAVAILABLE
- 503 MODEL_REGISTRY_UNAVAILABLE

### Headers every operation takes

- X-Expected-Model-Release-Id: Optional. The model release the request was built on. Where the request's workspace or change set runs another release, the request is refused with `409 MODEL_RELEASE_CHANGED` and nothing is saved.
