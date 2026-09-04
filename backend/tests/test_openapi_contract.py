import hashlib
import json

from app.main import app


def test_base_0_5_wp1_complete_openapi_document_is_locked():
    canonical_schema = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":"))

    assert hashlib.sha256(canonical_schema.encode()).hexdigest() == (
        "254a689b5599f30832e1fb5a53dca49dad5bcf890575665d35b84c4a42c2cff4"
    )


def test_base_0_5_wp1_openapi_path_and_method_inventory_is_locked():
    schema = app.openapi()

    actual = {
        path: frozenset(operation for operation in path_item if operation != "parameters")
        for path, path_item in schema["paths"].items()
    }

    assert actual == {
        "/health": frozenset({"get"}),
        "/api/v1/model": frozenset({"get"}),
        "/api/v1/model-releases": frozenset({"get"}),
        "/api/v1/model-releases/{release_id}": frozenset({"get"}),
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
        "/api/v1/relations": frozenset({"get", "post"}),
        "/api/v1/relations/{relation_id}": frozenset({"delete", "get", "patch"}),
        "/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}": (
            frozenset({"delete", "get", "patch", "post"})
        ),
    }


def test_base_0_5_wp1_openapi_component_schema_inventory_is_locked():
    schema_names = set(app.openapi()["components"]["schemas"])

    assert schema_names == {
        "AllowedObjectTypePair",
        "ApplicationResponse",
        "AttributeBindingResponse",
        "AttributeInput",
        "AttributeOutput",
        "AttributeTypeResponse",
        "AttributeValueResponse",
        "AttributeValueWrite",
        "HTTPValidationError",
        "InitialRelationInput",
        "MetadataPage_ApplicationResponse_",
        "MetadataPage_AttributeTypeResponse_",
        "MetadataPage_ObjectTypeRelationResponse_",
        "MetadataPage_ObjectTypeResponse_",
        "MetadataPage_RelationTypeResponse_",
        "ModelReleasePage",
        "ModelReleaseResponse",
        "ModelReleaseSummary",
        "ObjectCreate",
        "ObjectPage",
        "ObjectResponse",
        "ObjectTypeRelationResponse",
        "ObjectTypeResponse",
        "ObjectUpdate",
        "RelationCreate",
        "RelationExpansion",
        "RelationResponse",
        "RelationTypeResponse",
        "RelationUpdate",
        "ValidationError",
    }
