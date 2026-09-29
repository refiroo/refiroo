"""Base 0.8 C2: the restructuring planner holds its budget as the subtree grows (D41).

The heavy group moves under the small group as a node, so it and each of its items change type
(:func:`volume_baseline.restructuring_scenarios`); the dataset and so the subtree grow fourfold
between the two scales, both within the 500-record limit (D41, D44). Planning reads level by level,
so its statements do not grow with the records, and it materialises no rows per record. The
preview's dry run writes each record through the change set services, so its statements grow with
the records, at the same cost per record at both scales. The wall time near the limit comes from
``volume_baseline.py --only-restructuring --scale 0.024`` and is recorded in the Base 0.8 plan.
"""

import pytest
from volume_baseline import restructuring_scenarios
from volume_fixture import scaled_shape, volume_app

from app.db import get_engine
from app.engine.operations.restructuring import RECORD_LIMIT

# The heavy group holds 100 and 400 items: a fourfold subtree, below the limit at both scales.
SMALL, LARGE = scaled_shape(0.005), scaled_shape(0.02)


@pytest.fixture(scope="module")
def measured(_migrated_template, tmp_path_factory) -> dict[str, object]:
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        directory = tmp_path_factory.mktemp(f"restructuring-{label}")
        with volume_app(_migrated_template, directory, shape) as (_client, dataset):
            (plan, preview), count = restructuring_scenarios(get_engine(), dataset, repeat=0)
            results[label] = {"plan": plan, "preview": preview, "records": count}
    return results


def test_the_plan_covers_the_subtree(measured):
    small, large = measured["small"], measured["large"]
    assert large["records"] <= RECORD_LIMIT
    # The group and each of its items; the items of the larger shape are four times as many.
    assert SMALL.heavy_items * 0.9 < small["records"] <= SMALL.heavy_items + 1
    assert LARGE.heavy_items * 0.9 < large["records"] <= LARGE.heavy_items + 1


def test_planning_reads_level_by_level(measured):
    small, large = measured["small"], measured["large"]
    # A subtree within the limit is read in one chunk per level at either scale.
    assert large["plan"].statements == small["plan"].statements
    assert small["plan"].statements <= 40
    for item in (small, large):
        assert item["plan"].rows_loaded <= 5


def test_the_dry_run_costs_the_same_per_record(measured):
    small, large = measured["small"], measured["large"]
    per_record = {
        label: item["preview"].statements / item["records"] for label, item in (("small", small), ("large", large))
    }
    assert per_record["large"] <= per_record["small"] * 1.05, per_record
