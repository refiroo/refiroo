import hashlib
import json

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
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "65d6de7e676e4835020fdc9a51b0c6771242e0054c25b2d80395acbae025aff1"
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
        name = schema["$ref"].rsplit("/", 1)[-1]
        properties = document["components"]["schemas"][name]["properties"]
        assert {"nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(properties)
        # S4R5: items first; totals are optional integers, omitted rather than null.
        assert next(iter(properties)) == "items", path
        assert {"totalCount", "startIndex"}.isdisjoint(document["components"]["schemas"][name]["required"])
        assert properties["totalCount"]["type"] == properties["startIndex"]["type"] == "integer"
    # 0.9 B1 added the job list and a job's outcomes; H4c removed GET /workspaces/{key}/mappings (D-1);
    # 0.9 J2 added the import profiles; 0.9 J3 an import's rows; 0.9 K6a what records hold.
    assert seekable <= paged and len(paged) == 29
    assert {
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}/items",
        "/api/v1/jobs/{job_id}/rows",
        "/api/v1/import-profiles",
        "/api/v1/relations/held",
    } <= paged
    objects = {item["name"] for item in document["paths"]["/api/v1/objects/{object_type_key}"]["get"]["parameters"]}
    relations = {item["name"] for item in document["paths"]["/api/v1/relations"]["get"]["parameters"]}
    assert "topLevel" in objects and {"search", "sort"} <= relations
    # 0.9 Q3: the model-aware query pages the same way, with its page selection in the body.
    query = document["paths"]["/api/v1/workspaces/{workspace_key}/queries/objects"]["post"]
    body = query["requestBody"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    assert {"cursor", "from", "position", "includeTotal", "pageSize"} <= set(
        document["components"]["schemas"][body]["properties"]
    )
    page = query["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    properties = document["components"]["schemas"][page]["properties"]
    assert next(iter(properties)) == "items"
    assert {"nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(properties)
    # 0.9 B1: an inline batch answers with the first page of its outcomes, continued on
    # GET /jobs/{id}/items.
    batch = document["paths"]["/api/v1/batches"]["post"]
    page = batch["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    properties = document["components"]["schemas"][page]["properties"]
    assert next(iter(properties)) == "items"
    assert {"job", "nextCursor", "prevCursor", "anchor", "totalCount", "startIndex"} <= set(properties)


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
            for old in ("workspace-draft", "workspace-revision", "/drafts", "/revisions", "/retirement")
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
    }


def test_base_0_9_c11_c12_enabled_openapi_exposes_the_subscriptions_api(monkeypatch):
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    schema = create_app().openapi()
    assert {
        path: frozenset(method for method in schema["paths"][path] if method != "parameters")
        for path in schema["paths"]
        if path.startswith("/api/v1/consumer-subscriptions")
    } == {
        "/api/v1/consumer-subscriptions": frozenset({"get", "post"}),
        "/api/v1/consumer-subscriptions/{subscription_id}": frozenset({"get", "patch", "delete"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/suspend": frozenset({"post"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/resume": frozenset({"post"}),
        # U5a: the delivery log.
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries": frozenset({"get"}),
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}": frozenset({"get"}),
        # U5a revision: resending an event by hand (C-D129).
        "/api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}/resend": frozenset({"post"}),
    }
    components = schema["components"]["schemas"]
    response = components["SubscriptionResponse"]
    assert "signingSecret" not in response["required"]
    # U5a: a subscription is named, on create and in every answer (C-D115).
    assert "name" in response["required"] and "name" in components["ConsumerSubscriptionCreate"]["required"]
    # C12: the delivery state, the reasons the dispatcher sets, and resume's reset (C-D108, C-D110).
    assert "delivery" in response["required"]
    assert set(components["SubscriptionDelivery"]["properties"]) == {"lastDeliveredAt", "pending"}
    assert set(components["DeliveryError"]["properties"]["kind"]["enum"]) == {
        "status", "redirect", "timeout", "connection", "tls", "address"
    }
    reasons = set(components["SubscriptionSuspension"]["properties"]["reason"]["enum"])
    assert {"DELIVERY_FAILED", "FILTER_MATCHES_NOTHING", "EVENTS_EXPIRED"} <= reasons
    assert "HOST_NOT_ALLOWED" not in reasons
    assert set(components["ConsumerSubscriptionResume"]["properties"]) == {"expectedVersion", "reset"}


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
        assert "changeSetId" in parameters and "publicationId" in parameters and "cursor" in parameters
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
