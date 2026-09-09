"""WP8 activation = delta-merge over the live active store.

Activation no longer rebuilds the live projection from the draft's membership.  Instead the draft is
applied as a delta onto the *current* live content: records the draft authored (created / edited /
tombstoned relative to its derived-from revision) are merged onto live, and live content the draft
never touched is preserved.  The merged graph is validated whole, then snapshotted into the new
revision.  These tests exercise the divergence cases the old wholesale rebuild could not represent:

* newer live content survives a draft activation (and is included in the merged revision snapshot);
* a draft touch on a record that changed live since the base is a per-record ``version_conflict``
  and nothing is published;
* a draft tombstone applies to live while the older revision keeps the record;
* a draft removal that would dangle a newer live child fails merged whole-graph validation, leaving
  live, the active revision and the draft untouched.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from wp8_support import (
    activate_draft,
    attribute,
    create_domain,
    create_draft,
    create_workspace,
    graph_snapshot_sets,
    published_graph_snapshot,
    revision_graph_snapshot,
    unique_key,
    workspace_active_revision_id,
)

from app.db import SessionLocal
from app.main import app
from app.models.database import WorkspaceDraft


def _live_get(client, object_type_key: str, object_id: str, workspace_key: str) -> dict:
    response = client.get(
        f"/api/v1/objects/{object_type_key}/{object_id}", params={"workspaceKey": workspace_key}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _draft_version(draft_id: str) -> int:
    with SessionLocal() as session:
        version = session.scalar(
            select(WorkspaceDraft.version).where(WorkspaceDraft.id == draft_id)
        )
        assert version is not None, f"Draft '{draft_id}' not found"
        return version


def _publish_domain_revision(client, workspace_key: str, suffix: str) -> dict:
    draft = create_draft(client, workspace_key, name=f"seed {suffix}").json()
    domain = create_domain(client, draft, unique_key(suffix))
    revision = activate_draft(
        client,
        draft["id"],
        expected_draft_version=draft["version"],
    ).json()
    return {**revision, "domain": domain}


# --------------------------------------------------------------------------- merge preservation


def test_activation_delta_merge_preserves_newer_live_content_and_snapshots_merged():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-preserve")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_revision(client, workspace_key, unique_key("p1"))
        r1_id = r1["id"]
        r1_snapshot = revision_graph_snapshot(client, r1_id)
        domain_id = r1["domain"]["id"]

        # A draft derived from the active revision authors a second standalone domain.
        draft = create_draft(
            client, workspace_key, name="merge", derived_from_revision_id=r1_id
        ).json()
        draft_domain = create_domain(client, draft, unique_key("p2"))

        # While the draft is open, live content advances on the SAME workspace: a live language is
        # created that the draft (derived from r1) never saw.  The old wholesale rebuild would have
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

        r2 = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            expected_active_revision_id=r1_id,
        ).json()

        # The newer live language survives, the draft's domain is applied, and the live projection
        # is the merged graph: both standalone domains + the live language.
        assert workspace_active_revision_id(workspace_key) == r2["id"]
        assert _live_get(client, "domain", domain_id, workspace_key)["id"] == domain_id
        assert _live_get(client, "domain", draft_domain["id"], workspace_key)["id"] == (
            draft_domain["id"]
        )
        live_ids = {
            item["id"]
            for item in client.get(
                "/api/v1/objects/language",
                params={"workspaceKey": workspace_key, "pageSize": 200},
            ).json()["items"]
        }
        assert live_language.json()["id"] in live_ids

        # The new revision snapshot captures the FULL merged live content (old r1 content + the
        # draft delta + the concurrent live add), so published == new snapshot and the old revision
        # stays a strict subset of it.
        published_objects, published_relations = graph_snapshot_sets(
            published_graph_snapshot(client, workspace_key)
        )
        snapshot_objects, snapshot_relations = graph_snapshot_sets(
            revision_graph_snapshot(client, r2["id"])
        )
        assert published_objects == snapshot_objects
        assert published_relations == snapshot_relations
        r1_objects, _r1_relations = graph_snapshot_sets(
            revision_graph_snapshot(client, r1_id)
        )
        assert r1_objects < snapshot_objects
        assert revision_graph_snapshot(client, r1_id) == r1_snapshot


# --------------------------------------------------------------------------- merge conflicts


def test_activation_rejects_when_a_draft_touched_record_changed_live_since_the_base():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-conflict")
        create_workspace(client, workspace_key)
        revision = _publish_domain_revision(client, workspace_key, unique_key("c1"))
        r1_id = revision["id"]
        domain_id = revision["domain"]["id"]
        base_version = _live_get(client, "domain", domain_id, workspace_key)["version"]

        # The draft edits the base domain it was derived from (first touch COWs at the base version,
        # then bumps, so the edit claims the base version it branched from)...
        draft = create_draft(
            client, workspace_key, name="conflict", derived_from_revision_id=r1_id
        ).json()
        edited = client.patch(
            f"/api/v1/objects/domain/{domain_id}",
            json={
                "name": "Draft rename",
                "expectedVersion": base_version,
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
            },
        )
        assert edited.status_code == 200, edited.text
        draft["version"] = edited.json()["workspaceDraftVersion"]

        # ...and concurrently the live record is edited too (claiming the live version), so live
        # advances past the base-revision version the draft branched from.
        live_edit = client.patch(
            f"/api/v1/objects/domain/{domain_id}",
            json={"name": "Live rename", "expectedVersion": base_version},
        )
        assert live_edit.status_code == 200, live_edit.text

        activation = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            expected_active_revision_id=r1_id,
            expected_status=409,
        )
        error = activation.json()["error"]
        assert error["code"] == "version_conflict"
        conflicts = error["details"]["conflicts"]
        assert any(
            conflict["kind"] == "object"
            and conflict["id"] == domain_id
            and conflict["code"] == "version_mismatch"
            and conflict["expectedVersion"] == base_version
            and conflict["actualVersion"] == base_version + 1
            for conflict in conflicts
        )

        # Nothing was published: live keeps the concurrent edit, the active revision is unchanged,
        # no revision was minted, and the draft still exists with its own edit intact.
        assert _live_get(client, "domain", domain_id, workspace_key)["name"] == "Live rename"
        assert workspace_active_revision_id(workspace_key) == r1_id
        history = client.get(f"/api/v1/workspaces/{workspace_key}/revisions")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["items"]] == [r1_id]
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").status_code == 200
        draft_read = client.get(
            f"/api/v1/objects/domain/{domain_id}",
            params={"workspaceDraftId": draft["id"]},
        )
        assert draft_read.status_code == 200, draft_read.text
        assert draft_read.json()["name"] == "Draft rename"


# --------------------------------------------------------------------------- tombstones


def test_activation_applies_a_draft_tombstone_to_live_and_keeps_the_older_revision():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-tombstone")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_revision(client, workspace_key, unique_key("t1"))
        r1_id = r1["id"]
        domain_id = r1["domain"]["id"]
        assert domain_id in {
            item["id"]
            for item in client.get(
                "/api/v1/objects/domain", params={"workspaceKey": workspace_key}
            ).json()["items"]
        }

        # Delete the base domain inside a draft derived from it (no draft children -> no dependants).
        draft = create_draft(
            client, workspace_key, name="tombstone", derived_from_revision_id=r1_id
        ).json()
        deleted = client.delete(
            f"/api/v1/objects/domain/{domain_id}",
            params={
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
                "expectedVersion": 1,
            },
        )
        assert deleted.status_code == 204, deleted.text

        r2 = activate_draft(
            client,
            draft["id"],
            expected_draft_version=_draft_version(draft["id"]),
            expected_active_revision_id=r1_id,
        ).json()

        # The tombstone applies to live: the domain is gone from the active projection, and the new
        # revision snapshot is empty, while the retired r1 snapshot still carries the record.
        assert workspace_active_revision_id(workspace_key) == r2["id"]
        gone = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"workspaceKey": workspace_key}
        )
        assert gone.status_code == 404
        objects, relations = graph_snapshot_sets(revision_graph_snapshot(client, r2["id"]))
        assert objects == set()
        assert relations == set()
        r1_objects, _r1_relations = graph_snapshot_sets(revision_graph_snapshot(client, r1_id))
        assert any(entry[1] == domain_id for entry in r1_objects)


def test_activation_refuses_when_removal_would_dangle_a_newer_live_child():
    with TestClient(app) as client:
        workspace_key = unique_key("merge-dangle")
        create_workspace(client, workspace_key)
        r1 = _publish_domain_revision(client, workspace_key, unique_key("d1"))
        r1_id = r1["id"]
        domain_id = r1["domain"]["id"]

        # Live adds a codelist contained under the published domain AFTER the draft's base revision.
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

        # The draft (which only knows the base revision) tombstones the domain.
        draft = create_draft(
            client, workspace_key, name="dangle", derived_from_revision_id=r1_id
        ).json()
        deleted = client.delete(
            f"/api/v1/objects/domain/{domain_id}",
            params={
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
                "expectedVersion": 1,
            },
        )
        assert deleted.status_code == 204, deleted.text

        # Activation re-validates the merged graph and must refuse: the draft cannot silently orphan
        # the newer live child whose containment parent it just removed.
        activation = activate_draft(
            client,
            draft["id"],
            expected_draft_version=_draft_version(draft["id"]),
            expected_active_revision_id=r1_id,
            expected_status=422,
        )
        assert activation.json()["error"]["code"] == "workspace_graph_invalid"

        # Live, the active revision and the draft are all preserved.
        assert _live_get(client, "domain", domain_id, workspace_key)["id"] == domain_id
        assert _live_get(client, "codelist", child_id, workspace_key)["id"] == child_id
        assert workspace_active_revision_id(workspace_key) == r1_id
        history = client.get(f"/api/v1/workspaces/{workspace_key}/revisions")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["items"]] == [r1_id]
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").status_code == 200
