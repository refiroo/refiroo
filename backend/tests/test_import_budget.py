"""Base 0.9 J3 budget (D88): a 10,000-row XLSX preview and a 100,000-row XLSX execution, live, on the
Track S volume fixture.

Each file holds one item per row: an item keyed by its unique code, with a name, a rank and its group
matched by name, so the 100,000-row file is a 100,000-item job. The application's worker is stopped
and a test worker runs the job, binding included; the time is from the first claim to the job's
end. Bounds: the preview under 30 s, the execution under 2 minutes. Basis: the 100,000-item batch
took 52 s live (PG5) and J2a's triggers add 0.1–0.2 s per 500-item chunk. A miss is reported with
its cause before anything is tuned. Measured once, at the package and at a release's acceptance.
"""

import io
import json
import time

import pytest
from openpyxl import Workbook
from test_batch_volume import SHAPE
from test_import_volume import _groups, _profile
from volume_fixture import WORKSPACE, volume_app

PREVIEW_ROWS, PREVIEW_SECONDS = 10_000, 30.0
EXECUTE_ROWS, EXECUTE_SECONDS = 100_000, 120.0


def _workbook(rows: int, group_name: str) -> bytes:
    book = Workbook(write_only=True)
    sheet = book.create_sheet("Items")
    sheet.append(["Code", "Name", "Rank", "Group", "Cites"])
    for n in range(rows):
        sheet.append([f"BUD-{rows}-{n:06d}", f"Budget {n}", n % 90, group_name, None])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    results = {}
    with volume_app(tmp_path_factory.mktemp("import-budget"), SHAPE) as (client, _dataset):
        worker = client.app.state.job_worker
        worker.stop()
        response = client.post("/api/v1/import-profiles", json=_profile())
        assert response.status_code == 201, response.text
        group_name, _codes = _groups(client)
        for stage, rows in (("preview", PREVIEW_ROWS), ("execute", EXECUTE_ROWS)):
            request = {
                "workspaceKey": WORKSPACE,
                "profileKey": "volume-items",
                "policy": "independent",
                "onExisting": "overwrite",
                "stage": stage,
            }
            content = _workbook(rows, group_name)
            queued = client.post(
                "/api/v1/imports",
                files={"file": ("items.xlsx", content, "application/octet-stream")},
                data={"request": json.dumps(request)},
            )
            assert queued.status_code == 202, queued.text
            job_url = f"/api/v1/jobs/{queued.json()['id']}"
            started = time.perf_counter()
            assert worker.run_once()
            bound = time.perf_counter() - started
            worker.run_until_idle()
            seconds = time.perf_counter() - started
            job = client.get(job_url).json()
            results[stage] = {"rows": rows, "bound": bound, "seconds": seconds, "job": job}
            print(
                f"\nJ3 {stage}: {rows} rows ({len(content) / 1e6:.1f} MB), binding {bound:.1f} s, "
                f"in all {seconds:.1f} s ({rows / max(seconds, 0.001):.0f} rows/s), "
                f"state {job['state']}"
            )
    return results


def test_a_10000_row_preview_runs_within_its_budget(measured):
    result = measured["preview"]
    job = result["job"]
    assert job["state"] == "awaiting_confirmation", job["error"]
    assert job["preview"]["coverage"] == "complete"
    assert job["preview"]["counts"]["created"] == PREVIEW_ROWS
    assert result["seconds"] < PREVIEW_SECONDS, result


def test_a_100000_row_execution_runs_within_its_budget(measured):
    result = measured["execute"]
    job = result["job"]
    assert job["state"] == "completed" and job["result"] == "applied", job["error"]
    assert job["counts"]["created"] == EXECUTE_ROWS
    assert result["seconds"] < EXECUTE_SECONDS, result
