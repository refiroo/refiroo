---
title: Arrange applications and views
description: Create an application, list shared types and choose the next navigation or layout task.
reader: model-admin
---

Arrange a draft so people can find the types and views they need. You need **Model authoring**.
Any application can use a view when its structure fits. See
[Applications and views](/docs/model/applications-and-views/) for listings and view rules.

1. In the model pane, choose **Add**, **Application…**. Enter **Name** and, if useful,
   **Description**, then apply. In an existing application, select its row instead.
2. Check **Object types** and **Stands** to see what it lists and where records belong. Use
   **Object type** to create a definition, or **List an existing type…** to list a shared type
   here. Check the intended type before applying: listing it does not copy its records.
3. Open a listed type's menu. Use **Stop listing in this application** where offered to remove
   only that listing. For containment or a move between applications, use
   [Split, merge and move types](/docs/guide/model/split-merge-and-move-types/) instead. Released
   listings and placements can be refused when data uses them; read the impact before proceeding.
4. Inspect **Views**, including each view's kind, **Shows** and state. **Rename…** changes a
   view's label. To add or configure a relation matrix, follow
   [Add a relation matrix](/docs/guide/model/add-a-relation-matrix/).
5. Use [Group collections in navigation](/docs/guide/model/group-collections-in-navigation/) for
   sidebar sections, their order and initial folded state. This does not change record parents.
6. Use [Preview a type](/docs/guide/model/preview-a-type/), then
   [Edit a record page](/docs/guide/model/edit-a-record-page/) or
   [Choose table columns, filters and sort](/docs/guide/model/choose-table-columns-filters-and-sort/)
   for screen layout. The visual editor does not configure tree or mapping-grid views.
7. Check **Issues** and review the saved steps before installing. A **Not applied** notice means
   the attempted step was refused; correct its named problem. **Undo** reverses unwanted saved work.

![Application editor listing types, views and navigation groups](/docs/screens/model-editor-application.png)

![Application view list with table, tree, mapping-grid and relation-matrix kinds](/docs/screens/model-editor-systems-views.png)

*Example: an application in the Graubünden model declares all four view kinds. These are choices
in that model, rather than features reserved for the subject of that application.*

The live workspace keeps its current navigation and layouts until the release is activated.
