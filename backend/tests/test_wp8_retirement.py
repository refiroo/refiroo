"""WP8 package-5 tests: workspace publication retirement and lifecycle audit wiring.

These cover the publication-retirement operation (an atomic pointer clear plus prior-revision
retirement that keeps the revision readable as history), reactivation from retained history, and the
distinctness of content-publication retirement from administrative catalogue retirement.

Under the corrected live-data contract the workspace's live object store is the authoritative read
surface for ``workspaceKey`` reads, independent of the active-revision checkpoint; publication
retirement therefore retires the checkpoint revision into history but never hides live data, and
live cursors (bound to the workspace + filters + sort only) survive a publication switch.  Restart
persistence of the retired state is covered, and the ``publication-retired`` lifecycle audit is
verified directly against :class:`AuditEvent` because workspace-scoped events carry no
``AuditEventSubject`` rows and never surface on object-history endpoints.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from wp8_support import (
    activate_draft,
    attribute,
    build_complete_graph,
    create_domain,
    create_draft,
    create_object,
    create_workspace,
    graph_snapshot_sets,
    publish_language_revision,
    published_graph_snapshot,
    published_object,
    retire_publication,
    revision_graph_snapshot,
    revision_status,
    unique_key,
    workspace_active_revision_id,
    workspace_revisions,
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
    """Immutable tuple of the active-projection rows so a retirement cannot mutate records silently."""
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


def _add_language(client, workspace_key: str, draft: dict, suffix: str) -> dict:
    return create_object(
        client,
        draft,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()


# --------------------------------------------------------------------------- publication retirement


def test_publication_retirement_clears_pointer_retains_history_and_records_audit():
    workspace_key = unique_key("retire-ok")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        draft, graph = build_complete_graph(client, workspace_key, unique_key("retire"))
        revision = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()
        revision_id = revision["id"]
        assert workspace_active_revision_id(workspace_key) == revision_id
        assert revision_status(revision_id) == "active"
        published_before = published_graph_snapshot(client, workspace_key)
        projection_before = _projection_rows(workspace_key)
        workspace_before = client.get(f"/api/v1/workspaces/{workspace_key}").json()

        retire_response = retire_publication(client, workspace_key, revision_id)
        assert retire_response.status_code == 204

        # The active-content-revision pointer is cleared atomically with the prior revision retire.
        assert workspace_active_revision_id(workspace_key) is None
        assert revision_status(revision_id) == "retired"
        detail = client.get(f"/api/v1/workspace-revisions/{revision_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "retired"
        assert detail.json()["retiredAt"] is not None

        # The workspace catalogue row is NOT administratively retired by a publication retirement.
        workspace_after = client.get(f"/api/v1/workspaces/{workspace_key}").json()
        assert workspace_after["status"] == "active"
        assert workspace_after["version"] == workspace_before["version"]
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200

        # Publication retirement clears the content-revision checkpoint but never hides live data:
        # the workspace's live object store is the authoritative read surface for workspaceKey reads
        # (no active-revision membership required), so every live record stays visible unchanged.
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

        # The retired revision remains readable as immutable history through the same generic reads.
        historical, historical_relations = graph_snapshot_sets(
            revision_graph_snapshot(client, revision_id)
        )
        before_objects, before_relations = graph_snapshot_sets(published_before)
        assert historical == before_objects
        assert historical_relations == before_relations
        domain_detail = client.get(
            f"/api/v1/objects/domain/{graph['domain']['id']}",
            params={"workspaceRevisionId": revision_id},
        )
        assert domain_detail.status_code == 200
        domain_relations = client.get(
            "/api/v1/relations",
            params={"objectId": graph["domain"]["id"], "workspaceRevisionId": revision_id},
        )
        assert domain_relations.status_code == 200
        assert any(
            item["relation"]["relationTypeKey"] == "object-has-translation"
            for item in domain_relations.json()["items"]
        )

        # No individual record is modified, deleted, or assigned retired state.
        assert _projection_rows(workspace_key) == projection_before
        assert {revision.id for revision in workspace_revisions(workspace_key)} == {revision_id}

    # The publication-retirement identity is audited on the workspace aggregate, same transaction.
    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-retired", 1)]
    assert events[0].changes == {
        "retiredRevisionId": revision_id,
        "revisionNumber": 1,
    }
    assert _subject_count([events[0].sequence_id]) == 0


def test_retirement_requires_and_enforces_the_active_revision_claim():
    workspace_key = unique_key("retire-conflict")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        previous = publish_language_revision(client, workspace_key, unique_key("previous"))
        revision = publish_language_revision(
            client, workspace_key, unique_key("rc"), expected_active_revision_id=previous["id"]
        )
        before_snapshot = published_graph_snapshot(client, workspace_key)

        # A stale expectedActiveRevisionId conflicts and clears nothing.
        stale = retire_publication(
            client, workspace_key, previous["id"], expected_status=409
        )
        assert stale.json()["error"]["code"] == "workspace_active_revision_conflict"
        assert stale.json()["error"]["message"] == "Active workspace revision has changed"
        assert workspace_active_revision_id(workspace_key) == revision["id"]
        assert revision_status(revision["id"]) == "active"
        assert published_graph_snapshot(client, workspace_key) == before_snapshot

        # expectedActiveRevisionId is required by the contract: omitting it is a validation error.
        missing = client.post(
            f"/api/v1/workspaces/{workspace_key}/retirement", json={}
        )
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "request_validation_error"
        assert workspace_active_revision_id(workspace_key) == revision["id"]
        assert revision_status(revision["id"]) == "active"

    assert _workspace_events(workspace_key) == []


# --------------------------------------------------------------------------- reactivation from retained history


def test_reactivation_from_retained_history_after_publication_retirement():
    workspace_key = unique_key("reactive")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        draft, graph = build_complete_graph(client, workspace_key, unique_key("r1"))
        r1 = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()
        retired_snapshot = revision_graph_snapshot(client, r1["id"])
        retire_publication(client, workspace_key, r1["id"])
        assert workspace_active_revision_id(workspace_key) is None
        assert revision_status(r1["id"]) == "retired"

        # Derive a NEW draft from the retained (retired, readable) revision, then modify + add.
        derived = create_draft(
            client, workspace_key, name="reactivate", derived_from_revision_id=r1["id"]
        ).json()
        assert derived["derivedFromRevisionId"] == r1["id"]
        renamed_value = "Language renamed after retirement"
        update_response = client.patch(
            f"/api/v1/objects/language/{graph['language']['id']}",
            json={
                "name": renamed_value,
                "expectedVersion": graph["language"]["version"],
                "workspaceDraftId": derived["id"],
                "expectedWorkspaceDraftVersion": derived["version"],
            },
        )
        assert update_response.status_code == 200, update_response.text
        derived["version"] = update_response.json()["workspaceDraftVersion"]
        added_domain = create_domain(client, derived, unique_key("reactivate"))

        validation = client.post(f"/api/v1/workspace-drafts/{derived['id']}/validation")
        assert validation.status_code == 200
        assert validation.json()["valid"] is True

        # Activate with an explicit null claim: the workspace pointer is empty after retirement.
        r2 = activate_draft(
            client,
            derived["id"],
            expected_draft_version=derived["version"],
            explicit_null_active_revision=True,
        ).json()
        assert r2["revisionNumber"] == 2
        assert r2["derivedFromRevisionId"] == r1["id"]
        assert r2["supersedesRevisionId"] is None
        assert r2["status"] == "active"
        assert workspace_active_revision_id(workspace_key) == r2["id"]

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

        # The retained retired history is untouched and still readable.
        assert revision_status(r1["id"]) == "retired"
        assert revision_graph_snapshot(client, r1["id"]) == retired_snapshot

    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-retired", 1)]


# --------------------------------------------------------------------------- catalogue vs publication retirement


def test_catalogue_retirement_remains_distinct_from_publication_retirement():
    # Publication retirement on its own leaves the catalogue row administratively active so a fresh
    # draft can still be created and records written into it.
    published_key = unique_key("pub-distinct")
    with TestClient(app) as client:
        create_workspace(client, published_key)
        revision = publish_language_revision(client, published_key, unique_key("pd"))
        retire_publication(client, published_key, revision["id"])
        assert workspace_active_revision_id(published_key) is None
        assert client.get(f"/api/v1/workspaces/{published_key}").json()["status"] == "active"

        fresh = create_draft(client, published_key, name="fresh after publication retirement").json()
        language = _add_language(client, published_key, fresh, "fresh")
        assert language["workspaceKey"] == published_key

    # Administrative catalogue retirement is a separate operation that never clears the publication
    # pointer and does not consult expectedActiveRevisionId.
    admin_key = unique_key("admin-distinct")
    with TestClient(app) as client:
        workspace = create_workspace(client, admin_key)
        revision = publish_language_revision(client, admin_key, unique_key("ad"))
        assert workspace_active_revision_id(admin_key) == revision["id"]

        retired = client.patch(
            f"/api/v1/workspaces/{admin_key}",
            json={"status": "retired", "expectedVersion": workspace["version"]},
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"
        # The content-publication pointer is untouched by administrative retirement.
        assert workspace_active_revision_id(admin_key) == revision["id"]
        assert revision_status(revision["id"]) == "active"
        # Published reads keep serving the last active publication.
        assert published_object(client, admin_key, "language", revision["language"]["id"]) is not None
        # Record writes into a fresh draft are blocked because the CATALOGUE record is retired.
        blocked = create_draft(client, admin_key, name="blocked", expected_status=409)
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
        draft = create_draft(client, workspace_key, name="two langs").json()
        _add_language(client, workspace_key, draft, unique_key("a"))
        _add_language(client, workspace_key, draft, unique_key("b"))
        r1 = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()
        assert workspace_active_revision_id(workspace_key) == r1["id"]

        first_page = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1},
        )
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 1
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        # A live cursor binds the workspace + filters + sort (position-based keyset), never a
        # revision.  A superseding activation therefore does not invalidate it: the cursor resumes
        # paging the live projection and yields the second carried-forward language.
        draft2 = create_draft(
            client, workspace_key, name="supersede", derived_from_revision_id=r1["id"]
        ).json()
        create_domain(client, draft2, unique_key("switch"))
        r2 = activate_draft(
            client,
            draft2["id"],
            expected_draft_version=draft2["version"],
            expected_active_revision_id=r1["id"],
        ).json()
        assert workspace_active_revision_id(workspace_key) == r2["id"]

        continued = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1, "cursor": cursor},
        )
        assert continued.status_code == 200
        assert len(continued.json()["items"]) == 1
        # The two languages are the only live language rows, so the projection is now consumed.
        assert continued.json()["nextCursor"] is None

        # Retirement is a checkpoint switch, never a live-data switch: a cursor minted against the
        # live store keeps working after retirement because the live rows are unchanged.
        r2_cursor = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1},
        ).json()["nextCursor"]
        assert r2_cursor is not None
        retire_publication(client, workspace_key, r2["id"])
        assert workspace_active_revision_id(workspace_key) is None
        after_retirement = client.get(
            "/api/v1/objects/language",
            params={"workspaceKey": workspace_key, "pageSize": 1, "cursor": r2_cursor},
        )
        assert after_retirement.status_code == 200
        assert len(after_retirement.json()["items"]) == 1
        assert after_retirement.json()["nextCursor"] is None


# --------------------------------------------------------------------------- restart persistence


def test_restart_after_activation_and_retirement_persists_state(tmp_path, monkeypatch):
    """Reopen a second app instance against the same real temporary database file.

    After activation + retirement the restarted instance must keep serving the authoritative live
    object store (retirement retires the revision checkpoint, never live data), keep the retired
    revision readable as history, and retain the workspace catalogue row (still administratively
    active) plus the ``publication-retired`` audit event.
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
            retired_revision_id = None
            language_id = None
            with TestClient(create_app()) as first_client:
                assert first_client.get("/health").json() == {"status": "ok"}
                create_workspace(first_client, workspace_key)
                draft = create_draft(first_client, workspace_key, name="restart seed").json()
                language = _add_language(first_client, workspace_key, draft, unique_key("restart"))
                revision = activate_draft(
                    first_client,
                    draft["id"],
                    expected_draft_version=draft["version"],
                    explicit_null_active_revision=True,
                ).json()
                retired_revision_id = revision["id"]
                language_id = language["id"]
                assert workspace_active_revision_id(workspace_key) == retired_revision_id
                assert (
                    retire_publication(first_client, workspace_key, retired_revision_id).status_code
                    == 204
                )
                assert workspace_active_revision_id(workspace_key) is None

            # Reopen a second app instance against the same file and confirm persisted state.
            model_registry.clear()
            with TestClient(create_app()) as restarted_client:
                assert restarted_client.get("/health").json() == {"status": "ok"}
                assert restarted_client.get("/api/v1/model").status_code == 200

                # Live data survives restart: retirement retires the revision checkpoint into
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

                # History revisions remain readable including their immutable snapshots.
                detail = restarted_client.get(f"/api/v1/workspace-revisions/{retired_revision_id}")
                assert detail.status_code == 200
                assert detail.json()["status"] == "retired"
                snapshot = restarted_client.get(
                    "/api/v1/objects/language",
                    params={"workspaceRevisionId": retired_revision_id},
                )
                assert snapshot.status_code == 200
                assert len(snapshot.json()["items"]) == 1

                # The workspace catalogue row survives (publication retirement never retires it).
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
                ("publication-retired", 1)
            ]
            assert events[0].changes["retiredRevisionId"] == retired_revision_id
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


def test_publication_retirement_succeeds_for_a_workspace_key_longer_than_36_characters():
    # Publication retirement audits on the real workspace key, which is legal up to String(160) while
    # the historical AuditEvent.aggregate_id was String(36).  SQLite does not enforce VARCHAR length,
    # so this is primarily behavioural + definitional protection for a length-strict database.
    workspace_key = uuid4().hex + ("w" * 118)
    assert len(workspace_key) > 36
    assert len(workspace_key) <= 160
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        revision = publish_language_revision(client, workspace_key, unique_key("long-key"))
        revision_id = revision["id"]
        assert workspace_active_revision_id(workspace_key) == revision_id

        retire_response = retire_publication(client, workspace_key, revision_id)
        assert retire_response.status_code == 204
        assert workspace_active_revision_id(workspace_key) is None
        assert revision_status(revision_id) == "retired"

    # The recorded aggregate id carries the full, untruncated workspace key.
    events = _workspace_events(workspace_key)
    assert [(event.action, event.version) for event in events] == [("publication-retired", 1)]
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


def test_live_crud_after_publication_retirement_then_catalogue_read_only():
    with TestClient(app) as client:
        key = unique_key("retire-live-crud")
        workspace = create_workspace(client, key)
        revision = publish_language_revision(client, key, unique_key("live"))
        snapshot = revision_graph_snapshot(client, revision["id"])
        retire_publication(client, key, revision["id"])
        language = published_object(client, key, "language", revision["language"]["id"])
        url = f"/api/v1/objects/language/{language['id']}"
        renamed = client.patch(
            url,
            json={"name": "Live after retirement", "expectedVersion": language["version"]},
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Live after retirement"
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
        assert workspace_active_revision_id(key) is None
        assert len(workspace_revisions(key)) == 1
        assert revision_graph_snapshot(client, revision["id"]) == snapshot

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
        assert revision_graph_snapshot(client, revision["id"]) == snapshot
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(AuditEvent)) == audit_count
