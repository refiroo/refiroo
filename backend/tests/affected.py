"""What a change requires to run (docs/testing/STRATEGY.md "Choosing what to run", H4b, TS4).

    .venv/bin/python -m tests.affected              # the working tree against HEAD
    .venv/bin/python -m tests.affected main~3       # everything since a commit

Python code is selected from the import graph (``import_graph.py``, the reading ``test_boundaries.py``
does): a changed app module selects every test module that imports it, directly or through other app
modules; a changed test module selects itself and the test modules importing it, a changed helper in
``tests/`` the test modules importing it. The import closure stops at the application (``CUT``:
``app.main`` imports every router, so everything would reach every test that creates the application).
What a test that starts the application (one that reaches ``app.main`` through any import, its
helpers' included) reaches over HTTP comes from ``reach_map.json``, a map of such a test module to the
app modules it executes, recorded by ``python -m tests.journey_trace --record`` and checked by a
harness test. What
code reads as data, and what runs before any test (the seeds, the migrations a seed applies, the
harness itself), is selected by the rules below: seed inputs select the tests cloning that seed (the
``schema`` seed is the session database of every test, so its inputs select everything).

Before the commands it prints the selection's expected time from ``durations.json`` (``durations.py``),
and says so when it exceeds the 3-minute package ceiling (EXECUTION_GUIDE section 1).

A selection holding journey or assistant tests runs with ``-n 4`` whatever its size, and its ``-m serial``
part next (``selection``); only a selection of unit tests is faster without ``-n``.
"""

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

# Run as a module from backend/ (python -m tests.affected), as seeds.py is.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import durations
import import_graph
import layout

FULL = "everything"
# Test modules chosen from the import graph and the reach map.
IMPORTS = "imports"
ROOT = layout.BACKEND.parent
REACH_MAP = layout.TESTS / "reach_map.json"
# The module that mounts every router. Its imports are not followed: a test that only starts the
# application reaches the code it runs through the map, not through this module's imports.
CUT = "app.main"
# The package ceiling of a run (EXECUTION_GUIDE section 1, TEST_HARNESS_PLAN "Time ceilings").
CEILING_SECONDS = 180

# A selection holding tests that wait (a journey's server and job worker, an assistant's stand-in) runs on
# four workers whatever its size: a small unit selection is faster without ``-n``, a waiting one is not (TS3).
WORKERS = "-n 4"
_WAITING = ("journeys", "assistant", "agent", "_ai_", "_ai.", "/ai/")


# What the seeds are built from (``seeds.py``: ``_migrations`` for ``schema``, ``volume_seed`` for the
# volume seeds); a harness test checks these lists against it. Migrations, ``volume_fixture.py`` and
# the other harness files are rules below. Every test clones ``schema`` (the session database), so
# its inputs select everything; the volume seeds' inputs select the test modules that use the volume
# fixture, found by import.
SCHEMA_SEED_INPUTS = (
    *(
        f"backend/app/engine/identity/{name}"
        for name in ("clients.py", "keys.py", "passwords.py", "settings.py", "users.py")
    ),
    "backend/app/engine/authorization/*.py",
    "backend/tests/harness_identity.py",
)
VOLUME_SEED_INPUTS = (
    "backend/app/engine/indexes/matrix_states.py",
    "backend/app/engine/indexes/snapshot_values.py",
    "backend/app/engine/model/bootstrap.py",
)
VOLUME_USER = "volume_fixture"


@dataclass(frozen=True)
class Rule:
    pattern: str  # a glob over repository paths
    selects: str  # FULL, a pytest target, or "" (nothing in the backend suite)
    why: str


# First match wins.
RULES: tuple[Rule, ...] = (
    Rule(
        "backend/app/migrations/*", FULL, "a migration changes the schema every seed is built from"
    ),
    Rule("model/*.json", FULL, "the starter model is read as data by bootstrap, seeds and tests"),
    Rule("backend/tests/seeds.py", FULL, "seed code runs before the tests"),
    Rule("backend/tests/postgres_server.py", FULL, "the test server runs before the tests"),
    Rule("backend/tests/volume_fixture.py", FULL, "the volume seeds run before the tests"),
    Rule("backend/tests/conftest.py", FULL, "the harness runs around every test"),
    Rule("backend/tests/run_ids.py", FULL, "conftest.py loads it: it runs around every test"),
    Rule("backend/tests/durations.py", FULL, "conftest.py loads it: it runs around every test"),
    Rule("backend/tests/layout.py", FULL, "the layout rules run at collection"),
    Rule("backend/pyproject.toml", FULL, "dependencies and pytest settings"),
    Rule(
        "docs/product-functionality/USER_JOURNEYS.md",
        "tests/journeys tests/unit/harness/test_layout.py tests/test_api_journeys.py",
        "the journey catalogue is read at collection and by the inventory check",
    ),
    Rule(
        "docs/testing/API_JOURNEYS.md",
        "tests/test_api_journeys.py",
        "the inventory is read as data",
    ),
    *(
        Rule(path, FULL, "the schema seed is built from it and every test clones that seed")
        for path in SCHEMA_SEED_INPUTS
    ),
    Rule(
        "backend/tests/reach_map.json",
        "tests/unit/harness/test_journey_trace.py",
        "the reach map is read as data and checked there",
    ),
    Rule(
        "backend/app/*", IMPORTS, "the tests that import it and the tests that reach it over HTTP"
    ),
    Rule("backend/tests/*", IMPORTS, "the tests that import it"),
    Rule("frontend/*", "", "frontend: Vitest and the build (EXECUTION_GUIDE §2)"),
    Rule("*", "", "not read by the backend suite"),
)


def rule_for(path: str) -> Rule:
    return next(rule for rule in RULES if fnmatch(path, rule.pattern))


def changed(since: str | None) -> list[str]:
    def git(*args: str) -> list[str]:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        return [line for line in result.stdout.splitlines() if line]

    root = git("rev-parse", "--show-toplevel")[0]
    paths = set(git("-C", root, "diff", "--name-only", since or "HEAD"))
    paths.update(git("-C", root, "ls-files", "--others", "--exclude-standard"))
    return sorted(paths)


def waits(target: str) -> bool:
    """True for a journey or an assistant test target (a path, with or without ``tests/``)."""
    return any(part in target for part in _WAITING)


def selection(targets: list[str], parallel: bool = False) -> list[str]:
    """The commands for named targets: on four workers when any waits, then the ``serial`` part next."""
    if not parallel and not any(waits(target) for target in targets):
        return [f"python -m pytest {' '.join(targets)} -q"]
    named = " ".join(targets)
    return [f"python -m pytest {WORKERS} {named} -q", f"python -m pytest -m serial {named} -q"]


@dataclass(frozen=True)
class Graph:
    """Who imports what, over the app's modules and the tests'."""

    known: dict[str, Path]
    importers: dict[str, set[str]]  # module -> the modules importing it (the cut applied)
    starting: frozenset[str] = frozenset()  # test modules that start the application, as paths
    root: Path = ROOT  # the repository; paths below are relative to it and to its backend/ folder

    def key_of(self, path: str) -> str | None:
        return {file.resolve(): key for key, file in self.known.items()}.get(
            (self.root / path).resolve()
        )

    def reaching(self, starts: set[str]) -> set[str]:
        """The modules importing any of ``starts``, directly or through other modules."""
        found, queue = set(starts), list(starts)
        while queue:
            for importer in self.importers.get(queue.pop(), ()):
                if importer not in found:
                    found.add(importer)
                    queue.append(importer)
        return found

    def tests_among(self, keys: set[str]) -> set[str]:
        return {self.target(key) for key in keys if self.known[key].name.startswith("test_")}

    def target(self, key: str) -> str:
        return self.known[key].relative_to(self.root / "backend").as_posix()


def build_graph(known: dict[str, Path] | None = None, root: Path = ROOT) -> Graph:
    """The import graph. A harness helper's imports inside a function (``seeds`` builds a seed by
    importing the app) are not edges: they would tie every test using a helper to everything the
    helper can start; a test module's own imports all are. The application module ``CUT`` follows
    none of its imports. Importing a module runs its packages' ``__init__`` files, so a module's
    edges include them. ``starting`` holds the test modules that reach ``CUT`` over every kind of
    import (a helper's lazy one too): the ones that start the application."""
    known = known or {**import_graph.modules(), **import_graph.test_side_modules()}
    importers: dict[str, set[str]] = defaultdict(set)
    every: dict[str, set[str]] = defaultdict(set)
    for importer, target, _name, top in import_graph.scan(known):
        if target not in known:
            continue
        helper = not known[importer].name.startswith("test_")
        lazy_helper = helper and not top and target.startswith("app")
        parts = target.split(".")
        for end in range(1, len(parts) + 1):
            package = ".".join(parts[:end])
            if package in known and package != importer:
                every[package].add(importer)
                if importer != CUT and not lazy_helper:
                    importers[package].add(importer)
    everyone = Graph(known, every, frozenset(), root)
    starting = everyone.tests_among(everyone.reaching({CUT})) if CUT in known else set()
    return Graph(known, importers, frozenset(starting), root)


def reach_map() -> dict[str, list[str]] | None:
    """Test module -> the app modules it executes (``reach_map.json``), None when absent."""
    try:
        return json.loads(REACH_MAP.read_text())
    except OSError, ValueError:
        return None


def import_selection(
    paths: list[str], graph: Graph | None = None, reached: dict[str, list[str]] | None = None
) -> tuple[set[str], list[str]]:
    """The test modules the import graph, the reach map and the volume seed's inputs select for the
    changed ``paths``, and notes for the reader."""
    graph = graph or build_graph()
    reached = reach_map() if reached is None else reached
    selected: set[str] = set()
    notes: list[str] = []
    for path in paths:
        key = graph.key_of(path)
        if key is not None:
            starts = {key}
        elif path.endswith("conftest.py") and path.startswith("backend/tests/"):
            selected.add(str(Path(path).parent.relative_to("backend")))
            continue
        else:
            # Not a module the graph knows (a data file, a deleted or unreadable module): the modules
            # of the nearest folder with any, so what imports them is selected.
            folder = (graph.root / path).parent
            starts = set()
            while not starts and folder != graph.root:
                starts = {k for k, file in graph.known.items() if file.parent == folder}
                folder = folder.parent
            notes.append(f"{path}: no module of its own, selects by its folder's modules")
        selected |= graph.tests_among(graph.reaching(starts))
        if any(fnmatch(path, pattern) for pattern in VOLUME_SEED_INPUTS):
            selected |= graph.tests_among(graph.reaching({VOLUME_USER}))
        if path.startswith("backend/app/"):
            if reached is None:
                selected |= graph.starting
                notes.append(
                    f"{REACH_MAP.name} is missing: every test module that starts the application "
                    f"({len(graph.starting)}) selected"
                )
                continue
            files = {graph.target(k) for k in starts}
            unseen = sorted(m for m in graph.starting if not reached.get(m))
            if unseen and not any("reach no app code" in note for note in notes):
                notes.append(
                    f"{len(unseen)} test modules that start the application reach no app code in the "
                    "map (they start the service as a process of their own, or are budget "
                    "modules), so an app change does not select them: "
                    + ", ".join(Path(m).stem for m in unseen)
                )
            selected |= {module for module, names in reached.items() if files & set(names)}
    return {
        t for t in selected if not any(t != d and t.startswith(d + "/") for d in selected)
    }, notes


def commands(paths: list[str]) -> list[str]:
    """The commands to run from backend/, in order; empty when the backend suite is not affected."""
    return plan(paths)[0]


def plan(paths: list[str]) -> tuple[list[str], list[str], list[str]]:
    """The commands, the test targets they run (empty for the whole suite) and notes."""
    selected = {rule_for(path).selects for path in paths} - {""}
    if FULL in selected:
        return ["python -m pytest -n auto -q", "python -m pytest -m serial -q"], [], []
    notes: list[str] = []
    targets = {target for entry in selected - {IMPORTS} for target in entry.split()}
    starting: frozenset[str] = frozenset()
    if IMPORTS in selected:
        graph = build_graph()
        starting = graph.starting
        chosen, notes = import_selection(
            [p for p in paths if rule_for(p).selects == IMPORTS], graph
        )
        targets |= chosen
    targets = {t for t in targets if not any(t != d and t.startswith(d + "/") for d in targets)}
    ordered = sorted(targets)
    # A test that starts the application waits (its server, its job worker): on workers (TS3).
    parallel = bool(targets & starting)
    return (selection(ordered, parallel) if ordered else []), ordered, notes


def workers_of(command: str) -> int:
    found = re.search(r" -n (\w+) ", command)
    if found is None:
        return 1
    return (os.cpu_count() or 1) if found.group(1) == "auto" else int(found.group(1))


def _matches(nodeid: str, target: str) -> bool:
    return (
        nodeid == target
        or nodeid.startswith((target + "::", target + "[", target.rstrip("/") + "/"))
        or not target
    )


def test_functions(targets: list[str]) -> set[str]:
    """``module::function`` of every test function and method in the targets (a parametrized test once)."""
    found: set[str] = set()
    for target in targets or ["tests"]:
        name = target.split("::", 1)
        base = layout.BACKEND / name[0]
        if not base.exists():
            continue
        files = sorted(base.rglob("test_*.py")) if base.is_dir() else [base]
        for file in files:
            relative = file.relative_to(layout.BACKEND).as_posix()
            if len(name) > 1:
                found.add(f"{relative}::{name[1].split('[')[0]}")
                continue
            tree = ast.parse(file.read_text())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                    found.add(f"{relative}::{node.name}")
                elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    found.update(
                        f"{relative}::{node.name}::{member.name}"
                        for member in node.body
                        if isinstance(member, ast.FunctionDef) and member.name.startswith("test")
                    )
    return found


@dataclass(frozen=True)
class Estimate:
    seconds: float
    total: float
    longest: float
    workers: int
    without_record: int
    functions: int


def estimate(
    targets: list[str], workers: int, recorded: dict[str, float] | None = None
) -> Estimate:
    """The expected time of a selection from the recorded durations. On workers: the larger of the
    longest unit one worker takes (a module, a journey test alone: ``layout.worker_scope``) and the
    sum divided by the workers; without workers the sum."""
    recorded = durations.load() if recorded is None else recorded
    chosen = {n: s for n, s in recorded.items() if any(_matches(n, t) for t in targets or [""])}
    units: dict[str, float] = defaultdict(float)
    for nodeid, seconds in chosen.items():
        units[layout.worker_scope(nodeid)] += seconds
    total, longest = sum(units.values()), max(units.values(), default=0.0)
    seconds = max(longest, total / workers) if workers > 1 else total
    known = {nodeid.split("[")[0] for nodeid in chosen}
    functions = test_functions(targets)
    return Estimate(seconds, total, longest, workers, len(functions - known), len(functions))


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)} min {seconds % 60:.0f} s" if seconds >= 60 else f"{seconds:.0f} s"


def expected_time(estimated: Estimate, serial_part: bool) -> list[str]:
    """The lines saying what a selection should take, and when it is over the package ceiling."""
    how = (
        f"on {estimated.workers} workers (sum {clock(estimated.total)}, longest unit "
        f"{clock(estimated.longest)})"
        if estimated.workers > 1
        else "in one process"
    )
    lines = [
        f"Expected time: {clock(estimated.seconds)} {how}"
        + (", without the serial part" if serial_part else ""),
        (
            f"{estimated.without_record} of {estimated.functions} selected test functions have no "
            "recorded duration (a parametrized test counts once; budget and serial tests are "
            "never recorded)"
        ),
    ]
    if estimated.seconds > CEILING_SECONDS:
        lines.append(
            f"OVER the {clock(CEILING_SECONDS)} package ceiling: announce the run with this time "
            "first; in a package it needs the user's go-ahead (EXECUTION_GUIDE section 1)"
        )
    return lines


def main() -> None:
    since = sys.argv[1] if len(sys.argv) > 1 else None
    if since in ("-h", "--help"):
        print(__doc__)
        return
    try:
        paths = changed(since)
    except subprocess.CalledProcessError:
        sys.exit(f"tests.affected: {since!r} is not a commit git knows (usage: --help)")
    for path in paths:
        rule = rule_for(path)
        print(f"{path}: {rule.selects or 'nothing'} ({rule.why})")
    run, targets, notes = plan(paths)
    for note in notes:
        print(f"note: {note}")
    if targets:
        print(f"\nSelected test modules: {len(targets)}")
        for target in targets[:60]:
            print(f"  {target}")
        if len(targets) > 60:
            print(f"  … and {len(targets) - 60} more")
    if run:
        if durations.FILE.exists() or durations.enabled():
            print()
            for line in expected_time(
                estimate(targets, workers_of(run[0] + " ")), any(" -m serial" in c for c in run)
            ):
                print(line)
        print("\nRun from backend/ with .venv/bin/:")
    else:
        print("\nNo backend tests to run.")
    for command in run:
        print(f"  {command}")


if __name__ == "__main__":
    main()
