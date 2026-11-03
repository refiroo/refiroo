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

## Additional declared presentation

The model document can also choose a record header's title and subtitle, breadcrumbs and which
panels display children, relationships, hierarchy, tables or attributes. List panels can declare
columns, permitted filters, sort fields and page sizes. A hidden panel remains declared with its
visibility disabled. Main and Side, ordering and the panel title are separate settings.

Table, tree, mapping-grid and relation-matrix declarations each identify the types and relationships
they show. Trees also declare root and child structure and child ordering. Mapping grids declare
source and target columns and candidate search fields. Relation matrices declare their row
relationship, cell fields, column-parent relationship and actions. These are model document
settings, not extra forms in the layout editor. Use a specialist author for settings the visual
controls do not expose, and review validation before activation. Page-size settings choose how
much is read at once; they do not cap the total number of records people may browse.
