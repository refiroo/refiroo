import hashlib
import json

from app.main import app, create_app


def test_base_0_6_wp3_default_openapi_document_is_locked():
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))

    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "20b9e55a79da738eabe80d75853ddeeade0f7dcac2c6931da7823fc89c39e3e1"
    )


def test_base_0_6_wp3_default_openapi_path_and_method_inventory_is_locked():
    schema = app.openapi()

    actual = {
        path: frozenset(operation for operation in path_item if operation != "parameters")
        for path, path_item in schema["paths"].items()
    }

    assert actual == {
        "/health": frozenset({"get"}),
        "/api/v1/capabilities": frozenset({"get"}),
        "/api/v1/model": frozenset({"get"}),
        "/api/v1/model-runtime-state": frozenset({"get"}),
        "/api/v1/model-validations": frozenset({"post"}),
        "/api/v1/model-releases": frozenset({"get"}),
        "/api/v1/model-releases/{release_id}": frozenset({"get"}),
        "/api/v1/model-releases/{release_id}/diff": frozenset({"get"}),
        "/api/v1/applications": frozenset({"get"}),
        "/api/v1/applications/{application_key}": frozenset({"get"}),
        "/api/v1/attribute-types": frozenset({"get"}),
        "/api/v1/attribute-types/{attribute_type_key}": frozenset({"get"}),
        "/api/v1/object-types": frozenset({"get"}),
        "/api/v1/object-types/{object_type_key}": frozenset({"get"}),
        "/api/v1/relation-types": frozenset({"get"}),
        "/api/v1/relation-types/{relation_type_key}": frozenset({"get"}),
        "/api/v1/object-type-relations": frozenset({"get"}),
        "/api/v1/workspaces": frozenset({"get", "post"}),
        "/api/v1/workspaces/{workspace_key}": frozenset({"get", "patch"}),
        "/api/v1/workspace-runtime-state": frozenset({"get", "patch"}),
        "/api/v1/objects/{object_type_key}": frozenset({"get"}),
        "/api/v1/objects": frozenset({"post"}),
        "/api/v1/objects/{object_type_key}/{object_id}": frozenset({"delete", "get", "patch"}),
        "/api/v1/objects/{object_type_key}/{object_id}/history": frozenset({"get"}),
        "/api/v1/relations": frozenset({"get", "post"}),
        "/api/v1/relations/{relation_id}": frozenset({"delete", "get", "patch"}),
        "/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}": (
            frozenset({"delete", "get", "patch", "post"})
        ),
    }


def test_base_0_6_wp3_default_openapi_component_schema_inventory_is_locked():
    schema_names = set(app.openapi()["components"]["schemas"])

    assert schema_names == {
        "ApiErrorBody",
        "ApiErrorResponse",
        "AllowedObjectTypePair",
        "AuditEventPage",
        "AuditEventResponse",
        "ApplicationResponse",
        "AttributeBindingResponse",
        "AttributeInput",
        "AttributeOutput",
        "AttributeTypeResponse",
        "AttributeValueResponse",
        "AttributeValueWrite",
        "CapabilitiesResponse",
        "InitialRelationInput",
        "MetadataPage_ApplicationResponse_",
        "MetadataPage_AttributeTypeResponse_",
        "MetadataPage_ObjectTypeRelationResponse_",
        "MetadataPage_ObjectTypeResponse_",
        "MetadataPage_RelationTypeResponse_",
        "ModelAdminCapabilities",
        "ModelChangeResponse",
        "ModelCompatibilityResponse",
        "ModelDiagnosticResponse",
        "ModelDocumentRequest",
        "ModelReleaseDiffResponse",
        "ModelReleasePage",
        "ModelReleaseResponse",
        "ModelReleaseSummary",
        "ModelRuntimeStateResponse",
        "ModelValidationResponse",
        "ObjectCreate",
        "ObjectPage",
        "ObjectResponse",
        "ObjectTypeRelationResponse",
        "ObjectTypeResponse",
        "ObjectUpdate",
        "RelationCreate",
        "RelationExpansion",
        "RelationPage",
        "RelationResponse",
        "RelationTypeResponse",
        "RelationUpdate",
        "WorkspaceAdminCapabilities",
        "WorkspaceCreate",
        "WorkspacePage",
        "WorkspaceResponse",
        "WorkspaceRuntimeStateResponse",
        "WorkspaceRuntimeStateUpdate",
        "WorkspaceUpdate",
    }


def test_base_0_5_openapi_documents_bounded_pages_and_structured_errors():
    schema = app.openapi()

    relation_response = schema["paths"]["/api/v1/relations"]["get"]["responses"]
    assert relation_response["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RelationPage"
    }
    error_content = relation_response["default"]["content"]["application/json"]
    assert error_content["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert set(error_content["examples"]) == {
        "invalidCursor",
        "requestValidation",
        "versionConflict",
    }
    object_parameters = schema["paths"]["/api/v1/objects/{object_type_key}"]["get"][
        "parameters"
    ]
    assert any(item["name"] == "filter.<field>.<operator>" for item in object_parameters)


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
    assert frozenset(
        method
        for method in schema["paths"]["/api/v1/model-releases/{release_id}/activation"]
        if method != "parameters"
    ) == {"post"}
    assert {
        "ModelCompilationResponse",
        "ModelActivationRequest",
        "ModelDraftCreate",
        "ModelDraftPage",
        "ModelDraftResponse",
        "ModelDraftUpdate",
        "ModelDraftVersionRequest",
        "ModelRuntimeStateResponse",
    }.issubset(schema["components"]["schemas"])
