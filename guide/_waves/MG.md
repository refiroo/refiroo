# MG guide: changes that need a migration are made in the editor

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

Package MG (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "MG: Changes that need a migration, made in the
editor", including its delivery note) removed a refusal. Until now the model editor refused a change to a
released element that stored records, values or relationships depend on (a type moved to another
application, a split, a merge, a removal, a tighter rule, a key change), and the only way round was the JSON
view and migration mappings typed by hand. The pages below still say the editor refuses these changes. Bring
them in line with the product. The code wins: `backend/app/engine/model/authoring/kinds.py` (`Context`),
`backend/app/engine/model/authoring/history.py`, `backend/app/engine/model/authoring/draft_migration.py`,
`backend/app/engine/model/migrations.py` (the plan and its statements),
`frontend/src/features/model-editor/` (`MoveToDialog.tsx`, `InstallDialog.tsx`, `ApplyDialog.tsx`,
`DraftMigration.tsx`, `IssuesAndHistory.tsx`, `history.ts`), `frontend/src/features/model-admin/`
(`MigrationPage.tsx`, `ProposedRows.tsx`), `docs/API.md` ("The draft's migration"),
`docs/product-functionality/USER_JOURNEYS.md` (J33.7, J33.19), `../CHANGELOG.md` (Unreleased, 0.13 MG).

## What the product does now (check each point in the code)

- **The editor applies the step.** A change to a released element is never refused for the stored data any more.
  It is applied like every other step (undo, redo and the dry run behave as usual). When stored records, values
  or relationships depend on the element, or the key of a released element changes, the step is marked
  **Needs a migration** in the editor's History, with the records, values and relationships that hold the
  element. A step on a released element nothing holds is not marked. Menu items that can need a migration
  read "Needs a migration when installed" (a key change: "Needs a migration when installed: integrations
  naming the key must change"); **Move to…** shows a notice with the same title and what becomes of the
  records. The API error `OPERATION_REQUIRES_MIGRATION` is no longer raised. The editor's element panel says
  "Released: a key change needs a migration" where it used to say the key is fixed.
- **The draft states its migration.** From the steps that stand now (an undone step takes its part away) and the
  two models, the engine derives: which type becomes which (a key change, a merge, a split's new type, a
  conversion's list type), which renamed attribute becomes which, which application a moved type goes to and
  whether its records become top-level records, a relation type's new key, and each key change with the
  consumer APIs of the base release that name the old key. It is read at `GET /model-drafts/{id}/migration`,
  computed each time, never stored. **Install and activate…** and **Apply to this workspace** state it
  ("Activation needs a migration": the steps, one line per part, the figures records move, records created,
  relationships created, refused, and for each key change that integrations naming the key must change, with
  the consumer APIs naming it), and the main button reads **Install … and preview the migration…**, which
  installs the release, starts the migration preview with the draft's mappings and opens the migration page.
  The release is installed but not activated until the migration is confirmed.
- **The migration page opens filled in** (**What the draft proposes**): a row per type the draft's steps
  change, with Records of, Become, In, Under, Records and a **Proposed** mark. A row's Become choice can be
  changed in place, which previews again; the draft does not change. The preview, the acceptance of loss and the
  confirmation are as before. A new **Created** outcome lists records and relationships a split or a list
  conversion creates.
- **What the migration carries** (set statements in the database): a record whose type stands at the top after a
  move becomes a top-level record (its parent and the containment relationship go); where the type is under
  other types, a record whose parent the new place does not allow is listed as refused. A moved type's records
  go to the application named (`toApplicationKey`), also where the type is listed in several. A relation type's
  new key carries its relationships. A **split** gives each record that holds a moved value a record of the new
  type holding the values, related to it (with the many-to-one cardinality, records holding the same values
  share one record; the new record is named by its first moved value, else by the record's name); a record
  holding none of them gets none. A **conversion to a list type** makes one record per distinct value, named by
  the value, and relates each record to its value's record; the values leave the source records. A tighter rule
  (required, cardinality, a value type, bounds) is checked in the preview, and the records that break it are
  listed as refused, as before. A removal is a loss to be accepted, as before. Moving an attribute to another
  type removes its values from the first type's records (they are listed as loss): different records, so no
  value can be carried across.
- **Publishing is unchanged**: activation still refuses a release whose migration has not run
  (`MODEL_MIGRATION_REQUIRED`), and rollback is by the earlier release.

## Passages known to be wrong (found by the builder; check the whole page around each)

- `model/types-attributes-relations.md`, "Released elements and refusals" (about lines 65–75): says a
  released element's key is fixed, that operations are refused with their impact and that zero impact can allow
  a change. Now: the step applies and is marked; a key change is allowed and needs a migration; what the
  migration does is on the Migrations page.
- `model/migrations.md`: the passage about a released field's value-type change "refused by the visual
  editor" (about lines 68–71) is no longer true; add how a migration starts from the editor (the draft states
  it, the page opens filled in, rows marked Proposed, the Created outcome, the new carried cases above).
- `model/the-model-editor.md` is not on this list; do not edit it. Where its sentence about splitting or
  merging "can be refused when stored data uses it" (about line 40) is now wrong, say so in your report.
- `guide/model/rename-or-re-key-an-element.md` (about lines 18–19: "If the key is fixed, keep it and rename the
  label instead… read **Not applied**"): a released key can be changed, with a migration and a warning that
  integrations naming it must change; the label still changes freely.
- `guide/model/reuse-and-change-attributes.md` (about lines 24–26), `guide/model/turn-an-attribute-into-a-list.md`
  (about lines 19–21), `guide/model/split-merge-and-move-types.md` (about lines 39–41) and
  `guide/model/remove-an-element.md` (about lines 18–25): each says the action is refused when data uses the
  element. Now: it applies, is marked, and installing the draft shows the migration to review.
- `guide/model/install-and-activate-a-release.md` (about lines 71–112) and
  `guide/model/migrate-a-workspace.md`: add the install dialog's statement of the migration, **Install … and
  preview the migration…**, the filled-in page with **Proposed** rows and the Created outcome.
- `guide/model/undo-and-review-the-draft-history.md`: the **Needs a migration** mark in History.
- `integrate/model-and-release-operations.md` (about lines 13 and 59): says
  `OPERATION_REQUIRES_MIGRATION` means an existing released element needs a migration instead of a draft-only
  edit, and that draft-only changes to released structures may require migration. Now: the operation applies,
  its history entry carries `migration`, and `GET /model-drafts/{id}/migration` states the migration (with
  `againstReleaseId` and `toReleaseId` after an installation); a workspace migration takes
  `relationTypeMappings`, `splits`, `listConversions`, `draftId` and a type mapping's `toApplicationKey`.
  Link the operations to `/docs/api`; do not repeat their fields.

## What to do

- Fix each passage in its page, so a reader following the page gets what the product does. Keep each page's
  voice and structure; change what is wrong, not what is right.
- Use the guide's reference world for examples (a type under another type moved to the top level of another
  application, for instance a stop code moved from the Network application to Systems). Never name any other
  model's types.
- No new pages; no new pictures. A picture that shows the old behaviour: list it in the report (name and
  page). Screens you would want taken for the new states: list them (screen, state, what must be visible).
- A point where the product does something the guide cannot honestly describe: list it in the report with the
  evidence; do not write around it.

## Files you may edit

- `src/content/docs/model/types-attributes-relations.md`
- `src/content/docs/model/migrations.md`
- `src/content/docs/guide/model/rename-or-re-key-an-element.md`
- `src/content/docs/guide/model/reuse-and-change-attributes.md`
- `src/content/docs/guide/model/turn-an-attribute-into-a-list.md`
- `src/content/docs/guide/model/split-merge-and-move-types.md`
- `src/content/docs/guide/model/remove-an-element.md`
- `src/content/docs/guide/model/install-and-activate-a-release.md`
- `src/content/docs/guide/model/migrate-a-workspace.md`
- `src/content/docs/guide/model/undo-and-review-the-draft-history.md`
- `src/content/docs/integrate/model-and-release-operations.md`
- `_waves/progress/MG.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures
that no longer match, the screens you would want, and any product point the guide cannot describe honestly.
