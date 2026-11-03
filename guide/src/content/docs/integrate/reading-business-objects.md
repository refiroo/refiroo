---
title: Reading business objects
description: Read one declared object or a complete list in the correct workspace and publication.
reader: integrator
---

Read through a [consumer API](/docs/integrate/consumer-apis/) when another system needs the model's declared business representation. Use an object ID already held, or page a list declared by the contract. Follow [Read through a consumer API](/docs/guide/integrate/read-through-a-consumer-api/) for a complete sequence.

## Read one or many

The get-by-ID operation reads a public record ID. A code from another system belongs in [lookup](/docs/integrate/looking-up-and-resolving/). A list returns its declared type in its configured order; an optional parent scope selects descendants at any depth, not just immediate children. Several parent IDs are alternatives.

**Example:** in the reference contract, use [Get by ID](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/objects/{id}) for a known stop identity, or [List all-stops](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/lists/all-stops) for all exposed stops. The contract also declares narrower lists; inspect its document rather than inventing one.

Parameters are declared by the contract. Values within one parameter are alternatives; different parameters combine to narrow the result. They may select a public type, an ancestor, a related record or records inside a projected block. Some projection parameters remove objects left with no matching related records; others only trim that block. On a single read, filtering the object out is `OBJECT_NOT_FOUND`, not an empty object.

## Page and cache

Consumer list pages hold 1–100 objects, default 20. Follow opaque cursors for traversal, or use supported position, end and seek navigation for a jump. Do not combine selectors. Totals are opt-in for lists; XREF lookup always provides them. Keep workspace, filters and selected publication with the checkpoint.

For a fixed extract, choose a publication. Selecting the current one resolves a concrete snapshot that its cursors keep using. A conditional GET lets the server return `304 Not Modified` while the cached answer remains valid. Keep the opaque ETag with the exact request, and retain the cached body on an unchanged response.

## Recover without changing the question

`CONSUMER_API_NOT_FOUND`, `CONTRACT_VERSION_NOT_FOUND`, `LIST_NOT_FOUND` and `OPERATION_NOT_OFFERED` require rediscovering the workspace's contract. `UNKNOWN_PARAMETER` and `PARAMETER_NOT_SUPPORTED` mean correct the request rather than dropping a requested restriction. `INVALID_PAGE_SIZE`, `INVALID_PAGE_PARAMETER` and `CONFLICTING_PAGE_PARAMETERS` require supported paging. `INVALID_CURSOR` requires restarting the intended query.

`WORKSPACE_NOT_FOUND` requires the intended workspace; `FORBIDDEN` requires its consumer grant. A missing or contract-mismatched publication needs an explicit baseline choice. Do not silently retry against live data and present it as a snapshot. Business dates remain a separate filter; see [Business dates](/docs/integrate/business-dates/).

## A complete object read

**Reference-data example:** the requests below use the `stops` declaration explained in [Consumer APIs](/docs/integrate/consumer-apis/#from-a-declaration-to-a-running-api). Replace the host and token with your instance's values. The bodies are composed from the reference snapshot; cursors and ETags shown in angle brackets stand for opaque strings returned by your own instance. They are not tokens to paste into a request.

The declaration's `operations.objects` exposes this request. Notice that the path uses the record UUID, while the returned `code` is a separate business identifier:

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
ETag: "<etag-from-this-response>"
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
  "translations": []
}
```

This is the whole body, not an envelope containing a record. `objectType` uses the declaration's public name. `stopNumber` is an integer; decimal coordinates and height use the API's decimal string encoding, preserving their precision. Nulls mean this object has no applicable value for that output. The declared operator is an object; modes, system codes and translations are arrays. An empty array is a real empty projection, not an omitted part of this example.

## A list page with navigation

`all-stops` declares `of: stop` and `sortBy: stop-number`. This request asks for its first record and an exact total:

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
        "name": "Automobildienst Matterhorn Gotthard Bahn (fo auto)"
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
  "nextCursor": "<next-cursor-from-this-page>",
  "prevCursor": null,
  "anchor": "<anchor-from-this-page>",
  "totalCount": 2443,
  "startIndex": 0
}
```

Follow `nextCursor` with the same list, workspace and filters. URL-encode the opaque cursor as one query value; keep `includeTotal=true` if you still need counts. `prevCursor` goes back; `anchor` reopens this page. At the last page `nextCursor` is null. The 2,443 total describes the reference snapshot, not a fixed product limit. Without totals requested, `totalCount` and `startIndex` are null.

Position navigation is a jump to a numbered row; `from=end` starts at the end; `seek` jumps by a supported sort value. Choose only one navigation method in a request. Use a publication when the extract must stay fixed while pages are read.

## The same list narrowed by a declared parameter

The declaration's `operator` filter reads the `operator` projection, matches its code or name, and requires a match. It does not add a new route. Add it to the list request:

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
      "translations": []
    }
  ],
  "workspace": "graubuenden",
  "publication": null,
  "pageSize": 1,
  "nextCursor": "<next-cursor-for-this-operator-filter>",
  "prevCursor": null,
  "anchor": "<anchor-for-this-operator-filter>",
  "totalCount": 13,
  "startIndex": 0
}
```

The reference snapshot has 13 stops for this operator. Reusing the unfiltered cursor here is invalid: the filter changes the collection. A `municipality` ancestor filter can instead match its declared fields, while the scoped `/lists/stops` route's municipality parent parameter takes municipality IDs. Do not assume a parent parameter accepts every field that an ordinary filter accepts.

## Reuse an unchanged answer

Save the body from the object read and its exact ETag. Repeat the same request with that tag, including its quotes:

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
If-None-Match: "<etag-from-this-response>"
```

```http
HTTP/1.1 304 Not Modified
RDM-Workspace: graubuenden
ETag: "<etag-from-this-response>"
```

There is **no response body**. Keep using the cached body. If the server instead returns 200, replace the cached body and tag together. A live write elsewhere in the workspace can change the tag; it is not a per-object change counter. Adding `publication=<publication-id>` pins the read, and the answer identifies it in `RDM-Publication` and collection `publication` fields.

## A request that the declaration cannot answer

The model offers a list named `all-stops`; it does not offer `no-such-list`:

```http
GET /api/consumer/stops/v1/lists/no-such-list?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

```http
HTTP/1.1 404 Not Found
Content-Type: application/json
RDM-Workspace: graubuenden
```

```json
{
  "error": {
    "code": "LIST_NOT_FOUND",
    "message": "List 'no-such-list' not found"
  }
}
```

Correct the list name using the declaration or rediscover the intended workspace's contract. Do not turn a request error into an empty dataset. Inspect the [reference operations](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/lists/all-stops) for the instance's complete generated schema.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0.*
