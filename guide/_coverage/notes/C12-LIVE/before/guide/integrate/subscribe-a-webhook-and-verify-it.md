---
title: Subscribe a webhook and verify it
description: Prepare a receiver, verify signatures and recover delivery without missing changes.
reader: integrator
---

Use a webhook when refiroo should send declared events to your endpoint. Read [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) for payload timing, ordering and retry rules.

1. Confirm with the operator that webhook subscriptions are enabled. Obtain Integration administration in the intended workspace. Inspect the contract's Events operation and choose the events and filters. For the reference model, inspect [stops Events](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events). Do not assume another model has that event.
2. Prepare an HTTPS receiver that retains raw request bytes, verifies signatures before handling data and acknowledges durably accepted work within 10 seconds. Make event handling repeatable by event ID. Accept both selected formats and batch sizes only as agreed; allow an oversized single object beyond the normal 1 MiB batch boundary.
3. Create the subscription through the [subscription operation](/docs/api/?api=management#tag/consumer%20subscriptions), selecting the workspace, contract, event names, receiver, filters, representation and batching. Save the one-time signing secret directly to protected receiver configuration. For browser setup, open **Settings › Integration › Webhooks**. See [Clients for other systems](/docs/administer/clients/) for client access.
4. Verify a delivery using its timestamp plus a dot plus the raw body bytes, with HMAC-SHA256 keyed by the secret exactly as issued. Reject stale timestamps and compare each comma-separated signature in constant time. Accept if one supported signature verifies. Return a 2xx after storing the work safely.
5. Inspect the [delivery log](/docs/api/?api=management#tag/consumer%20subscriptions). Check successful acknowledgment and your local deduplication record. A timeout can cause repeat delivery even if your receiver processed the first request. Automatic retries can contain newer object values for the same event.
6. Rotate the signing key with an overlap, install the new secret in the receiver, verify it works and let the old key end. Keep multi-signature support: it is needed during rotation and on retries.
7. If delivery pauses, read its reason before resuming. Correct the receiver or filter and continue from the first unacknowledged event. If events expired, reset first, then rebuild the baseline from a publication and reconcile events received during that read. Never reset and assume no data was missed.

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

Inspect the delivery log and your receiver's stored event ID together. If processing failed after acknowledgment, use a deliberate manual resend and account for its same event ID. If the sender is retrying, repair the receiver and allow the ordered retry to finish. If the subscription has expired events, reset before rebuilding its baseline; a manual resend does not repair its ordinary checkpoint.
