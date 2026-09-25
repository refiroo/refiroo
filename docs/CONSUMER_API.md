# Consumer API (Product 0.9)

Status: proposed scope for 0.9, alongside the integration items already listed in ROADMAP.md.
Decisions still open are listed at the end (C-D1 to C-D6).

## Why a second API tier

The API in API.md is the **management API**. It maintains models and data: change sets, publication
history, typed filters, optimistic concurrency and graph-shaped responses. The UI and the tools that
synchronize or administer reference data use it.

The **consumer API** is for the systems that *use* reference data in integration flows. Those systems
look a value up, translate it between systems and read lists of it. They need:

- one object shape for every object type, so a flow does not need a parser per type;
- a single lookup that finds an object by any of its identifiers: its own ID or code, a system's code
  or external ID, a translated name;
- the object's system representations, translations and selected related objects in the same response;
- a contract that stays stable while the model and management API change.

The consumer API is read-only. It is not a thinner management API. Its responses are composed business
objects, and its contract is defined in the model, not in code.

## Reference implementation

This design comes from a consumer API already running in production. It is an API gateway policy set
over the source platform's reference data, and it is the functional baseline for this scope. The
policies are not stored in this repository (AGENTS.md). This section records what they do in engine
terms.

### XREF lookup

`GET /xref?query=…&type=…&codelist=…&domain=…&system=…&location=…`

- `query` is required. A comma-separated value is several terms, and an object's score is its best
  score across the terms.
- Candidates are master-data objects of every type, locations included.
- **Scoring for one term** (case-insensitive):

  | Where the term matches | Exact | Contains |
  | --- | ---: | ---: |
  | Object: global ID (master ID) | 1000 | — |
  | Object: value code, operator code | 500 each | 40 each |
  | Object: name, value name | 200 each | 30 each |
  | System value: name | 80 | 15 |
  | System value: external ID, system value name | 75 | 10 |
  | System value: system value code | 70 | 10 |
  | Translation: translated name | 60 | 12 |

  The object's own exact scores add up. Its "contains" scores count only when no exact score applied.
  A system value takes the first match in this order: exact name, code, external ID, value name, then
  contains on the same four. So a value whose code and external ID both match scores 70, not 75.
  Translations work the same way.
- **Promotion:** a matching system value or translation passes its score to the objects it relates to
  (highest score wins). When a system value relates to a location and to something else, only the
  location gets the score. This is what lets a location-only system value be found by external ID.
- **Filters**, applied after scoring:
  - `type`: object type.
  - `system`: keep only objects mapped by a system value of that system. Also limits which system
    values score and which appear in `systemVariants`.
  - `codelist` and `domain`: an ancestor's name or code.
  - `location`: a location matched by ID, name, code or value name. Keeps the location itself, objects
    available at it, and objects sharing a system value with it.
- **Cap:** results stop at `max(20, number of terms)`. `totalCount` is the number returned, not the
  number matched.

### Lists

One list per object type, on hierarchical routes such as `/domains/{domainId}/codelists`,
`/codelists/{codelist}/values` and `/stations/{stationId}/locations`.

- The parent segment accepts a global ID, an internal ID, or a name or code.
- Paging uses `page` and `pageSize`. `language` keeps only objects that have a translation in that
  language and limits `translations` to it. `locationId` filters by availability.
- The envelope is `page`, `pageSize`, `totalCount`, `returnedCount`, `items`.

### The shared object

XREF results and list items use the same object:

```json
{
  "objectType": "TimetableType",
  "masterId": "…", "code": "…", "name": "…", "valueName": "…",
  "sortOrder": 0, "isActive": true, "internalOnly": false,
  "validFrom": "", "validTo": "",
  "matchScore": 60,
  "systemVariants": [{ "system": "…", "value": "…", "valueCode": "…", "valueName": "…", "externalId": "…", "isActive": true }],
  "translations":   [{ "name": "…", "languageCode": "es", "languageName": "Spanish", "translatedName": "…", "translatedDescription": "…", "isActive": "true" }],
  "availableAt":    [{ "locationId": "…", "locationName": "…", "locationValueCode": "…", "locationValueName": "…" }],
  "duration":       [{ "durationId": "…", "durationCode": "…", "durationName": "…" }],
  "alternative":   [{ "objectType": "…", "masterId": "…", "code": "…", "name": "…" }],
  "path": "A/B/C", "parent": { "objectType": "…", "name": "…", "code": "…", "masterId": "…" },
  "hierarchy": ["A", "B", "C"]
}
```

`code` takes the first non-empty value of operator code, value code, codelist code, domain code and
station code. List items also carry `description`. Stations also carry `operatorCode` in XREF results.

### How flows call it

Integration flows call XREF through a shared gateway fragment. It sends the query with optional
filters, **takes the first result** and extracts one to three fields from it. It looks for the field at
the top level first, then in the nested arrays (limited to the requested system when the array has a
`system` field), then in `parent`. In practice XREF is the resolve operation: most flows pass a code or
external ID with `system` and use the top result.

### Behavior the engine does not carry over

Each item below is observed in the reference policies. The engine either fixes it or makes it explicit:

| Reference behavior | Engine behavior |
| --- | --- |
| Result cap of `max(20, terms)`; `totalCount` equals the returned count | Paged (ADR-030) with a real total. The default page size keeps the familiar 20 |
| Results with equal scores come back in an unspecified order (unstable sort), and flows take the first | Deterministic order: score, then object type, name, ID. `expect=one` returns an error instead of guessing when the top score is tied |
| Booleans and dates as strings (`"isActive": "true"` in translations, `validFrom: ""`) | Declared types kept: booleans, ISO dates, `null` |
| XREF omits `parent` for top-level objects; lists send a parent with empty strings | `parent` is always present; `null` when there is none |
| Lists build `hierarchy` by splitting `path` on `/`; XREF walks parents | Always walks parents, so names containing `/` stay one element |
| `operatorCode` exists only for one type; `description` only in lists | Fields come from the definition, not from type checks. XREF and lists return the same object |
| `alternative` is documented as an object or null but returned as an array | Single-valued relations project as an object or `null`, many-valued ones as an array (from relation cardinality) |
| The list `locationId` filter keeps items with no availability and compares a field that does not exist | Filter semantics are defined and tested |
| Cache invalidation by `X-Reset-Cache` and TTL | No manual reset: responses carry an ETag derived from the data and definition versions |

## Engine design

### Principle

The engine gets **no runtime knowledge** of locations, durations, alternatives, stations, system
values or translations (AGENTS.md). In this document they are examples from the reference deployment,
not requirements. Everything the reference policies hard-code (attribute and relation IDs, type
names, scoring weights, filter behavior, output field names) becomes a **consumer API definition** in
the model. The reference response must be reproducible from a definition alone. That is the
acceptance test for this scope (C8).

### Where definitions live

Consumer API definitions are a new top-level `consumerApis` section of the model document. They are
validated, compiled, installed and pinned like the rest of the model release. This reuses the existing
draft → validate → install lifecycle, gives every definition the model's precise path-and-reason
errors, and ensures a definition can never reference a type or relation the release lacks.

Each definition has its own `contractVersion`, separate from the model release version. A new model
release that changes a published definition's output must raise that definition's `contractVersion`.
Model validation compares definitions with the previously installed release and rejects an unmarked
breaking change (C-D2).

### Definition shape

```jsonc
"consumerApis": [{
  "key": "rdm",
  "name": "RDM consumer API",
  "contractVersion": 1,

  // Public object type names and which types are exposed.
  "objectTypes": {
    "master-value": { "publicName": "CodelistValue" },
    "codelist":     { "publicName": "Codelist" },
    "location":     { "publicName": "Location" }
    // …
  },

  // The common object: fixed roles, output names chosen by the definition.
  "object": {
    "id":        { "output": "masterId",  "source": ["master-id"] },
    "code":      { "output": "code",      "source": ["operator-code", "value-code", "codelist-code", "domain-code"] },
    "name":      { "output": "name",      "source": ["name"] },
    "active":    { "output": "isActive",  "source": ["active"], "default": true },
    "validFrom": { "output": "validFrom", "source": ["valid-from"] },
    "validTo":   { "output": "validTo",   "source": ["valid-to"] },
    "attributes": {
      "valueName":    { "source": ["value-name"] },
      "sortOrder":    { "source": ["sort-order"], "default": 0 },
      "internalOnly": { "source": ["internal-only"], "default": false },
      "description":  { "source": ["description"] }
    },
    "parent": { "output": "parent", "fields": ["objectType", "id", "code", "name"] },
    "path": "path", "hierarchy": "hierarchy"
  },

  // Named related-object blocks.
  "projections": {
    "systemVariants": {
      "from": { "relation": "system-value-maps-to-master", "direction": "incoming" },
      "fields": {
        "system":     "ancestor:system.name",
        "value":      "name",
        "valueCode":  "value-code",
        "valueName":  "value-name",
        "externalId": "external-id",
        "isActive":   "active"
      }
    },
    "translations": {
      "from": { "relation": "object-has-translation", "direction": "outgoing" },
      "fields": {
        "languageCode":          "ancestor:language.language-code",
        "languageName":          "ancestor:language.name",
        "translatedName":        "translated-name",
        "translatedDescription": "translated-description",
        "isActive":              "active"
      }
    },
    "availableAt": {
      "from": { "relation": "available-at-location", "direction": "outgoing" },
      "fields": { "locationId": "master-id", "locationName": "name", "locationValueCode": "value-code", "locationValueName": "value-name" }
    }
  },

  // XREF matching.
  "match": {
    "own": [
      { "field": "master-id",  "exact": 1000 },
      { "field": "value-code", "exact": 500, "contains": 40 },
      { "field": "operator-code", "exact": 500, "contains": 40 },
      { "field": "name",       "exact": 200, "contains": 30 },
      { "field": "value-name", "exact": 200, "contains": 30 }
    ],
    "promoted": [
      { "projection": "systemVariants", "firstMatch": [
          { "field": "name", "exact": 80 }, { "field": "value-code", "exact": 70 },
          { "field": "external-id", "exact": 75 }, { "field": "value-name", "exact": 75 },
          { "field": "name", "contains": 15 }, { "field": "value-code", "contains": 10 },
          { "field": "external-id", "contains": 10 }, { "field": "value-name", "contains": 10 } ],
        "preferTargetTypes": ["location"] },
      { "projection": "translations", "firstMatch": [
          { "field": "translated-name", "exact": 60 }, { "field": "translated-name", "contains": 12 } ] }
    ]
  },

  // Request parameters, each bound to a generic filter kind.
  "parameters": {
    "type":     { "kind": "objectType" },
    "system":   { "kind": "projection", "projection": "systemVariants", "matchFields": ["ancestor:system.name", "ancestor:system.system-code"],
                  "scoresFrom": true, "requireMatch": true },
    "codelist": { "kind": "ancestor", "objectTypes": ["codelist"], "matchFields": ["name", "codelist-code"] },
    "domain":   { "kind": "ancestor", "objectTypes": ["domain"], "matchFields": ["name", "domain-code"] },
    "location": { "kind": "related", "objectTypes": ["location"], "matchFields": ["master-id", "name", "value-code", "value-name"],
                  "via": ["availableAt", "self", "sharedProjection:systemVariants"] },
    "language": { "kind": "projection", "projection": "translations", "matchFields": ["ancestor:language.language-code"], "requireMatch": true }
  },

  // Lists.
  "lists": [
    { "key": "codelists", "objectType": "codelist", "parentParameter": { "name": "domain", "objectTypes": ["domain"] } },
    { "key": "values",    "objectType": "master-value", "parentParameter": { "name": "codelist", "objectTypes": ["codelist"] } }
    // …
  ]
}]
```

The example is the reference deployment's definition. Every key, projection and parameter name in it
is that deployment's choice, not something the engine requires. Keys missing from `rdm-starter.json`
(`available-at-location`, `location`, `operator-code`, `internal-only`) come from a model that extends the
starter, as the source deployment's does.

The engine supplies only these parameter kinds. A definition names its parameters and binds each one
to a kind:

| Kind | Effect |
| --- | --- |
| `objectType` | Keeps objects of the named public types |
| `ancestor` | Keeps objects that have an ancestor of the listed types matching on `matchFields` |
| `related` | Keeps objects linked to a matching object through the `via` routes: a projection, the object itself, or a shared projection (both objects relate to the same projected object) |
| `projection` | Limits a projection to the items that match on `matchFields`. `requireMatch` also drops objects left with no matching item. `scoresFrom` means only the matching items pass scores on to their objects |

In the example, `system` and `language` are both `projection` parameters. The engine does not treat
them as a system or a language.

Rules the validator enforces:

- **Sources:** every `source`, `field` and `ancestor:<type>.<field>` reference resolves in the release.
  A source list means "first non-empty value", which replaces the reference `code` fallback chain.
- **Scalar values** keep their declared attribute type; `default` must match that type.
- **Projection shape:** a projection is an object or `null` when the relation, in that direction,
  allows at most one related object, and an array otherwise. This is derived, never declared, so a
  model cardinality change becomes a contract change the validator can see.
- **Match fields** must be `searchable` or explicitly listed as identifiers; weights are positive
  integers.
- **Parameter names** are unique per definition and cannot shadow reserved names (`query`, `expect`,
  `pageSize`, `cursor`, `position`, `revision`).

### Endpoints

```text
GET /api/consumer/{apiKey}/v{contractVersion}/xref?query=…&{parameters}&expect=one|any&pageSize=…
GET /api/consumer/{apiKey}/v{contractVersion}/objects/{id}?{parameters}
GET /api/consumer/{apiKey}/v{contractVersion}/lists/{listKey}?{parentParameter}=…&{parameters}&position=…&pageSize=…
GET /api/consumer/{apiKey}/v{contractVersion}/openapi.json
```

- **XREF** keeps the reference request and response shape, with `results`, `query` and `totalCount`
  plus the paging fields of ADR-030. `expect=one` returns the single top result, `404` when nothing
  matched, and `409 AMBIGUOUS_MATCH` naming the tied candidates when the top score is shared. Flows
  that resolve a value use it in place of "take the first result".
- **Get by ID** returns one object in the same shape; `id` is the definition's identity field.
- **Lists** use position paging (`position`/`pageSize`), the reference's page-number model. The
  parent parameter accepts the parent's identity, name or declared code fields, like the reference.
- **Unknown parameters** are rejected with `400` naming them. Unknown `apiKey`, `listKey` or
  `contractVersion` return `404`.
- **Generated OpenAPI:** each definition generates its own OpenAPI document, so integrators get a
  typed contract per API.
- **Consistency:** reads use live data by default. `revision={workspaceRevisionId}` reads a
  publication, so a flow or extract can pin one consistent snapshot. Responses carry
  `ETag: "{dataVersion}:{contractVersion}"` and honor `If-None-Match`.

The existing gateway can stay in front and map the reference routes (`/xref`,
`/stations/{stationId}/locations`, …) onto these endpoints, so current consumers move without changes
(C-D5).

### Read index

The reference answers in about 100 ms only from its cache; a miss reloads the whole dataset. The
engine cannot score every object and join every projection per request. Each definition gets a
**consumer index** per workspace:

- a match table of (object, source field or promoted-from object, normalized value, weights), so an
  exact lookup is an index seek and "contains" runs over one narrow table;
- a precomputed hierarchy path per object;
- updated in the same transaction as the live write that changes an indexed value or relation, like
  `snapshot_attribute_values` in 0.8 S2, and rebuilt on definition or model install.

Projections for a result page are loaded in one batched query per projection, not per object. Budgets
are set against the 0.8 Track S volume fixture (C8).

## Delivery packages

| Package | Scope |
| --- | --- |
| C1 | `consumerApis` schema, model validation with precise paths, compile into the immutable snapshot, breaking-change check against the installed release |
| C2 | Common object and projections: get by ID, ancestor fields, cardinality-derived shape, typed values |
| C3 | Lists: parent parameter resolution, position paging, parameters of kind `ancestor`, `projection` and `related` |
| C4 | Consumer index and XREF scoring: own-field and promoted scores, multi-term queries, deterministic order, `expect=one` |
| C5 | XREF parameters of kind `objectType`, `projection`, `ancestor` and `related` (including via a shared projection) |
| C6 | ETag / `If-None-Match`, `revision` reads, per-definition OpenAPI |
| C7 | Consumer access control (see C-D1) |
| C8 | Parity acceptance: a test-only fixture model extending the starter with locations, availability and a single-valued self relation (fixture content, not product scope), a fixture dataset, and a definition that reproduces the reference response for the scenarios below; volume budgets |

C1 comes first. C2 builds on C1. C3 and C4 can run in parallel after C2. C5 follows C4, C6 follows C3
and C4, and C8 closes the scope. The P1 cross-type lookup (Base 0.8 plan, D20) is not a prerequisite:
XREF searches the consumer index, not `GET /objects`.

**C8 parity scenarios.** For each, the response must match the reference shape, except where the
table under "Behavior the engine does not carry over" says otherwise:

1. an exact global ID; an exact code; a partial name;
2. an external ID with and without `system`;
3. a system value that maps only to a location, found by its external ID;
4. a translated name;
5. a multi-term query;
6. `codelist` and `domain` by name and by code;
7. `location` via availability, via the location itself, and via a shared system value;
8. `system` combined with `location`;
9. a tie at the top score with `expect=one`;
10. a list with a parent given by ID, name and code, with and without `language`.

## Open decisions

| # | Question | Recommendation |
| --- | --- | --- |
| C-D1 | Authentication for an external API before OIDC in 0.10 | Per-definition consumer API keys in 0.9 (hashed, revocable, scoped to one `apiKey`). OIDC client credentials replace or complement them in 0.10 |
| C-D2 | How strict the breaking-change check is | Removing or retyping an output field, or changing a projection's shape, needs a new `contractVersion`. Adding fields does not |
| C-D3 | Serve several contract versions of one definition at once | Not in 0.9. One installed version per definition; the gateway handles overlap |
| C-D4 | Are the scoring weights part of the contract | Yes. Weights change ranking, and flows depend on ranking, so a weight change needs a new `contractVersion` |
| C-D5 | Route compatibility for existing consumers | The existing gateway maps routes. The engine does not accept free-form route templates in 0.9 |
| C-D6 | Consumer reads in change-set (draft) context | No. Consumers read live or a publication, never unpublished work |
