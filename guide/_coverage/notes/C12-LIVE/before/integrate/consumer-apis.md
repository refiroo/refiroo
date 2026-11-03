---
title: Consumer APIs
description: Use a declared business contract rather than the underlying record model.
reader: integrator
---

A consumer API is a read-only business contract declared in a model. It exposes selected record types under public names, defines their fields and related blocks, and chooses which reads, lookups, lists and events are available. Integrators use that contract without reconstructing the underlying record graph.

A model administrator [designs the consumer API](/docs/model/consumer-apis/). Defaults are expanded by the engine, and references are validated before use. Adding an operation can extend a contract; removing fields, operations, exposed types or supported behavior requires a higher contract version. The activation check refuses an unversioned breaking change.

## Learn one way to read business objects

Consumer APIs share one way of presenting and reading business objects, whatever data the model describes. Within a consumer API, every exposed type uses the same declared object shape: common identity and descriptive fields, followed by the fields and related parts its definition adds. Get by ID, lists, lookups and batch resolution reuse that object. You do not need a separate parser for each type or a sequence of management reads to assemble its relationships.

The model chooses the content: exposed types, public names, field sources, related blocks, filters, matching rules and events. The engine supplies the ways to compose and read it. Related records can appear as an object or an array, with selected fields such as identity, code and name. System codes, translations, a parent and an ancestor path are declared parts of the same answer. They use ordinary fields and relationships; they are not special features tied to one domain.

### Two types, one declared shape

**Reference-data example:** the `stops` API exposes both stops and operators. These two Get by ID answers have exactly the same fields. The table places their complete object bodies side by side; values come from the reference snapshot, composed with the engine's object renderer rather than captured over HTTP.

| Field | Stop: Tschamut-Selva | Operator: Matterhorn Gotthard Bahn (fo) |
| --- | --- | --- |
| `objectType` | `"Stop"` | `"Operator"` |
| `id` | `"8d90eede-23cf-47c1-8dac-cb37956f5fd5"` | `"f94ef862-2a95-4675-9e31-6b1d0a03317f"` |
| `code` | `"ch:1:sloid:5173"` | `"MGB-fo"` |
| `name` | `"Tschamut-Selva"` | `"Matterhorn Gotthard Bahn (fo)"` |
| `validFrom` | `"2021-04-01"` | `null` |
| `validTo` | `null` | `null` |
| `stopNumber` | `8505173` | `null` |
| `abbreviation` | `"TSSE"` | `null` |
| `fsoNumber` | `null` | `null` |
| `latitude` | `"46.65674442039232"` | `null` |
| `longitude` | `"8.709084193690385"` | `null` |
| `height` | `"1701.3"` | `null` |
| `sboid` | `null` | `"ch:1:sboid:100029"` |
| `parent` | `{"objectType": "Municipality", "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc", "code": null, "name": "Tujetsch"}` | `null` |
| `path` | `"Graubünden/Surselva/Tujetsch"` | `""` |
| `operator` | `{"id": "f94ef862-2a95-4675-9e31-6b1d0a03317f", "code": "MGB-fo", "name": "Matterhorn Gotthard Bahn (fo)"}` | `null` |
| `modes` | `[{"id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9", "code": "TRAIN", "name": "Train"}]` | `[]` |
| `systemCodes` | `[{"system": "Wikidata: stations", "systemKey": "wikidata-stations", "code": "Q33467326", "name": "Q33467326 Tschamut-Selva"}]` | `[]` |
| `translations` | `[]` | `[]` |

The operator's stop-specific fields are null, while its own business identifier appears in `sboid`. It has no parent, so `parent` is null and `path` is empty. Its related arrays are empty. A reader handles these using the same rules as for the stop. Values keep their declared types: `stopNumber` is an integer, while decimals are strings to retain precision.

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

This lets you reuse a parser and the same read, page, resolve, cache and event-processing flows across types and consumer APIs. A client driven by the declared contract can accommodate another type or API through configuration. Check its generated document: output names, optional parts, related fields and cardinality can differ between declarations, so a client with fixed field names may need changes.

Each consumer contract has its own version, separate from the model release and management API. Model changes can preserve what consumers read; breaking contract changes require a higher version. Stability protects an agreed contract while its underlying model evolves. It does not promise that every declaration has identical field names or that a new version requires no client changes.

## Discover and obtain access

Read the [consumer API index](/docs/api/?api=management#tag/consumer) for the workspace. It identifies contracts and their own OpenAPI documents. Each contract's routes and typed answers are described separately from the management API. The workspace's model determines the available version; using another version can produce `CONTRACT_VERSION_NOT_FOUND`. The workspace serves its currently declared version for live reads. Raising the version does not leave a parallel old live endpoint; coordinate activation with consuming systems. Historical publication reads resolve the publication's own definition as described below.

A client needs a consumer-audience token and a consumer API grant in that workspace. A management role does not grant consumer data. An administrator [grants the client access](/docs/administer/clients/). Public OpenAPI documents describe contracts without exposing records; the index and data reads require authentication. A consumer token sees only granted APIs in the index, possibly none. A management token with Browse in the workspace sees all its APIs in the index. The per-definition OpenAPI document is public. Its OAuth 2.0 client-credentials scheme points to the instance’s token endpoint and requests the consumer scope.

Data requests check the token, workspace, consumer grant, then API name and version, in that order. A missing grant can therefore return `403 FORBIDDEN` even for an undeclared API name. This also applies to publication reads. Missing credentials return `401 AUTHENTICATION_REQUIRED`; invalid credentials return `401 TOKEN_INVALID`, with `details.reason` such as `expired`, `revoked`, `audience`, `unknownKey`, `malformed` or `signature`. Both 401 responses carry `WWW-Authenticate: Bearer`. A forbidden consumer read names `consumerApi` and `workspaceKey` in its details. Obtain a valid token for a 401; ask the administrator to review the workspace grant for a 403.

**Example:** the guide's reference model declares the `stops` contract. Its [Get by ID operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/objects/{id}) presents stops with their municipality, operator, modes, system codes and names. Those names and projections are model configuration; other models can expose different business objects.

## Understand the shared object

Reads by ID, lists and lookups use the same declared business representation. Values retain their types. Declared fields use their configured sources, defaults or an empty value. Parent fields use the object's declared output names; an unexposed parent's public type is empty. The declaration can include the parent, ancestor path and hierarchy as part of that representation. Related blocks follow cardinality: a single object or an ordered list. A projected public type is available only when the definition exposes all reachable types.

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
        "fields": {"id": "id", "code": "operator-code", "name": "name"}
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
| `object.fields` | Every shared object has these output names. `stopNumber` reads the underlying `stop-number` value. |
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

In the browser, **Settings › Integration › Consumer APIs** lists the declared APIs, and **API reference** opens their interactive documents. Both describe the selected workspace's model; they do not make a contract available in another workspace. The [reference stops source](/docs/api/?api=consumer-stops-v1) is a pointer to this example's instance contract.

The examples in this section use the reference snapshot of 2026-11-02. Object values were composed from that data with the engine's object renderer; they are not captures of a live HTTP session. Tokens, cursors, ETags, event positions, event IDs and delivery IDs depend on an instance and are marked as example values where used.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Regional ticketing codes, where used, are fictional.*

## Stable API names

The `consumerApi` in a route, subscription or event is the definition’s public `key`, not a secret or credential. It uses lowercase letters, digits and hyphens and is unique within a model release. A model can declare several APIs for different consumers, each with its own shape, operations, events and contract version. Keep the key when raising the contract version. Changing the key moves the address; requests to the removed name return 404. Display names can change without moving that address.

## Declaration rules and defaults

When authoring a model through an integration, put definitions in `consumerApis`. The current supported model schema language is `0.10`. Its consumer declaration vocabulary uses `exposes`, `object.fields`, `operations` and `filters`. Earlier schema versions are refused with `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`. Eligible stored releases must be raised before use; see [Model language versions](/docs/model/model-language-versions/). Use the [model operations](/docs/api/?api=management#tag/model) to inspect expanded definitions rather than copying an older declaration.

### Fields and related records

A field can be a source name, an ordered list of sources, or an object with `from`, `default`, `role` and `description`. Roles are `id`, `code`, `name`, `active`, `validFrom` and `validTo`. Exactly one field supplies the identity role, and each role is assigned at most once. Role fields appear first in that order; other fields follow declaration order. Do not rely on JSON property order when parsing an object.

The identity role reads the built-in UUID, never a former system's identifier. Publish a former identifier as a separate field and match it through XREF. Sources in one field must share a value type; text and long text count as one type. Defaults must have that served type. Missing values and empty text are skipped in a fallback chain; zero and false are retained. No supplied source or default means null.

Related `via` names are the relation's forward key or reverse key. The selected direction must be bound to at least one exposed type. Its cardinality determines object-or-null versus array; arrays order by related record name, then ID. Fields may read the related record's ID, name, attributes or `ancestor:<type>.<field>`. An ancestor projection reads the ancestor of that type nearest the root. An ancestor criterion in a filter can match any ancestor of that type. A related `objectType` output is allowed only when all reachable types have public names in this API.

The parent block uses the role fields' public output names. A parent can be present even when its type is not exposed: its public `objectType` is then null. Paths and hierarchies walk ancestors from the root, excluding the record itself. Ancestor labels use the declared name role and fall back to the ancestor’s built-in name. A name containing a slash remains one hierarchy element; do not reconstruct the hierarchy by splitting the path.

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

Filter names cannot shadow `query`, `expect`, `pageSize`, `cursor`, `position`, `from`, `seek`, `includeTotal`, `publication`, `asOf`, `workspace`, `ref`, `id`, `event`, `after` or `payload`, or start with `to.`. Every source, type, relation and ancestor reference is checked against the release. Invalid definitions report the authored path and reason; repair the definition rather than removing a restriction from a client's request.

Descriptions on fields, related blocks, operations, lists and filters appear in generated OpenAPI. They explain a contract without changing stored records. Review the expanded definition, schema and OpenAPI together before activating it.

## Review a contract change

Activation compares with what consumers read in the workspace’s current release and refuses unversioned breaks. Draft contract review compares with its base release, or the latest installed release of the same model when there is no base. Review the target workspace’s activation compatibility as well. Installing a release alone does not change the API consumers read. Removing a whole definition produces a warning and ends its address on activation; it does not preserve the old API.

Removing or retyping a field, changing related cardinality, removing an exposed type, operation, list or filter, changing a filter’s verb, changing a list’s type, parent scope or ordering, changing matching weights or score restrictions, or disabling crosswalks can require a higher `contractVersion`. Event coverage is checked too. Adding fields or operations is normally compatible. Coordinate any version increase before activation: the current server serves one live version per definition. See [Compatibility](/docs/integrate/compatibility/) for the published commitment and this implementation limit.
