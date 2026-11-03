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

A client needs a consumer-audience token and a consumer API grant in that workspace. A management role does not grant consumer data. An administrator [grants the client access](/docs/administer/clients/). Public OpenAPI documents describe contracts without exposing records; the index and data reads require authentication.

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

Read the authenticated index at `/api/consumer?workspace=graubuenden` in this example. Each entry gives the API key, contract version and its OpenAPI document address. The reference document is `/api/consumer/stops/v1/openapi.json?workspace=graubuenden`. Each document is OpenAPI 3.1 and includes the concrete paths and shapes generated from that workspace's declaration. Use it to generate or validate your client after understanding the sequence here.

In the browser, **Settings › Integration › Consumer APIs** lists the declared APIs, and **API reference** opens their interactive documents. Both describe the selected workspace's model; they do not make a contract available in another workspace. The [reference stops source](/docs/api/?api=consumer-stops-v1) is a pointer to this example's instance contract.

The examples in this section use the reference snapshot of 2026-11-02. Object values were composed from that data with the engine's object renderer; they are not captures of a live HTTP session. Tokens, cursors, ETags, event positions, event IDs and delivery IDs depend on an instance and are marked as example values where used.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Regional ticketing codes, where used, are fictional.*
