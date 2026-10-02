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
        "python -m pytest tests/test_api_journeys.py -q"
    ]
    catalogue = affected.commands(["docs/product-functionality/USER_JOURNEYS.md"])
    assert catalogue == [
        "python -m pytest tests/journeys tests/test_api_journeys.py tests/unit/harness/test_layout.py -q"
    ]


def test_code_and_data_together_run_both():
    run = affected.commands(["backend/app/db.py", "docs/testing/API_JOURNEYS.md"])
    assert run[-1] == "python -m pytest tests/test_api_journeys.py -q"
    assert run[0].endswith("--testmon -q")


def test_documentation_and_frontend_select_nothing_here():
    assert affected.commands(["docs/TODO.md", "frontend/src/app/App.tsx", "README.md"]) == []
