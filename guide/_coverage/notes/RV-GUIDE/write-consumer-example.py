import json
from pathlib import Path
from datetime import datetime
root=Path('guide'); p=root/'src/content/docs/integrate/consumer-apis.md'
s=p.read_text()
# Keep the earlier wave's explanation and add one focused worked example.
intro='''## Publish values of the connection

A related block can expose a value held by the relationship used to reach its item. Write
`relation:<attribute-key>` in `object.related.<block>.fields`. The source reads that connection,
not an attribute of either endpoint. A missing value becomes null; the schema and generated
OpenAPI retain the attribute's type, including boolean and numeric types. All business-object
reads use it: Get by ID, lists, XREF and Resolve. A crosswalk can return it in its selected
related representation too.

**Illustrative extension of the reference stops model:** the shipped reference model has no
carried attributes. Suppose its stop-to-operator pair is extended to carry a Text attribute
`local-name` and a Yes or no attribute `is-primary`. The following alternative v2 definition
keeps the object deliberately small so each complete answer is readable. It is a worked model
example, not an activated release or a capture of the reference instance. Existing v1 clients
continue using the original shape only if its definition is retained separately.

The relationship's `attributeTypeKeys` must include both added global attribute definitions.
This consumer declaration then exposes their values:

'''
api=json.loads((root/'_coverage/notes/RV-GUIDE/consumer-declaration.json').read_text())
def block(obj): return '```json\n'+json.dumps(obj,indent=2,ensure_ascii=False)+'\n```\n\n'
def request(method,path,body=None):
 return '```http\n'+method+' '+path+' HTTP/1.1\nHost: <instance>\nAuthorization: Bearer <consumer-token>\nAccept: application/json\n'+('Content-Type: application/json\n\n'+json.dumps(body,indent=2) if body is not None else '')+'\n```\n\n'
def response(obj):return '```http\nHTTP/1.1 200 OK\nContent-Type: application/json\nRDM-Workspace: graubuenden\n```\n\n'+block(obj)
obj={'objectType':'Stop','id':'8d90eede-23cf-47c1-8dac-cb37956f5fd5','name':'Tschamut-Selva','operator':{'id':'f94ef862-2a95-4675-9e31-6b1d0a03317f','name':'Matterhorn Gotthard Bahn (fo)','localName':'FO contact','isPrimary':True}}
text=intro+block(api)+'''The `operator` block is object-or-null because this directed pair allows one operator per
stop. In this illustrative state, only Tschamut-Selva's connection holds `local-name` equal to
“FO contact” and `is-primary` true. Those two values are fictional. The stop and operator names
and identities come from the reference example. Another stop connected to the same operator
can hold a different local name and primary flag.

### Read the object and filter a list

'''+request('GET',f'/api/consumer/stops/v2/objects/{obj["id"]}?workspace=graubuenden')+response(obj)+'''The `contact` filter compares the connection's local name without letter case. The `primary`
filter parses a Yes or no value. With `keepOnlyMatching: true`, each drops objects with no
matching item; without that option it only trims the related block. `scoreOnlyMatching` and
`crosswalk` retain their usual meanings for On related filters.

'''+request('GET','/api/consumer/stops/v2/lists/all-stops?workspace=graubuenden&contact=FO%20contact&primary=true&pageSize=20&includeTotal=true')+response({'items':[obj],'workspace':'graubuenden','publication':None,'pageSize':20,'nextCursor':None,'prevCursor':None,'anchor':'<opaque-anchor-from-response>','totalCount':1,'startIndex':0})+'''The anchor above stands for an instance-generated opaque value; use the actual value returned
by your instance. This complete illustrative page has one match and no continuation.

### Match and resolve through that connection

`alsoMatchThrough.firstOf` can name `relation:local-name` even if the block does not expose it.
A scored relationship source must hold text. Its weight belongs to the connection that
matched: another stop sharing the operator does not receive 90 just because this stop's
connection holds “FO contact”. Relationship attributes need neither Searchable nor Unique
for these matching choices. Matching reads the relationships' values, so broad rules over
many connections can cost more than an indexed identifier lookup.

'''+request('GET','/api/consumer/stops/v2/xref?workspace=graubuenden&query=FO%20contact&expect=one')+response({**obj,'matchScore':90})+request('POST','/api/consumer/stops/v2/resolve?workspace=graubuenden',{'items':[{'ref':'row-1','query':'FO contact'}]})+response({'items':[{'index':0,'ref':'row-1','status':'found','object':{**obj,'matchScore':90}}],'workspace':'graubuenden','publication':None,'counts':{'found':1,'notFound':0,'ambiguous':0,'rejected':0}})+'''These are full answers for the small v2 declaration above, not additional fields automatically
added to the shipped v1 answers. See [Looking up and resolving](/docs/integrate/looking-up-and-resolving/)
for ties, missing results, score restrictions and crosswalks.

### Publications, business dates and validation

Use `publication` to read the saved relationship values in a compatible publication. An `asOf`
read applies business validity in the selected source; it does not restore the relationship's
values to what they were on that date. For the shipped contract's validity fields and the
complete sequence, see [Business dates](/docs/integrate/business-dates/) and
[Reading business objects](/docs/integrate/reading-business-objects/).

The source is allowed only in related fields, an `onRelated` filter's `matchOn`, and a related
XREF promotion's `firstOf`. Main object fields, own XREF rules and `under` or `linkedTo` match
fields refuse it with `INVALID_REFERENCE`. The named attribute must be carried by a binding
of that relation, in the chosen direction, reachable from an exposed type. Validation names
the authored path, relation and attribute. A non-text relationship attribute in a scored
`firstOf` rule is `INVALID_MODEL`. Correct the model; dropping a request filter does not repair
an invalid declaration.

### Follow edits of carried values

The illustrative event watches the `operator` related block. Because that block reads
relationship values, an update of the relationship can produce `stops-changed` with
`change: updated` and `changed: ["operator"]`. This reports an affected block, not an old/new
value diff. The shipped reference event watches only main fields, so it does not report this
extra change without a declaration change. Unpublished change-set edits produce no consumer
event; publication makes their committed effects eligible.

Here is an illustrative identity event page after a relationship edit. Event identity, position,
time and cursor are illustrative, rather than values captured from the reference instance.

'''
event={'eventId':'8b6b294b-ff1a-4bb8-898c-a2e412e64f71','position':64,'occurredAt':'2026-11-02T08:00:00+00:00','event':'stops-changed','change':'updated','contractVersion':2,'objectType':'Stop','id':obj['id'],'code':None,'name':obj['name'],'changed':['operator'],'cause':{'kind':'user'}}
text+=request('GET','/api/consumer/stops/v2/events?workspace=graubuenden&after=63&event=stops-changed&payload=identity&pageSize=20')+response({'items':[event],'workspace':'graubuenden','pageSize':20,'cursor':'<opaque-event-cursor-from-response>','caughtUp':True,'headPosition':64,'earliestPosition':1})+'''A subscription for this event using identity payload and RDM JSON sends this body. The
signature and delivery headers follow the [webhook contract](/docs/integrate/consumer-events-and-webhooks/#the-actual-webhook-request-shape);
the placeholders below must be replaced by the sender's real values. Do not use this
pretty-printed example to verify a signature; verification uses the exact received bytes.

```http
POST /refiroo-events HTTP/1.1
Host: receiver.example
Content-Type: application/json
RDM-Delivery-Id: 85c0fa4d-c85c-4e2d-b788-24c8f3800fd8
RDM-Timestamp: <delivery-unix-seconds>
RDM-Signature: sha256=<signature-over-the-received-body>
```

'''+block({'deliveryId':'85c0fa4d-c85c-4e2d-b788-24c8f3800fd8','subscriptionId':'a7447804-c8c0-4e13-9a7f-117e7ec6ba15','consumerApi':'stops','contractVersion':2,'workspaceKey':'graubuenden','events':[event]})+'''With full payload, the event also carries `object` in the same declared shape and `stateAt`.
Those are composed from current data at delivery or read time, not frozen at position 64.
See [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) for signing,
deduplication, retries, CloudEvents and recovery.

*Reference identities and names: Source: opentransportdata.swiss, Service Points (Didok), Federal
Office of Transport / SBB, snapshot 2026-11-02. Relationship values and event metadata here are fictional.*

'''
marker='## Review a contract change'
s=s.replace(marker,text+marker)
p.write_text(s)
with (root/'_waves/progress/RV-GUIDE.md').open('a') as f:f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `integrate/consumer-apis.md`. Preserved earlier content and added a compiler-validated illustrative stops v2 declaration with full object/list/XREF/Resolve answers, typed values, validation, publication/date semantics and event/webhook bodies. No live HTTP capture is claimed; the reference model carries none. No steering file present.\n')
