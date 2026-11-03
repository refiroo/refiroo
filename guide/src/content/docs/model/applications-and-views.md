---
title: Applications and views
description: Organise shared types into applications, navigation groups and declared views.
reader: model-admin
---

Applications give people named places to work. A model decides which types and views each
application lists. Any application can use any supported view when its structure fits; an
application's name does not give it special capabilities. You need **Model authoring** to edit
these definitions. Start with [Arrange applications and views](/docs/guide/model/arrange-applications-and-views/).

## Listings and navigation

Select an application to inspect **Object types**, **Views** and **Navigation groups**.
The type table shows where records stand and their attribute and relation counts. **List an
existing type…** adds another listing of a shared definition; it does not copy records.
**Stop listing in this application** removes a listing where allowed. Moving containment or
removing the definition has a different effect; see [Types](/docs/model/types-attributes-relations/).

![Application panel with its object types, views and navigation groups](/docs/screens/model-application-panel.png)

Navigation groups have a **Label**, ordered collections and an **Open** or **Folded** starting
state. A collection can belong to only one group in an application. Ungrouped collections appear
at the top. An empty group is valid. Grouping does not change parents, data access or the type's
identity. Follow [Group collections in navigation](/docs/guide/model/group-collections-in-navigation/).

## Views

| View | What people use it for |
| --- | --- |
| Table | Read a collection with declared columns, filters and sorting. |
| Tree | Browse and move records through a declared hierarchy. |
| Mapping grid | Connect source and target records through a relationship. |
| Relation matrix | Read or edit related cell records at row and column intersections. |

A type created through the editor receives a table view. **Views** lists each view's kind,
what it shows and its state. Use its menu's **Rename…** for a label change.
The browser can arrange existing table columns, filters and sort and create, change or remove
relation matrices. It has no tree-view or mapping-grid configuration form, general table-view
creation form, icon or colour editor. Specialist authors use the [JSON view](/docs/model/json-view/)
for settings beyond the visual controls, including application descriptions, default view,
icons, colours and other declared presentation settings.

## A relation matrix needs a particular structure

Rows must connect to cell records; the cell records stand under column records. The form offers
only suitable choices. **Column heading**, ordered **Fields in a cell** and **Row columns**
determine what is shown. A cell displays its first text or number field, or its record name.
**What people can do in a cell** enables offered actions but never grants access by itself.

![Relation matrix form beside its structural preview](/docs/screens/model-matrix-view-dialog.png)

[Add a relation matrix](/docs/guide/model/add-a-relation-matrix/) walks through the form.
Do not confuse it with the editor's **Relationship matrix**, which defines permitted type pairs.
[Record pages and tables](/docs/model/record-pages-and-tables/) covers layout settings. A draft's
navigation and views become active only when its release is applied to the workspace.

Application declarations can also carry a description, a starting view, presentation settings
and an application state. The visual **Application…** form includes **Name** and **Description**;
there is no general application-settings or state form. An application state is separate from
retiring a workspace or an installed release. Have a specialist maintain settings outside the
listed controls and validate the draft; the presence of a setting in a document does not imply
that the editor offers a button for it.
