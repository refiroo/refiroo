# Product contract coverage map

**Package:** Base 0.7 WP-13A, 2026-09-24. **Consumers:** WP-13B (command groups), WP-13C (UI
acceptance), WP-9 (composed acceptance) and every later package choosing focused checks.

This map links product contracts to the tests that prove them. It is derived from the invariants in
[AGENTS.md](../../AGENTS.md), the [acceptance scenarios](../product-functionality/ACCEPTANCE_SCENARIOS.md),
[DECISIONS.md](../DECISIONS.md), [API.md](../API.md) and the model contract — not from test-file layout
or recent incidents. Test count and line coverage are not quality measures here; an entry is
**covered** only when a test exercises the promised behavior at a real boundary.

## How to read this map

**Audit status**

| Status | Meaning |
| --- | --- |
| **A✓** | Audited in WP-13A: partitions listed were checked against the tests; evidence is meaningful. |
| **A+** | Audited; a missing partition was filled in WP-13A (named below). |
| **A✗** | Audited; a product defect is confirmed and reproduced by a strict `xfail` test (WP-10 slice). |
| **M** | Mapped to evidence by name and scope, not audited partition-by-partition. Residual risk applies. |
| **P** | Planned outside 0.7; listed so it is not mistaken for coverage. |

**Cost tier** (relative; WP-13B measures actual time)

| Tier | Boundary | Examples |
| --- | --- | --- |
| T0 | Pure function or static source check, no database | `test_model.py`, `test_model_diagnostics.py`, `test_model_independence.py` |
| T1 | Component test, Vitest + jsdom, mocked API | `src/**/*.test.tsx` |
| T2 | Real HTTP request through FastAPI `TestClient` on a temporary or shared SQLite database | most `backend/tests/test_*.py` |
| T3 | Startup, lifespan, Alembic upgrade or interrupted migration against a real temporary database | `test_startup.py`, `test_migrations.py`, `test_wp8_audit_migration.py`, `test_model_schema_upgrade.py` |
| T4 | Real browser against isolated real backend and Vite servers | `frontend/e2e/wp9-*.mjs`, `wp11/12/14-*.mjs`, `ui03*.mjs` |
| T5 | Comprehensive build gates | `npm run test:a11y`, `npm run test:visual`, full suites (WP-9) |

**Risk** is H/M/L from documented impact (data loss, silent overwrite, wrong workspace, unusable
release), likelihood, change frequency in 0.7, boundary complexity (transactions, concurrency,
contexts) and existing evidence. Section 3 ranks the H contracts.

Test references use `file::test` with the `test_` prefix dropped; backend files are under
`backend/tests/`, frontend files under `frontend/src/`, browser runners under `frontend/e2e/`.

**Inventory at audit:** 528 backend test cases collected (after this package's changes, counting
parameterizations), 36 frontend component/unit files with ~200 cases, 10 browser journey scripts,
and accessibility and visual gates with 13 committed baselines. No suite was run in full; collection and source inspection only.

---

## 1. Cross-cutting product invariants

| ID | Invariant | Lowest proving boundary | Evidence | Partitions / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INV-01 | Versioned JSON model is the declarative source; every reference validated at startup with JSON pointer and reason | Pure compile | `model_diagnostics::every_rule_module_is_covered_by_a_case`, `::reference_rule_reports_code_and_path`; `model::compiler_returns_stable_cross_reference_diagnostic_path`, `::compiler_infers_paths_for_top_level_validation_failures`; `model_lifecycle::release_installation_rejects_a_shape_only_model_with_invalid_references` | Every rule module has a failing case (self-checking). Startup refusal of an invalid active model: `model_lifecycle::activation_rejects_corrupted_installed_model_without_mutation`. | A✓ | T0/T2 | H |
| INV-02 | Runtime code is unaware of starter keys; renderers never branch on application/object-type keys | Static source scan | **Added:** `model_independence::runtime_sources_contain_no_starter_model_key_literal` (backend `app/` and frontend `src/`, all starter application, view, object, relation, reverse and attribute keys; four generic words exempt with reasons). Behavioral: `model::detail_composition_changes_are_preserved_without_renderer_changes`; `model/model.test.ts` "produces the same generic panel shape for two different object types"; `ui/ObjectTable.test.tsx` two-type cases | Literal scan does not catch computed keys; behavioral two-type tests cover renderers. Browser runners use starter keys in fixtures, which is permitted. | A+ | T0/T1 | H |
| INV-03 | Attribute types are global; object types attach them through bindings | Pure compile | `model::unknown_attribute_binding_is_rejected`, `::object_cross_field_validation_rejects_unbound_attributes`; `attributes::create_attribute_value_rejects_unattached_key` | | A✓ | T0/T2 | M |
| INV-04 | Relation types define semantics separately from permitted pairs | Pure compile + API | `api::object_type_relations_compatibility_endpoint`; `relations::relation_attributes_must_be_declared_by_the_allowed_pair`; `wp8_graph_validation::invalid_relation_pair_is_a_graph_diagnostic` | | A✓ | T0/T2 | M |
| INV-05 | Parent containment is hierarchy **and** typed relation, maintained atomically | API | Live: `api::delete_object_with_parent_cascades_parent_relation`, `relations::create/update/delete_engine_maintained_relation_is_rejected`, `wp8_review_regressions::live_containment_delete_respects_foreign_keys`, `::activation_reparents_survivor_before_deleting_old_parent`. Draft: `wp8_review_regressions::draft_requires_parent_on_create_update_and_activation` | **Defect WP-10D (fixed 2026-09-24):** editing a *based* contained record in a current-live or revision-derived draft added a second containment edge with a new identity, so activation refused. Now proven by `wp81b_current_live_bases::editing_a_based_child_keeps_its_one_containment_edge_and_activates` (rename keeps the edge ID) and `::moving_a_based_child_replaces_its_containment_edge_and_activates` (one new edge, live parent and edge after activation). | A+ | T2 | H |
| INV-06 | Every model reference fails with precise path — also for mapping views | Pure compile | `model::mapping_grid_rejects_*` (9 cases), `::schema_05_rejects_mapping_grid_with_the_view_type_path` | | A✓ | T0 | M |
| INV-07 | No undocumented result cap; collections are cursor-paged | API + OpenAPI | `pagination::*` (9, pure paginator); `api::metadata_collections_use_cursor_pagination`; `query_foundations::every_built_in_object_sort_supports_cursor_traversal`, `::object_cursor_handles_duplicate_names_and_insert_between_pages`; `mapping_coverage::coverage_pagination_and_cursor_scope_validation`, `::list_mappings_pagination`, `::candidates_multiple_views_search_and_all_pages`; `wp8_history::revision_list_cursor_pagination_is_bounded_and_scoped_to_workspace` | `pageSize` bounds (1–100 mapping, 1–500 elsewhere) are FastAPI-declared and locked by `openapi_contract::base_0_7_wp12_openapi_document_is_locked`; no separate boundary test is needed. | A✓ | T0/T2 | H |
| INV-08 | Cursors are bound to query semantics; foreign or tampered cursors are refused | API | `pagination::paginate_sequence_rejects_a_cursor_from_another_scope`, `::..._from_different_filters`, `::paginate_statement_rejects_an_unparseable_cursor_before_querying`; `api::metadata_cursor_rejects_filter_reuse_and_tampering`; `model_lifecycle::release_cursor_rejects_tampering_and_filter_reuse`; `mapping_coverage::draft_pinned_model_and_release_bound_cursor`, `::cascade_deletion_invalidates_mapping_continuations`; `build07_wp6::model_metadata_and_cursors_follow_the_pin` | | A✓ | T0/T2 | H |
| INV-09 | Bulk/integration APIs are first-class | — | Mapping replacement is the only 0.7 bulk-shaped write (see C-MAP-W). Import/export/change feed | Planned 0.9 (SC-10). | P | — | — |
| INV-10 | Public IDs and model keys stable; no sequence IDs exposed | API + migration | `api::create_object_with_provided_id`, `::create_object_without_id_generates_one`; `wp8_review_regressions::live_relation_is_addressed_only_by_public_uuid`; `request_scope::object_type_public_ids_survive_the_cache`; `migrations::public_id_migration_upgrades_existing_metadata_table`, `::base_0_5_graph_becomes_one_workspace_revision_with_stable_ids`; `wp8_activation::activated_revision_snapshot_preserves_stable_public_uuids_and_membership`; `mapping_replacement::retained_identity` | WP-10D changed a containment relation's identity on draft edit; fixed (INV-05). | A+ | T2/T3 | H |
| INV-11 | Attribute values keep declared types (boolean, numbers, dates never reduced to strings) | API + component | Boolean/number: `typed_table_queries::typed_text_boolean_null_and_unset_filters_are_distinct`, `::numeric_ranges_and_capability_errors_are_model_aware`; `api::attribute_response_format`, `::integer_minimum_is_enforced`; `ui/AttributeField.test.tsx` (false/zero, dates, JSON); `ObjectFormDialog.test.tsx` zero/false. **Added:** `typed_table_queries::date_values_keep_their_type_through_write_filter_and_sort[live]` — valid/invalid calendar dates, non-ISO text, a number, inclusive/exclusive boundary filters, both sort directions, invalid-filter path | **WP-10C (fixed 2026-09-24):** the `[draft]` case, `::draft_writes_keep_decimal_datetime_and_date_values_through_activation` (test model with `decimal`/`dateTime`/`date`: create, update, field endpoint, invalid values, draft filters and sorts, activation) and `pagination::sequence_sort_text_orders_numbers_and_instants_by_value`. **Open WP-10E:** a live `dateTime` write drops its offset (strict xfail `::live_datetime_keeps_its_instant`); live decimals are padded to the column scale. | A✗ | T1/T2 | H |
| INV-12 | Optimistic concurrency; a newer version is never silently overwritten | API | Objects: `api::version_conflict_error_format`; attributes: `attributes::*_rejects_stale_version`, `::version_claim_rejects_an_object_loaded_before_a_competing_write`; relations: `relations::relation_version_claim_rejects_a_relation_loaded_before_a_competing_write`; drafts: `wp8_draft_lifecycle::draft_rename_and_discard_enforce_optimistic_concurrency`, `wp8_review_regressions::stale_loaded_draft_cannot_overwrite_a_committed_rename`; workspaces: `workspaces::default_switch_is_atomic...`; model: `model_lifecycle::concurrent_activation_allows_only_one_runtime_state_claim`; mapping sets: see C-MAP-W | UI side: `ObjectFormDialog` conflict refresh, `draftClient.test.ts`, `ModelWorkbench` version conflict, `MappingGridView` conflict. PostgreSQL concurrency not exercised (SQLite only). | A✓ | T1/T2 | H |
| INV-13 | Model releases are immutable; schema and content versions are separate | API | `model_lifecycle::bootstrap_rejects_same_release_identity_with_different_content`, `::resolved_model_snapshot_graph_is_immutable`, `::concurrent_identical_draft_installations_are_idempotent`; `model_schema_upgrade::schema_04_release_remains_listable_and_exportable_as_history` | | A✓ | T2/T3 | H |
| INV-14 | One request resolves one model snapshot and one DB session | API | `request_scope::one_session_serves_the_whole_request`; `model_lifecycle::resolved_request_snapshots_keep_model_and_metadata_from_one_release`, `::active_model_headers_and_release_read_apis_are_coherent` | | A✓ | T2 | M |
| INV-15 | Operator-facing errors are actionable; no traceback; correlation ID for unexpected failures | API + T3 | `build07_wp11::unexpected_error_includes_correlation_id`; `startup::startup_handles_unsafe_partial_migration_without_a_traceback`; `model_schema_upgrade::startup_reports_the_exact_schema_upgrade_command_without_a_traceback`; `api::error_response_format`; `api/client.test.ts` HTML/non-JSON bodies | WP-10C was an instance where a valid draft write escaped as 500 (correlation ID worked as designed); fixed. | A✓ | T2/T3 | M |
| INV-16 | Workspace scope: explicit keys never fall back to the default; unknown keys fail | API | `workspaces::workspace_catalogue_pages_searches_and_rejects_unknown_scope`, `::default_switch_is_atomic_and_omitted_scope_uses_the_catalogue_default`; `wp81a_context::0_explicit_workspace_key_mismatch_is_rejected_for_all_pinned_read_paths`, `::live_relation_detail_honors_explicit_workspace_key`; `query_foundations::object_parent_candidate_and_relation_queries_preserve_workspace_scope`; `mapping_coverage::coverage_sources_are_scoped_to_the_declaring_application`. **Added:** mapping write in C-MAP-W | UI: `WorkspaceSelector.test.tsx`, `useCursorPages` workspace switch, `wp9-navigation.mjs` two workspaces. | A+ | T1/T2/T4 | H |

---

## 2. Capability contracts

Columns: **Job** is the user or consumer goal; **Context** is live (L), draft (D), revision (R) or
admin; **Promise** lists success / refusal / failure behavior and data effect.

### 2.1 Model metadata and administration

| ID | Job / operation | Context | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-MOD-R | Read applications, types, relations, bindings (`GET /model`, metadata collections) | L, D pin, R pin | Paged, model of the addressed context, no fallback to active | `api::metadata_collections_use_cursor_pagination`; `build07_wp6::model_metadata_and_cursors_follow_the_pin`; `wp81a_context::pinned_model_unavailable_and_invalid_are_structured_without_fallback`; `client.test.ts` exact model per workspace context | | A✓ | T2 | M |
| C-MOD-DRAFT | Create, edit, validate, compile model drafts | admin | Side-effect-free validation, stable diagnostics, optimistic version | `model_lifecycle::draft_crud_compile_and_installation_lifecycle`, `::inline_validation_is_side_effect_free_and_returns_stable_diagnostics`; `ModelWorkbench.test.tsx` conflict recovery | | M | T1/T2 | M |
| C-MOD-INST | Install a release | admin | Recompiled, immutable, idempotent for identical content, refused for conflicting identity; changes no active selection | `model_lifecycle::draft_installation_recompiles_and_rejects_invalid_or_conflicting_content`, `::different_bootstrap_release_installs_inactive_and_preserves_runtime_selection` | | A✓ | T2 | H |
| C-MOD-ACT | Activate a release | admin | Guarded by runtime compatibility, stale tokens, topology (single worker), schema support; refusal changes nothing | `model_lifecycle::activation_blocks_incompatible_runtime_data_without_changing_selection`, `::activation_rejects_stale_runtime_tokens`, `::model_admin_mutations_reject_multi_worker_configuration`, `::registry_refresh_failure_leaves_committed_activation_unready`; `build07_wp11::activation_*`; `wp81a_context::1_*`–`3_*` | Compatibility classes: `model_compatibility::*` (6). | A✓ | T2 | H |
| C-MOD-DIFF | Compare releases; release history and identity (WP-12) | admin | Key-based semantic diff; unsupported schema → 422, missing → 404, corrupt → 500 with correlation | `model_lifecycle::installed_release_diff_is_key_based...`, `::release_diff_*`, `::release_activation_history_*`; `build07_wp11::diff_*` (6); `ModelReleaseDetail.test.tsx` (10); `wp12-release-identity.mjs` | | A✓ | T1/T2/T4 | M |
| C-MOD-OFF | Admin disabled by default; read-only inspection remains | admin | Mutation routes absent, reads available | `model_lifecycle::model_admin_capabilities_and_routes_are_disabled_by_default`; `openapi_contract::base_0_5_enabled_openapi_exposes_guarded_activation`; `ModelWorkbench.test.tsx` "keeps release inspection visible while hiding mutation actions" | | A✓ | T1/T2 | M |

### 2.2 Startup, migration and recovery

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-BOOT | Clean bootstrap, restart | Idempotent bootstrap and restart against a real DB via lifespan | `startup::application_lifespan_boots_and_restarts_against_a_real_clean_database`; `model_lifecycle::first_bootstrap_initializes_runtime_state_and_restart_is_idempotent`; `wp81b::current_live_base_remains_frozen_and_readable_after_restart`; `wp8_retirement::restart_after_activation_and_retirement_persists_state` | | A✓ | T3 | H |
| C-MIG | Upgrade from preceding revisions; interrupted migration refuses safely | Actionable refusal, preserved partial state, no traceback | `migrations::*` (12, including `fresh_migration_provisions_the_complete_current_schema`, `object_lifecycle_migration_recovers_empty_sqlite_ddl_from_interrupted_run`, `workspace_revision_migration_refuses_unknown_partial_ddl`); `wp8_audit_migration::*` (3) | The only 0.7 revision (`20260912_01_relation_set_versions`) is covered by `fresh_migration...`, which compares the head schema with the complete metadata. No upgrade-with-existing-data case targets it; it only adds a lazily populated table (low risk). | A✓ | T3 | H |
| C-SCHEMA-UP | Offline schema upgrade of the selected release | Atomic selection, rollback on incompatibility, exact recovery command | `model_schema_upgrade::*` (6) | | A✓ | T3 | M |

### 2.3 Workspaces

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-WS-CAT | Create, label, search, page workspaces (SC-14) | Stable keys, duplicate refused, unknown key 404 | `workspaces::workspace_catalogue_pages_searches_and_rejects_unknown_scope` | Label change keeping explicit links: indirect only. | M | T2 | M |
| C-WS-DEF | Change default workspace | Atomic claim; omitted scope follows default; explicit scope unaffected | `workspaces::default_switch_is_atomic_and_omitted_scope_uses_the_catalogue_default`; `App.test.tsx` "uses the catalogue runtime default" | | A✓ | T1/T2 | M |
| C-WS-RET | Catalogue retirement (read-only workspace) | Default cannot be retired; retired remains readable; **every** runtime mutation refused with `workspace_retired` | `workspaces::retired_workspace_remains_readable_but_blocks_all_runtime_mutations` (object create/update/delete, attribute, relation); `wp8_draft_lifecycle::catalogue_retirement_blocks_draft_derive_rename_and_discard`; `wp8_review_regressions::retired_catalogue_rejects_publication_retirement`; **Added:** `mapping_replacement::replacement_authority_follows_the_addressed_workspace_context` (live and draft mapping writes) | UI: `App.test.tsx` retired context without mutation entry points; `WorkspaceSelector.test.tsx`. | A+ | T1/T2 | H |
| C-WS-OFF | Workspace admin mutations can be disabled | Discovery remains | `workspaces::workspace_mutations_can_be_removed_while_discovery_remains` | | A✓ | T2 | L |

### 2.4 Live records, attributes, relations and deletion

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-OBJ-C | Create a record with typed fields and parent (SC-03) | One request; required fields, parent type, uniqueness; refusal leaves nothing | `api::create_*` (6), `::unique_attribute_*` (3), `::create_rejects_invalid_parent_object_id`; `ObjectFormDialog.test.tsx`; `wp9-authoring.mjs` | | A✓ | T1/T2/T4 | H |
| C-OBJ-U | Correct a record (SC-02) | Same identity; partial update; required not nullable; stale refused with current content | `api::partial_update_without_required_attribute_succeeds`, `::update_cannot_null_required_attribute`, `::version_conflict_error_format`; `ObjectFormDialog.test.tsx` conflict; `InlineAttributeEditor.test.tsx`; `wp9-authoring.mjs` | Live parent move: `wp9-authoring.mjs` "parent moves" (browser only). | A✓ | T1/T2/T4 | H |
| C-ATTR | Field sub-resource read/write/delete | Typed, versioned, required/read-only protected | `attributes::*` (21); `wp7_canonical_crud::historical_attribute_read_uses_the_canonical_subresource`; `AttributesPanel.test.tsx` | | A✓ | T1/T2 | M |
| C-REL | Relation CRUD (non-parent edges) | Declared attributes/types; engine-maintained edges immutable; stale refused; duplicates conflict without orphans | `relations::*` (19); `RelationsPanel.test.tsx` (6) | | A✓ | T1/T2 | H |
| C-DEL | Delete with truthful signed preview (SC-04) | Preview lists owned and affected; confirm with exact token; any change after preview → retry conflict, no side effects; independent endpoints survive | `cascade_delete::*` (4); `wp8_review_regressions::cascade_*` (4), `::association_delete_requires_confirmation_and_retains_other_endpoint`, `::missing_preview_token_precedes_stale_root_version`, `::live_delete_refuses_corrupt_cross_workspace_*`; `api::delete_object_with_children_is_rejected`, `::delete_object_with_mapping_relation_is_rejected`; `ObjectDeleteDialog.test.tsx`; `wp9-authoring.mjs`, `wp9-drafts.mjs` | | A✓ | T1/T2/T4 | H |
| C-TR | Translations created atomically with target; duplicates refused (SC-03) | No partial translation; last content attribute cannot be removed | `translations::*` (7); `wp8_graph_validation::translation_*` (3), `::duplicate_translation_language_target_is_a_graph_diagnostic`; `wp8_activation::atomic_translation_publication` | Draft-context translation create on a based target: covered by browser `wp9-drafts.mjs` only. | M | T2/T4 | M |
| C-HIST-OBJ | Record activity history | Bounded pages, safe fields, relation events on both endpoints | `query_foundations::object_history_includes_safe_object_and_connected_relation_events`, `::relation_writes_project_both_endpoint_subjects`; `wp7_canonical_crud::draft_history_projects_canonical_mutation_events`; `HistoryPanel.test.tsx` (3) | | A✓ | T1/T2 | L |

### 2.5 Queries

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-Q-FILTER | Typed filters, search, sort (SC-01) | Model-declared only; typed parsing with path-precise 422; null vs unset distinct; stable cursors | `typed_table_queries::*` (5 + date); `query_foundations::object_lifecycle_is_bound_to_cursor_filters_and_sort`; `CollectionView.test.tsx` (6); `client.test.ts` filter encoding; `wp9-navigation.mjs` UI-02 | Date partition added (INV-11). Draft/revision lists filter and sort by declared type since WP-10C (numbers had sorted as text); `integer` draft paging covered in `::numeric_ranges_and_capability_errors_are_model_aware`. `dateTime` built-ins (`createdAt`) only filter-parsed, not end-to-end tested — low risk. | A+ | T1/T2/T4 | M |
| C-Q-SCOPE | Direct-parent scope (`parentObjectId`) and application scope | Cursor-bound; valid in L/D/R | `mapping_coverage::coverage_parent_and_state_filters_apply_before_pagination`, `::draft_coverage_parent_scope_uses_effective_objects`; `CollectionView.test.tsx` direct-parent scope; `wp14-contextual-browser.mjs` | Object-list `parentObjectId` in revision context: indirect via shared read path. | M | T1/T2/T4 | M |

### 2.6 Data drafts, activation, history and retirement

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-DR-SRC | Start a draft from current live, a revision, or empty (SC-05) | Frozen capture of current live including unpublished work; explicit source; refusals keep meaning | `wp81b_current_live_bases::*` (10, plus the WP-10D xfail); `wp8_draft_lifecycle::draft_derivation_*`, `::empty_root_draft_creation_records_created_audit_event`; `WorkspaceHistory.test.tsx`; `wp9-drafts.mjs` | | A✓ | T2/T4 | H |
| C-DR-EDIT | Edit records inside a draft | Copy-on-write; draft version claimed; live untouched; typed values retained; containment maintained | `workspace_revisions::workspace_draft_membership_is_copy_on_write_with_tombstones`; `wp7_canonical_crud::*`; all `DraftTestClient` suites (`api`, `typed_table_queries`, `attributes`, …) | **Structural gap found:** `DraftTestClient` starts an *empty* draft, so the "edit a record inherited from a base" partition was barely exercised. Probing it found WP-10C (typed values, 500) and WP-10D (containment edge duplication), both fixed with based-draft regressions. Attribute-endpoint edits and deletes of based records behave correctly. | A+ | T2 | H |
| C-DR-VAL | Validate the complete draft graph | Side-effect free; every graph rule a diagnostic | `wp8_graph_validation::*` (20) | | A✓ | T2 | H |
| C-DR-ACT | Activate: delta merge over current live (SC-06) | All or nothing; preserves unrelated live work; refuses touched-record conflicts, divergent touched mapping sets, invalid merged graph, stale pins/revisions | `wp8_activation::*` (10), especially `::no_partial_publication_after_every_failure_class`; `wp8_activation_merge::*` (4); `wp81b::current_live_activation_*` (2); `mapping_replacement::activation_*` (5); `relation_set_versions::draft_activation_merges_set_versions_into_live`; `wp9-drafts.mjs` | Based child rename/move (WP-10D) and typed values (WP-10C) now activate. | A✓ | T2/T4 | H |
| C-DR-LIFE | Rename, discard, list drafts | Optimistic; discard removes only mutable draft data (and set-version rows) | `wp8_draft_lifecycle::*`; `relation_set_versions::draft_discard_cascades_set_version_rows`; `wp81b::discard_and_successful_activation_remove_private_base_rows_with_sqlite_fk_off`; `WorkspaceDrafts.test.tsx` | | A✓ | T1/T2 | M |
| C-DR-PIN | Draft model version selection (SC-15, ADR-028) | Complete-candidate compatibility on create/change; atomic audited pin change; refusal changes nothing; pinned reads; activation refused when pin ≠ active | `build07_wp6::*` (13); `wp81a_context::0_unsupported_pinned_draft_model_is_explicit...`, `::draft_write_uses_pinned_model_when_active_registry_is_unhealthy`; `wp8_graph_validation::non_active_pin_validates_its_graph_without_activation_agreement`; `WorkspaceDrafts.test.tsx`, `WorkspaceDataContext.test.tsx`; `App.test.tsx` removed-view recovery; `wp11-model-admin.mjs` | | A✓ | T1/T2/T4 | H |
| C-REV | Read immutable history (SC-08) | Revision reads never change; pinned model; newest first; paged | `wp8_history::*` (6); `wp81a_context::4_pinned_history_survives_active_model_switch...`; `historyClient.test.ts`; `WorkspaceHistory.test.tsx`; `App.test.tsx` immutable history; `wp9-history.mjs` | | A✓ | T1/T2/T4 | H |
| C-PUB-RET | Publication retirement | Clears pointer only; live stays writable; history readable; claim enforced | `wp8_retirement::*` (9) | | A✓ | T2 | M |

### 2.7 Mapping (0.7)

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-MAP-R | Coverage, list, candidates, target details (SC-07/16) | Bounded batched reads; exact counts; states filtered before paging; both directions; application-scoped; L/D/R contexts; stale continuation refused | `mapping_coverage::*` (27), including `::coverage_query_count_does_not_grow_per_source`, `::concurrent_coverage_keeps_edges_fields_and_versions_in_one_snapshot`, `::revision_coverage_is_immutable_scoped_and_version_bound`; `MappingGridView.test.tsx` rendering/state cases; `wp14-contextual-browser.mjs` | Candidates in revision context rely on the shared `open_mapping_read` path; not separately asserted. | A✓ | T1/T2/T4 | H |
| C-MAP-W | Atomic replacement (create, replace, clear) | Set-version claim; retained identity/attributes; direction-aware cardinality; forbidden clear/ownership; draft version claimed; independent bindings untouched; **authority follows addressed workspace/draft** | `mapping_replacement::*` (43 functions), including `::concurrent_replacements_claim_initial_set_once`, `::overlapping_generic_write_forces_mapping_save_to_refresh`, `::independent_binding_is_unchanged_by_replacement_and_clear`. **Added:** `::replacement_authority_follows_the_addressed_workspace_context` — foreign-workspace draft (404), unknown workspace (404, no default), revision body field (422), retired live and draft (409 `workspace_retired`), no data change in any refusal | | A+ | T2 | H |
| C-MAP-SET | Relation-set versions across all generic relation writes (ADR-022) | Every create/update/delete/cascade in L and D advances both anchors' set versions; L and D independent | `relation_set_versions::*`; `mapping_coverage::cascade_deletion_invalidates_mapping_continuations`. **Added:** `relation_set_versions::draft_relation_update_and_delete_advance_both_draft_anchors_only`; live update now asserts the PATCH succeeded | Before WP-13A, draft update/delete had no evidence and the live update test did not check its request succeeded. | A+ | T2 | H |
| C-MAP-UI | Mapping lens: search, select, save, remove, conflict review | Conflict shows current targets and keeps the attempted choice; explicit remove only; read-only hides actions | `MappingGridView.test.tsx` (22). **Strengthened:** the conflict case now asserts the retry sends the user's attempted target (`targetObjectId`), not just the new version; `wp14-contextual-browser.mjs` real replacement | Contextual target creation and keyboard/a11y evidence for new controls: WP-13C/WP-9. | A+ | T1/T4 | H |

### 2.8 Frontend shell and interaction contracts

| ID | Job / operation | Promise | Evidence | Missing / notes | Status | Tier | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-UI-NAV | Keep my place (SC-01, SC-16) | URL-backed workspace/context/query/scope/lens; origin return; reload/Back/Forward | `routes.test.ts` (9); `useRouter.test.tsx` (4); `App.test.tsx` (17); `wp9-navigation.mjs`, `ui03a-navigation.mjs`, `wp14-contextual-browser.mjs` | | M | T1/T4 | H |
| C-UI-DIRTY | Never lose typed input | Guarded navigation, dialogs, failed save, conflicts | `useRouter.test.tsx`; `ObjectFormDialog.test.tsx`; `Modal.test.tsx`; `InlineAttributeEditor.test.tsx`; `WorkspaceDataContext.test.tsx`; `ui03a-navigation.mjs` | | M | T1/T4 | H |
| C-UI-RETRY | Failed reads keep loaded content and retry the exact request | | `useCursorPages.test.tsx`, `useCursorFeed.test.tsx`, `CollectionPanelTable.test.tsx`, `RelationsPanel.test.tsx`, `ObjectLookup.test.tsx`, `HistoryPanel.test.tsx`, `Explorer.test.tsx`, `WorkspaceHistory.test.tsx` | | M | T1 | M |
| C-UI-A11Y | Keyboard, semantics, contrast, visual stability | | `Modal.test.tsx`, `UIFoundation.test.tsx`; `accessibility-gate.mjs`; `visual-regression-gate.mjs` + 13 baselines | New 0.7 surfaces' state inventory and screenshots: WP-13C. | M | T1/T5 | M |

---

## 3. Risk ranking and audit record

High-risk contracts in priority order, with the partitions audited. "Normal / boundary / invalid /
unavailable / conflict / unexpected dependency" are the outcome classes from the WP-13A method;
omissions state why.

| Rank | Contract | Why high | Partitions audited | Result |
| --- | --- | --- | --- | --- |
| 1 | C-DR-EDIT / INV-05 | Draft edits feed activation; defects block publication or corrupt structure; 0.7 added based drafts to more flows | normal (root/child rename, move, attribute endpoint, delete on based records), invalid (bad date) | **2 defects**, fixed as WP-10C/WP-10D |
| 2 | C-MAP-W | New 0.7 write path; silent loss of a mapping is the SC-07 failure | normal, conflict, invalid context (foreign/unknown/revision), unavailable (retired live/draft) | covered + authority gap filled |
| 3 | C-MAP-SET | Concurrency boundary shared by generic and mapping writes | create/update/delete × L/D × outgoing/incoming anchors | draft update/delete gap filled |
| 4 | C-DR-ACT | All-or-nothing publication | every failure class (`no_partial_publication_after_every_failure_class`), conflict variants, based edits | covered; WP-10D fixed |
| 5 | INV-11 | Types reduced to strings or lost silently | boolean, integer, date (valid/invalid/boundary/sort), null vs unset, L/D | date gap filled; WP-10C fixed; live `dateTime` offset loss open as WP-10E |
| 6 | INV-02 | Architectural invariant with no automated guard | static literal scan | guard added |
| 7 | C-WS-RET / INV-16 | Wrong-workspace or retired writes | every runtime write route incl. mapping | mapping gap filled |
| 8 | C-DR-PIN, C-MOD-ACT, C-MIG, C-BOOT | Model/runtime selection and startup | mapped by name to dense existing suites | covered (not re-audited partition by partition) |

Unexpected-dependency outcomes (registry unavailable, corrupt release, unsupported schema, HTML
error bodies) are covered by `wp81a_context::pinned_resolution_reports_registry_unavailable_as_structured_http_error`,
`build07_wp11::*` and `api/client.test.ts`. Database unavailability mid-request is not simulated;
it falls back to the correlation-ID handler (INV-15).

## 4. Changes made in WP-13A

| Change | File | Protects |
| --- | --- | --- |
| Added | `backend/tests/test_mapping_replacement.py::test_replacement_authority_follows_the_addressed_workspace_context` | C-MAP-W, C-WS-RET, INV-16 |
| Added | `backend/tests/test_relation_set_versions.py::test_draft_relation_update_and_delete_advance_both_draft_anchors_only` | C-MAP-SET |
| Strengthened | `backend/tests/test_relation_set_versions.py::test_update_relation_increments_set_versions` asserts its PATCH succeeded | C-MAP-SET |
| Added | `backend/tests/test_model_independence.py::test_runtime_sources_contain_no_starter_model_key_literal` | INV-02 |
| Added (live and draft) | `backend/tests/test_typed_table_queries.py::test_date_values_keep_their_type_through_write_filter_and_sort` | INV-11, C-Q-FILTER; reproduced WP-10C, now passing |
| Added | `backend/tests/test_wp81b_current_live_bases.py::test_editing_a_based_child_keeps_its_one_containment_edge_and_activates` | INV-05, INV-10, C-DR-ACT; reproduced WP-10D, now passing |
| Strengthened | `frontend/src/features/objects/views/MappingGridView.test.tsx` conflict retry asserts the attempted `targetObjectId` | C-MAP-UI (SC-07 "preserve the attempted choice") |
| Removed | `backend/tests/test_relation_set_versions.py::test_existing_relation_tests_still_pass_transparently` | See section 5 |

The two WP-13A `xfail(strict=True)` reproductions failed at their intended assertions (checked with
`--runxfail`) and became ordinary passing evidence when WP-10C/WP-10D landed the same day.

**WP-10C/WP-10D follow-up (2026-09-24):** added
`typed_table_queries::draft_writes_keep_decimal_datetime_and_date_values_through_activation`,
integer draft paging in both sort directions in `::numeric_ranges_and_capability_errors_are_model_aware`,
`pagination::sequence_sort_text_orders_numbers_and_instants_by_value` and
`wp81b_current_live_bases::moving_a_based_child_replaces_its_containment_edge_and_activates`.
`typed_table_queries::live_datetime_keeps_its_instant` is a strict `xfail` reproducing open WP-10E.

## 5. Redundancy and consolidation

| Candidate | Decision | Surviving protection / reason |
| --- | --- | --- |
| `relation_set_versions::existing_relation_tests_still_pass_transparently` (create a mapping relation; assert 201, id, type, version 1, no `mappingVersion` field) | **Removed** | `relations::get_relation_by_id_returns_stored_relation` creates the same relation and asserts identity, type, endpoints, attributes and version 1; the response shape is enforced by `response_model=RelationResponse` and locked by `openapi_contract::base_0_7_wp12_openapi_document_is_locked`. |
| `openapi_contract` partial inventories (`wp6_*`, `wp8_*`, `wp4_*`, `build07_wp6_*`) vs the whole-document hash lock | Kept | The hash lock is re-baselined on every intentional API change and says nothing about intent. The named inventories protect specific promises (rejected lifecycle routes stay absent, mapping context parameters stay required) that survive a re-hash. |
| `pagination::*` (pure paginator) vs per-endpoint cursor tests | Kept | Pure tests cover keyset mechanics cheaply (T0); endpoint tests prove each collection is wired to them with its own scope. Different boundaries, distinct assertions. |
| `DraftTestClient` re-running legacy CRUD suites in a draft | Kept, but insufficient | It proves draft routing of the same assertions; it does not cover based records (section 2.6). WP-10C/10D fixes should add based-draft cases rather than more empty-draft repetition. |
| `mapping_coverage::list_mappings_*` (14 small cases) | Kept | Each asserts a distinct filter or projection; consolidation into parameterization would save little. Candidate for WP-13B grouping, not removal. |

## 6. Recent incidents mapped to the same taxonomy

| Incident | Contract | Now protected by |
| --- | --- | --- |
| WP-10A: cascade deletion did not advance mapping-set versions | C-MAP-SET, INV-08 | `mapping_coverage::cascade_deletion_invalidates_mapping_continuations` |
| WP-10B: activation accepted a new live edge in a set the draft cleared | C-DR-ACT, C-MAP-SET | `mapping_replacement::activation_refuses_live_divergence_in_touched_mapping_set`, `::activation_protects_initially_empty_mapping_set` |
| WP-11: unsupported schema diff/activation returned 500 | C-MOD-DIFF, C-MOD-ACT, INV-15 | `build07_wp11::*` |
| WP-8 review regressions (preview tokens, parent requirements, cross-workspace corruption) | C-DEL, INV-05, INV-16 | `wp8_review_regressions::*` |
| WP-13A: WP-10C draft typed values (500, text-ordered numbers) | INV-11, C-DR-EDIT, C-Q-FILTER | `typed_table_queries::date_values_...[draft]`, `::draft_writes_keep_decimal_datetime_and_date_values_through_activation`, `pagination::sequence_sort_text_orders_numbers_and_instants_by_value` |
| WP-13A: WP-10D based child containment duplication | INV-05, INV-10, C-DR-ACT | `wp81b_current_live_bases::editing_a_based_child...`, `::moving_a_based_child...` |

## 7. Unaudited areas and residual risk

- **M-status rows** were mapped by test name and scope only; partitions were not checked one by one.
  The highest-residual ones are C-UI-NAV and C-UI-DIRTY (browser-only evidence, expensive to rerun)
  and C-TR draft translations on based targets.
- **Based-draft edits beyond those probed:** translation create/delete on a based target, relation
  edits between based records, and draft moves across applications were not probed. WP-10C/10D
  suggest this partition still deserves a dedicated sweep.
- **Typed value representation (WP-10E, open):** live `dateTime` values lose their offset; live
  decimals are padded to the column scale while draft writes keep the submitted form, so draft
  uniqueness compares unequal strings for equal decimals. Existing deployed `dateTime` data may need
  a migration decision.
- **Draft built-in timestamps:** draft-local records carry no `createdAt`/`updatedAt`, so those
  filters match none of them in a draft list (pre-existing; not changed by WP-10C, which only stopped
  mixed naive/aware comparisons from failing). Decide the intended draft semantics before 0.7 acceptance.
- **Order-dependent test (resolved in WP-13B):** `pagination::statement_paginator_accepts_the_historical_draft_cursor_identity`
  failed when run alone (no schema yet); it now owns a migrated database.
- **Concurrency** is proven on SQLite only; PostgreSQL locking behavior is not exercised (WP-9 or
  production milestone).
- **Frontend mapping controls** (contextual target creation, keyboard operation, narrow layout)
  and every materially changed 0.7 surface's state inventory belong to WP-13C.
- **Timing and command grouping** are delivered in the [execution guide](EXECUTION_GUIDE.md) (WP-13B):
  pytest group markers, Vitest projects, boundary-to-check expansion and measured costs.
- **Planned capabilities** (integration, business dates, authentication, staged migration, 0.8
  specialist views) have no evidence by design.
