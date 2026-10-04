"""J29 — Resolve a business object through a consumer API (USER_JOURNEYS.md)."""

import pytest
from scenario import consumer_object, consumer_xref, consumer_xref_typed, ok, refused

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
    """No query or only empty terms: 400 QUERY_REQUIRED; 101 terms: 400 TOO_MANY_TERMS; a definition
    parameter, seek or includeTotal: 400 PARAMETER_NOT_SUPPORTED; a two-character term matches
    exactly only."""
    _ledger(world, "Qz", "QZ-1")
    _ledger(world, "Qz long", "QZ-2")

    refused(consumer_xref(world), 400, "QUERY_REQUIRED")
    refused(consumer_xref_typed(world, "query=,,"), 400, "QUERY_REQUIRED")
    refused(consumer_xref(world, query=""), 400, "QUERY_REQUIRED")
    terms = ",".join(f"T{number}" for number in range(101))
    error = refused(consumer_xref_typed(world, f"query={terms}"), 400, "TOO_MANY_TERMS")
    assert "100" in error["message"]
    assert _typed(world, "query=" + ",".join(f"T{number}" for number in range(100)))["results"] == []

    for name, value in ((world.key("Capi.token"), "x"), ("seek", "1"), ("includeTotal", "true")):
        error = refused(consumer_xref(world, query="qz", **{name: value}), 400, "PARAMETER_NOT_SUPPORTED")
        assert error["details"]["parameters"] == [name]

    assert _scored(world, _xref(world, query="qz")) == [("Qz", 200)]
