---
title: How refiroo protects data
description: Model rules, conflict protection and reviewed changes keep shared data dependable.
reader: evaluator
---

One set of rules applies on every path into refiroo. Browser edits, API calls and bulk loads meet the same model validation and permission checks. See [What refiroo is](/docs/about/what-is-refiroo/) for how these checks support shared reference data.

## Values keep their types and rules

A number stays a number, a date stays a date and a yes/no field stays distinct from text. The model can require a field, give it a default, make it read-only, limit a number's range or require at least one of several fields.

A unique field value cannot be assigned to another record in the same workspace. A separate relationship rule can allow only one counting related record beneath each ancestor of a chosen type; this is how a model can limit one active representation per owner and group. A required field cannot be emptied. A declared validity period must end after it starts. Correct the reported value, or ask a model administrator if the rule itself needs to change. See [Records](/docs/use/records/) and [Types, attributes and relations](/docs/model/types-attributes-relations/).

## Connections are checked too

The model decides which record types can connect, whether a connection is required and how many are allowed. A parent must be a permitted parent in the same application and workspace. A record cannot become its own ancestor.

The parent link is maintained with the record's position. Move the record to change its parent; ordinary relationship controls cannot alter that link. See [Relationships](/docs/use/relationships/) and [Hierarchies](/docs/use/hierarchies/).

## A save cannot silently overwrite newer work

Changes carry the version the editor read. If someone else saved a newer version, refiroo refuses the stale save and keeps the attempted input available for review. Read the current information and decide how to apply the intended correction.

A change set also checks for competing live changes when published. Unrelated live edits survive, but a conflicting change publishes nothing. Validation before publication is useful; it does not reserve values or guarantee that Live stays unchanged afterwards. See [Change sets](/docs/use/change-sets/).

## Review changes with wider effects

Deleting a record first shows the impact: children, records it owns and relationships it would remove. Independent related records are disconnected rather than deleted. Review this preview before confirming.

Bulk changes and file loads offer previews showing what can be applied and what is refused. Their result depends on the chosen operation: publishing a change set is all-or-nothing, while a bulk job may apply independent items and refuse others. Cancellation cannot undo chunks an independent job already saved. Review the result rather than assuming every row succeeded. See [Changing many records](/docs/use/changing-many-records/) and [Imports and exports](/docs/use/importing-and-exporting/).

## History makes changes accountable

Record history names who changed what and when, including the person or client behind a background job. Publication changes name their publication. Older entries without attribution say **Before sign-in**; some operations did not record the previous value. History is evidence of changes, not a substitute for a complete backup. See [History](/docs/use/history/) and [Security, audit and privacy](/docs/about/security-and-trust/).
