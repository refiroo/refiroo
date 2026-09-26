from uuid import uuid4

from test_api import ChangeSetTestClient

from app.main import app

TestClient = ChangeSetTestClient


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _create(client: TestClient, object_type: str, name: str, attributes, **extra):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": extra.pop("applicationKey", "rdm-translations"),
            "objectTypeKey": object_type,
            "name": name,
            "attributes": attributes,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _language_and_group(client: TestClient, suffix: str):
    language = _create(
        client,
        "language",
        f"Language {suffix}",
        [_attr("language-code", f"L_{suffix}")],
    )
    group = _create(
        client,
        "translation-group",
        f"Group {suffix}",
        [_attr("group-code", f"G_{suffix}")],
        parentObjectId=language["id"],
    )
    return language, group


def _domain(client: TestClient, suffix: str):
    return _create(
        client,
        "domain",
        f"Domain {suffix}",
        [_attr("domain-code", f"D_{suffix}")],
        applicationKey="rdm-master",
    )


def _master_targets(client: TestClient, suffix: str):
    domain = _domain(client, suffix)
    codelist = _create(
        client,
        "codelist",
        f"Codelist {suffix}",
        [_attr("codelist-code", f"C_{suffix}")],
        applicationKey="rdm-master",
        parentObjectId=domain["id"],
    )
    master_value = _create(
        client,
        "master-value",
        f"Master value {suffix}",
        [
            _attr("master-id", f"M_{suffix}"),
            _attr("value-code", f"V_{suffix}"),
            _attr("value-name", f"Value {suffix}"),
        ],
        applicationKey="rdm-master",
        parentObjectId=codelist["id"],
    )
    return domain, codelist, master_value


def _translation_payload(group_id: str, target_id: str, suffix: str, *, public_id=None):
    payload = {
        "applicationKey": "rdm-translations",
        "objectTypeKey": "translation",
        "parentObjectId": group_id,
        "name": f"Translation {suffix}",
        "attributes": [_attr("translated-value", f"Translated {suffix}")],
        "initialRelations": [
            {
                "relationTypeKey": "object-has-translation",
                "direction": "incoming",
                "otherObjectId": target_id,
            }
        ],
    }
    if public_id:
        payload["id"] = public_id
    return payload


def test_translation_is_created_with_containment_and_target_atomically():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        language, group = _language_and_group(client, suffix)
        domain = _domain(client, suffix)

        response = client.post(
            "/api/v1/objects",
            json=_translation_payload(group["id"], domain["id"], suffix),
        )
        assert response.status_code == 201, response.text
        translation = response.json()
        assert translation["parentObjectId"] == group["id"]
        assert [part["id"] for part in translation["path"]] == [
            language["id"],
            group["id"],
            translation["id"],
        ]
        values = {item["attributeTypeKey"]: item["value"] for item in translation["attributes"]}
        assert values["translated-value"] == f"Translated {suffix}"
        assert values["active"] is True

        relations = client.get("/api/v1/relations", params={"objectId": translation["id"]}).json()[
            "items"
        ]
        assert {(item["direction"], item["relation"]["relationTypeKey"]) for item in relations} == {
            ("incoming", "translation-group-contains-translation"),
            ("incoming", "object-has-translation"),
        }
        target = next(
            item
            for item in relations
            if item["relation"]["relationTypeKey"] == "object-has-translation"
        )
        assert target["object"]["id"] == domain["id"]


def test_domain_codelist_and_master_value_are_all_translation_targets():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _language, group = _language_and_group(client, suffix)
        targets = _master_targets(client, suffix)

        for index, target in enumerate(targets):
            response = client.post(
                "/api/v1/objects",
                json=_translation_payload(group["id"], target["id"], f"{suffix}_{index}"),
            )
            assert response.status_code == 201, response.text
            relation = next(
                item
                for item in client.get(
                    "/api/v1/relations", params={"objectId": response.json()["id"]}
                ).json()["items"]
                if item["relation"]["relationTypeKey"] == "object-has-translation"
            )
            assert relation["object"]["objectTypeKey"] == target["objectTypeKey"]


def test_translation_requires_content_and_a_target_without_leaving_an_orphan():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _language, group = _language_and_group(client, suffix)
        public_id = str(uuid4())

        empty = client.post(
            "/api/v1/objects",
            json={
                "id": public_id,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation",
                "parentObjectId": group["id"],
                "name": f"Empty {suffix}",
                "attributes": [],
            },
        )
        assert empty.status_code == 422
        assert empty.json()["error"]["code"] == "object_attribute_rule_violation"

        missing_target = client.post(
            "/api/v1/objects",
            json={
                "id": public_id,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation",
                "parentObjectId": group["id"],
                "name": f"Untargeted {suffix}",
                "attributes": [_attr("translated-name", "Localized")],
            },
        )
        assert missing_target.status_code == 422
        assert missing_target.json()["error"]["code"] == "missing_required_relations"
        assert client.get(f"/api/v1/objects/translation/{public_id}").status_code == 404


def test_target_and_language_combination_is_unique_and_failed_create_rolls_back():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _language, group = _language_and_group(client, suffix)
        domain = _domain(client, suffix)
        first = client.post(
            "/api/v1/objects",
            json=_translation_payload(group["id"], domain["id"], f"{suffix}_1"),
        )
        assert first.status_code == 201

        duplicate_id = str(uuid4())
        duplicate = client.post(
            "/api/v1/objects",
            json=_translation_payload(
                group["id"], domain["id"], f"{suffix}_2", public_id=duplicate_id
            ),
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "duplicate_relation_scope"
        assert client.get(f"/api/v1/objects/translation/{duplicate_id}").status_code == 404

        deactivated = client.patch(
            f"/api/v1/objects/translation/{first.json()['id']}/attributes/active",
            json={"value": False, "expectedVersion": 1},
        )
        assert deactivated.status_code == 200
        historical_successor = client.post(
            "/api/v1/objects",
            json=_translation_payload(
                group["id"], domain["id"], f"{suffix}_2", public_id=duplicate_id
            ),
        )
        assert historical_successor.status_code == 201, historical_successor.text

        _other_language, other_group = _language_and_group(client, f"{suffix}_other")
        other_language = client.post(
            "/api/v1/objects",
            json=_translation_payload(other_group["id"], domain["id"], f"{suffix}_3"),
        )
        assert other_language.status_code == 201, other_language.text


def test_required_translation_target_cannot_be_unlinked_and_cascades_with_owner():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _language, group = _language_and_group(client, suffix)
        domain = _domain(client, suffix)
        translation = client.post(
            "/api/v1/objects",
            json=_translation_payload(group["id"], domain["id"], suffix),
        ).json()
        relations = client.get("/api/v1/relations", params={"objectId": translation["id"]}).json()[
            "items"
        ]
        target_relation = next(
            item["relation"]
            for item in relations
            if item["relation"]["relationTypeKey"] == "object-has-translation"
        )

        unlink = client.delete(
            f"/api/v1/relations/{target_relation['id']}", params={"expectedVersion": 1}
        )
        assert unlink.status_code == 422
        assert unlink.json()["error"]["code"] == "required_relation"

        preview = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
        )
        assert preview.status_code == 409
        assert any(
            item["id"] == translation["id"] and item["reason"] == "required-ownership"
            for item in preview.json()["error"]["details"]["objectsToRetire"]
        )

        deleted = client.delete(
            f"/api/v1/objects/domain/{domain['id']}",
            params={
                "expectedVersion": 1,
                "cascade": True,
                "deletionPreviewToken": preview.json()["error"]["details"]["deletionPreviewToken"],
            },
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/translation/{translation['id']}").status_code == 404
        assert client.get(f"/api/v1/objects/translation-group/{group['id']}").status_code == 200


def test_last_translation_content_attribute_cannot_be_removed():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _language, group = _language_and_group(client, suffix)
        domain = _domain(client, suffix)
        translation = client.post(
            "/api/v1/objects",
            json=_translation_payload(group["id"], domain["id"], suffix),
        ).json()

        removed = client.delete(
            f"/api/v1/objects/translation/{translation['id']}/attributes/translated-value",
            params={"expectedVersion": 1},
        )
        assert removed.status_code == 422
        assert removed.json()["error"]["code"] == "object_attribute_rule_violation"

        unchanged = client.get(f"/api/v1/objects/translation/{translation['id']}").json()
        assert unchanged["version"] == 1
        assert any(
            item["attributeTypeKey"] == "translated-value" for item in unchanged["attributes"]
        )


def test_reparenting_cannot_create_a_duplicate_target_language_translation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        _first_language, first_group = _language_and_group(client, f"{suffix}_first")
        _second_language, second_group = _language_and_group(client, f"{suffix}_second")
        domain = _domain(client, suffix)
        first = client.post(
            "/api/v1/objects",
            json=_translation_payload(first_group["id"], domain["id"], f"{suffix}_1"),
        )
        assert first.status_code == 201
        second = client.post(
            "/api/v1/objects",
            json=_translation_payload(second_group["id"], domain["id"], f"{suffix}_2"),
        ).json()

        moved = client.patch(
            f"/api/v1/objects/translation/{second['id']}",
            json={"parentObjectId": first_group["id"], "expectedVersion": 1},
        )
        assert moved.status_code == 409
        assert moved.json()["error"]["code"] == "duplicate_relation_scope"

        unchanged = client.get(f"/api/v1/objects/translation/{second['id']}").json()
        assert unchanged["version"] == 1
        assert unchanged["parentObjectId"] == second_group["id"]
