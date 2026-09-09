from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class DraftTestClient(TestClient):
    """Exercise the legacy generic CRUD assertions through one explicit draft context."""

    draft_id: str
    draft_version: int

    def __enter__(self):
        client = super().__enter__()
        draft = super().request("POST", "/api/v1/workspaces/default/drafts", json={})
        assert draft.status_code == 201, draft.text
        self.draft_id = draft.json()["id"]
        self.draft_version = draft.json()["version"]
        return client

    def request(self, method, url, **kwargs):
        is_runtime_route = url.startswith(("/api/v1/objects", "/api/v1/relations"))
        if not is_runtime_route:
            return super().request(method, url, **kwargs)
        if method.upper() in {"POST", "PATCH"}:
            payload = dict(kwargs.get("json") or {})
            payload.setdefault("workspaceDraftId", self.draft_id)
            payload.setdefault("expectedWorkspaceDraftVersion", self.draft_version)
            kwargs["json"] = payload
        else:
            supplied = kwargs.get("params") or {}
            if isinstance(supplied, list):
                params = list(supplied)
                keys = {key for key, _value in params}
                if "workspaceDraftId" not in keys:
                    params.append(("workspaceDraftId", self.draft_id))
            else:
                params = dict(supplied)
                params.setdefault("workspaceDraftId", self.draft_id)
            if method.upper() == "DELETE":
                if isinstance(params, list):
                    if not any(key == "expectedWorkspaceDraftVersion" for key, _value in params):
                        params.append(("expectedWorkspaceDraftVersion", self.draft_version))
                else:
                    params.setdefault("expectedWorkspaceDraftVersion", self.draft_version)
            kwargs["params"] = params
        response = super().request(method, url, **kwargs)
        if response.is_success:
            version = response.json().get("workspaceDraftVersion") if response.content else None
            if version is not None:
                self.draft_version = version
            elif method.upper() == "DELETE":
                self.draft_version += 1
        return response


TestClient = DraftTestClient


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _attr_value(attributes: list, key: str):
    return next(a["value"] for a in attributes if a["attributeTypeKey"] == key)


def test_create_object_with_provided_id():
    with TestClient(app) as client:
        custom_id = str(uuid4())
        response = client.post(
            "/api/v1/objects",
            json={
                "id": custom_id,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Domain with custom ID",
                "attributes": [_attr("domain-code", "CUSTOM_ID_TEST")],
            },
        )
        assert response.status_code == 201
        assert response.json()["id"] == custom_id

        get_response = client.get(f"/api/v1/objects/domain/{custom_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == custom_id


def test_create_object_with_duplicate_id_is_rejected():
    with TestClient(app) as client:
        custom_id = str(uuid4())
        first = client.post(
            "/api/v1/objects",
            json={
                "id": custom_id,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "First domain",
                "attributes": [_attr("domain-code", "DUP_TEST_1")],
            },
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/objects",
            json={
                "id": custom_id,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Second domain",
                "attributes": [_attr("domain-code", "DUP_TEST_2")],
            },
        )
        assert second.status_code == 409
        body = second.json()
        assert body["error"]["code"] == "object_already_exists"
        assert custom_id in body["error"]["message"]


def test_create_object_without_id_generates_one():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Domain without explicit ID",
                "attributes": [_attr("domain-code", "NO_ID_TEST")],
            },
        )
        assert response.status_code == 201
        assert response.json()["id"]


def test_create_object_rejects_extra_fields():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Should be rejected",
                "attributes": [_attr("domain-code", "EXTRA_FIELDS")],
                "version": 1,
                "createdAt": "2026-09-02T19:59:45",
                "path": [{"id": "fake", "name": "fake", "objectTypeKey": "domain"}],
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "request_validation_error"


def test_create_object_rejects_invalid_id_and_duplicate_attributes():
    with TestClient(app) as client:
        invalid_id = client.post(
            "/api/v1/objects",
            json={
                "id": "not-a-uuid",
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Invalid ID",
                "attributes": [_attr("domain-code", "INVALID_ID")],
            },
        )
        assert invalid_id.status_code == 422
        assert invalid_id.json()["error"]["code"] == "request_validation_error"

        duplicate_attribute = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Duplicate attribute",
                "attributes": [
                    _attr("domain-code", "FIRST"),
                    _attr("domain-code", "SECOND"),
                ],
            },
        )
        assert duplicate_attribute.status_code == 422
        assert duplicate_attribute.json()["error"]["code"] == "duplicate_attribute"


def test_error_response_format():
    with TestClient(app) as client:
        response = client.get("/api/v1/objects/nonexistent-type/some-id")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert body["error"]["code"] == "unknown_object_type"


def test_object_type_relations_compatibility_endpoint():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/object-type-relations",
            params={"fromObjectType": "domain", "toObjectType": "codelist"},
        )
        assert response.status_code == 200
        assert response.json()["items"] == [
            {
                "id": response.json()["items"][0]["id"],
                "relationTypeKey": "domain-contains-codelist",
                "fromObjectTypeKey": "domain",
                "toObjectTypeKey": "codelist",
                "cardinality": "one-to-many",
                "required": False,
                "attributeTypeKeys": [],
                "features": {},
            }
        ]
        assert response.json()["items"][0]["id"]
        assert response.json()["nextCursor"] is None


def test_metadata_collections_use_cursor_pagination():
    with TestClient(app) as client:
        first_page = client.get("/api/v1/attribute-types", params={"pageSize": 1})
        assert first_page.status_code == 200
        first_body = first_page.json()
        assert len(first_body["items"]) == 1
        assert first_body["nextCursor"] is not None

        second_page = client.get(
            "/api/v1/attribute-types",
            params={"pageSize": 1, "cursor": first_body["nextCursor"]},
        )
        assert second_page.status_code == 200
        second_body = second_page.json()
        assert len(second_body["items"]) == 1
        assert second_body["items"][0]["id"] != first_body["items"][0]["id"]


def test_metadata_collection_rejects_invalid_cursor():
    with TestClient(app) as client:
        response = client.get("/api/v1/object-types", params={"cursor": "not-a-cursor"})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_cursor"


def test_metadata_cursor_rejects_filter_reuse_and_tampering():
    with TestClient(app) as client:
        first_page = client.get("/api/v1/object-type-relations", params={"pageSize": 1})
        assert first_page.status_code == 200
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        reused = client.get(
            "/api/v1/object-type-relations",
            params={"fromObjectType": "domain", "cursor": cursor, "pageSize": 1},
        )
        assert reused.status_code == 422
        assert reused.json()["error"]["code"] == "invalid_cursor"

        replacement = "A" if cursor[-1] != "A" else "B"
        tampered = client.get(
            "/api/v1/object-type-relations",
            params={"cursor": cursor[:-1] + replacement, "pageSize": 1},
        )
        assert tampered.status_code == 422
        assert tampered.json()["error"]["code"] == "invalid_cursor"


def test_version_conflict_error_format():
    with TestClient(app) as client:
        create = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Conflict test domain",
                "attributes": [_attr("domain-code", "CONFLICT_FMT")],
            },
        )
        assert create.status_code == 201
        obj = create.json()

        stale = client.patch(
            f"/api/v1/objects/domain/{obj['id']}",
            json={"name": "Stale", "expectedVersion": 999},
        )
        assert stale.status_code == 409
        body = stale.json()
        assert body["error"]["code"] == "version_conflict"


def test_attribute_response_format():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Attr format test",
                "attributes": [_attr("domain-code", "ATTR_FMT")],
            },
        )
        assert response.status_code == 201
        attrs = response.json()["attributes"]
        assert isinstance(attrs, list)
        code_attr = next(a for a in attrs if a["attributeTypeKey"] == "domain-code")
        assert code_attr["value"] == "ATTR_FMT"
        assert code_attr["id"]
        assert "name" in code_attr
        assert "valueType" in code_attr


def test_model_object_hierarchy_and_relation_vertical_slice():
    with TestClient(app) as client:
        model_response = client.get("/api/v1/model")
        assert model_response.status_code == 200
        assert model_response.json()["schemaVersion"] == "0.5"
        assert model_response.json()["applications"][0]["details"][0]["panels"][0]["type"] == (
            "children"
        )

        suffix = uuid4().hex[:8]
        domain_response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Connections {suffix}",
                "attributes": [_attr("domain-code", f"CONNECTIONS_{suffix}")],
            },
        )
        assert domain_response.status_code == 201
        domain = domain_response.json()
        assert _attr_value(domain["attributes"], "active") is True

        codelist_response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Timetable type {suffix}",
                "attributes": [_attr("codelist-code", f"MOT_{suffix}")],
            },
        )
        assert codelist_response.status_code == 201
        codelist = codelist_response.json()
        assert codelist["parentObjectId"] == domain["id"]
        assert [part["name"] for part in codelist["path"]] == [
            domain["name"],
            codelist["name"],
        ]

        list_response = client.get(
            "/api/v1/objects/domain",
            params={"pageSize": 1, "applicationKey": "rdm-master"},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["items"]) == 1

        second_domain_response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Connections second {suffix}",
                "attributes": [_attr("domain-code", f"CONNECTIONS_SECOND_{suffix}")],
            },
        )
        assert second_domain_response.status_code == 201
        search_page = client.get(
            "/api/v1/objects/domain",
            params={
                "pageSize": 1,
                "applicationKey": "rdm-master",
                "search": suffix,
            },
        ).json()
        assert len(search_page["items"]) == 1
        assert search_page["nextCursor"] is not None
        next_search_page = client.get(
            "/api/v1/objects/domain",
            params={
                "pageSize": 1,
                "applicationKey": "rdm-master",
                "search": suffix,
                "cursor": search_page["nextCursor"],
            },
        ).json()
        assert len(next_search_page["items"]) == 1
        assert next_search_page["items"][0]["id"] != search_page["items"][0]["id"]

        relation_response = client.get("/api/v1/relations", params={"objectId": domain["id"]})
        assert relation_response.status_code == 200
        assert relation_response.json()["items"][0]["relation"]["relationTypeKey"] == (
            "domain-contains-codelist"
        )

        update_response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={
                "attributes": [_attr("description", "Updated")],
                "expectedVersion": 1,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["version"] == 2

        stale_response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"name": "Stale write", "expectedVersion": 1},
        )
        assert stale_response.status_code == 409
        assert stale_response.json()["error"]["code"] == "version_conflict"

        system_response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system",
                "name": f"System {suffix}",
                "attributes": [_attr("system-code", f"SYS_{suffix}")],
            },
        )
        assert system_response.status_code == 201
        system = system_response.json()
        delete_response = client.delete(
            f"/api/v1/objects/system/{system['id']}", params={"expectedVersion": 1}
        )
        assert delete_response.status_code == 204


def _create_domain(client, suffix):
    return client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Domain {suffix}",
            "attributes": [_attr("domain-code", f"DOM_{suffix}")],
        },
    ).json()


def test_delete_object_with_parent_cascades_parent_relation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        codelist = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Codelist {suffix}",
                "attributes": [_attr("codelist-code", f"CL_{suffix}")],
            },
        ).json()
        assert codelist["parentObjectId"] == domain["id"]

        response = client.delete(
            f"/api/v1/objects/codelist/{codelist['id']}", params={"expectedVersion": 1}
        )
        assert response.status_code == 204
        # The parent no longer has children and can now be deleted.
        assert (
            client.delete(
                f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
            ).status_code
            == 204
        )


def test_delete_object_with_children_is_rejected():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Codelist {suffix}",
                "attributes": [_attr("codelist-code", f"CL_{suffix}")],
            },
        )
        response = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "object_has_dependants"


def test_delete_object_with_mapping_relation_is_rejected():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        codelist = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Codelist {suffix}",
                "attributes": [_attr("codelist-code", f"CL_{suffix}")],
            },
        ).json()
        master = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "master-value",
                "parentObjectId": codelist["id"],
                "name": f"Master {suffix}",
                "attributes": [
                    _attr("master-id", f"MID_{suffix}"),
                    _attr("value-code", f"VC_{suffix}"),
                    _attr("value-name", f"Value {suffix}"),
                ],
            },
        ).json()
        system = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system",
                "name": f"System {suffix}",
                "attributes": [_attr("system-code", f"SYS_{suffix}")],
            },
        ).json()
        system_value = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system-value",
                "parentObjectId": system["id"],
                "name": f"System value {suffix}",
                "attributes": [
                    _attr("value-code", f"SVC_{suffix}"),
                    _attr("value-name", f"System value {suffix}"),
                ],
            },
        ).json()
        mapping = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": system_value["id"],
                "toObjectId": master["id"],
            },
        )
        assert mapping.status_code == 201

        response = client.delete(
            f"/api/v1/objects/master-value/{master['id']}", params={"expectedVersion": 1}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "object_has_dependants"
        # An association requires explicit cascade confirmation even without dependent objects.
        assert client.get(f"/api/v1/relations/{mapping.json()['id']}").status_code == 200
        assert client.get(f"/api/v1/objects/master-value/{master['id']}").status_code == 200


def test_update_cannot_null_required_attribute():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"attributes": [_attr("domain-code", None)], "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "missing_required_attributes"


def test_partial_update_without_required_attribute_succeeds():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"attributes": [_attr("description", "Updated")], "expectedVersion": 1},
        )
        assert response.status_code == 200
        assert response.json()["version"] == 2


def test_unique_attribute_enforced_on_create():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        code = f"UNIQ_{suffix}"
        first = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"First {suffix}",
                "attributes": [_attr("domain-code", code)],
            },
        )
        assert first.status_code == 201
        second = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Second {suffix}",
                "attributes": [_attr("domain-code", code)],
            },
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "duplicate_attribute_value"


def test_unique_attribute_enforced_on_update():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        first = _create_domain(client, f"{suffix}a")
        second = _create_domain(client, f"{suffix}b")
        first_code = next(
            a["value"] for a in first["attributes"] if a["attributeTypeKey"] == "domain-code"
        )

        conflict = client.patch(
            f"/api/v1/objects/domain/{second['id']}",
            json={"attributes": [_attr("domain-code", first_code)], "expectedVersion": 1},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "duplicate_attribute_value"

        # Re-submitting its own current value is not a conflict.
        unchanged = client.patch(
            f"/api/v1/objects/domain/{second['id']}",
            json={
                "attributes": [_attr("domain-code", f"DOM_{suffix}b")],
                "expectedVersion": 1,
            },
        )
        assert unchanged.status_code == 200


def test_unique_attribute_scope_is_per_attribute_type():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        # A different attribute type may reuse the same value without conflict.
        codelist = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Codelist {suffix}",
                "attributes": [_attr("codelist-code", f"DOM_{suffix}")],
            },
        )
        assert codelist.status_code == 201


def test_integer_minimum_is_enforced():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        domain = _create_domain(client, suffix)
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": domain["id"],
                "name": f"Codelist {suffix}",
                "attributes": [
                    _attr("codelist-code", f"CL_{suffix}"),
                    _attr("maximum-hierarchy-depth", 0),
                ],
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "attribute_below_minimum"


def test_create_rejects_invalid_parent_object_id():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": "not-a-uuid",
                "name": "Invalid parent",
                "attributes": [_attr("codelist-code", "INV_PARENT")],
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "request_validation_error"


def test_relation_rejects_invalid_object_ids():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": "not-a-uuid",
                "toObjectId": "not-a-uuid",
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "request_validation_error"
