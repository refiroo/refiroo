"""What a change requires to run (tests/affected.py)."""

from pathlib import Path

import affected
import layout
import seeds


def _tree(root: Path, files: dict[str, str]) -> affected.Graph:
    """A repository of ``files`` (path -> source) and the graph over its app and test modules."""
    known = {}
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    for path in (root / "backend" / "app").rglob("*.py"):
        parts = list(path.relative_to(root / "backend").with_suffix("").parts)
        known[".".join(parts[:-1] if parts[-1] == "__init__" else parts)] = path
    for path in (root / "backend" / "tests").glob("*.py"):
        known[path.stem] = path
    return affected.build_graph(known, root)


TREE = {
    "backend/app/__init__.py": "",
    "backend/app/low.py": "X = 1\n",
    "backend/app/mid.py": "from app.low import X\n",
    "backend/app/top.py": "from app import mid\n",
    "backend/app/alone.py": "Y = 1\n",
    "backend/app/lazy.py": "Z = 1\n",
    "backend/tests/test_top.py": "from app.top import mid\n",
    "backend/tests/test_lazy.py": "def test():\n    from app.lazy import Z\n",
    "backend/tests/helper.py": "from app.alone import Y\n",
    "backend/tests/test_helped.py": "import helper\n",
    "backend/tests/test_unrelated.py": "import os\n",
    # the application module mounts the routers; tests that start it reach the app by its map
    "backend/app/main.py": "from app import top\nfrom app.alone import Y\n",
    "backend/tests/test_api.py": "from app.main import create_app\n",
    "backend/tests/starter.py": "def start():\n    from app.main import create_app\n",
    "backend/tests/test_via_helper.py": "import starter\n",
}


def test_a_changed_app_module_selects_the_tests_importing_it_directly_or_through_modules(tmp_path):
    graph = _tree(tmp_path, TREE)
    assert affected.import_selection(["backend/app/low.py"], graph, {})[0] == {"tests/test_top.py"}
    assert affected.import_selection(["backend/app/lazy.py"], graph, {})[0] == {
        "tests/test_lazy.py"
    }


def test_a_changed_helper_selects_the_tests_importing_it_and_a_test_selects_itself(tmp_path):
    graph = _tree(tmp_path, TREE)
    assert affected.import_selection(["backend/tests/helper.py"], graph, {})[0] == {
        "tests/test_helped.py"
    }
    # the helper's top-level import of the app reaches the test using the helper
    assert affected.import_selection(["backend/app/alone.py"], graph, {})[0] == {
        "tests/test_helped.py"
    }
    assert affected.import_selection(["backend/tests/test_unrelated.py"], graph, {})[0] == {
        "tests/test_unrelated.py"
    }


def test_the_import_closure_stops_at_the_application_and_the_map_reaches_what_starts_it(tmp_path):
    graph = _tree(tmp_path, TREE)
    # test_api and test_via_helper start the application (a helper's lazy import counts)
    assert graph.starting == {"tests/test_api.py", "tests/test_via_helper.py"}
    # the application imports `top`, but a change to `low` does not reach them by imports
    assert (
        "tests/test_api.py" not in affected.import_selection(["backend/app/low.py"], graph, {})[0]
    )
    reached = {"tests/test_api.py": ["app/low.py"], "tests/test_via_helper.py": []}
    selected, notes = affected.import_selection(["backend/app/low.py"], graph, reached)
    assert selected == {"tests/test_top.py", "tests/test_api.py"}
    assert "test_via_helper" in notes[0] and "reach no app code" in notes[0]


def test_without_a_map_every_test_that_starts_the_application_is_selected(tmp_path, monkeypatch):
    graph = _tree(tmp_path, TREE)
    monkeypatch.setattr(affected, "REACH_MAP", tmp_path / "missing.json")
    selected, notes = affected.import_selection(["backend/app/low.py"], graph)
    assert selected == {"tests/test_top.py", *graph.starting}
    assert "missing.json is missing" in notes[0]


def test_a_data_file_selects_by_its_folders_modules(tmp_path):
    files = {
        **TREE,
        "backend/app/data/__init__.py": "",
        "backend/app/data/row.json": "{}",
        "backend/tests/test_data.py": "from app import data\n",
    }
    graph = _tree(tmp_path, files)
    selected, notes = affected.import_selection(["backend/app/data/row.json"], graph, {})
    assert selected == {"tests/test_data.py"} and "no module of its own" in notes[0]


def test_code_is_selected_from_the_import_graph_and_run_by_its_modules():
    run = affected.commands(["backend/app/engine/records/writes.py"])
    assert "tests/unit/engine/records/test_writes.py" in run[0]
    assert run[0].startswith("python -m pytest -n 4 ") and "serial" in run[1]
    assert "testmon" not in " ".join(run)


def test_the_seed_inputs_listed_here_are_what_the_seeds_are_built_from():
    schema = {
        path.relative_to(layout.BACKEND.parent).as_posix()
        for path in seeds._migrations()
        if isinstance(path, Path)
    }
    listed = {path for path in schema if not path.startswith("backend/app/migrations/")}
    patterns = affected.SCHEMA_SEED_INPUTS
    assert all(any(Path(path).match(pattern) for pattern in patterns) for path in listed)
    assert {p for p in patterns if "*" not in p} <= listed
    import volume_fixture

    name = seeds.volume_seed(volume_fixture.scaled_shape(0.01))
    inputs = {
        path.relative_to(layout.BACKEND.parent).as_posix()
        for path in seeds.SEEDS[name].inputs()
        if isinstance(path, Path)
    }
    assert inputs - {"backend/tests/volume_fixture.py"} == set(affected.VOLUME_SEED_INPUTS)


def test_schema_seed_inputs_select_everything_and_volume_inputs_the_volume_tests():
    assert affected.commands(["backend/app/engine/authorization/policy.py"])[0] == (
        "python -m pytest -n auto -q"
    )
    assert affected.commands(["backend/tests/harness_identity.py"])[0] == (
        "python -m pytest -n auto -q"
    )
    selected, _ = affected.import_selection(["backend/app/engine/model/bootstrap.py"])
    assert "tests/test_restructuring_volume.py" in selected


def test_the_expected_time_is_the_larger_of_the_longest_unit_and_the_sum_over_the_workers():
    recorded = {
        "tests/test_a.py::test_1": 30.0,
        "tests/test_a.py::test_2[x]": 30.0,
        "tests/test_b.py::test_1": 10.0,
        "tests/unit/engine/test_c.py::test_1": 20.0,
        "tests/test_d.py::test_1": 60.0,
        "tests/test_e.py::test_1": 60.0,
    }
    estimate = affected.estimate(["tests/test_a.py", "tests/test_b.py"], 4, recorded)
    assert (estimate.total, estimate.longest, estimate.seconds) == (70.0, 60.0, 60.0)
    spread = affected.estimate(
        ["tests/test_a.py", "tests/test_b.py", "tests/test_d.py", "tests/test_e.py"], 2, recorded
    )
    assert spread.seconds == 95.0  # 190 s over two workers; no unit is longer
    assert affected.estimate(["tests/test_a.py", "tests/test_b.py"], 1, recorded).seconds == 70.0


def test_a_journey_test_is_a_unit_of_its_own_in_the_expected_time():
    recorded = {
        "tests/journeys/test_j01.py::test_a": 50.0,
        "tests/journeys/test_j01.py::test_b": 50.0,
    }
    assert affected.estimate(["tests/journeys"], 4, recorded).seconds == 50.0


def test_the_expected_time_says_how_many_tests_have_no_record_and_when_it_is_over_the_ceiling():
    recorded = {"tests/test_pagination.py::test_x": 400.0}
    lines = affected.expected_time(
        affected.estimate(["tests/test_pagination.py"], 1, recorded), False
    )
    assert "6 min 40 s in one process" in lines[0]
    assert lines[1].startswith(f"{lines[1].split()[0]} of ") and "no recorded duration" in lines[1]
    assert "OVER the 3 min 0 s package ceiling" in lines[-1]
    short = affected.estimate(["tests/test_pagination.py"], 1, {"tests/test_pagination.py::a": 5.0})
    assert not any("OVER" in line for line in affected.expected_time(short, False))


def test_what_runs_before_the_tests_selects_everything():
    for path in (
        "backend/app/migrations/versions/20261001_02_trigram_search_indexes.py",
        "model/rdm-starter.json",
        "backend/tests/seeds.py",
        "backend/tests/conftest.py",
    ):
        assert affected.commands([path]) == [
            "python -m pytest -n auto -q",
            "python -m pytest -m serial -q",
        ], path


def test_data_files_select_their_readers():
    assert affected.commands(["docs/testing/API_JOURNEYS.md"]) == [
        "python -m pytest -n 4 tests/test_api_journeys.py -q",
        "python -m pytest -m serial tests/test_api_journeys.py -q",
    ]
    targets = "tests/journeys tests/test_api_journeys.py tests/unit/harness/test_layout.py"
    catalogue = affected.commands(["docs/product-functionality/USER_JOURNEYS.md"])
    assert catalogue == [
        f"python -m pytest -n 4 {targets} -q",
        f"python -m pytest -m serial {targets} -q",
    ]


def test_a_selection_with_journey_or_assistant_tests_runs_on_four_workers_then_its_serial_part():
    for target in (
        "tests/journeys/test_j50_ai_reshape.py",
        "tests/journeys/test_j02_correct.py::test_one",
        "tests/test_reference_ai.py",
        "tests/unit/engine/agent_access",
    ):
        assert affected.selection([target]) == [
            f"python -m pytest -n 4 {target} -q",
            f"python -m pytest -m serial {target} -q",
        ], target
    # one waiting target makes the whole selection parallel
    mixed = affected.selection(
        ["tests/unit/engine/records", "tests/journeys/test_j50_ai_reshape.py"]
    )
    assert mixed[0].startswith("python -m pytest -n 4 ") and mixed[1].startswith(
        "python -m pytest -m serial "
    )


def test_a_selection_of_unit_tests_stays_without_workers():
    assert affected.selection(["tests/unit/engine/records/test_rules.py"]) == [
        "python -m pytest tests/unit/engine/records/test_rules.py -q"
    ]


def test_code_and_data_together_run_both():
    run = affected.commands(["backend/app/db.py", "docs/testing/API_JOURNEYS.md"])
    assert run[-1].startswith("python -m pytest -m serial ")
    assert "tests/test_api_journeys.py" in run[0] and "tests/test_db.py" not in run[0]
    assert "tests/unit/test_db.py" in run[0]


def test_documentation_and_frontend_select_nothing_here():
    assert affected.commands(["docs/TODO.md", "frontend/src/app/App.tsx", "README.md"]) == []


def test_the_files_conftest_loads_select_everything_like_conftest():
    for path in ("backend/tests/run_ids.py", "backend/tests/durations.py"):
        assert affected.rule_for(path).selects == affected.FULL
