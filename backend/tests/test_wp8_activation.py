"""WP8 package-3 tests: atomic workspace-draft activation.

These cover the single-transaction publication of a complete effective graph: the active-revision
pointer switch, active projection rebuild, immutable revision creation with stable public UUIDs,
derived-from/supersedes lineage, and the distinct concurrency/model-release/graph conflict classes.
Every conflict test asserts that nothing publishes -- active pointer and projection unchanged, no new
revision row, and the draft still present with unchanged version and content.  Activation audit is
verified directly against :class:`AuditEvent` because ``workspace-revision`` events carry no
``AuditEventSubject`` rows.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from wp8_support import (
    activate_draft,
    attribute,
    copy_active_model_release_as_unused,
    create_draft,
    create_object,
    create_workspace,
    draft_membership_counts,
    inject_draft_object,
    publish_language_revision,
    published_graph_snapshot,
    published_object,
    published_relations,
    revision_counts,
    revision_status,
    rewire_draft_to_release,
    unique_key,
    workspace_active_revision_id,
    workspace_revisions,
)

from app.db import SessionLocal
from app.main import app
from app.models.database import AuditEvent, AuditEventSubject
from app.services.workspace_revisions import effective_draft_membership


def _translation_relation(target_id: str) -> list[dict]:
    return [
        {
            "relationTypeKey": "object-has-translation",
            "direction": "incoming",
            "otherObjectId": target_id,
        }
    ]


def _domain(client, draft, suffix: str) -> dict:
    return create_object(
        client,
        draft,
        "rdm-master",
        "domain",
        f"Domain {suffix}",
        attributes=[attribute("domain-code", f"dom-{suffix}-{uuid4().hex[:8]}")],
    ).json()


def _build_complete_graph(client, workspace_key: str, suffix: str) -> tuple[dict, dict]:
    """Language->group containment, domain->codelist containment, one translation.

    The graph spans rdm-translations (language/translation-group/translation) and rdm-master
    (domain/codelist), carries typed containment edges, and one independent required ownership
    relation (``object-has-translation`` from the domain to the translation).  This is the graph the
    package-2 suite already validates as complete.
    """
    draft = create_draft(client, workspace_key, name=f"graph {suffix}").json()
    language = create_object(
        client,
        draft,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()
    group = create_object(
        client,
        draft,
        "rdm-translations",
        "translation-group",
        f"Group {suffix}",
        attributes=[attribute("group-code", f"grp-{suffix}-{uuid4().hex[:8]}")],
        parent_object_id=language["id"],
    ).json()
    domain = _domain(client, draft, unique_key(suffix))
    codelist = create_object(
        client,
        draft,
        "rdm-master",
        "codelist",
        f"Codelist {suffix}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain["id"],
    ).json()
    translation = create_object(
        client,
        draft,
        "rdm-translations",
        "translation",
        f"Translation {suffix}",
        attributes=[attribute("translated-value", f"tv-{uuid4().hex[:8]}")],
        parent_object_id=group["id"],
        initial_relations=_translation_relation(domain["id"]),
    ).json()
    return draft, {
        "language": language,
        "group": group,
        "domain": domain,
        "codelist": codelist,
        "translation": translation,
    }


def _activation_events(revision_id: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "workspace-revision",
                    AuditEvent.aggregate_id == revision_id,
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


def _relation_type_keys(client, workspace_key: str, object_id: str) -> set[str]:
    return {
        item["relation"]["relationTypeKey"]
        for item in published_relations(client, workspace_key, object_id)
    }


def _assert_draft_unchanged(client, draft_id: str, expected_version: int, expected_membership: tuple[int, int]) -> None:
    detail = client.get(f"/api/v1/workspace-drafts/{draft_id}")
    assert detail.status_code == 200
    assert detail.json()["version"] == expected_version
    assert draft_membership_counts(draft_id) == expected_membership


def _assert_publication_state_unchanged(
    client,
    workspace_key: str,
    *,
    before_snapshot: str,
    before_active_revision: str | None,
    before_revision_count: int,
) -> None:
    assert published_graph_snapshot(client, workspace_key) == before_snapshot
    assert workspace_active_revision_id(workspace_key) == before_active_revision
    assert len(workspace_revisions(workspace_key)) == before_revision_count


# --------------------------------------------------------------------------- success


def test_successful_activation_publishes_complete_graph_and_records_activation_audit():
    with TestClient(app) as client:
        workspace_key = unique_key("activate-ok")
        create_workspace(client, workspace_key)
        draft, graph = _build_complete_graph(client, workspace_key, unique_key("ok"))

        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        )
        revision = response.json()
        assert revision["status"] == "active"
        assert revision["derivedFromRevisionId"] is None
        assert revision["supersedesRevisionId"] is None
        assert revision["revisionNumber"] == 1
        assert workspace_active_revision_id(workspace_key) == revision["id"]
        assert revision_status(revision["id"]) == "active"
        assert revision_counts(revision["id"]) == (5, 4)

        # The mutable draft is closed only after publication succeeds.
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").status_code == 404

        # Every object of the effective graph is visible on the published read path together.
        for object_type, expected in (
            ("language", graph["language"]),
            ("translation-group", graph["group"]),
            ("translation", graph["translation"]),
            ("domain", graph["domain"]),
            ("codelist", graph["codelist"]),
        ):
            published = published_object(client, workspace_key, object_type, expected["id"])
            assert published is not None, f"{object_type} {expected['id']} not published"
            assert published["name"] == expected["name"]
            assert published["version"] == expected["version"]
        assert published_object(client, workspace_key, "translation-group", graph["group"]["id"])["parentObjectId"] == graph["language"]["id"]
        assert published_object(client, workspace_key, "codelist", graph["codelist"]["id"])["parentObjectId"] == graph["domain"]["id"]

        # Containment and the independent relation appear together on the domain's published edges.
        keys = _relation_type_keys(client, workspace_key, graph["domain"]["id"])
        assert "domain-contains-codelist" in keys
        assert "object-has-translation" in keys
        language_keys = _relation_type_keys(client, workspace_key, graph["language"]["id"])
        assert "language-contains-group" in language_keys

    # Activation identity audit is recorded on the workspace-revision aggregate, same transaction.
    events = _activation_events(revision["id"])
    assert [(event.action, event.version) for event in events] == [("activated", 1)]
    changes = events[0].changes
    assert changes["draftId"] == draft["id"]
    assert changes["workspaceKey"] == workspace_key
    assert changes["modelReleaseId"] == revision["modelReleaseId"]
    assert changes["objectCount"] == 5
    assert changes["relationCount"] == 4
    assert "derivedFromRevisionId" not in changes
    assert "supersedesRevisionId" not in changes
    assert _subject_count([events[0].sequence_id]) == 0


def test_atomic_translation_publication():
    with TestClient(app) as client:
        workspace_key = unique_key("translation-pub")
        create_workspace(client, workspace_key)
        draft = create_draft(client, workspace_key, name="translations").json()
        domain = _domain(client, draft, unique_key("tpub"))
        language = create_object(
            client,
            draft,
            "rdm-translations",
            "language",
            "Translation language",
            attributes=[attribute("language-code", f"lang-{uuid4().hex[:8]}")],
        ).json()
        group = create_object(
            client,
            draft,
            "rdm-translations",
            "translation-group",
            "Translation group",
            attributes=[attribute("group-code", f"grp-{uuid4().hex[:8]}")],
            parent_object_id=language["id"],
        ).json()
        translation = create_object(
            client,
            draft,
            "rdm-translations",
            "translation",
            "Published translation",
            attributes=[attribute("translated-value", f"tv-{uuid4().hex[:8]}")],
            parent_object_id=group["id"],
            initial_relations=_translation_relation(domain["id"]),
        ).json()

        # Nothing is published before activation.
        assert published_object(client, workspace_key, "translation", translation["id"]) is None
        assert published_object(client, workspace_key, "language", language["id"]) is None
        assert published_object(client, workspace_key, "domain", domain["id"]) is None

        revision = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()

        # The translation records publish atomically with their cross-application owner graph.
        assert published_object(client, workspace_key, "translation", translation["id"])["version"] == translation["version"]
        assert published_object(client, workspace_key, "translation-group", group["id"])["parentObjectId"] == language["id"]
        assert published_object(client, workspace_key, "domain", domain["id"])["id"] == domain["id"]
        domain_keys = _relation_type_keys(client, workspace_key, domain["id"])
        assert "object-has-translation" in domain_keys
        assert revision_counts(revision["id"]) == (4, 3)


def test_activation_from_no_active_revision():
    with TestClient(app) as client:
        workspace_key = unique_key("activate-first")
        create_workspace(client, workspace_key)
        assert workspace_active_revision_id(workspace_key) is None
        draft = create_draft(client, workspace_key, name="first").json()
        domain = _domain(client, draft, unique_key("first"))

        # Both the omitted and the explicit-null claim publish the first revision.
        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        )
        revision = response.json()
        assert revision["revisionNumber"] == 1
        assert revision["derivedFromRevisionId"] is None
        assert revision["supersedesRevisionId"] is None
        assert workspace_active_revision_id(workspace_key) == revision["id"]
        assert revision_status(revision["id"]) == "active"
        assert published_object(client, workspace_key, "domain", domain["id"]) is not None

    events = _activation_events(revision["id"])
    assert events[0].action == "activated"
    assert "supersedesRevisionId" not in events[0].changes


def test_activation_supersedes_an_active_revision_and_retires_it_in_the_same_transaction():
    with TestClient(app) as client:
        workspace_key = unique_key("supersede")
        create_workspace(client, workspace_key)
        first = publish_language_revision(client, workspace_key, unique_key("first"))
        assert revision_status(first["id"]) == "active"
        assert workspace_active_revision_id(workspace_key) == first["id"]

        draft = create_draft(
            client,
            workspace_key,
            name="supersede",
            derived_from_revision_id=first["id"],
        ).json()
        added_domain = _domain(client, draft, unique_key("supersede"))

        second = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            expected_active_revision_id=first["id"],
        ).json()
        assert second["revisionNumber"] == 2
        assert second["derivedFromRevisionId"] == first["id"]
        assert second["supersedesRevisionId"] == first["id"]
        assert workspace_active_revision_id(workspace_key) == second["id"]
        assert revision_status(second["id"]) == "active"
        assert revision_status(first["id"]) == "retired"
        assert client.get(f"/api/v1/workspace-revisions/{first['id']}").json()["retiredAt"] is not None

        # The derived draft carried the first revision's language forward and added the domain.
        assert published_object(client, workspace_key, "language", first["language"]["id"]) is not None
        assert published_object(client, workspace_key, "domain", added_domain["id"]) is not None

    events = _activation_events(second["id"])
    assert [(event.action, event.version) for event in events] == [("activated", 2)]
    assert events[0].changes["derivedFromRevisionId"] == first["id"]
    assert events[0].changes["supersedesRevisionId"] == first["id"]
    assert _subject_count([events[0].sequence_id]) == 0


# --------------------------------------------------------------------------- conflicts


def test_activation_draft_version_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("draft-version")
        create_workspace(client, workspace_key)
        baseline = publish_language_revision(client, workspace_key, unique_key("dv"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_revisions = len(workspace_revisions(workspace_key))

        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("dv"))
        stale_version = draft["version"] - 1
        expected_membership = draft_membership_counts(draft["id"])

        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=stale_version,
            expected_active_revision_id=baseline["id"],
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_draft_version_conflict"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=baseline["id"], before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], expected_membership)


def test_activation_active_revision_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("active-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_revision(client, workspace_key, unique_key("ac"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_revisions = len(workspace_revisions(workspace_key))

        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("ac"))
        expected_membership = draft_membership_counts(draft["id"])

        # Caller claims no active revision while one is active.
        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_active_revision_conflict"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=baseline["id"], before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], expected_membership)


def test_activation_model_release_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("model-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_revision(client, workspace_key, unique_key("mc"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_revisions = len(workspace_revisions(workspace_key))

        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("mc"))
        expected_membership = draft_membership_counts(draft["id"])
        twin = copy_active_model_release_as_unused()
        rewire_draft_to_release(draft["id"], twin)

        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            expected_active_revision_id=baseline["id"],
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_draft_model_release_conflict"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=baseline["id"], before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], expected_membership)


def test_activation_invalid_graph_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("graph-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_revision(client, workspace_key, unique_key("gc"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_revisions = len(workspace_revisions(workspace_key))

        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("gc"))
        inject_draft_object(draft["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost")
        expected_membership = draft_membership_counts(draft["id"])

        response = activate_draft(
            client,
            draft["id"],
            expected_draft_version=draft["version"],
            expected_active_revision_id=baseline["id"],
            expected_status=422,
        )
        body = response.json()["error"]
        assert body["code"] == "workspace_graph_invalid"
        assert "unknown_object_type" in [item["code"] for item in body["details"]]

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=baseline["id"], before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], expected_membership)


# --------------------------------------------------------------------------- no partial publication sweep


def test_no_partial_publication_after_every_failure_class():
    with TestClient(app) as client:
        workspace_key = unique_key("no-partial")
        create_workspace(client, workspace_key)
        baseline = publish_language_revision(client, workspace_key, unique_key("np"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_active = baseline["id"]
        before_revisions = len(workspace_revisions(workspace_key))

        # Draft-version conflict.
        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("np"))
        membership = draft_membership_counts(draft["id"])
        response = activate_draft(
            client, draft["id"], expected_draft_version=draft["version"] - 1,
            expected_active_revision_id=before_active, expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_draft_version_conflict"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=before_active, before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], membership)
        assert client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": draft["version"]}
        ).status_code == 204

        # Active-revision conflict.
        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("np"))
        membership = draft_membership_counts(draft["id"])
        response = activate_draft(
            client, draft["id"], expected_draft_version=draft["version"],
            explicit_null_active_revision=True, expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_active_revision_conflict"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=before_active, before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], membership)
        assert client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": draft["version"]}
        ).status_code == 204

        # Pinned-model-release conflict.
        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("np"))
        membership = draft_membership_counts(draft["id"])
        twin = copy_active_model_release_as_unused()
        rewire_draft_to_release(draft["id"], twin)
        response = activate_draft(
            client, draft["id"], expected_draft_version=draft["version"],
            expected_active_revision_id=before_active, expected_status=409,
        )
        assert response.json()["error"]["code"] == "workspace_draft_model_release_conflict"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=before_active, before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], membership)
        assert client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": draft["version"]}
        ).status_code == 204

        # Invalid effective graph.
        draft = create_draft(client, workspace_key).json()
        _domain(client, draft, unique_key("np"))
        inject_draft_object(draft["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost")
        membership = draft_membership_counts(draft["id"])
        response = activate_draft(
            client, draft["id"], expected_draft_version=draft["version"],
            expected_active_revision_id=before_active, expected_status=422,
        )
        assert response.json()["error"]["code"] == "workspace_graph_invalid"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_revision=before_active, before_revision_count=before_revisions,
        )
        _assert_draft_unchanged(client, draft["id"], draft["version"], membership)

        # The baseline remains fully readable after every failed activation.
        assert revision_status(before_active) == "active"
        assert workspace_active_revision_id(workspace_key) == before_active
        assert published_object(client, workspace_key, "language", baseline["language"]["id"]) is not None


# --------------------------------------------------------------------------- effective membership snapshots


def test_activated_revision_snapshot_preserves_stable_public_uuids_and_membership():
    with TestClient(app) as client:
        workspace_key = unique_key("stable-uuids")
        create_workspace(client, workspace_key)
        draft, graph = _build_complete_graph(client, workspace_key, unique_key("uuid"))
        with SessionLocal() as session:
            membership = effective_draft_membership(session, draft["id"])
        expected_object_ids = sorted(item.object_id for item in membership.objects)
        expected_relation_ids = sorted(item.relation_id for item in membership.relations)

        revision = activate_draft(
            client, draft["id"], expected_draft_version=draft["version"],
            explicit_null_active_revision=True,
        ).json()

        from app.models.database import WorkspaceRevisionObject, WorkspaceRevisionRelation

        with SessionLocal() as session:
            snapshot_object_ids = sorted(
                session.scalars(
                    select(WorkspaceRevisionObject.object_id).where(
                        WorkspaceRevisionObject.revision_id == revision["id"]
                    )
                )
            )
            snapshot_relation_ids = sorted(
                session.scalars(
                    select(WorkspaceRevisionRelation.relation_id).where(
                        WorkspaceRevisionRelation.revision_id == revision["id"]
                    )
                )
            )
        assert snapshot_object_ids == expected_object_ids
        assert snapshot_relation_ids == expected_relation_ids
        # Every draft object/relation id equals its published projection id (no reissued UUIDs).
        for object_type, expected in (
            ("language", graph["language"]),
            ("translation-group", graph["group"]),
            ("translation", graph["translation"]),
            ("domain", graph["domain"]),
            ("codelist", graph["codelist"]),
        ):
            assert published_object(client, workspace_key, object_type, expected["id"])["id"] == expected["id"]
