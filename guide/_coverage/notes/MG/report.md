# MG completion review

All 11 assigned pages were updated. No pictures or other pages were changed. No commits or state-changing git commands were used. Existing content outside the corrected passages was preserved. The per-page progress log records each completed unit and final review. No steering file existed when the units were started.

Paths below are relative to `guide/src/content/docs/`.

| Page | What changed and why | Passages checked and retained | Pictures / capture requests |
| --- | --- | --- | --- |
| `model/types-attributes-relations.md` | Released keys can change; structural edits apply and receive migration marks instead of in-use refusals. Corrected the related relation-control restrictions. | Placement, shared attributes, relationships, value rules, ownership, candidates, periods and field guidance. | `model-type-fields.png` has the obsolete key badge. Capture a released type with the new badge and migration-aware menu. Matrix picture has no MG contradiction. |
| `model/migrations.md` | Added the editor entry flow, Proposed rows, Created outcomes, moves, split/list creation, key carrying, field-move loss and checked return to an earlier release. Removed the obsolete JSON workaround. | Permissions, missing definitions, loss acceptance, atomic execution, cancellation, stale reviews, change-set variants, supported conversions, subscriptions and assistant entry. | `model-migration-review.png` remains a manual-mapping example, not the new editor proposal. Capture Proposed rows and Created items. |
| `guide/model/rename-or-re-key-an-element.md` | Replaced the fixed-key instruction with editable released keys, integration warnings and migration review. | Label renaming, shared names, generated keys and collision suffixes. | Existing rename and unreleased-key dialogs remain valid; capture a released key change and its consumer warning. |
| `guide/model/reuse-and-change-attributes.md` | Field changes apply with migration marks; moving an attachment loses source values; released keys can change. | Attachment, shared/local settings, ordering, detach, bounds, Hidden and Help text. | `model-attribute-settings.png` has the obsolete key badge. Other pictures show valid unreleased operations. Capture released-field menu, move warning and resulting History mark. |
| `guide/model/turn-an-attribute-into-a-list.md` | Replaced refusal with the marked step, proposed conversion and Created review for distinct-value records and relationships. | Purpose, naming fields, candidate criteria and Issues. | Existing dialog still shows its form; capture the subsequent proposal and Created records/relationships using the transport reference world. |
| `guide/model/split-merge-and-move-types.md` | Added migration review to each task, split sharing, record identity, application destinations and parent release/refusal. | Dialog fields, keyboard/drag paths, listing versus removal and cross-model link. | Existing pictures show new types and remain valid forms, but not released moves. Capture a released contained type moving to another application's top level, with the notice. |
| `guide/model/remove-an-element.md` | Replaced in-use refusal with an applied marked step and deliberate migration-loss review. | Removal scopes, confirmation, Issues, Undo and listing distinction. | Existing confirmation remains valid; capture removal's History mark and resulting loss review. |
| `guide/model/install-and-activate-a-release.md` | Added the migration statement, key/API warnings, installation-preview action, Proposed and Created review in both editor entry paths. Clarified an installed release survives cancellation. | Release identity, workspace choice, consumer-version checks, already-installed activation, failures and existing captions. | Existing install and Apply pictures are compatible-data states and remain valid. Capture migration-required Install and Apply states. |
| `guide/model/migrate-a-workspace.md` | Added both editor entry points, installed-but-inactive state, Proposed row editing and Created review. | Loss consent, mandatory fixes, stale handling, action variants, success and atomic failure. | Existing manual review, blocked-loss and stale pictures remain valid states; capture Proposed rows and Created outcomes. |
| `guide/model/undo-and-review-the-draft-history.md` | Added migration marks, released key changes with no data and undo/redo's effect on the proposed migration. | History paging, JSON edits, dependent undo, redo clearing and concurrency. | `model-history.png` has the obsolete key badge and no migration-mark example. Capture marked and undone migration steps. Dependent-undo image remains valid. |
| `integrate/model-and-release-operations.md` | Replaced the obsolete error guidance with history metadata and derived migration reads, including the post-install release comparison and extended migration sequence. Added the migration branch to rollout. | Limits, validation, concurrency, activation and consumer refusals, change-set paths, mappings, transfer, conversions, AI, access and recovery. | No pictures on this page; none requested. |

## Pictures that no longer match

- `model-type-fields.png` on `model/types-attributes-relations.md`: **Key fixed: released** is obsolete.
- `model-attribute-settings.png` on `guide/model/reuse-and-change-attributes.md`: same obsolete badge.
- `model-history.png` on `guide/model/undo-and-review-the-draft-history.md`: same obsolete badge. Its shown additive steps remain valid, but do not illustrate migration marks.

The existing manual migration picture does not falsely depict a draft-proposed migration: it depicts an independently selected target. The compatible install/Apply pictures and new-element dialogs also remain valid for their stated states. They do not illustrate the newly documented states. No picture was removed, generated, retouched or replaced.

## Screens wanted (no new picture references added)

1. Released type/attribute panel: **Released: a key change needs a migration**, its menu's migration note, and the selected transport-model definition visible. Use on the types, rename and attribute pages.
2. Released type's **Move to…**: top level of another application selected; **Needs a migration when installed** notice, destination application and explanation of top-level records visible. Use on split/merge/move.
3. **History** after a move, removal or tighter field rule: applied step, **Needs a migration**, record/value/relationship counts, and Undo visible; also show the undone step and refreshed proposal without that contribution. Use on history and the affected task pages.
4. **Install and activate…**, migration required: selected workspace, **Activation needs a migration**, proposed steps, moved/created/refused figures, changed-key warning naming consumer APIs and **Install … and preview the migration…** visible. Use on install and migrations.
5. **Apply to this workspace…**, migration required: workspace, the migration statement and counts, change sets left behind and **Preview what happens to the records…** visible. Use on install.
6. Migration page from the editor: **What the draft proposes**, all six table columns including status, **Proposed**, destination application/placement and a **Become** selection; another capture after editing the selection and previewing again. Use on migrations and migrate-workspace.
7. Migration preview for a split and a list conversion: proposal lines plus **Created**, the created record and relationship rows, source names and destination visible. Include repeated values to show sharing. Use on migrations, list conversion, split and migrate-workspace.
8. Removal/attribute-move preview after blockers are fixed: lost records/values/relationships, loss acceptance and the final migration action visible. Use on removal and attribute tasks. Existing blocked-loss screenshot can remain for the blocked state.

Use only the guide's Graubünden transport reference data for new captures. Several existing new-type dialog images use Facilities/Building/Room/Equipment, and the manual migration images target the starter model; these were retained under the brief's instruction to change no pictures. They are not suitable examples for new captures under the one-world rule.

## Product and source discrepancies

- Out-of-scope `model/the-model-editor.md:39–41` still says released keys are fixed and split/merge can be refused for stored data. It was read and left untouched as instructed.
- Apply's main action is **Preview what happens to the records…**, not **Install … and preview the migration…** (`frontend/src/features/model-editor/ApplyDialog.tsx:326`). The install action has the latter label (`InstallDialog.tsx:520`). Pages use each actual label.
- The proposal table's **In** cell lists all target applications (`frontend/src/features/model-admin/ProposedRows.tsx:83`), rather than selecting `row.toApplicationKey`. The install summary does name the chosen destination (`DraftMigration.tsx:65`). The guide therefore does not claim that this cell uniquely identifies the actual destination when several applications list the type.
- The split summary says “for each value” (`DraftMigration.tsx:99`, `ProposedRows.tsx:43`), but execution creates one related record per source record with moved values, sharing identical value sets for many-to-one (`backend/app/engine/model/migrations.py:772–805`). Pages describe the data behavior rather than echoing the misleading summary.
- The opening J33 description in `docs/product-functionality/USER_JOURNEYS.md:850` still says migration-class changes are refused; its J33.7 and J33.19 variants describe the new behavior. The code and variants were followed; this source file was not changed.

## Validation scope

Source review covered the assigned pages, the named authoring/migration code and UI components, migration item labels, the API's draft migration section, J33.7/J33.19 and the MG delivery note and changelog. Large combined reads were truncated; targeted follow-up reads supplied the decision points recorded above. Unchanged passages were reviewed for surrounding consistency, not every unrelated backend capability revalidated.

The guide build, terms/brand and built local-link checks passed. This is documentation validation, not an API execution or browser migration test. No runtime servers or databases were started. Build logs are kept beside this report.
