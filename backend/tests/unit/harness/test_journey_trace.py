"""The reach map is checked against the code (tests/journey_trace.py, TS4)."""

import json

import affected
import journey_trace
import layout


def test_the_reach_map_names_only_code_and_tests_that_exist_and_every_test_that_starts_the_app():
    starting = set(affected.build_graph().starting)
    problems = journey_trace.map_problems(json.loads(journey_trace.MAP.read_text()), starting)
    assert not problems, (
        "tests/reach_map.json is out of date:\n  "
        + "\n  ".join(problems)
        + f"\nRegenerate it: cd backend && .venv/bin/{journey_trace.COMMAND}"
        + " (add --all to record every module again)"
    )


def test_the_check_finds_a_vanished_module_a_vanished_test_and_a_missing_one():
    present = sorted(layout.JOURNEYS.glob("test_*.py"))
    names = [path.relative_to(layout.BACKEND).as_posix() for path in present]
    kept = {name: ["app/main.py"] for name in names[1:]}
    kept["tests/journeys/test_j99_gone.py"] = ["app/gone.py"]
    found = journey_trace.map_problems(kept, set(names))
    assert "tests/journeys/test_j99_gone.py reaches app/gone.py, which no longer exists" in found
    assert "tests/journeys/test_j99_gone.py no longer exists" in found
    assert f"{names[0]} is missing from the map" in found


def test_a_journey_and_an_api_module_start_the_application_a_pure_unit_test_does_not():
    starting = affected.build_graph().starting
    assert "tests/journeys/test_j02_correct.py" in starting
    assert "tests/test_api.py" in starting
    assert "tests/unit/engine/records/test_values.py" not in starting


def test_an_app_module_in_no_entry_is_a_problem_the_command_line_tools_aside():
    present = sorted(layout.JOURNEYS.glob("test_*.py"))
    name = present[0].relative_to(layout.BACKEND).as_posix()
    kept = {name: ["app/main.py"]}
    found = journey_trace.map_problems(kept, {name})
    assert "app/engine/identity/lookup.py is in no entry of the map" in found
    assert not [problem for problem in found if "app/cli/" in problem]
    everything = sorted(journey_trace.app_modules())
    assert journey_trace.map_problems({name: everything}, {name}) == []


def test_code_that_runs_only_at_import_is_reached_by_every_test_module_that_starts_the_app(
    monkeypatch,
):
    monkeypatch.setattr(journey_trace, "executed_files", lambda: {"tests/a.py::t": {"app/x.py"}})
    monkeypatch.setattr(journey_trace, "import_time_files", lambda: {"app/x.py", "app/schemas.py"})
    mapping = journey_trace.reach_map(["tests/a.py", "tests/b.py"])
    assert mapping == {
        "tests/a.py": ["app/schemas.py", "app/x.py"],
        "tests/b.py": ["app/schemas.py"],
    }
