---
title: Subscribe a webhook and verify it
description: Prepare a receiver, verify signatures and recover delivery without missing changes.
reader: integrator
---

Use a webhook when refiroo should send declared events to your endpoint. Read [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) for payload timing, ordering and retry rules.

1. Confirm with the operator that webhook subscriptions are enabled. Obtain Integration administration in the intended workspace. Inspect the contract's Events operation and choose the events and filters. For the reference model, inspect [stops Events](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events). Do not assume another model has that event.
2. Prepare an HTTPS receiver that retains raw request bytes, verifies signatures before handling data and acknowledges durably accepted work within 10 seconds. Make event handling repeatable by event ID. Accept both selected formats and batch sizes only as agreed; allow an oversized single object beyond the normal 1 MiB batch boundary.
3. Create the subscription through the [subscription operation](/docs/api/?api=management#tag/consumer%20subscriptions), selecting the workspace, contract, event names, receiver, filters, representation and batching. Supply `contractVersion` to select a served earlier version; omitting it selects the current version. Read [Earlier-contract subscriptions](/docs/integrate/consumer-events-and-webhooks/#keep-a-receiver-on-an-earlier-contract) before choosing. Save the one-time signing secret directly to protected receiver configuration. For browser setup, open **Settings › Integration › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
4. Verify a delivery using its timestamp plus a dot plus the raw body bytes, with HMAC-SHA256 keyed by the secret exactly as issued. Reject stale timestamps and compare each comma-separated signature in constant time. Accept if one supported signature verifies. Return a 2xx after storing the work safely.
5. Inspect the [delivery log](/docs/api/?api=management#tag/consumer%20subscriptions). Check successful acknowledgment and your local deduplication record. A timeout can cause repeat delivery even if your receiver processed the first request. Automatic retries can contain newer object values for the same event.
6. Rotate the signing key with an overlap, install the new secret in the receiver, verify it works and let the old key end. Keep multi-signature support: it is needed during rotation and on retries.
7. If delivery pauses, read its reason before resuming. Correct the receiver or filter and continue from the first unacknowledged event. If events expired, follow the recovery choices below. Reset skips the undelivered range; a publication older than the reset is insufficient on its own.

Manual resend repeats a stored event in its original format, with the same event ID and a manual-redelivery indication. It is one attempt and does not repair the ordinary delivery checkpoint. Use it deliberately when testing or recovering receiver processing, and retain ordinary deduplication for automatic retries.

## Use the reference event end to end

The `stops` declaration watches code, name and validity outputs through `stops-changed`. Read its [declaration and complete event page](/docs/integrate/consumer-events-and-webhooks/#a-declaration-and-the-event-it-exposes). A height-only edit does not exercise this watched event; a name change does. Use an intentional change in a suitable workspace when testing your receiver.

With a management token holding Integration administration in that workspace, create an identity-payload subscription:

```http
POST /api/v1/consumer-subscriptions HTTP/1.1
Host: <instance>
Authorization: Bearer <management-token>
Content-Type: application/json
Accept: application/json

{
  "name": "Stop mirror",
  "consumerApi": "stops",
  "workspaceKey": "graubuenden",
  "events": ["stops-changed"],
  "url": "https://receiver.example/refiroo-events",
  "payload": "identity",
  "format": "rdm",
  "maxEventsPerBatch": 1
}
```

Replace the reserved example receiver address with your own HTTPS endpoint. The successful creation returns 201 with the subscription and a one-time `signingSecret`. Store that exact secret in the receiver; do not log it. Retain the subscription's ID, version and acknowledgment position. Consumer grants for reading data and Integration administration for subscriptions are separate permissions.

When a matching change commits, the receiver gets the [complete signed request shown here](/docs/integrate/consumer-events-and-webhooks/#the-actual-webhook-request-shape). Its RDM envelope holds `deliveryId`, `subscriptionId`, the API, version, workspace and an `events` array. Identity payloads carry enough identity to fetch current data but omit the full object. Select `payload: full` if your receiver needs the current shared object in the event instead.

Apply the [verification function](/docs/integrate/consumer-events-and-webhooks/#verify-the-bytes-before-decoding-json) to raw bytes before JSON decoding. The page's demonstration key and dated timestamp reproduce the sample signature only; the real receiver uses its actual secret and current time. Confirm that changing a single body byte fails verification and that an old timestamp is refused. Then durably queue the verified event, make processing repeatable by event ID and acknowledge with a 2xx.

Inspect the delivery log and your receiver's stored event ID together. If processing failed after acknowledgment, use a deliberate manual resend and account for its same event ID. If the sender is retrying, repair the receiver and allow the ordered retry to finish. If the subscription has expired events, rebuild its baseline using the sequence below; a manual resend does not repair its ordinary checkpoint.

## Recover an expired subscription

Choose one recovery boundary explicitly. Keep deliveries durably queued while rebuilding a baseline, and make replay safe by event ID.

- **Keep a retained publication as the baseline.** Select a compatible publication with a non-null `eventSequence`. Create a replacement subscription with `startAfter` equal to that sequence, rather than accepting its default of today's head. If that position is still available, load the publication's lists and then reconcile queued events. Retire the old subscription after the replacement works. An expired position is refused: choose another usable baseline, not an arbitrary later number.
- **Reset the existing subscription.** Read its current version and resume with reset. Record its new acknowledgment position, then arrange a fresh baseline at or after that position: for example, a new publication made after the reset, or a live export taken after it by a suitably authorised management client. Load that baseline and reconcile the queued events. Do not load an older publication and discard its intervening changes.

The [load-and-follow sequence](/docs/guide/integrate/load-then-follow-changes/) explains baseline checkpoints. When replaying queued notifications after loading the baseline, prefer current-object reads for creates and updates so an older notification cannot replace newer baseline values. Deletions remove local objects. A filtered mirror also needs reconciliation of surviving objects that left its scope.

## Change or retire the connection

To move the receiver, deploy its secret and durable queue/deduplication state at the new endpoint, then edit the URL with the subscription's current version. An edit restarts any pending delivery from the unacknowledged point. Verify acknowledgments at the new receiver before decommissioning the old one; allow for a request already in flight.

A subscription retains its accepted contract while that version remains served. A model release
that stops it can suspend delivery with `CONTRACT_VERSION_CHANGED`; missing events or filters
produce `MODEL_CHANGED` findings instead. Read the replacement document and update the receiver
before resuming on the current version. A sunset date alone does not pause delivery.

Suspend for a temporary stop. Resume without reset after fixing the cause if its unacknowledged range remains available. To retire it, save the delivery records you need, then delete it with the current version through the [subscription operations](/docs/api/?api=management#tag/consumer%20subscriptions). Deletion also removes the delivery log; it does not reverse work already accepted by the receiver. Remove unused receiver secrets and local schedules once the connection is retired.
