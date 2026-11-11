"""Base 0.9 C4, C5 and C14: XREF lookups and batch resolve hold the read budgets as the dataset grows.

An item's code in another case, the cited group's code (its own match and the citing items it
promotes), a 4-character contains, ``expect=one``, the cited group's code narrowed to the heavy group
and with the ``scoresFrom`` parameter (C5), the cited group's code dated by ``asOf`` (C16), and a term in every item refused as ``QUERY_TOO_BROAD``,
live and pinned to the seed's publication (C6a), must each execute the same statements when the dataset grows fourfold, and load
at most ``ROWS_PER_LISTED_ROW`` ORM rows per listed row. Batch resolve (C14) must execute the same
statements for 10 items and for 100, at both sizes: identifiers (codes, promoted codes, misses and a
contains-only term), the same dated (C16), and the same items over three parameter sets. Wall times at full volume come from
``volume_baseline.py --only-consumer`` and are recorded in the Base 0.9 plan.

The test shapes hold at most 4,000 items, below the 10,000 records a query may match, so the limit is
lowered to 500 here: the refusal's statements are the same whatever the limit, and at full volume the
baseline meets the real one. The same lowered limit shows the exact-first rule (C-D52): an
``expect=one`` lookup settled by an exact code is answered although its contains term matches past
the limit, while a lookup that needs contains is refused.
"""

import pytest
from test_volume_baseline import LARGE, ROWS_PER_LISTED_ROW, SMALL
from volume_baseline import (
    CONSUMER_RESOLVE,
    CONSUMER_XREF,
    PAGE_SIZE,
    consumer_resolve_scenarios,
    consumer_xref_scenarios,
)
from volume_fixture import WORKSPACE, volume_app

from app.db import get_engine
from app.engine.reads import consumer_xref

FAMILIES = ("identifiers", "dated identifiers", "three parameter sets")
SIZES = (10, 100)


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, dict]:
    results = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(consumer_xref, "MATCH_LIMIT", 500)
        for label, shape in (("small", SMALL), ("large", LARGE)):
            with volume_app(tmp_path_factory.mktemp(f"xref-{label}"), shape) as (client, dataset):
                engine = get_engine()
                results[label] = {
                    "xref": consumer_xref_scenarios(client, engine, dataset, repeat=0),
                    "resolve": consumer_resolve_scenarios(
                        client, engine, dataset, repeat=0, sizes=SIZES, families=FAMILIES
                    ),
                    "broad": _broad(client),
                }
    return results


def _broad(client) -> dict:
    """An item's exact code beside a term in every item, and that term alone: as one XREF
    ``expect=one``, and as two batch items."""
    code = client.get(
        CONSUMER_XREF, params={"workspace": WORKSPACE, "query": "item", "pageSize": 1}
    )
    assert code.status_code == 400, code.text
    first = client.post(
        CONSUMER_RESOLVE,
        params={"workspace": WORKSPACE},
        json={"items": [{"query": "ITEM-000001"}]},
    )
    one = client.get(
        CONSUMER_XREF,
        params={"workspace": WORKSPACE, "query": ["ITEM-000001", "item"], "expect": "one"},
    )
    batch = client.post(
        CONSUMER_RESOLVE,
        params={"workspace": WORKSPACE},
        json={"items": [{"query": ["ITEM-000001", "item"]}, {"query": "item"}]},
    )
    return {"first": first.json(), "one": (one.status_code, one.json()), "batch": batch.json()}


def _compare(small: list, large: list, rows_per: int) -> list[str]:
    by_scenario = {item.scenario: item for item in large}
    failures = []
    for item in small:
        other = by_scenario[item.scenario]
        if (item.status, item.statements) != (other.status, other.statements):
            failures.append(
                f"{item.scenario}: status {item.status} → {other.status},"
                f" statements {item.statements} → {other.statements}"
            )
        if max(item.rows_loaded, other.rows_loaded) > ROWS_PER_LISTED_ROW * rows_per:
            failures.append(f"{item.scenario}: rows {item.rows_loaded} → {other.rows_loaded}")
    return failures


def test_xref_holds_the_budgets_as_the_data_grows(measured):
    assert not _compare(measured["small"]["xref"], measured["large"]["xref"], PAGE_SIZE)
    assert [item.status for item in measured["small"]["xref"]] == [
        200,
        200,
        200,
        200,
        200,
        200,
        200,
        400,
    ] * 2


def test_batch_resolve_statements_follow_the_parameter_sets_not_the_items(measured):
    assert not _compare(measured["small"]["resolve"], measured["large"]["resolve"], max(SIZES))
    for label in ("small", "large"):
        by_family = {}
        for item in measured[label]["resolve"]:
            assert item.status == 200, item
            by_family.setdefault(item.scenario.split(",")[0], set()).add(item.statements)
        # Ten items or a hundred: the same statements.
        assert all(len(statements) == 1 for statements in by_family.values()), by_family


def test_exact_matches_settle_a_lookup_whatever_its_contains_term_matches(measured):
    for label in ("small", "large"):
        broad = measured[label]["broad"]
        item = broad["first"]["items"][0]["object"]
        status, one = broad["one"]
        assert status == 200 and one == item
        settled, unsettled = broad["batch"]["items"]
        assert settled["object"] == item
        assert (unsettled["status"], unsettled["error"]["code"]) == ("rejected", "QUERY_TOO_BROAD")
        assert unsettled["error"]["details"]["pointer"] == "/items/1/query"
