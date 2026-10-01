"""Base 0.8 P2a: the change lists hold the volume budgets over a large change set.

The review change set touches about a tenth of the catalogue with every kind of change over items
and groups (:func:`volume_fixture.seed_review_change_set`). Each list's first, last, backward,
deep-position, kind-filtered and containment-filtered pages must execute the same statements when
the dataset and the change set grow fourfold, and load at most ``ROWS_PER_LISTED_ROW`` ORM rows per
listed row. Wall times at full volume come from ``volume_baseline.py --only-change-lists`` and are
recorded in the Base 0.8 plan.
"""

import pytest
from test_volume_baseline import LARGE, ROWS_PER_LISTED_ROW, SMALL
from volume_baseline import PAGE_SIZE, change_list_scenarios
from volume_fixture import GROUP, ITEM, seed_review_change_set, volume_app

from app.db import get_engine


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, object]:
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        directory = tmp_path_factory.mktemp(f"change-lists-{label}")
        with volume_app(directory, shape) as (client, dataset):
            review = seed_review_change_set(get_engine(), dataset)
            results[label] = change_list_scenarios(client, get_engine(), review, repeat=0)
            if label == "small":
                results["review"] = review
                results["totals"] = _totals(client, review.change_set_id)
    return results


def _totals(client, change_set_id: str) -> dict[tuple[str, str, str], int]:
    """The number of entries per list, kind and type (or containment), read through the filters."""
    totals = {}
    for kind in ("added", "changed", "removed"):
        for object_type in (ITEM, GROUP):
            body = client.get(
                f"/api/v1/change-sets/{change_set_id}/object-changes",
                params={"kind": kind, "objectTypeKey": object_type, "includeTotal": True, "pageSize": 1},
            ).json()
            totals[("object", kind, object_type)] = body["totalCount"]
        for containment in ("true", "false"):
            body = client.get(
                f"/api/v1/change-sets/{change_set_id}/relation-changes",
                params={"kind": kind, "containment": containment, "includeTotal": True, "pageSize": 1},
            ).json()
            totals[("relation", kind, containment)] = body["totalCount"]
    return totals


def test_change_lists_hold_the_budgets_as_the_change_set_grows(measured):
    large = {item.scenario: item for item in measured["large"]}
    failures = []
    for small in measured["small"]:
        other = large[small.scenario]
        if small.statements != other.statements:
            failures.append(f"{small.scenario}: statements {small.statements} → {other.statements}")
        if max(small.rows_loaded, other.rows_loaded) > ROWS_PER_LISTED_ROW * PAGE_SIZE:
            failures.append(f"{small.scenario}: rows {small.rows_loaded} → {other.rows_loaded}")
    assert not failures
    assert len(measured["small"]) == 11


def test_the_lists_count_what_the_change_set_holds(measured):
    counts, totals = measured["review"].counts, measured["totals"]
    assert totals[("object", "changed", ITEM)] == counts["changed"] + counts["moved"]
    assert totals[("object", "removed", ITEM)] == counts["removed"]
    assert totals[("object", "added", ITEM)] == counts["added"]
    assert totals[("object", "changed", GROUP)] == counts["groupsChanged"]
    assert totals[("object", "added", GROUP)] == counts["groupsAdded"]
    assert totals[("object", "removed", GROUP)] == 0
    # A move removes one containment edge and adds one; a removal removes one.
    assert totals[("relation", "removed", "true")] == counts["moved"] + counts["removed"]
    assert totals[("relation", "added", "true")] == counts["moved"] + counts["added"]
    assert totals[("relation", "changed", "false")] == counts["citationsChanged"]
    assert totals[("relation", "changed", "true")] == 0
    assert sum(value for (records, *_), value in totals.items() if records == "object") == counts["objects"]
    assert sum(value for (records, *_), value in totals.items() if records == "relation") == counts["relations"]
