"""Base 0.9 J2: binding an import holds its statements as the file grows (D68).

A CSV file of items keyed by their unique code, each under a group matched by name and citing groups
matched by code through a split cell, is imported into the volume seed's workspace at two sizes,
four times apart. Binding the file (the worker's first step: the rows copied in, keys, matches and
order resolved and the items built by set statements) must execute the same statements at both
sizes and load no record into the ORM: the job only. Applying the items is the batch path's, whose
budgets are its own (B1–B3).

0.9 J3: the same files previewed first, before any execution. The preview's step (every item run in
one transaction rolled back, then the outcomes and summary recorded) is one call of the batch path,
which pages its bulk statements (lookups, inserts, audit subjects, outcomes) about 1,000 rows at a
time and looks for a cancel request every ``STOP_CHECK_ITEMS`` items: its statements grow by those
pages only, and it loads no record into the ORM beyond the job's context.
"""

import csv
import io
import json

import pytest
from volume_fixture import CODE, RANK, WORKSPACE, measure, scaled_shape, volume_app

from app.db import get_engine
from app.engine.jobs.batches import STOP_CHECK_ITEMS

SHAPE = scaled_shape(0.01)
SIZES = (500, 2_000)
# The job, read by the worker's claim and by its binding.
ORM_ROWS = 4
# The preview's context too: the workspace, the runtime state and release, and the parents' records.
PREVIEW_ORM_ROWS = 8
# The batch path's statements paged by about 1,000 rows, measured at 0.9 J3 as about ten per 1,000
# items: relation and record lookups, record, relationship, value and audit inserts, audit
# subjects, relation set versions, outcomes.
PAGED_STATEMENTS = 10
# A stop check renews the job's lease in a short transaction of its own (0.9 R-F12): the job row
# locked, its lease moved on.
CHECK_STATEMENTS = 2


def _profile():
    by_code = {"attributeTypeKey": CODE}
    return {
        "key": "volume-items",
        "name": "Volume items",
        "sources": [
            {
                "applicationKey": "vol-catalogue",
                "objectTypeKey": "vol-item",
                "key": {"attributeTypeKey": CODE},
                "columns": [
                    {"column": "Code", "attributeTypeKey": CODE},
                    {"column": "Name", "field": "name"},
                    {"column": "Rank", "attributeTypeKey": RANK},
                    {
                        "column": "Group",
                        "parent": {"objectTypeKey": "vol-group", "matchBy": {"field": "name"}},
                    },
                    {
                        "column": "Cites",
                        "relation": {
                            "relationTypeKey": "vol-item-cites-group",
                            "objectTypeKey": "vol-group",
                            "matchBy": by_code,
                            "split": ";",
                        },
                    },
                ],
            }
        ],
    }


def _groups(client):
    page = client.get(
        "/api/v1/objects/vol-group", params={"workspaceKey": WORKSPACE, "pageSize": 3}
    ).json()["items"]
    codes = [
        next(
            a["value"]
            for a in client.get(
                f"/api/v1/objects/vol-group/{g['id']}", params={"workspaceKey": WORKSPACE}
            ).json()["attributes"]
            if a["attributeTypeKey"] == CODE
        )
        for g in page
    ]
    return page[0]["name"], codes


def _file(rows, group_name, codes):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Code", "Name", "Rank", "Group", "Cites"])
    for n in range(rows):
        writer.writerow(
            [f"IMP-{rows}-{n}", f"Imported {n}", n % 90, group_name, ";".join(codes[:2])]
        )
    return buffer.getvalue().encode()


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    with volume_app(tmp_path_factory.mktemp("imports"), SHAPE) as (client, _dataset):
        worker = client.app.state.job_worker
        worker.stop()
        response = client.post("/api/v1/import-profiles", json=_profile())
        assert response.status_code == 201, response.text
        group_name, codes = _groups(client)
        results = {}
        for rows in SIZES:
            preview = {
                "workspaceKey": WORKSPACE,
                "profileKey": "volume-items",
                "policy": "independent",
                "onExisting": "overwrite",
                "stage": "preview",
            }
            queued = client.post(
                "/api/v1/imports",
                files={"file": ("items.csv", _file(rows, group_name, codes), "text/csv")},
                data={"request": json.dumps(preview)},
            )
            assert queued.status_code == 202, queued.text
            assert worker.run_once()
            with measure(get_engine()) as cost:
                assert worker.run_once()
            waiting = client.get(f"/api/v1/jobs/{queued.json()['id']}").json()
            results[("preview", rows)] = (cost, waiting)
        for rows in SIZES:
            request = {
                "workspaceKey": WORKSPACE,
                "profileKey": "volume-items",
                "policy": "independent",
                "onExisting": "overwrite",
                "stage": "execute",
            }
            queued = client.post(
                "/api/v1/imports",
                files={"file": ("items.csv", _file(rows, group_name, codes), "text/csv")},
                data={"request": json.dumps(request)},
            )
            assert queued.status_code == 202, queued.text
            with measure(get_engine()) as cost:
                assert worker.run_once()
            bound = client.get(f"/api/v1/jobs/{queued.json()['id']}").json()
            worker.run_until_idle()
            done = client.get(f"/api/v1/jobs/{queued.json()['id']}").json()
            results[rows] = (cost, bound, done)
        return results


def test_the_preview_grows_only_by_its_paged_statements_and_cancel_checks(measured):
    (few, small), (many, large) = measured[("preview", SIZES[0])], measured[("preview", SIZES[1])]
    for rows, waiting in ((SIZES[0], small), (SIZES[1], large)):
        assert waiting["state"] == "awaiting_confirmation", waiting["error"]
        preview = waiting["preview"]
        assert preview["coverage"] == "complete" and preview["counts"]["created"] == rows * 3
    few_items, many_items = SIZES[0] * 3, SIZES[1] * 3
    checks = many_items // STOP_CHECK_ITEMS - few_items // STOP_CHECK_ITEMS
    pages = -(-many_items // 1_000) - -(-few_items // 1_000)
    assert (
        many.statements - few.statements <= CHECK_STATEMENTS * checks + PAGED_STATEMENTS * pages
    ), (few, many)
    assert max(few.rows_loaded, many.rows_loaded) <= PREVIEW_ORM_ROWS, (few, many)


def test_binding_holds_its_statements_as_the_file_grows(measured):
    (few, *small), (many, *large) = measured[SIZES[0]], measured[SIZES[1]]
    for rows, (bound, done) in ((SIZES[0], small), (SIZES[1], large)):
        assert bound["stage"] == "applying" and bound["counts"]["rejected"] == 0, bound["error"]
        # One upsert per row, and the two relationships of each row's split cell.
        assert bound["progress"]["total"] == rows * 3, bound["progress"]
        assert done["result"] == "applied" and done["counts"]["created"] == rows * 3, done["counts"]
    assert few.statements == many.statements, (few, many)
    assert max(few.rows_loaded, many.rows_loaded) <= ORM_ROWS, (few, many)
