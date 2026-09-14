"""WP-4 integration: real HTTP, stored typed attributes, contexts and cursors."""

import json
from pathlib import Path
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
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
from app.main import create_app
from app.models.database import ModelRelease, ModelRuntimeState
from app.services.mapping import MappingRead
from app.services.model.compiler import canonical_model, parse_model
from app.services.model.registry import model_registry

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
BASE = "/api/v1/workspaces/default"


@pytest.fixture
def client(tmp_path, monkeypatch, request):
    model = json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
    model["attributeTypes"].append(
        {"key": "rank", "name": "Rank", "valueType": "integer", "features": {"searchable": True}}
    )
    master = next(row for row in model["objectTypes"] if row["key"] == "master-value")
    master["attributes"].append({"attributeTypeKey": "rank"})
    for application in model["applications"]:
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
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'mapping.db'}")
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        # WAL lets a writer commit while a coverage snapshot is held by a reader.
        with get_engine().connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
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
    assert ambiguous["state"] == "ambiguous"
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
    assert stale.json()["error"]["code"] == "mapping_version_conflict"
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
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"
    for params, code, error in (
        (dict(OUT, viewKey="missing"), 404, "mapping_view_not_found"),
        (dict(OUT, relationTypeKey="missing"), 404, "mapping_binding_not_found"),
        (dict(OUT, direction="incoming"), 422, "mapping_view_binding_mismatch"),
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
    assert r.status_code == 422 and r.json()["error"]["code"] == "mapping_candidate_type_mismatch"


def test_draft_coverage_versions_and_context_bound_cursors(client):
    master = masters(client, 1)[0]
    sources = [_create_system_value(client, _suffix()) for _ in range(3)]
    draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
    relation(
        client,
        sources[0],
        master,
        workspaceDraftId=draft["id"],
        expectedWorkspaceDraftVersion=draft["version"],
    )
    rows = get(client, "/mapping-coverage", dict(OUT, workspaceDraftId=draft["id"]))["items"]
    assert sum(row["state"] == "mapped" for row in rows) == 1
    assert (
        next(row for row in rows if row["source"]["id"] == sources[0]["id"])["mappingVersion"] == 1
    )
    assert all(
        row["mappingVersion"] == 0 and row["state"] == "unmapped"
        for row in get(client, "/mapping-coverage", OUT)["items"]
    )
    first = get(client, "/mapping-coverage", dict(OUT, workspaceDraftId=draft["id"], pageSize=1))
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, cursor=first["nextCursor"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"
    assert (
        get(
            client,
            "/mapping-candidates",
            {
                "applicationKey": OUT["applicationKey"],
                "viewKey": OUT["viewKey"],
                "objectTypeKey": "master-value",
                "workspaceDraftId": draft["id"],
            },
        )["items"][0]["id"]
        == master["id"]
    )
    detail = get(
        client,
        "/mapping-targets",
        dict(OUT, workspaceDraftId=draft["id"], sourceObjectId=sources[0]["id"], mappingVersion=1),
    )
    assert detail["targetCount"] == 1


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


@pytest.mark.parametrize("draft_context", [False, True])
def test_coverage_query_count_does_not_grow_per_source(client, draft_context):
    master = masters(client, 1)[0]
    for _ in range(12):
        relation(client, _create_system_value(client, _suffix()), master)
    params = dict(OUT)
    if draft_context:
        draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
        params["workspaceDraftId"] = draft["id"]
    counts = []
    for size in (1, 12):
        statements = []

        def capture(
            connection, cursor, statement, parameters, context, executemany, statements=statements
        ):
            statements.append(statement)

        event.listen(get_engine(), "before_cursor_execute", capture)
        try:
            get(client, "/mapping-coverage", dict(params, pageSize=size))
        finally:
            event.remove(get_engine(), "before_cursor_execute", capture)
        counts.append(len(statements))
    assert counts[0] == counts[1]


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


def test_builtin_projections_live_and_draft(client):
    source = _create_system_value(client, _suffix())
    params = dict(OUT, viewKey="builtins", search=source["name"])
    live = get(client, "/mapping-coverage", params)["items"][0]["source"]["fields"]
    assert live["id"] == source["id"] and live["objectType"] == "System value"
    assert live["ancestor:system"].startswith("System ")
    assert live["path"].endswith(source["name"])
    assert isinstance(live["createdAt"], str)
    draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
    fields = get(client, "/mapping-coverage", dict(params, workspaceDraftId=draft["id"]))["items"][
        0
    ]["source"]["fields"]
    assert {key: value for key, value in fields.items() if key != "createdAt"} == {
        key: value for key, value in live.items() if key != "createdAt"
    }
    assert fields["createdAt"] is None  # Draft snapshots do not store object timestamps.


def test_draft_pinned_model_and_release_bound_cursor(client):
    for _ in range(2):
        _create_system_value(client, _suffix())
    draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
    first = get(client, "/mapping-coverage", dict(OUT, pageSize=1))
    # Select a distinct installed same-schema release with different view content.
    # The draft's pin remains the original immutable release.
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
        runtime = session.get(ModelRuntimeState, 1)
        runtime.active_model_release_id = release.id
        runtime.version += 1
        session.commit()
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, viewKey="by-name"))
    assert r.status_code == 404
    pinned = get(
        client, "/mapping-coverage", dict(OUT, viewKey="by-name", workspaceDraftId=draft["id"])
    )
    assert len(pinned["items"]) == 2
    r = client.get(BASE + "/mapping-coverage", params=dict(OUT, cursor=first["nextCursor"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_cursor"


def test_draft_base_overlay_tombstones_and_target_preview(client):
    master = masters(client, 1)[0]
    sources = [_create_system_value(client, _suffix()) for _ in range(23)]
    edges = [relation(client, source, master) for source in sources]
    draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
    params = dict(IN, workspaceDraftId=draft["id"])
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
            "workspaceDraftId": draft["id"],
            "expectedWorkspaceDraftVersion": draft["version"],
            "expectedVersion": edges[0]["version"],
        },
    )
    assert deleted.status_code == 204, deleted.text
    version = client.get(f"/api/v1/workspace-drafts/{draft['id']}").json()["version"]
    changed = client.patch(
        f"/api/v1/objects/system-value/{sources[1]['id']}",
        json={
            "workspaceDraftId": draft["id"],
            "expectedWorkspaceDraftVersion": version,
            "expectedVersion": sources[1]["version"],
            "name": "Draft renamed target",
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
        == "Draft renamed target"
    )
    assert get(client, "/mapping-coverage", IN)["items"][0]["targetCount"] == 23
    # Candidate attribute search executes against the effective draft JSON fields.
    search = next(
        row["value"] for row in master["attributes"] if row["attributeTypeKey"] == "value-code"
    )
    candidates = get(
        client,
        "/mapping-candidates",
        {
            "applicationKey": OUT["applicationKey"],
            "viewKey": OUT["viewKey"],
            "workspaceDraftId": draft["id"],
            "objectTypeKey": "master-value",
            "search": search,
        },
    )
    assert candidates["items"][0]["id"] == master["id"]


@pytest.mark.parametrize("draft_context", [False, True])
@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
def test_cascade_deletion_invalidates_mapping_continuations(client, draft_context, direction):
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
    draft_id = None
    if draft_context:
        draft = client.post(BASE + "/drafts", json={"source": "currentLive"}).json()
        draft_id = draft["id"]
        params["workspaceDraftId"] = draft_id
        context = {"workspaceDraftId": draft_id, "expectedWorkspaceDraftVersion": draft["version"]}
    # Search identifies the one anchor in the outgoing view; incoming has one master.
    if direction == "outgoing":
        params["search"] = source["name"]
    before = get(client, "/mapping-coverage", params)["items"][0]
    first = before["targets"][0]
    removed_edge = next(edge for edge in edges if edge["id"] == first["relationId"])
    untouched_edge = next(edge for edge in edges if edge["id"] != first["relationId"])
    root = first["object"]
    path = f"/api/v1/objects/{root['objectTypeKey']}/{root['id']}"

    def version(edge, side, selected_draft=draft_id):
        return _set_version(
            "default",
            selected_draft,
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
    if draft_context:
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
    assert error["code"] == "mapping_version_conflict" and "refresh" in error["message"]
    assert error["details"]["mappingVersion"] == after["mappingVersion"]
