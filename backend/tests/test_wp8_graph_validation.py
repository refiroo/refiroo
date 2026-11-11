"""WP8 package-2 tests: whole-graph validation.

These exercise ``POST /api/v1/change-sets/{change_set_id}/validation`` over the effective workspace
change set.  The suite builds change sets through the canonical generic CRUD routers and injects only the graph
states the CRUD write path legitimately refuses to persist (orphan translations, duplicate scoped
translations, cardinality and containment violations, unknown types/applications, identity
collisions).  Each category asserts a structured, path-addressable diagnostic whose shape matches the
public ``ChangeSetValidation.diagnostics`` payload.
"""

from uuid import uuid4

from harness_identity import TestClient
from sqlalchemy import func, select
from wp8_support import (
    attribute,
    change_set_membership_counts,
    copy_active_model_release_as_unused,
    create_change_set,
    create_object,
    create_workspace,
    delete_change_set_relation,
    diagnostic_codes,
    inject_change_set_object,
    inject_change_set_relation,
    publish_change_set,
    publish_language_publication,
    rewire_change_set_to_release,
    unique_key,
    update_object,
    validate_change_set,
)

from app.db import SessionLocal
from app.engine.change_sets.access import effective_change_set_membership
from app.main import app
from app.models.database import AuditEvent, AuditEventSubject, ChangeSetObject


def _translation_relation(target_id: str) -> list[dict]:
    return [
        {
            "relationTypeKey": "object-has-translation",
            "direction": "incoming",
            "otherObjectId": target_id,
        }
    ]


def _language_group(client, change_set, suffix: str) -> tuple[dict, dict]:
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
    return language, group


def _domain(client, change_set, suffix: str) -> dict:
    return create_object(
        client,
        change_set,
        "rdm-master",
        "domain",
        f"Domain {suffix}",
        attributes=[attribute("domain-code", f"dom-{suffix}-{uuid4().hex[:8]}")],
    ).json()


def _build_complete_valid_graph(client, workspace_key: str) -> tuple[dict, list[dict], list[dict]]:
    """Language -> group containment, domain -> codelist containment, and one translation.

    The graph contains every validation category that must pass: multiple object types, typed
    required attributes, containment parent/child edges, an independent required ownership relation
    (``object-has-translation``) and a valid translation object.
    """
    change_set = create_change_set(client, workspace_key, name="valid graph").json()
    language, group = _language_group(client, change_set, unique_key("vg"))
    domain = _domain(client, change_set, unique_key("vg"))
    codelist = create_object(
        client,
        change_set,
        "rdm-master",
        "codelist",
        f"Codelist {unique_key('vg')}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain["id"],
    ).json()
    translation = create_object(
        client,
        change_set,
        "rdm-translations",
        "translation",
        f"Translation {unique_key('vg')}",
        attributes=[attribute("translated-value", f"Translated {uuid4().hex[:8]}")],
        parent_object_id=group["id"],
        initial_relations=_translation_relation(domain["id"]),
    ).json()
    objects = [language, group, domain, codelist, translation]
    return change_set, objects, [language, group, domain, codelist, translation]


def _change_set_events(change_set_id: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "change-set",
                    AuditEvent.aggregate_id == change_set_id,
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


def _assert_validation_audit(
    change_set_id: str, *, valid: bool, error_codes: list[str]
) -> AuditEvent:
    events = _change_set_events(change_set_id)
    assert events[-1].action == "validated"
    event = events[-1]
    # The route records effective membership counts (immutable base plus change set overrides), which for
    # a derived change set can exceed the raw change set row count.
    with SessionLocal() as session:
        membership = effective_change_set_membership(session, change_set_id)
    object_count, relation_count = len(membership.objects), len(membership.relations)
    assert event.changes == {
        "valid": valid,
        "errorCodes": sorted(set(error_codes)),
        "objectCount": object_count,
        "relationCount": relation_count,
        "errorCount": len(error_codes),
    }
    assert _subject_count([event.sequence_id]) == 0
    return event


def _diag_by_code(result: dict, code: str) -> dict:
    matches = [item for item in result["diagnostics"] if item["code"] == code]
    assert matches, f"Expected diagnostic {code!r} in {result['diagnostics']!r}"
    return matches[0]


# --------------------------------------------------------------------------- valid graph


def test_complete_valid_graph_validates_and_records_bounded_audit():
    with TestClient(app) as client:
        workspace_key = unique_key("valid")
        create_workspace(client, workspace_key)
        change_set, _objects, _unused = _build_complete_valid_graph(client, workspace_key)

        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is True
        assert result["diagnostics"] == []

        detail = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        assert detail["version"] == change_set["version"]

        event = _assert_validation_audit(change_set["id"], valid=True, error_codes=[])
        assert event.version == change_set["version"]
        assert event.aggregate_type == "change-set"


# ------------------------------------------------------------------------- object membership


def test_unknown_object_type_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("unknowntype")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        inject_change_set_object(
            change_set["id"], str(uuid4()), "rdm-translations", "not-a-real-type", "Ghost"
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "UNKNOWN_OBJECT_TYPE")
        assert "message" in diagnostic and "objectId" in diagnostic["details"]


def test_object_type_not_enabled_in_application_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("appmembership")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        # domain exists in the model but is not enabled in the rdm-translations application.
        inject_change_set_object(
            change_set["id"],
            str(uuid4()),
            "rdm-translations",
            "domain",
            "Wrong app domain",
            attributes={"domain-code": f"wrong-app-{uuid4().hex[:8]}"},
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "OBJECT_TYPE_NOT_IN_APPLICATION")
        assert diagnostic["details"]["objectId"]


# --------------------------------------------------------------------------- attributes


def test_missing_required_attribute_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("missingattr")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        inject_change_set_object(
            change_set["id"],
            str(uuid4()),
            "rdm-master",
            "domain",
            "No code",
            attributes={"active": True},
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "MISSING_REQUIRED_ATTRIBUTES")
        assert diagnostic["details"]["objectId"]
        assert diagnostic["details"]["attributeTypeKeys"] == ["domain-code"]
        assert diagnostic["message"] == "Required fields are missing: Domain code"


def test_attribute_bounds_violation_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("bounds")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        domain = _domain(client, change_set, unique_key("bounds"))
        codelist_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            codelist_id,
            "rdm-master",
            "codelist",
            "Deep codelist",
            parent_object_id=domain["id"],
            attributes={"codelist-code": f"cl-{uuid4().hex[:8]}", "maximum-hierarchy-depth": 0},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "domain-contains-codelist",
            domain["id"],
            codelist_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "ATTRIBUTE_BELOW_MINIMUM")
        assert diagnostic["details"]["objectId"] == codelist_id


def test_unique_attribute_collision_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("duplicateattr")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        code = f"dom-{uuid4().hex[:8]}"
        first = _domain(client, change_set, unique_key("dup"))
        create_object(
            client,
            change_set,
            "rdm-master",
            "domain",
            "First dup",
            attributes=[attribute("domain-code", code)],
        )
        inject_change_set_object(
            change_set["id"],
            str(uuid4()),
            "rdm-master",
            "domain",
            "Second dup",
            attributes={"domain-code": code},
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "DUPLICATE_ATTRIBUTE_VALUE")
        assert diagnostic["details"]["attributeTypeKey"] == "domain-code"
        assert first["id"] not in diagnostic["details"]["conflictingObjectIds"]


# --------------------------------------------------------------------------- containment


def test_containment_cycle_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("cycle")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        language, first_group = _language_group(client, change_set, unique_key("cycle"))
        assert language
        second_group = create_object(
            client,
            change_set,
            "rdm-translations",
            "translation-group",
            "Second group",
            attributes=[attribute("group-code", f"g2-{uuid4().hex[:8]}")],
            parent_object_id=first_group["id"],
        ).json()
        # The API must reject the cycle before writing it.
        rejected = update_object(
            client,
            change_set,
            "translation-group",
            first_group["id"],
            payload={"parentObjectId": second_group["id"], "expectedVersion": 1},
            expected_status=422,
        )
        assert rejected.json()["error"]["code"] == "PARENT_CYCLE"
        # Exercise validation of invalid persisted/imported content independently of that guard.
        with SessionLocal() as session:
            row = session.scalar(
                select(ChangeSetObject).where(
                    ChangeSetObject.change_set_id == change_set["id"],
                    ChangeSetObject.object_id == first_group["id"],
                )
            )
            row.parent_object_id = second_group["id"]
            session.commit()
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "CONTAINMENT_CYCLE" in diagnostic_codes(result)


def test_missing_containment_relation_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("parentrel")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        domain = _domain(client, change_set, unique_key("parentrel"))
        codelist = create_object(
            client,
            change_set,
            "rdm-master",
            "codelist",
            "Codelist",
            attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
            parent_object_id=domain["id"],
        ).json()
        delete_change_set_relation(
            change_set["id"],
            relation_type_key="domain-contains-codelist",
            to_object_id=codelist["id"],
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "CONTAINMENT_RELATION_MISSING")
        assert diagnostic["details"]["objectId"] == codelist["id"]
        assert diagnostic["details"]["parentObjectId"] == domain["id"]


# --------------------------------------------------------------------------- required ownership


def test_translation_target_requirement_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("orphantrans")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("orphan"))
        translation_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            translation_id,
            "rdm-translations",
            "translation",
            "Orphan translation",
            parent_object_id=group["id"],
            attributes={"translated-value": "No target"},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "translation-group-contains-translation",
            group["id"],
            translation_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "MISSING_REQUIRED_RELATION")
        assert diagnostic["details"]["objectId"] == translation_id
        assert diagnostic["details"]["relationTypeKey"] == "object-has-translation"


# --------------------------------------------------------------------------- relations


def test_relation_endpoint_missing_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("endpoint")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        language, _group = _language_group(client, change_set, unique_key("endpoint"))
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "language-contains-group",
            str(uuid4()),
            language["id"],
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "RELATION_ENDPOINT_MISSING" in diagnostic_codes(result)


def test_invalid_relation_pair_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("invalidpair")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        domain = _domain(client, change_set, unique_key("invalidpair"))
        _language, group = _language_group(client, change_set, unique_key("invalidpair"))
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "no-such-relation-type",
            domain["id"],
            group["id"],
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "INVALID_RELATION_PAIR" in diagnostic_codes(result)


def test_relation_cardinality_violation_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("cardinality")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("card"))
        first_domain = _domain(client, change_set, unique_key("card"))
        second_domain = _domain(client, change_set, unique_key("card"))
        translation = create_object(
            client,
            change_set,
            "rdm-translations",
            "translation",
            "Shared translation",
            attributes=[attribute("translated-value", f"tv-{uuid4().hex[:8]}")],
            parent_object_id=group["id"],
            initial_relations=_translation_relation(first_domain["id"]),
        ).json()
        # A translation is one-to-many on its target side: a second owner exceeds cardinality.
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "object-has-translation",
            second_domain["id"],
            translation["id"],
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "RELATION_CARDINALITY_VIOLATION" in diagnostic_codes(result)


def test_relation_attribute_error_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("relationattr")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        domain = _domain(client, change_set, unique_key("relattr"))
        system = create_object(
            client,
            change_set,
            "rdm-systems",
            "system",
            "System",
            attributes=[attribute("system-code", f"sys-{uuid4().hex[:8]}")],
        ).json()
        system_value = create_object(
            client,
            change_set,
            "rdm-systems",
            "system-value",
            "System value",
            attributes=[
                attribute("value-code", f"svc-{uuid4().hex[:8]}"),
                attribute("value-name", "System value"),
            ],
            parent_object_id=system["id"],
        ).json()
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "reference-has-system-representation",
            domain["id"],
            system_value["id"],
            attributes={"not-a-relation-attribute": True},
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "UNKNOWN_RELATION_ATTRIBUTES" in diagnostic_codes(result)


# --------------------------------------------------------------------------- translation rules


def test_translation_content_requirement_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("content")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("content"))
        domain = _domain(client, change_set, unique_key("content"))
        translation_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            translation_id,
            "rdm-translations",
            "translation",
            "Empty translation",
            parent_object_id=group["id"],
            attributes={},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "translation-group-contains-translation",
            group["id"],
            translation_id,
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "object-has-translation",
            domain["id"],
            translation_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "OBJECT_ATTRIBUTE_RULE_VIOLATION" in diagnostic_codes(result)


def test_translation_invalid_target_relation_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("invalidtarget")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("invalidtarget"))
        translation_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            translation_id,
            "rdm-translations",
            "translation",
            "Badly targeted translation",
            parent_object_id=group["id"],
            attributes={"translated-value": "Targets a language"},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "translation-group-contains-translation",
            group["id"],
            translation_id,
        )
        # A language is not an allowed target owner for object-has-translation.
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "object-has-translation",
            _language["id"],
            translation_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "INVALID_RELATION_PAIR" in diagnostic_codes(result)
        assert "MISSING_REQUIRED_RELATION" in diagnostic_codes(result)


def test_duplicate_translation_language_target_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("languagetarget")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("langtgt"))
        domain = _domain(client, change_set, unique_key("langtgt"))
        first = create_object(
            client,
            change_set,
            "rdm-translations",
            "translation",
            "First translation",
            attributes=[attribute("translated-value", f"first-{uuid4().hex[:8]}")],
            parent_object_id=group["id"],
            initial_relations=_translation_relation(domain["id"]),
        ).json()
        second_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            second_id,
            "rdm-translations",
            "translation",
            "Second translation",
            parent_object_id=group["id"],
            attributes={"translated-value": f"second-{uuid4().hex[:8]}"},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "translation-group-contains-translation",
            group["id"],
            second_id,
        )
        # Same owning domain, same language ancestor, both active: language/target duplicate.
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "object-has-translation",
            domain["id"],
            second_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "DUPLICATE_RELATION_SCOPE")
        assert diagnostic["details"]["objectId"] == domain["id"]
        assert first["id"] not in (
            diagnostic["details"]["relationId"],
            diagnostic["details"]["conflictingRelationId"],
        )


# --------------------------------------------------------------------------- identity collision


def test_object_and_relation_identity_collision_is_a_graph_diagnostic():
    with TestClient(app) as client:
        workspace_key = unique_key("idcollision")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        _language, group = _language_group(client, change_set, unique_key("idcoll"))
        domain = _domain(client, change_set, unique_key("idcoll"))
        shared_id = str(uuid4())
        inject_change_set_object(
            change_set["id"],
            shared_id,
            "rdm-translations",
            "translation",
            "Shared identity translation",
            parent_object_id=group["id"],
            attributes={"translated-value": "tv"},
        )
        inject_change_set_relation(
            change_set["id"],
            str(uuid4()),
            "translation-group-contains-translation",
            group["id"],
            shared_id,
        )
        inject_change_set_relation(
            change_set["id"],
            shared_id,
            "object-has-translation",
            domain["id"],
            shared_id,
        )
        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        diagnostic = _diag_by_code(result, "IDENTITY_COLLISION")
        assert diagnostic["details"]["id"] == shared_id


# --------------------------------------------------------------------------- pinned model release


def test_non_active_pin_validates_its_graph_without_activation_agreement():
    with TestClient(app) as client:
        workspace_key = unique_key("modelconflict")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key, name="release pinned").json()
        twin = copy_active_model_release_as_unused()
        rewire_change_set_to_release(change_set["id"], twin)

        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is True
        assert result["diagnostics"] == []

        detail = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        assert detail["version"] == change_set["version"]


# --------------------------------------------------------------------------- side-effect-free failure


def test_failed_validation_is_side_effect_free_on_change_set_and_published_reads():
    with TestClient(app) as client:
        workspace_key = unique_key("sideeffect")
        create_workspace(client, workspace_key)
        published = publish_language_publication(client, workspace_key, unique_key("pub"))

        change_set = create_change_set(
            client,
            workspace_key,
            name="failing change set",
            derived_from_publication_id=published["id"],
        ).json()
        # The derived change set is unchanged at first; corrupt it with a graph-invalid injected object.
        before_detail = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        inject_change_set_object(
            change_set["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost"
        )
        before_objects, before_relations = change_set_membership_counts(change_set["id"])

        result = validate_change_set(client, change_set["id"])
        assert result["valid"] is False
        assert "UNKNOWN_OBJECT_TYPE" in diagnostic_codes(result)

        after_detail = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
        assert after_detail["version"] == before_detail["version"]
        after_objects, after_relations = change_set_membership_counts(change_set["id"])
        assert (after_objects, after_relations) == (before_objects, before_relations)

        # Published reads remain untouched.
        language_id = published["language"]["id"]
        published_read = client.get(
            f"/api/v1/objects/language/{language_id}", params={"workspaceKey": workspace_key}
        ).json()
        assert published_read["version"] == published["language"]["version"]
        assert published_read["name"] == published["language"]["name"]
        assert client.get(f"/api/v1/publications/{published['id']}").json()["status"] == "active"

        # The only side effect is the bounded validation audit event.
        event = _assert_validation_audit(
            change_set["id"], valid=False, error_codes=["UNKNOWN_OBJECT_TYPE"]
        )
        assert event.version == before_detail["version"]


# --------------------------------------------------------------------------- activation precondition


def test_activation_rejects_an_invalid_graph_without_publishing():
    with TestClient(app) as client:
        workspace_key = unique_key("activereject")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key).json()
        inject_change_set_object(
            change_set["id"], str(uuid4()), "rdm-translations", "not-a-type", "Ghost"
        )
        response = publish_change_set(
            client,
            change_set["id"],
            expected_change_set_version=change_set["version"],
            expected_status=422,
        )
        assert response.json()["error"]["code"] == "WORKSPACE_GRAPH_INVALID"
        assert "UNKNOWN_OBJECT_TYPE" in [
            item["code"] for item in response.json()["error"]["details"]
        ]
        assert (
            client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
            == change_set["version"]
        )
        with SessionLocal() as session:
            rows = list(
                session.scalars(
                    select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set["id"])
                )
            )
            assert len(rows) == 1
