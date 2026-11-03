---
title: Read as of a date
description: Find records effective on one day and keep the date fixed while paging.
reader: integrator
---

Use this when a downstream system needs data valid on a business day. [Business dates](/docs/integrate/business-dates/) explains the boundary rules.

1. Discover the selected context's [model and type](/docs/api/?api=management#tag/model). Confirm that the type declares an effective period. Having date fields is not enough.
2. Choose live data, a change set or a publication. A publication fixes stored content; the business date then filters that content. These are separate choices.
3. Send the date to the [per-type list or model-aware query](/docs/api/?api=management#tag/objects), using a calendar date rather than a timestamp. For a consumer contract, use the dated read described by its [API reference source](/docs/api/).
4. Inspect the result. A record ending on that day is excluded; one starting on it is included. Open ends remain valid without a bound, and overlapping records can both appear. Do not assume exactly one match.
5. Continue with the returned cursor and the same date and context. If related records must also be constrained, express their dates in the query criteria; expansion alone does not date them.

On `AS_OF_NOT_SUPPORTED`, choose a dated type or remove the date intentionally. Do not retry without the date while presenting the answer as dated. For a mixed consumer lookup, check which returned types the engine actually dated.
