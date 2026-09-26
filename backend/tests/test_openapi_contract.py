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
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "19d0f7a13f5c5ab4188aff6b35541388fdcaa8baad603a113e415556e38b82e4"
    )


def test_paging_openapi_inventory():
    """Base 0.8 S3: every cursor-paged collection pages both ways, by position and with totals."""
    document = app.openapi()
    seekable = {
        "/api/v1/objects/{object_type_key}",
        "/api/v1/relations",
        "/api/v1/workspaces/{workspace_key}/mapping-coverage",
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
    assert seekable <= paged and len(paged) == 17
    objects = {item["name"] for item in document["paths"]["/api/v1/objects/{object_type_key}"]["get"]["parameters"]}
    relations = {item["name"] for item in document["paths"]["/api/v1/relations"]["get"]["parameters"]}
    assert "topLevel" in objects and {"search", "sort"} <= relations


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
    assert set(paths["/api/v1/objects"]) == {"post"}
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
    assert methods("/api/v1/objects") == {"post"}
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
        "$ref": "#/components/schemas/ObjectPage"
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
    assert "get" in paths[mappings_path]
    list_op = paths[mappings_path]["get"]
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
