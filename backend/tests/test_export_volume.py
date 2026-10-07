"""Base 0.9 J1: an export holds its statements as the data grows (D56).

The whole live workspace of the volume seed, with its relationships, is exported in each format on
the small seed and the one four times larger. Each export must execute the same statements at both
sizes (the records and relationships are written by set statements and streamed, never one
statement per record), except its progress checks, two statements per 10,000 rows written, and
load almost no ORM rows: the job, never the records. The full-size wall
times come from ``volume_baseline.py --only-exports`` and are recorded in POSTGRESQL_BUDGETS.
"""

import pytest
from test_volume_baseline import LARGE, SMALL
from volume_baseline import EXPORT_FORMATS, export_scenarios
from volume_fixture import volume_app

from app.db import get_engine
from app.engine.jobs.exports import CHECK_ROWS

# The job, read by the worker's claim, its checks and its completion.
ORM_ROWS = 10


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        with volume_app(tmp_path_factory.mktemp(f"exports-{label}"), shape) as (client, dataset):
            results[label] = export_scenarios(client, get_engine(), dataset)
    return results


def test_an_export_holds_its_statements_as_the_data_grows(measured):
    small, large = measured["small"], measured["large"]
    assert len(small) == len(large) == len(EXPORT_FORMATS)
    for (before, few), (after, many) in zip(small, large, strict=True):
        checks = 2 * (many // CHECK_ROWS - few // CHECK_ROWS)
        assert after.statements - before.statements == checks, (before, after)
        assert max(before.rows_loaded, after.rows_loaded) <= ORM_ROWS, (before, after)
