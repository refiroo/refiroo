"""Base 0.8 C1: a record's type changes in a change set (ADR-034).

The engine service (``engine/operations/type_changes``) is exercised directly, since the restructuring API
is C3; reads, history, change lists and publishing go through the HTTP API. Each part runs over the
starter model and the same model with every key renamed (the ``k`` fixture maps a starter key to the
model's), and the generated volume model has its own cases, so nothing depends on a key.

Starter shapes used: a system value becoming a system group under its system and back (values
mapped, kept and without a place; a relationship to a master value removed and restored with its
former ID); a system group moving to the top level as a system (its children's containment edges
re-typed); a translation group becoming a translation (a required, language-scoped relationship
given as an input, and a relation matrix cell).
"""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from model_support import MODEL_PATH, renamed_model
from volume_fixture import (
    ACTIVE,
    APPLICATION,
    CELL,
    CODE,
    COLUMN,
    GROUP,
    GROUP_HAS_CELL,
    ITEM,
    ITEM_CITES_GROUP,
    MATRIX_APPLICATION,
    NODE,
    RANK,
    SHELF,
    volume_model,
)
from wp8_support import create_workspace, publish_change_set, workspace_active_publication_id

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.model.registry import model_registry
from app.engine.operations.type_changes import (
    RelationInput,
    RestoredRelation,
    TypeChange,
    apply_type_change,
    check_type_change,
)
from app.errors import ApiError
from app.main import create_app
from app.models.database import AuditEvent, ChangeSetRelation, RelationSetVersion

WORKSPACE = "c1-types"


def _client(tmp_path, monkeypatch, migrated_database, model: dict):
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", migrated_database("type-changes.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    return TestClient(create_app())


@pytest.fixture(params=["example", "renamed"])
def starter(request, tmp_path, monkeypatch, migrated_database):
    """A client over the starter model or its renamed copy, and the key map ``k``."""
    source = json.loads(MODEL_PATH.read_text())
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    with _client(tmp_path, monkeypatch, migrated_database, source) as client:
        create_workspace(client, WORKSPACE)
        yield client, (lambda key: names.get(key, key))
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _volume_variant() -> dict:
    """The generated model, where a node may also cite a group, so an item's citation stays."""
    model = volume_model()
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": ITEM_CITES_GROUP,
            "fromObjectTypeKey": NODE,
            "toObjectTypeKey": GROUP,
            "cardinality": "many-to-many",
        }
    )
    return model


@pytest.fixture
def volume(tmp_path, monkeypatch, migrated_database):
    with _client(tmp_path, monkeypatch, migrated_database, _volume_variant()) as client:
        create_workspace(client, WORKSPACE)
        yield client
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


# --- helpers -----------------------------------------------------------------------------------


def attr(key, value):
    return {"attributeTypeKey": key, "value": value}


def values(record) -> dict:
    return {item["attributeTypeKey"]: item["value"] for item in record["attributes"]}


def create(client, application, object_type, name, attributes, parent=None, relations=None, **context):
    payload = {
        "applicationKey": application,
        "objectTypeKey": object_type,
        "name": name,
        "attributes": attributes,
        **(context or {"workspaceKey": WORKSPACE}),
    }
    if parent is not None:
        payload["parentObjectId"] = parent["id"]
    if relations:
        payload["initialRelations"] = relations
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def relate(client, relation_type, source, target):
    response = client.post(
        "/api/v1/relations",
        json={"relationTypeKey": relation_type, "fromObjectId": source["id"], "toObjectId": target["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def start_change_set(client) -> dict:
    response = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def version(client, change_set) -> int:
    return client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]


def change_type(client, change_set, change: TypeChange):
    with SessionLocal() as session:
        return apply_type_change(session, change_set["id"], version(client, change_set), change)


def refused(client, change_set, change: TypeChange) -> ApiError:
    """The refusal, having checked that nothing was written."""
    before = version(client, change_set)
    changes = object_changes(client, change_set)
    with SessionLocal() as session, pytest.raises(ApiError) as caught:
        apply_type_change(session, change_set["id"], before, change)
    assert version(client, change_set) == before
    assert object_changes(client, change_set) == changes
    # The check refuses the same way.
    with SessionLocal() as session, pytest.raises(ApiError) as checked:
        check_type_change(session, change_set["id"], change)
    assert checked.value.code == caught.value.code
    return caught.value


def read(client, object_type, object_id, expected=200, **params):
    response = client.get(f"/api/v1/objects/{object_type}/{object_id}", params=params)
    assert response.status_code == expected, response.text
    return response.json() if expected == 200 else response.json()["error"]


def object_changes(client, change_set, **params) -> list[dict]:
    response = client.get(
        f"/api/v1/change-sets/{change_set['id']}/object-changes", params=params
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def relation_changes(client, change_set, **params) -> list[dict]:
    response = client.get(
        f"/api/v1/change-sets/{change_set['id']}/relation-changes", params=params
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def relations_of(client, object_id, **params) -> list[dict]:
    response = client.get(
        "/api/v1/relations",
        params={"objectId": object_id, "direction": "both", "pageSize": 100, **params},
    )
    assert response.status_code == 200, response.text
    return [item["relation"] for item in response.json()["items"]]


def publish(client, change_set, expected_status=200):
    active = workspace_active_publication_id(WORKSPACE)
    response = publish_change_set(
        client,
        change_set["id"],
        expected_change_set_version=version(client, change_set),
        expected_active_publication_id=active,
        explicit_null_active_publication=active is None,
        expected_status=expected_status,
    )
    return response.json()


def reclassified(object_id: str) -> list[dict]:
    with SessionLocal() as session:
        return [
            event.changes
            for event in session.query(AuditEvent)
            .filter(AuditEvent.aggregate_id == object_id, AuditEvent.action == "reclassified")
            .order_by(AuditEvent.sequence_id)
        ]


# --- starter model: values, relationships, containment ---------------------------------------


@pytest.fixture
def systems(starter):
    """System S > value V (mapped to master value M), and S > group G > [group G2, value W]."""
    client, k = starter
    systems_app, master_app = k("rdm-systems"), k("rdm-master")
    domain = create(client, master_app, k("domain"), "D", [attr(k("domain-code"), "d")])
    codelist = create(
        client, master_app, k("codelist"), "C", [attr(k("codelist-code"), "c")], domain
    )
    master = create(
        client,
        master_app,
        k("master-value"),
        "M",
        [attr(k("master-id"), "m"), attr(k("value-code"), "m"), attr(k("value-name"), "M")],
        codelist,
    )
    system = create(client, systems_app, k("system"), "S", [attr(k("system-code"), "s")])
    value = create(
        client,
        systems_app,
        k("system-value"),
        "V",
        [
            attr(k("value-code"), "v-code"),
            attr(k("value-name"), "V name"),
            attr(k("external-id"), "ext-1"),
            attr(k("active"), False),
        ],
        system,
    )
    mapped = relate(client, k("system-value-maps-to-master"), value, master)
    group = create(
        client,
        systems_app,
        k("system-group"),
        "G",
        [attr(k("group-code"), "g"), attr(k("description"), "About G")],
        system,
    )
    inner = create(
        client, systems_app, k("system-group"), "G2", [attr(k("group-code"), "g2")], group
    )
    child_value = create(
        client,
        systems_app,
        k("system-value"),
        "W",
        [attr(k("value-code"), "w"), attr(k("value-name"), "W")],
        group,
    )
    return {
        "S": system,
        "V": value,
        "M": master,
        "G": group,
        "G2": inner,
        "W": child_value,
        "mapped": mapped,
    }


def test_value_becomes_group_and_back_keeping_its_identity(starter, systems):
    client, k = starter
    value, system = systems["V"], systems["S"]
    live_before = read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)
    first = publish(client, start_change_set(client))  # the publication that keeps the old type
    change_set = start_change_set(client)

    result = change_type(
        client,
        change_set,
        TypeChange(
            object_id=value["id"],
            object_type_key=k("system-group"),
            mapping={k("group-code"): k("value-name")},
            expected_record_version=live_before["version"],
        ),
    )

    # Values: the display value mapped, the shared attribute kept, the rest without a place.
    outcomes = {item.attribute_type_key: (item.outcome, item.source) for item in result.attributes}
    assert outcomes == {
        k("group-code"): ("mapped", k("value-name")),
        k("description"): ("empty", None),
        k("active"): ("kept", k("active")),
    }
    assert result.values_without_place == {k("value-code"): "v-code", k("external-id"): "ext-1"}
    # The relationship to the master value has no place; the containment edge is re-typed.
    assert [state.relation_id for state in result.relationships_without_place] == [
        systems["mapped"]["id"]
    ]
    record = read(client, k("system-group"), value["id"], changeSetId=change_set["id"])
    assert record["objectTypeKey"] == k("system-group")
    assert record["parentObjectId"] == system["id"]
    assert record["version"] == live_before["version"] + 1
    assert values(record) == {k("group-code"): "V name", k("active"): False}
    assert [part["objectTypeKey"] for part in record["path"]] == [k("system"), k("system-group")]
    edges = relations_of(client, value["id"], changeSetId=change_set["id"])
    assert [(item["relationTypeKey"], item["fromObjectId"]) for item in edges] == [
        (k("system-contains-group"), system["id"])
    ]

    # D42: the old type's routes answer with the current type, in the change set only.
    error = read(
        client, k("system-value"), value["id"], expected=409, changeSetId=change_set["id"]
    )
    assert error["code"] == "object_type_changed"
    assert error["details"] == {
        "objectId": value["id"],
        "objectTypeKey": k("system-group"),
        "requestedObjectTypeKey": k("system-value"),
    }
    for response in (
        client.get(
            f"/api/v1/objects/{k('system-value')}/{value['id']}/history",
            params={"changeSetId": change_set["id"]},
        ),
        client.get(
            f"/api/v1/objects/{k('system-value')}/{value['id']}/parent-candidates",
            params={"changeSetId": change_set["id"]},
        ),
        client.patch(
            f"/api/v1/objects/{k('system-value')}/{value['id']}",
            json={
                "name": "renamed",
                "expectedVersion": record["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": version(client, change_set),
            },
        ),
        client.delete(
            f"/api/v1/objects/{k('system-value')}/{value['id']}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": version(client, change_set),
                "expectedVersion": record["version"],
            },
        ),
    ):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "object_type_changed"
    assert read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)["version"] == (
        live_before["version"]
    )

    # History: one reclassified event naming what changed, without values.
    history = client.get(
        f"/api/v1/objects/{k('system-group')}/{value['id']}/history",
        params={"changeSetId": change_set["id"]},
    ).json()["items"]
    assert history[0]["action"] == "reclassified"
    assert history[0]["changedFields"] == ["objectType", "attributes", "relationships"]
    assert history[0]["attributeTypeKeys"] == sorted(
        [k("group-code"), k("active"), k("value-code"), k("value-name"), k("external-id")]
    )
    # The stored payload holds the full before state; the master value's history shows the loss.
    (event,) = reclassified(value["id"])
    assert event["objectType"] == {"before": k("system-value"), "after": k("system-group")}
    assert event["before"]["attributes"] == values(live_before)
    assert event["before"]["relationships"][0]["relationId"] == systems["mapped"]["id"]
    assert event["before"]["relationships"][0]["toObjectId"] == systems["M"]["id"]
    master_history = client.get(
        f"/api/v1/objects/{k('master-value')}/{systems['M']['id']}/history",
        params={"changeSetId": change_set["id"]},
    ).json()["items"]
    assert master_history[0]["action"] == "reclassified"

    # Change lists: the type on both sides, objectType first, the type filter on either side.
    (entry,) = object_changes(client, change_set)
    assert entry["kind"] == "changed"
    assert entry["before"]["objectTypeKey"] == k("system-value")
    assert entry["after"]["objectTypeKey"] == k("system-group")
    assert entry["changedFields"][0] == "objectType"
    for key in (k("system-value"), k("system-group")):
        assert [item["objectId"] for item in object_changes(client, change_set, objectTypeKey=key)] == [
            value["id"]
        ]
    relations = {
        (item["relationTypeKey"], item["kind"]): item for item in relation_changes(client, change_set)
    }
    assert set(relations) == {
        (k("system-contains-value"), "removed"),
        (k("system-contains-group"), "added"),
        (k("system-value-maps-to-master"), "removed"),
    }
    assert relations[(k("system-contains-value"), "removed")]["containment"] is True
    # The removed edge's end reads as the change set holds it, now a group; the edge is still a
    # parent edge by the type the record had.
    removed_edge = relations[(k("system-contains-value"), "removed")]
    assert removed_edge["toObject"]["objectTypeKey"] == k("system-group")

    # Publishing applies it to live; the earlier publication keeps the old type.
    publish(client, change_set)
    live = read(client, k("system-group"), value["id"], workspaceKey=WORKSPACE)
    assert live["objectTypeKey"] == k("system-group") and values(live) == values(record)
    assert read(client, k("system-value"), value["id"], expected=409, workspaceKey=WORKSPACE)[
        "code"
    ] == "object_type_changed"
    assert read(client, k("system-value"), value["id"], publicationId=first["id"])[
        "objectTypeKey"
    ] == k("system-value")
    maps = {"relationTypeKey": k("system-value-maps-to-master")}
    assert relations_of(client, systems["M"]["id"], workspaceKey=WORKSPACE, **maps) == []

    # And back: the lost relationship restored with its former ID, the values given back.
    back = start_change_set(client)
    mapped = systems["mapped"]
    result = change_type(
        client,
        back,
        TypeChange(
            object_id=value["id"],
            object_type_key=k("system-value"),
            mapping={k("value-name"): k("group-code")},
            values={k("value-code"): "v-code"},
            restored_values={k("external-id"): "ext-1"},
            restored_relations=[
                RestoredRelation(
                    mapped["id"], mapped["relationTypeKey"], value["id"], systems["M"]["id"]
                )
            ],
        ),
    )
    assert result.restored_relation_ids == (mapped["id"],)
    publish(client, back)
    restored = read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)
    assert values(restored) == values(live_before)
    restored_ids = [
        item["id"] for item in relations_of(client, systems["M"]["id"], workspaceKey=WORKSPACE, **maps)
    ]
    assert restored_ids == [mapped["id"]]


def test_group_moves_to_the_top_level_as_a_system_and_its_children_follow(starter, systems):
    client, k = starter
    group, inner, child = systems["G"], systems["G2"], systems["W"]
    change_set = start_change_set(client)
    change_type(
        client,
        change_set,
        TypeChange(
            object_id=group["id"],
            object_type_key=k("system"),
            parent_object_id=None,
            mapping={k("system-code"): k("group-code")},
        ),
    )
    record = read(client, k("system"), group["id"], changeSetId=change_set["id"])
    assert record["parentObjectId"] is None
    assert values(record) == {
        k("system-code"): "g",
        k("description"): "About G",
        k("active"): True,
    }
    # The children keep their type and parent; their edges become the system's relations.
    edges = {
        item["toObjectId"]: item["relationTypeKey"]
        for item in relations_of(client, group["id"], changeSetId=change_set["id"])
    }
    assert edges == {
        inner["id"]: k("system-contains-group"),
        child["id"]: k("system-contains-value"),
    }
    assert [part["id"] for part in read(client, k("system-value"), child["id"], changeSetId=change_set["id"])["path"]] == [
        group["id"],
        child["id"],
    ]
    # The move is part of the reclassification.
    (event,) = reclassified(group["id"])
    assert event["parent"] == {"before": systems["S"]["id"], "after": None}
    assert event["changedFields"][:2] == ["objectType", "parent"]
    publish(client, change_set)
    assert read(client, k("system"), group["id"], workspaceKey=WORKSPACE)["parentObjectId"] is None


def test_a_reclassified_record_removed_later_lists_no_type_change(starter, systems):
    """Found in C5: removed after its type changed, the entry named ``objectType`` with no after side."""
    client, k = starter
    value = systems["V"]
    change_set = start_change_set(client)
    change_type(
        client,
        change_set,
        TypeChange(
            object_id=value["id"],
            object_type_key=k("system-group"),
            mapping={k("group-code"): k("value-code")},
        ),
    )
    group = read(client, k("system-group"), value["id"], changeSetId=change_set["id"])
    response = client.delete(
        f"/api/v1/objects/{k('system-group')}/{value['id']}",
        params={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": version(client, change_set),
            "expectedVersion": group["version"],
        },
    )
    assert response.status_code == 204, response.text
    (entry,) = object_changes(client, change_set)
    assert entry["kind"] == "removed"
    assert entry["before"]["objectTypeKey"] == k("system-value")
    assert entry["after"] is None
    # A removed record names the fields its source holds; a type change needs both sides.
    assert entry["changedFields"][:2] == ["name", "parent"]
    assert "objectType" not in entry["changedFields"]
    # The source type still finds it.
    assert [
        item["objectId"]
        for item in object_changes(client, change_set, objectTypeKey=k("system-value"))
    ] == [value["id"]]


def test_refusals_leave_nothing_behind(starter, systems):
    client, k = starter
    change_set = start_change_set(client)
    value, group = systems["V"], systems["G"]

    def code(change):
        return refused(client, change_set, change).code

    # A value cannot contain the group's children; the cascade is the planner's (C2).
    as_value = TypeChange(
        group["id"],
        k("system-value"),
        mapping={k("value-name"): k("group-code")},
        values={k("value-code"): "gv"},
    )
    assert code(as_value) == "child_type_not_allowed"
    # Another application's type (D39), the same type, a type that cannot be at the top level.
    assert code(TypeChange(value["id"], k("domain"))) == "object_type_not_in_application"
    assert code(TypeChange(value["id"], k("system-value"))) == "object_type_unchanged"
    assert (
        code(TypeChange(value["id"], k("system-group"), parent_object_id=None, mapping={k("group-code"): k("value-name")}))
        == "parent_required"
    )
    # A system needs its required code, which a group does not have.
    assert (
        code(TypeChange(systems["G2"]["id"], k("system"), parent_object_id=None))
        == "missing_required_attributes"
    )
    # A mapping across value types, a source the old type does not bind, a missing required value.
    assert (
        code(TypeChange(value["id"], k("system-group"), mapping={k("group-code"): k("active")}))
        == "invalid_type_mapping"
    )
    assert (
        code(TypeChange(value["id"], k("system-group"), mapping={k("group-code"): k("group-code")}))
        == "invalid_type_mapping"
    )
    assert code(TypeChange(value["id"], k("system-group"))) == "missing_required_attributes"
    # A unique value another record holds.
    assert (
        code(
            TypeChange(
                group["id"],
                k("system"),
                parent_object_id=None,
                values={k("system-code"): "s"},
            )
        )
        == "duplicate_attribute_value"
    )
    # A stale record version.
    assert (
        code(
            TypeChange(
                value["id"],
                k("system-group"),
                mapping={k("group-code"): k("value-name")},
                expected_record_version=99,
            )
        )
        == "version_conflict"
    )
    # A record the change set does not hold.
    assert code(TypeChange(str(uuid4()), k("system-group"))) == "object_not_found"


def test_a_cycle_is_refused(starter, systems):
    client, k = starter
    change_set = start_change_set(client)
    # G moves under its own child G2, becoming a value there.
    group, inner = systems["G"], systems["G2"]
    error = refused(
        client,
        change_set,
        TypeChange(
            group["id"],
            k("system-value"),
            parent_object_id=inner["id"],
            mapping={k("value-name"): k("group-code")},
            values={k("value-code"): "gv"},
        ),
    )
    assert error.code == "parent_cycle"


def test_publishing_refuses_a_live_edit_and_a_live_relationship_the_new_type_cannot_have(
    starter, systems
):
    client, k = starter
    value = systems["V"]
    change = TypeChange(
        value["id"], k("system-group"), mapping={k("group-code"): k("value-name")}
    )

    # A live edit of the same record since the change set's base.
    edited = start_change_set(client)
    change_type(client, edited, change)
    live = read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)
    response = client.patch(
        f"/api/v1/objects/{k('system-value')}/{value['id']}",
        json={"name": "V live", "expectedVersion": live["version"]},
    )
    assert response.status_code == 200, response.text
    error = publish(client, edited, expected_status=409)["error"]
    assert error["code"] == "version_conflict"
    assert read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)["name"] == "V live"

    # A live mapping in a set the type change touched: the existing set divergence rule.
    staged = start_change_set(client)
    change_type(client, staged, change)
    codelist = {"id": systems["M"]["parentObjectId"]}
    second = create(
        client,
        k("rdm-master"),
        k("master-value"),
        "M2",
        [attr(k("master-id"), "m2"), attr(k("value-code"), "m2"), attr(k("value-name"), "M2")],
        codelist,
    )
    relate(client, k("system-value-maps-to-master"), value, second)
    error = publish(client, staged, expected_status=409)["error"]
    assert error["details"]["conflicts"][0]["code"] == "mapping_set_changed"

    # A live relationship in a set it did not touch, which the record's version does not show:
    # the merged graph's validation refuses it.
    untouched = start_change_set(client)
    change_type(client, untouched, change)
    relate(client, k("reference-has-system-representation"), codelist, value)
    error = publish(client, untouched, expected_status=422)["error"]
    assert error["code"] == "workspace_graph_invalid"
    assert "invalid_relation_pair" in {item["code"] for item in error["details"]}
    assert read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)["objectTypeKey"] == (
        k("system-value")
    )


def test_translation_group_becomes_a_translation_with_its_required_scoped_relationship(starter):
    client, k = starter
    translations, master_app = k("rdm-translations"), k("rdm-master")
    domain = create(client, master_app, k("domain"), "D", [attr(k("domain-code"), "d")])
    codelist = create(
        client, master_app, k("codelist"), "C", [attr(k("codelist-code"), "c")], domain
    )

    def master(name):
        return create(
            client,
            master_app,
            k("master-value"),
            name,
            [attr(k("master-id"), name), attr(k("value-code"), name), attr(k("value-name"), name)],
            codelist,
        )

    translated, untranslated = master("M1"), master("M2")
    language = create(client, translations, k("language"), "L", [attr(k("language-code"), "l")])
    outer = create(
        client, translations, k("translation-group"), "TG", [attr(k("group-code"), "tg")], language
    )
    inner = create(
        client,
        translations,
        k("translation-group"),
        "TG2",
        [attr(k("group-code"), "Hello"), attr(k("description"), "A greeting")],
        outer,
    )
    create(
        client,
        translations,
        k("translation"),
        "T1",
        [attr(k("translated-name"), "One"), attr(k("active"), True)],
        outer,
        [
            {
                "relationTypeKey": k("object-has-translation"),
                "direction": "incoming",
                "otherObjectId": translated["id"],
            }
        ],
    )
    change_set = start_change_set(client)
    mapping = {
        k("translated-name"): k("group-code"),
        k("translated-description"): k("description"),
    }

    def becomes(source):
        return TypeChange(
            inner["id"],
            k("translation"),
            mapping=mapping,
            values={k("active"): True},
            relations=[RelationInput(k("object-has-translation"), "incoming", source["id"])],
        )

    # The required relationship is an input; one into a scope the language already holds (one
    # active translation per record and language) is held by the change set for validation to
    # report (H4c), so the check passes it.
    missing = TypeChange(inner["id"], k("translation"), mapping=mapping)
    assert refused(client, change_set, missing).code == "missing_required_relations"
    with SessionLocal() as session:
        check_type_change(session, change_set["id"], becomes(translated))

    result = change_type(client, change_set, becomes(untranslated))
    assert len(result.created_relation_ids) == 1
    record = read(client, k("translation"), inner["id"], changeSetId=change_set["id"])
    assert values(record) == {
        k("translated-name"): "Hello",
        k("translated-description"): "A greeting",
        k("active"): True,
    }
    # The containment edge is the translation's; the fixture's teardown checks the matrix cell
    # states the new translation adds.
    edges = {
        item["relationTypeKey"]
        for item in relations_of(client, inner["id"], changeSetId=change_set["id"])
    }
    assert edges == {k("translation-group-contains-translation"), k("object-has-translation")}
    publish(client, change_set)
    assert read(client, k("translation"), inner["id"], workspaceKey=WORKSPACE)["objectTypeKey"] == (
        k("translation")
    )


# --- generated model -----------------------------------------------------------------------------


def _code(prefix):
    return [attr(CODE, f"{prefix}-{uuid4().hex[:6]}"), attr(RANK, 3)]


def test_generated_model_item_becomes_node_keeping_its_citation(volume):
    client = volume
    group = create(client, APPLICATION, GROUP, "G", _code("g"))
    cited = create(client, APPLICATION, GROUP, "Cited", _code("c"))
    item = create(client, APPLICATION, ITEM, "I", _code("i"), group)
    citation = relate(client, ITEM_CITES_GROUP, item, cited)
    change_set = start_change_set(client)

    result = change_type(client, change_set, TypeChange(item["id"], NODE))
    assert {item.outcome for item in result.attributes} == {"kept"}
    assert result.values_without_place == {}
    assert result.kept_relation_ids == (citation["id"],)
    edges = {
        item["relationTypeKey"]: item["id"]
        for item in relations_of(client, item["id"], changeSetId=change_set["id"])
    }
    assert set(edges) == {"vol-group-contains-node", ITEM_CITES_GROUP}
    assert edges[ITEM_CITES_GROUP] == citation["id"]
    # The citation's sets advance under both bindings: the old item one and the new node one.
    with SessionLocal() as session:
        bindings = {
            (row.from_object_type_key, row.direction)
            for row in session.query(RelationSetVersion).filter(
                RelationSetVersion.change_set_id == change_set["id"],
                RelationSetVersion.relation_type_key == ITEM_CITES_GROUP,
            )
        }
    assert bindings == {(ITEM, "outgoing"), (ITEM, "incoming"), (NODE, "outgoing"), (NODE, "incoming")}
    publish(client, change_set)
    assert read(client, NODE, item["id"], workspaceKey=WORKSPACE)["objectTypeKey"] == NODE
    assert [row["id"] for row in relations_of(client, cited["id"], workspaceKey=WORKSPACE)] == [
        citation["id"]
    ]

    # A node holding nodes cannot become an item, which contains nothing.
    parent = create(client, APPLICATION, NODE, "N", _code("n"), group)
    create(client, APPLICATION, NODE, "N2", _code("n2"), parent)
    again = start_change_set(client)
    assert refused(client, again, TypeChange(parent["id"], ITEM)).code == "child_type_not_allowed"


def test_generated_model_shelf_becomes_a_matrix_cell(volume):
    client = volume
    column = create(client, MATRIX_APPLICATION, COLUMN, "Col", _code("col"))
    shelf = create(client, MATRIX_APPLICATION, SHELF, "Shelf", _code("s"), column)
    inner = create(client, MATRIX_APPLICATION, SHELF, "Inner", _code("s2"), shelf)
    group = create(client, MATRIX_APPLICATION, GROUP, "Row", _code("row"))
    other = create(client, MATRIX_APPLICATION, GROUP, "Row 2", _code("row2"))
    create(
        client,
        MATRIX_APPLICATION,
        CELL,
        "Existing",
        [*_code("cell"), attr(ACTIVE, True)],
        shelf,
        [{"relationTypeKey": GROUP_HAS_CELL, "direction": "incoming", "otherObjectId": group["id"]}],
    )
    change_set = start_change_set(client)

    def becomes(row):
        return TypeChange(
            inner["id"],
            CELL,
            relations=[RelationInput(GROUP_HAS_CELL, "incoming", row["id"])],
        )

    assert refused(client, change_set, TypeChange(inner["id"], CELL)).code == (
        "missing_required_relations"
    )
    # One active cell per row and column (the scope): a second one is held by the change set for
    # validation to report (H4c), so the check passes it.
    with SessionLocal() as session:
        check_type_change(
            session,
            change_set["id"],
            TypeChange(
                inner["id"],
                CELL,
                values={ACTIVE: True},
                relations=[RelationInput(GROUP_HAS_CELL, "incoming", group["id"])],
            ),
        )
    # The new cell's stored matrix states are checked by the fixture's teardown.
    change_type(client, change_set, becomes(other))
    publish(client, change_set)
    assert read(client, CELL, inner["id"], workspaceKey=WORKSPACE)["parentObjectId"] == shelf["id"]


def test_the_check_keeps_no_write(volume):
    client = volume
    group = create(client, APPLICATION, GROUP, "G", _code("g"))
    item = create(client, APPLICATION, ITEM, "I", _code("i"), group)
    change_set = start_change_set(client)
    before = version(client, change_set)
    with SessionLocal() as session:
        result = check_type_change(session, change_set["id"], TypeChange(item["id"], NODE))
    assert result.after_type_key == NODE
    assert version(client, change_set) == before
    assert object_changes(client, change_set) == []
    assert read(client, ITEM, item["id"], changeSetId=change_set["id"])["objectTypeKey"] == ITEM
    assert reclassified(item["id"]) == []
    with SessionLocal() as session:
        assert (
            session.query(ChangeSetRelation)
            .filter(ChangeSetRelation.change_set_id == change_set["id"])
            .count()
            == 0
        )
