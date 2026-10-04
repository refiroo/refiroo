"""Pins the diagnostic each model reference rule reports, and where it points.

The path of a diagnostic is a published API field that the Models workbench navigates by, so
every rule gets one case here. A rule that stops producing its pointer is a contract break even
when the model is still correctly rejected.
"""

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.engine.model.compiler import compile_model

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"


@dataclass(frozen=True)
class Case:
    name: str
    mutate: Callable[[dict], None]
    code: str
    path: str


@pytest.fixture(scope="module")
def source() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _duplicate_attribute_type(m):
    m["attributeTypes"].append(copy.deepcopy(m["attributeTypes"][0]))


def _duplicate_object_type(m):
    m["objectTypes"].append(copy.deepcopy(m["objectTypes"][0]))


def _duplicate_relation_type_key(m):
    m["relationTypes"].append(copy.deepcopy(m["relationTypes"][0]))


def _duplicate_application(m):
    m["applications"].append(copy.deepcopy(m["applications"][0]))


def _duplicate_view(m):
    app = m["applications"][0]
    app["views"].append(copy.deepcopy(app["views"][0]))


def _duplicate_attribute_binding(m):
    ot = next(i for i in m["objectTypes"] if i["attributes"])
    ot["attributes"].append(copy.deepcopy(ot["attributes"][0]))


def _unique_on_json(m):
    at = m["attributeTypes"][0]
    at["valueType"] = "json"
    at["features"] = dict(at.get("features") or {}, unique=True)


def _bounds_on_text(m):
    at = next(i for i in m["attributeTypes"] if i.get("valueType", "text") == "text")
    at["validation"] = dict(at.get("validation") or {}, minimum=1)


def _bound_not_numeric(m):
    at = m["attributeTypes"][0]
    at["valueType"] = "integer"
    at["validation"] = dict(at.get("validation") or {}, minimum="nope")


def _minimum_exceeds_maximum(m):
    at = m["attributeTypes"][0]
    at["valueType"] = "integer"
    at["validation"] = dict(at.get("validation") or {}, minimum=10, maximum=1)


def _duplicate_reverse_key(m):
    m["relationTypes"][1]["reverseKey"] = m["relationTypes"][0]["key"]


def _duplicate_object_type_relation(m):
    m["objectTypeRelations"].append(copy.deepcopy(m["objectTypeRelations"][0]))


def _object_type_unknown_attribute(m):
    ot = next(i for i in m["objectTypes"] if i["attributes"])
    ot["attributes"][0]["attributeTypeKey"] = "no-such-attribute"


def _display_attribute_not_attached(m):
    ot = next(i for i in m["objectTypes"] if i.get("displayAttributeTypeKey"))
    ot["displayAttributeTypeKey"] = m["attributeTypes"][-1]["key"]
    if any(a["attributeTypeKey"] == ot["displayAttributeTypeKey"] for a in ot["attributes"]):
        ot["displayAttributeTypeKey"] = "definitely-not-bound"


def _at_least_one_of_not_list(m):
    m["objectTypes"][0]["validation"] = {"atLeastOneOf": "nope"}


def _at_least_one_of_duplicates(m):
    ot = next(i for i in m["objectTypes"] if i["attributes"])
    key = ot["attributes"][0]["attributeTypeKey"]
    ot["validation"] = dict(ot.get("validation") or {}, atLeastOneOf=[key, key])


def _at_least_one_of_unbound(m):
    m["objectTypes"][0]["validation"] = {"atLeastOneOf": ["not-bound-here"]}


def _incompatible_parent_relation(m):
    ot = next(i for i in m["objectTypes"] if i.get("behavior", {}).get("parentRelationTypeKeys"))
    ot["behavior"] = dict(ot["behavior"], parentRelationTypeKeys=["no-such-relation"])


def _otr_unknown_relation_type(m):
    m["objectTypeRelations"][0]["relationTypeKey"] = "no-such-relation-type"


def _otr_unknown_source(m):
    m["objectTypeRelations"][0]["fromObjectTypeKey"] = "no-such-source"


def _otr_unknown_target(m):
    m["objectTypeRelations"][0]["toObjectTypeKey"] = "no-such-target"


def _otr_unknown_attributes(m):
    m["objectTypeRelations"][0]["attributeTypeKeys"] = ["no-such-attribute"]


def _otr_unknown_ancestor(m):
    otr = next(i for i in m["objectTypeRelations"] if i.get("features", {}).get("uniqueToAncestorTypeKey"))
    otr["features"] = dict(otr["features"], uniqueToAncestorTypeKey="no-such-object-type")


def _otr_invalid_unique_condition(m):
    otr = next(i for i in m["objectTypeRelations"] if i.get("features", {}).get("uniqueWhenToAttributeEquals"))
    otr["features"] = dict(otr["features"], uniqueWhenToAttributeEquals={"attributeTypeKey": "nope", "value": 1})


def _application_unknown_object_type(m):
    m["applications"][0]["objectTypeKeys"] = list(m["applications"][0]["objectTypeKeys"]) + ["no-such-object-type"]


def _application_unknown_default_view(m):
    m["applications"][0]["defaultView"] = "no-such-view"


def _view_unknown_object_type(m):
    view = next(v for a in m["applications"] for v in a["views"] if v.get("objectTypeKey"))
    view["objectTypeKey"] = "no-such-object-type"


def _view_unavailable_fields(m):
    view = next(v for a in m["applications"] for v in a["views"] if v.get("objectTypeKey") and v.get("config", {}).get("columns"))
    view["config"] = dict(view["config"], columns=list(view["config"]["columns"]) + ["no-such-field"])


def _detail_duplicated(m):
    app = next(a for a in m["applications"] if a.get("details"))
    app["details"].append(copy.deepcopy(app["details"][0]))


def _detail_unknown_object_type(m):
    app = next(a for a in m["applications"] if a.get("details"))
    app["details"][0]["objectTypeKey"] = "no-such-object-type"


def _detail_header_unavailable_field(m):
    app = next(a for a in m["applications"] if a.get("details"))
    app["details"][0]["header"] = dict(app["details"][0].get("header") or {}, subtitleField="no-such-field")


def _detail_panel_duplicated(m):
    app = next(a for a in m["applications"] if a.get("details"))
    detail = next(d for d in app["details"] if len(d.get("panels") or []) >= 1)
    detail["panels"].append(copy.deepcopy(detail["panels"][0]))


def _detail_attributes_panel_unknown_field(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for p in d.get("panels") or []:
                if p["type"] == "attributes":
                    p["config"] = dict(p["config"], fields=list(p["config"].get("fields") or []) + ["no-such-field"])
                    return


def _detail_relations_panel_unknown_relation(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for p in d.get("panels") or []:
                if p["type"] == "relations":
                    p["config"] = dict(p["config"], relationTypeKeys=["no-such-relation"])
                    return


def _missing_required_field(m):
    del m["schemaVersion"]


def _unknown_top_level_field(m):
    m["surpriseField"] = True


def _view_duplicate_fields(m):
    view = next(v for a in m["applications"] for v in a["views"] if v.get("objectTypeKey") and v.get("config", {}).get("columns"))
    cols = list(view["config"]["columns"])
    view["config"] = dict(view["config"], columns=cols + [cols[0]])


def _view_unknown_ancestor_field(m):
    view = next(v for a in m["applications"] for v in a["views"] if v.get("objectTypeKey") and v.get("config", {}).get("columns"))
    view["config"] = dict(view["config"], columns=list(view["config"]["columns"]) + ["ancestor:no-such-type"])


def _detail_not_available_in_application(m):
    app = next(a for a in m["applications"] if a.get("details"))
    keys = [k for k in app["objectTypeKeys"] if k != app["details"][0]["objectTypeKey"]]
    app["objectTypeKeys"] = keys
    # A tree over the removed type would fail first, at its own node type.
    app["views"] = [v for v in app["views"] if v["type"] != "tree"]


def _detail_header_duplicate_fields(m):
    app = next(a for a in m["applications"] if a.get("details"))
    app["details"][0]["header"] = dict(app["details"][0].get("header") or {}, titleField="name", subtitleField="name")


def _children_panel_unknown_object_type(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for pnl in d.get("panels") or []:
                if pnl["type"] == "children":
                    pnl["config"] = dict(pnl["config"], objectTypeKeys=["no-such-object-type"])
                    return


def _children_panel_not_configured_child(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for pnl in d.get("panels") or []:
                if pnl["type"] == "children":
                    other = next(k for k in app["objectTypeKeys"] if k not in pnl["config"]["objectTypeKeys"] and k != d["objectTypeKey"])
                    pnl["config"] = dict(pnl["config"], objectTypeKeys=[other], columns=["name"])
                    return


def _children_panel_empty_object_types(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for pnl in d.get("panels") or []:
                if pnl["type"] == "children":
                    pnl["config"] = dict(pnl["config"], objectTypeKeys=[])
                    return


def _relations_panel_incompatible_direction(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for pnl in d.get("panels") or []:
                if pnl["type"] == "relations":
                    other = next(rt["key"] for rt in m["relationTypes"] if rt["key"] not in pnl["config"]["relationTypeKeys"])
                    pnl["config"] = dict(pnl["config"], relationTypeKeys=[other])
                    return


def _table_panel_object_type_outside_application(m):
    for app in m["applications"]:
        for d in app.get("details") or []:
            for pnl in d.get("panels") or []:
                if pnl["type"] == "table":
                    other = next(ot["key"] for ot in m["objectTypes"] if ot["key"] not in app["objectTypeKeys"])
                    pnl["config"] = dict(pnl["config"], objectTypeKey=other)
                    return


CASES = [
    Case("duplicate_attribute_type", _duplicate_attribute_type, "DUPLICATE_KEY", '/attributeTypes/description'),
    Case("duplicate_object_type", _duplicate_object_type, "DUPLICATE_KEY", '/objectTypes/domain'),
    Case("duplicate_relation_type_key", _duplicate_relation_type_key, "DUPLICATE_KEY", '/relationTypes/domain-contains-codelist'),
    Case("duplicate_application", _duplicate_application, "DUPLICATE_KEY", '/applications/rdm-master'),
    Case("duplicate_view", _duplicate_view, "DUPLICATE_KEY", '/applications/rdm-master/views/domains'),
    Case("duplicate_attribute_binding", _duplicate_attribute_binding, "DUPLICATE_KEY", '/objectTypes/domain/attributes/domain-code'),
    Case("unique_on_json", _unique_on_json, "INVALID_MODEL", '/attributeTypes/description/features/unique'),
    Case("bounds_on_text", _bounds_on_text, "INVALID_MODEL", '/attributeTypes/domain-code/validation/minimum'),
    Case("bound_not_numeric", _bound_not_numeric, "INVALID_MODEL", '/attributeTypes/description/validation/minimum'),
    Case("minimum_exceeds_maximum", _minimum_exceeds_maximum, "INVALID_MODEL", '/attributeTypes/description/validation/minimum'),
    Case("duplicate_reverse_key", _duplicate_reverse_key, "DUPLICATE_KEY", '/relationTypes/codelist-contains-value/reverseKey'),
    Case("duplicate_object_type_relation", _duplicate_object_type_relation, "DUPLICATE_KEY", '/objectTypeRelations/domain-contains-codelist/domain/codelist'),
    Case("object_type_unknown_attribute", _object_type_unknown_attribute, "UNKNOWN_ATTRIBUTE_TYPE", '/objectTypes/domain/attributes/no-such-attribute/attributeTypeKey'),
    Case("display_attribute_not_attached", _display_attribute_not_attached, "INVALID_MODEL", '/objectTypes/domain/displayAttributeTypeKey'),
    Case("at_least_one_of_not_list", _at_least_one_of_not_list, "INVALID_MODEL", '/objectTypes/domain/validation/atLeastOneOf'),
    Case("at_least_one_of_duplicates", _at_least_one_of_duplicates, "DUPLICATE_KEY", '/objectTypes/domain/validation/atLeastOneOf'),
    Case("at_least_one_of_unbound", _at_least_one_of_unbound, "UNKNOWN_ATTRIBUTE_TYPE", '/objectTypes/domain/validation/atLeastOneOf'),
    Case("incompatible_parent_relation", _incompatible_parent_relation, "INVALID_REFERENCE", '/objectTypes/codelist/behavior/parentRelationTypeKeys/no-such-relation'),
    Case("otr_unknown_relation_type", _otr_unknown_relation_type, "UNKNOWN_RELATION_TYPE", '/objectTypeRelations/no-such-relation-type/domain/codelist/relationTypeKey'),
    Case("otr_unknown_source", _otr_unknown_source, "UNKNOWN_OBJECT_TYPE", '/objectTypeRelations/domain-contains-codelist/no-such-source/codelist/fromObjectTypeKey'),
    Case("otr_unknown_target", _otr_unknown_target, "UNKNOWN_OBJECT_TYPE", '/objectTypeRelations/domain-contains-codelist/domain/no-such-target/toObjectTypeKey'),
    Case("otr_unknown_attributes", _otr_unknown_attributes, "UNKNOWN_ATTRIBUTE_TYPE", '/objectTypeRelations/domain-contains-codelist/domain/codelist/attributeTypeKeys/no-such-attribute'),
    Case("otr_unknown_ancestor", _otr_unknown_ancestor, "INVALID_REFERENCE", '/objectTypeRelations/object-has-translation/domain/translation/features/uniqueToAncestorTypeKey'),
    Case("otr_invalid_unique_condition", _otr_invalid_unique_condition, "INVALID_MODEL", '/objectTypeRelations/object-has-translation/domain/translation/features/uniqueWhenToAttributeEquals'),
    Case("application_unknown_object_type", _application_unknown_object_type, "UNKNOWN_OBJECT_TYPE", '/applications/rdm-master/objectTypeKeys/3'),
    Case("application_unknown_default_view", _application_unknown_default_view, "INVALID_MODEL", '/applications/rdm-master/defaultView'),
    Case("view_unknown_object_type", _view_unknown_object_type, "UNKNOWN_OBJECT_TYPE", '/applications/rdm-master/views/domains/objectTypeKey'),
    Case("view_unavailable_fields", _view_unavailable_fields, "INVALID_MODEL", '/applications/rdm-master/views/domains/config/columns'),
    Case("detail_duplicated", _detail_duplicated, "DUPLICATE_KEY", '/applications/rdm-master/details/domain'),
    Case("detail_unknown_object_type", _detail_unknown_object_type, "UNKNOWN_OBJECT_TYPE", '/applications/rdm-master/details/no-such-object-type'),
    Case("detail_header_unavailable_field", _detail_header_unavailable_field, "INVALID_MODEL", '/applications/rdm-master/details/domain/header'),
    Case("detail_panel_duplicated", _detail_panel_duplicated, "DUPLICATE_KEY", '/applications/rdm-master/details/domain/panels/codelists'),
    Case("detail_attributes_panel_unknown_field", _detail_attributes_panel_unknown_field, "INVALID_MODEL", '/applications/rdm-master/details/domain/panels/attributes'),
    Case("detail_relations_panel_unknown_relation", _detail_relations_panel_unknown_relation, "UNKNOWN_RELATION_TYPE", '/applications/rdm-master/details/domain/panels/system-representations'),
    Case("missing_required_field", _missing_required_field, "missing_field", '/schemaVersion'),
    Case("unknown_top_level_field", _unknown_top_level_field, "unknown_field", '/surpriseField'),
    Case("view_duplicate_fields", _view_duplicate_fields, "DUPLICATE_KEY", '/applications/rdm-master/views/domains/config/columns'),
    Case("view_unknown_ancestor_field", _view_unknown_ancestor_field, "INVALID_REFERENCE", '/applications/rdm-master/views/domains/config/columns'),
    Case("detail_not_available_in_application", _detail_not_available_in_application, "INVALID_MODEL", '/applications/rdm-master/details/domain'),
    Case("detail_header_duplicate_fields", _detail_header_duplicate_fields, "DUPLICATE_KEY", '/applications/rdm-master/details/domain/header'),
    Case("children_panel_unknown_object_type", _children_panel_unknown_object_type, "UNKNOWN_OBJECT_TYPE", '/applications/rdm-master/details/domain/panels/codelists'),
    Case("children_panel_not_configured_child", _children_panel_not_configured_child, "INVALID_MODEL", '/applications/rdm-master/details/domain/panels/codelists'),
    Case("children_panel_empty_object_types", _children_panel_empty_object_types, "INVALID_MODEL", '/applications/rdm-master/details/domain/panels/codelists'),
    Case("relations_panel_incompatible_direction", _relations_panel_incompatible_direction, "INVALID_MODEL", '/applications/rdm-master/details/domain/panels/system-representations'),
    Case("table_panel_object_type_outside_application", _table_panel_object_type_outside_application, "INVALID_MODEL", '/applications/rdm-systems/details/system/panels/values'),
]


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_reference_rule_reports_code_and_path(case: Case, source: dict):
    candidate = copy.deepcopy(source)
    case.mutate(candidate)

    compiled = compile_model(candidate)

    assert not compiled.valid, f"{case.name} should be rejected"
    assert len(compiled.diagnostics) == 1
    diagnostic = compiled.diagnostics[0]
    assert diagnostic.severity == "error"
    assert (diagnostic.code, diagnostic.path) == (case.code, case.path)


def test_every_rule_module_is_covered_by_a_case():
    """Guards against a rule module being added without a pinned diagnostic."""
    from app.engine.model import validation as model_validation

    assert len(CASES) >= len(model_validation.RULES)
    assert len({case.name for case in CASES}) == len(CASES)


def test_valid_model_produces_no_diagnostics(source: dict):
    compiled = compile_model(source)
    assert compiled.valid
    assert compiled.diagnostics == ()
