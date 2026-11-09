# D-USE depth review

Read: guide/AGENTS.md, D-USE.md, COMPLETE-COMMON.md and DEPTH-COMMON.md. No top-level repository instructions applied. Existing inventory available; no regeneration needed.

Each entry records purpose, setup/use, changes, retention/growth, failure/recovery, removal and permissions as applicable. Server backup/migration is operator work and is linked rather than repeated in steward pages.

## Inventory unit: notification removal

`use/inbox-and-approvals.md`: purpose, filtering, bulk selection, retention (90 days), removal scope, permissions, failure/retry and approval lifecycle already covered; added exact clear-read dialog and confirmation labels. Source: frontend/src/features/inbox/NotificationsPage.tsx:285-350. Backup/rotation does not apply to a personal notice action. No open questions.

## Import profile and upload removal

`use/importing-and-exporting.md`, `guide/use/load-the-next-version-of-a-workbook.md`: purpose, upload/check/load setup, changing profiles, recurring keys, missing-record deletion, sampling, file refusals and retention already covered. Added separate removal, confirmation, access, conflict recovery and retained-data consequences. Sources: ImportProfilesPage.tsx:211-212,355-384; DeleteAction.tsx; engine/imports/profiles.py:726-742; engine/sources/store.py:254-306. No automatic restore; operator backup is outside this task. No open questions.

## Inventory unit: internal route and dialog names

Excluded six implementation identifiers, not their capabilities. Checked RouteState in types/ui.ts, SettingsArea.tsx:78,152 and DeleteAction.tsx; mapped each to its reader page in exclusions.md. Applications already explains group pages and their empty/search states; the assistant continuation guide explains Jobs and the task lifecycle. No missing reader screen hidden by these exclusions.

## Record fields: hidden fields and help

`use/records.md`, `guide/use/add-a-record.md`: added model-defined visibility, unchanged stored values, per-type help and recovery when the needed input is absent. Source: ObjectFormDialog.tsx:66-69; ui/AttributeField.tsx:14,29,69; panels/AttributesPanel.tsx:41. No claim that hiding is an access control. No expiry or server-move procedure applies to visibility.

## use/home.md

Reviewed workspace cards, following, continuation, approvals and recent actions; added the unavailable-model card and recovery link. Sources checked: frontend/src/features/home/HomePage.tsx (Continue, WorkspaceCard, FollowToggle, WaitingApprovals). Not applicable: credential rotation and backup of the Home page; those concern account or operator work.

## use/account.md

Reviewed sign-in, password changes, passkeys, sessions, role inspection and recovery; added step-by-step second-factor sign-in and device cleanup after passkey removal. Sources checked: SignInScreen.tsx:370-435; AccountPage.tsx; PasskeysPanel.tsx; SecondFactorPanel.tsx; engine/identity/passwords.py; config.py:99-103. Not applicable: server restore instructions; link to administration retained. No open depth question.

## use/applications.md, use/workspaces.md, guide/use/open-an-application.md, guide/use/switch-workspace.md, guide/use/open-a-retired-or-unavailable-workspace.md

Reviewed entry points, groups, workspace switching, permission and model failures; added the exact group no-match state and its recovery. Other pages already cover applicable depth questions. Sources checked: NavigationGroupPage.tsx; WorkspaceSelector.tsx; HomePage.tsx; types/ui.ts; source-labelled workspace recovery passages. Not applicable: workspace creation/removal and model release repair are administrator tasks, already linked; views have no independent expiry.

## use/lists-and-filters.md, guide/use/find-records.md, guide/use/continue-a-long-list.md, use/ask-in-words.md, guide/use/ask-a-list-in-words.md

Reviewed purpose, search/filter setup, changing and clearing conditions, growing lists, defaults, query failures, page recovery, permissions and AI data/cost limits. Existing pages answer applicable depth questions without additions. Sources: ObjectToolbar.tsx; ui/TableDisplay.tsx:147-172; ui/ScrollWindow.tsx:654-737,857-900; engine/proposals/query_translation.py:53-89; CURRENT_FUNCTIONALITY F03. N/A: query expiry/rotation and server restoration; addresses retain query state, not data snapshots.

## use/records.md, guide/use/add-a-record.md, guide/use/correct-a-record.md, guide/use/delete-a-record.md, guide/use/stop-offering-a-value.md, guide/use/propose-a-change.md

Reviewed creation, typed/default/required/unique values, help and hiding, editing, concurrency, deletion cascade, proposal permissions and validity. Corrected Set null: it stores null; removing an optional field makes it unset. No remaining depth gap. Sources: InlineAttributeEditor.tsx; ObjectFormDialog.tsx; ObjectDeleteDialog.tsx; engine/records/attributes.py; engine/records/rules.py; BEHAVIOUR-RULES A. N/A: credential rotation; records do not expire through validity dates, and restoration from backups is operator work.

## use/changing-many-records.md, guide/use/change-values-of-many-records.md, guide/use/change-relationships-of-many-records.md, guide/use/delete-many-records.md

Reviewed selection, field/relationship changes, deletion impacts, sample previews, conflict recovery, background cancellation and partial commits; added numeric defaults and exact delete refusal-policy labels. Sources: BulkJobDialog.tsx; BulkDeleteDialog.tsx:19-20; BulkChangeDialog.tsx; BulkRelationDialog.tsx; config.py:125-140. N/A: credential rotation and server migration; expiry and job retention cross-link to Jobs.

## use/relationships.md, guide/use/relate-records.md, guide/use/replace-a-records-related-records.md

Purpose, cardinality, candidate restrictions and existing connections, owned creation, optional removal, whole-set atomic replacement, permission, conflict and read recovery reviewed. No additions needed. Sources: engine/records/rules.py:200-420; panels/RelationFormDialog.tsx; DeleteRelationDialog.tsx. N/A: expiry/rotation and backups; connections have no independent expiry.

## use/hierarchies.md, guide/use/arrange-records-in-a-tree.md, guide/use/move-several-records-together.md, guide/use/reshape-a-hierarchy.md

Purpose, parents, tree browsing/search, touch and keyboard moves, all-or-none selections, restructuring/500-record limit, restored/lost values, changing back, stale previews, permissions and deletion consequences reviewed. No additions needed. Sources: TreeMoveDialog.tsx; RestructuringDialog.tsx; engine/operations/restructuring.py:76; BEHAVIOUR-RULES B and L17-L19. N/A: rotation and server recovery; ordinary moves retain identity.

## use/mapping-grids.md, guide/use/map-codes-between-systems.md, guide/use/propose-targets.md

Reviewed states, replacement/removal, target creation side effects, candidate limits, AI jobs, correction, partial failure and provenance; added the default minimum confidence of 0.5. Sources: MappingGridView.tsx; mapping_selection.py:35-36; mapping_targets.py:23,184-215; mapping_job.py; config.py:153. N/A: automatic expiration of mappings; only jobs and AI task evidence expire.

## use/relation-matrices.md, guide/use/fill-in-a-relation-matrix.md

Reviewed row/column/cell meaning, state and column filters, 20-column and five-preview limits, creation/link/unlink, historical creation, changing existing cells, dirty-form protection, access and concurrency recovery. Existing pages cover applicable questions. Sources: RelationMatrixCellDialog.tsx:146-392,758; RelationMatrixView.tsx; BEHAVIOUR-RULES L17. N/A: rotation, automatic renewal and server restore; history-only content is not a restore mechanism.

## use/change-sets.md, guide/use/prepare-and-publish-a-change-set.md, guide/use/review-what-a-change-set-changes.md, guide/use/continue-live-work-while-a-change-set-is-open.md, guide/use/start-from-an-earlier-publication.md, guide/use/prepare-under-the-next-model-version.md

Reviewed creation/source, shared edits, review tabs, validation, publication merge, conflicts, approvals, model pinning/moves and discard. Added the missing step-by-step discard task with exact confirmation and recovery. Sources: ChangeSets.tsx:445-572,594-884; ChangeSetReview.tsx; BEHAVIOUR-RULES G; publications source action. N/A: rotation/renewal; open sets are not job previews and have no preview retention deadline.

## use/publications.md, guide/use/browse-a-publication.md, guide/use/withdraw-a-publication.md

Reviewed immutable contents/model, list growth, reading and export, current/withdrawn status, starting a new proposal, permission, stale withdrawal and no rollback. No additions needed. Sources: Publications.tsx:108-195; engine/change_sets/publish.py; BEHAVIOUR-RULES G5-G9. N/A: credential rotation and per-publication restore/expiry controls; server backup belongs to operator documentation.

## use/history.md, guide/use/see-who-changed-what.md, guide/use/explain-a-period-in-history.md

Reviewed record/workspace/person activity, filters and growth, missing values, AI period facts and cache, provenance, failure/retry, access and lack of undo. Existing pages answer applicable depth questions; external-assistant editing wording needs reconciliation with submission freezing below. Sources: HistoryPanel.tsx; engine/proposals/history_account.py; summaries.py:32; BEHAVIOUR-RULES G3. N/A: manual history editing/removal and credential rotation.

## use/importing-and-exporting.md, guide/use/export-records.md, guide/use/edit-in-excel-and-import-back.md, guide/use/add-a-language-with-a-workbook.md, guide/use/import-a-file.md, guide/use/load-the-next-version-of-a-workbook.md

Reviewed all manual import/export guides, readable and technical files, versions, blank cells, columns-per-parent, profile changes/deletion and error recovery. Added the assistant-to-manual entry path, numeric file/sample/retention defaults, and a safe warning about splitting missing-delete files. Sources: ImportDialog.tsx; LoadWorkbookDialog.tsx:112-160; ImportProfilesPage.tsx; config.py:125-140; CURRENT_FUNCTIONALITY F22. Backup of service files is operator work.

## use/jobs.md, guide/use/follow-and-cancel-a-job.md

Reviewed progress, states, partial commits, item outcomes, default retention, permission changes, download and cancellation recovery. Added exact different list/detail/preview confirmation labels. Sources: JobPage.tsx:324-347; JobsPage.tsx:213-230; config.py:128. No per-job restoration or credential renewal task.

## use/ai-and-your-data.md, use/loading-with-the-assistant.md, guide/use/load-a-workbook-with-the-assistant.md, guide/use/change-records-with-the-assistant.md, guide/use/continue-an-assistant-task.md

Reviewed information sent/costs, access, file/words limits, proposal/check/accept/load, saved layouts, corrections, migration branches, stopping/discarding, task retention and onward actions. Added recovery for a failed load that leaves a change set, and clarified submitted-work editing in History. Sources: ai-tasks/TaskEnd.tsx:46-86; LoadWorkbookDialog.tsx; LoadedView.tsx; engine/tasks/agent.py:76,503-549,2002; store.py:161-275; management/mcp_tools.py:126-143,604; change_sets/submissions.py:54-105. All applicable depth questions answered; server transcript backup is operator work. Follow-up source check corrected waiting-job label to preview (JobPage.tsx:179).

## use/appearance-and-devices.md, guide/use/change-how-refiroo-looks.md

Reviewed immediate local changes, per-table overrides, defaults/reset, keyboard/touch operation and permission-based Settings. Fixed Theme to Normal/Website purple and separate Light or dark. Sources: AppearancePage.tsx; lib/scheme.ts, palette.ts, tableDensity.ts, editHint.ts. No expiry/renewal or server backup: browser preferences remain local. Screenshot refresh requested.

## use/inbox-and-approvals.md, guide/use/approve-a-change-set.md, use/notifications-settings.md, guide/use/set-up-email-notices.md, guide/use/follow-a-workspace.md

Reviewed notice selection/deletion, retention/handled subjects, approval policy, submit/withdraw/send-back/approve, conflicts, mail eligibility/defaults/schedule/digests/following and recovery. Added exact unavailable-email messages. Sources: inbox/NotificationsPage.tsx; settings/NotificationsPage.tsx:19-21; NoticeMailPanel.tsx; notifications/mailing.py:36-50,108-193; approvals UI in ChangeSets/ChangeSetReview. Server mail recovery and policy configuration link to their owning sections. No unresolved depth question.

## use/copying-and-moving.md, guide/use/copy-or-move-records.md

Added the steward transfer task, linked to model-admin mapping design without duplicating it. Answers purpose, setup with saved mapping, selection, changes to mappings/releases, growing reports, refusal/partial-result recovery, repeat transfer/identity, abandoning/removing proposals and permissions. Sources: moves/NewMoveDialog.tsx, SelectionDialog.tsx, StartMoveDialog.tsx, MoveStatus.tsx, moveAbility.ts; management/routers/moves.py; engine/moves/move_load.py. Job retention links to Jobs; server backup/restore belongs to operators. Permission detail verified next against MOVE resolver.

Transfer permission follow-up: management/access.py `_move` requires Copy and move on target; the MOVE authorization branch requires Browse on source for Copy and Work in change sets for Move. Corrected the steward page to these exact permissions.

## Coverage reconciliation complete

917 legacy rows: 812 covered, 105 not for readers; no deferred/empty Covered by cells. The 185 prior AI resolutions were in Source, not Covered by; repaired in five saved row groups. Seven inventory gaps resolved. The coverage checker writes a shared file outside this wave: run its logic with only that output redirected into D-USE notes, leaving shared inventory untouched. Transfer source permission is enforced in management/access.py:495-505.

Notification screenshot follow-up: the inherited screenshot shows no address, so it cannot illustrate configuring a digest. Added an enabled-settings placeholder to the capability and task pages and requested its precise state. Final filesystem count: 68 pages (66 original plus two new); all are listed in the sidebar and depth notes.
