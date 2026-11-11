---
title: Reading business objects
description: Read one declared object or a complete list in the correct workspace and publication.
reader: integrator
---

Read through a [consumer API](/docs/integrate/consumer-apis/) when another system needs the model's declared business representation. Use an object ID already held, or page a list declared by the contract. Follow [Read through a consumer API](/docs/guide/integrate/read-through-a-consumer-api/) for a complete sequence.

Values carried by a connection can appear inside a declared related block, with their own types
and nulls. When the block is served, they use the same object shape in single reads, lists, XREF and Resolve; see
[Publish values of the connection](/docs/integrate/consumer-apis/#publish-values-of-the-connection).
To read or maintain the underlying connections through the management API, use
[Relationships and their values](/docs/integrate/relationships-and-their-values/).

## Read one or many

The get-by-ID operation reads a public record ID. A code from another system belongs in [lookup](/docs/integrate/looking-up-and-resolving/). A list returns its declared type in its configured order; an optional parent scope selects descendants at any depth, not just immediate children. Several parent IDs are alternatives.

**Example:** in the reference contract, use [Get by ID](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/objects/{id}) for a known stop identity, or [List all-stops](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/lists/all-stops) for all exposed stops. The contract also declares narrower lists; inspect its document rather than inventing one.

Parameters are declared by the contract. Values within one parameter are alternatives; different parameters combine to narrow the result. They may select a public type, an ancestor, a related record or records inside a projected block. Some projection parameters remove objects left with no matching related records; others only trim that block. On a single read, filtering the object out is `OBJECT_NOT_FOUND`, not an empty object.

## Ask for a related block

The contract can serve related blocks always or only on request. This applies both to the
object's blocks and to blocks nested inside its parent. Get by ID and lists accept `include`;
XREF uses the same choice. The generated contract lists the valid names. Name only blocks
served on request; always-served blocks are already present.

**Illustrative catalogue example:** these requests use the
[catalogue declaration](/docs/integrate/consumer-apis/#parent-values-and-blocks-served-on-request),
not the reference instance. An item has a category with an approval flag. Both the item's
codes and its category's codes are served on request. Start without include:

```http
GET /api/consumer/catalog/v1/objects/11111111-1111-4111-8111-111111111111?workspace=catalogue HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: catalogue
```

```json
{
  "objectType": "Item",
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Notebook",
  "parent": {
    "objectType": "Category",
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "Stationery",
    "isApproved": true
  }
}
```

The parent's `isApproved` output reads the `approved` attribute as a boolean; its name comes
from the declaration, not the attribute key. Its extra attributes keep their declared types; a missing
value or an attribute not bound by this parent's type is null. The two codes blocks are absent,
not empty. To read both, repeat include:

```http
GET /api/consumer/catalog/v1/objects/11111111-1111-4111-8111-111111111111?workspace=catalogue&include=codes&include=parent.codes HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: catalogue
```

```json
{
  "objectType": "Item",
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Notebook",
  "parent": {
    "objectType": "Category",
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "Stationery",
    "isApproved": true,
    "codes": [{"code": "CAT-01"}]
  },
  "codes": [{"code": "ITEM-01"}]
}
```

`include=codes,parent.codes` is equivalent. The parent prefix is used in the request, not
as a key inside the returned parent. It stays `parent.` even if the parent output is renamed.
An included many-valued block with no related records is `[]`; a single-valued block is null.
If the record has no parent, the entire parent output remains null even with an include.

A list can select children by a parent's code and ask to see the matching codes:

```http
GET /api/consumer/catalog/v1/lists/items?workspace=catalogue&categoryCode=CAT-01&include=parent.codes HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

Here `categoryCode` is the declared filter name; `parent.codes` is the block name. The
filter keeps items whose parent has a matching code and trims that parent's codes to
matches. With no matching parent item, a child is removed because the filter declares
`keepOnlyMatching`. Omitting include still selects the same children, but their parent
codes are absent. A filter without keep-only-matching trims the block without removing
children. On Get by ID, a child removed by a filter gives `OBJECT_NOT_FOUND`.

An include name outside the on-request list gives `400 UNKNOWN_INCLUDE`, even if it names
an always-served block. Read `error.details.valid`, correct the name against the contract,
and retry the intended request. Adding a parent field or serving a new block always does
not make it a valid include name. Events and webhook deliveries do not accept includes and
leave on-request blocks out of their full objects.

## Page and cache

Consumer list pages hold 1–100 objects, default 20. Follow opaque cursors for traversal, or use supported position, end and seek navigation for a jump. Do not combine selectors. Totals are opt-in for lists; XREF lookup always provides them. Keep workspace, filters, requested includes and selected publication with the checkpoint.

For a fixed extract, choose a publication. Selecting the current one resolves a concrete snapshot that its cursors keep using. A conditional GET lets the server return `304 Not Modified` while the cached answer remains valid. Keep the opaque ETag with the exact request, and retain the cached body on an unchanged response.

## Recover without changing the question

`CONSUMER_API_NOT_FOUND`, `CONTRACT_VERSION_NOT_FOUND`, `LIST_NOT_FOUND` and `OPERATION_NOT_OFFERED` require rediscovering the workspace's contract. `UNKNOWN_PARAMETER` and `PARAMETER_NOT_SUPPORTED` mean correct the request rather than dropping a requested restriction. `INVALID_PAGE_SIZE`, `INVALID_PAGE_PARAMETER` and `CONFLICTING_PAGE_PARAMETERS` require supported paging. `INVALID_CURSOR` requires restarting the intended query.

`WORKSPACE_NOT_FOUND` requires the intended workspace; `FORBIDDEN` requires its consumer grant. A missing or contract-mismatched publication needs an explicit baseline choice. Do not silently retry against live data and present it as a snapshot. Business dates remain a separate filter; see [Business dates](/docs/integrate/business-dates/).

## A complete object read

**Reference-data example:** the requests below use the `stops` declaration explained in [Consumer APIs](/docs/integrate/consumer-apis/#from-a-declaration-to-a-running-api). Replace the host and token with your instance's values. The response bodies below were read from the reference instance using the 2 November 2026 dataset. Cursors and ETags are the complete values from that read. Obtain fresh values from your own responses; these strings depend on the instance and read context.

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

The reference snapshot has 13 stops for this operator. Reusing the unfiltered cursor here is invalid: the filter changes the collection. A `municipality` ancestor filter can instead match its declared fields, while the scoped `/lists/stops` route's municipality parent parameter takes municipality IDs. Do not assume a parent parameter accepts every field that an ordinary filter accepts.

## Reuse an unchanged answer

Save the body from the earlier object GET and read its `ETag` response header. In the captured response it is `W/"aa0a706f7657c2adb5a7:1"`. Copy the whole header value into `If-None-Match`, including `W/` and both quotes; use the value from your own response rather than a placeholder:

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
If-None-Match: W/"aa0a706f7657c2adb5a7:1"
```

If the saved tag still matches, the conditional response is:


```http
HTTP/1.1 304 Not Modified
RDM-Workspace: graubuenden
ETag: "aa0a706f7657c2adb5a7:1"
```

A matching-tag 304 has **no response body**. Keep using the cached body. If the server instead returns 200, replace the cached body and tag together. A live write elsewhere in the workspace can change the tag; it is not a per-object change counter. Adding `publication=<publication-id>` pins the read, and the answer identifies it in `RDM-Publication` and collection `publication` fields.

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

## Parameter values and response metadata

In query strings, repeat a parameter or separate its values with commas for alternatives. A literal comma inside a value must be percent-encoded as `%2C`. Comparisons are case-insensitive. For a list's special parent parameter, supply public record UUIDs, not names or codes; use a declared ancestor filter on another list to match those values instead. Without that parent parameter the list covers the whole type.

Successful data responses identify the workspace in `RDM-Workspace`. The missing-list error above does not include that header; retain the request context when handling an error. Publication reads also supply `RDM-Publication` and collection `publication`. Lists return `items`, `workspace`, `publication`, `pageSize`, `nextCursor`, `prevCursor`, `anchor`, `totalCount` and `startIndex`; totals and start index are null unless requested with `includeTotal=true`. A get-by-ID response is the bare business object. Unknown, deleted, unexposed or other-workspace records all answer `404 OBJECT_NOT_FOUND`.

The contract's Publications operation lists snapshots newest first, with `id`, `publishedAt`, `status` and `eventSequence`. It supports ordinary paging but no seek. `eventSequence` can be null for an older snapshot; do not assume that is zero. Use a snapshot with a usable sequence when preparing a load-and-follow baseline. `publication=latest` selects the active publication, and fails with `PUBLICATION_NOT_FOUND` if none exists.

ETags have an opaque digest and contract version. Keep the whole value, including quotes, and send it as `If-None-Match` for the same GET. The server compares after validating the read; a cached tag does not bypass access or request validation. Resolve is POST and has no conditional GET behavior.

A parent UUID that is missing or has the wrong parent type gives `404 PARENT_NOT_FOUND`. An unknown public type filter gives `400 UNKNOWN_OBJECT_TYPE`. A value that cannot parse as a typed match field simply does not match that field. A shared-related route does not by itself include the matching record: that needs `itself` in the declaration.

Conditional reads accept `If-None-Match: *`, a list of tags and weak comparison. A 304 has no body and retains the ETag and read-context headers. A live cursor combined with publication selection, a pinned cursor without publication selection, or a different explicit publication ID gives `INVALID_CURSOR`. Keep `publication=latest` on continuation requests to follow the publication first resolved by that cursor.

## Select a publication before a baseline

**Reference-data example:** ask for the workspace's publications through the [Publications operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/publications):

```http
GET /api/consumer/stops/v1/publications?workspace=graubuenden&pageSize=20&includeTotal=true HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

Before that workspace has any publications, the complete successful body has this shape. This is an illustration of the empty state, not a captured answer from the reference instance:

```json
{
  "items": [],
  "workspace": "graubuenden",
  "pageSize": 20,
  "nextCursor": null,
  "prevCursor": null,
  "anchor": null,
  "totalCount": 0,
  "startIndex": 0
}
```

A nonempty answer includes each publication's `id`, `publishedAt`, `eventSequence` and `status`. `active` identifies the snapshot selected by `publication=latest`; `withdrawn` includes superseded or withdrawn snapshots, still readable by explicit ID. The collection has no `publication` field of its own. Without `includeTotal=true`, its total fields are omitted; this operation uses the ordinary collection envelope rather than a data list's nullable totals.

For a baseline, select an ID with a usable sequence, then add `publication=<id>` to the declared list or object request. A publication can still fail the contract-compatibility check on that read; its presence in the catalogue does not establish compatibility. If the catalogue is empty, use live reads for current answers or arrange a publication for a fixed extract. Do not invent a publication ID or treat null `eventSequence` as zero. Follow [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/#use-a-consumer-contract-instead) when continuing from its sequence.

## Reading through an earlier contract

A retained earlier contract reads current data using that version’s fields, names and
related blocks. Keep its version in object, list and lookup addresses, and keep checkpoints
with that version and workspace. It is not a snapshot of the data from when the contract
was superseded. Use a compatible publication for fixed values.

The workspace must currently serve the requested version, even for a publication read.
The publication must also contain that version’s definition; keeping v1 live does not
make a publication containing only v2 compatible with v1. If the administrator stops v1,
its reads return `404 CONTRACT_VERSION_NOT_FOUND`; `details.servedContractVersions` lists
available numbers. Rediscover and inspect the intended replacement rather than changing
the URL and reusing an unreviewed parser. See [Earlier contract versions](/docs/integrate/consumer-apis/#earlier-contract-versions)
for deprecation headers, discovery and an example response.
