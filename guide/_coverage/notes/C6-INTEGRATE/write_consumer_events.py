import json
from datetime import datetime
from finish_unit import root,steering,finish
from app.engine.events.delivery import RequestFormat,encode,headers,events_source
steering()
e=json.loads((root/'_coverage/notes/C6-INTEGRATE/examples.json').read_text());stop=e['stop']
def js(x):return '```json\n'+json.dumps(x,ensure_ascii=False,indent=2)+'\n```\n'
event={'eventId':'8b6b294b-ff1a-4bb8-898c-a2e412e64f71','position':64,'occurredAt':'2026-11-02T08:00:00+00:00','event':'stops-changed','change':'updated','contractVersion':1,'objectType':'Stop','id':e['id'],'code':stop['code'],'name':stop['name'],'changed':['name'],'cause':{'kind':'user'}}
full={**event,'stateAt':64,'object':stop}
subscription='a7447804-c8c0-4e13-9a7f-117e7ec6ba15';delivery='85c0fa4d-c85c-4e2d-b788-24c8f3800fd8'
f=RequestFormat('rdm',False,{'subscriptionId':subscription,'consumerApi':'stops','contractVersion':1,'workspaceKey':'graubuenden'},events_source('stops',1,'graubuenden'))
body=encode(f.body(delivery,[event])); timestamp=int(datetime.fromisoformat(event['occurredAt']).timestamp()); signed=headers(delivery,['guide-example-only'],timestamp,body,f.content_type)
(root/'_coverage/notes/C6-INTEGRATE/webhook-example.json').write_text(json.dumps({'event':full,'body':body.decode(),'headers':signed,'timestamp':timestamp,'secret':'guide-example-only'},ensure_ascii=False,indent=2)+'\n')
p=root/'src/content/docs/integrate/consumer-events-and-webhooks.md'
s=p.read_text()+'''
## A declaration and the event it exposes

**Reference-data example:** the `stops` contract declares this event:

```json
{
  "events": {
    "custom": [{
      "key": "stops-changed",
      "objectTypes": ["stop"],
      "changes": ["created", "updated", "deleted"],
      "watch": {"fields": ["code", "name", "validFrom", "validTo"]}
    }]
  }
}
```

This adds an event named `stops-changed` to the contract's Events operation. It watches those output fields, so a change affecting only height is not this event. A broader event or additional watched fields needs a model declaration. Standard per-type events are available when a model declares them; this reference model declares this custom event instead.

The following is an **illustrative update to the reference stop's name**, not a captured event from the seed. The object values are production-composed reference data; event IDs, positions and times are example values. Suppose the update is at position 64 and events have been derived through that position:

```http
GET /api/consumer/stops/v1/events?workspace=graubuenden&after=63&event=stops-changed&pageSize=1&payload=full HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'items':[full],'workspace':'graubuenden','pageSize':1,'cursor':'<lasting-cursor-after-this-event>','caughtUp':True,'headPosition':64,'earliestPosition':1})+'''
`position` says which committed change produced the event. `stateAt` says when the current object was composed; it can be later than the event position. `changed` names affected outputs, not old and new values. `cause` identifies the kind of work; it is not the actor's identity. A deletion omits `object` and `stateAt` and has null `code` and `name`.

With `payload=identity`, the event retains identity, change, cause and affected output names but omits `object` and `stateAt`. Save `cursor` after durably processing the page, then use it instead of `after` to continue, including within a position. `caughtUp` applies to derived events; more can arrive later. Do not treat a short filtered page as caught up without checking the flag.

## The actual webhook request shape

A subscription is separate from that declaration. Choose the workspace, consumer API, event names, filters, receiver, payload, format and request batching. For this example, take an active subscription to `stops-changed` with **identity** payload, RDM JSON format and one event per request. Its [management operations](/docs/api/?api=management#tag/consumer%20subscriptions) require a management token with Integration administration, even though the receiver gets consumer events.

Here is a complete delivery body in the compact form the sender signs. The IDs and timestamp are illustrative. The demonstration signing secret is the literal text `guide-example-only`; it is a public example, not a credential for any instance. The engine's production delivery encoder and signer generated this example header and body. There is no trailing newline in the signed body.

```http
POST /refiroo-events HTTP/1.1
Host: receiver.example
'''+''.join(k+': '+v+'\n' for k,v in signed.items())+f'Content-Length: {len(body)}\n\n'+body.decode()+'''
```

Even a one-event RDM JSON request has an envelope and an `events` array. `deliveryId` identifies this delivery request; `eventId` identifies the business event. On an automatic retry the delivery identity stays the same while a full object's values may have changed. Use event IDs to make processing repeatable.

## Verify the bytes before decoding JSON

This Python example verifies the timestamp and any supported signature. Your HTTP framework must supply the original body bytes and a case-insensitive header mapping. The five-minute freshness window is this receiver's example replay policy, not a server setting:

```python
import hashlib
import hmac
from collections.abc import Mapping


def verify_webhook(
    secret: str, headers: Mapping[str, str], raw_body: bytes, now: int
) -> bool:
    try:
        timestamp_text = headers["RDM-Timestamp"]
        timestamp = int(timestamp_text)
        supplied = headers["RDM-Signature"]
    except (KeyError, ValueError):
        return False
    if abs(now - timestamp) > 300:
        return False
    digest = hmac.new(
        secret.encode("utf-8"),
        timestamp_text.encode("ascii") + b"." + raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected = "sha256=" + digest
    return any(
        hmac.compare_digest(expected, candidate.strip())
        for candidate in supplied.split(",")
        if candidate.strip().startswith("sha256=")
    )
```

For the sample request, pass its timestamp as the test clock to reproduce verification. A live receiver uses the actual current time and must reject this dated sample. During rotation, run verification with each currently accepted secret; either an accepted current or overlap key can authenticate the request. Never decode the displayed hexadecimal secret or reformat the JSON before signing: use the secret as issued and the request's raw bytes.

After verification, durably store or queue events and deduplicate by event ID, then acknowledge within ten seconds with a 2xx. If storage fails, do not acknowledge acceptance. A slow acknowledgment can cause a retry even after local processing succeeded.

## If the subscription chooses CloudEvents

With CloudEvents format and one event per request, the same identity event is wrapped as follows. The content type is `application/cloudevents+json; charset=utf-8`; its signature covers the bytes of this CloudEvent, not the RDM JSON envelope above. The displayed indentation is for reading, so do not reuse the previous signature for it:

'''+js(RequestFormat('cloudevents',False,f.envelope,f.source).body(delivery,[event]))+'''
With batching enabled the body is an array of these CloudEvents and the content type is `application/cloudevents-batch+json; charset=utf-8`, even if only one event is ready. `data` remains the same consumer event. The subscription ID is an extension attribute; the event type combines `rdm.`, the declared event name and its change.

Follow [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for setup, testing, rotation and recovery in order. The [Events reference](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events) documents the actual contract on your instance.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Event occurrence, delivery IDs and the verification key are illustrative.*
'''
p.write_text(s)
finish(['src/content/docs/integrate/consumer-events-and-webhooks.md'],'Applied steering: declaration-to-event explanation, complete full event page, production-encoded identity webhook with computed signature headers, verification function and complete CloudEvent. Shapes checked against J30 event and delivery assertions. The occurrence is illustrative; no receiver or live subscription was created.')
