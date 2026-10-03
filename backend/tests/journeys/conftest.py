"""Journey tests run on two model configurations each (``configurations.choose``).

A test names the structures it uses with ``@pytest.mark.structures("R", "Bown", …)`` and takes the
``world`` fixture; it then runs on generated A, and on the example model when the example holds every
named structure, otherwise on generated B.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from configurations import choose
from scenario import world_for


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "structures(*names): the model structures a journey test uses (configurations.py)",
    )
    config.addinivalue_line(
        "markers", "settings(**values): settings the journey application starts with (scenario.py)"
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """``world`` is a configuration's seeded world; ``configuration`` the configuration alone, for a
    test that starts the service itself (J12)."""
    names = tuple(n for m in metafunc.definition.iter_markers("structures") for n in m.args)
    for argument in ("world", "configuration"):
        if argument in metafunc.fixturenames:
            configurations = choose(names)
            metafunc.parametrize(
                argument,
                configurations,
                ids=[c.name for c in configurations],
                indirect=argument == "world",
            )
            return


@pytest.fixture
def world(request):
    marker = request.node.get_closest_marker("settings")
    with world_for(request.param, marker.kwargs if marker else None) as world:
        yield world
