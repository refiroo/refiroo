"""J28 — Read a business object through a consumer API (USER_JOURNEYS.md)."""

import copy
from uuid import uuid4

import pytest
from scenario import W1, W2, W3, consumer_list, consumer_list_typed, consumer_object, ok, refused

CAPI = (
    "Capi", "R", "R2", "R.u", "R2.u", "R.b", "R.n", "R.dt", "K", "K.code", "B11", "Bown", "Bscope",
    "G", "M", "D",
)


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
        *(_out(world, name) for name in ("parent", "path", "hierarchy", "B11", "Bown", "Bscope")),
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
    OBJECT_NOT_FOUND. pagesize=5 is 400 UNKNOWN_PARAMETER, naming it. A list's parent parameter is
    400 PARAMETER_NOT_SUPPORTED (C3)."""
    record = world.made("R", "Refusals")
    refused(consumer_object(world, record["id"], api="no-such-api"), 404, "CONSUMER_API_NOT_FOUND")
    error = refused(consumer_object(world, record["id"], version=2), 404, "CONTRACT_VERSION_NOT_FOUND")
    assert error["details"]["contractVersion"] == 1
    token = world.made("K", "Not exposed")
    refused(consumer_object(world, token["id"]), 404, "OBJECT_NOT_FOUND")
    error = refused(consumer_object(world, record["id"], pagesize=5), 400, "UNKNOWN_PARAMETER")
    assert error["details"]["parameters"] == ["pagesize"]
    declared = world.key("Capi.entries.parent")
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


# --- lists and parameters (C3) -------------------------------------------------------------------


def _page(world, list_key, **params):
    return ok(consumer_list(world, world.key(f"Capi.{list_key}"), **params))


def _names(world, page):
    return [item[_out(world, "name")] for item in page["items"]]


def _listed(world, list_key, **params):
    """Every item's name, reading the list to its end through ``nextCursor``."""
    names, page = [], _page(world, list_key, pageSize=100, **params)
    names += _names(world, page)
    while page["nextCursor"]:
        page = _page(world, list_key, pageSize=100, cursor=page["nextCursor"], **params)
        names += _names(world, page)
    return names


def _param(world, name):
    return world.key(f"Capi.{name}")


def _permit_under(world, owner, g, name):
    """A ``D`` owned by ``owner`` in a new ``M`` container under ``g`` (two levels below it)."""
    container = world.made("M", f"{name} zone", parent=g)
    return world.made(
        "D", name, parent=container["id"], relations=[world.owner("Bown", owner)]
    ), container


@pytest.mark.journey("J28.6")
@pytest.mark.structures(*CAPI)
def test_every_object_of_a_type(world):
    """Given five R, two of them without R.n, an R only in an open change set, and some R2. When all
    is read with pageSize=2 to the end through nextCursor, back through prevCursor, at position=2,
    with from=end, and with seek on an R.n value. Then each live R appears once, by R.n and then
    name, the two without a value last; the R2 and the change set's R are absent; with
    includeTotal=true, totalCount is 5 and startIndex follows the page; without it, both are null;
    each item equals its get by ID answer; workspace is named in the field and in the header."""
    made = {}
    for name, n in (("Echo", 30), ("Delta", 10), ("Bravo", 10), ("Alpha", None), ("Charlie", None)):
        made[name] = world.made("R", name, values={} if n is None else {"R.n": n})
    world.made("R2", "Entry under echo", parent=made["Echo"]["id"])
    change_set = world.change_set()
    world.made("R", "Staged", change_set=world.current(change_set))
    expected = ["Bravo", "Delta", "Echo", "Alpha", "Charlie"]

    response = consumer_list(world, world.key("Capi.all"), pageSize=2)
    first = ok(response)
    assert response.headers["RDM-Workspace"] == W1
    assert first["workspace"] == W1
    assert first["pageSize"] == 2
    assert (first["totalCount"], first["startIndex"]) == (None, None)
    assert _names(world, first) == expected[:2]
    assert first["prevCursor"] is None

    forward, page = [first], first
    while page["nextCursor"]:
        page = _page(world, "all", pageSize=2, cursor=page["nextCursor"], includeTotal=True)
        forward.append(page)
    assert [_names(world, p) for p in forward] == [expected[0:2], expected[2:4], expected[4:]]
    assert [(p["totalCount"], p["startIndex"]) for p in forward[1:]] == [(5, 2), (5, 4)]

    back, page = [], forward[-1]
    while page["prevCursor"]:
        page = _page(world, "all", pageSize=2, cursor=page["prevCursor"])
        back.append(_names(world, page))
    assert back == [expected[2:4], expected[0:2]]

    at = _page(world, "all", pageSize=2, position=2, includeTotal=True)
    assert (_names(world, at), at["totalCount"], at["startIndex"]) == (expected[2:4], 5, 2)
    reopened = _page(world, "all", pageSize=2, cursor=at["anchor"])
    assert _names(world, reopened) == expected[2:4]
    last = _page(world, "all", pageSize=2, includeTotal=True, **{"from": "end"})
    assert (_names(world, last), last["startIndex"]) == (expected[3:], 3)
    sought = _page(world, "all", pageSize=2, seek="30")
    assert _names(world, sought) == ["Echo", "Alpha"]

    for page in forward:
        for item in page["items"]:
            assert item == _read(world, item[_out(world, "id")])


@pytest.mark.journey("J28.7")
@pytest.mark.structures(*CAPI)
def test_below_a_parent(world):
    """Given R "North" with two R2 and "South" with one; and two G, each with an M holding D. Then
    entries by North's ID gives its two R2; by North's and South's IDs, repeated or comma-separated
    in the URL, all three, while the same IDs sent as one value (the comma encoded as %2C) are one ID
    that is no record, 404 PARENT_NOT_FOUND (C3b); without a parent value, all three, each with its parent; permits by one G's ID gives
    the D two levels below it and none of the other G's; North's name answers 404 PARENT_NOT_FOUND,
    and so do a K's ID and an unknown ID."""
    north = world.made("R", "North")
    south = world.made("R", "South")
    world.made("R2", "North one", parent=north["id"])
    world.made("R2", "North two", parent=north["id"])
    world.made("R2", "South one", parent=south["id"])
    east = world.made("G", "Region east")
    west = world.made("G", "Region west")
    _permit_under(world, north["id"], east["id"], "Permit east")
    _permit_under(world, north["id"], west["id"], "Permit west")

    ledger = _param(world, "entries.parent")
    assert _listed(world, "entries", **{ledger: north["id"]}) == ["North one", "North two"]
    both = ["North one", "North two", "South one"]
    assert _listed(world, "entries", **{ledger: [north["id"], south["id"]]}) == both
    typed = ok(consumer_list_typed(world, world.key("Capi.entries"), f"{ledger}={north['id']},{south['id']}"))
    assert _names(world, typed) == both
    refused(
        consumer_list(world, world.key("Capi.entries"), **{ledger: f"{north['id']},{south['id']}"}),
        404,
        "PARENT_NOT_FOUND",
    )
    every = _page(world, "entries")
    assert _names(world, every) == both
    parents = [item[_out(world, "parent")]["id"] for item in every["items"]]
    assert parents == [north["id"], north["id"], south["id"]]

    region = _param(world, "permits.parent")
    assert _listed(world, "permits", **{region: east["id"]}) == ["Permit east"]

    permits = world.key("Capi.permits")
    token = world.made("K", "Not a region")
    for value in ("North", token["id"], str(uuid4())):
        error = refused(
            consumer_list(world, world.key("Capi.entries"), **{ledger: value}), 404, "PARENT_NOT_FOUND"
        )
        assert value in error["message"]
    refused(consumer_list(world, permits, **{region: north["id"]}), 404, "PARENT_NOT_FOUND")


def _narrowing_world(world):
    """Three R: a pairs Gold token and owns a permit in each region; b pairs "Bonds, Notes" and owns
    one in the south; c has neither. a and b both watch a's northern permit."""
    north = world.made("G", "Region north")
    south = world.made("G", "Region south")
    gold = world.made("K", "Gold token")
    bonds = world.made("K", "Bonds, Notes")
    a = world.made("R", "Ledger a")
    b = world.made("R", "Ledger b")
    c = world.made("R", "Ledger c")
    ok(world.relate("B11", a["id"], gold["id"]), 201)
    ok(world.relate("B11", b["id"], bonds["id"]), 201)
    permit_a, zone_one = _permit_under(world, a["id"], north["id"], "Permit a")
    permit_b, zone_two = _permit_under(world, b["id"], south["id"], "Permit b")
    _permit_under(world, a["id"], south["id"], "Permit c")
    ok(world.relate("Bscope", a["id"], permit_a["id"]), 201)
    ok(world.relate("Bscope", b["id"], permit_a["id"]), 201)
    return {"a": a, "b": b, "c": c, "permit_b": permit_b, "zone_one": zone_one, "zone_two": zone_two}


@pytest.mark.journey("J28.8")
@pytest.mark.structures(*CAPI)
def test_parameters_narrow_a_list(world):
    """permits with container keeps the D of that M. token keeps the R whose B11 target has that
    name, in another case as well. peer=Ra keeps Ra (through self) and Rb (it shares a Bscope D),
    and not Rc. permit limits each R's permits to that G's and drops the R without one, and
    totalCount follows. kind with R's public name keeps every R, with R2's keeps none, and with an
    unknown name answers 400 UNKNOWN_OBJECT_TYPE. Two values of token, repeated and comma-separated,
    keep the R matching either. A K named "Bonds, Notes" is matched by token=Bonds%2C%20Notes; in
    the URL, token=Bonds,Notes is two values and token=Bonds\\,%20Notes is no escape, so neither
    matches (C3b). Two parameters together give the records both keep."""
    _narrowing_world(world)
    container, token, peer = _param(world, "container"), _param(world, "token"), _param(world, "peer")
    permit, kind = _param(world, "permit"), _param(world, "kind")

    assert _listed(world, "permits", **{container: "Permit a zone"}) == ["Permit a"]
    assert _listed(world, "all", **{token: "gOLD TOKEN"}) == ["Ledger a"]
    assert _listed(world, "all", **{peer: "Ledger a"}) == ["Ledger a", "Ledger b"]

    north = _page(world, "all", includeTotal=True, **{permit: "Region north"})
    assert (_names(world, north), north["totalCount"]) == (["Ledger a"], 1)
    (item,) = north["items"]
    assert [p[_out(world, "Bown.name")] for p in item[_out(world, "Bown")]] == ["Permit a"]
    south = _page(world, "all", includeTotal=True, **{permit: "Region south"})
    assert (_names(world, south), south["totalCount"]) == (["Ledger a", "Ledger b"], 2)
    assert [p[_out(world, "Bown.name")] for p in south["items"][0][_out(world, "Bown")]] == [
        "Permit c"
    ]

    assert _listed(world, "all", **{kind: world.key("Capi.R")}) == ["Ledger a", "Ledger b", "Ledger c"]
    assert _listed(world, "all", **{kind: world.key("Capi.R2")}) == []
    error = refused(
        consumer_list(world, world.key("Capi.all"), **{kind: "Nothing"}), 400, "UNKNOWN_OBJECT_TYPE"
    )
    assert world.key("Capi.R") in error["message"]

    either = ["Ledger a", "Ledger b"]
    all_ = world.key("Capi.all")

    def typed(query):
        return _names(world, ok(consumer_list_typed(world, all_, query)))

    assert _listed(world, "all", **{token: ["Gold token", "Bonds, Notes"]}) == either
    assert typed(f"{token}=Gold%20token,Bonds%2C%20Notes") == either
    assert typed(f"{token}=Bonds%2C%20Notes") == ["Ledger b"]
    assert _listed(world, "all", **{token: "Bonds, Notes"}) == ["Ledger b"]
    assert typed(f"{token}=Bonds,Notes") == []
    assert typed(f"{token}=Bonds\\,%20Notes") == []
    assert _listed(world, "all", **{token: "Bonds"}) == []

    assert typed(f"{peer}=Ledger%20a&{token}=Bonds%2C%20Notes") == ["Ledger b"]


@pytest.mark.journey("J28.9")
@pytest.mark.structures(*CAPI)
def test_parameters_on_get_by_id(world):
    """permit limits the array. An R without such a permit, or with a container that does not match,
    answers 404 OBJECT_NOT_FOUND. pageSize, or a list's parent parameter, answers 400
    PARAMETER_NOT_SUPPORTED."""
    made = _narrowing_world(world)
    permit, container = _param(world, "permit"), _param(world, "container")

    limited = _read(world, made["a"]["id"], **{permit: "Region north"})
    assert [p[_out(world, "Bown.name")] for p in limited[_out(world, "Bown")]] == ["Permit a"]
    refused(consumer_object(world, made["c"]["id"], **{permit: "Region north"}), 404, "OBJECT_NOT_FOUND")
    permit_b = made["permit_b"]["id"]
    refused(consumer_object(world, permit_b, **{container: "Permit a zone"}), 404, "OBJECT_NOT_FOUND")
    assert _read(world, permit_b, **{container: "Permit b zone"})[_out(world, "name")] == "Permit b"

    error = refused(consumer_object(world, permit_b, pageSize=5), 400, "PARAMETER_NOT_SUPPORTED")
    assert error["details"]["parameters"] == ["pageSize"]
    parent = _param(world, "permits.parent")
    error = refused(consumer_object(world, permit_b, **{parent: "x"}), 400, "PARAMETER_NOT_SUPPORTED")
    assert error["details"]["parameters"] == [parent]


@pytest.mark.journey("J28.10")
@pytest.mark.structures(*CAPI)
def test_paging_refusals(world):
    """An unknown list answers 404 LIST_NOT_FOUND. pageSize=0 and pageSize=101 answer 400
    INVALID_PAGE_SIZE. cursor with position answers 400 CONFLICTING_PAGE_PARAMETERS. A cursor from all
    sent with a different token answers 400 INVALID_CURSOR."""
    for name in ("One", "Two", "Three"):
        world.made("R", name)
    all_ = world.key("Capi.all")
    refused(consumer_list(world, "no-such-list"), 404, "LIST_NOT_FOUND")
    for size in (0, 101):
        refused(consumer_list(world, all_, pageSize=size), 400, "INVALID_PAGE_SIZE")
    cursor = _page(world, "all", pageSize=1)["nextCursor"]
    refused(consumer_list(world, all_, cursor=cursor, position=1), 400, "CONFLICTING_PAGE_PARAMETERS")
    token = _param(world, "token")
    refused(consumer_list(world, all_, pageSize=1, cursor=cursor, **{token: "x"}), 400, "INVALID_CURSOR")
