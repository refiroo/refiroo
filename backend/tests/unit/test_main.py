"""``main.py``: the application the service builds from its settings.

J12.7 starts the service with integration jobs off and finds no route that creates or cancels a
job. Here the same setting leaves the application without a job worker, so a job queued before the
setting was turned off is not run either.
"""

import pytest

from app.config import reload_settings
from app.main import create_app


@pytest.mark.parametrize("enabled", ["true", "false"])
def test_the_job_worker_exists_only_with_integration_jobs(monkeypatch, enabled):
    monkeypatch.setenv("INTEGRATION_JOBS_ENABLED", enabled)
    reload_settings()
    try:
        assert (create_app().state.job_worker is not None) == (enabled == "true")
    finally:
        monkeypatch.undo()
        reload_settings()
