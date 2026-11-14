"""The durations file: merged by side-by-side runs, latest value kept (tests/durations.py)."""

import json
import multiprocessing

import durations


def _write(file, nodeid):
    durations.record({nodeid: 1.5, "shared": 2.0}, file)


def test_a_record_replaces_the_old_value_and_keeps_the_other_tests(tmp_path):
    file = tmp_path / "durations.json"
    durations.record({"tests/test_a.py::test_1": 1.0, "tests/test_a.py::test_2": 2.0}, file)
    durations.record({"tests/test_a.py::test_2": 5.0}, file)
    assert durations.load(file) == {"tests/test_a.py::test_1": 1.0, "tests/test_a.py::test_2": 5.0}


def test_runs_side_by_side_do_not_lose_each_others_tests(tmp_path):
    file = tmp_path / "durations.json"
    with multiprocessing.get_context("spawn").Pool(4) as pool:
        pool.starmap(_write, [(file, f"tests/test_{n}.py::test") for n in range(8)])
    saved = durations.load(file)
    assert set(saved) == {f"tests/test_{n}.py::test" for n in range(8)} | {"shared"}
    assert json.loads(file.read_text())  # whole, never half-written


def test_a_missing_or_broken_file_is_empty_and_a_missing_folder_is_not_created(tmp_path):
    assert durations.load(tmp_path / "none.json") == {}
    (tmp_path / "broken.json").write_text("{")
    assert durations.load(tmp_path / "broken.json") == {}
    durations.record({"a": 1.0}, tmp_path / "absent" / "durations.json")
    assert not (tmp_path / "absent").exists()


def test_ci_an_external_server_and_a_recording_run_write_nothing(monkeypatch):
    for name in ("CI", "RDM_TEST_DATABASE_SERVER", "RDM_JOURNEY_COVERAGE"):
        monkeypatch.delenv(name, raising=False)
    assert durations.enabled()
    for name in ("CI", "RDM_TEST_DATABASE_SERVER", "RDM_JOURNEY_COVERAGE"):
        monkeypatch.setenv(name, "x")
        assert not durations.enabled(), name
        monkeypatch.delenv(name)
