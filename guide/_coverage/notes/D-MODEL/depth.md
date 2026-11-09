# Depth review

## Types, attributes and relationships
Pages: model/types-attributes-relations; guide/model/add-a-record-type-and-fields; reuse-and-change-attributes; add-a-relationship.
Answered: purpose, setup and exact controls, subsequent changes, existing-data impact, removal, permissions, defaults, limits and recovery via Issues/compatibility/migration.
Expiry: business effective periods covered; definitions do not rotate. Backup/restore belongs to model releases/export, linked through Models.
Sources: elementSettings.tsx; ElementPanel.tsx Attributes and relationColumns; operations.ts type-display-attribute through relation-rule; schema.py AttributeTypeDefinition through ObjectTypeRelationDefinition; record forms/panels hidden checks.
Open: no browser exercise or screenshot capture in this writing assignment.

## Applications and views
Answered purpose/setup/change/removal, membership and defaults, eligibility and permission limits, draft recovery and activation effects; navigation and matrix guides reviewed alongside operations.ts and matrixView.ts. No expiry/rotation; data backup belongs to workspace operations, view definitions to export.
Sources: operations.ts addViewFields/treeFields/gridFields/view-remove; viewKinds.ts; elementSettings.tsx applicationSettings. Existing navigation grouping guide remains current.
Potential defect: viewKinds.ts changeView/treeConfig regenerates actions as availability only; editing a tree can remove previously declared create/rename/move actions. Also one shared child sort replaces per-type sort choices. Exposed honestly in the guide.

## Record pages and tables
All four pages reviewed including preview-a-type. Answered purpose/setup/change/removal, defaults/limits/permissions, invalid draft and empty-state recovery; activation effect separated from preview. No expiry; definitions export with release, no data writes from layout. Sources layout.ts pageHeaderSpec/tableMenuSpec/panelSettingsSpec; layout addPanelSpec; schema.py panel defaults. Specialist-only panel type/list controls identified; related-record panels have no declared page-size setting.

## Consumer APIs
Reviewed documentation and define/raise/documents guides against ConsumerApis.tsx, consumer operations in operations.ts and schema.py. Answered setup/output meaning, changes/version transitions, removal, access, defaults/limits, error/compatibility recovery; no rotation of declarations. Generated documents support handover; release export preserves declarations. Specialist row/API edit remains explicitly identified.

## Model mappings
Reviewed model-mappings and edit-a-mapping-row/choose-what-moves guides. Added deletion guide and lifecycle section against MovesPage.tsx and engine/moves/mappings.py delete_mapping. Answered setup/change/reuse/removal, copy versus move consequences, version refusal and dry-run recovery, permissions/deployment limits. No expiry; source/target data backup is an operator task. Existing runs/change sets survive mapping deletion.

## Models and editor (sidebar groups 1–3)
Reviewed models.md, the-model-editor.md, create-a-model-draft.md, delete-a-draft.md, find-your-way-around-the-editor.md, undo-and-review-the-draft-history.md, work-on-a-draft-with-others.md, split-merge-and-move-types.md, turn-an-attribute-into-a-list.md, rename-or-re-key-an-element.md, remove-an-element.md. Purpose/setup/change/removal, released-key limits, invalid/intermediate states and concurrency recovery are present. Added cross-instance definition reuse and explicit backup boundary to Models. No expiry/rotation of drafts or definitions; attached files use source lifecycle.
Sources: operations.ts; OperationDialog.tsx; ModelEditor.tsx; authoring/released.py, drafts.py; CreateDraftDialog.tsx; glossary and PRODUCT model-authoring section.

## Issues and specialist view
Reviewed issues-and-dry-run.md and fix-issues-before-installing.md: model/data/source checks separated, failures/stale checks and direct fixes explained. json-view.md and edit-a-draft-as-json.md: save/validate/compile/install, preservation of local text on conflict and export covered. Added explicit list of specialist-only settings, without exposing model paths on browser pages. No expiry; saved document recovery uses history/export, installation restore is operator-owned.

## Releases, migrations and language versions
Reviewed releases.md, install-and-activate-a-release.md, compare-releases.md, retire-or-delete-a-release.md, export-a-release.md; migrations.md, change-a-workspaces-model.md, migrate-a-workspace.md; model-language-versions.md, raise-a-model-language-version.md. All applicable depth questions answered: immutable identity; setup/selection; existing data/change-set/consumer impact; failure/stale-result retry; loss acceptance; retirement/removal; export versus database backup; special schema recovery. No timed expiry of model releases; retired and unsupported states explicitly covered.
Sources: ModelReleaseDetail.tsx; InstallDialog.tsx; ApplyDialog.tsx; engine/model/release_lifecycle.py and model/compatibility.py; engine/model/migrations.py and change_set_migrations.py; model language recovery screen.

## Workspace management
Reviewed managing-workspaces.md, create-a-workspace.md, edit-a-workspaces-model.md, make-a-workspace-the-default.md, retire-or-delete-a-workspace.md. Applicable depth: setup/change/removal/defaults/permanent keys/permissions/concurrent changes and read-only recovery. Added suspension/resumption consequence for webhooks from engine/events/subscription_rules.py suspend_for_retired_workspace. No scheduled expiry or growth limit; database/file backups belong to operator guide. Definitions export does not back up workspace data.

## Workbook onboarding and proposals
Reviewed workbook-onboarding.md, workbook-proposals.md, start-a-draft-from-a-workbook.md, map-a-column.md, read-lists-in-a-sheet.md, propose-again-with-a-newer-workbook.md, check-a-workbook-with-a-dry-run.md, load-a-workbook-into-a-change-set.md. Applicable depth answered: recognition limits/defaults; exact controls; file replacement and proposal ownership; failure/refusal/stale-check recovery; model/profile/data stage boundaries; deletion and retained-file limits; roles and permissions. Added Ignore this sheet behavior/removal scope and Undo. Files do not renew automatically; sources remain attached until owner cleanup, saved profiles can be reused. Back up original source separately; model export is not file backup.
Sources: SourcePane.tsx, MapColumnDialog.tsx, ProposeFields.tsx, LoadDialog.tsx; authoring/mapping.py ignore_sheet; sources/inference/patterns.py and build.py; tasks/profile_reading.py. Recognition thresholds reviewed against source constants rather than treated as adjustable settings.

## Assistant changes and model-change accounts
Reviewed ai-model-changes.md, change-a-model-with-the-assistant.md, review-an-assistants-workbook-design.md, model-change-accounts.md, explain-a-model-change.md. All applicable depth answered: enabled/disabled conditions and permissions; requests and data disclosure; costs/retention/expiry; model acceptance versus migration/publication; direct draft edits; partial/whole-type paths; failed/stopped/discarded recovery; saved-layout reuse and account cache invalidation. Added per-kind design-check display limit (12); the source check is bounded, not a completeness guarantee.
Sources: ModelProposal.tsx, DesignModel.tsx, ProposalMoves.tsx, LoadedView.tsx; engine/tasks/store.py/design_job.py/model_changes.py/design_checks.py; engine/proposals/impact_summary.py, summaries.py. No provider calls or browser tasks were executed. Other-server AI setup and retention policies belong to linked operator pages.

## Moving data between models (remaining guide)
Reviewed move-records-to-another-model.md: proposal/setup, sources/targets, scope, defaults/matching, refusals/losses, retries, copy-before-delete publication and permissions all present. No expiry of mapping definition; dry-run/job lifetime is distinct. Data recovery is history/new corrective change or installation restore, not mapping Undo.

## Validation and capture boundary
Initial isolated build and terms/brand checks passed. Links found nine requested images not yet captured. Because this wave cannot write public/screens, their exact Markdown references remain as pending HTML comments in the pages, with capture recipes in screens-wanted/D-MODEL.md; no invented or substituted screenshots. Restore those references when the images are captured. All existing images remain rendered.
Coverage uses the stock check with only the generated uncovered report redirected to this wave's notes, preserving the shared inventory file outside the allowlist. No model entries remain open: 33 management operations are covered by the generated API reference, 205 model features documented, 3 unused fields excluded, 140 screens documented. Other sections' 20 open entries are outside this wave.
