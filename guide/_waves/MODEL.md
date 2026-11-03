# Model your data

Read `guide/AGENTS.md` again (documentation pages and guides; capabilities, not applications; generic
steps with the example only in captions; detail). Keep the standard of the "Use refiroo" pages.

Reader: model administrators, who shape what the applications hold, in the model editor in the browser.
No JSON on these pages: a model is shown as the editor shows it, never as a model file. Sources: the screens
in `frontend/src/`, `docs/MODEL_AUTHORING.md`, `docs/APPLICATION_MODEL.md`, `docs/EXAMPLE_MODEL.md`,
`docs/product-functionality/USER_JOURNEYS.md` (the model journeys), and the code where they disagree.

Write these pages (documentation page first, then its guides):

| Group | Documentation page | Guides |
| --- | --- | --- |
| Models | `model/models.md`: what a model is (applications, record types, fields, relationships, hierarchies, views), drafts, releases and activation as three stages, which roles may do what | `guide/model/create-a-model-draft.md` |
| The model editor | `model/the-model-editor.md`: the editor's parts, the source pane when a draft came from a workbook, the history and undo, comparing with the active release | `guide/model/add-a-record-type-and-fields.md`, `guide/model/add-a-relationship.md`, `guide/model/arrange-applications-and-views.md` |
| Checking a model | `model/issues-and-dry-run.md`: issues, what blocks installing, the dry run against a workspace's data and its figures | `guide/model/fix-issues-before-installing.md` |
| Releases | `model/releases.md`: installing makes a release that never changes; activating is a separate step and is refused when existing data would not fit; each workspace runs its own release | `guide/model/install-and-activate-a-release.md` |
| Moving data between models | `model/model-mappings.md`: moving records between workspaces whose models differ: the proposed mapping, editing it, the dry run, the reviewed change set | `guide/model/move-records-to-another-model.md` |

Loading a workbook is already documented under Use refiroo (`use/loading-a-workbook.md`); link to it where
a model draft can start from a workbook, do not repeat it.

## Screenshots

Screens file: `MODEL.screens.json`

Those screenshots are attached and are the real screens; earlier ones (e.g. `use-wb-*` in
`USE2.screens.json`) may also be referenced. Use `/docs/screens/<name>.png` with captions saying what the
example shows. List any screenshot still needed.

## Files you may edit

- `src/content/docs/model/*.md`
- `src/content/docs/guide/model/*.md`

## Report

The pages written, the screenshots used and still needed, anything you were unsure of, and anything in
refiroo that looked wrong.
