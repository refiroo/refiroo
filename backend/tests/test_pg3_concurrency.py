"""0.9.0-alpha.1 PG3: live writes of one workspace serialize on its row lock (PG-D5).

Each race holds one write where it stands (after it took the workspace lock, or with its checks done
and its rows flushed, just before it commits), starts a second write on another connection,
observes that write waiting on PostgreSQL's lock, and then lets the first one go. Without the lock
the second write would read before the first commits, pass the same check and commit too; with it,
the second write reads what the first committed and is refused with its single write's code.

Then: workspaces write in parallel, an activation does not wait for the workspace lock, and a
background job holds the lock for one chunk only, answers a cancel request while a chunk runs and
hands its job to another worker through the lease (D28).
"""

import base64
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text, update
from sqlalchemy.orm import Session
from test_w5_activation_write_race import _activate, _candidate
from wp8_support import create_change_set, create_workspace, unique_key

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.jobs.worker import JobWorker, WorkerSettings
from app.engine.model.registry import model_registry
from app.engine.records import rules
from app.engine.records.writes import ChangeSetWrites, LiveWrites
from app.main import create_app
from app.models.database import Job, RdmObject

HOLD_TIMEOUT = 10
WORKSPACE_LOCK = "%FROM workspaces%FOR NO KEY UPDATE%"
# The assignment row activation holds for update (0.11 M1).
RUNTIME_STATE_LOCK = "%FROM workspace_models%FOR UPDATE%"


@pytest.fixture
def client(monkeypatch, migrated_database) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", migrated_database("pg3.db"))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    model_registry.clear()
    application = create_app()
    application.state.run_job_worker = False
    with TestClient(application) as test_client:
        yield test_client
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


# --- holding a write ------------------------------------------------------------------------------


class Hold:
    """Hold the ``nth`` live write (counted from ``arm``) that reaches ``point`` until ``release``.

    ``lock``: just after ``LiveWrites._begin`` took the workspace lock. ``commit``: in the session's
    ``before_commit``, after the engine's own commit checks flushed and rechecked the write.
    """

    def __init__(self, monkeypatch, point: str) -> None:
        self.point = point
        self.reached, self.released = threading.Event(), threading.Event()
        self._armed, self._seen, self._nth = False, 0, 1
        self._guard = threading.Lock()
        original = LiveWrites._begin
        hold = self

        def begin(writes: LiveWrites) -> None:
            original(writes)
            writes.session.info["pg3_live_write"] = True
            if hold.point == "lock":
                hold._maybe_hold()

        monkeypatch.setattr(LiveWrites, "_begin", begin)
        change_set_writes = ChangeSetWrites.__init__

        def change_set_write(writes: ChangeSetWrites, session: Session, change_set: Any) -> None:
            change_set_writes(writes, session, change_set)
            session.info["pg3_live_write"] = True

        # A change set write is held at its commit too (the ``commit`` point only).
        monkeypatch.setattr(ChangeSetWrites, "__init__", change_set_write)
        event.listen(Session, "before_commit", self._before_commit)

    def arm(self, nth: int = 1) -> None:
        self._armed, self._seen, self._nth = True, 0, nth

    def release(self) -> None:
        self.released.set()

    def close(self) -> None:
        self.released.set()
        event.remove(Session, "before_commit", self._before_commit)

    def _before_commit(self, session: Session) -> None:
        if session.info.pop("pg3_live_write", None) and self.point == "commit":
            self._maybe_hold()

    def _maybe_hold(self) -> None:
        with self._guard:
            if not self._armed:
                return
            self._seen += 1
            if self._seen != self._nth:
                return
            self._armed = False
        self.reached.set()
        assert self.released.wait(HOLD_TIMEOUT), "the held write was never released"


@pytest.fixture
def at_commit(monkeypatch) -> Iterator[Hold]:
    hold = Hold(monkeypatch, "commit")
    yield hold
    hold.close()


@pytest.fixture
def at_lock(monkeypatch) -> Iterator[Hold]:
    hold = Hold(monkeypatch, "lock")
    yield hold
    hold.close()


def waiting_on(pattern: str, count: int = 1) -> bool:
    """Whether ``count`` sessions of this database wait on a lock in a statement like ``pattern``."""
    deadline = time.monotonic() + HOLD_TIMEOUT
    while time.monotonic() < deadline:
        # A new connection each time: pg_stat_activity is a snapshot per transaction.
        with get_engine().connect() as connection:
            waiting = connection.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                    "AND wait_event_type = 'Lock' AND query LIKE :pattern"
                ),
                {"pattern": pattern},
            )
        if waiting >= count:
            return True
        time.sleep(0.05)
    return False


def race(
    hold: Hold, first: Callable[[], httpx.Response], second: Callable[[], httpx.Response]
) -> tuple[httpx.Response, httpx.Response]:
    """Hold ``first``, show ``second`` waiting for the workspace lock, then let both finish."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        hold.arm()
        held = pool.submit(first)
        try:
            assert hold.reached.wait(HOLD_TIMEOUT), "the first write never reached its hold"
            waiting = pool.submit(second)
            assert waiting_on(WORKSPACE_LOCK), "the second write did not wait for the lock"
            assert not waiting.done()
        finally:
            hold.release()
        return held.result(HOLD_TIMEOUT), waiting.result(HOLD_TIMEOUT)


# --- records --------------------------------------------------------------------------------------

APPLICATIONS = {
    "domain": "rdm-master",
    "codelist": "rdm-master",
    "master-value": "rdm-master",
    "system": "rdm-systems",
    "system-value": "rdm-systems",
    "language": "rdm-translations",
    "translation-group": "rdm-translations",
    "translation": "rdm-translations",
}


def post_object(
    client: TestClient,
    workspace_key: str,
    object_type_key: str,
    *,
    parent: str | None = None,
    initial: list[dict] | None = None,
    **attributes: Any,
) -> httpx.Response:
    return client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": APPLICATIONS[object_type_key],
            "objectTypeKey": object_type_key,
            "name": unique_key(object_type_key),
            "parentObjectId": parent,
            "attributes": [
                {"attributeTypeKey": key.replace("_", "-"), "value": value}
                for key, value in attributes.items()
            ],
            "initialRelations": initial or [],
        },
    )


def created(response: httpx.Response) -> dict:
    assert response.status_code == 201, response.text
    return response.json()


def domain(client, workspace_key: str, code: str | None = None) -> dict:
    return created(post_object(client, workspace_key, "domain", domain_code=code or unique_key("d")))


def master_value(client, workspace_key: str, parent: str) -> dict:
    return created(
        post_object(
            client,
            workspace_key,
            "master-value",
            parent=parent,
            master_id=unique_key("m"),
            value_code=unique_key("v"),
            value_name="Value",
        )
    )


def codelist(client, workspace_key: str) -> dict:
    owner = domain(client, workspace_key)
    return created(
        post_object(
            client, workspace_key, "codelist", parent=owner["id"], codelist_code=unique_key("c")
        )
    )


def system_value(client, workspace_key: str, system: str) -> dict:
    return created(
        post_object(
            client,
            workspace_key,
            "system-value",
            parent=system,
            value_code=unique_key("sv"),
            value_name="System value",
        )
    )


def system(client, workspace_key: str) -> dict:
    return created(post_object(client, workspace_key, "system", system_code=unique_key("s")))


def relate(client, relation_type_key: str, source: dict, target: dict) -> httpx.Response:
    return client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": relation_type_key,
            "fromObjectId": source["id"],
            "toObjectId": target["id"],
        },
    )


def move(client, item: dict, parent: dict) -> httpx.Response:
    return client.patch(
        f"/api/v1/objects/{item['objectTypeKey']}/{item['id']}",
        json={"expectedVersion": item["version"], "parentObjectId": parent["id"]},
    )


def refused(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


@pytest.fixture
def workspace(client) -> str:
    key = unique_key("pg3")
    create_workspace(client, key)
    return key


def test_two_creates_racing_for_one_unique_value(client, workspace, at_commit):
    code = unique_key("same")
    first, second = race(
        at_commit,
        lambda: post_object(client, workspace, "domain", domain_code=code),
        lambda: post_object(client, workspace, "domain", domain_code=code),
    )
    created(first)
    refused(second, 409, "DUPLICATE_ATTRIBUTE_VALUE")


def test_two_moves_racing_into_a_parent_cycle(client, workspace, at_commit):
    owner = codelist(client, workspace)
    one, two = master_value(client, workspace, owner["id"]), master_value(client, workspace, owner["id"])
    first, second = race(at_commit, lambda: move(client, one, two), lambda: move(client, two, one))
    assert first.status_code == 200, first.text
    refused(second, 422, "PARENT_CYCLE")


def test_two_relations_racing_for_a_cardinality_limit(client, workspace, at_commit):
    # reference-has-system-representation is one-to-many: a system value has one source.
    target = system_value(client, workspace, system(client, workspace)["id"])
    one, two = domain(client, workspace), domain(client, workspace)
    first, second = race(
        at_commit,
        lambda: relate(client, "reference-has-system-representation", one, target),
        lambda: relate(client, "reference-has-system-representation", two, target),
    )
    created(first)
    refused(second, 409, "CARDINALITY_VIOLATION")


def test_a_required_relation_racing_with_the_deletion_of_its_source(client, workspace, at_commit):
    """A translation needs its incoming ``object-has-translation``; its source cannot be deleted
    from under it."""
    source = domain(client, workspace)
    language = created(
        post_object(client, workspace, "language", language_code=unique_key("l"))
    )
    group = created(
        post_object(
            client, workspace, "translation-group", parent=language["id"], group_code="g"
        )
    )
    translation = {
        "relationTypeKey": "object-has-translation",
        "direction": "incoming",
        "otherObjectId": source["id"],
    }
    first, second = race(
        at_commit,
        lambda: post_object(
            client,
            workspace,
            "translation",
            parent=group["id"],
            initial=[translation],
            translated_name="Name",
        ),
        lambda: client.delete(
            f"/api/v1/objects/domain/{source['id']}", params={"expectedVersion": source["version"]}
        ),
    )
    created(first)
    refused(second, 409, "OBJECT_HAS_DEPENDANTS")


def mapping(client, workspace_key: str, source: dict, target: dict) -> httpx.Response:
    return client.put(
        f"/api/v1/workspaces/{workspace_key}/mappings",
        json={
            "relationTypeKey": "system-value-maps-to-master",
            "fromObjectTypeKey": "system-value",
            "toObjectTypeKey": "master-value",
            "direction": "outgoing",
            "sourceObjectId": source["id"],
            "expectedMappingVersion": 0,
            "targetObjectId": target["id"],
        },
    )


def test_two_mapping_saves_racing_for_one_relation_set_version(client, workspace, at_commit):
    owner = codelist(client, workspace)
    one, two = master_value(client, workspace, owner["id"]), master_value(client, workspace, owner["id"])
    source = system_value(client, workspace, system(client, workspace)["id"])
    first, second = race(
        at_commit,
        lambda: mapping(client, workspace, source, one),
        lambda: mapping(client, workspace, source, two),
    )
    assert first.status_code == 200, first.text
    refused(second, 409, "MAPPING_VERSION_CONFLICT")


def test_a_relation_create_and_a_mapping_save_on_one_edge_do_not_deadlock(
    client, workspace, at_lock
):
    """H3's deadlock: the create inserted the edge before advancing the set versions, the mapping
    save claimed a set version before inserting the edge. Both now take the workspace lock first."""
    owner = codelist(client, workspace)
    target = master_value(client, workspace, owner["id"])
    source = system_value(client, workspace, system(client, workspace)["id"])
    first, second = race(
        at_lock,
        lambda: relate(client, "system-value-maps-to-master", source, target),
        lambda: mapping(client, workspace, source, target),
    )
    created(first)
    refused(second, 409, "MAPPING_VERSION_CONFLICT")


def test_two_relations_racing_into_one_matrix_cell_keep_its_stored_state(
    client, workspace, at_commit
):
    """Both system values sit in one cell of ``master-values-by-system`` (row: the master value,
    column: their system); the fixture's teardown verifies every stored state."""
    owner = codelist(client, workspace)
    row = master_value(client, workspace, owner["id"])
    column = system(client, workspace)
    one, two = system_value(client, workspace, column["id"]), system_value(client, workspace, column["id"])
    first, second = race(
        at_commit,
        lambda: relate(client, "system-value-maps-to-master", one, row),
        lambda: relate(client, "system-value-maps-to-master", two, row),
    )
    created(first)
    created(second)
    with SessionLocal() as session:
        assert matrix_states.verify(session) == []


# --- what the lock does not serialize ---------------------------------------------------------------


def test_two_workspaces_write_in_parallel(client, workspace, at_commit):
    """Not serialized: a write in another workspace completes while this one holds its lock (it is
    held until both others are seen); one in the same workspace waits for it."""
    other = unique_key("pg3-other")
    create_workspace(client, other)
    with ThreadPoolExecutor(max_workers=3) as pool:
        at_commit.arm()
        held = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("a"))
        try:
            assert at_commit.reached.wait(HOLD_TIMEOUT)
            elsewhere = post_object(client, other, "domain", domain_code=unique_key("b"))
            same = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("c"))
            assert waiting_on(WORKSPACE_LOCK)
            assert not held.done() and not same.done()
        finally:
            at_commit.release()
        created(elsewhere)
        created(held.result(HOLD_TIMEOUT))
        created(same.result(HOLD_TIMEOUT))


def test_an_activation_does_not_wait_for_the_workspace_lock(client, workspace, at_lock):
    """W5 on row locks: a live write holding the workspace lock does not hold up an activation;
    the write is then refused, since its release is no longer active."""
    release = _candidate(client, lambda _source: None)
    with ThreadPoolExecutor(max_workers=1) as pool:
        at_lock.arm()
        pending = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("d"))
        try:
            assert at_lock.reached.wait(HOLD_TIMEOUT)
            activation = _activate(client, release, workspace)
        finally:
            at_lock.release()
        response = pending.result(HOLD_TIMEOUT)
    assert activation.status_code == 200, activation.text
    refused(response, 409, "MODEL_RELEASE_CHANGED")


def test_an_activation_waits_for_a_write_committing_under_the_old_release(
    client, workspace, at_commit
):
    """A write that rechecked its release as it commits holds the runtime-state row shared: the
    activation waits for it, and neither deadlocks on the other's locks."""
    release = _candidate(client, lambda _source: None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        at_commit.arm()
        pending = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("d"))
        try:
            assert at_commit.reached.wait(HOLD_TIMEOUT)
            activation = pool.submit(_activate, client, release, workspace)
            assert waiting_on(RUNTIME_STATE_LOCK)
        finally:
            at_commit.release()
        created(pending.result(HOLD_TIMEOUT))
        assert activation.result(HOLD_TIMEOUT).status_code == 200


def _domain_code_not_unique(source: dict) -> None:
    attribute = next(item for item in source["attributeTypes"] if item["key"] == "domain-code")
    attribute["features"]["unique"] = False


def test_an_activation_waits_for_a_subscription_row_a_delivery_holds(client, workspace):
    """0.9 R-F2: a dispatcher step changes its subscription's row and then, as it commits, takes the
    runtime state's share lock. The activation locks the active subscriptions before the runtime
    state, so it waits for that row, the step commits, and neither deadlocks."""
    created_subscription = client.post(
        "/api/v1/consumer-subscriptions",
        json={
            "name": "Receiver",
            "consumerApi": "rdm",
            "workspaceKey": workspace,
            "events": ["values-changed"],
            "url": "https://hooks.example.test/rdm",
        },
    )
    assert created_subscription.status_code == 201, created_subscription.text
    release = _candidate(client, lambda _source: None)
    with SessionLocal() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(
            text("UPDATE consumer_subscriptions SET updated_at = updated_at WHERE public_id = :id"),
            {"id": created_subscription.json()["id"]},
        )
        activation = pool.submit(_activate, client, release, workspace)
        try:
            assert waiting_on("%FROM consumer_subscriptions%FOR UPDATE%")
            holder.execute(text("SET LOCAL lock_timeout = '3s'"))
            holder.execute(
                text("SELECT 1 FROM workspace_models WHERE workspace_key = :w FOR SHARE"),
                {"w": workspace},
            )
        finally:
            holder.commit()
        assert activation.result(HOLD_TIMEOUT).status_code == 200


def test_an_activation_changing_unique_waits_for_a_write_of_those_values(client, workspace):
    """0.9 R-F3: a live write's values reach the unique values' rows through a trigger before it
    takes the runtime state's share lock at commit. An activation changing ``unique`` locks those
    rows' table before the runtime state, so it waits for the write, which commits."""
    record = created(post_object(client, workspace, "domain", domain_code=unique_key("d")))
    release = _candidate(client, _domain_code_not_unique)
    with SessionLocal() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(
            text(
                "UPDATE attribute_values SET text_value = text_value"
                " WHERE object_id = :id AND attribute_type_key = 'domain-code'"
            ),
            {"id": record["id"]},
        )
        activation = pool.submit(_activate, client, release, workspace)
        try:
            assert waiting_on("%LOCK TABLE unique_attribute_values%")
            holder.execute(text("SET LOCAL lock_timeout = '3s'"))
            holder.execute(
                text("SELECT 1 FROM workspace_models WHERE workspace_key = :w FOR SHARE"),
                {"w": workspace},
            )
        finally:
            holder.commit()
        assert activation.result(HOLD_TIMEOUT).status_code == 200


def test_retiring_a_workspace_waits_for_its_live_write(client, workspace, at_commit):
    """Retirement locks the workspace before the runtime state, the order of a live write that
    rechecks its release as it commits; the write commits, then the workspace retires."""
    version = client.get(f"/api/v1/workspaces/{workspace}").json()["version"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        at_commit.arm()
        pending = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("d"))
        try:
            assert at_commit.reached.wait(HOLD_TIMEOUT)
            retirement = pool.submit(
                client.patch,
                f"/api/v1/workspaces/{workspace}",
                json={"expectedVersion": version, "status": "retired"},
            )
            assert waiting_on("%FROM workspaces%FOR UPDATE%")
        finally:
            at_commit.release()
        created(pending.result(HOLD_TIMEOUT))
        assert retirement.result(HOLD_TIMEOUT).status_code == 200


def test_retiring_a_workspace_waits_for_a_change_set_write(client, workspace, at_commit):
    """A change set write holds the workspace's key share lock: retirement waits for it, and a
    write after the retirement is refused."""
    change_set = create_change_set(client, workspace).json()
    version = client.get(f"/api/v1/workspaces/{workspace}").json()["version"]

    def write(code: str) -> httpx.Response:
        current = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
        return client.post(
            "/api/v1/objects",
            json={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": current,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": unique_key("domain"),
                "attributes": [{"attributeTypeKey": "domain-code", "value": code}],
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        at_commit.arm()
        pending = pool.submit(write, unique_key("d"))
        try:
            assert at_commit.reached.wait(HOLD_TIMEOUT)
            retirement = pool.submit(
                client.patch,
                f"/api/v1/workspaces/{workspace}",
                json={"expectedVersion": version, "status": "retired"},
            )
            assert waiting_on("%FROM workspaces%FOR UPDATE%")
            assert not retirement.done()
        finally:
            at_commit.release()
        created(pending.result(HOLD_TIMEOUT))
        assert retirement.result(HOLD_TIMEOUT).status_code == 200
    refused(write(unique_key("e")), 409, "WORKSPACE_RETIRED")


def test_a_publication_leaves_another_change_sets_writes_free(client, workspace, at_commit):
    """Publishing locks the workspace against live writes, not against the key share lock of a
    write in another change set."""
    published = create_change_set(client, workspace).json()
    other = create_change_set(client, workspace).json()
    staged = created(
        client.post(
            "/api/v1/objects",
            json={
                "changeSetId": published["id"],
                "expectedChangeSetVersion": published["version"],
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": unique_key("domain"),
                "attributes": [{"attributeTypeKey": "domain-code", "value": unique_key("s")}],
            },
        )
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        at_commit.arm()
        publication = pool.submit(
            client.post,
            f"/api/v1/change-sets/{published['id']}/publication",
            json={"expectedChangeSetVersion": staged["changeSetVersion"]},
        )
        try:
            assert at_commit.reached.wait(HOLD_TIMEOUT)
            written = client.post(
                "/api/v1/objects",
                json={
                    "changeSetId": other["id"],
                    "expectedChangeSetVersion": other["version"],
                    "applicationKey": "rdm-master",
                    "objectTypeKey": "domain",
                    "name": unique_key("domain"),
                    "attributes": [{"attributeTypeKey": "domain-code", "value": unique_key("p")}],
                },
            )
            assert not publication.done()
        finally:
            at_commit.release()
        created(written)
        response = publication.result(HOLD_TIMEOUT)
        assert response.status_code == 200, response.text


# --- feed positions (Base 0.9 F1) -----------------------------------------------------------------


def feed(client, workspace_key: str) -> list[dict]:
    response = client.get(f"/api/v1/workspaces/{workspace_key}/feed", params={"pageSize": 1000})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_feed_positions_follow_commit_order(client, workspace, at_commit):
    """A write that took its position and is held before its commit keeps the next write waiting
    for the workspace lock; the waiting write's position comes after it, with no gap."""
    first, second = race(
        at_commit,
        lambda: post_object(client, workspace, "domain", domain_code=unique_key("first")),
        lambda: post_object(client, workspace, "domain", domain_code=unique_key("second")),
    )
    entries = feed(client, workspace)
    assert [(e["position"], e["id"]) for e in entries] == [
        (1, created(first)["id"]),
        (2, created(second)["id"]),
    ]


def test_a_publish_and_a_live_write_of_its_record_do_not_deadlock(client, workspace, at_commit):
    """Publishing takes the workspace lock before any record, as every live write does: a live
    rename of a record the publish changes waits for it and is then refused on the version the
    publish moved, while the feed lists the publish's entries and then the publication."""
    record = domain(client, workspace)
    staged_set = create_change_set(client, workspace, source="currentLive").json()
    staged = client.patch(
        f"/api/v1/objects/domain/{record['id']}",
        json={
            "changeSetId": staged_set["id"],
            "expectedChangeSetVersion": staged_set["version"],
            "expectedVersion": record["version"],
            "name": "Renamed in the change set",
        },
    )
    assert staged.status_code == 200, staged.text
    publication, live = race(
        at_commit,
        lambda: client.post(
            f"/api/v1/change-sets/{staged_set['id']}/publication",
            json={"expectedChangeSetVersion": staged.json()["changeSetVersion"]},
        ),
        lambda: client.patch(
            f"/api/v1/objects/domain/{record['id']}",
            json={"expectedVersion": record["version"], "name": "Renamed live"},
        ),
    )
    assert publication.status_code == 200, publication.text
    refused(live, 409, "VERSION_CONFLICT")
    entries = feed(client, workspace)
    assert [(e["kind"], e["action"], e["id"]) for e in entries[1:]] == [
        ("object", "updated", record["id"]),
        ("publication", "published", publication.json()["id"]),
    ]


# --- background jobs (D28) --------------------------------------------------------------------------

CHUNK = 2


def worker(owner: str) -> JobWorker:
    return JobWorker(SessionLocal, WorkerSettings(CHUNK, 120, 7), owner=owner)


def domain_items(count: int) -> list[dict]:
    return [
        {
            "op": "create",
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Job domain {n}",
            "attributes": [{"attributeTypeKey": "domain-code", "value": unique_key(f"j{n}")}],
        }
        for n in range(count)
    ]


def queue(client, workspace_key: str, count: int, policy: str = "independent") -> dict:
    response = client.post(
        "/api/v1/batches",
        json={
            "policy": policy,
            "run": "background",
            "workspaceKey": workspace_key,
            "items": domain_items(count),
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def job(client, job_id: str) -> dict:
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200, response.text
    return response.json()


def job_domains(workspace_key: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(RdmObject)
            .where(RdmObject.workspace_key == workspace_key, RdmObject.name.like("Job domain %"))
        )


def in_chunk(pool: ThreadPoolExecutor, hold: Hold, runner: JobWorker, nth: int = 1) -> Future:
    hold.arm(nth)
    running = pool.submit(runner.run_once)
    assert hold.reached.wait(HOLD_TIMEOUT), "the chunk never reached its hold"
    return running


def test_a_cancel_request_is_answered_while_a_chunk_runs(client, workspace, at_lock):
    queued = queue(client, workspace, 3 * CHUNK)
    runner = worker("worker-a")
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = in_chunk(pool, at_lock, runner)
        try:
            cancel = client.post(f"/api/v1/jobs/{queued['id']}/cancel")
            assert cancel.status_code == 202, cancel.text
            assert not running.done()
        finally:
            at_lock.release()
        assert running.result(HOLD_TIMEOUT) is True
    runner.run_until_idle()
    finished = job(client, queued["id"])
    assert finished["state"] == "cancelled"
    # The chunk running when the request came commits; the job stops before the next one.
    assert job_domains(workspace) == CHUNK


def test_an_atomic_job_cancelled_between_items_rolls_back(
    client, workspace, at_lock, monkeypatch
):
    """Held while it decides its second item, after the first (PG3b: the items are decided, then
    written together): the cancel request answered meanwhile stops the job before it writes, and
    nothing it applied stays."""
    queued = queue(client, workspace, 3, policy="atomic")
    runner = worker("worker-a")
    unique_values = rules.unique_values

    def deciding(*args: Any, **kwargs: Any) -> None:
        at_lock._maybe_hold()
        unique_values(*args, **kwargs)

    monkeypatch.setattr(rules, "unique_values", deciding)
    with ThreadPoolExecutor(max_workers=1) as pool:
        # The chunk's lock is the first hold point, each item's unique-value check the next: the
        # third is the second item's.
        running = in_chunk(pool, at_lock, runner, nth=3)
        try:
            cancel = client.post(f"/api/v1/jobs/{queued['id']}/cancel")
            assert cancel.status_code == 202, cancel.text
        finally:
            at_lock.release()
        running.result(HOLD_TIMEOUT)
    finished = job(client, queued["id"])
    assert finished["state"] == "cancelled"
    assert job_domains(workspace) == 0


def test_two_workers_share_a_job_through_its_lease(client, workspace, at_lock):
    """A worker whose lease expired mid-chunk loses that chunk to the worker that took the job
    over; every item is applied once."""
    queued = queue(client, workspace, 2 * CHUNK)
    first, second = worker("worker-a"), worker("worker-b")
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = in_chunk(pool, at_lock, first)
        try:
            with SessionLocal() as session:
                session.execute(
                    update(Job)
                    .where(Job.id == queued["id"])
                    .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
                session.commit()
            # The second worker claims the job; its chunk waits for the first one's lock.
            taking_over = threading.Thread(target=second.run_until_idle)
            taking_over.start()
            assert waiting_on(WORKSPACE_LOCK)
        finally:
            at_lock.release()
        running.result(HOLD_TIMEOUT)
        taking_over.join(HOLD_TIMEOUT)
    assert not taking_over.is_alive()
    second.run_until_idle()
    finished = job(client, queued["id"])
    assert finished["state"] == "completed"
    assert finished["counts"]["created"] == 2 * CHUNK
    assert job_domains(workspace) == 2 * CHUNK


def test_a_live_write_beside_a_background_job_waits_for_one_chunk_at_most(
    client, workspace, at_lock
):
    """The job holds the workspace lock for its chunk, not for the job: a live write in its
    workspace runs between two chunks, one in another workspace does not wait at all."""
    other = unique_key("pg3-other")
    create_workspace(client, other)
    queued = queue(client, workspace, 3 * CHUNK)
    runner = worker("worker-a")
    with ThreadPoolExecutor(max_workers=2) as pool:
        running = in_chunk(pool, at_lock, runner)
        try:
            created(post_object(client, other, "domain", domain_code=unique_key("o")))
            beside = pool.submit(post_object, client, workspace, "domain", domain_code=unique_key("b"))
            assert waiting_on(WORKSPACE_LOCK)
        finally:
            at_lock.release()
        running.result(HOLD_TIMEOUT)
        # Written after the first chunk, before the job's next chunk runs.
        created(beside.result(HOLD_TIMEOUT))
    assert job(client, queued["id"])["progress"]["processed"] == CHUNK
    runner.run_until_idle()
    assert job(client, queued["id"])["state"] == "completed"
