"""J37.8 — Schema versions side by side (USER_JOURNEYS.md, Base 0.11 V4, D97–D103).

Workspaces run releases of different schema versions in the window at once, each read under its own
release; what moves data between them compares the releases' declarations, never their versions;
a version outside the window is refused wherever it is named. Each test runs on one configuration
``X`` (schema 0.9) beside ``Y``, the other generated configuration; a primed model (``X′``, ``Y′``)
is the same model raised to schema 0.10 with a navigation group (D103). Naming no configuration key.
"""

import copy
import json
from uuid import uuid4

import pytest
from scenario import W1, application, consumer_object, ok, refused, scenario_seed
from service import execute, serve
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j12_run_the_service import _clone, databases  # noqa: F401 (fixture)
from test_j36_workspace_models import BOTH, _model, _on, _other
from test_j37_workspace_migration import (
    _confirm,
    _previewed,
    _probe,
    _read,
    _rows,
    _run,
    _value,
    _workspace,
    _x2,
)

from app.engine.model.compiler import SCHEMA_VERSIONS

NEWEST = "0.10"


def _window(world):
    return ok(world.api.get("/system"))["schemaLanguages"]


def _after_newest(world=None):
    """A schema version after the newest in the window."""
    major, minor = SCHEMA_VERSIONS[-1].split(".")
    return f"{major}.{int(minor) + 1}"


def _raised(world, model):
    """``model`` raised to the newest schema with a navigation group on R's application."""
    raised = copy.deepcopy(model)
    raised["schemaVersion"] = NEWEST
    raised["release"]["version"] += "-raised"
    application_ = next(a for a in raised["applications"] if a["key"] == world.app("R"))
    application_["navigation"] = {"groups": [{"key": "grouped", "label": "Grouped"}]}
    return raised


def _draft(world, model, **body):
    return ok(world.api.post("/model-drafts", {"name": "Window", "model": model, **body}), 201)


def _install(world, draft):
    current = ok(world.api.get(f"/model-drafts/{draft['id']}"))
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": current["version"]}
    )


def _operate(world, draft, *operations):
    current = ok(world.api.get(f"/model-drafts/{draft['id']}"))
    body = {"expectedVersion": current["version"], "operations": list(operations)}
    return world.api.post(f"/model-drafts/{draft['id']}/operations", body)


def _navigation_refusal(answer):
    """The diagnostic of a navigation group in a document older than schema 0.10."""
    assert answer["valid"] is False
    [diagnostic] = [d for d in answer["diagnostics"] if d["path"].endswith("/navigation")]
    assert NEWEST in diagnostic["message"]


@pytest.mark.journey("J37.8")
@pytest.mark.structures(*BOTH)
def test_two_schema_versions_side_by_side(world):
    """Given the default workspace on X (0.9) and a workspace on Y′ (0.10). When each reads its
    model, creates and reads an R, publishes a change set and reads its record through the consumer
    API. Then each answers under its own release and schema version, Y′'s with its navigation."""
    other = _other(world)
    y = other.install(_raised(other, other.configuration.model), name="Raised")
    key = _on(world, y["id"])
    x = _model(world)

    for keys, workspace, release, schema in (
        (world, W1, x["releaseId"], "0.9"),
        (other, key, y["id"], NEWEST),
    ):
        response = world.api.get("/model", workspaceKey=workspace)
        model = ok(response)
        assert response.headers["X-Model-Release-Id"] == release
        assert model["schemaVersion"] == schema
        application_ = next(a for a in model["applications"] if a["key"] == keys.app("R"))
        assert (application_.get("navigation") is not None) == (schema == NEWEST)

        made = keys.made("R", f"Live in {workspace}", workspace=workspace)
        assert keys.record("R", made["id"], workspaceKey=workspace)["objectTypeKey"] == keys.key(
            "R"
        )
        change_set = keys.change_set(workspace)
        assert change_set["modelReleaseId"] == release
        staged = keys.made("R", f"Published in {workspace}", change_set=change_set)
        keys.publish(change_set, workspace)
        response = consumer_object(keys, staged["id"], workspace=workspace)
        assert ok(response)[keys.key("Capi.name")] == f"Published in {workspace}"
        assert response.headers["RDM-Workspace"] == workspace


@pytest.mark.journey("J37.8")
@pytest.mark.structures(*BOTH)
def test_raising_the_schema_version_is_no_migration(world):
    """Given the default workspace on X with a record. When X′ (X raised to 0.10) is activated, and
    X again. Then neither needs a migration nor a contract version, and the record keeps its
    version."""
    x = _model(world)["releaseId"]
    record = world.made("R", "Kept as it is")
    raised = world.install(_raised(world, world.configuration.model), name="Raised")

    ok(world.activate(raised["id"]))
    assert _model(world)["releaseId"] == raised["id"]
    assert world.record("R", record["id"])["version"] == record["version"]
    ok(world.activate(x))
    assert _model(world)["releaseId"] == x
    assert world.record("R", record["id"])["version"] == record["version"]


@pytest.mark.journey("J37.8")
@pytest.mark.structures(*BOTH)
def test_a_migration_across_versions_converts_by_declarations(world):
    """Given a workspace on X1 (0.9) and X2′: X1 raised to 0.10 with the count an integer and the
    note dropped. When the workspace is migrated to X2′. Then the preview lists exactly the two
    conversions and the two losses those declarations cause, no item about the schema version; once
    confirmed the workspace runs X2′ at 0.10 and its counts read as integers."""
    key, made, _citation = _workspace(world)
    k = _probe(world)
    target = world.install(_raised(world, _x2(world, "count-integer", "drop-note")), name="Probe")

    job = _previewed(world, key, target["id"])
    assert job["migration"]["counts"] == {
        "conversion": 2,
        "reclassified": 0,
        "loss": 2,
        "refused": 0,
    }
    rows = _rows(world, job["id"])
    assert {row["code"] for row in rows} == {
        "VALUE_CONVERTED",
        "VALUE_NOT_CONVERTIBLE",
        "ATTRIBUTE_BINDING_IN_USE",
    }
    assert {(row["objectId"], row.get("attributeTypeKey")) for row in rows} == {
        (made["twelve"]["id"], k.count),
        (made["forty"]["id"], k.count),
        (made["words"]["id"], k.count),
        (made["twelve"]["id"], k.note),
    }

    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    assert _model(world, key)["releaseId"] == target["id"]
    assert ok(world.api.get("/model", workspaceKey=key))["schemaVersion"] == NEWEST
    assert _value(_read(world, key, made["forty"]), k.count) == 40


@pytest.mark.journey("J37.8")
@pytest.mark.structures(*BOTH)
def test_a_draft_on_an_older_version_raised_and_lowered(world):
    """Given a draft based on X's release (0.9). When a navigation group is added, the draft raised
    to 0.10, installed, and lowered to 0.9 again. Then the group is invalid at its path naming 0.10
    until the draft is raised; raised, it installs; lowered with the group declared, it is invalid
    at the navigation path again and does not install."""
    base = _model(world)["releaseId"]
    draft = _draft(world, copy.deepcopy(world.configuration.model), baseReleaseId=base)
    group = {"kind": "addNavigationGroup", "applicationKey": world.app("R"), "label": "Grouped"}

    _navigation_refusal(ok(_operate(world, draft, group)))
    raised = ok(
        _operate(
            world,
            draft,
            {"kind": "setRelease", "schemaVersion": NEWEST, "version": f"{uuid4().hex[:6]}"},
        )
    )
    assert raised["valid"] is True
    installed = ok(_install(world, draft), 201)
    assert installed["schemaVersion"] == NEWEST

    _navigation_refusal(ok(_operate(world, draft, {"kind": "setRelease", "schemaVersion": "0.9"})))
    refused(_install(world, draft), 422, "INVALID_MODEL")


@pytest.mark.journey("J37.8")
@pytest.mark.parametrize("version", ["0.4", "after-newest"])
@pytest.mark.structures(*BOTH)
def test_installation_outside_the_window_is_refused(world, version):
    """Given a draft naming schema 0.4, or the version after the newest. When it is installed,
    validated and set to that version by an operation. Then installation is refused naming the
    version and the window, and installs nothing; validation is invalid at /schemaVersion; the
    operation is refused."""
    schema = _after_newest(world) if version == "after-newest" else version
    model = copy.deepcopy(world.configuration.model)
    model["schemaVersion"] = schema
    model["release"]["version"] += f"-{uuid4().hex[:6]}"
    releases = ok(world.api.get("/model-releases", pageSize=500))["items"]

    error = refused(_install(world, _draft(world, model)), 422, "UNSUPPORTED_SCHEMA_VERSION")
    assert error["details"]["schemaVersion"] == schema
    assert error["details"]["supportedSchemaVersions"] == _window(world)
    assert error["details"]["operation"] == "install"
    assert ok(world.api.get("/model-releases", pageSize=500))["items"] == releases

    validation = ok(world.api.post("/model-validations", {"model": model}))
    assert validation["valid"] is False
    assert [d["path"] for d in validation["diagnostics"]] == ["/schemaVersion"]

    draft = _draft(world, copy.deepcopy(world.configuration.model))
    refused(
        _operate(world, draft, {"kind": "setRelease", "schemaVersion": schema}),
        422,
        "INVALID_OPERATION",
    )


@pytest.mark.journey("J37.8")
@pytest.mark.structures(*BOTH)
def test_a_workspace_on_a_release_after_the_window(world):
    """Given a workspace on Y's release, which a later engine left at a schema after the window (the
    state arrives from outside the API: the schema is set in the database). When the engine starts.
    Then only that workspace answers unavailable naming its schema and the window, the default
    workspace serves; an activation into it is refused and changes nothing."""
    other = _other(world)
    y = other.install(other.configuration.model, name="Other model")
    key = _on(world, y["id"])
    later = _after_newest(world)
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE model_releases SET schema_version = :v, model_json = CAST(:m AS json) WHERE public_id = :id"
            ),
            {
                "v": later,
                "m": json.dumps({**other.configuration.model, "schemaVersion": later}),
                "id": y["id"],
            },
        )
    engine.dispose()

    with application(world.configuration, world.database) as restarted:
        error = refused(
            restarted.api.get("/model", workspaceKey=key), 503, "MODEL_REGISTRY_UNAVAILABLE"
        )
        assert error["details"]["schemaVersion"] == later
        assert error["details"]["supportedSchemaVersions"] == _window(restarted)
        restarted.made("R", "Still served")
        before = ok(restarted.api.get(f"/workspaces/{key}/model"))
        refused(
            restarted.activate(_model(restarted)["releaseId"], key),
            422,
            "UNSUPPORTED_SCHEMA_VERSION",
        )
        assert ok(restarted.api.get(f"/workspaces/{key}/model")) == before


@pytest.mark.journey("J37.8")
@pytest.mark.structures("R")
def test_the_log_names_the_recovery_for_a_release_after_the_window(configuration, databases):  # noqa: F811
    """Given a database whose default workspace runs a release a later engine left at a schema after
    the window (set in the database, as J12.6 sets 0.4). When the service starts. Then the log names
    the schema, the window and that a later RDM Engine is needed, and not the schema 0.4 command."""
    url = _clone(databases, scenario_seed(configuration))
    later = _after_newest()
    model = {**configuration.model, "schemaVersion": later}
    execute(
        url,
        "UPDATE model_releases SET schema_version = :v, model_json = CAST(:m AS json) WHERE id = "
        "(SELECT model_release_id FROM workspace_models WHERE workspace_key = 'default')",
        v=later,
        m=json.dumps(model),
    )
    with serve(configuration, url) as service:
        [record] = service.errors()
        message = record.getMessage()
    assert f"schema {later}" in message and "later RDM Engine" in message, message
    assert "model_schema_upgrade" not in message
    assert "Traceback" not in message and record.exc_info is None


@pytest.mark.journey("J37.8")
@pytest.mark.structures("R")
def test_a_model_file_outside_the_window_refuses_to_start(configuration, databases, tmp_path):  # noqa: F811
    """When the service starts with RDM_MODEL_PATH naming a model of a schema after the window. Then
    it refuses to start with a message naming the setting, the file, its version and the window."""
    model = copy.deepcopy(configuration.model)
    model["schemaVersion"] = "9.0"
    path = tmp_path / "later.json"
    path.write_text(json.dumps(model))
    with (
        pytest.raises(RuntimeError) as refusal,
        serve(configuration, _clone(databases), RDM_MODEL_PATH=str(path)),
    ):
        pass
    message = str(refusal.value)
    for phrase in ("RDM_MODEL_PATH", str(path), "schema 9.0", "0.5", NEWEST):
        assert phrase in message, message
