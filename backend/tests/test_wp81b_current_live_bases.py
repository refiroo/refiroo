"""WP8.1-B regressions for explicit current-live workspace draft sources."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from wp8_support import (
    activate_draft,
    build_complete_graph,
    create_draft,
    create_object,
    create_workspace,
    published_relations,
    unique_key,
)

from app.config import database_url, reload_settings
from app.db import SessionLocal
from app.errors import ApiError
from app.main import app, create_app
from app.models.database import (
    ModelRuntimeState,
    WorkspaceDraftBase,
    WorkspaceDraftBaseObject,
    WorkspaceDraftBaseRelation,
)
from app.models.schema import EngineModel
from app.services import workspace_revisions
from app.services.model.bootstrap import ensure_bootstrap_release
from app.services.model.registry import model_registry
from app.services.workspace_revisions import create_draft as create_draft_service


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

        draft = create_draft(client, workspace_key, source="currentLive").json()
        assert draft["source"] == "currentLive"
        captured = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"workspaceDraftId": draft["id"]}
        )
        assert captured.status_code == 200, captured.text
        assert captured.json()["name"] == domain["name"]
        captured_child = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"workspaceDraftId": draft["id"]},
        )
        assert captured_child.status_code == 200, captured_child.text
        assert captured_child.json()["parentObjectId"] == domain["id"]
        edges = client.get(
            "/api/v1/relations",
            params={"objectId": domain["id"], "workspaceDraftId": draft["id"]},
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
            f"/api/v1/objects/domain/{domain['id']}", params={"workspaceDraftId": draft["id"]}
        )
        assert frozen.status_code == 200, frozen.text
        assert frozen.json()["name"] == domain["name"]
        assert client.get(f"/api/v1/workspaces/{workspace_key}/revisions").json()["items"] == []

        with SessionLocal() as session:
            base = session.get(WorkspaceDraftBase, session.scalar(select(WorkspaceDraftBase.id)))
            assert base is not None
            assert base.model_runtime_version >= 1
            base_object = session.scalar(
                select(WorkspaceDraftBaseObject).where(WorkspaceDraftBaseObject.base_id == base.id)
            )
            assert base_object is not None and base_object.version == domain["version"]


def test_current_live_activation_preserves_untouched_live_addition_and_refuses_touched_conflict():
    with TestClient(app) as client:
        workspace_key = unique_key("current-live-merge")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("base"))
        draft = create_draft(client, workspace_key, source="currentLive").json()

        staged = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={
                "name": "Draft name",
                "expectedVersion": domain["version"],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
            },
        )
        assert staged.status_code == 200, staged.text
        draft["version"] = staged.json()["workspaceDraftVersion"]
        untouched = _live_domain(client, workspace_key, unique_key("untouched"))

        conflict = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"name": "Live name", "expectedVersion": domain["version"]},
        )
        assert conflict.status_code == 200, conflict.text
        activation = client.post(
            f"/api/v1/workspace-drafts/{draft['id']}/activation",
            json={"expectedDraftVersion": draft["version"], "expectedActiveRevisionId": None},
        )
        assert activation.status_code == 409, activation.text
        assert activation.json()["error"]["code"] == "version_conflict"
        assert (
            client.get(
                f"/api/v1/objects/domain/{untouched['id']}", params={"workspaceKey": workspace_key}
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").status_code == 200
        assert client.get(f"/api/v1/workspaces/{workspace_key}/revisions").json()["items"] == []


def test_current_live_activation_preserves_unrelated_live_edit_and_addition_with_prior_history():
    with TestClient(app) as client:
        workspace_key = unique_key("current-live-success")
        create_workspace(client, workspace_key)
        seed = create_draft(client, workspace_key).json()
        original = create_object(
            client,
            seed,
            "rdm-master",
            "domain",
            "Original",
            attributes=[{"attributeTypeKey": "domain-code", "value": unique_key("original")}],
        ).json()
        first = client.post(
            f"/api/v1/workspace-drafts/{seed['id']}/activation",
            json={"expectedDraftVersion": seed["version"], "expectedActiveRevisionId": None},
        )
        assert first.status_code == 200, first.text
        current = create_draft(client, workspace_key, source="currentLive").json()
        authored = create_object(
            client,
            current,
            "rdm-master",
            "domain",
            "Draft addition",
            attributes=[{"attributeTypeKey": "domain-code", "value": unique_key("draft")}],
        ).json()
        live_edit = client.patch(
            f"/api/v1/objects/domain/{original['id']}",
            json={"name": "Live correction", "expectedVersion": original["version"]},
        )
        assert live_edit.status_code == 200, live_edit.text
        live_addition = _live_domain(client, workspace_key, unique_key("live-addition"))
        activated = client.post(
            f"/api/v1/workspace-drafts/{current['id']}/activation",
            json={
                "expectedDraftVersion": current["version"],
                "expectedActiveRevisionId": first.json()["id"],
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
            params={"workspaceRevisionId": first.json()["id"]},
        )
        assert old.status_code == 200 and old.json()["name"] == "Original"


def test_draft_source_rejections_and_legacy_requests_keep_their_meaning():
    with TestClient(app) as client:
        workspace_key = unique_key("source-contract")
        create_workspace(client, workspace_key)
        invalid_revision = client.post(
            f"/api/v1/workspaces/{workspace_key}/drafts", json={"source": "revision"}
        )
        assert invalid_revision.status_code == 422
        invalid_live = client.post(
            f"/api/v1/workspaces/{workspace_key}/drafts",
            json={
                "source": "currentLive",
                "derivedFromRevisionId": "11111111-1111-4111-8111-111111111111",
            },
        )
        assert invalid_live.status_code == 422
        # Omission remains the old empty development/bootstrap root; it is not silently upgraded.
        legacy = create_draft(client, workspace_key).json()
        assert legacy["source"] == "empty"
        assert legacy["derivedFromRevisionId"] is None
        with SessionLocal() as session:
            assert (
                session.scalar(
                    select(WorkspaceDraftBase.id).where(
                        WorkspaceDraftBase.workspace_key == workspace_key
                    )
                )
                is None
            )


def test_current_live_capture_refuses_a_model_selection_that_changed_before_lock():
    with TestClient(app) as client:
        workspace_key = unique_key("model-capture-race")
        create_workspace(client, workspace_key)
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        with pytest.raises(ApiError) as error:
            create_draft_service(
                session,
                workspace_key,
                state.active_model_release_id,
                source="currentLive",
                expected_model_runtime_release_id=state.active_model_release_id + 1,
            )
        assert error.value.code == "workspace_draft_snapshot_retry"
        assert (
            session.scalar(
                select(WorkspaceDraftBase.id).where(
                    WorkspaceDraftBase.workspace_key == workspace_key
                )
            )
            is None
        )


def test_current_live_capture_explicitly_refuses_an_unsupported_database_dialect():
    session = MagicMock()
    session.bind.dialect.name = "postgresql"

    with pytest.raises(ApiError) as error:
        create_draft_service(
            session,
            "default",
            1,
            source="currentLive",
            expected_model_runtime_release_id=1,
        )

    assert error.value.status == 409
    assert error.value.code == "workspace_draft_snapshot_unsupported"
    session.rollback.assert_not_called()


def test_current_live_capture_excludes_a_synchronized_external_sqlite_writer(monkeypatch):
    with TestClient(app) as client:
        workspace_key = unique_key("capture-writer-lock")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("captured"))
        original_loader = workspace_revisions._load_live_membership
        writer_attempted = False

        def load_with_external_writer(session, key):
            nonlocal writer_attempted
            external = create_engine(database_url(), connect_args={"timeout": 0})
            try:
                with external.begin() as connection:
                    with pytest.raises(OperationalError):
                        connection.execute(
                            text("UPDATE objects SET name = 'must not mix' WHERE id = :id"),
                            {"id": domain["id"]},
                        )
                    writer_attempted = True
            finally:
                external.dispose()
            return original_loader(session, key)

        monkeypatch.setattr(workspace_revisions, "_load_live_membership", load_with_external_writer)
        draft = create_draft(client, workspace_key, source="currentLive").json()
        assert writer_attempted
        captured = client.get(
            f"/api/v1/objects/domain/{domain['id']}", params={"workspaceDraftId": draft["id"]}
        )
        assert captured.status_code == 200 and captured.json()["name"] == domain["name"]


def test_discard_and_successful_activation_remove_private_base_rows_with_sqlite_fk_off():
    with TestClient(app) as client:
        workspace_key = unique_key("base-cleanup")
        create_workspace(client, workspace_key)
        domain = _live_domain(client, workspace_key, unique_key("discard"))
        _live_codelist(client, workspace_key, domain["id"], unique_key("discard-edge"))
        discarded = create_draft(client, workspace_key, source="currentLive").json()
        with SessionLocal() as session:
            base_id = session.scalar(
                select(WorkspaceDraftBase.id).where(
                    WorkspaceDraftBase.workspace_key == workspace_key
                )
            )
            assert base_id is not None
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseObject.sequence_id).where(
                        WorkspaceDraftBaseObject.base_id == base_id
                    )
                )
                is not None
            )
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseRelation.sequence_id).where(
                        WorkspaceDraftBaseRelation.base_id == base_id
                    )
                )
                is not None
            )
        response = client.delete(
            f"/api/v1/workspace-drafts/{discarded['id']}",
            params={"expectedVersion": discarded["version"]},
        )
        assert response.status_code == 204, response.text
        with SessionLocal() as session:
            assert session.get(WorkspaceDraftBase, base_id) is None
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseObject.sequence_id).where(
                        WorkspaceDraftBaseObject.base_id == base_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseRelation.sequence_id).where(
                        WorkspaceDraftBaseRelation.base_id == base_id
                    )
                )
                is None
            )

        activated = create_draft(client, workspace_key, source="currentLive").json()
        with SessionLocal() as session:
            activation_base_id = session.scalar(
                select(WorkspaceDraftBase.id).where(
                    WorkspaceDraftBase.workspace_key == workspace_key
                )
            )
            assert activation_base_id is not None
        activation = client.post(
            f"/api/v1/workspace-drafts/{activated['id']}/activation",
            json={"expectedDraftVersion": activated["version"], "expectedActiveRevisionId": None},
        )
        assert activation.status_code == 200, activation.text
        assert (
            client.get(f"/api/v1/workspace-revisions/{activation.json()['id']}").status_code == 200
        )
        with SessionLocal() as session:
            assert session.get(WorkspaceDraftBase, activation_base_id) is None
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseObject.sequence_id).where(
                        WorkspaceDraftBaseObject.base_id == activation_base_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(WorkspaceDraftBaseRelation.sequence_id).where(
                        WorkspaceDraftBaseRelation.base_id == activation_base_id
                    )
                )
                is None
            )


def test_sc05_current_live_copies_post_publication_independent_relation_changes(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "sc05-current-live.db"
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
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
                    state = session.get(ModelRuntimeState, 1)
                    assert state is not None
                    state.active_model_release_id = release.id
                    state.version += 1
                    session.commit()
                model_registry.clear()

                workspace_key = unique_key("sc05")
                create_workspace(client, workspace_key)
                seed, graph = build_complete_graph(client, workspace_key, unique_key("seed"))
                published = client.post(
                    f"/api/v1/workspace-drafts/{seed['id']}/activation",
                    json={
                        "expectedDraftVersion": seed["version"],
                        "expectedActiveRevisionId": None,
                    },
                )
                assert published.status_code == 200, published.text
                revision_id = published.json()["id"]
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

                draft = create_draft(client, workspace_key, source="currentLive").json()
                current_domain = client.get(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    params={"workspaceDraftId": draft["id"]},
                )
                assert current_domain.json()["name"] == "Published live correction"
                assert (
                    client.get(
                        f"/api/v1/objects/domain/{live_addition['id']}",
                        params={"workspaceDraftId": draft["id"]},
                    ).status_code
                    == 200
                )
                current_edge = client.get(
                    f"/api/v1/relations/{replacement.json()['id']}",
                    params={"workspaceDraftId": draft["id"]},
                )
                assert current_edge.status_code == 200
                assert current_edge.json()["attributes"] == {"relation-note": "replacement"}
                assert current_edge.json()["version"] == replacement.json()["version"]
                assert (
                    client.get(
                        f"/api/v1/relations/{old_relation['id']}",
                        params={"workspaceDraftId": draft["id"]},
                    ).status_code
                    == 404
                )

                historical_domain = client.get(
                    f"/api/v1/objects/domain/{graph['domain']['id']}",
                    params={"workspaceRevisionId": revision_id},
                )
                assert historical_domain.json()["name"] == graph["domain"]["name"]
                assert (
                    client.get(
                        f"/api/v1/relations/{old_relation['id']}",
                        params={"workspaceRevisionId": revision_id},
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
                        params={"workspaceDraftId": draft["id"]},
                    ).json()["name"]
                    == "Published live correction"
                )
                assert client.get(
                    f"/api/v1/relations/{replacement.json()['id']}",
                    params={"workspaceDraftId": draft["id"]},
                ).json()["attributes"] == {"relation-note": "replacement"}
        finally:
            patch.undo()
            model_registry.clear()
            reload_settings()


def test_current_live_base_remains_frozen_and_readable_after_restart(tmp_path, monkeypatch):
    database_path = tmp_path / "current-live-restart.db"
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        reload_settings()
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                workspace_key = unique_key("current-live-restart")
                create_workspace(client, workspace_key)
                domain = _live_domain(client, workspace_key, unique_key("before-restart"))
                draft = create_draft(client, workspace_key, source="currentLive").json()

            model_registry.clear()
            with TestClient(create_app()) as restarted_client:
                restored_draft = restarted_client.get(
                    f"/api/v1/workspace-drafts/{draft['id']}"
                )
                assert restored_draft.status_code == 200, restored_draft.text
                assert restored_draft.json()["source"] == "currentLive"
                restored_domain = restarted_client.get(
                    f"/api/v1/objects/domain/{domain['id']}",
                    params={"workspaceDraftId": draft["id"]},
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
        draft = create_draft(client, workspace_key, source="currentLive").json()
        current = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"workspaceDraftId": draft["id"]},
        ).json()
        renamed = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "name": "Renamed in draft",
                "expectedVersion": current["version"],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
            },
        )
        assert renamed.status_code == 200, renamed.text
        draft_edges = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "workspaceDraftId": draft["id"]},
        ).json()["items"]
        assert [item["relation"]["id"] for item in draft_edges] == [
            item["relation"]["id"] for item in live_edges
        ]
        activate_draft(
            client, draft["id"], expected_draft_version=renamed.json()["workspaceDraftVersion"]
        )


def test_moving_a_based_child_replaces_its_containment_edge_and_activates():
    workspace_key = unique_key("wp10d-move")
    with TestClient(app) as client:
        create_workspace(client, workspace_key)
        first = _live_domain(client, workspace_key, unique_key("a"))
        second = _live_domain(client, workspace_key, unique_key("b"))
        codelist = _live_codelist(client, workspace_key, first["id"], unique_key("c"))
        [old_edge] = published_relations(client, workspace_key, codelist["id"])
        draft = create_draft(client, workspace_key, source="currentLive").json()
        current = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}",
            params={"workspaceDraftId": draft["id"]},
        ).json()
        moved = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "parentObjectId": second["id"],
                "expectedVersion": current["version"],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": draft["version"],
            },
        )
        assert moved.status_code == 200, moved.text
        [draft_edge] = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "workspaceDraftId": draft["id"]},
        ).json()["items"]
        assert draft_edge["relation"]["fromObjectId"] == second["id"]
        assert draft_edge["relation"]["id"] != old_edge["relation"]["id"]
        assert published_relations(client, workspace_key, codelist["id"]) == [old_edge]

        renamed = client.patch(
            f"/api/v1/objects/codelist/{codelist['id']}",
            json={
                "name": "Moved and renamed",
                "expectedVersion": moved.json()["version"],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": moved.json()["workspaceDraftVersion"],
            },
        )
        assert renamed.status_code == 200, renamed.text
        [kept] = client.get(
            "/api/v1/relations",
            params={"objectId": codelist["id"], "workspaceDraftId": draft["id"]},
        ).json()["items"]
        assert kept["relation"]["id"] == draft_edge["relation"]["id"]

        activate_draft(
            client, draft["id"], expected_draft_version=renamed.json()["workspaceDraftVersion"]
        )
        live = client.get(
            f"/api/v1/objects/codelist/{codelist['id']}", params={"workspaceKey": workspace_key}
        ).json()
        assert (live["parentObjectId"], live["name"]) == (second["id"], "Moved and renamed")
        [live_edge] = published_relations(client, workspace_key, codelist["id"])
        assert live_edge["relation"]["id"] == draft_edge["relation"]["id"]
        assert live_edge["relation"]["fromObjectId"] == second["id"]
