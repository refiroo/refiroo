"""An export of a view (0.17 EX1, ``engine/jobs/export_views.py``, ``people.plan_people``): what a
view and the page's state make of the request, checked against a model without a database."""

import copy

import pytest
from configurations import generated

from app.engine.jobs import export_views, people
from app.engine.model.compiler import parse_model
from app.errors import ApiError
from app.models.exports import ExportRequest


def _model():
    configuration = generated("a")
    model = copy.deepcopy(configuration.model)
    k = configuration.keys
    application = next(item for item in model["applications"] if k["P"] in item["objectTypeKeys"])
    application["views"].append(
        {
            "key": "tree",
            "name": "A tree",
            "type": "tree",
            "config": {
                "rootObjectTypeKeys": [k["P"]],
                "objectTypeKeys": [k["C"], k["P"]],
                "labelField": "name",
                "pageSize": 20,
            },
        }
    )
    return parse_model(model), application["key"], k


def _request(application, view, **state):
    return ExportRequest.model_validate(
        {
            "workspaceKey": "w",
            "view": {"applicationKey": application, "viewKey": view, "state": state},
            "format": "xlsx",
        }
    )


def test_a_tree_is_a_sheet_per_type_with_parents_first_and_the_parent_by_name():
    """A tree of P above C: both types are written, P's sheet first, and C's sheet shows its parent."""
    model, application, k = _model()
    request = _request(application, "tree")
    view = export_views.resolve_view(model, request)
    effective = export_views.effective_request(model, request, view)
    assert [item.objectTypeKey for item in effective.scope.types] == [
        item.key for item in model.objectTypes if item.key in (k["P"], k["C"])
    ]
    workbook = people.plan_people(model, effective)
    order = [item.object_type_key for item in workbook.types]
    assert order.index(k["P"]) < order.index(k["C"])
    child = next(item for item in workbook.types if item.object_type_key == k["C"])
    parents = [column for column in child.columns if column.kind == "parent"]
    assert {column.key.removeprefix(people.PARENT_PREFIX) for column in parents} == {k["P"], k["Q"]}
    # A relationship loads back from the later sheet only, so the sources never wait on each other.
    for item in workbook.types:
        for column in item.columns:
            if column.related is not None and column.editable:
                far = column.related.target_type_keys
                assert all(
                    key not in order or order.index(key) <= order.index(item.object_type_key)
                    for key in far
                )


@pytest.mark.parametrize(
    ("state", "path"),
    [
        ({"columnIds": ["x"]}, "/view/state/columnIds"),
        ({"where": [{"field": "name", "op": "eq", "value": "x"}]}, "/view/state/where"),
    ],
)
def test_a_tree_refuses_state_it_does_not_read(state, path):
    model, application, _ = _model()
    with pytest.raises(ApiError) as refused:
        export_views.resolve_view(model, _request(application, "tree", **state))
    assert refused.value.code == "INVALID_EXPORT_LAYOUT" and refused.value.details["path"] == path
