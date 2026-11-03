---
title: Identifiers, paging and errors
description: Keep stable identifiers, traverse complete collections and handle failures safely.
reader: integrator
---

Store public IDs and model keys when connecting refiroo data to another system. Runtime entities use stable UUIDs; model definitions use stable keys as well as their public identity. Names are display text and can change. Database sequence numbers are not public identifiers.

## Read a complete collection

Collections are bounded pages, not truncated lists. Follow the returned next cursor until it is absent. Store the cursor with the exact filters, order, workspace and context that produced it. Cursors are signed and opaque: do not decode or construct them. See the [collection operations](/docs/api/?api=management#tag/objects) and [Read a collection completely and resume](/docs/guide/integrate/read-a-collection-completely-and-resume/).

Use cursor navigation for traversal, positions for jumps, and seek where the operation supports a jump by sort value. You can also start at the end. Select only one navigation method per request. Position jumps can move when rows before the position are inserted or deleted. Cursor boundaries are stable against those shifts; they do not turn live data into an immutable snapshot. Use a publication or export when you need a fixed baseline.

Ask for totals when you need counts or an index into the filtered list. Otherwise no total is computed. Consumer pages keep `totalCount` and `startIndex` as null; do not treat null as zero. Attribute sorting places records with values before those without; a stable ID breaks ties. A date-time filter given a calendar day compares the whole UTC day. An ancestor field chooses the matching ancestor nearest the root.

| Refusal | What to do |
| --- | --- |
| `CONFLICTING_PAGE_PARAMETERS` | Choose one navigation method. |
| `INVALID_CURSOR` | Restart the list with the intended query; a cursor from another context or route cannot be reused. |
| `INVALID_POSITION` | Use a non-negative row position. |
| `INVALID_SEEK` | Use a value appropriate to the sort field. |
| `REQUEST_VALIDATION_ERROR` or an unknown query parameter | Correct the request using the named path and the operation schema. Do not drop filters silently. |

## Handle failures by meaning

Read the structured error code and explanation; do not parse a human message to make program decisions. Expected failures tell you what to correct. An unknown error code should fall back to its HTTP status. Preserve the request or correlation reference when escalating an unexpected failure. OAuth token operations have their own standard error format.

A `VERSION_CONFLICT` requires a fresh read and a decision about the intended change. A `MODEL_RELEASE_CHANGED` requires the model and request to be reconsidered. Neither is a reason for an unconditional overwrite. See [Versions and conflicts](/docs/integrate/versions-and-conflicts/).

For `DATABASE_UNAVAILABLE`, wait for the retry interval before resending. When a connection drops and you cannot know whether a write committed, reconcile by ID or replay an [idempotency key](/docs/integrate/writing-in-bulk/#retry-without-duplicating-a-job). Do not retry an unprotected create blindly. `INTERNAL_ERROR` needs the correlation reference; `WORKSPACE_RUNTIME_STATE_MISSING` indicates an instance problem for the operator.

Accept additional response fields and unknown response values. Requests remain strict; send only documented fields. See [Compatibility](/docs/integrate/compatibility/).

## Metadata keys and workspace identity

Model entities have public UUIDs and stable keys. Use keys for model references and type paths; their public IDs are assigned on installation and remain stable while that release is served. Runtime records, relationships and attribute values use public UUIDs. An attribute value is addressed through its record and attribute-type key even though its response includes a value ID. A workspace is the deliberate exception: its immutable, case-sensitive key is its public identity and it has no separate UUID.

## Request validation and page metadata

Management routes reject unknown query names with `422 UNKNOWN_PARAMETER`; details list the parameters and the first query path. Protected routes check identity and permission first, so a 401 or 403 can precede a parameter error. Consumer reads normally use 400 for invalid query parameters; consult that contract’s document. Never silently remove a requested filter after a validation failure.

For management collections, `totalCount` and `startIndex` are omitted unless `includeTotal=true`; when requested they are numbers, never null. Consumer lists instead keep the keys with null values when totals are not requested. XREF always supplies totals. `anchor` reopens a page from its first row and is null on an empty page. Pass it back as a cursor. `prevCursor` reads backward but still returns rows in list order. A position at or beyond the end returns an empty page and a previous cursor to the last page, with start index equal to total when requested.

Seek uses the sorted field’s value type: ISO 8601 for dates and `true` or `false` for booleans. It lands at or after the value for ascending order, at or before for descending order. Rows with missing sort values follow valued rows. Use the operation’s own page-size default and maximum; there is no universal collection size.

## Operational error details

API errors use `error` with uppercase `code`, a human-readable `message` and optional `details`. Status, action and kind values remain lowercase. Unexpected errors carry `details.correlationId`, the response’s `X-Request-Id`, which the operator can find in logs. Retain it with the operation and time when escalating.

A request unable to obtain a usable database connection returns `503 DATABASE_UNAVAILABLE` with `Retry-After` and saves nothing. Its reason can be `poolExhausted`, `tooManyConnections`, `transactionEnded` or `unreachable`. Respect the interval and alert the operator if it persists; do not change credentials or overwrite data to recover a capacity failure. After an ambiguous connection loss during a write, use reconciliation or idempotency as described above.
