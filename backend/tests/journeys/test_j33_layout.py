"""J33 — Design a model in the editor (USER_JOURNEYS.md): the preview and layout (0.10 A4b, J33.10).

The editor previews a draft with the generic renderers, so it reads the draft compiled as
``GET /model`` serves the active model, with its placements; the read changes nothing. A type is
laid out by the view verbs, one step per request, and the record screen shows the same layout after
activation. A type without a detail page gets one by ``addDetailPage`` (D48). The tests name
structures of the configuration (``R``, ``K``) and elements they create under ``j33-`` keys.
"""

from typing import Any

import pytest
from scenario import ok, refused
from test_j33_operations import (
    _apply,
    _by_key,
    _draft,
    _draft_of_active,
    _empty_draft,
    _history,
    _model,
    _undo,
)

DISABLED = {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"}


def _draft_model(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/model"))


def _note_under_r(world) -> list[dict[str, Any]]:
    """A type under R with two attributes, one sortable, and a relation from it to K."""
    return [
        {
            "kind": "addObjectType",
            "applicationKey": world.app("R"),
            "key": "j33-note",
            "name": "Note",
            "pluralName": "Notes",
            "parent": {
                "objectTypes": [world.key("R")],
                "relationType": {"key": "j33-has-note", "name": "Has note", "reverseName": "Note of"},
            },
        },
        {
            "kind": "addAttributeType",
            "key": "j33-text",
            "name": "Note text",
            "valueType": "text",
            "features": {"filterable": True, "sortable": True},
        },
        {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-text"},
        {"kind": "addAttributeType", "key": "j33-code", "name": "Note code", "valueType": "text"},
        {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-code"},
        {"kind": "addRelationType", "key": "j33-cites", "name": "Cites", "reverseName": "Cited by"},
        {"kind": "allowRelation", "relationType": "j33-cites", "from": "j33-note", "to": world.key("K")},
    ]


def _page(model: dict[str, Any], application: str, type_key: str) -> dict[str, Any] | None:
    app = _by_key(model["applications"], application)
    return next((d for d in app.get("details") or [] if d["objectTypeKey"] == type_key), None)


def _table(model: dict[str, Any], application: str, type_key: str) -> dict[str, Any]:
    app = _by_key(model["applications"], application)
    return next(v for v in app["views"] if v["type"] == "table" and v["objectTypeKey"] == type_key)


def _panel_keys(page: dict[str, Any], region: str) -> list[str]:
    panels = [p for p in page["panels"] if p["region"] == region]
    return [p["key"] for p in sorted(panels, key=lambda p: p["order"])]


@pytest.mark.journey("J33.10", "J33.3")
@pytest.mark.structures("R", "K")
def test_the_drafts_model_is_read_compiled_with_its_placements_and_the_read_changes_nothing(world):
    """Given a draft of the active release with a type added under R. When the draft's model is
    read. Then it is valid, holds the new type with its generated table view, its placements list
    the type under R's type, its version is the draft's, and the draft's version and history are
    unchanged by the read."""
    draft = _draft_of_active(world)
    answer = ok(_apply(world, draft, draft["version"], *_note_under_r(world)))
    history = _history(world, draft)["items"]

    read = _draft_model(world, draft)
    assert read["valid"] is True, read["diagnostics"]
    assert read["version"] == answer["version"]
    assert read["diagnostics"] == []
    model = read["model"]
    assert "j33-note" in [t["key"] for t in model["objectTypes"]]
    assert _table(model, world.app("R"), "j33-note")["config"]["columns"][:1] == ["name"]
    places = _by_key(read["placements"]["applications"], world.app("R"), "applicationKey")
    r_place = _by_key(places["parents"], world.key("R"), "objectTypeKey")
    assert "j33-note" in r_place["childObjectTypeKeys"]

    assert _draft(world, draft)["version"] == answer["version"]
    assert _history(world, draft)["items"] == history


@pytest.mark.journey("J33.10", "J08")
@pytest.mark.structures("A1")
def test_a_draft_that_does_not_compile_is_read_without_a_model(world):
    """Given an empty draft. When an application is added alone. Then the draft's model answers
    200 with valid false, no model and no placements, and the diagnostics the step answered."""
    draft = _empty_draft(world)
    answer = ok(_apply(world, draft, draft["version"], {"kind": "addApplication", "name": "J33 Empty"}))
    read = _draft_model(world, draft)
    assert read["valid"] is False
    assert read.get("model") is None
    assert read.get("placements") is None
    assert [{k: v for k, v in d.items() if k != "element"} for d in read["diagnostics"]] == answer["diagnostics"]


@pytest.mark.journey("J33.10", "J33.4", "J08")
@pytest.mark.structures("R", "K")
def test_a_type_laid_out_step_by_step_shows_the_same_layout_after_activation(world):
    """Given a draft with a type under R and its detail page. When its panels are reordered, the
    relations panel moved to the side, the hierarchy hidden, a field moved into a new attributes
    panel in one request, a table column moved and one removed and the default sort set. Then each
    request is one step; one undo gives back the previous step's layout; and after install and
    activate the active model has the page and the view the draft's model held."""
    draft = _draft_of_active(world)
    app, model = world.app("R"), _model(world, draft)
    operations = _note_under_r(world)
    answer = ok(_apply(world, draft, draft["version"], *operations))
    if _page(_model(world, draft), app, "j33-note") is None:
        answer = ok(
            _apply(world, draft, answer["version"], {"kind": "addDetailPage", "applicationKey": app, "objectType": "j33-note"})
        )
    page = _page(_model(world, draft), app, "j33-note")
    assert _panel_keys(page, "main") == ["j33-cites"]
    assert _panel_keys(page, "side") == ["attributes", "hierarchy"]

    detail = {"applicationKey": app, "detail": "j33-note"}
    view_key = _table(_model(world, draft), app, "j33-note")["key"]
    view = {"applicationKey": app, "view": view_key}
    steps = [
        [{"kind": "moveViewItem", **detail, "list": "panels", "item": "j33-cites", "position": 0}],
        [
            {"kind": "setViewProperty", **detail, "panel": "j33-cites", "property": "region", "value": "side"},
        ],
        [{"kind": "setViewProperty", **detail, "panel": "hierarchy", "property": "visible", "value": False}],
        [
            {
                "kind": "insertViewItem",
                **detail,
                "list": "panels",
                "item": {"key": "j33-more", "title": "More", "type": "attributes", "region": "main", "config": {"fields": []}},
            },
            {"kind": "removeViewItem", **detail, "panel": "attributes", "list": "fields", "item": "j33-text"},
            {"kind": "insertViewItem", **detail, "panel": "j33-more", "list": "fields", "item": "j33-text"},
        ],
        [{"kind": "moveViewItem", **view, "list": "columns", "item": "j33-text", "position": 0}],
        [{"kind": "removeViewItem", **view, "list": "columns", "item": "j33-code"}],
        [{"kind": "setViewProperty", **view, "property": "defaultSort", "value": "j33-text"}],
    ]
    before_last = None
    for request in steps:
        before_last = _draft_model(world, draft)["model"]
        step = ok(_apply(world, draft, answer["version"], *request))
        assert step["version"] == answer["version"] + 1
        assert step["valid"] is True, step["diagnostics"]
        answer = step
    entries = _history(world, draft, **{"from": "end"})["items"]
    grouped = [
        e
        for e in entries
        if e["parameters"].get("panel") == "j33-more"
        or (e["kind"] == "removeViewItem" and e["parameters"].get("item") == "j33-text")
    ]
    (group_step,) = {e["step"] for e in grouped}
    assert [e["kind"] for e in entries if e["step"] == group_step] == ["insertViewItem", "removeViewItem", "insertViewItem"]

    laid_out = _draft_model(world, draft)["model"]
    page = _page(laid_out, app, "j33-note")
    assert set(_panel_keys(page, "side")) == {"attributes", "hierarchy", "j33-cites"}
    assert _by_key(page["panels"], "hierarchy")["visible"] is False
    assert _by_key(page["panels"], "j33-more")["config"]["fields"] == ["j33-text"]
    assert "j33-text" not in _by_key(page["panels"], "attributes")["config"]["fields"]
    table = _table(laid_out, app, "j33-note")
    assert table["config"]["columns"][0] == "j33-text"
    assert "j33-code" not in table["config"]["columns"]
    assert table["config"]["defaultSort"] == "j33-text"

    undone = ok(_undo(world, draft, answer["version"]))
    assert _table(_draft_model(world, draft)["model"], app, "j33-note") == _table(before_last, app, "j33-note")
    redone = ok(world.api.post(f"/model-drafts/{draft['id']}/redo", {"expectedVersion": undone["version"]}))
    answer = ok(
        _apply(
            world,
            draft,
            redone["version"],
            {"kind": "setRelease", "version": model["release"]["version"] + "-j33"},
        )
    )
    expected = _draft_model(world, draft)["model"]
    release = ok(world.api.post(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}), 201)
    ok(world.activate(release["id"]))
    active = ok(world.api.get("/model"))
    assert _page(active, app, "j33-note") == _page(expected, app, "j33-note")
    assert _table(active, app, "j33-note") == _table(expected, app, "j33-note")


@pytest.mark.journey("J33.10", "J33.4", "J33.8")
@pytest.mark.structures("R", "K")
def test_a_type_without_a_detail_page_gets_the_generated_one(world):
    """Given a draft with a type under R. When its detail page is removed and added again by
    addDetailPage. Then the page is the one the server generates for a new type; undo removes it;
    and addDetailPage on a type that has a page is refused alreadyPresent with nothing applied."""
    draft = _draft_of_active(world)
    app = world.app("R")
    answer = ok(_apply(world, draft, draft["version"], *_note_under_r(world)))
    if _page(_model(world, draft), app, "j33-note") is not None:
        answer = ok(
            _apply(world, draft, answer["version"], {"kind": "removeDetailPage", "applicationKey": app, "objectType": "j33-note"})
        )
    assert _page(_model(world, draft), app, "j33-note") is None

    added = ok(_apply(world, draft, answer["version"], {"kind": "addDetailPage", "applicationKey": app, "objectType": "j33-note"}))
    page = _page(_model(world, draft), app, "j33-note")
    assert [(p["key"], p["type"], p["region"]) for p in page["panels"]] == [
        ("attributes", "attributes", "side"),
        ("hierarchy", "hierarchy", "side"),
        ("j33-cites", "relations", "main"),
    ]
    assert _by_key(page["panels"], "attributes")["config"]["fields"] == ["j33-text", "j33-code"]

    error = refused(
        _apply(world, draft, added["version"], {"kind": "addDetailPage", "applicationKey": app, "objectType": "j33-note"}),
        422,
        "INVALID_OPERATION",
    )
    assert error["details"]["reason"] == "alreadyPresent"
    assert _draft(world, draft)["version"] == added["version"]

    ok(_undo(world, draft, added["version"]))
    assert _page(_model(world, draft), app, "j33-note") is None


@pytest.mark.journey("J33")
@pytest.mark.structures("A1")
def test_the_model_of_an_unknown_draft_is_not_found(world):
    refused(world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/model"), 404, "MODEL_DRAFT_NOT_FOUND")


@pytest.mark.journey("J33", "J08.7")
@pytest.mark.structures("A1")
@pytest.mark.settings(**DISABLED)
def test_with_model_administration_disabled_the_drafts_model_is_absent(world):
    response = world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/model")
    assert response.status_code == 404, response.text
    assert "MODEL_DRAFT_NOT_FOUND" not in response.text
