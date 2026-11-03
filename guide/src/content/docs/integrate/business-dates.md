---
title: Business dates
description: Read records effective on a calendar date, independently of snapshots and history.
reader: integrator
---

A business date answers which records are valid on that day. It does not rewind edits, choose a publication by date or read audit history. Follow [Read as of a date](/docs/guide/integrate/read-as-of-a-date/) for the sequence.

A model can declare an effective period using two date attributes. The start is inclusive and the end exclusive. An empty start means no lower bound; an empty end means no upper bound. A record is absent on its end date. Different records' periods may overlap, so a business-date read can legitimately return several matching records.

Every write checks that a supplied end is after the start, including single-value edits, type changes, imports and changes prepared for publication. `INVALID_EFFECTIVE_PERIOD` means correct the resulting period; changing just the end is checked against the stored start.

## Management reads

Use a dated [per-type collection or query](/docs/api/?api=management#tag/objects) in live data, a change set or a publication. A declared date field alone does not make a type dated: the model must declare the period. `AS_OF_NOT_SUPPORTED` refuses a date for an undated type or the management cross-type lookup. Use the relevant per-type operation instead.

The date filters the queried records. Related hops and expanded records remain undated unless your criteria explicitly constrain their dates. The cursor binds the date: keep it unchanged while paging. A malformed calendar date is refused rather than silently interpreted as a timestamp.

## Consumer reads

Consumer contracts support dated object, list, lookup and batch reads where their exposed types declare periods. See the selected contract's [operations in the API reference](/docs/api/) and [consumer reading sequence](/docs/guide/integrate/read-through-a-consumer-api/).

An existing object or list of an undated type refuses a date. A mixed lookup retains undated types and filters the dated ones. Check the answer's indication of which public types were dated. Ancestors, related items, parameter matching and score sources remain undated: a returned object's period does not imply that everything represented with it was valid that day. Invalid consumer dates produce `INVALID_AS_OF`.

Adding or moving a period in a model can require data repair before activation. Removing a period used by a consumer contract requires a higher contract version. The built-in browser shows ordinary date fields; it has no business-date filter.

Consumer pages and batch answers name the sorted public types dated in `asOfApplied`; every dated object or page read also carries `RDM-As-Of-Applied`. Both are absent without `asOf`. If none of the types an XREF can return has a declared period, it answers `400 AS_OF_NOT_SUPPORTED`. An otherwise known dated object outside its period answers `404 OBJECT_NOT_FOUND`. Batch items use these same rules individually. Supply exactly one `YYYY-MM-DD` calendar day; timestamps, zones, impossible dates and repeated dates produce `400 INVALID_AS_OF`.
