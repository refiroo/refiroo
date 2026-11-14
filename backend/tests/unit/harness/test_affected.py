"""What a change requires to run (tests/affected.py)."""

import affected


def test_code_is_selected_by_testmon():
    assert affected.commands(["backend/app/engine/records/rules.py"]) == [
        "python -m pytest -n auto --testmon -q",
        "python -m pytest -m serial --testmon --testmon-forceselect -q",
    ]


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
    assert run[-1] == "python -m pytest -m serial tests/test_api_journeys.py -q"
    assert run[0].endswith("--testmon -q")


def test_documentation_and_frontend_select_nothing_here():
    assert affected.commands(["docs/TODO.md", "frontend/src/app/App.tsx", "README.md"]) == []
