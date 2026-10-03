# API inventory by journey

**H4a, 2026-10-02.** Every route, parameter and error code of the management API, every operator
setting and command, and every browser runner, mapped to the [user journeys](../product-functionality/USER_JOURNEYS.md)
that use it. The API is the product: an option is justified by a journey of any client (integrator,
steward, operator, model author), not by the built-in UI. What maps to no journey, or reaches one goal
in two ways without a reason, is listed under [Decisions](#decisions).

Built from the OpenAPI document of `create_app()` (81 operations, model administration enabled) and
the codes the backend raises (139). `tests/test_api_journeys.py` (H4b) keeps this file in step with both: a route,
parameter or code missing here fails it.

## Shared parameter groups

| Parameters | Routes | Journeys |
| --- | --- | --- |
| `workspaceKey` | record, relation, model and metadata reads; writes | J01.2, J19, J21, J22 |
| `changeSetId`, `publicationId` (exclusive with each other) | every read with a context; `changeSetId` on writes | J01.1, J05, J07.1, J20.1, J21.6, J22 |
| `expectedVersion`, `expectedChangeSetVersion` | every write and delete | J02.2, J05.6, J13, J19 |
| `pageSize`, `cursor`, `from`, `position`, `includeTotal` | every collection | J21, J21.1, J21.2, J21.4 |
| `seek` | objects, lookup, relations, mapping coverage, relation matrix | J21.3 |
| `search`, `sort`, `filter.<field>.<operator>` | per-type list, lookup (built-in fields), relations, coverage | J01, J01.3, J22, J22.3 |
| `parentObjectId`, `topLevel` | per-type list, lookup, coverage, matrix | J01, J14 |
| `asOf` | per-type list, query body; on the lookup it is refused (D21) | J23, J22.4 |
| `applicationKey`, `viewKey` | lookup, mapping and matrix reads | J01, J10, J16, J22.1 |
| `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction` | relations, edge list, mapping reads | J10, J13, J22.2, J22.3 |
| `Idempotency-Key` header | `POST /batches` | J11.5, J24 |

## Routes

Every operation, by method and path (under `/api/v1` except `/health`, `/docs` and `/openapi.json`).

| Operation | Journeys |
| --- | --- |
| `GET /health` | J12 |
| `GET /docs`, `GET /openapi.json` | J20 |
| `GET /capabilities` | J20, J12.7 |
| `GET /model`, `GET /model/placements` | J20, J20.1, J03, J14 |
| `GET /model-runtime-state` | J08 (fresh version for activation), J20.2 |
| `POST /model-validations` | J08.1 |
| `GET /applications`, `GET /applications/{key}`, `GET /attribute-types`, `GET /attribute-types/{key}`, `GET /object-types`, `GET /object-types/{key}`, `GET /relation-types`, `GET /relation-types/{key}` | J20 |
| `GET /object-type-relations` (`fromObjectType`, `toObjectType`) | J20, J13 |
| `GET /model-releases` (`releaseKey`, `active`), `GET /model-releases/{id}` (`includeModel`) | J08, J08.7, J20.2 |
| `GET /model-releases/{id}/activations` | J08.8 |
| `GET /model-releases/{id}/diff` (`againstReleaseId`) | J08.2, J25 |
| `POST /model-releases/{id}/activation` | J08, J08.3, J08.5, J08.6 |
| `GET/POST /model-drafts`, `GET/PATCH/DELETE /model-drafts/{id}` | J08 |
| `POST /model-drafts/{id}/compile`, `POST /model-drafts/{id}/installation` | J08, J25 |
| `GET/POST /workspaces` (`search`, `status`) | J19, J19.3 |
| `GET/PATCH/DELETE /workspaces/{key}` | J19 |
| `GET/PATCH /workspace-runtime-state` | J19 (default), J19.1 |
| `GET/POST /workspaces/{key}/change-sets` | J05, J05.1–J05.3, J18 |
| `GET/PATCH/DELETE /change-sets/{id}` | J05.5 |
| `PATCH /change-sets/{id}/model-release` | J18, J18.4 |
| `GET /change-sets/{id}/object-changes` (`kind`, `objectTypeKey`), `GET /change-sets/{id}/relation-changes` (`kind`, `relationTypeKey`, `containment`) | J17 |
| `POST /change-sets/{id}/restructurings/preview`, `POST /change-sets/{id}/restructurings` | J15 |
| `POST /change-sets/{id}/validation` | J05.4 |
| `POST /change-sets/{id}/publication` | J05, J06, J18 |
| `GET /workspaces/{key}/publications`, `GET /publications/{id}` | J07, J07.1 |
| `POST /publications/{id}/withdrawal` | J07 |
| `POST /objects` | J03, J14, J16 |
| `GET /objects` (cross-type lookup, `objectTypeKey` repeatable) | J22.1, J01.4 |
| `GET /objects/{type}` | J01, J21, J22, J23 |
| `GET /objects/{type}/{id}` | J01 |
| `PATCH /objects/{type}/{id}` | J02, J14 (move) |
| `DELETE /objects/{type}/{id}` (`cascade`, `deletionPreviewToken`) | J04 |
| `GET /objects/{type}/{id}/parent-candidates` (`parentObjectTypeKey`, `includeTypeChanges`, `withinObjectTypeKey`) | J14, J15 |
| `GET /objects/{type}/{id}/history` | J01.6, J15 |
| `POST /workspaces/{key}/queries/objects` | J22, J23 |
| `GET/POST/PATCH/DELETE /objects/{type}/{id}/attributes/{key}` | J01.5, J02.4 |
| `POST /relations`, `PATCH/DELETE /relations/{id}` (`expectedRelationSetVersion`, `relationSetDirection`) | J13, J13.5, J16 |
| `GET /relations` (`objectId`), `GET /relations/{id}` | J01, J22.3 |
| `GET /workspaces/{key}/mapping-coverage` (`state`) | J10 |
| `GET /workspaces/{key}/mapping-candidates`, `GET /workspaces/{key}/mapping-targets` (`sourceObjectId`, `mappingVersion`) | J10, J10.3 |
| `PUT /workspaces/{key}/mappings` | J10 |
| `GET /workspaces/{key}/relations` | J22.2, J10 (a relationship view's edges, with `applicationKey` and `viewKey`) |
| `GET /workspaces/{key}/relation-matrix` (`columnIds`, `columnCursor`, `columnPageSize`, `state`) | J16 |
| `GET /workspaces/{key}/relation-matrix/containers`, `GET /workspaces/{key}/relation-matrix/link-candidates` (`rowId`, `columnId`) | J16 |
| `POST /batches` (`run`: `inline`) | J11 |
| `POST /batches` (`run`: `background`), `GET /jobs` (`kind`, `state`), `GET /jobs/{id}`, `GET /jobs/{id}/items` (`status`), `POST /jobs/{id}/cancel` | J24 |

## Error codes

Every code the API returns, by the journey that meets it. 32 of them were raised by the backend but
documented nowhere; API.md documents them since H4c (D-4).

| Journeys | Codes |
| --- | --- |
| Every route | `request_validation_error`, `unknown_parameter` (J21.8), `internal_error` (with a correlation ID), `invalid_cursor`, `invalid_position`, `conflicting_page_parameters`, `invalid_seek`, `mutually_exclusive_context`, `workspace_not_found`, `change_set_not_found`, `publication_not_found`, `workspace_context_mismatch`, `model_registry_unavailable`, `model_runtime_state_unavailable`, `workspace_runtime_state_missing` |
| J01, J21, J22 | `object_not_found`, `unknown_object_type`, `invalid_filter`, `invalid_sort`, `invalid_query`, `mutually_exclusive_scope`, `workspace_key_required`, `attribute_not_found` |
| J02, J03, J13, J14 (the write rules) | `version_conflict`, `version_required`, `invalid_attribute_value`, `attribute_below_minimum`, `attribute_above_maximum`, `unknown_attributes`, `unknown_attribute_type`, `duplicate_attribute`, `duplicate_attribute_value`, `missing_required_attributes`, `object_attribute_rule_violation`, `cannot_delete_required_attribute`, `read_only_attributes`, `attribute_already_exists`, `object_already_exists`, `unknown_application`, `invalid_object_type_for_application`, `object_type_not_in_application`, `parent_required`, `invalid_parent_type`, `parent_wrong_scope`, `parent_cycle`, `missing_required_relations`, `duplicate_initial_relation`, `duplicate_relation`, `duplicate_relation_scope`, `unknown_relation_type`, `invalid_relation_pair`, `relation_endpoint_missing`, `relation_wrong_scope`, `unknown_relation_attributes`, `immutable_relation`, `required_relation`, `cardinality_violation`, `relation_not_found`, `relation_set_version_conflict`, `relation_set_claim_incomplete`, `workspace_retired` |
| J04 | `deletion_preview_required`, `deletion_preview_changed`, `object_has_dependants` |
| J05, J06, J07, J17 | `change_set_required`, `change_set_version_conflict`, `change_set_snapshot_retry`, `change_set_source_invalid`, `change_set_base_invalid`, `workspace_graph_invalid`, `activation_conflict`, `workspace_active_publication_conflict` |
| J10 | `mapping_version_conflict`, `invalid_clear_attributes`, `required_ownership_binding`, `relation_ancestor_required`, `mapping_view_required`, `mapping_view_not_found`, `mapping_view_binding_mismatch`, `mapping_binding_not_found`, `mapping_source_not_found`, `mapping_candidate_type_mismatch`, `mapping_endpoint_not_found`, `mapping_endpoint_type_mismatch`, `mapping_parent_not_found`, `mapping_parent_scope_mismatch`, `incomplete_view_identity` |
| J15 | `restructuring_not_ready`, `restructuring_too_large`, `restructuring_plan_changed`, `invalid_type_mapping`, `object_type_unchanged`, `object_type_changed`, `type_changes_need_change_set`, `child_type_not_allowed`, `required_relation_without_place`, `relation_already_exists` |
| J16 | `relation_matrix_view_not_found`, `relation_matrix_row_not_found`, `relation_matrix_column_not_found`, `relation_matrix_parent_not_found`, `relation_matrix_action_not_allowed`, `relation_matrix_parent_scope_mismatch`, `relation_matrix_state_requires_columns`, `too_many_columns`, `duplicate_column_ids`, `conflicting_column_parameters` |
| J18 | `change_set_content_incompatible`, `change_set_model_release_conflict`, `pinned_model_unavailable`, `pinned_model_invalid`, `unsupported_pinned_model_schema`, `invalid_installed_model` |
| J08, J25 | `invalid_model`, `release_identity_conflict`, `model_migration_required`, `model_release_not_found`, `model_draft_not_found`, `unsupported_schema_version`, `model_registry_refresh_failed`, `consumer_contract_version_required`; diff findings `consumer_api_removed`, `consumer_contract_version_decreased` |
| J08, J11, J24 | `model_release_changed` |
| J19 | `workspace_already_exists`, `default_workspace_cannot_be_retired`, `workspace_is_default`, `workspace_has_publications`, `workspace_not_empty` |
| J23 | `as_of_not_supported`, `invalid_effective_period` |
| J11, J24 | `batch_too_large`, `invalid_batch_context`, `idempotency_key_reused`, `idempotency_in_progress`, `missing_record_key`, `invalid_record_key`, `reference_not_found`, `reference_type_mismatch`, `job_not_found`, `job_finished`, `job_failed` |

## Operator surface (J12)

| Setting or command | Journeys |
| --- | --- |
| `DATABASE_URL` | J12, J12.1 |
| `RDM_MODEL_PATH` | J12 (the starter or bootstrap model), J08 |
| `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, `INTEGRATION_JOBS_ENABLED` | J12.7, J08, J19.4, J11 |
| `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`, `ATOMIC_JOB_MAX_ITEMS`, `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`, `JOB_CHUNK_ITEMS`, `JOB_LEASE_SECONDS`, `JOB_RETENTION_DAYS` | J12.7, J11, J24 |
| `WEB_CONCURRENCY` | J12.7 (refused above 1 with model administration) |
| `CORS_ORIGINS` | J12.7 (a browser client on another origin) |
| `RDM_CURSOR_SIGNING_KEY` | J21 (cursors that survive a restart), J12.7 |
| `RDM_API_REFERENCE_SCRIPT` | J20, J12.7 |
| `python -m app.cli.database_upgrade` | J12, J12.5 |
| `python -m app.cli.model_schema_upgrade --model` | J12.6 |
| `scripts/postgres.sh start\|stop\|status\|backup` | J12 (development) |

## Browser runners and frontend tests

| Runner or area | Journeys |
| --- | --- |
| `wp9-navigation`, `ui03a-navigation`, `wp14-contextual-browser` | J01, SC-01, SC-16 |
| `wp9-authoring`, `record-actions` | J02, J03, J04, J08 |
| `wp9-change-sets` | J04.4, J05, J06 |
| `wp9-publications` | J07 |
| `ui03b-deletion` | J04 |
| `ui03b-hierarchy`, `s6-sidebar-tree`, `b3-tree-lens`, `b4-hierarchy-acceptance` | J14 |
| `c4-restructuring`, `c5-restructuring-acceptance` | J15 |
| `sc07-mapping-acceptance`, `wp13c-ui-states` | J10 |
| `a4-relation-matrix`, `a5-matrix-acceptance` | J16 |
| `p2-change-review` | J17 |
| `sc15-model-version-acceptance`, `wp11-model-admin` | J18 |
| `wp12-release-identity` | J08 |
| `w4-workspace-admin` | J19 |
| `s5-continuous-lists`, `s7-volume-acceptance` | J21 |
| `v1-api-reference` | J20 |
| `accessibility-gate`, `visual-regression-gate` | every UI journey (gates, not journeys) |
| Vitest `src/features/objects/**` | J01–J04, J10, J13–J16 |
| Vitest `src/features/workspaces/**` | J05–J07, J17–J19 |
| Vitest `src/features/model-admin/**` | J08 |
| Vitest `src/api`, `src/lib`, `src/model`, `src/routing`, `src/ui`, `src/app` | the UI channel of every journey (client, routing, paging window, shared components) |

## Decisions

Raised by the inventory; answered by the user on 2026-10-02.

- **D-1. `/workspaces/{key}/mappings` and `/workspaces/{key}/relations` (GET).** *Decided: remove
  `GET /mappings`* (*delivered in H4c, 2026-10-03*, with the OpenAPI lock re-baselined; the path keeps
  the `PUT` and answers a `GET` with `405`, J22.2). The two are identical in input and output: one parameter set (`EdgeList`), one
  paging, one response model (`MappingListPage`), one function (`edge_list`). Only their cursors
  differ (each route refuses the other's) and their reference-page tag. The built-in UI calls
  neither (it uses `PUT /mappings` to save). Two ways with no reason: `GET /workspaces/{key}/relations`
  stays and takes the same mapping-view parameters; `PUT /mappings` (J10's save) stays. The first
  recommendation, to keep both, was made from the Q2 record without reading the code; it was wrong.
- **D-2. Two ways to change one value.** *Decided: keep both*, as J02 and its variant J02.4. The
  attribute resource is also the only way to read one value (J01.5).
- **D-3. Unknown query parameters.** *Decided: refuse them* with `422 unknown_parameter` naming the
  parameter (journey variant J21.8). *Delivered in H4c (2026-10-03):* J21.8's test failed first, then
  every route was made to accept only the parameters it declares (`management/query_parameters.py`).
- **D-4. 32 undocumented error codes.** *Decided: document them* in API.md with route, status and
  meaning, in H4c beside the journey tests that meet them. *Done 2026-10-03:*
  [API.md, further error codes](../API.md#further-error-codes).
- **D-5. Lifecycle audit.** *Decided: keep capturing it and add reads*, and consider showing it in
  the UI. Journey variants J19.5 (a workspace's activity: change sets created, renamed, discarded,
  published, withdrawn) and J08.9 (a model draft's history), planned as their own package
  ([TODO](../TODO.md#now--product-09)).
- **D-6. Batch delete with cascade.** *Decided: a batch delete item must be able to cascade*, as a
  single delete can; refusing an item with dependants, or deleting only as one atomic batch, is not
  a realistic integration path. Journey variant J11.6 (planned). How a batch confirms the impact it
  deletes (the single delete's signed preview token) is designed with
  [PG-D18](../POSTGRESQL_RUNTIME_PLAN.md#decisions), which now carries this direction.
- **D-7. The schema upgrade command's help** named schemas 0.5–0.7. *Fixed 2026-10-02:* the help
  is built from the supported schema list (now 0.5–0.8).
