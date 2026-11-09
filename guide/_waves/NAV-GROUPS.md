# Navigation groups: relation matrices as entries, a collection's opening view, the group panel

Read `guide/AGENTS.md`. Reader: model administrators (Model your data), data stewards (Use refiroo).

## Why

The product changed (see `../CHANGELOG.md`, Unreleased, "relation matrices in navigation groups, a
collection's opening view, a group panel in the editor"; `../docs/APPLICATION_MODEL.md`, "Navigation
groups"; `../docs/API.md`, operations `placeCollection` and `setCollectionOpening`). The existing sentences
that described grouping were adjusted so they stay true. The new behaviour still needs its own words.

## What exists now (check each against the code; the code wins)

- A relation matrix placed in a navigation group is an entry of its own in the sidebar and on the group
  page: named after the view, with a matrix glyph in its row type's colour, opening the matrix directly.
  Its row type's entry stays, and its view switch still offers the matrix. A matrix placed nowhere stays
  inside its row type's entry. `frontend/src/features/objects/Explorer.tsx`, `NavigationGroupPage.tsx`.
- A collection can open on a view the model names for it (**Opens on**), in place of the application's
  default view. `frontend/src/model/collections.ts` (`collectionGroups`).
- In the model editor, choosing a group in the model tree opens its **group panel**: its facts, an
  **Entries** table (**Entry**, **Kind**, **Opens on** edited in place, **State**, a row menu with **Move
  up**, **Move down**, **Move to another group…**, **Take out of the group**), and the buttons **Add to
  group…**, **Rename…**, **Start folded** / **Start unfolded**. `frontend/src/features/model-editor/ElementPanel.tsx`
  (the group panel), `operations.ts` (`group-add`, `entry-*`, `application-group-add`, `view-group`).
- **Add to group…** is one dialog that adds several collections and relation matrices at once, with a search
  and, beside each, where it stands now ("Top of the sidebar", "In <group>", "Inside <row type>", "Moves
  from <group>"). It is one step in the history: one **Undo** takes it all back.
- The application panel's group table has an **Entries** column listing types and matrices; the group's name
  opens its panel; **In no group:** offers **Add to a group…** with those collections chosen; a relation
  matrix's menu in the **Views** table has **Move to group…**.

## What to do

- `src/content/docs/guide/model/group-collections-in-navigation.md`: add the steps for the group panel,
  **Add to group…**, placing a relation matrix, ordering entries and **Opens on**. Keep the existing steps
  that remain true.
- `src/content/docs/model/applications-and-views.md` and `src/content/docs/model/the-model-editor.md`: describe
  matrices as entries and **Opens on**, and the group panel, in the pages' own words. Update the "Inventory
  trace" comment with the new operation ids (`operation:group-add`, `operation:application-group-add`,
  `operation:entry-up`, `operation:entry-down`, `operation:entry-move`, `operation:entry-out`,
  `operation:view-group`) and the model path `applications[].navigation.opens`.
- `src/content/docs/use/applications.md`: say what a reader sees for a matrix entry and for an entry that
  opens on a chosen view.
- Screenshots to list in the report (taken afterwards from the reference instance, the stops of Graubünden):
  the group panel with a collection and a "Municipalities by system" matrix entry; the **Add to group…**
  dialog with some entries ticked; the sidebar with the matrix entry in a group.
- Run `npm run build` and `npm run check:coverage` in `guide/`; every new operation id is named on a page.

## Files you may edit
- `src/content/docs/guide/model/group-collections-in-navigation.md`
- `src/content/docs/model/applications-and-views.md`
- `src/content/docs/model/the-model-editor.md`
- `src/content/docs/use/applications.md`

## Report
Say what you changed per file, the screenshots wanted, and anything the product does that you could not
describe honestly.
