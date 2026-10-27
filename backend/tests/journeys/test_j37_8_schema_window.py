"""J37.8 — The schema-language window (USER_JOURNEYS.md, Base 0.11 V4, 0.12 L2a).

Before 1.0 the window holds the one version a release writes (D439, D441). A version outside it is
refused wherever it is named, and a stored release of one makes only its workspaces unavailable.
Naming no configuration key.
"""

import copy
import json
from uuid import uuid4

import pytest
from scenario import application, ok, refused, scenario_seed
from service import execute, serve
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j12_run_the_service import _clone, databases  # noqa: F401 (fixture)
from test_j36_workspace_models import BOTH, _model, _on, _other

from app.engine.model.compiler import SCHEMA_VERSIONS

NEWEST = "0.10"


def _window(world):
    return ok(world.api.get("/system"))["schemaLanguages"]


def _after_newest(world=None):
    """A schema version after the newest in the window."""
    major, minor = SCHEMA_VERSIONS[-1].split(".")
    return f"{major}.{int(minor) + 1}"


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


@pytest.mark.journey("J37.8")
@pytest.mark.parametrize("version", ["0.9", "after-newest"])
@pytest.mark.structures(*BOTH)
def test_installation_outside_the_window_is_refused(world, version):
    """Given a draft naming schema 0.9 (which left the window), or the version after the newest. When it is installed,
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
    the window (set in the database). When the service starts. Then the log names
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
    for phrase in ("RDM_MODEL_PATH", str(path), "schema 9.0", NEWEST):
        assert phrase in message, message
