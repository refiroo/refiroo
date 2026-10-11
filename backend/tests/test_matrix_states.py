"""Base 0.8 A3b: stored relation matrix cell states.

The row state filter reads ``matrix_cell_states`` instead of deriving every cell from records. Each
write path is exercised at the HTTP boundary over the starter model's shapes (a conditioned
binding read outgoing, a many-to-many binding read incoming), live and in a change set, and after
each step two checks hold: every stored (owner, shape) equals states rebuilt from records
(``matrix_states.verify``), and each state filter lists exactly the rows whose unfiltered cells show
that state. The derived filter is disabled while they run, so the stored states answer.

Model activation, a change set's release change, discard, startup builds, a failed build and the
migration are covered at their own boundaries.
"""

import json
import logging

import pytest
import test_relation_matrix as reads
import test_relation_matrix_writes as writes
from sqlalchemy import delete, event, func, select
from test_relation_matrix import MASTER_SYSTEMS, TRANSLATIONS, attr, create, translation
from test_relation_matrix import delete as delete_record
from test_relation_matrix_writes import (
    CODELIST_SYSTEMS,
    STARTER,
    cell,
    link,
    matrix,
    patch,
    serve,
    translation_payload,
    unlink,
)
from wp8_support import create_change_set, create_workspace, publish_change_set

from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.management.projections import relation_matrix
from app.models.database import (
    MatrixCellState,
    MatrixStateBuild,
    ModelRelease,
    ModelRuntimeState,
    RdmObject,
)
from app.models.schema import EngineModel

# The A2 and A3 data fixtures, over this module's client.
translations = reads.translations
languages = writes.languages
systems = writes.systems

BASE = "/api/v1/workspaces/default/relation-matrix"
STATES = ("one", "several", "inactive", "historyOnly", "none")


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database):
    yield from serve(json.loads(STARTER.read_text()), tmp_path, monkeypatch, migrated_database("a3b.db"))


@pytest.fixture
def stored_only(monkeypatch):
    """A filter that derives its cells from records fails the test."""

    def refuse(*_args, **_kwargs):
        raise AssertionError("the state filter derived its cells instead of reading stored states")

    monkeypatch.setattr(relation_matrix, "_current_pairs", refuse)
    monkeypatch.setattr(relation_matrix, "_history_pairs", refuse)


def assert_derived() -> None:
    with SessionLocal() as session:
        assert matrix_states.verify(session) == []


def _all(client, params: dict) -> list[dict]:
    rows, cursor = [], None
    while True:
        response = client.get(BASE, params={**params, "pageSize": 100, **({"cursor": cursor} if cursor else {})})
        assert response.status_code == 200, response.text
        body = response.json()
        rows += body["items"]
        cursor = body["nextCursor"]
        if cursor is None:
            return rows


def assert_filters(client, view, columns, **context) -> dict[str, set[str]]:
    """Every state filter equals the rows whose cells show the state; returns the cell states."""
    params = {**view, "columnIds": columns, **context}
    states = {item["row"]["name"]: {c["state"] for c in item["cells"]} for item in _all(client, params)}
    for state in STATES:
        expected = [name for name, held in states.items() if state in held]
        filtered = _all(client, {**params, "state": state})
        assert [item["row"]["name"] for item in filtered] == expected, (state, context)
        total = client.get(BASE, params={**params, "state": state, "includeTotal": True, "pageSize": 1})
        assert total.json()["totalCount"] == len(expected), state
    return states


def check(client, view, columns, *contexts: dict) -> None:
    assert_derived()
    for context in ({}, *contexts):
        assert_filters(client, view, columns, **context)


def builds(**where) -> set[tuple[str, str]]:
    with SessionLocal() as session:
        statement = select(MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id)
        for key, value in where.items():
            statement = statement.where(getattr(MatrixStateBuild, key) == value)
        return {tuple(item) for item in session.execute(statement)}


def test_live_writes_keep_states_derived(client, languages, stored_only):
    columns, groups, masters = languages["columns"], languages["groups"], languages["masters"]
    records = languages["records"]
    assert ("live", "default") in builds(owner_kind="live")
    check(client, TRANSLATIONS, columns)

    # Create with an initial relation, then flip the binding's condition both ways.
    created = client.post("/api/v1/objects", json=translation_payload("M1 cs", groups["cs"], masters["M1"], active=False))
    assert created.status_code == 201, created.text
    check(client, TRANSLATIONS, columns)
    activated = patch(client, created.json(), attributes=[attr("active", True)])
    check(client, TRANSLATIONS, columns)
    patch(client, activated, attributes=[attr("active", False)])
    check(client, TRANSLATIONS, columns)

    # A parent move carries every cell under the container to another column.
    moved = patch(client, groups["nested"], parentObjectId=languages["language"]["de"]["id"])
    check(client, TRANSLATIONS, columns)
    assert cell(matrix(client, TRANSLATIONS, columnIds=columns), "M1", columns[2])["state"] == "one"
    patch(client, moved, parentObjectId=groups["en"]["id"])
    check(client, TRANSLATIONS, columns)

    # Deleting a cell record, and a row with its relations.
    delete_record(client, records["M2 en old"])
    check(client, TRANSLATIONS, columns)
    delete_record(client, masters["M2"])
    check(client, TRANSLATIONS, columns)
    with SessionLocal() as session:
        assert not session.scalar(
            select(func.count()).select_from(MatrixCellState).where(MatrixCellState.row_id == masters["M2"]["id"])
        )


def test_links_in_both_directions_keep_states_derived(client, systems, stored_only):
    s1, s2 = systems["columns"]
    values, codelists, masters = systems["values"], systems["codelists"], systems["masters"]
    check(client, MASTER_SYSTEMS, [s1, s2])
    # Incoming many-to-many: the row is the relation's to end.
    first = link(client, "system-value-maps-to-master", values["V1"], masters["SM1"])
    link(client, "system-value-maps-to-master", values["V2"], masters["SM1"])
    link(client, "system-value-maps-to-master", values["V3"], masters["SM2"])
    check(client, MASTER_SYSTEMS, [s1, s2])
    assert cell(matrix(client, MASTER_SYSTEMS, columnIds=[s1]), "SM1", s1)["state"] == "several"
    unlink(client, {"relationId": first["id"], "relationVersion": first["version"]})
    check(client, MASTER_SYSTEMS, [s1, s2])
    # Outgoing, optional binding: link and move the value's group to another system.
    link(client, "reference-has-system-representation", codelists["C2"], values["V2"])
    check(client, CODELIST_SYSTEMS, [s1, s2])
    patch(client, systems["group"], parentObjectId=s2)
    check(client, CODELIST_SYSTEMS, [s1, s2])
    check(client, MASTER_SYSTEMS, [s1, s2])


def test_change_set_writes_and_publishing_keep_states_derived(client, translations, stored_only):
    """The A2 fixture: a live change set with an injected duplicate and a deletion, a publication,
    and a translation deleted live since it was published."""
    columns = translations["columns"]
    change_set = translations["change_set"]
    staged = {"changeSetId": change_set["id"]}
    publication = {"publicationId": translations["publication"]["id"]}
    check(client, TRANSLATIONS, columns, staged, publication)
    assert ("change_set", change_set["id"]) in builds(owner_kind="change_set")

    # Stage more: an inactive translation for M4, a move and a condition edit.
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    group = client.get(
        "/api/v1/objects/translation-group", params={"workspaceKey": "default", "search": "Group cs"}
    ).json()["items"][0]
    created = client.post(
        "/api/v1/objects",
        json=translation_payload(
            "M4 cs", group, translations["masters"]["M4"], active=False,
            changeSetId=change_set["id"], expectedChangeSetVersion=version,
        ),
    )
    assert created.status_code == 201, created.text
    check(client, TRANSLATIONS, columns, staged)
    record = created.json()
    edited = patch(
        client, record, attributes=[attr("active", True)],
        changeSetId=change_set["id"], expectedChangeSetVersion=record["changeSetVersion"],
    )
    check(client, TRANSLATIONS, columns, staged)
    moved = patch(
        client, group, parentObjectId=translations["languages"]["de"]["id"],
        changeSetId=change_set["id"], expectedChangeSetVersion=edited["changeSetVersion"],
    )
    check(client, TRANSLATIONS, columns, staged)
    assert "one" in assert_filters(client, TRANSLATIONS, columns, **staged)["M4"]
    # Live stays as it was: the change set's rows replace the base's only in the change set.
    assert "none" in assert_filters(client, TRANSLATIONS, columns)["M4"]

    # Publishing is refused while the staged duplicate breaks the scope; resolve it and publish.
    duplicate = next(
        item
        for item in matrix(client, TRANSLATIONS, columnIds=[columns[0]], **staged)["items"][1]["cells"][0]["records"]
        if item["name"] == "M2 en duplicate"
    )
    response = client.delete(
        f"/api/v1/objects/translation/{duplicate['id']}",
        params={"expectedVersion": duplicate["version"], **staged, "expectedChangeSetVersion": moved["changeSetVersion"]},
    )
    if response.status_code == 409:
        token = response.json()["error"]["details"]["deletionPreviewToken"]
        response = client.delete(
            f"/api/v1/objects/translation/{duplicate['id']}",
            params={
                "expectedVersion": duplicate["version"], **staged,
                "expectedChangeSetVersion": moved["changeSetVersion"], "cascade": True, "deletionPreviewToken": token,
            },
        )
    assert response.status_code == 204, response.text
    check(client, TRANSLATIONS, columns, staged)
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    published = publish_change_set(
        client, change_set["id"], expected_change_set_version=version,
        expected_active_publication_id=translations["publication"]["id"],
    )
    assert published.status_code == 200, published.text
    second = {"publicationId": published.json()["id"]}
    check(client, TRANSLATIONS, columns, publication, second)
    assert not builds(owner_id=change_set["id"])
    # History: M1's EN translation was deleted by the change set, publication 1 held it.
    assert "historyOnly" in assert_filters(client, TRANSLATIONS, columns)["M1"]

    # A change set from a publication reads that publication's states; discarding drops its own.
    derived = create_change_set(client, "default", derived_from_publication_id=published.json()["id"]).json()
    check(client, TRANSLATIONS, columns, {"changeSetId": derived["id"]})
    assert client.delete(
        f"/api/v1/change-sets/{derived['id']}", params={"expectedVersion": derived["version"]}
    ).status_code == 204
    assert not builds(owner_id=derived["id"])
    assert_derived()


def _candidate(client, change) -> ModelRelease:
    source = client.get("/api/v1/model").json()
    change(source)
    source["release"]["version"] = f"{source['release']['version']}-a3b"
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, EngineModel.model_validate(source))
        session.commit()
        return release


def _without_codelist_systems(source: dict) -> None:
    for application in source["applications"]:
        application["views"] = [view for view in application["views"] if view["key"] != "codelists-by-system"]


@pytest.fixture
def admin_client(tmp_path, monkeypatch, migrated_database):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    yield from serve(json.loads(STARTER.read_text()), tmp_path, monkeypatch, migrated_database("a3b-admin.db"))


def test_a_change_sets_walk_anti_joins_the_rows_it_replaces(client, translations, stored_only):
    """0.9 R (R-F25): deleting about 100,000 records in a change set held one walk of the cells
    under a moved container for more than 5 minutes. Its base rows left out the change set's rows
    by `NOT IN`, a subplan PostgreSQL hashes only while they fit in `work_mem`; past that it scans
    them for every base row. Moving a container in a change set walks without a subplan."""
    change_set = translations["change_set"]
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    group = client.get(
        "/api/v1/objects/translation-group", params={"workspaceKey": "default", "search": "Group cs"}
    ).json()["items"][0]
    plans = []

    def explain(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("WITH RECURSIVE matrix_descendants"):
            with cursor.connection.cursor() as probe:
                probe.execute("EXPLAIN " + statement, parameters)
                plans.append("\n".join(row[0] for row in probe.fetchall()))

    event.listen(get_engine(), "before_cursor_execute", explain)
    try:
        patch(
            client, group, parentObjectId=translations["languages"]["de"]["id"],
            changeSetId=change_set["id"], expectedChangeSetVersion=version,
        )
    finally:
        event.remove(get_engine(), "before_cursor_execute", explain)
    assert plans, "moving a container in the change set walked nothing"
    assert all("SubPlan" not in plan for plan in plans), plans
    check(client, TRANSLATIONS, translations["columns"], {"changeSetId": change_set["id"]})


def test_activation_and_release_change_follow_the_model(admin_client, stored_only):
    client = admin_client
    before = {key for kind, _id, key in _all_builds() if kind == "live"}
    assert len(before) == 4
    change_set = create_change_set(client, "default", source="currentLive").json()
    release = _candidate(client, _without_codelist_systems)

    # A change set pinned to the new release keeps only its shapes, and so does its base.
    response = client.patch(
        f"/api/v1/change-sets/{change_set['id']}/model-release",
        json={"modelReleaseId": release.public_id, "expectedChangeSetVersion": change_set["version"]},
    )
    assert response.status_code == 200, response.text
    assert len({key for kind, owner, key in _all_builds() if owner == change_set["id"]}) == 3
    assert_derived()

    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        active = session.get(ModelRelease, state.active_model_release_id)
        expected = {"expectedRuntimeVersion": state.version, "expectedActiveReleaseId": active.public_id}
    activated = client.post(f"/api/v1/model-releases/{release.public_id}/activation", json=expected)
    assert activated.status_code == 200, activated.text
    after = {key for kind, _id, key in _all_builds() if kind == "live"}
    assert after < before and len(after) == 3
    # The removed shape is no longer used by any model in use, so no owner keeps it.
    assert {key for *_rest, key in _all_builds()} <= after
    assert_derived()


def _all_builds() -> set[tuple[str, str, str]]:
    with SessionLocal() as session:
        return {
            tuple(item)
            for item in session.execute(
                select(MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id, MatrixStateBuild.shape_key)
            )
        }


def test_workspaces_build_and_drop_their_states(client):
    create_workspace(client, "a3b-space")
    assert {kind for kind, _id in builds(workspace_key="a3b-space")} == {"live", "history"}
    workspace = client.get("/api/v1/workspaces/a3b-space").json()
    response = client.delete("/api/v1/workspaces/a3b-space", params={"expectedVersion": workspace["version"]})
    assert response.status_code == 204, response.text
    assert not builds(workspace_key="a3b-space")


def test_startup_builds_what_is_missing_and_a_failed_build_falls_back(
    tmp_path, monkeypatch, migrated_database, caplog
):
    database = migrated_database("a3b-startup.db")
    model = json.loads(STARTER.read_text())
    with serve_once(model, tmp_path, monkeypatch, database) as client:
        data = _seed_translations(client)
        expected = assert_filters(client, TRANSLATIONS, data["columns"])
        with SessionLocal() as session:
            # As after the migration, or a stopped build: nothing stored.
            session.execute(delete(MatrixCellState))
            session.execute(delete(MatrixStateBuild))
            session.commit()
        # Unbuilt owners derive their cells: correct, only slower.
        assert assert_filters(client, TRANSLATIONS, data["columns"]) == expected

    # A failed build leaves the API serving and says what to do.
    monkeypatch.setattr(matrix_states, "sync_workspace", _raise)
    with caplog.at_level(logging.ERROR), serve_once(model, tmp_path, monkeypatch, database) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert assert_filters(client, TRANSLATIONS, data["columns"]) == expected
    message = next(item.getMessage() for item in caplog.records if "matrix cell states" in item.getMessage())
    assert "derive their cells from records" in message and "restart" in message
    monkeypatch.undo()

    # A restart builds every missing owner, and a second one builds nothing more.
    for _start in range(2):
        with serve_once(model, tmp_path, monkeypatch, database) as client:
            assert ("live", "default") in builds(owner_kind="live")
            assert_derived()
            assert assert_filters(client, TRANSLATIONS, data["columns"]) == expected


def _raise(*_args, **_kwargs):
    raise RuntimeError("disk full")


class serve_once:
    def __init__(self, model, tmp_path, monkeypatch, database):
        self._generator = serve(model, tmp_path, monkeypatch, database)

    def __enter__(self):
        return next(self._generator)

    def __exit__(self, *_exc):
        next(self._generator, None)


def _seed_translations(client) -> dict:
    domain = create(client, "rdm-master", "domain", "Domain", [attr("domain-code", "D")])
    codelist = create(client, "rdm-master", "codelist", "Codelist", [attr("codelist-code", "C")], parent=domain)
    masters = [
        create(
            client, "rdm-master", "master-value", name,
            [attr("master-id", name), attr("value-code", name), attr("value-name", name)], parent=codelist,
        )
        for name in ("M1", "M2", "M3")
    ]
    columns, groups = [], []
    for code in ("en", "cs"):
        columns.append(create(client, "rdm-translations", "language", code, [attr("language-code", code)]))
        groups.append(
            create(client, "rdm-translations", "translation-group", f"G {code}", [attr("group-code", code)], parent=columns[-1])
        )
    translation(client, "M1 en", groups[0], masters[0])
    translation(client, "M2 en", groups[0], masters[1], active=False)
    translation(client, "M2 cs", groups[1], masters[1])
    staged = create_change_set(client, "default", source="currentLive").json()
    added = translation(
        client, "M3 cs", groups[1], masters[2], changeSetId=staged["id"], expectedChangeSetVersion=staged["version"]
    )
    publish_change_set(client, staged["id"], expected_change_set_version=added["changeSetVersion"])
    delete_record(client, added)
    return {"columns": [item["id"] for item in columns]}


def test_a_long_row_list_filters_as_one_value(client, languages):
    """Over 500 matching rows the filter passes its list as one array value, not one parameter each."""
    ids = [languages["masters"]["M2"]["id"], *(f"missing-{number}" for number in range(1200))]
    with SessionLocal() as session:
        statement = select(RdmObject.name).where(matrix_states.listed(RdmObject.id, ids))
        compiled = statement.compile(session.get_bind())
        assert "= ANY (" in str(compiled)
        assert [value for value in compiled.params.values() if isinstance(value, list)] == [ids]
        assert list(session.scalars(statement)) == ["M2"]
        negated = select(RdmObject.name).where(
            RdmObject.object_type_key == "master-value", ~matrix_states.listed(RdmObject.id, ids)
        )
        assert list(session.scalars(negated)) == ["M1"]
