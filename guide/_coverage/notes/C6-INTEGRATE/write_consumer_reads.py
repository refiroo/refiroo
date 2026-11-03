import json
from finish_unit import root,steering,finish
steering()
e=json.loads((root/'_coverage/notes/C6-INTEGRATE/examples.json').read_text())
stop=e['stop']; ident=e['id']
def js(x):return '```json\n'+json.dumps(x,ensure_ascii=False,indent=2)+'\n```\n'
def request(path,extra=''):
 return '```http\nGET '+path+' HTTP/1.1\nHost: <instance>\nAuthorization: Bearer <consumer-token>\nAccept: application/json\n'+extra+'```\n'
p=root/'src/content/docs/integrate/reading-business-objects.md'
s=p.read_text()+'''
## A complete object read

**Reference-data example:** the requests below use the `stops` declaration explained in [Consumer APIs](/docs/integrate/consumer-apis/#from-a-declaration-to-a-running-api). Replace the host and token with your instance's values. The bodies are composed from the reference snapshot; cursors and ETags shown in angle brackets stand for opaque strings returned by your own instance. They are not tokens to paste into a request.

The declaration's `operations.objects` exposes this request. Notice that the path uses the record UUID, while the returned `code` is a separate business identifier:

'''+request(f'/api/consumer/stops/v1/objects/{ident}?workspace=graubuenden')+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
ETag: "<etag-from-this-response>"
```

'''+js(stop)+'''
This is the whole body, not an envelope containing a record. `objectType` uses the declaration's public name. `stopNumber` is an integer; decimal coordinates and height use the API's decimal string encoding, preserving their precision. Nulls mean this object has no applicable value for that output. The declared operator is an object; modes, system codes and translations are arrays. An empty array is a real empty projection, not an omitted part of this example.

## A list page with navigation

`all-stops` declares `of: stop` and `sortBy: stop-number`. This request asks for its first record and an exact total:

'''+request('/api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&pageSize=1&includeTotal=true')+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'items':[e['firstStop']],'workspace':'graubuenden','publication':None,'pageSize':1,'nextCursor':'<next-cursor-from-this-page>','prevCursor':None,'anchor':'<anchor-from-this-page>','totalCount':e['count'],'startIndex':0})+'''
Follow `nextCursor` with the same list, workspace and filters. URL-encode the opaque cursor as one query value; keep `includeTotal=true` if you still need counts. `prevCursor` goes back; `anchor` reopens this page. At the last page `nextCursor` is null. The 2,443 total describes the reference snapshot, not a fixed product limit. Without totals requested, `totalCount` and `startIndex` are null.

Position navigation is a jump to a numbered row; `from=end` starts at the end; `seek` jumps by a supported sort value. Choose only one navigation method in a request. Use a publication when the extract must stay fixed while pages are read.

## The same list narrowed by a declared parameter

The declaration's `operator` filter reads the `operator` projection, matches its code or name, and requires a match. It does not add a new route. Add it to the list request:

'''+request('/api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&operator=MGB-fo&pageSize=1&includeTotal=true')+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'items':[stop],'workspace':'graubuenden','publication':None,'pageSize':1,'nextCursor':'<next-cursor-for-this-operator-filter>','prevCursor':None,'anchor':'<anchor-for-this-operator-filter>','totalCount':13,'startIndex':0})+'''
The reference snapshot has 13 stops for this operator. Reusing the unfiltered cursor here is invalid: the filter changes the collection. A `municipality` ancestor filter can instead match its declared fields, while the scoped `/lists/stops` route's municipality parent parameter takes municipality IDs. Do not assume a parent parameter accepts every field that an ordinary filter accepts.

## Reuse an unchanged answer

Save the body from the object read and its exact ETag. Repeat the same request with that tag, including its quotes:

'''+request(f'/api/consumer/stops/v1/objects/{ident}?workspace=graubuenden','If-None-Match: "<etag-from-this-response>"\n')+'''
```http
HTTP/1.1 304 Not Modified
RDM-Workspace: graubuenden
ETag: "<etag-from-this-response>"
```

There is **no response body**. Keep using the cached body. If the server instead returns 200, replace the cached body and tag together. A live write elsewhere in the workspace can change the tag; it is not a per-object change counter. Adding `publication=<publication-id>` pins the read, and the answer identifies it in `RDM-Publication` and collection `publication` fields.

## A request that the declaration cannot answer

The model offers a list named `all-stops`; it does not offer `no-such-list`:

'''+request('/api/consumer/stops/v1/lists/no-such-list?workspace=graubuenden')+'''
```http
HTTP/1.1 404 Not Found
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'error':{'code':'LIST_NOT_FOUND','message':"List 'no-such-list' not found"}})+'''
Correct the list name using the declaration or rediscover the intended workspace's contract. Do not turn a request error into an empty dataset. Inspect the [reference operations](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/lists/all-stops) for the instance's complete generated schema.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0.*
'''
p.write_text(s)
finish(['src/content/docs/integrate/reading-business-objects.md'],'Applied steering: full stop, unfiltered and parameter-filtered list bodies, paging, conditional 304 and a real-shaped LIST_NOT_FOUND error. Production object composer confirmed values; list envelopes and caching checked against J28 source assertions. Cursors/ETags are explicit opaque placeholders; no live HTTP capture.')
