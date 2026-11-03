---
title: Webhook delivery
description: Enable event delivery, diagnose retries, and retain enough history for recovery.
reader: operator
---

Enable `CONSUMER_SUBSCRIPTIONS_ENABLED=true` in the engine environment and recreate the container
to serve subscription routes and run delivery. The default is `false`. Subscriptions are deployment
state, separate from model releases. Switching delivery off removes all subscription routes, including reads, and stops the dispatcher.
It preserves stored subscriptions, but their undelivered events can expire while it is off.
Turning it back on resumes delivery subject to subscription validation and event retention;
expired positions suspend delivery as `EVENTS_EXPIRED`. Repeated requests to an absent route do
not turn it on. Check Deployment, enable the setting on the intended instance and recreate it.

An administrator or integration owner manages subscriptions on **Settings › Integration › Webhooks**.
Use [Subscribe a webhook and verify it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/) for the integration sequence and the
[API reference](/docs/api) for operations. Receivers need a consumer API that declares events.

## Find the subscription's state

Subscription management requires Integration administration for its workspace; an Operator role
alone does not grant it. On **Settings › Integration › Webhooks**, open the subscription by name.
Check the address, consumer API, workspace, selected events, filter tags and request format against
the receiver's configuration. The **Configuration** tab shows its state, suspension reason and
recovery advice. Authorised owners can edit, suspend, resume, rotate its key or delete it there.
Read current state before an edit: a version conflict requires reloading and reviewing the other
administrator's change.

A workspace with subscriptions cannot be deleted. Its refusal identifies the subscriptions to
review; delete unneeded subscriptions or keep the workspace. Retiring a workspace suspends its
subscriptions instead. Before resuming, correct the recorded cause: resume checks the model,
contract, filter and retained position again.

## Network and receiver requirements

Allow direct outbound HTTPS from the engine to receivers. A redirect is not followed: configure
the final URL. Private addresses are permitted; there is no host allowlist. Plain HTTP is accepted
only for a loopback host in development. Every attempt resolves DNS again and refuses link-local
addresses, and loopback addresses unless the URL itself names a loopback host.
Certificates must verify against the system trust store. For an internal CA, supply a bundle with
`SSL_CERT_FILE`. Delivery does not use an outbound proxy.

A receiver must durably accept the POST and return 2xx within ten seconds. Allow bodies up to 1 MiB
and larger for an unusually large single object. Verify the timestamp and `RDM-Signature`, and
deduplicate events by `eventId`: delivery is at least once. During key rotation, accept any valid
signature in the comma-separated header. Signing secrets must never be committed or logged.
[Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) explains the protocol.

## Retries and suspensions

Requests to one subscription stay ordered. A failed batch blocks later batches and keeps its events
and delivery ID while retrying after 10 seconds, 30 seconds, 1, 2, 5, 10 and 30 minutes, then hourly,
with 20% jitter. After 24 hours from its first failure, the subscription is suspended.
Inspect its pending attempt, last error and next-attempt time before restarting anything.

| Suspension | Recovery |
| --- | --- |
| `DELIVERY_FAILED` | Fix the receiver or URL, then resume from the first unacknowledged event. Editing the URL retries immediately. |
| `FILTER_MATCHES_NOTHING` | Fix the filter and resume. |
| `EVENTS_EXPIRED` | Resume with reset first, then re-sync the receiver from the publication named in the details. |
| `MODEL_CHANGED` | Review what the activated model removed; correct the subscription before resuming. |
| `CONTRACT_VERSION_CHANGED` | Update the receiver for the selected consumer contract, then resume. |
| `WORKSPACE_RETIRED` | Resolve the workspace's retired state before resuming delivery. |

Events derive from the change feed in the background, normally checked once per second. They expire
with `FEED_RETENTION_DAYS`, default 30, and are cleaned hourly. A consumer's `headPosition` is the
derived event head, which can lag the workspace feed. Several processes divide derivation by
workspace and delivery by a 60-second subscription lease.

## Retain delivery evidence

`CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` defaults to 7. The delivery log keeps request bodies up to
1 MiB and response excerpts up to 4 KiB, with attempts and durations. Retried or awaiting-resume
batches can remain longer. Expiry runs at most hourly. Inspect **Deliveries** on the webhook's page. Choose **Status**: **All**, **Queued**, **Sending**,
**Retrying**, **Succeeded**, **Failed** or **Dropped**, and use **Refresh** to read again.
The table shows **Event ID**, **Event**, **Object ID**, **Status**, **Attempts**, **Response** and
**Sent**. Open an event ID for the request as sent, each attempt and its response excerpt.
**No delivery has this status** can mean the filter is too narrow; **Nothing delivered yet** means
there are no retained deliveries to show, not proof the receiver never received data.

**Resend** sends the selected event again; an already delivered event asks **Resend a delivered
event?** before **Resend event**. A failed event can be resent directly. An event never sent has
nothing to resend and the control is disabled. A manual resend is marked with `RDM-Redelivery`;
the receiver must still deduplicate by event ID. It does not repair the subscription's normal
position or replace resolving its suspension. Operations summarizes failing and suspended subscriptions. Budget database space for these payloads
and restrict access to logs containing reference data. Your delivery capacity is **not measured**.

Rotate a subscription key when it leaks or policy requires it. The default overlap is 24 hours,
up to seven days; **Stop it now** selects zero, which ends the old key at the next delivery. Give the receiver the new key before
the overlap ends. This is separate from [resealing the installation's secrets](/docs/run/secrets-and-keys/).

Filters use a record's state at delivery time. A record leaving a filtered scope is not delivered
as a removal; deletions are always delivered. A receiver needing exact scope membership should
subscribe by type and narrow locally, or periodically reconcile its list.

The subscription defaults to one event per request. For a bulk workload, choose a larger batch
(up to 1,000 events); requests stop at 1 MiB except that a single larger event is sent alone.
A slow receiver adds its response time to each sequential request. Increase batching before
assuming another engine process speeds up one subscription; several processes share its lease
and preserve its order.

## Enable and check delivery without creating duplicate loads

Before enabling delivery, have an Integration administrator for the workspace, a consumer API with
events, a working HTTPS receiver, its signing-secret storage and enough retained feed history for
the expected outage window. The operator needs Docker and Operations access. CPU, database sizing
and delivery throughput for that receiver are **not measured** by this guide.

1. Set the capability in the private environment and recreate the engine:

   ```dotenv
   CONSUMER_SUBSCRIPTIONS_ENABLED=true
   ```

   ```bash
   docker compose up -d engine
   curl -i https://refiroo.example.org/health
   docker compose logs --tail=100 engine
   ```

   Expect readiness 200 and `webhookDispatcher` Running on Operations once a model is servable.
   No subscription means there is nothing to deliver; a running dispatcher alone is not a test
   of the receiver.
2. Ask the Integration administrator to review the subscription's URL, workspace, contract version,
   filter and retained position. Coordinate a harmless reviewed change with the data owner, then
   check the event and successful attempt in Deliveries and the receiver's durable event log.
3. Compare delivery ID, event ID and response status across both sides. Confirm that a retry of an
   already stored event is acknowledged without applying it again. Verification/deduplication is
   the receiver's responsibility; a successful HTTP answer does not prove its downstream update.
4. If delivery is failing, inspect the same pending batch and fix its cause. Do not delete and
   recreate the subscription merely to clear its state: that can abandon its recorded position.

All three delivery-related environment settings are non-secret and need engine recreation:
`CONSUMER_SUBSCRIPTIONS_ENABLED`, `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` and `FEED_RETENTION_DAYS`.
The subscription's signing secret is secret database state sealed with the installation key.

## Recover a suspension in order

For `DELIVERY_FAILED`, repair the receiver's certificate, body limit, authentication or response
time, then resume the existing subscription. Inspect the first resumed delivery and the receiver
before declaring the backlog recovered. Later events wait behind the failed batch by design.
For `FILTER_MATCHES_NOTHING`, correct the saved filter, then resume and check its scope.

For `EVENTS_EXPIRED`, coordinate a full receiver re-sync with the integrator. Reset the subscription
first, then load the publication/list named by the refusal and reconcile the receiver. Reset starts
after the current head; it does not replay expired events. A receiver loaded before reset could
miss the interval between loading and reset. Preserve the old receiver state or a rollback copy
until reconciliation and later deliveries have been checked.

After `MODEL_CHANGED` or `CONTRACT_VERSION_CHANGED`, involve the model administrator and receiver
owner before resuming. After `WORKSPACE_RETIRED`, resolve the workspace's retirement intentionally;
repeated engine restarts do not change that state. Manual **Resend** is for a retained event and
does not move the normal subscription position or repair a suspension.

To pause the entire capability, restore `CONSUMER_SUBSCRIPTIONS_ENABLED=false` and recreate.
Subscriptions stay stored, while their events continue to age. To undo that pause, enable it again,
then inspect each subscription for expiry and validation failures. This is not an indefinite queue
retention switch. For a single receiver pause, use the subscription's suspend operation through
its administrator, retaining its identity and position.
