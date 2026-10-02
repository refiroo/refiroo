"""What a change requires to run (docs/testing/STRATEGY.md "Choosing what to run", H4b).

    .venv/bin/python -m tests.affected              # the working tree against HEAD
    .venv/bin/python -m tests.affected main~3       # everything since a commit

Python code is selected by ``pytest-testmon``: it records which code each test executes and runs the
tests whose code changed, so a change at the bottom of the hierarchy reaches everything above it that
uses it, and a change used nowhere else runs only its own tests. Coverage cannot see what the code
reads as data, nor code that runs before any test (the seeds, the migrations a seed applies, the
harness itself); a change to one of those selects what reads it, by the rules below.
"""

import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch

FULL = "everything"


@dataclass(frozen=True)
class Rule:
    pattern: str  # a glob over repository paths
    selects: str  # FULL, a pytest target, or "" (nothing in the backend suite)
    why: str


# First match wins.
RULES: tuple[Rule, ...] = (
    Rule("backend/app/migrations/*", FULL, "a migration changes the schema every seed is built from"),
    Rule("model/*.json", FULL, "the starter model is read as data by bootstrap, seeds and tests"),
    Rule("backend/tests/seeds.py", FULL, "seed code runs before the tests"),
    Rule("backend/tests/postgres_server.py", FULL, "the test server runs before the tests"),
    Rule("backend/tests/volume_fixture.py", FULL, "the volume seeds run before the tests"),
    Rule("backend/tests/conftest.py", FULL, "the harness runs around every test"),
    Rule("backend/tests/layout.py", FULL, "the layout rules run at collection"),
    Rule("backend/pyproject.toml", FULL, "dependencies and pytest settings"),
    Rule(
        "docs/product-functionality/USER_JOURNEYS.md",
        "tests/journeys tests/unit/harness/test_layout.py tests/test_api_journeys.py",
        "the journey catalogue is read at collection and by the inventory check",
    ),
    Rule("docs/testing/API_JOURNEYS.md", "tests/test_api_journeys.py", "the inventory is read as data"),
    Rule("backend/app/*", "testmon", "code the tests execute"),
    Rule("backend/tests/*", "testmon", "test code"),
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


def commands(paths: list[str]) -> list[str]:
    """The commands to run from backend/, in order; empty when the backend suite is not affected."""
    selected = {rule_for(path).selects for path in paths} - {""}
    if FULL in selected:
        return ["python -m pytest -n auto -q", "python -m pytest -m serial -q"]
    run = []
    if "testmon" in selected:
        run += [
            "python -m pytest -n auto --testmon -q",
            "python -m pytest -m serial --testmon --testmon-forceselect -q",
        ]
    targets = sorted({target for entry in selected - {"testmon"} for target in entry.split()})
    if targets:
        run.append(f"python -m pytest {' '.join(targets)} -q")
    return run


def main() -> None:
    since = sys.argv[1] if len(sys.argv) > 1 else None
    paths = changed(since)
    for path in paths:
        rule = rule_for(path)
        print(f"{path}: {rule.selects or 'nothing'} ({rule.why})")
    run = commands(paths)
    print("\nRun from backend/ with .venv/bin/:" if run else "\nNo backend tests to run.")
    for command in run:
        print(f"  {command}")


if __name__ == "__main__":
    main()
