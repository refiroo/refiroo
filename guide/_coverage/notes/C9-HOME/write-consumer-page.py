from pathlib import Path
from datetime import datetime
import copy,json
root=Path('guide')
raw=json.loads((root/'samples/model.json').read_text())['consumerApis'][0]
starter=json.loads(Path('model/rdm-starter.json').read_text())['consumerApis'][0]
proof=json.loads((root/'_coverage/notes/C9-HOME/composed-examples.json').read_text())
webhook=json.loads((root/'_coverage/notes/C6-INTEGRATE/webhook-example.json').read_text())
def js(x):return '```json\n'+json.dumps(x,ensure_ascii=False,indent=2)+'\n```\n'
def request(path,method='GET',body=None,headers=''):
 return '```http\n'+method+' '+path+' HTTP/1.1\nHost: <instance>\nAuthorization: Bearer <consumer-token>\nAccept: application/json\n'+headers+('Content-Type: application/json\n\n'+json.dumps(body,ensure_ascii=False,indent=2)+'\n' if body is not None else '')+'```\n'
def response(body,status='200 OK',headers=''):
 return '```http\nHTTP/1.1 '+status+'\nContent-Type: application/json\nRDM-Workspace: graubuenden\n'+headers+'```\n\n'+js(body)
pieces=['''---
title: The consumer API example
description: See how a model turns reference data into a contract for other systems, with complete stop requests and answers.
reader: evaluator
---

A consumer API lets another system read the business objects a model chooses to share. It brings
fields and related records into one answer, so a consumer does not have to assemble the record
structure itself. The contract, including its names, lists and events, belongs to the model.

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

''', js({k:starter[k] for k in ['key','name','contractVersion','exposes','publicNames']}), '''
The declaration also includes these lists and event under its operations:

''',js({'lists':starter['operations']['lists'],'events':starter['operations']['events']}),'''
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

''']
excerpt={k:raw[k] for k in ['key','name','contractVersion','exposes','publicNames']}
excerpt['object']={'fields':raw['object']['fields'],'parent':raw['object']['parent'],'path':True,'related':{'operator':raw['object']['related']['operator']}}
excerpt['operations']={'objects':{},'lists':{'all-stops':raw['operations']['lists']['all-stops']},'events':raw['operations']['events']}
excerpt['filters']={'operator':raw['filters']['operator']}
pieces += [js(excerpt),'''
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
use the 2 November 2026 reference snapshot, composed with the engine's object renderer. They are not
captures of live requests. ETags, cursors and event identifiers shown as examples depend on an instance.

''',request('/api/consumer/stops/v1/objects/'+proof['id']+'?workspace=graubuenden'),response(proof['stop'],headers='ETag: "<etag-returned-by-your-instance>"\n'),'''
The UUID in the path is the record's stable identity. Its code and stop number are separate business
identifiers. The stop number is an integer; decimal coordinates and height use decimal strings to
retain precision. Null fields have no applicable value here. The parent is one object, modes and
system codes are arrays, and an empty translations array is a complete answer.

### Read a list, then narrow it

This first-page request asks for one stop and an exact total:

''',request('/api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&pageSize=1&includeTotal=true')]
page={'items':[proof['firstStop']],'workspace':'graubuenden','publication':None,'pageSize':1,'nextCursor':'<next-cursor-returned-by-your-instance>','prevCursor':None,'anchor':'<anchor-returned-by-your-instance>','totalCount':proof['count'],'startIndex':0}
pieces += [response(page),'''
The snapshot holds 2,443 stops; that is not a product limit. List pages hold 1–100 objects, default
20. Follow `nextCursor` with the same workspace, list and filters, URL-encoding the cursor as one
value. `prevCursor` goes back and `anchor` reopens the page. Counts are null unless requested.
For an extract that must stay fixed across pages, select a [publication](/docs/integrate/reading-business-objects/#page-and-cache).

Now add the declared operator parameter:

''',request('/api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&operator=MGB-fo&pageSize=1&includeTotal=true')]
filtered=copy.deepcopy(page);filtered.update(items=[proof['stop']],totalCount=13,nextCursor='<next-cursor-for-this-operator>',anchor='<anchor-for-this-operator>')
pieces += [response(filtered),'''
There are 13 reference stops for this operator. The parameter narrows the existing list; it does
not create another route. Use the cursor from this filtered answer, rather than the unfiltered one.

### Look up a stop number

XREF adds a score to the same business object. Asking for exactly one answer returns the untied top
match directly. A tied top score is an ambiguity to resolve, rather than permission to choose the
first record.

''',request('/api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&expect=one'),response({**proof['stop'],'matchScore':900}),'''
Without `expect=one`, XREF returns a page with `results`, `query`, workspace, publication and paging
fields. See the [complete scored page](/docs/integrate/looking-up-and-resolving/#a-lookup-with-a-score)
and [system-code crosswalk](/docs/integrate/looking-up-and-resolving/#a-crosswalk-from-a-stop-number-to-another-systems-code).

### Resolve several inputs

Batch resolution is a read expressed as POST. Each item asks by query or by ID; the result keeps
input order and the supplied row reference. This example's second code is the deliberately unmapped
**fictional** Regional ticketing code:

''',request('/api/consumer/stops/v1/resolve?workspace=graubuenden',method='POST',body={'defaults':{'mode':'TRAIN'},'items':[{'ref':'row-1','query':'8505173'},{'ref':'row-2','query':'T-9999'}]}),response({'items':[{'index':0,'ref':'row-1','status':'found','object':{**proof['stop'],'matchScore':900}},{'index':1,'ref':'row-2','status':'not_found','error':{'code':'NO_MATCH','message':'No object matches the query'}}],'workspace':'graubuenden','publication':None,'counts':{'found':1,'notFound':1,'ambiguous':0,'rejected':0}}),'''
HTTP success does not mean every input resolved. Keep each outcome, including not found, ambiguous
and rejected. For a file, follow [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/).

### Reuse an unchanged answer

Repeat the identical object request with the ETag received above, including its quotes:

''',request('/api/consumer/stops/v1/objects/'+proof['id']+'?workspace=graubuenden',headers='If-None-Match: "<etag-returned-by-your-instance>"\n'),'''```http
HTTP/1.1 304 Not Modified
RDM-Workspace: graubuenden
ETag: "<etag-returned-by-your-instance>"
```

There is no response body; retain the cached answer. A 200 response replaces the body and tag
together. A live tag can change after another workspace write, even if this stop looks the same.

### Correct a request error

The declaration offers `all-stops`, not `no-such-list`:

''',request('/api/consumer/stops/v1/lists/no-such-list?workspace=graubuenden'),response({'error':{'code':'LIST_NOT_FOUND','message':"List 'no-such-list' not found"}},status='404 Not Found'),'''
Correct the name from the workspace's contract. An error is not an empty collection.

### Follow the declared event

The declaration above enables `stops-changed`. This example supposes a committed name update at
position 64, with events derived through that position. The occurrence, positions and event IDs
are illustrative; the stop's values come from the reference data.

''',request('/api/consumer/stops/v1/events?workspace=graubuenden&after=63&event=stops-changed&pageSize=1&payload=identity')]
event={k:v for k,v in webhook['event'].items() if k not in ['stateAt','object']}
pieces += [response({'items':[event],'workspace':'graubuenden','pageSize':1,'cursor':'<lasting-cursor-returned-by-your-instance>','caughtUp':True,'headPosition':64,'earliestPosition':1}),'''
Save the lasting cursor after processing the page; it can resume within a position containing several
events. With `payload=full`, the event also includes the object read now and `stateAt`, the position
at which it was composed. It is not a historical copy of the object at the event's time.
See the [complete full event](/docs/integrate/consumer-events-and-webhooks/#a-declaration-and-the-event-it-exposes).

### Receive the event at a webhook

An administrator can separately create a subscription to this event. The model declaration does not
register a receiver. Delivery needs the deployment's webhook capability and a configured subscription;
see [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/).

For identity payloads in RDM JSON format, one event per request, the receiver gets the following
complete body. It uses the public demonstration secret `guide-example-only`. The IDs, timestamp
and signature are example values. The compact body has no trailing newline:

```http
POST /refiroo-events HTTP/1.1
Host: receiver.example
'''+''.join(k+': '+v+'\n' for k,v in webhook['headers'].items())+'Content-Length: '+str(len(webhook['body'].encode()))+'\n\n'+webhook['body']+'\n```\n','''
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
''']
(root/'src/content/docs/examples/the-consumer-api.md').write_text(''.join(pieces))
with (root/'_waves/progress/C9-HOME.md').open('a') as f:
 f.write('\n'+datetime.now().astimezone().isoformat(timespec='seconds')+' — Finished `guide/src/content/docs/examples/the-consumer-api.md`. Applied C6 steering: starter and stops declaration excerpts, complete reference stop/list/filtered-list/lookup/resolve/cache/error/event/webhook examples, plus signature verification and instance document pointers. Object values were recomposed offline with the production renderer; opaque tokens and the illustrative event are labelled, with no claim of live HTTP verification. No C9 steering file exists.\n')
