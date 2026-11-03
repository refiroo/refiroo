---
title: Continue live work while a change set is open
description: Make immediate corrections and understand which ones can conflict with proposed work.
reader: steward
---

Live remains editable while a change set is open, if you hold Edit live. See
[Change sets](/docs/use/change-sets/#publishing-and-intervening-live-work).

1. Leave the change-set context and choose **Live**. Check the green band before editing.
   Opening another browser tab can help keep the contexts distinct.
2. Make and save the immediate correction. It is visible in Live now; it does not update
   the starting copy inside the existing change set.
3. Return to the change set and review its changes. An unrelated new Live record or a Live
   correction to an untouched record is kept when the change set publishes.
4. Validate and attempt publication only after reviewing current work. If Live and the change
   set changed the same record, publication refuses the conflict even if different fields
   changed. Changed mapping sets and invalid combined relationships can also stop publication.
5. Read the conflict list. Both Live and the change set remain intact, and nothing is partially
   published. Prepare a new change set from current Live and reapply the intended corrections
   after reconciling them. There is no automatic rebase or forced overwrite through retry.

Another publication between review and confirmation can also make the attempt stale. Refresh
and inspect the current result before retrying.
