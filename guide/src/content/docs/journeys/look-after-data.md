---
title: Look after data
description: Find, correct and connect records, maintain hierarchies and review data history.
reader: steward
---

These journeys connect everyday data work, from opening a workspace to checking the history of a
saved change. Start with the task you need. The linked pages explain the rules and the guides give
the screen-by-screen steps. Your workspace's model determines the applications, record types and
views available.

Reading needs Browse access. Live changes need Edit live; proposed changes need Work in change
sets. Publications are read-only, and retired workspaces refuse changes. See
[record permissions](/docs/use/records/#who-may-read-and-change-records) before starting.

## Start from home

Anyone returning to refiroo can use [Home](/docs/use/home/) to find accessible workspaces,
continue a recent visit, open a proposal or review a request awaiting approval. Choose the
workspace and then [open an application](/docs/guide/use/open-an-application/). Check the workspace
and data context on arrival before changing anything. If there are no workspaces to open, ask an
administrator for Browse access; signing in alone does not grant it.

## Find and inspect a record

A steward or integrator starts by choosing the workspace and the data to read: Live, a change set
or a publication. [Workspaces](/docs/use/workspaces/) and [applications](/docs/use/applications/)
explain that choice. [Find records](/docs/guide/use/find-records/) then connects search, filters
and sorting to the record's fields, hierarchy path, related records and history. Returning to the
list keeps its search and position. An empty relationship list means there are no matching
connections; a failed read needs a retry before drawing that conclusion.

An integrator can follow [reading records](/docs/integrate/reading-records/) for the corresponding
reads, including typed filters and related fields. Zero and No remain values in both channels.

## Correct a record

A steward or integrator corrects a name or field while keeping the record's identity, place and
relationships. Read [Records](/docs/use/records/), then [correct a record](/docs/guide/use/correct-a-record/)
in the intended context and check its saved values and history. A routine Live correction needs
no change set; a correction made within an open change set stays there until publication.

If another person saves first, review the current record and your attempted value before retrying.
Required, read-only, unique and range rules still apply. Integrators use
[versions and conflicts](/docs/integrate/versions-and-conflicts/) to protect the same save.

## Add a record where it belongs

A steward or integrator starts from a collection, a parent, or the record that must own the new
record. [Add a record](/docs/guide/use/add-a-record/) brings together its name, typed fields,
allowed parent and required relationships in one save. [Relationships](/docs/use/relationships/)
explains ownership, including an owner in another application. If a required choice is missing
or a value is already taken, correct it before saving again: no incomplete record is created.
A record created in a change set is not visible in Live until publication.

## Delete a record and what depends on it

A steward or integrator who needs permanent removal first reads the
[deletion rules](/docs/use/records/#deleting-a-record), then
[deletes a record](/docs/guide/use/delete-a-record/) after reviewing its impact. Descendants and
owned dependants go with it, including dependants in other applications; independent records
survive the removal of their connections. Cancelling changes nothing. If the impact changes,
obtain a fresh preview and review it again. Existing publications keep their snapshots.

## Relate records and maintain their relationships

A steward or integrator uses [Relationships](/docs/use/relationships/) to understand the connection
and its meaning in each direction, then [relates records](/docs/guide/use/relate-records/).
Choose an eligible candidate, save the connection and, where allowed, edit its fields or remove
it later. Connections can cross applications within the workspace. The model controls candidates,
required connections and how many are allowed. Move a record through its parent to change
containment; do not try to remove its parent relationship here.

## Build and change a hierarchy

A steward or integrator finds a branch, adds children and moves records to permitted parents.
[Hierarchies](/docs/use/hierarchies/) explains placement; [arrange records in a tree](/docs/guide/use/arrange-records-in-a-tree/)
and [move several records together](/docs/guide/use/move-several-records-together/) take the work
through confirmation to the new paths. Descendants and relationships travel with the moved record.
A move into its own subtree, or one breaking a relationship rule, is refused. A refused multi-record
move moves none of the selection. Review the named record and choose a permitted destination.

## Reshape a hierarchy across types, and change a record back

A steward or integrator makes structural changes in a change set when a move also changes record
types, inserts a level or removes one. [Reshape a hierarchy](/docs/guide/use/reshape-a-hierarchy/)
connects choosing the operation to reviewing the proposed types, values, relationships and missing
information. Apply only after resolving the plan's questions, then
[review and publish](/docs/guide/use/prepare-and-publish-a-change-set/). IDs and history survive.
Content without a place in the new type is retained in history and can be offered when changing
back. If the data changes after preview, preview again before applying.

## Review and replace a record's related records

A steward or integrator reviews which sources have no, one or several connections, then chooses
the set they should have. Start with [mapping grids](/docs/use/mapping-grids/), then
[replace a record's related records](/docs/guide/use/replace-a-records-related-records/).
A replacement saves together; retained connections keep their identity and values. Clearing is
available only where the rules permit it. If the set changed meanwhile, review the current
connections alongside your preserved choice before trying again. Publications allow inspection only.

**Example:** codes from another system can be connected to the stops they identify. The codes,
stops and connection rules come from the example model; the same journey works with other types.

## See and fill relationship coverage across ancestors

A steward or integrator uses a model-declared [relation matrix](/docs/use/relation-matrices/)
to compare row records with columns above their related records in a hierarchy. Start by
[filtering and filling the matrix](/docs/guide/use/fill-in-a-relation-matrix/): inspect missing,
filled, inactive or conflicting cells, then create a related record or link an eligible existing
one where offered. The state filter covers every matching row, beyond those currently visible.
An inactive cell may already contain a record that needs correction. Removing a connection cannot
leave an owned record without its required owner. Review staged work before publication.

**Example:** a matrix can compare stops with languages, showing each stop's names under a language.
The model supplies the row types, columns and rules for which names count.

## Change many records of a collection at once

A steward uses [changing many records](/docs/use/changing-many-records/) to select explicit rows or
all records matching a search and its filters. Continue with the guide for
[values](/docs/guide/use/change-values-of-many-records/),
[relationships](/docs/guide/use/change-relationships-of-many-records/) or
[deletion](/docs/guide/use/delete-many-records/), then inspect the preview and each job outcome.
Choose whether the change must succeed together or may apply to records that can change.
A deletion's total can include descendants and owned records beyond the selection.

A new search, filter, scope or context clears the selection; scrolling and sorting keep it.
Publications do not offer selection for writes, and bulk work requires jobs to be enabled.
If a preview is stale or exceeds a deployment limit, refresh it or narrow the selection.
[Follow the job](/docs/guide/use/follow-and-cancel-a-job/) to distinguish refused items from saved ones.

## See who changed what

A steward, model administrator, access administrator or integrator starts with the question:
one record, activity across a workspace, or a person's actions. [History](/docs/use/history/)
and [See who changed what](/docs/guide/use/see-who-changed-what/) connect the question to filters
and recorded before-and-after values. These reads respect access and do not undo changes.
For sign-in, access or administration events, continue to [Audit](/docs/administer/audit/)
and [find who changed something](/docs/guide/administer/find-who-changed-something/).
An empty filtered result calls for widening the filters, rather than assuming nothing changed.
