---
title: The consumer API example
description: See how a model turns reference data into a contract for other systems, with complete stop requests and answers.
reader: evaluator
---

A consumer API lets another system read the business objects a model chooses to share. It brings
fields and related records into one answer, so a consumer does not have to assemble the record
structure itself. The contract, including its names, lists and events, belongs to the model.

Both examples use [the same object and operation patterns](/docs/integrate/consumer-apis/#learn-one-way-to-read-business-objects), so consuming systems can reuse how they read data while each model chooses the contract's content.

The optional [starter model](/docs/examples/the-starter-model/) includes one such contract.
The [reference-data model](/docs/examples/the-example-data/) uses the same capability for transport
stops. Neither contract is built into refiroo. This page first shows what the starter offers, then
uses the populated reference example to show what another system receives.

## What the starter offers

**RDM API**, version 1, exposes domains, codelists and master values. A master value has the public
type name **CodelistValue**. Its answer includes its code, name, active status, validity dates,
description, master identifier, value name, sort order, parent and ancestor path, plus related
system representations and translations.

These are selected parts of the starter declaration; the object and matching definitions are
omitted here. It is an explanatory excerpt, not a complete declaration to install:

```json
{
  "key": "rdm",
  "name": "RDM API",
  "contractVersion": 1,
  "exposes": [
    "domain",
    "codelist",
    "master-value"
  ],
  "publicNames": {
    "master-value": "CodelistValue"
  }
}
```

The declaration also includes these lists and event under its operations:

```json
{
  "lists": {
    "domains": {
      "of": "domain"
    },
    "codelists": {
      "of": "codelist",
      "within": {
        "filter": "domain"
      }
    },
    "values": {
      "of": "master-value",
      "within": {
        "filter": "codelist"
      },
      "sortBy": "sort-order"
    }
  },
  "events": {
    "custom": [
      {
        "key": "values-changed",
        "objectTypes": [
          "master-value"
        ],
        "changes": [
          "created",
          "updated",
          "deleted"
        ],
        "watch": {
          "fields": [
            "code",
            "name",
            "isActive",
            "validFrom",
            "validTo"
          ]
        }
      }
    ]
  }
}
```

The domain list reads domains; the codelist list can narrow to a domain; the values list can narrow
to a codelist and orders by sort order. Lookup finds records through their identifiers, codes, names,
related system values or translated names. Batch resolution applies those questions to many inputs.

The **values-changed** event announces creations and deletions of master values and updates affecting
the watched public fields: code, name, active status and validity dates. It does not promise a
notification for every field or related translation edit. Unpublished change-set edits do not send
consumer events.

A fresh installation can therefore show a contract even before records have been added. The
empty starter workspace has no populated answer to demonstrate; the examples below use real values
from the guide's transport snapshot instead.

## The populated reference example

**Stops API**, version 1, exposes stops, municipalities, operators and modes. A stop answer brings
together its municipality, operator, modes, system codes and any related name translations. A related
block can be empty: this model's Names application supplies municipality and operator names, so the
stop below has no translations of its own.

For browser readers, [Consumer APIs in the model](/docs/model/consumer-apis/) explains where to
inspect the contract. For integration developers, the remainder of this example shows the declaration
and complete requests and answers. Start with [Consumer APIs](/docs/integrate/consumer-apis/) for
access, versioning and consistency rules.

### How the declaration becomes the API

These selected parts come from the reference model. Other exposed fields, lists, filters and
related blocks are omitted from this excerpt; it is not a complete model to install:

```json
{
  "key": "stops",
  "name": "Stops API",
  "contractVersion": 1,
  "exposes": [
    "stop",
    "municipality",
    "operator",
    "mode"
  ],
  "publicNames": {
    "stop": "Stop",
    "municipality": "Municipality",
    "operator": "Operator",
    "mode": "Mode"
  },
  "object": {
    "fields": {
      "id": {
        "role": "id"
      },
      "code": {
        "role": "code",
        "from": [
          "sloid",
          "operator-code",
          "mode-code"
        ]
      },
      "name": {
        "role": "name",
        "from": "name"
      },
      "validFrom": {
        "role": "validFrom",
        "from": "valid-from"
      },
      "validTo": {
        "role": "validTo",
        "from": "valid-to"
      },
      "stopNumber": "stop-number",
      "abbreviation": "abbreviation",
      "fsoNumber": "fso-number",
      "latitude": "latitude",
      "longitude": "longitude",
      "height": "height",
      "sboid": "operator-sboid"
    },
    "parent": [
      "objectType",
      "id",
      "code",
      "name"
    ],
    "path": true,
    "related": {
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
  },
  "operations": {
    "objects": {},
    "lists": {
      "all-stops": {
        "of": "stop",
        "sortBy": "stop-number"
      }
    },
    "events": {
      "custom": [
        {
          "key": "stops-changed",
          "objectTypes": [
            "stop"
          ],
          "changes": [
            "created",
            "updated",
            "deleted"
          ],
          "watch": {
            "fields": [
              "code",
              "name",
              "validFrom",
              "validTo"
            ]
          }
        }
      ]
    }
  },
  "filters": {
    "operator": {
      "onRelated": "operator",
      "matchOn": [
        "operator-code",
        "name"
      ],
      "keepOnlyMatching": true
    }
  }
}
```

| Declaration | What another system sees |
| --- | --- |
| `key` and `contractVersion` | The base address `/api/consumer/stops/v1`. |
| `exposes` and `publicNames` | Public types `Stop`, `Municipality`, `Operator` and `Mode`. |
| `object.fields` | Output names such as `stopNumber`, sourced from the model's fields. `code` takes the first nonempty source in its list. A missing value takes a declared default, otherwise null. |
| `parent` and `path` | The immediate parent and its ancestor path, without the stop itself in that path. |
| `related.operator` | An operator object, or null; the other declared blocks include arrays of modes, codes and translations. |
| `operations.objects` | A read by public record ID at `/objects/{id}`. |
| `operations.lists.all-stops` | A paged stop list at `/lists/all-stops`, ordered by stop number. |
| `filters.operator` | An `operator` parameter matching operator code or name and keeping only stops with a match. |
| The declared custom event | An event named `stops-changed`, watching code, name and validity dates. |

The complete declaration also enables XREF lookup and batch resolution. Its exact stop-number match
has weight 900; a name match has weight 200 for the whole name or 30 for part of it. Those are this
model's choices, not confidence percentages. See the [matching declaration and scoring example](/docs/integrate/looking-up-and-resolving/#a-lookup-with-a-score).

### Read a stop by its ID

Use a consumer token belonging to a client granted this API in this workspace. A person's role does
not provide that grant. See [Clients](/docs/administer/clients/) and
[Signing in and tokens](/docs/integrate/signing-in-and-tokens/).

**Reference-data example:** replace the host and token with your instance's values. The bodies below
were read from the reference instance using the 2 November 2026 dataset. ETags, cursors and event
identifiers are the values from that read and depend on the instance. Obtain fresh values from your own responses.

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
ETag: W/"aa0a706f7657c2adb5a7:1"
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
    "name": "Matterhorn Gotthard Bahn (fo)",
    "localName": null,
    "isPrimary": null
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
  "translations": []
}
```

The UUID in the path is the record's stable identity. Its code and stop number are separate business
identifiers. The stop number is an integer; decimal coordinates and height use decimal strings to
retain precision. Null fields have no applicable value here. The parent is one object, modes and
system codes are arrays, and an empty translations array is a complete answer.

### Read a list, then narrow it

This first-page request asks for one stop and an exact total:

```http
GET /api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&pageSize=1&includeTotal=true HTTP/1.1
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
  "items": [
    {
      "objectType": "Stop",
      "id": "6583e8c9-582c-4bc5-b113-dbdbcc31a44a",
      "code": "ch:1:sloid:4",
      "name": "Selva, via Alpsu spv.",
      "validFrom": "2022-11-14",
      "validTo": null,
      "stopNumber": 8500004,
      "abbreviation": "SAXX",
      "fsoNumber": null,
      "latitude": "46.662107304536484",
      "longitude": "8.723794590415595",
      "height": "1553.9",
      "sboid": null,
      "parent": {
        "objectType": "Municipality",
        "id": "06073bf3-cb29-475e-a87a-8fc6dbb8b8cc",
        "code": null,
        "name": "Tujetsch"
      },
      "path": "Graubünden/Surselva/Tujetsch",
      "operator": {
        "id": "69907d18-f444-400a-b8a2-359bfbd405fc",
        "code": "MGB/Autofo",
        "name": "Automobildienst Matterhorn Gotthard Bahn (fo auto)",
        "localName": null,
        "isPrimary": null
      },
      "modes": [
        {
          "id": "ef9e4eea-74a4-4380-a426-b9faae4a298f",
          "code": "BUS",
          "name": "Bus"
        }
      ],
      "systemCodes": [],
      "translations": []
    }
  ],
  "workspace": "graubuenden",
  "publication": null,
  "pageSize": 1,
  "nextCursor": "eyJmaWx0ZXJzIjoiYjIzZTk0OTg0NzVlMDVmYWZmNTc1MGYzOTBkNDdlOWE3ZmJmZDQ5NWIwZWViZTc4NTY5ZDk4ZjE3ZmFkM2M1MiIsInBvc2l0aW9uIjpbIjAiLCI4NTAwMDA0IiwiU2VsdmEsIHZpYSBBbHBzdSBzcHYuIiwiNjU4M2U4YzktNTgyYy00YmM1LWIxMTMtZGJkYmNjMzFhNDRhIl0sInNjb3BlIjoiY29uc3VtZXItbGlzdDpzdG9wczphbGwtc3RvcHMiLCJzb3J0IjpbInN0b3AtbnVtYmVyOm51bGwiLCJzdG9wLW51bWJlciIsIm5hbWUiLCJpZCJdLCJ2ZXJzaW9uIjoxfQ.Xq2rRTwSbhFk87_MbE_pH5rw0C6dLWShygnYcAxwlxs",
  "prevCursor": null,
  "anchor": "eyJkaXJlY3Rpb24iOiJmcm9tIiwiZmlsdGVycyI6ImIyM2U5NDk4NDc1ZTA1ZmFmZjU3NTBmMzkwZDQ3ZTlhN2ZiZmQ0OTViMGVlYmU3ODU2OWQ5OGYxN2ZhZDNjNTIiLCJwb3NpdGlvbiI6WyIwIiwiODUwMDAwNCIsIlNlbHZhLCB2aWEgQWxwc3Ugc3B2LiIsIjY1ODNlOGM5LTU4MmMtNGJjNS1iMTEzLWRiZGJjYzMxYTQ0YSJdLCJzY29wZSI6ImNvbnN1bWVyLWxpc3Q6c3RvcHM6YWxsLXN0b3BzIiwic29ydCI6WyJzdG9wLW51bWJlcjpudWxsIiwic3RvcC1udW1iZXIiLCJuYW1lIiwiaWQiXSwidmVyc2lvbiI6MX0.JvqCknm2cJdxKet5Qn-csSed-VGI0kJdJgpKM6_DYSI",
  "totalCount": 2443,
  "startIndex": 0
}
```

The snapshot holds 2,443 stops; that is not a product limit. List pages hold 1–100 objects, default
20. Follow `nextCursor` with the same workspace, list and filters, URL-encoding the cursor as one
value. `prevCursor` goes back and `anchor` reopens the page. Counts are null unless requested.
For an extract that must stay fixed across pages, select a [publication](/docs/integrate/reading-business-objects/#page-and-cache).

Now add the declared operator parameter:

```http
GET /api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&operator=MGB-fo&pageSize=1&includeTotal=true HTTP/1.1
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
  "items": [
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
        "name": "Matterhorn Gotthard Bahn (fo)",
        "localName": null,
        "isPrimary": null
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
      "translations": []
    }
  ],
  "workspace": "graubuenden",
  "publication": null,
  "pageSize": 1,
  "nextCursor": "eyJmaWx0ZXJzIjoiNTRhMTExMzQxODIzZjk3NWYzNjkyNWMzZTEwMTk2ZDNiNjg4ZWY2OGQ1YWVkZjAyNGMxZGE1YTBhNmU5NjFmOCIsInBvc2l0aW9uIjpbIjAiLCI4NTA1MTczIiwiVHNjaGFtdXQtU2VsdmEiLCI4ZDkwZWVkZS0yM2NmLTQ3YzEtOGRhYy1jYjM3OTU2ZjVmZDUiXSwic2NvcGUiOiJjb25zdW1lci1saXN0OnN0b3BzOmFsbC1zdG9wcyIsInNvcnQiOlsic3RvcC1udW1iZXI6bnVsbCIsInN0b3AtbnVtYmVyIiwibmFtZSIsImlkIl0sInZlcnNpb24iOjF9.1v9cIpsLdk52jHId-gxF6o2ZOCtL2rUovcSK_qeVVxo",
  "prevCursor": null,
  "anchor": "eyJkaXJlY3Rpb24iOiJmcm9tIiwiZmlsdGVycyI6IjU0YTExMTM0MTgyM2Y5NzVmMzY5MjVjM2UxMDE5NmQzYjY4OGVmNjhkNWFlZGYwMjRjMWRhNWEwYTZlOTYxZjgiLCJwb3NpdGlvbiI6WyIwIiwiODUwNTE3MyIsIlRzY2hhbXV0LVNlbHZhIiwiOGQ5MGVlZGUtMjNjZi00N2MxLThkYWMtY2IzNzk1NmY1ZmQ1Il0sInNjb3BlIjoiY29uc3VtZXItbGlzdDpzdG9wczphbGwtc3RvcHMiLCJzb3J0IjpbInN0b3AtbnVtYmVyOm51bGwiLCJzdG9wLW51bWJlciIsIm5hbWUiLCJpZCJdLCJ2ZXJzaW9uIjoxfQ.8FyXbvb1X-LjSKkbpn39MjxS1xGXaCaxFkbpxrQDCNc",
  "totalCount": 13,
  "startIndex": 0
}
```

There are 13 reference stops for this operator. The parameter narrows the existing list; it does
not create another route. Use the cursor from this filtered answer, rather than the unfiltered one.

### Look up a stop number

XREF adds a score to the same business object. Asking for exactly one answer returns the untied top
match directly. A tied top score is an ambiguity to resolve, rather than permission to choose the
first record.

```http
GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&expect=one HTTP/1.1
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
    "name": "Matterhorn Gotthard Bahn (fo)",
    "localName": null,
    "isPrimary": null
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
```

Without `expect=one`, XREF returns a page with `results`, `query`, workspace, publication and paging
fields. See the [complete scored page](/docs/integrate/looking-up-and-resolving/#a-lookup-with-a-score)
and [system-code crosswalk](/docs/integrate/looking-up-and-resolving/#a-crosswalk-from-a-stop-number-to-another-systems-code).

### Resolve several inputs

Batch resolution is a read expressed as POST. Each item asks by query or by ID; the result keeps
input order and the supplied row reference. This example's second code is the deliberately unmapped
**fictional** Regional ticketing code:

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
          "name": "Matterhorn Gotthard Bahn (fo)",
          "localName": null,
          "isPrimary": null
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

HTTP success does not mean every input resolved. Keep each outcome, including not found, ambiguous
and rejected. For a file, follow [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/).

### Reuse an unchanged answer

Read the `ETag` header from the earlier object GET and save it with that body. The captured header is
`"aa0a706f7657c2adb5a7:1"`. Repeat the identical request with the complete value, including `W/`
and both quotes. Use your own response header rather than a literal placeholder:

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
If-None-Match: "aa0a706f7657c2adb5a7:1"
```

If the saved tag still matches, the conditional response is:

```http
HTTP/1.1 304 Not Modified
RDM-Workspace: graubuenden
ETag: "aa0a706f7657c2adb5a7:1"
```

A matching-tag 304 has no response body; retain the cached answer. A 200 response replaces the body and tag
together. A live tag can change after another workspace write, even if this stop looks the same.

### Correct a request error

The declaration offers `all-stops`, not `no-such-list`:

```http
GET /api/consumer/stops/v1/lists/no-such-list?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```
```http
HTTP/1.1 404 Not Found
Content-Type: application/json
```

```json
{
  "error": {
    "code": "LIST_NOT_FOUND",
    "message": "List 'no-such-list' not found"
  }
}
```

Correct the name from the workspace's contract. An error is not an empty collection.

### Follow the declared event

The declaration above enables `stops-changed`. The response below reports the creation of
Selva, via Alpsu spv. by an import job at position 207. Although the request starts after 63,
the first matching event is later. The captured head is 8986 and `caughtUp` is false;
continue with the returned cursor to read the remaining events.

```http
GET /api/consumer/stops/v1/events?workspace=graubuenden&after=63&event=stops-changed&pageSize=1&payload=identity HTTP/1.1
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
  "items": [
    {
      "eventId": "a141f374-b312-9649-bd6f-b878fd2aacf5",
      "position": 207,
      "occurredAt": "2026-11-03T21:29:54.748509+00:00",
      "event": "stops-changed",
      "change": "created",
      "contractVersion": 1,
      "objectType": "Stop",
      "id": "6583e8c9-582c-4bc5-b113-dbdbcc31a44a",
      "code": "ch:1:sloid:4",
      "name": "Selva, via Alpsu spv.",
      "changed": [],
      "cause": {
        "kind": "job",
        "id": "b2984b17-a315-4fba-a2d5-e08432e86cfd"
      }
    }
  ],
  "workspace": "graubuenden",
  "pageSize": 1,
  "cursor": "eyJmaWx0ZXJzIjoiYWVhNmJjYzI4YmQxNTAzZWMwYWNiMjQ2NjVkNzUxMzFjNjhjYTJmMjA4ZTEwMTM2NzQ4MmNmOWUxODY5MTcwYyIsInBvc2l0aW9uIjpbIjIwNyIsIjEiXSwic2NvcGUiOiJjb25zdW1lci1ldmVudHM6c3RvcHM6Z3JhdWJ1ZW5kZW4iLCJzb3J0IjpbInBvc2l0aW9uIiwib3JkaW5hbCJdLCJ2ZXJzaW9uIjoxfQ.jE5ueunEtvaETHuI__-kBACi5xvxqymz6-tzSB9_x-w",
  "caughtUp": false,
  "headPosition": 8986,
  "earliestPosition": 1
}
```

Save the lasting cursor after processing the page; it can resume within a position containing several
events. With `payload=full`, the event also includes the object read now and `stateAt`, the position
at which it was composed. It is not a historical copy of the object at the event's time.
See the [complete full event](/docs/integrate/consumer-events-and-webhooks/#a-declaration-and-the-event-it-exposes).

### Receive the event at a webhook

An administrator can separately create a subscription to this event. The model declaration does not
register a receiver. Delivery needs the deployment's webhook capability and a configured subscription;
see [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/).

For identity payloads in RDM JSON format, one event per request, the receiver gets the following
illustrative body for a separate name-update event; it is not a delivery captured from the feed above.
It uses the public demonstration secret `guide-example-only`. The IDs, timestamp
and signature are example values. The compact body has no trailing newline:

```http
POST /refiroo-events HTTP/1.1
Host: receiver.example
Content-Type: application/json
User-Agent: rdm-engine
RDM-Delivery-Id: 85c0fa4d-c85c-4e2d-b788-24c8f3800fd8
RDM-Timestamp: 1793606400
RDM-Signature: sha256=fd32dc6d2633f1ac0cad65c9fbe0d61353a581e66655509d391d9708d3fe15a6
Content-Length: 516

{"deliveryId":"85c0fa4d-c85c-4e2d-b788-24c8f3800fd8","subscriptionId":"a7447804-c8c0-4e13-9a7f-117e7ec6ba15","consumerApi":"stops","contractVersion":1,"workspaceKey":"graubuenden","events":[{"eventId":"8b6b294b-ff1a-4bb8-898c-a2e412e64f71","position":64,"occurredAt":"2026-11-02T08:00:00+00:00","event":"stops-changed","change":"updated","contractVersion":1,"objectType":"Stop","id":"8d90eede-23cf-47c1-8dac-cb37956f5fd5","code":"ch:1:sloid:5173","name":"Tschamut-Selva","changed":["name"],"cause":{"kind":"user"}}]}
```

Verify `RDM-Signature` as HMAC-SHA256 of the timestamp text, a dot and the original body bytes,
using the secret exactly as issued. Compare in constant time, reject stale timestamps under your
receiver's replay policy, then deduplicate using `eventId`. Store or queue accepted work durably before
acknowledging with a 2xx. Do not parse and reserialize the JSON before verification.
The [verification example](/docs/integrate/consumer-events-and-webhooks/#verify-the-bytes-before-decoding-json)
shows the code, including key rotation overlap. The dated sample must fail a live receiver's freshness
check; use its timestamp only when reproducing the example.

## Find the contract on your instance

In the browser, **Settings › Integration › Consumer APIs** lists the selected workspace's contracts
and their documents. For the reference example, the authenticated index is
`/api/consumer?workspace=graubuenden`; its entry points to
`/api/consumer/stops/v1/openapi.json?workspace=graubuenden`.
The starter instead uses the key `rdm` in a workspace running that model. Always inspect the intended
workspace: installing a release alone does not activate it there.

The instance's [interactive API reference](/docs/api/) describes its actual declarations.
For access and limits, read [Consumer APIs](/docs/integrate/consumer-apis/); for changing the
contract, read [Model consumer APIs](/docs/model/consumer-apis/). A client needs a consumer grant in
the chosen workspace. This contract is read-only; changes use the
[management integration](/docs/integrate/overview/).

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB,
snapshot 2026-11-02. Wikidata, CC0. Regional ticketing and its codes are fictional.*
