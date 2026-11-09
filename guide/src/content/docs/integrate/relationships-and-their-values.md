---
title: Relationships and their values
description: Read connections and change their typed attributes through the management API.
reader: integrator
---

Use management relationship operations when an integration maintains connections or values
belonging to those connections. A relationship joins two public record IDs and holds only the
attributes declared for its directed type pair. Those values retain their declared types and
numeric bounds. They are separate from both endpoint records' attributes.

All management paths below begin with `/api/v1`. Use a management token with Browse for reads
and Edit live or Work in change sets for writes in the selected context, subject to scoped
grants. Consumer grants do not grant these writes. The [relationship operations](/docs/api/?api=management#tag/relations)
define the requests and responses. For read-only business projections, see
[Consumer APIs](/docs/integrate/consumer-apis/#publish-values-of-the-connection).

## Read connections before writing

Use the [workspace edge list](/docs/api/?api=management#tag/relations/GET/api/v1/workspaces/{workspace_key}/relations)
when the integration needs relationships across records. `fromObjectId` and `toObjectId` narrow
the list to particular endpoints. Page until no continuation remains; do not infer that one
page contains every connection.

To read the rows of a declared relationships table, supply its `applicationKey` and `viewKey`.
The view fixes its relation and endpoint types. Do not also supply `relationTypeKey`,
`fromObjectTypeKey`, `toObjectTypeKey` or `direction`: that gives `422 RELATION_TABLE_BINDING_FIXED`.
A row has `source` and `target` with the endpoint fields chosen by the view, `attributes`,
`relationId` and `relationVersion`. Keep that relationship version for a value edit.
`mappingVersion` instead versions the source record's relationship set; it is used when
changing membership, not as the version of one connection's values.

The view's `sortFields` and `filterFields` determine sorting and filtering. An equality filter
uses `filter.<ref>.eq`, where the reference begins with `from:`, `to:` or `relation:`. Repeated
equalities on one field are alternatives; different fields must all match. Values are parsed
in the field's type. `search` finds either endpoint's name without letter case. Use `sort` or
a leading minus for descending order. Missing sort values come last.

Cursor, position, end and seek navigation follow the [paging rules](/docs/integrate/identifiers-paging-and-errors/).
With a grouped view, `seek` targets the group record's name; otherwise it targets the first
sort value. `groupCounts` reports matching relationships for each group record on the page,
across the filtered list rather than just that page. An undeclared filter or operator gives
`422 INVALID_FILTER`; an undeclared sort gives `422 INVALID_SORT`. Sort or field filters
without a relationships-table view give `422 RELATION_TABLE_VIEW_REQUIRED`.

The same read works in Live, a change set (`changeSetId`) or a publication (`publicationId`).
Select one context deliberately and keep it with paging checkpoints. A publication is read-only.

## Read a grid without losing missing connections

Use the [relationship grid read](/docs/api/?api=management#tag/relations/GET/api/v1/workspaces/{workspace_key}/relation-grid)
with `applicationKey` and `viewKey`. It accepts any relationships-table view, whichever layout
the browser uses. A different view gives `404 RELATION_TABLE_NOT_FOUND`.

Each matching from record appears once, including records with no connection. The page's
`columns` contains up to 50 matching to records in name order, each with `linkedCount` across
all filtered source rows. `columnTotal` reports all matching column records and `rowTotal`
reports matching rows. Narrow the column selection when the total exceeds what is returned.
Repeat `toObjectId` to select column records and use `toSearch` to search them.

Each source row has `mappingVersion` and a `relations` map keyed by column record ID. An entry
holds `relationId`, `version`, `attributes` and `proposed`. A missing entry means not linked;
an empty or missing attribute on an existing entry means no held value, not no connection.
`proposed` marks a staged connection in a change set and is false in Live and publications.

Filters use `filter.<ref>.<operator>`. The grid offers its declared filters and the filter fields
of each endpoint type's main table view. `from:` narrows rows, `to:` narrows column records,
and `relation:` keeps rows with a matching connection to a shown column record. Conditions on
relationship attributes must hold on the same connection. Operators follow the field's type,
including equality, text comparisons, ranges and empty/unset tests where supported. The
endpoint fields also support their collection's related-record filters. Invalid fields or
operators are refused rather than ignored. Row sorting uses a declared `from:` field; a
declared sort for another part falls back to the source record's name.

Repeat `attribute` to request particular relationship attributes among the view's attribute
columns. An invalid choice gives `422 INVALID_ATTRIBUTE`. Without this parameter the read returns
all stored relationship values, including values not displayed by the view. Preserve those
values when constructing a replacement write.

Grid paging, search and context selection follow the row read. See the
[grid's browser explanation](/docs/use/relationship-tables/#grid-each-from-record-once) for the
meaning of linked counts and gaps.

## Change one connection or a known set

Use [Update relationship](/docs/api/?api=management#tag/relations/PATCH/api/v1/relations/{relation_id})
with `attributes` and `expectedVersion` from the read. **PATCH replaces the relationship's
attribute set.** Merge a single changed value into the complete stored set before sending it,
otherwise omitted values are removed. A stale claim gives `409 VERSION_CONFLICT`; reread and
reconcile instead of silently retrying against a new version. This edit does not replace its
endpoint records or change their own fields.

For several known connection IDs, use [Batch relationship values](/docs/api/?api=management#tag/relations/POST/api/v1/relations/batch).
Each item's attributes are merged over its stored values, and null clears a named value.
Omitted attributes remain. This differs from PATCH. Keep each item's relationship version.
All items are validated and saved together: a refusal leaves every connection unchanged.

`RELATION_BATCH_REFUSED` returns 409 when a version was stale, otherwise 422. Its
`details.items` identifies each failure by index, relationship ID, error code, message and
further details. Read these item codes before deciding whether to reread, correct a value or
change the intended links. Repeating a relationship ID gives `422 DUPLICATE_BATCH_ITEMS`;
exceeding `BATCH_MAX_ITEMS` gives `413 BATCH_TOO_LARGE`.

For Live batch writes, pass `workspaceKey` explicitly. For change-set writes, pass `changeSetId`
and the current `expectedChangeSetVersion` as well as each connection's version. Keep the
returned `changeSetVersion` for the next write. None of these operations changes a publication.

## Change a filtered grid selection

[Grid change](/docs/api/?api=management#tag/relations/POST/api/v1/relations/grid-change) changes one
scalar relationship attribute across selected source rows and column records. Unlike a list
of known relationship IDs, it can also link missing pairs. Start with `dryRun: true`, inspect
all counts and refusals, then submit the reviewed selection with `dryRun: false`. The server
checks current data again; the preview does not reserve it.

Follow [Submit a bulk change](/docs/guide/integrate/submit-a-bulk-change/#change-relationship-values-from-a-grid-selection)
for a request and preview. This is a synchronous atomic operation, distinct from a background
job. It does not inherit job confirmation or idempotency behavior just because it affects many
connections. After a lost response, reread current data before deciding what to send next.
