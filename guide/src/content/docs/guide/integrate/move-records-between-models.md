---
title: Move records between models
description: Preview a mapped copy or move and publish its target before any source deletion.
reader: integrator
---

Use a model mapping when the destination has a different structure. Counterpart file imports only handle workspaces of the same model. Read [Model and release operations](/docs/integrate/model-and-release-operations/) for the distinction.

1. Read both workspaces' models and release identities. Obtain Browse on the source and Copy and move on the target; a move also needs Work in change sets at the source. Publication requires the relevant publish or approval rights separately.
2. Create or select a [model mapping](/docs/api/?api=management#tag/model%20mappings). Review its type and relationship coverage, parent placements, attribute conversion, defaults and match keys. Resolve its reported problems against the releases the workspaces run.
3. Start a preview through the [move operation](/docs/api/?api=management#tag/moves). Choose copy to leave the source intact, or move to prepare source deletions too. Select the exact records, types or subtree and whether the source is live or a publication. Related records outside the selection are not automatically included.
4. Follow the [job](/docs/api/?api=management#tag/jobs) and page its rows. Review refused and not-moved records, missing parent or relationship mappings, uncarried values and possible duplicates. Correct the mapping and dry-run again when necessary. No data or change set is created by the preview.
5. Confirm the reviewed job. A changed mapping or workspace release refuses confirmation; review another dry run. On success, read the target change-set identity and execution outcomes. Target rules are checked again as the load runs.
6. Review and publish the target change set through the [change-set operations](/docs/api/?api=management#tag/change-sets), following the workspace's approval policy. Until publication, the copied data is absent from consumer reads.
7. For a move, inspect any prepared source-deletion change set. Source records changed since preview or needed by records left behind can be retained with a reason. Publish source deletions only after the target copy is published. If the target copy was discarded, discard the dependent deletion instead of forcing it.

Keep both jobs and change-set identities in your reconciliation record. A completed load prepares changes; it does not mean the full two-workspace transfer has been published.
