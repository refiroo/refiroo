---
title: Looking up and resolving
description: Match identifiers to business objects and translate representations without guessing ambiguity.
reader: integrator
---

Use lookup when you have a code, name or related identifier rather than refiroo's record ID. The consumer contract decides which fields match and their weights. Use batch resolution when a file contains many such questions. Follow [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/) for the sequence.

**Example:** the reference contract's [XREF lookup](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/xref) can find a stop through its own identifiers, translated name or a related system code. Its [Batch resolve operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/POST/api/consumer/stops/v1/resolve) applies the same contract to many inputs. These matching choices belong to this model.

## How matches are chosen

Own-field exact weights that apply add together. Contains weights count only when no own exact weight applied. A related record can promote its weight to exposed records using the first matching rule in declaration order. The final score is the higher of the object's own score and its best promoted score. Type preferences can decide which related owners receive promoted scores.

For several terms, an object's best term score wins. Results order by descending score, then public type name, name and ID. Parameters narrow the matching set without rescaling scores. A projection parameter can additionally restrict which related records contribute scores when the definition says so. Knowing the source system can therefore remove an ambiguity without changing the weighting rules.

Choose a page of results when a person or later process needs alternatives. Choose exactly one when the integration needs a single best answer. Exactly one means an untied top result; lower-scoring candidates may still exist. `NO_MATCH` means none, and `AMBIGUOUS_MATCH` means the top score is tied. Do not pick the first tied result yourself.

Partial matching needs at least three characters. Shorter inputs match whole values only. At most 100 terms are accepted. More than 10,000 matches before parameter narrowing is `QUERY_TOO_BROAD`; use more specific terms, not merely more parameters. An exactly-one request settled safely by exact matches can avoid that contains scan. `QUERY_REQUIRED`, `TOO_MANY_TERMS` and `INVALID_EXPECT` require correcting the question. XREF pages always include totals; they do not support seek.

## Resolve many questions

Batch resolve is a read. Each item asks by query or by ID, exactly one of them. Shared parameters can be overridden per item; JSON list values keep commas inside a value rather than splitting them. The response stays in input order, distinguishing found, not found, ambiguous and rejected items. A processed HTTP request does not mean every item resolved.

The default maximum is 1,000 items (`CONSUMER_RESOLVE_MAX_ITEMS`), reported by the [capabilities operation](/docs/api/?api=management#tag/model). `BATCH_TOO_LARGE` requires smaller batches. Malformed bodies and unknown defaults refuse the request as a whole; an item-specific failure is reported with that item's outcome. `QUERY_OR_ID_REQUIRED` requires one input form. Keep a source-row reference so a refusal can be returned to the right row.

## Translate to another representation

A crosswalk asks for a target through a parameter declared as target-capable. Source matching and scoring stay unchanged; the target selects the corresponding related representation. It can translate codes between systems or names between languages only where the model declares that relationship.

One read names one target parameter (`MULTIPLE_TARGETS` otherwise). The target's selection replaces that parameter's ordinary projection restriction; other restrictions on the same projection still apply. An unknown or non-target-capable name is `UNKNOWN_PARAMETER`. Several values for the one target parameter are alternatives. Targets do not affect score, order, totals or ties and are not bound into the paging cursor. A page keeps the related block’s declared shape in `target`; a single-object answer requires exactly one related target. `AMBIGUOUS_TARGET` details include the count and up to ten targets, together with the source object ID, public type and parameter.

For a single object, the source is chosen first, then exactly one target must exist. `TARGET_NOT_FOUND` and `AMBIGUOUS_TARGET` describe separate problems from source ambiguity. Pages can show no target or several without refusing the whole page. Batch items use the same single-object rule. Publication-pinned lookup and resolution use the fixed snapshot, including its matching and targets.

## A lookup with a score

**Reference-data example:** the `stops` declaration includes these XREF rules. This excerpt shows selected rules; the complete declaration also matches IDs, other codes and translated names:

```json
{
  "xref": {
    "matchOn": [
      {"field": "stop-number", "exact": 900},
      {"field": "name", "exact": 200, "contains": 30}
    ],
    "alsoMatchThrough": [
      {
        "related": "systemCodes",
        "firstOf": [
          {"field": "external-id", "exact": 90},
          {"field": "name", "contains": 10}
        ]
      }
    ]
  }
}
```

The number `8505173` matches Tschamut-Selva's own stop number exactly, so its score is 900. A match through its Wikidata system code would use 90 instead. These weights come from this declaration; they are not universal thresholds or confidence percentages.

```http
GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&pageSize=20 HTTP/1.1
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
  "results": [
    {
      "objectType": "Stop",
      "id": "8d90eede-23cf-47c1-8dac-cb37956f5fd5",
      "code": "ch:1:sloid:5173",
      "name": "Tschamut-Selva",
      "validFrom": "2021-04-01",
      "validTo": null,
      "stopNumber": 8505173,
      "abbreviation": "TSSE",
      "fsoNumber": null,
      "latitude": "46.65674442039232",
      "longitude": "8.709084193690385",
      "height": "1701.3",
      "sboid": null,
      "parent": {
        "objectType": "Municipality",
        "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc",
        "code": null,
        "name": "Tujetsch"
      },
      "path": "Graubünden/Surselva/Tujetsch",
      "operator": {
        "id": "f94ef862-2a95-4675-9e31-6b1d0a03317f",
        "code": "MGB-fo",
        "name": "Matterhorn Gotthard Bahn (fo)"
      },
      "modes": [
        {
          "id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9",
          "code": "TRAIN",
          "name": "Train"
        }
      ],
      "systemCodes": [
        {
          "system": "Wikidata: stations",
          "systemKey": "wikidata-stations",
          "code": "Q33467326",
          "name": "Q33467326 Tschamut-Selva"
        }
      ],
      "translations": [],
      "matchScore": 900
    }
  ],
  "query": [
    "8505173"
  ],
  "workspace": "graubuenden",
  "publication": null,
  "pageSize": 20,
  "nextCursor": null,
  "prevCursor": null,
  "anchor": "<anchor-for-this-lookup>",
  "totalCount": 1,
  "startIndex": 0
}
```

The complete shared object is returned with `matchScore` added. XREF pages use `results`, not a list's `items`. Here there is one candidate and no next page. If you add `expect=one`, the response is this one scored object directly, without the page envelope. With no candidate it is `404 NO_MATCH`; with tied top candidates it is `409 AMBIGUOUS_MATCH`. Lower-scoring alternatives do not make an untied top answer ambiguous.

Name search is case-insensitive. A contains match begins at three characters. Multiple terms use repeated `query` values or the supported comma syntax; percent-encode a literal comma inside a URL value. JSON resolution items can instead use arrays without URL splitting. Keep terms and filters unchanged when following a lookup cursor.

## A crosswalk from a stop number to another system's code

The reference declaration makes `system` target-capable:

```json
{
  "system": {
    "onRelated": "systemCodes",
    "matchOn": ["ancestor:system.system-key", "ancestor:system.name"],
    "keepOnlyMatching": true,
    "scoreOnlyMatching": true,
    "crosswalk": true
  }
}
```

As an ordinary filter, `system=wikidata-stations` narrows the objects and the related code records contributing scores. As a target, `to.system=wikidata-stations` selects the returned code representation while leaving source matching unchanged:

```http
GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&expect=one&to.system=wikidata-stations HTTP/1.1
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
  "id": "8d90eede-23cf-47c1-8dac-cb37956f5fd5",
  "code": "ch:1:sloid:5173",
  "name": "Tschamut-Selva",
  "validFrom": "2021-04-01",
  "validTo": null,
  "stopNumber": 8505173,
  "abbreviation": "TSSE",
  "fsoNumber": null,
  "latitude": "46.65674442039232",
  "longitude": "8.709084193690385",
  "height": "1701.3",
  "sboid": null,
  "parent": {
    "objectType": "Municipality",
    "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc",
    "code": null,
    "name": "Tujetsch"
  },
  "path": "Graubünden/Surselva/Tujetsch",
  "operator": {
    "id": "f94ef862-2a95-4675-9e31-6b1d0a03317f",
    "code": "MGB-fo",
    "name": "Matterhorn Gotthard Bahn (fo)"
  },
  "modes": [
    {
      "id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9",
      "code": "TRAIN",
      "name": "Train"
    }
  ],
  "systemCodes": [
    {
      "system": "Wikidata: stations",
      "systemKey": "wikidata-stations",
      "code": "Q33467326",
      "name": "Q33467326 Tschamut-Selva"
    }
  ],
  "translations": [],
  "target": {
    "system": "Wikidata: stations",
    "systemKey": "wikidata-stations",
    "code": "Q33467326",
    "name": "Q33467326 Tschamut-Selva"
  },
  "matchScore": 900
}
```

`target` is the one selected system-code object. It is distinct from the source stop's identity and score. A page can carry a target array in the projection's declared shape; the single-object response requires exactly one target and returns that target as an object. The reference contract does not declare a target filter for translated names; that example capability needs a declaration that provides one.

## Resolve a small file in one request

`operations.resolve` enables this read by POST. Shared defaults are declared parameters; each item can override them. The workspace belongs on the URL. This complete request asks about two source rows and keeps their references:

```http
POST /api/consumer/stops/v1/resolve?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
Content-Type: application/json

{
  "defaults": {
    "mode": "TRAIN"
  },
  "items": [
    {
      "ref": "row-1",
      "query": "8505173"
    },
    {
      "ref": "row-2",
      "query": "T-9999"
    }
  ]
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

```json
{
  "items": [
    {
      "index": 0,
      "ref": "row-1",
      "status": "found",
      "object": {
        "objectType": "Stop",
        "id": "8d90eede-23cf-47c1-8dac-cb37956f5fd5",
        "code": "ch:1:sloid:5173",
        "name": "Tschamut-Selva",
        "validFrom": "2021-04-01",
        "validTo": null,
        "stopNumber": 8505173,
        "abbreviation": "TSSE",
        "fsoNumber": null,
        "latitude": "46.65674442039232",
        "longitude": "8.709084193690385",
        "height": "1701.3",
        "sboid": null,
        "parent": {
          "objectType": "Municipality",
          "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc",
          "code": null,
          "name": "Tujetsch"
        },
        "path": "Graubünden/Surselva/Tujetsch",
        "operator": {
          "id": "f94ef862-2a95-4675-9e31-6b1d0a03317f",
          "code": "MGB-fo",
          "name": "Matterhorn Gotthard Bahn (fo)"
        },
        "modes": [
          {
            "id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9",
            "code": "TRAIN",
            "name": "Train"
          }
        ],
        "systemCodes": [
          {
            "system": "Wikidata: stations",
            "systemKey": "wikidata-stations",
            "code": "Q33467326",
            "name": "Q33467326 Tschamut-Selva"
          }
        ],
        "translations": [],
        "matchScore": 900
      }
    },
    {
      "index": 1,
      "ref": "row-2",
      "status": "not_found",
      "error": {
        "code": "NO_MATCH",
        "message": "No object matches the query"
      }
    }
  ],
  "workspace": "graubuenden",
  "publication": null,
  "counts": {
    "found": 1,
    "notFound": 1,
    "ambiguous": 0,
    "rejected": 0
  }
}
```

`T-9999` is the reference data's deliberately unmapped **fictional** Regional ticketing code. The HTTP request succeeded, but the second source row has no answer. Keep its `not_found` outcome rather than replacing it with the first result. A malformed item is `rejected`; a tied best match is `ambiguous`. The response keeps input order and echoes each `ref`.

An item using `id` reads the known UUID directly and does not add a query score. Use one of `query` and `id` per item. For a whole file, follow [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/). The instance's [Resolve reference](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/POST/api/consumer/stops/v1/resolve) remains the generated contract pointer.

These bodies use production-composed object values and the envelopes checked by the consumer code and journey assertions. The opaque anchor is illustrative, not a live resume token.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Regional ticketing and its codes are fictional.*

An ambiguous lookup’s details include the tied count and up to ten candidates with ID, public type, name and score. Paging parameters are unsupported with `expect=one`. XREF pages support cursor traversal, position and end selection, but neither seek nor `includeTotal`: totals are always returned. Empty query terms are ignored.

Resolve’s optional `ref` is 1–200 characters. Outcome errors preserve the single-read code and add a JSON pointer into the item or defaults. Over-limit errors name the setting, maximum and submitted item count. Put `workspace`, `publication` and `asOf` on the request URL, never in `defaults` or items; definition filters and crosswalk choices belong in the body.
