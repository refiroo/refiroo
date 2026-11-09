---
title: Load, then follow changes
description: Build a complete mirror and continue from the exact position matching its baseline.
reader: integrator
---

Use this sequence to keep another system in step without a gap between its initial load and incremental changes. Read [Following changes](/docs/integrate/following-changes/) for position and retention rules.

1. Give the integration Browse and Feed access in the workspace. Read its [model and capabilities](/docs/api/?api=management#tag/model). Decide the exact scope your mirror holds.
2. Request a live [export](/docs/api/?api=management#tag/exports) of that scope, including required relationships. Wait for the [job](/docs/api/?api=management#tag/jobs) to complete. Save its output metadata, especially the feed position matching its database snapshot. Do not substitute a head read before or after the export.
3. Download the completed output and build the local baseline. Check its size and checksum. Store the baseline and its position together so a restart cannot pair an old dataset with a new checkpoint.
4. Read the [workspace feed](/docs/api/?api=management#tag/workspaces) after that position. Apply creates, updates, deletions and type changes to the mirror, rereading records for values. A deletion removes the local record; a publication marker identifies the snapshot boundary.
5. Commit local effects before saving the returned continuation position. Make replay safe by workspace and position. Follow all pages until the returned continuation equals the head; sparse filtered pages must still advance the checkpoint.
6. After interruption, continue from the stored position. If it expired, reread the publication named in the refusal and continue from its feed position, or repeat the live-export baseline. If it is ahead of the head, check for a wrong workspace or restored database and rebuild the baseline.

A publication is an alternative starting point: page its immutable records and relationships through the [management reads](/docs/api/?api=management#tag/objects), then continue after its feed position. Do not use an unpositioned old publication as a synchronization checkpoint. A filtered feed cannot repair data omitted from an incompatible baseline; keep the scope and recovery policy explicit.

## Use a consumer contract instead

A consumer-only client cannot request management exports or the raw workspace feed. Use the contract's Publications, Lists and Events operations instead. The contract must declare lists covering the objects you need and events covering the changes you need; the reference `stops-changed` event watches code, name and validity, not every stop field.

1. Read the contract's [Publications operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/publications). Select a compatible publication with a non-null `eventSequence`. Save its ID and sequence.
2. Page every required list with that explicit publication ID. Keep the same workspace, API name, contract version, filters and publication while traversing. Build a separate local generation and promote it only when all lists finish.
3. Start the contract's [Events operation](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/GET/api/consumer/stops/v1/events) with `after` equal to that publication's sequence. Event reads are live: do not send `publication` on them.
4. After each durable page, save the returned `cursor`, not just the last integer position. Continue with that cursor and without `after`. Several events can share a position. Even a caught-up page's cursor is your next polling checkpoint.
5. Deduplicate by event ID. Full payloads describe the current object, not its state at the event time. For identity payloads, reread the object; it may already have been deleted. Remove local data on deletion and preserve unknown event kinds for reconciliation.

The complete [event example](/docs/integrate/consumer-events-and-webhooks/#a-declaration-and-the-event-it-exposes) shows the envelope, composition position and lasting cursor. A filtered contract can miss a surviving object's departure from a scope; schedule reconciliation of such a mirror. On expired events, rebuild from the baseline identified in the refusal. If no compatible positioned publication exists, arrange one with the people publishing data rather than substituting today's head.

## Restart after a restore or configuration change

Store your baseline and continuation together in your own backups. After either system is restored, verify the instance, workspace and contract before resuming. A checkpoint ahead of the restored server requires a new baseline. Changing scope, model mapping or contract version also needs an explicit reconciliation decision; an old checkpoint does not establish that the new dataset was ever loaded.

To retire a pull mirror, stop polling and archive or remove its local data and checkpoint as required. Pulling creates no server subscription. A webhook mirror additionally needs its [subscription suspended or deleted](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/).
