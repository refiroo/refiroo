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
    assert len(model.attributeTypes) == 21
    assert len(model.objectTypes) == 9
    assert len(model.relationTypes) == 12
    assert len(model.objectTypeRelations) == 12
    assert [detail.objectTypeKey for detail in model.applications[0].details] == [
        "domain",
        "codelist",
        "master-value",
    ]
    assert model.applications[0].details[0].panels[0].type == "children"
    assert model.applications[0].details[1].panels[0].type == "children"


def test_unknown_application_object_type_is_rejected():
    source = load_model(MODEL_PATH).model_dump()
    source["applications"][0]["objectTypeKeys"].append("missing")

    with pytest.raises(ValidationError, match="unknown object types"):
        EngineModel.model_validate(source)


def test_unknown_attribute_binding_is_rejected():
    source = load_model(MODEL_PATH).model_dump()
    source["objectTypes"][0]["attributes"].append({"attributeTypeKey": "missing"})

    with pytest.raises(ValidationError, match="unknown attribute type"):
        EngineModel.model_validate(source)


def test_detail_composition_changes_are_preserved_without_renderer_changes():
    source = load_model(MODEL_PATH).model_dump()
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
    assert configured[3].config.fields == ["value-name", "active"]
    assert configured[1].config.columns == ["name", "external-id"]


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
            lambda source: source["applications"][0]["details"][0]["panels"][1][
                "config"
            ].update({"fields": ["missing"]}),
            "references unavailable fields",
        ),
        (
                lambda source: source["applications"][0]["details"][0]["panels"][0][
                    "config"
                ].update({"objectTypeKeys": ["master-value"], "columns": ["name", "master-id"]}),
            "is not a configured child",
        ),
        (
            lambda source: source["applications"][0]["details"][2]["panels"][1][
                "config"
            ].update({"direction": "outgoing"}),
            "is incompatible",
        ),
        (
            lambda source: source["applications"][0]["details"][0]["panels"][0].update(
                {"unsupported": True}
            ),
            "Extra inputs are not permitted",
        ),
    ],
)
def test_invalid_detail_composition_is_rejected(mutate, message):
    source = load_model(MODEL_PATH).model_dump()
    mutate(source)

    with pytest.raises(ValidationError, match=message):
        EngineModel.model_validate(source)
