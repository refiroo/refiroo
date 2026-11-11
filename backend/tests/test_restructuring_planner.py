"""Base 0.8 C2: the restructuring planner — mapping, cascade and the way back (ADR-034).

The planner (``engine/operations/restructuring``) is exercised directly, since the routes are C3; the
records it writes are read back through the HTTP API. The starter cases run over the starter model
and the same model with every key renamed (``k`` maps a starter key to the model's); the cascade,
its type question, the refusals and the size limit run over the generated model.

Budgets are in ``test_restructuring_volume.py``.
"""

import json
from uuid import uuid4

import pytest
from test_type_changes import (
    WORKSPACE,
    _client,
    attr,
    create,
    publish,
    read,
    relate,
    relations_of,
    start_change_set,
    starter,  # noqa: F401 - fixture
    values,
    version,
    volume,  # noqa: F401 - fixture
)
from volume_fixture import (
    APPLICATION,
    CODE,
    COLUMN,
    GROUP,
    GROUP_CONTAINS_NODE,
    ITEM,
    ITEM_CITES_GROUP,
    MATRIX_APPLICATION,
    NODE,
    NODE_HAS_CHILD,
    RANK,
    volume_model,
)
from wp8_support import create_workspace

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.model.registry import model_registry
from app.engine.operations import restructuring
from app.engine.operations.restructuring import (
    ChangeTypeOperation,
    MappingChoice,
    MoveOperation,
    RecordInputs,
    Restructuring,
    TypeChoice,
    apply_restructuring,
    preview_restructuring,
    suggest_mapping,
)
from app.errors import ApiError
from app.models.schema import EngineModel

NODE_CONTAINS_ITEM = "vol-node-contains-item"
SCORE = "vol-score"


# --- helpers -----------------------------------------------------------------------------------


def preview(change_set, request: Restructuring):
    with SessionLocal() as session:
        return preview_restructuring(session, change_set["id"], request)


def apply(client, change_set, request: Restructuring):
    """Preview, then apply the previewed plan; the plan as previewed."""
    plan = preview(change_set, request)
    assert plan.status == "ready", plan.payload()
    with SessionLocal() as session:
        result = apply_restructuring(
            session,
            change_set["id"],
            request,
            expected_change_set_version=plan.change_set_version,
            plan_digest=plan.plan_digest,
        )
    assert result.change_set_version == plan.change_set_version + 1
    assert version(client, change_set) == result.change_set_version
    return plan


def records(plan) -> dict[str, dict]:
    return {item["objectId"]: item for item in plan.payload()["records"]}


def outcomes(record: dict) -> dict[str, tuple[str, str | None]]:
    return {
        item["attributeTypeKey"]: (item["outcome"], item["from"]) for item in record["attributes"]
    }


def refusal_codes(plan) -> list[tuple[str, str | None]]:
    return [(item["code"], item.get("objectId")) for item in plan.payload()["refusals"]]


# --- the D40 rules, in order -------------------------------------------------------------------


def _rules_model() -> EngineModel:
    """Two types whose attributes meet each rule once: same type, display, unique and required."""
    model = volume_model()
    model["attributeTypes"] += [
        {"key": "label", "name": "Label"},
        {"key": "title", "name": "Title"},
        {"key": "key-a", "name": "Key A", "features": {"unique": True}},
        {"key": "key-b", "name": "Key B", "features": {"unique": True}},
        {"key": "note", "name": "Note", "valueType": "longText"},
        {"key": "count", "name": "Count", "valueType": "integer"},
        {"key": "weight", "name": "Weight", "valueType": "decimal"},
    ]
    model["objectTypes"] += [
        {
            "key": "a",
            "name": "A",
            "pluralName": "As",
            "displayAttributeTypeKey": "label",
            "attributes": [
                {"attributeTypeKey": "label"},
                {"attributeTypeKey": "key-a", "required": True},
                {"attributeTypeKey": "count"},
                {"attributeTypeKey": RANK},
            ],
        },
        {
            "key": "b",
            "name": "B",
            "pluralName": "Bs",
            "displayAttributeTypeKey": "title",
            "attributes": [
                {"attributeTypeKey": "title"},
                {"attributeTypeKey": "key-b", "required": True},
                {"attributeTypeKey": "note"},
                {"attributeTypeKey": "weight"},
                {"attributeTypeKey": RANK},
            ],
        },
    ]
    return EngineModel.model_validate(model)


def test_suggestions_follow_the_rules_in_order():
    model = _rules_model()
    a, b = model.object_type("a"), model.object_type("b")
    sources = {item.attribute_type_key: item for item in suggest_mapping(model, a, b)}
    assert {key: (item.source, item.rule) for key, item in sources.items()} == {
        "title": ("label", "display"),
        "key-b": ("key-a", "uniqueRequired"),
        "note": (None, "none"),
        "weight": (None, "none"),
        RANK: (RANK, "sameType"),
    }
    # Alternatives are the other compatible sources: text widens to longText, integer to decimal.
    assert sources["note"].alternatives == ("label", "key-a")
    assert sources["weight"].alternatives == ("count", RANK)
    assert sources["title"].alternatives == ("key-a",)
    # And back: nothing widens the other way, so decimal and longText have no place.
    back = {item.attribute_type_key: item for item in suggest_mapping(model, b, a)}
    assert back["count"].source is None and back["count"].alternatives == (RANK,)
    # A choice overrides any rule and may leave an attribute without a source.
    chosen = {
        item.attribute_type_key: (item.source, item.rule)
        for item in suggest_mapping(
            model,
            a,
            b,
            MappingChoice("a", "b", {"note": "label", "title": None, "weight": "count"}),
        )
    }
    assert chosen["note"] == ("label", "choice")
    assert chosen["title"] == (None, "choice")
    assert chosen["weight"] == ("count", "choice")
    for mapping in ({"weight": "label"}, {"note": "title"}, {"label": "label"}):
        with pytest.raises(ApiError) as caught:
            suggest_mapping(model, a, b, MappingChoice("a", "b", mapping))
        assert caught.value.code == "INVALID_TYPE_MAPPING"


# --- starter model: type questions, missing values, uniqueness ---------------------------------


@pytest.fixture
def estate(starter):  # noqa: F811 - the fixture imported above
    """System S; system T holding group G (holding group G2) and value V; system U alone."""
    client, k = starter
    systems_app = k("rdm-systems")
    system = create(client, systems_app, k("system"), "S", [attr(k("system-code"), "s")])
    moved = create(
        client,
        systems_app,
        k("system"),
        "T",
        [
            attr(k("system-code"), "t"),
            attr(k("system-type"), "erp"),
            attr(k("description"), "About T"),
        ],
    )
    group = create(client, systems_app, k("system-group"), "G", [attr(k("group-code"), "g")], moved)
    inner = create(
        client, systems_app, k("system-group"), "G2", [attr(k("group-code"), "g2")], group
    )
    value = create(
        client,
        systems_app,
        k("system-value"),
        "V",
        [attr(k("value-code"), "v"), attr(k("value-name"), "V")],
        moved,
    )
    alone = create(client, systems_app, k("system"), "U", [attr(k("system-code"), "u")])
    return {"S": system, "T": moved, "G": group, "G2": inner, "V": value, "U": alone}


def test_a_type_question_is_asked_once_and_answered_by_a_choice(starter, estate):  # noqa: F811
    client, k = starter
    system, moved = estate["S"], estate["T"]
    change_set = start_change_set(client)
    operation = MoveOperation(moved["id"], system["id"])

    # A system under a system: a group or a value, so the plan asks.
    plan = preview(change_set, Restructuring(operation))
    body = plan.payload()
    assert body["status"] == "needsInput"
    assert body["typeQuestions"] == [
        {
            "objectTypeKey": k("system"),
            "parentObjectTypeKey": k("system"),
            "options": [k("system-group"), k("system-value")],
            "chosen": None,
            "recordCount": 1,
        }
    ]
    assert [item["after"] for item in body["records"]] == [
        {"objectTypeKey": None, "parentObjectId": system["id"]}
    ]
    assert body["changeSetVersion"] == version(client, change_set)

    # As a value, its children have no type a value can contain.
    as_value = TypeChoice(k("system"), k("system"), k("system-value"))
    plan = preview(change_set, Restructuring(operation, type_choices=[as_value]))
    assert plan.status == "refused"
    assert sorted(refusal_codes(plan)) == sorted(
        [("noPossibleType", estate["G"]["id"]), ("noPossibleType", estate["V"]["id"])]
    )
    # A choice outside the options is refused.
    wrong = TypeChoice(k("system"), k("system"), k("system"))
    assert [
        code
        for code, _ in refusal_codes(
            preview(change_set, Restructuring(operation, type_choices=[wrong]))
        )
    ] == ["typeNotAllowed"]

    # As a group, it keeps its children, whose edges become the group's relations.
    as_group = TypeChoice(k("system"), k("system"), k("system-group"))
    request = Restructuring(operation, type_choices=[as_group])
    plan = apply(client, change_set, request)
    (record,) = plan.payload()["records"]
    assert record["outcomes"] == ["typeChanged", "moved"]
    assert [part["id"] for part in record["path"]] == [system["id"], moved["id"]]
    assert outcomes(record) == {
        k("group-code"): ("mapped", k("system-code")),
        k("description"): ("kept", k("description")),
        k("active"): ("kept", k("active")),
    }
    assert record["withoutPlace"]["attributes"] == [
        {"attributeTypeKey": k("system-type"), "value": "erp"}
    ]
    (pair,) = plan.payload()["pairs"]
    assert {item["attributeTypeKey"]: item["rule"] for item in pair["attributes"]} == {
        k("group-code"): "display",
        k("description"): "sameType",
        k("active"): "sameType",
    }
    assert pair["withoutPlace"] == [{"attributeTypeKey": k("system-type"), "count": 1}]
    group = read(client, k("system-group"), moved["id"], changeSetId=change_set["id"])
    assert group["parentObjectId"] == system["id"]
    assert values(group)[k("group-code")] == "t"
    edges = {
        item["toObjectId"]: item["relationTypeKey"]
        for item in relations_of(client, moved["id"], changeSetId=change_set["id"])
        if item["fromObjectId"] == moved["id"]
    }
    assert edges == {
        estate["G"]["id"]: k("system-group-has-child"),
        estate["V"]["id"]: k("system-group-contains-value"),
    }


def test_a_value_without_a_source_is_an_input(starter, estate):  # noqa: F811
    client, k = starter
    system, alone = estate["S"], estate["U"]
    change_set = start_change_set(client)
    operation = MoveOperation(alone["id"], system["id"], k("system-value"))

    plan = preview(change_set, Restructuring(operation))
    (record,) = plan.payload()["records"]
    assert plan.status == "needsInput"
    assert record["inputsNeeded"] == [
        {"kind": "attribute", "key": k("value-code"), "reason": "required"}
    ]
    assert outcomes(record)[k("value-name")] == ("mapped", k("system-code"))
    # The ambiguous source: value-code could take system-code too, but display took it first.
    pair = plan.payload()["pairs"][0]
    code = next(item for item in pair["attributes"] if item["attributeTypeKey"] == k("value-code"))
    assert code["from"] is None and code["rule"] == "none"
    assert k("system-code") in code["alternatives"]
    assert code["empty"] == 1

    # A choice takes the other source; the name then needs an input instead.
    choice = MappingChoice(
        k("system"), k("system-value"), {k("value-code"): k("system-code"), k("value-name"): None}
    )
    plan = preview(change_set, Restructuring(operation, mapping_choices=[choice]))
    (record,) = plan.payload()["records"]
    assert record["inputsNeeded"] == [
        {"kind": "attribute", "key": k("value-name"), "reason": "required"}
    ]

    request = Restructuring(
        operation, inputs=[RecordInputs(alone["id"], {k("value-code"): "u-code"})]
    )
    plan = apply(client, change_set, request)
    (record,) = plan.payload()["records"]
    assert outcomes(record)[k("value-code")] == ("input", None)
    assert values(read(client, k("system-value"), alone["id"], changeSetId=change_set["id"])) == {
        k("value-code"): "u-code",
        k("value-name"): "u",
        k("active"): True,
    }


def test_the_dry_run_refuses_a_collision_and_the_change_type_rules(starter, estate):  # noqa: F811
    client, k = starter
    group = estate["G"]
    change_set = start_change_set(client)
    # G to the top as a system: its code "g" becomes the unique system code, held by nothing yet.
    top = Restructuring(MoveOperation(group["id"], None))
    assert preview(change_set, top).status == "ready"
    create(
        client,
        k("rdm-systems"),
        k("system"),
        "Taken",
        [attr(k("system-code"), "g")],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=version(client, change_set),
    )
    before = version(client, change_set)
    plan = preview(change_set, top)
    assert plan.status == "refused"
    ((refusal),) = plan.payload()["refusals"]
    assert refusal["code"] == "uniqueness" and refusal["objectId"] == group["id"]
    assert refusal["conflictingObjectId"]
    # The preview kept nothing.
    assert version(client, change_set) == before
    assert read(client, k("system-group"), group["id"], changeSetId=change_set["id"])[
        "parentObjectId"
    ]

    # Changing a type in place: the same type is a bad request; a type the parent cannot hold is
    # refused; so are another application's type and the top level for a type that needs a parent.
    with pytest.raises(ApiError) as caught:
        preview(change_set, Restructuring(ChangeTypeOperation(group["id"], k("system-group"))))
    assert caught.value.code == "OBJECT_TYPE_UNCHANGED"
    for operation, code in (
        (ChangeTypeOperation(group["id"], k("system")), "typeNotAllowed"),
        (ChangeTypeOperation(group["id"], k("translation")), "application"),
        (MoveOperation(group["id"], None, k("system-group")), "notRoot"),
        (MoveOperation(group["id"], estate["G2"]["id"]), "cycle"),
        (MoveOperation(str(uuid4()), None), "notInChangeSet"),
    ):
        assert [
            code for code, _ in refusal_codes(preview(change_set, Restructuring(operation)))
        ] == [code], operation
    # A move that changes nothing plans nothing.
    same = preview(change_set, Restructuring(MoveOperation(group["id"], estate["T"]["id"])))
    assert same.status == "ready" and same.payload()["records"] == []


# --- the way back ------------------------------------------------------------------------------


@pytest.fixture
def mapped_value(starter):  # noqa: F811
    """System S > value V, with values only a value has and a relationship to master value M."""
    client, k = starter
    master_app = k("rdm-master")
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
    system = create(client, k("rdm-systems"), k("system"), "S", [attr(k("system-code"), "s")])
    value = create(
        client,
        k("rdm-systems"),
        k("system-value"),
        "V",
        [
            attr(k("value-code"), "v-code"),
            attr(k("value-name"), "V name"),
            attr(k("external-id"), "ext-1"),
        ],
        system,
    )
    mapped = relate(client, k("system-value-maps-to-master"), value, master)
    return {"S": system, "V": value, "M": master, "mapped": mapped}


def test_a_round_trip_offers_back_values_and_relationships(starter, mapped_value):  # noqa: F811
    client, k = starter
    value, master, mapped = mapped_value["V"], mapped_value["M"], mapped_value["mapped"]
    original = values(read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE))

    there = start_change_set(client)
    plan = apply(client, there, Restructuring(ChangeTypeOperation(value["id"], k("system-group"))))
    (record,) = plan.payload()["records"]
    assert outcomes(record)[k("group-code")] == ("mapped", k("value-name"))
    assert {item["attributeTypeKey"] for item in record["withoutPlace"]["attributes"]} == {
        k("value-code"),
        k("external-id"),
    }
    assert [item["relationId"] for item in record["withoutPlace"]["relationships"]] == [
        mapped["id"]
    ]
    assert plan.summary()["relationshipsWithoutPlaceCount"] == 1
    publish(client, there)

    back = start_change_set(client)
    request = Restructuring(ChangeTypeOperation(value["id"], k("system-value")))
    plan = preview(back, request)
    (record,) = plan.payload()["records"]
    assert plan.status == "ready"
    assert outcomes(record) == {
        k("value-code"): ("restored", None),
        k("value-name"): ("mapped", k("group-code")),
        k("external-id"): ("restored", None),
        k("active"): ("kept", k("active")),
    }
    assert [item["relationId"] for item in record["restoredRelationships"]] == [mapped["id"]]
    assert record["restoredRelationships"][0]["objectId"] == master["id"]
    assert plan.summary()["restoredCount"] == 3
    assert "restored" in plan.records[0].outcome_tags()

    # Declining the offer leaves the required value to be given, and the relationship behind.
    declined = preview(
        back,
        Restructuring(
            request.operation,
            mapping_choices=[MappingChoice(k("system-group"), k("system-value"), restore=False)],
        ),
    )
    (record,) = declined.payload()["records"]
    assert record["inputsNeeded"] == [
        {"kind": "attribute", "key": k("value-code"), "reason": "required"}
    ]
    assert record["restoredRelationships"] == []

    apply(client, back, request)
    publish(client, back)
    assert values(read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)) == original
    maps = {"relationTypeKey": k("system-value-maps-to-master")}
    assert [
        item["id"] for item in relations_of(client, master["id"], workspaceKey=WORKSPACE, **maps)
    ] == [mapped["id"]]


def test_a_discarded_reclassification_is_not_offered_back(starter, mapped_value):  # noqa: F811
    client, k = starter
    value = mapped_value["V"]
    discarded = start_change_set(client)
    apply(client, discarded, Restructuring(ChangeTypeOperation(value["id"], k("system-group"))))
    response = client.delete(
        f"/api/v1/change-sets/{discarded['id']}",
        params={"expectedVersion": version(client, discarded)},
    )
    assert response.status_code in (200, 204), response.text

    # Live, the external ID is cleared; the next reclassification's before state has none.
    live = read(client, k("system-value"), value["id"], workspaceKey=WORKSPACE)
    response = client.patch(
        f"/api/v1/objects/{k('system-value')}/{value['id']}",
        json={"attributes": [attr(k("external-id"), None)], "expectedVersion": live["version"]},
    )
    assert response.status_code == 200, response.text
    change_set = start_change_set(client)
    apply(client, change_set, Restructuring(ChangeTypeOperation(value["id"], k("system-group"))))
    plan = preview(change_set, Restructuring(ChangeTypeOperation(value["id"], k("system-value"))))
    (record,) = plan.payload()["records"]
    # The value code lost in this change set comes back; the discarded change set's external ID
    # does not, and the relationship is offered back from this change set's event.
    assert outcomes(record)[k("value-code")] == ("restored", None)
    assert outcomes(record)[k("external-id")] == ("empty", None)
    assert [item["relationId"] for item in record["restoredRelationships"]] == [
        mapped_value["mapped"]["id"]
    ]


# --- generated model: the cascade --------------------------------------------------------------


def _question_model() -> dict:
    """The generated model where a node may also hold items, so a group under a node may become
    an item or a node, and a score that only a node has, at least 10."""
    model = volume_model()
    model["attributeTypes"].append(
        {"key": SCORE, "name": "Score", "valueType": "integer", "validation": {"minimum": 10}}
    )
    model["relationTypes"].append(
        {
            "key": NODE_CONTAINS_ITEM,
            "reverseKey": f"{NODE_CONTAINS_ITEM}-reverse",
            "name": NODE_CONTAINS_ITEM,
            "reverseName": "in node",
            "features": {"parentOf": True},
        }
    )
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": NODE_CONTAINS_ITEM,
            "fromObjectTypeKey": NODE,
            "toObjectTypeKey": ITEM,
            "cardinality": "one-to-many",
        }
    )
    for item in model["objectTypes"]:
        if item["key"] == ITEM:
            item["behavior"]["parentRelationTypeKeys"].append(NODE_CONTAINS_ITEM)
        if item["key"] == NODE:
            item["attributes"].append({"attributeTypeKey": SCORE, "order": 40})
    return model


@pytest.fixture
def questions(tmp_path, monkeypatch, migrated_database):
    with _client(tmp_path, monkeypatch, migrated_database, _question_model()) as client:
        create_workspace(client, WORKSPACE)
        yield client
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _group(client, name, parent=None, rank=None, object_type=GROUP, **context):
    attributes = [attr(CODE, name.lower())]
    if rank is not None:
        attributes.append(attr(RANK, rank))
    return create(client, APPLICATION, object_type, name, attributes, parent, **context)


def test_a_cascade_over_three_levels_changes_each_level(volume):  # noqa: F811
    """A > B > C > I and A > J, moved under Z as a node: every level becomes a node, since a node
    holds only nodes; I's citation stays, since this variant lets a node cite a group."""
    client = volume
    target = _group(client, "Z")
    top = _group(client, "A", rank=1)
    middle = _group(client, "B", top)
    lower = _group(client, "C", middle)
    leaf = _group(client, "I", lower, object_type=ITEM)
    beside = _group(client, "J", top, object_type=ITEM)
    cited = relate(client, ITEM_CITES_GROUP, leaf, target)
    change_set = start_change_set(client)

    request = Restructuring(MoveOperation(top["id"], target["id"], NODE))
    plan = apply(client, change_set, request)
    body = plan.payload()
    # Plan order: the operation's record, then each level down by name.
    assert [item["name"] for item in body["records"]] == ["A", "B", "J", "C", "I"]
    assert {item["name"]: [part["name"] for part in item["path"]] for item in body["records"]} == {
        "A": ["Z", "A"],
        "B": ["Z", "A", "B"],
        "J": ["Z", "A", "J"],
        "C": ["Z", "A", "B", "C"],
        "I": ["Z", "A", "B", "C", "I"],
    }
    assert body["summary"]["typeChangeCount"] == 5 and body["summary"]["moveCount"] == 1
    assert body["typeQuestions"] == []
    pairs = {(item["fromObjectTypeKey"], item["toObjectTypeKey"]): item for item in body["pairs"]}
    assert {key: item["recordCount"] for key, item in pairs.items()} == {
        (GROUP, NODE): 3,
        (ITEM, NODE): 2,
    }
    assert pairs[(ITEM, NODE)]["relations"] == [
        {
            "relationTypeKey": ITEM_CITES_GROUP,
            "direction": "outgoing",
            "outcome": "kept",
            "count": 1,
        }
    ]
    record = records(plan)[top["id"]]
    assert outcomes(record) == {CODE: ("kept", CODE), RANK: ("kept", RANK)}

    for item, parent, relation in (
        (top, target, GROUP_CONTAINS_NODE),
        (middle, top, NODE_HAS_CHILD),
        (beside, top, NODE_HAS_CHILD),
        (lower, middle, NODE_HAS_CHILD),
        (leaf, lower, NODE_HAS_CHILD),
    ):
        stored = read(client, NODE, item["id"], changeSetId=change_set["id"])
        assert stored["parentObjectId"] == parent["id"]
        edges = relations_of(client, item["id"], changeSetId=change_set["id"], direction="incoming")
        assert [(edge["relationTypeKey"], edge["fromObjectId"]) for edge in edges] == [
            (relation, parent["id"])
        ]
    assert [
        item["id"]
        for item in relations_of(
            client, leaf["id"], changeSetId=change_set["id"], direction="outgoing"
        )
    ] == [cited["id"]]
    publish(client, change_set)
    assert read(client, NODE, leaf["id"], workspaceKey=WORKSPACE)["parentObjectId"] == lower["id"]


def test_a_cascade_asks_once_per_type_pair(questions):
    """A > B > C > I and A > J under Z as a node: B and C may become items or nodes, asked once;
    the items stay items, since a node now holds them."""
    client = questions
    target = _group(client, "Z")
    top = _group(client, "A")
    middle = _group(client, "B", top, rank=5)
    lower = _group(client, "C", middle, rank=20)
    leaf = _group(client, "I", lower, object_type=ITEM)
    beside = _group(client, "J", top, object_type=ITEM)
    change_set = start_change_set(client)
    operation = MoveOperation(top["id"], target["id"], NODE)

    plan = preview(change_set, Restructuring(operation))
    body = plan.payload()
    assert body["status"] == "needsInput"
    assert body["typeQuestions"] == [
        {
            "objectTypeKey": GROUP,
            "parentObjectTypeKey": NODE,
            "options": [ITEM, NODE],
            "chosen": None,
            "recordCount": 1,
        }
    ]
    # B waits for the answer; nothing below it is planned yet.
    assert [item["name"] for item in body["records"]] == ["A", "B"]
    assert "needsInput" not in plan.records[1].outcome_tags()

    as_node = TypeChoice(GROUP, NODE, NODE)
    plan = preview(change_set, Restructuring(operation, type_choices=[as_node]))
    body = plan.payload()
    assert [item["name"] for item in body["records"]] == ["A", "B", "C"]
    assert body["typeQuestions"][0]["recordCount"] == 2
    assert body["typeQuestions"][0]["chosen"] == NODE

    # A score from the rank: B's rank of 5 fails the score's minimum and is an input.
    score = MappingChoice(GROUP, NODE, {SCORE: RANK})
    request = Restructuring(operation, type_choices=[as_node], mapping_choices=[score])
    plan = preview(change_set, request)
    by_name = {item["name"]: item for item in plan.payload()["records"]}
    assert by_name["B"]["inputsNeeded"] == [
        {"kind": "attribute", "key": SCORE, "reason": "invalidValue"}
    ]
    assert outcomes(by_name["C"])[SCORE] == ("mapped", RANK)
    assert [record.name for record in plan.records_with(["needsInput"])] == ["B"]

    request = Restructuring(
        operation,
        type_choices=[as_node],
        mapping_choices=[score],
        inputs=[RecordInputs(middle["id"], {SCORE: 12})],
    )
    apply(client, change_set, request)
    assert values(read(client, NODE, middle["id"], changeSetId=change_set["id"]))[SCORE] == 12
    assert values(read(client, NODE, lower["id"], changeSetId=change_set["id"]))[SCORE] == 20
    for item, parent in ((leaf, lower), (beside, top)):
        edges = relations_of(client, item["id"], changeSetId=change_set["id"], direction="incoming")
        assert [(edge["relationTypeKey"], edge["fromObjectId"]) for edge in edges] == [
            (NODE_CONTAINS_ITEM, parent["id"])
        ]
    assert read(client, ITEM, leaf["id"], changeSetId=change_set["id"])["objectTypeKey"] == ITEM


def test_refusals_and_the_size_limit(volume, monkeypatch):  # noqa: F811
    client = volume
    top = _group(client, "A")
    middle = _group(client, "B", top)
    items = [_group(client, f"I{index}", middle, object_type=ITEM) for index in range(3)]
    column = create(client, MATRIX_APPLICATION, COLUMN, "Col", [attr(CODE, "col")])
    change_set = start_change_set(client)

    # An item holds nothing: B's items have no possible type.
    plan = preview(change_set, Restructuring(ChangeTypeOperation(middle["id"], ITEM)))
    assert sorted(refusal_codes(plan)) == sorted(("noPossibleType", item["id"]) for item in items)
    assert plan.summary()["refusalCount"] == 3
    # Another application's parent, and an item at the top level, which becomes a group.
    assert refusal_codes(
        preview(change_set, Restructuring(MoveOperation(top["id"], column["id"])))
    ) == [("application", top["id"])]
    plan = preview(change_set, Restructuring(MoveOperation(items[0]["id"], None)))
    assert plan.status == "ready"
    assert plan.payload()["records"][0]["after"] == {"objectTypeKey": GROUP, "parentObjectId": None}

    # D41: a larger operation is refused with the limit, never cut short. A, B and B's three
    # items all become nodes under Z: five records.
    target = _group(client, "Z")
    request = Restructuring(MoveOperation(top["id"], target["id"], NODE))
    change_set = start_change_set(client)
    assert preview(change_set, request).summary()["recordCount"] == 5
    monkeypatch.setattr(restructuring, "RECORD_LIMIT", 4)
    with pytest.raises(ApiError) as caught:
        preview(change_set, request)
    assert caught.value.code == "RESTRUCTURING_TOO_LARGE"
    assert caught.value.details == {"limit": 4}


def test_apply_claims_the_previewed_plan(volume):  # noqa: F811
    client = volume
    target = _group(client, "Z")
    top = _group(client, "A")
    _group(client, "I", top, object_type=ITEM)
    change_set = start_change_set(client)
    request = Restructuring(MoveOperation(top["id"], target["id"], NODE))
    plan = preview(change_set, request)
    assert plan.plan_digest == preview(change_set, request).plan_digest

    def refused(**claim):
        before = version(client, change_set)
        with SessionLocal() as session, pytest.raises(ApiError) as caught:
            apply_restructuring(session, change_set["id"], **claim)
        assert version(client, change_set) == before
        assert (
            read(client, GROUP, top["id"], changeSetId=change_set["id"])["objectTypeKey"] == GROUP
        )
        return caught.value

    stale = refused(
        request=request,
        expected_change_set_version=plan.change_set_version - 1,
        plan_digest=plan.plan_digest,
    )
    assert stale.code == "CHANGE_SET_VERSION_CONFLICT"
    # Another choice is another plan.
    other = Restructuring(
        request.operation, mapping_choices=[MappingChoice(GROUP, NODE, {RANK: None})]
    )
    changed = refused(
        request=other,
        expected_change_set_version=plan.change_set_version,
        plan_digest=plan.plan_digest,
    )
    assert changed.code == "RESTRUCTURING_PLAN_CHANGED"
    assert changed.details == {"planDigest": preview(change_set, other).plan_digest}
    # A plan that is not ready is not applied.
    waiting = Restructuring(MoveOperation(top["id"], target["id"], ITEM))
    waiting_plan = preview(change_set, waiting)
    assert waiting_plan.status == "refused"
    not_ready = refused(
        request=waiting,
        expected_change_set_version=waiting_plan.change_set_version,
        plan_digest=waiting_plan.plan_digest,
    )
    assert not_ready.code == "RESTRUCTURING_NOT_READY"
    assert not_ready.details["summary"]["refusalCount"] == 1

    apply(client, change_set, request)
    # The change set moved on: the old plan's digest no longer matches.
    assert preview(change_set, request).plan_digest != plan.plan_digest


def test_json_request_normalization_ignores_order():
    first = Restructuring(
        MoveOperation("a", "b"),
        type_choices=[TypeChoice("x", "y", "z"), TypeChoice("p", None, "q")],
        inputs=[RecordInputs("2", {"k": 1}), RecordInputs("1", {"b": 2, "a": 1})],
    )
    second = Restructuring(
        MoveOperation("a", "b"),
        type_choices=[TypeChoice("p", None, "q"), TypeChoice("x", "y", "z")],
        inputs=[RecordInputs("1", {"a": 1, "b": 2}), RecordInputs("2", {"k": 1})],
    )
    assert json.dumps(first.normalized(), sort_keys=True) == json.dumps(
        second.normalized(), sort_keys=True
    )
