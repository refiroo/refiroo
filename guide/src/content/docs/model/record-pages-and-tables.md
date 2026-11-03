---
title: Record pages and tables
description: Preview draft screens over live records and arrange panels, fields and table defaults.
reader: model-admin
---

Design how people read a type before activating its model. **Preview** uses draft definitions
with live records from a chosen workspace. It writes nothing, and data-changing controls are
disabled. You need **Model authoring**. Follow [Preview a type](/docs/guide/model/preview-a-type/).

## Preview states

Choose a **Workspace** and **Record**, or **Show an empty record**. A new type may have no live
records yet; an empty record helps review its fields. Invalid drafts cannot be previewed:
**Show issues** takes you to the definitions to repair. This check concerns model validity,
not compatibility with all stored data.

![Draft preview showing workspace and record choices](/docs/screens/model-type-preview.png)

## Record pages

**Edit layout**, **Record page** arranges panels in **Main** and **Side**. Panels may contain
fields, children, relationships, hierarchy or other declared content. A panel has a title, order,
region and visibility. Hiding keeps it declared; removing takes it off the page. Neither deletes
stored records or field values. A new field group moves selected fields into a titled panel.
A type without a page offers **Declare its page**.

Menus provide alternatives to dragging for moving panels and fields. **Columns…** changes the
columns of supported list panels; **Sort…** is offered where the panel declares sort fields.
The editor does not offer a form for every panel kind or configuration the model can declare.
Follow [Edit a record page](/docs/guide/model/edit-a-record-page/).

## Tables

The **Table** tab changes an existing table view's ordered columns, available filters and
initial sort. These are model defaults for the collection, not a saved search by one person.
The default sort must be among the view's allowed sort fields. Columns can include identifying
fields, parents and relationships where offered.

![Table layout showing column order and the Columns, Filters and Default sort controls](/docs/screens/model-layout-table-tab.png)

An empty table says what it will show. **The draft declares no table view** means there is no
view to arrange in this editor. There is no table-density, tree-view or mapping-grid layout form.
Specialist authors maintain additional definitions through the [JSON view](/docs/model/json-view/).
Follow [Choose table columns, filters and sort](/docs/guide/model/choose-table-columns-filters-and-sort/).

Every saved layout change is a draft history step. Review it with more than one record and check
Issues before [installing and activating](/docs/guide/model/install-and-activate-a-release/).

For tree, mapping-grid and relation-matrix settings, see
[Applications and views](/docs/model/applications-and-views/). Use a specialist author for
settings beyond the visual layout controls and validate the draft before activation.

## Table fields, filters and relationship columns

A table needs at least one column, filter field and sort field, with no repeats in each list.
Its initial sort must name one of its declared sort fields. All ordinary non-JSON data columns
sort from their headers; the declared sort list also supplies options for fields without a column.
A view reads 1–100 rows per page. This is a reading size, not a total-record limit.

A relationship column shows related records as chips in name order, then **+N more** when they
do not fit. It combines the permitted type pairs for that relationship at the displayed end.
There is no fixed limit on the number of relationship columns: each must name an available
relationship or related field, and the same column cannot appear twice. People can hide columns
in **Display**; hidden relationship columns are no longer read for that table.

A relationship column can instead show a field of the related record, or a field of its ancestor.
Missing values display as a dash. Such a field column cannot sort. A column of related record
names can sort only when it represents one permitted pair and at most one related record per row.
Columns with several possible targets do not have an unambiguous single-record sort.

The view can offer a relationship filter for records linked to any selected records, to none,
or to any record. Choose the relationship itself for that filter; a field of the related record
is not a relationship filter. Ordinary attribute filters require a filterable, non-JSON field.

Relationship columns belong in table views and children or table panels. They are not extra
columns for trees, grids, matrices, relationship panels or record headers. The visual table
editor arranges existing offered fields; ask a specialist to declare additional supported
relationship-field columns where they are not offered.

## What each panel can show

A shared type can have a different record page in each application. Each application declares
at most one page for that type. Without an explicit page, refiroo derives fields and hierarchy
context, plus children and relationships from the type's bindings. Declaring a page lets you tailor it to the task.

| Panel | What its declaration selects |
| --- | --- |
| Attributes | The identifying or attached fields to display. Group fields with separate panels. |
| Children | One or more types the current record can contain, their columns and reading size. |
| Relations | Which relationships, the incoming, outgoing or both directions, columns and initial order. |
| Table | A type listed in the application, columns and reading size; optionally only direct children of the open record. |
| Hierarchy | Whether to show the parent, ancestors or both. |

Children and table panels default to name as their column and 20 rows per page; the declared
reading size can be 1–100. A relationships panel defaults to both directions, name and type
columns, and showing the relationship label. That label can be hidden when it would repeat the
same meaning on every row. An ancestor column identifies the containing record of a declared
type, even when intervening levels stand between them.

Relationship panels sort each data column and the relationship label from the header. Additional
sort options can include name, type, relationship, a non-JSON field of a related type, or an
ancestor type when the panel reaches exactly one related type. Records without the selected
field sort last. Initial order defaults to name; a declared order may be descending. An ancestor
sort needs a type the related record can sit under. Live timestamps are not relationship-panel
sort options.

A record header defaults to the record name and showing its type. Its title can use another
available field, and an optional subtitle can show a second field. Breadcrumbs independently
include application, type and ancestors, all shown by default. These settings give context;
they do not change a record's identity or parent. They need a specialist author where the visual
layout form does not offer them.

Panels start visible in **Main** unless declared otherwise. Their order is local to **Main** or
**Side**. Validation checks distinct panel identities, attached fields, allowed relationships,
containment, application membership and page sizes. If Issues names an invalid panel or header,
correct the declaration before installation; hiding it is not a substitute for a valid reference.
