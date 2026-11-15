"""Which code each journey reaches, and which code no journey or no test reaches (H4b, TS4).

    .venv/bin/python -m tests.journey_trace --record   # record the tests the map lacks, write the map
    .venv/bin/python -m tests.journey_trace --record --all    # record every test module that starts the app
    .venv/bin/python -m tests.journey_trace --record --suite  # the whole suite (not budget), same map
    .venv/bin/python -m tests.journey_trace           # the report, from the last recording
    .venv/bin/python -m tests.journey_trace --modules  # also list every module per journey

Every piece of code traces to a journey (docs/testing/STRATEGY.md). The links are not kept by hand:
``--record`` runs the tests under Coverage.py with one context per test (``journey_coverage.py``),
combines the data in ``journey-coverage/`` beside the test server's data (not in git) and writes
``reach_map.json``: each test module that starts the application (one that reaches ``app.main``
through any import, ``affected.build_graph``) and the app modules it executes. ``tests.affected``
reads the map to select the tests that reach a changed app module over HTTP, and a harness test
checks it (an app module or a test module that no longer exists, a module that starts the
application missing from it). Without ``--all`` only the modules the data holds no test of are run
and their data is merged into what was recorded before. The journey
markers say which journeys a test walks. A module no journey test reaches is either dead code or
serves a journey nobody wrote down; a module no test reaches at all is untested.

The report holds what the recordings ran: the tests that start the application; ``--record --suite``
also covers the others.
"""

import ast
import json
import os
import shutil
import sqlite3  # coverage's data file, not the engine's database
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Run as a module from backend/ (python -m tests.journey_trace), as seeds.py is.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout
import postgres_server

DIRECTORY = postgres_server.ROOT / "journey-coverage"
DATA = DIRECTORY / "coverage"
MAP = layout.TESTS / "reach_map.json"
COMMAND = "python -m tests.journey_trace --record"
WORKERS = "4"
_EXECUTED = """
    SELECT context.context, file.path
    FROM line_bits
    JOIN context ON context.id = line_bits.context_id
    JOIN file ON file.id = line_bits.file_id
    WHERE context.context != ''
"""
_IMPORTED = """
    SELECT DISTINCT file.path
    FROM line_bits
    JOIN context ON context.id = line_bits.context_id
    JOIN file ON file.id = line_bits.file_id
    WHERE context.context = ''
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
code = pytest.main(["--collect-only", "-q", "tests/journeys"], plugins=[plugin])
print("JOURNEYS=" + json.dumps(plugin.found))
"""


def record(everything: bool, redo: bool = False) -> None:
    """Run the test modules that start the application and are not in the map yet (``redo``: all of
    them; ``everything``: the whole suite) under coverage, merge the data with what was recorded
    before and write the map."""
    import affected

    starting = sorted(affected.build_graph().starting)
    # What the data holds a test of; a module with none (it starts the service as a process of its
    # own, or holds only budget tests) is run again, which costs little.
    known = {test.split("::", 1)[0] for test in executed_files()} if DATA.exists() else set()
    if everything:
        targets, redo = ["tests"], True
    else:
        targets = starting if redo else [m for m in starting if m not in known]
    if redo:
        shutil.rmtree(DIRECTORY, ignore_errors=True)
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for stray in DIRECTORY.glob("coverage.*"):
        stray.unlink()
    environment = {
        **os.environ,
        "RDM_JOURNEY_COVERAGE": str(DIRECTORY),
        "PYTHONPATH": os.pathsep.join(
            [str(layout.TESTS), *filter(None, [os.environ.get("PYTHONPATH")])]
        ),
    }
    print(f"Recording {len(targets)} of {len(starting)} test modules that start the application")
    for marks in ([], ["-m", "serial"]) if targets else ():
        command = [sys.executable, "-m", "pytest", "-p", "journey_coverage", "-q", *targets, *marks]
        if not marks:
            command[3:3] = ["-n", WORKERS]
        code = subprocess.run(command, cwd=layout.BACKEND, env=environment, check=False).returncode
        if code == 1:  # tests failed: what they executed before failing is in the data
            print("Some tests failed in the recording run; the map holds what they executed.")
        elif code not in (0, 5):  # 5: the serial part holds no test
            raise SystemExit(f"The recording run did not finish (pytest exit {code}); no map.")
    combine()
    write_map(reach_map(starting))
    print(f"Wrote {MAP.relative_to(layout.BACKEND.parent)} from {DATA}")


def combine() -> None:
    """The data files of the recording's processes in the one file, which keeps what was in it."""
    from coverage import CoverageData
    from coverage.data import combine_parallel_data

    data = CoverageData(basename=str(DATA))
    data.read()  # without it the first update erases the file: coverage starts a data object empty
    combine_parallel_data(data, data_paths=[str(DIRECTORY)])
    data.write()


def reach_map(starting: list[str]) -> dict[str, list[str]]:
    """Test module that starts the application -> the app modules its tests executed, from the
    recorded data. A module that starts the service as a process of its own, or holds only
    ``budget`` tests, executes no app code in a recording: it is listed with none."""
    reached: dict[str, set[str]] = {module: set() for module in starting}
    executed = executed_files()
    for test, files in executed.items():
        module = test.split("::", 1)[0]
        if module in reached:
            reached[module].update(files)
    # Code that runs only at import (the declarations: schemas, constants) has no test context; every
    # test module that starts the application imports it, so each reaches it (R172-F5).
    import_only = import_time_files() - set().union(*executed.values(), set())
    for files in reached.values():
        files.update(import_only)
    return {module: sorted(files) for module, files in sorted(reached.items())}


def map_problems(mapping: dict[str, list[str]], starting: set[str]) -> list[str]:
    """What is wrong with ``mapping``: an app module or a test module that no longer exists, a test
    module that starts the application (``starting``) and is missing from it, or an app module (the
    command line tools aside) that is in no entry, which an edit to it would select no test for
    (checked by ``tests/unit/harness/test_journey_trace.py``)."""
    found = [
        f"{test} reaches {module}, which no longer exists"
        for test, modules in mapping.items()
        for module in modules
        if not (layout.BACKEND / module).is_file()
    ]
    found += [
        f"{test} no longer exists" for test in mapping if not (layout.BACKEND / test).is_file()
    ]
    found += [f"{test} is missing from the map" for test in sorted(starting - set(mapping))]
    listed = {module for modules in mapping.values() for module in modules}
    found += [
        f"{module} is in no entry of the map"
        for module in sorted(app_modules() - listed)
        if not module.startswith("app/cli/")
    ]
    return found


def write_map(mapping: dict[str, list[str]]) -> None:
    """One line per test module, so a change shows as a changed line."""
    lines = [f" {json.dumps(module)}: {json.dumps(files)}" for module, files in mapping.items()]
    MAP.write_text("{\n" + ",\n".join(lines) + "\n}\n")


def executed_files() -> dict[str, set[str]]:
    """Test node ID → the app modules it executed, from the recorded coverage data."""
    if not DATA.exists():
        raise SystemExit(f"No coverage data at {DATA}. Record it: {COMMAND}, then run this again.")
    with sqlite3.connect(DATA) as connection:
        rows = connection.execute(_EXECUTED).fetchall()
    executed: dict[str, set[str]] = defaultdict(set)
    for test, path in rows:
        try:
            filename = Path(path).resolve().relative_to(layout.BACKEND).as_posix()
        except ValueError:
            continue
        if filename.startswith("app/") and "/migrations/" not in filename:
            executed[test].add(filename)
    return executed


def import_time_files() -> set[str]:
    """The app modules that executed lines outside any test (context ``''``: at import)."""
    if not DATA.exists():
        raise SystemExit(f"No coverage data at {DATA}. Record it: {COMMAND}, then run this again.")
    with sqlite3.connect(DATA) as connection:
        rows = connection.execute(_IMPORTED).fetchall()
    found: set[str] = set()
    for (path,) in rows:
        try:
            filename = Path(path).resolve().relative_to(layout.BACKEND).as_posix()
        except ValueError:
            continue
        if filename.startswith("app/") and "/migrations/" not in filename:
            found.add(filename)
    return found


def journey_tests() -> dict[str, list[str]]:
    """Test node ID → the journeys it walks, by collecting tests/journeys/ in a subprocess."""
    if not any(layout.JOURNEYS.rglob("test_*.py")):
        return {}
    result = subprocess.run(
        [sys.executable, "-c", _COLLECT],
        cwd=layout.BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    line = next((row for row in result.stdout.splitlines() if row.startswith("JOURNEYS=")), None)
    if line is None:
        raise SystemExit(
            "Collecting tests/journeys failed:\n" + result.stdout[-2000:] + result.stderr[-2000:]
        )
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
            f"tests in the recorded data that executed app code: {len(executed)}; journey tests: "
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
        lines.append(
            f"  {key}: {len(reached)} modules" + ("" if reached else "  (no journey test yet)")
        )
        if show_modules:
            lines.extend(f"      {module}" for module in sorted(reached))
    no_journey = sorted(modules - reached_by_journeys)
    no_test = sorted(modules - reached_by_tests)
    lines += ["", f"Reached by no journey test: {len(no_journey)} of {len(modules)} modules"]
    if journeys:
        lines.extend(f"  {module}" for module in no_journey)
    if any(not test.startswith("tests/journeys/") for test in executed):
        lines += ["", f"Reached by no test at all: {len(no_test)} modules"]
        lines.extend(f"  {module}" for module in no_test)
    else:
        lines += [
            "",
            f"Reached by no test at all: not known, the recording ran the journey tests only ({COMMAND} --suite)",
        ]
    lines += ["", f"Declarations only, not traceable (run at import): {len(declarations)}"]
    lines.extend(f"  {module}" for module in declarations)
    return "\n".join(lines)


if __name__ == "__main__":
    if "--record" in sys.argv:
        record("--suite" in sys.argv, "--all" in sys.argv)
    else:
        print(report("--modules" in sys.argv))
