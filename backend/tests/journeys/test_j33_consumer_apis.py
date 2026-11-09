"""J33 — Design a model in the editor (USER_JOURNEYS.md): consumer APIs (0.10 A4c, J33.13, J33.14).

A consumer API definition of a draft changes by operations, as the model does: ``addConsumerApi``
writes a starting definition from the exposed types (D53), and four part verbs set, insert, move and
remove a part named by a JSON pointer below the definition (D51). A value of the wrong shape is
refused; a wrong reference is left to the issues (D52). The editor reads the definition with its
contract against the active release, its schema and a message example (D56); a change consumers
would notice needs a higher contract version at activation (D55, C-D17). ``setKey`` rewrites the
definitions that name a new element (D54). The tests name structures of the configuration (``R``,
``D``, ``Bown``, ``G``, ``Capi``) and elements they create under ``j33-`` keys.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from scenario import consumer_object, ok, refused
from test_j33_operations import (
    _apply,
    _by_key,
    _draft,
    _draft_of_active,
    _empty_draft,
    _model,
    _undo,
)

DISABLED = {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"}
FEED = "j33-feed"


def _definition(world, draft: dict[str, Any], key: str = FEED, part: str = "") -> Any:
    return world.api.get(f"/model-drafts/{draft['id']}/consumer-apis/{key}{part}")


def _outline_entry(world, draft: dict[str, Any], key: str) -> dict[str, Any]:
    outline = ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))
    return _by_key(outline["consumerApis"], key)


def _bound(world, model: dict[str, Any], *structures: str) -> list[str]:
    keys: list[str] = []
    for structure in structures:
        object_type = _by_key(model["objectTypes"], world.key(structure))
        keys += [b["attributeTypeKey"] for b in object_type["attributes"] if b["attributeTypeKey"] not in keys]
    return keys


def _activate(world, draft: dict[str, Any], version: int, model: dict[str, Any]) -> None:
    answer = ok(_apply(world, draft, version, {"kind": "setRelease", "version": model["release"]["version"] + "-j33"}))
    release = ok(world.api.post(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}), 201)
    ok(world.activate(release["id"]))


@pytest.mark.journey("J33.13", "J25", "J28")
@pytest.mark.structures("R", "D", "G", "Bown")
def test_a_consumer_api_defined_by_operations_is_served_after_activation(world):
    """Given a draft of the active release. When addConsumerApi exposes R and D. Then the draft is
    valid, the outline lists the definition as new and compatible, and it has the id and name, a
    field for each attribute R and D bind, Get by ID and a list per type; its schema and message
    example agree. When a field, a related block over Bown, an under filter with a list within it
    and an XREF rule are added, each in its own request, then each is one step and the draft stays
    valid, and one undo takes back only the last. After install and activate, the consumer tier
    serves an R record with the properties the schema listed, and the list of R pages it."""
    draft = _draft_of_active(world)
    model = _model(world, draft)
    r, d = world.key("R"), world.key("D")
    answer = ok(_apply(world, draft, draft["version"], {"kind": "addConsumerApi", "name": "J33 Feed", "key": FEED, "exposes": [r, d]}))
    assert answer["valid"] is True, answer["diagnostics"]

    entry = _outline_entry(world, draft, FEED)
    assert entry["mark"] == "new"
    assert entry["contractVersion"] == 1
    assert [item["objectType"] for item in entry["exposes"]] == [r, d]
    assert entry["contract"]["classification"] == "compatible"

    read = ok(_definition(world, draft))
    assert read["valid"] is True
    written = read["definition"]
    fields = written["object"]["fields"]
    assert fields["id"] == {"role": "id"}
    assert fields["name"] == {"role": "name", "from": "name"}
    sources = [value for name, value in fields.items() if name not in ("id", "name")]
    assert sources == _bound(world, model, "R", "D")
    assert written["operations"]["objects"] == {}
    assert sorted(item["of"] for item in written["operations"]["lists"].values()) == sorted([r, d])

    schema = ok(_definition(world, draft, part="/schema.json"))
    example = ok(_definition(world, draft, part="/example.json"))
    assert set(fields) <= set(schema["properties"])
    assert set(example) == set(schema["properties"])
    assert set(schema["required"]) <= set(example)

    relation = _by_key(model["relationTypes"], world.key("Bown"))
    steps = [
        {"kind": "insertConsumerApiPart", "consumerApi": FEED, "pointer": "/object/fields", "key": "j33Label", "value": "name"},
        {
            "kind": "insertConsumerApiPart",
            "consumerApi": FEED,
            "pointer": "/object/related",
            "key": "j33Owned",
            "value": {"via": relation["key"], "fields": {"ownedName": "name"}},
        },
        {
            "kind": "setConsumerApiPart",
            "consumerApi": FEED,
            "pointer": "/filters",
            "value": {"j33-region": {"under": [world.key("G")]}},
        },
        {
            "kind": "insertConsumerApiPart",
            "consumerApi": FEED,
            "pointer": "/operations/lists",
            "key": "j33-in-region",
            "value": {"of": d, "within": {"filter": "j33-region"}},
        },
        {
            "kind": "setConsumerApiPart",
            "consumerApi": FEED,
            "pointer": "/operations/xref",
            "value": {"matchOn": [{"field": "name", "exact": 100}]},
        },
    ]
    for operation in steps:
        step = ok(_apply(world, draft, answer["version"], operation))
        assert step["version"] == answer["version"] + 1
        assert step["valid"] is True, step["diagnostics"]
        answer = step
    undone = ok(_undo(world, draft, answer["version"]))
    written = ok(_definition(world, draft))["definition"]
    assert "xref" not in written["operations"]
    assert "j33-in-region" in written["operations"]["lists"]
    assert written["object"]["related"]["j33Owned"]["via"] == relation["key"]

    schema = ok(_definition(world, draft, part="/schema.json"))
    _activate(world, draft, undone["version"], model)
    record = world.made("R", "J33 served")
    served = ok(consumer_object(world, record["id"], api=FEED))
    assert set(served) <= set(schema["properties"])
    assert {"id", "name", "j33Label", "j33Owned"} <= set(served)
    assert served["id"] == record["id"]
    assert served["j33Label"] == "J33 served"
    list_key = next(key for key, item in written["operations"]["lists"].items() if item["of"] == r)
    page = ok(world.api.get(f"/api/consumer/{FEED}/v1/lists/{list_key}"))
    assert record["id"] in [item["id"] for item in page["items"]]


@pytest.mark.journey("J33.13", "J33.8", "J25.8")
@pytest.mark.structures("R", "D")
def test_a_wrong_source_is_an_issue_and_a_value_of_the_wrong_shape_is_refused(world):
    """Given a draft with a consumer API exposing R and D. When a field naming no attribute is
    inserted, then the step applies and the draft is invalid with the diagnostic at the source's
    pointer, tied to the definition in the outline. When an XREF weight is a text, a position is
    out of range, or the definition is unknown, then the request is refused INVALID_OPERATION at its
    parameter and the draft's version is unchanged."""
    draft = _draft_of_active(world)
    added = ok(
        _apply(world, draft, draft["version"], {"kind": "addConsumerApi", "name": "J33 Feed", "key": FEED, "exposes": [world.key("R"), world.key("D")]})
    )
    wrong = ok(
        _apply(world, draft, added["version"], {"kind": "insertConsumerApiPart", "consumerApi": FEED, "pointer": "/object/fields", "key": "j33Lost", "value": "j33-no-such-attribute"})
    )
    assert wrong["valid"] is False
    pointers = [item["path"] for item in wrong["diagnostics"]]
    assert f"/consumerApis/{FEED}/object/fields/j33Lost" in [p.rsplit("/source", 1)[0].rsplit("/from", 1)[0] for p in pointers]
    outline = ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))
    tied = [item for item in outline["diagnostics"] if item["path"].startswith(f"/consumerApis/{FEED}")]
    assert tied and all(item["element"] == {"consumerApi": FEED} for item in tied)
    assert ok(_definition(world, draft))["valid"] is False

    for operation, parameter in (
        ({"kind": "setConsumerApiPart", "consumerApi": FEED, "pointer": "/operations/xref", "value": {"matchOn": [{"field": "name", "exact": "high"}]}}, "value"),
        ({"kind": "moveConsumerApiPart", "consumerApi": FEED, "pointer": "/object/fields/name", "position": 99}, "position"),
        ({"kind": "removeConsumerApiPart", "consumerApi": "j33-no-such-api", "pointer": "/object/fields/name"}, "consumerApi"),
    ):
        error = refused(_apply(world, draft, wrong["version"], operation), 422, "INVALID_OPERATION")
        assert error["details"]["pointer"] == f"/operations/0/{parameter}"
        assert _draft(world, draft)["version"] == wrong["version"]


@pytest.mark.journey("J33.14", "J25.1", "J28")
@pytest.mark.structures("Capi", "R", "Capi.dt")
def test_a_field_consumers_read_needs_a_higher_contract_version_to_be_removed(world):
    """Given a draft of the active release with its consumer API. When a field the active release
    serves is removed, then the outline's contract is version_required at the field's pointer and
    activation is refused CONSUMER_CONTRACT_VERSION_REQUIRED. When the contract version is raised by
    one step, then the contract is compatible, the draft activates, version 2 serves the record
    without the field and version 1 answers 404."""
    draft = _draft_of_active(world)
    model = _model(world, draft)
    api, field = world.key("Capi"), world.key("Capi.dt")
    removed = ok(_apply(world, draft, draft["version"], {"kind": "removeConsumerApiPart", "consumerApi": api, "pointer": f"/object/fields/{field}"}))
    assert removed["valid"] is True, removed["diagnostics"]
    entry = _outline_entry(world, draft, api)
    assert entry["mark"] == "changed"
    assert entry["contract"]["classification"] == "version_required"
    assert any(item["path"].startswith(f"/consumerApis/{api}/object") for item in entry["contract"]["diagnostics"])

    answer = ok(_apply(world, draft, removed["version"], {"kind": "setRelease", "version": model["release"]["version"] + "-j33"}))
    release = ok(world.api.post(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}), 201)
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")

    raised = ok(_apply(world, draft, answer["version"], {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": "/contractVersion", "value": 2}))
    entry = _outline_entry(world, draft, api)
    assert entry["contractVersion"] == 2
    assert entry["contract"]["classification"] == "compatible"
    answer = ok(_apply(world, draft, raised["version"], {"kind": "setRelease", "version": model["release"]["version"] + "-j33b"}))
    release = ok(world.api.post(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": answer["version"]}), 201)
    ok(world.activate(release["id"]))

    record = world.made("R", "J33 versioned")
    served = ok(consumer_object(world, record["id"], version=2))
    assert field not in served and served[world.key("Capi.id")] == record["id"]
    refused(consumer_object(world, record["id"], version=1), 404, "CONTRACT_VERSION_NOT_FOUND")


@pytest.mark.journey("J33.13", "J33.2")
@pytest.mark.structures("R")
def test_a_key_changed_after_it_is_exposed_is_rewritten_in_the_definition(world):
    """Given a draft with a new type under R, a new attribute it binds, and a consumer API exposing
    the type with a field from the attribute and a list of it. When setKey re-keys the type and the
    attribute, then the definition names the new keys and the draft is valid; one undo puts the old
    keys back in the definition."""
    draft = _draft_of_active(world)
    operations = [
        {
            "kind": "addObjectType",
            "applicationKey": world.app("R"),
            "key": "j33-note",
            "name": "Note",
            "pluralName": "Notes",
            "parent": {"objectTypes": [world.key("R")], "relationType": {"key": "j33-has-note", "name": "Has note", "reverseName": "Note of"}},
        },
        {"kind": "addAttributeType", "key": "j33-text", "name": "Note text", "valueType": "text"},
        {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-text"},
        {"kind": "addConsumerApi", "name": "J33 Feed", "key": FEED, "exposes": ["j33-note"]},
    ]
    answer = ok(_apply(world, draft, draft["version"], *operations))
    assert answer["valid"] is True, answer["diagnostics"]
    before = ok(_definition(world, draft))["definition"]
    assert "j33-text" in before["object"]["fields"].values()

    renamed = ok(
        _apply(
            world,
            draft,
            answer["version"],
            {"kind": "setKey", "element": {"objectType": "j33-note"}, "key": "j33-memo"},
            {"kind": "setKey", "element": {"attributeType": "j33-text"}, "key": "j33-body"},
        )
    )
    assert renamed["valid"] is True, renamed["diagnostics"]
    after = ok(_definition(world, draft))["definition"]
    assert after["exposes"] == ["j33-memo"]
    assert "j33-body" in after["object"]["fields"].values()
    assert [item["of"] for item in after["operations"]["lists"].values()] == ["j33-memo"]
    assert "j33-note" not in str(after) and "j33-text" not in str(after)

    ok(_undo(world, draft, renamed["version"]))
    assert ok(_definition(world, draft))["definition"] == before


@pytest.mark.journey("J33.13", "J25.1", "J33.8")
@pytest.mark.structures("Capi")
def test_a_removed_consumer_api_is_a_warning_and_undo_puts_it_back(world):
    """Given a draft of the active release. When its consumer API is removed, then the compile's
    consumer contracts warn CONSUMER_API_REMOVED; undo returns the definition exactly; adding a
    consumer API under a key taken is refused keyTaken."""
    draft = _draft_of_active(world)
    api = world.key("Capi")
    before = _model(world, draft)["consumerApis"]
    removed = ok(_apply(world, draft, draft["version"], {"kind": "removeConsumerApi", "consumerApi": api}))
    compiled = ok(world.api.post(f"/model-drafts/{draft['id']}/compile", {"expectedVersion": removed["version"]}))
    assert [item["code"] for item in compiled["consumerContracts"]["diagnostics"]] == ["CONSUMER_API_REMOVED"]

    undone = ok(_undo(world, draft, removed["version"]))
    assert _model(world, draft)["consumerApis"] == before
    error = refused(
        _apply(world, draft, undone["version"], {"kind": "addConsumerApi", "name": "Again", "key": api, "exposes": [world.key("R")]}),
        422,
        "INVALID_OPERATION",
    )
    assert error["details"]["reason"] == "keyTaken"


@pytest.mark.journey("J33.13", "J25.9")
@pytest.mark.structures("Capi")
def test_raising_a_version_keeps_the_previous_one_and_it_is_announced_then_stopped(world):
    """Given a draft of the active release. When the editor raises Capi's version, then version 1 is
    kept frozen with today's day as deprecated and the draft stays valid; a sunset day is set (a bad
    one is refused), the version stopped, and each step undone exactly. A raise that does not keep
    leaves no earlier version, and a version not above the current one is refused."""
    draft = _draft_of_active(world)
    api = world.key("Capi")
    before = _by_key(_model(world, draft)["consumerApis"], api)

    raised = ok(_apply(world, draft, draft["version"], {"kind": "raiseConsumerApiVersion", "consumerApi": api}))
    assert raised["valid"] is True, raised["diagnostics"]
    after = _by_key(_model(world, draft)["consumerApis"], api)
    (kept,) = after["earlierVersions"]
    assert after["contractVersion"] == 2 and kept["contractVersion"] == 1
    assert kept["object"] == before["object"] and kept["operations"] == before["operations"]
    assert kept["deprecated"] == datetime.now(UTC).date().isoformat() and "sunset" not in kept

    dated = ok(_apply(world, draft, raised["version"], {"kind": "setConsumerApiSunset", "consumerApi": api, "version": 1, "sunset": "2027-06-30"}))
    assert _by_key(_model(world, draft)["consumerApis"], api)["earlierVersions"][0]["sunset"] == "2027-06-30"
    error = refused(
        _apply(world, draft, dated["version"], {"kind": "setConsumerApiSunset", "consumerApi": api, "version": 1, "sunset": "next spring"}),
        422,
        "INVALID_OPERATION",
    )
    assert error["details"]["reason"] == "invalidValue"
    refused(
        _apply(world, draft, dated["version"], {"kind": "removeConsumerApiVersion", "consumerApi": api, "version": 7}),
        422,
        "INVALID_OPERATION",
    )

    stopped = ok(_apply(world, draft, dated["version"], {"kind": "removeConsumerApiVersion", "consumerApi": api, "version": 1}))
    assert not _by_key(_model(world, draft)["consumerApis"], api).get("earlierVersions")
    assert stopped["valid"] is True
    undone = ok(_undo(world, draft, stopped["version"]))
    assert _by_key(_model(world, draft)["consumerApis"], api)["earlierVersions"][0]["sunset"] == "2027-06-30"
    undone = ok(_undo(world, draft, undone["version"]))
    undone = ok(_undo(world, draft, undone["version"]))
    assert _by_key(_model(world, draft)["consumerApis"], api) == before

    alone = ok(_apply(world, draft, undone["version"], {"kind": "raiseConsumerApiVersion", "consumerApi": api, "version": 5, "keep": False}))
    assert alone["valid"] is True
    again = _by_key(_model(world, draft)["consumerApis"], api)
    assert again["contractVersion"] == 5 and not again.get("earlierVersions")
    refused(
        _apply(world, draft, alone["version"], {"kind": "raiseConsumerApiVersion", "consumerApi": api, "version": 5}),
        422,
        "INVALID_OPERATION",
    )


@pytest.mark.journey("J33.13", "J25.9")
@pytest.mark.structures("Capi")
def test_the_kept_version_is_what_the_base_release_served_and_a_new_api_keeps_none(world):
    """Given a draft whose Capi already lost a field (a breaking edit). When the editor raises the
    version, then the kept version 1 holds the field as the base release served it and compiling
    reports no change to a kept version; a consumer API added in the draft keeps nothing when raised."""
    draft = _draft_of_active(world)
    api = world.key("Capi")
    before = _by_key(_model(world, draft)["consumerApis"], api)
    score = world.key("Capi.n")
    edited = ok(_apply(world, draft, draft["version"], {"kind": "removeConsumerApiPart", "consumerApi": api, "pointer": f"/object/fields/{score}"}))
    raised = ok(_apply(world, draft, edited["version"], {"kind": "raiseConsumerApiVersion", "consumerApi": api}))
    after = _by_key(_model(world, draft)["consumerApis"], api)
    assert score not in after["object"]["fields"]
    assert after["earlierVersions"][0]["object"] == before["object"]
    compiled = ok(world.api.post(f"/model-drafts/{draft['id']}/compile", {"expectedVersion": raised["version"]}))
    assert "CONSUMER_KEPT_VERSION_CHANGED" not in {d["code"] for d in compiled["consumerContracts"]["diagnostics"]}

    added = ok(_apply(world, draft, raised["version"], {"kind": "addConsumerApi", "name": "J33 New", "key": "j33-new", "exposes": [world.key("R")]}))
    ok(_apply(world, draft, added["version"], {"kind": "raiseConsumerApiVersion", "consumerApi": "j33-new"}))
    assert not _by_key(_model(world, draft)["consumerApis"], "j33-new").get("earlierVersions")


@pytest.mark.journey("J33.13")
@pytest.mark.structures("Capi")
def test_the_definition_of_an_unknown_draft_or_api_is_not_found_and_an_invalid_drafts_documents_are_refused(world):
    refused(world.api.get(f"/model-drafts/00000000-0000-4000-8000-000000000000/consumer-apis/{world.key('Capi')}"), 404, "MODEL_DRAFT_NOT_FOUND")
    draft = _draft_of_active(world)
    refused(_definition(world, draft, "j33-no-such-api"), 404, "CONSUMER_API_NOT_FOUND")
    invalid = ok(_apply(world, draft, draft["version"], {"kind": "addApplication", "name": "J33 Empty"}))
    assert invalid["valid"] is False
    assert ok(_definition(world, draft, world.key("Capi")))["valid"] is False
    for part in ("/schema.json", "/example.json", "/openapi.json"):
        refused(_definition(world, draft, world.key("Capi"), part), 422, "INVALID_MODEL")
    empty = _empty_draft(world)
    refused(_definition(world, empty, world.key("Capi")), 404, "CONSUMER_API_NOT_FOUND")


@pytest.mark.journey("J33", "J08.7")
@pytest.mark.structures("A1")
@pytest.mark.settings(**DISABLED)
def test_with_model_administration_disabled_the_drafts_consumer_apis_are_absent(world):
    response = world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/consumer-apis/any")
    assert response.status_code == 404, response.text
    assert "MODEL_DRAFT_NOT_FOUND" not in response.text
