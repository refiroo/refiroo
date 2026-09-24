"""WP-5 integration: atomic mapping replacement via PUT /mappings."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_relation_set_versions import (
    _create_codelist,
    _create_domain,
    _create_master_value,
    _create_system_value,
    _mapping_endpoints,
    _set_version,
    _suffix,
)

from app.config import reload_settings
from app.db import get_engine
from app.main import create_app
from app.services.model.registry import model_registry

RELATION_TYPE = "system-value-maps-to-master"
FROM_TYPE = "system-value"
TO_TYPE = "master-value"
BASE = "/api/v1/workspaces/default"
PUT = BASE + "/mappings"


def _live_set_version(anchor_id, direction):
    return _set_version("default", None, RELATION_TYPE, FROM_TYPE, TO_TYPE, anchor_id, direction)


def _draft_set_version(draft_id, anchor_id, direction):
    return _set_version(
        "default", draft_id, RELATION_TYPE, FROM_TYPE, TO_TYPE, anchor_id, direction
    )


def _replacement_body(
    sv,
    mv,
    version,
    *,
    direction="outgoing",
    target=...,
    attrs=None,
    draft_id=None,
    draft_version=None,
):
    body = {
        "relationTypeKey": RELATION_TYPE,
        "fromObjectTypeKey": FROM_TYPE,
        "toObjectTypeKey": TO_TYPE,
        "direction": direction,
        "sourceObjectId": sv["id"],
        "expectedMappingVersion": version,
    }
    if target is not ...:
        body["targetObjectId"] = target["id"] if target else None
    if attrs is not None:
        body["attributes"] = attrs
    if draft_id:
        body["workspaceDraftId"] = draft_id
    if draft_version is not None:
        body["expectedWorkspaceDraftVersion"] = draft_version
    return body


def _make_model(
    tmp_path,
    monkeypatch,
    database_url,
    *,
    cardinality="many-to-many",
    attr_key=None,
    no_mapping_views=False,
    independent_binding=False,
    required=False,
    oriented=True,
    ancestor_type=None,
):
    model = json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
    if no_mapping_views:
        for app in model["applications"]:
            for view in app["views"]:
                if view["type"] == "mappingGrid":
                    config = view["config"]
                    view["objectTypeKey"] = (
                        config["fromObjectTypeKey"]
                        if config["direction"] == "outgoing"
                        else config["toObjectTypeKey"]
                    )
                    view["type"] = "table"
                    view["config"] = {
                        "columns": ["name"],
                        "filterFields": ["name"],
                        "sortFields": ["name"],
                        "defaultSort": "name",
                        "pageSize": 20,
                    }
    if attr_key:
        model["attributeTypes"].append(
            {"key": attr_key, "name": attr_key.title(), "valueType": "integer"}
        )
    binding = next(
        row for row in model["objectTypeRelations"] if row["relationTypeKey"] == RELATION_TYPE
    )
    binding["cardinality"] = cardinality
    binding["required"] = required
    next(row for row in model["relationTypes"] if row["key"] == RELATION_TYPE)["isOriented"] = (
        oriented
    )
    if ancestor_type:
        binding.setdefault("features", {})["uniqueToAncestorTypeKey"] = ancestor_type
    if independent_binding:
        extra = json.loads(
            json.dumps(next(row for row in model["relationTypes"] if row["key"] == RELATION_TYPE))
        )
        extra.update(
            key="alternate-mapping",
            reverseKey="alternate-mapped-from",
            name="Alternate target",
            reverseName="Alternate source",
        )
        model["relationTypes"].append(extra)
        model["objectTypeRelations"].append({**binding, "relationTypeKey": "alternate-mapping"})
    if attr_key:
        binding["attributeTypeKeys"] = [attr_key]
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database, request):
    options = getattr(request, "param", False)
    options = options if isinstance(options, dict) else {"no_mapping_views": options}
    _make_model(tmp_path, monkeypatch, migrated_database(), **options)
    with TestClient(create_app()) as c:
        with get_engine().connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        yield c
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture
def attr_client(tmp_path, monkeypatch, migrated_database):
    _make_model(tmp_path, monkeypatch, migrated_database(), attr_key="rank")
    with TestClient(create_app()) as c:
        with get_engine().connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        yield c
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture
def oto_client(tmp_path, monkeypatch, migrated_database):
    _make_model(tmp_path, monkeypatch, migrated_database(), cardinality="one-to-one")
    with TestClient(create_app()) as c:
        with get_engine().connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        yield c
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture
def otm_client(tmp_path, monkeypatch, migrated_database):
    _make_model(tmp_path, monkeypatch, migrated_database(), cardinality="one-to-many")
    with TestClient(create_app()) as c:
        with get_engine().connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        yield c
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _create_relation(client, sv, mv, **kw):
    r = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": RELATION_TYPE,
            "fromObjectId": sv["id"],
            "toObjectId": mv["id"],
            **kw,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _endpoints(client):
    s = _suffix()
    return _mapping_endpoints(client, s)


# ---------------------------------------------------------------------------
# 1. Create (unmapped → mapped)
# ---------------------------------------------------------------------------


def test_create_mapping_from_unmapped(client):
    sv, mv = _endpoints(client)
    body = _replacement_body(sv, mv, 0, target=mv)
    r = client.put(PUT, json=body)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["state"] == "mapped"
    assert result["mappingVersion"] == 1
    assert result["sourceObjectId"] == sv["id"]
    assert result["relationId"] is not None
    assert _live_set_version(sv["id"], "outgoing") == 1
    assert _live_set_version(mv["id"], "incoming") == 1


# ---------------------------------------------------------------------------
# 2. Replace (mapped → different target)
# ---------------------------------------------------------------------------


def test_replace_target(client):
    sv, mv1 = _endpoints(client)
    s = _suffix()
    domain = _create_domain(client, s)
    codelist = _create_codelist(client, s, domain["id"])
    mv2 = _create_master_value(client, s, codelist["id"])

    r1 = client.put(PUT, json=_replacement_body(sv, mv1, 0, target=mv1))
    assert r1.status_code == 200

    r2 = client.put(PUT, json=_replacement_body(sv, mv2, 1, target=mv2))
    assert r2.status_code == 200
    result = r2.json()
    assert result["state"] == "mapped"
    assert result["mappingVersion"] == 2
    assert result["relationId"] != r1.json()["relationId"]
    assert _live_set_version(sv["id"], "outgoing") == 2
    assert _live_set_version(mv1["id"], "incoming") == 2
    assert _live_set_version(mv2["id"], "incoming") == 1


# ---------------------------------------------------------------------------
# 3. Remove (mapped → unmapped)
# ---------------------------------------------------------------------------


def test_clear_mapping(client):
    sv, mv = _endpoints(client)
    client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))
    r = client.put(PUT, json=_replacement_body(sv, mv, 1, target=None))
    assert r.status_code == 200
    result = r.json()
    assert result["state"] == "unmapped"
    assert result["mappingVersion"] == 2
    assert result["relationId"] is None


# ---------------------------------------------------------------------------
# 4. Idempotent no-op (same target, same attributes)
# ---------------------------------------------------------------------------


def test_noop_same_target_same_attributes(client):
    sv, mv = _endpoints(client)
    r1 = client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))
    relation_id = r1.json()["relationId"]
    r2 = client.put(PUT, json=_replacement_body(sv, mv, 1, target=mv))
    assert r2.status_code == 200
    result = r2.json()
    assert result["mappingVersion"] == 1
    assert result["relationId"] == relation_id
    assert result["state"] == "mapped"


def test_noop_clearing_already_unmapped(client):
    sv, mv = _endpoints(client)
    r = client.put(PUT, json=_replacement_body(sv, mv, 0, target=None))
    assert r.status_code == 200
    assert r.json()["state"] == "unmapped"
    assert r.json()["mappingVersion"] == 0


# ---------------------------------------------------------------------------
# 5. Version conflict (stale expectedMappingVersion)
# ---------------------------------------------------------------------------


def test_stale_version_returns_409(client):
    sv, mv = _endpoints(client)
    client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))
    r = client.put(PUT, json=_replacement_body(sv, mv, 0, target=None))
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "mapping_version_conflict"
    assert err["details"]["mappingVersion"] == 1
    assert err["details"]["targetCount"] == 1


def test_stale_version_checked_before_noop(client):
    sv, mv = _endpoints(client)
    client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))
    r = client.put(PUT, json=_replacement_body(sv, mv, 99, target=mv))
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# 6. Attribute handling
# ---------------------------------------------------------------------------


def test_attributes_explicit_replace(attr_client):
    sv, mv = _endpoints(attr_client)
    r1 = attr_client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv, attrs={"rank": 10}))
    assert r1.status_code == 200
    r2 = attr_client.put(PUT, json=_replacement_body(sv, mv, 1, target=mv, attrs={"rank": 20}))
    assert r2.status_code == 200
    assert r2.json()["mappingVersion"] == 2


def test_attributes_omitted_preserves_retained(attr_client):
    sv, mv = _endpoints(attr_client)
    attr_client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv, attrs={"rank": 42}))
    r = attr_client.put(PUT, json=_replacement_body(sv, mv, 1, target=mv))
    assert r.status_code == 200
    assert r.json()["mappingVersion"] == 1


def test_attributes_empty_dict_clears(attr_client):
    sv, mv = _endpoints(attr_client)
    attr_client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv, attrs={"rank": 42}))
    r = attr_client.put(PUT, json=_replacement_body(sv, mv, 1, target=mv, attrs={}))
    assert r.status_code == 200
    assert r.json()["mappingVersion"] == 2


def test_clear_with_nonempty_attributes_rejected(client):
    sv, mv = _endpoints(client)
    r = client.put(PUT, json=_replacement_body(sv, mv, 0, target=None, attrs={"rank": 1}))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_clear_attributes"


# ---------------------------------------------------------------------------
# 7. Retained identity: replacing ambiguous → mapped keeps edge UUID
# ---------------------------------------------------------------------------


def test_retained_identity(client):
    sv, mv = _endpoints(client)
    s = _suffix()
    domain = _create_domain(client, s)
    codelist = _create_codelist(client, s, domain["id"])
    mv2 = _create_master_value(client, s, codelist["id"])
    rel1 = _create_relation(client, sv, mv)
    _create_relation(client, sv, mv2)
    ver = _live_set_version(sv["id"], "outgoing")
    r = client.put(PUT, json=_replacement_body(sv, mv, ver, target=mv))
    assert r.status_code == 200
    assert r.json()["relationId"] == rel1["id"]


# ---------------------------------------------------------------------------
# 8. Both directions (outgoing and incoming)
# ---------------------------------------------------------------------------


def test_incoming_direction(client):
    sv, mv = _endpoints(client)
    body = _replacement_body(sv, mv, 0, direction="incoming", target=sv)
    body["sourceObjectId"] = mv["id"]
    r = client.put(PUT, json=body)
    assert r.status_code == 200
    result = r.json()
    assert result["state"] == "mapped"
    assert result["sourceObjectId"] == mv["id"]
    assert _live_set_version(mv["id"], "incoming") == 1
    assert _live_set_version(sv["id"], "outgoing") == 1


# ---------------------------------------------------------------------------
# 9. Containment binding rejected
# ---------------------------------------------------------------------------


def test_containment_binding_rejected(client):
    s = _suffix()
    domain = _create_domain(client, s)
    codelist = _create_codelist(client, s, domain["id"])
    body = {
        "relationTypeKey": "codelist-contains-value",
        "fromObjectTypeKey": "codelist",
        "toObjectTypeKey": "master-value",
        "direction": "outgoing",
        "sourceObjectId": codelist["id"],
        "targetObjectId": domain["id"],
        "expectedMappingVersion": 0,
    }
    r = client.put(PUT, json=body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "immutable_relation"


# ---------------------------------------------------------------------------
# 10. Cross-cardinality (one-to-one)
# ---------------------------------------------------------------------------


def test_one_to_one_cross_cardinality_violation(oto_client):
    sv1, mv = _endpoints(oto_client)
    sv2 = _create_system_value(oto_client, _suffix())
    oto_client.put(PUT, json=_replacement_body(sv1, mv, 0, target=mv))
    ver = _live_set_version(sv2["id"], "outgoing")
    r = oto_client.put(PUT, json=_replacement_body(sv2, mv, ver, target=mv))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "cardinality_violation"


# ---------------------------------------------------------------------------
# 11. One-to-many outgoing cross-cardinality
# ---------------------------------------------------------------------------


def test_one_to_many_outgoing_cross_check(otm_client):
    sv1, mv = _endpoints(otm_client)
    sv2 = _create_system_value(otm_client, _suffix())
    otm_client.put(PUT, json=_replacement_body(sv1, mv, 0, target=mv))
    ver = _live_set_version(sv2["id"], "outgoing")
    r = otm_client.put(PUT, json=_replacement_body(sv2, mv, ver, target=mv))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "cardinality_violation"


def test_one_to_many_incoming_no_cross_check(otm_client):
    """Incoming direction on one-to-many does NOT cross-check."""
    sv1, mv = _endpoints(otm_client)
    sv2 = _create_system_value(otm_client, _suffix())
    body1 = _replacement_body(sv1, mv, 0, direction="incoming", target=sv1)
    body1["sourceObjectId"] = mv["id"]
    otm_client.put(PUT, json=body1)
    ver = _live_set_version(mv["id"], "incoming")
    body2 = _replacement_body(sv2, mv, ver, direction="incoming", target=sv2)
    body2["sourceObjectId"] = mv["id"]
    r = otm_client.put(PUT, json=body2)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 12. Draft context
# ---------------------------------------------------------------------------


def _create_draft(client):
    r = client.post(f"{BASE}/drafts", json={"source": "currentLive"})
    assert r.status_code == 201, r.text
    return r.json()


def _draft_version(client, draft_id):
    r = client.get(f"/api/v1/workspace-drafts/{draft_id}")
    assert r.status_code == 200, r.text
    return r.json()["version"]


def test_draft_create_and_clear(client):
    sv, mv = _endpoints(client)
    draft = _create_draft(client)
    dv = draft["version"]
    body = _replacement_body(sv, mv, 0, target=mv, draft_id=draft["id"], draft_version=dv)
    r = client.put(PUT, json=body)
    assert r.status_code == 200
    result = r.json()
    assert result["state"] == "mapped"
    assert result["workspaceDraftVersion"] is not None
    dv2 = _draft_version(client, draft["id"])
    ver = _draft_set_version(draft["id"], sv["id"], "outgoing")
    body2 = _replacement_body(sv, mv, ver, target=None, draft_id=draft["id"], draft_version=dv2)
    r2 = client.put(PUT, json=body2)
    assert r2.status_code == 200
    assert r2.json()["state"] == "unmapped"


def test_draft_stale_draft_version_409(client):
    sv, mv = _endpoints(client)
    draft = _create_draft(client)
    body = _replacement_body(sv, mv, 0, target=mv, draft_id=draft["id"], draft_version=999)
    r = client.put(PUT, json=body)
    assert r.status_code == 409


def test_draft_missing_draft_version_409(client):
    sv, mv = _endpoints(client)
    draft = _create_draft(client)
    body = _replacement_body(sv, mv, 0, target=mv, draft_id=draft["id"])
    r = client.put(PUT, json=body)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "workspace_draft_required"


def test_replacement_authority_follows_the_addressed_workspace_context(client):
    key = f"archive-{_suffix()}"
    created = client.post("/api/v1/workspaces", json={"key": key, "label": "Archive"})
    assert created.status_code == 201, created.text
    sv, mv = _mapping_endpoints(client, _suffix(), ws=key)
    archive_put = f"/api/v1/workspaces/{key}/mappings"
    mapped = client.put(archive_put, json=_replacement_body(sv, mv, 0, target=mv))
    assert mapped.status_code == 200, mapped.text
    draft = client.post(f"/api/v1/workspaces/{key}/drafts", json={"source": "currentLive"})
    assert draft.status_code == 201, draft.text
    draft = draft.json()

    def mapping_state():
        relations = client.get(
            "/api/v1/relations",
            params={"objectId": sv["id"], "workspaceKey": key, "relationTypeKey": RELATION_TYPE},
        )
        assert relations.status_code == 200, relations.text
        return (
            _set_version(key, None, RELATION_TYPE, FROM_TYPE, TO_TYPE, sv["id"], "outgoing"),
            [row["relation"]["id"] for row in relations.json()["items"]],
            _draft_version(client, draft["id"]),
        )

    before = mapping_state()
    assert len(before[1]) == 1

    # A draft is addressed only through its own workspace; the default is never substituted.
    foreign = client.put(
        PUT,
        json=_replacement_body(
            sv, mv, 0, target=None, draft_id=draft["id"], draft_version=draft["version"]
        ),
    )
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "workspace_draft_not_found"
    unknown = client.put(
        f"/api/v1/workspaces/missing-{_suffix()}/mappings",
        json=_replacement_body(sv, mv, before[0], target=None),
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "workspace_not_found"
    # Immutable history has no write context.
    revision = client.put(
        archive_put,
        json={
            **_replacement_body(sv, mv, before[0], target=None),
            "workspaceRevisionId": draft["id"],
        },
    )
    assert revision.status_code == 422
    assert mapping_state() == before

    retired = client.patch(
        f"/api/v1/workspaces/{key}",
        json={"status": "retired", "expectedVersion": created.json()["version"]},
    )
    assert retired.status_code == 200, retired.text
    live = client.put(archive_put, json=_replacement_body(sv, mv, before[0], target=None))
    assert live.status_code == 409
    assert live.json()["error"]["code"] == "workspace_retired"
    in_draft = client.put(
        archive_put,
        json=_replacement_body(
            sv, mv, 0, target=None, draft_id=draft["id"], draft_version=draft["version"]
        ),
    )
    assert in_draft.status_code == 409
    assert in_draft.json()["error"]["code"] == "workspace_retired"
    assert mapping_state() == before


# ---------------------------------------------------------------------------
# 13. Generic-write vs replacement race (set version reflects both)
# ---------------------------------------------------------------------------


def test_generic_write_bumps_mapping_version(client):
    sv, mv = _endpoints(client)
    _create_relation(client, sv, mv)
    ver = _live_set_version(sv["id"], "outgoing")
    assert ver == 1
    r = client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# 14. Conflict response shows correct target for incoming direction
# ---------------------------------------------------------------------------


def test_incoming_conflict_shows_correct_target(client):
    """Conflict details must return the target (from_object for incoming), not the source."""
    sv, mv = _endpoints(client)
    body = _replacement_body(sv, mv, 0, direction="incoming", target=sv)
    body["sourceObjectId"] = mv["id"]
    r1 = client.put(PUT, json=body)
    assert r1.status_code == 200

    body2 = _replacement_body(sv, mv, 0, direction="incoming", target=None)
    body2["sourceObjectId"] = mv["id"]
    r2 = client.put(PUT, json=body2)
    assert r2.status_code == 409
    details = r2.json()["error"]["details"]
    assert details["targetCount"] == 1
    assert details["targets"][0]["object"]["id"] == sv["id"]


# ---------------------------------------------------------------------------
# 15. Draft no-op does not increment draft version
# ---------------------------------------------------------------------------


def test_draft_noop_clear_unmapped_preserves_draft_version(client):
    sv, mv = _endpoints(client)
    draft = _create_draft(client)
    dv = draft["version"]
    body = _replacement_body(sv, mv, 0, target=None, draft_id=draft["id"], draft_version=dv)
    r = client.put(PUT, json=body)
    assert r.status_code == 200
    assert r.json()["state"] == "unmapped"
    assert _draft_version(client, draft["id"]) == dv


def test_draft_noop_same_target_preserves_draft_version(client):
    sv, mv = _endpoints(client)
    draft = _create_draft(client)
    dv = draft["version"]
    body = _replacement_body(sv, mv, 0, target=mv, draft_id=draft["id"], draft_version=dv)
    r1 = client.put(PUT, json=body)
    assert r1.status_code == 200
    dv2 = _draft_version(client, draft["id"])
    ver = _draft_set_version(draft["id"], sv["id"], "outgoing")
    body2 = _replacement_body(sv, mv, ver, target=mv, draft_id=draft["id"], draft_version=dv2)
    r2 = client.put(PUT, json=body2)
    assert r2.status_code == 200
    assert r2.json()["mappingVersion"] == ver
    assert _draft_version(client, draft["id"]) == dv2


@pytest.mark.parametrize("mapped", [False, True])
def test_draft_noop_rejects_stale_aggregate_token(client, mapped):
    sv, mv = _endpoints(client)
    if mapped:
        _create_relation(client, sv, mv)
    draft = _create_draft(client)
    response = client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            0,
            target=mv if mapped else None,
            draft_id=draft["id"],
            draft_version=draft["version"] + 1,
        ),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "workspace_draft_version_conflict"
    assert _draft_version(client, draft["id"]) == draft["version"]


def test_concurrent_replacements_claim_initial_set_once(client):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    sv, mv = _endpoints(client)
    barrier = Barrier(2)

    def save():
        barrier.wait(timeout=10)
        return client.put(PUT, json=_replacement_body(sv, mv, 0, target=mv))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] == "mapping_version_conflict"
    assert _live_set_version(sv["id"], "outgoing") == 1


def test_draft_attribute_update_and_clear_record_relation_audits(attr_client):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import AuditEvent

    sv, mv = _endpoints(attr_client)
    relation = _create_relation(attr_client, sv, mv, attributes={"rank": 1})
    draft = _create_draft(attr_client)
    updated = attr_client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            0,
            target=mv,
            attrs={"rank": 2},
            draft_id=draft["id"],
            draft_version=draft["version"],
        ),
    )
    assert updated.status_code == 200, updated.text
    cleared = attr_client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            1,
            target=None,
            draft_id=draft["id"],
            draft_version=updated.json()["workspaceDraftVersion"],
        ),
    )
    assert cleared.status_code == 200, cleared.text
    with SessionLocal() as session:
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "relation",
                    AuditEvent.aggregate_id == relation["id"],
                )
                .order_by(AuditEvent.sequence_id)
            )
        )
        assert [event.action for event in events] == ["created", "updated", "deleted"]
        assert events[-1].changes["workspaceDraftId"] == draft["id"]


@pytest.mark.parametrize("client", [False, True], indirect=True)
@pytest.mark.parametrize("draft_context", [False, True])
def test_conflict_preview_continues_without_loss(client, draft_context):
    sv, mv = _endpoints(client)
    targets = [mv]
    for _ in range(20):
        suffix = _suffix()
        domain = _create_domain(client, suffix)
        codelist = _create_codelist(client, suffix, domain["id"])
        targets.append(_create_master_value(client, suffix, codelist["id"]))
    relations = [_create_relation(client, sv, target) for target in targets]
    draft = _create_draft(client) if draft_context else None
    body = _replacement_body(
        sv,
        mv,
        999,
        target=mv,
        draft_id=draft["id"] if draft else None,
        draft_version=draft["version"] if draft else None,
    )
    response = client.put(PUT, json=body)
    assert response.status_code == 409, response.text
    details = response.json()["error"]["details"]
    assert details["targetCount"] == 21 and len(details["targets"]) == 20
    assert details["targetsNextCursor"]
    params = {
        "relationTypeKey": RELATION_TYPE,
        "fromObjectTypeKey": FROM_TYPE,
        "toObjectTypeKey": TO_TYPE,
        "direction": "outgoing",
        "sourceObjectId": sv["id"],
        "mappingVersion": details["mappingVersion"],
        "cursor": details["targetsNextCursor"],
        "applicationKey": details["applicationKey"],
        "viewKey": details["viewKey"],
    }
    params = {key: value for key, value in params.items() if value is not None}
    if draft:
        params["workspaceDraftId"] = draft["id"]
    continuation = client.get(BASE + "/mapping-targets", params=params)
    assert continuation.status_code == 200, continuation.text
    assert {row["relationId"] for row in details["targets"] + continuation.json()["items"]} == {
        row["id"] for row in relations
    }


def test_conditional_claim_rejects_changed_set_without_overwriting(client, monkeypatch):
    from app.services import mapping

    sv, mv = _endpoints(client)
    relation = _create_relation(client, sv, mv)
    original = mapping._get_set_version
    calls = 0

    def stale_read(*args, **kwargs):
        nonlocal calls
        calls += 1
        return 0 if calls == 1 else original(*args, **kwargs)

    monkeypatch.setattr(mapping, "_get_set_version", stale_read)
    response = client.put(PUT, json=_replacement_body(sv, mv, 0, target=None))
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "mapping_version_conflict"
    assert error["details"]["mappingVersion"] == 1
    assert error["details"]["targets"][0]["relationId"] == relation["id"]
    assert _live_set_version(sv["id"], "outgoing") == 1


@pytest.mark.parametrize("client", [{"attr_key": "rank"}], indirect=True)
@pytest.mark.parametrize("draft_source", ["currentLive", "revision"])
@pytest.mark.parametrize("mutation", ["add", "update", "delete"])
@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
def test_activation_refuses_live_divergence_in_touched_mapping_set(
    client, direction, mutation, draft_source
):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import ObjectRelation, Workspace, WorkspaceRevision

    sv, mv = _endpoints(client)
    old_relation = _create_relation(client, sv, mv, attributes={"rank": 1})
    if direction == "outgoing":
        _, other = _endpoints(client)
        from_obj, to_obj = sv, other
    else:
        other = _create_system_value(client, _suffix())
        from_obj, to_obj = other, mv
    different_edge = (
        _create_relation(client, from_obj, to_obj, attributes={"rank": 1})
        if mutation != "add"
        else None
    )
    active_revision_id = None
    if draft_source == "revision":
        seed = _create_draft(client)
        published = client.post(
            f"/api/v1/workspace-drafts/{seed['id']}/activation",
            json={"expectedDraftVersion": seed["version"], "expectedActiveRevisionId": None},
        )
        assert published.status_code == 200, published.text
        active_revision_id = published.json()["id"]
        derived = client.post(
            BASE + "/drafts",
            json={"source": "revision", "derivedFromRevisionId": active_revision_id},
        )
        assert derived.status_code == 201, derived.text
        draft = derived.json()
    else:
        draft = _create_draft(client)
    anchor, selected = (sv, mv) if direction == "outgoing" else (mv, sv)
    saved = client.put(
        PUT,
        json=_replacement_body(
            anchor,
            selected,
            0,
            target=None,
            direction=direction,
            draft_id=draft["id"],
            draft_version=draft["version"],
        ),
    )
    assert saved.status_code == 200, saved.text
    if mutation == "add":
        live_edge = _create_relation(client, from_obj, to_obj, attributes={"rank": 2})
    elif mutation == "update":
        result = client.patch(
            f"/api/v1/relations/{different_edge['id']}",
            json={"expectedVersion": 1, "attributes": {"rank": 2}},
        )
        assert result.status_code == 200, result.text
        live_edge = result.json()
    else:
        result = client.delete(
            f"/api/v1/relations/{different_edge['id']}", params={"expectedVersion": 1}
        )
        assert result.status_code == 204, result.text
        live_edge = None
    with SessionLocal() as session:
        before = [
            (row.id, row.version)
            for row in session.scalars(select(ObjectRelation).order_by(ObjectRelation.id))
        ]
        revision_count = len(list(session.scalars(select(WorkspaceRevision))))
    activation = client.post(
        f"/api/v1/workspace-drafts/{draft['id']}/activation",
        json={
            "expectedDraftVersion": saved.json()["workspaceDraftVersion"],
            "expectedActiveRevisionId": active_revision_id,
        },
    )
    assert activation.status_code == 409, activation.text
    assert activation.json()["error"]["code"] == "version_conflict"
    conflicts = activation.json()["error"]["details"]["conflicts"]
    assert any(
        item["kind"] == "mapping-set"
        and item["anchorObjectId"] == anchor["id"]
        and item["direction"] == direction
        for item in conflicts
    )
    assert _draft_version(client, draft["id"]) == saved.json()["workspaceDraftVersion"]
    with SessionLocal() as session:
        assert [
            (row.id, row.version)
            for row in session.scalars(select(ObjectRelation).order_by(ObjectRelation.id))
        ] == before
        assert len(list(session.scalars(select(WorkspaceRevision)))) == revision_count
        assert session.get(Workspace, "default").active_revision_id == active_revision_id
    assert old_relation["id"] in {item[0] for item in before}
    if live_edge:
        assert live_edge["id"] in {item[0] for item in before}
    assert any(
        "Review live mappings" in item["message"]
        for item in conflicts
        if item["kind"] == "mapping-set"
    )


@pytest.mark.parametrize("client", [{"independent_binding": True}], indirect=True)
@pytest.mark.parametrize("draft_context", [False, True])
def test_independent_binding_is_unchanged_by_replacement_and_clear(client, draft_context):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import ObjectRelation, WorkspaceDraftRelation

    sv, mv = _endpoints(client)
    extra = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": "alternate-mapping",
            "fromObjectId": sv["id"],
            "toObjectId": mv["id"],
        },
    )
    assert extra.status_code == 201, extra.text
    draft = _create_draft(client) if draft_context else None
    draft_id = draft["id"] if draft else None
    extra_versions = [
        _set_version(
            "default", draft_id, "alternate-mapping", FROM_TYPE, TO_TYPE, anchor["id"], direction
        )
        for anchor, direction in [(sv, "outgoing"), (mv, "incoming")]
    ]
    version = draft["version"] if draft else None
    saved = client.put(
        PUT, json=_replacement_body(sv, mv, 0, target=mv, draft_id=draft_id, draft_version=version)
    )
    assert saved.status_code == 200, saved.text
    cleared = client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            1,
            target=None,
            draft_id=draft_id,
            draft_version=saved.json()["workspaceDraftVersion"],
        ),
    )
    assert cleared.status_code == 200, cleared.text
    assert [
        _set_version(
            "default", draft_id, "alternate-mapping", FROM_TYPE, TO_TYPE, anchor["id"], direction
        )
        for anchor, direction in [(sv, "outgoing"), (mv, "incoming")]
    ] == extra_versions
    with SessionLocal() as session:
        edge = session.scalar(select(ObjectRelation).where(ObjectRelation.id == extra.json()["id"]))
        assert edge is not None and edge.version == 1
        assert (
            session.scalar(
                select(WorkspaceDraftRelation).where(
                    WorkspaceDraftRelation.draft_id == draft_id,
                    WorkspaceDraftRelation.relation_id == extra.json()["id"],
                )
            )
            is None
        )
    # The second binding is itself replaceable in the reverse direction.
    extra_body = _replacement_body(
        mv,
        sv,
        extra_versions[1],
        target=sv,
        direction="incoming",
        draft_id=draft_id,
        draft_version=cleared.json()["workspaceDraftVersion"],
    )
    extra_body["relationTypeKey"] = "alternate-mapping"
    result = client.put(PUT, json=extra_body)
    assert result.status_code == 200, result.text
    assert result.json()["relationId"] == extra.json()["id"]


@pytest.mark.parametrize(
    "client",
    [{"required": True, "cardinality": "one-to-many", "no_mapping_views": True}],
    indirect=True,
)
@pytest.mark.parametrize("draft_context", [False, True])
def test_required_ownership_binding_is_rejected_before_endpoint_changes(client, draft_context):
    from uuid import uuid4

    draft = _create_draft(client) if draft_context else None
    body = _replacement_body(
        {"id": str(uuid4())},
        None,
        0,
        target=None,
        draft_id=draft["id"] if draft else None,
        draft_version=draft["version"] if draft else None,
    )
    result = client.put(PUT, json=body)
    assert result.status_code == 422, result.text
    assert result.json()["error"]["code"] == "required_ownership_binding"
    if draft:
        assert _draft_version(client, draft["id"]) == draft["version"]


@pytest.mark.parametrize("client", [{"required": True}], indirect=True)
@pytest.mark.parametrize("draft_context", [False, True])
def test_required_mapping_cannot_be_cleared(client, draft_context):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import ObjectRelation

    suffix = _suffix()
    sv = _create_system_value(client, suffix)
    domain = _create_domain(client, suffix)
    codelist = _create_codelist(client, suffix, domain["id"])
    target = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": "default",
            "applicationKey": "rdm-master",
            "objectTypeKey": TO_TYPE,
            "name": "Required target",
            "parentObjectId": codelist["id"],
            "attributes": [
                {"attributeTypeKey": key, "value": suffix}
                for key in ["master-id", "value-code", "value-name"]
            ],
            "initialRelations": [
                {
                    "relationTypeKey": RELATION_TYPE,
                    "direction": "incoming",
                    "otherObjectId": sv["id"],
                }
            ],
        },
    )
    assert target.status_code == 201, target.text
    mv = target.json()
    draft = _create_draft(client) if draft_context else None
    expected = 0 if draft else _live_set_version(sv["id"], "outgoing")
    result = client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            expected,
            target=None,
            draft_id=draft["id"] if draft else None,
            draft_version=draft["version"] if draft else None,
        ),
    )
    assert result.status_code == 422, result.text
    assert result.json()["error"]["code"] == "required_relation"
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(ObjectRelation.id).where(
                    ObjectRelation.relation_type_key == RELATION_TYPE,
                    ObjectRelation.from_object_id == sv["id"],
                    ObjectRelation.to_object_id == mv["id"],
                )
            )
            is not None
        )
    if draft:
        assert _draft_version(client, draft["id"]) == draft["version"]


@pytest.mark.parametrize("mutation", ["create", "update", "delete"])
def test_overlapping_generic_write_forces_mapping_save_to_refresh(
    attr_client, monkeypatch, mutation
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import event, select

    import app.routers.mapping as mapping_router
    from app.db import SessionLocal
    from app.models.database import ObjectRelation

    sv, mv = _endpoints(attr_client)
    relation = (
        _create_relation(attr_client, sv, mv, attributes={"rank": 1})
        if mutation != "create"
        else None
    )
    expected = 1 if relation else 0
    generic_written, release_generic, mapping_started = Event(), Event(), Event()
    engine = get_engine()
    operation = {"create": "INSERT INTO", "update": "UPDATE", "delete": "DELETE FROM"}[mutation]

    def pause_generic(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith(operation + " object_relations"):
            generic_written.set()
            assert release_generic.wait(10), "generic write was not released"

    original = mapping_router.replace_mapping

    def mapping_save(*args, **kwargs):
        mapping_started.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(mapping_router, "replace_mapping", mapping_save)
    event.listen(engine, "after_cursor_execute", pause_generic)

    def generic_save():
        if mutation == "create":
            return attr_client.post(
                "/api/v1/relations",
                json={
                    "relationTypeKey": RELATION_TYPE,
                    "fromObjectId": sv["id"],
                    "toObjectId": mv["id"],
                    "attributes": {"rank": 2},
                },
            )
        if mutation == "update":
            return attr_client.patch(
                f"/api/v1/relations/{relation['id']}",
                json={"expectedVersion": 1, "attributes": {"rank": 2}},
            )
        return attr_client.delete(
            f"/api/v1/relations/{relation['id']}", params={"expectedVersion": 1}
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            generic = pool.submit(generic_save)
            try:
                assert generic_written.wait(10), "generic write did not reach persistence"
                mapping = pool.submit(
                    attr_client.put,
                    PUT,
                    json=_replacement_body(sv, mv, expected, target=mv, attrs={"rank": 3}),
                )
                assert mapping_started.wait(10), "mapping request did not overlap generic write"
            finally:
                release_generic.set()
            generic_result, mapping_result = generic.result(timeout=15), mapping.result(timeout=15)
    finally:
        release_generic.set()
        event.remove(engine, "after_cursor_execute", pause_generic)
    assert generic_result.status_code == {"create": 201, "update": 200, "delete": 204}[mutation], (
        generic_result.text
    )
    assert mapping_result.status_code == 409, mapping_result.text
    assert mapping_result.json()["error"]["code"] == "mapping_version_conflict"
    assert _live_set_version(sv["id"], "outgoing") == expected + 1
    assert _live_set_version(mv["id"], "incoming") == expected + 1
    with SessionLocal() as session:
        edge = session.scalar(
            select(ObjectRelation).where(
                ObjectRelation.from_object_id == sv["id"],
                ObjectRelation.to_object_id == mv["id"],
                ObjectRelation.relation_type_key == RELATION_TYPE,
            )
        )
        if mutation == "delete":
            assert edge is None
        else:
            assert edge.attributes == {"rank": 2}
            if relation:
                assert edge.id == relation["id"]


@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
def test_activation_protects_initially_empty_mapping_set(client, direction):
    sv, mv = _endpoints(client)
    other_sv, other_mv = _endpoints(client)
    draft = _create_draft(client)
    anchor, selected = (sv, mv) if direction == "outgoing" else (mv, sv)
    saved = client.put(
        PUT,
        json=_replacement_body(
            anchor,
            selected,
            0,
            target=selected,
            direction=direction,
            draft_id=draft["id"],
            draft_version=draft["version"],
        ),
    )
    assert saved.status_code == 200, saved.text
    live_edge = (
        _create_relation(client, sv, other_mv)
        if direction == "outgoing"
        else _create_relation(client, other_sv, mv)
    )
    response = client.post(
        f"/api/v1/workspace-drafts/{draft['id']}/activation",
        json={
            "expectedDraftVersion": saved.json()["workspaceDraftVersion"],
            "expectedActiveRevisionId": None,
        },
    )
    assert response.status_code == 409, response.text
    conflicts = response.json()["error"]["details"]["conflicts"]
    assert any(
        item["kind"] == "mapping-set"
        and item["anchorObjectId"] == anchor["id"]
        and item["expectedTargetCount"] == 0
        for item in conflicts
    )
    assert _live_set_version(anchor["id"], direction) == 1
    assert _draft_version(client, draft["id"]) == saved.json()["workspaceDraftVersion"]
    page = client.get(
        BASE + "/mapping-targets",
        params={
            "relationTypeKey": RELATION_TYPE,
            "fromObjectTypeKey": FROM_TYPE,
            "toObjectTypeKey": TO_TYPE,
            "direction": direction,
            "sourceObjectId": anchor["id"],
            "mappingVersion": 1,
        },
    )
    assert page.status_code == 200, page.text
    assert [item["relationId"] for item in page.json()["items"]] == [live_edge["id"]]


@pytest.mark.parametrize("client", [{"independent_binding": True}], indirect=True)
@pytest.mark.parametrize("unrelated_binding", [False, True])
def test_activation_preserves_unrelated_live_mapping_work(client, unrelated_binding):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import ObjectRelation

    sv, mv = _endpoints(client)
    other_sv, other_mv = (sv, mv) if unrelated_binding else _endpoints(client)
    draft = _create_draft(client)
    saved = client.put(
        PUT,
        json=_replacement_body(
            sv, mv, 0, target=mv, draft_id=draft["id"], draft_version=draft["version"]
        ),
    )
    assert saved.status_code == 200, saved.text
    relation_type = "alternate-mapping" if unrelated_binding else RELATION_TYPE
    live = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": relation_type,
            "fromObjectId": other_sv["id"],
            "toObjectId": other_mv["id"],
        },
    )
    assert live.status_code == 201, live.text
    response = client.post(
        f"/api/v1/workspace-drafts/{draft['id']}/activation",
        json={
            "expectedDraftVersion": saved.json()["workspaceDraftVersion"],
            "expectedActiveRevisionId": None,
        },
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as session:
        assert (
            session.scalar(select(ObjectRelation.id).where(ObjectRelation.id == live.json()["id"]))
            == live.json()["id"]
        )
        assert (
            session.scalar(
                select(ObjectRelation.id).where(ObjectRelation.id == saved.json()["relationId"])
            )
            == saved.json()["relationId"]
        )
    assert _live_set_version(sv["id"], "outgoing") == 1
    assert (
        _set_version("default", None, relation_type, FROM_TYPE, TO_TYPE, other_sv["id"], "outgoing")
        == 1
    )


def test_activation_bounds_mapping_set_diagnostics(client):
    first, mv = _endpoints(client)
    sources = [first] + [_create_system_value(client, _suffix()) for _ in range(20)]
    draft = _create_draft(client)
    draft_version = draft["version"]
    for source in sources:
        result = client.put(
            PUT,
            json=_replacement_body(
                source, mv, 0, target=mv, draft_id=draft["id"], draft_version=draft_version
            ),
        )
        assert result.status_code == 200, result.text
        draft_version = result.json()["workspaceDraftVersion"]
        _create_relation(client, source, mv)
    response = client.post(
        f"/api/v1/workspace-drafts/{draft['id']}/activation",
        json={"expectedDraftVersion": draft_version, "expectedActiveRevisionId": None},
    )
    assert response.status_code == 409, response.text
    details = response.json()["error"]["details"]
    assert details["mappingSetConflictCount"] == 22
    assert details["mappingSetConflictsTruncated"] is True
    assert len([item for item in details["conflicts"] if item["kind"] == "mapping-set"]) == 20
    assert _draft_version(client, draft["id"]) == draft_version
    assert _live_set_version(mv["id"], "incoming") == 21


@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
def test_activation_accepts_restored_source_graph_despite_advanced_live_token(client, direction):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.database import ObjectRelation, WorkspaceDraft

    sv, mv = _endpoints(client)
    original = _create_relation(client, sv, mv)
    other_sv, other_mv = _endpoints(client)
    draft = _create_draft(client)
    anchor, target = (sv, mv) if direction == "outgoing" else (mv, sv)
    cleared = client.put(
        PUT,
        json=_replacement_body(
            anchor,
            target,
            0,
            target=None,
            direction=direction,
            draft_id=draft["id"],
            draft_version=draft["version"],
        ),
    )
    assert cleared.status_code == 200, cleared.text
    temporary = (
        _create_relation(client, sv, other_mv)
        if direction == "outgoing"
        else _create_relation(client, other_sv, mv)
    )
    deleted = client.delete(f"/api/v1/relations/{temporary['id']}", params={"expectedVersion": 1})
    assert deleted.status_code == 204, deleted.text
    assert _live_set_version(anchor["id"], direction) == 3
    activated = client.post(
        f"/api/v1/workspace-drafts/{draft['id']}/activation",
        json={
            "expectedDraftVersion": cleared.json()["workspaceDraftVersion"],
            "expectedActiveRevisionId": None,
        },
    )
    assert activated.status_code == 200, activated.text
    with SessionLocal() as session:
        assert (
            session.scalar(select(WorkspaceDraft.id).where(WorkspaceDraft.id == draft["id"]))
            is None
        )
        assert (
            session.scalar(
                select(ObjectRelation.id).where(
                    ObjectRelation.id.in_([original["id"], temporary["id"]])
                )
            )
            is None
        )
    assert _live_set_version(anchor["id"], direction) == 4


@pytest.mark.parametrize("client", [{"ancestor_type": "codelist"}], indirect=True)
@pytest.mark.parametrize("draft_context", [False, True])
def test_replacement_validates_final_ancestor_scope(client, draft_context):
    sv, mv = _endpoints(client)
    other = _create_master_value(client, _suffix(), mv["parentObjectId"])
    edge = _create_relation(client, sv, mv)
    draft = _create_draft(client) if draft_context else None
    response = client.put(
        PUT,
        json=_replacement_body(
            other,
            sv,
            0,
            direction="incoming",
            target=sv,
            draft_id=draft["id"] if draft else None,
            draft_version=draft["version"] if draft else None,
        ),
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "duplicate_relation_scope"
    assert "ancestor scope" in response.json()["error"]["message"]
    assert _live_set_version(other["id"], "incoming") == 0
    if draft:
        assert _draft_version(client, draft["id"]) == draft["version"]
    # Replacing an outgoing edge within the same scope validates the final graph.
    response = client.put(
        PUT,
        json=_replacement_body(
            sv,
            other,
            0 if draft else 1,
            target=other,
            draft_id=draft["id"] if draft else None,
            draft_version=draft["version"] if draft else None,
        ),
    )
    assert response.status_code == 200, response.text
    assert response.json()["relationId"] != edge["id"]


@pytest.mark.parametrize("client", [{"ancestor_type": "system"}], indirect=True)
@pytest.mark.parametrize("draft_context", [False, True])
def test_missing_mapping_ancestor_is_actionable_at_both_write_boundaries(client, draft_context):
    sv, mv = _endpoints(client)
    draft = _create_draft(client) if draft_context else None
    context = (
        {"workspaceDraftId": draft["id"], "expectedWorkspaceDraftVersion": draft["version"]}
        if draft
        else {}
    )
    generic = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": RELATION_TYPE,
            "fromObjectId": sv["id"],
            "toObjectId": mv["id"],
            **context,
        },
    )
    assert generic.status_code == 422, generic.text
    assert generic.json()["error"]["code"] == "relation_ancestor_required"
    response = client.put(
        PUT,
        json=_replacement_body(
            sv,
            mv,
            0,
            target=mv,
            draft_id=draft["id"] if draft else None,
            draft_version=draft["version"] if draft else None,
        ),
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "relation_ancestor_required"
    assert "ancestor of type 'system'" in response.json()["error"]["message"]
    assert _live_set_version(sv["id"], "outgoing") == 0
    if draft:
        assert _draft_version(client, draft["id"]) == draft["version"]


@pytest.mark.parametrize(
    "client",
    [{"required": True, "oriented": False, "cardinality": "one-to-many", "no_mapping_views": True}],
    indirect=True,
)
@pytest.mark.parametrize("draft_context", [False, True])
def test_nonoriented_required_ownership_replacement_is_rejected(client, draft_context):
    test_required_ownership_binding_is_rejected_before_endpoint_changes(client, draft_context)


@pytest.mark.parametrize("endpoint", ["mappings", "mapping-targets"])
@pytest.mark.parametrize(
    "identity",
    [
        {"applicationKey": "", "viewKey": "missing"},
        {"applicationKey": "", "viewKey": ""},
        {"applicationKey": ""},
    ],
)
def test_supplied_empty_view_identity_cannot_bypass_validation(client, endpoint, identity):
    sv, _ = _endpoints(client)
    params = dict(identity)
    if endpoint == "mapping-targets":
        params.update(
            relationTypeKey=RELATION_TYPE,
            fromObjectTypeKey=FROM_TYPE,
            toObjectTypeKey=TO_TYPE,
            direction="outgoing",
            sourceObjectId=sv["id"],
            mappingVersion=0,
        )
    response = client.get(BASE + "/" + endpoint, params=params)
    assert response.status_code == (404 if "viewKey" in identity else 422), response.text
