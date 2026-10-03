"""Which code each journey reaches, and which code no journey or no test reaches (H4b).

    .venv/bin/python -m tests.journey_trace           # from the last testmon run's data
    .venv/bin/python -m tests.journey_trace --modules  # also list every module per journey

Every piece of code traces to a journey (docs/testing/STRATEGY.md). The links are not kept by hand:
``pytest --testmon`` records which files each test executed (``backend/.testmondata``), and the
journey markers say which journeys a test walks. A module no journey test reaches is either dead code
or serves a journey nobody wrote down; a module no test reaches at all is untested.

The report is as complete as the testmon data: tests that have not run under ``--testmon`` since
their code changed are missing from it, and it says how many tests the data holds.
"""

import ast
import json
import sqlite3  # testmon's data file, not the engine's database
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Run as a module from backend/ (python -m tests.journey_trace), as seeds.py is.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout

DATA = layout.BACKEND / ".testmondata"
# testmon's schema (pytest-testmon 2.x, pinned in pyproject.toml).
_EXECUTED = """
    SELECT te.test_name, ff.filename
    FROM test_execution te
    JOIN test_execution_file_fp link ON link.test_execution_id = te.id
    JOIN file_fp ff ON ff.id = link.fingerprint_id
"""
_COLLECT = """
import json, sys, pytest

class Journeys:
    def __init__(self):
        self.found = {}
    def pytest_collection_modifyitems(self, items):
        for item in items:
            ids = [key for marker in item.iter_markers("journey") for key in marker.args]
            if ids:
                self.found[item.nodeid] = ids

plugin = Journeys()
code = pytest.main(["--collect-only", "-q", "-p", "no:testmon", "tests/journeys"], plugins=[plugin])
print("JOURNEYS=" + json.dumps(plugin.found))
"""


def executed_files() -> dict[str, set[str]]:
    """Test node ID → the app modules it executed, from the testmon data."""
    if not DATA.exists():
        raise SystemExit(
            f"No testmon data at {DATA}. Run the suite once with --testmon "
            "(python -m pytest -n auto --testmon), then run this report again."
        )
    with sqlite3.connect(DATA) as connection:
        rows = connection.execute(_EXECUTED).fetchall()
    executed: dict[str, set[str]] = defaultdict(set)
    for test, filename in rows:
        if filename.startswith("app/") and filename.endswith(".py"):
            executed[test].add(filename)
    return executed


def journey_tests() -> dict[str, list[str]]:
    """Test node ID → the journeys it walks, by collecting tests/journeys/ in a subprocess."""
    if not any(layout.JOURNEYS.rglob("test_*.py")):
        return {}
    result = subprocess.run(
        [sys.executable, "-c", _COLLECT], cwd=layout.BACKEND, capture_output=True, text=True,
        check=False,
    )
    line = next((row for row in result.stdout.splitlines() if row.startswith("JOURNEYS=")), None)
    if line is None:
        raise SystemExit("Collecting tests/journeys failed:\n" + result.stdout[-2000:] + result.stderr[-2000:])
    return json.loads(line.removeprefix("JOURNEYS="))


def has_functions(module: str) -> bool:
    """A module of declarations only runs at import, before any test, so no test is recorded as
    reaching it; it cannot be traced and is listed apart."""
    tree = ast.parse((layout.BACKEND / module).read_text())
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))


def app_modules() -> set[str]:
    return {
        str(path.relative_to(layout.BACKEND))
        for path in layout.APP.rglob("*.py")
        if path.name != "__init__.py" and "migrations" not in path.parts
    }


def report(show_modules: bool) -> str:
    executed = executed_files()
    journeys = journey_tests()
    everything = app_modules()
    modules = {module for module in everything if has_functions(module)}
    declarations = sorted(everything - modules)
    reached_by_tests = set().union(*executed.values()) if executed else set()
    by_journey: dict[str, set[str]] = defaultdict(set)
    for test, ids in journeys.items():
        for key in ids:
            by_journey[key.split(".")[0]].update(executed.get(test, set()))
    reached_by_journeys = set().union(*by_journey.values()) if by_journey else set()

    lines = [
        (
            f"tests in the testmon data that executed app code: {len(executed)}; journey tests: "
            f"{len(journeys)}; app modules with functions: {len(modules)} (migrations, package "
            f"files and {len(declarations)} declaration-only modules left out)"
        ),
        "",
        "Journeys and the modules they reach:",
    ]
    for key in sorted(layout.journey_ids()):
        if "." in key:
            continue
        reached = by_journey.get(key, set())
        lines.append(f"  {key}: {len(reached)} modules" + ("" if reached else "  (no journey test yet)"))
        if show_modules:
            lines.extend(f"      {module}" for module in sorted(reached))
    no_journey = sorted(modules - reached_by_journeys)
    no_test = sorted(modules - reached_by_tests)
    lines += ["", f"Reached by no journey test: {len(no_journey)} of {len(modules)} modules"]
    if journeys:
        lines.extend(f"  {module}" for module in no_journey)
    lines += ["", f"Reached by no test at all: {len(no_test)} modules"]
    lines.extend(f"  {module}" for module in no_test)
    lines += ["", f"Declarations only, not traceable (run at import): {len(declarations)}"]
    lines.extend(f"  {module}" for module in declarations)
    return "\n".join(lines)


if __name__ == "__main__":
    print(report("--modules" in sys.argv))
