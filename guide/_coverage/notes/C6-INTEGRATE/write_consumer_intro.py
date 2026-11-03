from finish_unit import root,steering,finish
steering()
p=root/'src/content/docs/integrate/consumer-apis.md'
s=p.read_text()
s=s.replace('using another version can produce `CONTRACT_VERSION_NOT_FOUND`.', 'using another version can produce `CONTRACT_VERSION_NOT_FOUND`. The workspace serves its currently declared version for live reads. Raising the version does not leave a parallel old live endpoint; coordinate activation with consuming systems.')
s=s.replace('The publication uses its own model definition at the requested contract version, not today\'s definition.', 'The publication uses its own model definition at the requested contract version, not today\'s definition. The requested version must first be offered by the workspace\'s current model. Selecting a publication cannot restore a route for a version no longer offered.')
s+='''
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
'''
p.write_text(s)
finish(['src/content/docs/integrate/consumer-apis.md'],'Applied steering: added a reference declaration excerpt, declaration-to-path/parameter/response mapping, defaults and direct contract discovery. Explained current-version and historical-definition limits. Examples use offline production composition; live HTTP capture is blocked by the environment.')
