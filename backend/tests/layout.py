"""Where a test belongs and what it may name (TEST_HARNESS_PLAN H4b, docs/testing/STRATEGY.md).

Two kinds of tests, in two folders:

- ``tests/journeys/``: journey tests. Each carries ``@pytest.mark.journey("J02", "J02.2", …)``
  naming the journeys and variants of ``docs/product-functionality/USER_JOURNEYS.md`` it walks.
- ``tests/unit/``: unit tests. The folders mirror the code under test: ``tests/unit/engine/records/
  test_rules.py`` tests ``app/engine/records/rules.py``; ``tests/unit/harness/test_seeds.py`` tests
  ``tests/seeds.py``. A module may be split as ``test_<module>__<topic>.py``.

Both folders are packages (``__init__.py``), so two unit tests may share a file name in different
folders. The modules directly under ``tests/`` are the suite H4d moves into these folders.
"""

import re
from functools import cache
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BACKEND = TESTS.parent
APP = BACKEND / "app"
CATALOGUE = BACKEND.parent / "docs" / "product-functionality" / "USER_JOURNEYS.md"
JOURNEYS = TESTS / "journeys"
UNIT = TESTS / "unit"
# tests/unit/harness/ mirrors the harness modules in tests/ rather than app/.
HARNESS = "harness"

_JOURNEY = re.compile(r"^### (J\d\d) — (.+)$", re.MULTILINE)
_VARIANT = re.compile(r"\*\*(J\d\d\.\d+) ")


@cache
def journey_ids() -> frozenset[str]:
    """Every journey and variant ID the catalogue defines; a retired journey is not one."""
    text = CATALOGUE.read_text()
    retired = {key for key, title in _JOURNEY.findall(text) if title.strip() == "Retired"}
    journeys = {key for key, _title in _JOURNEY.findall(text)} - retired
    variants = {key for key in _VARIANT.findall(text) if key.split(".")[0] in journeys}
    return frozenset(journeys | variants)


def unknown_journeys(ids: tuple[str, ...]) -> list[str]:
    # The catalogue is read only when a test names journeys.
    return sorted(set(ids) - journey_ids()) if ids else []


def walks(ids: tuple[str, ...], wanted: str) -> bool:
    """True when the IDs name ``wanted`` or, for a journey, any of its variants."""
    return any(key == wanted or key.startswith(f"{wanted}.") for key in ids)


def kind(path: Path) -> str:
    """``journey``, ``unit``, or ``suite`` for a module directly under tests/ (moved in H4d)."""
    resolved = path.resolve()
    if resolved.is_relative_to(JOURNEYS):
        return "journey"
    if resolved.is_relative_to(UNIT):
        return "unit"
    return "suite"


def worker_scope(nodeid: str) -> str:
    """The unit a parallel run sends to one worker (S1, D124): a journey test alone, since its
    ``world`` is a database of its own; any other test with its whole module, which may share module
    fixtures and the worker's session database. ``nodeid`` is relative to the backend folder."""
    module = nodeid.split("::", 1)[0]
    return nodeid if kind(BACKEND / module) == "journey" else module


def unit_target(path: Path) -> Path | None:
    """The module a unit test file tests, or None when its path mirrors no module."""
    relative = path.resolve().relative_to(UNIT)
    name = relative.stem
    if not name.startswith("test_"):
        return None
    module = name.removeprefix("test_").split("__", 1)[0]
    folder = relative.parent
    if folder.parts[:1] == (HARNESS,):
        root, folder = TESTS, Path(*folder.parts[1:])
    else:
        root = APP
    target = root / folder / f"{module}.py"
    return target if target.is_file() else None
