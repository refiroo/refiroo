from uuid import uuid4

from test_api import DraftTestClient as TestClient

from app.main import app


def _attribute(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _domain(client: TestClient, token: str, name: str, code: str, *, description=...):
    attributes = [_attribute("domain-code", f"{token}_{code}")]
    if description is not ...:
        attributes.append(_attribute("description", description))
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": name,
            "attributes": attributes,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_typed_text_boolean_null_and_unset_filters_are_distinct():
    token = f"WP3_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        explicit_null = _domain(client, token, "Connections", "A", description=None)
        unset = _domain(client, token, "station archive", "B")
        matching = client.get(
            "/api/v1/objects/domain",
            params={"filter.domain-code.startsWith": token.lower()},
        )
        assert matching.status_code == 200
        assert {item["id"] for item in matching.json()["items"]} == {
            explicit_null["id"],
            unset["id"],
        }

        exact_case = client.get(
            "/api/v1/objects/domain",
            params={"filter.domain-code.eq": f"{token.lower()}_A"},
        )
        assert exact_case.status_code == 200
        assert exact_case.json()["items"] == []

        null_page = client.get(
            "/api/v1/objects/domain",
            params={"filter.description.isNull": "true", "search": token},
        )
        unset_page = client.get(
            "/api/v1/objects/domain",
            params={"filter.description.isUnset": "true", "search": token},
        )
        assert [item["id"] for item in null_page.json()["items"]] == [explicit_null["id"]]
        assert [item["id"] for item in unset_page.json()["items"]] == [unset["id"]]


def test_repeated_equality_is_or_other_filters_are_and_and_values_are_typed():
    token = f"WP3_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        first = _domain(client, token, f"{token} First", "A")
        second = _domain(client, token, f"{token} Second", "B")
        _domain(client, token, f"{token} Third", "C")
        response = client.get(
            "/api/v1/objects/domain",
            params=[
                ("filter.domain-code.eq", f"{token}_A"),
                ("filter.domain-code.eq", f"{token}_B"),
                ("filter.active.eq", "true"),
            ],
        )
        assert response.status_code == 200
        assert {item["id"] for item in response.json()["items"]} == {first["id"], second["id"]}

        invalid = client.get(
            "/api/v1/objects/domain", params={"filter.active.eq": "not-a-boolean"}
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"] == {
            "code": "invalid_filter",
            "message": "Invalid boolean value for field 'active'",
            "details": {"path": "/query/filter.active.eq"},
        }


def test_attribute_sort_is_cursor_stable_nulls_last_and_bound_to_filters():
    token = f"WP3_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        expected = [
            _domain(client, token, f"{token} B", "B", description="Bravo"),
            _domain(client, token, f"{token} A", "A", description="Alpha"),
            _domain(client, token, f"{token} Null", "N", description=None),
            _domain(client, token, f"{token} Unset", "U"),
        ]
        seen: list[str] = []
        cursor = None
        while True:
            params = {"search": token, "sort": "-description", "pageSize": 1}
            if cursor:
                params["cursor"] = cursor
            response = client.get("/api/v1/objects/domain", params=params)
            assert response.status_code == 200, response.text
            page = response.json()
            seen.extend(item["id"] for item in page["items"])
            cursor = page["nextCursor"]
            if cursor is None:
                break
        assert seen[:2] == [expected[0]["id"], expected[1]["id"]]
        assert set(seen[2:]) == {expected[2]["id"], expected[3]["id"]}

        first = client.get(
            "/api/v1/objects/domain",
            params={"search": token, "sort": "domain-code", "pageSize": 1},
        ).json()
        mismatch = client.get(
            "/api/v1/objects/domain",
            params={
                "search": token,
                "sort": "domain-code",
                "filter.active.eq": "true",
                "pageSize": 1,
                "cursor": first["nextCursor"],
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "invalid_cursor"


def test_numeric_ranges_and_capability_errors_are_model_aware():
    token = f"WP3_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        domain = _domain(client, token, "Numeric fixture", "parent")
        parent = client.post("/api/v1/objects", json={
            "applicationKey": "rdm-master", "objectTypeKey": "codelist", "name": "Numbers",
            "parentObjectId": domain["id"],
            "attributes": [_attribute("codelist-code", f"{token}-numbers")],
        })
        assert parent.status_code == 201, parent.text
        created = []
        for number in (1, 5, 10):
            response = client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": "rdm-master",
                    "objectTypeKey": "master-value",
                    "parentObjectId": parent.json()["id"],
                    "name": f"{token} {number}",
                    "attributes": [
                        _attribute("master-id", f"{token}-master-{number}"),
                        _attribute("value-code", f"{token}-value-{number}"),
                        _attribute("value-name", f"{token} {number}"),
                        _attribute("sort-order", number),
                    ],
                },
            )
            assert response.status_code == 201, response.text
            created.append((number, response.json()["id"]))

        response = client.get(
            "/api/v1/objects/master-value",
            params={
                "search": token,
                "filter.sort-order.gte": "5",
                "filter.sort-order.lt": "10",
            },
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [dict(created)[5]]

        invalid_sort = client.get(
            "/api/v1/objects/master-value", params={"sort": "value-name"}
        )
        assert invalid_sort.status_code == 422
        assert invalid_sort.json()["error"]["code"] == "invalid_sort"
        assert invalid_sort.json()["error"]["details"] == {"path": "/query/sort"}
