# PL4-GUIDE-2: one permission is not on a page

The inventory lists one permission the guide does not name (`_coverage/inventory/uncovered.md`):
`action:workspaces.create-from-workbook`, "Creating a workspace from a workbook", declared in
`backend/app/engine/authorization/catalogue.py` in the Workspace administration group.

On `src/content/docs/administer/permissions-reference.md`, add **Creating a workspace from a workbook** to the
actions of the Workspace administration row, in the wording the row already uses, and, if the page explains
actions that need more than one group, one sentence saying this action also needs Install a model or Model
release, and Bulk and import, at the instance (read `backend/app/management/routers/workspaces.py`). Change
nothing else. Then run `GUIDE_OUT=_build/PL4-GUIDE-2 npm run build` and `npm run check:coverage` in `guide/`.

## Files you may edit

- `src/content/docs/administer/permissions-reference.md`

## Report

The text changed.
