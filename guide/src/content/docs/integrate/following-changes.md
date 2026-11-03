---
title: Following changes
description: Keep a local mirror current using workspace feed positions and recoverable baselines.
reader: integrator
---

Use a workspace's raw change feed when your integration understands management records and needs to maintain a local copy. Use [consumer events](/docs/integrate/consumer-events-and-webhooks/) when it depends on a declared business contract instead. Follow [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/) to combine a baseline and a feed safely.

## Follow committed changes

The [change-feed operation](/docs/api/?api=management#tag/workspaces) reads entries after a saved position. Positions are gapless within a workspace and increase in commit order, including across concurrent writers. They are not shared between workspaces. Rolled-back writes take no position.

Entries identify created, updated, deleted or reclassified records, relationships and published or withdrawn publications. A reclassified record names its previous type. Each entry identifies affected fields and attribute types, its model release and whether a single write, job or publication caused it. **It carries no field values.** Read current records separately when you need them; they can already have changed again.

Parent changes are represented with the record; containment edges do not get separate feed entries. Publishing emits the committed record and relationship changes, then the publication marker. That marker's position corresponds to the complete publication snapshot. Withdrawing also adds a marker. Change-set edits, validation, model checks and discarded or refused work do not change live data and add no live position. Only applied batch changes appear, with their job as cause.

Persist your mirror updates before advancing the saved checkpoint. Deduplicate repeated processing by workspace and position. Continue from the returned next position, even when a kind or type filter returns few or no entries: the position advances across excluded entries. You are caught up when that position equals the reported head, not merely when a page is short. Changing the filter requires reconsidering your baseline.

## Retention and recovery

Default feed retention is 30 days, reported by capabilities. Entries after the current publication's position remain available even when older. With no active publication that has a feed position, nothing expires: there is no publication baseline to recover from.

`FEED_POSITION_EXPIRED` names the earliest available position and a publication baseline. Replace the local mirror from that publication, then follow from its recorded position. Alternatively take a new live export and use its job metadata's feed position. Do not jump directly to today's head: that silently discards changes.

`FEED_POSITION_AHEAD` means the checkpoint is beyond this workspace's head, perhaps because it belongs to another workspace or the database was restored. Verify the source, then establish a new baseline. A retired workspace's feed stays readable for reconciliation. Access requires the Feed action group; a Browse grant alone does not provide it.

## Narrow a feed safely

The feed’s `after` is a stable integer checkpoint: start at zero for all retained entries or use a baseline’s position. This feed does not use a collection cursor. Pages default to 500 entries and allow 1–1,000. Repeated kind or object-type values are alternatives; the two filter groups combine. An object-type filter matches a reclassified record’s old or new type, but excludes relation and publication entries. Plan how to load relationships if you use it.

The server scans at most ten times the requested page size. Save `nextAfter`, even on an empty page, and compare it with `headPosition`. `earliestPosition` is the retained floor: a checkpoint below that floor minus one is expired. `FEED_RETENTION_DAYS` controls the default 30 days; it does not erase object history.

Deleted relation entries retain their type and endpoint IDs so you can remove local edges without rereading the deleted relationship. Handle unknown action values without failing to read the page; reconcile unfamiliar changes against a fresh baseline if your mirror cannot apply them. Mapping transitions are history summaries, not extra feed changes.

A publication’s `eventSequence` on the consumer API and `feedPosition` on the management API refer to the same workspace sequence. Several consumer events can share one raw position, so consumer checkpoints also need their lasting cursor. Neither interface is a replacement for audit history with historical field values.
