"""A relationships table's references, judged by the model's validation (0.13 RV,
``validation/application_rules._check_relation_table_view``): each failure names the node it is in."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "journeys"))

from configurations import generated

from app.engine.model.compiler import compile_model

CONFIGURATION = generated("a")
KEYS = CONFIGURATION.keys


def _view(model: dict) -> dict:
    for application in model["applications"]:
        for view in application["views"]:
            if view["key"] == KEYS["Vrt"]:
                return view
    raise AssertionError("the configuration declares the view")


def _compile(change) -> list[tuple[str, str]]:
    model = copy.deepcopy(CONFIGURATION.model)
    change(_view(model)["config"], model)
    return [(item.path, item.message) for item in compile_model(model).diagnostics]


def _path(*tail: str) -> str:
    application = next(
        a["key"]
        for a in CONFIGURATION.model["applications"]
        if any(v["key"] == KEYS["Vrt"] for v in a["views"])
    )
    return f"/applications/{application}/views/{KEYS['Vrt']}/config" + "".join(
        f"/{t}" for t in tail
    )


def test_the_declared_view_is_valid():
    assert compile_model(CONFIGURATION.model).valid


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda c, _m: c.update(attributeColumns=["name"]), _path("attributeColumns", "0")),
        (
            lambda c, _m: c.update(attributeColumns=[KEYS["Bnn.weight"], KEYS["R.u"]]),
            _path("attributeColumns", "1"),
        ),
        (lambda c, _m: c.update(fromColumns=["name", "nothing"]), _path("fromColumns", "1")),
        (lambda c, _m: c.update(toColumns=[KEYS["H.code"]]), _path("toColumns", "0")),
        (lambda c, _m: c.update(filterFields=["name"]), _path("filterFields", "0")),
        (lambda c, _m: c.update(filterFields=["relation:nothing"]), _path("filterFields", "0")),
        (
            lambda c, _m: c.update(filterFields=[f"to:{KEYS['K.rank']}x"]),
            _path("filterFields", "0"),
        ),
        (lambda c, _m: c.update(sortFields=["from:name", "bogus:name"]), _path("sortFields", "1")),
        (lambda c, _m: c.update(defaultSort="-to:name-missing"), _path("defaultSort")),
        (lambda c, _m: c.update(relationTypeKey="nothing"), _path("relationTypeKey")),
    ],
    ids=[
        "attribute column the binding does not declare",
        "second attribute column foreign",
        "from column that is neither name nor an attribute of the type",
        "to column that is an attribute of the other end",
        "filter field with no place",
        "filter on an attribute of the relationship that is not declared",
        "filter on an attribute that is not on the end's type",
        "sort field with an unknown place",
        "default sort that is not a sort field",
        "unknown relation type",
    ],
)
def test_a_reference_that_does_not_resolve_names_its_node(change, path):
    found = _compile(change)
    assert found and found[0][0] == path, found


def test_a_binding_that_is_not_declared_is_refused_at_the_config():
    found = _compile(lambda c, _m: c.update(toObjectTypeKey=CONFIGURATION.key("R")))
    assert found and found[0][0] == _path("relationTypeKey"), found


def test_a_filter_needs_a_filterable_attribute_and_a_sort_does_not():
    def make_unfilterable(config, model):
        for attribute in model["attributeTypes"]:
            if attribute["key"] == KEYS["Bnn.weight"]:
                attribute["features"] = {"sortable": True}

    found = _compile(make_unfilterable)
    assert found and found[0][0] == _path("filterFields", "1"), found


def test_a_table_may_be_a_grid_and_no_other_layout_exists():
    assert _compile(lambda c, _m: c.update(layout="grid")) == []
    assert _compile(lambda c, _m: c.update(layout="rows")) == []
    found = _compile(lambda c, _m: c.update(layout="columns"))
    assert found and found[0][0].endswith("/config/layout"), found
