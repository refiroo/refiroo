# UX2-GUIDE: one field edited in place saves when it is left

On 2026-11-12 the way ONE value is edited where it stands changed (0.17 package UX2, decision PP-D68). What
changed is written in `CHANGELOG.md` under `[Unreleased]`, the entry headed **0.17 UX2: one field saves when it
is left**, and in `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, section **UX2** (it has a table of what each value
type does). Read both, then the code they name (`frontend/src/ui/EditInPlace.tsx`, `InlineEditForm`;
`frontend/src/features/objects/panels/InlineAttributeEditor.tsx`; `frontend/src/ui/TextInPlace.tsx`;
`frontend/src/features/objects/relations/RelationValueCell.tsx`; `frontend/src/features/objects/useCellEditing.tsx`),
and bring the guide in line. The code wins over the changelog; if they differ, write what the code does and list
the difference in your report.

## What is true now

- A single value edited in place (a list's cell, a record's details and header, the record opened beside its
  list, a relationship's value, a relation matrix cell's fields, the names and short texts edited in place in
  Settings, the model editor's names and table cells) becomes its input where it stands. There is no small form:
  no **Cancel** and **Save** buttons and no **No value** tick.
- Leaving the field saves it (a click elsewhere, Tab). Enter saves too; in a text of several lines Enter is a new
  line and Ctrl+Enter (Cmd+Enter on a Mac) saves. A choice from a list and a tick save as they are made. Escape
  puts the old value back. An input left as it was opened saves nothing and shows no notice.
- The notice after a save is **‹Field› saved** with **Undo**, also for a value set for the first time (Undo takes
  it out again) and for a relationship's value.
- An optional field left empty is the value removed (it reads **Not set**), with the notice **‹Field› removed**
  and **Undo**, the same as the remove-value button, which stays. A required field left empty is refused under
  the field ("‹Field› needs a value.").
- A refusal (a rule of the model, the record changed elsewhere, a change set conflict) keeps the field open with
  the reason under it and what was typed kept. Only then **Cancel** and **Save again** appear under the reason;
  leaving the field again saves only once the input has changed.
- Another field can be opened while one is open; the first is saved as it is left.
- A list's value cell shows one notice (the field's own), no longer a second one saying where it was saved.
- **Cleared** (an explicit empty value) and **Empty text** are still shown where the data holds them, but the
  interface can no longer set them; the API can.
- A Yes/No value in a record's details and in a matrix cell's table is still the switch that saves itself; in a
  list's cell it is a tick that saves when ticked.
- Forms with several fields (the add and edit sheets, dialogs) are unchanged: they keep **Save** and **Cancel**.

## What to do

1. Correct every sentence these changes made wrong, on the pages listed below. Known places (check for more with
   the searches under "How to find the sentences"):
   - `src/content/docs/use/records.md`: the paragraph on editing a value on the record page ("Choose **Save** or
     press Enter …") and the paragraph on clearing an optional field (the sentence about **No value**).
   - `src/content/docs/guide/use/correct-a-record.md`: the step that enters the replacement value, the sentence
     "Where **No value** is offered …", what the save notice offers, and any later step that tells the reader to
     save or cancel ONE value (steps about the edit form of several fields stay as they are).
   - `src/content/docs/use/appearance-and-devices.md`: the keyboard sentence about an inline edit.
   - `src/content/docs/use/relation-matrices.md`, `src/content/docs/use/relationship-tables.md`,
     `src/content/docs/guide/use/fill-in-a-relation-matrix.md`: the sentences on editing a value in a cell
     (they already say leaving saves for some cells: make them one consistent description, and add the notice
     with Undo for a relationship's value).
   - `src/content/docs/about/accessibility.md`: any sentence on how an in-place edit is saved or cancelled with
     the keyboard.
   - Settings and model editor pages that tell the reader to press **Save** after changing a name in place.
2. Change only what is wrong or incomplete. Do not restructure pages, do not rewrite correct text, do not touch
   screenshots, their file names or their captions' file references. If a screenshot now shows the old small
   form, do not remove it: list it in your report under "Screens to retake".
3. Keep the guide's voice and its words: "record", not "object"; **Save**, **Cancel**, **Undo** as the interface
   writes them; no time estimates.
4. Then run, in `guide/`: `GUIDE_OUT=_build/UX2-GUIDE npm run build` and `npm run verify`.

## How to find the sentences

Search `src/content/docs` for: `No value`, `Enter saves`, `Escape cancels`, `becomes its field`, `inline edit`,
`small editor`, `where it stands`, `where the value stands`, `pencil`, `Save again`, and for **Save** in a
sentence about one value (not a form or a dialog).

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/use/*.mdx`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/use/*.mdx`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/guide/model/*.mdx`
- `src/content/docs/model/*.md`
- `src/content/docs/model/*.mdx`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/guide/administer/*.mdx`
- `src/content/docs/administer/*.md`
- `src/content/docs/administer/*.mdx`
- `src/content/docs/journeys/*.md`
- `src/content/docs/about/*.md`

## Report

- Each page changed, with the sentences before and after in one line each.
- Differences you found between the changelog and the code.
- Screens to retake (file name and what it shows now that is no longer true).
- The result of the build and of `npm run verify`.
