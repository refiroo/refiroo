"""J28.16, J28.17, J25.10, J30.2 — The parent carries fields and related blocks (0.17 CA1).

Each test activates a release whose ``Capi`` shows, beside its object's fields, a parent with an
attribute of its own and related blocks of its own (PP-D29): one served always, one only when a read
names it in ``include`` (PP-D30), with an On related filter naming the parent's block (PP-D31). The
parent types of ``Capi`` are ``R`` (above ``R2``), ``G`` and ``M`` (above ``D``); ``R`` has the
one-to-one relationship ``B11`` to ``K``.
"""

import copy
from uuid import uuid4

import pytest
from openapi_schema_validator import OAS31Validator
from scenario import (
    consumer_events,
    consumer_list,
    consumer_object,
    consumer_resolve,
    consumer_xref,
    derive_events,
    ok,
    refused,
)

LEDGER = (
    "Capi",
    "R",
    "R2",
    "R.u",
    "R.n",
    "K",
    "K.code",
    "B11",
    "Bnn",
    "Bown",
    "G",
    "M",
    "D",
    "D.active",
)
# The names the new parts take: an author's own, so they stand for no model key.
PARENT_TOKEN, PARENT_PLAIN, OWN_TOKEN, FILTER = (
    "parentToken",
    "parentPlain",
    "ownToken",
    "parentHasToken",
)
EVERY = "ledger-any"


def _definition_of(world, model):
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    return definition


def _parent(world, *, served=True):
    """Capi's parent: its four built-in fields, ``R.u``, a block shown always and one on request."""
    token = {
        "via": world.key("B11"),
        "fields": {"tokenName": "name", "tokenCode": world.key("K.code")},
    }
    return {
        "output": world.key("Capi.parent"),
        "fields": {
            "objectType": "objectType",
            world.key("Capi.id"): "id",
            world.key("Capi.code"): "code",
            world.key("Capi.name"): "name",
            "parentRef": world.key("R.u"),
            "parentScore": world.key("R.n"),
        },
        "related": {
            PARENT_PLAIN: {"via": world.key("B11"), "fields": {"tokenName": "name"}},
            PARENT_TOKEN: {**token, **({"served": "onRequest"} if served else {})},
        },
    }


def _model(world, suffix="parent", *, served=True):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    definition = _definition_of(world, model)
    definition["object"]["parent"] = _parent(world, served=served)
    definition["object"]["related"][OWN_TOKEN] = {
        "via": world.key("B11"),
        "fields": {"tokenName": "name"},
        "served": "onRequest",
    }
    definition["filters"][FILTER] = {
        "onRelated": f"parent.{PARENT_TOKEN}",
        "matchOn": ["name"],
        "keepOnlyMatching": True,
    }
    return model


def _activate(world, suffix="parent", **options):
    release = world.install(_model(world, suffix, **options))
    ok(world.activate_everywhere(release["id"]))
    return release


def _ledgers(world):
    """Alpha ledger (R.u LED-1) with a token and two entries, Beta ledger with no token and one."""
    token = world.made("K", "Paired token", values={"K.code": "TK-1"})
    alpha = world.made("R", "Alpha ledger", values={"R.u": "LED-1"})
    ok(world.relate("B11", alpha["id"], token["id"]), 201)
    beta = world.made("R", "Beta ledger", values={"R.u": "LED-2"})
    entries = {
        "alpha": world.made("R2", "Alpha entry", parent=alpha["id"]),
        "alpha2": world.made("R2", "Alpha second", parent=alpha["id"]),
        "beta": world.made("R2", "Beta entry", parent=beta["id"]),
    }
    return alpha, beta, entries


def _parent_of(world, body):
    return body[world.key("Capi.parent")]


def _read(world, object_id, **params):
    return ok(consumer_object(world, object_id, **params))


@pytest.mark.journey("J28.16")
@pytest.mark.structures(*LEDGER)
def test_the_parent_serves_its_fields_and_the_blocks_served_always(world):
    """Given a parent with an attribute field and two blocks, one served always and one on request.
    When a child, a record with no parent and a record whose parent has no token are read by ID.
    Then the child's parent shows its four built-in fields as before, the attribute under its own
    name, and the always block; the on-request block is not in the answer. A record with no parent
    has a null parent; a parent with no token has a null block and a null attribute."""
    _activate(world)
    alpha, _beta, entries = _ledgers(world)
    parent = _parent_of(world, _read(world, entries["alpha"]["id"]))
    assert parent == {
        "objectType": world.key("Capi.R"),
        world.key("Capi.id"): alpha["id"],
        world.key("Capi.code"): "LED-1",
        world.key("Capi.name"): "Alpha ledger",
        "parentRef": "LED-1",
        "parentScore": None,
        PARENT_PLAIN: {"tokenName": "Paired token"},
    }
    assert _parent_of(world, _read(world, entries["beta"]["id"]))[PARENT_PLAIN] is None
    assert _parent_of(world, _read(world, alpha["id"])) is None
    assert OWN_TOKEN not in _read(world, alpha["id"])

    # A parent that does not bind the attribute (a G or M above a D) serves null for it, and has no block
    # over a relation it is no end of (OT-D1, OT-D2).
    permit = world.made(
        "D",
        "Permit",
        parent=world.dependant_parent(world.made("G", "North")["id"]),
        relations=[world.owner("Bown", alpha["id"])],
    )
    above = _parent_of(world, _read(world, permit["id"]))
    assert above["parentRef"] is None and PARENT_PLAIN not in above


@pytest.mark.journey("J28.16")
@pytest.mark.structures(*LEDGER)
def test_a_block_served_on_request_comes_with_include_on_every_read(world):
    """Given an on-request block on the parent and one on the object. When a record is read by ID
    with ``include`` naming them, repeated or comma-separated; in a list; in XREF; and in a batch's
    items and defaults. Then each answer carries exactly the named blocks, in the parent or on the
    object; a name that is no on-request block is ``400 UNKNOWN_INCLUDE`` naming the valid ones, and
    a batch item's is rejected at its own pointer."""
    _activate(world)
    alpha, _beta, entries = _ledgers(world)
    child = entries["alpha"]["id"]
    named = [f"parent.{PARENT_TOKEN}", OWN_TOKEN]

    body = _read(world, child, include=named)
    assert _parent_of(world, body)[PARENT_TOKEN] == {
        "tokenName": "Paired token",
        "tokenCode": "TK-1",
    }
    # The entry is no end of the relationship, so it has no such block; its ledger has (OT-D2).
    assert OWN_TOKEN not in body
    assert _read(world, alpha["id"], include=OWN_TOKEN)[OWN_TOKEN] == {"tokenName": "Paired token"}
    only_parent = _read(world, child, include=f"parent.{PARENT_TOKEN}")
    assert PARENT_TOKEN in _parent_of(world, only_parent) and OWN_TOKEN not in only_parent
    commas = ok(
        world.api.client.get(
            f"/api/consumer/{world.key('Capi')}/v1/objects/{child}?include={named[0]},{named[1]}"
        )
    )
    assert commas == body

    page = ok(consumer_list(world, world.key("Capi.all"), include=named))
    assert all(OWN_TOKEN in item for item in page["items"])
    found = ok(consumer_xref(world, query="Alpha entry", include=named))["results"]
    assert PARENT_TOKEN in _parent_of(world, found[0])

    resolved = ok(
        consumer_resolve(
            world,
            {
                "defaults": {"include": [f"parent.{PARENT_TOKEN}"]},
                "items": [
                    {"id": child},
                    {"id": entries["beta"]["id"], "include": [OWN_TOKEN]},
                    {"id": child, "include": ["parent.nope"]},
                    {"id": alpha["id"], "include": [OWN_TOKEN]},
                ],
            },
        )
    )
    first, second, third, fourth = resolved["items"]
    assert PARENT_TOKEN in _parent_of(world, first["object"])
    assert PARENT_TOKEN not in _parent_of(world, second["object"])
    assert OWN_TOKEN in fourth["object"]
    assert (third["status"], third["error"]["code"]) == ("rejected", "UNKNOWN_INCLUDE")
    assert third["error"]["details"]["pointer"] == "/items/2/include"

    error = refused(
        consumer_object(world, child, include=f"parent.{PARENT_PLAIN}"), 400, "UNKNOWN_INCLUDE"
    )
    assert error["details"]["valid"] == [OWN_TOKEN, f"parent.{PARENT_TOKEN}"]


@pytest.mark.journey("J28.17")
@pytest.mark.structures(*LEDGER)
def test_a_filter_on_a_parent_block_narrows_it_and_the_results(world):
    """Given a filter On related the parent's on-request block, keeping only matching. When a list
    is read with the filter's value, with and without ``include``. Then only the children whose
    parent has a matching token remain (children of a parent with none are dropped, and so are
    records with no parent), the block is served only with ``include``, and without the filter every
    child is back. A value no token has keeps none."""
    _activate(world)
    alpha, _beta, entries = _ledgers(world)
    list_key = world.key("Capi.entries")

    everyone = ok(consumer_list(world, list_key, pageSize=100))["items"]
    assert len(everyone) == 3
    narrowed = ok(consumer_list(world, list_key, **{FILTER: "Paired token"}, pageSize=100))["items"]
    assert {item[world.key("Capi.name")] for item in narrowed} == {
        "Alpha entry",
        "Alpha second",
    }
    assert all(PARENT_TOKEN not in _parent_of(world, item) for item in narrowed)

    shown = ok(
        consumer_list(
            world,
            list_key,
            **{FILTER: "Paired token"},
            include=f"parent.{PARENT_TOKEN}",
            pageSize=100,
        )
    )["items"]
    assert [_parent_of(world, item)[PARENT_TOKEN]["tokenName"] for item in shown] == [
        "Paired token"
    ] * 2
    assert ok(consumer_list(world, list_key, **{FILTER: "Nothing"}, pageSize=100))["items"] == []
    refused(
        consumer_object(world, entries["beta"]["id"], **{FILTER: "Paired token"}),
        404,
        "OBJECT_NOT_FOUND",
    )
    assert _read(world, entries["alpha"]["id"], **{FILTER: "Paired token"})
    assert (
        alpha["id"] == _parent_of(world, _read(world, entries["alpha"]["id"]))[world.key("Capi.id")]
    )


@pytest.mark.journey("J28.16", "J28.17")
@pytest.mark.structures(*LEDGER)
def test_the_openapi_document_types_the_parent_and_lists_the_names(world):
    """Given the release. When the definition's OpenAPI document is read and answers are validated
    against it, with and without ``include``. Then ``include`` is an enum of the on-request names on
    get by ID, lists and XREF, the on-request blocks are optional properties of the object and of
    the parent, the parent's schema has its fields, and answers conform."""
    _activate(world)
    alpha, _beta, entries = _ledgers(world)
    key = world.key("Capi")
    document = ok(world.api.get(f"/api/consumer/{key}/v1/openapi.json"))
    names = [OWN_TOKEN, f"parent.{PARENT_TOKEN}"]
    for path in (f"/api/consumer/{key}/v1/objects/{{id}}", f"/api/consumer/{key}/v1/xref"):
        (include,) = [
            p for p in document["paths"][path]["get"]["parameters"] if p["name"] == "include"
        ]
        assert include["schema"]["items"]["enum"] == names
    schemas = document["components"]["schemas"]
    # Each type has its own schema (OT-D3): the ledger holds the object's block, the entry (whose parent is
    # a ledger) holds the parent's.
    ledger = schemas[world.key("Capi.R")]
    assert OWN_TOKEN in ledger["properties"] and OWN_TOKEN not in ledger["required"]
    schema = schemas[world.key("Capi.R2")]
    assert OWN_TOKEN not in schema["properties"]
    parent = schema["properties"][world.key("Capi.parent")]
    # A parent attribute is null where the parent has no value, and keeps its own type.
    assert parent["properties"]["parentScore"]["type"] == ["integer", "null"]
    assert PARENT_TOKEN in parent["properties"] and PARENT_TOKEN not in parent["required"]
    assert {PARENT_PLAIN, "parentRef"} <= set(parent["required"])
    validator = OAS31Validator({**schema, "components": document["components"]})
    validator.validate(_read(world, entries["alpha"]["id"]))
    validator.validate(_read(world, entries["alpha"]["id"], include=names))
    OAS31Validator({**ledger, "components": document["components"]}).validate(
        _read(world, alpha["id"], include=names)
    )


@pytest.mark.journey("J25.10")
@pytest.mark.structures(*LEDGER)
def test_a_parent_the_model_cannot_serve_is_refused_at_the_authors_pointer(world):
    """Given drafts whose parent names an attribute no parent type binds, a block over a relation no
    parent type has, a block named ``parent.…`` on the object, and a ``parent`` inside the parent.
    When each is compiled. Then each is refused at the pointer of the part the author wrote; and
    serving an existing block only on request needs a higher contract version, while adding parent
    fields and blocks does not."""
    _activate(world, "active", served=False)

    def refusal(change, expected):
        model = _model(world, "mistake")
        change(_definition_of(world, model))
        draft = ok(world.api.post("/model-drafts", {"name": "Mistake", "model": model}), 201)
        compiled = ok(
            world.api.post(
                f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
            )
        )
        assert compiled["valid"] is False
        assert any(d["path"].startswith(expected) for d in compiled["diagnostics"]), compiled[
            "diagnostics"
        ]

    base = f"/consumerApis/{world.key('Capi')}/object"
    refusal(
        lambda d: d["object"]["parent"]["fields"].update(bad=world.key("D.active")),
        f"{base}/parent/fields/bad",
    )
    refusal(
        lambda d: d["object"]["parent"]["related"][PARENT_PLAIN].update(via=world.key("Bnn")),
        f"{base}/parent/related/{PARENT_PLAIN}",
    )
    refusal(
        lambda d: d["object"]["related"].update({"parent.x": d["object"]["related"][OWN_TOKEN]}),
        f"{base}/related/parent.x",
    )

    model = _model(world, "served")
    draft = ok(world.api.post("/model-drafts", {"name": "Served", "model": model}), 201)
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )
    assert compiled["valid"] is True
    changes = [
        d
        for d in compiled["consumerContracts"]["diagnostics"]
        if d["code"] == "CONSUMER_CONTRACT_VERSION_REQUIRED"
    ]
    # Everything new is an addition; the parent block that was served always and now only on request
    # leaves the default answer.
    assert [d["path"].startswith(f"{base}/parent/related/{PARENT_TOKEN}") for d in changes] == [
        True
    ]
    assert "only on request" in changes[0]["message"]


@pytest.mark.journey("J30.2")
@pytest.mark.structures(*LEDGER)
def test_changing_what_a_parent_shows_makes_its_children_updated(world):
    """Given a parent showing an attribute and blocks of its own, and an event for the children.
    When the parent's attribute changes, its token is renamed, its token relationship is removed, and
    another record's token is renamed. Then each change tells every child of that parent that its
    parent output changed, and no other record."""
    model = _model(world, "events")
    _definition_of(world, model)["operations"]["events"] = {
        "custom": [
            {
                "key": EVERY,
                "objectTypes": [world.key("R2")],
                "changes": ["created", "updated", "deleted"],
            }
        ]
    }
    release = world.install(model)
    ok(world.activate_everywhere(release["id"]))
    workspace = f"events-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": workspace, "label": "Events site"}), 201)
    token = world.made("K", "Paired token", values={"K.code": "TK-1"}, workspace=workspace)
    other = world.made("K", "Other token", workspace=workspace)
    alpha = world.made("R", "Alpha", values={"R.u": "LED-1"}, workspace=workspace)
    beta = world.made("R", "Beta", values={"R.u": "LED-2"}, workspace=workspace)
    link = ok(world.relate("B11", alpha["id"], token["id"]), 201)
    ok(world.relate("B11", beta["id"], other["id"]), 201)
    children = [
        world.made("R2", f"Entry {i}", parent=alpha["id"], workspace=workspace) for i in (1, 2)
    ]
    world.made("R2", "Beta entry", parent=beta["id"], workspace=workspace)
    derive_events(world)
    parent = world.key("Capi.parent")

    def told_after(change):
        head = ok(world.api.get(f"/workspaces/{workspace}/feed"))["headPosition"]
        change()
        derive_events(world)
        page = ok(consumer_events(world, workspace=workspace, after=head))
        return {(e["id"], tuple(e["changed"])) for e in page["items"] if e["event"] == EVERY}

    expected = {(child["id"], (parent,)) for child in children}
    version = world.record("R", alpha["id"], workspaceKey=workspace)["version"]
    assert (
        told_after(lambda: ok(world.update("R", alpha["id"], version, values={"R.u": "LED-1b"})))
        == expected
    )
    version = world.record("K", token["id"], workspaceKey=workspace)["version"]
    assert (
        told_after(lambda: ok(world.update("K", token["id"], version, name="Token renamed")))
        == expected
    )
    unlink = lambda: world.api.delete(f"/relations/{link['id']}", expectedVersion=link["version"])
    assert told_after(unlink) == expected


@pytest.mark.journey("J33.13")
@pytest.mark.structures(*LEDGER)
def test_every_edit_of_a_parent_block_changes_the_draft(world):
    """Given a draft whose parent has a related block. When the editor's steps change the block's
    fields, its Served, its output name and its route, and the parent's fields. Then each is applied,
    appears as a step and the draft holds the new value."""
    model = _model(world)
    # As released definitions write it: the short list of sources, an attribute among them.
    _definition_of(world, model)["object"]["parent"]["fields"] = [
        "objectType",
        "id",
        world.key("R.u"),
    ]
    draft = ok(world.api.post("/model-drafts", {"name": "Parent", "model": model}), 201)
    api = world.key("Capi")
    block = f"/object/parent/related/{PARENT_PLAIN}"

    def apply(*operations):
        nonlocal draft
        result = ok(
            world.api.post(
                f"/model-drafts/{draft['id']}/operations",
                {"expectedVersion": draft["version"], "operations": list(operations)},
            )
        )
        assert result["entries"], "the step is recorded"
        draft = ok(world.api.get(f"/model-drafts/{draft['id']}"))
        (definition,) = [d for d in draft["model"]["consumerApis"] if d["key"] == api]
        return definition["object"]["parent"]

    def part(pointer, value):
        return {
            "kind": "setConsumerApiPart",
            "consumerApi": api,
            "pointer": pointer,
            "value": value,
        }

    parent = apply(part(f"{block}/fields", {"tokenName": "name", "tokenCode": world.key("K.code")}))
    assert parent["related"][PARENT_PLAIN]["fields"] == {
        "tokenName": "name",
        "tokenCode": world.key("K.code"),
    }
    # Existing entries renamed or re-sourced, with one added, in one step.
    parent = apply(
        part(
            f"{block}/fields",
            {"tokenLabel": "name", "tokenCode": "name", "added": world.key("K.code")},
        )
    )
    assert parent["related"][PARENT_PLAIN]["fields"] == {
        "tokenLabel": "name",
        "tokenCode": "name",
        "added": world.key("K.code"),
    }
    parent = apply(part(f"{block}/served", "onRequest"))
    assert parent["related"][PARENT_PLAIN]["served"] == "onRequest"
    parent = apply(part(f"{block}/served", None))
    assert "served" not in parent["related"][PARENT_PLAIN]
    parent = apply(part(f"{block}/via", world.key("B11")))
    parent = apply(
        {"kind": "removeConsumerApiPart", "consumerApi": api, "pointer": block},
        {
            "kind": "insertConsumerApiPart",
            "consumerApi": api,
            "pointer": "/object/parent/related",
            "key": "renamed",
            "value": {"via": world.key("B11"), "fields": {"tokenName": "name"}},
        },
    )
    assert "renamed" in parent["related"] and PARENT_PLAIN not in parent["related"]
    parent = apply(part("/object/parent", {**parent, "fields": {"onlyId": "id"}}))
    assert parent["fields"] == {"onlyId": "id"}


@pytest.mark.journey("J28.17")
@pytest.mark.structures(*LEDGER)
def test_a_parent_block_reads_the_system_a_related_record_sits_under(world):
    """Given a parent block over a relationship whose records sit under a type above them, reading
    that ancestor's name, and an On related filter on that block matching the ancestor's name. When
    a child is read with the filter's value. Then the parent's block shows only the matching items and
    a child whose parent has none is dropped: the parent's block carries what an object's block does."""
    model = _model(world)
    definition = _definition_of(world, model)
    definition["object"]["parent"]["related"]["permits"] = {
        "via": world.key("Bown"),
        "fields": {"permitName": "name", "region": f"ancestor:{world.key('G')}.name"},
    }
    definition["filters"]["parentRegion"] = {
        "onRelated": "parent.permits",
        "matchOn": [f"ancestor:{world.key('G')}.name"],
        "keepOnlyMatching": True,
    }
    ok(world.activate_everywhere(world.install(model)["id"]))
    alpha, beta, entries = _ledgers(world)
    north, south = world.made("G", "Region north"), world.made("G", "Region south")
    for owner, g, name in (
        (alpha, north, "Permit a"),
        (alpha, south, "Permit b"),
        (beta, south, "Permit c"),
    ):
        world.made(
            "D",
            name,
            parent=world.dependant_parent(g["id"]),
            relations=[world.owner("Bown", owner["id"])],
        )
    answer = _read(world, entries["alpha"]["id"], parentRegion="Region north")
    assert _parent_of(world, answer)["permits"] == [
        {"permitName": "Permit a", "region": "Region north"}
    ]
    page = ok(
        consumer_list(world, world.key("Capi.entries"), parentRegion="Region north", pageSize=100)
    )
    assert {item[world.key("Capi.name")] for item in page["items"]} == {
        "Alpha entry",
        "Alpha second",
    }
    refused(
        consumer_object(world, entries["beta"]["id"], parentRegion="Region north"),
        404,
        "OBJECT_NOT_FOUND",
    )
