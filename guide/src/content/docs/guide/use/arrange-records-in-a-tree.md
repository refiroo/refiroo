---
title: Arrange records in a tree
description: Browse branches, rename a record and move it to an allowed parent.
reader: steward
---

Use a tree view to inspect where records belong and move them to an allowed place. See
[Hierarchies](/docs/use/hierarchies/) for parents, type rules and the effect on descendants.

## Browse a branch

1. Open an application in the current workspace. Choose a collection and its tree view, where
   offered. Check the heading and the banner: **Live**, a named change set or a publication.
2. Expand the arrow beside a type group or record. Its children appear below it. Continue
   down to the branch you need; collapse an arrow to hide that branch without changing data.
3. Use **Find a record** to search, checking names, types and paths before selecting a match.
   Clear the search to return to browsing. A branch loads more records as you scroll.
4. For keyboard browsing, focus the tree and use arrow keys to move through it and expand
   or collapse branches. Open the record when you need its full fields and relationships.

![A hierarchy expanded through several record types to a municipality's stops](/docs/screens/tree-geography-chur.png)

*Above: Geography in Network is expanded through Graubünden, Plessur and Chur. Stops appears
as a type group above the stop records.*

![A hierarchy with records nested under others of the same type](/docs/screens/tree-modes.png)

*Above: Modes groups Train and Tram under Rail-bound, and Bus under Road. The record type is
Mode at both levels; a tree is not limited to a chain of different types.*

If a branch reports a loading failure, retry it. A failed read does not mean the parent has
no children. If the tree is empty, check its workspace, context and search before adding data.

## Move a record

1. Choose **Live** for an immediate move, or [open a change set](/docs/guide/use/prepare-and-publish-a-change-set/)
   to stage it. Check the banner and the record's current ancestors.
2. Open the record's **…** menu and choose **Move to…**. You can also open the menu with a
   right click or **Shift+F10** while the record has focus. The dialog names the record and
   shows **Now in** followed by its current path.
3. Search by name for the new parent. Check the path below each candidate to distinguish
   repeated names. Select its radio button; typing a name alone is not a selection.
4. Use **Top level** only if you intend to remove the parent and the choice is available.
   Unavailable destinations state their reason. If no destination matches, shorten the search
   and check the model's allowed placements before continuing.
5. Check the selected destination and choose **Move to** followed by its name, or
   **Move to the top level**. Before selection the button reads **Move**. Wait for completion,
   then inspect the new branch or the record's path. The descendants move with the record.
   **Cancel** leaves its placement unchanged.

![A move dialog showing the present path, candidate parents and an unavailable top level](/docs/screens/tree-move-dialog.png)

*Above: Move 85 Garage Chur shows its current place under Graubünden / Plessur / Chur and offers
other municipalities. Top level explains why it is unavailable in this tree. The dialog was cancelled.*

A choice marked **Becomes** changes the record's type in a change set. Its button opens a type
change preview instead of making an ordinary move; review the resulting fields and missing
values before applying it. Cancel if you only intended to change the parent.

Dragging a record onto a parent is another way to move it. Review the destination and any
confirmation before proceeding. On touch screens, hold the record still until it lifts, then
drag. Beginning to move your finger before it lifts scrolls the tree instead.

## Add the first top-level record

In an editable tree, choose **Add …** for the intended top-level type in the header or empty
view. Complete the new record’s name and required fields, then choose **Create**. This form
has no parent field: the record starts at the top of this tree. Add children from its menu
afterwards. The action appears only for types allowed at the top, when the view allows creation
and your permissions allow writing that type.

## Rename or add a child

1. Open the record's menu and choose its rename action, or press **F2** on the focused record.
   Enter the intended name and confirm the rename. Check the new label; the record retains
   its identity and connections.
2. To add within a parent, choose the menu's add-child action for an offered type. Complete
   the new record form, check its parent and choose **Create**. If the needed type is absent,
   ask a model administrator about the permitted children.
3. Where an availability action is offered, use it only to change whether the record is
   available under that model's rule. It does not delete the record.

If a move or rename is refused, read the reason and review the current record before retrying.
Another person's change can make your version stale. If editing controls are absent, check
[permissions](/docs/use/records/#who-may-read-and-change-records) and the configured actions;
publications and retired workspaces are read-only. For permanent removal and its impact, see
[Deleting a record](/docs/use/records/#deleting-a-record).

## Move a selection together

1. In the sidebar tree or tree view, use Cmd or Ctrl to select individual records, or Shift
   for a range. With the keyboard, use Ctrl+Space and Shift+arrows. Escape clears the selection.
2. Open the selection's menu with right click or Shift+F10 and choose **Move to…**, or drag
   the selected records together onto the new parent.
3. Read the destination and confirmation for the whole selection. Confirm only when every
   selected record belongs there. If any cannot move, none moves; correct the selection or
   destination and try again.

In a long branch opened partway down, use **Show earlier records** to read those above it.
For **Change type…**, **Insert level above…**, **Remove this level…** or
**Change type of all … in here…**, first open a change set. Review the preview's types,
values, missing values and content kept only in history before applying; see
[Restructuring](/docs/use/hierarchies/#restructure-in-a-change-set).

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
