# Steering for UX1-GUIDE (written 2026-11-12 04:37)

- **Deleting a record is being changed while you work.** `frontend/src/features/objects/ObjectDeleteDialog.tsx`
  is becoming one confirmation: it reads what the deletion takes with it when it opens (a new read-only route for
  the deletion impact) and then asks once, naming what is deleted. Before you write or correct anything about
  deleting a record (`guide/use/delete-a-record` and the pages that mention it), read that file as it is at that
  moment and describe what it does then. If it still asks in two steps, write the two steps.
- **Home** now shows "Waiting for your approval" and the person's own change sets above the workspace cards, and
  a file field is also a place to drop the file. Mention each only where a page already describes that surface.
- The list page's header has a pin button that brings the list to the person's shelf on the workspace's page.
