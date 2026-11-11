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


def _application_of_r(world) -> str:
    return next(
        a["key"]
        for a in _active_release(world)["model"]["applications"]
        if world.key("R") in a["objectTypeKeys"]
    )


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
        {
            "kind": "attachAttribute",
            "objectType": "j33-shelf",
            "attributeType": "j33-shelf-codigo",
            "required": True,
        },
        {"kind": "addAttributeType", "name": "J33 Weight", "valueType": "decimal"},
        {"kind": "attachAttribute", "objectType": "j33-item", "attributeType": "j33-weight"},
        {"kind": "addRelationType", "name": "J33 Replaces", "reverseName": "J33 Replaced by"},
        {
            "kind": "allowRelation",
            "relationType": "j33-replaces",
            "from": "j33-item",
            "to": "j33-item",
        },
        {
            "kind": "addNavigationGroup",
            "applicationKey": "j33-storage-rooms",
            "label": "J33 Storage",
        },
        {
            "kind": "placeCollection",
            "applicationKey": "j33-storage-rooms",
            "collection": "j33-shelf",
            "group": "j33-storage",
        },
        {
            "kind": "placeCollection",
            "applicationKey": "j33-storage-rooms",
            "collection": "j33-item",
            "group": "j33-storage",
        },
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
    assert history[0]["inverse"] == {
        "kind": "removeApplication",
        "applicationKey": "j33-storage-rooms",
    }

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
    assert any(
        p["type"] == "children" and "j33-item" in p["config"]["objectTypeKeys"]
        for p in shelf_page["panels"]
    )
    assert application["navigation"]["groups"] == [
        {
            "key": "j33-storage",
            "label": "J33 Storage",
            "collections": ["j33-shelf", "j33-item"],
            "collapsed": False,
        }
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
                    "relationType": {
                        "key": "j33-has-note",
                        "name": "Has note",
                        "reverseName": "Note of",
                    },
                },
            },
            _attribute("j33-text", "Note text"),
            {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-text"},
            {
                "kind": "addRelationType",
                "key": "j33-cites",
                "name": "Cites",
                "reverseName": "Cited by",
            },
            {
                "kind": "allowRelation",
                "relationType": "j33-cites",
                "from": "j33-note",
                "to": world.key("K"),
            },
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
    before = [
        d
        for d in _application(_active_release(world)["model"], r_app)["details"]
        if d["objectTypeKey"] == world.key("R")
    ]
    assert len(r_pages) == len(before)
    for r_page in r_pages:
        assert any(
            p["type"] == "children" and "j33-note" in p["config"]["objectTypeKeys"]
            for p in r_page["panels"]
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
    renamed = ok(
        _apply(
            world,
            draft,
            current["version"],
            {"kind": "setKey", "element": {"objectType": "j33-note"}, "key": "j33-memo"},
        )
    )
    (marked,) = renamed["entries"][0]["migration"]
    assert marked["element"] == {"objectType": "j33-note"} and marked["keyChange"] is True
    assert marked["impact"]["records"] == 1


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
def test_a_draft_only_operation_on_a_released_element_applies_and_is_marked_with_its_impact(world):
    """Given a draft of the active release. When a request holding an additive operation and then
    the removal of R is sent, before and after one more R record exists. Then each applies; only the
    removal is marked as needing a migration, naming R with its records counted (one more the second
    time). A key change of R.u is marked the same way with its values counted, and an undo takes the
    request back."""

    def removal() -> dict[str, Any]:
        draft = _draft_of_active(world)
        answer = ok(
            _apply(
                world,
                draft,
                draft["version"],
                _attribute("j33-extra", "Extra"),
                {"kind": "removeObjectType", "objectType": world.key("R")},
            )
        )
        assert [bool(entry["migration"]) for entry in answer["entries"]] == [False, True]
        assert not [t for t in _model(world, draft)["objectTypes"] if t["key"] == world.key("R")]
        return answer["entries"][1]["migration"][0]

    def rekey() -> dict[str, Any]:
        draft = _draft_of_active(world)
        answer = ok(
            _apply(
                world,
                draft,
                draft["version"],
                {
                    "kind": "setKey",
                    "element": {"attributeType": world.key("R.u")},
                    "key": "j33-renamed",
                },
            )
        )
        undone = ok(_undo(world, draft, answer["version"]))
        assert _model(world, draft) == _model(world, _draft_of_active(world))
        assert undone["entries"][0]["migration"] == []
        return answer["entries"][0]["migration"][0]

    before, values_before = removal(), rekey()
    assert before["element"] == {"objectType": world.key("R")} and before["keyChange"] is False
    assert values_before["keyChange"] is True
    world.made("R", "One more", values={"R.u": "J33-IMPACT-1"})
    after, values_after = removal(), rekey()
    assert after["impact"]["records"] == before["impact"]["records"] + 1
    assert values_after["impact"]["values"] == values_before["impact"]["values"] + 1


@pytest.mark.journey("J33.7")
@pytest.mark.structures("R")
def test_a_released_element_no_data_holds_is_removed_and_activation_checks_the_data_again(world):
    """Given a released type with no records. When its key is changed, then it is removed. Then the
    key change applies, marked with nothing held, and the removal applies unmarked. When a record of it arrives and
    that draft is installed, activating it is refused; a new draft's removal is applied and marked with
    the record counted."""
    model = _model(world, _draft_of_active(world))
    r_app = _application_of_r(world)
    draft = _draft_of_active(world, "Empty type")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "addObjectType",
                "applicationKey": r_app,
                "key": "j33-empty",
                "name": "Empty",
                "pluralName": "Empties",
                "parent": None,
            },
            {
                "kind": "setRelease",
                "key": model["release"]["key"],
                "name": model["release"]["name"],
                "version": model["release"]["version"] + "-empty",
            },
        )
    )
    ok(
        world.activate(
            ok(
                world.api.post(
                    f"/model-drafts/{draft['id']}/installation",
                    {"expectedVersion": answer["version"]},
                ),
                201,
            )["id"]
        )
    )

    current = _draft(world, draft)
    rekey = {"kind": "setKey", "element": {"objectType": "j33-empty"}, "key": "j33-renamed"}
    renamed = ok(_apply(world, draft, current["version"], rekey))
    (marked,) = renamed["entries"][0]["migration"]
    assert marked["keyChange"] is True and marked["impact"] == {
        "records": 0,
        "values": 0,
        "relationships": 0,
    }
    current = ok(_undo(world, draft, renamed["version"]))
    removed = ok(
        _apply(
            world,
            draft,
            current["version"],
            {"kind": "removeObjectType", "objectType": "j33-empty"},
            {
                "kind": "setRelease",
                "key": model["release"]["key"],
                "name": model["release"]["name"],
                "version": model["release"]["version"] + "-gone",
            },
        )
    )
    assert removed["valid"] is True, removed["diagnostics"]
    assert not [t for t in _model(world, draft)["objectTypes"] if t["key"] == "j33-empty"]

    ok(
        world.api.post(
            "/objects",
            {
                "applicationKey": r_app,
                "objectTypeKey": "j33-empty",
                "name": "Arrived",
                "workspaceKey": "default",
            },
        ),
        201,
    )
    release = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": removed["version"]}
        ),
        201,
    )
    refused(world.activate(release["id"]), 409, "MODEL_MIGRATION_REQUIRED")

    later = _draft_of_active(world, "Too late")
    gone = ok(
        _apply(
            world, later, later["version"], {"kind": "removeObjectType", "objectType": "j33-empty"}
        )
    )
    assert gone["entries"][0]["migration"][0]["impact"]["records"] == 1


@pytest.mark.journey("J33.7")
@pytest.mark.structures("R")
def test_a_required_relationship_to_a_released_type_is_marked_as_a_required_attribute_is(world):
    """0.10 R-F3. Given a draft of the active release. When a new relation type is allowed to R as
    required, then as optional. Then both apply; the first is marked as needing a migration at its
    entry with R's records counted, as attaching a required attribute to R is; the second is not."""
    draft = _draft_of_active(world)
    relation = {
        "kind": "addRelationType",
        "key": "j33-needs",
        "name": "Needs",
        "reverseName": "Needed by",
        "isOriented": True,
    }

    def allow(required: bool) -> dict[str, Any]:
        return {
            "kind": "allowRelation",
            "relationType": "j33-needs",
            "from": world.key("R"),
            "to": world.key("R"),
            "required": required,
        }

    required = ok(_apply(world, draft, draft["version"], relation, allow(True)))
    (marked,) = required["entries"][1]["migration"]
    assert marked["element"] == {"objectType": world.key("R")} and marked["impact"]["records"] >= 0
    optional = ok(_apply(world, _draft_of_active(world), 1, relation, allow(False)))
    assert optional["entries"][1]["migration"] == []


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
            {
                "kind": "attachAttribute",
                "objectType": "j33-no-such-type",
                "attributeType": "j33-ok",
            },
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
    answer = ok(
        _apply(world, draft, draft["version"], {"kind": "addApplication", "name": "J33 Empty"})
    )
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


def _hub_model_operations() -> list[dict[str, Any]]:
    """A page ("hub") in one application whose relations panels list relations that types of another
    application have to it: one panel lists both relations, one lists a single one."""
    panel = lambda key, title, relations: {
        "kind": "insertViewItem",
        "applicationKey": "j33-core",
        "detail": "j33-hub",
        "list": "panels",
        "item": {
            "key": key,
            "title": title,
            "type": "relations",
            "region": "main",
            "order": 9,
            "visible": True,
            "config": {
                "relationTypeKeys": relations,
                "direction": "incoming",
                "columns": ["name", "objectType"],
            },
        },
    }
    top = {"parent": None}
    return [
        {"kind": "addApplication", "name": "J33 Core"},
        {"kind": "addApplication", "name": "J33 Extra"},
        {
            "kind": "addObjectType",
            "applicationKey": "j33-core",
            "name": "J33 Hub",
            "pluralName": "J33 Hubs",
            **top,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-extra",
            "name": "J33 Left",
            "pluralName": "J33 Lefts",
            **top,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-extra",
            "name": "J33 Right",
            "pluralName": "J33 Rights",
            **top,
        },
        {"kind": "addRelationType", "name": "J33 Feeds", "reverseName": "J33 Fed by"},
        {"kind": "addRelationType", "name": "J33 Serves", "reverseName": "J33 Served by"},
        {"kind": "allowRelation", "relationType": "j33-feeds", "from": "j33-left", "to": "j33-hub"},
        {
            "kind": "allowRelation",
            "relationType": "j33-serves",
            "from": "j33-right",
            "to": "j33-hub",
        },
        panel("j33-both", "Both", ["j33-feeds", "j33-serves"]),
        panel("j33-serving", "Serving", ["j33-serves"]),
    ]


@pytest.mark.journey("J33.17")
@pytest.mark.structures("A1")
def test_a_removal_takes_the_panels_of_other_pages_that_depended_on_it_and_undoes_whole(world):
    """Given pages in one application listing relations from types of another. When a type of the
    other application is removed, then a panel listing its relation and another is left with the other
    and a panel listing only it goes, the relation type nothing uses goes, and the draft is valid.
    When the application is removed, no panel of the page is left. Each undo restores the draft
    exactly."""
    draft = _empty_draft(world)
    answer = ok(_apply(world, draft, draft["version"], *_hub_model_operations()))
    assert answer["valid"] is True, answer["diagnostics"]
    before = _model(world, draft)

    removed = ok(
        _apply(
            world, draft, answer["version"], {"kind": "removeObjectType", "objectType": "j33-right"}
        )
    )
    assert removed["valid"] is True, removed["diagnostics"]
    page = _by_key(
        _application(_model(world, draft), "j33-core")["details"], "j33-hub", "objectTypeKey"
    )
    panels = {p["key"]: p for p in page["panels"] if p["type"] == "relations"}
    assert panels["j33-both"]["config"]["relationTypeKeys"] == ["j33-feeds"]
    assert "j33-serving" not in panels
    kept = [r["key"] for r in _model(world, draft)["relationTypes"]]
    assert "j33-serves" not in kept
    assert "j33-feeds" in kept  # still bound, with no data: it stays
    undone = ok(_undo(world, draft, removed["version"]))
    assert _model(world, draft) == before

    removed = ok(
        _apply(
            world,
            draft,
            undone["version"],
            {"kind": "removeApplication", "applicationKey": "j33-extra"},
        )
    )
    assert removed["valid"] is True, removed["diagnostics"]
    page = _by_key(
        _application(_model(world, draft), "j33-core")["details"], "j33-hub", "objectTypeKey"
    )
    assert [p for p in page["panels"] if p["type"] == "relations"] == []
    assert _model(world, draft)["relationTypes"] == []
    ok(_undo(world, draft, removed["version"]))
    assert _model(world, draft) == before


@pytest.mark.journey("J33.17")
@pytest.mark.structures("A1")
def test_a_draft_with_broken_panels_reports_them_all_and_a_panel_is_removed_from_the_invalid_draft(
    world,
):
    """Given a draft whose pages list a relation their type no longer has in several panels (a binding
    removed by a whole-model edit). Then its diagnostics name every panel in plain words, each tied to
    its page and panel; and while the draft is invalid a panel is removed from its page by the
    operation the issue offers, which leaves the other issue and undoes."""
    draft = _empty_draft(world)
    answer = ok(_apply(world, draft, draft["version"], *_hub_model_operations()))
    broken = copy.deepcopy(_model(world, draft))
    broken["objectTypeRelations"] = [
        b for b in broken["objectTypeRelations"] if b["relationTypeKey"] != "j33-serves"
    ]
    patched = ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": answer["version"], "model": broken}
        )
    )

    def hub_issues() -> list[dict[str, Any]]:
        found = ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))["diagnostics"]
        # The generated pages and tables of the far types break too (the relationship's own panel and
        # column, 0.13 RL); the hub's panels are the ones read here.
        return [i for i in found if i["element"].get("detail") == "j33-hub"]

    issues = hub_issues()
    # The panel the hub got for the removed binding (generated when it was allowed) breaks with them.
    assert sorted(i["element"]["panel"] for i in issues) == [
        "j33-both",
        "j33-served-by",
        "j33-serving",
    ]
    assert all(i["element"]["applicationKey"] == "j33-core" for i in issues)
    serving = next(i for i in issues if i["element"]["panel"] == "j33-serving")
    assert serving["message"].startswith(
        "The Serving panel on the J33 Hub page lists a relation J33 Hub no longer has"
    )
    assert serving["message"].endswith("Remove the panel or restore the relation.")

    remove = {
        "kind": "removeViewItem",
        "applicationKey": "j33-core",
        "detail": "j33-hub",
        "list": "panels",
        "item": "j33-serving",
    }
    removed = ok(_apply(world, draft, patched["version"], remove))
    assert removed["valid"] is False
    assert sorted(i["element"]["panel"] for i in hub_issues()) == ["j33-both", "j33-served-by"]
    ok(_undo(world, draft, removed["version"]))
    assert len(hub_issues()) == 3


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
    edited["attributeTypes"].append(
        {"key": "j33-patched", "name": "Patched in", "valueType": "text"}
    )
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
            {
                "kind": "setLabel",
                "element": {"attributeType": "j33-patched"},
                "name": "Patched, renamed",
            },
        )
    )
    assert (
        _by_key(_model(world, draft)["attributeTypes"], "j33-patched")["name"] == "Patched, renamed"
    )

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


@pytest.mark.journey("J33.1")
@pytest.mark.structures("A1")
def test_a_relation_types_reverse_name_is_edited_in_place_by_set_label(world):
    """Given a draft with a relation type that has a reverse name. When the editor's in-place edit of
    the reverse name is applied as a `setLabel` operation with `reverseName`. Then the draft read back
    shows the new reverse name and the name is untouched (R13-F40: `setLabel` refused `reverseName`
    as an unknown parameter)."""
    draft = _empty_draft(world)
    made = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "addRelationType",
                "key": "j33-holds",
                "name": "Holds",
                "reverseName": "Held by",
            },
        )
    )
    answer = ok(
        _apply(
            world,
            draft,
            made["version"],
            {
                "kind": "setLabel",
                "element": {"relationType": "j33-holds"},
                "reverseName": "Kept on",
            },
        )
    )
    relation = _by_key(_model(world, draft)["relationTypes"], "j33-holds")
    assert (relation["name"], relation["reverseName"]) == ("Holds", "Kept on")
    assert answer["version"] > made["version"]


def _outline(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))


def _tree_of(outline: dict[str, Any], application: str) -> list[Any]:
    def shape(node: dict[str, Any]) -> Any:
        return (node["objectType"], [shape(child) for child in node["children"]])

    return [shape(node) for node in _by_key(outline["applications"], application)["tree"]]


@pytest.mark.journey("J33.15")
@pytest.mark.structures("A1")
def test_a_branch_moved_to_another_application_keeps_its_hierarchy_and_undoes_in_one_step(world):
    """Given a draft whose application holds a three-level branch with its tree view, beside a second
    application. When the branch's top is moved to the top of the second application, then into a
    type there, by `setContainment` with `application`. Then the branch leaves the first application
    with its views and detail pages and stands in the second with its containment as it was, the tree
    view growing up to the new parent; the draft stays valid; one undo returns it. Moving a type
    between applications was missing (found 2026-10-19: the editor's move only set a parent)."""
    draft = _draft_of_active(world)
    parent = {"relationType": {"name": "Holds", "reverseName": "Held by"}}
    steps = [
        {"kind": "addApplication", "key": "j33-from", "name": "From"},
        {"kind": "addApplication", "key": "j33-to", "name": "To"},
        {
            "kind": "addObjectType",
            "applicationKey": "j33-from",
            "key": "j33-top",
            "name": "Top",
            "parent": None,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-from",
            "key": "j33-mid",
            "name": "Mid",
            "parent": {**parent, "objectTypes": ["j33-top"]},
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-from",
            "key": "j33-leaf",
            "name": "Leaf",
            "parent": {**parent, "objectTypes": ["j33-mid"]},
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-from",
            "key": "j33-stays",
            "name": "Stays",
            "parent": None,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "j33-to",
            "key": "j33-holder",
            "name": "Holder",
            "parent": None,
        },
        {
            "kind": "addView",
            "applicationKey": "j33-from",
            "view": {
                "key": "j33-hierarchy",
                "name": "Hierarchy",
                "type": "tree",
                "config": {
                    "rootObjectTypeKeys": ["j33-top"],
                    "objectTypeKeys": ["j33-top", "j33-mid", "j33-leaf"],
                    "labelField": "name",
                    "pageSize": 50,
                    "actions": ["createChild", "move"],
                },
            },
        },
    ]
    built = ok(_apply(world, draft, draft["version"], *steps))
    before = _model(world, draft)
    assert _outline(world, draft)["valid"]

    moved = ok(
        _apply(
            world,
            draft,
            built["version"],
            {
                "kind": "setContainment",
                "objectType": "j33-top",
                "parent": None,
                "application": "j33-to",
            },
        )
    )
    model, outline = _model(world, draft), _outline(world, draft)
    assert outline["valid"], outline["diagnostics"]
    source, target = _application(model, "j33-from"), _application(model, "j33-to")
    assert source["objectTypeKeys"] == ["j33-stays"]
    assert target["objectTypeKeys"] == ["j33-holder", "j33-top", "j33-mid", "j33-leaf"]
    assert {d["objectTypeKey"] for d in target["details"]} == {
        "j33-holder",
        "j33-top",
        "j33-mid",
        "j33-leaf",
    }
    assert "j33-hierarchy" in {v["key"] for v in target["views"]}
    assert not {"j33-top", "j33-mid", "j33-leaf"} & {d["objectTypeKey"] for d in source["details"]}
    assert _tree_of(outline, "j33-to") == [
        ("j33-holder", []),
        ("j33-top", [("j33-mid", [("j33-leaf", [])])]),
    ]
    assert _tree_of(outline, "j33-from") == [("j33-stays", [])]

    under = ok(
        _apply(
            world,
            draft,
            moved["version"],
            {
                "kind": "setContainment",
                "objectType": "j33-top",
                "parent": {**parent, "objectTypes": ["j33-holder"]},
            },
        )
    )
    outline = _outline(world, draft)
    assert outline["valid"], outline["diagnostics"]
    assert _tree_of(outline, "j33-to") == [
        ("j33-holder", [("j33-top", [("j33-mid", [("j33-leaf", [])])])])
    ]
    tree = _by_key(_application(_model(world, draft), "j33-to")["views"], "j33-hierarchy")["config"]
    assert tree["rootObjectTypeKeys"] == ["j33-holder"]

    undone = ok(_undo(world, draft, under["version"]))
    ok(_undo(world, draft, undone["version"]))
    assert _model(world, draft) == before
    assert moved["entries"][0]["removed"] == []

    # A middle type moved alone leaves its parent's children panel nothing to list: the answer says so.
    alone = ok(
        _apply(
            world,
            draft,
            _draft(world, draft)["version"],
            {"kind": "setContainment", "objectType": "j33-mid", "application": "j33-to"},
        )
    )
    removed = alone["entries"][0]["removed"]
    assert [(r["kind"], r["applicationKey"], r["detail"]) for r in removed] == [
        ("panel", "j33-from", "j33-top")
    ], removed
    assert removed[0]["name"]
    listed = _history(world, draft, pageSize=1, **{"from": "end"})["items"][0]
    assert listed["removed"] == removed


@pytest.mark.journey("J33.15")
@pytest.mark.structures("A1")
def test_a_move_between_applications_that_cannot_apply_says_why(world):
    """Given a draft. When a type is moved to an application it is already in, to an unknown one, or
    from an application that does not list it. Then each is refused at its parameter and nothing
    applies."""
    draft = _draft_of_active(world)
    app = world.app("R")
    key = world.key("R")
    start = _model(world, draft)
    for operation, parameter in (
        (
            {
                "kind": "setContainment",
                "objectType": key,
                "application": app,
                "fromApplication": app,
            },
            "fromApplication",
        ),
        (
            {"kind": "setContainment", "objectType": key, "application": "j33-nowhere"},
            "application",
        ),
        (
            {
                "kind": "setContainment",
                "objectType": key,
                "application": "j33-nowhere-else",
                "fromApplication": app,
            },
            "application",
        ),
    ):
        answer = refused(
            _apply(world, draft, draft["version"], operation), 422, "INVALID_OPERATION"
        )
        assert parameter in str(answer), answer
    assert _model(world, draft) == start


@pytest.mark.journey("J33.16", "J08")
@pytest.mark.structures("R")
def test_a_relation_matrix_over_a_listed_type_shows_the_records_where_they_stand(world):
    """Given R records in R's application and a second application holding a column type over a cell
    type. When a matrix of R by that column is added there with R listed in one step. Then the draft
    is valid, the matrix reads the R record though it stands in the other application, and a cell can
    be created from it. A type still needed cannot be unlisted; a released listing needs a migration;
    a draft's matrix removed with ``unlist`` leaves as it came, and undo returns it."""
    draft = _draft_of_active(world)
    model = _model(world, draft)
    r_key, r_app = world.key("R"), world.app("R")
    parent = {"relationType": {"key": "j33-holds", "name": "Holds", "reverseName": "Held by"}}
    built = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {"kind": "addApplication", "key": "j33-words", "name": "Words"},
            {
                "kind": "addObjectType",
                "applicationKey": "j33-words",
                "key": "j33-tongue",
                "name": "Tongue",
                "parent": None,
            },
            {
                "kind": "addObjectType",
                "applicationKey": "j33-words",
                "key": "j33-word",
                "name": "Word",
                "parent": {**parent, "objectTypes": ["j33-tongue"]},
            },
            _attribute("j33-text", "Text"),
            {"kind": "attachAttribute", "objectType": "j33-word", "attributeType": "j33-text"},
            {
                "kind": "addRelationType",
                "key": "j33-worded",
                "name": "Worded",
                "reverseName": "Words of",
            },
            {
                "kind": "allowRelation",
                "relationType": "j33-worded",
                "from": r_key,
                "to": "j33-word",
                "cardinality": "one-to-many",
            },
        )
    )
    matrix = {
        "key": "j33-words-by-tongue",
        "name": "Words by tongue",
        "type": "relationMatrix",
        "config": {
            "relationTypeKey": "j33-worded",
            "direction": "outgoing",
            "rowObjectTypeKey": r_key,
            "columnObjectTypeKey": "j33-tongue",
            "cellObjectTypeKey": "j33-word",
            "rowColumns": ["name"],
            "columnLabelField": "name",
            "cellFields": ["j33-text"],
            "searchFields": ["name"],
            "cellActions": ["create", "edit"],
            "pageSize": 20,
        },
    }
    listed = {"kind": "listObjectType", "applicationKey": "j33-words", "objectType": r_key}
    added = ok(
        _apply(
            world,
            draft,
            built["version"],
            listed,
            {"kind": "addView", "applicationKey": "j33-words", "view": matrix},
        )
    )
    assert added["valid"] is True, added["diagnostics"]
    outline = _outline(world, draft)
    words = next(a for a in outline["applications"] if a["key"] == "j33-words")
    assert next(v for v in words["views"] if v["key"] == matrix["key"])["shows"] == [
        r_key,
        "j33-tongue",
        "j33-word",
    ]
    assert r_key not in words["unlistable"]

    refused(
        _apply(
            world,
            draft,
            added["version"],
            {"kind": "unlistObjectType", "applicationKey": "j33-words", "objectType": r_key},
        ),
        422,
        "INVALID_OPERATION",
    )
    removed = ok(
        _apply(
            world,
            draft,
            added["version"],
            {
                "kind": "removeView",
                "applicationKey": "j33-words",
                "view": matrix["key"],
                "unlist": True,
            },
        )
    )
    assert r_key not in _application(_model(world, draft), "j33-words")["objectTypeKeys"]
    undone = ok(_undo(world, draft, removed["version"]))
    assert r_key in _application(_model(world, draft), "j33-words")["objectTypeKeys"]

    versioned = ok(
        _apply(
            world,
            draft,
            undone["version"],
            {
                "kind": "setRelease",
                "key": model["release"]["key"],
                "name": model["release"]["name"],
                "version": model["release"]["version"] + "-j33m",
            },
        )
    )
    release = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": versioned["version"]}
        ),
        201,
    )
    ok(world.activate(release["id"]))

    row = world.made("R", "Row standing elsewhere")
    tongue = ok(
        world.api.post(
            "/objects",
            {
                "applicationKey": "j33-words",
                "objectTypeKey": "j33-tongue",
                "name": "First tongue",
                "workspaceKey": "default",
            },
        ),
        201,
    )
    page = ok(
        world.api.get(
            "/workspaces/default/relation-matrix",
            applicationKey="j33-words",
            viewKey=matrix["key"],
            search="Row standing elsewhere",
        )
    )
    assert [item["row"]["id"] for item in page["items"]] == [row["id"]]
    assert row["applicationKey"] == r_app
    assert [column["id"] for column in page["columns"]] == [tongue["id"]]
    word = ok(
        world.api.post(
            "/objects",
            {
                "applicationKey": "j33-words",
                "objectTypeKey": "j33-word",
                "name": "A word",
                "workspaceKey": "default",
                "parentObjectId": tongue["id"],
                "attributes": [{"attributeTypeKey": "j33-text", "value": "A word"}],
            },
        ),
        201,
    )
    ok(
        world.api.post(
            "/relations",
            {"relationTypeKey": "j33-worded", "fromObjectId": row["id"], "toObjectId": word["id"]},
        ),
        201,
    )
    (read,) = ok(
        world.api.get(
            "/workspaces/default/relation-matrix",
            applicationKey="j33-words",
            viewKey=matrix["key"],
            search="Row standing elsewhere",
        )
    )["items"]
    assert [cell["state"] for cell in read["cells"]] == ["one"]

    current = _draft(world, draft)
    # The matrix still needs the listing, so it is refused as invalid, not as needing a migration.
    refused(
        _apply(
            world,
            draft,
            current["version"],
            {"kind": "unlistObjectType", "applicationKey": r_app, "objectType": r_key},
        ),
        422,
        "INVALID_OPERATION",
    )


@pytest.mark.journey("J33.1", "J33.5")
@pytest.mark.structures("R")
def test_the_settings_a_model_holds_are_set_by_operations_undone_and_met_by_stored_data(world):
    """Given a released number attribute on R holding a record at 7. When a draft sets a type's
    display attribute and at-least-one rule, the attribute's help text and bounds, a binding's
    hint, a relation type's orientation and the application's default view, then one step holds
    them all and one undo takes them all back. A text attribute's bound, a bound above the other
    and an unknown display attribute are each refused at their pointer, applying nothing. A
    minimum above the stored 7 applies in the draft and compiling names the record it meets."""
    model = _model(world, _draft_of_active(world))
    r_app = _application_of_r(world)
    first = _draft_of_active(world, "Number")
    bump = {"kind": "setRelease", "key": model["release"]["key"], "name": model["release"]["name"]}
    added = ok(
        _apply(
            world,
            first,
            first["version"],
            {
                "kind": "addAttributeType",
                "key": "j33-count",
                "name": "Count",
                "valueType": "integer",
            },
            {"kind": "attachAttribute", "objectType": world.key("R"), "attributeType": "j33-count"},
            {**bump, "version": model["release"]["version"] + "-count"},
        )
    )
    ok(
        world.activate(
            ok(
                world.api.post(
                    f"/model-drafts/{first['id']}/installation",
                    {"expectedVersion": added["version"]},
                ),
                201,
            )["id"]
        )
    )
    world.made("R", "Holds seven", values={"j33-count": 7})

    draft = _draft_of_active(world, "Settings")
    start = _model(world, draft)
    relation = start["relationTypes"][0]["key"]
    view = _application(start, r_app)["views"][-1]["key"]
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "setObjectTypeProperty",
                "objectType": world.key("R"),
                "property": "displayAttributeTypeKey",
                "value": "j33-count",
            },
            {
                "kind": "setObjectTypeProperty",
                "objectType": world.key("R"),
                "property": "atLeastOneOf",
                "value": ["j33-count"],
            },
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "j33-count",
                "property": "minimum",
                "value": 1,
            },
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "j33-count",
                "property": "maximum",
                "value": 99,
            },
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "j33-count",
                "property": "helpText",
                "value": "How many",
            },
            {
                "kind": "setAttributeBinding",
                "objectType": world.key("R"),
                "attributeType": "j33-count",
                "ui": {"hidden": True, "helpText": "Here"},
            },
            {
                "kind": "setRelationTypeProperty",
                "relationType": relation,
                "property": "isOriented",
                "value": False,
            },
            {
                "kind": "setApplicationProperty",
                "applicationKey": r_app,
                "property": "defaultView",
                "value": view,
            },
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    held = _model(world, draft)
    r_type = _by_key(held["objectTypes"], world.key("R"))
    assert r_type["displayAttributeTypeKey"] == "j33-count"
    assert r_type["validation"]["atLeastOneOf"] == ["j33-count"]
    assert _by_key(r_type["attributes"], "j33-count", "attributeTypeKey")["ui"] == {
        "hidden": True,
        "helpText": "Here",
    }
    count = _by_key(held["attributeTypes"], "j33-count")
    assert count["validation"] == {"minimum": 1, "maximum": 99} and count["ui"] == {
        "helpText": "How many"
    }
    assert _by_key(held["relationTypes"], relation)["isOriented"] is False
    assert _application(held, r_app)["defaultView"] == view
    outline = ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))
    assert _by_key(outline["attributeTypes"], "j33-count")["minimum"] == 1
    assert _by_key(outline["objectTypes"], world.key("R"))["displayAttribute"] == "j33-count"

    ok(_undo(world, draft, answer["version"]))
    assert _model(world, draft) == start

    text_attribute = _by_key(
        start["attributeTypes"],
        next(a["key"] for a in start["attributeTypes"] if a.get("valueType", "text") == "text"),
    )
    version = _draft(world, draft)["version"]
    for operation, pointer in (
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": text_attribute["key"],
                "property": "minimum",
                "value": 1,
            },
            "/operations/0/property",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "j33-count",
                "property": "maximum",
                "value": 0,
            },
            "/operations/0/value",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "objectType": world.key("R"),
                "property": "displayAttributeTypeKey",
                "value": "j33-unbound",
            },
            "/operations/0/value",
        ),
    ):
        if operation["property"] == "maximum":
            ok(
                _apply(
                    world,
                    draft,
                    version,
                    {
                        "kind": "setAttributeTypeProperty",
                        "attributeType": "j33-count",
                        "property": "minimum",
                        "value": 5,
                    },
                )
            )
            version = _draft(world, draft)["version"]
        error = refused(_apply(world, draft, version, operation), 422, "INVALID_OPERATION")
        assert error["details"]["pointer"] == pointer

    tightened = ok(
        _apply(
            world,
            draft,
            version,
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "j33-count",
                "property": "minimum",
                "value": 10,
            },
        )
    )
    current = _draft(world, draft)
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": current["version"]}
        )
    )
    assert compiled["valid"] is True and tightened["valid"] is True
    (diagnostic,) = [
        d
        for d in compiled["compatibility"]["diagnostics"]
        if d["path"] == "/attributeTypes/j33-count/validation/minimum"
    ]
    assert diagnostic["code"] == "ATTRIBUTE_VALIDATION_VIOLATED" and diagnostic["count"] == 1


def _matrix_application(world) -> tuple[dict[str, Any], dict[str, Any]]:
    """An empty draft built, in one request, into an application with a row type, a column type and a
    cell type, a relation matrix over them and two navigation groups; returns the draft and the answer."""
    draft = _empty_draft(world)
    parent = {"relationType": {"key": "j33-holds", "name": "Holds", "reverseName": "Held by"}}
    matrix = {
        "key": "j33-rows-by-tongue",
        "name": "Rows by tongue",
        "type": "relationMatrix",
        "config": {
            "relationTypeKey": "j33-worded",
            "direction": "outgoing",
            "rowObjectTypeKey": "j33-row",
            "columnObjectTypeKey": "j33-tongue",
            "cellObjectTypeKey": "j33-word",
            "rowColumns": ["name"],
            "columnLabelField": "name",
            "cellFields": ["j33-text"],
            "searchFields": ["name"],
            "cellActions": ["create", "edit"],
            "pageSize": 20,
        },
    }
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {"kind": "addApplication", "key": "j33-nav", "name": "J33 Navigation"},
            {
                "kind": "addObjectType",
                "applicationKey": "j33-nav",
                "key": "j33-row",
                "name": "Row",
                "pluralName": "Rows",
                "parent": None,
            },
            {
                "kind": "addObjectType",
                "applicationKey": "j33-nav",
                "key": "j33-tongue",
                "name": "Tongue",
                "pluralName": "Tongues",
                "parent": None,
            },
            {
                "kind": "addObjectType",
                "applicationKey": "j33-nav",
                "key": "j33-word",
                "name": "Word",
                "pluralName": "Words",
                "parent": {**parent, "objectTypes": ["j33-tongue"]},
            },
            _attribute("j33-text", "Text"),
            {"kind": "attachAttribute", "objectType": "j33-word", "attributeType": "j33-text"},
            {
                "kind": "addRelationType",
                "key": "j33-worded",
                "name": "Worded",
                "reverseName": "Words of",
            },
            {
                "kind": "allowRelation",
                "relationType": "j33-worded",
                "from": "j33-row",
                "to": "j33-word",
                "cardinality": "one-to-many",
            },
            {"kind": "addView", "applicationKey": "j33-nav", "view": matrix},
            {"kind": "addNavigationGroup", "applicationKey": "j33-nav", "label": "First"},
            {"kind": "addNavigationGroup", "applicationKey": "j33-nav", "label": "Second"},
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    return draft, answer


def _navigation(world, draft: dict[str, Any]) -> dict[str, Any]:
    return _application(_model(world, draft), "j33-nav")["navigation"]


@pytest.mark.journey("J33.9", "J33.2")
@pytest.mark.structures("A1")
def test_a_relation_matrix_is_placed_in_a_group_ordered_moved_and_opened_on(world):
    """Given an application with a matrix and two groups. When the matrix and its row type are placed
    in the first group, reordered, the matrix moved to the second group and the row type set to open
    on it. Then each step shows in the model and the outline in the group's one order, the matrix
    stands in one group only, and the draft installs. Taking an entry out and clearing the opening
    leave the application without navigation members it no longer needs."""
    draft, built = _matrix_application(world)
    view = "j33-rows-by-tongue"
    place = {"kind": "placeCollection", "applicationKey": "j33-nav"}

    step = ok(
        _apply(
            world,
            draft,
            built["version"],
            {**place, "collection": "j33-row", "group": "first"},
            {**place, "view": view, "group": "first", "position": 0},
        )
    )
    assert _navigation(world, draft)["groups"][0]["collections"] == [{"view": view}, "j33-row"]
    outline = _by_key(_outline(world, draft)["applications"], "j33-nav")["navigation"]
    assert outline["groups"][0]["entries"] == [{"view": view}, {"collection": "j33-row"}]
    assert outline["ungrouped"] == ["j33-tongue", "j33-word"]

    step = ok(
        _apply(
            world,
            draft,
            step["version"],
            {**place, "collection": "j33-row", "group": "first", "position": 0},
        )
    )
    assert _navigation(world, draft)["groups"][0]["collections"] == ["j33-row", {"view": view}]

    step = ok(_apply(world, draft, step["version"], {**place, "view": view, "group": "second"}))
    groups = _navigation(world, draft)["groups"]
    assert [g["collections"] for g in groups] == [["j33-row"], [{"view": view}]]

    step = ok(
        _apply(
            world,
            draft,
            step["version"],
            {
                "kind": "setCollectionOpening",
                "applicationKey": "j33-nav",
                "collection": "j33-row",
                "view": view,
            },
        )
    )
    assert _navigation(world, draft)["opens"] == {"j33-row": view}
    assert _by_key(_outline(world, draft)["applications"], "j33-nav")["navigation"]["opens"] == {
        "j33-row": view
    }

    # The step's inverse puts the opening back to the default view.
    undone = ok(_undo(world, draft, step["version"]))
    assert "opens" not in _navigation(world, draft)
    redone = ok(_redo(world, draft, undone["version"]))
    assert _navigation(world, draft)["opens"] == {"j33-row": view}

    step = ok(_apply(world, draft, redone["version"], {**place, "view": view, "group": None}))
    assert _navigation(world, draft)["groups"][1]["collections"] == []
    release = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": step["version"]}
        ),
        201,
    )
    assert release["id"]


@pytest.mark.journey("J33.9", "J33.2")
@pytest.mark.structures("A1")
def test_adding_several_entries_is_one_step_and_one_undo(world):
    """Given two groups and a matrix. When one request places the row type, the tongue type and the
    matrix in the first group, moving the tongue from the second. Then it is one step of the history,
    and one undo restores both groups as they were."""
    draft, built = _matrix_application(world)
    view = "j33-rows-by-tongue"
    place = {"kind": "placeCollection", "applicationKey": "j33-nav"}
    first = ok(
        _apply(
            world, draft, built["version"], {**place, "collection": "j33-tongue", "group": "second"}
        )
    )
    before = _navigation(world, draft)
    several = ok(
        _apply(
            world,
            draft,
            first["version"],
            {**place, "collection": "j33-row", "group": "first"},
            {**place, "collection": "j33-tongue", "group": "first"},
            {**place, "view": view, "group": "first"},
        )
    )
    assert [g["collections"] for g in _navigation(world, draft)["groups"]] == [
        ["j33-row", "j33-tongue", {"view": view}],
        [],
    ]
    latest = _history(world, draft)["items"][-3:]
    assert len({entry["step"] for entry in latest}) == 1
    ok(_undo(world, draft, several["version"]))
    assert _navigation(world, draft) == before


@pytest.mark.journey("J33.9", "J33.2")
@pytest.mark.structures("A1")
def test_a_matrix_entry_follows_its_view_key_and_goes_with_its_view(world):
    """Given a matrix in a group that its row type opens on. When the view is given a new key, then
    the group's entry and the opening follow it. When the view is removed, the entry and the opening
    go with it, and one undo returns both."""
    draft, built = _matrix_application(world)
    view = "j33-rows-by-tongue"
    place = {"kind": "placeCollection", "applicationKey": "j33-nav"}
    step = ok(
        _apply(
            world,
            draft,
            built["version"],
            {**place, "view": view, "group": "first"},
            {
                "kind": "setCollectionOpening",
                "applicationKey": "j33-nav",
                "collection": "j33-row",
                "view": view,
            },
        )
    )
    renamed = ok(
        _apply(
            world,
            draft,
            step["version"],
            {
                "kind": "setKey",
                "element": {"applicationKey": "j33-nav", "view": view},
                "key": "j33-matrix",
            },
        )
    )
    assert _navigation(world, draft)["groups"][0]["collections"] == [{"view": "j33-matrix"}]
    assert _navigation(world, draft)["opens"] == {"j33-row": "j33-matrix"}
    ok(_undo(world, draft, renamed["version"]))
    assert _navigation(world, draft)["groups"][0]["collections"] == [{"view": view}]

    removed = ok(
        _apply(
            world,
            draft,
            _draft(world, draft)["version"],
            {"kind": "removeView", "applicationKey": "j33-nav", "view": view},
        )
    )
    assert removed["valid"] is True, removed["diagnostics"]
    assert _navigation(world, draft)["groups"][0]["collections"] == []
    assert "opens" not in _navigation(world, draft)
    ok(_undo(world, draft, removed["version"]))
    assert _navigation(world, draft)["groups"][0]["collections"] == [{"view": view}]
    assert _navigation(world, draft)["opens"] == {"j33-row": view}


@pytest.mark.journey("J33.9")
@pytest.mark.structures("A1")
def test_navigation_entries_that_name_nothing_valid_are_refused(world):
    """Given an application with a matrix. When an operation places a table view or an unknown view,
    or sets an opening on a view of another collection, it is refused INVALID_OPERATION at its
    parameter. When a document names a table as a matrix entry, a matrix in two groups, or an opening
    for a view of another collection, validation refuses each at its pointer."""
    draft, built = _matrix_application(world)
    place = {"kind": "placeCollection", "applicationKey": "j33-nav"}
    tongue_view = next(
        v["key"]
        for v in _application(_model(world, draft), "j33-nav")["views"]
        if v.get("objectTypeKey") == "j33-tongue"
    )
    for operation, parameter in (
        ({**place, "view": tongue_view, "group": "first"}, "view"),
        ({**place, "view": "j33-nowhere", "group": "first"}, "view"),
        (
            {**place, "view": "j33-rows-by-tongue", "collection": "j33-row", "group": "first"},
            "collection",
        ),
        (
            {
                "kind": "setCollectionOpening",
                "applicationKey": "j33-nav",
                "collection": "j33-row",
                "view": tongue_view,
            },
            "view",
        ),
        (
            {
                "kind": "setCollectionOpening",
                "applicationKey": "j33-nav",
                "collection": "j33-nowhere",
                "view": tongue_view,
            },
            "collection",
        ),
    ):
        assert parameter in str(
            refused(_apply(world, draft, built["version"], operation), 422, "INVALID_OPERATION")
        )

    model = _model(world, draft)
    navigation = _application(model, "j33-nav")["navigation"] = {
        "groups": [
            {
                "key": "first",
                "label": "First",
                "collections": [{"view": tongue_view}, {"view": "j33-rows-by-tongue"}],
            },
            {"key": "second", "label": "Second", "collections": [{"view": "j33-rows-by-tongue"}]},
        ],
        "opens": {"j33-tongue": "j33-rows-by-tongue"},
    }
    found = {
        (d["code"], d["path"])
        for d in ok(world.api.post("/model-validations", {"model": model}))["diagnostics"]
        if d["severity"] == "error"
    }
    pointer = "/applications/j33-nav/navigation"
    assert ("INVALID_REFERENCE", f"{pointer}/groups/first/collections/0/view") in found, found
    navigation["groups"][0]["collections"].pop(0)
    found = {
        (d["code"], d["path"])
        for d in ok(world.api.post("/model-validations", {"model": model}))["diagnostics"]
        if d["severity"] == "error"
    }
    assert ("INVALID_MODEL", f"{pointer}/groups/second/collections/0") in found, found
    navigation["groups"][1]["collections"].clear()
    found = {
        (d["code"], d["path"])
        for d in ok(world.api.post("/model-validations", {"model": model}))["diagnostics"]
        if d["severity"] == "error"
    }
    assert found == {("INVALID_REFERENCE", f"{pointer}/opens/j33-tongue")}, found


@pytest.mark.journey("J33.20")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight", "Vrt", "R", "R.u")
def test_a_relationships_table_is_added_to_a_draft_and_checked(world):
    """Given the active model with a relationship that carries a value. When a relationships table
    over it is added to a draft of it. Then the draft is valid and the outline lists the table under
    its from type's collection; one with a column naming an attribute the relationship does not
    carry leaves the draft invalid at that column."""
    draft = _draft_of_active(world)
    application = world.app("H")
    table = {
        "key": "j33-relationship-rows",
        "name": "Relationship rows",
        "type": "relationTable",
        "config": {
            "relationTypeKey": world.key("Bnn"),
            "fromObjectTypeKey": world.key("H"),
            "toObjectTypeKey": world.key("K"),
            "fromColumns": ["name"],
            "toColumns": ["name"],
            "attributeColumns": [world.key("Bnn.weight")],
            "filterFields": [f"relation:{world.key('Bnn.weight')}"],
            "sortFields": ["from:name", f"relation:{world.key('Bnn.weight')}"],
            "defaultSort": "-relation:" + world.key("Bnn.weight"),
            "groupBy": "to",
            "pageSize": 20,
        },
    }
    added = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {"kind": "addView", "applicationKey": application, "view": table},
        )
    )
    assert added["valid"] is True, added["diagnostics"]
    outline = _outline(world, draft)
    view = _by_key(_by_key(outline["applications"], application)["views"], table["key"])
    assert view["type"] == "relationTable" and view["collection"] == world.key("H")

    broken = {
        **table,
        "key": "j33-broken-rows",
        "config": {**table["config"], "attributeColumns": [world.key("R.u")]},
    }
    refusal = ok(
        _apply(
            world,
            draft,
            added["version"],
            {"kind": "addView", "applicationKey": application, "view": broken},
        )
    )
    assert refusal["valid"] is False
    assert any("attributeColumns/0" in item["path"] for item in refusal["diagnostics"]), refusal[
        "diagnostics"
    ]
