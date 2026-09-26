"""WP8 package-5 tests: workspace publication withdrawal and lifecycle audit wiring.

These cover the publication-withdrawal operation (an atomic pointer clear plus status change that
keeps the publication readable), publishing again from a retained publication, and the
distinctness of content-publication withdrawal from administrative catalogue retirement.

Under the corrected live-data contract the workspace's live object store is the authoritative read
surface for ``workspaceKey`` reads, independent of the active-publication checkpoint; withdrawal
therefore only removes the checkpoint designation and never hides live data, and live cursors
(bound to the workspace + filters + sort only) survive a publication switch.  Restart persistence
of the withdrawn state is covered, and the ``publication-withdrawn`` lifecycle audit is
verified directly against :class:`AuditEvent` because workspace-scoped events carry no
``AuditEventSubject`` rows and never surface on object-history endpoints.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from wp8_support import (
    attribute,
    build_complete_graph,
    change_sets,
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
    published_object,
    unique_key,
    withdraw_publication,
    workspace_active_publication_id,
)

from app.db import SessionLocal, get_engine
from app.main import app
from app.models.database import (
    AuditEvent,
    AuditEventSubject,
    ObjectRelation,
    RdmObject,
)

# --------------------------------------------------------------------------- helpers


def _workspace_events(workspace_key: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "workspace",
                    AuditEvent.aggregate_id == workspace_key,
                )
                .order_by(AuditEvent.sequence_id)
            )
        )


def _subject_count(event_ids: list[int]) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(AuditEventSubject)
            .where(AuditEventSubject.audit_event_id.in_(event_ids))
        )


def _projection_rows(workspace_key: str) -> tuple:
    """Immutable tuple of the active-projection rows so a withdrawal cannot mutate records silently."""
    with SessionLocal() as session:
        objects = tuple(
            sorted(
                (row.id, row.name, row.version, row.parent_object_id)
                for row in session.scalars(
                    select(RdmObject).where(RdmObject.workspace_key == workspace_key)
                )
            )
        )
        relation_count = session.scalar(
            select(func.count())
            .select_from(ObjectRelation)
            .where(
                ObjectRelation.from_object_id.in_(row[0] for row in objects)
                | ObjectRelation.to_object_id.in_(row[0] for row in objects)
            )
        )
    return objects, int(relation_count or 0)


def _add_language(client, workspace_key: str, change_set: dict, suffix: str) -> dict:
    return create_object(
        client,
        change_set,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()


# --------------------------------------------------------------------------- publication withdrawal


def test_publication_withdrawal_clears_pointer_retains_history_and_records_audit():
    workspace_key = unique_key("withdraw-ok")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        change_set, graph = build_complete_graph(client, workspace_key, unique_key("withdraw"))
        publication = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()
        publication_id = publication["id"]
        assert workspace_active_publication_id(workspace_key) == publication_id
        assert publication_status(publication_id) == "active"
        published_before = published_graph_snapshot(client, workspace_key)
        projection_before = _projection_rows(workspace_key)
        workspace_before = client.get(f"/api/v1/workspaces/{workspace_key}").json()

        withdraw_response = withdraw_publication(client, publication_id)
        assert withdraw_response.status_code == 204

        # The active-content-publication pointer is cleared atomically with the publication's withdrawal.
        assert workspace_active_publication_id(workspace_key) is None
        assert publication_status(publication_id) == "withdrawn"
        detail = client.get(f"/api/v1/publications/{publication_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "withdrawn"
        assert detail.json()["withdrawnAt"] is not None
        # A publication names its model release, so a reader can show "Publication N · model X".
        release = client.get(f"/api/v1/model-releases/{detail.json()['modelReleaseId']}").json()
        assert (detail.json()["modelReleaseKey"], detail.json()["modelReleaseVersion"]) == (
            release["key"],
            release["version"],
        )

        # The workspace catalogue row is NOT administratively retired by a publication withdrawal.
        workspace_after = client.get(f"/api/v1/workspaces/{workspace_key}").json()
        assert workspace_after["status"] == "active"
        assert workspace_after["version"] == workspace_before["version"]
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200

        # Publication withdrawal clears the content-publication checkpoint but never hides live data:
        # the workspace's live object store is the authoritative read surface for workspaceKey reads
        # (no active-publication membership required), so every live record stays visible unchanged.
        before_objects, before_relations = graph_snapshot_sets(published_before)
        live_after, live_relations_after = graph_snapshot_sets(
            published_graph_snapshot(client, workspace_key)
        )
        assert live_after == before_objects
        assert live_relations_after == before_relations
        page = client.get(
            "/api/v1/objects/language", params={"workspaceKey": workspace_key, "pageSize": 50}
        )
        assert page.status_code == 200
        assert len(page.json()["items"]) == 1
        for object_type, expected in (
            ("language", graph["language"]),
            ("translation-group", graph["group"]),
            ("translation", graph["translation"]),
            ("domain", graph["domain"]),
            ("codelist", graph["codelist"]),
        ):
            assert (
                published_object(client, workspace_key, object_type, expected["id"])["id"]
                == expected["id"]
            )

        # The withdrawn publication remains readable as immutable history through the same generic reads.
        historical, historical_relations = graph_snapshot_sets(
            publication_graph_snapshot(client, publication_id)
        )
        before_objects, before_relations = graph_snapshot_sets(published_before)
        assert historical == before_objects
        assert historical_relations == before_relations
        domain_detail = client.get(
            f"/api/v1/objects/domain/{graph['domain']['id']}",
            params={"publicationId": publication_id},
        )
        assert domain_detail.status_code == 200
        domain_relations = client.get(
            "/api/v1/relations",
            params={"objectId": graph["domain"]["id"], "publicationId": publication_id},
        )
        assert domain_relations.status_code == 200
        assert any(
            item["relation"]["relationTypeKey"] == "object-has-translation"
            for item in domain_relations.json()["items"]
        )

        # No individual record is modified, deleted, or assigned retired state.
        assert _projection_rows(workspace_key) == projection_before
        assert {publication.id for publication in change_sets(workspace_key)} == {publication_id}

    # The publication-withdrawal identity is audited on the workspace aggregate, same transaction.
    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-withdrawn", 1)]
    assert events[0].changes == {
        "withdrawnPublicationId": publication_id,
        "publicationNumber": 1,
    }
    assert _subject_count([events[0].sequence_id]) == 0


def test_withdrawal_requires_and_enforces_the_active_publication_claim():
    workspace_key = unique_key("withdraw-conflict")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        previous = publish_language_publication(client, workspace_key, unique_key("previous"))
        publication = publish_language_publication(
            client, workspace_key, unique_key("rc"), expected_active_publication_id=previous["id"]
        )
        before_snapshot = published_graph_snapshot(client, workspace_key)

        # Withdrawing a publication that is no longer current conflicts and clears nothing.
        stale = withdraw_publication(client, previous["id"], expected_status=409)
        assert stale.json()["error"]["code"] == "workspace_active_publication_conflict"
        assert stale.json()["error"]["message"] == "Active publication has changed"
        assert workspace_active_publication_id(workspace_key) == publication["id"]
        assert publication_status(publication["id"]) == "active"
        assert published_graph_snapshot(client, workspace_key) == before_snapshot

        # An unknown publication is not found and clears nothing.
        missing = withdraw_publication(client, str(uuid4()), expected_status=404)
        assert missing.json()["error"]["code"] == "publication_not_found"
        assert workspace_active_publication_id(workspace_key) == publication["id"]
        assert publication_status(publication["id"]) == "active"

    assert _workspace_events(workspace_key) == []


# --------------------------------------------------------------------------- reactivation from retained history


def test_publishing_from_a_retained_publication_after_withdrawal():
    workspace_key = unique_key("reactive")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        change_set, graph = build_complete_graph(client, workspace_key, unique_key("r1"))
        r1 = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()
        withdrawn_snapshot = publication_graph_snapshot(client, r1["id"])
        withdraw_publication(client, r1["id"])
        assert workspace_active_publication_id(workspace_key) is None
        assert publication_status(r1["id"]) == "withdrawn"

        # Derive a NEW change set from the retained (withdrawn, readable) publication, then modify + add.
        derived = create_change_set(
            client, workspace_key, name="reactivate", derived_from_publication_id=r1["id"]
        ).json()
        assert derived["derivedFromPublicationId"] == r1["id"]
        renamed_value = "Language renamed after withdrawal"
        update_response = client.patch(
            f"/api/v1/objects/language/{graph['language']['id']}",
            json={
                "name": renamed_value,
                "expectedVersion": graph["language"]["version"],
                "changeSetId": derived["id"],
                "expectedChangeSetVersion": derived["version"],
            },
        )
        assert update_response.status_code == 200, update_response.text
        derived["version"] = update_response.json()["changeSetVersion"]
        added_domain = create_domain(client, derived, unique_key("reactivate"))

        validation = client.post(f"/api/v1/change-sets/{derived['id']}/validation")
        assert validation.status_code == 200
        assert validation.json()["valid"] is True

        # Activate with an explicit null claim: the workspace pointer is empty after withdrawal.
        r2 = publish_change_set(
            client,
            derived["id"],
            expected_change_set_version=derived["version"],
            explicit_null_active_publication=True,
        ).json()
        assert r2["publicationNumber"] == 2
        assert r2["derivedFromPublicationId"] == r1["id"]
        assert r2["supersedesPublicationId"] is None
        assert r2["status"] == "active"
        assert workspace_active_publication_id(workspace_key) == r2["id"]

        # Published reads return the reactivated graph: the retained records, the renamed language
        # and the newly added domain are all visible together.
        assert (
            published_object(
                client, workspace_key, "language", graph["language"]["id"]
            )["name"]
            == renamed_value
        )
        assert (
            published_object(client, workspace_key, "domain", added_domain["id"])["id"]
            == added_domain["id"]
        )
        # The carried-forward records keep their stable public identities.
        assert (
            published_object(client, workspace_key, "codelist", graph["codelist"]["id"])["id"]
            == graph["codelist"]["id"]
        )
        reactivated, _ = graph_snapshot_sets(published_graph_snapshot(client, workspace_key))
        assert (graph["domain"]["objectTypeKey"], graph["domain"]["id"]) in {
            (item[0], item[1]) for item in reactivated
        }

        # The retained withdrawn publication is untouched and still readable.
        assert publication_status(r1["id"]) == "withdrawn"
        assert publication_graph_snapshot(client, r1["id"]) == withdrawn_snapshot

    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-withdrawn", 1)]


# --------------------------------------------------------------------------- catalogue vs publication withdrawal


def test_catalogue_retirement_remains_distinct_from_publication_withdrawal():
    # Publication withdrawal on its own leaves the catalogue row administratively active so a fresh
    # change set can still be created and records written into it.
    published_key = unique_key("pub-distinct")
    with TestClient(app) as client:
        create_workspace(client, published_key)
        publication = publish_language_publication(client, published_key, unique_key("pd"))
        withdraw_publication(client, publication["id"])
        assert workspace_active_publication_id(published_key) is None
        assert client.get(f"/api/v1/workspaces/{published_key}").json()["status"] == "active"

        fresh = create_change_set(client, published_key, name="fresh after publication withdrawal").json()
        language = _add_language(client, published_key, fresh, "fresh")
        assert language["workspaceKey"] == published_key

    # Administrative catalogue retirement is a separate operation that never clears the publication
    # pointer and does not consult expectedActivePublicationId.
    admin_key = unique_key("admin-distinct")
    with TestClient(app) as client:
        workspace = create_workspace(client, admin_key)
        publication = publish_language_publication(client, admin_key, unique_key("ad"))
        assert workspace_active_publication_id(admin_key) == publication["id"]

        retired = client.patch(
            f"/api/v1/workspaces/{admin_key}",
            json={"status": "retired", "expectedVersion": workspace["version"]},
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"
        # The content-publication pointer is untouched by administrative retirement.
        assert workspace_active_publication_id(admin_key) == publication["id"]
        assert publication_status(publication["id"]) == "active"
        # Published reads keep serving the last active publication.
        assert published_object(client, admin_key, "language", publication["language"]["id"]) is not None
        # Record writes into a fresh change set are blocked because the CATALOGUE record is retired.
        blocked = create_change_set(client, admin_key, name="blocked", expected_status=409)
        assert blocked.json()["error"]["code"] == "workspace_retired"

    # The two operations never emit each other's audit events.
    assert _workspace_events(published_key)
    assert _workspace_events(admin_key) == []


# --------------------------------------------------------------------------- active cursor invalidation


def test_live_cursor_survives_publication_switches_and_keeps_paging():
    workspace_key = unique_key("cursor-switch")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)

        # Publish R1 with two languages so a page of size 1 returns a real live-collection cursor.
        change_set = create_change_set(client, workspace_key, name="two langs").json()
        _add_language(client, workspace_key, change_set, unique_key("a"))
        _add_language(client, workspace_key, change_set, unique_key("b"))
        r1 = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()
        assert workspace_active_publication_id(workspace_key) == r1["id"]

        first_page = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1},
        )
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 1
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        # A live cursor binds the workspace + filters + sort (position-based keyset), never a
        # publication.  A superseding activation therefore does not invalidate it: the cursor resumes
        # paging the live projection and yields the second carried-forward language.
        change_set2 = create_change_set(
            client, workspace_key, name="supersede", derived_from_publication_id=r1["id"]
        ).json()
        create_domain(client, change_set2, unique_key("switch"))
        r2 = publish_change_set(
            client,
            change_set2["id"],
            expected_change_set_version=change_set2["version"],
            expected_active_publication_id=r1["id"],
        ).json()
        assert workspace_active_publication_id(workspace_key) == r2["id"]

        continued = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1, "cursor": cursor},
        )
        assert continued.status_code == 200
        assert len(continued.json()["items"]) == 1
        # The two languages are the only live language rows, so the projection is now consumed.
        assert continued.json()["nextCursor"] is None

        # Withdrawal is a checkpoint switch, never a live-data switch: a cursor minted against the
        # live store keeps working after withdrawal because the live rows are unchanged.
        r2_cursor = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1},
        ).json()["nextCursor"]
        assert r2_cursor is not None
        withdraw_publication(client, r2["id"])
        assert workspace_active_publication_id(workspace_key) is None
        after_withdrawal = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1, "cursor": r2_cursor},
        )
        assert after_withdrawal.status_code == 200
        assert len(after_withdrawal.json()["items"]) == 1
        assert after_withdrawal.json()["nextCursor"] is None


# --------------------------------------------------------------------------- restart persistence


def test_restart_after_publish_and_withdrawal_persists_state(tmp_path, monkeypatch):
    """Reopen a second app instance against the same real temporary database file.

    After publish + withdrawal the restarted instance must keep serving the authoritative live
    object store (withdrawal removes the publication checkpoint, never live data), keep the withdrawn
    publication readable as history, and retain the workspace catalogue row (still administratively
    active) plus the ``publication-withdrawn`` audit event.
    """
    from app.config import reload_settings
    from app.main import create_app
    from app.services.model.registry import model_registry

    database_path = tmp_path / "wp8-restart.db"
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
            reload_settings()
            model_registry.clear()
            workspace_key = unique_key("restart")
            withdrawn_publication_id = None
            language_id = None
            with TestClient(create_app()) as first_client:
                assert first_client.get("/health").json() == {"status": "ok"}
                create_workspace(first_client, workspace_key)
                change_set = create_change_set(first_client, workspace_key, name="restart seed").json()
                language = _add_language(first_client, workspace_key, change_set, unique_key("restart"))
                publication = publish_change_set(
                    first_client,
                    change_set["id"],
                    expected_change_set_version=change_set["version"],
                    explicit_null_active_publication=True,
                ).json()
                withdrawn_publication_id = publication["id"]
                language_id = language["id"]
                assert workspace_active_publication_id(workspace_key) == withdrawn_publication_id
                assert (
                    withdraw_publication(first_client, withdrawn_publication_id).status_code
                    == 204
                )
                assert workspace_active_publication_id(workspace_key) is None

            # Reopen a second app instance against the same file and confirm persisted state.
            model_registry.clear()
            with TestClient(create_app()) as restarted_client:
                assert restarted_client.get("/health").json() == {"status": "ok"}
                assert restarted_client.get("/api/v1/model").status_code == 200

                # Live data survives restart: withdrawal removes the publication checkpoint into
                # history, never the authoritative live object store that workspaceKey reads serve.
                assert (
                    published_object(restarted_client, workspace_key, "language", language_id)["id"]
                    == language_id
                )
                page = restarted_client.get(
                    "/api/v1/objects/language",
                    params={"workspaceKey": workspace_key, "pageSize": 50},
                )
                assert page.status_code == 200
                assert len(page.json()["items"]) == 1

                # History publications remain readable including their immutable snapshots.
                detail = restarted_client.get(f"/api/v1/publications/{withdrawn_publication_id}")
                assert detail.status_code == 200
                assert detail.json()["status"] == "withdrawn"
                snapshot = restarted_client.get(
                    "/api/v1/objects/language",
                    params={"publicationId": withdrawn_publication_id},
                )
                assert snapshot.status_code == 200
                assert len(snapshot.json()["items"]) == 1

                # The workspace catalogue row survives (publication withdrawal never retires it).
                workspace = restarted_client.get(f"/api/v1/workspaces/{workspace_key}")
                assert workspace.status_code == 200
                assert workspace.json()["status"] == "active"

            # Lifecycle audit survives the restart.
            with SessionLocal() as session:
                events = list(
                    session.scalars(
                        select(AuditEvent)
                        .where(
                            AuditEvent.aggregate_type == "workspace",
                            AuditEvent.aggregate_id == workspace_key,
                        )
                        .order_by(AuditEvent.sequence_id)
                    )
                )
            assert [(event.action, event.version) for event in events] == [
                ("publication-withdrawn", 1)
            ]
            assert events[0].changes["withdrawnPublicationId"] == withdrawn_publication_id
    finally:
        model_registry.clear()
        reload_settings()


# --------------------------------------------------------------------------- long workspace keys


def _audit_aggregate_id_column_length() -> int:
    """Reflect the live ``audit_events.aggregate_id`` declared column width."""
    columns = {column["name"]: column for column in inspect(get_engine()).get_columns("audit_events")}
    length = columns["aggregate_id"]["type"].length
    assert isinstance(length, int)
    return length


def test_publication_withdrawal_succeeds_for_a_workspace_key_longer_than_36_characters():
    # Publication withdrawal audits on the real workspace key, which is legal up to String(160) while
    # the historical AuditEvent.aggregate_id was String(36).  SQLite does not enforce VARCHAR length,
    # so this is primarily behavioural + definitional protection for a length-strict database.
    workspace_key = uuid4().hex + ("w" * 118)
    assert len(workspace_key) > 36
    assert len(workspace_key) <= 160
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        publication = publish_language_publication(client, workspace_key, unique_key("long-key"))
        publication_id = publication["id"]
        assert workspace_active_publication_id(workspace_key) == publication_id

        withdraw_response = withdraw_publication(client, publication_id)
        assert withdraw_response.status_code == 204
        assert workspace_active_publication_id(workspace_key) is None
        assert publication_status(publication_id) == "withdrawn"

    # The recorded aggregate id carries the full, untruncated workspace key.
    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-withdrawn", 1)]
    assert events[0].aggregate_id == workspace_key
    assert len(events[0].aggregate_id) == len(workspace_key)


def test_audit_aggregate_id_column_is_wide_enough_for_the_longest_legal_workspace_key():
    # Workspace.key is String(160); the workspace-scoped lifecycle aggregate stores the real key, so
    # the ORM model AND the migrated schema must both be at least that wide.
    model_length = AuditEvent.__table__.c.aggregate_id.type.length
    assert model_length is not None
    assert model_length >= 160
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _audit_aggregate_id_column_length() >= 160


def test_live_crud_after_publication_withdrawal_then_catalogue_read_only():
    with TestClient(app) as client:
        key = unique_key("withdraw-live-crud")
        workspace = create_workspace(client, key)
        publication = publish_language_publication(client, key, unique_key("live"))
        snapshot = publication_graph_snapshot(client, publication["id"])
        withdraw_publication(client, publication["id"])
        language = published_object(client, key, "language", publication["language"]["id"])
        url = f"/api/v1/objects/language/{language['id']}"
        renamed = client.patch(
            url,
            json={"name": "Live after withdrawal", "expectedVersion": language["version"]},
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Live after withdrawal"
        changed = client.patch(
            f"{url}/attributes/language-code",
            json={"value": unique_key("changed"), "expectedVersion": renamed.json()["version"]},
        )
        assert changed.status_code == 200, changed.text
        payload = {
            "workspaceKey": key,
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": "Created after retirement",
            "attributes": [attribute("domain-code", unique_key("live-domain"))],
        }
        created = client.post("/api/v1/objects", json=payload)
        assert created.status_code == 201, created.text
        domain = created.json()
        deleted = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": domain["version"]}
        )
        assert deleted.status_code == 204, deleted.text
        assert workspace_active_publication_id(key) is None
        assert len(change_sets(key)) == 1
        assert publication_graph_snapshot(client, publication["id"]) == snapshot

        retired = client.patch(
            f"/api/v1/workspaces/{key}",
            json={"status": "retired", "expectedVersion": workspace["version"]},
        )
        assert retired.status_code == 200, retired.text
        live = published_object(client, key, "language", language["id"])
        before = published_graph_snapshot(client, key)
        with SessionLocal() as session:
            audit_count = session.scalar(select(func.count()).select_from(AuditEvent))
        attempts = [
            client.post("/api/v1/objects", json=payload),
            client.patch(url, json={"name": "Forbidden", "expectedVersion": live["version"]}),
            client.patch(
                f"{url}/attributes/language-code",
                json={"value": "forbidden", "expectedVersion": live["version"]},
            ),
            client.delete(url, params={"expectedVersion": live["version"]}),
        ]
        for response in attempts:
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "workspace_retired"
            assert response.json()["error"]["message"]
        assert published_graph_snapshot(client, key) == before
        assert publication_graph_snapshot(client, publication["id"]) == snapshot
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(AuditEvent)) == audit_count
