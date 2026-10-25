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
| `filter.related:<key>.eq`, `filter.related:<key>.isNull` (relationship filters; 0.9 K6) | per-type list | J01.10, J32.6 |
| `parentObjectId`, `topLevel` | per-type list, lookup, coverage, matrix | J01, J14 |
| `expand`, `expandLimit` (relation columns: a relation key or reverse key, optionally `.<field>` (0.9 K5a), each once, as many as the type has (D142 revised in K6a); 1–20 records each, 3 by default; 0.9 K5) | per-type list | J01.8, J01.9 |
| `candidateFor`, `anchorTypeKey` (the records a record of the anchor's type may choose through a relation key or reverse key, by the binding's `candidates`; 0.9 K7, D173) | per-type list | J13.9, J13.10 |
| `asOf` | per-type list, query body; on the lookup it is refused (D21); on the consumer API: get by ID, lists, XREF, batch resolve's URL | J23, J22.4, J23.6–J23.8 |
| `applicationKey`, `viewKey` | lookup, mapping and matrix reads | J01, J10, J16, J22.1 |
| `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction` | relations, edge list, mapping reads | J10, J13, J22.2, J22.3 |
| `Idempotency-Key` header | `POST /batches` | J11.5, J24 |
| `Authorization` header (`Bearer <access token>`, 0.12 I1): `401 AUTHENTICATION_REQUIRED` without one, `401 TOKEN_INVALID` with its reason | every route but `/health`, `/health/live`, `/openapi.json`, `/docs` and the OAuth endpoints; on `POST /oauth/token`, `Basic` client credentials | J39, J41, J41.4, J41.5, J43.2 |
| `X-Expected-Model-Release-Id` header (0.11 M6a) | every route of the management API: a record, relation or value write live or in a change set, a batch, an import; a read naming its context's release | J36.9 |

## Routes

Every operation, by method and path (under `/api/v1` except `/health`, `/health/live`, `/metrics`, `/docs` and
`/openapi.json`).

| Operation | Journeys |
| --- | --- |
| `GET /health` | J12, J12.12 |
| `GET /health/live` (0.11 O1) | J12.12 |
| `GET /metrics` (the Prometheus text format, 0.11 O1) | J12.14 |
| `GET /docs` (`api`, the source Scalar opens; `workspace`, whose consumer APIs it lists, 0.11 M3), `GET /openapi.json` | J20, J20.5 |
| `GET /capabilities` | J20, J12.7, J26.6 (`changeFeed.retentionDays`) |
| `GET /system` (the engine, schema languages, active release), `GET /system/configuration` (the database revision and every setting, 0.12 I1, D246) | J31, J31.1–J31.3 |
| Delivered in 0.12 I1 ([API.md § Security](../API.md#security-product-012-designed)): `GET /.well-known/oauth-authorization-server`, `GET /oauth/jwks`, `POST /oauth/token` (`grant_type=client_credentials`, `scope` `management` or `consumer`, `client_secret_basic` or `client_secret_post`; RFC errors `invalid_request`, `invalid_client`, `invalid_scope`, `unsupported_grant_type`); `GET /me`; `GET /users` (`q`, `active`), `POST /users`, `GET/PATCH /users/{id}`; `GET /clients` (`active`), `POST /clients`, `GET/PATCH /clients/{id}`, `POST /clients/{id}/secrets` (`overlapHours`), `DELETE /clients/{id}/secrets/{secretId}`; `GET /token-signing-keys`, `POST /token-signing-keys/rotation` (`immediate`) | J39, J40, J41, J41.3, J41.4, J41.5, J43.1, J43.2 |
| Delivered in 0.12 I2: `GET/POST /oauth/authorize` (the sign-in page, PKCE `S256`, `client_id=browser`, D267), `POST /oauth/token` (`authorization_code`, `refresh_token`; the `oauth_refresh` cookie), `POST /oauth/revoke`, `GET/POST /oauth/password` (the reset link's page); `GET /me/sessions`, `DELETE /me/sessions`, `DELETE /me/sessions/{id}`, `POST /me/password`; `POST /users/{id}/password-reset`, `DELETE /users/{id}/sessions` | J39, J39.1–J39.6, J40 |
| Delivered in 0.12 Z1 (ADR-044): every operation declares its action (`x-action`, `x-action-groups`, `x-action-scope` in the document) and answers `403 FORBIDDEN` when no grant allows it; `GET /me/permissions` (`workspaceKey`), `GET /me/grants`; `GET /action-groups`; `GET/POST /roles`, `GET/PATCH/DELETE /roles/{key}` (`copiedFrom`); `GET/POST /groups`, `GET/PATCH/DELETE /groups/{id}`, `GET/POST /groups/{id}/members`, `DELETE /groups/{id}/members/{userId}`; `GET /grants` (`principalId`, `workspaceKey`, `roleKey`), `POST /grants`, `DELETE /grants/{id}`; `GET /workspaces/{key}/access`; the workspace list, the workspace models, the jobs and the subscriptions filtered (D285, D288) | J40, J40.1, J40.2, J40.4–J40.9, J41 |
| Delivered in 0.12 SP1: `GET /users` and `GET /users/{id}` answer the person's `roles` and where (D298); `GET /users/{id}/grants`, direct and through groups (D299); `GET /groups` (`q`, `memberId`), `GET /clients` (`q`) (D300); `POST /grants` refuses a workspace grant of a role held only at the instance (`GRANT_SCOPE_INVALID`, D302); the Security pages (People, Groups, Roles) and a workspace's Access in Settings | J40, J40.4 |
| Delivered in 0.12 Z4: `GET /security-events` (`principalId`, `aggregateType`, paging; D317, D318); `actor` on a record's history, a feed entry and a release's activation, `createdBy` on a change set, `publishedBy` and `withdrawnBy` on a publication, `requestedBy` on a job and `author` on a draft's and a mapping's operations (D313, D315) | J44.1–J44.6, J40.11 |
| Delivered in 0.12 Z5: `GET /workspaces` (`holding`, the workspaces where the caller holds an action group, D327), `GET /me/action-groups` (every group held, at the instance or in which workspaces, D328), `GET /workspaces/{key}/change-sets` (`createdBy`, D325) | J40.12 |
| Delivered in 0.12 HM1: `GET /me/workspaces` (the workspaces where the caller holds Browse, with their applications, `ownChangeSets` and `openChangeSets`; D332), `GET /me/change-sets` (the caller's open change sets across workspaces with `workspaceLabel` and `changeCount`; D333) | J45.1–J45.4 |
| Delivered in 0.12 Z6: `GET /changes` (`actorId`, `workspaceKey`, `kind`, `since`, `until`, paging; data and model changes across workspaces, each with its workspace, change set, subject, cause and actor, filtered to what the caller may see; D340–D344) | J44.7–J44.11 |
| `GET /system/processes`, `GET /system/readiness` (paging; 0.11 O1) | J12.13 |
| `GET /system/summary` (0.11 O2) | J12.13, J12.14 |
| `GET /system/backup-rehearsals` (paging; 0.11 O2) and `python -m app.cli.restore_check` | J12.16, J12.17 |
| `GET /model`, `GET /model/placements` | J20, J20.1, J03, J14 |
| `GET /model/consumer-apis/{consumerApi}` (the definition expanded, C18) | J20.6 |
| `GET /workspaces/{key}/model` (0.11 M1; `releaseName`, M5) | J08 (fresh version for activation), J20.2, J36.1 |
| `GET /workspace-models` (`releaseKey`, `releaseId`, paging; 0.11 M1) | J36.2 |
| `POST /model-validations` | J08.1, J25.6, J11.12 |
| `GET /applications`, `GET /applications/{key}`, `GET /attribute-types`, `GET /attribute-types/{key}`, `GET /object-types`, `GET /object-types/{key}`, `GET /relation-types`, `GET /relation-types/{key}` | J20 |
| `GET /object-type-relations` (`fromObjectType`, `toObjectType`) | J20, J13 |
| `GET /model-releases` (`releaseKey`, `assigned`; each release's `assigned` and `workspaces`), `GET /model-releases/{id}` (`includeModel`) | J08, J08.7, J20.2, J36.1 |
| `GET /model-releases/{id}/activations` | J08.8 |
| `GET /model-releases/{id}/diff` (`againstReleaseId`; `compatibility.workspaces`, 0.11 M3; `workspaceKey`, 0.11 M5) | J08.2, J25, J08.11, J36.2 |
| `POST /workspaces/{key}/model/activation` (`releaseId`, `expectedVersion`, `expectedReleaseId`; `changeSetsLeftBehind`; 0.11 M1) | J08, J08.3, J08.5, J08.6, J08.10, J08.11, J36.2, J36.5 |
| `GET/POST /model-drafts`, `GET/PATCH/DELETE /model-drafts/{id}` | J08 |
| `POST /model-drafts/{id}/compile` (`compatibility.workspaces`, compared with the draft's own model, 0.11 M3), `POST /model-drafts/{id}/installation` | J08, J25, J36.2, J36.4 |
| `POST /model-drafts/{id}/operations` (`expectedVersion`, `operations`, the model-side kinds; `proposalId` planned for A6; `setContainment`'s `application` and `fromApplication`, 2026-10-19), `GET /model-drafts/{id}/operations` (paging) (0.10 A2, [API.md § Draft operations](../API.md#draft-operations)) | J33, J33.1–J33.8, J33.12, J33.15, J08.9 |
| `POST /model-drafts/{id}/undo` (`step`, `steps`), `POST /model-drafts/{id}/redo` (0.10 A2) | J33.4, J33.5, J33.12 |
| `GET /model-drafts/{id}/outline`: the draft's structure as the editor shows it, each element marked against the base release, diagnostics tied to elements (0.10 A4a, D36, [API.md § The draft's outline](../API.md#the-drafts-outline)) | J33, J33.1, J33.2 |
| `GET /model-drafts/{id}/model`: the draft compiled as `GET /model` serves the active model, with its placements, or `valid: false` and its diagnostics; reads and writes nothing (0.10 A4b, D43, [API.md § The draft's model](../API.md#the-drafts-model)) | J33, J33.10, J33.3 |
| `GET /model-drafts/{id}/consumer-apis/{consumerApi}`: a consumer API definition of the draft as written and, when the draft compiles, with every default and its contract against the active release; reads and writes nothing; `404 MODEL_DRAFT_NOT_FOUND`, `404 CONSUMER_API_NOT_FOUND` (0.10 A4c, D56, [API.md § A draft's consumer APIs](../API.md#a-drafts-consumer-apis)) | J33.13, J33.14 |
| `GET /model-drafts/{id}/consumer-apis/{consumerApi}/schema.json`: the JSON Schema of the object message the definition serves, from the draft; `422 INVALID_MODEL` while the draft does not compile (0.10 A4c, D56, [API.md § A draft's consumer APIs](../API.md#a-drafts-consumer-apis)) | J33.13 |
| `GET /model-drafts/{id}/consumer-apis/{consumerApi}/example.json`: one object message valid against that schema, written from it, no record read; `422 INVALID_MODEL` while the draft does not compile (0.10 A4c, D56, [API.md § A draft's consumer APIs](../API.md#a-drafts-consumer-apis)) | J33.13 |
| `GET /model-drafts/{id}/consumer-apis/{consumerApi}/openapi.json`: the definition's OpenAPI document as the consumer tier will serve it from the draft; `422 INVALID_MODEL` while the draft does not compile (0.10 A4c, D56, [API.md § A draft's consumer APIs](../API.md#a-drafts-consumer-apis)) | J33.13 |
| `POST /model-drafts/{id}/installation` making the new release the draft's base (0.10 A2, D17); `PATCH /model-drafts/{id}` with a `model` recorded as one `replaceModel` step | J33.2, J33.12 |
| `POST /source-files` (multipart: `file`, `request` with `owner` `{draftId}` or `{profileKey}`, `format`, `csv`, `workspaceKey`), `GET /source-files` (`draftId`, `profileKey`, paging), `GET /source-files/{id}`, `DELETE /source-files/{id}` (`expectedVersion`), `GET /source-files/{id}/profile/sheets`, `GET /source-files/{id}/profile/sheets/{sheet}/columns` (paging); job kind `profile` (0.10 A3, D5, D66, D68–D70, [API.md § Source files and their profiles](../API.md#source-files-and-their-profiles)) | J34.1, J35 |
| `sourceFileId` on `POST /imports` in place of the `file` part (0.10 A3, D5) | J27.8, J35 |
| `POST /model-drafts/{id}/dry-run` (`sourceFileId`, `workspaceKey`, `profile`, `onExisting`), `GET /model-drafts/{id}/dry-run`, `GET /model-drafts/{id}/dry-run/rows` (`source`, `status`, `code`, paging); job kind `dryRun`; `GET /jobs/{id}/rows` serves a dry run's rows too (0.10 A3, D65–D67, D71, [API.md § The dry-run summary](../API.md#the-dry-run-summary)) | J34.3 |
| `GET /model-drafts/{id}/profile`: the draft's import profile as it holds it, the import profile it stands for (`definition`), `valid` and its warnings against the draft's model, the source file it binds; the source and mapping kinds on `POST /model-drafts/{id}/operations` (`setProfile`, `addSource`, `setSource`, `removeSource`, `ignoreSheet`, `mapColumn`, `setColumnReading`, `splitColumn`, `ignoreColumn`, `addValuesToList`, `setValueMap`); a step's `dryRun` (D79); `importProfile` on `POST /model-drafts/{id}/installation` (D80) (0.10 A5a, D75–D80, [API.md § A draft's import profile](../API.md#a-drafts-import-profile)) | J34.2, J34.3, J34.7, J34.8 |
| `missing: "create"` on a profile's `relation` and `parent` bindings: a cell naming no record creates one by its name (0.10 A5a, D77) | J27.8, J34.2 |
| `POST /model-drafts/{id}/inference` (`mode`, `applicationKey`, `applicationName`), `GET /model-drafts/{id}/inference` (its counts, `disagreements`, `warnings`, `proposed`), `GET /model-drafts/{id}/inference/proposals` (`sheet`, `column`, paging), `POST /model-drafts/{id}/inference/application` (`expectedVersion`, `proposals`); job kind `inference`; `INFERENCE_DISAGREES` among `GET /model-drafts/{id}/profile`'s warnings (0.10 A6, D86–D98, [API.md § Inferences](../API.md#inferences)) | J34.4, J34.5, J34.6 |
| `GET /source-files/{id}/profile/sheets/{sheet}/cells` (`range`, paging), `POST /model-drafts/{id}/inference/list` (`sheet`, `headerRow`, `block`, `applicationKey`); `setSource`'s bindings following their column letters when the header row moves (0.10 A8b, D124, D126, D128, [API.md § Source files and their profiles](../API.md#source-files-and-their-profiles), [§ Inferences](../API.md#inferences)) | J34.10 |
| The kinds `unmapColumn` (a column's binding taken out, also one the file no longer has) and `addValuesToList` on a flag set and a related record's column (0.10 A6); a profiled column's `values` and `valuesListed` | J34.6, J34.4 |
| `missing: "create"` on a flag set and on a related record's `parent`, and a `record: "existing"` row finding the record another row of the same file creates (0.10 A6, D93) | J27.8, J34.4 |
| A source's `rowsWithoutKey` (`refuse`, `skip`) on imports and `setSource`; `skippedRows` in the binding report and the dry run (0.10 A7, D110) | J27.8, J34.9 |
| A sheet laid out for reading in the profile (`laidOut`, a block's `titles` and `note`, columns per block; 0.10 A8a, D115, D119) and its `listBlock` proposals with their translations, yes/no and flag columns, notes and title groups (D116, D118); a source keyed by name (`key: {"field": "name"}`, `AMBIGUOUS_NAME_KEY`, `KEY_NOT_BOUND` at `/key/field`; D117); a header ending in a space mapped by its trimmed name | J34.10, J27.8, J34.2 |
| A source's fixed `parent` on imports, `addSource` and `setSource` (`PARENT_BOUND_TWICE`, `REFERENCE_NOT_FOUND` for a parent no record matches; 0.10 A8c, D141); a name key finding records among the parent's children, one key under one parent across sources (D142); a note's `meaning: "heading"` (D144); the `listBlock` alternative reading a run of lists of one shape as one list under their headers (D140, D143) | J34.10, J27.8 |
| The inference's model description (`modelDescription`, `describedList`, `describedField`, `describedFlags`), extend mode across files (a type matched by its fields, a list by its name, a code column by a stored unique attribute) and its `evidence.missing` and `evidence.drift`; a file without a workspace compared with the default workspace (0.10 A7, D106–D112) | J34.9, J34.5 |
| `GET /import-profiles/{key}/check` (the check of the profile's latest file: its columns new, missing and renamed, `valid` and `problems` against the active release, the dry run's summary and per source the counts of new values, drift and missing records), `GET /import-profiles/{key}/check/new-values`, `GET /import-profiles/{key}/check/drift`, `GET /import-profiles/{key}/check/missing-records` (`source`, paging), `GET /import-profiles/{key}/check/rows` (`source`, `status`, `code`, paging), `POST /import-profiles/{key}/check` (check the current file again); job kind `profileCheck`, queued once a file uploaded to a profile is profiled (0.10 A5c, D83, [API.md § The next version of a workbook](../API.md#the-next-version-of-a-workbook)) | J35.1, J35.2, J35.3 |
| A profile source's `missing` (`report`, `delete`): records of the type no row names, reported by every binding (`missingRecords`) and deleted with their own relationships into a change set (D82, D104); the source and mapping kind `setMissing`; a lookup onto a relation the row's record holds one of made replacing by the mapping kinds (D105) | J35.2 |
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
| `POST /objects` | J03, J14, J16; in a change set, a unique number or date refused naming its holder J06.5 |
| `GET /objects` (cross-type lookup, `objectTypeKey` repeatable) | J22.1, J01.4 |
| `GET /objects/{type}` (`expand`, `expandLimit`, `sort=related:<key>`, `filter.related:<key>…`, `candidateFor` with `anchorTypeKey`, items with `expanded`) | J01, J01.8, J01.9, J01.10, J13.9, J13.10, J21, J22, J23; `sort=<attribute>` in every context, ties by record ID, J21.9 |
| `GET /objects/{type}/{id}` | J01 |
| `PATCH /objects/{type}/{id}` | J02, J14 (move) |
| `DELETE /objects/{type}/{id}` (`cascade`, `deletionPreviewToken`) | J04 |
| `GET /objects/{type}/{id}/parent-candidates` (`parentObjectTypeKey`, `includeTypeChanges`, `withinObjectTypeKey`) | J14, J15 |
| `GET /objects/{type}/{id}/history` | J01.6, J15 |
| `POST /workspaces/{key}/queries/objects` | J22, J23 |
| `GET/POST/PATCH/DELETE /objects/{type}/{id}/attributes/{key}` | J01.5, J02.4 |
| `POST /relations`, `PATCH/DELETE /relations/{id}` (`expectedRelationSetVersion`, `relationSetDirection`) | J13, J13.3, J13.5, J16 |
| `GET /relations` (`objectId`), `GET /relations/{id}` | J01, J22.3; `relationSets` (each anchored set's version) J13.5 |
| `GET /relations/held` (`objectTypeKey`, `relationTypeKey`, `direction`, `objectId` repeatable up to 500, a context, paging) | J32.7 |
| `GET /workspaces/{key}/mapping-coverage` (`state`) | J10 |
| `GET /workspaces/{key}/mapping-candidates`, `GET /workspaces/{key}/mapping-targets` (`sourceObjectId`, `mappingVersion`) | J10, J10.3 |
| `PUT /workspaces/{key}/mappings` | J10 |
| `GET /workspaces/{key}/relations` | J22.2, J10 (a relationship view's edges, with `applicationKey` and `viewKey`) |
| `GET /workspaces/{key}/relation-matrix` (`columnIds`, `columnCursor`, `columnPageSize`, `state`) | J16 |
| `GET /workspaces/{key}/relation-matrix/containers`, `GET /workspaces/{key}/relation-matrix/link-candidates` (`rowId`, `columnId`) | J16 |
| `POST /batches` (`run`: `inline`) | J11; relationship items J11.7, J11.8; `replaceRelationSet` J10.10, J11.8; an upsert in a change set keyed by a unique number J06.5 |
| `POST /batches` (`run`: `background`), `GET /jobs` (`kind`, `state`), `GET /jobs/{id}`, `GET /jobs/{id}/items` (`status`), `POST /jobs/{id}/cancel` | J24, J24.8 (several nodes: every kind under a short lease, submissions of one subject sent together, a busy node, an export taken over; 0.11 N2) |
| `GET /workspaces/{key}/feed` (`after`, `pageSize`, `kind` and `objectTypeKey` repeatable) | J26, J26.1–J26.6 |
| `POST /exports` (`context`, `scope`: `types` with `where`, `parentObjectId`, `asOf`; `include.relations`; `format`: `jsonl`, `csv`, `xlsx`), `GET /jobs/{id}/output`, the job's `output` (0.9 J1) | J27, J27.1–J27.5 |
| `POST /import-profiles`, `GET /import-profiles`, `GET /import-profiles/{key}`, `PUT /import-profiles/{key}` (the whole profile with `expectedVersion`), `DELETE /import-profiles/{key}` (`expectedVersion`); a profile's `valid` and `problems` under the release of `workspaceKey` (0.9 J2); its `modelKey`, `workspaceKey` on every route and the list's `modelKey` (0.11 M3) | J27.7, J36.3, J36.4 |
| `POST /imports` (`multipart/form-data`: `file`, and `request` as JSON: `workspaceKey` or `changeSetId` with `expectedChangeSetVersion`, `profileKey` or an inline `profile` or neither, `format`, `policy`, `onExisting`, `stage`; `Idempotency-Key`); an import job's `parameters.profile` and `parameters.file`, its items' `ref` (`{sheet}!{row}`) (0.9 J2) | J27.8, J27.9, J27.10 |
| `POST /imports` with `stage: preview`; the job's `preview` (`coverage`, `items`, `rows`, `counts`, `result`, `previewedAt`), `bindingReport` and `confirmedAt`; `POST /jobs/{id}/confirm`; `POST /jobs/{id}/cancel` of a waiting preview; `GET /jobs/{id}/rows` (`status`, paging); `GET /jobs/{id}/items` (`ref`); a row refusal's `details.cells` (0.9 J3) | J27.10, J27.11, J27.12 |
| The job's `notices` (`RECORD_IDS_OF_ANOTHER_WORKSPACE`); `OBJECT_ALREADY_EXISTS` and `REFERENCE_NOT_FOUND` naming the workspace that holds the ID (`details.workspaceKey`) (0.9 J4a) | J27.10, J27.11 |
| `stage` (`execute`, `preview`) on `POST /batches`, refused with `run: inline`; a batch's `preview` (`coverage`, `items`, `counts`, `result`, `previewedAt`, no `rows`); `POST /jobs/{id}/confirm` and `POST /jobs/{id}/cancel` of a waiting batch preview (0.9 K2) | J11.9 |
| The `delete` item's `cascade` and `deletionPreviewToken`; an outcome's `impact` (`objectCount`, `objectsByType`, `relationshipCount`, `retainedAssociationCount`, `deletionPreviewToken`) and `deletedWithItem`; a preview's `deletion` totals; `OBJECT_HAS_DEPENDANTS` with `details.impact`, `DELETION_PREVIEW_REQUIRED` and `DELETION_PREVIEW_CHANGED` per item; the single delete's token accepted by a batch item (0.9 K2b) | J11.6 |
| `many-to-one` cardinality: a second relationship from a `from` record refused `CARDINALITY_VIOLATION` by `POST /relations`, an `ensureRelation` item, a `replaceRelationSet` with two targets and a change set's batch; the value refused in schema 0.8 and with `required` at validation; a release tightening a binding to it counted at `…/cardinality` by the diff and refused at activation until the data fits (0.9 K3a, D136–D138) | J11.12, J08.11 |
| The `ensureNoRelation` item (`relationTypeKey`, `from`, `to`, optional `expectedVersion`): `deleted` with `relationId` or `unchanged` without it; `IMMUTABLE_RELATION`, `REQUIRED_RELATION`, `VERSION_CONFLICT` per item (0.9 K3, D129) | J11.10 |
| A set replacement's `previousRelationSetVersion` and its refusals' `details.relationSetVersion`; `replaceRelationSet` without a claim in a preview; the claim carried at `POST /jobs/{id}/confirm` and `RELATION_SET_VERSION_CONFLICT` at execution for a set changed since (0.9 K3, D130) | J11.11 |
| `POST /exports` with `layout: "people"` and `people` (`columns`, `sheets`, `columnFields`); the output's `layout` and `sheets`; `POST /imports` of such a workbook without a profile, read through the profile it carries (`parameters.profile.embedded`); a profile's `key.versionColumn` and `key.nameColumn`, a relation binding's `idColumn`, `versionColumn` and `attributes` (0.9 J6) | J27.15, J27.16, J27.17 |
| `people.ownedColumns` (`parents`, `fields`) and `people.referenceLists` on `POST /exports`; a columns-per-parent sheet, reference sheets and their list rules; a related record binding's `versionColumn` and its `not loaded` mark (0.9 J6a) | J27.18, J27.19, J27.20, J27.21 |
| `otherWorkspaceIds` (`refuse`, `counterparts`) on `POST /imports` and `POST /batches`; the counterpart derivation; an outcome's `sourceId`; the `RECORD_IDS_AS_COUNTERPARTS` notice; `REFERENCE_NOT_FOUND` for a counterpart not loaded yet (0.9 J5) | J27.14, J11 |
| `GET /jobs/{id}/events` (server-sent events: the job at once and after each committed change, ending after a final state; 0.9 J1u) | J24.7, J27.6 |
| `POST /consumer-subscriptions`, `GET /consumer-subscriptions` (`consumerApi`, `workspaceKey`, `status`), `GET`, `PATCH` and `DELETE /consumer-subscriptions/{id}`, `POST /consumer-subscriptions/{id}/suspend`, `POST /consumer-subscriptions/{id}/resume` (`reset`); served with `CONSUMER_SUBSCRIPTIONS_ENABLED`; the subscription's `delivery`; `name` (U5a); `maxEventsPerBatch`, `payload`, `format` (C17; `mode` and `debounceSeconds` retired) | J30.6, J30.7, J30.8, J30.9 |
| `GET /consumer-subscriptions/{id}/deliveries` (`status`, paging), `GET /consumer-subscriptions/{id}/deliveries/{deliveryId}`, `POST …/deliveries/{deliveryId}/resend` (`eventId`); `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` and `consumerSubscriptions.logRetentionDays` (U5a) | J30.10 |
| Delivered in 0.11 M1 ([API.md § Workspace models](../API.md#workspace-models-product-011)): a workspace's `model` (`releaseId`, `releaseKey`, `releaseVersion`, `schemaVersion`, `modelHash`, `version`, `updatedAt`); `modelReleaseId` on `POST /workspaces`; `RDM-Workspace` on `GET /model`; `MODEL_RELEASE_CHANGED`'s `workspaceKey` and `currentReleaseId`; `CHANGE_SET_MODEL_RELEASE_CONFLICT`'s `workspaceKey`; `MODEL_REGISTRY_UNAVAILABLE`'s `workspaceKey`, `releaseId` and `schemaVersion` (`GET /model-runtime-state` and `POST /model-releases/{id}/activation` removed) | J36.1, J36.2, J36.3, J36.5, J36.6, J36.8 |
| Delivered in 0.11 M3: `compatibility.workspaces` on draft compile and the release diff (D25, D37); an import profile's `modelKey`; `workspace` on the consumer API index and OpenAPI document, which answer `RDM-Workspace` and `X-Model-Release-Id` | J36.2, J36.3, J36.4 |
| Delivered in 0.11 M4: `GET /objects` with `workspaceKey` repeatable (two or more: a read spanning workspaces), `modelReleaseId` on its items, `422 MODEL_ELEMENT_NOT_IN_EVERY_MODEL` (`details.element`, `details.workspaces`), `422 WORKSPACE_CONTEXT_MISMATCH` for a context with several workspaces; `COUNTERPARTS_ACROSS_MODELS` per item and as an import's notice (`workspaceKey`, `modelKey`, `workspaceModelKey`) | J36.7, J27.14 |
| Delivered in 0.11 M5: `releaseName` on a workspace's `model`, its model route, `GET /workspace-models` and an activation's answer (D53); `workspaceKey` on `GET /model-releases/{id}/diff`, its `compatibility` and `consumerContracts` then for that workspace (D52) | J36.1, J36.2 |
| `POST /workspaces/{key}/model/migrations` (`targetReleaseId`, `expectedVersion`, `typeMappings`); a migration job's `migration` summary, its rows (`GET /jobs/{id}/rows`, `status`: `conversion`, `reclassified`, `loss`, `refused`), its confirmation (`POST /jobs/{id}/confirm` with `expectedVersion`, `expectedFeedPosition`, `acceptLoss`) and cancel (0.11 V1) | J37, J37.1–J37.5 |
| `changeSetId` and `expectedChangeSetVersion` on `POST /workspaces/{key}/model/migrations`, `targetReleaseId` then optional; the `migration` summary's `changeSetId`, `changeSetVersion`, `activePublicationId` and, executed, `publicationId`; refused rows `CHANGE_SET_CONFLICT` and the publication's graph codes (0.11 V2, D79–D83) | J37.6 |
| `POST /change-sets/{id}/model-migrations` (`expectedChangeSetVersion`, `targetReleaseId` optional, `typeMappings`), registered with background jobs; a migration job's `parameters.moves: "changeSet"`; its summary's `currentReleaseId` (the change set's release) and the change set's fields as V2's; refused rows `CHANGE_SET_CONFLICT`, `MAPPING_SET_CHANGED` and the change set validation's codes (0.11 V3, D87–D94) | J37.7 |
| Delivered in 0.11 X1: `GET /model-mappings` (`sourceModelKey`, `targetModelKey`), `POST /model-mappings` (`key`, `name`, `sourceWorkspaceKey` or `sourceReleaseId`, `targetWorkspaceKey` or `targetReleaseId`), `GET /model-mappings/{key}` (`sourceWorkspaceKey`, `targetWorkspaceKey`: problems and coverage against those workspaces' releases), `DELETE /model-mappings/{key}` (`expectedVersion`), `POST/GET /model-mappings/{key}/operations` (the kinds `mapType`, `unmapType`, `mapAttribute`, `unmapAttribute`, `mapRelation`, `unmapRelation`, `setParent`, `setMatch`, `setValueMap`, `setMissing`, `setDefault`, `setReleases`), `POST /model-mappings/{key}/undo` (`step`, `steps`), `POST /model-mappings/{key}/redo`, `POST/GET /model-mappings/{key}/inference` (a job of kind `mappingInference`), `GET /model-mappings/{key}/inference/proposals` (`sourceType`), `POST /model-mappings/{key}/inference/application` (`proposals`) | J38.1 (a `setMatch` proposed on the unique attribute whose values the workspaces share, of any value type: 0.11 Q2) |
| Delivered in 0.11 X2: `POST /moves` (`sourceWorkspaceKey`, `targetWorkspaceKey`, `mapping` with `key` and `expectedVersion`, `selection` with `types` and their `where`, `parentObjectId` and `objectIds`, `sourceAt`, `mode: copy`, `stage: preview`), a job of kind `move` with its `move` summary; a move's rows at `GET /jobs/{jobId}/rows` (`outcome`, `reason`, `sourceType`): `create`, `update`, `refused`, `notMoved` | J38, J38.2, J38.4, J38.5 (matched by a unique number: 0.11 Q2), J38.7 |
| Delivered in 0.11 X3: `POST /moves` (`mode: copy` or `move`, `stage: preview` or `execute`); a move's dry run waits in `awaiting_confirmation`, and `POST /jobs/{jobId}/confirm` loads it into a new change set of the target (the job's `changeSetId`), with `mode: move` a change set of the source deleting what loaded (`move.sourceChangeSetId`), published only after the target's; a move's rows `updateOriginal`, `foundBy: origin`, `origin` and `source`; `GET /objects/{objectTypeKey}/{objectId}/history`'s `cause.origin` | J38.2, J38.3, J38.6, J38.8 |

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
| `GET /` (the API index: `workspace` (0.11 M3), `pageSize`, `cursor`, `position`, `from`, `includeTotal`) | J20.3, J36.3 |
| `GET /{consumerApi}/v{contractVersion}/openapi.json` (`workspace`, 0.11 M3) | J20.3, J20.4, J36.3 |

### Planned for 0.12 (designed in P0)

The security routes, codes and settings designed in [API.md § Security](../API.md#security-product-012-designed);
each moves into the tables above with its package. Every existing route gains `401` and `403`
(J39, J40), and every operation its declared action (the catalogue in API.md).

| Operation | Journeys | Package |
| --- | --- | --- |
| `GET /.well-known/oauth-authorization-server`, `GET /oauth/jwks` | J39, J41, J43.1 | I1 |
| `GET/POST /oauth/authorize` (the sign-in page; PKCE `S256`) | J39, J39.1, J39.5, J39.7 | I2, I3 |
| `POST /oauth/token` (`authorization_code`, `refresh_token`, `client_credentials`), `POST /oauth/revoke` | J39.2, J39.3, J41, J41.3, J41.4 | I1, I2 |
| `GET/DELETE /me/sessions`, `DELETE /me/sessions/{id}`, `POST /me/password` | J39.3, J39.6 | I2 |
| `GET/POST /users`, `GET/PATCH /users/{id}`, `POST /users/{id}/password-reset`, `DELETE /users/{id}/sessions`, `GET /users/{id}/grants` | J40, J39.3, J39.4 | I1, SP1 |
| Provider groups on `/groups` (D229) | J39.7 | I3 |
| Delivered in 0.12 Z2: a grant's record types enforced at the write unit (`publish` and `copy-move` narrowable); `stale`, `scope.missingApplications`, `scope.missingRecordTypes` on a grant and `stale` per group on `/me/permissions`; jobs run as their requester, who reads, follows, cancels and confirms them; `POST /moves` with `mode: move` needs `change-sets` in the source; source files read by their uploader and their workspace's `bulk` holders | J40.3, J40.10, J40 | Z2 |
| Delivered in 0.12 Z3: a consumer API grant on `POST /grants` (`consumerApi` instead of `role`, one workspace, not narrowed), `role: null` and `consumerApi` on a grant, `consumerApi=` on `GET /grants`; the consumer routes refusing without the grant (`403 FORBIDDEN`, `details: {consumerApi, workspaceKey}`, after the workspace and before the definition), the index listing the granted APIs for a `consumer` token and every API with Browse for a `management` one; the `oauth2` client credentials scheme, `401` and `403` in each consumer OpenAPI document; a subscription's `owner` and `ownerId=` | J41.2, J40, J30.6 | Z3 |
| `GET/POST /clients`, `GET/PATCH /clients/{id}`, `POST /clients/{id}/secrets`, `DELETE /clients/{id}/secrets/{secretId}` | J41, J41.3, J41.4 | I1, SP2 |
| `GET /token-signing-keys`, `POST /token-signing-keys/rotation` | J43.1, J43.2 | I1 |
| `GET/POST /sign-in-providers`, `GET/PATCH/DELETE /sign-in-providers/{key}` | J39.7 | I3 |
| `GET /system/configuration` (`GET /system` narrowed) | J31, J31.2 | I1 |
| `POST /consumer-subscriptions/{id}/rotate-secret` (`overlapHours`) | J43.3, J43.4 | K1 |
| `POST/DELETE /change-sets/{id}/submission`, `POST /change-sets/{id}/decisions`, `GET /workspaces/{key}/publication-requests`, `GET/PUT /workspaces/{key}/approval-policy` | J42, J42.1–J42.4, J42.6 | A1, A3 |
| `GET /me/notifications`, `POST /me/notifications/read`, `GET /me/notifications/events` | J42.5 | A2 |

Codes: `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID` (J39, J41.5, J43.2), `FORBIDDEN` (J40, J41.2),
`PASSWORD_REJECTED` (J39.6), `ROLE_PREDEFINED`, `ROLE_IN_USE` (J40.5),
`LAST_SECURITY_ADMINISTRATOR` (J40.8), `CHANGE_SET_SUBMITTED`, `APPROVAL_REQUIRED` (J42.2, J42.4);
the OAuth endpoints' `invalid_request`, `invalid_grant`, `invalid_client`, `unsupported_grant_type`.
Settings: `SECRETS_ENCRYPTION_KEY` (replaces `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, J43.5), the token
and session lifetimes (J39.2), `python -m app.cli.create_admin` (J40) and the re-sealing command
(J43.5).

## Error codes

Every code the API returns, by the journey that meets it. 32 of them were raised by the backend but
documented nowhere; API.md documents them since H4c (D-4).

| Journeys | Codes |
| --- | --- |
| Every route | `REQUEST_VALIDATION_ERROR`, `UNKNOWN_PARAMETER` (J21.8), `INTERNAL_ERROR` (with a correlation ID, the request's `X-Request-Id`, 0.11 O1), `DATABASE_UNAVAILABLE` (J12.8, J12.11; 0.11 Q1; `transactionEnded`, J24.3, 0.11 N3), `INVALID_CURSOR`, `INVALID_POSITION`, `CONFLICTING_PAGE_PARAMETERS`, `INVALID_SEEK`, `MUTUALLY_EXCLUSIVE_CONTEXT`, `WORKSPACE_NOT_FOUND`, `CHANGE_SET_NOT_FOUND`, `PUBLICATION_NOT_FOUND`, `WORKSPACE_CONTEXT_MISMATCH`, `MODEL_REGISTRY_UNAVAILABLE`, `MODEL_RUNTIME_STATE_UNAVAILABLE`, `WORKSPACE_RUNTIME_STATE_MISSING` |
| J32.7 | `UNKNOWN_RELATION_TYPE`, `INVALID_RELATION_PAIR`, `TOO_MANY_RECORDS` |
| J01, J21, J22 | `OBJECT_NOT_FOUND`, `UNKNOWN_OBJECT_TYPE`, `INVALID_FILTER`, `INVALID_SORT`, `INVALID_EXPAND` (J01.8), `INVALID_FILTER` for a relationship filter (J01.10), `INVALID_QUERY`, `MUTUALLY_EXCLUSIVE_SCOPE`, `WORKSPACE_KEY_REQUIRED`, `ATTRIBUTE_NOT_FOUND` |
| J02, J03, J13, J14 (the write rules) | `VERSION_CONFLICT`, `VERSION_REQUIRED`, `INVALID_ATTRIBUTE_VALUE`, `ATTRIBUTE_BELOW_MINIMUM`, `ATTRIBUTE_ABOVE_MAXIMUM`, `UNKNOWN_ATTRIBUTES`, `UNKNOWN_ATTRIBUTE_TYPE`, `DUPLICATE_ATTRIBUTE`, `DUPLICATE_ATTRIBUTE_VALUE`, `MISSING_REQUIRED_ATTRIBUTES`, `OBJECT_ATTRIBUTE_RULE_VIOLATION`, `CANNOT_DELETE_REQUIRED_ATTRIBUTE`, `READ_ONLY_ATTRIBUTES`, `ATTRIBUTE_ALREADY_EXISTS`, `OBJECT_ALREADY_EXISTS`, `UNKNOWN_APPLICATION`, `INVALID_OBJECT_TYPE_FOR_APPLICATION`, `OBJECT_TYPE_NOT_IN_APPLICATION`, `PARENT_REQUIRED`, `INVALID_PARENT_TYPE`, `PARENT_WRONG_SCOPE`, `PARENT_CYCLE`, `MISSING_REQUIRED_RELATIONS`, `DUPLICATE_INITIAL_RELATION`, `DUPLICATE_RELATION`, `DUPLICATE_RELATION_SCOPE`, `UNKNOWN_RELATION_TYPE`, `INVALID_RELATION_PAIR`, `RELATION_ENDPOINT_MISSING`, `RELATION_WRONG_SCOPE`, `UNKNOWN_RELATION_ATTRIBUTES`, `IMMUTABLE_RELATION`, `REQUIRED_RELATION`, `CARDINALITY_VIOLATION`, `RELATION_NOT_FOUND`, `RELATION_SET_VERSION_CONFLICT`, `RELATION_SET_CLAIM_INCOMPLETE`, `RELATION_CANDIDATE_REFUSED` (J13.9, J03.9; 0.9 K7), `WORKSPACE_RETIRED` |
| J04 | `DELETION_PREVIEW_REQUIRED`, `DELETION_PREVIEW_CHANGED`, `OBJECT_HAS_DEPENDANTS` |
| J05, J06, J07, J17 | `CHANGE_SET_REQUIRED`, `CHANGE_SET_VERSION_CONFLICT`, `CHANGE_SET_SNAPSHOT_RETRY`, `CHANGE_SET_SOURCE_INVALID`, `CHANGE_SET_BASE_INVALID`, `WORKSPACE_GRAPH_INVALID`, `ACTIVATION_CONFLICT`, `WORKSPACE_ACTIVE_PUBLICATION_CONFLICT` |
| J10 | `MAPPING_VERSION_CONFLICT`, `INVALID_CLEAR_ATTRIBUTES`, `REQUIRED_OWNERSHIP_BINDING`, `RELATION_ANCESTOR_REQUIRED`, `MAPPING_VIEW_REQUIRED`, `MAPPING_VIEW_NOT_FOUND`, `MAPPING_VIEW_BINDING_MISMATCH`, `MAPPING_BINDING_NOT_FOUND`, `MAPPING_SOURCE_NOT_FOUND`, `MAPPING_CANDIDATE_TYPE_MISMATCH`, `MAPPING_ENDPOINT_NOT_FOUND`, `MAPPING_ENDPOINT_TYPE_MISMATCH`, `MAPPING_PARENT_NOT_FOUND`, `MAPPING_PARENT_SCOPE_MISMATCH`, `INCOMPLETE_VIEW_IDENTITY` |
| J15 | `RESTRUCTURING_NOT_READY`, `RESTRUCTURING_TOO_LARGE`, `RESTRUCTURING_PLAN_CHANGED`, `INVALID_TYPE_MAPPING`, `OBJECT_TYPE_UNCHANGED`, `OBJECT_TYPE_CHANGED`, `TYPE_CHANGES_NEED_CHANGE_SET`, `CHILD_TYPE_NOT_ALLOWED`, `REQUIRED_RELATION_WITHOUT_PLACE`, `RELATION_ALREADY_EXISTS` |
| J16 | `RELATION_MATRIX_VIEW_NOT_FOUND`, `RELATION_MATRIX_ROW_NOT_FOUND`, `RELATION_MATRIX_COLUMN_NOT_FOUND`, `RELATION_MATRIX_PARENT_NOT_FOUND`, `RELATION_MATRIX_ACTION_NOT_ALLOWED`, `RELATION_MATRIX_PARENT_SCOPE_MISMATCH`, `RELATION_MATRIX_STATE_REQUIRES_COLUMNS`, `TOO_MANY_COLUMNS`, `DUPLICATE_COLUMN_IDS`, `CONFLICTING_COLUMN_PARAMETERS` |
| J18 | `CHANGE_SET_CONTENT_INCOMPATIBLE`, `CHANGE_SET_MODEL_RELEASE_CONFLICT`, `PINNED_MODEL_UNAVAILABLE`, `PINNED_MODEL_INVALID`, `UNSUPPORTED_PINNED_MODEL_SCHEMA`, `INVALID_INSTALLED_MODEL` |
| J08, J25 | `INVALID_MODEL`, `RELEASE_IDENTITY_CONFLICT`, `MODEL_MIGRATION_REQUIRED`, `MODEL_RELEASE_NOT_FOUND`, `MODEL_DRAFT_NOT_FOUND`, `UNSUPPORTED_SCHEMA_VERSION` (also a schema 0.8 document declaring `consumerApis`, J25.6), `MODEL_REGISTRY_REFRESH_FAILED`, `CONSUMER_CONTRACT_VERSION_REQUIRED`; diff findings `CONSUMER_API_REMOVED`, `CONSUMER_CONTRACT_VERSION_DECREASED` |
| J25.7 | `OPERATION_NOT_OFFERED` (`404`, on `objects`, `xref` and `resolve` of a definition that does not list the operation) |
| J20.6 | `CONSUMER_API_NOT_FOUND` (`404`, the expanded read of a definition the context's model does not declare) |
| J36.3, J36.4 (0.11 M3) | `IMPORT_PROFILE_MODEL_MISMATCH` (422 on a profile's save, import or file in another model's workspace; 409 on installing a draft over another model's profile) |
| J37 (0.11 V1) | Start: `WORKSPACE_NOT_FOUND`, `MODEL_RELEASE_NOT_FOUND`, `WORKSPACE_RETIRED`, `ACTIVATION_CONFLICT`, `UNSUPPORTED_SCHEMA_VERSION`, `MIGRATION_TARGET_IS_CURRENT` (held by the startup test, which reaches the route), `INVALID_MIGRATION_MAPPING` (`details.pointer`; held by a unit test of the plan, as no journey sends a wrong mapping), `CONSUMER_CONTRACT_VERSION_REQUIRED` (held by a unit test of the start). Confirm: `MIGRATION_REVIEW_STALE` (J37.4), `MIGRATION_HAS_REFUSALS` (J37), `MIGRATION_LOSS_NOT_ACCEPTED` (J37.2), `JOB_NOT_AWAITING_CONFIRMATION` (J37.3), `REQUEST_VALIDATION_ERROR`. The job's error: `MIGRATION_FAILED` (J37.5, injected at the execution boundary), `MIGRATION_REVIEW_STALE` |
| J37.6 (0.11 V2) | Start: `CHANGE_SET_NOT_FOUND`, `MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`, `MIGRATION_TARGET_IS_CURRENT` (a change set on the workspace's own release), `CHANGE_SET_VERSION_CONFLICT`. Confirm: `MIGRATION_REVIEW_STALE` (the change set or the active publication changed), `MIGRATION_HAS_REFUSALS` (what would stop the publication), `MIGRATION_LOSS_NOT_ACCEPTED`. The job's error: `MIGRATION_FAILED` (the publication step, injected) |
| J37.7 (0.11 V3) | Start: `CHANGE_SET_NOT_FOUND`, `CHANGE_SET_VERSION_CONFLICT`, `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`, `MIGRATION_TARGET_IS_CURRENT` (a change set on the workspace's release already). Confirm: `MIGRATION_REVIEW_STALE` (the change set edited or the workspace written since the preview), `MIGRATION_HAS_REFUSALS` (a conflict with live data, a rule the moved content breaks), `MIGRATION_LOSS_NOT_ACCEPTED`, `JOB_NOT_AWAITING_CONFIRMATION`. The job's error: `MIGRATION_FAILED` (the change set's event, injected) |
| J37.8 (0.11 V4) | `UNSUPPORTED_SCHEMA_VERSION` on installation (`details.draftId`, `schemaVersion`, `supportedSchemaVersions`, `operation: "install"`) and on activation into a workspace whose release is outside the window; `INVALID_OPERATION` (`setRelease` to a version outside the window); `INVALID_MODEL` (a lowered draft using a newer feature); `MODEL_REGISTRY_UNAVAILABLE` (a workspace on a release after the window, `details.schemaVersion`, `supportedSchemaVersions`); startup refusal of `RDM_MODEL_PATH` outside the window |
| J38.1 (0.11 X1) | `MODEL_MAPPING_EXISTS`, `MODEL_MAPPING_NOT_FOUND`, `MODEL_MAPPING_MODEL_MISMATCH` (a workspace running another model; `details` names the four model keys), `INVALID_MODEL_MAPPING` (a side named by both a workspace and a release, or by neither; held by the route's own check, as no journey sends it), `WORKSPACE_NOT_FOUND`, `WORKSPACE_RETIRED`, `MODEL_RELEASE_NOT_FOUND`; `INVALID_OPERATION` with `details.reason` (`unknownElement`, `bindingNotAllowed`, `valueTypesNotConvertible`, `modelMismatch`, `inUse`, `invalidValue`), `VERSION_CONFLICT`, `OPERATION_HAS_DEPENDANTS`, `NOTHING_TO_UNDO`, `NOTHING_TO_REDO`; `INFERENCE_NOT_FOUND`, `INFERENCE_NOT_READY`, `INFERENCE_STALE`, `PROPOSAL_NOT_FOUND`, `PROPOSAL_ALREADY_APPLIED`, `PROPOSAL_REQUIREMENT_MISSING`, `NOTHING_TO_APPLY` |
| J36, J37, J38 (planned for 0.11) | `MODEL_ELEMENT_NOT_IN_EVERY_MODEL`, `COUNTERPARTS_ACROSS_MODELS`, `MOVE_SAME_WORKSPACE`, `MODEL_MAPPING_MODEL_MISMATCH`, `MODEL_MAPPING_NOT_FOUND`, `MOVE_MAPPING_CHANGED`, `MOVE_MAPPING_HAS_PROBLEMS` (X2); `MOVE_NOTHING_TO_MOVE` (a confirmation with nothing to create or update), `MOVE_COPY_NOT_PUBLISHED` (a move's deletion published before its copy, `details.changeSetId` and `state`), and at a move's confirmation `MOVE_MAPPING_CHANGED`, `MODEL_RELEASE_CHANGED` and `WORKSPACE_RETIRED` (X3); rows kept in the source `SOURCE_CHANGED`, `OBJECT_HAS_DEPENDANTS` (X3); `ACTIVATION_CONFLICT`, `MODEL_RELEASE_CHANGED`, `CHANGE_SET_MODEL_RELEASE_CONFLICT` and `MODEL_REGISTRY_UNAVAILABLE` naming the workspace |
| J08, J11, J24 | `MODEL_RELEASE_CHANGED` |
| J19 | `WORKSPACE_ALREADY_EXISTS`, `DEFAULT_WORKSPACE_CANNOT_BE_RETIRED`, `WORKSPACE_IS_DEFAULT`, `WORKSPACE_HAS_PUBLICATIONS`, `WORKSPACE_NOT_EMPTY` |
| J23 | `AS_OF_NOT_SUPPORTED`, `INVALID_EFFECTIVE_PERIOD`; on the consumer API both answer `400`: `AS_OF_NOT_SUPPORTED` (J23.6, J23.7) and `INVALID_AS_OF` (J23.8) |
| J26 | `FEED_POSITION_AHEAD`, `FEED_POSITION_EXPIRED` (naming the export route, J27.2) |
| J27 | Exports: `INVALID_QUERY` (at a body pointer), `AS_OF_NOT_SUPPORTED`, `PARENT_NOT_FOUND`, `WORKSPACE_NOT_FOUND`, `CHANGE_SET_NOT_FOUND`, `PUBLICATION_NOT_FOUND`, `REQUEST_VALIDATION_ERROR` (J27.5), `INVALID_EXPORT_LAYOUT` for a workbook for people (J27.17, J27.21); the output: `JOB_NOT_FOUND`, `JOB_HAS_NO_OUTPUT`, `JOB_NOT_COMPLETED`, `JOB_EXPIRED` (J27.4), `JOB_OUTPUT_MISSING` (`410`, a file removed from `JOB_FILE_DIR` by hand; no journey reaches it, the route's own check); a failed export's `MODEL_RELEASE_CHANGED` and `JOB_FAILED` (J27.4) |
| J27.7–J27.10 | Profiles: `INVALID_IMPORT_PROFILE` (every problem at its pointer), `IMPORT_PROFILE_EXISTS`, `IMPORT_PROFILE_NOT_FOUND`, `IMPORT_PROFILE_VERSION_CONFLICT` (J27.7). Imports, before a job is stored: `IMPORT_TOO_LARGE` (`413`), `UNSUPPORTED_FILE_FORMAT`, `INVALID_IMPORT_PROFILE`, the context's codes (J27.10). A job that fails before an item runs: `IMPORT_FILE_MISMATCH`, `IMPORT_FILE_UNREADABLE` (J27.10); `IMPORT_TOO_MANY_ITEMS` (rows making more items than `BACKGROUND_JOB_MAX_ITEMS` or, atomic, `ATOMIC_JOB_MAX_ITEMS`; no journey reaches it, the binding's own check) and `IMPORT_FILE_MISSING` (a file removed from `JOB_FILE_DIR` by hand; no journey reaches it). A row's own: `INVALID_ATTRIBUTE_VALUE` (with `column`), `REFERENCE_NOT_FOUND`, `REFERENCE_AMBIGUOUS` (with `count`), `DUPLICATE_KEY_IN_FILE` (with `rows`), `REFERENCE_CYCLE`, `MISSING_RECORD_KEY`, `NAME_REQUIRED`, `INVALID_NAME`, `INVALID_CELL` (an export's table cell that is not an ID, a version or a known key), `REQUEST_VALIDATION_ERROR` (a JSON Lines line that is not a batch item) (J27.8–J27.10) |
| J27.11, J27.12 | Confirm: `JOB_NOT_AWAITING_CONFIRMATION` (`409`, with `state`: an executed import, a batch, a cancelled preview), `JOB_EXPIRED` (`410`), `CHANGE_SET_VERSION_CONFLICT` (`409`, the job still waiting); `MODEL_RELEASE_CHANGED`, `WORKSPACE_NOT_FOUND` and `CHANGE_SET_NOT_FOUND` as at submission (the same check as a chunk's context; no journey of its own). Rows: `JOB_HAS_NO_ROWS` (`404`, a batch or an export) |
| J30 | `EVENTS_NOT_DECLARED` (`404`), `UNKNOWN_EVENT`, `INVALID_PAYLOAD` (`400`), `EVENT_POSITION_AHEAD` (`409`), `EVENTS_EXPIRED` (`410`) (J30.4, J30.5); `PARAMETER_NOT_SUPPORTED` for `publication`, `asOf` and `to.` names, and the paging codes, as on the other consumer reads |
| J30.6, J30.7 | Subscriptions: `CONSUMER_API_NOT_FOUND`, `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`, `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, `UNKNOWN_OBJECT_TYPE`, `FILTER_MATCHES_NOTHING`, `INVALID_WEBHOOK_URL` (`400`, at a body pointer); `WORKSPACE_NOT_FOUND`, `SUBSCRIPTION_NOT_FOUND` (`404`); `VERSION_CONFLICT`, `SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED`, `SUBSCRIPTION_NEEDS_EDIT`, `EVENT_POSITION_AHEAD`, `EVENTS_EXPIRED` (resume), `WORKSPACE_HAS_SUBSCRIPTIONS` (`409`); `EVENTS_EXPIRED` (`410`, `startAfter`) |
| J30.10 | Deliveries: `SUBSCRIPTION_NOT_FOUND`, `DELIVERY_NOT_FOUND`, `EVENT_NOT_IN_DELIVERY` (`404`); `DELIVERY_NOT_SENT` (`409`, resend; held by a unit test, since no journey reaches a request never sent reliably); `REQUEST_VALIDATION_ERROR` (`422`: a create without `name`, J30.6; a resend without `eventId`; `maxEventsPerBatch` outside 1–1,000, an unknown `format`, the retired `mode` or `debounceSeconds`, J30.6 and J30.8) |
| J30.8, J30.9 | Webhook delivery (no route of its own; the receiver's requests and the subscription's state): suspension reasons `DELIVERY_FAILED`, `FILTER_MATCHES_NOTHING`, `EVENTS_EXPIRED`; a failed attempt's `kind` `status`, `redirect`, `timeout`, `connection`, `tls`, `address`; resume `409 EVENTS_EXPIRED` naming `reset` |
| J28 | `CONSUMER_API_NOT_FOUND`, `CONTRACT_VERSION_NOT_FOUND`, `PARAMETER_NOT_SUPPORTED`, `LIST_NOT_FOUND`, `PARENT_NOT_FOUND`, `INVALID_PAGE_SIZE`, `INVALID_PAGE_PARAMETER`; on the consumer API `UNKNOWN_PARAMETER`, `UNKNOWN_OBJECT_TYPE` and the paging codes are `400` (J28.4, J28.8, J28.10), and an unknown or retired workspace `404 WORKSPACE_NOT_FOUND` (J28.3); a pinned read: `PUBLICATION_NOT_FOUND` (`404`: an unknown publication, another workspace's, `latest` with none current) and `PUBLICATION_CONTRACT_MISMATCH` (`409`) (J28.12, J28.13) |
| J29 | `QUERY_REQUIRED`, `TOO_MANY_TERMS`, `QUERY_TOO_BROAD` (`test_consumer_xref_volume`), `INVALID_EXPECT`, `NO_MATCH`, `AMBIGUOUS_MATCH` (J29.3, J29.5, J29.6), `UNKNOWN_OBJECT_TYPE` (J29.6); batch resolve: each item's outcome carries the single read's code, plus `QUERY_OR_ID_REQUIRED`; the request is refused as `400 REQUEST_VALIDATION_ERROR` (a body of the wrong shape), `400 UNKNOWN_PARAMETER` or `PARAMETER_NOT_SUPPORTED` (`defaults`, the URL) and `413 BATCH_TOO_LARGE` (J29.10); crosswalk: `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET` (J29.11–J29.13), `MULTIPLE_TARGETS` and `UNKNOWN_PARAMETER` for a `to.` name (J29.14) |
| J33 (0.10 A2) | `INVALID_OPERATION` (`422`, with `index` and `pointer`), `OPERATION_REQUIRES_MIGRATION` (`409`, with the impact), `OPERATION_HAS_DEPENDANTS`, `NOTHING_TO_UNDO`, `NOTHING_TO_REDO` (`409`), `VERSION_CONFLICT` (`409`, with the steps since), `OPERATION_BATCH_TOO_LARGE` (`413`), `MODEL_DRAFT_NOT_FOUND` |
| J34 (0.10 A6) | `PROPOSAL_NOT_FOUND`, `INFERENCE_NOT_FOUND` (`404`), `PROPOSAL_ALREADY_APPLIED`, `NOTHING_TO_APPLY`, `INFERENCE_STALE` (the draft changed after the inference), `INFERENCE_NOT_READY` (`409`), `PROPOSAL_REQUIREMENT_MISSING` (with `proposal` and `requirement`), `INVALID_INFERENCE_REQUEST` (an application key that does not fit the mode), `INVALID_MODEL` (`422`); `SOURCE_FILE_NOT_FOUND`, `SOURCE_FILE_PROFILE_NOT_READY` as for the dry run; the warning `INFERENCE_DISAGREES` (D92); `SKIP_NEEDS_KEY` (an `INVALID_IMPORT_PROFILE` problem, 0.10 A7, D110); `REFERENCE_NOT_FOUND` on the rows naming a value the stored list lacks (D112); `AMBIGUOUS_NAME_KEY` on a row of a source keyed by name naming a name two records share (0.10 A8a, D117); `INVALID_RANGE` (`422`, a range that is malformed, empty or outside the sheet, or a rectangle with no value under its header, 0.10 A8b) |
| J35 (0.10 A5c) | `MISSING_DELETE_NEEDS_CHANGE_SET` (`422`, a live load through a profile that deletes missing records, D82), `PROFILE_CHECK_NOT_FOUND` (`404`, a profile without a checked file), `SOURCE_FILE_NOT_FOUND` (`404`) and `SOURCE_FILE_PROFILE_NOT_READY` (`409`) on `POST …/check`; `INVALID_IMPORT_PROFILE` for a load through a profile a newer release broke (J35.3); a missing record with dependants refused `OBJECT_HAS_DEPENDANTS` with its impact (D104) |
| J34 (0.10 A3, A5a) | `CREATE_NEEDS_NAME_MATCH` (an `INVALID_IMPORT_PROFILE` problem, D77); the draft profile's warnings `COLUMN_UNMAPPED`, `SOURCE_WITHOUT_COLUMNS`, `SOURCE_WITHOUT_KEY` (D78); `SOURCE_FILE_NOT_FOUND`, `SOURCE_SHEET_NOT_FOUND`, `DRY_RUN_NOT_FOUND`, `MODEL_DRAFT_NOT_FOUND`, `IMPORT_PROFILE_NOT_FOUND` (`404`), `SOURCE_FILE_PROFILE_NOT_READY` (`409`, with the profile's `state`), `VERSION_CONFLICT` (`409`, delete), `SOURCE_FILE_MISSING` (`410`, the stored file gone from `JOB_FILE_DIR`: a profile job's or a load's error), `IMPORT_TOO_LARGE` (`413`), `UNSUPPORTED_FILE_FORMAT`, `INVALID_IMPORT_PROFILE`, `INVALID_MODEL` (`422`, a dry run of a draft that does not compile, D71), `REQUEST_VALIDATION_ERROR` (`422`, an import sending a file and naming `sourceFileId`); J27's import codes for the load |
| J39, J40, J41, J43 (0.12 I1) | `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID` (`expired`, `revoked`, `audience`, `unknownKey`, `malformed`, `signature`), `USERNAME_TAKEN`, `USER_NOT_FOUND`, `CLIENT_NOT_FOUND`, `CLIENT_SECRET_NOT_FOUND`, `PASSWORD_REJECTED` (`create_admin`; `tooShort`, `tooLong`, `username`, `common`) |
| J39.1–J39.6, J40 (0.12 I2) | `TOKEN_INVALID` (`revoked`: a session ended, reused or lapsed), `PASSWORD_INCORRECT` (`422`), `PASSWORD_REJECTED` (`/me/password`, the reset page), `SESSION_NOT_FOUND` (`404`), `NOT_A_PERSON` (`403`, a client on `/me/sessions` or `/me/password`); the token endpoint's `invalid_grant` (a code or refresh token unknown, expired, used or not this browser's) and `invalid_client` (the browser's grants with a secret or another `client_id`); the sign-in page's `401`, `429` with `Retry-After`, `403` (posted from another origin) and `400` (an unknown client or address, never redirected); the reset page's `410` |
| J40, J40.1–J40.9 (0.12 Z1) | `FORBIDDEN` (`403`; `details.action`, `groups`, `workspaceKey`), `ROLE_PREDEFINED`, `ROLE_IN_USE`, `ROLE_NOT_FOUND`, `ROLE_NAME_TAKEN`, `ACTION_GROUP_UNKNOWN`, `GROUP_NOT_FOUND`, `GROUP_NAME_TAKEN`, `GROUP_MEMBER_NOT_FOUND`, `GRANT_NOT_FOUND`, `GRANT_SCOPE_INVALID` (instance and workspace both or neither; an instance grant narrowed; a role held only at the instance granted in a workspace, SP1, D302), `GRANT_SCOPE_UNKNOWN` (`422`, an application or record type the workspace's model lacks, D281), `LAST_SECURITY_ADMINISTRATOR` (`409`, D283), `ROUTE_NOT_DECLARED` (`500`, an operation without a declaration; the contract test keeps it from shipping) |
| J40.3, J40.10, J40 (0.12 Z2) | `FORBIDDEN` with `details.recordTypes` (`403`, a write of record types the caller's grants in the workspace do not name: a single write, each refused batch, import or move item, a publication, a restructuring's plan; D289–D293), `FORBIDDEN` with `details.requestedBy` (a job whose requester lost the group or was deactivated, at confirmation or its next step, D294), `WRITER_UNKNOWN` (`500`, a write naming no writer, failing closed, D292) |
| J11, J24 | `BATCH_TOO_LARGE`, `INVALID_BATCH_CONTEXT`, `IDEMPOTENCY_KEY_REUSED`, `IDEMPOTENCY_IN_PROGRESS`, `MISSING_RECORD_KEY`, `INVALID_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `REFERENCE_TYPE_MISMATCH`, `JOB_NOT_FOUND`, `JOB_FINISHED`, `JOB_FAILED` |

## Operator surface (J12)

| Setting or command | Journeys |
| --- | --- |
| `DATABASE_URL` | J12, J12.1, J31.2 (reported without its password) |
| Every setting (reported by `GET /system/configuration` with value, default and source; secrets as set or not) | J31, J31.1, J31.2 |
| `RDM_MODEL_PATH` | J12 (the starter or bootstrap model), J08 |
| `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, `INTEGRATION_JOBS_ENABLED` | J12.7, J08, J19.4, J11 |
| `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`, `ATOMIC_JOB_MAX_ITEMS`, `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`, `JOB_CHUNK_ITEMS`, `JOB_LEASE_SECONDS`, `JOB_RETENTION_DAYS` | J12.7, J11, J24, J24.8 |
| `FEED_RETENTION_DAYS` | J26.6 |
| `JOB_FILE_DIR` (export files and import uploads; a directory that cannot be written refuses the start with jobs on) | J27, J12.1 |
| `IMPORT_MAX_BYTES` (an import's largest file, reported as `integrationJobs.limits.importMaxBytes`) | J27.10 |
| `MODEL_OPERATION_MAX_ITEMS` (the operations one request may hold, 500; 0.10 A2) | J33.8 |
| `INFERENCE_ASSISTANT` (the optional assistant's factory, empty by default) and `INFERENCE_ASSISTANT_ROWS` (the rows of each sheet it is sent, 20; 0.10 A6, D95): the interface only, no provider bundled; covered by a unit test with a fake | J34.4 |
| `JOB_PREVIEW_MAX_ITEMS` (the items a preview of an import or a batch runs before it is a sample, reported as `integrationJobs.limits.previewMaxItems`) | J27.12, J11.9 |
| `CONSUMER_RESOLVE_MAX_ITEMS` (reported by `GET /capabilities` as `consumerApi.resolveMaxItems`) | J29.10 |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` (the subscriptions API and their delivery, reported by `GET /capabilities` as `consumerSubscriptions` with the delivery limits, `maxEventsPerBatch` among them), their signing keys sealed with `SECRETS_ENCRYPTION_KEY` | J30.6–J30.9 |
| `SECRETS_ENCRYPTION_KEY` (required; seals token and webhook signing keys; `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` refused by name, 0.12 I1, D253), `PUBLIC_URL` (the token issuer, D259) | J12.7, J39, J41 |
| `ACCESS_TOKEN_MINUTES` (an access token's lifetime, D251), `TOKEN_SIGNING_KEY_DAYS` (the signing key's age before the next token replaces it, D264) | J41, J43.1 |
| `SESSION_IDLE_HOURS`, `SESSION_DAYS` (a browser session's ends, D251), `PASSWORD_RESET_HOURS` (a reset link's life, D272), `CORS_ORIGINS` as the sign-in's return addresses (D267) (0.12 I2) | J39, J39.2, J40 |
| `PASSWORD_MIN_LENGTH` (a local password's least length, 15; lowered only on a development machine, D276) | J39.6, J40 |
| `python -m app.cli.create_admin` (the first administrator's roles at the instance, D282), `python -m app.cli.create_client --role` (0.12 Z1) | J40, J41 |
| `python -m app.cli.create_admin` (`--password-stdin`), `python -m app.cli.create_client` (`--json`) (0.12 I1, D235, D262) | J40, J41 |
| `python -m app.cli.generate_key` | J30.6, J12.7 (the secrets key) |
| `WEB_CONCURRENCY` | J12.7 (served above 1 with model administration on), J12.10 (several workers or processes on one database, 0.11 N1) |
| `DATABASE_POOL_SIZE`, `DATABASE_POOL_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT` (each process's connections, 0.11 Q1) | J12.7, J12.11 |
| `DATABASE_IDLE_TRANSACTION_TIMEOUT` (a stalled process's transaction ended, 0.11 N3) | J12.7, J24.3 |
| `LOG_FORMAT`, `LOG_LEVEL` (the log, 0.11 O1) and the `X-Request-Id` header | J12.15, J12.7 |
| `PROCESS_HEARTBEAT_SECONDS` (each process's report to the others, 0.11 O1) | J12.13, J12.7 |
| `CORS_ORIGINS` | J12.7 (a browser client on another origin) |
| `RDM_CURSOR_SIGNING_KEY` | J21 (cursors that survive a restart), J12.7 |
| `RDM_API_REFERENCE_SCRIPT` | J20, J12.7 |
| `python -m app.cli.database_upgrade` | J12 |
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
  ([TODO](../TODO.md#now--product-09)). J08.9 is delivered by 0.10 A2 as the draft's operation
  history.
- **D-6. Batch delete with cascade.** *Decided: a batch delete item must be able to cascade*, as a
  single delete can; refusing an item with dependants, or deleting only as one atomic batch, is not
  a realistic integration path. Journey variant J11.6 (delivered in 0.9 K2b). How a batch confirms the impact it
  deletes (the single delete's signed preview token) is designed with
  [PG-D18](../POSTGRESQL_RUNTIME_PLAN.md#decisions), which now carries this direction.
- **D-7. The schema upgrade command's help** named schemas 0.5–0.7. *Fixed 2026-10-02:* the help
  is built from the supported schema list (now 0.5–0.8).
