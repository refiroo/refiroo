"""Base 0.9 C4 and C5: XREF lookups hold the read budgets as the dataset grows.

An item's code in another case, the cited group's code (its own match and the citing items it
promotes), a 4-character contains, ``expect=one``, the cited group's code narrowed to the heavy group
and with the ``scoresFrom`` parameter (C5), and a term in every item refused as ``QUERY_TOO_BROAD``
must each execute the same statements when the dataset grows fourfold, and load
at most ``ROWS_PER_LISTED_ROW`` ORM rows per listed row. Wall times at full volume come from
``volume_baseline.py --only-consumer`` and are recorded in the Base 0.9 plan.

The test shapes hold at most 4,000 items, below the 10,000 records a query may match, so the limit is
lowered to 500 here: the refusal's statements are the same whatever the limit, and at full volume the
baseline meets the real one.
"""

import pytest
from test_volume_baseline import LARGE, ROWS_PER_LISTED_ROW, SMALL
from volume_baseline import PAGE_SIZE, consumer_xref_scenarios
from volume_fixture import volume_app

from app.db import get_engine
from app.engine.reads import consumer_xref


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, list]:
    results = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(consumer_xref, "MATCH_LIMIT", 500)
        for label, shape in (("small", SMALL), ("large", LARGE)):
            with volume_app(tmp_path_factory.mktemp(f"xref-{label}"), shape) as (client, dataset):
                results[label] = consumer_xref_scenarios(client, get_engine(), dataset, repeat=0)
    return results


def test_xref_holds_the_budgets_as_the_data_grows(measured):
    large = {item.scenario: item for item in measured["large"]}
    failures = []
    for small in measured["small"]:
        other = large[small.scenario]
        if (small.status, small.statements) != (other.status, other.statements):
            failures.append(
                f"{small.scenario}: status {small.status} → {other.status},"
                f" statements {small.statements} → {other.statements}"
            )
        if max(small.rows_loaded, other.rows_loaded) > ROWS_PER_LISTED_ROW * PAGE_SIZE:
            failures.append(f"{small.scenario}: rows {small.rows_loaded} → {other.rows_loaded}")
    assert not failures
    assert [item.status for item in measured["small"]] == [200, 200, 200, 200, 200, 200, 400]
