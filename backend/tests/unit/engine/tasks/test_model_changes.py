"""What a draft changes is read from its model, whatever steps made it (a single whole-model step too)."""

from app.engine.tasks.model_changes import model_changes

BASE = {
    "applications": [{"key": "a", "name": "A", "objectTypeKeys": ["stop"]}],
    "attributeTypes": [{"key": "code", "name": "Code"}],
    "objectTypes": [
        {
            "key": "stop",
            "name": "Stop",
            "pluralName": "Stops",
            "attributes": [{"attributeTypeKey": "code"}],
        }
    ],
    "relationTypes": [],
    "objectTypeRelations": [],
}


def test_a_whole_model_draft_reads_as_the_types_it_adds_and_the_type_it_changes():
    draft = {
        **BASE,
        "attributeTypes": [*BASE["attributeTypes"], {"key": "step-free", "name": "Step free"}],
        "objectTypes": [
            {
                "key": "stop",
                "name": "Bus stop",
                "pluralName": "Stops",
                "attributes": [{"attributeTypeKey": "code"}, {"attributeTypeKey": "step-free"}],
            },
            {"key": "line", "name": "Line", "pluralName": "Lines", "attributes": []},
        ],
        "applications": [{"key": "a", "name": "A", "objectTypeKeys": ["stop", "line"]}],
        "relationTypes": [{"key": "serves", "name": "Serves", "reverseName": "Served by"}],
        "objectTypeRelations": [
            {
                "relationTypeKey": "serves",
                "fromObjectTypeKey": "line",
                "toObjectTypeKey": "stop",
                "cardinality": "many-to-many",
            }
        ],
    }
    kinds = [
        (op["kind"], op.get("key") or op.get("objectType")) for op in model_changes(BASE, draft)
    ]
    assert ("addAttributeType", "step-free") in kinds
    assert ("addObjectType", "line") in kinds
    assert ("changeObjectType", "stop") in kinds
    assert ("attachAttribute", "stop") in kinds
    assert ("addRelationType", "serves") in kinds
    assert ("allowRelation", None) in kinds
    line = next(op for op in model_changes(BASE, draft) if op["kind"] == "addObjectType")
    assert line["applicationKey"] == "a"


def test_an_unchanged_model_has_no_changes():
    assert model_changes(BASE, BASE) == []


def test_a_type_that_differs_only_in_form_is_no_change_and_a_flipped_required_flag_is():
    same = {
        **BASE,
        "objectTypes": [
            {
                "key": "stop",
                "name": "Stop",
                "pluralName": "Stops",
                "description": None,
                "attributes": [{"attributeTypeKey": "code", "required": False, "order": 90}],
            }
        ],
    }
    assert model_changes(BASE, same) == []
    required = {
        **BASE,
        "objectTypes": [
            {
                **BASE["objectTypes"][0],
                "attributes": [{"attributeTypeKey": "code", "required": True}],
            }
        ],
    }
    assert model_changes(BASE, required) == [
        {
            "kind": "changeAttachment",
            "objectType": "stop",
            "attributeType": "code",
            "required": True,
        }
    ]
