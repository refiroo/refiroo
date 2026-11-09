---
title: Read through a consumer API
description: Discover a contract, choose its data context and read business objects consistently.
reader: integrator
---

Use this sequence when a downstream system needs a stable business representation. Read [Consumer APIs](/docs/integrate/consumer-apis/) for the contract and permission model.

1. Have an administrator [grant the client](/docs/administer/clients/) the intended consumer API in the workspace. [Get a consumer token](/docs/guide/integrate/get-a-token/); a management role alone does not open these reads.
2. Read the [consumer API index](/docs/api/?api=management#tag/consumer). For the reference example, request `GET /api/consumer?workspace=graubuenden` and select `stops`, version 1. Its document is `/api/consumer/stops/v1/openapi.json?workspace=graubuenden`. Read [how the declaration becomes routes and outputs](/docs/integrate/consumer-apis/#from-a-declaration-to-a-running-api), then use the instance's document to confirm its shape. An earlier served version has its own entry marked `deprecated: true`, with `sunset` when announced. Select the version your client implements; deprecated does not mean unavailable.
3. Choose live data for current answers, or a publication for a fixed extract. Use the contract's Publications operation to select an available snapshot. Keep its identity; a business date, if supported, filters that snapshot rather than choosing another one.
4. Read a known object ID, or start a declared list. Check that the answer identifies the intended workspace and publication. Apply only documented narrowing parameters.
5. Process each page and follow its next cursor with the same request scope. Persist completed work before the cursor. A cursor started on the current publication continues on that snapshot if a new one is published.
6. For repeated GET reads, retain the ETag and cached body and send a conditional request. On `304`, keep that body. Batch resolution has no such GET cache response.

**Example:** the reference `stops` API offers [List all-stops](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/lists/all-stops) and [Get by ID](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/objects/{id}). Choose the workspace that declares that contract; other models need not offer it.

If an object is not found, check whether its parameters filtered it out or it exists only in unpublished work. If a publication's contract does not match the requested version, choose a compatible snapshot explicitly. Do not substitute live data without changing the integration's stated guarantees.

## When the version is being retired

Watch `Deprecation` and `Sunset` on the version you use. The model administrator chooses
its notice period; a sunset day does not itself stop service. Arrange migration to a tested
replacement before the administrator removes the version. Each retained version continues
reading current data through its own definition.

`404 CONTRACT_VERSION_NOT_FOUND` means the workspace no longer serves the requested number.
Read `details.servedContractVersions`, rediscover the index and inspect the replacement’s
document. Do not automatically retry another version with the same parser. An older
publication cannot restore a version that the workspace no longer serves. See
[Earlier contract versions](/docs/integrate/consumer-apis/#earlier-contract-versions).

## Work through the reference contract

The `stops` contract is one configuration. Use these exact paths only in a workspace declaring it. Supply a consumer-audience bearer token with the API's workspace grant:

```http
GET /api/consumer/stops/v1/objects/8d90eede-23cf-47c1-8dac-cb37956f5fd5?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

The 200 body is the shared `Stop` object for Tschamut-Selva: the stop number, typed fields, parent, ancestor path, operator, modes, system codes and translations. It is not wrapped in `items`. Check the [complete response](/docs/integrate/reading-business-objects/#a-complete-object-read) before coding a client that expects another shape.

To enumerate stops, use a list instead:

```http
GET /api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&pageSize=1&includeTotal=true HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

This answers an `items` array plus `workspace`, `publication` and paging fields. Process the first page, save its next cursor after committing local work, and send that cursor with the same request scope. See the [complete first-page body and continuation rules](/docs/integrate/reading-business-objects/#a-list-page-with-navigation).

To read only stops for one operator, start a new request with `operator=MGB-fo`. The declaration matches operator code or name and requires a matching relationship. The result begins with Tschamut-Selva and counts 13 stops in the reference snapshot. The [parameter example](/docs/integrate/reading-business-objects/#the-same-list-narrowed-by-a-declared-parameter) shows the complete body. Do not reuse the unfiltered cursor.

Finally repeat a GET with its saved ETag in `If-None-Match`. A 304 has no body; retain the previous one. The [unchanged-response exchange](/docs/integrate/reading-business-objects/#reuse-an-unchanged-answer) shows both headers and the absence of a response body. For a missing list or refused filter, correct the declaration name or request rather than accepting an empty extract.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0.*
