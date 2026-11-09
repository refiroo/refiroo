# Compatibility commitment

What refiroo promises to the systems and people that build on it, from the first public release, 0.12.0
(decisions D436–D440, [the plan](BASE_0_12_IMPLEMENTATION_PLAN.md#l2-the-compatibility-commitment)). Security fixes
are a separate promise, in [SECURITY.md](../SECURITY.md): before 1.0 only the latest minor release receives them.

## In short

- **From 0.12.0, a committed contract changes only by adding to it.** Anything that would break a caller is
  offered beside the old version, never in its place, and the old version keeps working for at least 12 months
  and two minor releases after the change is announced.
- **Clients tolerate additions**: fields, values and codes they do not know yet, and the reserved extensions
  below.
- **The schema language of models is the exception before 1.0**: each release reads the version it writes, and
  the engine raises stored models to it. From 1.0 a version leaves only in a major release, with notice.
- **Everything else may change in any release**: the database, the code's modules, the interface.

## What is committed (D437)

| Contract | Where it is described | Versioned by |
| --- | --- | --- |
| The management API, `/api/v1`: its operations, request and response shapes, status codes and error codes, as its OpenAPI document (`/openapi.json`) states them | [API.md](API.md) | the path (`/api/v1`, a later `/api/v2`) |
| Each consumer API contract | [CONSUMER_API.md](CONSUMER_API.md), and each contract's own OpenAPI document (`/api/consumer/{consumerApi}/v{contractVersion}/openapi.json`) | the contract version in the path (`v{contractVersion}`); a breaking change raises it, and the engine serves the earlier version beside the new one until the model administrator removes it ([below](#how-a-breaking-change-is-made)) |
| Webhooks and change events: the CloudEvents attributes, the event types (`rdm.<event>`, the event names a consumer API declares and the workspace events), the payloads, the `RDM-*` headers (`RDM-Signature`, `RDM-Timestamp`, `RDM-Delivery-Id`, `RDM-Redelivery`, `RDM-Workspace`, `RDM-Publication`, `RDM-As-Of-Applied`) and how a signature is computed and checked | [CONSUMER_API.md § Change events and webhooks](CONSUMER_API.md#change-events-and-webhooks), [API.md § Webhook delivery](API.md#webhook-delivery-base-09-c12) | the event type; a breaking change is a new type beside the old |
| Sign-in and tokens: the OAuth 2.0 and OpenID Connect endpoints and metadata, the access token's claims, the scope names, and the application's JSON sign-in routes (D416) | [API.md § Security](API.md#security-product-012-designed) | additions only; a breaking change is a new endpoint beside the old |
| The model schema language | [APPLICATION_MODEL.md § Schema versions and the window](APPLICATION_MODEL.md#schema-versions-and-the-window) | `schemaVersion`; see [below](#the-schema-language-of-models) |
| Deployment settings: the names, meanings and defaults of the environment variables | [OPERATIONS.md § Settings](OPERATIONS.md#settings) | additions only; a renamed setting is read under both names for the notice period |
| The documented commands, `python -m app.cli.<command>`, with their arguments and exit codes | [OPERATIONS.md](OPERATIONS.md) | additions only |

**Not committed**: the database's tables and migrations (only the engine writes them; restore a backup with the
engine version that took it), the Python modules and their functions, the interface's screens, layout and
addresses, any route that is not in an OpenAPI document and is not listed above, the test seeds and fixtures,
and two maintenance tools of the releases before 1.0: raising a stored release
(`POST /api/v1/model-releases/{releaseId}/raising` and `python -m app.cli.model_release_raise`).

## Additive or breaking

**Additive**, so made at any release without notice:

- a new operation, route, consumer API, event type, header, setting or command;
- a new optional request field or query parameter, whose absence keeps today's behaviour;
- a new field in a response, an event payload or a token;
- a new value in an enumeration that a response or an event carries (a status, a kind, a reason);
- a new error code, or a more specific one in place of a general one for a request that already failed with
  the same status;
- a new schema-language feature that a model may use and need not.

**Breaking**, so only beside the old version, with notice:

- removing or renaming anything listed above;
- changing a field's type, meaning, unit or default;
- making an optional field or parameter required;
- refusing a request that was accepted, or changing the status of an answer;
- changing how a signature, a token or a cursor is checked;
- a new value in an enumeration that a **request** must send.

## What clients must tolerate

A client that follows these rules keeps working across every additive change:

1. **Ignore fields you do not know**, in responses, event payloads and tokens. (The other way round, the engine refuses
   unknown query parameters, and most request bodies refuse unknown fields, so a mistake in a request is found at
   once.)
2. **Treat an unknown enumeration value as "other"**, and an unknown error code by its HTTP status.
3. **Accept a comma-separated `RDM-Signature`**: during a key rotation it names several signatures, and a delivery
   is genuine when any of them verifies.
4. **Follow cursors as opaque strings**; never build or read one.
5. **Expect the reserved extensions** below.

### Reserved extensions (D440)

These are announced now so that adding them later is not a breaking change. No format is chosen yet; each will
be documented when it is built.

| Extension | What a client must expect |
| --- | --- |
| A retired record points to its survivor | A lookup by ID that answers `404` today may, for a record merged into another, answer with a pointer to the surviving record instead (object reads, relation endpoints, consumer API reads, cursors). |
| A value carries where it came from | An attribute value may carry a `source` beside its author: the system or person that supplied it. |
| A value computed from related records | A field may be computed by the engine from related records, declared in the model and read-only: it is returned like any other and refused on write. |
| A new value type | A model may declare an attribute of a value type a client does not know. Show its value as text; do not write it. |

## How a breaking change is made

1. **Beside the old one**: the next path (`/api/v2`), the next consumer API contract version, a new event type, a
   new endpoint, or a second name for a setting. The old one keeps answering as before.
2. **Announced** in the [CHANGELOG](../CHANGELOG.md) under "Deprecated", in this document, and on every answer of
   the old version with the `Deprecation` and `Sunset` headers (RFC 9745, RFC 8594). A consumer API's earlier
   version carries them since 0.13; the management API's are built when its first version is deprecated.
3. **Kept for the notice period (D438)**: at least **12 months and two minor releases** from the announcement to
   the first release that removes it.

**A consumer API's earlier version is the model administrator's (DF-D2).** Twelve months and two minor releases is
refiroo's own promise for the contracts it publishes. A consumer API contract is written by the instance's model
administrator, not by refiroo, so the engine does not apply that period to it: it serves the earlier contract
version beside the new one, with the `Deprecation` header and, when the administrator sets a day, the `Sunset`
header, until the administrator removes the version from the model. The administrator chooses the notice, and the
sunset day is announced, never enforced. See [CONSUMER_API.md](CONSUMER_API.md#earlier-versions-served-beside-the-new-one-013-df3).

## The schema language of models

**Before 1.0 (D439, the user, 2026-10-27).** The window is cleaned at every release: a release reads the
schema version it writes, and a version nobody runs leaves in the next release, without the notice period. Each
release's CHANGELOG names the versions that left. A model **file** is raised by its author by changing its
`schemaVersion` (each version contains the ones before). A model **stored** in a database is raised by the engine:
the interface offers it on a workspace that cannot be opened, and `python -m app.cli.model_release_raise` raises
every stored release at once. Its records, history, change sets and publications are unchanged.

| Version | Status in 0.12 |
| --- | --- |
| 0.10 | Supported: the version 0.12 reads and writes |
| 0.5–0.9 | Left the window in 0.12; stored releases are raised to 0.10 |
| 0.4 and earlier | Not readable; not carried forward |

**From 1.0.** A version leaves the window only in a major release, announced with the notice period above, and
that release ships an offline upgrader that raises the stored releases and the publications pinned to them, so
nothing becomes unreadable.

## The doors kept open

The [composable domains](COMPOSABLE_DOMAINS.md#doors-to-keep-open) direction needs four extensions to be addable
without breaking this commitment. Checked against the code on 2026-10-27:

| Door | Open? | What adding it takes, and why it breaks no contract |
| --- | --- | --- |
| A retired record points to its survivor | **Yes, by the reservation above.** Today an unknown or retired ID is `404 OBJECT_NOT_FOUND` (consumer and management reads) and batch resolve's outcome is one of `found`, `not_found`, `ambiguous`, `rejected` | A store of retired IDs written when records are merged or deleted (none exists: a merge deletes the loser's rows); the reads answer the pointer where they answer `404` now, and resolve gains an outcome value. Cursors hold sort values and opaque positions, never a lookup, so they keep decoding |
| A value carries where it came from | **Yes.** `attribute_values.value_source` exists (always `own` today); the management value responses are open objects | `source` added to value answers. Change-set, base and publication rows keep values as a plain key-to-value map, so their sources go in a column beside it, never inside it; published snapshots cannot recover a source afterwards. A new kind of origin in audit events needs its database check widened |
| A value computed from related records | **Yes, with the writers named.** A binding's `readOnly` exists and writes refuse it | Values are stored by three writers, not one: the single-record path (`apply_attribute_values`), the bulk and import path (`LiveWrites`) and the change-set merge (`save_values`); a model migration rewrites them in SQL. A derived value must be written and guarded in all of them |
| A new value type | **Yes for the contracts; not a one-line change.** Management answers name `valueType` as a string; a consumer API document gives an unknown type an open schema | The list of types is repeated in about 25 places in the engine, in the database's per-type value columns (a type that needs a new column is a migration) and in the interface's type list. Its conversions are reported as loss until written (D102) |

Also from the check: the consumer API documents described every answer object as closed (`additionalProperties:
false`), so a client validating against them would refuse an added field. Since 0.12 L2 answers are open and only
requests are closed.

## How a release is checked

Every release's build acceptance (R) begins with the full review of the changes since the last release. It
lists every re-baseline of the OpenAPI lock (`backend/tests/test_openapi_contract.py`, each with a comment that
names what changed) and of each consumer API document, and marks each one **additive** or **breaking** against
this document. A breaking one needs a recorded decision and the side-by-side path above before the release.
