"""J29 — Resolve a business object through a consumer API (USER_JOURNEYS.md)."""

import pytest
from scenario import (
    consumer_list,
    consumer_object,
    consumer_resolve,
    consumer_xref,
    consumer_xref_typed,
    ok,
    refused,
)

CAPI = (
    "Capi", "R", "R2", "R.u", "R2.u", "K", "K.code", "B11", "Bown", "Bscope", "G", "D",
)


def _out(world, name):
    """An output name of ``Capi``, chosen by the configuration."""
    return world.key(f"Capi.{name}")


def _xref(world, **params):
    return ok(consumer_xref(world, **params))


def _typed(world, query):
    return ok(consumer_xref_typed(world, query))


def _scored(world, page):
    """Each result's name and score, in order."""
    return [(item[_out(world, "name")], item["matchScore"]) for item in page["results"]]


def _ledger(world, name, code, **kwargs):
    """An R with its own R.u, so no generated value takes part in a match."""
    return world.made("R", name, values={"R.u": code}, **kwargs)


def _paired(world, name, code, token_name, token_code):
    """An R paired (B11) with a new K."""
    record = _ledger(world, name, code)
    token = world.made("K", token_name, values={"K.code": token_code})
    ok(world.relate("B11", record["id"], token["id"]), 201)
    return record


def _same_as_get_by_id(world, page):
    for item in page["results"]:
        expected = ok(consumer_object(world, item[_out(world, "id")]))
        assert item == {**expected, "matchScore": item["matchScore"]}
        assert list(item)[-1] == "matchScore"


@pytest.mark.journey("J29")
@pytest.mark.structures(*CAPI)
def test_scored_lookup(world):
    """Given an R with R.u "LED-7", an R2 named "Led" and an R named "Ledger seven". When query=led-7
    (another case), query=Led and query=dger. Then the first finds the R by its code with matchScore
    500; the second ranks the R2 (name exact, 200) above the records whose name or code contains it
    (30 or 40, the higher first); the third finds only by contains; ties order by public type name,
    then name; each result equals get by ID's answer plus matchScore."""
    coded = _ledger(world, "Alpha", "LED-7")
    world.made("R2", "Led", parent=coded["id"])
    seven = _ledger(world, "Ledger seven", "SEV-7")
    world.made("R2", "Zed ledger", parent=seven["id"])
    _ledger(world, "Abc ledger", "ABC-1")

    by_code = _xref(world, query="led-7")
    assert _scored(world, by_code) == [("Alpha", 500)]
    assert by_code["results"][0][_out(world, "id")] == coded["id"]

    by_name = _xref(world, query="Led")
    assert _scored(world, by_name) == [
        ("Led", 200),
        ("Alpha", 40),
        ("Zed ledger", 30),
        ("Abc ledger", 30),
        ("Ledger seven", 30),
    ]
    contained = _xref(world, query="dger")
    # The R2's public name sorts before the R's in both configurations, whatever their names.
    assert _scored(world, contained) == [("Zed ledger", 30), ("Abc ledger", 30), ("Ledger seven", 30)]
    for page in (by_code, by_name, contained):
        _same_as_get_by_id(world, page)


def _watched(world, name):
    """A D named ``name``, owned by a new R and watched (Bscope) by another R and an R2 under it."""
    owner = _ledger(world, "Owner", "OW-1")
    region = world.made("G", "Region one", values={"K.code": "RG-1"})
    permit = world.made(
        "D", name, parent=world.dependant_parent(region["id"]), relations=[world.owner("Bown", owner["id"])]
    )
    watcher = _ledger(world, "Watcher", "WA-1")
    entry = world.made("R2", "Watching entry", parent=watcher["id"])
    ok(world.relate("Bscope", watcher["id"], permit["id"]), 201)
    ok(world.relate("Bscope", entry["id"], permit["id"]), 201)
    return permit


@pytest.mark.journey("J29.1")
@pytest.mark.structures(*CAPI)
def test_promoted_matches(world):
    """Given an R paired (B11) with a K whose K.code is "TK-9", and a D named "Watch zone" watched
    (Bscope) by an R and an R2. When query=tk-9, and query=Watch zone. Then the R is found with 80;
    the D passes 60 to the R2 only (preferTargetTypes); an object matching itself and through
    promotion keeps the higher score."""
    _paired(world, "Paired", "PA-1", "Token nine", "TK-9")
    # Its own code contains the term (40); its K is named the term exactly (75).
    _paired(world, "Beta", "BTK-9B", "TK-9", "KB-1")
    # Its own code is the term (500); its K's code contains it (10).
    _paired(world, "Gamma", "TK-9", "Third", "TK-9X")
    assert _scored(world, _xref(world, query="tk-9")) == [("Gamma", 500), ("Paired", 80), ("Beta", 75)]

    _watched(world, "Watch zone")
    watched = _xref(world, query="Watch zone")
    assert _scored(world, watched) == [("Watch zone", 200), ("Watching entry", 60)]
    assert watched["results"][1]["objectType"] == world.key("Capi.R2")
    _same_as_get_by_id(world, watched)


@pytest.mark.journey("J29.2")
@pytest.mark.structures(*CAPI)
def test_several_terms(world):
    """query=LED-7,TK-9 and the same as two query parameters find both, each with its best score; a
    K named "Bonds, Notes" pairing an R is matched by Bonds%2C%20Notes."""
    _ledger(world, "Alpha", "LED-7")
    _paired(world, "Paired", "PA-1", "Token nine", "TK-9")
    _paired(world, "Bonded", "BO-1", "Bonds, Notes", "BN-1")

    both = [("Alpha", 500), ("Paired", 80)]
    typed = _typed(world, "query=LED-7,TK-9")
    assert _scored(world, typed) == both
    assert typed["query"] == ["LED-7", "TK-9"]
    assert _scored(world, _xref(world, query=["LED-7", "TK-9"])) == both

    assert _scored(world, _typed(world, "query=Bonds%2C%20Notes")) == [("Bonded", 75)]
    assert _scored(world, _xref(world, query="Bonds, Notes")) == [("Bonded", 75)]
    assert _typed(world, "query=Bonds,Notes")["results"] == []


@pytest.mark.journey("J29.3")
@pytest.mark.structures(*CAPI)
def test_expect_one(world):
    """A unique code answers the bare object with matchScore; no match answers 404 NO_MATCH; two
    records with the same name answer 409 AMBIGUOUS_MATCH naming both; expect=one&pageSize=5 answers
    400 PARAMETER_NOT_SUPPORTED."""
    coded = _ledger(world, "Alpha", "LED-7")
    twins = [_ledger(world, "Twin", "TW-1"), _ledger(world, "Twin", "TW-2")]

    found = _xref(world, query="led-7", expect="one")
    assert found == {**ok(consumer_object(world, coded["id"])), "matchScore": 500}
    refused(consumer_xref(world, query="nothing-like-it", expect="one"), 404, "NO_MATCH")

    error = refused(consumer_xref(world, query="twin", expect="one"), 409, "AMBIGUOUS_MATCH")
    assert error["details"]["count"] == 2
    candidates = error["details"]["candidates"]
    assert sorted(c["id"] for c in candidates) == sorted(t["id"] for t in twins)
    assert all(c["matchScore"] == 200 and c["objectType"] == world.key("Capi.R") for c in candidates)
    assert all(c["name"] == "Twin" for c in candidates)

    refused(consumer_xref(world, query="led-7", expect="one", pageSize=5), 400, "PARAMETER_NOT_SUPPORTED")


@pytest.mark.journey("J29.4")
@pytest.mark.structures(*CAPI)
def test_paging(world):
    """Given seven records containing a term. With pageSize=3: to the end and back through the
    cursors, position=3, from=end; totalCount 7 and startIndex on every page; a cursor sent with
    another query answers 400 INVALID_CURSOR."""
    names = [f"Pager {number}" for number in range(1, 8)]
    for number, name in enumerate(names, start=1):
        _ledger(world, name, f"PG-{number}")

    def page(**params):
        return _xref(world, query="pager", pageSize=3, **params)

    def listed(found):
        return [item[_out(world, "name")] for item in found["results"]]

    first = page()
    assert (first["query"], first["workspace"], first["pageSize"]) == (["pager"], "default", 3)
    assert first["prevCursor"] is None
    forward, current = [first], first
    while current["nextCursor"]:
        current = page(cursor=current["nextCursor"])
        forward.append(current)
    assert [listed(p) for p in forward] == [names[0:3], names[3:6], names[6:]]
    assert [(p["totalCount"], p["startIndex"]) for p in forward] == [(7, 0), (7, 3), (7, 6)]

    back, current = [], forward[-1]
    while current["prevCursor"]:
        current = page(cursor=current["prevCursor"])
        back.append((listed(current), current["totalCount"], current["startIndex"]))
    assert back == [(names[3:6], 7, 3), (names[0:3], 7, 0)]

    at = page(position=3)
    assert (listed(at), at["totalCount"], at["startIndex"]) == (names[3:6], 7, 3)
    last = page(**{"from": "end"})
    assert (listed(last), last["totalCount"], last["startIndex"]) == (names[4:], 7, 4)

    refused(
        consumer_xref(world, query="other", pageSize=3, cursor=first["nextCursor"]), 400, "INVALID_CURSOR"
    )


@pytest.mark.journey("J29.5")
@pytest.mark.structures(*CAPI)
def test_refusals(world):
    """No query or only empty terms: 400 QUERY_REQUIRED; 101 terms: 400 TOO_MANY_TERMS; a list's
    parent parameter, seek or includeTotal: 400 PARAMETER_NOT_SUPPORTED, while a definition parameter
    is applied; a two-character term matches exactly only."""
    _ledger(world, "Qz", "QZ-1")
    _ledger(world, "Qz long", "QZ-2")

    refused(consumer_xref(world), 400, "QUERY_REQUIRED")
    refused(consumer_xref_typed(world, "query=,,"), 400, "QUERY_REQUIRED")
    refused(consumer_xref(world, query=""), 400, "QUERY_REQUIRED")
    terms = ",".join(f"T{number}" for number in range(101))
    error = refused(consumer_xref_typed(world, f"query={terms}"), 400, "TOO_MANY_TERMS")
    assert "100" in error["message"]
    assert _typed(world, "query=" + ",".join(f"T{number}" for number in range(100)))["results"] == []

    for name, value in ((world.key("Capi.entries.parent"), "x"), ("seek", "1"), ("includeTotal", "true")):
        error = refused(consumer_xref(world, query="qz", **{name: value}), 400, "PARAMETER_NOT_SUPPORTED")
        assert error["details"]["parameters"] == [name]
    assert _xref(world, query="qz", **{world.key("Capi.token"): "x"})["results"] == []

    assert _scored(world, _xref(world, query="qz")) == [("Qz", 200)]


def _param(world, name):
    """A parameter name of ``Capi``, chosen by the configuration."""
    return world.key(f"Capi.{name}")


def _found(world, page):
    """Each result's public type, name and score, ignoring the order of equal results."""
    return sorted((item["objectType"], item[_out(world, "name")], item["matchScore"]) for item in page["results"])


@pytest.mark.journey("J29.6")
@pytest.mark.structures(*CAPI, "M")
def test_parameters_narrow_the_lookup(world):
    """Given an R and an R2 both named "Twin", and records matching "Twin" by contains: an R paired
    (B11) with a K named "Coin", an R with a permit in G "North", and a D under an M named "Yard".
    kind keeps the named type and totalCount follows; an unknown kind is 400 UNKNOWN_OBJECT_TYPE.
    container, token and peer keep what they keep on lists; permitRegion keeps the R with a North
    permit and limits its permits. Two parameters keep what both keep, each result with the score it
    has without parameters. A kind resolves an ambiguous expect=one; a cursor sent with another kind
    is 400 INVALID_CURSOR; a list's parent parameter is 400 PARAMETER_NOT_SUPPORTED."""
    holder = _ledger(world, "Holder", "HO-1")
    twin = _ledger(world, "Twin", "TW-1")
    base = _ledger(world, "Base", "BA-1")
    twin_entry = world.made("R2", "Twin", parent=base["id"])
    _paired(world, "Twin paired", "TP-1", "Coin", "CO-1")
    permitted = _ledger(world, "Twin permitted", "TPM-1")
    north = world.made("G", "North", values={"K.code": "GN"})
    south = world.made("G", "South", values={"K.code": "GS"})
    for region, name in ((north, "North permit"), (south, "South permit")):
        world.made(
            "D", name, parent=world.dependant_parent(region["id"]), relations=[world.owner("Bown", permitted["id"])]
        )
    yard = world.made("M", "Yard", parent=south["id"])
    world.made("D", "Twin yard permit", parent=yard["id"], relations=[world.owner("Bown", holder["id"])])
    spot = world.made(
        "D", "Watched spot", parent=world.dependant_parent(south["id"]), relations=[world.owner("Bown", base["id"])]
    )
    ok(world.relate("Bscope", twin["id"], spot["id"]), 201)
    ok(world.relate("Bscope", twin_entry["id"], spot["id"]), 201)

    ledger, entry, permit = world.key("Capi.R"), world.key("Capi.R2"), world.key("Capi.D")
    everything = _xref(world, query="Twin")
    assert _found(world, everything) == sorted([
        (ledger, "Twin", 200),
        (entry, "Twin", 200),
        (ledger, "Twin paired", 30),
        (ledger, "Twin permitted", 30),
        (permit, "Twin yard permit", 30),
    ])
    scores = {item[_out(world, "id")]: item["matchScore"] for item in everything["results"]}

    def narrowed(**params):
        page = _xref(world, query="Twin", **{_param(world, name): value for name, value in params.items()})
        assert page["totalCount"] == len(page["results"])
        for item in page["results"]:
            assert item["matchScore"] == scores[item[_out(world, "id")]]
        return page

    assert _found(world, narrowed(kind=ledger)) == sorted([
        (ledger, "Twin", 200), (ledger, "Twin paired", 30), (ledger, "Twin permitted", 30),
    ])
    refused(consumer_xref(world, query="Twin", **{_param(world, "kind"): "Nothing"}), 400, "UNKNOWN_OBJECT_TYPE")
    assert _found(world, narrowed(container="Yard")) == [(permit, "Twin yard permit", 30)]
    assert _found(world, narrowed(token="coin")) == [(ledger, "Twin paired", 30)]
    assert _found(world, narrowed(peer="Twin")) == sorted([(ledger, "Twin", 200), (entry, "Twin", 200)])

    held = narrowed(permit="North")
    assert _found(world, held) == [(ledger, "Twin permitted", 30)]
    assert held["results"][0][_out(world, "Bown")] == [
        {_out(world, "Bown.name"): "North permit", _out(world, "Bown.G"): "North"}
    ]
    assert _found(world, narrowed(kind=ledger, peer="Twin")) == [(ledger, "Twin", 200)]

    error = refused(consumer_xref(world, query="Twin", expect="one"), 409, "AMBIGUOUS_MATCH")
    assert error["details"]["count"] == 2
    one = _xref(world, query="Twin", expect="one", **{_param(world, "kind"): entry})
    assert one == {**ok(consumer_object(world, twin_entry["id"])), "matchScore": 200}

    first = _xref(world, query="Twin", pageSize=2, **{_param(world, "kind"): ledger})
    assert first["totalCount"] == 3 and first["nextCursor"]
    refused(
        consumer_xref(world, query="Twin", pageSize=2, cursor=first["nextCursor"], **{_param(world, "kind"): entry}),
        400,
        "INVALID_CURSOR",
    )
    error = refused(
        consumer_xref(world, query="Twin", **{_param(world, "entries.parent"): twin["id"]}),
        400,
        "PARAMETER_NOT_SUPPORTED",
    )
    assert error["details"]["parameters"] == [_param(world, "entries.parent")]


@pytest.mark.journey("J29.7")
@pytest.mark.structures(*CAPI)
def test_scores_from_limits_which_related_records_score(world):
    """Given two D named "Gate zone", one below G "North" and one below "South"; an R2 "North watcher"
    watching the North one, an R2 "South watcher" the South one, and an R2 named "Gate zone" watching
    the South one. query=Gate zone finds both D and the R2 named "Gate zone" (200, own) and both
    watchers (60, promoted). With watchRegion=North the North watcher keeps 60 and its watchedPermits
    holds only the North D; the South watcher is absent; the own matches keep 200."""
    owner = _ledger(world, "Owner", "OW-1")
    base = _ledger(world, "Watch base", "WB-1")
    zones = {}
    for region_name in ("North", "South"):
        region = world.made("G", region_name, values={"K.code": f"G{region_name[0]}"})
        zones[region_name] = world.made(
            "D", "Gate zone", parent=world.dependant_parent(region["id"]), relations=[world.owner("Bown", owner["id"])]
        )
    watchers = {}
    for name, region_name in (("North watcher", "North"), ("South watcher", "South"), ("Gate zone", "South")):
        watchers[name] = world.made("R2", name, parent=base["id"])
        ok(world.relate("Bscope", watchers[name]["id"], zones[region_name]["id"]), 201)

    entry, permit = world.key("Capi.R2"), world.key("Capi.D")
    assert _found(world, _xref(world, query="Gate zone")) == sorted([
        (entry, "Gate zone", 200),
        (permit, "Gate zone", 200),
        (permit, "Gate zone", 200),
        (entry, "North watcher", 60),
        (entry, "South watcher", 60),
    ])

    watched = _xref(world, query="Gate zone", **{_param(world, "watch"): "North"})
    assert _found(world, watched) == sorted([
        (entry, "Gate zone", 200),
        (permit, "Gate zone", 200),
        (permit, "Gate zone", 200),
        (entry, "North watcher", 60),
    ])
    assert watched["totalCount"] == 4
    (north_watcher,) = [item for item in watched["results"] if item[_out(world, "name")] == "North watcher"]
    assert north_watcher[_out(world, "id")] == watchers["North watcher"]["id"]
    assert north_watcher[_out(world, "Bscope")] == [{_out(world, "Bscope.name"): "Gate zone"}]


# --- batch resolve (C14) ---


def _resolve(world, body, **params):
    response = consumer_resolve(world, body, **params)
    answer = ok(response)
    assert response.headers["RDM-Workspace"] == answer["workspace"]
    return answer


def _single(world, item, defaults=None):
    """The single read an item stands for: xref?expect=one by query, get by ID by id, with the
    defaults overlaid by the item's own parameters."""
    params = {**(defaults or {}), **{name: value for name, value in item.items() if name not in ("ref", "query", "id")}}
    if "id" in item:
        return consumer_object(world, item["id"], **params)
    return consumer_xref(world, query=item["query"], expect="one", **params)


def _same_as_single(world, body, answer):
    """Each outcome is the single read's answer: the object when found, its error otherwise."""
    statuses = {200: "found", 404: "not_found", 409: "ambiguous", 400: "rejected"}
    for index, (item, outcome) in enumerate(zip(body["items"], answer["items"], strict=True)):
        assert (outcome["index"], outcome["ref"]) == (index, item.get("ref"))
        single = _single(world, item, body.get("defaults"))
        assert outcome["status"] == statuses[single.status_code], (item, outcome)
        if single.status_code == 200:
            assert outcome["object"] == single.json()
            assert "error" not in outcome
        else:
            assert outcome["error"] == single.json()["error"]
            assert "object" not in outcome


def _statuses(answer):
    return [outcome["status"] for outcome in answer["items"]]


@pytest.mark.journey("J29.8")
@pytest.mark.structures(*CAPI)
def test_batch_resolve_a_mixed_batch(world):
    """One batch holding J29's lookups as items: a code in another case, a name, a promoted code, two
    terms in one item, a "Bonds, Notes" term as one string, an object ID, an unknown ID, a miss, a
    term found by contains only and the two records sharing a name. Outcomes come in item order with
    index and ref; each found equals the xref?expect=one (or get by ID) body; each not_found and
    ambiguous equals that read's 404 or 409 error; counts add up. The same lookup sent again, its
    terms reordered or repeated, gets the same answer."""
    coded = _ledger(world, "Alpha", "LED-7")
    world.made("R2", "Led", parent=coded["id"])
    _ledger(world, "Ledger seven", "SEV-7")
    _paired(world, "Paired", "PA-1", "Token nine", "TK-9")
    _paired(world, "Bonded", "BO-1", "Bonds, Notes", "BN-1")
    _ledger(world, "Twin", "TW-1")
    _ledger(world, "Twin", "TW-2")

    body = {
        "items": [
            {"ref": "row-1", "query": "led-7"},
            {"ref": "row-2", "query": "Led"},
            {"ref": "row-3", "query": "tk-9"},
            {"ref": "row-4", "query": ["LED-7", "TK-9"]},
            {"ref": "row-5", "query": "Bonds, Notes"},
            {"ref": "row-6", "id": coded["id"]},
            {"ref": "row-7", "id": "00000000-0000-4000-8000-000000000000"},
            {"query": "nothing-like-it"},
            {"ref": "row-9", "query": "dger"},
            {"ref": "row-10", "query": "twin"},
        ]
    }
    answer = _resolve(world, body)
    assert answer["workspace"] == "default"
    assert _statuses(answer) == [
        "found", "found", "found", "found", "found", "found", "not_found", "not_found", "found", "ambiguous",
    ]
    found = [outcome["object"] for outcome in answer["items"] if outcome["status"] == "found"]
    assert [(item[_out(world, "name")], item.get("matchScore")) for item in found] == [
        ("Alpha", 500), ("Led", 200), ("Paired", 80), ("Alpha", 500), ("Bonded", 75), ("Alpha", None),
        ("Ledger seven", 30),
    ]
    codes = [outcome["error"]["code"] for outcome in answer["items"] if "error" in outcome]
    assert codes == ["OBJECT_NOT_FOUND", "NO_MATCH", "AMBIGUOUS_MATCH"]
    assert answer["counts"] == {"found": 7, "notFound": 2, "ambiguous": 1, "rejected": 0}
    _same_as_single(world, body, answer)

    # The same lookup sent again, its terms reordered and repeated, has the same answer.
    repeated = {"items": [{"query": ["LED-7", "TK-9"]}, {"query": ["TK-9", "LED-7", "TK-9"]}, {"query": "twin"}] * 2}
    answer = _resolve(world, repeated)
    assert answer["items"][1]["object"] == answer["items"][0]["object"] == found[3]
    assert [outcome["status"] for outcome in answer["items"]] == ["found", "found", "ambiguous"] * 2
    assert answer["items"][5]["error"] == answer["items"][2]["error"]


@pytest.mark.journey("J29.9")
@pytest.mark.structures(*CAPI)
def test_batch_resolve_defaults_and_item_parameters(world):
    """defaults kind with R's public name narrows every item; an item giving kind with R2's replaces
    it; an item resolving the "Twin" 409 with defaults alone is found with its own kind; a by-ID item
    filtered out by container is not_found; watchRegion (scoresFrom) in defaults gives J29.7's
    scores."""
    twin = _ledger(world, "Twin", "TW-1")
    base = _ledger(world, "Base", "BA-1")
    twin_entry = world.made("R2", "Twin", parent=base["id"])
    owner = _ledger(world, "Owner", "OW-1")
    watchers = {}
    for region_name in ("North", "South"):
        region = world.made("G", region_name, values={"K.code": f"G{region_name[0]}"})
        zone = world.made(
            "D", "Portal", parent=world.dependant_parent(region["id"]), relations=[world.owner("Bown", owner["id"])]
        )
        watchers[region_name] = world.made("R2", f"{region_name} watcher", parent=base["id"])
        ok(world.relate("Bscope", watchers[region_name]["id"], zone["id"]), 201)

    ledger, entry = world.key("Capi.R"), world.key("Capi.R2")
    kind, container, watch = _param(world, "kind"), _param(world, "container"), _param(world, "watch")

    body = {
        "defaults": {kind: ledger},
        "items": [
            {"ref": "default kind", "query": "Twin"},
            {"ref": "own kind", "query": "Twin", kind: entry},
            {"ref": "by id", "id": twin["id"], container: "Yard"},
            {"ref": "by id, default kind", "id": twin_entry["id"]},
        ],
    }
    answer = _resolve(world, body)
    assert _statuses(answer) == ["found", "found", "not_found", "not_found"]
    assert answer["items"][0]["object"][_out(world, "id")] == twin["id"]
    assert answer["items"][1]["object"][_out(world, "id")] == twin_entry["id"]
    _same_as_single(world, body, answer)

    plain = {"items": [{"query": "Twin"}, {"query": "Twin", kind: entry}]}
    answer = _resolve(world, plain)
    assert _statuses(answer) == ["ambiguous", "found"]
    _same_as_single(world, plain, answer)

    # Both watchers take 60 from the Portal they watch; scoresFrom lets only North's pass.
    portals = {"defaults": {kind: entry}, "items": [{"query": "Portal"}, {"query": "Portal", watch: "North"}]}
    answer = _resolve(world, portals)
    assert _statuses(answer) == ["ambiguous", "found"]
    assert answer["items"][1]["object"][_out(world, "id")] == watchers["North"]["id"]
    assert answer["items"][1]["object"]["matchScore"] == 60
    _same_as_single(world, portals, answer)
    narrowed = _resolve(world, {"defaults": {kind: entry, watch: "North"}, "items": [{"query": "Portal"}]})
    assert narrowed["items"][0]["object"] == answer["items"][1]["object"]


@pytest.mark.journey("J29.10")
@pytest.mark.structures(*CAPI)
def test_batch_resolve_refusals(world):
    """Per item, rejected with the single read's code and a pointer into the item: both query and id,
    neither, expect, pageSize, an unknown name, an empty term list, 101 terms, an unknown kind. As a
    whole: an unknown or unapplied name in defaults, a definition parameter in the query string, a
    body of the wrong shape (400), an unknown workspace (404), and, with the limit set to 5, six items
    (413 BATCH_TOO_LARGE naming the setting). GET /capabilities reports the limit."""
    coded = _ledger(world, "Alpha", "LED-7")
    kind = _param(world, "kind")
    items = [
        {"query": "led-7", "id": coded["id"]},
        {"ref": "neither"},
        {"query": "led-7", "expect": "one"},
        {"query": "led-7", "pageSize": "5"},
        {"query": "led-7", "bogus": "1"},
        {"query": ["", " "]},
        {"query": [f"T{number}" for number in range(101)]},
        {"query": "led-7", kind: "Nothing"},
        {"query": "led-7"},
    ]
    answer = _resolve(world, {"items": items})
    assert _statuses(answer) == ["rejected"] * 8 + ["found"]
    errors = [(outcome["error"]["code"], outcome["error"]["details"]["pointer"]) for outcome in answer["items"][:8]]
    assert errors == [
        ("QUERY_OR_ID_REQUIRED", "/items/0"),
        ("QUERY_OR_ID_REQUIRED", "/items/1"),
        ("PARAMETER_NOT_SUPPORTED", "/items/2/expect"),
        ("PARAMETER_NOT_SUPPORTED", "/items/3/pageSize"),
        ("UNKNOWN_PARAMETER", "/items/4/bogus"),
        ("QUERY_REQUIRED", "/items/5/query"),
        ("TOO_MANY_TERMS", "/items/6/query"),
        ("UNKNOWN_OBJECT_TYPE", f"/items/7/{kind}"),
    ]
    assert answer["counts"] == {"found": 1, "notFound": 0, "ambiguous": 0, "rejected": 8}
    # A value from defaults points at defaults.
    defaulted = _resolve(world, {"defaults": {kind: "Nothing"}, "items": [{"query": "led-7"}]})
    assert defaulted["items"][0]["error"]["details"]["pointer"] == f"/defaults/{kind}"

    one = {"items": [{"query": "led-7"}]}
    error = refused(consumer_resolve(world, {**one, "defaults": {"bogus": "1"}}), 400, "UNKNOWN_PARAMETER")
    assert error["details"]["pointer"] == "/defaults/bogus"
    refused(consumer_resolve(world, {**one, "defaults": {"expect": "one"}}), 400, "PARAMETER_NOT_SUPPORTED")
    refused(consumer_resolve(world, one, **{kind: world.key("Capi.R")}), 400, "PARAMETER_NOT_SUPPORTED")
    refused(consumer_resolve(world, one, query="led-7"), 400, "PARAMETER_NOT_SUPPORTED")
    refused(consumer_resolve(world, one, bogus="1"), 400, "UNKNOWN_PARAMETER")
    refused(consumer_resolve(world, one, workspace="nowhere"), 404, "WORKSPACE_NOT_FOUND")
    for wrong in (
        None,
        [],
        {"items": []},
        {"items": "led-7"},
        {"items": ["led-7"]},
        {"items": [{"query": 7}]},
        {"items": [{"query": "led-7", "ref": ""}]},
        {"items": [{"id": ["a", "b"]}]},
        {"items": [{"query": "led-7"}], "defaults": []},
        {"items": [{"query": "led-7"}], "other": 1},
    ):
        refused(consumer_resolve(world, wrong), 400, "REQUEST_VALIDATION_ERROR")
    raw = world.api.client.post(
        f"/api/consumer/{world.key('Capi')}/v1/resolve", content=b"{not json", headers={"content-type": "application/json"}
    )
    refused(raw, 400, "REQUEST_VALIDATION_ERROR")

    capabilities = ok(world.api.get("/capabilities"))
    assert capabilities["consumerApi"] == {"resolveMaxItems": 1000, "setting": "CONSUMER_RESOLVE_MAX_ITEMS"}
    state = world.api.client.app.state
    saved = state.consumer_resolve_max_items
    state.consumer_resolve_max_items = 5
    try:
        error = refused(consumer_resolve(world, {"items": [{"query": "led-7"}] * 6}), 413, "BATCH_TOO_LARGE")
        assert error["details"] == {"setting": "CONSUMER_RESOLVE_MAX_ITEMS", "maximum": 5, "items": 6}
        assert _statuses(_resolve(world, {"items": [{"query": "led-7"}] * 5})) == ["found"] * 5
    finally:
        state.consumer_resolve_max_items = saved


# --- crosswalk (C15) ---


def _to(world, name):
    """The ``to.`` name of a targetable parameter of ``Capi``."""
    return f"to.{_param(world, name)}"


def _crosswalk(world):
    """Ledger X (LX) watching (Bscope) a D below G North and a D below South; Ledger Y (LY) watching
    only the North D; Entry Z (EZ, an R2) watching two D below South. Each D has its own owner, since
    an R owns one active D per G."""
    regions = {name: world.made("G", name, values={"K.code": f"G{name[0]}"}) for name in ("North", "South")}
    desks = {}
    for number, (name, region) in enumerate(
        (("North desk", "North"), ("South desk", "South"), ("South annex", "South")), start=1
    ):
        owner = _ledger(world, f"Owner {number}", f"OW-{number}")
        desks[name] = world.made(
            "D",
            name,
            parent=world.dependant_parent(regions[region]["id"]),
            relations=[world.owner("Bown", owner["id"])],
        )
    x = _ledger(world, "Ledger X", "LX")
    y = _ledger(world, "Ledger Y", "LY")
    z = world.made("R2", "Entry Z", parent=y["id"], values={"R2.u": "EZ"})
    for record, names in ((x, ("North desk", "South desk")), (y, ("North desk",)), (z, ("South desk", "South annex"))):
        for name in names:
            ok(world.relate("Bscope", record["id"], desks[name]["id"]), 201)
    return x, y, z


def _watched_item(world, name):
    return {_out(world, "Bscope.name"): name}


def _without_pointer(error):
    """An error without where it points: a single read names the query parameter, a batch item the
    place in the body."""
    details = {key: value for key, value in error.get("details", {}).items() if key not in ("path", "pointer")}
    return {**error, "details": details}


@pytest.mark.journey("J29.11")
@pytest.mark.structures(*CAPI)
def test_crosswalk_with_expect_one(world):
    """query=LX&to.watchRegion=South&expect=one answers Ledger X with target the South item, its
    watchedPermits only that item and the matchScore it has without to.; watchRegion=North with the
    target gives the same answer. LY is 404 TARGET_NOT_FOUND, EZ 409 AMBIGUOUS_TARGET with count 2
    and both items, to.watchRegion=North,South on LX 409 AMBIGUOUS_TARGET. Two records sharing a
    name, one with a South target, stay 409 AMBIGUOUS_MATCH."""
    x, y, z = _crosswalk(world)
    to, watch = _to(world, "watch"), _param(world, "watch")
    south = _watched_item(world, "South desk")

    plain = _xref(world, query="LX", expect="one")
    found = _xref(world, query="LX", expect="one", **{to: "South"})
    assert found[_out(world, "id")] == x["id"]
    assert found["target"] == south
    assert found[_out(world, "Bscope")] == [south]
    assert found["matchScore"] == plain["matchScore"] == 500
    assert list(found)[-2:] == ["target", "matchScore"]
    assert {key: value for key, value in found.items() if key not in ("target", _out(world, "Bscope"))} == {
        key: value for key, value in plain.items() if key != _out(world, "Bscope")
    }
    assert _xref(world, query="LX", expect="one", **{watch: "North", to: "South"}) == found

    error = refused(consumer_xref(world, query="LY", expect="one", **{to: "South"}), 404, "TARGET_NOT_FOUND")
    assert (error["details"]["id"], error["details"]["objectType"]) == (y["id"], world.key("Capi.R"))
    assert error["details"]["parameter"] == to
    error = refused(consumer_xref(world, query="EZ", expect="one", **{to: "South"}), 409, "AMBIGUOUS_TARGET")
    assert (error["details"]["id"], error["details"]["objectType"]) == (z["id"], world.key("Capi.R2"))
    assert error["details"]["count"] == 2
    assert sorted(error["details"]["targets"], key=str) == sorted(
        [south, _watched_item(world, "South annex")], key=str
    )
    error = refused(
        consumer_xref_typed(world, f"query=LX&expect=one&{to}=North,South"), 409, "AMBIGUOUS_TARGET"
    )
    assert error["details"]["count"] == 2

    twin = _ledger(world, "Twin", "TW-1")
    _ledger(world, "Twin", "TW-2")
    south_desk = _xref(world, query="South desk", expect="one")[_out(world, "id")]
    ok(world.relate("Bscope", twin["id"], south_desk), 201)
    refused(consumer_xref(world, query="twin", expect="one", **{to: "South"}), 409, "AMBIGUOUS_MATCH")


@pytest.mark.journey("J29.12")
@pytest.mark.structures(*CAPI)
def test_crosswalk_on_pages_and_get_by_id(world):
    """Get by ID with to.watchRegion=South: Ledger X has target the item, Ledger Y is 404
    TARGET_NOT_FOUND, Entry Z 409 AMBIGUOUS_TARGET. The list of every R with the target keeps every
    ledger and its totalCount, each target an array (Ledger Y's empty); a cursor from the page without
    to. reads the next page with it. XREF expect=any for a term both ledgers match: both, with the
    same scores and order."""
    x, y, z = _crosswalk(world)
    to = _to(world, "watch")
    south = _watched_item(world, "South desk")

    by_id = ok(consumer_object(world, x["id"], **{to: "South"}))
    assert by_id["target"] == south
    assert list(by_id)[-1] == "target"
    refused(consumer_object(world, y["id"], **{to: "South"}), 404, "TARGET_NOT_FOUND")
    refused(consumer_object(world, z["id"], **{to: "South"}), 409, "AMBIGUOUS_TARGET")

    ledgers = world.key("Capi.all")
    plain = ok(consumer_list(world, ledgers, includeTotal="true"))
    targeted = ok(consumer_list(world, ledgers, includeTotal="true", **{to: "South"}))
    assert targeted["totalCount"] == plain["totalCount"] == 5
    names = [item[_out(world, "name")] for item in plain["items"]]
    assert [item[_out(world, "name")] for item in targeted["items"]] == names
    targets = {item[_out(world, "name")]: item["target"] for item in targeted["items"]}
    assert targets["Ledger X"] == [south]
    assert targets["Ledger Y"] == []
    first = ok(consumer_list(world, ledgers, pageSize=2))
    following = ok(consumer_list(world, ledgers, pageSize=2, cursor=first["nextCursor"], **{to: "South"}))
    assert [item[_out(world, "name")] for item in following["items"]] == names[2:4]
    assert all("target" in item for item in following["items"])

    without = _xref(world, query="Ledger")
    page = _xref(world, query="Ledger", **{to: "South"})
    assert _scored(world, page) == _scored(world, without) == [("Ledger X", 30), ("Ledger Y", 30)]
    assert page["totalCount"] == without["totalCount"]
    assert [item["target"] for item in page["results"]] == [[south], []]


@pytest.mark.journey("J29.13")
@pytest.mark.structures(*CAPI)
def test_crosswalk_in_batch_resolve(world):
    """defaults to.watchRegion=South; items LX, LY, EZ, Ledger X by ID, and LY with its own
    to.watchRegion=North: found with target, not_found TARGET_NOT_FOUND, ambiguous AMBIGUOUS_TARGET,
    found, found; each outcome is the single read's answer, and counts add up."""
    x, _y, _z = _crosswalk(world)
    to = _to(world, "watch")
    body = {
        "defaults": {to: "South"},
        "items": [
            {"query": "LX"},
            {"query": "LY"},
            {"query": "EZ"},
            {"id": x["id"]},
            {"query": "LY", to: "North"},
        ],
    }
    answer = _resolve(world, body)
    assert _statuses(answer) == ["found", "not_found", "ambiguous", "found", "found"]
    assert answer["counts"] == {"found": 3, "notFound": 1, "ambiguous": 1, "rejected": 0}
    assert answer["items"][0]["object"]["target"] == _watched_item(world, "South desk")
    assert answer["items"][4]["object"]["target"] == _watched_item(world, "North desk")
    for index, (item, outcome) in enumerate(zip(body["items"], answer["items"], strict=True)):
        single = _single(world, item, body["defaults"])
        if single.status_code == 200:
            assert outcome["object"] == single.json()
        else:
            assert _without_pointer(outcome["error"]) == _without_pointer(single.json()["error"])
            assert outcome["error"]["details"]["pointer"] == f"/defaults/{to}", index
    assert [o["error"]["code"] for o in answer["items"] if "error" in o] == ["TARGET_NOT_FOUND", "AMBIGUOUS_TARGET"]


@pytest.mark.journey("J29.14")
@pytest.mark.structures(*CAPI)
def test_crosswalk_refusals(world):
    """to.token (a related parameter) and to.nothing are 400 UNKNOWN_PARAMETER;
    to.watchRegion=South&to.permitRegion=North is 400 MULTIPLE_TARGETS. In batch resolve the same in
    an item rejects that item with a pointer into it, an item's to. name replaces a different one
    from defaults, and to.token in defaults refuses the request."""
    x, _y, _z = _crosswalk(world)
    watch_to, permit_to, token_to = _to(world, "watch"), _to(world, "permit"), f"to.{_param(world, 'token')}"
    for name in (token_to, "to.nothing"):
        error = refused(consumer_xref(world, query="LX", **{name: "South"}), 400, "UNKNOWN_PARAMETER")
        assert error["details"]["parameters"] == [name]
        assert watch_to in error["message"] and permit_to in error["message"]
    error = refused(
        consumer_object(world, x["id"], **{watch_to: "South", permit_to: "North"}), 400, "MULTIPLE_TARGETS"
    )
    assert sorted(error["details"]["parameters"]) == sorted([watch_to, permit_to])
    refused(
        consumer_list(world, world.key("Capi.all"), **{watch_to: "South", permit_to: "North"}),
        400,
        "MULTIPLE_TARGETS",
    )

    answer = _resolve(
        world,
        {
            "defaults": {watch_to: "South"},
            "items": [
                {"query": "LX", token_to: "x"},
                {"query": "LX", watch_to: "South", permit_to: "North"},
                {"query": "LX", permit_to: "North"},
                {"query": "LX"},
            ],
        },
    )
    assert _statuses(answer) == ["rejected", "rejected", "not_found", "found"]
    errors = [(o["error"]["code"], o["error"]["details"]["pointer"]) for o in answer["items"][:3]]
    assert errors[0] == ("UNKNOWN_PARAMETER", f"/items/0/{token_to}")
    assert errors[1][0] == "MULTIPLE_TARGETS" and errors[1][1].startswith("/items/1/")
    assert errors[2] == ("TARGET_NOT_FOUND", f"/items/2/{permit_to}")

    one = {"items": [{"query": "LX"}]}
    error = refused(consumer_resolve(world, {**one, "defaults": {token_to: "x"}}), 400, "UNKNOWN_PARAMETER")
    assert error["details"]["pointer"] == f"/defaults/{token_to}"
    refused(
        consumer_resolve(world, {**one, "defaults": {watch_to: "South", permit_to: "North"}}),
        400,
        "MULTIPLE_TARGETS",
    )


@pytest.mark.journey("J29.15")
@pytest.mark.structures(*CAPI)
def test_resolving_against_a_publication(world):
    """Given Ledger X watching the South desk, published as P1; then, live, Ledger X's code changed
    from LX to LX-NEW and its South watch removed. Then query=LX&expect=one with publication=P1 finds
    Ledger X by its published code, where live answers 404 NO_MATCH; with to.watchRegion=South the
    target is the published South item. Batch resolve with publication=P1 answers each item as the
    pinned single read does, with publication P1 in the envelope and the RDM-Publication header."""
    x, _y, _z = _crosswalk(world)
    to = _to(world, "watch")
    p1 = world.publish(world.change_set())["id"]
    record = world.record("R", x["id"])
    ok(world.update("R", x["id"], record["version"], values={"R.u": "LX-NEW"}))
    watches = ok(
        world.api.get(
            "/relations", objectId=x["id"], direction="outgoing", relationTypeKey=world.key("Bscope"), pageSize=100
        )
    )["items"]
    (south,) = [item["relation"] for item in watches if item["object"]["name"] == "South desk"]
    removed = world.api.delete(f"/relations/{south['id']}", expectedVersion=south["version"])
    assert removed.status_code == 204

    refused(consumer_xref(world, query="LX", expect="one"), 404, "NO_MATCH")
    pinned = _xref(world, query="LX", expect="one", publication=p1)
    assert pinned[_out(world, "id")] == x["id"]
    assert pinned[_out(world, "code")] == "LX"
    crossed = _xref(world, query="LX", expect="one", publication=p1, **{to: "South"})
    assert crossed["target"] == _watched_item(world, "South desk")
    refused(consumer_xref(world, query="LX-NEW", expect="one", **{to: "South"}), 404, "TARGET_NOT_FOUND")
    page = _xref(world, query="LX", publication=p1)
    assert page["publication"] == p1
    assert [item[_out(world, "id")] for item in page["results"]] == [x["id"]]

    body = {"defaults": {to: "South"}, "items": [{"query": "LX"}, {"query": "LX-NEW"}, {"id": x["id"]}]}
    response = consumer_resolve(world, body, publication=p1)
    answer = ok(response)
    assert answer["publication"] == p1
    assert response.headers["RDM-Publication"] == p1
    assert _statuses(answer) == ["found", "not_found", "found"]
    for item, outcome in zip(body["items"], answer["items"], strict=True):
        params = {to: "South", "publication": p1}
        single = (
            consumer_object(world, item["id"], **params)
            if "id" in item
            else consumer_xref(world, query=item["query"], expect="one", **params)
        )
        if single.status_code == 200:
            assert outcome["object"] == single.json()
        else:
            assert _without_pointer(outcome["error"]) == _without_pointer(single.json()["error"])
