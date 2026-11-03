---
title: Group collections in navigation
description: Add labelled sidebar groups, place collections and choose their starting state.
reader: model-admin
---

Work in a draft with **Model authoring**. See
[Applications and views](/docs/model/applications-and-views/) for grouping rules.

1. Select the application. Choose **Add a navigation group…** from its menu, or **Navigation
   group…** from **Add** and choose **Application**.
2. Enter **Label** and choose whether it is **Folded when the sidebar opens**. Apply and check
   **Navigation groups** in the application panel. An empty group is allowed.
3. On a type listed in the application, choose **Move to group…**. Select **Application** if
   offered, then **Group**. **No group: the top of the sidebar** leaves the collection ungrouped.
4. Inspect the group's collections. A collection belongs to at most one group in this application;
   selecting a new group replaces its old placement. This does not move records under a parent.
5. Use the group menu's **Rename…**, **Start unfolded** / **Start folded**, **Move up** or
   **Move down** to adjust its label, initial state and order. The application table also lets
   you edit **Label** and **Starts** directly. **Change key…** is for unreleased keys only.
6. To remove the grouping, choose **Remove group**, read the confirmation and confirm. Its
   collections remain available outside the group. Check **Issues** and use **Undo** if needed.

![Application navigation groups with their collection counts and starting states](/docs/screens/model-application-groups.png)

![Navigation group menu with ordering and initial-state choices](/docs/screens/model-group-menu.png)

These are model defaults. The active workspace keeps its current navigation until the release
is activated. If an action says **Not applied**, correct the stated problem before retrying.
