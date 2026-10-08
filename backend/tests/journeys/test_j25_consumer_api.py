"""J25 — Define a consumer API in the model (USER_JOURNEYS.md)."""

import copy
import json

import pytest
from scenario import consumer_object, consumer_resolve, consumer_xref, ok, refused

from app.db import SessionLocal
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.compiler import parse_model
from app.engine.model.consumer_definitions import consumer_apis

API = ("R", "R.u", "R.b", "R.dt", "K", "B1n")


def _model(world, suffix, **definition):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    return world.with_consumer_api(model, **definition)


def _compile(world, model):
    draft = ok(world.api.post("/model-drafts", {"name": "Consumer API", "model": model}), 201)
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )
    return draft, compiled


def _install(world, draft):
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
    )


def _activate_definition(world, suffix, **definition):
    draft, _compiled = _compile(world, _model(world, suffix, **definition))
    release = ok(_install(world, draft), 201)
    ok(world.activate(release["id"]))
    return release


def _codes(compiled):
    return {d["code"] for d in compiled["consumerContracts"]["diagnostics"]}


@pytest.mark.journey("J25")
@pytest.mark.structures(*API)
def test_declare_validate_compare_and_activate_a_consumer_api(world):
    """Given a model with no consumer API. When a draft declares one and is compiled; a draft whose
    field reads an undeclared attribute is compiled and installed; the valid one installed and
    activated. Then the valid draft is compatible; the broken one is invalid at the field's JSON
    pointer, and installing it is refused with that pointer; the valid one activates. When a later
    draft removes an output field at the same contract version. Then compiling asks for a version,
    activation is refused leaving the selection, and with a higher version it activates."""
    _draft, compiled = _compile(world, _model(world, "api"))
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "compatible"

    broken = _model(world, "broken")
    broken["consumerApis"][-1]["object"]["fields"]["number"] = "no-such-attribute"
    broken_draft, broken_compiled = _compile(world, broken)
    assert broken_compiled["valid"] is False
    pointer = "/consumerApis/journey-api/object/fields/number"
    assert any(d["path"].startswith(pointer) for d in broken_compiled["diagnostics"]), (
        broken_compiled["diagnostics"]
    )
    error = refused(_install(world, broken_draft), 422, "INVALID_MODEL")
    assert pointer in json.dumps(error["details"])

    _activate_definition(world, "api")
    state = ok(world.api.get("/model-runtime-state"))
    draft, compiled = _compile(world, _model(world, "removed", drop_flag=True))
    assert compiled["consumerContracts"]["classification"] == "version_required"
    (diagnostic,) = [
        d
        for d in compiled["consumerContracts"]["diagnostics"]
        if d["code"] == "CONSUMER_CONTRACT_VERSION_REQUIRED"
    ]
    # A removed field has no place in the new document: the diagnostic points at its parent and
    # names it.
    assert diagnostic["path"].startswith("/consumerApis/journey-api/object")
    assert "flag" in diagnostic["path"] + diagnostic["message"], diagnostic
    release = ok(_install(world, draft), 201)
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    assert ok(world.api.get("/model-runtime-state")) == state
    _activate_definition(world, "removed-v2", drop_flag=True, version=2)


@pytest.mark.journey("J25.1")
@pytest.mark.structures(*API)
def test_additions_are_compatible_and_removals_and_lower_versions_are_reported(world):
    """Given an active consumer API at contract version 2. When drafts add a field and a list, omit the
    whole API, or lower its contract version to 1. Then the first is compatible, the second compatible with a removal warning,
    the third reports the decreased version."""
    _activate_definition(world, "api", version=2)
    _draft, added = _compile(world, _model(world, "added", extra=True, version=2))
    assert added["consumerContracts"]["classification"] == "compatible"

    omitted = copy.deepcopy(world.configuration.model)
    omitted["release"]["version"] += "-omitted"
    _draft, without = _compile(world, omitted)
    assert without["consumerContracts"]["classification"] == "compatible"
    assert "CONSUMER_API_REMOVED" in _codes(without)

    _draft, lowered = _compile(world, _model(world, "lowered", version=1))
    assert "CONSUMER_CONTRACT_VERSION_DECREASED" in _codes(lowered) | {
        d["code"] for d in lowered["diagnostics"]
    }


@pytest.mark.journey("J25.2")
@pytest.mark.structures(*API)
def test_a_model_change_that_changes_a_projection_needs_a_new_version(world):
    """Given an active consumer API projecting over a one-to-many relationship from its many side (one
    related record each). When a draft makes that relationship many-to-many at the same contract
    version, and is compiled, compared and
    activated. Then a new version is required, naming the projection, and activation is refused."""
    active = _activate_definition(world, "api")
    model = _model(world, "wider")
    binding = next(
        b for b in model["objectTypeRelations"] if b["relationTypeKey"] == world.key("B1n")
    )
    binding["cardinality"] = "many-to-many"
    draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    assert any(
        "related/ledger" in d["path"] for d in compiled["consumerContracts"]["diagnostics"]
    )
    release = ok(_install(world, draft), 201)
    diff = ok(world.api.get(f"/model-releases/{release['id']}/diff", againstReleaseId=active["id"]))
    assert diff["consumerContracts"]["classification"] == "version_required"
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.u")
def test_the_identity_reads_the_object_id(world):
    """A definition whose id field reads an attribute is refused with 422 INVALID_MODEL at
    /consumerApis/<key>/object/fields/<id field>/from."""
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-former-id"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["object"]["fields"][world.key("Capi.id")]["from"] = world.key("R.u")
    draft, _compiled = _compile(world, model)
    error = refused(_install(world, draft), 422, "INVALID_MODEL")
    pointer = f"/consumerApis/{world.key('Capi')}/object/fields/{world.key('Capi.id')}/from"
    assert any(d["path"] == pointer for d in error["details"]), error["details"]


def _capi(model, world):
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    return definition


def _capi_model(world, suffix):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    return model, _capi(model, world)


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.n", "K.code")
def test_a_list_sorts_by_a_scalar_attribute_of_its_type(world):
    """An unknown attribute, a JSON attribute and an attribute the list's type does not bind are each
    refused at /consumerApis/<key>/operations/lists/<list>/sortBy. Changing sortBy is reported as
    version_required. A filter named from, seek or includeTotal is refused as reserved."""
    pointer = f"/consumerApis/{world.key('Capi')}/operations/lists/{world.key('Capi.all')}/sortBy"
    json_key = "consumer-notes"
    for sort_by in ("no-such-attribute", json_key, world.key("K.code")):
        model, definition = _capi_model(world, f"sort-{sort_by}")
        model["attributeTypes"].append({"key": json_key, "name": "Notes", "valueType": "json"})
        r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
        r_type["attributes"].append({"attributeTypeKey": json_key, "order": 900})
        definition["operations"]["lists"][world.key("Capi.all")]["sortBy"] = sort_by
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, sort_by
        assert any(d["path"] == pointer for d in compiled["diagnostics"]), compiled["diagnostics"]

    model, definition = _capi_model(world, "sort-name")
    del definition["operations"]["lists"][world.key("Capi.all")]["sortBy"]
    _draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    assert any(
        d["path"].startswith(f"/consumerApis/{world.key('Capi')}/operations/lists")
        for d in compiled["consumerContracts"]["diagnostics"]
    )

    for name in ("from", "seek", "includeTotal"):
        model, definition = _capi_model(world, f"reserved-{name}")
        definition["filters"][name] = {"byType": True}
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, name
        reserved = f"/consumerApis/{world.key('Capi')}/filters/{name}"
        assert any(d["path"] == reserved for d in compiled["diagnostics"]), compiled["diagnostics"]


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.u", "K.code", "B11")
def test_contains_reads_text_only(world):
    """A contains weight on id, or on an integer attribute, is refused at its
    /operations/xref/…/contains pointer: it could never match."""
    number = "consumer-serial"
    base = f"/consumerApis/{world.key('Capi')}/operations/xref"
    for where in ("own-id", "own-integer", "promoted-id"):
        model, definition = _capi_model(world, f"contains-{where}")
        model["attributeTypes"].append(
            {"key": number, "name": "Serial", "valueType": "integer", "features": {"unique": True}}
        )
        r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
        r_type["attributes"].append({"attributeTypeKey": number, "order": 900})
        if where == "promoted-id":
            first_of = definition["operations"]["xref"]["alsoMatchThrough"][0]["firstOf"]
            first_of.append({"field": "id", "contains": 5})
            pointer = f"{base}/alsoMatchThrough/0/firstOf/{len(first_of) - 1}/contains"
        else:
            field = "id" if where == "own-id" else number
            match_on = definition["operations"]["xref"]["matchOn"]
            match_on.append({"field": field, "exact": 5, "contains": 5})
            pointer = f"{base}/matchOn/{len(match_on) - 1}/contains"
        draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, where
        assert any(d["path"] == pointer for d in compiled["diagnostics"]), compiled["diagnostics"]
        error = refused(_install(world, draft), 422, "INVALID_MODEL")
        assert pointer in json.dumps(error["details"])


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "Bown", "Bscope", "G")
def test_scores_from_needs_a_promoted_entry_and_is_contract(world):
    """scoreOnlyMatching on a filter over related records no alsoMatchThrough entry reads is refused at
    its /filters/<name>/scoreOnlyMatching pointer; turning a filter's scoreOnlyMatching off is
    version_required."""
    permit = world.key("Capi.permit")
    model, definition = _capi_model(world, "scores-from-bown")
    definition["filters"][permit]["scoreOnlyMatching"] = True
    draft, compiled = _compile(world, model)
    pointer = f"/consumerApis/{world.key('Capi')}/filters/{permit}/scoreOnlyMatching"
    assert compiled["valid"] is False
    assert any(d["path"] == pointer for d in compiled["diagnostics"]), compiled["diagnostics"]
    error = refused(_install(world, draft), 422, "INVALID_MODEL")
    assert pointer in json.dumps(error["details"])

    watch = world.key("Capi.watch")
    model, definition = _capi_model(world, "scores-from-off")
    definition["filters"][watch]["scoreOnlyMatching"] = False
    _draft, compiled = _compile(world, model)
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "version_required"
    changed = f"/consumerApis/{world.key('Capi')}/filters/{watch}/scoreOnlyMatching"
    assert any(d["path"] == changed for d in compiled["consumerContracts"]["diagnostics"]), compiled[
        "consumerContracts"
    ]["diagnostics"]


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "Bown", "Bscope", "G", "M")
def test_targetable_is_contract(world):
    """A candidate turning crosswalk off for a filter is version_required at
    /filters/<name>/crosswalk; turning it back on needs no new version. crosswalk on an under filter
    is refused at its pointer."""
    watch = world.key("Capi.watch")
    changed = f"/consumerApis/{world.key('Capi')}/filters/{watch}/crosswalk"
    model, definition = _capi_model(world, "targetable-off")
    definition["filters"][watch]["crosswalk"] = False
    draft, compiled = _compile(world, model)
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "version_required"
    assert any(d["path"] == changed for d in compiled["consumerContracts"]["diagnostics"]), compiled[
        "consumerContracts"
    ]["diagnostics"]

    definition["contractVersion"] = 2
    model["release"]["version"] += "-v2"
    draft, _compiled = _compile(world, model)
    ok(world.activate(ok(_install(world, draft), 201)["id"]))
    model, definition = _capi_model(world, "targetable-on")
    definition["contractVersion"] = 2
    _draft, compiled = _compile(world, model)
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "compatible"

    container = world.key("Capi.container")
    model, definition = _capi_model(world, "targetable-ancestor")
    definition["filters"][container]["crosswalk"] = True
    _draft, compiled = _compile(world, model)
    assert compiled["valid"] is False
    pointer = f"/consumerApis/{world.key('Capi')}/filters/{container}/crosswalk"
    assert [d["path"] for d in compiled["diagnostics"]] == [pointer], compiled["diagnostics"]


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "B11", "Bown", "K", "D")
def test_a_projection_names_its_items_type_where_the_types_are_exposed(world):
    """A projection field with the source objectType gives each related record's public type name
    (C-D73). Over a route reaching a type the definition does not expose (B11 to K) it is refused at
    the field; over one reaching only exposed types (Bown to D) adding it is compatible, and removing it
    again is version_required at the projection's fields."""
    key, paired, permits = world.key("Capi"), world.key("Capi.B11"), world.key("Capi.Bown")
    model, definition = _capi_model(world, "type-of-unexposed")
    definition["object"]["related"][paired]["fields"]["tokenType"] = "objectType"
    draft, compiled = _compile(world, model)
    pointer = f"/consumerApis/{key}/object/related/{paired}/fields/tokenType"
    assert compiled["valid"] is False
    assert [d["path"] for d in compiled["diagnostics"]] == [pointer], compiled["diagnostics"]
    error = refused(_install(world, draft), 422, "INVALID_MODEL")
    assert pointer in json.dumps(error["details"])

    model, definition = _capi_model(world, "type-added")
    definition["object"]["related"][permits]["fields"]["permitType"] = "objectType"
    draft, compiled = _compile(world, model)
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "compatible"
    ok(world.activate(ok(_install(world, draft), 201)["id"]))

    model, definition = _capi_model(world, "type-removed")
    _draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    changed = f"/consumerApis/{key}/object/related/{permits}/fields"
    assert any(d["path"] == changed for d in compiled["consumerContracts"]["diagnostics"]), compiled[
        "consumerContracts"
    ]["diagnostics"]


def _events(world):
    """Two events on ``Capi``: one over R and R2 with every change, watching the code, the name, the
    parent and the B11 projection; one over D, creations and deletions only, with no watch."""
    return [
        {
            "key": "ledger-changed",
            "objectTypes": [world.key("R"), world.key("R2")],
            "changes": ["created", "updated", "deleted"],
            "watch": {
                "fields": [world.key("Capi.code"), world.key("Capi.name"), world.key("Capi.parent")],
                "related": [world.key("Capi.B11")],
            },
        },
        {"key": "permit-churn", "objectTypes": [world.key("D")], "changes": ["created", "deleted"]},
    ]


def _with_events(world, suffix, events=None):
    model, definition = _capi_model(world, suffix)
    definition["operations"]["events"] = {"custom": _events(world) if events is None else events}
    return model, definition


@pytest.mark.journey("J25.3")
@pytest.mark.structures("Capi", "R", "R2", "D", "B11")
def test_declare_events(world):
    """Given the active Capi without events. When a draft gives it two events and is compiled,
    installed and activated. Then it is valid and compatible (adding events), activates, and the
    release's model holds both events as declared."""
    model, _definition = _with_events(world, "events")
    draft, compiled = _compile(world, model)
    assert compiled["valid"] is True, compiled["diagnostics"]
    assert compiled["consumerContracts"]["classification"] == "compatible"
    release = ok(_install(world, draft), 201)
    ok(world.activate(release["id"]))
    read = ok(world.api.get(f"/model-releases/{release['id']}", includeModel=True))
    assert _capi(read["model"], world)["operations"]["events"] == {"custom": _events(world)}


@pytest.mark.journey("J25.3")
@pytest.mark.structures("Capi", "R", "R2", "D", "K", "B11")
def test_event_mistakes_are_refused_at_their_pointer(world):
    """Each mistake in an event is refused with 422 INVALID_MODEL at its pointer under
    /consumerApis/<Capi>/operations/events/custom/<index>: a type not exposed or unknown, a repeated
    or upper-case key, no change or a repeated one, a watch naming a role rather than its output or an
    unknown output, an unknown related block, an empty watch, a watch on an event without updates. An
    unknown change kind is a shape error at its position. A filter named event or after is reserved."""
    base = f"/consumerApis/{world.key('Capi')}"
    first = f"{base}/operations/events/custom/0"

    def first_event(change):
        def mutate(events):
            change(events[0])
            return events

        return mutate

    cases = {
        "not-exposed": (first_event(lambda e: e["objectTypes"].append(world.key("K"))), f"{first}/objectTypes"),
        "unknown-type": (first_event(lambda e: e["objectTypes"].append("no-such-type")), f"{first}/objectTypes"),
        "repeated-type": (first_event(lambda e: e["objectTypes"].append(world.key("R"))), f"{first}/objectTypes"),
        "repeated-key": (lambda events: events + [copy.deepcopy(events[0])], f"{base}/operations/events/custom/2"),
        "upper-key": (first_event(lambda e: e.update(key="Ledger-changed")), f"{first}/key"),
        "no-change": (first_event(lambda e: e.update(changes=[])), f"{first}/changes"),
        "repeated-change": (first_event(lambda e: e["changes"].append("deleted")), f"{first}/changes"),
        "role-name": (first_event(lambda e: e["watch"]["fields"].append("active")), f"{first}/watch/fields"),
        "unknown-output": (first_event(lambda e: e["watch"]["fields"].append("no-such-output")), f"{first}/watch/fields"),
        "unknown-projection": (
            first_event(lambda e: e["watch"]["related"].append("noSuchBlock")),
            f"{first}/watch/related",
        ),
        "empty-watch": (first_event(lambda e: e.update(watch={})), f"{first}/watch"),
        "watch-without-updates": (
            first_event(lambda e: e.update(changes=["created", "deleted"])),
            f"{first}/watch",
        ),
    }
    for name, (mutate, pointer) in cases.items():
        model, _definition = _with_events(world, f"event-{name}", mutate(_events(world)))
        draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, name
        assert any(d["path"].startswith(pointer) for d in compiled["diagnostics"]), (name, compiled["diagnostics"])
        error = refused(_install(world, draft), 422, "INVALID_MODEL")
        assert pointer in json.dumps(error["details"]), name

    events = _events(world)
    events[0]["changes"].append("renamed")
    model, _definition = _with_events(world, "event-renamed", events)
    _draft, compiled = _compile(world, model)
    assert compiled["valid"] is False
    assert any(d["path"].endswith("/operations/events/custom/0/changes/3") for d in compiled["diagnostics"]), compiled["diagnostics"]

    for name in ("event", "after"):
        model, definition = _capi_model(world, f"reserved-{name}")
        definition["filters"][name] = {"byType": True}
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, name
        reserved = f"{base}/filters/{name}"
        assert any(d["path"] == reserved for d in compiled["diagnostics"]), compiled["diagnostics"]


@pytest.mark.journey("J25.4")
@pytest.mark.structures("Capi", "R", "R2", "D", "E", "B11", "R.n")
def test_events_are_contract(world):
    """Given Capi's two events active at contract version 1. When drafts at the same version tell
    their consumers less (an event removed, a type or a change removed, a watched output removed, a
    watch added). Then each is version_required at its path, and activating one is refused until the
    version is raised. When drafts tell them more (an event, a type, a change or a watched output
    added, a watch dropped). Then each is compatible."""
    model, _definition = _with_events(world, "events")
    draft, _compiled = _compile(world, model)
    ok(world.activate(ok(_install(world, draft), 201)["id"]))
    events = f"/consumerApis/{world.key('Capi')}/operations/events"
    first, second = f"{events}/custom/0", f"{events}/custom/1"

    def drop_second(e):
        del e[1]

    def drop_r2(e):
        e[0]["objectTypes"].remove(world.key("R2"))

    def drop_deleted(e):
        e[0]["changes"].remove("deleted")

    def drop_parent(e):
        e[0]["watch"]["fields"].remove(world.key("Capi.parent"))

    def watch_second(e):
        e[1]["changes"].append("updated")
        e[1]["watch"] = {"fields": [world.key("Capi.name")]}

    narrower = {
        "drop-event": (drop_second, events),
        "drop-type": (drop_r2, f"{first}/objectTypes"),
        "drop-change": (drop_deleted, f"{first}/changes"),
        "drop-watched": (drop_parent, f"{first}/watch"),
        "add-watch": (watch_second, f"{second}/watch"),
    }
    for name, (change, path) in narrower.items():
        changed = _events(world)
        change(changed)
        model, _definition = _with_events(world, name, changed)
        draft, compiled = _compile(world, model)
        assert compiled["valid"] is True, (name, compiled["diagnostics"])
        assert compiled["consumerContracts"]["classification"] == "version_required", name
        assert any(d["path"] == path for d in compiled["consumerContracts"]["diagnostics"]), (
            name,
            compiled["consumerContracts"]["diagnostics"],
        )

    # Telling less is refused at activation until the version is raised.
    changed = _events(world)
    drop_parent(changed)
    model, _definition = _with_events(world, "less", changed)
    draft, _compiled = _compile(world, model)
    refused(world.activate(ok(_install(world, draft), 201)["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    model, _definition = _with_events(world, "less-v2", changed)
    _capi(model, world)["contractVersion"] = 2
    draft, _compiled = _compile(world, model)
    ok(world.activate(ok(_install(world, draft), 201)["id"]))
    model, _definition = _with_events(world, "events-v2")
    _capi(model, world)["contractVersion"] = 2
    draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "compatible"
    ok(world.activate(ok(_install(world, draft), 201)["id"]))

    def add_event(e):
        e.append({"key": "rate-changed", "objectTypes": [world.key("E")], "changes": ["updated"]})

    def add_type(e):
        e[0]["objectTypes"].append(world.key("E"))

    def add_change(e):
        e[1]["changes"].append("updated")

    def add_watched(e):
        e[0]["watch"]["fields"].append(world.key("Capi.n"))

    def drop_watch(e):
        del e[0]["watch"]

    for name, change in {
        "add-event": add_event,
        "add-type": add_type,
        "add-change": add_change,
        "add-watched": add_watched,
        "drop-watch": drop_watch,
    }.items():
        changed = _events(world)
        change(changed)
        model, _definition = _with_events(world, name, changed)
        _capi(model, world)["contractVersion"] = 2
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is True, (name, compiled["diagnostics"])
        assert compiled["consumerContracts"]["classification"] == "compatible", (
            name,
            compiled["consumerContracts"]["diagnostics"],
        )


# --- schema 0.9 (C18) ----------------------------------------------------------------------------


def _in_schema_0_8(world, suffix):
    """The configuration's model in schema 0.8, its definitions in the 0.8 shape (the engine's
    internal form written out), as a release stored before C18 holds them."""
    model = copy.deepcopy(world.configuration.model)
    model["schemaVersion"] = "0.8"
    model["release"]["version"] += f"-{suffix}"
    model["consumerApis"] = [
        item.model_dump(mode="json") for item in consumer_apis(parse_model(world.configuration.model))
    ]
    return model


@pytest.mark.journey("J25.6")
@pytest.mark.structures("Capi")
def test_schema_0_8_is_refused_for_new_definitions(world):
    """Given the configuration's definitions written in schema 0.8. When the document is validated,
    compiled as a draft and installed. Then each is refused at /schemaVersion naming schema 0.9. The
    same document without consumerApis installs, and a release stored in 0.8 before reads as
    stored."""
    legacy = _in_schema_0_8(world, "legacy")
    validated = ok(world.api.post("/model-validations", {"model": legacy}))
    assert validated["valid"] is False
    ((code, path, message),) = [(d["code"], d["path"], d["message"]) for d in validated["diagnostics"]]
    assert (code, path) == ("UNSUPPORTED_SCHEMA_VERSION", "/schemaVersion")
    assert "schema 0.9" in message
    draft, compiled = _compile(world, legacy)
    assert compiled["valid"] is False
    assert [(d["code"], d["path"]) for d in compiled["diagnostics"]] == [("UNSUPPORTED_SCHEMA_VERSION", "/schemaVersion")]
    error = refused(_install(world, draft), 422, "INVALID_MODEL")
    assert "UNSUPPORTED_SCHEMA_VERSION" in json.dumps(error["details"])

    without = copy.deepcopy(legacy)
    del without["consumerApis"]
    without["release"]["version"] += "-without"
    ok(_install(world, _compile(world, without)[0]), 201)

    with SessionLocal() as session:
        stored = ensure_bootstrap_release(session, parse_model(_in_schema_0_8(world, "stored")))
        session.commit()
        stored_id = stored.public_id
    read = ok(world.api.get(f"/model-releases/{stored_id}", includeModel=True))
    assert read["schemaVersion"] == "0.8"
    assert _capi(read["model"], world) == _capi(_in_schema_0_8(world, "stored"), world)


@pytest.mark.journey("J25.7")
@pytest.mark.structures("Capi", "R")
def test_a_definition_offers_the_operations_it_lists(world):
    """Given the active Capi offering every operation. When a draft lists objects only (no filter left
    scoring XREF), at the same contract version. Then a new version is required at /operations and
    activation is refused. At
    version 2 it activates: get by ID answers, XREF and batch resolve are 404 OPERATION_NOT_OFFERED,
    and its OpenAPI document leaves them out. Listing them again is compatible. resolve listed
    without xref is refused at /operations/resolve."""
    record = world.made("R", "Offered ledger")
    model, definition = _capi_model(world, "objects-only")
    del definition["operations"]["xref"], definition["operations"]["resolve"]
    del definition["filters"][world.key("Capi.watch")]["scoreOnlyMatching"]
    draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    paths = [d["path"] for d in compiled["consumerContracts"]["diagnostics"]]
    assert f"/consumerApis/{world.key('Capi')}/operations" in paths, paths
    refused(world.activate(ok(_install(world, draft), 201)["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")

    definition["contractVersion"] = 2
    model["release"]["version"] += "-v2"
    ok(world.activate(world.install(model)["id"]))
    assert ok(consumer_object(world, record["id"], version=2))[world.key("Capi.id")] == record["id"]
    for operation, response in (
        ("xref", consumer_xref(world, version=2, query="Offered")),
        ("resolve", consumer_resolve(world, {"items": [{"query": "Offered"}]}, version=2)),
    ):
        error = refused(response, 404, "OPERATION_NOT_OFFERED")
        assert error["details"] == {"operation": operation}
    document = ok(world.api.get(f"/api/consumer/{world.key('Capi')}/v2/openapi.json"))
    base = f"/api/consumer/{world.key('Capi')}/v2"
    assert f"{base}/objects/{{id}}" in document["paths"]
    assert f"{base}/xref" not in document["paths"] and f"{base}/resolve" not in document["paths"]

    model, definition = _capi_model(world, "all-again")
    definition["contractVersion"] = 2
    del definition["filters"][world.key("Capi.watch")]["scoreOnlyMatching"]
    _draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "compatible", compiled["consumerContracts"]

    model, definition = _capi_model(world, "resolve-alone")
    del definition["operations"]["xref"]
    _draft, compiled = _compile(world, model)
    assert compiled["valid"] is False
    assert [d["path"] for d in compiled["diagnostics"]] == [f"/consumerApis/{world.key('Capi')}/operations/resolve"]


@pytest.mark.journey("J25.8")
@pytest.mark.structures("Capi", "B11", "M")
def test_mistakes_are_refused_at_the_authors_pointers(world):
    """A via naming no relation, a filter with two verbs, a role given to two fields and an
    alsoMatchThrough naming no related block are each refused at their pointer in the 0.9 document,
    by compile and by install."""
    base = f"/consumerApis/{world.key('Capi')}"
    paired, kind = world.key("Capi.B11"), world.key("Capi.kind")

    def via(definition):
        definition["object"]["related"][paired]["via"] = "no-such-relation"
        return f"{base}/object/related/{paired}/via", "INVALID_REFERENCE"

    def two_verbs(definition):
        definition["filters"][kind] = {"byType": True, "under": [world.key("M")]}
        return f"{base}/filters/{kind}", "INVALID_MODEL"

    def role_twice(definition):
        fields = definition["object"]["fields"]
        fields["alsoName"] = {"role": "name", "from": "name"}
        return f"{base}/object/fields/alsoName/role", "DUPLICATE_KEY"

    def unknown_related(definition):
        definition["operations"]["xref"]["alsoMatchThrough"][0]["related"] = "noSuchBlock"
        return f"{base}/operations/xref/alsoMatchThrough/0/related", "INVALID_REFERENCE"

    for mistake in (via, two_verbs, role_twice, unknown_related):
        model, definition = _capi_model(world, mistake.__name__.replace("_", "-"))
        pointer, code = mistake(definition)
        draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, mistake.__name__
        assert [(d["code"], d["path"]) for d in compiled["diagnostics"]] == [(code, pointer)], compiled["diagnostics"]
        error = refused(_install(world, draft), 422, "INVALID_MODEL")
        assert pointer in json.dumps(error["details"]), mistake.__name__
