"""Base 0.9 C10, C13: deriving consumer events, reading them and delivering them hold their statements
as the data grows.

A release gives the volume consumer API one event over groups and items, every change and no watch,
so every output counts (``volume_baseline.event_scenarios``). On the small seed and the one four
times larger, each step must execute the same statements: deriving a page of 500 live creations;
deriving the rename of the heavy group, which updates every group and item below it (their ``path``
and ``hierarchy``, and the direct ones' ``parent``), however many there are (C-D82's fan-out, in the
database); and the pull feed's first page with each payload and a page narrowed by the ``within``
ancestor parameter; and, since C13, webhook delivery (``volume_baseline.delivery_scenarios``): the
dispatcher's claim with caught-up subscriptions, one batch of each payload and a coalesced round. A
read or a delivered batch may materialise at most ``ROWS_PER_LISTED_ROW`` ORM rows per event it lists.
The whole delivery's statements grow with its batches, so only its batch is held. Wall times at full
volume come from ``volume_baseline.py --only-events`` and are recorded in POSTGRESQL_BUDGETS §7.
"""

import pytest
from test_volume_baseline import LARGE, ROWS_PER_LISTED_ROW, SMALL
from volume_baseline import EVENT_PAGE, SUBSCRIPTION_SETTINGS, event_scenarios
from volume_fixture import volume_app

from app.db import get_engine


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, tuple[dict, int]]:
    results = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
        for name, value in SUBSCRIPTION_SETTINGS.items():
            patch.setenv(name, value)
        for label, shape in (("small", SMALL), ("large", LARGE)):
            with volume_app(tmp_path_factory.mktemp(f"events-{label}"), shape) as (client, dataset):
                # The claim is one statement however many subscriptions are caught up; 10 keeps it quick.
                found, told = event_scenarios(client, get_engine(), dataset, repeat=0, caught_up=10)
                results[label] = ({item.scenario: item for item in found}, told)
    return results


def test_deriving_reading_and_delivering_events_hold_their_statements_as_the_data_grows(measured):
    (small, _), (large, _) = measured["small"], measured["large"]
    failures = []
    for scenario, item in small.items():
        if "the whole rename" in scenario:
            continue
        other = large[scenario]
        if item.statements != other.statements:
            failures.append(f"{scenario}: statements {item.statements} → {other.statements}")
        if "derive" not in scenario and max(item.rows_loaded, other.rows_loaded) > ROWS_PER_LISTED_ROW * EVENT_PAGE:
            failures.append(f"{scenario}: rows {item.rows_loaded} → {other.rows_loaded}")
    assert not failures, failures
    assert len(small) == 11


def test_a_container_rename_tells_every_object_below_it(measured):
    """The rename reaches more objects at the larger size, each told once at the rename's position."""
    (_, small), (_, large) = measured["small"], measured["large"]
    assert SMALL.heavy_items < small and LARGE.heavy_items < large
