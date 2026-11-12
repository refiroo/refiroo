---
title: Add a table, tree or mapping grid
description: Add a collection view and choose its hierarchy or matching relationship.
reader: model-admin
---

Work in a draft with **Model authoring**. A view gives people a way to work with existing
types; adding it does not create records. Read [Applications and views](/docs/model/applications-and-views/)
for the structural rules. For cells at row and column intersections, use
[Add a relation matrix](/docs/guide/model/add-a-relation-matrix/) instead.

## Start with the application

1. Select the application and choose **Add a view…** from its menu.
2. Choose **Kind of view**. Only suitable kinds are offered. A table needs a type; a tree
   needs a listed type that permits records without a parent; a mapping grid needs an optional
   non-containment relationship. Add those definitions first if the kind is missing.
3. Complete the form for that kind below. Enter **Name**, then **Add view**. Check **Views** and
   **Issues**. **Not applied** means the step was refused: read its reason and revise the
   choices. **Cancel** leaves the draft unchanged.

## Table

Choose **Table: the records of one type in rows**, select **Type**, and enter **Name**.
The application also lists the type if necessary. Columns, filters and sorting start from
its attributes. After adding it, select the type and open **Preview**, **Edit layout**, **Table**;
choose this view in **View** to [arrange it](/docs/guide/model/choose-table-columns-filters-and-sort/).

## Tree

1. Choose **Tree: records under the records that contain them**.
2. Select **Top of the tree**. These are types that can stand without a parent. The tree
   includes the types beneath them that this application lists. List missing child types in
   the application before adding the tree.
3. Set **Each record reads** to Name or a field shared by every shown type. **Second line**
   adds another shared field; **None** removes it.
4. Set **Records under a record are ordered by**. The form applies that one field to child
   types. It starts with Name. More detailed per-type or descending ordering needs a specialist.
5. For an on/off control, choose a common Yes or no field in **Switch a record on and off with**.
   Choose None for no availability action. A read-only field cannot support this action.
6. Enter the name and choose **Add view**. Review Issues. The form sets availability actions only; do not
   expect Create, Rename or Move just from choosing a tree. Ask a specialist to declare those
   separately when needed.

![Add a view with Tree selected and roots, label, second line, order and availability choices](/docs/screens/model-add-tree-view.png)

## Mapping grid

1. Choose **Mapping grid: records of one type matched to records of another**.
2. In **Matches records through**, choose the permitted relationship and its two types.
   Containment and required ownership are not offered.
3. In **Rows are**, choose the first or second type. This decides which end chooses records
   at the other end. Changing the relationship or row end resets the column and search choices
   to Name: select them again afterwards.
4. Choose and order **Columns of a row** and **Columns of the matched record**. Keep at
   least one in each list. Fields holding JSON are not offered. In **Columns of a row**,
   **From the parents** offers the types the row can stand beneath. Add one to show the name
   of each row record's nearest parent of that type, even several levels above it. The type's
   name heads the column. These parent names give context but are not searched when people
   search the grid's rows.
5. Choose **Find a record to match by**. Name and searchable attributes of the matched type
   are offered. This controls candidate searching, not a relationship’s eligibility rules.
6. Enter the name, choose **Add view** and check the resulting view and type listings. The new grid starts
   with 20 rows per page. A specialist can change that reading size.

![Add a view with Mapping grid selected, relationship, row end and display/search fields](/docs/screens/model-add-mapping-grid.png)

## Change or remove a view

In **Views**, open a tree or mapping grid’s menu and choose **Change…**. Choose **Save** and
review the saved step. On a tree, the form rebuilds actions from its availability choice:
review any actions a specialist had previously declared. New trees start with 50 records per
branch page; the change form preserves an existing reading size.

**Rename…** changes the label. **Remove view** removes the view and can stop listing types
only it needed. Review the confirmation and remaining listings. Stored data remains. Use
**Undo** to restore the draft step. Review the application’s **Default view** in Settings
when changing its views, then [install and activate](/docs/guide/model/install-and-activate-a-release/)
when the draft is ready. People keep the current views until activation.
