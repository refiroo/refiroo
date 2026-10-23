import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from harness_identity import TestClient as LiveTestClient
from test_api import ChangeSetTestClient as TestClient

from app.common.time import as_utc
from app.config import reload_settings
from app.db import get_engine
from app.engine.model.registry import model_registry
from app.main import app, create_app


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
            "code": "INVALID_FILTER",
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
        assert mismatch.json()["error"]["code"] == "INVALID_CURSOR"


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

        for sort, expected in (("sort-order", [1, 5, 10]), ("-sort-order", [10, 5, 1])):
            seen, cursor = [], None
            while True:
                page = client.get("/api/v1/objects/master-value", params={
                    "search": token, "sort": sort, "pageSize": 1,
                    **({"cursor": cursor} if cursor else {}),
                })
                assert page.status_code == 200, page.text
                seen += [item["id"] for item in page.json()["items"]]
                cursor = page.json()["nextCursor"]
                if cursor is None:
                    break
            assert seen == [dict(created)[number] for number in expected]

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

        # Every scalar attribute sorts, whether or not its type is flagged sortable.
        by_value_name = client.get(
            "/api/v1/objects/master-value", params={"search": token, "sort": "value-name"}
        )
        assert by_value_name.status_code == 200, by_value_name.text
        # A field the type does not have is still refused at the parameter.
        invalid_sort = client.get(
            "/api/v1/objects/master-value", params={"sort": "translated-name"}
        )
        assert invalid_sort.status_code == 422
        assert invalid_sort.json()["error"]["code"] == "INVALID_SORT"
        assert invalid_sort.json()["error"]["details"] == {"path": "/query/sort"}


@pytest.mark.parametrize(
    "context",
    [
        "live",
        "change_set",
    ],
)
def test_date_values_keep_their_type_through_write_filter_and_sort(context):
    token = f"WP13_{uuid4().hex[:8]}"
    client_type, scope = (
        (LiveTestClient, {"workspaceKey": "default"}) if context == "live" else (TestClient, {})
    )
    with client_type(app) as client:
        def create(type_key: str, name: str, parent: str | None, attributes):
            return client.post("/api/v1/objects", json={
                "applicationKey": "rdm-master", "objectTypeKey": type_key, "name": name,
                "parentObjectId": parent, "attributes": attributes, **scope,
            })

        domain = create("domain", f"{token} domain", None, [_attribute("domain-code", token)])
        assert domain.status_code == 201, domain.text
        codelist = create("codelist", f"{token} dates", domain.json()["id"], [
            _attribute("codelist-code", f"{token}-dates"),
        ])
        assert codelist.status_code == 201, codelist.text

        def value(label: str, valid_from):
            return create("master-value", f"{token} {label}", codelist.json()["id"], [
                _attribute("master-id", f"{token}-master-{label}"),
                _attribute("value-code", f"{token}-value-{label}"),
                _attribute("value-name", f"{token} {label}"),
                _attribute("valid-from", valid_from),
            ])

        ids = {}
        for label, date in (("late", "2027-01-01"), ("boundary", "2026-07-01"), ("early", "2025-12-31")):
            response = value(label, date)
            assert response.status_code == 201, response.text
            stored = next(
                item for item in response.json()["attributes"]
                if item["attributeTypeKey"] == "valid-from"
            )
            assert stored["value"] == date
            ids[label] = response.json()["id"]

        for index, invalid in enumerate(("2026-02-30", "01/07/2026", 20260701)):
            refused = value(f"invalid-{index}", invalid)
            assert refused.status_code == 422
            assert refused.json()["error"]["code"] == "INVALID_ATTRIBUTE_VALUE"

        def listed(**params):
            response = client.get(
                "/api/v1/objects/master-value", params={"search": token, **params}
            )
            assert response.status_code == 200, response.text
            return [item["id"] for item in response.json()["items"]]

        assert set(listed()) == set(ids.values())
        assert listed(**{"filter.valid-from.gte": "2026-07-01", "sort": "valid-from"}) == [
            ids["boundary"], ids["late"],
        ]
        assert listed(**{"filter.valid-from.lt": "2026-07-01"}) == [ids["early"]]
        assert listed(sort="-valid-from") == [ids["late"], ids["boundary"], ids["early"]]

        invalid_filter = client.get("/api/v1/objects/master-value", params={
            "filter.valid-from.gte": "July 2026",
        })
        assert invalid_filter.status_code == 422
        assert invalid_filter.json()["error"]["code"] == "INVALID_FILTER"
        assert invalid_filter.json()["error"]["details"] == {
            "path": "/query/filter.valid-from.gte"
        }


@pytest.fixture
def typed_model_client(tmp_path, monkeypatch, migrated_database):
    """Starter model plus decimal and dateTime fields on domains, which the starter lacks."""
    model = json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
    queryable = {"filterable": True, "sortable": True}
    model["attributeTypes"] += [
        {"key": "wp10-amount", "name": "Amount", "valueType": "decimal", "features": queryable},
        {"key": "wp10-seen-at", "name": "Seen at", "valueType": "dateTime", "features": queryable},
        {"key": "wp10-due", "name": "Due", "valueType": "date", "features": queryable},
    ]
    domain = next(item for item in model["objectTypes"] if item["key"] == "domain")
    domain["attributes"] += [
        {"attributeTypeKey": key, "order": 100 + index}
        for index, key in enumerate(("wp10-amount", "wp10-seen-at", "wp10-due"))
    ]
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", migrated_database("typed.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    reload_settings()
    model_registry.clear()
    with LiveTestClient(create_app()) as client:
        yield client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def test_change_set_writes_keep_decimal_datetime_and_date_values_through_activation(typed_model_client):
    client = typed_model_client
    change_set = client.post("/api/v1/workspaces/default/change-sets", json={})
    assert change_set.status_code == 201, change_set.text
    change_set = change_set.json()
    context = {"changeSetId": change_set["id"]}

    def values(body):
        return {
            item["attributeTypeKey"]: item["value"]
            for item in body["attributes"]
            if item["attributeTypeKey"].startswith("wp10-")
        }

    created = client.post("/api/v1/objects", json={
        "applicationKey": "rdm-master", "objectTypeKey": "domain", "name": "Typed",
        "attributes": [
            _attribute("domain-code", "TYPED"),
            _attribute("wp10-amount", "12.50"),
            _attribute("wp10-seen-at", "2026-09-24T10:15:00+00:00"),
            _attribute("wp10-due", "2026-10-01"),
        ],
        **context, "expectedChangeSetVersion": change_set["version"],
    })
    assert created.status_code == 201, created.text
    # One canonical form in every context: trailing zeros dropped, instants in UTC with an offset.
    assert values(created.json()) == {
        "wp10-amount": "12.5",
        "wp10-seen-at": "2026-09-24T10:15:00+00:00",
        "wp10-due": "2026-10-01",
    }
    record = created.json()

    updated = client.patch(f"/api/v1/objects/domain/{record['id']}", json={
        "attributes": [_attribute("wp10-amount", 7), _attribute("wp10-due", "2026-11-30")],
        "expectedVersion": record["version"],
        **context, "expectedChangeSetVersion": record["changeSetVersion"],
    })
    assert updated.status_code == 200, updated.text
    assert values(updated.json())["wp10-amount"] == "7"
    record = updated.json()

    field = client.patch(
        f"/api/v1/objects/domain/{record['id']}/attributes/wp10-seen-at",
        json={
            "value": "2026-12-24T18:00:00+01:00",
            "expectedVersion": record["version"],
            **context, "expectedChangeSetVersion": record["changeSetVersion"],
        },
    )
    assert field.status_code == 200, field.text
    record = field.json()
    for key, invalid in (("wp10-amount", "twelve"), ("wp10-seen-at", "noon"), ("wp10-due", "2026-02-30")):
        refused = client.patch(
            f"/api/v1/objects/domain/{record['id']}/attributes/{key}",
            json={
                "value": invalid,
                "expectedVersion": record["version"],
                **context, "expectedChangeSetVersion": record["changeSetVersion"],
            },
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["error"]["code"] == "INVALID_ATTRIBUTE_VALUE"

    expected = {
        "wp10-amount": "7",
        "wp10-seen-at": "2026-12-24T17:00:00+00:00",
        "wp10-due": "2026-11-30",
    }
    change_set_read = client.get(f"/api/v1/objects/domain/{record['id']}", params=context)
    assert values(change_set_read.json()) == expected
    # Change sets record no timestamps (WP-10K): report them as absent, never as the current time.
    assert change_set_read.json()["createdAt"] is None and change_set_read.json()["updatedAt"] is None
    for params, found in (
        ({"filter.wp10-amount.gt": "6.5"}, True),
        ({"filter.wp10-amount.gt": "10"}, False),
        ({"filter.wp10-due.lte": "2026-11-30"}, True),
        ({"filter.wp10-seen-at.gte": "2026-12-24T17:00:00+00:00"}, True),
        ({"filter.wp10-seen-at.gt": "2026-12-24T17:00:00+00:00"}, False),
        ({"filter.wp10-seen-at.lt": "2026-12-25T00:00:00"}, True),
        ({"sort": "-wp10-amount"}, True),
        ({"sort": "wp10-seen-at"}, True),
    ):
        listed = client.get("/api/v1/objects/domain", params={**context, **params})
        assert listed.status_code == 200, (params, listed.text)
        assert (record["id"] in [item["id"] for item in listed.json()["items"]]) is found, params
    # Built-in timestamps are not recorded in a change set: a query on them is refused, not matched empty.
    for params, code, message in (
        ({"filter.createdAt.gte": "2000-01-01T00:00:00"}, "INVALID_FILTER", "Created"),
        ({"filter.updatedAt.lt": "2000-01-01T00:00:00+02:00"}, "INVALID_FILTER", "Updated"),
        ({"sort": "-updatedAt"}, "INVALID_SORT", "Updated"),
    ):
        listed = client.get("/api/v1/objects/domain", params={**context, **params})
        assert listed.status_code == 422, (params, listed.text)
        assert listed.json()["error"]["code"] == code
        assert listed.json()["error"]["message"] == f"{message} is not recorded in change sets or publications"

    activated = client.post(
        f"/api/v1/change-sets/{change_set['id']}/publication",
        json={"expectedChangeSetVersion": record["changeSetVersion"]},
    )
    assert activated.status_code == 200, activated.text
    live = client.get(
        f"/api/v1/objects/domain/{record['id']}", params={"workspaceKey": "default"}
    )
    assert live.status_code == 200, live.text
    assert values(live.json()) == expected


def test_live_datetime_keeps_its_instant(typed_model_client):
    written = "2026-12-24T18:00:00+01:00"
    created = typed_model_client.post("/api/v1/objects", json={
        "applicationKey": "rdm-master", "objectTypeKey": "domain", "name": "Instant",
        "workspaceKey": "default",
        "attributes": [
            _attribute("domain-code", "INSTANT"),
            _attribute("wp10-seen-at", written),
            _attribute("wp10-amount", "12.50"),
        ],
    })
    assert created.status_code == 201, created.text
    read = typed_model_client.get(
        f"/api/v1/objects/domain/{created.json()['id']}", params={"workspaceKey": "default"}
    )
    body = read.json()
    stored = {item["attributeTypeKey"]: item["value"] for item in body["attributes"]}
    assert as_utc(datetime.fromisoformat(stored["wp10-seen-at"])) == as_utc(
        datetime.fromisoformat(written)
    )
    # The same forms a change set row carries, so equal values compare equal across contexts.
    assert stored["wp10-seen-at"] == "2026-12-24T17:00:00+00:00"
    assert stored["wp10-amount"] == "12.5"
    for filter_value, found in (("2026-12-24T18:00:00+01:00", True), ("2026-12-24T16:30:00", False)):
        listed = typed_model_client.get("/api/v1/objects/domain", params={
            "workspaceKey": "default", "filter.wp10-seen-at.lte": filter_value,
        })
        assert listed.status_code == 200, listed.text
        assert (body["id"] in [item["id"] for item in listed.json()["items"]]) is found


def test_server_timestamps_carry_an_explicit_offset(typed_model_client):
    """A timestamp without its zone would reach clients as local wall-clock time."""
    created = typed_model_client.post("/api/v1/objects", json={
        "applicationKey": "rdm-master", "objectTypeKey": "domain", "name": "Stamped",
        "workspaceKey": "default", "attributes": [_attribute("domain-code", "STAMPED")],
    })
    assert created.status_code == 201, created.text
    read = typed_model_client.get(
        f"/api/v1/objects/domain/{created.json()['id']}", params={"workspaceKey": "default"}
    )
    change_set = typed_model_client.post("/api/v1/workspaces/default/change-sets", json={})
    assert change_set.status_code == 201, change_set.text
    history = typed_model_client.get(
        f"/api/v1/objects/domain/{created.json()['id']}/history"
    )
    assert history.status_code == 200, history.text
    stamps = [read.json()["createdAt"], read.json()["updatedAt"], change_set.json()["createdAt"]]
    stamps += [item["occurredAt"] for item in history.json()["items"]]
    assert len(stamps) > 3
    for stamp in stamps:
        parsed = datetime.fromisoformat(stamp)
        assert parsed.utcoffset() is not None, stamp
