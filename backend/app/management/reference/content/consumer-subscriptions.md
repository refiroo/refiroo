# consumer subscriptions

A webhook subscription has the engine post a consumer API's events, or a workspace's change-set events, to a receiver's URL as they happen. The engine signs each request, sends them in event order, one at a time, and retries a failed one. Delivery is at least once: a receiver that sees a delivery ID again has seen that request before.

1. Subscribe with `POST /api/v1/consumer-subscriptions` and keep `signingSecret`.
2. In the receiver, verify `RDM-Signature` (see `signingSecret`) and answer `2xx`.
3. Follow `GET .../deliveries`; `POST .../resend` repeats one event.
4. A subscription that cannot continue is suspended with a reason: correct it, then `POST .../resume`.

A request carries up to `maxEventsPerBatch` events. `pending` shows a failing request's retry schedule; `GET /api/v1/capabilities` the limits.

## POST /api/v1/consumer-subscriptions

Title: Create a subscription

Subscribes `url` to events in one workspace and answers the subscription with its `signingSecret`, which no later read returns. Delivery starts after the workspace's current feed head, or after `startAfter`: earlier events are not sent. The consumer API, its events, each filter value, the URL and the workspace are checked, and the first problem is answered.

### Errors

- 400 INVALID_WEBHOOK_URL: not https, has user information or a fragment, or not public
- 400 CONSUMER_API_NOT_FOUND: the active release has no such consumer API
- 400 CONTRACT_VERSION_NOT_FOUND: the model no longer serves that version
- 400 EVENTS_NOT_DECLARED: the consumer API declares no events
- 400 UNKNOWN_EVENT: an event the consumer API does not declare
- 400 UNKNOWN_PARAMETER: a filter names no parameter of the consumer API
- 400 UNKNOWN_OBJECT_TYPE: a type filter names a type the consumer API does not expose
- 400 PARAMETER_NOT_SUPPORTED: a filter names something that is not a filter
- 400 FILTER_MATCHES_NOTHING: no record matches a filter value
- 403 FORBIDDEN: needs Integration administration in the workspace
- 404 WORKSPACE_NOT_FOUND: no active workspace has this key
- 409 EVENT_POSITION_AHEAD: `startAfter` is beyond the feed's head
- 410 EVENTS_EXPIRED: `startAfter` is older than the feed keeps
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or does not fit the `source`

## GET /api/v1/consumer-subscriptions

Title: List subscriptions

Lists subscriptions, newest first, in the workspaces where the caller holds Integration administration. Narrow the list by consumer API, workspace, status or the person or client that created the subscription.

### Parameters

- consumerApi: Only subscriptions to this consumer API's events.
- workspaceKey: Only subscriptions in this workspace.
- status: Only `active` or `suspended` subscriptions.
- ownerId: Only subscriptions created by this person or client, by ID.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Integration administration in some workspace
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/consumer-subscriptions/{subscription_id}

Title: Read a subscription

Reads one subscription: its state, the request being retried while one fails, and when a request was last delivered. Read it before changing it, for its `version`.

### Parameters

- subscription_id: The subscription's ID.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID

## PATCH /api/v1/consumer-subscriptions/{subscription_id}

Title: Edit a subscription

Changes the name, events, filters, URL, batch size, payload or format, checked as a create is; send only what changes, with `expectedVersion`. The consumer API, workspace and source cannot change: create another subscription. Anything but a rename drops the request being retried, so the next attempt follows at once with the edit, from the first event not acknowledged. A suspended subscription stays suspended.

### Parameters

- subscription_id: The subscription's ID.

### Errors

- 400 INVALID_WEBHOOK_URL: not https, has user information or a fragment, or not public
- 400 CONSUMER_API_NOT_FOUND: the active release no longer has the consumer API
- 400 EVENTS_NOT_DECLARED: the consumer API declares no events
- 400 UNKNOWN_EVENT: an event the source does not declare
- 400 UNKNOWN_PARAMETER: a filter names no parameter of the consumer API
- 400 UNKNOWN_OBJECT_TYPE: a type filter names a type the consumer API does not expose
- 400 PARAMETER_NOT_SUPPORTED: a filter names something that is not a filter
- 400 FILTER_MATCHES_NOTHING: no record matches a filter value
- 400 NOT_SUPPORTED_BY_SOURCE: `filters` or `payload` on a workspace-events subscription
- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not the subscription's version
- 422 REQUEST_VALIDATION_ERROR: nothing to change, or a field is invalid

## POST /api/v1/consumer-subscriptions/{subscription_id}/suspend

Title: Suspend a subscription

Stops delivery, with the reason `SUSPENDED_BY_USER`, until the subscription is resumed. Events wait in the feed meanwhile; resuming after they expired answers `409 EVENTS_EXPIRED`.

### Parameters

- subscription_id: The subscription's ID.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 409 SUBSCRIPTION_ALREADY_SUSPENDED: it is suspended, for the reason in `details.reason`
- 409 VERSION_CONFLICT: `expectedVersion` is not the subscription's version
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing

## POST /api/v1/consumer-subscriptions/{subscription_id}/resume

Title: Resume a subscription

Continues a suspended subscription, whatever the reason, from the first event not acknowledged, at once. It is checked as a create is, a failing request's retries are cleared, and the contract version the model serves now becomes the accepted one. `reset: true` starts after the workspace's current feed head instead; what happened meanwhile is not sent, so reload the receiver from current data.

### Parameters

- subscription_id: The subscription's ID.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 409 SUBSCRIPTION_NOT_SUSPENDED: it is active
- 409 SUBSCRIPTION_NEEDS_EDIT: it fails the create checks; `details.errors` lists them
- 409 EVENTS_EXPIRED: events it had not acknowledged expired; resume with `reset`
- 409 VERSION_CONFLICT: `expectedVersion` is not the subscription's version
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing

## POST /api/v1/consumer-subscriptions/{subscription_id}/rotate-secret

Title: Rotate the signing key

Makes a new signing key and answers it once in `signingSecret`. For `overlapHours` every request is signed with both keys, so the receiver can switch without missing one; `0` ends the old key at once, for a leaked key. It works on a suspended subscription and does not interrupt delivery.

### Parameters

- subscription_id: The subscription's ID.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not the subscription's version
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## DELETE /api/v1/consumer-subscriptions/{subscription_id}

Title: Delete a subscription

Deletes a subscription and its delivery log. Delivery stops, a request being retried included, and nothing undoes it; to pause, suspend the subscription instead.

### Parameters

- subscription_id: The subscription's ID.
- expectedVersion: The subscription's `version`.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not the subscription's version
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing

## GET /api/v1/consumer-subscriptions/{subscription_id}/deliveries

Title: List the deliveries

Lists what a subscription delivered or is delivering, newest first, one row per event; the events of one request share its status and attempts. Rows are kept for the log retention that `GET /api/v1/capabilities` reports, and longer while their request is being retried.

### Parameters

- subscription_id: The subscription's ID.
- status: Only requests in this status.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}

Title: Read a delivery

Reads one request by its delivery ID, the `RDM-Delivery-Id` header the receiver saw: its events, the body of its latest attempt as the receiver got it, and every attempt with its answer. Use it to see why a receiver refused a request.

### Parameters

- subscription_id: The subscription's ID.
- delivery_id: The request's delivery ID.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 404 DELIVERY_NOT_FOUND: the log of this subscription has no such request

## POST /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}/resend

Title: Resend an event

Sends one event of a delivered request again, alone in a new request with a new delivery ID, the same `eventId`, the format it was sent in and the header `RDM-Redelivery: manual`. One attempt is made during the call and none is retried, on a suspended subscription too. The answer is the new request, whatever the receiver said; the subscription's position does not move.

### Parameters

- subscription_id: The subscription's ID.
- delivery_id: The delivery ID of the request that carried the event.

### Errors

- 403 FORBIDDEN: needs Integration administration in its workspace
- 404 SUBSCRIPTION_NOT_FOUND: no subscription has this ID
- 404 DELIVERY_NOT_FOUND: the log of this subscription has no such request
- 404 EVENT_NOT_IN_DELIVERY: that request did not carry the event
- 409 DELIVERY_NOT_SENT: the request was never sent
- 422 REQUEST_VALIDATION_ERROR: `eventId` is missing

## Schemas

### ConsumerSubscriptionCreate

A subscription to the events of a consumer API or of a workspace's change sets, delivered to a URL.

- name: What you call the subscription, 1 to 200 characters; it need not be unique.
- source: `consumerApi` (the default): the record events of a consumer API. `workspace`: the change-set events `change-set.submitted`, `change-set.approved` and `change-set.sent-back`; it takes no `consumerApi`, `contractVersion`, `filters` or `payload`.
- consumerApi: The consumer API's key; required for the source `consumerApi`.
- contractVersion: The contract version to receive events in, one the model still serves; the version served now when omitted.
- workspaceKey: The workspace whose events are sent; the default workspace when omitted, stored as resolved.
- events: 1 to 100 events to send, as the consumer API declares them; a workspace subscription names the change-set events above.
- filters: Keep the events of some records: a parameter of the consumer API with one value or a list, each value matching a record now.
- url: Where requests are posted: `https`, or `http` to `localhost`, `127.0.0.1` or `::1` alone; at most 2,048 characters, with no user information or fragment.
- maxEventsPerBatch: 1 to 1,000, 1 by default. A request carries at most this many events and 1 MiB of body; an event over 1 MiB is sent alone.
- payload: `full` (the default): each event carries its `object`. `identity`: the `object` is left out.
- format: `rdm` (the default): a JSON envelope whose `events` holds the batch. `cloudevents`: CloudEvents 1.0, one structured event per request when `maxEventsPerBatch` is 1, otherwise a batched array.
- startAfter: A feed position still kept, to start after; omit it to start after the workspace's current head.

### ConsumerSubscriptionUpdate

The changes to a subscription, with the version read; at least one field besides `expectedVersion`.

- expectedVersion: The subscription's `version`.
- name: A new name; a rename alone leaves a request being retried as it is.
- events: The events to send, replacing the list.
- filters: The filters, replacing them; an empty object removes them.
- url: A new address, with the rules of a create.
- maxEventsPerBatch: 1 to 1,000: at most this many events per request.
- payload: `full` or `identity`, as when creating.
- format: `rdm` or `cloudevents`, as when creating.

### ConsumerSubscriptionVersion

The version the caller read, claimed by a change.

- expectedVersion: The subscription's `version`.

### ConsumerSubscriptionResume

Resumes a suspended subscription, from where it stopped or after the workspace's current feed head.

- expectedVersion: The subscription's `version`.
- reset: `true` starts after the workspace's current feed head and skips what happened since; `false` (the default) continues from the first event not acknowledged.

### ConsumerSubscriptionRotate

Makes a new signing key; the previous one keeps signing beside it for `overlapHours`.

- expectedVersion: The subscription's `version`.
- overlapHours: 0 to 168, 24 by default: how long the previous key signs beside the new one; `0` ends it at once.

### SubscriptionResponse

A subscription, its state and how delivery is going.

- id: The subscription's ID.
- name: The name it was given.
- source: `consumerApi` or `workspace`, as created.
- consumerApi: The consumer API's key; null for the source `workspace`.
- contractVersion: The contract version the subscription was accepted under; 1 for the source `workspace`.
- workspaceKey: The workspace whose events are sent.
- events: The events it sends.
- filters: The filters, each parameter with a list of values.
- url: Where requests are posted.
- maxEventsPerBatch: The most events one request carries.
- payload: `full` or `identity`.
- format: `rdm` or `cloudevents`.
- status: `active`, or `suspended` with the reason in `suspension`.
- suspension: Why it is suspended; null while active.
- acknowledgedThrough: The feed position of the last event acknowledged; delivery continues after it.
- delivery: How delivery is going; it changes neither `version` nor `updatedAt`.
- signingKeyCreatedAt: When the current signing key was made.
- previousSigningKeyExpiresAt: When the previous key stops signing, while a rotation's overlap runs; null otherwise.
- signingSecret: The signing key, `rdmwh_` and 43 characters: answered by create and rotate only, never by a read. A request is genuine when `sha256=` and the hex HMAC-SHA256 of `<RDM-Timestamp>.<body>`, with this key as the key and the raw body bytes, is one of the comma-separated values of `RDM-Signature`; two values appear during an overlap.
- version: Send it as `expectedVersion` to change or delete the subscription.
- createdAt: When it was created.
- updatedAt: When it was last changed.
- owner: The person or client that created it; null for one created before owners were recorded. Owning gives no right of its own.

### SubscriptionPage

Subscriptions, newest first.

### SubscriptionSuspension

Why a subscription is suspended and what it needs to continue.

- reason: `SUSPENDED_BY_USER`: suspended through the API. `MODEL_CHANGED`: a model release no longer declares the consumer API, an event or a filter parameter. `CONTRACT_VERSION_CHANGED`: the model serves a higher contract version than the subscription accepted. `WORKSPACE_RETIRED`: the workspace was retired. `DELIVERY_FAILED`: a request failed for 24 hours. `FILTER_MATCHES_NOTHING`: a filter value matches no record any more. `EVENTS_EXPIRED`: events not yet delivered passed the feed's retention.
- message: What happened, for a person.
- details: By reason: `MODEL_CHANGED` `errors` (each finding's `code`, `message` and `pointer`); `CONTRACT_VERSION_CHANGED` `contractVersion` and `servedContractVersion`; `WORKSPACE_RETIRED` `workspaceKey`; `DELIVERY_FAILED` `deliveryId`, `attempts`, `failingSince` and `lastError`; `FILTER_MATCHES_NOTHING` `parameter`, `values`, `pointer` and `position`; `EVENTS_EXPIRED` `fromPosition`, `toPosition` and the `publication` to reload from. Null for `SUSPENDED_BY_USER`.
- suspendedAt: When it was suspended.

### SubscriptionDelivery

How delivery goes: when a request was last delivered, and the request being retried.

- lastDeliveredAt: When a request was last answered `2xx`; null before the first.
- pending: The request being retried; null while none fails.

### PendingDelivery

The request being retried. It keeps its delivery ID and events through every attempt, so a receiver can tell a repeat. After a failure the waits are 10 seconds, 30 seconds, 1, 2, 5, 10 and 30 minutes, then an hour, each varied by up to 20 percent. A `2xx` ends it; after 24 hours of failures the subscription is suspended `DELIVERY_FAILED`. An edit or a resume discards it.

- deliveryId: The request's delivery ID, the same on every attempt.
- throughPosition: The feed position of the request's last event.
- attempts: The failed attempts since `failingSince`.
- failingSince: When the request first failed.
- lastAttemptAt: When the latest attempt started.
- nextAttemptAt: When the next attempt is due; null while the subscription is suspended.
- lastError: What the latest attempt failed with.

### DeliveryError

Why an attempt failed.

- kind: `status`: the receiver answered something other than `2xx`. `redirect`: it answered a redirect, which is not followed. `timeout`: no answer within 10 seconds. `connection`: no connection. `tls`: the secure connection failed. `address`: the host resolves to an address the engine refuses.
- status: The receiver's status for the kind `status`.
- message: At most 200 characters of the answer or the error.

### DeliveryAttemptError

Why an attempt failed.

- kind: As in `DeliveryError`: `status`, `redirect`, `timeout`, `connection`, `tls` or `address`.
- message: At most 200 characters of the answer or the error.

### DeliveryPage

A subscription's deliveries, newest first.

### DeliveryRow

One event of a request. The rows of one request share its `deliveryId`, `status`, `attempts`, `responseStatus` and `sentAt`.

- deliveryId: The request's delivery ID.
- eventId: The event's ID, the same in every request that carries it.
- event: The event's key.
- change: What happened: `created`, `updated` or `deleted`; a workspace event's own (`submitted`, `approved` or `sentBack`).
- objectType: The type of the record; for a workspace event, the change set.
- objectId: The record's ID; for a workspace event, the change set's.
- position: The event's position in the feed.
- status: `queued`: built, not sent yet. `sending`: an attempt is under way. `retrying`: it failed and waits for its next attempt. `succeeded`: answered `2xx`. `failed`: given up after 24 hours, or a resend that failed. `dropped`: an edit or a resume discarded it.
- attempts: How many attempts were made.
- responseStatus: The receiver's status for the latest attempt; null before one is answered.
- sentAt: When the latest attempt started; null before the first.
- nextAttemptAt: When the next attempt is due while `retrying`; null otherwise.
- resendOf: The delivery ID of the request a resend repeats; null for any other.

### DeliveryDetail

A request: its events, the body its latest attempt sent and every attempt.

- deliveryId: The request's delivery ID, the `RDM-Delivery-Id` header.
- batchId: The batch the request belongs to; it equals `deliveryId`.
- status: As `DeliveryRow.status`.
- events: The events the request carries, in order.
- requestBody: The body of the latest attempt as the receiver got it, in the subscription's format then; null while it has not been sent.
- requestBytes: The size of `requestBody` in bytes; null while it has not been sent.
- createdAt: When the request was queued.
- nextAttemptAt: When the next attempt is due while `retrying`; null otherwise.
- resendOf: The delivery ID of the request a resend repeats; null for any other.
- attempts: Every attempt, oldest first.

### DeliveryEvent

- eventId: The event's ID.
- event: The event's key.
- change: What happened, as in `DeliveryRow`.
- objectType: The type of the record; for a workspace event, the change set.
- objectId: The record's ID; for a workspace event, the change set's.
- position: The event's position in the feed.

### DeliveryAttempt

One attempt to deliver a request.

- number: 1 for the first attempt.
- startedAt: When it started.
- completedAt: When it ended; null while it is under way.
- durationMs: How long it took, in milliseconds; null while it is under way.
- responseStatus: The receiver's status; null without an answer.
- error: Why it failed; null when it succeeded.
- responseBody: Up to 4 KiB of the receiver's answer; null when none was read.

### DeliveryResend

The event of a delivered request to send again.

- eventId: The event to send again; it must be one the request carried.
