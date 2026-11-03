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
