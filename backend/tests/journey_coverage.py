"""The pytest plugin of the recording run (``python -m tests.journey_trace --record``, TS4).

Coverage.py records which app lines each test executes, one dynamic context per test (its node ID),
into the folder ``RDM_JOURNEY_COVERAGE`` names; without that variable the plugin does nothing, so no
ordinary run loads it. The C tracer is used: Python 3.14's default ``sys.monitoring`` core lost the
lines that run in the TestClient's request threads (an API test recorded 5-13 of its 38-66 modules).
Each pytest process (the run's own, every ``-n`` worker) writes a data file of its own there.
"""

import os
from pathlib import Path

import pytest

_FOLDER = os.environ.get("RDM_JOURNEY_COVERAGE")
_COVERAGE = None

if _FOLDER:
    os.environ["COVERAGE_CORE"] = "ctrace"
    import coverage

    _COVERAGE = coverage.Coverage(
        data_file=str(Path(_FOLDER) / "coverage"),
        data_suffix=True,
        source=[str(Path(__file__).resolve().parents[1] / "app")],
        config_file=False,
    )
    _COVERAGE.start()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if _COVERAGE is None:
        return (yield)
    _COVERAGE.switch_context(item.nodeid)
    try:
        return (yield)
    finally:
        _COVERAGE.switch_context("")


def pytest_unconfigure(config):
    if _COVERAGE is not None:
        _COVERAGE.stop()
        _COVERAGE.save()
