---
title: Applications
description: Understand the collections and the kinds of view an application can offer.
reader: steward
---

Open an application to reach the records and views you need in the current workspace.
Follow [Open an application](/docs/guide/use/open-an-application/) for the steps.

An **application** groups record types and views. Its name, collections and starting view come
from the workspace's model. Applications are not fixed modules of refiroo: a model can rename,
replace or remove them. Any application can offer any of the view kinds when the model
declares the structure that view needs.

## Collections and views

Choose an application in the top bar, then a collection in the sidebar. A collection can have
several views, shown as tabs. Changing tabs changes how you inspect the records; it does not
copy them. The model can choose which view opens when you select a collection in the
sidebar or on a group page. That choice may differ from the application's starting view;
use the tabs to switch to another view when needed. **Browse records** offers another route to individual records through their hierarchy.

![An application with collections, record browsing and a table of records](/docs/screens/app-network.png)

*Above: Network in Graubünden shows the Stops table and the collections declared by its model.*

| View | What you can do |
| --- | --- |
| Table | Search, filter and sort records, then open one. See [Records](/docs/use/records/) and [Find records](/docs/guide/use/find-records/). |
| Tree | Browse parents and children and move records to an allowed place. See [Hierarchies](/docs/use/hierarchies/) and [Arrange records in a tree](/docs/guide/use/arrange-records-in-a-tree/). |
| Mapping grid | Inspect connections, missing connections and multiple targets. See [Mapping grids](/docs/use/mapping-grids/) and [Map codes between systems](/docs/guide/use/map-codes-between-systems/). |
| Relationships table | List one relationship's records and its own values (a weight, a flag) as rows. Declared by the model; in the model contract (`relationTable`). |
| Relation matrix | Compare related records across columns and find missing connections. See [Relation matrices](/docs/use/relation-matrices/) and [Fill in a relation matrix](/docs/guide/use/fill-in-a-relation-matrix/). |

![A collection with a table and two mapping views](/docs/screens/app-systems.png)

*Above: System codes in Systems offers a table and mapping views. These are choices in the
example model, not features reserved for this application.*

A missing tab may mean the model does not declare that view. Ask a model administrator if you
need a different presentation. An empty table means no records match the current context and
filters; a loading error needs a retry before you can draw that conclusion.

## Shared workspace, different ways in

Applications in one [workspace](/docs/use/workspaces/) use that workspace's data. Relationships
may connect records across applications where the model allows it. The same record can appear
in a table, a hierarchy, a mapping grid and a relation matrix without becoming separate records.

The banner identifies **Live**, a **Change set**, or a publication. Live edits apply immediately;
a change set holds proposed changes; a publication is read-only. Check that context before editing.
Your roles determine which actions are offered. A declared view does not grant permission to
change its records. See [Record permissions](/docs/use/records/#who-may-read-and-change-records).

For configurations of these capabilities, see [The example data](/docs/examples/the-example-data/)
and [The starter model](/docs/examples/the-starter-model/).

## Collection groups and record pages

Ungrouped collections appear first. Expand or fold a labelled group with its arrow; your choice
is remembered in this browser. The model sets whether a group starts folded on your first visit. A folded group is marked when it contains the open collection.
Choose the group's name to open its page, search entries by name and open one in the same
Live, change-set or publication context.

A relation matrix the model places in a group has its own entry, named after the matrix's
view. Its matrix symbol uses the row collection's colour. Choose it to open the matrix
directly, from either the sidebar or the group page. The row collection stays in the sidebar
and still offers the matrix among its view tabs. A matrix without its own group entry is
available through that collection. Groups have one level and show no record counts.

![Application sidebar with a relation matrix listed alongside a collection in a group](/docs/screens/app-navigation-matrix-entry.png)

*Above: the Graubünden example model places Municipalities by system in a navigation group.
The matrix opens directly; its row collection is still available.*

A record page combines panels for fields, children, relationships, tables, hierarchy and history.
The model chooses their arrangement. If it declares no detail layout, refiroo provides a default.
The collection views above are the supported kinds; dedicated form and dashboard views are
not available.

The group page's **Find a collection or matrix** searches collection and matrix names. **This group has no collections or relation matrices.**
describes an empty group, rather than no records in its collections. For the shared table
controls, see [Lists, search and filters](/docs/use/lists-and-filters/).

On a wide screen, each application has a coloured tile in the top bar. The open application
is underlined; hovering over its tab shows the model's description. The product mark returns
to **Home**, and the gear opens **Settings**. On a phone, choose the application from the band
beneath the top bar instead. See [Appearance and devices](/docs/use/appearance-and-devices/).

If a group says **No collection or relation matrix in this group matches “…”**, clear **Find a collection or matrix**
or press Escape in that search field. This search covers collection and matrix names, not records.
Opening a collection result uses its chosen starting view; opening a matrix result goes straight
to that matrix. Both keep the current data context.

### Find a list in the sidebar

When an application has more than ten sidebar entries, **Find a list** appears under
**Collections**. Collections and relation matrices with their own sidebar entry count together,
including entries in folded groups. With ten entries or fewer, this search is not shown.

Type part of a list's name. The search ignores upper and lower case and matches your words
as one phrase within a name, in the order you type them. Reversing the words does not match
the same phrase. Matching letters appear in bold. It searches entries in every group and
those in no group, rather than the names of groups or records. The count beside **Collections**
shows the total, such as **25 lists**, then the matching count, such as **3 of 25**, while you
search. Screen readers announce count changes without interrupting you.

Groups with matches open and show only those entries; groups without matches disappear.
Their fold buttons are unavailable during the search. Choose a result, or press **Enter** in
the box to open the first match. The hint **Enter opens the first match · Esc clears** reminds
you of these keys. If **No list matches** appears, shorten or clear the text. Press **Esc** in
the box to clear it and restore each group's previous fold choice.

**Find a record**, under **Browse records**, searches records instead. The group page's
**Find a collection or matrix** searches only that group's entries.
