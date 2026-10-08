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
| `asOf` | per-type list, query body; on the lookup it is refused (D21); on the consumer API: get by ID, lists, XREF, batch resolve's URL | J23, J22.4, J23.6–J23.8 |
| `applicationKey`, `viewKey` | lookup, mapping and matrix reads | J01, J10, J16, J22.1 |
| `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction` | relations, edge list, mapping reads | J10, J13, J22.2, J22.3 |
| `Idempotency-Key` header | `POST /batches` | J11.5, J24 |

## Routes

Every operation, by method and path (under `/api/v1` except `/health`, `/docs` and `/openapi.json`).

| Operation | Journeys |
| --- | --- |
| `GET /health` | J12 |
| `GET /docs` (`api`, the source Scalar opens), `GET /openapi.json` | J20, J20.5 |
| `GET /capabilities` | J20, J12.7, J26.6 (`changeFeed.retentionDays`) |
| `GET /system` | J31, J31.1–J31.3 |
| `GET /model`, `GET /model/placements` | J20, J20.1, J03, J14 |
| `GET /model/consumer-apis/{consumerApi}` (the definition expanded, C18) | J20.6 |
| `GET /model-runtime-state` | J08 (fresh version for activation), J20.2 |
| `POST /model-validations` | J08.1, J25.6 |
| `GET /applications`, `GET /applications/{key}`, `GET /attribute-types`, `GET /attribute-types/{key}`, `GET /object-types`, `GET /object-types/{key}`, `GET /relation-types`, `GET /relation-types/{key}` | J20 |
| `GET /object-type-relations` (`fromObjectType`, `toObjectType`) | J20, J13 |
| `GET /model-releases` (`releaseKey`, `active`), `GET /model-releases/{id}` (`includeModel`) | J08, J08.7, J20.2 |
| `GET /model-releases/{id}/activations` | J08.8 |
| `GET /model-releases/{id}/diff` (`againstReleaseId`) | J08.2, J25 |
| `POST /model-releases/{id}/activation` | J08, J08.3, J08.5, J08.6, J08.10 |
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
| `POST /change-sets/{id}/publication` | J05, J05.1 (typed snapshot and filter parity), J06, J06.4, J18 |
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
| `POST /relations`, `PATCH/DELETE /relations/{id}` (`expectedRelationSetVersion`, `relationSetDirection`) | J13, J13.3, J13.5, J16 |
| `GET /relations` (`objectId`), `GET /relations/{id}` | J01, J22.3; `relationSets` (each anchored set's version) J13.5 |
| `GET /workspaces/{key}/mapping-coverage` (`state`) | J10 |
| `GET /workspaces/{key}/mapping-candidates`, `GET /workspaces/{key}/mapping-targets` (`sourceObjectId`, `mappingVersion`) | J10, J10.3 |
| `PUT /workspaces/{key}/mappings` | J10 |
| `GET /workspaces/{key}/relations` | J22.2, J10 (a relationship view's edges, with `applicationKey` and `viewKey`) |
| `GET /workspaces/{key}/relation-matrix` (`columnIds`, `columnCursor`, `columnPageSize`, `state`) | J16 |
| `GET /workspaces/{key}/relation-matrix/containers`, `GET /workspaces/{key}/relation-matrix/link-candidates` (`rowId`, `columnId`) | J16 |
| `POST /batches` (`run`: `inline`) | J11; relationship items J11.7, J11.8; `replaceRelationSet` J10.10, J11.8 |
| `POST /batches` (`run`: `background`), `GET /jobs` (`kind`, `state`), `GET /jobs/{id}`, `GET /jobs/{id}/items` (`status`), `POST /jobs/{id}/cancel` | J24 |
| `GET /workspaces/{key}/feed` (`after`, `pageSize`, `kind` and `objectTypeKey` repeatable) | J26, J26.1–J26.6 |
| `POST /exports` (`context`, `scope`: `types` with `where`, `parentObjectId`, `asOf`; `include.relations`; `format`: `jsonl`, `csv`, `xlsx`), `GET /jobs/{id}/output`, the job's `output` (0.9 J1) | J27, J27.1–J27.5 |
| `POST /import-profiles`, `GET /import-profiles`, `GET /import-profiles/{key}`, `PUT /import-profiles/{key}` (the whole profile with `expectedVersion`), `DELETE /import-profiles/{key}` (`expectedVersion`); a profile's `valid` and `problems` under the active release (0.9 J2) | J27.7 |
| `POST /imports` (`multipart/form-data`: `file`, and `request` as JSON: `workspaceKey` or `changeSetId` with `expectedChangeSetVersion`, `profileKey` or an inline `profile` or neither, `format`, `policy`, `onExisting`, `stage`; `Idempotency-Key`); an import job's `parameters.profile` and `parameters.file`, its items' `ref` (`{sheet}!{row}`) (0.9 J2) | J27.8, J27.9, J27.10 |
| `POST /imports` with `stage: preview`; the job's `preview` (`coverage`, `items`, `rows`, `counts`, `result`, `previewedAt`), `bindingReport` and `confirmedAt`; `POST /jobs/{id}/confirm`; `POST /jobs/{id}/cancel` of a waiting preview; `GET /jobs/{id}/rows` (`status`, paging); `GET /jobs/{id}/items` (`ref`); a row refusal's `details.cells` (0.9 J3) | J27.10, J27.11, J27.12 |
| The job's `notices` (`RECORD_IDS_OF_ANOTHER_WORKSPACE`); `OBJECT_ALREADY_EXISTS` and `REFERENCE_NOT_FOUND` naming the workspace that holds the ID (`details.workspaceKey`) (0.9 J4a) | J27.10, J27.11 |
| `stage` (`execute`, `preview`) on `POST /batches`, refused with `run: inline`; a batch's `preview` (`coverage`, `items`, `counts`, `result`, `previewedAt`, no `rows`); `POST /jobs/{id}/confirm` and `POST /jobs/{id}/cancel` of a waiting batch preview (0.9 K2) | J11.9 |
| The `delete` item's `cascade` and `deletionPreviewToken`; an outcome's `impact` (`objectCount`, `objectsByType`, `relationshipCount`, `retainedAssociationCount`, `deletionPreviewToken`) and `deletedWithItem`; a preview's `deletion` totals; `OBJECT_HAS_DEPENDANTS` with `details.impact`, `DELETION_PREVIEW_REQUIRED` and `DELETION_PREVIEW_CHANGED` per item; the single delete's token accepted by a batch item (0.9 K2b) | J11.6 |
| `otherWorkspaceIds` (`refuse`, `counterparts`) on `POST /imports` and `POST /batches`; the counterpart derivation; an outcome's `sourceId`; the `RECORD_IDS_AS_COUNTERPARTS` notice; `REFERENCE_NOT_FOUND` for a counterpart not loaded yet (0.9 J5) | J27.14, J11 |
| `GET /jobs/{id}/events` (server-sent events: the job at once and after each committed change, ending after a final state; 0.9 J1u) | J24.7, J27.6 |
| `POST /consumer-subscriptions`, `GET /consumer-subscriptions` (`consumerApi`, `workspaceKey`, `status`), `GET`, `PATCH` and `DELETE /consumer-subscriptions/{id}`, `POST /consumer-subscriptions/{id}/suspend`, `POST /consumer-subscriptions/{id}/resume` (`reset`); served with `CONSUMER_SUBSCRIPTIONS_ENABLED`; the subscription's `delivery`; `name` (U5a); `maxEventsPerBatch`, `payload`, `format` (C17; `mode` and `debounceSeconds` retired) | J30.6, J30.7, J30.8, J30.9 |
| `GET /consumer-subscriptions/{id}/deliveries` (`status`, paging), `GET /consumer-subscriptions/{id}/deliveries/{deliveryId}`, `POST …/deliveries/{deliveryId}/resend` (`eventId`); `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` and `consumerSubscriptions.logRetentionDays` (U5a) | J30.10 |

### Consumer API

Under `/api/consumer`, outside the management OpenAPI document: each definition serves its own
(`openapi.json`), and the API index lists them.
Every response names the workspace it read in the `RDM-Workspace` header, and a read pinned with
`publication` the publication in `RDM-Publication`. Every `GET` answers an `ETag` and `304` to a
matching `If-None-Match` (J28.14). The parity tests (`test_j28_j29_parity`, 0.9 C8) walk get by ID,
lists, XREF, batch resolve, the index and the document again on a model shaped like the reference
deployment's, each answer checked against the API's own document.

| Operation | Journeys |
| --- | --- |
| `GET /{consumerApi}/v{contractVersion}/objects/{id}` (`workspace`, `publication`, `asOf`, the definition's parameters, `to.{parameter}`) | J28, J28.1–J28.5, J28.9, J28.11–J28.14, J29.12, J29.14, J29.15, J23.6, J23.8, J25.5, J25.7 |
| `GET /{consumerApi}/v{contractVersion}/lists/{listKey}` (`workspace`, `publication`, `asOf`, the list's parent parameter, the definition's parameters, `to.{parameter}`, `pageSize`, `cursor`, `position`, `from`, `seek`, `includeTotal`) | J28.6–J28.13, J29.12, J29.14, J23.6, J23.8 |
| `GET /{consumerApi}/v{contractVersion}/xref` (`query`, `expect`, `workspace`, `publication`, `asOf`, the definition's parameters, `to.{parameter}`, `pageSize`, `cursor`, `position`, `from`) | J29, J29.1–J29.7, J29.11, J29.12, J29.14, J29.15, J23.7, J23.8, J25.5, J25.7 |
| `POST /{consumerApi}/v{contractVersion}/resolve` (`workspace`, `publication`, `asOf`; the body's `defaults` and `items`, each with `ref`, `query` or `id`, the definition's parameters and `to.{parameter}`) | J28.13, J28.14, J29.8–J29.10, J29.13, J29.14, J29.15, J23.7, J23.8, J25.5, J25.7 |
| `GET /{consumerApi}/v{contractVersion}/publications` (`workspace`, `pageSize`, `cursor`, `position`, `from`, `includeTotal`) | J28.14, J30.3, J30.5 |
| `GET /{consumerApi}/v{contractVersion}/events` (`workspace`, `event`, `after`, `cursor`, `pageSize`, `payload`, the definition's parameters) | J30, J30.1–J30.5 |
| `GET /` (the API index: `pageSize`, `cursor`, `position`, `from`, `includeTotal`) | J20.3 |
| `GET /{consumerApi}/v{contractVersion}/openapi.json` | J20.3, J20.4 |

## Error codes

Every code the API returns, by the journey that meets it. 32 of them were raised by the backend but
documented nowhere; API.md documents them since H4c (D-4).

| Journeys | Codes |
| --- | --- |
| Every route | `REQUEST_VALIDATION_ERROR`, `UNKNOWN_PARAMETER` (J21.8), `INTERNAL_ERROR` (with a correlation ID), `INVALID_CURSOR`, `INVALID_POSITION`, `CONFLICTING_PAGE_PARAMETERS`, `INVALID_SEEK`, `MUTUALLY_EXCLUSIVE_CONTEXT`, `WORKSPACE_NOT_FOUND`, `CHANGE_SET_NOT_FOUND`, `PUBLICATION_NOT_FOUND`, `WORKSPACE_CONTEXT_MISMATCH`, `MODEL_REGISTRY_UNAVAILABLE`, `MODEL_RUNTIME_STATE_UNAVAILABLE`, `WORKSPACE_RUNTIME_STATE_MISSING` |
| J01, J21, J22 | `OBJECT_NOT_FOUND`, `UNKNOWN_OBJECT_TYPE`, `INVALID_FILTER`, `INVALID_SORT`, `INVALID_QUERY`, `MUTUALLY_EXCLUSIVE_SCOPE`, `WORKSPACE_KEY_REQUIRED`, `ATTRIBUTE_NOT_FOUND` |
| J02, J03, J13, J14 (the write rules) | `VERSION_CONFLICT`, `VERSION_REQUIRED`, `INVALID_ATTRIBUTE_VALUE`, `ATTRIBUTE_BELOW_MINIMUM`, `ATTRIBUTE_ABOVE_MAXIMUM`, `UNKNOWN_ATTRIBUTES`, `UNKNOWN_ATTRIBUTE_TYPE`, `DUPLICATE_ATTRIBUTE`, `DUPLICATE_ATTRIBUTE_VALUE`, `MISSING_REQUIRED_ATTRIBUTES`, `OBJECT_ATTRIBUTE_RULE_VIOLATION`, `CANNOT_DELETE_REQUIRED_ATTRIBUTE`, `READ_ONLY_ATTRIBUTES`, `ATTRIBUTE_ALREADY_EXISTS`, `OBJECT_ALREADY_EXISTS`, `UNKNOWN_APPLICATION`, `INVALID_OBJECT_TYPE_FOR_APPLICATION`, `OBJECT_TYPE_NOT_IN_APPLICATION`, `PARENT_REQUIRED`, `INVALID_PARENT_TYPE`, `PARENT_WRONG_SCOPE`, `PARENT_CYCLE`, `MISSING_REQUIRED_RELATIONS`, `DUPLICATE_INITIAL_RELATION`, `DUPLICATE_RELATION`, `DUPLICATE_RELATION_SCOPE`, `UNKNOWN_RELATION_TYPE`, `INVALID_RELATION_PAIR`, `RELATION_ENDPOINT_MISSING`, `RELATION_WRONG_SCOPE`, `UNKNOWN_RELATION_ATTRIBUTES`, `IMMUTABLE_RELATION`, `REQUIRED_RELATION`, `CARDINALITY_VIOLATION`, `RELATION_NOT_FOUND`, `RELATION_SET_VERSION_CONFLICT`, `RELATION_SET_CLAIM_INCOMPLETE`, `WORKSPACE_RETIRED` |
| J04 | `DELETION_PREVIEW_REQUIRED`, `DELETION_PREVIEW_CHANGED`, `OBJECT_HAS_DEPENDANTS` |
| J05, J06, J07, J17 | `CHANGE_SET_REQUIRED`, `CHANGE_SET_VERSION_CONFLICT`, `CHANGE_SET_SNAPSHOT_RETRY`, `CHANGE_SET_SOURCE_INVALID`, `CHANGE_SET_BASE_INVALID`, `WORKSPACE_GRAPH_INVALID`, `ACTIVATION_CONFLICT`, `WORKSPACE_ACTIVE_PUBLICATION_CONFLICT` |
| J10 | `MAPPING_VERSION_CONFLICT`, `INVALID_CLEAR_ATTRIBUTES`, `REQUIRED_OWNERSHIP_BINDING`, `RELATION_ANCESTOR_REQUIRED`, `MAPPING_VIEW_REQUIRED`, `MAPPING_VIEW_NOT_FOUND`, `MAPPING_VIEW_BINDING_MISMATCH`, `MAPPING_BINDING_NOT_FOUND`, `MAPPING_SOURCE_NOT_FOUND`, `MAPPING_CANDIDATE_TYPE_MISMATCH`, `MAPPING_ENDPOINT_NOT_FOUND`, `MAPPING_ENDPOINT_TYPE_MISMATCH`, `MAPPING_PARENT_NOT_FOUND`, `MAPPING_PARENT_SCOPE_MISMATCH`, `INCOMPLETE_VIEW_IDENTITY` |
| J15 | `RESTRUCTURING_NOT_READY`, `RESTRUCTURING_TOO_LARGE`, `RESTRUCTURING_PLAN_CHANGED`, `INVALID_TYPE_MAPPING`, `OBJECT_TYPE_UNCHANGED`, `OBJECT_TYPE_CHANGED`, `TYPE_CHANGES_NEED_CHANGE_SET`, `CHILD_TYPE_NOT_ALLOWED`, `REQUIRED_RELATION_WITHOUT_PLACE`, `RELATION_ALREADY_EXISTS` |
| J16 | `RELATION_MATRIX_VIEW_NOT_FOUND`, `RELATION_MATRIX_ROW_NOT_FOUND`, `RELATION_MATRIX_COLUMN_NOT_FOUND`, `RELATION_MATRIX_PARENT_NOT_FOUND`, `RELATION_MATRIX_ACTION_NOT_ALLOWED`, `RELATION_MATRIX_PARENT_SCOPE_MISMATCH`, `RELATION_MATRIX_STATE_REQUIRES_COLUMNS`, `TOO_MANY_COLUMNS`, `DUPLICATE_COLUMN_IDS`, `CONFLICTING_COLUMN_PARAMETERS` |
| J18 | `CHANGE_SET_CONTENT_INCOMPATIBLE`, `CHANGE_SET_MODEL_RELEASE_CONFLICT`, `PINNED_MODEL_UNAVAILABLE`, `PINNED_MODEL_INVALID`, `UNSUPPORTED_PINNED_MODEL_SCHEMA`, `INVALID_INSTALLED_MODEL` |
| J08, J25 | `INVALID_MODEL`, `RELEASE_IDENTITY_CONFLICT`, `MODEL_MIGRATION_REQUIRED`, `MODEL_RELEASE_NOT_FOUND`, `MODEL_DRAFT_NOT_FOUND`, `UNSUPPORTED_SCHEMA_VERSION` (also a schema 0.8 document declaring `consumerApis`, J25.6), `MODEL_REGISTRY_REFRESH_FAILED`, `CONSUMER_CONTRACT_VERSION_REQUIRED`; diff findings `CONSUMER_API_REMOVED`, `CONSUMER_CONTRACT_VERSION_DECREASED` |
| J25.7 | `OPERATION_NOT_OFFERED` (`404`, on `objects`, `xref` and `resolve` of a definition that does not list the operation) |
| J20.6 | `CONSUMER_API_NOT_FOUND` (`404`, the expanded read of a definition the context's model does not declare) |
| J08, J11, J24 | `MODEL_RELEASE_CHANGED` |
| J19 | `WORKSPACE_ALREADY_EXISTS`, `DEFAULT_WORKSPACE_CANNOT_BE_RETIRED`, `WORKSPACE_IS_DEFAULT`, `WORKSPACE_HAS_PUBLICATIONS`, `WORKSPACE_NOT_EMPTY` |
| J23 | `AS_OF_NOT_SUPPORTED`, `INVALID_EFFECTIVE_PERIOD`; on the consumer API both answer `400`: `AS_OF_NOT_SUPPORTED` (J23.6, J23.7) and `INVALID_AS_OF` (J23.8) |
| J26 | `FEED_POSITION_AHEAD`, `FEED_POSITION_EXPIRED` (naming the export route, J27.2) |
| J27 | Exports: `INVALID_QUERY` (at a body pointer), `AS_OF_NOT_SUPPORTED`, `PARENT_NOT_FOUND`, `WORKSPACE_NOT_FOUND`, `CHANGE_SET_NOT_FOUND`, `PUBLICATION_NOT_FOUND`, `REQUEST_VALIDATION_ERROR` (J27.5); the output: `JOB_NOT_FOUND`, `JOB_HAS_NO_OUTPUT`, `JOB_NOT_COMPLETED`, `JOB_EXPIRED` (J27.4), `JOB_OUTPUT_MISSING` (`410`, a file removed from `JOB_FILE_DIR` by hand; no journey reaches it, the route's own check); a failed export's `MODEL_RELEASE_CHANGED` and `JOB_FAILED` (J27.4) |
| J27.7–J27.10 | Profiles: `INVALID_IMPORT_PROFILE` (every problem at its pointer), `IMPORT_PROFILE_EXISTS`, `IMPORT_PROFILE_NOT_FOUND`, `IMPORT_PROFILE_VERSION_CONFLICT` (J27.7). Imports, before a job is stored: `IMPORT_TOO_LARGE` (`413`), `UNSUPPORTED_FILE_FORMAT`, `INVALID_IMPORT_PROFILE`, the context's codes (J27.10). A job that fails before an item runs: `IMPORT_FILE_MISMATCH`, `IMPORT_FILE_UNREADABLE` (J27.10); `IMPORT_TOO_MANY_ITEMS` (rows making more items than `BACKGROUND_JOB_MAX_ITEMS` or, atomic, `ATOMIC_JOB_MAX_ITEMS`; no journey reaches it, the binding's own check) and `IMPORT_FILE_MISSING` (a file removed from `JOB_FILE_DIR` by hand; no journey reaches it). A row's own: `INVALID_ATTRIBUTE_VALUE` (with `column`), `REFERENCE_NOT_FOUND`, `REFERENCE_AMBIGUOUS` (with `count`), `DUPLICATE_KEY_IN_FILE` (with `rows`), `REFERENCE_CYCLE`, `MISSING_RECORD_KEY`, `NAME_REQUIRED`, `INVALID_NAME`, `INVALID_CELL` (an export's table cell that is not an ID, a version or a known key), `REQUEST_VALIDATION_ERROR` (a JSON Lines line that is not a batch item) (J27.8–J27.10) |
| J27.11, J27.12 | Confirm: `JOB_NOT_AWAITING_CONFIRMATION` (`409`, with `state`: an executed import, a batch, a cancelled preview), `JOB_EXPIRED` (`410`), `CHANGE_SET_VERSION_CONFLICT` (`409`, the job still waiting); `MODEL_RELEASE_CHANGED`, `WORKSPACE_NOT_FOUND` and `CHANGE_SET_NOT_FOUND` as at submission (the same check as a chunk's context; no journey of its own). Rows: `JOB_HAS_NO_ROWS` (`404`, a batch or an export) |
| J30 | `EVENTS_NOT_DECLARED` (`404`), `UNKNOWN_EVENT`, `INVALID_PAYLOAD` (`400`), `EVENT_POSITION_AHEAD` (`409`), `EVENTS_EXPIRED` (`410`) (J30.4, J30.5); `PARAMETER_NOT_SUPPORTED` for `publication`, `asOf` and `to.` names, and the paging codes, as on the other consumer reads |
| J30.6, J30.7 | Subscriptions: `CONSUMER_API_NOT_FOUND`, `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`, `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, `UNKNOWN_OBJECT_TYPE`, `FILTER_MATCHES_NOTHING`, `INVALID_WEBHOOK_URL` (`400`, at a body pointer); `WORKSPACE_NOT_FOUND`, `SUBSCRIPTION_NOT_FOUND` (`404`); `VERSION_CONFLICT`, `SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED`, `SUBSCRIPTION_NEEDS_EDIT`, `EVENT_POSITION_AHEAD`, `EVENTS_EXPIRED` (resume), `WORKSPACE_HAS_SUBSCRIPTIONS` (`409`); `EVENTS_EXPIRED` (`410`, `startAfter`) |
| J30.10 | Deliveries: `SUBSCRIPTION_NOT_FOUND`, `DELIVERY_NOT_FOUND`, `EVENT_NOT_IN_DELIVERY` (`404`); `DELIVERY_NOT_SENT` (`409`, resend; held by a unit test, since no journey reaches a request never sent reliably); `REQUEST_VALIDATION_ERROR` (`422`: a create without `name`, J30.6; a resend without `eventId`; `maxEventsPerBatch` outside 1–1,000, an unknown `format`, the retired `mode` or `debounceSeconds`, J30.6 and J30.8) |
| J30.8, J30.9 | Webhook delivery (no route of its own; the receiver's requests and the subscription's state): suspension reasons `DELIVERY_FAILED`, `FILTER_MATCHES_NOTHING`, `EVENTS_EXPIRED`; a failed attempt's `kind` `status`, `redirect`, `timeout`, `connection`, `tls`, `address`; resume `409 EVENTS_EXPIRED` naming `reset` |
| J28 | `CONSUMER_API_NOT_FOUND`, `CONTRACT_VERSION_NOT_FOUND`, `PARAMETER_NOT_SUPPORTED`, `LIST_NOT_FOUND`, `PARENT_NOT_FOUND`, `INVALID_PAGE_SIZE`, `INVALID_PAGE_PARAMETER`; on the consumer API `UNKNOWN_PARAMETER`, `UNKNOWN_OBJECT_TYPE` and the paging codes are `400` (J28.4, J28.8, J28.10), and an unknown or retired workspace `404 WORKSPACE_NOT_FOUND` (J28.3); a pinned read: `PUBLICATION_NOT_FOUND` (`404`: an unknown publication, another workspace's, `latest` with none current) and `PUBLICATION_CONTRACT_MISMATCH` (`409`) (J28.12, J28.13) |
| J29 | `QUERY_REQUIRED`, `TOO_MANY_TERMS`, `QUERY_TOO_BROAD` (`test_consumer_xref_volume`), `INVALID_EXPECT`, `NO_MATCH`, `AMBIGUOUS_MATCH` (J29.3, J29.5, J29.6), `UNKNOWN_OBJECT_TYPE` (J29.6); batch resolve: each item's outcome carries the single read's code, plus `QUERY_OR_ID_REQUIRED`; the request is refused as `400 REQUEST_VALIDATION_ERROR` (a body of the wrong shape), `400 UNKNOWN_PARAMETER` or `PARAMETER_NOT_SUPPORTED` (`defaults`, the URL) and `413 BATCH_TOO_LARGE` (J29.10); crosswalk: `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET` (J29.11–J29.13), `MULTIPLE_TARGETS` and `UNKNOWN_PARAMETER` for a `to.` name (J29.14) |
| J11, J24 | `BATCH_TOO_LARGE`, `INVALID_BATCH_CONTEXT`, `IDEMPOTENCY_KEY_REUSED`, `IDEMPOTENCY_IN_PROGRESS`, `MISSING_RECORD_KEY`, `INVALID_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `REFERENCE_TYPE_MISMATCH`, `JOB_NOT_FOUND`, `JOB_FINISHED`, `JOB_FAILED` |

## Operator surface (J12)

| Setting or command | Journeys |
| --- | --- |
| `DATABASE_URL` | J12, J12.1, J31.2 (reported without its password) |
| Every setting (reported by `GET /system` with value, default and source; secrets as set or not) | J31, J31.1, J31.2 |
| `RDM_MODEL_PATH` | J12 (the starter or bootstrap model), J08 |
| `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, `INTEGRATION_JOBS_ENABLED` | J12.7, J08, J19.4, J11 |
| `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`, `ATOMIC_JOB_MAX_ITEMS`, `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`, `JOB_CHUNK_ITEMS`, `JOB_LEASE_SECONDS`, `JOB_RETENTION_DAYS` | J12.7, J11, J24 |
| `FEED_RETENTION_DAYS` | J26.6 |
| `JOB_FILE_DIR` (export files and import uploads; a directory that cannot be written refuses the start with jobs on) | J27, J12.1 |
| `IMPORT_MAX_BYTES` (an import's largest file, reported as `integrationJobs.limits.importMaxBytes`) | J27.10 |
| `JOB_PREVIEW_MAX_ITEMS` (the items a preview of an import or a batch runs before it is a sample, reported as `integrationJobs.limits.previewMaxItems`) | J27.12, J11.9 |
| `CONSUMER_RESOLVE_MAX_ITEMS` (reported by `GET /capabilities` as `consumerApi.resolveMaxItems`) | J29.10 |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` (the subscriptions API and their delivery, reported by `GET /capabilities` as `consumerSubscriptions` with the delivery limits, `maxEventsPerBatch` among them), `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (required with the capability on) | J30.6–J30.9 |
| `python -m app.cli.generate_key` | J30.6 (the encryption key) |
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
- **D-3. Unknown query parameters.** *Decided: refuse them* with `422 UNKNOWN_PARAMETER` naming the
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
  a realistic integration path. Journey variant J11.6 (delivered in 0.9 K2b). How a batch confirms the impact it
  deletes (the single delete's signed preview token) is designed with
  [PG-D18](../POSTGRESQL_RUNTIME_PLAN.md#decisions), which now carries this direction.
- **D-7. The schema upgrade command's help** named schemas 0.5–0.7. *Fixed 2026-10-02:* the help
  is built from the supported schema list (now 0.5–0.8).
