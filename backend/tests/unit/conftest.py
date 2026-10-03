"""Unit tests that need stored data (TEST_HARNESS_PLAN H4d).

A unit test whose code is a query or a write runs the engine directly on a clone of a journey
configuration's ``scenario`` seed (``tests/journeys/scenario.py``): the seed is built once through the
public API and reused, so the data is what a client could produce. ``seeded`` points the engine's
settings at the clone and gives a :class:`~scenario.World` without an API: its model helpers
(``key``, ``app``, ``required_values``) and the seed's record IDs. No application starts; the test
opens sessions with ``app.db.SessionLocal`` and calls the module it tests.
"""

import sys
from collections.abc import Iterator

import layout
import pytest

sys.path.insert(0, str(layout.JOURNEYS))

import seeds
from configurations import all_configurations
from scenario import World, model_path, scenario_seed

# Keys never drive the code these tests reach, so one configuration is enough (H4d); the journey
# tests run each journey on two.
CONFIGURATION = "generated-a"


@pytest.fixture
def seeded() -> Iterator[World]:
    configuration = all_configurations()[CONFIGURATION]
    name = scenario_seed(configuration)
    payload = seeds.ensure(name)
    url = seeds.clone(name)
    try:
        with seeds.application_environment(url, model_path(configuration)):
            yield World(configuration, None, url, dict(payload["ids"]))  # type: ignore[arg-type]
    finally:
        seeds.drop(url.database)
