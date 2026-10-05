"""Base 0.9 C3: consumer list reads hold the read budgets as the dataset grows.

A first page of every item by rank, the next cursor page, a position jump to the middle, the items
under the heavy group (by parent ID) and the items below it through an ancestor parameter with a
total, live and pinned to the seed's publication (C6a), must each execute the same statements when the dataset grows fourfold, and load at most
``ROWS_PER_LISTED_ROW`` ORM rows per listed row. Wall times at full volume come from
``volume_baseline.py --only-consumer`` and are recorded in the Base 0.9 plan.
"""

import pytest
from test_volume_baseline import LARGE, ROWS_PER_LISTED_ROW, SMALL
from volume_baseline import PAGE_SIZE, consumer_scenarios
from volume_fixture import volume_app

from app.db import get_engine


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, list]:
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        with volume_app(tmp_path_factory.mktemp(f"consumer-{label}"), shape) as (client, dataset):
            results[label] = consumer_scenarios(client, get_engine(), dataset, repeat=0)
    return results


def test_consumer_lists_hold_the_budgets_as_the_data_grows(measured):
    large = {item.scenario: item for item in measured["large"]}
    failures = []
    for small in measured["small"]:
        other = large[small.scenario]
        if small.statements != other.statements:
            failures.append(f"{small.scenario}: statements {small.statements} → {other.statements}")
        if max(small.rows_loaded, other.rows_loaded) > ROWS_PER_LISTED_ROW * PAGE_SIZE:
            failures.append(f"{small.scenario}: rows {small.rows_loaded} → {other.rows_loaded}")
    assert not failures
    assert len(measured["small"]) == 10
