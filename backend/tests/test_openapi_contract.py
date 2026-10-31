import hashlib
import json

from harness_identity import TestClient

from app.main import app, create_app


def test_base_0_7_wp12_openapi_document_is_locked():
    # Re-baselined for WP-10K: object and relation timestamps are nullable (not recorded in drafts
    # and history). Re-baselined for Base 0.8 S3/S4: every collection gains from, position and
    # includeTotal and every page prevCursor, anchor, totalCount and startIndex; objects, relations
    # and mapping coverage gain seek; objects gain topLevel; relations gain search and sort
    # (test_paging_openapi_inventory below states them). Re-baselined for the S4R3 revision: the
    # object and relation sort descriptions name every data field (scalar attributes, objectType,
    # relationship) instead of the sortable feature. Re-baselined for S4R4: the object sort
    # description states that an omitted sort orders by name. Re-baselined for S4R5: pages list
    # items first and document totalCount and startIndex as optional integers, omitted unless
    # includeTotal=true. Re-baselined for W2 (ADR-031): drafts and revisions are change sets and
    # publications in every route, parameter, field, schema and error code, and a publication names
    # its model release key and version. Re-baselined for W3: change-set and publication operations
    # carry the change-sets tag, since they no longer belong to workspace administration.
    # Re-baselined for W4: each capability group names the deployment setting that controls it.
    # Re-baselined for W6: DELETE /workspaces/{key}, and single-workspace responses state deletable
    # and deleteBlockedBy (WorkspaceDetailResponse). Re-baselined for A2: GET
    # /workspaces/{key}/relation-matrix and the RelationMatrix* schemas. Re-baselined for A3: the
    # relation matrix containers and link-candidates reads, relationVersion on cell records, and an
    # optional relation-set claim (expectedRelationSetVersion, relationSetDirection) on relation
    # create and delete, whose response states the claimed set's relationSetVersion. Re-baselined
    # for B2: GET /objects/{type}/{id}/parent-candidates and the ParentCandidate* and ObjectPathPart
    # schemas; no existing path or schema changed. Re-baselined for P2a: GET
    # /change-sets/{id}/object-changes and /relation-changes and the ObjectChange* and
    # RelationChange* schemas; no existing path or schema changed. Re-baselined for P2b: the
    # optional ObjectChange.beforePath (where the source held a moved record). Re-baselined for
    # C1: ObjectChangeState.objectTypeKey (the type on each side), and the descriptions of
    # ObjectChange.changedFields and the object-changes objectTypeKey filter; no path changed.
    # Re-baselined for C3: POST /change-sets/{id}/restructurings/preview and /restructurings and
    # the Restructuring* schemas, and parent candidates' includeTypeChanges parameter with the
    # optional ParentCandidate.objectTypeKeys; no existing path or schema otherwise changed.
    # Re-baselined for C4: parent candidates' repeatable withinObjectTypeKey parameter, and GET
    # /model/placements with the ModelPlacements, ModelApplicationPlacements and ModelPlacementParent
    # schemas; nothing else. Re-baselined for 0.9 Q1: GET /objects, the cross-type lookup, added to
    # the existing /objects path beside POST; no existing operation or schema changed.
    # Re-baselined for 0.9 Q2: publicationId on GET /workspaces/{key}/mappings, and the same edge
    # list published as GET /workspaces/{key}/relations; no schema changed. Re-baselined for 0.9
    # Q3: POST /workspaces/{key}/queries/objects with the ModelQuery body, the ObjectQueryPage
    # response and their parts; no existing path or schema changed. Re-baselined for 0.9 C1: the
    # release diff's consumerContracts block (ModelConsumerContractsResponse); nothing else.
    # Re-baselined for 0.9 Q4: an optional asOf date on GET /objects/{objectTypeKey}, an optional
    # asOf on GET /objects that is refused (D21), and ModelQuery.asOf's description; nothing else.
    # Re-baselined for 0.9 B1: POST /batches, GET /jobs, /jobs/{id} and /jobs/{id}/items with the
    # Batch*, Job*, RecordReference, RecordKeyValue and UpsertKey schemas; the capabilities'
    # integrationJobs group, and an optional cause on audit events; no existing path changed.
    # Re-baselined for 0.9 B2: POST /jobs/{id}/cancel, a 202 JobResponse on POST /batches and its
    # description, cancelRequestedAt, leaseOwner and leaseExpiresAt on JobResponse, and the
    # background limits in JobLimits; removing those gives B1's document exactly. Re-baselined for
    # H4c (D-1): GET /workspaces/{key}/mappings removed (the same list as /relations), and
    # /relations' description no longer names it; nothing else. Re-baselined for 0.9.0-alpha.1 PG5:
    # info.version 0.9.0-alpha.1; with 0.8.0 the document hashes to the previous lock exactly.
    # Re-baselined for 0.9 F1: GET /workspaces/{key}/feed with FeedPage, FeedEntry and FeedCause,
    # and AuditCause.kind gaining "publication" (D15) with its description; removing those gives
    # the previous document exactly. Re-baselined for 0.9 B3: the relationship batch items
    # (Batch*RelationItem, BatchReplaceRelationSetItem, RelationSetTarget) in BatchRequest.items,
    # relationId, relationSetVersion and relationIds (RelationIds) on JobItemResponse, relationSets
    # (RelationSetVersionItem) on RelationPage with its description, and POST /batches' description
    # naming relationship writes; no path added or removed, no other schema changed. Re-baselined
    # for 0.9 F2: changeFeed (ChangeFeedCapabilities) on CapabilitiesResponse, feedPosition on
    # PublicationResponse and the feed route's description naming the expiry; removing those gives
    # the previous document exactly. Re-baselined for 0.9 T1b: the codes in the document are upper
    # case (the four job reasons and the invalidCursor, versionConflict and requestValidation error
    # examples); lower-casing those seven gives the previous document exactly. Re-baselined for
    # 0.9 C14: consumerApi (ConsumerApiCapabilities) on CapabilitiesResponse; removing it gives the
    # previous document exactly.
    # Re-baselined for 0.9 C11: capabilities gain consumerSubscriptions (ConsumerSubscriptionCapabilities)
    # and deleteBlockedBy gains "subscribed"; the subscription routes are gated off by default (checked
    # with the capability on below), and no existing path changed.
    # Re-baselined for 0.9 C12: consumerSubscriptions gains delivery (WebhookDeliveryLimits) and its
    # description says the group also delivers; removing those gives the previous document exactly.
    # Re-baselined for 0.9 U3: GET /system with SystemResponse, EngineInfo, ActiveModelRelease,
    # DatabaseInfo and SystemSetting; removing those gives the previous document exactly.
    # Re-baselined for C-D101 revised: consumerSubscriptions loses allowedHosts and its description
    # the allowlist; adding those back gives the previous document exactly.
    # Re-baselined for 0.9 U5a: consumerSubscriptions gains logRetentionDays; removing it gives the
    # previous document exactly (the subscription routes, with name and the deliveries, are gated off).
    # Re-baselined for 0.9 C17: WebhookDeliveryLimits' maxEvents becomes maxEventsPerBatch, with its
    # description; renaming it back with the previous description gives the previous document
    # exactly (the subscription routes, with the delivery choices, are gated off).
    # Re-baselined for 0.9 J1: POST /exports and GET /jobs/{job_id}/output, the Export* schemas
    # and JobResponse.output; no existing path or schema otherwise changed. Re-baselined for 0.9
    # J1u: GET /jobs/{job_id}/events, the job event stream; nothing else changed. Re-baselined for
    # 0.9 J2: GET/POST /import-profiles, GET/PUT/DELETE /import-profiles/{profile_key} and POST
    # /imports with the ImportProfile*, ImportRequest and binding schemas, and importMaxBytes in
    # JobLimits with its description; removing those gives J1u's document exactly. Re-baselined for
    # 0.9 J3: POST /jobs/{job_id}/confirm and GET /jobs/{job_id}/rows with the JobRow*, JobActions,
    # ImportPreview, Preview* and BindingReport* schemas; JobResponse gains confirmedAt, preview and
    # bindingReport, JobLimits importPreviewMaxItems (and its description), ImportRequest's stage
    # takes preview (and its description), GET /jobs/{job_id}/items gains ref and the cancel
    # route's description names a waiting preview; no other path or schema changed. Re-baselined
    # for 0.9 C18: GET /model/consumer-apis/{consumerApi} with ConsumerApiDocument and the schema
    # 0.9 definition parts it names; removing the path and the schemas only it reaches gives J3's
    # document exactly. Re-baselined for 0.9 J4a: JobResponse.notices with the JobNotice schema;
    # removing those two gives C18's document exactly. Re-baselined for 0.9 J5: otherWorkspaceIds on
    # BatchRequest and ImportRequest and sourceId on JobItemResponse; removing those three gives
    # J4a's document exactly. Re-baselined for 0.9 K2: BatchRequest's stage, ImportPreview renamed
    # JobPreview with rows optional, JobLimits' importPreviewMaxItems renamed previewMaxItems, and
    # the descriptions of POST /batches, the confirm route and the preview naming a batch's
    # preview; no path changed. Re-baselined for 0.9 K2b: the delete item's cascade and
    # deletionPreviewToken, the outcome's impact and deletedWithItem, the preview's deletion
    # totals (DeletionImpact, DeletionTotals) and their descriptions; no path changed. Re-baselined
    # for 0.9 K3: the ensureNoRelation item (BatchEnsureNoRelationItem, in BatchRequest's items),
    # the outcome's previousRelationSetVersion and the descriptions of the set replacement and the
    # outcome; no path changed. Re-baselined for 0.9 K5: GET /objects/{object_type_key} takes
    # expand and expandLimit and answers TypedObjectPage (QueryObject items, with expanded), its
    # sort description names related:<key>, and QueryObject's description; no other path changed.
    # Re-baselined for 0.9 K5a: ExpandedRelations.field and the expand description's <key>.<field>.
    # Re-baselined for 0.9 K6: the per-type list's filter description names the relationship filter;
    # no schema or path changed. Re-baselined for 0.9 K6a: GET /relations/held with HeldRecordPage,
    # HeldRecord and HeldObject, and expand's description losing "at most 5" (D142 revised); removing
    # those and restoring the phrase gives K6's document exactly. Re-baselined for 0.9 K7: candidateFor
    # and anchorTypeKey on GET /objects/{object_type_key}; no other path or schema changed.
    # Re-baselined for 0.9 J6: ExportRequest's layout and people (PeopleLayout), ExportOutput's
    # layout and sheets, SourceKey's versionColumn and nameColumn, RelationBinding's idColumn,
    # versionColumn and attributes (RelationValue); no path or other schema changed.
    # Re-baselined for 0.9 J6a: PeopleLayout's ownedColumns (OwnedColumns) and referenceLists,
    # RelatedRecordBinding's versionColumn; no path or other schema changed.
    # Re-baselined for 0.9 R-F14: three route descriptions name their codes in upper case (the
    # cancel route's JOB_FINISHED, the feed's FEED_POSITION_EXPIRED, the query's INVALID_QUERY);
    # diffed against HEAD, nothing else changed. Re-baselined for 0.9.0 (R, D207): info.version
    # 0.9.0; diffed against the previous document, nothing else changed. Re-baselined for 0.10 A3:
    # the source file routes (/source-files, /source-files/{id}, its profile's sheets and columns)
    # with the Source* schemas and their upload body; ImportRequest's sourceFileId and the import
    # route's optional file part; the job kinds profile and dryRun on JobResponse and the job list's
    # kind filter. Diffed against HEAD, nothing else changed (the dry-run routes are model
    # administration's, outside the default document). Re-baselined for 0.10 A5a: ParentBinding's and
    # RelationBinding's optional missing (refuse or create, D77). Diffed against HEAD, nothing else
    # changed (the draft profile route and the step's dryRun are model administration's).
    # Re-baselined for 0.10 A6a: FlagsBinding's and RelatedParent's optional missing (D93), the job
    # kind inference on JobResponse and the job list's kind filter, and a profiled column's values
    # (SourceColumnResponse) and valuesListed (SourceColumnLimits). Diffed against HEAD, nothing
    # else changed (the inference routes are model administration's). Re-baselined for 0.10 A5c: the
    # profile check's reads (GET /import-profiles/{key}/check, its new-values, drift,
    # missing-records and rows) with the Check* schemas and ProfileCheckResponse, which brings the
    # DryRun* summary schemas into the default document; Source's optional missing (D82),
    # BindingReportSource's missingRecords and the job kind profileCheck on JobResponse and the job
    # list's kind filter. Diffed against HEAD, nothing else changed (POST …/check is registered with
    # integration jobs, off in the default document). Re-baselined for A5c's last load: a profile's
    # lastLoad (ImportProfileLastLoad, ImportLoadCounts) and the two read routes' descriptions;
    # diffed against the previous commit, nothing else changed. Re-baselined for A7 (D110): Source's
    # optional rowsWithoutKey and its description, skippedRows on BindingReportSource and
    # DryRunSourceSummary; diffed against the previous commit, nothing else changed. Re-baselined for
    # A8a (D115–D119): SourceBlock's titles and note (SourceBlockNote), SourceSheetResponse's laidOut,
    # SourceOverlap's block, SourceKey's field (name) and the descriptions of those and of the column
    # page; diffed against the previous commit, nothing else changed. Re-baselined for A8b (D124): GET
    # /source-files/{id}/profile/sheets/{sheet}/cells and the SourceCell, SourceCellRow and
    # SourceCellPage schemas; diffed against the previous commit, nothing else changed.
    # Re-baselined for 0.10 A8c: a source's fixed parent (FixedParent, Source.parent and its
    # description) and a note's meaning heading (SourceBlockNote); diffed against the previous
    # commit, nothing else changed. Re-baselined for 0.10.0 (R, D153): info.version 0.10.0; with
    # 0.10.0-alpha.1 the document hashes to the previous lock exactly. Re-baselined for 0.11 M1
    # (ADR-042): GET /workspaces/{key}/model and GET /workspace-models (WorkspaceModelResponse,
    # WorkspaceAssignmentResponse, WorkspaceAssignmentPage); a workspace's model; WorkspaceCreate's
    # modelReleaseId; a release's assigned and workspaces in place of active, and the list's assigned
    # filter; an activation's workspaceKey; GET /model's RDM-Workspace header; GET
    # /model-runtime-state and ModelRuntimeStateResponse removed. Diffed against the previous
    # commit, nothing else changed (the activation route is registered with model administration,
    # off in the default document). Re-baselined for 0.11 M3 (D9, D25, D35, D37, D40): an import
    # profile's modelKey, workspaceKey on its create and update bodies and on its read and list, the
    # list's modelKey filter and the routes' descriptions; the release diff's compatibility as
    # CandidateCompatibilityResponse with its workspaces (WorkspaceCompatibilityResponse), replacing
    # ModelCompatibilityResponse. Diffed against the previous commit, nothing else changed.
    # Re-baselined for 0.11 M4 (D41, D43): GET /objects takes workspaceKey repeatable (an array) and
    # its items are LookupObject, an ObjectResponse with modelReleaseId; the route's description.
    # Diffed against the previous commit, nothing else changed. Re-baselined for 0.11 M5 (D52, D53):
    # the release diff's workspaceKey and a workspace's model's releaseName (WorkspaceModelResponse,
    # WorkspaceAssignmentResponse). Diffed against the previous commit, nothing else changed.
    # Re-baselined for 0.11 M6a (D63): the optional X-Expected-Model-Release-Id header on every
    # management route. Diffed against the previous commit, nothing else changed. Re-baselined for
    # 0.11.0-alpha.1 (D12): info.version 0.11.0-alpha.1; with 0.10.0 the document hashes to the
    # previous lock exactly. Re-baselined for 0.11 V1 (D72, D74): a job's kind migration and its
    # migration summary (MigrationSummary, MigrationCounts), the confirmation's optional body
    # (JobConfirmation), a job's rows as an import's or a migration's page (MigrationRowPage,
    # MigrationRow) with the migration outcomes as statuses, and the jobs list's kind filter. Diffed
    # against the previous commit, nothing else changed (the migration route is registered with
    # model administration, off in the default document). Re-baselined for 0.11 V2 (D80, D83): the
    # migration summary's changeSetId, changeSetVersion, activePublicationId and publicationId.
    # Diffed against the previous commit, nothing else changed (the route's request is off in the
    # default document, as above). Re-baselined for 0.11 V3 (D91): POST
    # /change-sets/{change_set_id}/model-migrations with ChangeSetMigrationRequest, and the
    # MigrationTypeMapping and MigrationAttributeSource it names (the route is registered with
    # background jobs, on in the default document). Diffed against the previous commit, nothing
    # else changed. Re-baselined for 0.11 X1 (D104–D113): the model-mappings routes (list, read,
    # create, delete, operations and their history, undo, redo, the inference, its proposals and
    # their application) with the ModelMapping* and Mapping* schemas, and a job's kind
    # mappingInference (JobResponse and the jobs list's kind filter). Diffed against the previous
    # commit, nothing else changed. Re-baselined for 0.11 X2 (D114, D119, D122): a job's kind move
    # and its move summary (MoveSummary and the Move* counts), a job's rows as a move's page too
    # (MoveRowPage, MoveRow, MoveReason, MoveLeftBehind) with the outcome, reason and sourceType
    # filters, and the jobs list's kind filter. Diffed against the previous commit, nothing else
    # changed (POST /moves is registered with model administration, off in the default document).
    # Re-baselined for 0.11 X3 (D128–D136): a move's summary gains mode, its change sets, the
    # source's feed position at the load and its deleted and kept counts (MoveSourceCounts), its
    # counts updateOriginal; a move's row gains the outcome updateOriginal, foundBy origin, origin
    # (RecordOrigin) and source (MoveSourceOutcome), and the rows' outcome filter updateOriginal; a
    # history entry's cause gains origin; the confirmation's description names a move's. Diffed against the previous commit, nothing else
    # changed. Re-baselined for 0.11 X4: a move's relationship row gains fromName and toName.
    # Diffed against the previous commit, nothing else changed. Re-baselined for 0.11 O1 (D191–D197):
    # GET /health/live, GET /metrics, GET /api/v1/system/processes and GET /api/v1/system/readiness
    # with their Process* and *Readiness* schemas. Diffed against the previous commit, nothing else
    # changed. Re-baselined for 0.11 O2 (D198–D204): GET /api/v1/system/summary and GET
    # /api/v1/system/backup-rehearsals with the Summary* and *Rehearsal* schemas. Diffed against the
    # previous commit, nothing else changed. Re-baselined for 0.11.0 (R, D229): info.version 0.11.0;
    # with 0.11.0-alpha.1 the document hashes to the previous lock exactly. Re-baselined for 0.12 I1
    # (ADR-043): the OAuth metadata, JWKS and token endpoints, /me, /users, /clients and their
    # secrets, /token-signing-keys and its rotation, /system/configuration with SystemResponse
    # narrowed to the engine, schema languages and active release (D246), the engineOAuth scheme
    # and `security` on every operation but the open ones. Diffed against 5622b67, nothing else
    # changed. Re-baselined for 0.12 I2: /oauth/revoke, the token endpoint's authorization_code and
    # refresh_token fields, /me/sessions, /me/password, /users/{id}/password-reset and
    # /users/{id}/sessions with their schemas, MeResponse's signedInWith and sessionId, and a
    # person's deactivation ending their sessions in PATCH /users/{id}'s description. Diffed against
    # 3633627, nothing else changed (the sign-in and reset pages are HTML, outside the document).
    # Re-baselined for 0.12 Z1 (ADR-044): /action-groups, /roles, /groups and their members,
    # /grants, /workspaces/{key}/access, /me/permissions and /me/grants with their schemas;
    # x-action, x-action-groups and x-action-scope on every operation but the open ones (D256);
    # GET /jobs' description (filtered, D285). Diffed against ffe558b, nothing else changed.
    # Re-baselined for 0.12 Z2 (D289–D297): a grant's stale and its scope's missingApplications
    # and missingRecordTypes, stale on a held group (D296), and GET /source-files' description
    # (filtered, D295). Diffed against eaa724c, nothing else changed. Re-baselined for 0.12 SP1
    # (D298–D302): a person's roles (UserRole, UserRoleWorkspace), GET /users/{user_id}/grants,
    # q and memberId on GET /groups, q on GET /clients, and the descriptions of GET /users and
    # POST /grants. Diffed against eea6ca1, nothing else changed. Re-baselined for 0.12 Z3
    # (D306): a grant's role nullable beside consumerApi (GrantConsumerApiResponse), consumerApi on
    # GrantCreate and as a filter on GET /grants, and the descriptions of GET and POST /grants and of
    # stale (the subscription routes, with their owner, are off in this document). Diffed against
    # 1ef0b7d, nothing else changed. Re-baselined for 0.12 Z4 (D313–D317): actor on a history
    # entry, a feed entry and an activation (ActorResponse), createdBy on a change set, publishedBy
    # and withdrawnBy on a publication, requestedBy on a job, a draft operation's author
    # (PrincipalResponse), and GET /security-events (SecurityEventPage). Diffed against f604cbd,
    # nothing else changed. Re-baselined for 0.12 Z5 (D325, D327, D328): holding on GET
    # /workspaces, createdBy on GET /workspaces/{workspace_key}/change-sets, and GET
    # /me/action-groups (HeldAnywhereList, HeldAnywhere, HeldWorkspace). Diffed against 260bac0,
    # nothing else changed. Re-baselined for 0.12 HM1 (D332, D333): GET /me/workspaces
    # (OwnWorkspacePage, OwnWorkspaceResponse, WorkspaceApplication) and GET /me/change-sets
    # (OwnChangeSetPage, OwnChangeSetResponse), and product on GET /system (InstanceProduct, D338).
    # Diffed against 56f090d, nothing else changed. Re-baselined for 0.12 Z6 (D340, D343): GET
    # /changes (ChangePage, ChangeEntry, ChangeWorkspace, ChangeSetRef, ChangeSubject, ChangeObject,
    # ChangeAttribute, ChangeCause). Diffed against 56903d2, nothing else changed. Re-baselined for
    # 0.12 SP2 (D348–D350, D355): a client's roles, consumerApis (ClientConsumerApi) and createdBy,
    # a secret's hint, and GET /workspaces/{workspace_key}/grant-options (GrantOptionsResponse,
    # GrantOption). Diffed against Z6's lock, nothing else changed. Re-baselined for 0.12 I3
    # (D363–D366): the sign-in providers and local sign-in (/sign-in-providers, its local entry and
    # {key}: SignInProviderCreate, SignInProviderUpdate, SignInProviderResponse, SignInProviderPage,
    # LocalSignInUpdate, LocalSignInResponse), a group's source (GroupSource, GroupSourceResponse)
    # and a member's seenAt, a person's identities (UserIdentityResponse) and localKept, signInProvider
    # on /me (SignInProviderRef), sign-in-provider among the security events' aggregates, and the
    # descriptions of POST /groups, POST /groups/{group_id}/members, GET /me, PATCH /users/{user_id}
    # and POST /users/{user_id}/password-reset. Diffed against a11f71e, nothing else changed.
    # Re-baselined for 0.12 I4a (D377–D381): POST /users/{user_id}/identities (IdentityLink) and
    # DELETE /users/{user_id}/identities/{provider}, signOutOfProvider on the provider's create,
    # update and read, signedOutUri on its read, and the description of PATCH /users/{user_id}.
    # Diffed against ebd2a2a with I4's files alone (the working tree also holds RH1's history
    # changes, which this hash leaves out), nothing else changed. Re-baselined for 0.12 I4b
    # (D383–D388): GET|POST /me/second-factor, POST /me/second-factor/confirmation, POST
    # /me/second-factor/recovery-codes, DELETE /me/second-factor (MySecondFactorResponse,
    # SecondFactorEnrolment, RecoveryCodesResponse, SecondFactorCode), DELETE
    # /users/{user_id}/second-factor, secondFactor on a person (SecondFactorSummary),
    # secondFactorRequired on local sign-in's read and update (whose enabled becomes optional) and
    # the description of PATCH /sign-in-providers/local. Diffed against I4a's lock, nothing else
    # changed. Re-baselined for 0.12 I4c (D389–D394): GET /me/passkeys, PATCH|DELETE
    # /me/passkeys/{passkey_id}, GET /users/{user_id}/passkeys, DELETE
    # /users/{user_id}/passkeys/{passkey_id} (PasskeyResponse, PasskeyPage, PasskeyRename), passkeys on
    # a person and on the caller's second factor, and the description of DELETE /me/second-factor.
    # The ceremonies' endpoints and the script are the engine's pages, outside the document. Diffed
    # against I4b's lock, nothing else changed. Re-baselined for the I4 review: DELETE
    # /me/passkeys/{passkey_id} takes an optional body (PasskeyRemoval: the password, or a code)
    # and its description. This hash is of the
    # whole working tree, RH1's history changes (HistoryRelated, HistoryValue, kind and actorId)
    # included, so the lock passes in the shared checkout; the earlier hash of I4's files alone
    # could not be re-derived. Re-baselined for the refiroo name: only the document's title and
    # description changed (verified by restoring the old two, which reproduces the earlier hash).
    # Re-baselined for 0.12 M1: GET/PUT/DELETE /mail-settings, POST /mail-settings/test and GET
    # /mail-outbox (the Mail schemas), `mail-settings` among a security event's aggregate types and
    # `mailSender` among a process's threads; diffed against C1's lock, nothing else changed.
    # Re-baselined for 0.12 SP3: POST /users/{id}/password-reset takes an optional body
    # (PasswordResetRequest: `send`) and answers `sentTo`; nothing else changed.
    # Re-baselined for 0.12 M1 (stop): POST /mail-outbox/{message_id}/stop. Diffed against the previous
    # lock, nothing else changed.
    # Re-baselined for 0.12 E1 (F5): the profile check's six routes (GET|POST
    # /import-profiles/{profile_key}/check and GET .../check/new-values, .../drift,
    # .../missing-records, .../rows) take a required workspaceKey query parameter, their
    # x-action-scope becomes "the query's workspace" (was "any scope"), and their descriptions
    # name the workspace. Verified by restoring the three changed app files, which reproduces the
    # previous hash.
    # Re-baselined for 0.12 A1: POST/DELETE /change-sets/{id}/submission, POST
    # /change-sets/{id}/decisions, GET /workspaces/{key}/publication-requests and GET/PUT
    # /workspaces/{key}/approval-policy with the PublicationRequest*, Decision*, Submission* and
    # ApprovalPolicy* schemas, `submission` on ChangeSetResponse, `approval-policy` among a security
    # event's aggregate types, and the description of POST /change-sets/{id}/publication; nothing
    # else changed.
    # Re-baselined for 0.12 A2: GET /me/notifications, POST /me/notifications/read and GET
    # /me/notifications/events with the Notification* schemas, and on the consumer subscriptions
    # `source` (create and answer) with `consumerApi` optional in the create and nullable in the
    # answer; nothing else changed.
    # Re-baselined for 0.12 M2: GET and PUT /me/notification-mail with NoticeMailResponse and
    # NoticeMailUpdate, and the description of MailMessageResponse.kind (`test` and `notice`);
    # nothing else changed.
    # Re-baselined for 0.12 A3: ApprovalPolicyResponse.approverCount; nothing else changed.
    # Re-baselined for 0.12 M2 follow-up (notification types): NoticeMailResponse.kinds (with
    # NoticeKindResponse) and NoticeMailUpdate takes optional `enabled` and `kinds`; the
    # descriptions of GET and PUT /me/notification-mail; nothing else changed.
    # Re-baselined for 0.12 L1: `info.license` (AGPL-3.0-or-later) and EngineInfo.license and
    # .sourceCode (GET /system); nothing else changed.
    # Re-baselined for 0.12 UW1: `availability` on WorkspaceResponse and WorkspaceDetailResponse
    # (WorkspaceAvailable, WorkspaceUnavailable) and POST /model-releases/{releaseId}/raising with
    # the ModelReleaseRaising* schemas; nothing else changed.
    # Re-baselined for 0.12 R: DELETE /change-sets/{id}/submission is declared by the new action
    # `change-sets.withdraw` (groups change-sets and approve, was change-sets.submit), so an
    # approver without Work in change sets may withdraw a request; nothing else changed.
    # Re-baselined for 0.12 R: the description of POST /me/password names `429 SIGN_IN_SLOWED` (a
    # wrong current password is counted like a wrong sign-in); nothing else changed.
    # Re-baselined for 0.12 MR1 (additive): PATCH and DELETE /model-releases/{releaseId}
    # (ModelReleaseStatusRequest), the list's `status` and `usable` parameters, and a release's
    # status, statusVersion, retiredAt, deletable and deleteBlockedBy; nothing else changed.
    # Re-baselined for 0.12 NT1 (additive): GET /me/notifications's `q`, `kind`, `workspace` and
    # `sort`; NotificationsRead's `subjectId` and `read`; POST /me/notifications/removal with
    # NotificationsRemoval and NotificationsRemovalResult; the descriptions of those routes and of
    # NotificationsReadResult.marked. Verified by restoring NT1's two files in a copy, which
    # reproduces MR1's hash. Re-baselined for 0.12.0: info.version 0.12.0; with 0.11.0 the document
    # hashes to the previous lock exactly.
    # Re-baselined for 0.16 AP1 (additive): GET /ai/status, GET /ai/calls and POST /ai/test with the
    # Ai* schemas, and `ai` (AiSystemInfo) on SystemResponse. Diffed against 0.12.0's document in a
    # worktree of HEAD: nothing else changed.
    # Re-baselined for 0.16 AP1 (fixes, additive): AiSystemInfo.model and
    # ModelDraftProfileResponse.freeKey; nothing else changed.
    # Re-baselined for 0.16 AP2 (additive): POST /workspaces/{key}/mapping-proposals with
    # MappingProposalRequest, AiProposalResult and ProposalOrigin; JobResponse.aiProposal and the
    # kind aiProposal; MappingTargetSummary.origin and AuditEventResponse.origin; the coverage
    # parameter proposed; the purpose mappingTarget on the Ai* schemas (AiFeature.purpose a
    # one-value const becomes an enum). Diffed against HEAD's document in a worktree. Then the
    # kind aiProposal on GET /jobs; with it removed the document hashes to the previous lock.
    # Re-baselined for 0.16 AP6a (removal): the inference's naming helper; InferenceRequest.assistant,
    # InferenceResponse.assistant, .assistantOutcome and .phase (with InferenceAssistantOutcome) and
    # the purpose modelNames on the Ai* schemas (AiFeature.purpose a one-value const again), and the
    # description of POST /model-drafts/{id}/inference; nothing else changed.
    # Re-baselined for 0.16 AP6a (additive): the assistant's tasks (GET and POST /ai/tasks, GET
    # /ai/tasks/{id} and its /changes, POST /ai/tasks/{id}/plan, /run and /cancel) with the AiTask*
    # and Task* schemas; the kind aiTask on JobResponse and GET /jobs; the purpose workbookLoad on
    # the Ai* schemas. With them removed the document hashes to the previous lock.
    # Re-baselined for 0.16 AP6a (revision, additive): the task reading's titles, profile and summary,
    # a table's parentTypeKeys, profile, parent, notes, attention and leftOut, a column's kind, label
    # and evidence, the owner profile, the check's summary and a check table's translations and
    # nothingToDo. Schemas only; not diffed against the previous document. Then AP6a's column
    # `known` (a column the followed profile always left out), additive.
    # Re-baselined for 0.16 AP6 (additive): POST /ai/tasks/{id}/answers (AiTaskAnswersRequest), the
    # task's `design` (TaskDesign, DesignQuestion, DesignRecord) and `draftId`, the check as
    # TaskCheck or DesignCheck (DesignSheet), the result's `releaseId` and the job phase
    # `designing`. Schemas and one path only; no existing field changed.
    # Re-baselined for 0.16 AP6 (words alone, relationships; additive): the optional `file` of POST
    # /ai/tasks (a request with words only), the design's `links` and the check's `links` and
    # `summary.relationships`, DesignCheck.dryRunJobId nullable, the result's `linksJobId` and the
    # error code AI_TASK_NEEDS_WORDS in the route's description.
    # Re-baselined for 0.16 AP6 (revision): GET /ai/tasks/{id}/changes takes `source` (a design's
    # sheet; `table` optional), DesignSheet.source, and the task phases narrowed to profiling,
    # reading, designing and checking (asking, matching and fixing were AP6a's removed turns);
    # DesignSheet.skipped (rows of a source skipping rows without a key that wrote nothing); the
    # import profile's RelatedParent.valueMap (a parent column's cell mapped before it is matched);
    # TaskDesign.leftOut (the columns no source loads, with the assistant's reason); 0.16 AP6r:
    # POST /ai/tasks/{id}/model and /accept, TaskDesign.stage, outline, checks and corrections.
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "a2acd612ad692c9684b71f1ec4a9267b7965f7419b7c15c6f861c4ef418179e4"
    )


def test_paging_openapi_inventory():
    """Base 0.8 S3: every cursor-paged collection pages both ways, by position and with totals."""
    document = app.openapi()
    seekable = {
        "/api/v1/objects",
        "/api/v1/objects/{object_type_key}",
        "/api/v1/relations",
        "/api/v1/workspaces/{workspace_key}/mapping-coverage",
        "/api/v1/workspaces/{workspace_key}/relation-matrix",
    }
    paged = set()
    for path, operations in document["paths"].items():
        parameters = {item["name"] for item in operations.get("get", {}).get("parameters", [])}
        if "cursor" not in parameters:
            continue
        paged.add(path)
        assert {"from", "position", "includeTotal"} <= parameters, path
        assert ("seek" in parameters) == (path in seekable), path
        schema = operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        # A job's rows are an import's or a migration's page (0.11 V1): each pages alike.
        for page in schema.get("anyOf", [schema]):
            name = page["$ref"].rsplit("/", 1)[-1]
            properties = document["components"]["schemas"][name]["properties"]
            assert {"nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(
                properties
            )
            # S4R5: items first; totals are optional integers, omitted rather than null.
            assert next(iter(properties)) == "items", path
            assert {"totalCount", "startIndex"}.isdisjoint(
                document["components"]["schemas"][name]["required"]
            )
            assert properties["totalCount"]["type"] == properties["startIndex"]["type"] == "integer"
    # 0.9 B1 added the job list and a job's outcomes; H4c removed GET /workspaces/{key}/mappings (D-1);
    # 0.9 J2 added the import profiles; 0.9 J3 an import's rows; 0.9 K6a what records hold; 0.10 A3
    # the source files and a profile's sheets and columns; 0.10 A5c a profile check's new values,
    # drift, missing records and rows; 0.10 A8b a range of a sheet's cells; 0.11 M1 the workspaces'
    # model assignments; 0.11 X1 the model mappings, a mapping's history and its proposals; 0.11 O1
    # the processes and the readiness per workspace; 0.11 O2 the backup rehearsals; 0.12 I1 the
    # people, clients and token signing keys; 0.12 I2 a person's sessions; 0.12 Z1 the roles, groups,
    # a group's members, grants, a workspace's access and the caller's grants; 0.12 SP1 a person's
    # grants; 0.12 Z4 the security events; 0.12 HM1 the caller's workspaces and change sets; 0.12
    # Z6 the changes across workspaces; 0.12 I3 the sign-in providers; 0.12 I4c a person's passkeys,
    # their own and an administrator's; 0.12 M1 the mail outbox; 0.12 A1 the publication requests; 0.12 A2 the inbox;
    # 0.16 AP1 the AI provider's calls; 0.16 AP6a the assistant's tasks and a task's changes.
    assert seekable <= paged and len(paged) == 68
    assert {
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}/items",
        "/api/v1/jobs/{job_id}/rows",
        "/api/v1/import-profiles",
        "/api/v1/relations/held",
    } <= paged
    objects = {
        item["name"]
        for item in document["paths"]["/api/v1/objects/{object_type_key}"]["get"]["parameters"]
    }
    relations = {
        item["name"] for item in document["paths"]["/api/v1/relations"]["get"]["parameters"]
    }
    assert "topLevel" in objects and {"search", "sort"} <= relations
    # 0.9 Q3: the model-aware query pages the same way, with its page selection in the body.
    query = document["paths"]["/api/v1/workspaces/{workspace_key}/queries/objects"]["post"]
    body = query["requestBody"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    assert {"cursor", "from", "position", "includeTotal", "pageSize"} <= set(
        document["components"]["schemas"][body]["properties"]
    )
    page = query["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit(
        "/", 1
    )[-1]
    properties = document["components"]["schemas"][page]["properties"]
    assert next(iter(properties)) == "items"
    assert {"nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(properties)
    # 0.9 B1: an inline batch answers with the first page of its outcomes, continued on
    # GET /jobs/{id}/items.
    batch = document["paths"]["/api/v1/batches"]["post"]
    page = batch["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit(
        "/", 1
    )[-1]
    properties = document["components"]["schemas"][page]["properties"]
    assert next(iter(properties)) == "items"
    assert {"job", "nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(
        properties
    )


def test_wp6_openapi_removes_rejected_object_lifecycle_and_direct_writes():
    paths = app.openapi()["paths"]
    forbidden = {
        "/api/v1/object-drafts",
        "/api/v1/object-drafts/{draft_id}",
        "/api/v1/object-drafts/{draft_id}/activation",
        "/api/v1/object-revisions/{revision_id}",
        "/api/v1/workspace-drafts/{draft_id}/objects",
        "/api/v1/workspace-drafts/{draft_id}/relations",
    }
    assert not (set(paths) & forbidden)
    # 0.9 Q1: GET /objects is the cross-type lookup, a read beside the canonical create.
    assert set(paths["/api/v1/objects"]) == {"get", "post"}
    assert set(paths["/api/v1/objects/{object_type_key}"]) == {"get"}
    assert set(paths["/api/v1/objects/{object_type_key}/{object_id}"]) == {"get", "patch", "delete"}
    assert set(paths["/api/v1/relations"]) == {"get", "post"}
    assert set(paths["/api/v1/relations/{relation_id}"]) == {"get", "patch", "delete"}
    schemas = set(app.openapi()["components"]["schemas"])
    assert (
        not {
            "ObjectDraftCreate",
            "ObjectDraftResponse",
            "ObjectRevisionResponse",
            "ObjectRetirementRequest",
        }
        & schemas
    )
    assert {"RelationCreate", "RelationResponse"} <= schemas


def test_wp8_openapi_inventory_locks_workspace_lifecycle_and_record_crud():
    paths = app.openapi()["paths"]

    def methods(path):
        return frozenset(method for method in paths[path] if method != "parameters")

    # Workspace lifecycle orchestration endpoints (WP8, named by ADR-031): change sets, validation,
    # atomic publish, immutable publication reads and publication withdrawal. Lists stay under
    # their workspace; single items are addressed by global id.
    assert methods("/api/v1/workspaces/{workspace_key}/change-sets") == {"get", "post"}
    assert methods("/api/v1/change-sets/{change_set_id}") == {"get", "patch", "delete"}
    assert methods("/api/v1/change-sets/{change_set_id}/model-release") == {"patch"}
    assert methods("/api/v1/change-sets/{change_set_id}/validation") == {"post"}
    assert methods("/api/v1/change-sets/{change_set_id}/publication") == {"post"}
    assert methods("/api/v1/workspaces/{workspace_key}/publications") == {"get"}
    assert methods("/api/v1/publications/{publication_id}") == {"get"}
    assert methods("/api/v1/publications/{publication_id}/withdrawal") == {"post"}
    # ADR-031 names only: no route keeps the earlier draft, revision, activation or retirement name.
    assert not [
        path
        for path in paths
        if any(
            old in path
            for old in (
                "workspace-draft",
                "workspace-revision",
                "/drafts",
                "/revisions",
                "/retirement",
            )
        )
        or (path.startswith("/api/v1/change-sets") and path.endswith("/activation"))
    ]

    # Canonical record CRUD remains the way objects, typed attribute values and relations are
    # addressed; containment and translation are ordinary object types/edges inside those records.
    assert methods("/api/v1/objects") == {"get", "post"}  # GET: the 0.9 Q1 cross-type lookup
    assert methods("/api/v1/objects/{object_type_key}") == {"get"}
    assert methods("/api/v1/objects/{object_type_key}/{object_id}") == {"get", "patch", "delete"}
    attribute_path = "/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"
    assert methods(attribute_path) == {"get", "post", "patch", "delete"}
    assert methods("/api/v1/relations") == {"get", "post"}
    assert methods("/api/v1/relations/{relation_id}") == {"get", "patch", "delete"}

    # Records are not nested inside a draft/revision resource, and object-level lifecycle resources
    # were rejected: no workspace-draft child CRUD and no object-draft/object-revision routes.
    assert not (
        set(paths)
        & {
            "/api/v1/object-drafts",
            "/api/v1/object-drafts/{draft_id}",
            "/api/v1/object-drafts/{draft_id}/activation",
            "/api/v1/object-revisions/{revision_id}",
            "/api/v1/workspace-drafts/{draft_id}/objects",
            "/api/v1/workspace-drafts/{draft_id}/relations",
            "/api/v1/workspace-drafts/{draft_id}/attributes/{attribute_type_key}",
        }
    )


def test_wp6_openapi_keeps_bounded_active_object_reads_and_structured_errors():
    schema = app.openapi()
    response = schema["paths"]["/api/v1/objects/{object_type_key}"]["get"]["responses"]
    assert response["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TypedObjectPage"
    }
    error_content = response["default"]["content"]["application/json"]
    assert error_content["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert set(error_content["examples"]) == {
        "invalidCursor",
        "requestValidation",
        "versionConflict",
    }
    parameters = schema["paths"]["/api/v1/objects/{object_type_key}"]["get"]["parameters"]
    assert any(item["name"] == "filter.<field>.<operator>" for item in parameters)


def test_base_0_5_enabled_openapi_exposes_guarded_activation(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    schema = create_app().openapi()
    assert {
        path: frozenset(method for method in schema["paths"][path] if method != "parameters")
        for path in schema["paths"]
        if path.startswith("/api/v1/model-drafts")
    } == {
        "/api/v1/model-drafts": frozenset({"get", "post"}),
        "/api/v1/model-drafts/{draft_id}": frozenset({"get", "patch", "delete"}),
        "/api/v1/model-drafts/{draft_id}/compile": frozenset({"post"}),
        "/api/v1/model-drafts/{draft_id}/installation": frozenset({"post"}),
        # 0.10 A2: operations, their history, undo and redo (ADR-041).
        "/api/v1/model-drafts/{draft_id}/operations": frozenset({"get", "post"}),
        "/api/v1/model-drafts/{draft_id}/undo": frozenset({"post"}),
        "/api/v1/model-drafts/{draft_id}/redo": frozenset({"post"}),
        # 0.10 A4a: the outline the editor reads (D36).
        "/api/v1/model-drafts/{draft_id}/outline": frozenset({"get"}),
        # 0.10 A4b: the draft compiled, for the preview (D43).
        "/api/v1/model-drafts/{draft_id}/model": frozenset({"get"}),
        "/api/v1/model-drafts/{draft_id}/profile": frozenset({"get"}),
        "/api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}": frozenset({"get"}),
        "/api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/schema.json": frozenset(
            {"get"}
        ),
        "/api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/example.json": frozenset(
            {"get"}
        ),
        "/api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/openapi.json": frozenset(
            {"get"}
        ),
        # 0.10 A3: a draft's dry run and the rows behind it (D65–D67).
        "/api/v1/model-drafts/{draft_id}/dry-run": frozenset({"get", "post"}),
        "/api/v1/model-drafts/{draft_id}/dry-run/rows": frozenset({"get"}),
        "/api/v1/model-drafts/{draft_id}/inference": frozenset({"get", "post"}),
        "/api/v1/model-drafts/{draft_id}/inference/proposals": frozenset({"get"}),
        "/api/v1/model-drafts/{draft_id}/inference/application": frozenset({"post"}),
        # 0.10 A8b: a rectangle read as a list (D128).
        "/api/v1/model-drafts/{draft_id}/inference/list": frozenset({"post"}),
    }
    # 0.11 M1: activation names its workspace; the instance-wide route is gone (ADR-042).
    assert set(schema["paths"]["/api/v1/workspaces/{workspace_key}/model/activation"]) == {"post"}
    assert "/api/v1/model-releases/{release_id}/activation" not in schema["paths"]


def test_base_0_9_c11_c12_enabled_openapi_exposes_the_subscriptions_api(monkeypatch):
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    schema = create_app().openapi()
    assert {
        path: frozenset(method for method in schema["paths"][path] if method != "parameters")
        for path in schema["paths"]
        if path.startswith("/api/v1/consumer-subscriptions")
    } == {
        "/api/v1/consumer-subscriptions": frozenset({"get", "post"}),
        "/api/v1/consumer-subscriptions/{subscription_id}": frozenset({"get", "patch", "delete"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/rotate-secret": frozenset({"post"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/suspend": frozenset({"post"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/resume": frozenset({"post"}),
        # U5a: the delivery log.
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries": frozenset({"get"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}": frozenset(
            {"get"}
        ),
        # U5a revision: resending an event by hand (C-D129).
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}/resend": frozenset(
            {"post"}
        ),
    }
    components = schema["components"]["schemas"]
    response = components["SubscriptionResponse"]
    assert "signingSecret" not in response["required"]
    # U5a: a subscription is named, on create and in every answer (C-D115).
    assert (
        "name" in response["required"]
        and "name" in components["ConsumerSubscriptionCreate"]["required"]
    )
    # C12: the delivery state, the reasons the dispatcher sets, and resume's reset (C-D108, C-D110).
    assert "delivery" in response["required"]
    assert set(components["SubscriptionDelivery"]["properties"]) == {"lastDeliveredAt", "pending"}
    assert set(components["DeliveryError"]["properties"]["kind"]["enum"]) == {
        "status",
        "redirect",
        "timeout",
        "connection",
        "tls",
        "address",
    }
    reasons = set(components["SubscriptionSuspension"]["properties"]["reason"]["enum"])
    assert {"DELIVERY_FAILED", "FILTER_MATCHES_NOTHING", "EVENTS_EXPIRED"} <= reasons
    assert "HOST_NOT_ALLOWED" not in reasons
    assert set(components["ConsumerSubscriptionResume"]["properties"]) == {
        "expectedVersion",
        "reset",
    }


def test_wp4_mapping_query_inventory_and_required_context():
    paths = app.openapi()["paths"]
    base = "/api/v1/workspaces/{workspace_key}/mapping-"
    for name, response in (
        ("coverage", "MappingCoveragePage"),
        ("candidates", "MappingCandidatePage"),
        ("targets", "MappingTargetPage"),
    ):
        assert set(paths[base + name]) == {"get"}
        operation = paths[base + name]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{response}"
        }
        parameters = {row["name"]: row for row in operation["parameters"]}
        assert parameters["applicationKey"]["required"] == (name != "targets")
        assert parameters["viewKey"]["required"] == (name != "targets")
        assert (
            "changeSetId" in parameters and "publicationId" in parameters and "cursor" in parameters
        )
        size = parameters["pageSize"]["schema"]
        bounds = next((row for row in size.get("anyOf", []) if row.get("type") == "integer"), size)
        assert bounds["minimum"] == 1 and bounds["maximum"] == 100
        if name != "candidates":
            assert all(
                parameters[key]["required"]
                for key in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey", "direction")
            )
        else:
            assert parameters["objectTypeKey"]["required"]
        if name == "coverage":
            assert "parentObjectId" in parameters
            state_schema = parameters["state"]["schema"]
            state_values = next(row["enum"] for row in state_schema["anyOf"] if "enum" in row)
            assert state_values == ["mapped", "unmapped", "ambiguous"]
        if name == "targets":
            assert (
                parameters["sourceObjectId"]["required"]
                and parameters["mappingVersion"]["required"]
            )

    mappings_path = "/api/v1/workspaces/{workspace_key}/mappings"
    # H4c (D-1): the edge list is published once, as /relations; /mappings keeps only the PUT.
    assert set(paths[mappings_path]) == {"put"}
    list_op = paths["/api/v1/workspaces/{workspace_key}/relations"]["get"]
    assert list_op["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MappingListPage"
    }
    list_params = {row["name"]: row for row in list_op["parameters"]}
    for key in (
        "applicationKey",
        "viewKey",
        "relationTypeKey",
        "fromObjectTypeKey",
        "toObjectTypeKey",
        "direction",
        "changeSetId",
        "publicationId",
    ):
        assert key in list_params
        assert not list_params[key].get("required", False)


def test_build07_wp6_openapi_selected_model_contract():
    schema = app.openapi()
    endpoint = schema["paths"]["/api/v1/change-sets/{change_set_id}/model-release"]
    assert set(endpoint) == {"patch"}
    models = schema["components"]["schemas"]
    assert set(models["ChangeSetModelReleaseUpdate"]["required"]) == {
        "modelReleaseId",
        "expectedChangeSetVersion",
    }
    assert "modelReleaseId" in models["ChangeSetCreate"]["properties"]
    assert {"modelReleaseId", "modelReleaseKey", "modelReleaseVersion"} <= set(
        models["ChangeSetResponse"]["required"]
    )
    for path in ("/api/v1/model", "/api/v1/applications", "/api/v1/attribute-types"):
        names = {item["name"] for item in schema["paths"][path]["get"]["parameters"]}
        assert {"changeSetId", "publicationId"} <= names


# The routes that need no token (0.12 D245); every other operation the document lists needs one.
OPEN_OPERATIONS = {
    ("get", "/health"),
    ("get", "/health/live"),
    ("get", "/.well-known/oauth-authorization-server"),
    ("get", "/oauth/jwks"),
    ("post", "/oauth/token"),
    ("post", "/oauth/revoke"),
}


def test_0_12_i1_every_operation_but_the_open_ones_refuses_a_call_without_a_token(monkeypatch):
    """With every capability on, each operation of the document, called with no token, answers
    `401 AUTHENTICATION_REQUIRED` before anything else is read (ADR-043: no route is left open)."""
    for flag in (
        "MODEL_ADMIN_MUTATIONS_ENABLED",
        "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        "INTEGRATION_JOBS_ENABLED",
        "CONSUMER_SUBSCRIPTIONS_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    application = create_app()
    schema = application.openapi()
    anonymous = TestClient(application, authenticated=False)
    checked = 0
    for path, operations in schema["paths"].items():
        for method in operations:
            if method == "parameters" or (method, path) in OPEN_OPERATIONS:
                continue
            assert operations[method]["security"] == [{"engineOAuth": []}], (method, path)
            response = anonymous.request(method, path.replace("{", "x").replace("}", "x"))
            assert response.status_code == 401, (method, path, response.text)
            assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
            checked += 1
    assert checked > 150


# Where a declared workspace comes from, and the path parameter it needs (0.12 Z1, D277).
_SCOPE_PARAMETERS = {
    "the path's workspace": "{workspace_key}",
    "the change set's workspace": "{change_set_id}",
    "the publication's workspace": "{publication_id}",
    "the subscription's workspace": "{subscription_id}",
    "the job's workspace and kind": "{job_id}",
    "the change set, or the record's workspace": "{object_id}",
    "the query's context, or the record's workspace": "{object_id}",
    "the change set, or the relationship's workspace": "{relation_id}",
    "the query's context, or the relationship's workspace": "{relation_id}",
    "the change set, or the path's workspace": "{workspace_key}",
}


def test_0_12_z1_every_operation_declares_its_action(monkeypatch):
    """With every capability on, each operation but the open ones declares an action of the
    catalogue, the groups allowing it and where its workspace comes from, and a declaration that
    reads a path parameter is on a route that has it (ADR-044, D256, D277)."""
    from app.engine.authorization.catalogue import ACTIONS

    for flag in (
        "MODEL_ADMIN_MUTATIONS_ENABLED",
        "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        "INTEGRATION_JOBS_ENABLED",
        "CONSUMER_SUBSCRIPTIONS_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    schema = create_app().openapi()
    declared = set()
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method == "parameters" or (method, path) in OPEN_OPERATIONS:
                continue
            action = operation.get("x-action")
            assert action in ACTIONS, (method, path, action)
            assert operation["x-action-groups"] == list(ACTIONS[action].groups), (method, path)
            needed = _SCOPE_PARAMETERS.get(operation["x-action-scope"])
            assert needed is None or needed in path, (method, path, operation["x-action-scope"])
            declared.add(action)
    assert declared == set(ACTIONS)
