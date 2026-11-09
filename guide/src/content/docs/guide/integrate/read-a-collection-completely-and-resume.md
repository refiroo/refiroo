---
title: Read a collection completely and resume
description: Traverse bounded pages and checkpoint a resumable read.
reader: integrator
---

Use cursors to walk an entire collection. Read [Identifiers, paging and errors](/docs/integrate/identifiers-paging-and-errors/) before choosing your checkpoint strategy.

1. Choose the workspace and context. If rows must stay fixed throughout the read, choose a publication. Discover the record type and supported filters through the [model operations](/docs/api/?api=management#tag/model).
2. Request the first page through the [object collection operation](/docs/api/?api=management#tag/objects), with the intended filter and order. Use a bounded page size supported by that operation. Request totals only if the task needs them.
3. Process the page. Make local writes repeatable by public ID. Commit them before storing the continuation cursor; a crash between these steps can replay a page, so make replay harmless.
4. Request the next page with the returned cursor and the same query and context. Continue until there is no next cursor. An individual short page is not your stopping rule.
5. To resume, load the saved query and cursor together. Do not combine it with a newly chosen workspace, sort or filter. On `INVALID_CURSOR`, restart the intended read and reconcile records already stored.

Use a returned anchor to reopen a page, or a position to jump to a row. Neither replaces the continuation checkpoint for reading every row. Live records can change while you traverse them; for ongoing synchronization, use [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/).

## Keep one durable checkpoint

Store the operation, workspace, context or publication ID, filters, order, business date if present, and continuation cursor as one checkpoint. Keep the consumer API name and contract version too when using a consumer list. This is integration state in your system; include it in that system's backup and restore procedure. A token is renewed separately and is not the checkpoint.

The processing sequence is:

```text
read page using saved query and cursor
upsert each returned record into local storage by public ID
commit local changes
save nextCursor with the unchanged query
repeat while nextCursor is present
```

If your storage can commit rows and the checkpoint in one transaction, do so. Otherwise replay after a crash can repeat the last committed page. An empty first page with no continuation is a complete empty collection. A short page with a continuation still has more to read.

For a fresh full replacement, load into a separate local generation and switch readers to it only after the final page succeeds. Do not delete records missing from an incomplete extract. On a restored local backup, resume its matching checkpoint, not a newer cursor from another machine. If the context is gone or the cursor is rejected, rebuild the generation from a new first page. For live data this is not a consistent snapshot; use a fixed publication when the task needs one.

To stop a read, stop issuing requests and retain or remove the local checkpoint according to whether you plan to resume. A collection read creates no server-side job to cancel.
