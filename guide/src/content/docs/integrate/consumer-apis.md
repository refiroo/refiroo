---
title: Consumer APIs
description: Use a declared business contract rather than the underlying record model.
reader: integrator
---

A consumer API is a read-only business contract declared in a model. It exposes selected record types under public names, defines their fields and related blocks, and chooses which reads, lookups, lists and events are available. Integrators use that contract without reconstructing the underlying record graph.

A model administrator [designs the consumer API](/docs/model/consumer-apis/). Defaults are expanded by the engine, and references are validated before use. Adding an operation can extend a contract; removing fields, operations, exposed types or supported behavior requires a higher contract version. The activation check refuses an unversioned breaking change.

## Learn one way to read business objects

Consumer APIs share one way of presenting and reading business objects, whatever data the model describes. Within a consumer API, one declared object definition supplies the fields and related blocks, but each exposed type is answered in its own shape. An object carries only the fields its type holds and the blocks whose relationships reach that type. Get by ID, lists, lookups and batch resolution reuse that type’s shape. You can use the contract’s schemas to read each type without a sequence of management reads to assemble its relationships.

The model chooses the content: exposed types, public names, field sources, related blocks, filters, matching rules and events. The engine supplies the ways to compose and read it. Related records can appear as an object or an array, with selected fields such as identity, code and name. System codes, translations, a parent and an ancestor path are declared parts of the same answer. They use ordinary fields and relationships; they are not special features tied to one domain.

### Two types, each in its own shape

**Reference-data example:** the `stops` API exposes both stops and operators. These two Get by ID answers carry different fields from one declared object definition. The table places their complete object bodies side by side; values were captured from the reference instance through Get by ID.

| Field | Stop: Tschamut-Selva | Operator: Matterhorn Gotthard Bahn (fo) |
| --- | --- | --- |
| `objectType` | `"Stop"` | `"Operator"` |
| `id` | `"8d90eede-23cf-47c1-8dac-cb37956f5fd5"` | `"f94ef862-2a95-4675-9e31-6b1d0a03317f"` |
| `code` | `"ch:1:sloid:5173"` | `"MGB-fo"` |
| `name` | `"Tschamut-Selva"` | `"Matterhorn Gotthard Bahn (fo)"` |
| `validFrom` | `"2021-04-01"` | not in the answer |
| `validTo` | `null` | not in the answer |
| `stopNumber` | `8505173` | not in the answer |
| `abbreviation` | `"TSSE"` | not in the answer |
| `latitude` | `"46.65674442039232"` | not in the answer |
| `longitude` | `"8.709084193690385"` | not in the answer |
| `height` | `"1701.3"` | not in the answer |
| `sboid` | not in the answer | `"ch:1:sboid:100029"` |
| `parent` | `{"objectType": "Municipality", "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc", "code": null, "name": "Tujetsch"}` | `null` |
| `path` | `"Graubünden/Surselva/Tujetsch"` | `""` |
| `operator` | `{"id": "f94ef862-2a95-4675-9e31-6b1d0a03317f", "code": "MGB-fo", "name": "Matterhorn Gotthard Bahn (fo)", "localName": null, "isPrimary": null}` | not in the answer |
| `modes` | `[{"id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9", "code": "TRAIN", "name": "Train"}]` | not in the answer |
| `systemCodes` | `[{"system": "Wikidata: stations", "systemKey": "wikidata-stations", "code": "Q33467326", "name": "Q33467326 Tschamut-Selva"}]` | not in the answer |
| `translations` | `[]` | `[{"languageCode": "de", "translatedName": "Matterhorn Gotthard Bahn (fo)", "isActive": true}, {"languageCode": "fr", "translatedName": "Matterhorn Gotthard Bahn (fo)", "isActive": true}]` |

The operator's stop-specific fields and blocks are absent, while its own business identifier appears in `sboid`. Neither type holds `fsoNumber`, so neither answer includes it. The operator has no parent, so `parent` is null and `path` is empty. Its `translations` array lists the operator's own translated names. For a main object field, `null` means the record has no value for a field its type holds; an absent field means the type does not hold it. A client reading several types should expect a field only on the types that hold it, as each type’s schema in the generated OpenAPI document describes. Values keep their declared types: `stopNumber` is an integer, while decimals are strings to retain precision.

### What carries across consumer APIs

| Shared pattern | What the declaration or instance supplies |
| --- | --- |
| Get by ID returns a business object. | The exposed types, public type names and output fields. |
| Named lists return `items` with the same cursor, position and page metadata. | List names, selected types, sort order and filters. |
| XREF lookup returns scored business objects, or one untied best answer. | The identifiers to match and their weights. |
| Batch Resolve keeps input order and reports each outcome separately. | The enabled operation, declared filters and matching rules. |
| Crosswalk selects a related representation as `target`. | Which related filters allow a crosswalk and the target fields. |
| Business-date reads use `asOf`; publication reads use `publication`. | Which types declare validity dates and which compatible publications exist. |
| The API index points to each contract's own generated OpenAPI document. | The API name, contract version and concrete paths and schemas. |
| Errors use `error` with `code`, `message` and optional `details`; GET caching uses ETags and conditional requests. | The error cause or opaque tag for the requested state. |
| Event feeds share an envelope and event structure; webhook delivery uses the same signing and delivery rules. | Declared events, identity or full payloads, and a subscription's RDM JSON or CloudEvents format. |

The operation patterns are shared; availability is declared. An API can omit Get by ID, XREF, Resolve, lists or events. Crosswalk needs an enabled related filter, and business-date filtering needs declared validity periods. List pages, XREF pages, batch answers and event pages have their own envelopes, reused across APIs; they are not one interchangeable envelope. The linked [read examples](/docs/integrate/reading-business-objects/), [lookup examples](/docs/integrate/looking-up-and-resolving/) and [event and webhook examples](/docs/integrate/consumer-events-and-webhooks/) show their complete requests and answers.

This lets you reuse a parser and the same read, page, resolve, cache and event-processing flows across types and consumer APIs. A client driven by the declared contract can accommodate another type or API through configuration. Check its generated OpenAPI document: it has one schema per exposed type. Output names, optional parts, related fields and cardinality can differ between declarations, so a client with fixed field names may need changes.

Each type’s schema is named and titled with its public name. Its fields are required, except for related blocks served on request. In the [API reference](/docs/api/?api=consumer-stops-v1), a response schema shows **One of** with a type selector and marks `objectType` as the discriminator. The named example picker under **The answer.** offers an example for each exposed type; a list offers its own type’s example. These examples come from field types, without reading a record.

Each consumer contract has its own version, separate from the model release and management API. Model changes can preserve what consumers read; breaking contract changes require a higher version. Stability protects an agreed contract while its underlying model evolves. It does not promise that every declaration has identical field names or that a new version requires no client changes.

## Discover and obtain access

Read the [consumer API index](/docs/api/?api=management) for the workspace. It identifies contracts and their own OpenAPI documents. Each contract's routes and typed answers are described separately from the management API. The workspace’s model determines the available versions: the current version and any retained earlier versions. The editor retains the draft’s base release definition by default when raising its version, even after breaking edits. A version that base release never served leaves nothing to retain. All served versions read current live data through their own definitions. Coordinate activation with consuming systems; versions explicitly stopped are no longer available. Historical publication reads resolve the publication's own definition as described below.

A client needs a consumer-audience token and a consumer API grant in that workspace. A management role does not grant consumer data. An administrator [grants the client access](/docs/administer/clients/). Public OpenAPI documents describe contracts without exposing records; the index and data reads require authentication. A consumer token sees only granted APIs in the index, possibly none. A management token with Browse in the workspace sees all its APIs in the index. The per-definition OpenAPI document is public. Its OAuth 2.0 client-credentials scheme points to the instance’s token endpoint and requests the consumer scope.

Data requests check the token, workspace, consumer grant, then API name and version, in that order. A missing grant can therefore return `403 FORBIDDEN` even for an undeclared API name. This also applies to publication reads. Missing credentials return `401 AUTHENTICATION_REQUIRED`; invalid credentials return `401 TOKEN_INVALID`, with `details.reason` such as `expired`, `revoked`, `audience`, `unknownKey`, `malformed` or `signature`. Both 401 responses carry `WWW-Authenticate: Bearer`. A forbidden consumer read names `consumerApi` and `workspaceKey` in its details. Obtain a valid token for a 401; ask the administrator to review the workspace grant for a 403.

**Example:** the guide's reference model declares the `stops` contract. Its [Get by ID operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/objects/{id}) presents stops with their municipality, operator, modes, system codes and names. Those names and projections are model configuration; other models can expose different business objects.

## Choose an operation

The paths below are the shared route patterns. Replace `{consumer_api}` with the declared key and `{contract_version}` with its integer version. Replace `{object_id}` with a public record UUID and `{list_key}` with a declared list name. Send the workspace on every request so a default-workspace change cannot redirect an integration.

| Operation | Purpose and next step |
| --- | --- |
| `GET /api/consumer` | Discover the APIs your token may read, their versions and document addresses. |
| `GET /api/consumer/{consumer_api}/v{contract_version}/openapi.json` | Read that workspace's generated OpenAPI contract. This document is public; it grants no data access. |
| `GET /api/consumer/{consumer_api}/v{contract_version}/objects/{object_id}` | Read one exposed record in its declared business shape. See [Reading business objects](/docs/integrate/reading-business-objects/). |
| `GET /api/consumer/{consumer_api}/v{contract_version}/lists/{list_key}` | Traverse a named list, optionally narrowed by its declared filters or parent scope. See [the collection guide](/docs/guide/integrate/read-through-a-consumer-api/). |
| `GET /api/consumer/{consumer_api}/v{contract_version}/xref` | Match terms to scored objects, or require one untied best answer. See [Looking up and resolving](/docs/integrate/looking-up-and-resolving/). |
| `POST /api/consumer/{consumer_api}/v{contract_version}/resolve` | Resolve many queries or known IDs while preserving input order and reporting each outcome. See [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/). |
| `GET /api/consumer/{consumer_api}/v{contract_version}/publications` | Find snapshots and their event positions before a fixed extract. See [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/). |
| `GET /api/consumer/{consumer_api}/v{contract_version}/events` | Follow the contract's business events from a saved position. See [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/). |

**Reference-data example:** the `stops` contract declares these five lists. They return objects in their listed type’s shape, in a paged `items` envelope. Supply `workspace=graubuenden` and a consumer token. Full request and response bodies are in [Reading business objects](/docs/integrate/reading-business-objects/); the instance's [generated list operations](/docs/api/?api=consumer-stops-v1) describe the concrete schemas.

| Request | Records and scope |
| --- | --- |
| `GET /api/consumer/stops/v1/lists/municipalities` | Municipalities; optional `district` parent UUIDs scope them below districts. |
| `GET /api/consumer/stops/v1/lists/stops` | Stops ordered by stop number; optional `municipality` parent UUIDs scope them below municipalities. |
| `GET /api/consumer/stops/v1/lists/all-stops` | Stops ordered by stop number, without a special parent parameter; declared filters still apply. |
| `GET /api/consumer/stops/v1/lists/operators` | Operators, using the default list order. |
| `GET /api/consumer/stops/v1/lists/modes` | Modes, using the default list order. |

`GET /api/consumer/stops/v1/publications` lists this workspace's snapshots; it does not list only changes to stops. Use each snapshot's ID to pin compatible reads and its `eventSequence` as the starting position for following events. No publication needs to exist for live reads to work.

## Understand the shared object

Reads by ID, lists, XREF, batch resolution, full event payloads and webhook deliveries all use each type’s business representation, including when reading a publication. Values retain their types. A main object field is present only when at least one source is a built-in field, such as `id` or `name`, or an attribute bound to that type. A field the type holds uses its configured sources, then its default or `null` when the record has no value. A default never adds a field to a type that does not hold it. `objectType` is always present; declared parent, path and hierarchy outputs remain present on every type, as do `matchScore` for XREF and `target` for a crosswalk.

The parent's fields use author-chosen output names; in the short list form, built-in fields keep their role's output name and other sources become camelCase words. An unexposed parent's public type is null. The declaration can include the parent, ancestor path and hierarchy as part of that representation.

A related block is present only when the object’s type is an end of its relationship in the declared direction; for a parent’s block, the parent’s type decides. A block the type cannot hold is absent. When the type holds a served block but there are no related records, it is `null` for one or `[]` for many. On-request blocks also need to be named in `include`. Related blocks follow cardinality: a single object or an ordered list. A projected public type is available only when the definition exposes all reachable types.

The object's identity is its public record ID. Other codes are lookup inputs, not substitutes for that identity. Parameters can narrow which objects are visible and which related records appear. A target representation can translate a code or name through a declared relationship; see [Looking up and resolving](/docs/integrate/looking-up-and-resolving/).

## Live and publication reads

Live consumer reads see committed live data, including direct live writes. Unpublished change-set work is invisible. To fix the state for an extract, read a publication by ID or select the current publication. A cursor started on the current publication stays pinned to it even after a newer one becomes current. Superseded or withdrawn publications remain readable by ID.

The publication uses its own model definition at the requested contract version, not today's definition. The requested version must first be offered by the workspace's current model. Selecting a publication cannot restore a route for a version no longer offered. `PUBLICATION_CONTRACT_MISMATCH` means it declared a different version or no such API. `PUBLICATION_NOT_FOUND` means no matching publication in that workspace, including no current publication. A publication from another workspace cannot be read by reusing its ID here.

GET reads support conditional caching. An unchanged answer can return without its body. A live tag may change after any live write in the workspace, even one this API does not show; it is not proof that this particular object changed. A pinned read's tag remains stable. Batch resolution is a read expressed as POST and does not offer this GET cache behavior.

Follow [Read through a consumer API](/docs/guide/integrate/read-through-a-consumer-api/) for the sequence. For the browser's read-only contract catalogue, the declaration's editor and integration setup, see [Consumer APIs in the model](/docs/model/consumer-apis/) and [The API reference](/docs/integrate/api-reference/).

## From a declaration to a running API

Your organisation declares its own consumer APIs. Their names, fields and operations are not fixed product modules. Once a valid model release is installed and activated in a workspace, its declarations become read routes under `/api/consumer/{key}/v{contractVersion}`. Installation alone does not change what the workspace serves. A consumer grant lets a client call the API; it does not change its shape.

**Reference-data example:** these excerpts are taken from the `stops` declaration. They show selected parts of one declaration, not a complete model to install:

```json
{
  "key": "stops",
  "name": "Stops API",
  "contractVersion": 1,
  "exposes": ["stop", "municipality", "operator", "mode"],
  "publicNames": {
    "stop": "Stop",
    "municipality": "Municipality",
    "operator": "Operator",
    "mode": "Mode"
  },
  "object": {
    "fields": {
      "id": {"role": "id"},
      "code": {"role": "code", "from": ["sloid", "operator-code", "mode-code"]},
      "name": {"role": "name", "from": "name"},
      "stopNumber": "stop-number"
    },
    "parent": ["objectType", "id", "code", "name"],
    "path": true,
    "related": {
      "operator": {
        "via": "stop-operated-by-operator",
        "fields": {"id": "id", "code": "operator-code", "name": "name", "localName": "relation:local-name", "isPrimary": "relation:is-primary"}
      }
    }
  },
  "operations": {
    "objects": {},
    "resolve": {},
    "lists": {
      "all-stops": {"of": "stop", "sortBy": "stop-number"},
      "stops": {"of": "stop", "within": {"filter": "municipality"}, "sortBy": "stop-number"}
    }
  },
  "filters": {
    "operator": {
      "onRelated": "operator",
      "matchOn": ["operator-code", "name"],
      "keepOnlyMatching": true
    }
  }
}
```

The complete reference declaration also exposes dates, coordinates, height and other fields, related modes, system codes and translations, the municipality filter, XREF matching and the `stops-changed` event. The following pages show those parts where used. `Resolve` requires object reads and XREF; this excerpt omits the XREF rules, which are explained in [Looking up and resolving](/docs/integrate/looking-up-and-resolving/#a-lookup-with-a-score).

| Declaration | What the consumer receives |
| --- | --- |
| `key: stops`, `contractVersion: 1` | The base path `/api/consumer/stops/v1`; another model can choose a different key and version. |
| `exposes` and `publicNames` | Those records can appear, named `Stop`, `Municipality`, `Operator` and `Mode` in `objectType`. Other types remain internal. |
| `object.fields` | Each type carries only the output names whose sources it holds. `stopNumber` reads the underlying `stop-number` value on types that bind it. |
| Ordered `from` sources | `code` takes the first non-empty source available on that record. An operator can therefore use its operator code while a stop uses its stop code. |
| A field default | When no source yields a value, the declared default is returned; with no default the value is `null`. The reference stop example shows nulls rather than an invented value. |
| `parent` and `path` | A parent object and a slash-separated ancestor path appear. Path lists the ancestors, not the record itself. |
| `related.operator` | The relationship is followed and exposed as `operator`. This reference binding allows one operator, so it is an object or `null`; multi-record bindings produce arrays. |
| `operations.objects` | `GET /objects/{id}` reads the shared object by its public record ID. |
| `operations.lists.all-stops` | `GET /lists/all-stops` pages stops by stop number. |
| `operations.lists.stops.within` | `GET /lists/stops` accepts the declared municipality parent scope. |
| `filters.operator` | `operator=MGB-fo` matches related operator records by code or name and removes objects with no matching operator. |
| XREF and Resolve | `GET /xref` scores codes, names and related values; `POST /resolve` answers many single-object questions. |
| Declared events | `GET /events` follows the declared business changes; a runtime webhook subscription can deliver them. |

Object, list, XREF and resolution results use the same business object. XREF adds `matchScore`; lists wrap objects in `items`; XREF pages wrap them in `results`; resolution wraps each outcome separately. See [Reading business objects](/docs/integrate/reading-business-objects/) for complete object and page bodies and [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) for the event bodies.

## Find your instance's actual contract

The API index pages in consumer API name order, without seek. Each entry has `consumerApi`, `name`, optional `description`, `contractVersion` and `openapi`. Its links preserve the requested workspace. Index and document responses identify it with `RDM-Workspace` and its release with `X-Model-Release-Id`. Each generated document is OpenAPI 3.1, with concrete names and versioned paths and its contract version in `info.version`. These documents describe the selected workspace’s release; the same API name in another workspace can mean another contract.

Read the authenticated index at `/api/consumer?workspace=graubuenden` in this example. Each entry gives the consumer API name, contract version and its OpenAPI document address. The reference document is `/api/consumer/stops/v1/openapi.json?workspace=graubuenden`. Each document is OpenAPI 3.1 and includes the concrete paths and shapes generated from that workspace's declaration. Use it to generate or validate your client after understanding the sequence here.

In the browser, **Settings › Connections › Consumer APIs** lists the declared APIs, and **API reference** opens their interactive documents. Both describe the selected workspace's model; they do not make a contract available in another workspace. The [reference stops source](/docs/api/?api=consumer-stops-v1) is a pointer to this example's instance contract.

The examples use the reference dataset of 2026-11-02. The worked object, list, lookup, resolution and Events response bodies on the linked pages were read from the reference instance. The comparison table above was composed with the object renderer; its operator object is not a captured Get by ID response. Cursors, ETags and event positions belong to a particular instance and read context. Obtain them from your own responses. Webhook deliveries remain explicitly illustrative.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Regional ticketing codes, where used, are fictional.*

## Stable API names

The `consumerApi` in a route, subscription or event is the definition’s public `key`, not a secret or credential. It uses lowercase letters, digits and hyphens and is unique within a model release. A model can declare several APIs for different consumers, each with its own shape, operations, events and contract version. Keep the key when raising the contract version. Changing the key moves the address; requests to the removed name return 404. Display names can change without moving that address.

## Declaration rules and defaults

When authoring a model through an integration, put definitions in `consumerApis`. The current supported model schema language is `0.10`. Its consumer declaration vocabulary uses `exposes`, `object.fields`, `operations` and `filters`. Earlier schema versions are refused with `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`. Eligible stored releases must be raised before use; see [Model language versions](/docs/model/model-language-versions/). Use the [model operations](/docs/api/?api=management#tag/model) to inspect expanded definitions rather than copying an older declaration.

### Fields and related records

A field can be a source name, an ordered list of sources, or an object with `from`, `default`, `role` and `description`. Roles are `id`, `code`, `name`, `active`, `validFrom` and `validTo`. Exactly one field supplies the identity role, and each role is assigned at most once. Role fields appear first in that order; other fields follow declaration order. Do not rely on JSON property order when parsing an object.

The identity role reads the built-in UUID, never a former system's identifier. Publish a former identifier as a separate field and match it through XREF. Sources in one field must share a value type; text and long text count as one type. Defaults must have that served type. Missing values and empty text are skipped in a fallback chain; zero and false are retained. No supplied source or default means null.

Related `via` names are the relation's forward key or reverse key. The selected direction must be bound to at least one exposed type. Its cardinality determines object-or-null versus array; arrays order by related record name, then ID. Fields may read the related record's ID, name, attributes or `ancestor:<type>.<field>`, or `relation:<attribute>`, the value stored on the relationship the item was reached through (`null` when it has none; the attribute must be one the relation's binding carries, and a filter's `matchOn` or an XREF rule may match on it, through that relationship only; the source is refused anywhere else). An ancestor projection reads the ancestor of that type nearest the root. An ancestor criterion in a filter can match any ancestor of that type. A related `objectType` output is allowed only when all reachable types have public names in this API.

The full parent form declares each field's output name and sources. In the short list form, built-in fields keep the role fields' public output names, while other sources use camelCase words. A parent can be present even when its type is not exposed: its public `objectType` is then null. Paths and hierarchies walk ancestors from the root, excluding the record itself. Ancestor labels use the declared name role and fall back to the ancestor’s built-in name. A name containing a slash remains one hierarchy element; do not reconstruct the hierarchy by splitting the path.

Public type names default to the type key in PascalCase and must be unique. Output names must be unique across fields, parent, path, hierarchy and related blocks. The names `objectType`, `matchScore` and `target` are reserved. Asking for a parent code needs a field with the code role.

### Operations and matching

An operation exists only when listed under `operations`. `objects`, `xref` and `resolve` otherwise return `404 OPERATION_NOT_OFFERED` and are omitted from generated OpenAPI. Resolve needs both object reads and XREF. XREF with no `matchOn` is available but finds nothing. Publications and the OpenAPI document remain available independently of the data operations. Lists and events need their own declarations.

A list's `of` selects an exposed type. Its optional `sortBy` must name a bound scalar attribute, excluding JSON. Missing sort values come last, followed by name and creation order as tie breakers. A list's `within` names a filter and optionally its parent types. An Under filter supplies those types by default; another filter verb requires explicit types that can contain the listed type. Changing list order is a contract change.

Match weights are positive integers. Match rules use ID, name or relevant attributes marked searchable or unique. `field: "code"` expands into one rule per source of the code-role field, using the same weights for each. It requires that role. Related promotion rules use `firstOf` in order and can use `preferTypes` to decide which exposed owners receive a related record's score.

### Four filter verbs

Each filter has exactly one verb and only that verb's options:

| Verb | What it does | Options |
| --- | --- | --- |
| `byType: true` | Keeps the selected public types. | No match fields. |
| `under: [types]` | Keeps records below matching ancestors. | `matchOn`; the types must be ancestors of an exposed type. |
| `linkedTo: [types]` | Keeps records linked to a matching record. | `matchOn` and `through`: a related block, `itself`, or `sharedWith:<related>` for records sharing a related record. |
| `onRelated: <block>` | Trims the selected related block to matching items. | `matchOn`, `keepOnlyMatching`, `scoreOnlyMatching`, `crosswalk`. |

Under and Linked to default to matching ID, applicable code sources and name. Code shorthand expands to the sources bound by the relevant types. On related reads fields of its block, including ancestor references. `keepOnlyMatching` also drops objects with no remaining related item; `scoreOnlyMatching` limits promoted scores; `crosswalk` enables `to.<filter>`. These three flags default to false. Only On related can enable crosswalks. `scoreOnlyMatching` requires an XREF promotion rule through that block; otherwise validation refuses a restriction that could never affect a score.

Filter names cannot shadow `query`, `expect`, `pageSize`, `cursor`, `position`, `from`, `seek`, `includeTotal`, `include`, `publication`, `asOf`, `workspace`, `ref`, `id`, `event`, `after` or `payload`, or start with `to.`. Every source, type, relation and ancestor reference is checked against the release. Invalid definitions report the authored path and reason; repair the definition rather than removing a restriction from a client's request.

Descriptions on fields, related blocks, operations, lists and filters appear in generated OpenAPI. They explain a contract without changing stored records. Review the expanded definition, schema and OpenAPI together before activating it.

## Parent values and blocks served on request

A parent can carry more than its identity, code and name. Its `fields` are written as the
object's `fields`: each output name maps to a source or a field definition with `from` and
an optional `default`, without a `role`. For example, `"isApproved": "approved"` publishes
the parent's approval flag under an author-chosen name. A source can be a built-in field,
an attribute bound by a type that directly contains an exposed type, or
`ancestor:<type>.<field>` read from the parent's own ancestors. Ancestor sources also have
an author-chosen output name.

Sources are tried in order and must share one value type. For example,
`"isApproved": {"from": ["approved"], "default": false}` supplies false when the parent has
no approval value. Without a default, missing or unbound values return null. With no
containing record, the entire parent output is null.

Use the full parent form to add named fields and `related` blocks. The short list form
remains valid and outputs a block named `parent`. It names sources only: built-in fields
keep their role's output name, and any other source uses its words in camelCase. For example,
`"category-code"` becomes `categoryCode`. In the full form, you choose the parent block's
output name and every field's output name. Its related blocks use the same `via` and `fields`
rules as the object's, starting from parent types. There is one level: a parent cannot
declare another parent, path or hierarchy inside itself.

**Illustrative catalogue declaration:** this is a consumer API definition for a model with
items contained by categories. The category binds a boolean `approved` attribute. The two
named relationships each allow many code records with a text `external-code` attribute.
These names and data are illustrative, not part of the reference instance.

```json
{
  "key": "catalog",
  "name": "Catalogue API",
  "contractVersion": 1,
  "exposes": ["item", "category"],
  "publicNames": {"item": "Item", "category": "Category"},
  "object": {
    "fields": {
      "id": {"role": "id"},
      "name": {"role": "name", "from": "name"}
    },
    "parent": {
      "output": "parent",
      "fields": {
        "objectType": "objectType",
        "id": "id",
        "name": "name",
        "isApproved": "approved"
      },
      "related": {
        "codes": {
          "via": "category-has-code",
          "fields": {"code": "external-code"},
          "served": "onRequest"
        }
      }
    },
    "related": {
      "codes": {
        "via": "item-has-code",
        "fields": {"code": "external-code"},
        "served": "onRequest"
      }
    }
  },
  "operations": {
    "objects": {},
    "xref": {"matchOn": [{"field": "name", "exact": 100}]},
    "resolve": {},
    "lists": {"items": {"of": "item"}}
  },
  "filters": {
    "categoryCode": {
      "onRelated": "parent.codes",
      "matchOn": ["external-code"],
      "keepOnlyMatching": true
    }
  }
}
```

Each related block has `served`: `always`, the default, or `onRequest`. Always-served blocks
are present in ordinary answers only on types their relationship reaches. On-request blocks are absent unless named in `include`:
`codes` asks for the object's block, and `parent.codes` asks for the parent's. Repeat the
parameter or separate names with commas. These names work on Get by ID, lists and XREF;
Resolve accepts them in each item's `include` or in `defaults.include`.

The `parent.` prefix is fixed for includes and filters, even if `parent.output` is renamed.
Inside `parent.related`, declare the block simply as `codes`, not `parent.codes`. An object's
own related block cannot have a name starting with `parent.`. Output names must not collide
with fields at the same level. An unreadable parent field or invalid relationship is refused
at its authored location, such as `/object/parent/fields/isApproved/source/0` or
`/object/parent/related/codes/via`.

The `categoryCode` filter's name is the author's choice. It narrows the parent's codes and,
with `keepOnlyMatching`, removes children whose parent has no matching code. It works even
when `include` is absent: selecting records does not request the block in the answer. Without
`keepOnlyMatching`, only that block is trimmed. A parent block cannot enable `crosswalk`;
crosswalk targets come from the object's own blocks. The name `include` is reserved and
cannot be used for a filter.

A parent block repeats in each child's answer, so on-request serving can keep lists small.
The generated OpenAPI document lists the accepted include names as an enum on the applicable
GET operations and marks these blocks as optional properties, at both object and parent level.
An included block retains its normal cardinality and field types. Unknown names, including an
always-served block's name, return `400 UNKNOWN_INCLUDE`; `details.valid` lists the valid choices.

In the generated OpenAPI, a parent attribute has its own declared value type and can be
`null` where the record's parent has no value or its type does not bind the attribute.
For example, the catalogue's `isApproved` output reads the `approved` attribute and is a boolean or null.

See [complete reads with and without includes](/docs/integrate/reading-business-objects/#ask-for-a-related-block)
and [includes in batch resolution](/docs/integrate/looking-up-and-resolving/#choose-blocks-for-each-resolved-object).

Events and webhook deliveries have no include request, so their full object payloads omit
on-request blocks. A write to an attribute or ancestor value the parent reads, an item in its
related block, or a relationship joining or leaving it can produce `updated` for each child.
The affected output is the parent's output name. The event must watch that output or leave
its watch list empty. The notification does not imply that an optional block appears in its
payload; read the child with include if you need that block's current contents.

Adding parent fields or blocks, include support or filters is compatible by itself. Changing
an always-served block to `onRequest` removes it from the default answer and needs a higher
contract version. Review that change before activation, just as you would a removed field.

## Publish values of the connection

A related block can expose a value held by the relationship used to reach its item. Write
`relation:<attribute-key>` in `object.related.<block>.fields`. The source reads that connection,
not an attribute of either endpoint. A missing value becomes null; the schema and generated
OpenAPI retain the attribute's type, including boolean and numeric types. All business-object
reads use it: Get by ID, lists, XREF and Resolve. A crosswalk can return it in its selected
related representation too.

**Reference-data example:** the stop-to-operator binding carries Local name (`local-name`,
text), Primary contact (`is-primary`, boolean) and Inspected on (`inspected-on`, date).
The Stops API exposes the first two in its existing v1 `operator` block:

```json
{
  "operator": {
    "via": "stop-operated-by-operator",
    "fields": {
      "id": "id",
      "code": "operator-code",
      "name": "name",
      "localName": "relation:local-name",
      "isPrimary": "relation:is-primary"
    }
  }
}
```

This is the `object.related` excerpt from the reference declaration. Adding these fields is
compatible with its existing contract; it does not require a v2. Carrying Inspected on does
not expose it automatically: this block does not select it.

### Read the object and filter a list

Palüds (B)'s connection to Rhätische Bahn holds Local name “Station office”, Primary contact
Yes and Inspected on 10 January 2026 in the reference data. This complete live answer returns
the two selected relationship values alongside the operator's own fields:

```http
GET /api/consumer/stops/v1/objects/f30fda47-f1a1-4e76-a87d-67f2156ba1f6?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

```json
{
  "objectType": "Stop",
  "id": "f30fda47-f1a1-4e76-a87d-67f2156ba1f6",
  "code": "ch:1:sloid:5331",
  "name": "Palüds (B)",
  "validFrom": "2025-10-14",
  "validTo": null,
  "stopNumber": 8505331,
  "abbreviation": "PALU",
  "latitude": "46.55352096785679",
  "longitude": "9.868828554080435",
  "height": "1755.847",
  "parent": {
    "objectType": "Municipality",
    "id": "8ec1aea0-c18a-4802-ba4f-ac14fc5a00e6",
    "code": null,
    "name": "Bever"
  },
  "path": "Graubünden/Maloja/Bever",
  "operator": {
    "id": "a678d368-1422-4534-bb30-060b163ad717",
    "code": "RhB",
    "name": "Rhätische Bahn",
    "localName": "Station office",
    "isPrimary": true
  },
  "modes": [],
  "systemCodes": [],
  "translations": []
}
```

Tschamut-Selva's connection has neither value: its complete answer near the start of this
page has `localName: null` and `isPrimary: null`. Another stop connected to the same operator
can hold different values. These are sample relationship values, not transport-source facts.
The [list examples](/docs/integrate/reading-business-objects/) return these fields too.
The reference `operator` filter still matches the operator's code or name; it does not match
Local name or Primary contact.

An `onRelated` filter's `matchOn` can select `relation:local-name` or `relation:is-primary`
when the model declares that choice. It compares each item's own connection. With
`keepOnlyMatching: true`, it drops objects with no matching item; without that option it
only trims the related block. `scoreOnlyMatching` and `crosswalk` retain their usual meanings.
These relationship-value filters are supported choices, but are not declared in Stops API.

### Match and resolve through that connection

`alsoMatchThrough.firstOf` can name `relation:local-name` even if the block does not expose it.
A scored relationship source must hold text. Its weight belongs to the connection that
matched: another stop sharing the operator does not receive that score just because this
stop's connection holds “Station office”. Relationship attributes need neither Searchable nor
Unique for these matching choices. Matching reads the relationships' values, so broad rules
over many connections can cost more than an indexed identifier lookup.

The reference Stops API matches through system codes and translated names, not through
Local name. Its [captured XREF and Resolve answers](/docs/integrate/looking-up-and-resolving/)
include `localName` and `isPrimary` because they reuse the declared object, regardless of
which source matched the query.

### Publications, business dates and validation

Use `publication` to read the saved relationship values in a compatible publication. An `asOf`
read applies business validity in the selected source; it does not restore the relationship's
values to what they were on that date. For the shipped contract's validity fields and the
complete sequence, see [Business dates](/docs/integrate/business-dates/) and
[Reading business objects](/docs/integrate/reading-business-objects/).

The source is allowed only in related fields, an `onRelated` filter's `matchOn`, and a related
XREF promotion's `firstOf`. Main object fields, own XREF rules and `under` or `linkedTo` match
fields refuse it with `INVALID_REFERENCE`. The named attribute must be carried by a binding
of that relation, in the chosen direction, reachable from an exposed type. Validation names
the authored path, relation and attribute. A non-text relationship attribute in a scored
`firstOf` rule is `INVALID_MODEL`. Correct the model; dropping a request filter does not repair
an invalid declaration.

### Follow edits of carried values

An event watching a related block that exposes relationship values can report an edit of
those values with `change: updated` and `changed: ["operator"]`. This names the affected
block, not an old/new value diff. The reference `stops-changed` event watches only code, name
and validity fields; it does not report connection-value edits unless its watch declaration
changes. Unpublished change-set edits produce no consumer event; publication makes their
committed effects eligible.

With full payload, a reference event includes the current business object, including
`operator.localName` and `operator.isPrimary`, and `stateAt`. Those values are composed at
read or delivery time, rather than frozen at the event's position. See the
[captured full event and webhook request shape](/docs/integrate/consumer-events-and-webhooks/)
for complete bodies, signing, retries, CloudEvents and recovery.

## Review a contract change

Activation compares with what consumers read in the workspace’s current release and refuses unversioned breaks. Draft contract review compares with its base release, or the latest installed release of the same model when there is no base. Review the target workspace’s activation compatibility as well. Installing a release alone does not change the API consumers read. Removing a whole definition produces a warning and ends its address on activation; it does not preserve the old API.

Removing or retyping a field, changing related cardinality, removing an exposed type, operation, list or filter, changing a filter’s verb, changing a list’s type, parent scope or ordering, changing matching weights or score restrictions, or disabling crosswalks can require a higher `contractVersion`. Event coverage is checked too. Unbinding an attribute from a type, or changing a relation so a related block no longer reaches that type, removes an output from that type’s objects and is breaking. A field or block joining a type is additive. Adding fields or operations is normally compatible. Coordinate any version increase before activation: the server serves the current definition and any retained earlier definitions. See [Compatibility](/docs/integrate/compatibility/) for notice ownership and [earlier versions](#earlier-contract-versions) for discovery and recovery.

## Earlier contract versions

A definition can retain frozen contracts in `earlierVersions`. Each contains its own
`contractVersion`, `exposes`, `publicNames`, `object`, `operations` and `filters`, with optional
`description`, `deprecated` and `sunset` dates. Numbers must be positive, unique and lower than
the current version. Dates use `YYYY-MM-DD`. Every reference is validated against the current
model; keeping a contract does not preserve deleted types or attributes. A missing source
is refused with the API, earlier version and failing path named. Restore that source or
stop the version deliberately. Model administrators
use [Earlier versions](/docs/model/consumer-apis/#keep-an-earlier-version-available).

The authenticated index returns an entry for each served version, current first followed by
retained versions for that API. A retained entry has `deprecated: true` and, when set, `sunset`.
Its `openapi` points to that version’s document. Each operation in the earlier document is
marked `deprecated: true`, and its introduction identifies the current version and announced
sunset day. Read that document when preparing a client migration; an unchanged API key does
not mean that v1 and v2 return the same shape.

The `deprecated` day records when the earlier contract was superseded. The editor defaults
it to the day of the raise. If an authored earlier version omits it, responses use the active
release’s installation time. The optional `sunset` date is the administrator’s announced
end day, and can be cleared without removing the version.

For a retained version, responses carry `Deprecation` as an RFC 9745 structured date
(`@` followed by Unix seconds). They also carry `Sunset` as an RFC 8594 HTTP date when a
sunset day is set, at midnight UTC. These headers announce the retained version even on
errors after the version has been selected. The sunset date does not turn a route off.
The model administrator chooses the notice period and explicitly removes the version.

For integrations that author models, use the [model-authoring operations](/docs/api/?api=management#tag/model%20administration)
to raise the current version and retain the base release’s definition, set or withdraw its
sunset, or remove an earlier version. Review the resulting authored definition and compile
findings before installation and workspace activation. Directly supplying `earlierVersions`
must preserve the original definition too; copying the new edited definition under the old
number does not preserve its contract. The same checks apply to browser and API authoring.

**Illustrative migration example using the reference stops API:** after its administrator
raises to v2 while keeping v1, the existing request still works:

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden
Authorization: Bearer <consumer-token>
```

The object remains in the v1 shape shown in [Reading business objects](/docs/integrate/reading-business-objects/),
with current values. Its headers might include:

```http
Deprecation: @1794009600
Sunset: Sun, 07 Nov 2027 00:00:00 GMT
```

These dates illustrate an administrator’s announcement, not a captured reference-instance
upgrade. Once v1 is explicitly removed and that release is activated, the same request
returns HTTP 404, with this body if v2 is the only remaining version:

```json
{
  "error": {
    "code": "CONTRACT_VERSION_NOT_FOUND",
    "message": "Consumer API 'stops' has no contract version '1'; it serves version 2",
    "details": {"contractVersion": 2, "servedContractVersions": [2]}
  }
}
```

Rediscover the contract, read its generated document and change the client deliberately.
Do not automatically retry against the first number in `servedContractVersions`: its output
may require a different parser. An older publication cannot make a stopped route available.

Release checks refuse changes that break a retained contract with
`CONSUMER_KEPT_VERSION_CHANGED`. Its message identifies the API, version and change, ending
**a kept version is served as it was: restore it, or stop serving it**. Restore that version’s
contract and the model sources it depends on, or coordinate its removal. Raising the current
number again does not fix the retained contract. Deliberately removing a retained version
produces `CONSUMER_VERSION_STOPPED`, for example:

> Consumer API 'stops' stops serving version 1; its consumers will receive 404 CONTRACT_VERSION_NOT_FOUND from /api/consumer/stops/v1

Review the warning with the affected client owners before activation. Stopping one version
preserves the records and other served versions; removing the whole API ends every version.
