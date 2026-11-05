"""WP-4 integration: real HTTP, stored typed attributes, contexts and cursors."""

import json
from pathlib import Path
from threading import Event, Thread, current_thread

import pytest
from harness_identity import TestClient
from postgres_server import collated
from sqlalchemy import event, select
from test_context_read_parity import reissue_cursor
from test_relation_set_versions import (
    _attr,
    _create_codelist,
    _create_domain,
    _create_master_value,
    _create_system_value,
    _set_version,
    _suffix,
)

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.compiler import canonical_model, parse_model
from app.engine.model.registry import model_registry
from app.main import create_app
from app.management.projections.mapping import MappingRead
from app.models.database import ModelRelease

BINDING = {
    "relationTypeKey": "system-value-maps-to-master",
    "fromObjectTypeKey": "system-value",
    "toObjectTypeKey": "master-value",
    "direction": "outgoing",
}
OUT = dict(applicationKey="rdm-systems", viewKey="system-to-master-mapping", **BINDING)
IN = dict(
    applicationKey="rdm-master",
    viewKey="master-to-system-mapping",
    **{**BINDING, "direction": "incoming"},
)
from workspace_model_support import default_model

BASE = "/api/v1/workspaces/default"


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database, request):
    model = json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
    model["attributeTypes"].append(
        {"key": "rank", "name": "Rank", "valueType": "integer", "features": {"searchable": True}}
    )
    master = next(row for row in model["objectTypes"] if row["key"] == "master-value")
    master["attributes"].append({"attributeTypeKey": "rank"})
    for application in model["applications"]:
        if application["key"] == "rdm-master":
            # Exercise globally reusable object types without letting one application's lens
            # surface another application's records.
            application["objectTypeKeys"].extend(["system", "system-value"])
        if application["key"] == "rdm-systems":
            view = next(row for row in application["views"] if row["type"] == "mappingGrid")
            view["config"]["targetDisplayColumns"].append("rank")
            view["config"]["candidateSearchFields"].append("rank")
            alternative = json.loads(json.dumps(view))
            alternative["key"] = "by-name"
            alternative["config"]["sourceColumns"] = ["name"]
            alternative["config"]["targetDisplayColumns"] = ["name"]
            alternative["config"]["candidateSearchFields"] = ["name"]
            application["views"].append(alternative)
            builtins = json.loads(json.dumps(alternative))
            builtins["key"] = "builtins"
            builtins["config"]["sourceColumns"] = [
                "id",
                "objectType",
                "path",
                "ancestor:system",
                "createdAt",
            ]
            application["views"].append(builtins)
    binding = next(
        row
        for row in model["objectTypeRelations"]
        if row["relationTypeKey"] == BINDING["relationTypeKey"]
    )
    binding["cardinality"] = getattr(request, "param", "many-to-many")
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", migrated_database("mapping.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def get(client, route, params):
    response = client.get(BASE + route, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def masters(client, count):
    suffix = _suffix()
    domain = _create_domain(client, suffix)
    codelist = _create_codelist(client, suffix, domain["id"])
    return [_create_master_value(client, f"{suffix}_{i}", codelist["id"]) for i in range(count)]


def relation(client, source, target, **context):
    response = client.post(
        "/api/v1/relations",
        json=dict(
            relationTypeKey=BINDING["relationTypeKey"],
            fromObjectId=source["id"],
            toObjectId=target["id"],
            **context,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_both_directions_states_typed_fields_and_bounded_target_continuation(client):
    master, unused = masters(client, 2)
    sources = [_create_system_value(client, _suffix()) for _ in range(25)]
    for source in sources[:23]:
        relation(client, source, master)
    rows = get(client, "/mapping-coverage", IN)["items"]
    by_id = {row["source"]["id"]: row for row in rows}
    ambiguous = by_id[master["id"]]
    # The binding is many-to-many: several targets are normal, so the row is mapped.
    assert ambiguous["state"] == "mapped"
    assert ambiguous["targetCount"] == 23
    assert ambiguous["mappingVersion"] == 23
    assert len(ambiguous["targets"]) == 20
    remaining = get(
        client,
        "/mapping-targets",
        dict(
            IN,
            sourceObjectId=master["id"],
            mappingVersion=23,
            cursor=ambiguous["targetsNextCursor"],
        ),
    )
    assert len(remaining["items"]) == 3 and remaining["nextCursor"] is None
    ids = [row["relationId"] for row in ambiguous["targets"] + remaining["items"]]
    assert len(set(ids)) == 23
    assert by_id[unused["id"]]["state"] == "unmapped"
    outgoing = get(client, "/mapping-coverage", dict(OUT, pageSize=100))["items"]
    assert sum(row["state"] == "mapped" for row in outgoing) == 23
    assert sum(row["state"] == "unmapped" for row in outgoing) == 2
    r = client.patch(
        f"/api/v1/objects/master-value/{master['id']}",
        json={"expectedVersion": master["version"], "attributes": [_attr("rank", 42)]},
    )
    assert r.status_code == 200, r.text
    typed = get(client, "/mapping-coverage", dict(OUT, search=sources[0]["name"]))["items"][0]
    assert typed["targets"][0]["object"]["fields"]["rank"] == 42
    relation(client, sources[-1], master)
    stale = client.get(
        BASE + "/mapping-targets",
        params=dict(
            IN,
            sourceObjectId=master["id"],
            mappingVersion=23,
            cursor=ambiguous["targetsNextCursor"],
        ),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "MAPPING_VERSION_CONFLICT"
    assert "refresh" in stale.json()["error"]["message"]


def test_candidates_multiple_views_search_and_all_pages(client):
    targets = masters(client, 7)
    source = _create_system_value(client, _suffix())
    relation(client, source, targets[0])
    params = {
        "applicationKey": OUT["applicationKey"],
        "viewKey": OUT["viewKey"],
        "objectTypeKey": "master-value",
        "pageSize": 2,
    }
    seen = []
    while True:
        page = get(client, "/mapping-candidates", params)
        seen += [row["id"] for row in page["items"]]
        if not page["nextCursor"]:
            break
        params["cursor"] = page["nextCursor"]
    assert set(seen) == {row["id"] for row in targets}
    assert len(seen) == 7
    search = next(
        row["value"] for row in targets[1]["attributes"] if row["attributeTypeKey"] == "value-code"
    )
    params = {
        "applicationKey": OUT["applicationKey"],
        "viewKey": OUT["viewKey"],
        "objectTypeKey": "master-value",
        "search": search,
    }
    assert len(get(client, "/mapping-candidates", params)["items"]) == 1
    assert get(client, "/mapping-candidates", dict(params, viewKey="by-name"))["items"] == []
    original = get(client, "/mapping-coverage", OUT)["items"][0]
    alternate = get(client, "/mapping-coverage", dict(OUT, viewKey="by-name"))["items"][0]
    assert set(original["source"]["fields"]) == {"name", "value-code", "value-name"}
    assert set(alternate["source"]["fields"]) == {"name"}
    assert original["mappingVersion"] == alternate["mappingVersion"] == 1
    assert set(alternate["targets"][0]["object"]["fields"]) == {"name"}
    # Incoming one-to-many candidates can have an outgoing edge: the source
    # (physical to-side) is the cardinality-constrained side, not the candidate.
    incoming = get(
        client,
        "/mapping-candidates",
        {
            "applicationKey": IN["applicationKey"],
            "viewKey": IN["viewKey"],
            "objectTypeKey": "system-value",
        },
    )
    assert [row["id"] for row in incoming["items"]] == [source["id"]]


def test_coverage_pagination_and_cursor_scope_validation(client):
    for _ in range(4):
        _create_system_value(client, _suffix())
    first = get(client, "/mapping-coverage", dict(OUT, pageSize=2))
    second = get(client, "/mapping-coverage", dict(OUT, pageSize=2, cursor=first["nextCursor"]))
    assert len(first["items"]) == len(second["items"]) == 2
    assert second["nextCursor"] is None
    assert len({row["source"]["id"] for row in first["items"] + second["items"]}) == 4
    for change in ({"viewKey": "by-name"}, {"search": "other"}):
        r = client.get(
            BASE + "/mapping-coverage",
            params=dict(OUT, pageSize=2, cursor=first["nextCursor"], **change),
        )
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR"
    for params, code, error in (
        (dict(OUT, viewKey="missing"), 404, "MAPPING_VIEW_NOT_FOUND"),
        (dict(OUT, relationTypeKey="missing"), 404, "MAPPING_BINDING_NOT_FOUND"),
        (dict(OUT, direction="incoming"), 422, "MAPPING_VIEW_BINDING_MISMATCH"),
    ):
        r = client.get(BASE + "/mapping-coverage", params=params)
        assert r.status_code == code and r.json()["error"]["code"] == error
    r = client.get(
        BASE + "/mapping-candidates",
        params={
            "applicationKey": OUT["applicationKey"],
            "viewKey": OUT["viewKey"],
            "objectTypeKey": "system-value",
        },
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "MAPPING_CANDIDATE_TYPE_MISMATCH"


def test_coverage_and_candidates_list_by_name_and_seek_a_name(client):
    """S4R4 (D22): sources and candidates list by name in live and change sets, and seek finds a name."""
    labels = ("zulu", "alpha", "mike", "bravo")
    tag = _suffix()
    sources = {label: _create_system_value(client, f"{label} {tag}") for label in labels}
    targets = masters(client, 3)
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    candidate_params = {
        "applicationKey": OUT["applicationKey"],
        "viewKey": OUT["viewKey"],
        "objectTypeKey": "master-value",
    }
    for context in ({}, {"changeSetId": change_set["id"]}):
        coverage = get(client, "/mapping-coverage", dict(OUT, search=tag, **context))["items"]
        assert [row["source"]["id"] for row in coverage] == [
            sources[label]["id"] for label in sorted(labels)
        ], context
        sought = get(
            client,
            "/mapping-coverage",
            dict(OUT, search=tag, seek="SysVal m", pageSize=1, **context),
        )
        assert [row["source"]["id"] for row in sought["items"]] == [sources["mike"]["id"]], context
        names = [
            row["name"]
            for row in get(client, "/mapping-candidates", dict(candidate_params, **context))[
                "items"
            ]
        ]
        assert names == collated(names) and len(names) == len(targets), context

    # A cursor bound to the former order, by source ID, is refused rather than read by name.
    first = get(client, "/mapping-coverage", dict(OUT, search=tag, pageSize=1))
    params = dict(OUT, search=tag, pageSize=1)
    assert get(
        client, "/mapping-coverage", dict(params, cursor=reissue_cursor(first["nextCursor"]))
    )
    stale = reissue_cursor(first["nextCursor"], sort=["id"], position=[sources["alpha"]["id"]])
    r = client.get(BASE + "/mapping-coverage", params=dict(params, cursor=stale))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR"


def test_coverage_parent_and_state_filters_apply_before_pagination(client):
    targets = masters(client, 2)
    sources = [_create_system_value(client, _suffix()) for _ in range(4)]
    relation(client, sources[0], targets[0])
    relation(client, sources[1], targets[0])
    relation(client, sources[1], targets[1])

    assert {
        row["source"]["id"]
        for row in get(client, "/mapping-coverage", dict(OUT, state="mapped"))["items"]
    } == {sources[0]["id"], sources[1]["id"]}
    # Several targets are normal on a many-to-many binding, so nothing is ambiguous.
    assert get(client, "/mapping-coverage", dict(OUT, state="ambiguous"))["items"] == []
    assert {
        row["source"]["id"]
        for row in get(client, "/mapping-coverage", dict(IN, state="mapped"))["items"]
    } == {targets[0]["id"], targets[1]["id"]}
    unmapped = get(client, "/mapping-coverage", dict(OUT, state="unmapped", pageSize=1))
    assert len(unmapped["items"]) == 1 and unmapped["nextCursor"] is not None

    parent_id = sources[2]["parentObjectId"]
    scoped = get(client, "/mapping-coverage", dict(OUT, parentObjectId=parent_id))["items"]
    assert [row["source"]["id"] for row in scoped] == [sources[2]["id"]]
    r = client.get(
        BASE + "/mapping-coverage",
        params=dict(OUT, state="mapped", cursor=unmapped["nextCursor"]),
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR"

    mismatch = client.get(
        BASE + "/mapping-coverage",
        params=dict(OUT, parentObjectId=targets[0]["parentObjectId"]),
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "MAPPING_PARENT_SCOPE_MISMATCH"
    missing = client.get(BASE + "/mapping-coverage", params=dict(OUT, parentObjectId="missing"))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "MAPPING_PARENT_NOT_FOUND"


def test_change_set_coverage_versions_and_context_bound_cursors(client):
    master = masters(client, 1)[0]
    sources = [_create_system_value(client, _suffix()) for _ in range(3)]
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    relation(
        client,
        sources[0],
        master,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    rows = get(client, "/mapping-coverage", dict(OUT, changeSetId=change_set["id"]))["items"]
    assert sum(row["state"] == "mapped" for row in rows) == 1
    assert (
        next(row for row in rows if row["source"]["id"] == sources[0]["id"])["mappingVersion"] == 1
    )
    assert all(
        row["mappingVersion"] == 0 and row["state"] == "unmapped"
        for row in get(client, "/mapping-coverage", OUT)["items"]
    )
    first = get(client, "/mapping-coverage", dict(OUT, changeSetId=change_set["id"], pageSize=1))
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, cursor=first["nextCursor"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR"
    assert (
        get(
            client,
            "/mapping-candidates",
            {
                "applicationKey": OUT["applicationKey"],
                "viewKey": OUT["viewKey"],
                "objectTypeKey": "master-value",
                "changeSetId": change_set["id"],
            },
        )["items"][0]["id"]
        == master["id"]
    )
    detail = get(
        client,
        "/mapping-targets",
        dict(OUT, changeSetId=change_set["id"], sourceObjectId=sources[0]["id"], mappingVersion=1),
    )
    assert detail["targetCount"] == 1


def test_change_set_coverage_parent_scope_uses_effective_objects(client):
    source = _create_system_value(client, _suffix())
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    rows = get(
        client,
        "/mapping-coverage",
        dict(OUT, changeSetId=change_set["id"], parentObjectId=source["parentObjectId"]),
    )["items"]
    assert [row["source"]["id"] for row in rows] == [source["id"]]


def test_coverage_sources_are_scoped_to_the_declaring_application(client):
    suffix = _suffix()
    own = _create_system_value(client, suffix)
    foreign_system = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "workspaceKey": "default",
            "objectTypeKey": "system",
            "name": f"Foreign system {suffix}",
            "attributes": [_attr("system-code", f"FOREIGN_{suffix}")],
        },
    )
    assert foreign_system.status_code == 201, foreign_system.text
    foreign = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "workspaceKey": "default",
            "objectTypeKey": "system-value",
            "name": f"Foreign value {suffix}",
            "parentObjectId": foreign_system.json()["id"],
            "attributes": [
                _attr("value-code", f"FOREIGN_VALUE_{suffix}"),
                _attr("value-name", f"Foreign value {suffix}"),
            ],
        },
    )
    assert foreign.status_code == 201, foreign.text

    rows = get(client, "/mapping-coverage", dict(OUT, search=suffix))["items"]
    assert own["id"] in {row["source"]["id"] for row in rows}
    assert foreign.json()["id"] not in {row["source"]["id"] for row in rows}


def test_publication_coverage_is_immutable_scoped_and_version_bound(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    activation = client.post(
        f"/api/v1/change-sets/{change_set['id']}/publication",
        json={
            "expectedChangeSetVersion": change_set["version"],
            "expectedActivePublicationId": None,
        },
    )
    assert activation.status_code == 200, activation.text
    publication_id = activation.json()["id"]

    old_code = next(
        item["value"] for item in source["attributes"] if item["attributeTypeKey"] == "value-code"
    )
    new_code = f"LIVE_ONLY_{_suffix()}"
    changed = client.patch(
        f"/api/v1/objects/system-value/{source['id']}",
        json={
            "expectedVersion": source["version"],
            "attributes": [
                _attr("value-code", new_code),
                _attr("value-name", source["name"]),
            ],
        },
    )
    assert changed.status_code == 200, changed.text
    assert [
        row["source"]["id"]
        for row in get(
            client,
            "/mapping-coverage",
            dict(OUT, publicationId=publication_id, search=old_code),
        )["items"]
    ] == [source["id"]]
    assert (
        get(
            client,
            "/mapping-coverage",
            dict(OUT, publicationId=publication_id, search=new_code),
        )["items"]
        == []
    )
    assert [
        row["source"]["id"]
        for row in get(client, "/mapping-coverage", dict(OUT, search=new_code))["items"]
    ] == [source["id"]]

    relation(client, source, master)
    assert (
        get(client, "/mapping-coverage", dict(OUT, search=source["name"]))["items"][0]["state"]
        == "mapped"
    )
    historical = get(
        client,
        "/mapping-coverage",
        dict(
            OUT,
            publicationId=publication_id,
            parentObjectId=source["parentObjectId"],
            state="unmapped",
        ),
    )["items"]
    assert len(historical) == 1
    assert historical[0]["source"]["id"] == source["id"]
    assert historical[0]["mappingVersion"] == 0
    detail = get(
        client,
        "/mapping-targets",
        dict(
            OUT,
            publicationId=publication_id,
            sourceObjectId=source["id"],
            mappingVersion=0,
        ),
    )
    assert detail["targetCount"] == 0

    invalid = client.get(
        BASE + "/mapping-coverage",
        params=dict(OUT, changeSetId="change_set", publicationId=publication_id),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "MUTUALLY_EXCLUSIVE_CONTEXT"


def test_concurrent_coverage_keeps_edges_fields_and_versions_in_one_snapshot(client, monkeypatch):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    read_started, write_finished = Event(), Event()
    original = MappingRead.summary

    def pause(read, objects, columns):
        # Pause after paging fields but before the coverage version and edge reads.
        if read.source_type == "system-value" and not read_started.is_set():
            read_started.set()
            assert write_finished.wait(10)
        return original(read, objects, columns)

    monkeypatch.setattr(MappingRead, "summary", pause)
    failures = []

    def write():
        try:
            assert read_started.wait(10)
            relation(client, source, master)
        except (AssertionError, RuntimeError) as exc:
            failures.append(exc)
        finally:
            write_finished.set()

    thread = Thread(target=write)
    thread.start()
    try:
        row = get(client, "/mapping-coverage", OUT)["items"][0]
    finally:
        thread.join(10)
    assert not thread.is_alive() and not failures
    assert row["mappingVersion"] == 0 and row["targetCount"] == 0 and row["state"] == "unmapped"
    refreshed = get(client, "/mapping-coverage", OUT)["items"][0]
    assert refreshed["mappingVersion"] == 1 and refreshed["targetCount"] == 1


@pytest.mark.parametrize("change_set_context", [False, True])
def test_coverage_query_count_does_not_grow_per_source(client, change_set_context):
    master = masters(client, 1)[0]
    for _ in range(12):
        relation(client, _create_system_value(client, _suffix()), master)
    params = dict(OUT)
    if change_set_context:
        change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
        params["changeSetId"] = change_set["id"]
    counts = []
    for size in (1, 12):
        statements = []

        def capture(
            connection, cursor, statement, parameters, context, executemany, statements=statements
        ):
            # The request's statements only: the engine's background threads (``rdm-…``) poll the
            # same engine while the app runs.
            if not current_thread().name.startswith("rdm-"):
                statements.append(statement)

        event.listen(get_engine(), "before_cursor_execute", capture)
        try:
            get(client, "/mapping-coverage", dict(params, pageSize=size))
        finally:
            event.remove(get_engine(), "before_cursor_execute", capture)
        counts.append(len(statements))
    assert counts[0] == counts[1]


@pytest.mark.parametrize("client", ["one-to-many"], indirect=True)
def test_one_to_many_source_with_several_targets_is_mapped(client):
    """The source end of a one-to-many view may hold many targets: that is Mapped, not Ambiguous."""
    targets = masters(client, 3)
    sources = [_create_system_value(client, _suffix()) for _ in range(2)]
    for target in targets[:2]:
        relation(client, sources[0], target)
    relation(client, sources[1], targets[2])
    rows = {
        row["source"]["id"]: row
        for row in get(client, "/mapping-coverage", dict(OUT, pageSize=100))["items"]
    }
    assert rows[sources[0]["id"]]["state"] == "mapped"
    assert rows[sources[0]["id"]]["targetCount"] == 2
    assert rows[sources[1]["id"]]["state"] == "mapped"
    mapped = get(client, "/mapping-coverage", dict(OUT, state="mapped", pageSize=100))["items"]
    assert {row["source"]["id"] for row in mapped} >= {sources[0]["id"], sources[1]["id"]}
    assert get(client, "/mapping-coverage", dict(OUT, state="ambiguous"))["items"] == []


@pytest.mark.parametrize("client", ["one-to-many", "one-to-one"], indirect=True)
def test_direction_aware_candidate_cardinality(client):
    targets = masters(client, 2)
    sources = [_create_system_value(client, _suffix()) for _ in range(2)]
    relation(client, sources[0], targets[0])
    outgoing = get(
        client,
        "/mapping-candidates",
        {
            "applicationKey": OUT["applicationKey"],
            "viewKey": OUT["viewKey"],
            "objectTypeKey": "master-value",
        },
    )
    assert [row["id"] for row in outgoing["items"]] == [targets[1]["id"]]
    incoming = get(
        client,
        "/mapping-candidates",
        {
            "applicationKey": IN["applicationKey"],
            "viewKey": IN["viewKey"],
            "objectTypeKey": "system-value",
        },
    )
    # One-to-many permits a physical from-side to have multiple outgoing edges.
    with get_engine().connect() as connection:
        from sqlalchemy import select

        from app.models.database import ModelRelease

        model = connection.execute(select(ModelRelease.model_json)).scalar_one()
    binding = next(
        row
        for row in model["objectTypeRelations"]
        if row["relationTypeKey"] == BINDING["relationTypeKey"]
    )
    expected = sources if binding["cardinality"] == "one-to-many" else sources[1:]
    assert {row["id"] for row in incoming["items"]} == {row["id"] for row in expected}


def test_builtin_projections_live_and_change_set(client):
    source = _create_system_value(client, _suffix())
    params = dict(OUT, viewKey="builtins", search=source["name"])
    live = get(client, "/mapping-coverage", params)["items"][0]["source"]["fields"]
    assert live["id"] == source["id"] and live["objectType"] == "System value"
    assert live["ancestor:system"].startswith("System ")
    assert live["path"].endswith(source["name"])
    assert isinstance(live["createdAt"], str)
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    fields = get(client, "/mapping-coverage", dict(params, changeSetId=change_set["id"]))["items"][
        0
    ]["source"]["fields"]
    assert {key: value for key, value in fields.items() if key != "createdAt"} == {
        key: value for key, value in live.items() if key != "createdAt"
    }
    assert fields["createdAt"] is None  # Change set snapshots do not store object timestamps.


def test_change_set_pinned_model_and_release_bound_cursor(client):
    for _ in range(2):
        _create_system_value(client, _suffix())
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    first = get(client, "/mapping-coverage", dict(OUT, pageSize=1))
    # Select a distinct installed same-schema release with different view content.
    # The change set's pin remains the original immutable release.
    with SessionLocal() as session:
        previous = session.scalar(select(ModelRelease))
        document = json.loads(json.dumps(previous.model_json))
        document["release"]["version"] = "0.7.1"
        application = next(
            row for row in document["applications"] if row["key"] == OUT["applicationKey"]
        )
        application["views"] = [row for row in application["views"] if row["key"] != "by-name"]
        model = parse_model(document)
        model_json, model_hash = canonical_model(model)
        release = ModelRelease(
            release_key=model.release.key,
            release_name=model.release.name,
            release_version=model.release.version,
            schema_version=model.schemaVersion,
            model_hash=model_hash,
            model_json=model_json,
        )
        session.add(release)
        session.flush()
        runtime = default_model(session)
        runtime.model_release_id = release.id
        runtime.version += 1
        session.commit()
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, viewKey="by-name"))
    assert r.status_code == 404
    pinned = get(
        client, "/mapping-coverage", dict(OUT, viewKey="by-name", changeSetId=change_set["id"])
    )
    assert len(pinned["items"]) == 2
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, cursor=first["nextCursor"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR"


def test_change_set_base_overlay_tombstones_and_target_preview(client):
    master = masters(client, 1)[0]
    sources = [_create_system_value(client, _suffix()) for _ in range(23)]
    edges = [relation(client, source, master) for source in sources]
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    params = dict(IN, changeSetId=change_set["id"])
    before = get(client, "/mapping-coverage", params)["items"][0]
    assert before["targetCount"] == 23 and len(before["targets"]) == 20
    assert before["mappingVersion"] == 0
    remaining = get(
        client,
        "/mapping-targets",
        dict(
            params,
            sourceObjectId=master["id"],
            mappingVersion=0,
            cursor=before["targetsNextCursor"],
        ),
    )
    assert len(remaining["items"]) == 3
    deleted = client.delete(
        f"/api/v1/relations/{edges[0]['id']}",
        params={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
            "expectedVersion": edges[0]["version"],
        },
    )
    assert deleted.status_code == 204, deleted.text
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    changed = client.patch(
        f"/api/v1/objects/system-value/{sources[1]['id']}",
        json={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": version,
            "expectedVersion": sources[1]["version"],
            "name": "Change set renamed target",
        },
    )
    assert changed.status_code == 200, changed.text
    after = get(client, "/mapping-coverage", params)["items"][0]
    detail = get(
        client,
        "/mapping-targets",
        dict(params, sourceObjectId=master["id"], mappingVersion=1, pageSize=100),
    )
    assert after["mappingVersion"] == 1 and after["targetCount"] == 22
    assert all(row["relationId"] != edges[0]["id"] for row in detail["items"])
    assert (
        next(row for row in detail["items"] if row["object"]["id"] == sources[1]["id"])["object"][
            "name"
        ]
        == "Change set renamed target"
    )
    assert get(client, "/mapping-coverage", IN)["items"][0]["targetCount"] == 23
    # Candidate attribute search executes against the effective change set JSON fields.
    search = next(
        row["value"] for row in master["attributes"] if row["attributeTypeKey"] == "value-code"
    )
    candidates = get(
        client,
        "/mapping-candidates",
        {
            "applicationKey": OUT["applicationKey"],
            "viewKey": OUT["viewKey"],
            "changeSetId": change_set["id"],
            "objectTypeKey": "master-value",
            "search": search,
        },
    )
    assert candidates["items"][0]["id"] == master["id"]


@pytest.mark.parametrize("change_set_context", [False, True])
@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
def test_cascade_deletion_invalidates_mapping_continuations(client, change_set_context, direction):
    if direction == "outgoing":
        targets = masters(client, 21)
        source = _create_system_value(client, _suffix())
        edges = [relation(client, source, target) for target in targets]
        params = dict(OUT)
    else:
        target = masters(client, 1)[0]
        sources = [_create_system_value(client, _suffix()) for _ in range(21)]
        edges = [relation(client, source, target) for source in sources]
        params = dict(IN)
    context = {}
    change_set_id = None
    if change_set_context:
        change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
        change_set_id = change_set["id"]
        params["changeSetId"] = change_set_id
        context = {"changeSetId": change_set_id, "expectedChangeSetVersion": change_set["version"]}
    # Search identifies the one anchor in the outgoing view; incoming has one master.
    if direction == "outgoing":
        params["search"] = source["name"]
    before = get(client, "/mapping-coverage", params)["items"][0]
    first = before["targets"][0]
    removed_edge = next(edge for edge in edges if edge["id"] == first["relationId"])
    untouched_edge = next(edge for edge in edges if edge["id"] != first["relationId"])
    root = first["object"]
    path = f"/api/v1/objects/{root['objectTypeKey']}/{root['id']}"

    def version(edge, side, selected_change_set=change_set_id):
        return _set_version(
            "default",
            selected_change_set,
            BINDING["relationTypeKey"],
            "system-value",
            "master-value",
            edge["fromObjectId"] if side == "outgoing" else edge["toObjectId"],
            side,
        )

    outgoing_before = version(removed_edge, "outgoing")
    incoming_before = version(removed_edge, "incoming")
    opposite = "incoming" if direction == "outgoing" else "outgoing"
    untouched_before = version(untouched_edge, opposite)
    live_before = version(removed_edge, direction, None)
    preview = client.delete(path, params=dict(context, expectedVersion=1))
    assert preview.status_code == 409, preview.text
    assert version(removed_edge, "outgoing") == outgoing_before
    assert version(removed_edge, "incoming") == incoming_before
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    stale = client.delete(
        path, params=dict(context, expectedVersion=2, cascade=True, deletionPreviewToken=token)
    )
    assert stale.status_code == 409, stale.text
    assert version(removed_edge, "outgoing") == outgoing_before
    assert version(removed_edge, "incoming") == incoming_before
    deleted = client.delete(
        path, params=dict(context, expectedVersion=1, cascade=True, deletionPreviewToken=token)
    )
    assert deleted.status_code == 204, deleted.text
    assert version(removed_edge, "outgoing") == outgoing_before + 1
    assert version(removed_edge, "incoming") == incoming_before + 1
    assert version(untouched_edge, opposite) == untouched_before
    if change_set_context:
        assert version(removed_edge, direction, None) == live_before
    after = get(client, "/mapping-coverage", params)["items"][0]
    assert after["targetCount"] == 20 and after["mappingVersion"] == before["mappingVersion"] + 1
    # Search belongs to coverage, so target details use only the configured binding.
    detail_params = {key: value for key, value in params.items() if key != "search"}
    continuation = client.get(
        BASE + "/mapping-targets",
        params=dict(
            detail_params,
            sourceObjectId=before["source"]["id"],
            mappingVersion=before["mappingVersion"],
            cursor=before["targetsNextCursor"],
        ),
    )
    assert continuation.status_code == 409
    error = continuation.json()["error"]
    assert error["code"] == "MAPPING_VERSION_CONFLICT" and "refresh" in error["message"]
    assert error["details"]["mappingVersion"] == after["mappingVersion"]


# ---------------------------------------------------------------------------
# Mapping list endpoint
# ---------------------------------------------------------------------------


def test_list_mappings_returns_source_and_target(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    rel = relation(client, source, master)
    page = get(client, "/relations", OUT)
    items = [row for row in page["items"] if row["relationId"] == rel["id"]]
    assert len(items) == 1
    row = items[0]
    assert row["source"]["id"] == source["id"]
    assert row["target"]["id"] == master["id"]
    assert row["direction"] == "outgoing"
    assert row["mappingVersion"] == 1
    assert isinstance(row["attributes"], dict)


def test_list_mappings_pagination(client):
    target = masters(client, 1)[0]
    sources = [_create_system_value(client, _suffix()) for _ in range(3)]
    for s in sources:
        relation(client, s, target)
    first = get(client, "/relations", dict(OUT, pageSize=2))
    assert len(first["items"]) == 2
    assert first["nextCursor"] is not None
    second = get(client, "/relations", dict(OUT, pageSize=2, cursor=first["nextCursor"]))
    assert len(second["items"]) == 1
    assert second["nextCursor"] is None
    all_ids = {row["relationId"] for row in first["items"] + second["items"]}
    assert len(all_ids) == 3


def test_list_mappings_search(client):
    target = masters(client, 1)[0]
    s1 = _create_system_value(client, "findme_" + _suffix())
    s2 = _create_system_value(client, "other_" + _suffix())
    relation(client, s1, target)
    relation(client, s2, target)
    page = get(client, "/relations", dict(OUT, search="findme"))
    assert all("findme" in row["source"]["name"].lower() for row in page["items"])
    assert len(page["items"]) >= 1


def test_list_mappings_incoming_direction(client):
    master = masters(client, 1)[0]
    s1 = _create_system_value(client, _suffix())
    s2 = _create_system_value(client, _suffix())
    relation(client, s1, master)
    relation(client, s2, master)
    page = get(client, "/relations", IN)
    matching = [row for row in page["items"] if row["source"]["id"] == master["id"]]
    assert len(matching) == 2
    target_ids = {row["target"]["id"] for row in matching}
    assert s1["id"] in target_ids and s2["id"] in target_ids


def test_list_mappings_empty(client):
    _create_system_value(client, _suffix())
    page = get(client, "/relations", OUT)
    assert page["items"] == []
    assert page["nextCursor"] is None


def test_list_mappings_change_set_context(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    relation(client, source, master)
    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    page = get(client, "/relations", dict(OUT, changeSetId=change_set["id"]))
    matching = [row for row in page["items"] if row["source"]["id"] == source["id"]]
    assert len(matching) == 1
    assert matching[0]["target"]["id"] == master["id"]


# ---------------------------------------------------------------------------
# Mapping list — all-optional parameter tests
# ---------------------------------------------------------------------------


def test_list_mappings_no_params_returns_both_directions(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    rel = relation(client, source, master)
    page = get(client, "/relations", {})
    matching = [row for row in page["items"] if row["relationId"] == rel["id"]]
    assert len(matching) == 2
    dirs = {row["direction"] for row in matching}
    assert dirs == {"outgoing", "incoming"}
    out_row = next(row for row in matching if row["direction"] == "outgoing")
    in_row = next(row for row in matching if row["direction"] == "incoming")
    assert out_row["source"]["id"] == source["id"]
    assert out_row["target"]["id"] == master["id"]
    assert in_row["source"]["id"] == master["id"]
    assert in_row["target"]["id"] == source["id"]


def test_list_mappings_direction_filter_single_row(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    rel = relation(client, source, master)
    page = get(client, "/relations", {"direction": "outgoing"})
    matching = [row for row in page["items"] if row["relationId"] == rel["id"]]
    assert len(matching) == 1
    assert matching[0]["direction"] == "outgoing"
    assert matching[0]["source"]["id"] == source["id"]


def test_list_mappings_relation_type_filter(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    relation(client, source, master)
    page = get(
        client,
        "/relations",
        {"relationTypeKey": "system-value-maps-to-master", "direction": "outgoing"},
    )
    assert len(page["items"]) >= 1
    bogus = get(client, "/relations", {"relationTypeKey": "nonexistent", "direction": "outgoing"})
    assert len(bogus["items"]) == 0


def test_list_mappings_no_view_default_projection(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    relation(client, source, master)
    page = get(client, "/relations", {"direction": "outgoing"})
    row = next(r for r in page["items"] if r["source"]["id"] == source["id"])
    assert row["source"]["fields"] == {}
    assert row["target"]["fields"] == {}
    assert row["source"]["objectTypeKey"] == "system-value"
    assert row["source"]["name"] != ""


def test_list_mappings_with_view_returns_rows(client):
    master = masters(client, 1)[0]
    source = _create_system_value(client, _suffix())
    relation(client, source, master)
    page = get(client, "/relations", {**OUT})
    matching = [r for r in page["items"] if r["source"]["id"] == source["id"]]
    assert len(matching) == 1
    assert matching[0]["direction"] == "outgoing"


def test_list_mappings_incomplete_view_identity_rejected(client):
    response = client.get(BASE + "/relations", params={"applicationKey": "rdm-systems"})
    assert response.status_code == 422
