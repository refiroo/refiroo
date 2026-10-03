"""WP8 package-4 tests: immutable workspace history reads and cursor binding.

This package adds no lifecycle routes.  It verifies that the read endpoints committed by the earlier
workspace-authority packages (publication LIST/DETAIL plus the generic object/relation routers
bound by ``publicationId``) satisfy the immutable-history contract:

* publication list is cursor-paginated, bounded, and scoped to the workspace identity;
* publication metadata exposes ``derivedFromPublicationId`` and ``supersedesPublicationId`` as separate fields
  and a branch activated from an older publication keeps them distinct;
* historical object/relation reads reuse the same generic record representations as active and change set
  reads, and publication snapshots stay immutable across later activations and across live writes;
* writes without a ``changeSetId`` target the LIVE active store directly (no release, no
  publication minted); publication snapshots are read-only history and are never mutated by live writes.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from wp8_support import (
    attribute,
    build_complete_graph,
    change_set_graph_snapshot,
    create_change_set,
    create_domain,
    create_object,
    create_workspace,
    graph_snapshot_sets,
    publication_graph_snapshot,
    publication_status,
    publish_change_set,
    publish_language_publication,
    published_graph_snapshot,
    unique_key,
    workspace_active_publication_id,
)

from app.common.cursors import encode_cursor
from app.db import SessionLocal
from app.main import app
from app.models.database import PublicationObject


def _canonical_object(item: dict) -> dict:
    # ``path`` is intentionally excluded: the change set/publication detail builders return an empty path
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


def _publication_object_ids(publication_id: str) -> list[str]:
    with SessionLocal() as session:
        return sorted(
            session.scalars(
                select(PublicationObject.object_id).where(
                    PublicationObject.publication_id == publication_id
                )
            )
        )


def _publish_language_publication(client, workspace_key: str, suffix: str) -> dict:
    """Publish one language-only publication, superseding whatever is active in the workspace."""
    active_id = workspace_active_publication_id(workspace_key)
    return publish_language_publication(
        client,
        workspace_key,
        suffix,
        expected_active_publication_id=active_id,
    )


# --------------------------------------------------------------------------- branching lineage


def test_branch_derived_from_older_history_has_distinct_derived_from_and_supersedes():
    with TestClient(app) as client:
        workspace_key = unique_key("branch-lineage")
        create_workspace(client, workspace_key)

        # R1: language-only root publication.
        r1 = _publish_language_publication(client, workspace_key, unique_key("r1"))
        assert r1["derivedFromPublicationId"] is None
        assert r1["supersedesPublicationId"] is None
        assert r1["status"] == "active"

        # R2 is derived from R1 and adds a domain, so R1 retires in the same transaction.
        change_set2 = create_change_set(
            client, workspace_key, name="r2", derived_from_publication_id=r1["id"]
        ).json()
        domain_a = create_domain(client, change_set2, unique_key("branchA"))
        r2 = publish_change_set(
            client,
            change_set2["id"],
            expected_change_set_version=change_set2["version"],
            expected_active_publication_id=r1["id"],
        ).json()
        assert r2["derivedFromPublicationId"] == r1["id"]
        assert r2["supersedesPublicationId"] == r1["id"]
        assert publication_status(r1["id"]) == "withdrawn"
        assert publication_status(r2["id"]) == "active"

        # R3 is derived from R2 and adds a codelist beneath the domain carried from R2.
        change_set3 = create_change_set(
            client, workspace_key, name="r3", derived_from_publication_id=r2["id"]
        ).json()
        codelist_a = create_object(
            client,
            change_set3,
            "rdm-master",
            "codelist",
            f"Codelist {unique_key('branchC')}",
            attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
            parent_object_id=domain_a["id"],
        ).json()
        r3 = publish_change_set(
            client,
            change_set3["id"],
            expected_change_set_version=change_set3["version"],
            expected_active_publication_id=r2["id"],
        ).json()
        assert r3["derivedFromPublicationId"] == r2["id"]
        assert r3["supersedesPublicationId"] == r2["id"]
        assert publication_status(r2["id"]) == "withdrawn"
        assert publication_status(r3["id"]) == "active"

        # The branch change set derives from the OLD retired R1, not from the active R3, then activates.
        branch = create_change_set(
            client, workspace_key, name="branch", derived_from_publication_id=r1["id"]
        ).json()
        domain_b = create_domain(client, branch, unique_key("branchB"))
        r4 = publish_change_set(
            client,
            branch["id"],
            expected_change_set_version=branch["version"],
            expected_active_publication_id=r3["id"],
        ).json()
        assert r4["publicationNumber"] == 4
        # derivedFrom points at the older publication the branch was derived from while supersedes
        # points at the publication that was active at activation time -- a genuine branch, so distinct.
        assert r4["derivedFromPublicationId"] == r1["id"]
        assert r4["supersedesPublicationId"] == r3["id"]
        assert r4["derivedFromPublicationId"] != r4["supersedesPublicationId"]
        assert r4["status"] == "active"
        assert publication_status(r3["id"]) == "withdrawn"
        assert workspace_active_publication_id(workspace_key) == r4["id"]

        # Inspect the relevant publication details: both lineage fields are separate and correct.
        r1_detail = client.get(f"/api/v1/publications/{r1['id']}").json()
        r4_detail = client.get(f"/api/v1/publications/{r4['id']}").json()
        assert r1_detail["derivedFromPublicationId"] is None
        assert r1_detail["supersedesPublicationId"] is None
        assert r4_detail["derivedFromPublicationId"] == r1["id"]
        assert r4_detail["supersedesPublicationId"] == r3["id"]
        assert "derivedFromPublicationId" in r4_detail and "supersedesPublicationId" in r4_detail

        # Historical derivation applies only authored changes: later live domain and child survive.
        assert client.get(
            f"/api/v1/objects/domain/{domain_a['id']}", params={"workspaceKey": workspace_key}
        ).status_code == 200
        assert client.get(
            f"/api/v1/objects/codelist/{codelist_a['id']}", params={"workspaceKey": workspace_key}
        ).status_code == 200
        published_domain = client.get(
            f"/api/v1/objects/domain/{domain_b['id']}", params={"workspaceKey": workspace_key}
        )
        assert published_domain.status_code == 200
        assert published_domain.json()["name"] == domain_b["name"]
        objects, _relations = graph_snapshot_sets(published_graph_snapshot(client, workspace_key))
        assert (r1["language"]["objectTypeKey"], r1["language"]["id"]) in {
            (item[0], item[1]) for item in objects
        }


# --------------------------------------------------------------------------- publication list pagination


def test_publication_list_cursor_pagination_is_bounded_and_scoped_to_workspace():
    with TestClient(app) as client:
        workspace_key = unique_key("publication-page")
        create_workspace(client, workspace_key)
        publication_ids: list[str] = []
        for index in range(12):
            publication = _publish_language_publication(
                client, workspace_key, unique_key(f"page-{index}")
            )
            publication_ids.append(publication["id"])

        first_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/publications", params={"pageSize": 2}
        )
        assert first_page.status_code == 200
        body = first_page.json()
        assert len(body["items"]) == 2
        cursor = body["nextCursor"]
        assert cursor is not None

        second_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/publications",
            params={"pageSize": 2, "cursor": cursor},
        )
        assert second_page.status_code == 200
        body2 = second_page.json()
        assert len(body2["items"]) == 2
        assert body2["nextCursor"] is not None

        retry = client.get(
            f"/api/v1/workspaces/{workspace_key}/publications",
            params={"pageSize": 2, "cursor": cursor},
        )
        assert retry.json() == body2
        # New publications appear before this cursor; continuing does not repeat or skip old rows.
        newest = _publish_language_publication(client, workspace_key, unique_key("during-paging"))
        combined = body["items"] + body2["items"]
        next_cursor = body2["nextCursor"]
        while next_cursor:
            page = client.get(
                f"/api/v1/workspaces/{workspace_key}/publications",
                params={"pageSize": 2, "cursor": next_cursor},
            )
            assert page.status_code == 200
            assert 0 < len(page.json()["items"]) <= 2
            combined.extend(page.json()["items"])
            next_cursor = page.json()["nextCursor"]
        assert [item["id"] for item in combined] == publication_ids[::-1]
        assert client.get(
            f"/api/v1/workspaces/{workspace_key}/publications", params={"pageSize": 1}
        ).json()["items"][0]["id"] == newest["id"]
        assert {item["id"] for item in combined} == set(publication_ids)
        numbers = [item["publicationNumber"] for item in combined]
        assert numbers == sorted(numbers, reverse=True)
        # Every page item carries the full publication metadata including the separate lineage fields.
        for item in combined:
            assert "derivedFromPublicationId" in item and "supersedesPublicationId" in item
            assert item["workspaceKey"] == workspace_key

        # Sort direction is part of the contract: old ascending and malformed tokens are refused.
        legacy = encode_cursor(
            ("0000000002", publication_ids[1]),
            scope="publications",
            sort=("publicationNumber", "id"),
            filters={"workspaceKey": workspace_key},
        )
        for invalid in (legacy, "malformed"):
            rejected = client.get(
                f"/api/v1/workspaces/{workspace_key}/publications",
                params={"cursor": invalid},
            )
            assert rejected.status_code == 422
            assert rejected.json()["error"] == {
                "code": "invalid_cursor", "message": "Publication cursor is invalid"
            }
        for size in (0, 501):
            assert client.get(
                f"/api/v1/workspaces/{workspace_key}/publications", params={"pageSize": size}
            ).status_code == 422

        # The list is bound to the workspace: a cursor minted for one workspace cannot page another.
        other_key = unique_key("publication-other")
        create_workspace(client, other_key)
        _publish_language_publication(client, other_key, unique_key("other"))
        mismatched = client.get(
            f"/api/v1/workspaces/{other_key}/publications",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "invalid_cursor"


# --------------------------------------------------------------------------- snapshot parity


def test_publication_snapshot_parity_across_active_and_change_set_read_contexts():
    with TestClient(app) as client:
        workspace_key = unique_key("snapshot-parity")
        create_workspace(client, workspace_key)
        change_set, graph = build_complete_graph(client, workspace_key, unique_key("parity"))
        publication = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()
        publication_id = publication["id"]

        # An untouched change set derived from the publication makes the same content reachable through the
        # mutable change set read context.
        derived = create_change_set(
            client, workspace_key, name="parity-derived", derived_from_publication_id=publication_id
        ).json()

        published = published_graph_snapshot(client, workspace_key)
        historical = publication_graph_snapshot(client, publication_id)
        change_set_snapshot = change_set_graph_snapshot(client, derived["id"])
        # The object/relation snapshot read through the publication context matches both the active
        # projection (this publication is active) and the derived change set's effective membership.
        assert graph_snapshot_sets(historical) == graph_snapshot_sets(published)
        assert graph_snapshot_sets(change_set_snapshot) == graph_snapshot_sets(published)

        # The generic record representation is identical across the three read contexts for the same
        # record (structural fields only -- change set and publication rows record no timestamps).
        domain_id = graph["domain"]["id"]
        active_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"workspaceKey": workspace_key}
        ).json()
        publication_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}",
            params={"publicationId": publication_id},
        ).json()
        change_set_detail = client.get(
            f"/api/v1/objects/domain/{domain_id}", params={"changeSetId": derived["id"]}
        ).json()
        assert _canonical_object(active_detail) == _canonical_object(publication_detail)
        assert _canonical_object(change_set_detail) == _canonical_object(publication_detail)
        # WP-10K: live keeps its timestamps; history and change sets report them as absent rather than
        # substituting the request time, and refuse queries on them instead of matching nothing.
        assert active_detail["createdAt"] and active_detail["updatedAt"]
        for detail in (publication_detail, change_set_detail):
            assert detail["createdAt"] is None and detail["updatedAt"] is None
        for context in ({"publicationId": publication_id}, {"changeSetId": derived["id"]}):
            for params, code in (
                ({"filter.updatedAt.gte": "2000-01-01T00:00:00Z"}, "invalid_filter"),
                ({"sort": "-createdAt"}, "invalid_sort"),
            ):
                refused = client.get("/api/v1/objects/domain", params={**context, **params})
                assert refused.status_code == 422, refused.text
                assert refused.json()["error"]["code"] == code
        live_sorted = client.get(
            "/api/v1/objects/domain", params={"workspaceKey": workspace_key, "sort": "-updatedAt"}
        )
        assert live_sorted.status_code == 200, live_sorted.text

        # A relation present in the graph reads with the same generic RelationResponse from every
        # context.  The active projection's per-anchor feed is the generic active relation read path;
        # the publication and change set feeds are the generic publication/change set relation read paths.
        def relation_for_anchor(context_params: dict, relation_type_key: str) -> dict:
            items = client.get(
                "/api/v1/relations", params={"objectId": domain_id, **context_params}
            ).json()["items"]
            match = next(
                item for item in items if item["relation"]["relationTypeKey"] == relation_type_key
            )
            recorded = "workspaceKey" in context_params
            assert (match["relation"]["createdAt"] is not None) is recorded
            assert (match["relation"]["updatedAt"] is not None) is recorded
            return _canonical_relation(match["relation"])

        active_relation = relation_for_anchor({"workspaceKey": workspace_key}, "object-has-translation")
        publication_relation = relation_for_anchor(
            {"publicationId": publication_id}, "object-has-translation"
        )
        change_set_relation = relation_for_anchor({"changeSetId": derived["id"]}, "object-has-translation")
        assert publication_relation == active_relation
        assert change_set_relation == active_relation


# --------------------------------------------------------------------------- live writes on the active workspace


def test_active_live_writes_apply_without_a_change_set_and_leave_publication_snapshots_frozen():
    with TestClient(app) as client:
        workspace_key = unique_key("active-live")
        create_workspace(client, workspace_key)
        publication = _publish_language_publication(client, workspace_key, unique_key("live"))
        language = publication["language"]
        language_id = language["id"]
        publication_id = publication["id"]
        before_publication_snapshot = publication_graph_snapshot(client, publication_id)

        def live_get(object_id: str) -> dict:
            response = client.get(
                f"/api/v1/objects/language/{object_id}", params={"workspaceKey": workspace_key}
            )
            assert response.status_code == 200, response.text
            return response.json()

        # A create without changeSetId targets the live active store directly: it needs no
        # change set claim and is immediately part of the active projection.
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
        assert live_created["changeSetVersion"] is None
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

        # None of the live writes minted a publication or touched the immutable snapshot, and the
        # workspace is still active on the same publication.
        assert publication_graph_snapshot(client, publication_id) == before_publication_snapshot
        assert workspace_active_publication_id(workspace_key) == publication_id
        assert publication_status(publication_id) == "active"
        publications = client.get(f"/api/v1/workspaces/{workspace_key}/publications")
        assert publications.status_code == 200
        assert len(publications.json()["items"]) == 1


# --------------------------------------------------------------------------- immutable historical context


def _build_three_publication_history(client, workspace_key: str) -> tuple[dict, dict, dict, dict]:
    """Return ``(r0, r1, r2, domain_a)`` where r0 and r1 are retired and r2 is active.

    r0 is a language-only root.  r1 is derived from r0 and adds a domain plus a codelist under it, so
    r1's snapshot contains one ``domain-contains-codelist`` relation.  r2 is derived from r1 and adds
    a second domain.
    """
    r0 = _publish_language_publication(client, workspace_key, unique_key("h0"))
    change_set1 = create_change_set(
        client, workspace_key, name="h1", derived_from_publication_id=r0["id"]
    ).json()
    domain_a = create_domain(client, change_set1, unique_key("histA"))
    create_object(
        client,
        change_set1,
        "rdm-master",
        "codelist",
        f"Codelist {unique_key('histA')}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain_a["id"],
    )
    r1 = publish_change_set(
        client,
        change_set1["id"],
        expected_change_set_version=change_set1["version"],
        expected_active_publication_id=r0["id"],
    ).json()
    change_set2 = create_change_set(
        client, workspace_key, name="h2", derived_from_publication_id=r1["id"]
    ).json()
    create_domain(client, change_set2, unique_key("histB"))
    r2 = publish_change_set(
        client,
        change_set2["id"],
        expected_change_set_version=change_set2["version"],
        expected_active_publication_id=r1["id"],
    ).json()
    assert publication_status(r0["id"]) == "withdrawn"
    assert publication_status(r1["id"]) == "withdrawn"
    assert publication_status(r2["id"]) == "active"
    return r0, r1, r2, domain_a


def test_historical_publication_reads_stay_immutable_while_live_writes_write_through():
    with TestClient(app) as client:
        workspace_key = unique_key("history-immutable")
        create_workspace(client, workspace_key)
        r0, r1, r2, domain_a = _build_three_publication_history(client, workspace_key)
        language = r0["language"]

        # Both the older retained publication (r0) and the recently retired publication (r1) stay readable.
        for publication_id in (r0["id"], r1["id"]):
            detail = client.get(f"/api/v1/publications/{publication_id}")
            assert detail.status_code == 200
            assert detail.json()["status"] == "withdrawn"
            objects, _relations = graph_snapshot_sets(publication_graph_snapshot(client, publication_id))
            assert objects  # each retired publication still serves its immutable object snapshot

        # The retired publication r1 carries the rows it shares with the still-active r2 plus its own
        # immutable snapshot: its object/relation content is a strict subset of r2's content because
        # r2 was derived from r1 and only added another domain.
        r1_objects, r1_relations = graph_snapshot_sets(publication_graph_snapshot(client, r1["id"]))
        r2_objects, r2_relations = graph_snapshot_sets(publication_graph_snapshot(client, r2["id"]))
        assert r1_objects < r2_objects
        assert r1_relations == r2_relations
        assert any(relation[1] == "domain-contains-codelist" for relation in r1_relations)
        r1_relations_http = client.get(
            "/api/v1/relations",
            params={"objectId": domain_a["id"], "publicationId": r1["id"]},
        )
        assert r1_relations_http.status_code == 200
        assert any(
            item["relation"]["relationTypeKey"] == "domain-contains-codelist"
            for item in r1_relations_http.json()["items"]
        )

        # The full publication history is listed for the workspace including every retired publication.
        history = client.get(f"/api/v1/workspaces/{workspace_key}/publications", params={"pageSize": 10})
        assert history.status_code == 200
        assert {item["id"] for item in history.json()["items"]} == {r0["id"], r1["id"], r2["id"]}

        # A write without changeSetId lands on the LIVE active store even when the caller passes
        # a publicationId query parameter (write endpoints ignore it): history cannot be
        # mutated, it is simply bypassed.  Snapshot the retired r1 membership, the active r2 snapshot
        # and the published projection before the live writes.
        before_published = published_graph_snapshot(client, workspace_key)
        before_snapshot = publication_graph_snapshot(client, r1["id"])
        before_object_ids = _publication_object_ids(r1["id"])
        r2_before = publication_graph_snapshot(client, r2["id"])
        live_before = client.get(
            f"/api/v1/objects/language/{language['id']}",
            params={"workspaceKey": workspace_key},
        )
        assert live_before.status_code == 200, live_before.text
        old_live_name = live_before.json()["name"]

        # A write naming a publication is refused: a publication is read-only (H4c D-3).
        aimed = client.patch(
            f"/api/v1/objects/language/{language['id']}",
            params={"publicationId": r1["id"]},
            json={"name": "Renamed live", "expectedVersion": live_before.json()["version"]},
        )
        assert aimed.status_code == 422 and aimed.json()["error"]["code"] == "unknown_parameter"
        # The live language row is updated in place...
        renamed = client.patch(
            f"/api/v1/objects/language/{language['id']}",
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

        # ...and a create without a change set is immediately part of the live active projection
        # (naming a publication is refused, as above).
        body = {
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": "Live domain",
            "attributes": [attribute("domain-code", f"dom-{uuid4().hex[:8]}")],
        }
        aimed = client.post("/api/v1/objects", params={"publicationId": r1["id"]}, json=body)
        assert aimed.status_code == 422 and aimed.json()["error"]["code"] == "unknown_parameter"
        created = client.post("/api/v1/objects", json=body)
        assert created.status_code == 201, created.text
        assert (
            client.get(
                f"/api/v1/objects/domain/{created.json()['id']}",
                params={"workspaceKey": workspace_key},
            ).status_code
            == 200
        )

        # Every immutable publication snapshot stays byte-identical: the retired r1 object/relation
        # membership and the active r2 snapshot are untouched by the live writes, while the live
        # projection changed.  The retired r1 historical read still serves the pre-rename language.
        assert publication_graph_snapshot(client, r1["id"]) == before_snapshot
        assert _publication_object_ids(r1["id"]) == before_object_ids
        assert publication_graph_snapshot(client, r2["id"]) == r2_before
        assert published_graph_snapshot(client, workspace_key) != before_published
        assert (
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"publicationId": r1["id"]},
            ).json()["name"]
            == old_live_name
        )


# --------------------------------------------------------------------------- snapshot immutability


def test_historical_snapshot_reads_are_immutable_across_later_activations():
    with TestClient(app) as client:
        workspace_key = unique_key("snapshot-immutable")
        create_workspace(client, workspace_key)
        r0 = _publish_language_publication(client, workspace_key, unique_key("i0"))
        language = r0["language"]

        def capture(publication_id: str) -> str:
            return publication_graph_snapshot(client, publication_id)

        r0_before = capture(r0["id"])
        r0_detail_before = _canonical_object(
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"publicationId": r0["id"]},
            ).json()
        )

        # r1 supersedes and retires r0; the older snapshot must not change.
        change_set1 = create_change_set(
            client, workspace_key, name="i1", derived_from_publication_id=r0["id"]
        ).json()
        create_domain(client, change_set1, unique_key("i1"))
        r1 = publish_change_set(
            client,
            change_set1["id"],
            expected_change_set_version=change_set1["version"],
            expected_active_publication_id=r0["id"],
        ).json()
        assert publication_status(r0["id"]) == "withdrawn"
        assert capture(r0["id"]) == r0_before
        r1_before = capture(r1["id"])

        # r2 supersedes and retires r1; both older snapshots remain byte-identical.
        change_set2 = create_change_set(
            client, workspace_key, name="i2", derived_from_publication_id=r1["id"]
        ).json()
        create_domain(client, change_set2, unique_key("i2"))
        r2 = publish_change_set(
            client,
            change_set2["id"],
            expected_change_set_version=change_set2["version"],
            expected_active_publication_id=r1["id"],
        ).json()
        assert publication_status(r1["id"]) == "withdrawn"
        assert publication_status(r2["id"]) == "active"
        assert capture(r0["id"]) == r0_before
        assert capture(r1["id"]) == r1_before

        # A second read of the same immutable publication returns identical content.
        assert capture(r0["id"]) == capture(r0["id"])
        r0_detail_after = _canonical_object(
            client.get(
                f"/api/v1/objects/language/{language['id']}",
                params={"publicationId": r0["id"]},
            ).json()
        )
        assert r0_detail_after == r0_detail_before
