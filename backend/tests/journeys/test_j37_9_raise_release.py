"""J37.9 — A workspace that cannot be served (USER_JOURNEYS.md, 0.12 UW1).

A workspace whose release is of a schema that left the window answers 503, says so in the workspace
list, and its release is brought up to date through the API by someone who may install models: a
preview that changes nothing, then a confirmation against the hash the preview named. The state
arrives from outside the API (the schema is set in the database), as after an engine upgrade.
"""

import json
import time

import pytest
from scenario import W1, application, ok, refused
from service import execute  # noqa: F401 (kept beside the harness imports)
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j36_workspace_models import BOTH, _on, _other
from test_j40_authorization import _client

from app.engine.model.compiler import SCHEMA_VERSIONS

NEWEST = SCHEMA_VERSIONS[-1]


def _raising(release_id: str) -> str:
    return f"/model-releases/{release_id}/raising"


def _stage_old(world, schema="0.9", version="1.0.0"):
    """A workspace on another model's release stored as an earlier engine left it; its key and the
    release. The stored hash is the earlier engine's, not the present one."""
    other = _other(world)
    model = {
        **other.configuration.model,
        "release": {**other.configuration.model["release"], "version": version},
    }
    release = world.install(model, name="Other model")
    key = _on(world, release["id"])
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE model_releases SET schema_version = :v, model_hash = :h, "
                "model_json = CAST(:m AS json) WHERE public_id = :id"
            ),
            {
                "v": schema,
                "m": json.dumps({**model, "schemaVersion": schema}),
                "id": release["id"],
                "h": "stale-hash" if version == "1.0.0" else f"stale-hash-{version}",
            },
        )
    engine.dispose()
    return key, release


def _availability(world, key):
    return ok(world.api.get(f"/workspaces/{key}"))["availability"]


@pytest.mark.journey("J37.9")
@pytest.mark.structures(*BOTH)
def test_an_unavailable_workspace_says_why_and_a_raising_serves_it_again(world):
    """Given a workspace whose release is stored in schema 0.9, and the default workspace on an
    ordinary one. When the service starts and the workspaces are listed. Then the first reads
    unavailable with the reason, the release, its schema, the window and that it can be raised, and
    the default reads available. When the raising is previewed, then it names the schemas and the
    workspaces and changes nothing. When it is confirmed, then the same service serves the workspace,
    the list reads available and the release has the window's schema; previewing again is `422
    RELEASE_NOT_RAISABLE`."""
    key, release = _stage_old(world)
    with application(world.configuration, world.database) as service:
        refused(service.api.get("/model", workspaceKey=key), 503, "MODEL_REGISTRY_UNAVAILABLE")
        listed = {
            item["key"]: item["availability"]
            for item in ok(service.api.get("/workspaces", pageSize=500))["items"]
        }
        assert listed[W1] == {"state": "available"}
        assert listed[key] == {
            "state": "unavailable",
            "reason": "schemaLeftWindow",
            "releaseId": release["id"],
            "schemaVersion": "0.9",
            "supportedSchemaVersions": list(SCHEMA_VERSIONS),
            "raisable": True,
        }
        assert listed[key] == _availability(service, key)

        preview = ok(service.api.post(_raising(release["id"]), {"confirm": False}))
        assert preview["applied"] is False
        assert (preview["releaseId"], preview["schemaFrom"], preview["schemaTo"]) == (
            release["id"],
            "0.9",
            NEWEST,
        )
        assert preview["modelHash"] == "stale-hash"
        assert preview["workspaces"] == [{"key": key, "label": key.title()}]
        assert ok(service.api.get(f"/model-releases/{release['id']}"))["schemaVersion"] == "0.9"
        assert _availability(service, key)["state"] == "unavailable"

        applied = ok(
            service.api.post(
                _raising(release["id"]),
                {"confirm": True, "expectedModelHash": preview["modelHash"]},
            )
        )
        assert applied["applied"] is True and applied["modelHash"] != "stale-hash"
        assert applied["workspaces"] == preview["workspaces"]
        stored = ok(service.api.get(f"/model-releases/{release['id']}"))
        assert stored["schemaVersion"] == NEWEST and stored["modelHash"] == applied["modelHash"]
        assert stored["key"] == release["key"] and stored["version"] == release["version"]
        ok(service.api.get("/model", workspaceKey=key))
        assert _availability(service, key) == {"state": "available"}

        error = refused(
            service.api.post(_raising(release["id"]), {"confirm": False}),
            422,
            "RELEASE_NOT_RAISABLE",
        )
        assert error["details"]["schemaVersion"] == NEWEST
        assert error["details"]["supportedSchemaVersions"] == list(SCHEMA_VERSIONS)
        refused(
            service.api.post(_raising("no-such-release"), {"confirm": False}),
            404,
            "MODEL_RELEASE_NOT_FOUND",
        )


@pytest.mark.journey("J37.9")
@pytest.mark.structures("R")
def test_a_raising_needs_the_right_to_install_and_the_previewed_hash(world):
    """Given a workspace whose release is stored in schema 0.9. When a Reader previews it, then
    `403 FORBIDDEN`. When a confirmation names a hash other than the release's, then `409
    MODEL_HASH_CHANGED` and nothing changed; a confirmation without a hash is a validation error."""
    key, release = _stage_old(world)
    with application(world.configuration, world.database) as service:
        _client_row, reader = _client(service, "Reader", ("reader", {"workspaceKey": W1}))
        refused(reader.api.post(_raising(release["id"]), {"confirm": False}), 403, "FORBIDDEN")
        error = refused(
            service.api.post(
                _raising(release["id"]), {"confirm": True, "expectedModelHash": "not-the-hash"}
            ),
            409,
            "MODEL_HASH_CHANGED",
        )
        assert error["details"]["currentModelHash"] == "stale-hash"
        refused(
            service.api.post(_raising(release["id"]), {"confirm": True}),
            422,
            "REQUEST_VALIDATION_ERROR",
        )
        assert _availability(service, key)["state"] == "unavailable"


@pytest.mark.journey("J37.9")
@pytest.mark.structures("R", "R.u")
def test_a_service_that_started_with_nothing_to_serve_serves_and_runs_jobs_after_a_raising(world):
    """Given every release stored in schema 0.9, as an engine upgrade leaves them. When the
    service starts, `/health` is `503` and no job runs; after the default workspace's release is
    raised through the API, the same process is ready, and a background batch is run by its job
    worker, without a restart (R-F9)."""
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE model_releases SET schema_version = '0.9', "
                "model_hash = 'stale-' || id, "
                "model_json = jsonb_set(model_json::jsonb, '{schemaVersion}', '\"0.9\"')::json"
            )
        )
        releases = connection.execute(
            text(
                "SELECT r.public_id, r.model_hash FROM model_releases r "
                "JOIN workspace_models m ON m.model_release_id = r.id"
            )
        ).all()
    engine.dispose()
    with application(world.configuration, world.database, worker=True) as service:
        assert service.api.get("/health").status_code == 503
        refused(service.api.get("/model"), 503, "MODEL_REGISTRY_UNAVAILABLE")
        for release_id, model_hash in dict(releases).items():
            ok(
                service.api.post(
                    _raising(release_id), {"confirm": True, "expectedModelHash": model_hash}
                )
            )
        assert service.api.get("/health").status_code == 200
        item = {
            "op": "create",
            "applicationKey": service.app("R"),
            "objectTypeKey": service.key("R"),
            "name": "After the raising",
            "attributes": [
                {"attributeTypeKey": k, "value": v}
                for k, v in {
                    **service.required_values("R"),
                    service.key("R.u"): "After-001",
                }.items()
            ],
        }
        job = ok(
            service.api.post(
                "/batches",
                {"workspaceKey": W1, "policy": "independent", "run": "background", "items": [item]},
            ),
            202,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = ok(service.api.get(f"/jobs/{job['id']}"))["state"]
            if state in ("completed", "failed"):
                break
            time.sleep(0.3)
        assert state == "completed"


@pytest.mark.journey("J37.9")
@pytest.mark.structures("R")
def test_a_page_of_unavailable_workspaces_reads_the_stored_releases_once(world, monkeypatch):
    """Given two workspaces on releases stored in schema 0.9. When the workspace list is read, both
    read unavailable and raisable, and the stored releases were read once for the page, not once per
    release."""
    from app.engine.model import availability, raising

    first, _ = _stage_old(world)
    second, _ = _stage_old(world, version="1.0.1")
    reads = []
    real = raising.hashes_taken
    for module in (raising, availability):
        monkeypatch.setattr(
            module, "hashes_taken", lambda s: reads.append(1) or real(s), raising=False
        )
    with application(world.configuration, world.database) as service:
        listed = {
            item["key"]: item["availability"]
            for item in ok(service.api.get("/workspaces", pageSize=500))["items"]
        }
    assert listed[first]["raisable"] is True and listed[second]["raisable"] is True
    assert len(reads) == 1
