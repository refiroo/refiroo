"""J28 — Read a business object through a consumer API (USER_JOURNEYS.md)."""

import copy
from uuid import uuid4

import pytest
from scenario import W1, W2, W3, consumer_object, ok, refused

CAPI = ("Capi", "R", "R2", "R.u", "R2.u", "R.b", "R.n", "R.dt", "K", "K.code", "B11", "Bown", "G", "D")


def _read(world, object_id, **params):
    return ok(consumer_object(world, object_id, **params))


def _out(world, name):
    """An output name of ``Capi``, chosen by the configuration."""
    return world.key(f"Capi.{name}")


def _dependant(world, owner, g, name):
    return world.made(
        "D", name, parent=world.dependant_parent(g), relations=[world.owner("Bown", owner)]
    )


@pytest.mark.journey("J28")
@pytest.mark.structures(*CAPI)
def test_the_shared_object(world):
    """Given an R with typed values, R.u set and R2.u empty text, one B11 target, two Bown dependants
    under different Gs, and an R2 under it. When each is read by its object ID. Then each answers
    exactly the declared fields with declared types: code skips the empty text and reads R.u, and the
    unset attribute takes its default; R's parent is null, its hierarchy [] and path ""; R2's parent
    names R, and its hierarchy is [R's name]; the B11 projection is an object, and null on a record
    without the relationship; the Bown projection is an array ordered by name, with each G's name; a
    record with no dependants has []."""
    r = world.made(
        "R", "Alpha ledger", values={"R.u": "LED-1", "R.b": False, "R.dt": "2026-03-04"}
    )
    token = world.made("K", "Paired token", values={"K.code": "TK-1"})
    ok(world.relate("B11", r["id"], token["id"]), 201)
    north = world.made("G", "Region north", values={"K.code": "GN"})
    south = world.made("G", "Region south", values={"K.code": "GS"})
    _dependant(world, r["id"], north["id"], "Permit b")
    _dependant(world, r["id"], south["id"], "Permit a")
    r2 = world.made("R2", "Alpha entry", parent=r["id"], values={"R2.u": "", "R.u": "ENT-1"})

    declared = {
        "objectType",
        *(_out(world, name) for name in ("id", "code", "name", "active", "n", "dt")),
        *(_out(world, name) for name in ("parent", "path", "hierarchy", "B11", "Bown")),
    }
    ledger = _read(world, r["id"])
    assert set(ledger) == declared
    assert ledger["objectType"] == world.key("Capi.R")
    assert ledger[_out(world, "id")] == r["id"]
    assert ledger[_out(world, "code")] == "LED-1"
    assert ledger[_out(world, "name")] == "Alpha ledger"
    assert ledger[_out(world, "active")] is False
    assert ledger[_out(world, "n")] == 50
    assert ledger[_out(world, "dt")] == "2026-03-04"
    assert ledger[_out(world, "parent")] is None
    assert (ledger[_out(world, "hierarchy")], ledger[_out(world, "path")]) == ([], "")
    assert ledger[_out(world, "B11")] == {
        _out(world, "B11.name"): "Paired token",
        _out(world, "B11.code"): "TK-1",
    }
    assert ledger[_out(world, "Bown")] == [
        {_out(world, "Bown.name"): "Permit a", _out(world, "Bown.G"): "Region south"},
        {_out(world, "Bown.name"): "Permit b", _out(world, "Bown.G"): "Region north"},
    ]

    entry = _read(world, r2["id"])
    assert set(entry) == declared
    assert entry["objectType"] == world.key("Capi.R2")
    assert entry[_out(world, "code")] == "ENT-1"
    assert entry[_out(world, "active")] is True
    assert entry[_out(world, "n")] == 50
    assert entry[_out(world, "dt")] is None
    assert entry[_out(world, "parent")] == {
        "objectType": world.key("Capi.R"),
        "id": r["id"],
        "code": "LED-1",
        "name": "Alpha ledger",
    }
    assert entry[_out(world, "hierarchy")] == ["Alpha ledger"]
    assert entry[_out(world, "path")] == "Alpha ledger"
    assert entry[_out(world, "B11")] is None
    assert entry[_out(world, "Bown")] == []


@pytest.mark.journey("J28.1")
@pytest.mark.structures(*CAPI)
def test_identity_is_the_object_id(world):
    """Given an R created with a client-assigned ID and one with a generated ID. When read by those
    IDs, then each is found. When read by its R.u value, then 404 OBJECT_NOT_FOUND."""
    assigned = str(uuid4())
    chosen = world.made("R", "Assigned", id=assigned, values={"R.u": "ASSIGNED-1"})
    generated = world.made("R", "Generated", values={"R.u": "GENERATED-1"})
    assert chosen["id"] == assigned
    for record in (chosen, generated):
        assert _read(world, record["id"])[_out(world, "id")] == record["id"]
    refused(consumer_object(world, "GENERATED-1"), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J28.2")
@pytest.mark.structures(*CAPI)
def test_live_data_never_unpublished_work(world):
    """When a record is changed live, the next read shows the change. A record created only in an
    open change set is 404 OBJECT_NOT_FOUND until the change set is published, then found."""
    record = world.made("R", "Before")
    assert _read(world, record["id"])[_out(world, "name")] == "Before"
    ok(world.update("R", record["id"], record["version"], name="After"))
    assert _read(world, record["id"])[_out(world, "name")] == "After"

    change_set = world.change_set()
    staged_id = world.made("R", "Staged", change_set=world.current(change_set))["id"]
    refused(consumer_object(world, staged_id), 404, "OBJECT_NOT_FOUND")
    world.publish(change_set)
    assert _read(world, staged_id)[_out(world, "name")] == "Staged"


@pytest.mark.journey("J28.3")
@pytest.mark.structures(*CAPI)
def test_another_workspace(world):
    """Given a record in W1 and one in W2. When read with workspace=W2, and without it. Then each is
    found only in its own workspace, named in RDM-Workspace (the default when omitted). An unknown
    workspace is 404 WORKSPACE_NOT_FOUND."""
    first = world.made("R", "First site ledger")
    second = world.made("R", "Second site ledger", workspace=W2)

    response = consumer_object(world, second["id"], workspace=W2)
    assert ok(response)[_out(world, "name")] == "Second site ledger"
    assert response.headers["RDM-Workspace"] == W2
    response = consumer_object(world, first["id"])
    assert ok(response)[_out(world, "name")] == "First site ledger"
    assert response.headers["RDM-Workspace"] == W1

    missing = consumer_object(world, second["id"])
    refused(missing, 404, "OBJECT_NOT_FOUND")
    assert missing.headers["RDM-Workspace"] == W1
    refused(consumer_object(world, first["id"], workspace=W2), 404, "OBJECT_NOT_FOUND")
    refused(consumer_object(world, first["id"], workspace="no-such-site"), 404, "WORKSPACE_NOT_FOUND")
    refused(consumer_object(world, world.ids["w3r"], workspace=W3), 404, "WORKSPACE_NOT_FOUND")


@pytest.mark.journey("J28.4")
@pytest.mark.structures(*CAPI)
def test_refusals(world):
    """An unknown apiKey is 404 CONSUMER_API_NOT_FOUND. Version 2 of a version-1 API is 404
    CONTRACT_VERSION_NOT_FOUND. A record of a type the definition does not expose is 404
    OBJECT_NOT_FOUND. pagesize=5 is 400 UNKNOWN_PARAMETER, naming it. A declared parameter is 400
    PARAMETER_NOT_SUPPORTED."""
    record = world.made("R", "Refusals")
    refused(consumer_object(world, record["id"], api="no-such-api"), 404, "CONSUMER_API_NOT_FOUND")
    error = refused(consumer_object(world, record["id"], version=2), 404, "CONTRACT_VERSION_NOT_FOUND")
    assert error["details"]["contractVersion"] == 1
    token = world.made("K", "Not exposed")
    refused(consumer_object(world, token["id"]), 404, "OBJECT_NOT_FOUND")
    error = refused(consumer_object(world, record["id"], pagesize=5), 400, "UNKNOWN_PARAMETER")
    assert error["details"]["parameters"] == ["pagesize"]
    declared = world.key("Capi.param")
    error = refused(
        consumer_object(world, record["id"], **{declared: "x"}), 400, "PARAMETER_NOT_SUPPORTED"
    )
    assert error["details"]["parameters"] == [declared]


@pytest.mark.journey("J28.5", "J25.2")
@pytest.mark.structures(*CAPI)
def test_the_contract_follows_the_release(world):
    """When a release changes B11 to one-to-many and raises contractVersion to 2, then v1 answers 404
    CONTRACT_VERSION_NOT_FOUND, and v2 returns the projection as an array."""
    record = world.made("R", "Widened")
    token = world.made("K", "Widened token", values={"K.code": "TK-W"})
    ok(world.relate("B11", record["id"], token["id"]), 201)

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-wider"
    binding = next(
        b for b in model["objectTypeRelations"] if b["relationTypeKey"] == world.key("B11")
    )
    binding["cardinality"] = "one-to-many"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["contractVersion"] = 2
    ok(world.activate(world.install(model)["id"]))

    refused(consumer_object(world, record["id"]), 404, "CONTRACT_VERSION_NOT_FOUND")
    widened = _read(world, record["id"], version=2)
    assert widened[_out(world, "B11")] == [
        {_out(world, "B11.name"): "Widened token", _out(world, "B11.code"): "TK-W"}
    ]
