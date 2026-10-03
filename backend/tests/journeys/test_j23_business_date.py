"""J23 — Answer a business-date question (USER_JOURNEYS.md).

E declares an effective period over two date attributes (start inclusive, end exclusive); F binds
the same attributes and declares none. Each test creates the records it asks about.
"""

import copy

import pytest
from scenario import W1, ok, refused

DATED = ("E", "E.from", "E.to", "K.code", "F")


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
    refused(_list(world, pageSize=1, cursor=cursor, asOf="2026-07-02"), 422, "invalid_cursor")
    refused(_list(world, pageSize=1, cursor=cursor), 422, "invalid_cursor")

    error = refused(_list(world, "F", asOf="2026-06-30"), 422, "as_of_not_supported")
    assert error["details"]["path"] == "/query/asOf"
    assert error["details"]["objectTypeKey"] == world.key("F")
    error = refused(world.api.get("/objects", asOf="2026-06-30"), 422, "as_of_not_supported")
    assert error["details"]["route"].endswith("/api/v1/objects/{objectTypeKey}")
    refused(_list(world, asOf="2026-02-30"), 422, "request_validation_error")
    query = {"objectTypeKey": world.key("E"), "asOf": "2026-02-30"}
    error = refused(
        world.api.post(f"/workspaces/{W1}/queries/objects", query), 422, "invalid_query"
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
        details = refused(response, 422, "invalid_effective_period")["details"]
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
    details = refused(world.activate(release), 409, "model_migration_required")["details"]
    [diagnostic] = [d for d in details if d["code"] == "invalid_effective_period"]
    assert world.key("F") in diagnostic["path"] and diagnostic["count"] == 2

    for record in inverted:
        ok(world.update("F", record["id"], record["version"], values={"E.to": "2026-10-01"}))
    ok(world.activate(release))
    dated = ok(_list(world, "F", asOf="2026-09-15", pageSize=100))
    assert sorted(world.names(dated)) == ["Fine", "Inverted 0", "Inverted 1"]

    e_type = next(t for t in model["objectTypes"] if t["key"] == world.key("E"))
    del e_type["effectivePeriod"]
    model["release"]["version"] += "-undated"
    ok(world.activate(world.install(model)["id"]))
    refused(_list(world, asOf="2026-01-15"), 422, "as_of_not_supported")
    after = world.record("E", kept["id"])
    assert (world.value(after, "E.from"), world.value(after, "E.to")) == (
        "2026-01-01",
        "2026-02-01",
    )
    assert after["version"] == kept["version"]
