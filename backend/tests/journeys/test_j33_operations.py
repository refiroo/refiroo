"""J33 — Design a model in the editor (USER_JOURNEYS.md): the operation API on model drafts (0.10 A2).

A draft changes through typed operations, each request one step of its history with the inverse of
every entry; undo and redo apply inverses; a draft-only operation on an element of the draft's base
release is refused with its impact. The tests name structures of the configuration (``R``, ``K``,
``R.u``) and elements they create themselves under ``j33-`` keys, never a configuration's keys.
"""

import copy
from typing import Any

import pytest
from scenario import ok, refused


def _active_release(world) -> dict[str, Any]:
    active = world.workspace_model()["releaseId"]
    return ok(world.api.get(f"/model-releases/{active}", includeModel=True))


def _draft_of_active(world, name: str = "Design") -> dict[str, Any]:
    release = _active_release(world)
    body = {"name": name, "model": release["model"], "baseReleaseId": release["id"]}
    return ok(world.api.post("/model-drafts", body), 201)


def _empty_draft(world) -> dict[str, Any]:
    model = {
        "schemaVersion": "0.10",
        "release": {"key": "j33-empty", "name": "Built by operations", "version": "1.0.0"},
        "product": {"name": "Built by operations"},
        "attributeTypes": [],
        "objectTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [],
    }
    return ok(world.api.post("/model-drafts", {"name": "Empty", "model": model}), 201)


def _apply(world, draft: dict[str, Any], version: int, *operations: dict[str, Any]):
    return world.api.post(
        f"/model-drafts/{draft['id']}/operations",
        {"expectedVersion": version, "operations": list(operations)},
    )


def _model(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}"))["model"]


def _draft(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}"))


def _by_key(items: list[dict[str, Any]], key: str, field: str = "key") -> dict[str, Any]:
    return next(item for item in items if item[field] == key)


def _application(model: dict[str, Any], key: str) -> dict[str, Any]:
    return _by_key(model["applications"], key)


def _history(world, draft: dict[str, Any], **params: Any) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/operations", **params))


def _undo(world, draft: dict[str, Any], version: int, **body: Any):
    return world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": version, **body})


def _redo(world, draft: dict[str, Any], version: int):
    return world.api.post(f"/model-drafts/{draft['id']}/redo", {"expectedVersion": version})


def _attribute(key: str, name: str) -> dict[str, Any]:
    return {"kind": "addAttributeType", "key": key, "name": name, "valueType": "text"}


@pytest.mark.journey("J33.1", "J33.3")
@pytest.mark.structures("A1")
def test_an_application_built_from_an_empty_draft_by_operations_installs(world):
    """Given a draft of an empty schema 0.10 document. When one request adds an application, a
    top-level type and a type under it, a new attribute type attached to each (one required), a
    relation type allowed between them and a group holding both collections. Then the draft is
    valid, the history holds the request as one step with each entry's inverse, each type has a
    generated table view and detail page, and the draft installs."""
    draft = _empty_draft(world)
    operations = [
        {"kind": "addApplication", "name": "J33 Storage Rooms"},
        {
            "kind": "addObjectType",
            "applicationKey": "j33-storage-rooms",
            "name": "J33 Shelf",
            "pluralName": "J33 Shelves",
            "parent": None,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-storage-rooms",
            "name": "J33 Item",
            "pluralName": "J33 Items",
            "parent": {
                "objectTypes": ["j33-shelf"],
                "relationType": {"name": "Holds item", "reverseName": "On shelf"},
            },
        },
        {
            "kind": "addAttributeType",
            "name": "J33 Shelf código",
            "valueType": "text",
            "features": {"searchable": True, "filterable": True, "sortable": True},
        },
        {"kind": "attachAttribute", "objectType": "j33-shelf", "attributeType": "j33-shelf-codigo", "required": True},
        {"kind": "addAttributeType", "name": "J33 Weight", "valueType": "decimal"},
        {"kind": "attachAttribute", "objectType": "j33-item", "attributeType": "j33-weight"},
        {"kind": "addRelationType", "name": "J33 Replaces", "reverseName": "J33 Replaced by"},
        {"kind": "allowRelation", "relationType": "j33-replaces", "from": "j33-item", "to": "j33-item"},
        {"kind": "addNavigationGroup", "applicationKey": "j33-storage-rooms", "label": "J33 Storage"},
        {"kind": "placeCollection", "applicationKey": "j33-storage-rooms", "collection": "j33-shelf", "group": "j33-storage"},
        {"kind": "placeCollection", "applicationKey": "j33-storage-rooms", "collection": "j33-item", "group": "j33-storage"},
    ]
    answer = ok(_apply(world, draft, draft["version"], *operations))
    assert answer["valid"] is True, answer["diagnostics"]
    assert answer["diagnostics"] == []
    assert answer["version"] == draft["version"] + 1

    history = _history(world, draft)["items"]
    assert [entry["kind"] for entry in history] == [item["kind"] for item in operations]
    assert {entry["step"] for entry in history} == {history[0]["step"]}
    assert all(entry["inverse"]["kind"] for entry in history)
    assert all(entry["origin"] == {"type": "request"} for entry in history)
    assert history[0]["inverse"] == {"kind": "removeApplication", "applicationKey": "j33-storage-rooms"}

    model = _model(world, draft)
    application = _application(model, "j33-storage-rooms")
    assert application["objectTypeKeys"] == ["j33-shelf", "j33-item"]
    for type_key in ("j33-shelf", "j33-item"):
        (view,) = [v for v in application["views"] if v.get("objectTypeKey") == type_key]
        assert view["type"] == "table"
        assert view["config"]["columns"][0] == "name"
        _by_key(application["details"], type_key, "objectTypeKey")
    shelf_view = next(v for v in application["views"] if v.get("objectTypeKey") == "j33-shelf")
    assert "j33-shelf-codigo" in shelf_view["config"]["columns"]
    assert "j33-shelf-codigo" in shelf_view["config"]["filterFields"]
    shelf_page = _by_key(application["details"], "j33-shelf", "objectTypeKey")
    assert any(p["type"] == "children" and "j33-item" in p["config"]["objectTypeKeys"] for p in shelf_page["panels"])
    assert application["navigation"]["groups"] == [
        {"key": "j33-storage", "label": "J33 Storage", "collections": ["j33-shelf", "j33-item"], "collapsed": False}
    ]

    installed = world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}
    )
    ok(installed, 201)


@pytest.mark.journey("J33.2", "J33.3", "J08")
@pytest.mark.structures("R", "K")
def test_the_active_model_extended_by_operations_activates_and_holds_records(world):
    """Given a draft of the active release. When a type is added under R with a new attribute, a
    relation from it to K is allowed, and the release version is raised. Then the new type's table
    view and detail page are generated, R's detail page gains a children panel, the draft installs
    and activates, and a record of the new type is created under an R record. The installed release
    is now the draft's base, so a key change of the new type is refused with its impact."""
    draft = _draft_of_active(world)
    model = _model(world, draft)
    r_app = world.app("R")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "addObjectType",
                "applicationKey": r_app,
                "key": "j33-note",
                "name": "Note",
                "pluralName": "Notes",
                "parent": {
                    "objectTypes": [world.key("R")],
                    "relationType": {"key": "j33-has-note", "name": "Has note", "reverseName": "Note of"},
                },
            },
            _attribute("j33-text", "Note text"),
            {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-text"},
            {"kind": "addRelationType", "key": "j33-cites", "name": "Cites", "reverseName": "Cited by"},
            {"kind": "allowRelation", "relationType": "j33-cites", "from": "j33-note", "to": world.key("K")},
            {
                "kind": "setRelease",
                "key": model["release"]["key"],
                "name": model["release"]["name"],
                "version": model["release"]["version"] + "-j33",
            },
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]

    model = _model(world, draft)
    application = _application(model, r_app)
    (view,) = [v for v in application["views"] if v.get("objectTypeKey") == "j33-note"]
    assert "j33-text" in view["config"]["columns"]
    note_page = _by_key(application["details"], "j33-note", "objectTypeKey")
    assert {p["type"] for p in note_page["panels"]} >= {"attributes", "hierarchy", "relations"}
    # R's detail page gains a children panel where it declares one; the server does not invent a
    # detail page for a released type that has none (the configurations' generated models declare
    # none; J33.1 checks the panel on a parent's generated page).
    r_pages = [d for d in application["details"] if d["objectTypeKey"] == world.key("R")]
    before = [d for d in _application(_active_release(world)["model"], r_app)["details"] if d["objectTypeKey"] == world.key("R")]
    assert len(r_pages) == len(before)
    for r_page in r_pages:
        assert any(
            p["type"] == "children" and "j33-note" in p["config"]["objectTypeKeys"] for p in r_page["panels"]
        )

    release = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}
        ),
        201,
    )
    ok(world.activate(release["id"]))
    parent = world.made("R", "Holder of notes")
    created = world.api.post(
        "/objects",
        {
            "applicationKey": r_app,
            "objectTypeKey": "j33-note",
            "name": "First note",
            "workspaceKey": "default",
            "parentObjectId": parent["id"],
            "attributes": [{"attributeTypeKey": "j33-text", "value": "Written after activation"}],
        },
    )
    ok(created, 201)

    current = _draft(world, draft)
    assert current["baseReleaseId"] == release["id"]
    assert current["version"] == answer["version"]
    error = refused(
        _apply(
            world,
            draft,
            current["version"],
            {"kind": "setKey", "element": {"objectType": "j33-note"}, "key": "j33-memo"},
        ),
        409,
        "OPERATION_REQUIRES_MIGRATION",
    )
    assert error["details"]["index"] == 0
    assert error["details"]["element"] == {"objectType": "j33-note"}
    assert error["details"]["impact"]["records"] == 1


@pytest.mark.journey("J33.4")
@pytest.mark.structures("A1")
def test_a_step_is_undone_and_redone_and_a_new_step_clears_redo(world):
    """Given a draft with two steps. When the latest is undone, then redone. Then the model is as it
    was after the first step, then after the second. After an undo, a new step leaves nothing to
    redo; a fresh draft has nothing to undo."""
    draft = _draft_of_active(world)
    refused(_undo(world, draft, draft["version"]), 409, "NOTHING_TO_UNDO")
    first = ok(_apply(world, draft, draft["version"], _attribute("j33-a", "First")))
    after_first = _model(world, draft)
    second = ok(_apply(world, draft, first["version"], _attribute("j33-b", "Second")))
    after_second = _model(world, draft)

    undone = ok(_undo(world, draft, second["version"]))
    assert _model(world, draft) == after_first
    assert [entry["origin"]["type"] for entry in undone["entries"]] == ["undo"]
    redone = ok(_redo(world, draft, undone["version"]))
    assert _model(world, draft) == after_second
    refused(_redo(world, draft, redone["version"]), 409, "NOTHING_TO_REDO")

    undone = ok(_undo(world, draft, redone["version"]))
    third = ok(_apply(world, draft, undone["version"], _attribute("j33-c", "Third")))
    refused(_redo(world, draft, third["version"]), 409, "NOTHING_TO_REDO")


@pytest.mark.journey("J33.5")
@pytest.mark.structures("R")
def test_an_undo_with_dependants_is_refused_naming_them_and_succeeds_together(world):
    """Given step 1 adding a type and step 2 attaching an attribute to it. When step 1 is undone
    alone. Then it is refused OPERATION_HAS_DEPENDANTS naming step 2; undoing both together returns
    the draft's starting model."""
    draft = _draft_of_active(world)
    start = _model(world, draft)
    first = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "addObjectType",
                "applicationKey": world.app("R"),
                "key": "j33-tag",
                "name": "Tag",
                "pluralName": "Tags",
                "parent": None,
            },
        )
    )
    second = ok(
        _apply(
            world,
            draft,
            first["version"],
            {"kind": "attachAttribute", "objectType": "j33-tag", "attributeType": world.key("R.u")},
        )
    )
    step_one, step_two = first["entries"][0]["step"], second["entries"][0]["step"]

    error = refused(
        _undo(world, draft, second["version"], steps=[step_one]), 409, "OPERATION_HAS_DEPENDANTS"
    )
    assert error["details"]["dependants"] == [step_two]
    assert _draft(world, draft)["version"] == second["version"]

    ok(_undo(world, draft, second["version"], steps=[step_one, step_two]))
    assert _model(world, draft) == start


@pytest.mark.journey("J33.6")
@pytest.mark.structures("A1")
def test_a_stale_editor_is_answered_with_the_steps_applied_since(world):
    """Given two editors of one draft at version v. When one applies a step and the other sends a
    step at v. Then the second is refused VERSION_CONFLICT with the first editor's entries, and
    applies when resent at the new version."""
    draft = _draft_of_active(world)
    first = ok(_apply(world, draft, draft["version"], _attribute("j33-first", "First editor")))
    error = refused(
        _apply(world, draft, draft["version"], _attribute("j33-second", "Second editor")),
        409,
        "VERSION_CONFLICT",
    )
    assert error["details"]["operations"] == first["entries"]
    assert error["details"].get("more", False) is False
    ok(_apply(world, draft, first["version"], _attribute("j33-second", "Second editor")))


@pytest.mark.journey("J33.7")
@pytest.mark.structures("R", "R.u")
def test_a_draft_only_operation_on_a_released_element_is_refused_with_its_impact(world):
    """Given a draft of the active release. When a request holding an additive operation and then
    the removal of R is sent, before and after one more R record exists. Then each is refused
    OPERATION_REQUIRES_MIGRATION at index 1 with R's records counted, one more the second time, and
    the draft is unchanged. A key change of R.u counts its values the same way."""
    draft = _draft_of_active(world)
    start = _model(world, draft)

    def removal() -> dict[str, Any]:
        return refused(
            _apply(
                world,
                draft,
                draft["version"],
                _attribute("j33-extra", "Extra"),
                {"kind": "removeObjectType", "objectType": world.key("R")},
            ),
            409,
            "OPERATION_REQUIRES_MIGRATION",
        )["details"]

    def rekey() -> dict[str, Any]:
        return refused(
            _apply(
                world,
                draft,
                draft["version"],
                {"kind": "setKey", "element": {"attributeType": world.key("R.u")}, "key": "j33-renamed"},
            ),
            409,
            "OPERATION_REQUIRES_MIGRATION",
        )["details"]

    before, values_before = removal(), rekey()
    assert before["index"] == 1
    assert before["element"] == {"objectType": world.key("R")}
    world.made("R", "One more", values={"R.u": "J33-IMPACT-1"})
    after, values_after = removal(), rekey()
    assert after["impact"]["records"] == before["impact"]["records"] + 1
    assert values_after["impact"]["values"] == values_before["impact"]["values"] + 1

    current = _draft(world, draft)
    assert current["version"] == draft["version"]
    assert current["model"] == start
    assert _history(world, draft)["items"] == []


@pytest.mark.journey("J33.7")
@pytest.mark.structures("R")
def test_a_required_relationship_to_a_released_type_is_refused_as_a_required_attribute_is(world):
    """0.10 R-F3. Given a draft of the active release. When a new relation type is allowed to R as
    required, then as optional. Then the first is refused OPERATION_REQUIRES_MIGRATION at its index
    with R's records counted, as attaching a required attribute to R is; the second applies."""
    draft = _draft_of_active(world)
    relation = {
        "kind": "addRelationType",
        "key": "j33-needs",
        "name": "Needs",
        "reverseName": "Needed by",
        "isOriented": True,
    }

    def allow(required: bool) -> dict[str, Any]:
        return {"kind": "allowRelation", "relationType": "j33-needs", "from": world.key("R"), "to": world.key("R"), "required": required}

    error = refused(_apply(world, draft, draft["version"], relation, allow(True)), 409, "OPERATION_REQUIRES_MIGRATION")
    assert error["details"]["index"] == 1
    assert error["details"]["element"] == {"objectType": world.key("R")}
    assert error["details"]["impact"]["records"] >= 0
    ok(_apply(world, draft, draft["version"], relation, allow(False)))


@pytest.mark.journey("J33.8")
@pytest.mark.structures("R")
@pytest.mark.settings(MODEL_OPERATION_MAX_ITEMS="3")
def test_a_request_that_cannot_apply_applies_nothing(world):
    """Given valid operations followed by one naming an unknown type, or adding a type under a key
    already taken. When sent. Then it is refused INVALID_OPERATION at its index and pointer, and
    nothing applies. More operations than the limit is refused OPERATION_BATCH_TOO_LARGE."""
    draft = _draft_of_active(world)
    start = _model(world, draft)
    error = refused(
        _apply(
            world,
            draft,
            draft["version"],
            _attribute("j33-ok", "Fine"),
            {"kind": "attachAttribute", "objectType": "j33-no-such-type", "attributeType": "j33-ok"},
        ),
        422,
        "INVALID_OPERATION",
    )
    assert error["details"]["index"] == 1
    assert error["details"]["pointer"] == "/operations/1/objectType"

    error = refused(
        _apply(
            world,
            draft,
            draft["version"],
            _attribute("j33-ok", "Fine"),
            {
                "kind": "addObjectType",
                "applicationKey": world.app("R"),
                "key": world.key("R"),
                "name": "Clash",
                "pluralName": "Clashes",
                "parent": None,
            },
        ),
        422,
        "INVALID_OPERATION",
    )
    assert error["details"]["index"] == 1
    assert error["details"]["pointer"] == "/operations/1/key"

    four = [_attribute(f"j33-{n}", f"Attribute {n}") for n in range(4)]
    refused(_apply(world, draft, draft["version"], *four), 413, "OPERATION_BATCH_TOO_LARGE")
    assert _draft(world, draft)["version"] == draft["version"]
    assert _model(world, draft) == start


@pytest.mark.journey("J33", "J08")
@pytest.mark.structures("A1")
def test_a_draft_left_invalid_between_steps_reports_the_compilers_diagnostics(world):
    """Given a draft of the active release. When an application is added alone. Then the step
    applies, the answer is invalid with the diagnostics whole-model validation gives for the draft's
    model, and installation is refused INVALID_MODEL."""
    draft = _draft_of_active(world)
    answer = ok(_apply(world, draft, draft["version"], {"kind": "addApplication", "name": "J33 Empty"}))
    assert answer["valid"] is False
    validation = ok(world.api.post("/model-validations", {"model": _model(world, draft)}))
    assert answer["diagnostics"] == validation["diagnostics"]
    refused(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}
        ),
        422,
        "INVALID_MODEL",
    )


@pytest.mark.journey("J33.12", "J08.9")
@pytest.mark.structures("A1")
def test_a_whole_model_edit_is_one_step_and_operations_continue_on_it(world):
    """Given a draft of the active release. When its model is replaced by PATCH and an operation
    follows. Then the PATCH is one replaceModel step of origin patch, the operation applies on the
    edited model, undoing both returns the model before the PATCH, and the history read from its end
    lists every step with its origin."""
    draft = _draft_of_active(world)
    start = _model(world, draft)
    edited = copy.deepcopy(start)
    edited["attributeTypes"].append({"key": "j33-patched", "name": "Patched in", "valueType": "text"})
    patched = ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": draft["version"], "model": edited}
        )
    )
    answer = ok(
        _apply(
            world,
            draft,
            patched["version"],
            {"kind": "setLabel", "element": {"attributeType": "j33-patched"}, "name": "Patched, renamed"},
        )
    )
    assert _by_key(_model(world, draft)["attributeTypes"], "j33-patched")["name"] == "Patched, renamed"

    undone = ok(_undo(world, draft, answer["version"]))
    undone = ok(_undo(world, draft, undone["version"]))
    assert _model(world, draft) == start

    latest = _history(world, draft, pageSize=2, **{"from": "end"})
    assert [entry["origin"]["type"] for entry in latest["items"]] == ["undo", "undo"]
    every = _history(world, draft, pageSize=100)["items"]
    assert [(entry["kind"], entry["origin"]["type"]) for entry in every[:2]] == [
        ("replaceModel", "patch"),
        ("setLabel", "request"),
    ]
    assert [entry["step"] for entry in every] == sorted(entry["step"] for entry in every)
