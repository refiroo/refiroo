from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.errors import ApiError
from app.main import app
from app.models.database import AttributeValue
from app.models.schema import ObjectTypeAttributeDefinition
from app.services.attributes import (
    build_attribute_value_response,
    validate_deletable_attribute,
)
from app.services.model.loader import load_bootstrap_model
from app.services.objects import claim_object_version, load_object


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _attr_value(attributes: list, key: str):
    return next(a["value"] for a in attributes if a["attributeTypeKey"] == key)


def _suffix():
    return uuid4().hex[:8]


def _create_domain(client, suffix):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Domain {suffix}",
            "attributes": [_attr("domain-code", f"DOM_{suffix}")],
        },
    )
    assert response.status_code == 201
    return response.json()


def _path(object_id: str, attribute_type_key: str) -> str:
    return f"/api/v1/objects/domain/{object_id}/attributes/{attribute_type_key}"


# --- GET ---


def test_get_attribute_value_returns_stored_value():
    with TestClient(app) as client:
        suffix = _suffix()
        domain = _create_domain(client, suffix)
        response = client.get(_path(domain["id"], "domain-code"))
        assert response.status_code == 200
        body = response.json()
        assert body["attributeTypeKey"] == "domain-code"
        assert body["name"] == "Domain code"
        assert body["valueType"] == "text"
        assert body["value"] == f"DOM_{suffix}"
        assert body["id"]
        assert body["objectVersion"] == domain["version"]


def test_get_attribute_value_returns_404_when_unset():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.get(_path(domain["id"], "description"))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "attribute_not_found"


def test_get_attribute_value_unknown_object_or_type():
    with TestClient(app) as client:
        missing_object = client.get(_path(str(uuid4()), "description"))
        assert missing_object.status_code == 404
        assert missing_object.json()["error"]["code"] == "object_not_found"

        missing_type = client.get(f"/api/v1/objects/nonexistent/{uuid4()}/attributes/description")
        assert missing_type.status_code == 404
        assert missing_type.json()["error"]["code"] == "unknown_object_type"


# --- POST ---


def test_create_attribute_value_on_unset_optional_attribute():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.post(
            _path(domain["id"], "description"),
            json={"value": "About reference data", "expectedVersion": 1},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["version"] == 2
        assert _attr_value(body["attributes"], "description") == "About reference data"

        get_response = client.get(_path(domain["id"], "description"))
        assert get_response.status_code == 200
        assert get_response.json()["value"] == "About reference data"
        assert get_response.json()["valueType"] == "longText"
        assert get_response.json()["objectVersion"] == body["version"]


def test_create_attribute_value_rejects_already_set_attribute():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        first = client.post(
            _path(domain["id"], "description"),
            json={"value": "First", "expectedVersion": 1},
        )
        assert first.status_code == 201

        second = client.post(
            _path(domain["id"], "description"),
            json={"value": "Second", "expectedVersion": 2},
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "attribute_already_exists"


def test_create_attribute_value_rejects_stale_version():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.post(
            _path(domain["id"], "description"),
            json={"value": "Stale", "expectedVersion": 99},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "version_conflict"


def test_create_attribute_value_rejects_unattached_key():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.post(
            _path(domain["id"], "hierarchical"),
            json={"value": True, "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unknown_attributes"


def test_create_attribute_value_rejects_invalid_value():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.post(
            _path(domain["id"], "description"),
            json={"value": 123, "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_attribute_value"


def test_create_attribute_value_rejects_extra_fields():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.post(
            _path(domain["id"], "description"),
            json={"value": "x", "expectedVersion": 1, "unexpected": "field"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "request_validation_error"


# --- PATCH ---


def test_update_attribute_value_updates_and_bumps_version():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        created = client.post(
            _path(domain["id"], "description"),
            json={"value": "Before", "expectedVersion": 1},
        )
        assert created.status_code == 201

        response = client.patch(
            _path(domain["id"], "description"),
            json={"value": "After", "expectedVersion": 2},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == 3
        assert _attr_value(body["attributes"], "description") == "After"

        get_response = client.get(_path(domain["id"], "description"))
        assert get_response.json()["value"] == "After"


def test_update_attribute_value_returns_404_when_unset():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.patch(
            _path(domain["id"], "description"),
            json={"value": "New", "expectedVersion": 1},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "attribute_not_found"


def test_update_attribute_value_rejects_invalid_value():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.patch(
            _path(domain["id"], "active"),
            json={"value": "not-a-boolean", "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_attribute_value"


def test_update_attribute_value_rejects_stale_version():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        created = client.post(
            _path(domain["id"], "description"),
            json={"value": "Before", "expectedVersion": 1},
        )
        assert created.status_code == 201

        stale = client.patch(
            _path(domain["id"], "description"),
            json={"value": "Stale", "expectedVersion": 1},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "version_conflict"


def test_version_claim_rejects_an_object_loaded_before_a_competing_write():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())

        with SessionLocal() as stale_session:
            stale_item = load_object(stale_session, domain["id"], "domain")
            stale_session.expunge(stale_item)

        with SessionLocal() as winning_session:
            winning_item = load_object(winning_session, domain["id"], "domain")
            claim_object_version(winning_session, winning_item, domain["version"])
            winning_session.commit()

        with SessionLocal() as losing_session:
            with pytest.raises(ApiError) as exc_info:
                claim_object_version(losing_session, stale_item, domain["version"])
            assert exc_info.value.code == "version_conflict"


def test_update_unique_attribute_conflicts_across_objects():
    with TestClient(app) as client:
        first = _create_domain(client, _suffix())
        second = _create_domain(client, _suffix())
        first_code = _attr_value(first["attributes"], "domain-code")

        conflict = client.patch(
            _path(second["id"], "domain-code"),
            json={"value": first_code, "expectedVersion": 1},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "duplicate_attribute_value"


# --- DELETE ---


def test_delete_optional_attribute_value():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        # `active` is auto-defaulted to true at create time, so a stored row exists.
        assert _attr_value(domain["attributes"], "active") is True

        response = client.delete(_path(domain["id"], "active"), params={"expectedVersion": 1})
        assert response.status_code == 204

        get_response = client.get(_path(domain["id"], "active"))
        assert get_response.status_code == 404
        assert get_response.json()["error"]["code"] == "attribute_not_found"


def test_delete_required_attribute_value_is_rejected():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.delete(_path(domain["id"], "domain-code"), params={"expectedVersion": 1})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "cannot_delete_required_attribute"


def test_delete_attribute_value_rejects_stale_version():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.delete(_path(domain["id"], "active"), params={"expectedVersion": 99})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "version_conflict"


def test_delete_attribute_value_returns_404_when_unset():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        response = client.delete(_path(domain["id"], "description"), params={"expectedVersion": 1})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "attribute_not_found"


# --- service-level guards ---


def test_validate_deletable_attribute_rejects_read_only_binding():
    model = load_bootstrap_model()
    domain = model.object_type("domain")
    read_only = domain.model_copy(
        update={
            "attributes": [
                ObjectTypeAttributeDefinition(
                    attributeTypeKey="domain-code", required=True, readOnly=True
                )
            ]
        }
    )
    with pytest.raises(ApiError) as exc_info:
        validate_deletable_attribute(read_only, "domain-code")
    assert exc_info.value.code == "read_only_attributes"


def test_build_attribute_value_response_uses_row_value():
    model = load_bootstrap_model()
    row = AttributeValue(
        id=str(uuid4()),
        attribute_type_key="description",
        value_type="longText",
        text_value="hello",
    )
    response = build_attribute_value_response(model, row, object_version=7)
    assert response.attributeTypeKey == "description"
    assert response.name == "Description"
    assert response.valueType == "longText"
    assert response.value == "hello"
    assert response.id == row.id
    assert response.objectVersion == 7
