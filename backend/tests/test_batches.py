"""Base 0.9 B1: inline object batches as jobs (ADR-036, INTEGRATION_API P and B).

A batch item goes through its single write's service, so each item op is refused with the code its
single-write route gives for the same cause, live and in a change set. The batch adds the failure
policies, record references by unique key, upsert with the per-item concurrency rules, ``unchanged``,
idempotency keys and the job reads. Everything runs on a generated model and on a copy with every
key renamed: nothing depends on a model key.
"""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from model_support import renamed_model
from sqlalchemy import select, update
from test_context_read_parity import APP, CITES, ENTRY, FOLDER, parity_model

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.jobs import inline
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import AuditEvent, IdempotencyKey, Job

Keys = Callable[[str], str]
WORKSPACE = "default"
CODE, COUNT = "par-code", "par-count"


def batch_model() -> dict[str, Any]:
    """The parity model with a unique code, which key references and upserts address records by."""
    source = parity_model()
    code = next(item for item in source["attributeTypes"] if item["key"] == CODE)
    code["features"] = {**code["features"], "unique": True}
    return source


def _serve(tmp_path, monkeypatch, migrated_database, source: dict, **env: str) -> TestClient:
    model_path = tmp_path / "batch-model.json"
    model_path.write_text(json.dumps(source))
    monkeypatch.setenv("DATABASE_URL", migrated_database("batches.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    reload_settings()
    model_registry.clear()
    return TestClient(create_app())


@pytest.fixture(params=["generated", "renamed"])
def batches(request, tmp_path, monkeypatch, migrated_database) -> Iterator[tuple[TestClient, Keys]]:
    source = batch_model()
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    with _serve(tmp_path, monkeypatch, migrated_database, source) as client:
        yield client, lambda key: names.get(key, key)
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture
def configured(tmp_path, monkeypatch, migrated_database):
    """A client factory with environment settings, on the generated model."""

    def serve(**env: str) -> TestClient:
        return _serve(tmp_path, monkeypatch, migrated_database, batch_model(), **env)

    yield serve
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


# --- helpers ------------------------------------------------------------------------------------


def _ok(response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _refused(response, code: str, status: int) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code, error
    return error


def attrs(k: Keys, **values: Any) -> list[dict[str, Any]]:
    return [{"attributeTypeKey": k(key.replace("_", "-")), "value": value} for key, value in values.items()]


def by_code(k: Keys, object_type: str, code: str) -> dict[str, Any]:
    return {"objectTypeKey": k(object_type), "key": {"attributeTypeKey": k(CODE), "value": code}}


def create_item(k: Keys, object_type: str, name: str, code: str | None, parent=None, **extra) -> dict:
    item = {
        "op": "create",
        "applicationKey": k(APP),
        "objectTypeKey": k(object_type),
        "name": name,
        "attributes": attrs(k, par_code=code) if code is not None else [],
        **extra,
    }
    if parent is not None:
        item["parent"] = parent
    return item


def upsert_item(k: Keys, object_type: str, name: str, code: str, parent=None, **extra) -> dict:
    item = {
        "op": "upsert",
        "applicationKey": k(APP),
        "objectTypeKey": k(object_type),
        "key": {"attributeTypeKey": k(CODE)},
        "name": name,
        "attributes": attrs(k, par_code=code),
        **extra,
    }
    if parent is not None:
        item["parent"] = parent
    return item


def batch(client, items: list[dict], *, policy="independent", headers=None, **context) -> Any:
    if not context:
        context = {"workspaceKey": WORKSPACE}
    return client.post(
        "/api/v1/batches",
        json={"policy": policy, "run": "inline", "items": items, **context},
        headers=headers or {},
    )


def outcomes(body: dict) -> list[tuple]:
    """(status, action or error code or reason) per item."""
    return [
        (
            item["status"],
            item.get("action") or (item.get("error") or {}).get("code") or item.get("reason"),
        )
        for item in body["items"]
    ]


def single_create(client, k: Keys, object_type: str, name: str, code: str | None, parent_id=None, **context):
    return client.post(
        "/api/v1/objects",
        json={
            "applicationKey": k(APP),
            "objectTypeKey": k(object_type),
            "name": name,
            "parentObjectId": parent_id,
            "attributes": attrs(k, par_code=code) if code is not None else [],
            **(context or {"workspaceKey": WORKSPACE}),
        },
    )


def read(client, k: Keys, object_type: str, object_id: str, **params) -> Any:
    return client.get(f"/api/v1/objects/{k(object_type)}/{object_id}", params=params)


def change_set(client) -> dict[str, Any]:
    return _ok(
        client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}), 201
    )


def change_set_version(client, change_set_id: str) -> int:
    return _ok(client.get(f"/api/v1/change-sets/{change_set_id}"))["version"]


def without_workspace(context: dict) -> dict:
    """A record route's change set fields; a live write names no workspace."""
    return {key: value for key, value in context.items() if key != "workspaceKey"}


def history(client, k: Keys, object_type: str, object_id: str, **params) -> list[dict]:
    return _ok(client.get(f"/api/v1/objects/{k(object_type)}/{object_id}/history", params=params))["items"]


def job_count() -> int:
    with SessionLocal() as session:
        return len(session.scalars(select(Job.id)).all())


# --- each item op is its single write -----------------------------------------------------------


def _seed(client, k: Keys, **context) -> dict[str, Any]:
    """Folder F1 holding entry E1, and folder F2; codes are their names."""
    folder = _ok(single_create(client, k, FOLDER, "F1", "F1", **context), 201)
    entry = _ok(single_create(client, k, ENTRY, "E1", "E1", folder["id"], **context), 201)
    other = _ok(single_create(client, k, FOLDER, "F2", "F2", **context), 201)
    return {"F1": folder, "E1": entry, "F2": other}


def _contexts(client) -> dict[str, dict]:
    """Live data and a new change set, each as a write's context."""
    staged = change_set(client)
    return {
        "live": {"workspaceKey": WORKSPACE},
        "change set": {"changeSetId": staged["id"], "expectedChangeSetVersion": staged["version"]},
    }


def claimed(client, context: dict) -> dict:
    """The context with the change set's current version, which every write claims."""
    if "changeSetId" not in context:
        return context
    return {**context, "expectedChangeSetVersion": change_set_version(client, context["changeSetId"])}


def _single_code(response) -> str:
    assert response.status_code >= 400, response.text
    return response.json()["error"]["code"]


def _batch_code(client, context: dict, item: dict) -> str:
    """The code a one-item batch refuses ``item`` with; its pointer is into the item."""
    [outcome] = _ok(batch(client, [item], **claimed(client, context)))["items"]
    assert outcome["status"] == "rejected", outcome
    assert outcome["error"]["details"]["pointer"].startswith("/items/0"), outcome
    return outcome["error"]["code"]


def test_each_item_op_is_refused_with_its_single_writes_code(batches):
    client, k = batches
    for label, context in _contexts(client).items():
        query = {"changeSetId": context["changeSetId"]} if "changeSetId" in context else {}
        folder = _ok(single_create(client, k, FOLDER, f"F1-{label}", f"F1-{label}", **claimed(client, context)), 201)
        entry = _ok(
            single_create(client, k, ENTRY, f"E1-{label}", f"E1-{label}", folder["id"], **claimed(client, context)),
            201,
        )

        def create(context=context, **fields):
            return client.post(
                "/api/v1/objects",
                json={"applicationKey": k(APP), "objectTypeKey": k(FOLDER), **fields, **claimed(client, context)},
            )

        # A second record with a unique value another holds.
        assert (
            _single_code(single_create(client, k, FOLDER, "dup", f"F1-{label}", **claimed(client, context)))
            == _batch_code(client, context, create_item(k, FOLDER, "dup", f"F1-{label}"))
            == "duplicate_attribute_value"
        )
        # An attribute the type does not bind.
        unknown = {"attributeTypeKey": k(CITES), "value": 1}
        assert (
            _single_code(create(name="x", attributes=[unknown]))
            == _batch_code(client, context, {**create_item(k, FOLDER, "x", None), "attributes": [unknown]})
            == "unknown_attributes"
        )
        # An entry needs a parent.
        assert (
            _single_code(single_create(client, k, ENTRY, "orphan", f"orphan-{label}", **claimed(client, context)))
            == _batch_code(client, context, create_item(k, ENTRY, "orphan", f"orphan-{label}"))
            == "parent_required"
        )
        # A client ID already taken.
        assert (
            _single_code(create(id=folder["id"], name="again"))
            == _batch_code(client, context, {**create_item(k, FOLDER, "again", None), "id": folder["id"]})
            == "object_already_exists"
        )
        # A stale version.
        stale = _ok(read(client, k, ENTRY, entry["id"], **query))["version"] + 5
        patch = {"name": "renamed", "expectedVersion": stale, **without_workspace(claimed(client, context))}
        assert (
            _single_code(client.patch(f"/api/v1/objects/{k(ENTRY)}/{entry['id']}", json=patch))
            == _batch_code(
                client, context, {"op": "update", "target": {"id": entry["id"]}, "name": "renamed", "expectedVersion": stale}
            )
            == "version_conflict"
        )
        # A record with children is not deleted without cascade; the batch carries no preview token.
        version = _ok(read(client, k, FOLDER, folder["id"], **query))["version"]
        delete = {"op": "delete", "target": {"id": folder["id"]}, "expectedVersion": version}
        assert (
            _single_code(
                client.delete(
                    f"/api/v1/objects/{k(FOLDER)}/{folder['id']}",
                    params={"expectedVersion": version, **without_workspace(claimed(client, context))},
                )
            )
            == _batch_code(client, context, delete)
            == "object_has_dependants"
        )
        body = _ok(batch(client, [delete], **claimed(client, context)))
        assert "deletionPreviewToken" not in body["items"][0]["error"]["details"]


def test_items_apply_like_their_single_writes(batches):
    """Create, update (a move), upsert and delete apply, live and in a change set, with the
    versions and audit entries their single writes give, and the job as the entries' cause."""
    client, k = batches
    for label, context in _contexts(client).items():
        folder_id = str(uuid4())
        body = _ok(
            batch(
                client,
                [
                    {**create_item(k, FOLDER, f"A-{label}", f"A-{label}"), "id": folder_id},
                    create_item(k, FOLDER, f"B-{label}", f"B-{label}"),
                    create_item(k, ENTRY, f"e-{label}", f"e-{label}", {"id": folder_id}),
                    {
                        "op": "update",
                        "target": by_code(k, ENTRY, f"e-{label}"),
                        "expectedVersion": 1,
                        "parent": by_code(k, FOLDER, f"B-{label}"),
                        "attributes": attrs(k, par_count=3),
                    },
                    upsert_item(k, ENTRY, f"u-{label}", f"u-{label}", by_code(k, FOLDER, f"B-{label}")),
                    {"op": "delete", "target": {"id": folder_id}, "expectedVersion": 1},
                ],
                **context,
            )
        )
        assert outcomes(body) == [
            ("applied", "created"),
            ("applied", "created"),
            ("applied", "created"),
            ("applied", "updated"),
            ("applied", "created"),
            ("applied", "deleted"),
        ], body
        job = body["job"]
        assert (job["state"], job["result"], job["kind"], job["policy"]) == (
            "completed",
            "applied",
            "batch",
            "independent",
        )
        assert job["counts"] == {
            "applied": 6, "rejected": 0, "unprocessed": 0, "created": 4, "updated": 1, "unchanged": 0, "deleted": 1,
        }
        assert job["progress"] == {"total": 6, "processed": 6}
        assert job["parameters"] == {"run": "inline", "onExisting": "reject"}
        query = {}
        if "changeSetId" in context:
            query = {"changeSetId": context["changeSetId"]}
            # One claim for the whole job.
            assert job["changeSetVersion"] == context["expectedChangeSetVersion"] + 1
            assert change_set_version(client, context["changeSetId"]) == job["changeSetVersion"]
            # The records are the change set's, not live.
            assert read(client, k, ENTRY, body["items"][2]["id"]).status_code == 404
        else:
            assert job["changeSetId"] is None and job["changeSetVersion"] is None
        moved = _ok(read(client, k, ENTRY, body["items"][2]["id"], **query))
        assert moved["parentObjectId"] == body["items"][1]["id"]
        assert moved["version"] == body["items"][3]["version"] == 2
        assert {item["attributeTypeKey"]: item["value"] for item in moved["attributes"]}[k(COUNT)] == 3
        assert read(client, k, FOLDER, folder_id, **query).status_code == 404
        entries = history(client, k, ENTRY, moved["id"], **query)
        assert [entry["action"] for entry in entries] == ["updated", "created"]
        assert all(entry["cause"] == {"kind": "job", "id": job["id"]} for entry in entries)
    # A single write records no cause.
    single = _ok(single_create(client, k, FOLDER, "solo", "solo"), 201)
    assert "cause" not in history(client, k, FOLDER, single["id"])[0]


# --- outcomes and policies (P2, P3) -------------------------------------------------------------


def test_independent_items_stand_alone_and_see_earlier_applied_items(batches):
    client, k = batches
    body = _ok(
        batch(
            client,
            [
                create_item(k, FOLDER, "P", "P"),
                create_item(k, ENTRY, "child of P", "C1", by_code(k, FOLDER, "P")),
                create_item(k, FOLDER, "dup", "P"),
                create_item(k, ENTRY, "child of missing", "C2", by_code(k, FOLDER, "missing")),
                # Refused after its record row was written: the savepoint removes the row.
                create_item(
                    k,
                    ENTRY,
                    "cites an entry",
                    "C3",
                    by_code(k, FOLDER, "P"),
                    initialRelations=[
                        {"relationTypeKey": k(CITES), "direction": "outgoing", "object": by_code(k, ENTRY, "C1")}
                    ],
                ),
            ],
            policy="independent",
        )
    )
    assert outcomes(body) == [
        ("applied", "created"),
        ("applied", "created"),
        ("rejected", "duplicate_attribute_value"),
        ("rejected", "reference_not_found"),
        ("rejected", "invalid_relation_pair"),
    ]
    entries = _ok(client.get("/api/v1/objects", params={"workspaceKey": WORKSPACE, "objectTypeKey": k(ENTRY)}))
    assert [item["name"] for item in entries["items"]] == ["child of P"]
    assert body["items"][3]["error"]["details"]["pointer"] == "/items/3/parent"
    assert body["items"][2]["error"]["details"]["pointer"] == "/items/2/attributes"
    assert body["job"]["result"] == "partial"
    assert body["job"]["counts"]["rejected"] == 3
    # A rejected item leaves nothing: one record holds the code.
    listed = _ok(client.get("/api/v1/objects", params={"workspaceKey": WORKSPACE, "objectTypeKey": k(FOLDER)}))
    assert [item["name"] for item in listed["items"] if item["name"] in {"P", "dup"}] == ["P"]

    rejected = _ok(batch(client, [create_item(k, FOLDER, "dup again", "P")]))
    assert rejected["job"]["result"] == "rejected"


def test_an_atomic_batch_applies_everything_or_nothing(batches):
    client, k = batches
    for label, context in _contexts(client).items():
        body = _ok(
            batch(
                client,
                [
                    create_item(k, FOLDER, f"P-{label}", f"P-{label}"),
                    create_item(k, ENTRY, "child", f"C-{label}", by_code(k, FOLDER, f"P-{label}")),
                    create_item(k, FOLDER, "dup", f"P-{label}"),
                    create_item(k, FOLDER, "never reached", f"N-{label}"),
                ],
                policy="atomic",
                **context,
            )
        )
        assert outcomes(body) == [
            ("unprocessed", "batch_rolled_back"),
            ("unprocessed", "batch_rolled_back"),
            ("rejected", "duplicate_attribute_value"),
            ("unprocessed", "batch_rolled_back"),
        ]
        assert body["job"]["result"] == "rejected"
        assert body["job"]["policy"] == "atomic"
        # Nothing was written, not even the audit entries or the change set's claim.
        params = {"changeSetId": context["changeSetId"]} if "changeSetId" in context else {"workspaceKey": WORKSPACE}
        listed = _ok(client.get("/api/v1/objects", params={**params, "objectTypeKey": k(FOLDER)}))
        assert not [item for item in listed["items"] if item["name"].startswith("P-")]
        with SessionLocal() as session:
            assert not session.scalars(select(AuditEvent).where(AuditEvent.cause_id == body["job"]["id"])).all()
        if "changeSetId" in context:
            assert change_set_version(client, context["changeSetId"]) == context["expectedChangeSetVersion"]
            assert body["job"]["changeSetVersion"] == context["expectedChangeSetVersion"]

        applied = _ok(
            batch(
                client,
                [
                    create_item(k, FOLDER, f"P-{label}", f"P-{label}"),
                    create_item(k, ENTRY, "child", f"C-{label}", by_code(k, FOLDER, f"P-{label}")),
                ],
                policy="atomic",
                **context,
            )
        )
        assert applied["job"]["result"] == "applied"


# --- upsert and per-item concurrency (P4, D11, D24) ---------------------------------------------


def test_upserts_need_a_version_claim_or_a_declared_overwrite(batches):
    client, k = batches
    created = _ok(batch(client, [upsert_item(k, FOLDER, "Feed", "FEED")]))
    assert outcomes(created) == [("applied", "created")]
    record_id = created["items"][0]["id"]

    # The same values again: unchanged, without a version, writing nothing (D24).
    again = _ok(batch(client, [upsert_item(k, FOLDER, "Feed", "FEED")]))
    assert outcomes(again) == [("applied", "unchanged")]
    assert again["items"][0]["version"] == 1
    assert again["job"]["counts"]["unchanged"] == 1
    assert len(history(client, k, FOLDER, record_id)) == 1

    # A change without a version claim is refused...
    changed = upsert_item(k, FOLDER, "Feed renamed", "FEED")
    refused = _ok(batch(client, [changed]))
    assert outcomes(refused) == [("rejected", "version_required")]
    assert refused["items"][0]["error"]["details"]["pointer"] == "/items/0/expectedVersion"
    # ...unless the request declares the overwrite, which is audited with the version it replaced.
    response = client.post(
        "/api/v1/batches",
        json={"workspaceKey": WORKSPACE, "policy": "independent", "run": "inline", "onExisting": "overwrite", "items": [changed]},
    )
    overwritten = _ok(response)["items"][0]
    assert (overwritten["action"], overwritten["version"], overwritten["previousVersion"]) == ("updated", 2, 1)
    latest = history(client, k, FOLDER, record_id)[0]
    # Audited as the PATCH it is; the overwrite marker is not a changed field.
    assert latest["changedFields"] == ["attributes", "name"]
    with SessionLocal() as session:
        stored = session.scalars(
            select(AuditEvent).where(AuditEvent.aggregate_id == record_id, AuditEvent.action == "updated")
        ).one()
        assert stored.changes["overwrite"] == {"previousVersion": 1}

    # With a claim: a stale one conflicts, a current one applies; equal values stay unchanged
    # whatever the claim.
    stale = _ok(batch(client, [{**upsert_item(k, FOLDER, "Feed v3", "FEED"), "expectedVersion": 1}]))
    assert outcomes(stale) == [("rejected", "version_conflict")]
    same = _ok(batch(client, [{**upsert_item(k, FOLDER, "Feed renamed", "FEED"), "expectedVersion": 1}]))
    assert outcomes(same) == [("applied", "unchanged")]
    current = _ok(batch(client, [{**upsert_item(k, FOLDER, "Feed v3", "FEED"), "expectedVersion": 2}]))
    assert outcomes(current) == [("applied", "updated")]
    assert "previousVersion" not in current["items"][0]

    # An update item with equal values is unchanged too; with other values it needs its version.
    unchanged = _ok(batch(client, [{"op": "update", "target": {"id": record_id}, "expectedVersion": 1, "name": "Feed v3"}]))
    assert outcomes(unchanged) == [("applied", "unchanged")]


def test_an_upsert_by_id_creates_with_that_id_and_never_changes_a_type(batches):
    client, k = batches
    record_id = str(uuid4())
    item = {
        "op": "upsert",
        "applicationKey": k(APP),
        "objectTypeKey": k(FOLDER),
        "key": {"id": record_id},
        "name": "By id",
        "attributes": attrs(k, par_code="BYID"),
    }
    assert outcomes(_ok(batch(client, [item]))) == [("applied", "created")]
    assert _ok(read(client, k, FOLDER, record_id))["name"] == "By id"
    assert outcomes(_ok(batch(client, [item]))) == [("applied", "unchanged")]
    # The same key naming another type: refused, never reclassified.
    other = {**item, "objectTypeKey": k(ENTRY), "parent": {"id": record_id}}
    body = _ok(batch(client, [other]))
    assert outcomes(body) == [("rejected", "reference_type_mismatch")]
    assert body["items"][0]["error"]["details"]["pointer"] == "/items/0/key"


def test_upsert_initial_relations_apply_only_when_it_creates(batches):
    client, k = batches
    folders = _seed(client, k)
    cites = [{"relationTypeKey": k(CITES), "direction": "outgoing", "object": by_code(k, FOLDER, "F2")}]
    item = upsert_item(k, ENTRY, "Cites", "CITES", {"id": folders["F1"]["id"]}, initialRelations=cites)
    created = _ok(batch(client, [item]))
    assert outcomes(created) == [("applied", "created")]
    relations = _ok(client.get("/api/v1/relations", params={"objectId": created["items"][0]["id"], "workspaceKey": WORKSPACE}))
    assert [relation["relation"]["relationTypeKey"] for relation in relations["items"]].count(k(CITES)) == 1
    # Found again, it is unchanged: the relation is not created twice.
    assert outcomes(_ok(batch(client, [item]))) == [("applied", "unchanged")]


# --- references and keys (B2, B3) ---------------------------------------------------------------


def test_references_resolve_by_unique_key_and_are_refused_at_their_pointer(batches):
    client, k = batches
    seeded = _seed(client, k)
    body = _ok(
        batch(
            client,
            [
                # A key over an attribute that is not unique.
                create_item(k, ENTRY, "x1", "X1", {"objectTypeKey": k(FOLDER), "key": {"attributeTypeKey": k(COUNT), "value": 1}}),
                # No record holds the value.
                create_item(k, ENTRY, "x2", "X2", by_code(k, FOLDER, "nope")),
                # The holder is an entry, not a folder.
                create_item(k, ENTRY, "x3", "X3", by_code(k, FOLDER, "E1")),
                # The upsert key needs a value.
                {**upsert_item(k, FOLDER, "x4", "X4"), "attributes": []},
                # An upsert key over an attribute that is not unique.
                {**upsert_item(k, FOLDER, "x5", "X5"), "key": {"attributeTypeKey": k(COUNT)}},
                # A value of the wrong type for the key.
                create_item(k, ENTRY, "x6", "X6", {"objectTypeKey": k(FOLDER), "key": {"attributeTypeKey": k(CODE), "value": 7}}),
                # Found by key: applied.
                create_item(k, ENTRY, "x7", "X7", by_code(k, FOLDER, "F1")),
            ],
        )
    )
    assert [(status, code, item["error"]["details"]["pointer"] if status == "rejected" else None)
            for (status, code), item in zip(outcomes(body), body["items"], strict=True)] == [
        ("rejected", "invalid_record_key", "/items/0/parent/key/attributeTypeKey"),
        ("rejected", "reference_not_found", "/items/1/parent"),
        ("rejected", "reference_type_mismatch", "/items/2/parent"),
        ("rejected", "missing_record_key", "/items/3/attributes"),
        ("rejected", "invalid_record_key", "/items/4/key/attributeTypeKey"),
        ("rejected", "invalid_attribute_value", "/items/5/parent/key/value"),
        ("applied", "created", None),
    ]
    assert body["items"][2]["error"]["details"]["id"] == seeded["E1"]["id"]
    assert _ok(read(client, k, ENTRY, body["items"][6]["id"]))["parentObjectId"] == seeded["F1"]["id"]


# --- context, limits and capability -------------------------------------------------------------


def test_request_level_refusals_create_no_job(configured):
    client = configured(BATCH_MAX_ITEMS="2", BATCH_MAX_BYTES="2000", BACKGROUND_JOB_MAX_ITEMS="2")
    with client:
        k: Keys = lambda key: key
        items = [create_item(k, FOLDER, f"F{n}", f"F{n}") for n in range(3)]
        error = _refused(batch(client, items), "batch_too_large", 413)
        assert error["details"] == {"setting": "BATCH_MAX_ITEMS", "maximum": 2, "items": 3}
        big = [create_item(k, FOLDER, "x" * 400, f"B{n}") for n in range(2)]
        big[0]["attributes"] += attrs(k, par_note="y" * 1800)
        error = _refused(batch(client, big), "batch_too_large", 413)
        assert error["details"]["setting"] == "BATCH_MAX_BYTES"
        # A background batch has its own limits (B2).
        response = client.post(
            "/api/v1/batches",
            json={"workspaceKey": WORKSPACE, "policy": "independent", "run": "background", "items": items},
        )
        error = _refused(response, "batch_too_large", 413)
        assert error["details"] == {"setting": "BACKGROUND_JOB_MAX_ITEMS", "maximum": 2, "items": 3}
        staged = change_set(client)
        _refused(batch(client, items[:1], workspaceKey=WORKSPACE, changeSetId=staged["id"]), "invalid_batch_context", 422)
        _refused(client.post("/api/v1/batches", json={"policy": "atomic", "run": "inline", "items": items[:1]}), "invalid_batch_context", 422)
        _refused(batch(client, items[:1], changeSetId=staged["id"]), "change_set_required", 409)
        _refused(
            batch(client, items[:1], changeSetId=staged["id"], expectedChangeSetVersion=staged["version"] + 1),
            "change_set_version_conflict",
            409,
        )
        _refused(batch(client, items[:1], workspaceKey="no-such-workspace"), "workspace_not_found", 404)
        # The policy has no default, and a malformed item fails the request.
        no_policy = client.post("/api/v1/batches", json={"workspaceKey": WORKSPACE, "run": "inline", "items": items[:1]})
        _refused(no_policy, "request_validation_error", 422)
        _refused(batch(client, [{"op": "rename"}]), "request_validation_error", 422)
        _refused(batch(client, []), "request_validation_error", 422)
        assert job_count() == 0
        capabilities = _ok(client.get("/api/v1/capabilities"))["integrationJobs"]
        assert capabilities == {
            "createJobs": True,
            "runModes": ["inline", "background"],
            "limits": {
                "batchMaxItems": 2,
                "batchMaxBytes": 2000,
                "atomicJobMaxItems": 10000,
                "backgroundJobMaxItems": 2,
                "backgroundBatchMaxBytes": 50 * 1024 * 1024,
                "chunkItems": 500,
                "retentionDays": 7,
            },
            "setting": "INTEGRATION_JOBS_ENABLED",
        }


def test_with_jobs_disabled_no_route_creates_one_and_reads_remain(configured):
    with configured(INTEGRATION_JOBS_ENABLED="false") as client:
        k: Keys = lambda key: key
        response = batch(client, [create_item(k, FOLDER, "F", "F")])
        assert response.status_code in {404, 405}, response.text
        assert "/api/v1/batches" not in client.get("/openapi.json").json()["paths"]
        assert _ok(client.get("/api/v1/jobs"))["items"] == []
        capabilities = _ok(client.get("/api/v1/capabilities"))["integrationJobs"]
        assert (capabilities["createJobs"], capabilities["runModes"]) == (False, [])


# --- idempotency (P5) ---------------------------------------------------------------------------


def test_an_idempotency_key_replays_the_finished_job(batches):
    client, k = batches
    items = [create_item(k, FOLDER, "Once", "ONCE")]
    key = {"Idempotency-Key": "load-2026-10-01 #1"}
    first = batch(client, items, headers=key)
    assert first.status_code == 200 and "Idempotent-Replayed" not in first.headers
    replay = batch(client, items, headers=key)
    assert replay.status_code == 200 and replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json() == first.json()
    assert job_count() == 1
    # The same key with another request runs nothing.
    error = _refused(batch(client, [create_item(k, FOLDER, "Other", "OTHER")], headers=key), "idempotency_key_reused", 422)
    assert error["details"]["jobId"] == first.json()["job"]["id"]
    # Keys are scoped to the workspace: another workspace's key is a new request.
    client.post("/api/v1/workspaces", json={"key": "other", "label": "Other"})
    elsewhere = batch(client, items, headers=key, workspaceKey="other")
    assert outcomes(_ok(elsewhere)) == [("applied", "created")]
    # A key whose job still runs answers 409 with the job and Retry-After.
    with SessionLocal() as session:
        session.execute(update(Job).where(Job.id == first.json()["job"]["id"]).values(state="running"))
        session.commit()
    running = batch(client, items, headers=key)
    assert _refused(running, "idempotency_in_progress", 409)["details"]["jobId"] == first.json()["job"]["id"]
    assert running.headers["Retry-After"] == "1"
    # Past retention the key counts as new.
    with SessionLocal() as session:
        session.execute(update(IdempotencyKey).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        session.commit()
    rerun = _ok(batch(client, items, headers=key))
    assert outcomes(rerun) == [("rejected", "duplicate_attribute_value")]
    assert rerun["job"]["id"] != first.json()["job"]["id"]
    _refused(batch(client, items, headers={"Idempotency-Key": ""}), "request_validation_error", 422)
    _refused(batch(client, items, headers={"Idempotency-Key": "x" * 201}), "request_validation_error", 422)


# --- job reads (P6) -----------------------------------------------------------------------------


def test_jobs_and_their_outcomes_page_in_order(batches):
    client, k = batches
    items = [create_item(k, FOLDER, f"F{n:02}", f"F{n:02}" if n % 3 else "same") for n in range(12)]
    first = _ok(batch(client, items))
    second = _ok(batch(client, items[:1], policy="atomic"))
    job_id = first["job"]["id"]
    assert first["nextCursor"] is None and len(first["items"]) == 12
    assert [item["index"] for item in first["items"]] == list(range(12))

    listed = _ok(client.get("/api/v1/jobs", params={"workspaceKey": WORKSPACE, "pageSize": 1}))
    assert [job["id"] for job in listed["items"]] == [second["job"]["id"]]
    following = _ok(client.get("/api/v1/jobs", params={"workspaceKey": WORKSPACE, "pageSize": 1, "cursor": listed["nextCursor"]}))
    assert [job["id"] for job in following["items"]] == [job_id]
    assert _ok(client.get("/api/v1/jobs", params={"kind": "export"}))["items"] == []
    assert len(_ok(client.get("/api/v1/jobs", params={"state": "completed"}))["items"]) == 2
    assert _ok(client.get(f"/api/v1/jobs/{job_id}")) == first["job"]
    _refused(client.get(f"/api/v1/jobs/{uuid4()}"), "job_not_found", 404)

    rejected = _ok(client.get(f"/api/v1/jobs/{job_id}/items", params={"status": "rejected", "pageSize": 2}))
    assert [item["index"] for item in rejected["items"]] == [3, 6]
    rest = _ok(client.get(f"/api/v1/jobs/{job_id}/items", params={"status": "rejected", "pageSize": 2, "cursor": rejected["nextCursor"]}))
    assert [item["index"] for item in rest["items"]] == [9]
    assert rest["nextCursor"] is None
    page = _ok(client.get(f"/api/v1/jobs/{job_id}/items", params={"position": 10, "includeTotal": "true"}))
    assert ([item["index"] for item in page["items"]], page["totalCount"]) == ([10, 11], 12)
    # Outcomes carry only their status's fields.
    applied, rejected_item = first["items"][1], first["items"][3]
    assert set(applied) == {"index", "ref", "status", "action", "id", "objectTypeKey", "version"}
    assert set(rejected_item) == {"index", "ref", "status", "error"}
    assert first["job"]["modelReleaseId"] == client.get("/api/v1/model").headers["X-Model-Release-Id"]


def test_refs_are_echoed(batches):
    client, k = batches
    items = [
        {**create_item(k, FOLDER, "R1", "R1"), "ref": "row-2"},
        {**create_item(k, FOLDER, "R2", "R1"), "ref": "row-3"},
        create_item(k, FOLDER, "R3", "R3"),
    ]
    body = _ok(batch(client, items))
    assert [item["ref"] for item in body["items"]] == ["row-2", "row-3", None]
    _refused(batch(client, [{**items[0], "ref": ""}]), "request_validation_error", 422)


def test_a_model_release_change_before_commit_saves_nothing(batches, monkeypatch):
    """The job pins the active release; one activated meanwhile refuses the whole inline job."""
    client, k = batches
    original = inline.run_batch

    def activate_meanwhile(session, context, request, job_id):
        result = original(session, context, request, job_id)
        # As if another release were active when the job commits.
        session.info["resolved_active_model_release_db_id"] = -1
        return result

    monkeypatch.setattr(inline, "run_batch", activate_meanwhile)
    _refused(batch(client, [create_item(k, FOLDER, "Pinned", "PIN")]), "model_release_changed", 409)
    assert job_count() == 0


