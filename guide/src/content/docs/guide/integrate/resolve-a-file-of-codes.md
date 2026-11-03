---
title: Resolve a file of codes
description: Resolve keyed source rows and keep missing, ambiguous and rejected results separate.
reader: integrator
---

Use consumer resolution to identify records without changing them. Read [Looking up and resolving](/docs/integrate/looking-up-and-resolving/) for scores, targets and limits.

1. Discover the contract and obtain a consumer token with the appropriate workspace grant. Inspect the contract's [resolution operation](/docs/api/) and declared parameters. Choose live data or one publication for the entire file.
2. Keep each source row's own reference. Decide which known facts narrow the question, such as public type or source system. Put shared facts in defaults and override them only where a row differs.
3. Build bounded batches, at most the configured maximum (1,000 by default). Each item supplies a query or an existing record ID, never both. Preserve multi-value terms as JSON values; do not split commas inside actual codes.
4. Submit the read through Batch resolve. **Example:** the reference contract's [Batch resolve](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/POST/api/consumer/stops/v1/resolve) can resolve the fictional Regional ticketing system's codes to stops. If another representation is needed, request one declared target parameter.
5. Reconcile outcomes in source-row order. Store found identities; return no-match and target-not-found items for source correction. Return ambiguous source or target items for disambiguation. Keep request errors separate from valid questions with no answer.
6. Retry corrected questions using additional known facts, without forcing the first tied match. A broad-query refusal needs more specific terms. A batch-size refusal needs smaller batches; a publication mismatch needs a compatible baseline.

**Reference-data example:** `T-9999` is deliberately unmapped and `T-0300` deliberately points to two stops. Both are fictional codes. A reliable integration preserves that distinction instead of inventing an answer.

## Try two rows from the reference world

The reference declaration offers Resolve because it declares both Get by ID and XREF. For a file of known stop numbers and supplier codes, send a bounded read like this. The mode default narrows both questions to records with a matching train mode; an item can override a default parameter.

```http
POST /api/consumer/stops/v1/resolve?workspace=graubuenden HTTP/1.1
Host: <instance>
Authorization: Bearer <consumer-token>
Content-Type: application/json
Accept: application/json

{
  "defaults": {"mode": "TRAIN"},
  "items": [
    {"ref": "row-1", "query": "8505173"},
    {"ref": "row-2", "query": "T-9999"}
  ]
}
```

The complete [response body](/docs/integrate/looking-up-and-resolving/#resolve-a-small-file-in-one-request) has two outcomes, in that order. Row 1 is `found`, with Tschamut-Selva's full object and `matchScore: 900` from the declared stop-number rule. Row 2 is `not_found` with `NO_MATCH`; the fictional code has no mapping. The counts are one found and one not found. An HTTP 200 is not a reason to mark both source rows as resolved.

For another system's representation, use a declared target such as `to.system=wikidata-stations` on a single lookup or as a resolution parameter. The [full crosswalk example](/docs/integrate/looking-up-and-resolving/#a-crosswalk-from-a-stop-number-to-another-systems-code) explains why the resulting code is a `target` separate from the source stop. If no unique target exists, correct the mapping or target restriction; do not substitute the source's code.

Keep each row's original reference, input, outcome and chosen publication together for reconciliation. A later retry against live data may legitimately resolve differently after a steward corrects the mappings.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Regional ticketing codes are fictional.*
