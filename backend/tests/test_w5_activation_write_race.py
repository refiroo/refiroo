"""0.8 W5: a live write resolved under release A must not commit after release B activates.

Each case holds one live write after it resolved the active model, activates a release B under
which that write is invalid, then lets the write continue. Draft-base capture is the protected
reference: it already rechecks the selection under the runtime-state row lock.
"""

import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
from wp8_support import create_workspace, unique_key

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import (
    AttributeValue,
    ChangeSetBase,
    ModelRelease,
    ModelRuntimeState,
    ObjectRelation,
    RdmObject,
)
from app.models.schema import EngineModel

HOLD_TIMEOUT = 10


@pytest.fixture
def client(monkeypatch, migrated_database) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", migrated_database("w5.db"))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    model_registry.clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _create(client: TestClient, workspace_key: str, object_type_key: str, name: str, *,
            parent: str | None = None, **attributes) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-systems" if object_type_key.startswith("system") else "rdm-master",
            "objectTypeKey": object_type_key,
            "name": name,
            "parentObjectId": parent,
            "attributes": [
                {"attributeTypeKey": key, "value": value} for key, value in attributes.items()
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _candidate(client: TestClient, change: Callable[[dict], None]) -> ModelRelease:
    source = client.get("/api/v1/model").json()
    change(source)
    source["release"]["version"] = f"0.8.0-w5-{unique_key('b')}"
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, EngineModel.model_validate(source))
        session.commit()
        return release


def _system_type_required(source: dict) -> None:
    system = next(item for item in source["objectTypes"] if item["key"] == "system")
    binding = next(item for item in system["attributes"] if item["attributeTypeKey"] == "system-type")
    binding["required"] = True


def _domain_representation_one_to_one(source: dict) -> None:
    pair = next(
        item
        for item in source["objectTypeRelations"]
        if item["relationTypeKey"] == "reference-has-system-representation"
        and item["fromObjectTypeKey"] == "domain"
    )
    pair["cardinality"] = "one-to-one"


def _activate(client: TestClient, release: ModelRelease) -> httpx.Response:
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        active = session.get(ModelRelease, state.active_model_release_id)
        assert active is not None
        expected_version, active_id = state.version, active.public_id
    return client.post(
        f"/api/v1/model-releases/{release.public_id}/activation",
        json={"expectedRuntimeVersion": expected_version, "expectedActiveReleaseId": active_id},
    )


def _race(monkeypatch, client: TestClient, release: ModelRelease,
          write: Callable[[], httpx.Response]) -> httpx.Response:
    """Hold ``write`` after it resolved release A, activate ``release``, then let it continue."""
    resolved, activated = threading.Event(), threading.Event()
    original = model_registry.resolve_active
    held = False

    def resolve_then_hold(session):
        nonlocal held
        snapshot = original(session)
        if not held:
            held = True
            resolved.set()
            assert activated.wait(HOLD_TIMEOUT)
        return snapshot

    monkeypatch.setattr(model_registry, "resolve_active", resolve_then_hold)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(write)
        assert resolved.wait(HOLD_TIMEOUT)
        activation = _activate(client, release)
        activated.set()
        response = pending.result(timeout=HOLD_TIMEOUT)
    monkeypatch.setattr(model_registry, "resolve_active", original)
    assert activation.status_code == 200, activation.text
    return response


def _assert_stale_release_refused(response: httpx.Response, release: ModelRelease) -> None:
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "MODEL_RELEASE_CHANGED"
    assert error["details"]["activeReleaseId"] == release.public_id


def test_object_write_resolved_under_a_is_refused_after_b_activates(monkeypatch, client):
    workspace_key = unique_key("w5-object")
    create_workspace(client, workspace_key)
    release = _candidate(client, _system_type_required)
    name = f"System {unique_key('held')}"

    response = _race(
        monkeypatch,
        client,
        release,
        lambda: client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace_key,
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system",
                "name": name,
                "attributes": [
                    {"attributeTypeKey": "system-code", "value": unique_key("sys")},
                ],
            },
        ),
    )

    _assert_stale_release_refused(response, release)
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).where(RdmObject.name == name)) == 0
    # The same request, resolved under B, is rejected by ordinary validation.
    retried = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-systems",
            "objectTypeKey": "system",
            "name": name,
            "attributes": [
                {"attributeTypeKey": "system-code", "value": unique_key("sys")},
            ],
        },
    )
    assert retried.status_code == 422, retried.text


def test_attribute_write_resolved_under_a_is_refused_after_b_activates(monkeypatch, client):
    workspace_key = unique_key("w5-attribute")
    create_workspace(client, workspace_key)
    system = _create(
        client, workspace_key, "system", "System",
        **{"system-code": unique_key("sys"), "system-type": "erp"},
    )
    release = _candidate(client, _system_type_required)

    response = _race(
        monkeypatch,
        client,
        release,
        lambda: client.delete(
            f"/api/v1/objects/system/{system['id']}/attributes/system-type",
            params={"expectedVersion": system["version"]},
        ),
    )

    _assert_stale_release_refused(response, release)
    with SessionLocal() as session:
        stored = session.scalar(
            select(func.count()).where(
                AttributeValue.object_id == system["id"],
                AttributeValue.attribute_type_key == "system-type",
            )
        )
        assert stored == 1


def test_relation_write_resolved_under_a_is_refused_after_b_activates(monkeypatch, client):
    workspace_key = unique_key("w5-relation")
    create_workspace(client, workspace_key)
    system = _create(client, workspace_key, "system", "System", **{"system-code": unique_key("sys")})
    first, second = (
        _create(
            client, workspace_key, "system-value", f"Value {index}", parent=system["id"],
            **{"value-code": unique_key("v"), "value-name": f"Value {index}"},
        )
        for index in (1, 2)
    )
    domain = _create(client, workspace_key, "domain", "Domain", **{"domain-code": unique_key("d")})

    def represent(value: dict) -> httpx.Response:
        return client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": domain["id"],
                "toObjectId": value["id"],
            },
        )

    assert represent(first).status_code == 201
    release = _candidate(client, _domain_representation_one_to_one)

    response = _race(monkeypatch, client, release, lambda: represent(second))

    _assert_stale_release_refused(response, release)
    with SessionLocal() as session:
        stored = session.scalar(
            select(func.count()).where(
                ObjectRelation.from_object_id == domain["id"],
                ObjectRelation.relation_type_key == "reference-has-system-representation",
            )
        )
        assert stored == 1


def test_activation_waits_for_a_flushed_live_write_and_then_sees_it(monkeypatch, client):
    workspace_key = unique_key("w5-reverse")
    create_workspace(client, workspace_key)
    release = _candidate(client, _system_type_required)
    name = f"System {unique_key('first')}"
    flushed, released = threading.Event(), threading.Event()

    def hold_after_recheck(session: Session) -> None:
        # Runs after the W5 recheck, which flushed the write and so holds its row locks.
        if "resolved_active_model_release_db_id" not in session.info or session.info.get("w5_held"):
            return
        session.info["w5_held"] = True
        flushed.set()
        assert released.wait(HOLD_TIMEOUT)

    event.listen(Session, "before_commit", hold_after_recheck)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            write = pool.submit(
                client.post,
                "/api/v1/objects",
                json={
                    "workspaceKey": workspace_key,
                    "applicationKey": "rdm-systems",
                    "objectTypeKey": "system",
                    "name": name,
                    "attributes": [{"attributeTypeKey": "system-code", "value": unique_key("sys")}],
                },
            )
            assert flushed.wait(HOLD_TIMEOUT)
            activation = pool.submit(_activate, client, release)
            time.sleep(0.3)
            assert not activation.done()
            released.set()
            written, activated = write.result(HOLD_TIMEOUT), activation.result(HOLD_TIMEOUT)
    finally:
        event.remove(Session, "before_commit", hold_after_recheck)

    assert written.status_code == 201, written.text
    assert activated.status_code == 409, activated.text
    assert activated.json()["error"]["code"] == "MODEL_MIGRATION_REQUIRED"


def test_draft_base_capture_resolved_under_a_is_refused_after_b_activates(monkeypatch, client):
    workspace_key = unique_key("w5-capture")
    create_workspace(client, workspace_key)
    release = _candidate(client, _system_type_required)

    response = _race(
        monkeypatch,
        client,
        release,
        lambda: client.post(
            f"/api/v1/workspaces/{workspace_key}/change-sets", json={"source": "currentLive"}
        ),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "CHANGE_SET_SNAPSHOT_RETRY"
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count()).where(ChangeSetBase.workspace_key == workspace_key)
            )
            == 0
        )
