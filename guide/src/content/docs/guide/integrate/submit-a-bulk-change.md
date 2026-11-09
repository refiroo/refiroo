---
title: Submit a bulk change
description: Prepare a bounded batch, inspect its preview and reconcile every outcome.
reader: integrator
---

Use a batch when your source supplies several changes together. Read [Writing in bulk](/docs/integrate/writing-in-bulk/) for policies and limits.

1. Read the target workspace's [model and capabilities](/docs/api/?api=management#tag/model). Decide whether changes go live or into a change set. Keep the model release and current version claims.
2. Prepare items in dependency order: parents before children, then relationships that need those records. Use public IDs or declared unique keys. Choose atomic if nothing may apply on a refusal, or independent if valid items may apply separately.
3. Submit through the [batch operation](/docs/api/?api=management#tag/jobs), with an idempotency key saved beside the exact request. Choose background preview if you need to review the changes, including cascading deletion impact. Inline execution cannot preview.
4. Follow the returned [job](/docs/integrate/jobs/). In a preview, inspect proposed outcomes, the policy result and whether coverage is complete. A sample does not prove the remaining items are valid. Confirm through the [job confirmation operation](/docs/api/?api=management#tag/jobs), or cancel without applying changes.
5. After execution, page every item outcome. Record committed IDs and versions, correct rejected source items and inspect why unprocessed items stopped. A successful HTTP response alone does not mean the batch applied completely.
6. If the response was lost, replay the exact keyed request. If data was refused for stale versions or changed deletion impact, reread or preview before building a corrected request with a new key. Never change a request under an existing key.

For independent work, retain earlier committed outcomes when a job fails or is cancelled. For an atomic refusal, nothing from the batch applied. Check which case occurred before planning a retry.

## Change relationship values from a grid selection

Use this sequence when an integration needs to set one scalar value across many connections,
possibly linking missing pairs. It uses the synchronous
[grid-change operation](/docs/api/?api=management#tag/relations/POST/api/v1/relations/grid-change),
not the job submission and confirmation sequence above. Read
[Relationships and their values](/docs/integrate/relationships-and-their-values/) for the
read models, permissions and version rules.

1. Read the model and the
   [grid](/docs/api/?api=management#tag/relations/GET/api/v1/workspaces/{workspace_key}/relation-grid).
   Keep the workspace, application, relationships-table view and context. Confirm that the
   binding carries the attribute you intend to change. JSON values cannot use this operation.
2. Choose source rows either by `fromObjectIds`, or by `allMatching: true` with the grid's
   search and filters, minus `exceptObjectIds`. Use exactly one selection method. Search,
   filters and exceptions belong only to all-matching selection. Each body filter includes
   `field`, `operator` and its lexical `value`; operators have the same meaning as in the grid read.
3. Choose 1–50 `toObjectIds`. These are the column records to affect, not every column the
   workspace could supply. Preserve the intended column IDs when a grid read reports more
   matching columns than it can show. A relationship-value filter matches through a connection
   to these selected columns.
4. Send `dryRun: true` with the value and `linkMissing` choice. Null clears the named attribute;
   false sets a Yes or no value to No. Missing connections are left alone unless
   `linkMissing: true` asks to create them with that value.
5. Read `change`, `same`, `missing`, `linked` and every `refused` item. The preview checks all
   selected pairs, not a sample. A 200 preview with refusals is not permission to apply a
   partial result. Correct the selection, model rule or value first.
6. Send the reviewed selection with `dryRun: false`. The operation checks current data again
   and applies all changes together. It does not accept a saved preview token or a relationship
   version per pair: an intervening live edit can change what the selection matches. If exact
   per-connection version claims are required, use the batch sequence below.
7. Reread the result, including rows hidden by a filter on the old value. For a change set,
   supply `changeSetId` and `expectedChangeSetVersion` on both requests. Keep the apply's returned
   `changeSetVersion`; the dry run does not advance it. Review and publish separately.

**Reference-data example:** the Network application's `stop-operators` grid reads the
stop-to-operator binding. It carries Local name (`local-name`), Primary contact (`is-primary`)
and Inspected on (`inspected-on`). To preview setting Primary contact on Tschamut-Selva's
connection to Matterhorn Gotthard Bahn (fo):

```http
POST /api/v1/relations/grid-change HTTP/1.1
Host: <instance>
Authorization: Bearer <management-token>
Content-Type: application/json

{
  "workspaceKey": "graubuenden",
  "applicationKey": "network",
  "viewKey": "stop-operators",
  "fromObjectIds": ["8d90eede-23cf-47c1-8dac-cb37956f5fd5"],
  "toObjectIds": ["f94ef862-2a95-4675-9e31-6b1d0a03317f"],
  "attributeTypeKey": "is-primary",
  "value": true,
  "linkMissing": false,
  "dryRun": true
}
```

The reference instance returns this preview: the connection exists and has no Primary contact value.

```json
{
  "dryRun": true,
  "change": 1,
  "same": 0,
  "missing": 0,
  "linked": 0,
  "refused": [],
  "changeSetVersion": null
}
```

For a filtered selection, replace `fromObjectIds` with, for example:

```json
{
  "allMatching": true,
  "exceptObjectIds": [],
  "search": "",
  "filters": [{"field": "relation:is-primary", "operator": "isNull", "value": "true"}]
}
```

This is a selection excerpt, not a whole request: retain the workspace, view, column IDs,
attribute, value and preview choice from the request above. It selects source records with an
existing connection to one of those columns whose primary value is empty. It does not select
unlinked pairs merely because they have no primary value.

An apply refusal is `RELATION_BATCH_REFUSED` (409 for a stale version, otherwise 422), with
item codes and messages, and writes nothing. `422 INVALID_GRID_CHANGE` means the attribute,
value or endpoint type is invalid. Model or request-shape errors must be corrected, not retried
unchanged. `413 BATCH_TOO_LARGE` reports the `ATOMIC_JOB_MAX_ITEMS` ceiling, including during
a dry run. The limit counts values that would change plus missing pairs to link, not source
rows. Narrow rows or columns, or coordinate a limit change with the operator.

## Change values on known relationship IDs

1. Read each relationship's full attributes and `relationVersion`, keeping its workspace or
   change-set context. Use the relationship's version, not its endpoint's or mapping set's version.
2. Submit the [relationship-value batch](/docs/api/?api=management#tag/relations/POST/api/v1/relations/batch)
   with one item per relationship. Supply its `id`, `expectedVersion` and only the attributes
   to set or clear. The batch merges these values; null clears a named value and omitted
   attributes stay. A single [relationship PATCH](/docs/api/?api=management#tag/relations/PATCH/api/v1/relations/{relation_id})
   instead replaces the full attribute set.
3. For Live, name `workspaceKey`; for a change set, include `changeSetId` and
   `expectedChangeSetVersion`. On success, retain returned relationship versions and any
   `changeSetVersion`. Results follow input order.
4. On `RELATION_BATCH_REFUSED`, reconcile `details.items` by index, relationship ID and item
   error code. A stale item makes the response 409, other refusals 422, and nothing applies.
   Read current values before sending corrected version claims. Repeating an ID is
   `DUPLICATE_BATCH_ITEMS`; an oversized request is `413 BATCH_TOO_LARGE` under `BATCH_MAX_ITEMS`.

This direct batch has no background job or job-confirmation step. After a lost response, read
the relationships to reconcile their state before sending another write.

*Reference names and identities: Source: opentransportdata.swiss, Service Points (Didok), Federal
Office of Transport / SBB, snapshot 2026-11-02. Relationship values are sample data; the preview above was captured from the reference instance without applying it.*
