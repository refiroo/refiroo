import hashlib
import json

from app.main import app, create_app


def test_base_0_5_wp5_default_openapi_document_is_locked():
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))

    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "b6bd2f1b3d9c7af0d2b5982615dec987c7c464f5f128b2fc6dc1cc297e2909f6"
    )


def test_base_0_5_wp5_default_openapi_path_and_method_inventory_is_locked():
    schema = app.openapi()

    actual = {
        path: frozenset(operation for operation in path_item if operation != "parameters")
        for path, path_item in schema["paths"].items()
    }

    assert actual == {
        "/health": frozenset({"get"}),
        "/api/v1/capabilities": frozenset({"get"}),
        "/api/v1/model": frozenset({"get"}),
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
        "/api/v1/objects/{object_type_key}": frozenset({"get"}),
        "/api/v1/objects": frozenset({"post"}),
        "/api/v1/objects/{object_type_key}/{object_id}": frozenset(
            {"delete", "get", "patch"}
        ),
        "/api/v1/objects/{object_type_key}/{object_id}/history": frozenset({"get"}),
        "/api/v1/relations": frozenset({"get", "post"}),
        "/api/v1/relations/{relation_id}": frozenset({"delete", "get", "patch"}),
        "/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}": (
            frozenset({"delete", "get", "patch", "post"})
        ),
    }


def test_base_0_5_wp5_default_openapi_component_schema_inventory_is_locked():
    schema_names = set(app.openapi()["components"]["schemas"])

    assert schema_names == {
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
        "HTTPValidationError",
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
        "ValidationError",
    }


def test_base_0_5_wp5_enabled_openapi_exposes_guarded_activation(monkeypatch):
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
