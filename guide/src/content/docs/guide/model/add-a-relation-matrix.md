---
title: Add a relation matrix
description: Choose row, cell and column types and the actions people can use in a matrix.
reader: model-admin
---

Open a draft with **Model authoring**. A matrix needs row records related to cell records that
stand under column records. See [Applications and views](/docs/model/applications-and-views/).

1. Select an application and choose **Add a relation matrix…** from its menu, or **Relation
   matrix** in its panel. The form has a preview beside it.
2. Choose **Rows**, then **Each cell shows**. Read the explanation of the relationship offered.
   If a type is missing, check its allowed relationships and the cell type's parent structure.
3. Choose **Columns**. There is one column per record of a type the cell records sit under.
   Choose **Column heading** to identify those column records clearly.
4. Choose and order **Fields in a cell** and **Row columns**. Use the add, remove and up/down
   controls to inspect the intended order. The first text or number cell field is used for the
   cell display; if none is available, it uses the record name.
5. Set **What people can do in a cell** from the offered **Create**, **Edit**, **Link existing**
   and **Unlink** choices. Availability depends on the declared structure. A checked action
   still needs the person's record or relationship permissions at runtime.
6. Enter **Name**, inspect the preview and choose **Apply**. Review **Issues** before installing.
   A preview is a design aid, not proof that every user has permission to perform its actions.
7. For an existing relation matrix, open its row in **Views** and choose **Change…**. Use
   **Rename…** for its label or **Remove relation matrix** to remove the view. Removing the
   view does not delete the data it displayed. **Undo** can restore the draft step.

![Relation matrix choices with ordered cell fields and a preview](/docs/screens/model-view-matrix-dialog.png)

*Example: Municipality rows connect to System code cells, which stand under System columns.*

A **Not applied** notice leaves the attempted change unapplied; read its reason and correct
the structure or choices. Saving this view in a draft does not change the live application.

Adding a matrix also adds any type listings it needs to the application in the same step.
Records retain their owning applications. Removing the matrix can remove listings needed only
by that view; a released listing in use can require migration. Inspect the removal confirmation
and Issues rather than assuming the view is the only affected definition.
