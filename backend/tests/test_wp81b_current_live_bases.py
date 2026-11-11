"""WP8.1-B regressions for explicit current-live change set sources."""

import threading

import pytest
from harness_identity import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from workspace_model_support import default_model
from wp8_support import (
    build_complete_graph,
    create_change_set,
    create_object,
    create_workspace,
    publish_change_set,
    published_relations,
    unique_key,
)

from app.config import database_url, reload_settings
from app.db import SessionLocal
from app.engine.change_sets import lifecycle as change_sets
from app.engine.change_sets.lifecycle import create_change_set as create_change_set_service
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.registry import model_registry
from app.errors import ApiError
from app.main import app, create_app
from app.models.database import (
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
)
from app.models.schema import EngineModel


def _live_domain(client: TestClient, workspace_key: str, suffix: str) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Domain {suffix}",
            "attributes": [{"attributeTypeKey": "domain-code", "value": f"dom-{suffix}"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _live_codelist(client: TestClient, workspace_key: str, parent_id: str, suffix: str) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-master",
            "objectTypeKey": "codelist",
            "name": f"Codelist {suffix}",
            "parentObjectId": parent_id,
            "attributes": [{"attributeTypeKey": "codelist-code", "value": f"cl-{suffix}"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_current_live_source_captures_unpublished_graph_and_stays_frozen():
    with TestClient(app) as client:
        workspace_key = unique_key("current-live-unpublished")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("before"))
        codelist = _live_codelist(client, workspace_key, domain["id"], unique_key("edge"))

        change_set = create_change_set(client, workspace_key, source="currentLive").json()
        assert change_set["source"] == "currentLive"
        captured = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"changeSetId": change_set["id"]}
        )
        assert captured.status_code == 200, captured.text
        assert captured.json()["name"] == domain["name"]
        captured_child = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"changeSetId": change_set["id"]},
        )
        assert captured_child.status_code == 200, captured_child.text
        assert captured_child.json()["parentObjectId"] == domain["id"]
        edges = client.get(
            "/api/v1/relations",
            params={"objectId": domain["id"], "changeSetId": change_set["id"]},
        )
        assert edges.status_code == 200, edges.text
        assert any(
            item["relation"]["relationTypeKey"] == "domain-contains-codelist"
            and item["relation"]["toObjectId"] == codelist["id"]
            for item in edges.json()["items"]
        )

        live_edit = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"name": "Live change after capture", "expectedVersion": domain["version"]},
        )
        assert live_edit.status_code == 200, live_edit.text
        frozen = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"changeSetId": change_set["id"]}
        )
        assert frozen.status_code == 200, frozen.text
        assert frozen.json()["name"] == domain["name"]
        assert client.get(f"/api/v1/workspaces/{workspace_key}/publications").json()["items"] == []

        with SessionLocal() as session:
            # The test database is shared across modules: select this workspace's base and domain.
            base = session.scalar(
                select(ChangeSetBase).where(ChangeSetBase.workspace_key == workspace_key)
            )
            assert base is not None
            assert base.model_runtime_version >= 1
            base_object = session.scalar(
                select(ChangeSetBaseObject).where(
                    ChangeSetBaseObject.base_id == base.id,
                    ChangeSetBaseObject.object_id == domain["id"],
                )
            )
            assert base_object is not None and base_object.version == domain["version"]


def test_current_live_activation_preserves_untouched_live_addition_and_refuses_touched_conflict():
    with TestClient(app) as client:
        workspace_key = unique_key("current-live-merge")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("base"))
        change_set = create_change_set(client, workspace_key, source="currentLive").json()

        staged = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={
                "name": "Change set name",
                "expectedVersion": domain["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert staged.status_code == 200, staged.text
        change_set["version"] = staged.json()["changeSetVersion"]
        untouched = _live_domain(client, workspace_key, unique_key("untouched"))

        conflict = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"name": "Live name", "expectedVersion": domain["version"]},
        )
        assert conflict.status_code == 200, conflict.text
        activation = client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            json={
                "expectedChangeSetVersion": change_set["version"],
                "expectedActivePublicationId": None,
            },
        )
        assert activation.status_code == 409, activation.text
        assert activation.json()["error"]["code"] == "VERSION_CONFLICT"
        assert (
            client.get(
                f"/api/v1/objects/domain/{untouched['id']}", params={"workspaceKey": workspace_key}
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 200
        assert client.get(f"/api/v1/workspaces/{workspace_key}/publications").json()["items"] == []


def test_current_live_activation_preserves_unrelated_live_edit_and_addition_with_prior_history():
    with TestClient(app) as client:
        workspace_key = unique_key("current-live-success")
        create_workspace(client, workspace_key)
        seed = create_change_set(client, workspace_key).json()
        original = create_object(
            client,
            seed,
            "rdm-master",
            "domain",
            "Original",
            attributes=[{"attributeTypeKey": "domain-code", "value": unique_key("original")}],
        ).json()
        first = client.post(
            f"/api/v1/change-sets/{seed['id']}/publication",
            json={"expectedChangeSetVersion": seed["version"], "expectedActivePublicationId": None},
        )
        assert first.status_code == 200, first.text
        current = create_change_set(client, workspace_key, source="currentLive").json()
        authored = create_object(
            client,
            current,
            "rdm-master",
            "domain",
            "Change set addition",
            attributes=[{"attributeTypeKey": "domain-code", "value": unique_key("change_set")}],
        ).json()
        live_edit = client.patch(
            f"/api/v1/objects/domain/{original['id']}",
            json={"name": "Live correction", "expectedVersion": original["version"]},
        )
        assert live_edit.status_code == 200, live_edit.text
        live_addition = _live_domain(client, workspace_key, unique_key("live-addition"))
        activated = client.post(
            f"/api/v1/change-sets/{current['id']}/publication",
            json={
                "expectedChangeSetVersion": current["version"],
                "expectedActivePublicationId": first.json()["id"],
            },
        )
        assert activated.status_code == 200, activated.text
        for object_id in (original["id"], authored["id"], live_addition["id"]):
            assert (
                client.get(
                    f"/api/v1/objects/domain/{object_id}", params={"workspaceKey": workspace_key}
                ).status_code
                == 200
            )
        assert (
            client.get(
                f"/api/v1/objects/domain/{original['id']}", params={"workspaceKey": workspace_key}
            ).json()["name"]
            == "Live correction"
        )
        old = client.get(
            f"/api/v1/objects/domain/{original['id']}",
            params={"publicationId": first.json()["id"]},
        )
        assert old.status_code == 200 and old.json()["name"] == "Original"


def test_change_set_source_rejections_and_legacy_requests_keep_their_meaning():
    with TestClient(app) as client:
        workspace_key = unique_key("source-contract")
        create_workspace(client, workspace_key)
        invalid_publication = client.post(
            f"/api/v1/workspaces/{workspace_key}/change-sets", json={"source": "publication"}
        )
        assert invalid_publication.status_code == 422
        invalid_live = client.post(
            f"/api/v1/workspaces/{workspace_key}/change-sets",
            json={
                "source": "currentLive",
                "derivedFromPublicationId": "11111111-1111-4111-8111-111111111111",
            },
        )
        assert invalid_live.status_code == 422
        # Omission remains the old empty development/bootstrap root; it is not silently upgraded.
        legacy = create_change_set(client, workspace_key).json()
        assert legacy["source"] == "empty"
        assert legacy["derivedFromPublicationId"] is None
        with SessionLocal() as session:
            assert (
                session.scalar(
                    select(ChangeSetBase.id).where(ChangeSetBase.workspace_key == workspace_key)
                )
                is None
            )


def test_current_live_capture_refuses_a_model_selection_that_changed_before_lock():
    with TestClient(app) as client:
        workspace_key = unique_key("model-capture-race")
        create_workspace(client, workspace_key)
    with SessionLocal() as session:
        state = default_model(session)
        assert state is not None
        with pytest.raises(ApiError) as error:
            create_change_set_service(
                session,
                workspace_key,
                state.model_release_id,
                source="currentLive",
                expected_model_runtime_release_id=state.model_release_id + 1,
            )
        assert error.value.code == "CHANGE_SET_SNAPSHOT_RETRY"
        assert (
            session.scalar(
                select(ChangeSetBase.id).where(ChangeSetBase.workspace_key == workspace_key)
            )
            is None
        )


def test_current_live_capture_reads_one_snapshot_while_an_external_writer_commits(monkeypatch):
    """A live write committing during the capture is not mixed into it (REPEATABLE READ)."""
    with TestClient(app) as client:
        workspace_key = unique_key("capture-snapshot")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("captured"))
        original_copy = change_sets.copy_live
        writer_committed = False

        def copy_with_external_writer(session, *arguments):
            nonlocal writer_committed
            external = create_engine(database_url())
            try:
                with external.begin() as connection:
                    connection.execute(
                        text("UPDATE objects SET name = 'must not mix' WHERE id = :id"),
                        {"id": domain["id"]},
                    )
                writer_committed = True
            finally:
                external.dispose()
            return original_copy(session, *arguments)

        monkeypatch.setattr(change_sets, "copy_live", copy_with_external_writer)
        change_set = create_change_set(client, workspace_key, source="currentLive").json()
        assert writer_committed
        captured = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"changeSetId": change_set["id"]}
        )
        assert captured.status_code == 200 and captured.json()["name"] == domain["name"]
        live = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"workspaceKey": workspace_key}
        )
        assert live.json()["name"] == "must not mix"


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE workspace_models SET version = version WHERE workspace_key = :key",
        "UPDATE workspaces SET status = status WHERE key = :key",
    ],
    ids=["activation", "retirement"],
)
def test_current_live_capture_holds_off_activation_and_retirement(monkeypatch, statement):
    """While the capture runs, the workspace's model assignment and its row cannot be changed."""
    with TestClient(app) as client:
        workspace_key = unique_key("capture-locks")
        create_workspace(client, workspace_key)
        _live_domain(client, workspace_key, unique_key("captured"))
        original_copy = change_sets.copy_live
        refused = False

        def copy_with_external_change(session, *arguments):
            nonlocal refused
            external = create_engine(database_url())
            try:
                with external.begin() as connection:
                    connection.execute(text("SET LOCAL lock_timeout = '200ms'"))
                    with pytest.raises(OperationalError, match="lock timeout"):
                        connection.execute(text(statement), {"key": workspace_key})
                    refused = True
            finally:
                external.dispose()
            return original_copy(session, *arguments)

        monkeypatch.setattr(change_sets, "copy_live", copy_with_external_change)
        response = create_change_set(client, workspace_key, source="currentLive")
        assert response.status_code == 201, response.text
        assert refused


def test_current_live_capture_after_a_concurrent_activation_asks_for_a_retry():
    """An activation committing while the capture waits for its lock ends it with a retry."""
    with TestClient(app) as client:
        workspace_key = unique_key("capture-retry")
        create_workspace(client, workspace_key)
        external = create_engine(database_url())
        try:
            connection = external.connect()
            transaction = connection.begin()
            connection.execute(
                text("UPDATE workspace_models SET version = version WHERE workspace_key = :key"),
                {"key": workspace_key},
            )
            # The capture starts its snapshot, then waits for the runtime-state row until the
            # "activation" above commits; a row changed after the snapshot cannot be captured.
            timer = threading.Timer(0.3, transaction.commit)
            timer.start()
            try:
                response = create_change_set(
                    client, workspace_key, source="currentLive", expected_status=409
                )
            finally:
                timer.join()
                connection.close()
        finally:
            external.dispose()
        assert response.json()["error"]["code"] == "CHANGE_SET_SNAPSHOT_RETRY"
        with SessionLocal() as session:
            assert (
                session.scalar(
                    select(ChangeSetBase.id).where(ChangeSetBase.workspace_key == workspace_key)
                )
                is None
            )
        create_change_set(client, workspace_key, source="currentLive")


def test_discard_and_successful_activation_remove_private_base_rows():
    with TestClient(app) as client:
        workspace_key = unique_key("base-cleanup")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("discard"))
        _live_codelist(client, workspace_key, domain["id"], unique_key("discard-edge"))
        discarded = create_change_set(client, workspace_key, source="currentLive").json()
        with SessionLocal() as session:
            base_id = session.scalar(
                select(ChangeSetBase.id).where(ChangeSetBase.workspace_key == workspace_key)
            )
            assert base_id is not None
            assert (
                session.scalar(
                    select(ChangeSetBaseObject.sequence_id).where(
                        ChangeSetBaseObject.base_id == base_id
                    )
                )
                is not None
            )
            assert (
                session.scalar(
                    select(ChangeSetBaseRelation.sequence_id).where(
                        ChangeSetBaseRelation.base_id == base_id
                    )
                )
                is not None
            )
        response = client.delete(
            f"/api/v1/change-sets/{discarded['id']}",
            params={"expectedVersion": discarded["version"]},
        )
        assert response.status_code == 204, response.text
        with SessionLocal() as session:
            assert session.get(ChangeSetBase, base_id) is None
            assert (
                session.scalar(
                    select(ChangeSetBaseObject.sequence_id).where(
                        ChangeSetBaseObject.base_id == base_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(ChangeSetBaseRelation.sequence_id).where(
                        ChangeSetBaseRelation.base_id == base_id
                    )
                )
                is None
            )

        activated = create_change_set(client, workspace_key, source="currentLive").json()
        with SessionLocal() as session:
            activation_base_id = session.scalar(
                select(ChangeSetBase.id).where(ChangeSetBase.workspace_key == workspace_key)
            )
            assert activation_base_id is not None
        activation = client.post(
            f"/api/v1/change-sets/{activated['id']}/publication",
            json={
                "expectedChangeSetVersion": activated["version"],
                "expectedActivePublicationId": None,
            },
        )
        assert activation.status_code == 200, activation.text
        assert client.get(f"/api/v1/publications/{activation.json()['id']}").status_code == 200
        with SessionLocal() as session:
            assert session.get(ChangeSetBase, activation_base_id) is None
            assert (
                session.scalar(
                    select(ChangeSetBaseObject.sequence_id).where(
                        ChangeSetBaseObject.base_id == activation_base_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(ChangeSetBaseRelation.sequence_id).where(
                        ChangeSetBaseRelation.base_id == activation_base_id
                    )
                )
                is None
            )


def test_sc05_current_live_copies_post_publication_independent_relation_changes(
    migrated_database, monkeypatch
):
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", migrated_database("sc05-current-live"))
        reload_settings()
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                source = client.get("/api/v1/model").json()
                source["release"]["version"] = f"0.6.0-sc05-{unique_key('relation')}"
                source["attributeTypes"].append(
                    {"key": "relation-note", "name": "Relation note", "valueType": "text"}
                )
                source["relationTypes"].append(
                    {
                        "key": "sc05-independent-link",
                        "reverseKey": "sc05-independent-link-reverse",
                        "name": "SC-05 independent link",
                        "reverseName": "SC-05 independent link reverse",
                    }
                )
                source["objectTypeRelations"].append(
                    {
                        "relationTypeKey": "sc05-independent-link",
                        "fromObjectTypeKey": "domain",
                        "toObjectTypeKey": "translation",
                        "cardinality": "many-to-many",
                        "attributeTypeKeys": ["relation-note"],
                    }
                )
                candidate = EngineModel.model_validate(source)
                with SessionLocal() as session:
                    release = ensure_bootstrap_release(session, candidate)
                    state = default_model(session)
                    assert state is not None
                    state.model_release_id = release.id
                    state.version += 1
                    session.commit()
                model_registry.clear()

                workspace_key = unique_key("sc05")
                create_workspace(client, workspace_key)
                seed, graph = build_complete_graph(client, workspace_key, unique_key("seed"))
                published = client.post(
                    f"/api/v1/change-sets/{seed['id']}/publication",
                    json={
                        "expectedChangeSetVersion": seed["version"],
                        "expectedActivePublicationId": None,
                    },
                )
                assert published.status_code == 200, published.text
                publication_id = published.json()["id"]
                domain_edit = client.patch(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    json={
                        "name": "Published live correction",
                        "expectedVersion": graph["domain"]["version"],
                    },
                )
                assert domain_edit.status_code == 200, domain_edit.text
                added = client.post(
                    "/api/v1/relations",
                    json={
                        "relationTypeKey": "sc05-independent-link",
                        "fromObjectId": graph["domain"]["id"],
                        "toObjectId": graph["translation"]["id"],
                        "attributes": {"relation-note": "initial"},
                    },
                )
                assert added.status_code == 201, added.text
                old_relation = added.json()
                relation_edit = client.patch(
                    f"/api/v1/relations/{old_relation['id']}",
                    json={
                        "attributes": {"relation-note": "changed"},
                        "expectedVersion": old_relation["version"],
                    },
                )
                assert relation_edit.status_code == 200, relation_edit.text
                removed = client.delete(
                    f"/api/v1/relations/{old_relation['id']}",
                    params={"expectedVersion": relation_edit.json()["version"]},
                )
                assert removed.status_code == 204, removed.text
                replacement = client.post(
                    "/api/v1/relations",
                    json={
                        "relationTypeKey": "sc05-independent-link",
                        "fromObjectId": graph["domain"]["id"],
                        "toObjectId": graph["translation"]["id"],
                        "attributes": {"relation-note": "replacement"},
                    },
                )
                assert replacement.status_code == 201, replacement.text
                live_addition = _live_domain(client, workspace_key, unique_key("after-publication"))

                change_set = create_change_set(client, workspace_key, source="currentLive").json()
                current_domain = client.get(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    params={"changeSetId": change_set["id"]},
                )
                assert current_domain.json()["name"] == "Published live correction"
                assert (
                    client.get(
                        f"/api/v1/objects/domain/{live_addition['id']}",
                        params={"changeSetId": change_set["id"]},
                    ).status_code
                    == 200
                )
                current_edge = client.get(
                    f"/api/v1/relations/{replacement.json()['id']}",
                    params={"changeSetId": change_set["id"]},
                )
                assert current_edge.status_code == 200
                assert current_edge.json()["attributes"] == {"relation-note": "replacement"}
                assert current_edge.json()["version"] == replacement.json()["version"]
                assert (
                    client.get(
                        f"/api/v1/relations/{old_relation['id']}",
                        params={"changeSetId": change_set["id"]},
                    ).status_code
                    == 404
                )

                historical_domain = client.get(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    params={"publicationId": publication_id},
                )
                assert historical_domain.json()["name"] == graph["domain"]["name"]
                assert (
                    client.get(
                        f"/api/v1/relations/{old_relation['id']}",
                        params={"publicationId": publication_id},
                    ).status_code
                    == 404
                )

                later_field = client.patch(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    json={
                        "name": "Later live change",
                        "expectedVersion": domain_edit.json()["version"],
                    },
                )
                assert later_field.status_code == 200, later_field.text
                later_edge = client.patch(
                    f"/api/v1/relations/{replacement.json()['id']}",
                    json={
                        "attributes": {"relation-note": "later"},
                        "expectedVersion": replacement.json()["version"],
                    },
                )
                assert later_edge.status_code == 200, later_edge.text
                assert (
                    client.get(
                        f"/api/v1/objects/domain/{graph['domain']['id']}",
                        params={"changeSetId": change_set["id"]},
                    ).json()["name"]
                    == "Published live correction"
                )
                assert client.get(
                    f"/api/v1/relations/{replacement.json()['id']}",
                    params={"changeSetId": change_set["id"]},
                ).json()["attributes"] == {"relation-note": "replacement"}
        finally:
            patch.undo()
            model_registry.clear()
            reload_settings()


def test_current_live_base_remains_frozen_and_readable_after_restart(
    migrated_database, monkeypatch
):
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", migrated_database("current-live-restart"))
        reload_settings()
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                workspace_key = unique_key("current-live-restart")
                create_workspace(client, workspace_key)
                domain = _live_domain(client, workspace_key, unique_key("before-restart"))
                change_set = create_change_set(client, workspace_key, source="currentLive").json()

            model_registry.clear()
            with TestClient(create_app()) as restarted_client:
                restored_change_set = restarted_client.get(
                    f"/api/v1/change-sets/{change_set['id']}"
                )
                assert restored_change_set.status_code == 200, restored_change_set.text
                assert restored_change_set.json()["source"] == "currentLive"
                restored_domain = restarted_client.get(
                    f"/api/v1/objects/domain/{domain['id']}",
                    params={"changeSetId": change_set["id"]},
                )
                assert restored_domain.status_code == 200, restored_domain.text
                assert restored_domain.json()["name"] == domain["name"]
        finally:
            patch.undo()
            model_registry.clear()
            reload_settings()


def test_editing_a_based_child_keeps_its_one_containment_edge_and_activates():
    workspace_key = unique_key("wp13-contained")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        suffix = unique_key("s")
        domain = _live_domain(client, workspace_key, suffix)
        codelist = _live_codelist(client, workspace_key, domain["id"], suffix)
        live_edges = published_relations(client, workspace_key, codelist["id"])
        change_set = create_change_set(client, workspace_key, source="currentLive").json()
        current = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"changeSetId": change_set["id"]},
        ).json()
        renamed = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "name": "Renamed in change set",
                "expectedVersion": current["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert renamed.status_code == 200, renamed.text
        change_set_edges = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "changeSetId": change_set["id"]},
        ).json()["items"]
        assert [item["relation"]["id"] for item in change_set_edges] == [
            item["relation"]["id"] for item in live_edges
        ]
        publish_change_set(
            client, change_set["id"], expected_change_set_version=renamed.json()["changeSetVersion"]
        )


def test_moving_a_based_child_replaces_its_containment_edge_and_activates():
    workspace_key = unique_key("wp10d-move")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        first = _live_domain(client, workspace_key, unique_key("a"))
        second = _live_domain(client, workspace_key, unique_key("b"))
        codelist = _live_codelist(client, workspace_key, first["id"], unique_key("c"))
        [old_edge] = published_relations(client, workspace_key, codelist["id"])
        change_set = create_change_set(client, workspace_key, source="currentLive").json()
        current = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"changeSetId": change_set["id"]},
        ).json()
        moved = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "parentObjectId": second["id"],
                "expectedVersion": current["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert moved.status_code == 200, moved.text
        [change_set_edge] = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "changeSetId": change_set["id"]},
        ).json()["items"]
        assert change_set_edge["relation"]["fromObjectId"] == second["id"]
        assert change_set_edge["relation"]["id"] != old_edge["relation"]["id"]
        assert published_relations(client, workspace_key, codelist["id"]) == [old_edge]

        renamed = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "name": "Moved and renamed",
                "expectedVersion": moved.json()["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": moved.json()["changeSetVersion"],
            },
        )
        assert renamed.status_code == 200, renamed.text
        [kept] = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "changeSetId": change_set["id"]},
        ).json()["items"]
        assert kept["relation"]["id"] == change_set_edge["relation"]["id"]

        publish_change_set(
            client, change_set["id"], expected_change_set_version=renamed.json()["changeSetVersion"]
        )
        live = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}", params={"workspaceKey": workspace_key}
        ).json()
        assert (live["parentObjectId"], live["name"]) == (second["id"], "Moved and renamed")
        [live_edge] = published_relations(client, workspace_key, codelist["id"])
        assert live_edge["relation"]["id"] == change_set_edge["relation"]["id"]
        assert live_edge["relation"]["fromObjectId"] == second["id"]
