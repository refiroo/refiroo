---
title: Move several records together
description: Select records in a tree and move them to one parent as a single confirmed change.
reader: steward
---

Move several records together while keeping their types. See
[Hierarchies](/docs/use/hierarchies/) for allowed placement and descendants.

1. Open an editable tree in Live or a change set. Use Cmd or Ctrl to add or remove records
   from selection, or Shift for a range. By keyboard, use Ctrl+Space and Shift+arrows.
   Selection does not itself open a different record; Escape clears it.
2. Drag the selected records to the intended parent, or right-click the selection (Shift+F10
   by keyboard) and choose **Move to…**.
3. In the move dialog, search for the parent and read disabled choices' reasons. The destination
   must allow every selected record without a type change. A place needing **Becomes …** is
   for an individual restructuring operation, not this multi-record move.
4. Review the destination and selected records, then confirm the move. They move together or
   none moves. Their descendants stay beneath them; IDs and history are kept.
5. Check their new paths. Live moves are immediate; change-set moves await publication.

On touch, hold a record still for half a second until it lifts. Moving first scrolls; a short
tap opens. Drag near an edge to scroll. In the sidebar, releasing where you lifted opens the
node menu and offers Move to. Read-only trees and publication trees do not drag.

A drop chooses a parent or level, not a manual position among siblings. The view's order
controls sibling positions. If records changed meanwhile, review the refreshed state and try
again rather than assuming the first destination is still valid.
