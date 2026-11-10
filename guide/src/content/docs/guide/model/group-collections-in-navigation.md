---
title: Group collections in navigation
description: Group collections and relation matrices in the sidebar, order entries and choose opening views.
reader: model-admin
---

Arrange an application's sidebar so people can find related collections and open a matrix directly.
Work in a draft with **Model authoring**. See
[Applications and views](/docs/model/applications-and-views/) for grouping rules.

## Create and open a group

1. Select the application. Choose **Add a navigation group…** from its menu, or **Navigation
   group…** from **Add** and choose **Application**.
2. Enter **Label** and choose whether it is **Folded when the sidebar opens**. Apply and check
   **Navigation groups** in the application panel. An empty group is allowed.
3. Choose the group's name in that table, or select it in the model pane. Its panel shows the
   application it belongs to, its starting state and entry count. The **Entries** table lists
   **Entry**, **Kind**, **Opens on** and **State**. A new group has no entries yet.

![Application navigation groups with their entries and starting states](/docs/screens/model-application-groups.png)

## Add collections and matrices

1. In the group panel, choose **Add to group…**. The dialog lists **Collections** and
   **Relation matrices** separately. Entries already in this group are left out.
2. Use **Search collections and matrices** to find entries by name. Tick all the entries you
   want to add. Beside each, **Top of the sidebar** means an ungrouped collection;
   **Inside** followed by a type's name means a matrix available through that row collection.
   **In** followed by a group name means the entry is in another group. Ticking it changes
   that note to **Moves from** followed by the old group name.
3. Review those moves, then choose **Add** with the selected count. The entries appear in
   the group's table. A collection or matrix belongs to at most one group in this application;
   choosing a new group replaces its old placement. This does not move records under a parent.
4. Check the result. Adding several entries at once is one saved step: one **Undo** takes
   the whole addition back.

![Add-to-group dialog with collections and relation matrices selected and their current locations](/docs/screens/model-group-add-entries-dialog.png)

From the application panel, **In no group:** lists ungrouped collections. Its **Add to a group…**
opens the same dialog with those collections ticked; choose **Group** and adjust the selection
before adding them.

You can also place one entry at a time. On a type listed in the application, choose
**Move to group…**. Select **Application** if offered, then **Group**.
**No group: the top of the sidebar** leaves the collection ungrouped. For a relation matrix,
find it in the application's **Views** table and choose **Move to group…** from its menu.
Choose a group, or the **No group: inside** option to keep it within its row collection.
Create a group first if the matrix's menu does not offer this action.

A grouped matrix has its own entry in the sidebar and on the group page. It uses the view's
name and a matrix symbol in its row type's colour, and opens the matrix directly. The row
collection stays where it was, and its view tabs still offer the matrix.

## Order entries and choose what opens

1. In **Entries**, drag a row by its grip to a new place, or open its menu and choose **Move up** or
   **Move down**. Collections and matrices share one order. The first entry cannot move up; the last cannot move down.
2. Choose **Move to another group…** to select a different **Group**. This action is available
   when another group exists. **Take out of the group** returns a collection to the top of the
   sidebar; a matrix returns to being available only through its row collection.
3. For a collection with several views, select its **Opens on** cell. Choose the view people
   should see when they open that collection, then **Save**. **Cancel** leaves it unchanged.
   With only one view there is no choice to edit. A matrix entry shows **Itself** and always
   opens that matrix.
4. Check the chosen view's name and kind in **Opens on**. It sets the collection's opening
   view in both the sidebar and the group page; people can still switch to its other views.
   Without a collection choice, refiroo uses the application's default view if it belongs to
   this collection, otherwise its table, otherwise its first view.

![Navigation group panel with a collection, a relation matrix and their opening views](/docs/screens/model-navigation-group-panel.png)

*Above: a group in the Graubünden model contains a collection and the Municipalities by system
relation matrix.*

## Adjust or remove the group

1. Use **Rename…** and **Start unfolded** / **Start folded** in the group panel to change its
   label and initial state. A person's later folding choice is remembered in their browser.
2. Drag a group's row by its grip in the application table, or use the group menu's **Move up** or
   **Move down**, to order groups. The table also lets you edit **Label** directly, and **Starts
   folded** is a box you click to change. **Change key…** is for unreleased keys only.
3. To remove the grouping, choose **Remove group**, read the confirmation and confirm.
   The confirmation says that its collections return to the top of the sidebar and, when the
   group holds relation matrices, that they go back inside their row type's entry; matrices
   remain available through their row collections. The views and records are kept. Check **Issues** and use **Undo** if needed.

![Navigation group menu with ordering and initial-state choices](/docs/screens/model-group-menu.png)

These are model defaults. The active workspace keeps its current navigation until the release
is activated. If an action says **Not applied**, correct the stated problem before retrying.
