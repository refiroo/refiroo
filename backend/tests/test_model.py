from copy import deepcopy
from pathlib import Path

import pytest

from app.models.schema import EngineModel
from app.services.model.compiler import ModelValidationError, compile_model, parse_model
from app.services.model.diff import semantic_diff
from app.services.model.loader import load_model

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
    assert model.schemaVersion == "0.6"
    assert model.release.version == "0.7.0"
    assert {view.type for app in model.applications for view in app.views} == {"table", "mappingGrid"}


def test_schema_dispatch_and_strict_table_shape_are_explicit():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    legacy = deepcopy(source)
    legacy["schemaVersion"] = "0.4"
    unsupported = compile_model(legacy)
    assert [(item.code, item.path) for item in unsupported.diagnostics] == [
        ("unsupported_schema_version", "/schemaVersion")
    ]

    unimplemented = deepcopy(source)
    unimplemented["applications"][0]["views"][0]["type"] = "dashboard"
    invalid_type = compile_model(unimplemented)
    assert "/applications/0/views/0" in invalid_type.diagnostics[0].path

    extra = deepcopy(source)
    extra["applications"][0]["views"][0]["config"]["endpoint"] = "/internal"
    invalid_extra = compile_model(extra)
    assert invalid_extra.diagnostics[0].code == "unknown_field"
    assert invalid_extra.diagnostics[0].path.endswith("/config/endpoint")


def test_compiler_returns_stable_cross_reference_diagnostic_path():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["applications"][0]["objectTypeKeys"].append("missing")

    result = compile_model(source)

    assert result.valid is False
    assert result.model is None
    assert result.model_hash is None
    assert result.diagnostics[0].code == "unknown_object_type"
    assert result.diagnostics[0].path == "/applications/rdm-master/objectTypeKeys/3"


def test_compiler_hash_is_canonical_and_semantic_diff_is_key_based():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    reordered = deepcopy(source)
    reordered["attributeTypes"].reverse()

    first = compile_model(source)
    second = compile_model(reordered)

    assert first.valid and second.valid
    assert first.model_hash != second.model_hash
    assert semantic_diff(first.canonical_model, second.canonical_model) == ()


def test_semantic_diff_uses_stable_nested_keys():
    before = load_model(MODEL_PATH).model_dump(mode="json")
    after = deepcopy(before)
    after["applications"][0]["views"][0]["name"] = "Renamed view"

    changes = semantic_diff(before, after)

    assert [(item.kind, item.path) for item in changes] == [
        ("changed", "/applications/rdm-master/views/domains/name")
    ]


def test_semantic_diff_treats_key_membership_arrays_as_unordered():
    before = {
        "objectTypeRelations": [
            {
                "relationTypeKey": "links",
                "fromObjectTypeKey": "source",
                "toObjectTypeKey": "target",
                "attributeTypeKeys": ["first", "second"],
            }
        ]
    }
    after = deepcopy(before)
    after["objectTypeRelations"][0]["attributeTypeKeys"].reverse()

    assert semantic_diff(before, after) == ()


def test_compiler_infers_paths_for_top_level_validation_failures():
    duplicate = load_model(MODEL_PATH).model_dump(mode="json")
    duplicate["attributeTypes"].append(deepcopy(duplicate["attributeTypes"][0]))
    duplicate_result = compile_model(duplicate)

    detail = load_model(MODEL_PATH).model_dump(mode="json")
    detail["applications"][0]["details"][0]["header"]["titleField"] = "missing"
    detail_result = compile_model(detail)

    assert duplicate_result.diagnostics[0].path == "/attributeTypes/description"
    assert detail_result.diagnostics[0].path == "/applications/rdm-master/details/domain/header"


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

    with pytest.raises(ModelValidationError, match="references unbound attributes"):
        parse_model(source)


def test_relation_scoped_uniqueness_rejects_unknown_ancestor_type():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    relation = next(
        item
        for item in source["objectTypeRelations"]
        if item["relationTypeKey"] == "object-has-translation"
    )
    relation["features"]["uniqueToAncestorTypeKey"] = "missing"

    with pytest.raises(ModelValidationError, match="unknown unique ancestor object type"):
        parse_model(source)


def test_relation_scoped_uniqueness_rejects_unbound_condition_attribute():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    relation = next(
        item
        for item in source["objectTypeRelations"]
        if item["relationTypeKey"] == "object-has-translation"
    )
    relation["features"]["uniqueWhenToAttributeEquals"]["attributeTypeKey"] = "missing"

    with pytest.raises(ModelValidationError, match="invalid uniqueWhenToAttributeEquals"):
        parse_model(source)


def test_unknown_application_object_type_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["applications"][0]["objectTypeKeys"].append("missing")

    with pytest.raises(ModelValidationError, match="unknown object types"):
        parse_model(source)


def test_unknown_attribute_binding_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["objectTypes"][0]["attributes"].append({"attributeTypeKey": "missing"})

    with pytest.raises(ModelValidationError, match="unknown attribute type"):
        parse_model(source)


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

    with pytest.raises(ModelValidationError, match=message):
        parse_model(source)


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

    with pytest.raises(ModelValidationError, match="does not support uniqueness"):
        parse_model(source)


def test_minimum_maximum_on_non_numeric_attribute_is_rejected():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["attributeTypes"][0]["validation"] = {"minimum": 1}

    with pytest.raises(ModelValidationError, match="does not support numeric bounds"):
        parse_model(source)


@pytest.mark.parametrize("bound", ["1", "not-a-number", True, float("inf")])
def test_non_numeric_or_non_finite_numeric_bound_is_rejected(bound):
    source = load_model(MODEL_PATH).model_dump(mode="json")
    numeric_attribute = next(
        item for item in source["attributeTypes"] if item["key"] == "maximum-hierarchy-depth"
    )
    numeric_attribute["validation"]["minimum"] = bound

    with pytest.raises(ModelValidationError, match="must be a finite number"):
        parse_model(source)


def test_minimum_must_not_exceed_maximum():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    numeric_attribute = next(
        item for item in source["attributeTypes"] if item["key"] == "maximum-hierarchy-depth"
    )
    numeric_attribute["validation"] = {"minimum": 10, "maximum": 5}

    with pytest.raises(ModelValidationError, match="minimum must not exceed"):
        parse_model(source)


# --- Schema 0.6: mappingGrid view contract ---


def test_schema_05_model_still_parses_and_activates():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    source["schemaVersion"] = "0.5"
    source["applications"] = [
        {**app, "views": [v for v in app["views"] if v["type"] == "table"]}
        for app in source["applications"]
    ]
    model = parse_model(source)
    assert model.schemaVersion == "0.5"


def test_schema_06_mapping_grid_views_parse():
    model = load_model(MODEL_PATH)
    assert model.schemaVersion == "0.6"
    mapping_views = [
        view for app in model.applications for view in app.views if view.type == "mappingGrid"
    ]
    assert len(mapping_views) == 2
    system_view = next(v for v in mapping_views if v.key == "system-to-master-mapping")
    assert system_view.config.relationTypeKey == "system-value-maps-to-master"
    assert system_view.config.direction == "outgoing"
    master_view = next(v for v in mapping_views if v.key == "master-to-system-mapping")
    assert master_view.config.direction == "incoming"


def _mapping_grid_source():
    source = load_model(MODEL_PATH).model_dump(mode="json")
    return source


def _find_mapping_view(source, app_key, view_key):
    app = next(a for a in source["applications"] if a["key"] == app_key)
    return next(v for v in app["views"] if v["key"] == view_key)


def test_mapping_grid_rejects_unknown_relation_type():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["relationTypeKey"] = "nonexistent-relation"
    result = compile_model(source)
    assert not result.valid
    assert result.diagnostics[0].code == "unknown_relation_type"


def test_mapping_grid_rejects_unknown_object_type():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["fromObjectTypeKey"] = "nonexistent-type"
    result = compile_model(source)
    assert not result.valid
    assert result.diagnostics[0].code == "unknown_object_type"


def test_mapping_grid_rejects_unmatched_binding():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["fromObjectTypeKey"] = "domain"
    view["config"]["toObjectTypeKey"] = "system"
    result = compile_model(source)
    assert not result.valid
    assert "not declared in objectTypeRelations" in result.diagnostics[0].message


def test_mapping_grid_rejects_containment_relation():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["relationTypeKey"] = "system-contains-value"
    view["config"]["fromObjectTypeKey"] = "system"
    view["config"]["toObjectTypeKey"] = "system-value"
    result = compile_model(source)
    assert not result.valid
    assert "containment" in result.diagnostics[0].message


def test_mapping_grid_rejects_required_ownership_binding():
    source = _mapping_grid_source()
    binding = next(
        b for b in source["objectTypeRelations"]
        if b["relationTypeKey"] == "system-value-maps-to-master"
    )
    binding["required"] = True
    binding["cardinality"] = "one-to-many"
    result = compile_model(source)
    assert not result.valid
    assert "required-ownership" in result.diagnostics[0].message


def test_mapping_grid_rejects_invalid_source_column():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["sourceColumns"] = ["name", "nonexistent-attr"]
    result = compile_model(source)
    assert not result.valid
    assert "unavailable fields" in result.diagnostics[0].message


def test_mapping_grid_rejects_nonsearchable_candidate_field():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["candidateSearchFields"] = ["name", "sort-order"]
    result = compile_model(source)
    assert not result.valid
    assert "not attached to target" in result.diagnostics[0].message or "not searchable" in result.diagnostics[0].message


def test_mapping_grid_rejects_extra_config_field():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["unknownField"] = True
    result = compile_model(source)
    assert not result.valid


def test_mapping_grid_rejects_duplicate_source_columns():
    source = _mapping_grid_source()
    view = _find_mapping_view(source, "rdm-systems", "system-to-master-mapping")
    view["config"]["sourceColumns"] = ["name", "name"]
    result = compile_model(source)
    assert not result.valid
