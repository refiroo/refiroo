"""WP8 package-3 tests: atomic change-set activation.

These cover the single-transaction publication of a complete effective graph: the active-publication
pointer switch, active projection rebuild, immutable publication creation with stable public UUIDs,
derived-from/supersedes lineage, and the distinct concurrency/model-release/graph conflict classes.
Every conflict test asserts that nothing publishes -- active pointer and projection unchanged, no new
publication row, and the change set still present with unchanged version and content.  Activation audit is
verified directly against :class:`AuditEvent` because ``publication`` events carry no
``AuditEventSubject`` rows.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from wp8_support import (
    attribute,
    change_set_membership_counts,
    change_sets,
    copy_active_model_release_as_unused,
    create_change_set,
    create_object,
    create_workspace,
    inject_change_set_object,
    publication_counts,
    publication_status,
    publish_change_set,
    publish_language_publication,
    published_graph_snapshot,
    published_object,
    published_relations,
    rewire_change_set_to_release,
    unique_key,
    workspace_active_publication_id,
)

from app.db import SessionLocal
from app.engine.change_sets.access import effective_change_set_membership
from app.main import app
from app.models.database import AuditEvent, AuditEventSubject


def _translation_relation(target_id: str) -> list[dict]:
    return [
        {
            "relationTypeKey": "object-has-translation",
            "direction": "incoming",
            "otherObjectId": target_id,
        }
    ]


def _domain(client, change_set, suffix: str) -> dict:
    return create_object(
        client,
        change_set,
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
    change_set = create_change_set(client, workspace_key, name=f"graph {suffix}").json()
    language = create_object(
        client,
        change_set,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()
    group = create_object(
        client,
        change_set,
        "rdm-translations",
        "translation-group",
        f"Group {suffix}",
        attributes=[attribute("group-code", f"grp-{suffix}-{uuid4().hex[:8]}")],
        parent_object_id=language["id"],
    ).json()
    domain = _domain(client, change_set, unique_key(suffix))
    codelist = create_object(
        client,
        change_set,
        "rdm-master",
        "codelist",
        f"Codelist {suffix}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain["id"],
    ).json()
    translation = create_object(
        client,
        change_set,
        "rdm-translations",
        "translation",
        f"Translation {suffix}",
        attributes=[attribute("translated-value", f"tv-{uuid4().hex[:8]}")],
        parent_object_id=group["id"],
        initial_relations=_translation_relation(domain["id"]),
    ).json()
    return change_set, {
        "language": language,
        "group": group,
        "domain": domain,
        "codelist": codelist,
        "translation": translation,
    }


def _publish_events(publication_id: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "publication",
                    AuditEvent.aggregate_id == publication_id,
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


def _assert_change_set_unchanged(client, change_set_id: str, expected_version: int, expected_membership: tuple[int, int]) -> None:
    detail = client.get(f"/api/v1/change-sets/{change_set_id}")
    assert detail.status_code == 200
    assert detail.json()["version"] == expected_version
    assert change_set_membership_counts(change_set_id) == expected_membership


def _assert_publication_state_unchanged(
    client,
    workspace_key: str,
    *,
    before_snapshot: str,
    before_active_publication: str | None,
    before_publication_count: int,
) -> None:
    assert published_graph_snapshot(client, workspace_key) == before_snapshot
    assert workspace_active_publication_id(workspace_key) == before_active_publication
    assert len(change_sets(workspace_key)) == before_publication_count


# --------------------------------------------------------------------------- success


def test_successful_publish_publishes_complete_graph_and_records_publish_audit():
    with TestClient(app) as client:
        workspace_key = unique_key("activate-ok")
        create_workspace(client, workspace_key)
        change_set, graph = _build_complete_graph(client, workspace_key, unique_key("ok"))

        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        )
        publication = response.json()
        assert publication["status"] == "active"
        assert publication["derivedFromPublicationId"] is None
        assert publication["supersedesPublicationId"] is None
        assert publication["publicationNumber"] == 1
        assert workspace_active_publication_id(workspace_key) == publication["id"]
        assert publication_status(publication["id"]) == "active"
        assert publication_counts(publication["id"]) == (5, 4)

        # The mutable change set is closed only after publication succeeds.
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 404

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

    # Activation identity audit is recorded on the publication aggregate, same transaction.
    events = _publish_events(publication["id"])
    assert [(event.action, event.version) for event in events] == [("published", 1)]
    changes = events[0].changes
    assert changes["changeSetId"] == change_set["id"]
    assert changes["workspaceKey"] == workspace_key
    assert changes["modelReleaseId"] == publication["modelReleaseId"]
    assert changes["objectCount"] == 5
    assert changes["relationCount"] == 4
    assert "derivedFromPublicationId" not in changes
    assert "supersedesPublicationId" not in changes
    assert _subject_count([events[0].sequence_id]) == 0


def test_atomic_translation_publication():
    with TestClient(app) as client:
        workspace_key = unique_key("translation-pub")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key, name="translations").json()
        domain = _domain(client, change_set, unique_key("tpub"))
        language = create_object(
            client,
            change_set,
            "rdm-translations",
            "language",
            "Translation language",
            attributes=[attribute("language-code", f"lang-{uuid4().hex[:8]}")],
        ).json()
        group = create_object(
            client,
            change_set,
            "rdm-translations",
            "translation-group",
            "Translation group",
            attributes=[attribute("group-code", f"grp-{uuid4().hex[:8]}")],
            parent_object_id=language["id"],
        ).json()
        translation = create_object(
            client,
            change_set,
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

        publication = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()

        # The translation records publish atomically with their cross-application owner graph.
        assert published_object(client, workspace_key, "translation", translation["id"])["version"] == translation["version"]
        assert published_object(client, workspace_key, "translation-group", group["id"])["parentObjectId"] == language["id"]
        assert published_object(client, workspace_key, "domain", domain["id"])["id"] == domain["id"]
        domain_keys = _relation_type_keys(client, workspace_key, domain["id"])
        assert "object-has-translation" in domain_keys
        assert publication_counts(publication["id"]) == (4, 3)


def test_publish_from_no_active_publication():
    with TestClient(app) as client:
        workspace_key = unique_key("activate-first")
        create_workspace(client, workspace_key)
        assert workspace_active_publication_id(workspace_key) is None
        change_set = create_change_set(client, workspace_key, name="first").json()
        domain = _domain(client, change_set, unique_key("first"))

        # Both the omitted and the explicit-null claim publish the first publication.
        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        )
        publication = response.json()
        assert publication["publicationNumber"] == 1
        assert publication["derivedFromPublicationId"] is None
        assert publication["supersedesPublicationId"] is None
        assert workspace_active_publication_id(workspace_key) == publication["id"]
        assert publication_status(publication["id"]) == "active"
        assert published_object(client, workspace_key, "domain", domain["id"]) is not None

    events = _publish_events(publication["id"])
    assert events[0].action == "published"
    assert "supersedesPublicationId" not in events[0].changes


def test_publish_supersedes_an_active_publication_and_retires_it_in_the_same_transaction():
    with TestClient(app) as client:
        workspace_key = unique_key("supersede")
        create_workspace(client, workspace_key)
        first = publish_language_publication(client, workspace_key, unique_key("first"))
        assert publication_status(first["id"]) == "active"
        assert workspace_active_publication_id(workspace_key) == first["id"]

        change_set = create_change_set(
            client,
            workspace_key,
            name="supersede",
            derived_from_publication_id=first["id"],
        ).json()
        added_domain = _domain(client, change_set, unique_key("supersede"))

        second = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_active_publication_id=first["id"],
        ).json()
        assert second["publicationNumber"] == 2
        assert second["derivedFromPublicationId"] == first["id"]
        assert second["supersedesPublicationId"] == first["id"]
        assert workspace_active_publication_id(workspace_key) == second["id"]
        assert publication_status(second["id"]) == "active"
        assert publication_status(first["id"]) == "withdrawn"
        assert client.get(f"/api/v1/publications/{first['id']}").json()["withdrawnAt"] is not None

        # The derived change set carried the first publication's language forward and added the domain.
        assert published_object(client, workspace_key, "language", first["language"]["id"]) is not None
        assert published_object(client, workspace_key, "domain", added_domain["id"]) is not None

    events = _publish_events(second["id"])
    assert [(event.action, event.version) for event in events] == [("published", 2)]
    assert events[0].changes["derivedFromPublicationId"] == first["id"]
    assert events[0].changes["supersedesPublicationId"] == first["id"]
    assert _subject_count([events[0].sequence_id]) == 0


# --------------------------------------------------------------------------- conflicts


def test_publish_change_set_version_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("change-set-version")
        create_workspace(client, workspace_key)
        baseline = publish_language_publication(client, workspace_key, unique_key("dv"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_publications = len(change_sets(workspace_key))

        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("dv"))
        stale_version = change_set["version"] - 1
        expected_membership = change_set_membership_counts(change_set["id"])

        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=stale_version,
            expected_active_publication_id=baseline["id"],
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "CHANGE_SET_VERSION_CONFLICT"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=baseline["id"], before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], expected_membership)


def test_publish_active_publication_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("active-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_publication(client, workspace_key, unique_key("ac"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_publications = len(change_sets(workspace_key))

        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("ac"))
        expected_membership = change_set_membership_counts(change_set["id"])

        # Caller claims no active publication while one is active.
        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=baseline["id"], before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], expected_membership)


def test_publish_model_release_conflict_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("model-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_publication(client, workspace_key, unique_key("mc"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_publications = len(change_sets(workspace_key))

        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("mc"))
        expected_membership = change_set_membership_counts(change_set["id"])
        twin = copy_active_model_release_as_unused()
        rewire_change_set_to_release(change_set["id"], twin)

        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_active_publication_id=baseline["id"],
            expected_status=409,
        )
        assert response.json()["error"]["code"] == "CHANGE_SET_MODEL_RELEASE_CONFLICT"

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=baseline["id"], before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], expected_membership)


def test_publish_invalid_graph_publishes_nothing():
    with TestClient(app) as client:
        workspace_key = unique_key("graph-conflict")
        create_workspace(client, workspace_key)
        baseline = publish_language_publication(client, workspace_key, unique_key("gc"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_publications = len(change_sets(workspace_key))

        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("gc"))
        inject_change_set_object(change_set["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost")
        expected_membership = change_set_membership_counts(change_set["id"])

        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_active_publication_id=baseline["id"],
            expected_status=422,
        )
        body = response.json()["error"]
        assert body["code"] == "WORKSPACE_GRAPH_INVALID"
        assert "UNKNOWN_OBJECT_TYPE" in [item["code"] for item in body["details"]]

        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=baseline["id"], before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], expected_membership)


# --------------------------------------------------------------------------- no partial publication sweep


def test_no_partial_publication_after_every_failure_class():
    with TestClient(app) as client:
        workspace_key = unique_key("no-partial")
        create_workspace(client, workspace_key)
        baseline = publish_language_publication(client, workspace_key, unique_key("np"))
        before_snapshot = published_graph_snapshot(client, workspace_key)
        before_active = baseline["id"]
        before_publications = len(change_sets(workspace_key))

        # Change set-version conflict.
        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("np"))
        membership = change_set_membership_counts(change_set["id"])
        response = publish_change_set(
            client, change_set["id"], expected_change_set_version=change_set["version"] - 1,
            expected_active_publication_id=before_active, expected_status=409,
        )
        assert response.json()["error"]["code"] == "CHANGE_SET_VERSION_CONFLICT"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=before_active, before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], membership)
        assert client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": change_set["version"]}
        ).status_code == 204

        # Active-publication conflict.
        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("np"))
        membership = change_set_membership_counts(change_set["id"])
        response = publish_change_set(
            client, change_set["id"], expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True, expected_status=409,
        )
        assert response.json()["error"]["code"] == "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=before_active, before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], membership)
        assert client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": change_set["version"]}
        ).status_code == 204

        # Pinned-model-release conflict.
        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("np"))
        membership = change_set_membership_counts(change_set["id"])
        twin = copy_active_model_release_as_unused()
        rewire_change_set_to_release(change_set["id"], twin)
        response = publish_change_set(
            client, change_set["id"], expected_change_set_version=change_set["version"],
            expected_active_publication_id=before_active, expected_status=409,
        )
        assert response.json()["error"]["code"] == "CHANGE_SET_MODEL_RELEASE_CONFLICT"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=before_active, before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], membership)
        assert client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": change_set["version"]}
        ).status_code == 204

        # Invalid effective graph.
        change_set = create_change_set(client, workspace_key).json()
        _domain(client, change_set, unique_key("np"))
        inject_change_set_object(change_set["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost")
        membership = change_set_membership_counts(change_set["id"])
        response = publish_change_set(
            client, change_set["id"], expected_change_set_version=change_set["version"],
            expected_active_publication_id=before_active, expected_status=422,
        )
        assert response.json()["error"]["code"] == "WORKSPACE_GRAPH_INVALID"
        _assert_publication_state_unchanged(
            client, workspace_key, before_snapshot=before_snapshot,
            before_active_publication=before_active, before_publication_count=before_publications,
        )
        _assert_change_set_unchanged(client, change_set["id"], change_set["version"], membership)

        # The baseline remains fully readable after every failed activation.
        assert publication_status(before_active) == "active"
        assert workspace_active_publication_id(workspace_key) == before_active
        assert published_object(client, workspace_key, "language", baseline["language"]["id"]) is not None


# --------------------------------------------------------------------------- effective membership snapshots


def test_activated_publication_snapshot_preserves_stable_public_uuids_and_membership():
    with TestClient(app) as client:
        workspace_key = unique_key("stable-uuids")
        create_workspace(client, workspace_key)
        change_set, graph = _build_complete_graph(client, workspace_key, unique_key("uuid"))
        with SessionLocal() as session:
            membership = effective_change_set_membership(session, change_set["id"])
        expected_object_ids = sorted(item.object_id for item in membership.objects)
        expected_relation_ids = sorted(item.relation_id for item in membership.relations)

        publication = publish_change_set(
            client, change_set["id"], expected_change_set_version=change_set["version"],
            explicit_null_active_publication=True,
        ).json()

        from app.models.database import PublicationObject, PublicationRelation

        with SessionLocal() as session:
            snapshot_object_ids = sorted(
                session.scalars(
                    select(PublicationObject.object_id).where(
                        PublicationObject.publication_id == publication["id"]
                    )
                )
            )
            snapshot_relation_ids = sorted(
                session.scalars(
                    select(PublicationRelation.relation_id).where(
                        PublicationRelation.publication_id == publication["id"]
                    )
                )
            )
        assert snapshot_object_ids == expected_object_ids
        assert snapshot_relation_ids == expected_relation_ids
        # Every change set object/relation id equals its published projection id (no reissued UUIDs).
        for object_type, expected in (
            ("language", graph["language"]),
            ("translation-group", graph["group"]),
            ("translation", graph["translation"]),
            ("domain", graph["domain"]),
            ("codelist", graph["codelist"]),
        ):
            assert published_object(client, workspace_key, object_type, expected["id"])["id"] == expected["id"]
