"""J23 — Answer a business-date question (USER_JOURNEYS.md).

E declares an effective period over two date attributes (start inclusive, end exclusive); F binds
the same attributes and declares none. Each test creates the records it asks about. J23.6–J23.8 ask
through the consumer API (Base 0.9 C16), where ``Capi`` exposes E as ``Rate`` and F as ``Fee``.
"""

import copy

import pytest
from scenario import (
    W1,
    consumer_list,
    consumer_object,
    consumer_publications,
    consumer_resolve,
    consumer_xref,
    ok,
    refused,
)

DATED = ("E", "E.from", "E.to", "K.code", "F")
CONSUMER = (*DATED, "R", "Capi")
APPLIED = "RDM-As-Of-Applied"


def _dated(world, name, start=None, end=None, **kwargs):
    values = {}
    if start:
        values["E.from"] = start
    if end:
        values["E.to"] = end
    return world.made(kwargs.pop("structure", "E"), name, values=values, **kwargs)


def _list(world, structure="E", **params):
    return world.api.get(f"/objects/{world.key(structure)}", **params)


def _walk(world, **params):
    """Every page of E at one page a record, by its cursors."""
    names, cursor = [], None
    while True:
        page = ok(_list(world, pageSize=1, cursor=cursor, **params))
        names += world.names(page)
        cursor = page.get("nextCursor")
        if not cursor:
            return names


def _replacement_pair(world):
    """An old record ending 2026-07-01, its replacement from that day, one valid always and one
    starting next year."""
    return {
        "old": _dated(world, "Old rate", end="2026-07-01"),
        "new": _dated(world, "New rate", start="2026-07-01"),
        "always": _dated(world, "Standing rate"),
        "future": _dated(world, "Future rate", start="2027-01-01"),
    }


@pytest.mark.journey("J23")
@pytest.mark.structures(*DATED)
def test_records_applicable_on_a_date_page_by_page(world):
    """When the dated type is listed for a date one record a page, following cursors, and a cursor is
    reused with another date or none. Then every page answers for that date: the old record and the
    standing one, not the replacement or the future one; the reused cursors are refused. A date on a
    type without a period, a date on the cross-type lookup and an impossible date are refused."""
    _replacement_pair(world)
    assert sorted(_walk(world, asOf="2026-06-30")) == ["Old rate", "Standing rate"]

    cursor = ok(_list(world, pageSize=1, asOf="2026-06-30"))["nextCursor"]
    refused(_list(world, pageSize=1, cursor=cursor, asOf="2026-07-02"), 422, "INVALID_CURSOR")
    refused(_list(world, pageSize=1, cursor=cursor), 422, "INVALID_CURSOR")

    error = refused(_list(world, "F", asOf="2026-06-30"), 422, "AS_OF_NOT_SUPPORTED")
    assert error["details"]["path"] == "/query/asOf"
    assert error["details"]["objectTypeKey"] == world.key("F")
    error = refused(world.api.get("/objects", asOf="2026-06-30"), 422, "AS_OF_NOT_SUPPORTED")
    assert error["details"]["route"].endswith("/api/v1/objects/{objectTypeKey}")
    refused(_list(world, asOf="2026-02-30"), 422, "REQUEST_VALIDATION_ERROR")
    query = {"objectTypeKey": world.key("E"), "asOf": "2026-02-30"}
    error = refused(
        world.api.post(f"/workspaces/{W1}/queries/objects", query), 422, "INVALID_QUERY"
    )
    assert error["details"]["path"] == "/asOf"


@pytest.mark.journey("J23.1")
@pytest.mark.structures(*DATED)
def test_the_boundary_day_itself(world):
    """When the dated type is listed for the day the replacement starts. Then the replacement (its
    start counts) and the standing record, not the old one (its end does not)."""
    _replacement_pair(world)
    assert sorted(_walk(world, asOf="2026-07-01")) == ["New rate", "Standing rate"]


@pytest.mark.journey("J23.2")
@pytest.mark.structures(*DATED)
def test_overlapping_periods(world):
    """Given two records whose periods overlap, both accepted. When the type is listed for a date
    inside both. Then both."""
    _dated(world, "Spring band", "2026-03-01", "2026-09-01")
    _dated(world, "Summer band", "2026-05-01", "2026-10-01")
    assert sorted(_walk(world, asOf="2026-06-15")) == ["Spring band", "Summer band"]
    assert _walk(world, asOf="2026-09-15") == ["Summer band"]


@pytest.mark.journey("J23.3")
@pytest.mark.structures(*DATED, "Bee")
def test_dated_reads_in_a_change_set_a_publication_and_a_query(world):
    """Given the replacement pair published, then a change set extending the old record. When the
    type is listed for a date in the change set, in the publication, and live; the publication
    without a date; and a query for a date whose hop reaches a record not effective then. Then each
    context answers by its own values, the undated publication read lists every record, and the
    query dates the queried records only."""
    records = _replacement_pair(world)
    publication = world.publish(world.change_set())
    cs = world.change_set()
    old = world.record("E", records["old"]["id"], changeSetId=cs["id"])
    staged = {
        "expectedVersion": old["version"],
        "attributes": [{"attributeTypeKey": world.key("E.to"), "value": "2026-08-01"}],
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('E')}/{old['id']}", staged))

    day = "2026-07-15"
    assert sorted(_walk(world, asOf=day, changeSetId=cs["id"])) == [
        "New rate",
        "Old rate",
        "Standing rate",
    ]
    assert sorted(_walk(world, asOf=day, publicationId=publication["id"])) == [
        "New rate",
        "Standing rate",
    ]
    assert sorted(_walk(world, asOf=day)) == ["New rate", "Standing rate"]
    assert len(_walk(world, publicationId=publication["id"])) == 4

    ok(world.relate("Bee", records["old"]["id"], records["future"]["id"]), 201)
    query = {
        "objectTypeKey": world.key("E"),
        "asOf": "2026-06-30",
        "where": [
            {
                "related": {
                    "relationTypeKey": world.key("Bee"),
                    "direction": "outgoing",
                    "where": [{"field": "name", "op": "eq", "value": "Future rate"}],
                }
            }
        ],
        "expand": [{"relationTypeKey": world.key("Bee"), "direction": "outgoing"}],
    }
    [item] = ok(world.api.post(f"/workspaces/{W1}/queries/objects", query))["items"]
    assert item["id"] == records["old"]["id"]
    assert [i["object"]["name"] for i in item["expanded"][0]["items"]] == ["Future rate"]


@pytest.mark.journey("J23.4")
@pytest.mark.structures(*DATED)
def test_a_period_that_does_not_end_after_it_starts_is_refused(world):
    """When a dated record is created ending the day it starts, an update sets only an end before the
    stored start, the end alone is changed the same way, and the create is staged in a change set.
    Then each is refused naming both attributes and both dates, and nothing changes."""
    start, end = world.key("E.from"), world.key("E.to")

    def assert_period_refused(response, first, last):
        details = refused(response, 422, "INVALID_EFFECTIVE_PERIOD")["details"]
        assert (details["startAttributeTypeKey"], details["endAttributeTypeKey"]) == (start, end)
        assert (details["start"], details["end"]) == (first, last)

    assert_period_refused(
        world.create("E", "Empty", values={"E.from": "2026-05-01", "E.to": "2026-05-01"}),
        "2026-05-01",
        "2026-05-01",
    )
    record = _dated(world, "Kept", "2026-05-01", "2026-07-01")
    assert_period_refused(
        world.update("E", record["id"], record["version"], values={"E.to": "2026-04-01"}),
        "2026-05-01",
        "2026-04-01",
    )
    value = {"value": "2026-04-01", "expectedVersion": record["version"]}
    assert_period_refused(
        world.api.patch(f"/objects/{world.key('E')}/{record['id']}/attributes/{end}", value),
        "2026-05-01",
        "2026-04-01",
    )
    cs = world.change_set()
    assert_period_refused(
        world.create(
            "E", "Staged", values={"E.from": "2026-05-01", "E.to": "2026-04-01"}, change_set=cs
        ),
        "2026-05-01",
        "2026-04-01",
    )
    assert world.record("E", record["id"])["version"] == record["version"]
    assert world.current(cs)["version"] == cs["version"]
    assert ok(_list(world, includeTotal=True))["totalCount"] == 1


@pytest.mark.journey("J23.5")
@pytest.mark.structures(*DATED)
def test_a_model_adding_or_removing_a_period(world):
    """Given F records whose end is not after their start, and a release declaring a period on F.
    When it is activated; then the records are corrected and it is activated; then a release removing
    E's period is activated. Then the first is refused naming the period's records and their count;
    the second activates and F answers dates; after the third, a date on E is refused and E's values
    are unchanged."""
    inverted = [
        _dated(world, f"Inverted {n}", "2026-09-01", "2026-08-01", structure="F") for n in range(2)
    ]
    _dated(world, "Fine", "2026-01-01", "2026-12-31", structure="F")
    kept = _dated(world, "Dated", "2026-01-01", "2026-02-01")

    model = copy.deepcopy(world.configuration.model)
    f_type = next(t for t in model["objectTypes"] if t["key"] == world.key("F"))
    f_type["effectivePeriod"] = {
        "startAttributeTypeKey": world.key("E.from"),
        "endAttributeTypeKey": world.key("E.to"),
    }
    model["release"]["version"] += "-dated"
    release = world.install(model)["id"]
    details = refused(world.activate(release), 409, "MODEL_MIGRATION_REQUIRED")["details"]
    [diagnostic] = [d for d in details if d["code"] == "INVALID_EFFECTIVE_PERIOD"]
    assert world.key("F") in diagnostic["path"] and diagnostic["count"] == 2

    for record in inverted:
        ok(world.update("F", record["id"], record["version"], values={"E.to": "2026-10-01"}))
    ok(world.activate(release))
    dated = ok(_list(world, "F", asOf="2026-09-15", pageSize=100))
    assert sorted(world.names(dated)) == ["Fine", "Inverted 0", "Inverted 1"]

    e_type = next(t for t in model["objectTypes"] if t["key"] == world.key("E"))
    del e_type["effectivePeriod"]
    # Capi exposes E: removing its period is a consumer contract break (Q4), so a new version.
    for definition in model.get("consumerApis", []):
        definition["contractVersion"] += 1
    model["release"]["version"] += "-undated"
    ok(world.activate(world.install(model)["id"]))
    refused(_list(world, asOf="2026-01-15"), 422, "AS_OF_NOT_SUPPORTED")
    after = world.record("E", kept["id"])
    assert (world.value(after, "E.from"), world.value(after, "E.to")) == (
        "2026-01-01",
        "2026-02-01",
    )
    assert after["version"] == kept["version"]


# --- the consumer API (C16) -----------------------------------------------------------------------


def _consumer_rates(world):
    """J23's replacement pair, and a transitional rate overlapping the boundary."""
    records = _replacement_pair(world)
    records["transitional"] = _dated(world, "Transitional rate", "2026-06-15", "2026-07-15")
    return records


def _named(world, items):
    return sorted(item[world.key("Capi.name")] for item in items)


def _rates_walk(world, **params):
    """Every page of the consumer list ``rates`` at one record a page, by its cursors, each page
    naming the dated type."""
    names, cursor = [], None
    while True:
        response = consumer_list(world, world.key("Capi.rates"), pageSize=1, cursor=cursor, **params)
        page = ok(response)
        assert page["asOfApplied"] == [world.key("Capi.E")]
        assert response.headers[APPLIED] == world.key("Capi.E")
        names += [item[world.key("Capi.name")] for item in page["items"]]
        cursor = page["nextCursor"]
        if not cursor:
            return sorted(names)


@pytest.mark.journey("J23.6")
@pytest.mark.structures(*CONSUMER)
def test_a_consumer_list_on_a_date_page_by_page(world):
    """When the consumer list of the dated type is read for a date one record a page, on either
    side of the boundary, and a cursor is reused with another date or none. Then every page answers
    for that date and names the dated type; the reused cursors are refused; the list of the undated
    type refuses a date, naming it."""
    _consumer_rates(world)
    assert _rates_walk(world, asOf="2026-06-30") == ["Old rate", "Standing rate", "Transitional rate"]
    assert _rates_walk(world, asOf="2026-07-01") == ["New rate", "Standing rate", "Transitional rate"]

    rates = world.key("Capi.rates")
    cursor = ok(consumer_list(world, rates, pageSize=1, asOf="2026-06-30"))["nextCursor"]
    refused(consumer_list(world, rates, pageSize=1, cursor=cursor, asOf="2026-07-02"), 400, "INVALID_CURSOR")
    refused(consumer_list(world, rates, pageSize=1, cursor=cursor), 400, "INVALID_CURSOR")
    undated = ok(consumer_list(world, rates, pageSize=100))
    assert "asOfApplied" not in undated and len(undated["items"]) == 5

    error = refused(consumer_list(world, world.key("Capi.fees"), asOf="2026-06-30"), 400, "AS_OF_NOT_SUPPORTED")
    assert error["details"] == {"objectTypes": [world.key("Capi.F")], "path": "/query/asOf"}


@pytest.mark.journey("J23.6")
@pytest.mark.structures(*CONSUMER)
def test_a_consumer_object_on_a_date(world):
    """When records are read by ID with a date and without. Then a dated record answers on a day its
    period holds and is not found on another; a record of the undated type refuses the date; an
    unknown ID is not found; without a date every record answers and no header names a dated type."""
    records = _consumer_rates(world)
    fee = _dated(world, "Flat rate", structure="F")
    old = records["old"]["id"]

    response = consumer_object(world, old, asOf="2026-06-30")
    assert ok(response)[world.key("Capi.name")] == "Old rate"
    assert response.headers[APPLIED] == world.key("Capi.E")
    refused(consumer_object(world, old, asOf="2026-07-01"), 404, "OBJECT_NOT_FOUND")
    error = refused(consumer_object(world, fee["id"], asOf="2026-06-30"), 400, "AS_OF_NOT_SUPPORTED")
    assert error["details"]["objectTypes"] == [world.key("Capi.F")]
    refused(consumer_object(world, "no-such-record", asOf="2026-06-30"), 404, "OBJECT_NOT_FOUND")

    for record in (records["old"], records["new"], records["future"], fee):
        response = consumer_object(world, record["id"])
        ok(response)
        assert APPLIED not in response.headers


@pytest.mark.journey("J23.6", "J23.3")
@pytest.mark.structures(*CONSUMER)
def test_a_consumer_list_on_a_date_in_a_publication(world):
    """Given the rates published, then the new rate's start moved live a month later. When the list
    is read for a date between, pinned to the publication and live. Then each answers by its own
    values."""
    records = _consumer_rates(world)
    world.publish(world.change_set())
    new = records["new"]
    ok(world.update("E", new["id"], new["version"], values={"E.from": "2026-08-01"}))

    rates = world.key("Capi.rates")
    pinned = ok(consumer_list(world, rates, publication="latest", asOf="2026-07-15", pageSize=100))
    live = ok(consumer_list(world, rates, asOf="2026-07-15", pageSize=100))
    assert "New rate" in _named(world, pinned["items"])
    assert "New rate" not in _named(world, live["items"])


@pytest.mark.journey("J23.7")
@pytest.mark.structures(*CONSUMER)
def test_a_lookup_across_dated_and_undated_types(world):
    """Given the rates, a fee and a ledger all named with "rate". When looked up for a date. Then
    the rates are filtered by their period, the fee and the ledger are not, scores are those without
    the date, and the answer names the dated type; narrowed to the ledgers alone the date is
    refused; with expect=one the replacement is not found before its first day and found on it."""
    _consumer_rates(world)
    _dated(world, "Flat rate", structure="F")
    world.made("R", "Rate ledger")

    plain = {item[world.key("Capi.name")]: item["matchScore"] for item in ok(consumer_xref(world, query="rate"))["results"]}
    response = consumer_xref(world, query="rate", asOf="2026-06-30")
    dated = ok(response)
    found = {item[world.key("Capi.name")]: item["matchScore"] for item in dated["results"]}
    assert sorted(found) == ["Flat rate", "Old rate", "Rate ledger", "Standing rate", "Transitional rate"]
    assert all(found[name] == plain[name] for name in found)
    assert dated["asOfApplied"] == [world.key("Capi.E")]
    assert response.headers[APPLIED] == world.key("Capi.E")

    error = refused(
        consumer_xref(world, query="rate", asOf="2026-06-30", **{world.key("Capi.kind"): world.key("Capi.R")}),
        400,
        "AS_OF_NOT_SUPPORTED",
    )
    assert error["details"]["objectTypes"] == [world.key("Capi.R")]

    refused(consumer_xref(world, query="New rate", expect="one", asOf="2026-06-30"), 404, "NO_MATCH")
    response = consumer_xref(world, query="New rate", expect="one", asOf="2026-07-01")
    assert ok(response)[world.key("Capi.name")] == "New rate"
    assert response.headers[APPLIED] == world.key("Capi.E")


@pytest.mark.journey("J23.7")
@pytest.mark.structures(*CONSUMER)
def test_a_batch_resolved_on_a_date(world):
    """When a batch is resolved for a date: the old and the new rate by name, the fee and the old
    rate by ID. Then found, not found, rejected for the undated fee, found; each outcome is its
    single read's answer, and the batch names the dated type."""
    records = _consumer_rates(world)
    fee = _dated(world, "Flat rate", structure="F")
    old = records["old"]["id"]
    day = "2026-06-30"
    items = [{"query": "Old rate"}, {"query": "New rate"}, {"id": fee["id"]}, {"id": old}]
    response = consumer_resolve(world, {"items": items}, asOf=day)
    answer = ok(response)
    assert [item["status"] for item in answer["items"]] == ["found", "not_found", "rejected", "found"]
    assert answer["asOfApplied"] == [world.key("Capi.E")]
    assert response.headers[APPLIED] == world.key("Capi.E")
    assert answer["items"][0]["object"] == ok(consumer_xref(world, query="Old rate", expect="one", asOf=day))
    single = refused(consumer_xref(world, query="New rate", expect="one", asOf=day), 404, "NO_MATCH")
    assert answer["items"][1]["error"] == single
    rejected = answer["items"][2]["error"]
    assert rejected["code"] == "AS_OF_NOT_SUPPORTED"
    assert rejected["details"] == {"objectTypes": [world.key("Capi.F")], "pointer": "/items/2/id"}
    assert answer["items"][3]["object"] == ok(consumer_object(world, old, asOf=day))


@pytest.mark.journey("J23.8")
@pytest.mark.structures(*CONSUMER)
def test_consumer_date_refusals(world):
    """When a date is a time, an impossible day or two days, on each read; a date on the publications
    list; and a date inside a batch item or its defaults. Then INVALID_AS_OF at the date, a date the
    publications list does not take, the item rejected and the request refused."""
    record = _dated(world, "Old rate", end="2026-07-01")
    reads = (
        lambda day: consumer_list(world, world.key("Capi.rates"), asOf=day),
        lambda day: consumer_object(world, record["id"], asOf=day),
        lambda day: consumer_xref(world, query="rate", asOf=day),
        lambda day: consumer_resolve(world, {"items": [{"query": "rate"}]}, asOf=day),
    )
    for read in reads:
        for day in ("2026-06-30T00:00", "2026-02-30", "2026-06-30,2026-07-01"):
            error = refused(read(day), 400, "INVALID_AS_OF")
            assert error["details"]["path"] == "/query/asOf"
    refused(consumer_publications(world, asOf="2026-06-30"), 400, "PARAMETER_NOT_SUPPORTED")

    answer = ok(consumer_resolve(world, {"items": [{"query": "Old rate", "asOf": "2026-06-30"}]}))
    [item] = answer["items"]
    assert item["status"] == "rejected" and item["error"]["code"] == "PARAMETER_NOT_SUPPORTED"
    assert item["error"]["details"]["pointer"] == "/items/0/asOf"
    body = {"defaults": {"asOf": "2026-06-30"}, "items": [{"query": "Old rate"}]}
    refused(consumer_resolve(world, body), 400, "PARAMETER_NOT_SUPPORTED")
