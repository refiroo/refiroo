"""WP8 activation = delta-merge over the live active store.

Activation no longer rebuilds the live projection from the change set's membership.  Instead the change set is
applied as a delta onto the *current* live content: records the change set authored (created / edited /
tombstoned relative to its derived-from publication) are merged onto live, and live content the change set
never touched is preserved.  The merged graph is validated whole, then snapshotted into the new
publication.  These tests exercise the divergence cases the old wholesale rebuild could not represent:

* newer live content survives a change set activation (and is included in the merged publication snapshot);
* a change set touch on a record that changed live since the base is a per-record ``VERSION_CONFLICT``
  and nothing is published;
* a change set tombstone applies to live while the older publication keeps the record;
* a change set removal that would dangle a newer live child fails merged whole-graph validation, leaving
  live, the active publication and the change set untouched.
"""

from uuid import uuid4

from harness_identity import TestClient
from sqlalchemy import select
from wp8_support import (
    attribute,
    create_change_set,
    create_domain,
    create_workspace,
    graph_snapshot_sets,
    publication_graph_snapshot,
    publish_change_set,
    published_graph_snapshot,
    unique_key,
    workspace_active_publication_id,
)

from app.db import SessionLocal
from app.main import app
from app.models.database import ChangeSet


def _live_get(client, object_type_key: str, object_id: str, workspace_key: str) -> dict:
    response = client.get(
        f"/api/v1/objects/{object_type_key}/{object_id}", params={"workspaceKey": workspace_key}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _change_set_version(change_set_id: str) -> int:
    with SessionLocal() as session:
        version = session.scalar(select(ChangeSet.version).where(ChangeSet.id == change_set_id))
        assert version is not None, f"Change set '{change_set_id}' not found"
        return version


def _publish_domain_publication(client, workspace_key: str, suffix: str) -> dict:
    change_set = create_change_set(client, workspace_key, name=f"seed {suffix}").json()
    domain = create_domain(client, change_set, unique_key(suffix))
    publication = publish_change_set(
        client,
        change_set["id"],
        expected_change_set_version=change_set["version"],
    ).json()
    return {**publication, "domain": domain}


# --------------------------------------------------------------------------- merge preservation


def test_publish_delta_merge_preserves_newer_live_content_and_snapshots_merged():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-preserve")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_publication(client, workspace_key, unique_key("p1"))
        r1_id = r1["id"]
        r1_snapshot = publication_graph_snapshot(client, r1_id)
        domain_id = r1["domain"]["id"]

        # A change set derived from the active publication authors a second standalone domain.
        change_set = create_change_set(
            client, workspace_key, name="merge", derived_from_publication_id=r1_id
        ).json()
        change_set_domain = create_domain(client, change_set, unique_key("p2"))

        # While the change set is open, live content advances on the SAME workspace: a live language is
        # created that the change set (derived from r1) never saw.  The old wholesale rebuild would have
        # wiped it on activation; the delta-merge must preserve it.
        live_language = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace_key,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": f"Live {unique_key('L')}",
                "attributes": [attribute("language-code", f"lang-{uuid4().hex[:8]}")],
            },
        )
        assert live_language.status_code == 201, live_language.text

        r2 = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_active_publication_id=r1_id,
        ).json()

        # The newer live language survives, the change set's domain is applied, and the live projection
        # is the merged graph: both standalone domains + the live language.
        assert workspace_active_publication_id(workspace_key) == r2["id"]
        assert _live_get(client, "domain", domain_id, workspace_key)["id"] == domain_id
        assert (
            _live_get(client, "domain", change_set_domain["id"], workspace_key)["id"]
            == (change_set_domain["id"])
        )
        live_ids = {
            item["id"]
            for item in client.get(
                "/api/v1/objects/language",
                params={"workspaceKey": workspace_key, "pageSize": 200},
            ).json()["items"]
        }
        assert live_language.json()["id"] in live_ids

        # The new publication snapshot captures the FULL merged live content (old r1 content + the
        # change set delta + the concurrent live add), so published == new snapshot and the old publication
        # stays a strict subset of it.
        published_objects, published_relations = graph_snapshot_sets(
            published_graph_snapshot(client, workspace_key)
        )
        snapshot_objects, snapshot_relations = graph_snapshot_sets(
            publication_graph_snapshot(client, r2["id"])
        )
        assert published_objects == snapshot_objects
        assert published_relations == snapshot_relations
        r1_objects, _r1_relations = graph_snapshot_sets(publication_graph_snapshot(client, r1_id))
        assert r1_objects < snapshot_objects
        assert publication_graph_snapshot(client, r1_id) == r1_snapshot


# --------------------------------------------------------------------------- merge conflicts


def test_publish_rejects_when_a_change_set_touched_record_changed_live_since_the_base():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-conflict")
        create_workspace(client, workspace_key)
        publication = _publish_domain_publication(client, workspace_key, unique_key("c1"))
        r1_id = publication["id"]
        domain_id = publication["domain"]["id"]
        base_version = _live_get(client, "domain", domain_id, workspace_key)["version"]

        # The change set edits the base domain it was derived from (first touch COWs at the base version,
        # then bumps, so the edit claims the base version it branched from)...
        change_set = create_change_set(
            client, workspace_key, name="conflict", derived_from_publication_id=r1_id
        ).json()
        edited = client.patch(
            f"/api/v1/objects/domain/{domain_id}",
            json={
                "name": "Change set rename",
                "expectedVersion": base_version,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert edited.status_code == 200, edited.text
        change_set["version"] = edited.json()["changeSetVersion"]

        # ...and concurrently the live record is edited too (claiming the live version), so live
        # advances past the base-publication version the change set branched from.
        live_edit = client.patch(
            f"/api/v1/objects/domain/{domain_id}",
            json={"name": "Live rename", "expectedVersion": base_version},
        )
        assert live_edit.status_code == 200, live_edit.text

        activation = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_active_publication_id=r1_id,
            expected_status=409,
        )
        error = activation.json()["error"]
        assert error["code"] == "VERSION_CONFLICT"
        conflicts = error["details"]["conflicts"]
        assert any(
            conflict["kind"] == "object"
            and conflict["id"] == domain_id
            and conflict["code"] == "VERSION_MISMATCH"
            and conflict["expectedVersion"] == base_version
            and conflict["actualVersion"] == base_version + 1
            for conflict in conflicts
        )

        # Nothing was published: live keeps the concurrent edit, the active publication is unchanged,
        # no publication was minted, and the change set still exists with its own edit intact.
        assert _live_get(client, "domain", domain_id, workspace_key)["name"] == "Live rename"
        assert workspace_active_publication_id(workspace_key) == r1_id
        history = client.get(f"/api/v1/workspaces/{workspace_key}/publications")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["items"]] == [r1_id]
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 200
        change_set_read = client.get(
            f"/api/v1/objects/domain/{domain_id}",
            params={"changeSetId": change_set["id"]},
        )
        assert change_set_read.status_code == 200, change_set_read.text
        assert change_set_read.json()["name"] == "Change set rename"


# --------------------------------------------------------------------------- tombstones


def test_publish_applies_a_change_set_tombstone_to_live_and_keeps_the_older_publication():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-tombstone")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_publication(client, workspace_key, unique_key("t1"))
        r1_id = r1["id"]
        domain_id = r1["domain"]["id"]
        assert domain_id in {
            item["id"]
            for item in client.get(
                "/api/v1/objects/domain", params={"workspaceKey": workspace_key}
            ).json()["items"]
        }

        # Delete the base domain inside a change set derived from it (no change set children -> no dependants).
        change_set = create_change_set(
            client, workspace_key, name="tombstone", derived_from_publication_id=r1_id
        ).json()
        deleted = client.delete(
            f"/api/v1/objects/domain/{domain_id}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
                "expectedVersion": 1,
            },
        )
        assert deleted.status_code == 204, deleted.text

        r2 = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=_change_set_version(change_set["id"]),
            expected_active_publication_id=r1_id,
        ).json()

        # The tombstone applies to live: the domain is gone from the active projection, and the new
        # publication snapshot is empty, while the retired r1 snapshot still carries the record.
        assert workspace_active_publication_id(workspace_key) == r2["id"]
        gone = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"workspaceKey": workspace_key}
        )
        assert gone.status_code == 404
        objects, relations = graph_snapshot_sets(publication_graph_snapshot(client, r2["id"]))
        assert objects == set()
        assert relations == set()
        r1_objects, _r1_relations = graph_snapshot_sets(publication_graph_snapshot(client, r1_id))
        assert any(entry[1] == domain_id for entry in r1_objects)


def test_publish_refuses_when_removal_would_dangle_a_newer_live_child():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-dangle")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_publication(client, workspace_key, unique_key("d1"))
        r1_id = r1["id"]
        domain_id = r1["domain"]["id"]

        # Live adds a codelist contained under the published domain AFTER the change set's base publication.
        child = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace_key,
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "name": f"Codelist {unique_key('child')}",
                "parentObjectId": domain_id,
                "attributes": [attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
            },
        )
        assert child.status_code == 201, child.text
        child_id = child.json()["id"]

        # The change set (which only knows the base publication) tombstones the domain.
        change_set = create_change_set(
            client, workspace_key, name="dangle", derived_from_publication_id=r1_id
        ).json()
        deleted = client.delete(
            f"/api/v1/objects/domain/{domain_id}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
                "expectedVersion": 1,
            },
        )
        assert deleted.status_code == 204, deleted.text

        # Activation re-validates the merged graph and must refuse: the change set cannot silently orphan
        # the newer live child whose containment parent it just removed.
        activation = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=_change_set_version(change_set["id"]),
            expected_active_publication_id=r1_id,
            expected_status=422,
        )
        assert activation.json()["error"]["code"] == "WORKSPACE_GRAPH_INVALID"

        # Live, the active publication and the change set are all preserved.
        assert _live_get(client, "domain", domain_id, workspace_key)["id"] == domain_id
        assert _live_get(client, "codelist", child_id, workspace_key)["id"] == child_id
        assert workspace_active_publication_id(workspace_key) == r1_id
        history = client.get(f"/api/v1/workspaces/{workspace_key}/publications")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["items"]] == [r1_id]
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 200
