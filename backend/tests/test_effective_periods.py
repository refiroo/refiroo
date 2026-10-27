"""Base 0.9 Q4: effective periods (schema 0.8) and ``asOf`` (ADR-038, INTEGRATION_API §Q4).

An object type declares one period over two ``date`` attributes it binds: inclusive start, exclusive
end, either open. Writes refuse an end not after its start; ``asOf`` on the per-type list and the
model-aware query keeps the records effective on a date, in live data, a change set and a
publication alike, across every page. A type without a period refuses ``asOf`` rather than reading
some date field (SC-11), and so does the cross-type lookup, which lists several types (D21).
Read and write checks run on a generated model and on a copy with every key renamed.
"""

import copy
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from harness_identity import TestClient
from model_support import MODEL_PATH, renamed_model
from sqlalchemy import select
from test_consumer_api_model import API, definition, with_definition
from test_context_read_parity import APP, ENTRY, FOLDER, parity_model
from test_type_changes import WORKSPACE as STARTER_WORKSPACE
from test_type_changes import starter  # noqa: F401 - fixture
from workspace_model_support import DEFAULT_ACTIVATION, default_model

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.compiler import canonical_model, compile_model, parse_model
from app.engine.model.consumer_contract import contract_diagnostics
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import ChangeSetObject
from app.models.schema import EngineModel

Keys = Callable[[str], str]
WORKSPACE = "default"
QUERY = f"/api/v1/workspaces/{WORKSPACE}/queries/objects"
START, END = "per-from", "per-to"
PERIOD_PATH = "/objectTypes/{type}/effectivePeriod"


# --- the model ----------------------------------------------------------------------------------


def starter_source(renamed: bool) -> tuple[dict[str, Any], Keys]:
    source = json.loads(MODEL_PATH.read_text())
    names: dict[str, str] = {}
    if renamed:
        source, names = renamed_model(source)
    return source, lambda key: names.get(key, key)


def _object_type(source: dict[str, Any], key: str) -> dict[str, Any]:
    return next(item for item in source["objectTypes"] if item["key"] == key)


def _diagnostic(source: dict[str, Any]) -> tuple[str, str]:
    compiled = compile_model(source)
    assert not compiled.valid
    return compiled.diagnostics[0].code, compiled.diagnostics[0].path


@pytest.mark.parametrize("renamed", [False, True], ids=["starter", "renamed"])
def test_the_starter_declares_its_period(renamed):
    source, k = starter_source(renamed)
    model = parse_model(source)
    assert (model.schemaVersion, model.release.version) == ("0.10", "0.10.0")
    declared = {item.key: item.effectivePeriod for item in model.objectTypes if item.effectivePeriod}
    assert list(declared) == [k("master-value")]
    period = declared[k("master-value")]
    assert (period.startAttributeTypeKey, period.endAttributeTypeKey) == (k("valid-from"), k("valid-to"))


@pytest.mark.parametrize("renamed", [False, True], ids=["starter", "renamed"])
def test_a_period_is_refused_at_its_path(renamed):
    source, k = starter_source(renamed)
    path = PERIOD_PATH.format(type=k("master-value"))

    def with_period(**period: str) -> dict[str, Any]:
        result = copy.deepcopy(source)
        _object_type(result, k("master-value"))["effectivePeriod"] = period
        return result

    unbound = with_period(startAttributeTypeKey=k("valid-from"), endAttributeTypeKey=k("domain-code"))
    assert _diagnostic(unbound) == ("UNKNOWN_ATTRIBUTE_TYPE", f"{path}/endAttributeTypeKey")
    not_a_date = with_period(startAttributeTypeKey=k("value-code"), endAttributeTypeKey=k("valid-to"))
    assert _diagnostic(not_a_date) == ("INVALID_MODEL", f"{path}/startAttributeTypeKey")
    same = with_period(startAttributeTypeKey=k("valid-from"), endAttributeTypeKey=k("valid-from"))
    assert _diagnostic(same) == ("INVALID_MODEL", f"{path}/endAttributeTypeKey")
    extra = with_period(
        startAttributeTypeKey=k("valid-from"), endAttributeTypeKey=k("valid-to"), timeZone="UTC"
    )
    # Shape errors point by position, as every Pydantic error in a model does.
    position = next(index for index, item in enumerate(source["objectTypes"]) if item["key"] == k("master-value"))
    shape_path = f"/objectTypes/{position}/effectivePeriod"
    assert _diagnostic(extra) == ("unknown_field", f"{shape_path}/timeZone")
    missing = copy.deepcopy(source)
    _object_type(missing, k("master-value"))["effectivePeriod"] = {"startAttributeTypeKey": k("valid-from")}
    assert _diagnostic(missing) == ("missing_field", f"{shape_path}/endAttributeTypeKey")


def test_a_model_without_a_period_keeps_its_canonical_form():
    """An absent period is omitted from the canonical form."""
    source, _k = starter_source(False)
    del _object_type(source, "master-value")["effectivePeriod"]
    model_json, _hash = canonical_model(parse_model(source))
    assert all("effectivePeriod" not in item for item in model_json["objectTypes"])


@pytest.mark.parametrize("renamed", [False, True], ids=["starter", "renamed"])
def test_removing_an_exposed_types_period_is_a_contract_change(renamed):
    source, k = starter_source(renamed)
    active = parse_model(with_definition(source, definition(k)))
    without = with_definition(source, definition(k))
    del _object_type(without, k("master-value"))["effectivePeriod"]
    diagnostics = contract_diagnostics(active, parse_model(without))
    assert [(d.code, d.path) for d in diagnostics] == [
        ("CONSUMER_CONTRACT_VERSION_REQUIRED", f"{API}/exposes/0")
    ]
    assert "no longer declares an effective period" in diagnostics[0].message
    # Adding one back is compatible, and so is a higher contract version.
    assert contract_diagnostics(parse_model(without), active) == []
    raised = with_definition(without, definition(k) | {"contractVersion": 2})
    assert contract_diagnostics(active, parse_model(raised)) == []


# --- reads and writes on a generated model ------------------------------------------------------


def period_model() -> dict[str, Any]:
    """The parity model: entries declare a period, folders bind a date without one."""
    source = parity_model()
    source["release"]["version"] = "0.9.0-q4"
    for key in (START, END):
        source["attributeTypes"].append(
            {"key": key, "name": key, "valueType": "date", "features": {"filterable": True, "sortable": True}}
        )
    entry = _object_type(source, ENTRY)
    entry["attributes"] += [
        {"attributeTypeKey": START, "order": 100},
        {"attributeTypeKey": END, "order": 101},
    ]
    entry["effectivePeriod"] = {"startAttributeTypeKey": START, "endAttributeTypeKey": END}
    return source


@pytest.fixture(params=["generated", "renamed"])
def periods(request, tmp_path, monkeypatch, migrated_database) -> Iterator[tuple[TestClient, Keys, dict]]:
    source = period_model()
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    model_path = tmp_path / "period-model.json"
    model_path.write_text(json.dumps(source))
    monkeypatch.setenv("DATABASE_URL", migrated_database("periods.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    reload_settings()
    model_registry.clear()
    with TestClient(create_app()) as client:
        yield client, lambda key: names.get(key, key), source
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _ok(response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _refused(response, code: str, path: str | None = None, status: int = 422) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code, error
    if path is not None:
        assert error["details"]["path"] == path, error
    return error


def _version(client, change_set_id: str) -> int:
    return _ok(client.get(f"/api/v1/change-sets/{change_set_id}"))["version"]


def _create(client, k: Keys, object_type: str, name: str, parent: str | None, values: dict, **context):
    return client.post(
        "/api/v1/objects",
        json={
            "applicationKey": k(APP),
            "objectTypeKey": k(object_type),
            "name": name,
            "parentObjectId": parent,
            "attributes": [{"attributeTypeKey": k(key), "value": value} for key, value in values.items()],
            **context,
        },
    )


# name: (start, end); None is open. The boundary is 2026-07-01: Old ends and New starts there.
DATED = {
    "Old": (None, "2026-07-01"),
    "New": ("2026-07-01", None),
    "Overlap": ("2026-06-01", "2026-08-01"),
    "Always": (None, None),
    "Closed": ("2026-01-01", "2026-03-01"),
    "Future": ("2027-01-01", None),
    "Late": ("2026-06-15", None),
}


def _seed(client, k: Keys) -> dict[str, Any]:
    """Dated entries live; a publication of them; a change set that ends Future before it starts
    by moving its start, and makes Always end at the boundary."""
    live = {"workspaceKey": WORKSPACE}
    folder = _ok(_create(client, k, FOLDER, "F", None, {"par-code": "F-1", "par-due": "2026-07-01"}, **live), 201)
    entries = {}
    for name, (start, end) in DATED.items():
        values = {"par-code": name, **({START: start} if start else {}), **({END: end} if end else {})}
        entries[name] = _ok(_create(client, k, ENTRY, name, folder["id"], values, **live), 201)

    publish = _ok(client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}), 201)
    publication = _ok(
        client.post(
            f"/api/v1/change-sets/{publish['id']}/publication",
            json={"expectedChangeSetVersion": publish["version"]},
        )
    )
    change_set = _ok(client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}), 201)["id"]
    for name, values in (("Future", {START: "2026-05-01"}), ("Always", {END: "2026-07-01"})):
        record = _ok(client.get(f"/api/v1/objects/{k(ENTRY)}/{entries[name]['id']}", params={"changeSetId": change_set}))
        _ok(
            client.patch(
                f"/api/v1/objects/{k(ENTRY)}/{entries[name]['id']}",
                json={
                    "attributes": [{"attributeTypeKey": k(key), "value": value} for key, value in values.items()],
                    "expectedVersion": record["version"],
                    "changeSetId": change_set,
                    "expectedChangeSetVersion": _version(client, change_set),
                },
            )
        )
    return {
        "folder": folder,
        "entries": entries,
        "change_set": change_set,
        "contexts": {
            "live": ({"workspaceKey": WORKSPACE}, {}),
            "change set": ({"changeSetId": change_set}, {"changeSetId": change_set}),
            "publication": ({"publicationId": publication["id"]}, {"publicationId": publication["id"]}),
        },
    }


def _names(items: list[dict[str, Any]]) -> list[str]:
    return [item["name"] for item in items]


def _walk_list(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    items, cursor = [], None
    while True:
        page = _ok(client.get(path, params={**params, "pageSize": 2, **({"cursor": cursor} if cursor else {})}))
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def _walk_query(client, body: dict[str, Any]) -> list[dict[str, Any]]:
    items, cursor = [], None
    while True:
        page = _ok(client.post(QUERY, json={**body, "pageSize": 2, **({"cursor": cursor} if cursor else {})}))
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


# Expected names by name order, per context and date. The change set moves Future's start to
# 2026-05-01 and ends Always at the boundary; the publication and live data do not have those edits.
EXPECTED = {
    "live": {
        "2026-02-15": ["Always", "Closed", "Old"],
        "2026-06-30": ["Always", "Late", "Old", "Overlap"],
        "2026-07-01": ["Always", "Late", "New", "Overlap"],
        "2027-01-01": ["Always", "Future", "Late", "New"],
    },
    "change set": {
        "2026-02-15": ["Always", "Closed", "Old"],
        "2026-06-30": ["Always", "Future", "Late", "Old", "Overlap"],
        "2026-07-01": ["Future", "Late", "New", "Overlap"],
        "2027-01-01": ["Future", "Late", "New"],
    },
}
EXPECTED["publication"] = EXPECTED["live"]


def test_as_of_follows_the_boundary_in_every_context_and_page(periods):
    client, k, _source = periods
    seeded = _seed(client, k)
    for label, (list_context, query_context) in seeded["contexts"].items():
        for as_of, expected in EXPECTED[label].items():
            listed = _walk_list(client, f"/api/v1/objects/{k(ENTRY)}", {**list_context, "asOf": as_of})
            assert _names(listed) == expected, (label, as_of)
            body = {"objectTypeKey": k(ENTRY), "asOf": as_of, "context": query_context}
            assert _names(_walk_query(client, body)) == expected, (label, as_of)
            # Combined with a criterion and a sort, the date still decides.
            narrowed = _walk_query(
                client, {**body, "where": [{"field": k(START), "op": "isUnset", "value": True}], "sort": "-name"}
            )
            open_start = sorted((name for name in expected if DATED[name][0] is None), reverse=True)
            assert _names(narrowed) == open_start, (label, as_of)
        # Without asOf nothing is filtered: business dates never apply on their own.
        assert len(_walk_list(client, f"/api/v1/objects/{k(ENTRY)}", list_context)) == len(DATED)


def test_as_of_is_bound_into_cursors(periods):
    client, k, _source = periods
    _seed(client, k)
    path = f"/api/v1/objects/{k(ENTRY)}"
    dated = _ok(client.get(path, params={"workspaceKey": WORKSPACE, "asOf": "2026-06-30", "pageSize": 2}))
    _refused(
        client.get(path, params={"workspaceKey": WORKSPACE, "asOf": "2026-07-01", "cursor": dated["nextCursor"]}),
        "INVALID_CURSOR",
    )
    undated = _ok(client.get(path, params={"workspaceKey": WORKSPACE, "pageSize": 2}))
    _refused(
        client.get(path, params={"workspaceKey": WORKSPACE, "asOf": "2026-06-30", "cursor": undated["nextCursor"]}),
        "INVALID_CURSOR",
    )
    body = {"objectTypeKey": k(ENTRY), "asOf": "2026-06-30", "pageSize": 2}
    first = _ok(client.post(QUERY, json=body))
    _refused(client.post(QUERY, json={**body, "asOf": "2026-07-01", "cursor": first["nextCursor"]}), "INVALID_CURSOR")


def test_as_of_is_refused_where_no_period_applies(periods):
    client, k, _source = periods
    _seed(client, k)
    # Folders bind a date field but declare no period: nothing is inferred from it (SC-11).
    error = _refused(
        client.get(f"/api/v1/objects/{k(FOLDER)}", params={"workspaceKey": WORKSPACE, "asOf": "2026-07-01"}),
        "AS_OF_NOT_SUPPORTED",
        "/query/asOf",
    )
    assert error["details"]["objectTypeKey"] == k(FOLDER)
    _refused(
        client.post(QUERY, json={"objectTypeKey": k(FOLDER), "asOf": "2026-07-01"}), "AS_OF_NOT_SUPPORTED", "/asOf"
    )
    for value in ("tomorrow", "20260701", "2026-07-01T00:00:00"):
        _refused(client.post(QUERY, json={"objectTypeKey": k(ENTRY), "asOf": value}), "INVALID_QUERY", "/asOf")
    for value in ("tomorrow", "2026-07-01T00:00:00", "1782864000", "2026-02-30"):
        bad = client.get(f"/api/v1/objects/{k(ENTRY)}", params={"workspaceKey": WORKSPACE, "asOf": value})
        _refused(bad, "REQUEST_VALIDATION_ERROR")
    # The lookup lists several types: asOf is refused with the route that answers it (D21).
    for params in ({}, {"objectTypeKey": k(ENTRY)}):
        error = _refused(
            client.get("/api/v1/objects", params={"workspaceKey": WORKSPACE, "asOf": "2026-07-01", **params}),
            "AS_OF_NOT_SUPPORTED",
            "/query/asOf",
        )
        assert error["details"]["route"] == "GET /api/v1/objects/{objectTypeKey}"
    assert len(_ok(client.get("/api/v1/objects", params={"workspaceKey": WORKSPACE}))["items"]) == len(DATED) + 1


def test_writes_refuse_a_period_that_does_not_end_after_it_starts(periods):
    client, k, _source = periods
    seeded = _seed(client, k)
    folder = seeded["folder"]["id"]
    live = {"workspaceKey": WORKSPACE}
    change_set = seeded["change_set"]

    def claims() -> dict[str, Any]:
        return {"changeSetId": change_set, "expectedChangeSetVersion": _version(client, change_set)}

    for context in (live, None):
        for start, end in (("2026-07-01", "2026-07-01"), ("2026-07-02", "2026-07-01")):
            values = {"par-code": "Bad", START: start, END: end}
            error = _refused(
                _create(client, k, ENTRY, "Bad", folder, values, **(context or claims())),
                "INVALID_EFFECTIVE_PERIOD",
            )
            assert error["details"] == {
                "startAttributeTypeKey": k(START),
                "endAttributeTypeKey": k(END),
                "start": start,
                "end": end,
            }
        # Open on either side is always valid.
        for values in ({START: "2026-07-01"}, {END: "2026-07-01"}, {}):
            _ok(_create(client, k, ENTRY, "Open", folder, {"par-code": "Open", **values}, **(context or claims())), 201)

    overlap = seeded["entries"]["Overlap"]["id"]
    path = f"/api/v1/objects/{k(ENTRY)}/{overlap}"
    for context in (live, None):
        params = {} if context else {"changeSetId": change_set}
        record = _ok(client.get(path, params=params))
        # An update checks the record's values after it: a new end before the stored start.
        _refused(
            client.patch(
                path,
                json={
                    "attributes": [{"attributeTypeKey": k(END), "value": "2026-05-01"}],
                    "expectedVersion": record["version"],
                    **({} if context else claims()),
                },
            ),
            "INVALID_EFFECTIVE_PERIOD",
        )
        _refused(
            client.patch(
                f"{path}/attributes/{k(START)}",
                json={"value": "2026-08-01", "expectedVersion": record["version"], **({} if context else claims())},
            ),
            "INVALID_EFFECTIVE_PERIOD",
        )
        # Moving both together is a valid period.
        _ok(
            client.patch(
                path,
                json={
                    "attributes": [
                        {"attributeTypeKey": k(START), "value": "2026-09-01"},
                        {"attributeTypeKey": k(END), "value": "2026-10-01"},
                    ],
                    "expectedVersion": record["version"],
                    **({} if context else claims()),
                },
            )
        )


def test_change_set_validation_reports_an_invalid_period(periods):
    """A period stored some other way (an older release, a direct import) is a publish diagnostic."""
    client, k, _source = periods
    seeded = _seed(client, k)
    change_set = seeded["change_set"]
    future = seeded["entries"]["Future"]["id"]
    with SessionLocal() as session:
        row = session.scalar(
            select(ChangeSetObject).where(
                ChangeSetObject.change_set_id == change_set, ChangeSetObject.object_id == future
            )
        )
        row.attributes = {**row.attributes, k(START): "2027-02-01", k(END): "2027-01-01"}
        session.commit()
    validation = _ok(client.post(f"/api/v1/change-sets/{change_set}/validation"))
    assert validation["valid"] is False
    found = [item for item in validation["diagnostics"] if item["code"] == "INVALID_EFFECTIVE_PERIOD"]
    assert len(found) == 1 and found[0]["details"]["objectId"] == future, validation


def _install(source: dict[str, Any], version: str) -> str:
    candidate = copy.deepcopy(source)
    candidate["release"]["version"] = version
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, EngineModel.model_validate(candidate))
        session.commit()
        return release.public_id


def _activate(client: TestClient, release_id: str):
    with SessionLocal() as session:
        state = default_model(session)
        assert state is not None
        version = state.version
    active = client.get("/api/v1/model").headers["X-Model-Release-Id"]
    return client.post(
        DEFAULT_ACTIVATION,
        json={"releaseId": release_id, "expectedVersion": version, "expectedReleaseId": active},
    )


def test_releases_remove_and_add_a_period(periods):
    """Removing a period changes no data and refuses asOf; adding one over records it would
    refuse is blocked with their count until they are fixed (D20)."""
    client, k, source = periods
    seeded = _seed(client, k)
    without = copy.deepcopy(source)
    del _object_type(without, k(ENTRY))["effectivePeriod"]
    _ok(_activate(client, _install(without, "0.9.0-q4-without")))
    _refused(
        client.get(f"/api/v1/objects/{k(ENTRY)}", params={"workspaceKey": WORKSPACE, "asOf": "2026-07-01"}),
        "AS_OF_NOT_SUPPORTED",
    )
    inverted = _ok(
        _create(
            client, k, ENTRY, "Inverted", seeded["folder"]["id"],
            {"par-code": "Inverted", START: "2026-09-01", END: "2026-08-01"}, workspaceKey=WORKSPACE,
        ),
        201,
    )

    with_period = _install(source, "0.9.0-q4-again")
    refused = _activate(client, with_period)
    assert refused.status_code == 409, refused.text
    diagnostics = refused.json()["error"]["details"]
    diagnostics = diagnostics.get("diagnostics", diagnostics) if isinstance(diagnostics, dict) else diagnostics
    assert [(item["code"], item["path"], item["count"]) for item in diagnostics] == [
        ("INVALID_EFFECTIVE_PERIOD", PERIOD_PATH.format(type=k(ENTRY)), 1)
    ]

    record = _ok(client.get(f"/api/v1/objects/{k(ENTRY)}/{inverted['id']}"))
    _ok(
        client.patch(
            f"/api/v1/objects/{k(ENTRY)}/{inverted['id']}",
            json={"attributes": [{"attributeTypeKey": k(END), "value": "2026-10-01"}], "expectedVersion": record["version"]},
        )
    )
    _ok(_activate(client, with_period))
    assert _names(
        _walk_list(client, f"/api/v1/objects/{k(ENTRY)}", {"workspaceKey": WORKSPACE, "asOf": "2026-09-15"})
    ) == ["Always", "Inverted", "Late", "New"]


# --- SC-11 on the starter -----------------------------------------------------------------------


def test_sc11_business_dates_on_the_starter(starter):  # noqa: F811 - fixture
    """SC-11's API half: an old value and its replacement meet at a boundary, a transitional value
    overlaps both, and the answer follows business dates on every page, live and in a publication.
    A list without a declared period refuses the question instead of reading some date field."""
    client, k = starter
    workspace = STARTER_WORKSPACE
    app = k("rdm-master")

    def made(type_key: str, name: str, parent: str | None, values: dict[str, Any]) -> dict[str, Any]:
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": app,
                "objectTypeKey": k(type_key),
                "name": name,
                "parentObjectId": parent,
                "workspaceKey": workspace,
                "attributes": [{"attributeTypeKey": k(key), "value": value} for key, value in values.items()],
            },
        )
        return _ok(response, 201)

    domain = made("domain", "Finance", None, {"domain-code": "FIN"})
    codelist = made("codelist", "Currencies", domain["id"], {"codelist-code": "CUR"})
    dated = {
        "DEM": {"valid-to": "2002-01-01"},
        "EUR": {"valid-from": "2002-01-01"},
        "XEU": {"valid-from": "1999-01-01", "valid-to": "2002-03-01"},
        "CHF": {},
        "GBP": {"valid-from": "1971-02-15"},
        "USD": {},
    }
    for code, dates in dated.items():
        made("master-value", code, codelist["id"], {"master-id": f"M-{code}", "value-code": code, "value-name": code, **dates})
    publish = _ok(client.post(f"/api/v1/workspaces/{workspace}/change-sets", json={"source": "currentLive"}), 201)
    publication = _ok(
        client.post(
            f"/api/v1/change-sets/{publish['id']}/publication",
            json={"expectedChangeSetVersion": publish["version"]},
        )
    )

    before = ["CHF", "DEM", "GBP", "USD", "XEU"]
    after = ["CHF", "EUR", "GBP", "USD", "XEU"]
    path = f"/api/v1/objects/{k('master-value')}"
    for context in ({"workspaceKey": workspace}, {"publicationId": publication["id"]}):
        for as_of, expected in (("2001-12-31", before), ("2002-01-01", after), ("2002-03-01", ["CHF", "EUR", "GBP", "USD"])):
            params = {**context, "parentObjectId": codelist["id"], "asOf": as_of}
            assert _names(_walk_list(client, path, params)) == expected, (context, as_of)
            query_context = {} if "workspaceKey" in context else context
            body = {
                "objectTypeKey": k("master-value"),
                "asOf": as_of,
                "context": query_context,
                "where": [{"field": f"ancestor:{k('codelist')}", "op": "eq", "value": codelist["id"]}],
            }
            items, cursor = [], None
            while True:
                page = _ok(
                    client.post(
                        f"/api/v1/workspaces/{workspace}/queries/objects",
                        json={**body, "pageSize": 2, **({"cursor": cursor} if cursor else {})},
                    )
                )
                items.extend(page["items"])
                cursor = page["nextCursor"]
                if cursor is None:
                    break
            assert _names(items) == expected, (context, as_of)
    # A codelist declares no period; the asOf is refused, not ignored.
    _refused(
        client.get(f"/api/v1/objects/{k('codelist')}", params={"workspaceKey": workspace, "asOf": "2002-01-01"}),
        "AS_OF_NOT_SUPPORTED",
    )
    # Dates have no time zone: asOf is a date, not a time.
    _refused(
        client.get(path, params={"workspaceKey": workspace, "asOf": "2002-01-01T00:00:00+01:00"}),
        "REQUEST_VALIDATION_ERROR",
    )
