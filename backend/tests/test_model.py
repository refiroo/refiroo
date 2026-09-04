from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.schema import EngineModel
from app.services.model_loader import load_model

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"


def test_starter_model_is_valid():
    model = load_model(MODEL_PATH)
    assert len(model.applications) == 3
    assert {app.key for app in model.applications} == {
        "rdm-master",
        "rdm-systems",
        "rdm-translations",
    }
    assert len(model.attributeTypes) == 22
    assert len(model.objectTypes) == 9
    assert len(model.relationTypes) == 13
    assert len(model.objectTypeRelations) == 16
    assert [detail.objectTypeKey for detail in model.applications[0].details] == [
        "domain",
        "codelist",
        "master-value",
    ]
    assert model.applications[0].details[0].panels[0].type == "children"
    assert model.applications[0].details[1].panels[0].type == "children"


def test_domain_and_codelist_system_representations_are_modelled_as_optional_associations():
    model = load_model(MODEL_PATH)
    relation = model.relation_type("reference-has-system-representation")
    assert relation is not None
    assert relation.name == "Has system representation"
    assert relation.reverseName == "Represents reference structure"

    allowed = [
        item
        for item in model.objectTypeRelations
        if item.relationTypeKey == relation.key
    ]
    assert {
        (item.fromObjectTypeKey, item.toObjectTypeKey, item.cardinality, item.required)
        for item in allowed
    } == {
        ("domain", "system-value", "one-to-many", False),
        ("codelist", "system-value", "one-to-many", False),
    }

    master_details = {item.objectTypeKey: item for item in model.applications[0].details}
    for object_type_key in ("domain", "codelist"):
        panel = next(
            item
            for item in master_details[object_type_key].panels
            if item.key == "system-representations"
        )
        assert panel.config.direction == "outgoing"
        assert panel.config.relationTypeKeys == (relation.key,)
        assert panel.config.columns[:2] == ("ancestor:system", "name")
        assert panel.config.showRelationshipColumn is False

    system_value_details = next(
        item
        for item in model.applications[1].details
        if item.objectTypeKey == "system-value"
    )
    panel = next(item for item in system_value_details.panels if item.key == "represented-structures")
    assert panel.config.direction == "incoming"
    assert panel.config.relationTypeKeys == (relation.key,)
    assert panel.config.showRelationshipColumn is False

    master_value_details = master_details["master-value"]
    mappings = next(item for item in master_value_details.panels if item.key == "mappings")
    assert mappings.config.columns[:2] == ("ancestor:system", "name")
    assert mappings.config.showRelationshipColumn is False


def test_translations_target_every_configured_master_object_type():
    model = load_model(MODEL_PATH)
    translation = model.object_type("translation")
    assert translation is not None
    assert translation.validation["atLeastOneOf"] == (
        "translated-name",
        "translated-description",
        "translated-value",
    )
    assert any(item.attributeTypeKey == "translated-value" for item in translation.attributes)

    allowed = [
        item
        for item in model.objectTypeRelations
        if item.relationTypeKey == "object-has-translation"
    ]
    assert {
        (item.fromObjectTypeKey, item.toObjectTypeKey, item.cardinality, item.required)
        for item in allowed
    } == {
        ("domain", "translation", "one-to-many", True),
        ("codelist", "translation", "one-to-many", True),
        ("master-value", "translation", "one-to-many", True),
    }
    assert all(item.features["uniqueToAncestorTypeKey"] == "language" for item in allowed)
    assert all(
        item.features["uniqueWhenToAttributeEquals"]
        == {"attributeTypeKey": "active", "value": True}
        for item in allowed
    )

    translation_app = next(app for app in model.applications if app.key == "rdm-translations")
    group_detail = next(
        detail for detail in translation_app.details if detail.objectTypeKey == "translation-group"
    )
    translations_panel = next(panel for panel in group_detail.panels if panel.key == "translations")
    assert translations_panel.type == "children"


def test_translation_target_relation_accepts_a_future_model_object_type():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["objectTypes"].append(
        {
            "key": "future-reference",
            "name": "Future reference",
            "pluralName": "Future references",
            "attributes": [
                {"attributeTypeKey": "description"},
                {"attributeTypeKey": "active"},
            ],
            "features": {"rootCreatable": True},
        }
    )
    source["applications"][0]["objectTypeKeys"].append("future-reference")
    source["objectTypeRelations"].append(
        {
            "relationTypeKey": "object-has-translation",
            "fromObjectTypeKey": "future-reference",
            "toObjectTypeKey": "translation",
            "cardinality": "one-to-many",
            "required": True,
            "features": {"uniqueToAncestorTypeKey": "language"},
        }
    )

    extended = EngineModel.model_validate(source)
    assert any(
        item.fromObjectTypeKey == "future-reference"
        and item.relationTypeKey == "object-has-translation"
        for item in extended.objectTypeRelations
    )


def test_object_cross_field_validation_rejects_unbound_attributes():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    translation = next(item for item in source["objectTypes"] if item["key"] == "translation")
    translation["validation"]["atLeastOneOf"] = ["missing"]

    with pytest.raises(ValidationError, match="references unbound attributes"):
        EngineModel.model_validate(source)


def test_relation_scoped_uniqueness_rejects_unknown_ancestor_type():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    relation = next(
        item
        for item in source["objectTypeRelations"]
        if item["relationTypeKey"] == "object-has-translation"
    )
    relation["features"]["uniqueToAncestorTypeKey"] = "missing"

    with pytest.raises(ValidationError, match="unknown unique ancestor object type"):
        EngineModel.model_validate(source)


def test_relation_scoped_uniqueness_rejects_unbound_condition_attribute():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    relation = next(
        item
        for item in source["objectTypeRelations"]
        if item["relationTypeKey"] == "object-has-translation"
    )
    relation["features"]["uniqueWhenToAttributeEquals"]["attributeTypeKey"] = "missing"

    with pytest.raises(ValidationError, match="invalid uniqueWhenToAttributeEquals"):
        EngineModel.model_validate(source)


def test_unknown_application_object_type_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["applications"][0]["objectTypeKeys"].append("missing")

    with pytest.raises(ValidationError, match="unknown object types"):
        EngineModel.model_validate(source)


def test_unknown_attribute_binding_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["objectTypes"][0]["attributes"].append({"attributeTypeKey": "missing"})

    with pytest.raises(ValidationError, match="unknown attribute type"):
        EngineModel.model_validate(source)


def test_detail_composition_changes_are_preserved_without_renderer_changes():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    panels = source["applications"][0]["details"][2]["panels"]
    panels[0]["order"] = 90
    panels[0]["visible"] = False
    panels[3]["config"]["fields"] = ["value-name", "active"]
    panels[1]["config"]["columns"] = ["name", "external-id"]
    panels[1]["config"]["relationTypeKeys"] = ["system-value-maps-to-master"]

    model = EngineModel.model_validate(source)
    configured = model.applications[0].details[2].panels
    assert configured[0].order == 90
    assert configured[0].visible is False
    assert configured[3].config.fields == ("value-name", "active")
    assert configured[1].config.columns == ("name", "external-id")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda source: source["applications"][0]["details"][0]["header"].update(
                {"titleField": "missing"}
            ),
            "header references unavailable fields",
        ),
        (
            lambda source: next(
                panel
                for panel in source["applications"][0]["details"][0]["panels"]
                if panel["key"] == "attributes"
            )["config"].update({"fields": ["missing"]}),
            "references unavailable fields",
        ),
        (
            lambda source: source["applications"][0]["details"][0]["panels"][0]["config"].update(
                {"objectTypeKeys": ["master-value"], "columns": ["name", "master-id"]}
            ),
            "is not a configured child",
        ),
        (
            lambda source: source["applications"][0]["details"][2]["panels"][1]["config"].update(
                {"direction": "outgoing"}
            ),
            "is incompatible",
        ),
        (
            lambda source: source["applications"][0]["details"][0]["panels"][0].update(
                {"unsupported": True}
            ),
            "Extra inputs are not permitted",
        ),
        (
            lambda source: source["applications"][0]["details"][0]["panels"][1][
                "config"
            ].update({"columns": ["ancestor:missing"]}),
            "unknown ancestor object type",
        ),
    ],
)
def test_invalid_detail_composition_is_rejected(mutate, message):
    source = load_model(MODEL_PATH).model_dump(mode="json")
    mutate(source)

    with pytest.raises(ValidationError, match=message):
        EngineModel.model_validate(source)


def test_unique_json_attribute_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["attributeTypes"].append(
        {
            "key": "unique-json",
            "name": "Unique JSON",
            "valueType": "json",
            "features": {"unique": True},
        }
    )

    with pytest.raises(ValidationError, match="does not support uniqueness"):
        EngineModel.model_validate(source)


def test_minimum_maximum_on_non_numeric_attribute_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["attributeTypes"][0]["validation"] = {"minimum": 1}

    with pytest.raises(ValidationError, match="does not support numeric bounds"):
        EngineModel.model_validate(source)


@pytest.mark.parametrize("bound", ["1", "not-a-number", True, float("inf")])
def test_non_numeric_or_non_finite_numeric_bound_is_rejected(bound):
    source = load_model(MODEL_PATH).model_dump(mode="json")
    numeric_attribute = next(
        item for item in source["attributeTypes"] if item["key"] == "maximum-hierarchy-depth"
    )
    numeric_attribute["validation"]["minimum"] = bound

    with pytest.raises(ValidationError, match="must be a finite number"):
        EngineModel.model_validate(source)


def test_minimum_must_not_exceed_maximum():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    numeric_attribute = next(
        item for item in source["attributeTypes"] if item["key"] == "maximum-hierarchy-depth"
    )
    numeric_attribute["validation"] = {"minimum": 10, "maximum": 5}

    with pytest.raises(ValidationError, match="minimum must not exceed"):
        EngineModel.model_validate(source)
