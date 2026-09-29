"""ADR-028: selected change set models, complete compatibility and atomic pin changes."""

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from wp8_support import create_change_set, create_object, create_workspace, unique_key

from app.db import SessionLocal
from app.engine.change_sets.access import effective_change_set_membership
from app.engine.model.compiler import parse_model
from app.main import app
from app.models.database import (
    AuditEvent,
    ChangeSet,
    ChangeSetBase,
    ModelRelease,
    ModelRuntimeState,
)


def install_model(client, mutate=None, *, schema=None, corrupt=False, source_model=None):
    model = copy.deepcopy(source_model or client.get("/api/v1/model").json())
    model["release"]["version"] = unique_key("wp6")
    if mutate:
        mutate(model)
    if not corrupt:
        parse_model(model)
    with SessionLocal() as session:
        release = ModelRelease(
            release_key=model["release"]["key"],
            release_name=model["release"]["name"],
            release_version=model["release"]["version"],
            schema_version=schema or model["schemaVersion"],
            model_json={} if corrupt else model,
            model_hash=hashlib.sha256(json.dumps(model).encode()).hexdigest(),
            is_active=False,
        )
        session.add(release)
        session.commit()
        return release.public_id, release.id, model


def add_field_and_view(model):
    model["attributeTypes"].append(
        {
            "key": "wp6-number",
            "name": "Next number",
            "valueType": "integer",
            "validation": {"minimum": 5},
        }
    )
    language = next(x for x in model["objectTypes"] if x["key"] == "language")
    language["attributes"].append({"attributeTypeKey": "wp6-number"})
    application = next(x for x in model["applications"] if x["key"] == "rdm-translations")
    view = next(
        x for x in application["views"] if x["objectTypeKey"] == "language" and x["type"] == "table"
    )
    view["name"] = "Next languages"
    view["config"]["columns"].append("wp6-number")


def change(client, change_set, release, version=None):
    return client.patch(
        f"/api/v1/change-sets/{change_set['id']}/model-release",
        json={"modelReleaseId": release, "expectedChangeSetVersion": version or change_set["version"]},
    )


def state(change_set_id):
    with SessionLocal() as session:
        membership = effective_change_set_membership(session, change_set_id)
        return (
            membership.change_set.model_release_id,
            membership.change_set.version,
            [(x.object_id, x.version, x.name, x.attributes) for x in membership.objects],
            [(x.relation_id, x.version, x.attributes) for x in membership.relations],
            session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.aggregate_id == change_set_id)
            ),
        )


def test_two_same_schema_change_sets_resolve_fields_rules_views_and_preserve_live_history():
    with TestClient(app) as client:
        workspace = unique_key("wp6-models")
        create_workspace(client, workspace)
        old = create_change_set(client, workspace).json()
        active_model = client.get("/api/v1/model").json()
        target, _, target_model = install_model(client, add_field_and_view)
        response = client.post(
            f"/api/v1/workspaces/{workspace}/change-sets",
            json={"source": "currentLive", "modelReleaseId": target},
        )
        assert response.status_code == 201, response.text
        new = response.json()
        assert new["modelReleaseKey"] == target_model["release"]["key"]
        assert new["modelReleaseVersion"] == target_model["release"]["version"]
        assert (
            client.get("/api/v1/model", params={"changeSetId": old["id"]}).json()
            == active_model
        )
        assert client.get(
            "/api/v1/model", params={"changeSetId": new["id"]}
        ).json() == parse_model(target_model).model_dump(mode="json")
        attrs = [
            {"attributeTypeKey": "language-code", "value": unique_key("lang")},
            {"attributeTypeKey": "wp6-number", "value": 7},
        ]
        create_object(
            client,
            old,
            "rdm-translations",
            "language",
            "Old",
            attributes=attrs,
            expected_status=422,
        )
        create_object(
            client,
            new,
            "rdm-translations",
            "language",
            "Invalid",
            attributes=[*attrs[:1], {"attributeTypeKey": "wp6-number", "value": 3}],
            expected_status=422,
        )
        record = create_object(
            client, new, "rdm-translations", "language", "Next", attributes=attrs
        ).json()
        detail = client.get(
            f"/api/v1/objects/language/{record['id']}", params={"changeSetId": new["id"]}
        )
        assert detail.status_code == 200
        assert any(
            a["attributeTypeKey"] == "wp6-number" and a["value"] == 7
            for a in detail.json()["attributes"]
        )
        assert (
            client.post(f"/api/v1/change-sets/{new['id']}/validation").json()["valid"] is True
        )
        refused = client.post(
            f"/api/v1/change-sets/{new['id']}/publication",
            json={"expectedChangeSetVersion": new["version"]},
        )
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == "change_set_model_release_conflict"
        assert client.get("/api/v1/model").json() == active_model
        assert client.get(f"/api/v1/workspaces/{workspace}/publications").json()["items"] == []
        assert (
            client.get("/api/v1/objects/language", params={"workspaceKey": workspace}).json()[
                "items"
            ]
            == []
        )
        assert (
            client.delete(
                f"/api/v1/change-sets/{new['id']}", params={"expectedVersion": new["version"]}
            ).status_code
            == 204
        )
        assert client.get(f"/api/v1/change-sets/{old['id']}").json() == old


def test_pin_change_noop_stale_claim_audit_and_other_contexts():
    with TestClient(app) as client:
        workspace = unique_key("wp6-change")
        create_workspace(client, workspace)
        other_workspace = unique_key("wp6-other")
        create_workspace(client, other_workspace)
        other = create_change_set(client, other_workspace).json()
        change_set = create_change_set(client, workspace).json()
        sibling = create_change_set(client, workspace).json()
        target, _, _ = install_model(client, add_field_and_view)
        before = state(change_set["id"])
        assert change(client, change_set, change_set["modelReleaseId"]).json() == change_set
        assert state(change_set["id"]) == before
        unknown = change(client, {**change_set, "id": str(uuid4())}, target)
        assert unknown.status_code == 404
        assert unknown.json()["error"]["code"] == "change_set_not_found"
        result = change(client, change_set, target)
        assert result.status_code == 200, result.text
        assert result.json()["version"] == change_set["version"] + 1
        after = state(change_set["id"])
        stale = change(client, change_set, target)
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "change_set_version_conflict"
        assert state(change_set["id"]) == after
        with SessionLocal() as session:
            event = session.scalar(
                select(AuditEvent).where(
                    AuditEvent.aggregate_id == change_set["id"],
                    AuditEvent.action == "model-release-changed",
                )
            )
            assert event.changes["modelRelease"]["from"]["id"] == change_set["modelReleaseId"]
            assert event.changes["modelRelease"]["to"]["id"] == target
        assert client.get(f"/api/v1/change-sets/{other['id']}").json() == other
        assert client.get(f"/api/v1/change-sets/{sibling['id']}").json() == sibling


def require_locale(model):
    language = next(x for x in model["objectTypes"] if x["key"] == "language")
    next(x for x in language["attributes"] if x["attributeTypeKey"] == "locale-code")[
        "required"
    ] = True


def test_inherited_incompatible_creation_change_and_tombstones_are_atomic():
    with TestClient(app) as client:
        workspace = unique_key("wp6-inherited")
        create_workspace(client, workspace)
        live = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Inherited",
                "attributes": [{"attributeTypeKey": "language-code", "value": unique_key("lang")}],
            },
        ).json()
        target, _, _ = install_model(client, require_locale)
        refused = client.post(
            f"/api/v1/workspaces/{workspace}/change-sets",
            json={"source": "currentLive", "modelReleaseId": target},
        )
        assert refused.status_code == 409, refused.text
        assert refused.json()["error"]["code"] == "change_set_content_incompatible"
        assert refused.json()["error"]["details"]["diagnosticCount"] > 0
        with SessionLocal() as session:
            assert (
                session.scalar(
                    select(ChangeSet.id).where(ChangeSet.workspace_key == workspace)
                )
                is None
            )
            assert (
                session.scalar(
                    select(ChangeSetBase.id).where(
                        ChangeSetBase.workspace_key == workspace
                    )
                )
                is None
            )
        change_set = create_change_set(client, workspace, source="currentLive").json()
        before = state(change_set["id"])
        refused = change(client, change_set, target)
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == "change_set_content_incompatible"
        assert state(change_set["id"]) == before
        deleted = client.delete(
            f"/api/v1/objects/language/{live['id']}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
                "expectedVersion": live["version"],
            },
        )
        assert deleted.status_code == 204, deleted.text
        change_set = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        assert change(client, change_set, target).status_code == 200
        assert (
            client.get(
                f"/api/v1/objects/language/{live['id']}", params={"workspaceKey": workspace}
            ).status_code
            == 200
        )
        with SessionLocal() as session:
            row = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set["id"]))
            base = session.get(ChangeSetBase, row.base_id)
            assert base.model_release_id != row.model_release_id
            assert (
                base.model_release_id == session.get(ModelRuntimeState, 1).active_model_release_id
            )


@pytest.mark.parametrize(
    "kind,code",
    [
        ("missing", "pinned_model_unavailable"),
        ("unsupported", "unsupported_pinned_model_schema"),
        ("corrupt", "pinned_model_invalid"),
    ],
)
def test_invalid_target_creation_and_change_preserve_state(kind, code):
    with TestClient(app) as client:
        workspace = unique_key("wp6-target")
        create_workspace(client, workspace)
        change_set = create_change_set(client, workspace).json()
        target = (
            str(uuid4())
            if kind == "missing"
            else install_model(
                client, schema="9.9" if kind == "unsupported" else None, corrupt=kind == "corrupt"
            )[0]
        )
        before = state(change_set["id"])
        for response in (
            change(client, change_set, target),
            client.post(
                f"/api/v1/workspaces/{workspace}/change-sets",
                json={"source": "currentLive", "modelReleaseId": target},
            ),
        ):
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == code
        assert state(change_set["id"]) == before
        assert len(client.get(f"/api/v1/workspaces/{workspace}/change-sets").json()["items"]) == 1


def test_overlapping_http_edit_and_pin_change_share_one_claim():
    with TestClient(app) as client:
        workspace = unique_key("wp6-race")
        create_workspace(client, workspace)
        change_set = create_change_set(client, workspace).json()
        target, _, _ = install_model(client, add_field_and_view)
        barrier = Barrier(2)

        def pin():
            barrier.wait()
            return change(client, change_set, target)

        def edit():
            barrier.wait()
            return client.post(
                "/api/v1/objects",
                json={
                    "changeSetId": change_set["id"],
                    "expectedChangeSetVersion": change_set["version"],
                    "applicationKey": "rdm-translations",
                    "objectTypeKey": "language",
                    "name": "Concurrent",
                    "attributes": [
                        {"attributeTypeKey": "language-code", "value": unique_key("race")}
                    ],
                },
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(pin), pool.submit(edit)
            responses = [a.result(), b.result()]
        assert sorted(x.status_code for x in responses) in ([200, 409], [201, 409]), [
            x.text for x in responses
        ]
        assert (
            next(x for x in responses if x.status_code == 409).json()["error"]["code"]
            == "change_set_version_conflict"
        )
        detail = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        assert detail["version"] == change_set["version"] + 1
        assert detail["modelReleaseId"] == (
            target if responses[0].status_code == 200 else change_set["modelReleaseId"]
        )


def test_historical_creation_retains_source_pin_then_explicitly_changes():
    from wp8_support import publish_language_publication

    with TestClient(app) as client:
        workspace = unique_key("wp6-history")
        create_workspace(client, workspace)
        publication = publish_language_publication(client, workspace, unique_key("history"))
        target, _, _ = install_model(client, add_field_and_view)
        payload = {"source": "publication", "derivedFromPublicationId": publication["id"]}
        refused = client.post(
            f"/api/v1/workspaces/{workspace}/change-sets", json={**payload, "modelReleaseId": target}
        )
        assert refused.status_code == 422
        created = client.post(f"/api/v1/workspaces/{workspace}/change-sets", json=payload)
        assert created.status_code == 201
        change_set = created.json()
        assert change_set["modelReleaseId"] == publication["modelReleaseId"]
        before_history = client.get(f"/api/v1/publications/{publication['id']}").json()
        result = change(client, change_set, target)
        assert result.status_code == 200, result.text
        assert state(change_set["id"])[2]
        assert client.get(f"/api/v1/publications/{publication['id']}").json() == before_history


@pytest.mark.parametrize(
    "rule,code",
    [
        ("required", "missing_required_attributes"),
        ("type", "invalid_attribute_value"),
        ("parent", "parent_required"),
        ("parentSemantics", "parent_relation_semantics_changed"),
        ("relation", "invalid_relation_pair"),
    ],
)
def test_target_constraints_check_inherited_complete_graph(rule, code):
    from wp8_support import build_complete_graph

    with TestClient(app) as client:
        workspace = unique_key("wp6-graph")
        create_workspace(client, workspace)
        seed, _ = build_complete_graph(client, workspace, unique_key("graph"))
        published = client.post(
            f"/api/v1/change-sets/{seed['id']}/publication",
            json={"expectedChangeSetVersion": seed["version"]},
        )
        assert published.status_code == 200, published.text
        change_set = create_change_set(client, workspace, source="currentLive").json()

        def mutate(model):
            if rule == "required":
                require_locale(model)
            elif rule == "type":
                next(x for x in model["attributeTypes"] if x["key"] == "language-code")[
                    "valueType"
                ] = "integer"
            elif rule == "parent":
                next(x for x in model["objectTypes"] if x["key"] == "domain")["features"][
                    "rootCreatable"
                ] = False
                # A tree rooted at domains would refuse the model first, at its own root type.
                for application in model["applications"]:
                    application["views"] = [
                        view
                        for view in application["views"]
                        if "domain" not in view.get("config", {}).get("rootObjectTypeKeys", [])
                    ]
            elif rule == "parentSemantics":
                next(x for x in model["relationTypes"] if x["key"] == "domain-contains-codelist")[
                    "features"
                ]["parentOf"] = False
            elif rule == "relation":
                model["objectTypeRelations"] = [
                    x
                    for x in model["objectTypeRelations"]
                    if not (
                        x["relationTypeKey"] == "object-has-translation"
                        and x["fromObjectTypeKey"] == "domain"
                    )
                ]

                for application in model["applications"]:
                    for detail in application["details"]:
                        if detail["objectTypeKey"] == "domain":
                            detail["panels"] = [
                                p for p in detail["panels"] if p["key"] != "translations"
                            ]

        target, _, _ = install_model(client, mutate)
        before = state(change_set["id"])
        refused = change(client, change_set, target)
        assert refused.status_code == 409, refused.text
        assert refused.json()["error"]["code"] == "change_set_content_incompatible"
        assert code in {x["code"] for x in refused.json()["error"]["details"]["diagnostics"]}
        assert state(change_set["id"]) == before
        # Creation checks the same inherited live graph and cannot leave a private base.
        refused = client.post(
            f"/api/v1/workspaces/{workspace}/change-sets",
            json={"source": "currentLive", "modelReleaseId": target},
        )
        assert refused.status_code == 409, refused.text
        assert len(client.get(f"/api/v1/workspaces/{workspace}/change-sets").json()["items"]) == 1


def test_selected_capture_keeps_active_identity_and_snapshot_retry():
    from app.engine.change_sets.lifecycle import create_change_set as create_change_set_service
    from app.errors import ApiError

    with TestClient(app) as client:
        workspace = unique_key("wp6-capture")
        create_workspace(client, workspace)
        target, target_db, _ = install_model(client, add_field_and_view)
        created = client.post(
            f"/api/v1/workspaces/{workspace}/change-sets",
            json={"source": "currentLive", "modelReleaseId": target},
        )
        assert created.status_code == 201, created.text
        with SessionLocal() as session:
            change_set = session.scalar(
                select(ChangeSet).where(ChangeSet.id == created.json()["id"])
            )
            base = session.get(ChangeSetBase, change_set.base_id)
            active = session.get(ModelRuntimeState, 1)
            assert base.model_release_id == active.active_model_release_id != target_db
            assert base.model_runtime_version == active.version
            with pytest.raises(ApiError) as error:
                create_change_set_service(
                    session,
                    workspace,
                    target_db,
                    source="currentLive",
                    expected_model_runtime_release_id=active.active_model_release_id + 100,
                    validate_selected_model=True,
                )
            assert error.value.code == "change_set_snapshot_retry"
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(ChangeSetBase)
                    .where(ChangeSetBase.workspace_key == workspace)
                )
                == 1
            )


def test_required_target_default_is_not_a_conversion_and_diagnostics_are_bounded():
    with TestClient(app) as client:
        workspace = unique_key("wp6-bounded")
        create_workspace(client, workspace)
        change_set = create_change_set(client, workspace).json()
        for index in range(21):
            create_object(
                client,
                change_set,
                "rdm-translations",
                "language",
                f"Language {index}",
                attributes=[{"attributeTypeKey": "language-code", "value": unique_key("bounded")}],
            )

        def mutate(model):
            require_locale(model)
            next(x for x in model["attributeTypes"] if x["key"] == "locale-code")["default"] = "en"

        target, _, _ = install_model(client, mutate)
        before = state(change_set["id"])
        refused = change(client, change_set, target)
        assert refused.status_code == 409, refused.text
        details = refused.json()["error"]["details"]
        assert details["diagnosticCount"] == 21
        assert len(details["diagnostics"]) == 20
        assert details["diagnosticsTruncated"] is True
        assert state(change_set["id"]) == before


def test_model_metadata_and_cursors_follow_the_pin():
    with TestClient(app) as client:
        workspace = unique_key("wp6-metadata")
        create_workspace(client, workspace)
        change_set = create_change_set(client, workspace).json()
        target, _, _ = install_model(client, add_field_and_view)
        pages = {}
        for endpoint in (
            "applications",
            "attribute-types",
            "object-types",
            "relation-types",
            "object-type-relations",
        ):
            first = client.get(
                f"/api/v1/{endpoint}", params={"changeSetId": change_set["id"], "pageSize": 1}
            )
            assert first.status_code == 200, first.text
            pages[endpoint] = first.json()["nextCursor"]
            assert pages[endpoint]
        changed = change(client, change_set, target)
        assert changed.status_code == 200
        for endpoint, cursor in pages.items():
            stale = client.get(
                f"/api/v1/{endpoint}",
                params={"changeSetId": change_set["id"], "cursor": cursor, "pageSize": 1},
            )
            assert stale.status_code == 422, stale.text
            assert stale.json()["error"]["code"] == "invalid_cursor"
        attribute = client.get(
            "/api/v1/attribute-types/wp6-number", params={"changeSetId": change_set["id"]}
        )
        assert attribute.status_code == 200, attribute.text
        assert attribute.json()["validation"]["minimum"] == 5
        application = client.get(
            "/api/v1/applications/rdm-translations", params={"changeSetId": change_set["id"]}
        )
        assert application.status_code == 200
        assert any(v["name"] == "Next languages" for v in application.json()["views"])
        assert client.get("/api/v1/attribute-types/wp6-number").status_code == 404


@pytest.mark.parametrize("source", [None, "currentLive"])
def test_valid_selected_creation_does_not_require_healthy_active_registry(source):
    from app.engine.model.registry import model_registry

    with TestClient(app) as client:
        workspace = unique_key("wp6-ready")
        create_workspace(client, workspace)
        target, _, _ = install_model(client, add_field_and_view)
        model_registry.mark_unhealthy()
        try:
            payload = {"modelReleaseId": target}
            if source:
                payload["source"] = source
            created = client.post(f"/api/v1/workspaces/{workspace}/change-sets", json=payload)
            assert created.status_code == 201, created.text
            assert created.json()["modelReleaseId"] == target
            assert (
                client.delete(
                    f"/api/v1/change-sets/{created.json()['id']}",
                    params={"expectedVersion": 1},
                ).status_code
                == 204
            )
        finally:
            model_registry.clear()


def test_uniqueness_diagnostic_nested_identity_previews_are_bounded():
    with TestClient(app) as client:
        workspace = unique_key("wp6-unique")
        create_workspace(client, workspace)
        change_set = create_change_set(client, workspace).json()
        for index in range(22):
            create_object(
                client,
                change_set,
                "rdm-translations",
                "language",
                f"Duplicate {index}",
                attributes=[
                    {"attributeTypeKey": "language-code", "value": unique_key("unique")},
                    {"attributeTypeKey": "locale-code", "value": "same"},
                ],
            )

        def mutate(model):
            next(x for x in model["attributeTypes"] if x["key"] == "locale-code")["features"][
                "unique"
            ] = True

        target, _, _ = install_model(client, mutate)
        refused = change(client, change_set, target)
        assert refused.status_code == 409, refused.text
        diagnostics = refused.json()["error"]["details"]["diagnostics"]
        assert len(diagnostics) == 20
        for diagnostic in diagnostics:
            details = diagnostic["details"]
            assert len(details["conflictingObjectIds"]) == 20
            assert details["conflictingObjectCount"] == 21
            assert details["conflictingObjectsTruncated"] is True


def test_inherited_object_and_relation_declared_type_changes_require_conversion():
    from app.models.database import (
        Publication,
        PublicationObject,
        PublicationRelation,
    )

    with TestClient(app) as client:
        workspace = unique_key("wp6-types")
        create_workspace(client, workspace)

        def add_measure(model):
            model["attributeTypes"].append(
                {"key": "wp6-measure", "name": "Measure", "valueType": "text"}
            )
            next(x for x in model["objectTypes"] if x["key"] == "language")["attributes"].append(
                {"attributeTypeKey": "wp6-measure"}
            )
            model["relationTypes"].append(
                {
                    "key": "wp6-links",
                    "reverseKey": "wp6-linked-by",
                    "name": "Links",
                    "reverseName": "Linked by",
                }
            )
            model["objectTypeRelations"].append(
                {
                    "relationTypeKey": "wp6-links",
                    "fromObjectTypeKey": "language",
                    "toObjectTypeKey": "domain",
                    "cardinality": "many-to-many",
                    "attributeTypeKeys": ["wp6-measure"],
                }
            )

        source, source_db, source_model = install_model(client, add_measure)
        publication_id, language_id, domain_id, relation_id = [str(uuid4()) for _ in range(4)]
        # A valid immutable source fixture includes values whose target decimal normalizer accepts
        # their strings. The compatibility rule must still refuse changing their declared type.
        with SessionLocal() as session:
            session.add(
                Publication(
                    id=publication_id,
                    workspace_key=workspace,
                    model_release_id=source_db,
                    publication_number=1,
                    status="withdrawn",
                )
            )
            session.flush()
            session.add_all(
                [
                    PublicationObject(
                        publication_id=publication_id,
                        object_id=language_id,
                        application_key="rdm-translations",
                        object_type_key="language",
                        name="Language",
                        attributes={"language-code": unique_key("measure"), "wp6-measure": "12"},
                        version=1,
                    ),
                    PublicationObject(
                        publication_id=publication_id,
                        object_id=domain_id,
                        application_key="rdm-master",
                        object_type_key="domain",
                        name="Domain",
                        attributes={"domain-code": unique_key("measure")},
                        version=1,
                    ),
                    PublicationRelation(
                        publication_id=publication_id,
                        relation_id=relation_id,
                        relation_type_key="wp6-links",
                        from_object_id=language_id,
                        to_object_id=domain_id,
                        attributes={"wp6-measure": "13"},
                        version=1,
                    ),
                ]
            )
            session.commit()
        change_set = create_change_set(client, workspace, derived_from_publication_id=publication_id).json()
        assert change_set["modelReleaseId"] == source

        def change_type(model):
            next(x for x in model["attributeTypes"] if x["key"] == "wp6-measure")["valueType"] = (
                "decimal"
            )

        target, _, _ = install_model(client, change_type, source_model=source_model)
        before = state(change_set["id"])
        refused = change(client, change_set, target)
        assert refused.status_code == 409, refused.text
        codes = {x["code"] for x in refused.json()["error"]["details"]["diagnostics"]}
        assert {"attribute_value_type_changed", "relation_attribute_value_type_changed"} <= codes
        assert state(change_set["id"]) == before
