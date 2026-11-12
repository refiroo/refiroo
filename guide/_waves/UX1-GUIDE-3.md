# UX1-GUIDE-3: three labels changed after the main wave

After wave UX1-GUIDE wrote the pages, three things in the application changed. Correct the sentences that
describe them, and nothing else:

1. **A record's edit form** (`frontend/src/features/objects/ObjectFormDialog.tsx`): its button is **Save**, no
   longer "Save changes".
2. **Starting a change set from a publication** (`frontend/src/features/workspaces/Publications.tsx`): the field
   is **Name** and the button **Start change set**, no longer "Change set name" and "Create change set".
3. **Undo** after a saved value (`frontend/src/features/objects/undoText.ts`): when the record changed again in
   the meantime, Undo is refused and the application says "Undo was not possible: the record changed again in the
   meantime." Add this in one sentence where Undo after a save is described, if a page describes it.

Search the pages for "Save changes", "Change set name", "Create change set" and "Undo". Read the code first.
Then run `GUIDE_OUT=_build/UX1-GUIDE-3 npm run build` and `npm run check:coverage` in `guide/`.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/model/*.md`
- `src/content/docs/journeys/*.md`
- `src/content/docs/examples/*.md`

## Report

The sentences changed, with their page.
