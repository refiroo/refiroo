"""WP8 package-4 tests: immutable workspace history reads and cursor binding.

This package adds no lifecycle routes.  It verifies that the read endpoints committed by the earlier
workspace-authority packages (workspace revision LIST/DETAIL plus the generic object/relation routers
bound by ``workspaceRevisionId``) satisfy the immutable-history contract:

* workspace revision list is cursor-paginated, bounded, and scoped to the workspace identity;
* revision metadata exposes ``derivedFromRevisionId`` and ``supersedesRevisionId`` as separate fields
  and a branch activated from an older revision keeps them distinct;
* historical object/relation reads reuse the same generic record representations as active and draft
  reads, and revision snapshots stay immutable across later activations and across live writes;
* writes without a ``workspaceDraftId`` target the LIVE active store directly (no release, no
  revision minted); revision snapshots are read-only history and are never mutated by live writes.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from wp8_support import (
    activate_draft,
    attribute,
    build_complete_graph,
    create_domain,
    create_draft,
    create_object,
    create_workspace,
    draft_graph_snapshot,
    graph_snapshot_sets,
    publish_language_revision,
    published_graph_snapshot,
    revision_graph_snapshot,
    revision_status,
    unique_key,
    workspace_active_revision_id,
)

from app.db import SessionLocal
from app.main import app
from app.models.database import WorkspaceRevisionObject


def _canonical_object(item: dict) -> dict:
    # ``path`` is intentionally excluded: the draft/revision detail builders return an empty path
    # (they only populate it on create/update responses) while the active projection read populates
    # the full ancestor chain.  The shared generic builders emit every other field identically.
    return {
        "id": item["id"],
        "workspaceKey": item["workspaceKey"],
        "applicationKey": item["applicationKey"],
        "objectTypeKey": item["objectTypeKey"],
        "parentObjectId": item["parentObjectId"],
        "name": item["name"],
        "version": item["version"],
        "attributes": sorted((a["attributeTypeKey"], a["value"]) for a in item["attributes"]),
    }


def _canonical_relation(item: dict) -> dict:
    return {
        "id": item["id"],
        "relationTypeKey": item["relationTypeKey"],
        "fromObjectId": item["fromObjectId"],
        "toObjectId": item["toObjectId"],
        "version": item["version"],
        "attributes": sorted((k, v) for k, v in (item["attributes"] or {}).items()),
    }


def _revision_object_ids(revision_id: str) -> list[str]:
    with SessionLocal() as session:
        return sorted(
            session.scalars(
                select(WorkspaceRevisionObject.object_id).where(
                    WorkspaceRevisionObject.revision_id == revision_id
                )
            )
        )


def _publish_language_revision(client, workspace_key: str, suffix: str) -> dict:
    """Publish one language-only revision, superseding whatever is active in the workspace."""
    active_id = workspace_active_revision_id(workspace_key)
    return publish_language_revision(
        client,
        workspace_key,
        suffix,
        expected_active_revision_id=active_id,
    )


# --------------------------------------------------------------------------- branching lineage


def test_branch_derived_from_older_history_has_distinct_derived_from_and_supersedes():
    with TestClient(app) as client:
        workspace_key = unique_key("branch-lineage")
        create_workspace(client, workspace_key)

        # R1: language-only root revision.
        r1 = _publish_language_revision(client, workspace_key, unique_key("r1"))
        assert r1["derivedFromRevisionId"] is None
        assert r1["supersedesRevisionId"] is None
        assert r1["status"] == "active"

        # R2 is derived from R1 and adds a domain, so R1 retires in the same transaction.
        draft2 = create_draft(
            client, workspace_key, name="r2", derived_from_revision_id=r1["id"]
        ).json()
        domain_a = create_domain(client, draft2, unique_key("branchA"))
        r2 = activate_draft(
            client,
            draft2["id"],
            expected_draft_version=draft2["version"],
            expected_active_revision_id=r1["id"],
        ).json()
        assert r2["derivedFromRevisionId"] == r1["id"]
        assert r2["supersedesRevisionId"] == r1["id"]
        assert revision_status(r1["id"]) == "retired"
        assert revision_status(r2["id"]) == "active"

        # R3 is derived from R2 and adds a codelist beneath the domain carried from R2.
        draft3 = create_draft(
            client, workspace_key, name="r3", derived_from_revision_id=r2["id"]
        ).json()
        create_object(
            client,
            draft3,
            "rdm-master",
            "codelist",
            f"Codelist {unique_key('branchC')}",
            attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
            parent_object_id=domain_a["id"],
        )
        r3 = activate_draft(
            client,
            draft3["id"],
            expected_draft_version=draft3["version"],
            expected_active_revision_id=r2["id"],
        ).json()
        assert r3["derivedFromRevisionId"] == r2["id"]
        assert r3["supersedesRevisionId"] == r2["id"]
        assert revision_status(r2["id"]) == "retired"
        assert revision_status(r3["id"]) == "active"

        # The branch draft derives from the OLD retired R1, not from the active R3, then activates.
        branch = create_draft(
            client, workspace_key, name="branch", derived_from_revision_id=r1["id"]
        ).json()
        domain_b = create_domain(client, branch, unique_key("branchB"))
        r4 = activate_draft(
            client,
            branch["id"],
            expected_draft_version=branch["version"],
            expected_active_revision_id=r3["id"],
        ).json()
        assert r4["revisionNumber"] == 4
        # derivedFrom points at the older revision the branch was derived from while supersedes
        # points at the revision that was active at activation time -- a genuine branch, so distinct.
        assert r4["derivedFromRevisionId"] == r1["id"]
        assert r4["supersedesRevisionId"] == r3["id"]
        assert r4["derivedFromRevisionId"] != r4["supersedesRevisionId"]
        assert r4["status"] == "active"
        assert revision_status(r3["id"]) == "retired"
        assert workspace_active_revision_id(workspace_key) == r4["id"]

        # Inspect the relevant revision details: both lineage fields are separate and correct.
        r1_detail = client.get(f"/api/v1/workspace-revisions/{r1['id']}").json()
        r4_detail = client.get(f"/api/v1/workspace-revisions/{r4['id']}").json()
        assert r1_detail["derivedFromRevisionId"] is None
        assert r1_detail["supersedesRevisionId"] is None
        assert r4_detail["derivedFromRevisionId"] == r1["id"]
        assert r4_detail["supersedesRevisionId"] == r3["id"]
        assert "derivedFromRevisionId" in r4_detail and "supersedesRevisionId" in r4_detail

        # The branch graph is published: the branch domain is visible and the retired R3 graph is no
        # longer the active projection (only the carried-forward language plus the branch domain).
        published_domain = client.get(
            f"/api/v1/objects/domain/{domain_b['id']}", params={"workspaceKey": workspace_key}
        )
        assert published_domain.status_code == 200
        assert published_domain.json()["name"] == domain_b["name"]
        objects, _relations = graph_snapshot_sets(published_graph_snapshot(client, workspace_key))
        assert (r1["language"]["objectTypeKey"], r1["language"]["id"]) in {
            (item[0], item[1]) for item in objects
        }


# --------------------------------------------------------------------------- revision list pagination


def test_revision_list_cursor_pagination_is_bounded_and_scoped_to_workspace():
    with TestClient(app) as client:
        workspace_key = unique_key("revision-page")
        create_workspace(client, workspace_key)
        revision_ids: list[str] = []
        for index in range(4):
            revision = _publish_language_revision(
                client, workspace_key, unique_key(f"page-{index}")
            )
            revision_ids.append(revision["id"])

        first_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/revisions", params={"pageSize": 2}
        )
        assert first_page.status_code == 200
        body = first_page.json()
        assert len(body["items"]) == 2
        cursor = body["nextCursor"]
        assert cursor is not None

        second_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/revisions",
            params={"pageSize": 2, "cursor": cursor},
        )
        assert second_page.status_code == 200
        body2 = second_page.json()
        assert len(body2["items"]) == 2
        assert body2["nextCursor"] is None

        combined = body["items"] + body2["items"]
        assert {item["id"] for item in combined} == set(revision_ids)
        numbers = [item["revisionNumber"] for item in combined]
        assert numbers == sorted(numbers)
        # Every page item carries the full revision metadata including the separate lineage fields.
        for item in combined:
            assert "derivedFromRevisionId" in item and "supersedesRevisionId" in item
            assert item["workspaceKey"] == workspace_key

        # The list is bound to the workspace: a cursor minted for one workspace cannot page another.
        other_key = unique_key("revision-other")
        create_workspace(client, other_key)
        _publish_language_revision(client, other_key, unique_key("other"))
        mismatched = client.get(
            f"/api/v1/workspaces/{other_key}/revisions",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "invalid_cursor"


# --------------------------------------------------------------------------- snapshot parity


def test_revision_snapshot_parity_across_active_and_draft_read_contexts():
    with TestClient(app) as client:
        workspace_key = unique_key("snapshot-parity")
        create_workspace(client, workspace_key)
        draft, graph = build_complete_graph(client, workspace_key, unique_key("parity"))
        revision = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()
        revision_id = revision["id"]

        # An untouched draft derived from the revision makes the same content reachable through the
        # mutable draft read context.
        derived = create_draft(
            client, workspace_key, name="parity-derived", derived_from_revision_id=revision_id
        ).json()

        published = published_graph_snapshot(client, workspace_key)
        historical = revision_graph_snapshot(client, revision_id)
        draft_snapshot = draft_graph_snapshot(client, derived["id"])
        # The object/relation snapshot read through the revision context matches both the active
        # projection (this revision is active) and the derived draft's effective membership.
        assert graph_snapshot_sets(historical) == graph_snapshot_sets(published)
        assert graph_snapshot_sets(draft_snapshot) == graph_snapshot_sets(published)

        # The generic record representation is identical across the three read contexts for the same
        # record (structural fields only -- the draft/revision builders emit request-time timestamps).
        domain_id = graph["domain"]["id"]
        active_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"workspaceKey": workspace_key}
        ).json()
        revision_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}",
            params={"workspaceRevisionId": revision_id},
        ).json()
        draft_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"workspaceDraftId": derived["id"]}
        ).json()
        assert _canonical_object(active_detail) == _canonical_object(revision_detail)
        assert _canonical_object(draft_detail) == _canonical_object(revision_detail)

        # A relation present in the graph reads with the same generic RelationResponse from every
        # context.  The active projection's per-anchor feed is the generic active relation read path;
        # the revision and draft feeds are the generic revision/draft relation read paths.
        def relation_for_anchor(context_params: dict, relation_type_key: str) -> dict:
            items = client.get(
                "/api/v1/relations", params={"objectId": domain_id, **context_params}
            ).json()["items"]
            match = next(
                item for item in items if item["relation"]["relationTypeKey"] == relation_type_key
            )
            return _canonical_relation(match["relation"])

        active_relation = relation_for_anchor({"workspaceKey": workspace_key}, "object-has-translation")
        revision_relation = relation_for_anchor(
            {"workspaceRevisionId": revision_id}, "object-has-translation"
        )
        draft_relation = relation_for_anchor({"workspaceDraftId": derived["id"]}, "object-has-translation")
        assert revision_relation == active_relation
        assert draft_relation == active_relation


# --------------------------------------------------------------------------- live writes on the active workspace


def test_active_live_writes_apply_without_a_draft_and_leave_revision_snapshots_frozen():
    with TestClient(app) as client:
        workspace_key = unique_key("active-live")
        create_workspace(client, workspace_key)
        revision = _publish_language_revision(client, workspace_key, unique_key("live"))
        language = revision["language"]
        language_id = language["id"]
        revision_id = revision["id"]
        before_revision_snapshot = revision_graph_snapshot(client, revision_id)

        def live_get(object_id: str) -> dict:
            response = client.get(
                f"/api/v1/objects/language/{object_id}", params={"workspaceKey": workspace_key}
            )
            assert response.status_code == 200, response.text
            return response.json()

        # A create without workspaceDraftId targets the live active store directly: it needs no
        # draft claim and is immediately part of the active projection.
        created = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace_key,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": f"Live {unique_key('L')}",
                "attributes": [attribute("language-code", f"lang-{uuid4().hex[:8]}")],
            },
        )
        assert created.status_code == 201, created.text
        live_created = created.json()
        assert live_created["id"] != language_id
        assert live_created["workspaceDraftVersion"] is None
        assert live_get(live_created["id"])["name"] == live_created["name"]
        listed = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 200},
        )
        assert listed.status_code == 200, listed.text
        assert {item["id"] for item in listed.json()["items"]} == {language_id, live_created["id"]}

        # An update claims the live object's optimistic-concurrency version and bumps it.
        before_version = live_get(language_id)["version"]
        renamed = client.patch(
            f"/api/v1/objects/language/{language_id}",
            json={"name": "Mutated live", "expectedVersion": before_version},
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Mutated live"
        assert renamed.json()["version"] == before_version + 1
        assert live_get(language_id)["name"] == "Mutated live"

        # A stale version claim is rejected with the live optimistic-concurrency code.
        stale = client.patch(
            f"/api/v1/objects/language/{language_id}",
            json={"name": "Racing write", "expectedVersion": before_version},
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["error"]["code"] == "version_conflict"

        # A single attribute value is mutable live under the object version.
        current_version = live_get(language_id)["version"]
        new_code = f"lang-{uuid4().hex[:8]}"
        attr = client.patch(
            f"/api/v1/objects/language/{language_id}/attributes/language-code",
            json={"value": new_code, "expectedVersion": current_version},
        )
        assert attr.status_code == 200, attr.text
        assert attr.json()["version"] == current_version + 1
        attributes = {a["attributeTypeKey"]: a["value"] for a in live_get(language_id)["attributes"]}
        assert attributes["language-code"] == new_code

        # A live delete (no dependants here) physically removes the row from the active projection.
        gone = client.delete(
            f"/api/v1/objects/language/{live_created['id']}", params={"expectedVersion": 1}
        )
        assert gone.status_code == 204, gone.text
        assert (
            client.get(
                f"/api/v1/objects/language/{live_created['id']}",
                params={"workspaceKey": workspace_key},
            ).status_code
            == 404
        )

        # None of the live writes minted a revision or touched the immutable snapshot, and the
        # workspace is still active on the same revision.
        assert revision_graph_snapshot(client, revision_id) == before_revision_snapshot
        assert workspace_active_revision_id(workspace_key) == revision_id
        assert revision_status(revision_id) == "active"
        revisions = client.get(f"/api/v1/workspaces/{workspace_key}/revisions")
        assert revisions.status_code == 200
        assert len(revisions.json()["items"]) == 1


# --------------------------------------------------------------------------- immutable historical context


def _build_three_revision_history(client, workspace_key: str) -> tuple[dict, dict, dict, dict]:
    """Return ``(r0, r1, r2, domain_a)`` where r0 and r1 are retired and r2 is active.

    r0 is a language-only root.  r1 is derived from r0 and adds a domain plus a codelist under it, so
    r1's snapshot contains one ``domain-contains-codelist`` relation.  r2 is derived from r1 and adds
    a second domain.
    """
    r0 = _publish_language_revision(client, workspace_key, unique_key("h0"))
    draft1 = create_draft(
        client, workspace_key, name="h1", derived_from_revision_id=r0["id"]
    ).json()
    domain_a = create_domain(client, draft1, unique_key("histA"))
    create_object(
        client,
        draft1,
        "rdm-master",
        "codelist",
        f"Codelist {unique_key('histA')}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain_a["id"],
    )
    r1 = activate_draft(
        client,
        draft1["id"],
        expected_draft_version=draft1["version"],
        expected_active_revision_id=r0["id"],
    ).json()
    draft2 = create_draft(
        client, workspace_key, name="h2", derived_from_revision_id=r1["id"]
    ).json()
    create_domain(client, draft2, unique_key("histB"))
    r2 = activate_draft(
        client,
        draft2["id"],
        expected_draft_version=draft2["version"],
        expected_active_revision_id=r1["id"],
    ).json()
    assert revision_status(r0["id"]) == "retired"
    assert revision_status(r1["id"]) == "retired"
    assert revision_status(r2["id"]) == "active"
    return r0, r1, r2, domain_a


def test_historical_revision_reads_stay_immutable_while_live_writes_write_through():
    with TestClient(app) as client:
        workspace_key = unique_key("history-immutable")
        create_workspace(client, workspace_key)
        r0, r1, r2, domain_a = _build_three_revision_history(client, workspace_key)
        language = r0["language"]

        # Both the older retained revision (r0) and the recently retired revision (r1) stay readable.
        for revision_id in (r0["id"], r1["id"]):
            detail = client.get(f"/api/v1/workspace-revisions/{revision_id}")
            assert detail.status_code == 200
            assert detail.json()["status"] == "retired"
            objects, _relations = graph_snapshot_sets(revision_graph_snapshot(client, revision_id))
            assert objects  # each retired revision still serves its immutable object snapshot

        # The retired revision r1 carries the rows it shares with the still-active r2 plus its own
        # immutable snapshot: its object/relation content is a strict subset of r2's content because
        # r2 was derived from r1 and only added another domain.
        r1_objects, r1_relations = graph_snapshot_sets(revision_graph_snapshot(client, r1["id"]))
        r2_objects, r2_relations = graph_snapshot_sets(revision_graph_snapshot(client, r2["id"]))
        assert r1_objects < r2_objects
        assert r1_relations == r2_relations
        assert any(relation[1] == "domain-contains-codelist" for relation in r1_relations)
        r1_relations_http = client.get(
            "/api/v1/relations",
            params={"objectId": domain_a["id"], "workspaceRevisionId": r1["id"]},
        )
        assert r1_relations_http.status_code == 200
        assert any(
            item["relation"]["relationTypeKey"] == "domain-contains-codelist"
            for item in r1_relations_http.json()["items"]
        )

        # The full revision history is listed for the workspace including every retired revision.
        history = client.get(f"/api/v1/workspaces/{workspace_key}/revisions", params={"pageSize": 10})
        assert history.status_code == 200
        assert {item["id"] for item in history.json()["items"]} == {r0["id"], r1["id"], r2["id"]}

        # A write without workspaceDraftId lands on the LIVE active store even when the caller passes
        # a workspaceRevisionId query parameter (write endpoints ignore it): history cannot be
        # mutated, it is simply bypassed.  Snapshot the retired r1 membership, the active r2 snapshot
        # and the published projection before the live writes.
        before_published = published_graph_snapshot(client, workspace_key)
        before_snapshot = revision_graph_snapshot(client, r1["id"])
        before_object_ids = _revision_object_ids(r1["id"])
        r2_before = revision_graph_snapshot(client, r2["id"])
        live_before = client.get(
            f"/api/v1/objects/language/{language['id']}",
            params={"workspaceKey": workspace_key},
        )
        assert live_before.status_code == 200, live_before.text
        old_live_name = live_before.json()["name"]

        # The live language row is updated in place...
        renamed = client.patch(
            f"/api/v1/objects/language/{language['id']}",
            params={"workspaceRevisionId": r1["id"]},
            json={"name": "Renamed live", "expectedVersion": live_before.json()["version"]},
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Renamed live"
        assert (
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"workspaceKey": workspace_key},
            ).json()["name"]
            == "Renamed live"
        )

        # ...and a create without a draft is immediately part of the live active projection.
        created = client.post(
            "/api/v1/objects",
            params={"workspaceRevisionId": r1["id"]},
            json={
                "workspaceKey": workspace_key,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Live domain",
                "attributes": [attribute("domain-code", f"dom-{uuid4().hex[:8]}")],
            },
        )
        assert created.status_code == 201, created.text
        assert (
            client.get(
                f"/api/v1/objects/domain/{created.json()['id']}",
                params={"workspaceKey": workspace_key},
            ).status_code
            == 200
        )

        # Every immutable revision snapshot stays byte-identical: the retired r1 object/relation
        # membership and the active r2 snapshot are untouched by the live writes, while the live
        # projection changed.  The retired r1 historical read still serves the pre-rename language.
        assert revision_graph_snapshot(client, r1["id"]) == before_snapshot
        assert _revision_object_ids(r1["id"]) == before_object_ids
        assert revision_graph_snapshot(client, r2["id"]) == r2_before
        assert published_graph_snapshot(client, workspace_key) != before_published
        assert (
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"workspaceRevisionId": r1["id"]},
            ).json()["name"]
            == old_live_name
        )


# --------------------------------------------------------------------------- snapshot immutability


def test_historical_snapshot_reads_are_immutable_across_later_activations():
    with TestClient(app) as client:
        workspace_key = unique_key("snapshot-immutable")
        create_workspace(client, workspace_key)
        r0 = _publish_language_revision(client, workspace_key, unique_key("i0"))
        language = r0["language"]

        def capture(revision_id: str) -> str:
            return revision_graph_snapshot(client, revision_id)

        r0_before = capture(r0["id"])
        r0_detail_before = _canonical_object(
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"workspaceRevisionId": r0["id"]},
            ).json()
        )

        # r1 supersedes and retires r0; the older snapshot must not change.
        draft1 = create_draft(
            client, workspace_key, name="i1", derived_from_revision_id=r0["id"]
        ).json()
        create_domain(client, draft1, unique_key("i1"))
        r1 = activate_draft(
            client,
            draft1["id"],
            expected_draft_version=draft1["version"],
            expected_active_revision_id=r0["id"],
        ).json()
        assert revision_status(r0["id"]) == "retired"
        assert capture(r0["id"]) == r0_before
        r1_before = capture(r1["id"])

        # r2 supersedes and retires r1; both older snapshots remain byte-identical.
        draft2 = create_draft(
            client, workspace_key, name="i2", derived_from_revision_id=r1["id"]
        ).json()
        create_domain(client, draft2, unique_key("i2"))
        r2 = activate_draft(
            client,
            draft2["id"],
            expected_draft_version=draft2["version"],
            expected_active_revision_id=r1["id"],
        ).json()
        assert revision_status(r1["id"]) == "retired"
        assert revision_status(r2["id"]) == "active"
        assert capture(r0["id"]) == r0_before
        assert capture(r1["id"]) == r1_before

        # A second read of the same immutable revision returns identical content.
        assert capture(r0["id"]) == capture(r0["id"])
        r0_detail_after = _canonical_object(
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"workspaceRevisionId": r0["id"]},
            ).json()
        )
        assert r0_detail_after == r0_detail_before
