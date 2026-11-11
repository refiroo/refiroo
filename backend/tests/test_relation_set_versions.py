"""WP-3: Relation-set version persistence and generic participation.

Tests verify that every relation mutation atomically maintains set versions,
that different bindings have independent version tracks, and that change set/live
scopes stay isolated until activation.
"""

from uuid import uuid4

from harness_identity import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.database import RelationSetVersion


def _suffix():
    return uuid4().hex[:8]


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


WS = "default"


def _obj(client, suffix, app_key, type_key, name, attrs, *, ws=WS, parent=None):
    payload = {
        "applicationKey": app_key,
        "objectTypeKey": type_key,
        "name": name,
        "workspaceKey": ws,
        "attributes": attrs,
    }
    if parent:
        payload["parentObjectId"] = parent
    r = client.post("/api/v1/objects", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_domain(client, suffix, *, ws=WS):
    return _obj(
        client,
        suffix,
        "rdm-master",
        "domain",
        f"Domain {suffix}",
        [_attr("domain-code", f"DOM_{suffix}")],
        ws=ws,
    )


def _create_codelist(client, suffix, parent_id, *, ws=WS):
    return _obj(
        client,
        suffix,
        "rdm-master",
        "codelist",
        f"Codelist {suffix}",
        [_attr("codelist-code", f"CL_{suffix}")],
        ws=ws,
        parent=parent_id,
    )


def _create_master_value(client, suffix, codelist_id, *, ws=WS):
    return _obj(
        client,
        suffix,
        "rdm-master",
        "master-value",
        f"Master {suffix}",
        [
            _attr("master-id", f"MID_{suffix}"),
            _attr("value-code", f"VC_{suffix}"),
            _attr("value-name", f"Value {suffix}"),
        ],
        ws=ws,
        parent=codelist_id,
    )


def _create_system_value(client, suffix, *, ws=WS):
    system = _obj(
        client,
        suffix,
        "rdm-systems",
        "system",
        f"System {suffix}",
        [_attr("system-code", f"SYS_{suffix}")],
        ws=ws,
    )
    return _obj(
        client,
        suffix,
        "rdm-systems",
        "system-value",
        f"SysVal {suffix}",
        [
            _attr("value-code", f"SVC_{suffix}"),
            _attr("value-name", f"SysVal {suffix}"),
        ],
        ws=ws,
        parent=system["id"],
    )


def _mapping_endpoints(client, suffix, *, ws=WS):
    domain = _create_domain(client, suffix, ws=ws)
    codelist = _create_codelist(client, suffix, domain["id"], ws=ws)
    master = _create_master_value(client, suffix, codelist["id"], ws=ws)
    system_value = _create_system_value(client, suffix, ws=ws)
    return system_value, master


def _set_version(
    workspace_key, change_set_id, relation_type_key, from_type, to_type, anchor_id, direction
):
    with SessionLocal() as session:
        change_set_filter = (
            RelationSetVersion.change_set_id == change_set_id
            if change_set_id is not None
            else RelationSetVersion.change_set_id.is_(None)
        )
        row = session.scalar(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == workspace_key,
                change_set_filter,
                RelationSetVersion.relation_type_key == relation_type_key,
                RelationSetVersion.from_object_type_key == from_type,
                RelationSetVersion.to_object_type_key == to_type,
                RelationSetVersion.anchor_object_id == anchor_id,
                RelationSetVersion.direction == direction,
            )
        )
        return row.version if row else 0


def _live_set_version(relation_type_key, from_type, to_type, anchor_id, direction):
    return _set_version(
        "default", None, relation_type_key, from_type, to_type, anchor_id, direction
    )


# --- Live relation set-version tracking ---


def test_create_relation_increments_outgoing_and_incoming_set_versions():
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
            },
        )
        assert r.status_code == 201, r.text
        outgoing = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv["id"], "outgoing"
        )
        incoming = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", mv["id"], "incoming"
        )
        assert outgoing == 1
        assert incoming == 1


def test_update_relation_increments_set_versions():
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
            },
        )
        assert r.status_code == 201
        relation = r.json()
        updated = client.patch(
            f"/api/v1/relations/{relation['id']}",
            json={"attributes": {}, "expectedVersion": relation["version"]},
        )
        assert updated.status_code == 200, updated.text
        outgoing = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv["id"], "outgoing"
        )
        assert outgoing == 2


def test_delete_relation_increments_set_versions():
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
            },
        )
        assert r.status_code == 201
        relation = r.json()
        d = client.delete(
            f"/api/v1/relations/{relation['id']}",
            params={"expectedVersion": relation["version"]},
        )
        assert d.status_code == 204, d.text
        outgoing = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv["id"], "outgoing"
        )
        assert outgoing == 2


def test_different_bindings_have_independent_versions():
    """Two relations of the same type but different from/to type pairs get separate version tracks."""
    with TestClient(app) as client:
        s = _suffix()
        sv1, mv1 = _mapping_endpoints(client, s)
        s2 = _suffix()
        sv2, mv2 = _mapping_endpoints(client, s2)
        client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv1["id"],
                "toObjectId": mv1["id"],
            },
        )
        client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv2["id"],
                "toObjectId": mv2["id"],
            },
        )
        v1_outgoing = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv1["id"], "outgoing"
        )
        v2_outgoing = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv2["id"], "outgoing"
        )
        assert v1_outgoing == 1
        assert v2_outgoing == 1


# --- Change set relation set-version tracking ---


def _create_change_set(client):
    r = client.post("/api/v1/workspaces/default/change-sets", json={"source": "currentLive"})
    assert r.status_code == 201, r.text
    return r.json()


def _change_set_set_version(
    change_set_id, relation_type_key, from_type, to_type, anchor_id, direction
):
    return _set_version(
        "default", change_set_id, relation_type_key, from_type, to_type, anchor_id, direction
    )


def _change_set_set_version_count(change_set_id):
    with SessionLocal() as session:
        return len(
            list(
                session.scalars(
                    select(RelationSetVersion).where(
                        RelationSetVersion.change_set_id == change_set_id
                    )
                )
            )
        )


def _change_set_version(client, change_set_id):
    r = client.get(f"/api/v1/change-sets/{change_set_id}")
    assert r.status_code == 200, r.text
    return r.json()["version"]


def test_change_set_relation_create_increments_change_set_scoped_set_version():
    """Create objects live, snapshot into a change set, then create a relation in the change set."""
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        change_set = _create_change_set(client)
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert r.status_code == 201, r.text
        change_set_v = _change_set_set_version(
            change_set["id"],
            "system-value-maps-to-master",
            "system-value",
            "master-value",
            sv["id"],
            "outgoing",
        )
        assert change_set_v == 1


def test_change_set_relation_update_and_delete_advance_both_change_set_anchors_only():
    binding = ("system-value-maps-to-master", "system-value", "master-value")
    with TestClient(app) as client:
        sv, mv = _mapping_endpoints(client, _suffix())
        change_set = _create_change_set(client)
        created = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": binding[0],
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert created.status_code == 201, created.text
        relation = created.json()

        def versions():
            return (
                _change_set_set_version(change_set["id"], *binding, sv["id"], "outgoing"),
                _change_set_set_version(change_set["id"], *binding, mv["id"], "incoming"),
                _live_set_version(*binding, sv["id"], "outgoing"),
                _live_set_version(*binding, mv["id"], "incoming"),
            )

        assert versions() == (1, 1, 0, 0)
        updated = client.patch(
            f"/api/v1/relations/{relation['id']}",
            json={
                "attributes": {},
                "expectedVersion": relation["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": relation["changeSetVersion"],
            },
        )
        assert updated.status_code == 200, updated.text
        assert versions() == (2, 2, 0, 0)
        updated = updated.json()
        deleted = client.delete(
            f"/api/v1/relations/{relation['id']}",
            params={
                "expectedVersion": updated["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": updated["changeSetVersion"],
            },
        )
        assert deleted.status_code == 204, deleted.text
        assert versions() == (3, 3, 0, 0)


def test_change_set_and_live_set_versions_are_independent():
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
            },
        )
        assert r.status_code == 201
        live_v = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv["id"], "outgoing"
        )
        assert live_v == 1
        s2 = _suffix()
        sv2, mv2 = _mapping_endpoints(client, s2)
        change_set = _create_change_set(client)
        r2 = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv2["id"],
                "toObjectId": mv2["id"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert r2.status_code == 201, r2.text
        change_set_v = _change_set_set_version(
            change_set["id"],
            "system-value-maps-to-master",
            "system-value",
            "master-value",
            sv2["id"],
            "outgoing",
        )
        assert change_set_v == 1
        live_v_sv2 = _live_set_version(
            "system-value-maps-to-master", "system-value", "master-value", sv2["id"], "outgoing"
        )
        assert live_v_sv2 == 0


def test_change_set_discard_cascades_set_version_rows():
    with TestClient(app) as client:
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s)
        change_set = _create_change_set(client)
        client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        change_set_id = change_set["id"]
        assert _change_set_set_version_count(change_set_id) > 0
        version = _change_set_version(client, change_set_id)
        d = client.delete(
            f"/api/v1/change-sets/{change_set_id}",
            params={"expectedVersion": version},
        )
        assert d.status_code == 204, d.text
        assert _change_set_set_version_count(change_set_id) == 0


def test_change_set_activation_merges_set_versions_into_live():
    ws_key = f"rsv-activate-{_suffix()}"
    with TestClient(app) as client:
        client.post("/api/v1/workspaces", json={"key": ws_key, "label": ws_key})
        s = _suffix()
        sv, mv = _mapping_endpoints(client, s, ws=ws_key)
        change_set = client.post(
            f"/api/v1/workspaces/{ws_key}/change-sets", json={"source": "currentLive"}
        )
        assert change_set.status_code == 201, change_set.text
        change_set = change_set.json()
        r = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": sv["id"],
                "toObjectId": mv["id"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert r.status_code == 201, r.text
        change_set_id = change_set["id"]
        version = _change_set_version(client, change_set_id)
        activation = client.post(
            f"/api/v1/change-sets/{change_set_id}/publication",
            json={
                "expectedChangeSetVersion": version,
            },
        )
        assert activation.status_code == 200, activation.text
        live_v = _set_version(
            ws_key,
            None,
            "system-value-maps-to-master",
            "system-value",
            "master-value",
            sv["id"],
            "outgoing",
        )
        assert live_v >= 1
        assert _change_set_set_version_count(change_set_id) == 0
