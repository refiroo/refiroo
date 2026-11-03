---
title: Choose table columns, filters and sort
description: Set the columns, filters and initial ordering of a declared table view.
reader: model-admin
---

Work in a draft with **Model authoring**. Select a type, **Preview**, **Edit layout**, then
**Table**. See [Record pages and tables](/docs/model/record-pages-and-tables/) for model defaults.

1. Find the table view to arrange. If the draft declares no table view, this tab has nothing
   to configure; the visual editor has no separate create-table-view form.
2. Choose **Columns**. Select the fields to show and apply. Choices include the parent where
   applicable, attributes and relationships. Include enough information to distinguish rows.
3. Reorder column frames by their grips, or open a column menu and use **Move left** or
   **Move right**. **Remove column** takes it out of the view, without deleting its values.
4. Choose **Filters** and select the fields people may filter by. Apply and check the list.
   This defines the available filters; it does not filter all users' data to a selected value.
5. Choose **Default sort**. Select **Sorted by** from the allowed fields and use **Descending**
   to reverse its direction. Apply and read the resulting arrow on the sort control.
6. Inspect the preview with real records. An empty table explains what it will show; it does
   not mean that the view is broken. Review **Issues** and use **Undo** for an unwanted draft step.

![Columns dialog with available table fields and relationships](/docs/screens/model-view-columns-dialog.png)

![Table default sort dialog with field and descending choices](/docs/screens/model-layout-sort-dialog.png)

The live collection keeps its existing layout until activation. Table density and tree or
mapping-grid configuration have no form in this layout editor.
