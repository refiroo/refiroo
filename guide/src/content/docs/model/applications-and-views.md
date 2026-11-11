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

Navigation groups have a **Label**, ordered entries (collections and relation matrices) and an **Open**
or **Folded** starting state. A collection, or a relation matrix, can belong to only one group in an
application. A relation matrix placed in a group has an entry of its own, named after the view, and its
row type's entry stays. The matrix symbol uses the row type's colour, and opening the entry
goes directly to the matrix. The matrix also stays among the row collection's view tabs. Without
a group placement, it is available through that collection only. Ungrouped collections appear
at the top. An empty group is valid. Grouping does not change parents, data access or the type's
identity. Follow [Group collections in navigation](/docs/guide/model/group-collections-in-navigation/).

Navigation groups have one level: a group cannot contain another group. Its collection page
lets people search collection and matrix names; it does not show a record count for each entry.
Only collections with a view in this application can be placed in its groups. Group labels
and ordering change navigation without requiring a data migration.

A new navigation group starts open unless **Folded when the sidebar opens** is selected.
A person's later folding choice is remembered in their browser. Within an application, each
group has its own key, and a collection cannot be declared in two groups at once. If validation
names a collection outside the application, add a suitable view there or remove that group entry.

### The group panel

Choose a group in the model pane, or its name in the application's **Navigation groups**
table, to open its panel. It shows the application, starting state and entry count. **Entries**
lists collections and matrices together, in their sidebar order, with **Entry**, **Kind**,
**Opens on** and **State**. The application's group table also lists both kinds in **Entries**.

**Add to group…** lets you search and select several collections and matrices in one dialog.
Their location notes distinguish ungrouped collections, matrices inside a row collection and
entries in another group. Selecting an entry from another group moves it rather than copying
it. Entries already in the destination group are omitted. The whole addition is one history
step, so one **Undo** reverses it. In the application panel, **In no group:** offers
**Add to a group…** with the ungrouped collections already selected.

An entry's row menu offers **Move up**, **Move down**, **Move to another group…** and
**Take out of the group** where applicable. Taking a matrix out removes its separate entry;
it keeps the view in the row collection. A matrix's menu in the application's **Views** table
also offers **Move to group…** when a group exists. The group panel has **Rename…** and
**Start folded** / **Start unfolded**; the group menu orders or removes the group itself.

### A collection's opening view

**Opens on** chooses which of a collection's views opens from its sidebar entry or the group
page. Edit the cell in the group panel when the collection has more than one view, then
**Save**. The choice belongs to that collection in this application; it does not change
another collection's opening view or remove any view tabs. A separate matrix entry always
opens itself and shows **Itself** in this column.

Without a collection choice, refiroo uses the application's **Default view** if it is one of
that collection's views, otherwise its table, otherwise its first view. Choosing that same
fallback in **Opens on** returns the collection to following the default rather than keeping
a separate choice.

## Views

| View | What people use it for |
| --- | --- |
| Table | Read a collection with declared columns, filters and sorting. |
| Tree | Browse and move records through a declared hierarchy. |
| Mapping grid | Connect source and target records through a relationship. |
| Relation matrix | Read or edit related cell records at row and column intersections. |

A type created through the editor receives a table view. **Views** lists each view's kind,
what it shows and its state. Use its menu's **Rename…** for a label change.
Choose **Add a view…** in the application’s menu to add a Table, Tree, Mapping grid or
Relation matrix. The kind list offers only views for which the model has suitable types and
relationships. Existing trees and mapping grids have **Change…**; table layouts are arranged
from the type’s Preview. Follow [Add a table, tree or mapping grid](/docs/guide/model/add-a-view/).

Application **Settings** has **Default view**, the view that opens first. Choose an existing
view and Save. A collection's **Opens on** choice takes precedence when opening that collection.
This changes the starting lens, not which types users can access. Icons,
colours and free-form presentation settings still need the [JSON view](/docs/model/json-view/).

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

## Application settings

The visual **Application…** form includes **Name** and **Description**. In an existing
application, **Settings** lets you change **Default view**. Application and type icons and
existing descriptions need a specialist in the [JSON view](/docs/model/json-view/).
Removing an application is a structural model change; retiring a workspace or release is a
separate administrative task. Check the removal confirmation for types only that application lists.

## Collections and their lenses

Views of the same source type appear as lenses of one collection. A table's source is the type
it lists. A mapping grid's source is the end chosen as its direction; a relation matrix's source
is its row type. A tree belongs to its first declared root type. Adding a second view for one
source type adds a way to work with that collection. Placing a relation matrix in a navigation
group adds a direct entry for that view while keeping the shared row collection.

## Mapping-grid declarations

A mapping grid chooses one permitted relationship and its two endpoint types. In the outgoing
direction its rows are sources choosing targets; in the incoming direction its rows are the
other end and the choices run back towards the source. Choose the direction before choosing
row and target-display fields. Both field lists must be non-empty and contain no repeats.
**Columns of a row** offers the row's own fields and, under **From the parents**, the types
it can stand beneath. Choosing a parent type adds a column headed by that type's name. It
shows the name of the row record's nearest parent of that type, including a parent several
levels above it. This gives context without changing the records being mapped. Row search
looks at source names and the source's displayed attributes; it does not search parent names.
**Columns of the matched record** offers that record's own fields, without parent columns.
Candidate search uses names or searchable attached fields of the type being chosen.

The configured relationship must be an optional association. Containment and required ownership
cannot be used, because replacing a mapping must not change a record's parent or orphan a
dependent. Saving one selected mapping replaces that source's mapping set; it does not change
the underlying relationship's cardinality for other clients.

A grid's model sets a page size of 1–100. The parent scope and coverage choices people select
while using it are temporary filters, not model settings. **Mapped**, **Unmapped** and
**Ambiguous** describe coverage for the configured relationship. **Add a view…** and the view’s **Change…** set its relationship, row end, display columns
and candidate search fields. New grids read 20 rows per page; changing that reading size
still needs the specialist view.

## Relation-matrix rules

A matrix uses one non-containment relationship, in either direction, between row and cell types.
The row, cell and column types must all be listed in the application. Its rows include records
of the row type in the workspace even when another application owns those records. Columns are
records of a type that can contain the cell type, directly or through intervening levels. A cell
record belongs to its nearest ancestor of that column type.

Choose unique, non-empty lists of **Row columns** and **Fields in a cell**. Row columns can include
fields of the row and its ancestor context. The column heading is the column record's name or a
non-JSON field attached to its type. Cell fields must be attached to the cell type. A specialist
can also declare row-search fields, using the name or searchable attached fields, and a page
size of 1–100.

| Cell action | Why it may be unavailable |
| --- | --- |
| Create | Every required cell field needs to be supplied or have a default. The cell must not require an additional owner relationship that the matrix cannot supply. |
| Edit | At least one displayed cell field must be editable. |
| Link existing | The chosen records must fit the binding, its candidate rules and number limits. |
| Unlink | A required owner relationship cannot be removed on its own. |

With no enabled cell actions, the matrix is read only. The form offers suitable actions; the
model's validation also rejects impossible declarations. Enabled actions still require each
person's data permissions. If Create is missing despite a default on a required field, ask a
specialist to inspect the declaration: the visual form checks that required fields are selected.

Uniqueness and conditional activity come from the relationship's rules, not a second rule on
the view. They describe the relationship's target end. An incoming matrix does not apply those
target-end rules to its cells, so it has no inactive or uniqueness-conflict states from them.
To inspect those states, use a suitable outgoing matrix. The matrix shows at most five cell
records as a preview with the full count; open a cell to inspect the rest.

## Tree declarations

A tree starts with parentless records of its root types. Every root type must also be a node
type and allow top-level creation. All shown node types must be listed in the application and
reachable from a root through containment using types the tree shows. A missing intermediate
type prevents that branch from being a valid tree. Recursive containment can show several levels
of the same type.

The main label is the name or a non-JSON field attached to every node type. An optional second
field can show identifying information, type, path, timestamps or another non-JSON field shared
by the node types. Child ordering is declared per type; without an entry, children sort by name.
Descending order is supported. Timestamp ordering falls back to name in change sets and
publications, which do not keep those live-only timestamps. Branches read 1–100 records at a time.

The declaration can offer creating children, renaming, moving and changing a Yes/No availability
field. With no actions it is read only. Create and Move need a containment possibility among
shown types. Rename cannot target a read-only label field. Availability needs an editable Yes/No
field attached to every node type, and that field cannot be declared without the availability
action. These choices enable controls; they do not grant permissions.

At runtime a node's menu offers allowed actions; F2 renames where enabled. Creating a child
offers only shown types the parent can contain. Move lists possible parents with unsuitable
choices disabled and their reasons. Search and opening a record reveal its path by loading
the relevant branches. **Add a view…** and **Change…** offer roots, a label, a second line, one shared child-order
field and an availability field. The editor includes reachable contained types already listed
in the application. New trees read 50 records per branch page. The form does not offer
separate ordering for each type, descending order, page size or the create, rename and move
actions: a specialist maintains those in the JSON view. Applying Change rebuilds the tree’s
action choices from the availability selection, so review previously declared actions afterwards.

<!-- Inventory trace: reader-facing controls are explained above.
applications
applications[].defaultView
applications[].description
applications[].icon
applications[].key
applications[].name
applications[].navigation
applications[].navigation.groups
applications[].navigation.opens
applications[].navigation.groups[].collapsed
applications[].navigation.groups[].collections
applications[].navigation.groups[].key
applications[].navigation.groups[].label
applications[].objectTypeKeys
applications[].views
applications[].views[].config
applications[].views[].config.actions
applications[].views[].config.availabilityField
applications[].views[].config.candidateSearchFields
applications[].views[].config.cellActions
applications[].views[].config.cellFields
applications[].views[].config.cellObjectTypeKey
applications[].views[].config.childSort
applications[].views[].config.columnLabelField
applications[].views[].config.columnObjectTypeKey
applications[].views[].config.columns
applications[].views[].config.defaultSort
applications[].views[].config.direction
applications[].views[].config.filterFields
applications[].views[].config.fromObjectTypeKey
applications[].views[].config.labelField
applications[].views[].config.objectTypeKeys
applications[].views[].config.pageSize
applications[].views[].config.relationTypeKey
applications[].views[].config.rootObjectTypeKeys
applications[].views[].config.rowColumns
applications[].views[].config.rowObjectTypeKey
applications[].views[].config.searchFields
applications[].views[].config.secondaryField
applications[].views[].config.sortFields
applications[].views[].config.sourceColumns
applications[].views[].config.targetDisplayColumns
applications[].views[].config.toObjectTypeKey
applications[].views[].key
applications[].views[].name
applications[].views[].objectTypeKey
applications[].views[].type
operation:add-group
operation:application-rename
operation:application-key
operation:application-add-type
operation:application-add-view
operation:application-list-type
operation:application-add-group
operation:application-remove
operation:view-rename
operation:view-matrix-change
operation:view-tree-change
operation:view-grid-change
operation:view-remove
operation:view-matrix-remove
operation:group-add
operation:application-group-add
operation:entry-up
operation:entry-down
operation:entry-move
operation:entry-out
operation:view-group
operation:group-rename
operation:group-fold
operation:group-key
operation:group-up
operation:group-down
operation:group-remove
-->
