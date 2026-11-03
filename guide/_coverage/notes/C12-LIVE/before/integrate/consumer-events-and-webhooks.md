---
title: Consumer events and webhooks
description: Follow declared business changes and receive signed, ordered, repeatable deliveries.
reader: integrator
---

Consumer events tell an integration which business objects were affected by committed changes. The model declares their names, exposed types, kinds of change and watched outputs as part of the contract. Read them through the contract's event operation or receive them at a webhook receiver. Follow [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for setup.

## Understand what an event means

Events report created, updated or deleted business objects. With `perType: true`, standard event names are `<type-key>-changed`, one per exposed type in declaration order; each covers `created`, `updated` and `deleted`. Models can also declare custom names. Event name and change kind are separate fields. Updates can arise from an object's fields, its parent or ancestors, or related blocks. The engine uses changed source names rather than comparing rendered answers, so a watched output can be named even when its displayed answer stayed equal. Applied jobs and publications identify their cause. Refused writes and unpublished change-set work produce none. Consumer record events contain no actor identity. A validity period starting or ending without a write produces no event. Installing a model or administering a workspace produces no consumer data event. Changing a record’s type is seen from each event’s declared types: leaving them is deleted, entering them is created, and moving between two included types is updated with `objectType` among the changed outputs.

Full payloads include the object as a read would answer **now**, with its composition position. They are not historical copies at event time. A deleted object has no full object and no current code or name. Identity-only events require separate reads for values. Keep event identity for deduplication even when a later read gives newer values.

Filters use current live data, except the public type stored with the event. Deleted objects pass other parameters. A surviving record that leaves a filtered scope does not generate an explicit departure notification for that filter. A filtered mirror therefore needs reconciliation; do not assume every scope exit arrives as deletion.

## Pull and resume

Use the contract's Events operation. **Example:** the reference contract offers [Events](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events) for its declared `stops-changed` event. Start from zero or from a publication's event sequence after loading that publication. Then retain the returned lasting cursor: it can continue within one position where several events exist. A position alone is not a sufficient checkpoint mid-position.

Pages support up to 100 full objects or 1,000 identities. Filtered reads can return short or empty pages while still behind; follow the cursor and the caught-up indication. Conditional GET is supported, but live object changes can change the tag before another event has been derived.

`EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT` and `INVALID_PAYLOAD` require a supported contract and payload choice. `EVENT_POSITION_AHEAD` needs source verification and a new baseline if necessary. `EVENTS_EXPIRED` requires rereading the indicated publication and following from its event sequence. Retention follows the change feed, normally 30 days; with no usable publication baseline, events do not expire. Event reads do not take publication, business-date or target-representation filters.

## Subscribe a receiver

The [consumer subscription operations](/docs/api/?api=management#tag/consumer%20subscriptions) require Integration administration in the workspace and the deployment's webhook capability. It is off by default. Subscriptions are runtime configuration, not model content. In the browser, administrators manage subscriptions under **Settings › Integration › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.

Choose events, declared narrowing filters, full objects or notifications, RDM JSON or CloudEvents, and one event per request or batching. Batching holds up to 1,000 events, sending what is ready without waiting to fill it. A batch normally stops at 1 MiB; a single oversized event is sent alone. The receiver must allow that exception. CloudEvents uses structured single-event or batch form according to the subscription's request mode, including a batch containing only one event.

Use an absolute URL of at most 2,048 characters, without a username, password or fragment. Use HTTPS. Plain HTTP is accepted only for named loopback hosts. Each attempt resolves and checks the destination before connecting; link-local addresses are refused and loopback resolution needs a loopback URL host. Redirects are not followed. `INVALID_WEBHOOK_URL` requires a supported URL, not an authentication retry. The consumer API and workspace cannot be edited on an existing subscription; create another when those change.

## Verify before accepting

Creation shows a signing secret once. Keep it in the receiver's protected configuration; it cannot be retrieved later. The signature is HMAC-SHA256 over the timestamp, a dot and the **raw body bytes**, using the secret exactly as supplied. Use the delivery contract in the [subscription reference](/docs/api/?api=management#tag/consumer%20subscriptions) when implementing verification. Do not parse and reserialize JSON before verifying it.

Reject stale timestamps according to your replay policy, compare signatures in constant time and accept a request when any supported signature in the comma-separated header verifies. Deduplicate by event ID. Acknowledge with a 2xx only after your receiver has durably accepted the work; queue longer processing locally.

Rotating the key keeps both current and previous signatures during the chosen overlap: 24 hours by default, from zero to seven days. Another rotation ends the older overlap. Switch the receiver before the previous key expires. Immediate rotation is available for a leaked key, including signatures on pending retries.

## Ordering, retries and resends

Requests go one at a time per subscription, in event order. A failed request blocks later requests. Any non-2xx response, redirect, connection or TLS failure, refused address, or a response taking over 10 seconds fails the attempt. Retries wait 10 seconds, 30 seconds, 1, 2, 5, 10 and 30 minutes, then hourly, with 20% timing variation. After 24 hours of failure the subscription pauses with `DELIVERY_FAILED`.

Automatic retries retain their event range and delivery ID but compose current objects again. The same event may arrive with newer values. A manual resend instead repeats the stored event payload and original format in a new, single-attempt request, keeping event ID and adding the manual-redelivery header. It does not advance the subscription or clear its pending batch. The header is `RDM-Redelivery: manual`. The resend can run while suspended; its result is a new delivery record with `resendOf` naming the original. Decide explicitly whether manual redelivery should bypass your normal duplicate suppression.

The delivery log distinguishes queued, sending, retrying, succeeded, failed and dropped requests, and shows attempt timing and receiver responses. It keeps entries seven days by default (`CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`, reported as `consumerSubscriptions.logRetentionDays`), longer for pending batches. Deleting a subscription deletes its log entries too. `DELIVERY_NOT_FOUND` means the request is unavailable; `DELIVERY_NOT_SENT` means it has no sent body to repeat; `EVENT_NOT_IN_DELIVERY` means choose an event actually in that request.

## Recover a paused subscription

Pause reasons include user suspension, changed or removed model declarations, contract-version changes, retired workspace, failed delivery, filters matching nothing and expired events. Read the reason, fix the receiver or declaration and resume. Resume normally starts at the first unacknowledged event. `SUBSCRIPTION_NEEDS_EDIT` names remaining problems. `SUBSCRIPTION_ALREADY_SUSPENDED` and `SUBSCRIPTION_NOT_SUSPENDED` require refreshing its state; `SUBSCRIPTION_NOT_FOUND` requires the correct ID.

If events expired, resetting starts after the current head and requires a fresh baseline. Reset **before** rereading the baseline so intervening changes can be processed twice instead of missed. `FILTER_MATCHES_NOTHING` requires correcting the stale reference filter. A workspace with subscriptions cannot be deleted (`WORKSPACE_HAS_SUBSCRIPTIONS`); review them first.

## Workspace approval events

Workspace subscriptions deliver `change-set.submitted`, `change-set.approved` and `change-set.sent-back`. They have a workspace source without a consumer API. They use the same signing, ordering, retry, logging, resend and rotation rules, but do not accept consumer filters or payload selection (`NOT_SUPPORTED_BY_SOURCE`). They identify submitter and decider without email addresses. Their positions are a separate per-workspace sequence. A model release change does not pause these subscriptions. See [Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/).

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

```json
{
  "items": [
    {
      "eventId": "8b6b294b-ff1a-4bb8-898c-a2e412e64f71",
      "position": 64,
      "occurredAt": "2026-11-02T08:00:00+00:00",
      "event": "stops-changed",
      "change": "updated",
      "contractVersion": 1,
      "objectType": "Stop",
      "id": "8d90eede-23cf-47c1-8dac-cb37956f5fd5",
      "code": "ch:1:sloid:5173",
      "name": "Tschamut-Selva",
      "changed": [
        "name"
      ],
      "cause": {
        "kind": "user"
      },
      "stateAt": 64,
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
        "translations": []
      }
    }
  ],
  "workspace": "graubuenden",
  "pageSize": 1,
  "cursor": "<lasting-cursor-after-this-event>",
  "caughtUp": true,
  "headPosition": 64,
  "earliestPosition": 1
}
```

`position` says which committed change produced the event. `stateAt` says when the current object was composed; it can be later than the event position. `changed` names affected outputs, not old and new values. `cause` identifies the kind of work; it is not the actor's identity. A deletion omits `object` and `stateAt` and has null `code` and `name`.

With `payload=identity`, the event retains identity, change, cause and affected output names but omits `object` and `stateAt`. Save `cursor` after durably processing the page, then use it instead of `after` to continue, including within a position. `caughtUp` applies to derived events; more can arrive later. Do not treat a short filtered page as caught up without checking the flag.

## The actual webhook request shape

A subscription is separate from that declaration. Choose the workspace, consumer API, event names, filters, receiver, payload, format and request batching. For this example, take an active subscription to `stops-changed` with **identity** payload, RDM JSON format and one event per request. Its [management operations](/docs/api/?api=management#tag/consumer%20subscriptions) require a management token with Integration administration, even though the receiver gets consumer events.

Here is a complete delivery body in the compact form the sender signs. The IDs and timestamp are illustrative. The demonstration signing secret is the literal text `guide-example-only`; it is a public example, not a credential for any instance. The engine's production delivery encoder and signer generated this example header and body. There is no trailing newline in the signed body.

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
    if not timestamp_text.isascii() or abs(now - timestamp) > 300:
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
        if candidate.strip().isascii() and candidate.strip().startswith("sha256=")
    )
```

For the sample request, pass its timestamp as the test clock to reproduce verification. A live receiver uses the actual current time and must reject this dated sample. During rotation, run verification with each currently accepted secret; either an accepted current or overlap key can authenticate the request. Never decode the displayed hexadecimal secret or reformat the JSON before signing: use the secret as issued and the request's raw bytes.

After verification, durably store or queue events and deduplicate by event ID, then acknowledge within ten seconds with a 2xx. If storage fails, do not acknowledge acceptance. A slow acknowledgment can cause a retry even after local processing succeeded.

## If the subscription chooses CloudEvents

With CloudEvents format and one event per request, the same identity event is wrapped as follows. The content type is `application/cloudevents+json; charset=utf-8`; its signature covers the bytes of this CloudEvent, not the RDM JSON envelope above. The displayed indentation is for reading, so do not reuse the previous signature for it:

```json
{
  "specversion": "1.0",
  "id": "8b6b294b-ff1a-4bb8-898c-a2e412e64f71",
  "source": "/api/consumer/stops/v1/events?workspace=graubuenden",
  "type": "rdm.stops-changed.updated",
  "subject": "Stop/8d90eede-23cf-47c1-8dac-cb37956f5fd5",
  "time": "2026-11-02T08:00:00+00:00",
  "datacontenttype": "application/json",
  "rdmsubscription": "a7447804-c8c0-4e13-9a7f-117e7ec6ba15",
  "data": {
    "eventId": "8b6b294b-ff1a-4bb8-898c-a2e412e64f71",
    "position": 64,
    "occurredAt": "2026-11-02T08:00:00+00:00",
    "event": "stops-changed",
    "change": "updated",
    "contractVersion": 1,
    "objectType": "Stop",
    "id": "8d90eede-23cf-47c1-8dac-cb37956f5fd5",
    "code": "ch:1:sloid:5173",
    "name": "Tschamut-Selva",
    "changed": [
      "name"
    ],
    "cause": {
      "kind": "user"
    }
  }
}
```

With batching enabled the body is an array of these CloudEvents and the content type is `application/cloudevents-batch+json; charset=utf-8`, even if only one event is ready. `data` remains the same consumer event. The subscription ID is an extension attribute; the event type combines `rdm.`, the declared event name and its change.

Follow [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for setup, testing, rotation and recovery in order. The [Events reference](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events) documents the actual contract on your instance.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Event occurrence, delivery IDs and the verification key are illustrative.*

## Rules for event declarations

An event lists at least one exposed object type and at least one of `created`, `updated` and `deleted`, without duplicates. Custom event keys are unique lowercase URL keys. `watch.fields` uses output names, including declared parent, path or hierarchy outputs and `objectType`; `watch.related` uses related-block names. A watch must name at least one output or block, without repeats, and requires updated among the changes. No watch means every output is watched. Watches restrict updates; they do not suppress creation or deletion.

Reducing notification coverage is breaking: removing an event, type, change kind or watched output, or adding a limiting watch, needs a higher contract version. Adding coverage or dropping a watch is compatible. The `stops-changed` example above is a custom event, not the automatically named event for its type.

## Subscription defaults and lifecycle

The defaults are `maxEventsPerBatch: 1`, `payload: "full"` and `format: "rdm"`. Batching, payload and format are independent choices. Creation starts after the workspace’s committed feed head, so it receives future changes even if event derivation is behind. To catch up from a retained earlier position, supply `startAfter`, for example a publication’s `eventSequence`; expired or future positions are refused. Omitted workspace selects and stores the deployment’s default workspace at creation.

Subscriptions have active or suspended status and use optimistic concurrency for edits. The creator appears as `owner` (kind, ID and name); older entries can have a null owner. The list can filter by owner. Ownership itself grants no permission: Integration administration in that workspace is required. The [subscription reference](/docs/api/?api=management#tag/consumer%20subscriptions) describes creation, reads, edits, suspend, resume, rotation and deletion.

On activation, a removed API, event or filter suspends delivery with `MODEL_CHANGED` and findings; a raised contract version suspends it with `CONTRACT_VERSION_CHANGED`. It does not silently rewrite the subscription. Retirement produces `WORKSPACE_RETIRED`. A stale filter is checked before sending, including before its deletions; fix the filter and resume to receive unacknowledged events. Resume validates the declaration and accepts the currently served version. Treat that as a contract changeover with the receiver.

A signing secret is generated from 32 random bytes, shown once as `signingSecret`, and stored sealed with AES-256-GCM under the deployment’s `SECRETS_ENCRYPTION_KEY`. Obtain a new secret through rotation if it is lost. Operators manage the sealing key; it is separate from the receiver’s HMAC secret.

## Delivery boundaries

The fixed body limit is 1,048,576 bytes in the selected format, except that one larger event is sent alone. [Capabilities](/docs/api/?api=management#tag/model) reports this as `consumerSubscriptions.delivery.maxBytes` and the event maximum as `maxEventsPerBatch`. Check the receiver and reverse proxy limits: nginx’s default `client_max_body_size` is exactly 1 MiB and can reject that single-event exception.

HTTPS accepts any host and port, including private networks. Plain HTTP accepts only the named loopback hosts `localhost`, `127.0.0.1` and `::1`. The dispatcher resolves the host on every attempt and connects to the checked address. It refuses IPv4 link-local `169.254.0.0/16`, IPv6 link-local `fe80::/10` and loopback addresses reached through a non-loopback URL host. It uses the system TLS trust store and no outbound proxy. There is no destination-host allowlist.

Retries run for 24 hours from the first failure, rather than from the most recent attempt. Success resets the failure count. Inspect `delivery.pending` for attempts, first failure, last error and next attempt. An edit or resume drops the pending batch and attempts delivery again from the unacknowledged position, using the revised configuration.

CloudEvents uses structured JSON only, with no binary mode, `dataschema`, OPTIONS webhook handshake or bearer-token handshake. HMAC signs every delivery. The `source` is a relative URI for the API and workspace; resolve it against your instance if an absolute address is needed. The pull feed always uses RDM JSON.

## Feed defaults and version changes

Full event pages default to 100 objects, with a maximum of 100. Identity pages default to 500 events, with a maximum of 1,000. Use `after` or `cursor`, never both. Filtering scans at most ten pages of underlying events per response, which explains a short page that is not caught up.

Derivation happens after commit and can lag writes. `headPosition` and `caughtUp` describe derived events, not every committed write. Each entry is evaluated under the model release used for the original write. A feed at the currently served contract version includes older events too: each event retains the `contractVersion` that derived it, while a full object is composed under the version served now. Do not treat that full object as a historical copy.

Retention is controlled by `FEED_RETENTION_DAYS` (default 30), bounded by the active publication’s position so its baseline remains usable. With no active baseline publication, events do not expire. Save the lasting cursor after durable processing, including on empty filtered pages, and reconcile from the indicated baseline after `410 EVENTS_EXPIRED`.

Delivery progress changes neither the subscription’s `version` nor `updatedAt`; suspension does. Do not poll the edit version as a delivery checkpoint. The delivery list has one row per event of a request, sharing the request outcome. Request details show the latest sent body, byte count and attempts with timing, status and at most 4 KiB of the receiver’s response. Before the first attempt there is no sent body to resend. Use the [delivery operations](/docs/api/?api=management#tag/consumer%20subscriptions) to diagnose these states.
