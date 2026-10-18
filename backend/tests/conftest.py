"""Test configuration: the PostgreSQL test harness (PG-D8, H1), parallel runs (H2) and the groups.

Every test runs on the harness's private PostgreSQL server (``postgres_server.py``), started for the
run and stopped after it. Databases are clones of seeds built once and reused (``seeds.py``): the
session database, which the modules importing ``app.main.app`` share, and each database a test asks
for through ``migrated_database`` or the volume fixture.

``pytest -n auto`` runs the modules on several worker processes (pytest-xdist, ``--dist loadfile``
in ``pyproject.toml``). The run's own process starts the server, removes databases an interrupted
run left behind and builds the ``schema`` seed before any worker starts; each worker has its own
session database. Timing-based checks are ``serial``: a parallel run leaves them out and names the
command that runs them, in a second, non-parallel invocation. Full-size budgets are ``budget``: a run
leaves them out unless its ``-m`` expression names ``budget`` (H3). The summary lists every test
over 10 s outside ``budget`` and the run's wall time, against the time ceilings in
``docs/TEST_HARNESS_PLAN.md``.

Journey tests live in ``tests/journeys/`` and name the journeys they walk; unit tests live in
``tests/unit/`` in folders that mirror the code they test (``layout.py``, H4b). A journey test without
a known journey ID, or a unit test that mirrors no module, fails collection; ``--journey J02`` selects
the tests that walk J02 or one of its variants.
"""

import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import layout
import postgres_server
import pytest
import seeds

# Test selection (pytest-testmon, H4b) records which code each test executes through Coverage.py.
# Its default on Python 3.14, sys.monitoring, loses the lines that run in the TestClient's request
# threads when testmon switches from one test to the next (an API test recorded 5-13 of its 38-66
# modules); the C tracer records them. Set before testmon starts coverage; workers inherit it.
os.environ.setdefault("COVERAGE_CORE", "ctrace")
_WORKER = os.environ.get("PYTEST_XDIST_WORKER")
SESSION_DATABASE = f"t_session_{_WORKER + '_' if _WORKER else ''}{uuid4().hex[:8]}"
_STARTED_SERVER = pytest.StashKey[bool]()
_SERIAL_LEFT_OUT = pytest.StashKey[int]()
_STARTED_AT = pytest.StashKey[float]()
# Each test's setup, call and teardown added up, by node ID (the slow-test report, H3).
_DURATIONS: dict[str, float] = {}

# A worker inherits the run's environment, including the URL this module set in the run's own
# process; it replaces it with its own session database, so no two workers share one.
_SESSION_URL = postgres_server.url(SESSION_DATABASE).render_as_string(hide_password=False)
if _WORKER:
    os.environ["DATABASE_URL"] = _SESSION_URL
else:
    os.environ.setdefault("DATABASE_URL", _SESSION_URL)
# Job files (0.9 J1) go to a directory of the session's own, never the project's ``var/``. Like the
# database URL, a worker replaces the one it inherits: an application reconciles its directory
# against its own database, so two workers sharing one would remove each other's files.
_SESSION_FILES = str(Path(tempfile.gettempdir()) / "rdm-test-job-files" / SESSION_DATABASE)
if _WORKER:
    os.environ["JOB_FILE_DIR"] = _SESSION_FILES
else:
    os.environ.setdefault("JOB_FILE_DIR", _SESSION_FILES)

from app.config import reload_settings
from app.db import get_engine

# Contract/risk groups (docs/testing/EXECUTION_GUIDE.md). Every test module is listed with the
# groups it is evidence for; `pytest -m <group>` selects them. A module missing here fails
# collection, so a new test file cannot silently fall outside every focused selection.
GROUP_DESCRIPTIONS = {
    "model": "model parsing, compilation, reference validation and compatibility classes",
    "model_admin": "model releases, model drafts, installation, activation, diff and change-set pins",
    "startup": "lifespan bootstrap, database checks, the baseline migration, schema upgrade",
    "records": "live objects, fields, relations, translations and signed deletion",
    "queries": "typed filters, sort, search, cursor pagination and scope",
    "workspaces": "workspace catalogue, explicit scope, pinned contexts, retirement and withdrawal",
    "change_sets": "change sets: sources, edits, graph validation, publishing and publications",
    "mapping": "mapping coverage, atomic replacement and relation-set versions",
    "matrix": "relation matrix reads: cells, states, row state filter and columns",
    "contract": "locked OpenAPI document and route inventories",
    "volume": "Track S volume fixture: read and write budgets as the dataset grows",
    "consumer": "consumer API definitions, reads, XREF, batch resolve, crosswalk, publications, parity",
    "jobs": "jobs, outcomes, idempotency, batches, background execution, import profiles, imports and exports",
    "feed": "feed positions, publish entries and the feed read, retention, consumer events (C10)",
    "authoring": "model draft operations, their history, undo and redo, generated layout (0.10 A2)",
    "workspace_models": "each workspace's model: assignment, resolution, activation and the commit guard per workspace (0.11 M1)",
    "migration": "a workspace's data migrated to another release: preview, confirmation, conversions (0.11 V1)",
    "move": "data moved between workspaces whose models differ: the model-to-model mapping, its inference (0.11 X1)",
}
TEST_GROUPS: dict[str, tuple[str, ...]] = {
    "test_model.py": ("model",),
    "test_model_diagnostics.py": ("model",),
    "test_model_independence.py": ("model",),
    "test_model_placements.py": ("model", "contract"),
    "test_model_compatibility.py": ("model", "model_admin"),
    "test_model_lifecycle.py": ("model_admin",),
    "test_consumer_api_model.py": ("consumer", "model", "model_admin"),
    "test_build07_wp11.py": ("model_admin",),
    "test_build07_wp6.py": ("model_admin", "change_sets"),
    "test_build07_wp9_acceptance.py": ("model_admin", "change_sets", "workspaces"),
    "test_startup.py": ("startup",),
    "test_schema_drift.py": ("startup",),
    "test_foreign_keys.py": ("startup",),
    "test_model_schema_upgrade.py": ("startup", "model_admin"),
    "test_api.py": ("records",),
    "test_attributes.py": ("records",),
    "test_relations.py": ("records",),
    "test_translations.py": ("records",),
    "test_cascade_delete.py": ("records",),
    "test_pagination.py": ("queries",),
    "test_typed_table_queries.py": ("queries", "change_sets"),
    "test_query_foundations.py": ("queries", "records"),
    "test_workspaces.py": ("workspaces",),
    "test_w6_workspace_deletion.py": ("workspaces",),
    "test_wp81a_context.py": ("workspaces", "model_admin"),
    "test_request_scope.py": ("workspaces",),
    "test_wp8_withdrawal.py": ("workspaces", "change_sets"),
    "test_change_sets.py": ("change_sets",),
    "test_wp7_canonical_crud.py": ("change_sets",),
    "test_wp8_change_set_lifecycle.py": ("change_sets",),
    "test_wp8_graph_validation.py": ("change_sets",),
    "test_wp8_publish.py": ("change_sets",),
    "test_wp8_publish_merge.py": ("change_sets",),
    "test_wp81b_current_live_bases.py": ("change_sets",),
    "test_wp8_history.py": ("change_sets",),
    "test_wp8_review_regressions.py": ("change_sets", "records"),
    "test_mapping_coverage.py": ("mapping",),
    "test_mapping_replacement.py": ("mapping", "change_sets"),
    "test_relation_set_versions.py": ("mapping", "records"),
    "test_openapi_contract.py": ("contract",),
    "test_boundaries.py": ("contract",),
    "test_error_codes.py": ("contract",),
    "test_api_journeys.py": ("contract",),
    "test_api_reference.py": ("contract",),
    "test_encoding.py": ("records",),
    "test_rule_parity.py": ("records", "change_sets"),
    "test_volume_baseline.py": ("volume",),
    "test_context_read_parity.py": ("change_sets", "queries"),
    "test_paging_contract.py": ("volume", "queries", "contract"),
    "test_change_set_position_reads.py": ("volume", "queries", "change_sets"),
    "test_change_set_write_lookups.py": ("change_sets",),
    "test_search_index.py": ("queries", "change_sets"),
    "test_w5_activation_write_race.py": ("model_admin", "records"),
    "test_pg3_concurrency.py": ("records", "mapping", "matrix", "jobs", "model_admin", "workspaces"),
    "test_pg3b_batch_writes.py": ("records", "jobs", "matrix"),
    "test_relation_matrix.py": ("matrix", "queries", "change_sets"),
    "test_relation_matrix_volume.py": ("matrix", "volume"),
    "test_relation_matrix_writes.py": ("matrix", "mapping", "change_sets", "records"),
    "test_matrix_states.py": ("matrix", "change_sets", "records", "startup"),
    "test_parent_candidates.py": ("records", "queries", "change_sets"),
    "test_change_lists.py": ("change_sets", "queries"),
    "test_change_lists_volume.py": ("volume", "change_sets"),
    "test_consumer_list_volume.py": ("consumer", "volume"),
    "test_consumer_xref_volume.py": ("consumer", "volume"),
    "test_consumer_event_volume.py": ("feed", "consumer", "volume"),
    "test_export_volume.py": ("jobs", "volume"),
    "test_import_volume.py": ("jobs", "volume"),
    "test_import_budget.py": ("volume", "jobs"),
    "test_migration_budget.py": ("volume", "migration"),
    "test_type_changes.py": ("change_sets", "records", "matrix"),
    "test_restructuring_planner.py": ("change_sets", "records", "matrix"),
    "test_restructuring_volume.py": ("volume", "change_sets"),
    "test_graph_validation_scale.py": ("change_sets", "volume"),
    "test_restructuring_api.py": ("change_sets", "records", "matrix"),
    "test_cross_type_lookup.py": ("queries", "change_sets"),
    "test_model_query.py": ("queries", "change_sets"),
    "test_effective_periods.py": ("queries", "records", "change_sets", "model"),
    "test_workspace_edge_list.py": ("mapping", "queries"),
    "test_batch_volume.py": ("volume", "jobs"),
    "test_batch_statements.py": ("volume", "jobs"),
    "test_background_volume.py": ("volume", "jobs"),
}


# While the groups remain (H4d is postponed), the tests H4d moved keep being selected by them: a unit test by its
# folder under tests/unit/ (the longest matching prefix), a journey test by its journeys.
UNIT_GROUPS: dict[str, tuple[str, ...]] = {
    "common/test_outage.py": ("feed", "jobs"),
    "common/test_sealing.py": ("feed",),
    "consumer/": ("consumer",),
    "engine/change_sets/test_publish.py": ("change_sets", "feed"),
    "engine/events/": ("feed", "consumer"),
    "engine/jobs/": ("jobs",),
    "engine/model/": ("model",),
    "engine/model/authoring/": ("authoring", "model"),
    "engine/moves/": ("move",),
    "engine/reads/": ("consumer",),
    "engine/sources/": ("authoring", "jobs"),
    "engine/records/test_audit.py": ("records", "jobs"),
    "engine/records/test_relation_set_versions.py": ("records", "jobs"),
    "models/test_commands.py": ("jobs",),
    "models/test_database.py": ("startup", "jobs"),
    "test_config.py": ("startup", "jobs"),
    "test_main.py": ("startup", "jobs"),
}
JOURNEY_GROUPS: dict[str, tuple[str, ...]] = {
    "J01": ("records", "queries"),
    "J02": ("records",),
    "J03": ("records",),
    "J04": ("records",),
    "J05": ("change_sets",),
    "J06": ("change_sets",),
    "J07": ("change_sets", "workspaces"),
    "J08": ("model_admin",),
    "J10": ("mapping",),
    "J11": ("jobs",),
    "J12": ("startup",),
    "J13": ("records", "mapping"),
    "J14": ("records",),
    "J15": ("records", "change_sets"),
    "J16": ("matrix",),
    "J17": ("change_sets",),
    "J18": ("model_admin", "change_sets"),
    "J19": ("workspaces",),
    "J20": ("contract", "model"),
    "J21": ("queries",),
    "J22": ("queries",),
    "J23": ("queries", "consumer"),
    "J24": ("jobs",),
    "J25": ("consumer", "model"),
    "J26": ("feed", "records", "change_sets"),
    "J28": ("consumer",),
    "J29": ("consumer",),
    "J30": ("feed", "consumer"),
    "J31": ("startup",),
    "J33": ("authoring", "model", "model_admin"),
    "J34": ("authoring", "jobs"),
    "J36": ("workspace_models", "model_admin", "workspaces"),
    "J37": ("migration", "workspace_models", "jobs"),
    "J38": ("move", "jobs"),
}


def _moved_groups(item: pytest.Item, kind: str) -> set[str]:
    if kind == "journey":
        return {g for key in _journey_ids(item) for g in JOURNEY_GROUPS.get(key.split(".")[0], ())}
    where = item.path.relative_to(layout.UNIT).as_posix()
    prefixes = [prefix for prefix in UNIT_GROUPS if where.startswith(prefix)]
    return set(UNIT_GROUPS[max(prefixes, key=len)]) if prefixes else set()

# Timing-based checks (H2, narrowed in H3): only a test whose outcome depends on wall time, which other
# processes' load would distort. An entry is a module or one test (`module::test`); a check that
# counts statements or rows runs in the parallel part, however large its data.
TIMED: dict[str, str] = {
    "test_graph_validation_scale.py::test_validating_and_publishing_a_large_workspace_stay_within_budget":
        "validating and publishing the large workspace against seconds",
    "test_wp81b_current_live_bases.py::test_current_live_capture_after_a_concurrent_activation_asks_for_a_retry":
        "the capture must reach its lock wait before a 0.3 s timer commits",
}
SERIAL_DESCRIPTION = "timing-based check: left out of a parallel run, run with `pytest -m serial`"

# Full-size budgets (H3): left out of every run whose -m expression does not name `budget`, and
# serial when named. PG3b replaces their timed checks with statement counts at two seeded sizes
# (PG-D17); the 100,000-item batch is measured once at PG5's acceptance.
BUDGET_MODULES = (
    "test_batch_volume.py",
    "test_background_volume.py",
    "test_import_budget.py",
    "test_migration_budget.py",
)
BUDGET_DESCRIPTION = "full-size budget: left out unless `-m` names `budget`; a release's acceptance only"
SLOW_SECONDS = 10.0
JOURNEY_DESCRIPTION = (
    "journey(*ids): the user journeys and variants of USER_JOURNEYS.md this test walks"
)
UNIT_DESCRIPTION = "unit test of one module, in tests/unit/ mirroring the module's path"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--journey",
        action="append",
        default=[],
        metavar="ID",
        help="Run only the tests that walk this journey or variant (J02, J02.2); repeatable.",
    )


def _is_worker(config: pytest.Config) -> bool:
    return hasattr(config, "workerinput")


def _is_parallel(config: pytest.Config) -> bool:
    """True in a worker of a parallel run and in the process that runs the workers."""
    return _is_worker(config) or bool(getattr(config.option, "tx", None))


def pytest_configure(config: pytest.Config) -> None:
    for group, description in GROUP_DESCRIPTIONS.items():
        config.addinivalue_line("markers", f"{group}: {description}")
    config.addinivalue_line("markers", f"serial: {SERIAL_DESCRIPTION}")
    config.addinivalue_line("markers", f"budget: {BUDGET_DESCRIPTION}")
    config.addinivalue_line("markers", JOURNEY_DESCRIPTION)
    config.addinivalue_line("markers", f"unit: {UNIT_DESCRIPTION}")
    config.stash[_SERIAL_LEFT_OUT] = 0
    config.stash[_STARTED_AT] = time.monotonic()


def _names_budget(config: pytest.Config) -> bool:
    return re.search(r"\bbudget\b", config.option.markexpr or "") is not None


def _deselect(config: pytest.Config, items: list[pytest.Item], marker: str) -> int:
    chosen = [item for item in items if item.get_closest_marker(marker)]
    if chosen:
        items[:] = [item for item in items if not item.get_closest_marker(marker)]
        config.hook.pytest_deselected(items=chosen)
    return len(chosen)


def pytest_sessionstart(session: pytest.Session) -> None:
    """In the run's own process, before any worker starts: start the server, remove databases an
    interrupted run left behind and build the ``schema`` seed, so no worker races another for them."""
    if _is_worker(session.config):
        return
    try:
        session.config.stash[_STARTED_SERVER] = postgres_server.start()
    except postgres_server.ServerUnavailable as unavailable:
        pytest.exit(str(unavailable), returncode=pytest.ExitCode.USAGE_ERROR)
    seeds.drop_clones()
    seeds.ensure("schema")


def pytest_unconfigure(config: pytest.Config) -> None:
    # After every worker has ended; a server another tool started stays running.
    if config.stash.get(_STARTED_SERVER, False):
        postgres_server.stop()


def _journey_ids(item: pytest.Item) -> tuple[str, ...]:
    return tuple(key for marker in item.iter_markers("journey") for key in marker.args)


def _check_layout(items: list[pytest.Item]) -> list[pytest.Item]:
    """Mark unit tests, check every journey ID and unit path, and return the suite's items."""
    problems, suite = set(), []
    for item in items:
        where = item.path.relative_to(layout.TESTS)
        unknown = layout.unknown_journeys(_journey_ids(item))
        if unknown:
            problems.add(f"{where}: unknown journey {', '.join(unknown)} (not in USER_JOURNEYS.md)")
        kind = layout.kind(item.path)
        if kind == "journey" and not _journey_ids(item):
            problems.add(f"{where}::{item.name}: a journey test names no journey (@pytest.mark.journey)")
        elif kind == "unit":
            if layout.unit_target(item.path) is None:
                problems.add(
                    f"{where}: mirrors no module; a unit test sits at tests/unit/<path>/test_<module>.py "
                    "for app/<path>/<module>.py, or tests/unit/harness/ for tests/<module>.py"
                )
            item.add_marker("unit")
        elif kind == "suite":
            suite.append(item)
        if kind in {"journey", "unit"}:
            for group in _moved_groups(item, kind):
                item.add_marker(group)
    if problems:
        raise pytest.UsageError("Test layout:\n" + "\n".join(sorted(problems)))
    return suite


def _select_journeys(config: pytest.Config, items: list[pytest.Item]) -> None:
    wanted = config.getoption("journey")
    unknown = layout.unknown_journeys(tuple(wanted))
    if unknown:
        raise pytest.UsageError(f"--journey names unknown journeys: {', '.join(unknown)}")
    if not wanted:
        return
    chosen = [i for i in items if any(layout.walks(_journey_ids(i), key) for key in wanted)]
    left = [item for item in items if item not in chosen]
    if left:
        items[:] = chosen
        config.hook.pytest_deselected(items=left)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    unclassified = set()
    for item in _check_layout(items):
        groups = TEST_GROUPS.get(item.path.name)
        if groups is None:
            unclassified.add(item.path.name)
            continue
        for group in groups:
            item.add_marker(group)
        if item.path.name in BUDGET_MODULES:
            item.add_marker("budget")
            item.add_marker("serial")
        name = item.path.name
        if name in TIMED or f"{name}::{item.name}" in TIMED or f"{name}::{item.originalname}" in TIMED:
            item.add_marker("serial")
    if unclassified:
        raise pytest.UsageError(
            "Unclassified test module(s): "
            + ", ".join(sorted(unclassified))
            + ". Add each to TEST_GROUPS in backend/tests/conftest.py with the contract groups it "
            "protects, and to docs/testing/EXECUTION_GUIDE.md."
        )
    _select_journeys(config, items)
    if not _names_budget(config):
        _deselect(config, items, "budget")
    if _is_parallel(config):
        config.stash[_SERIAL_LEFT_OUT] = _deselect(config, items, "serial")


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Add up each test's setup, call and teardown; in a parallel run the run's own process receives
    every worker's reports here. Budget tests are not listed: their size is known."""
    if "budget" in report.keywords:
        return
    _DURATIONS[report.nodeid] = _DURATIONS.get(report.nodeid, 0.0) + report.duration


def pytest_sessionfinish(session: pytest.Session) -> None:
    # This process's job files go with the session (each worker has its own directory).
    shutil.rmtree(os.environ.get("JOB_FILE_DIR", _SESSION_FILES), ignore_errors=True)
    # A worker hands what it did with seeds and serial tests to the run's own process.
    if _is_worker(session.config):
        session.config.workeroutput["seed_activity"] = [list(entry) for entry in seeds.ACTIVITY]
        session.config.workeroutput["serial_left_out"] = session.config.stash[_SERIAL_LEFT_OUT]


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error) -> None:
    output = getattr(node, "workeroutput", {})
    seeds.ACTIVITY.extend(tuple(entry) for entry in output.get("seed_activity", []))
    left_out = output.get("serial_left_out", 0)
    node.config.stash[_SERIAL_LEFT_OUT] = max(node.config.stash[_SERIAL_LEFT_OUT], left_out)


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    """Name each seed the run used and whether it was reused or built (H1's evidence), and the
    serial tests a parallel run left out with the command that runs them (H2), then the tests over
    10 s outside ``budget`` and the run's wall time (H3)."""
    if seeds.ACTIVITY:
        used: dict[str, str] = {}
        for name, outcome, seconds in seeds.ACTIVITY:
            if outcome == "built" or name not in used:
                used[name] = f"{name}: {outcome}" + (f" in {seconds:.1f} s" if outcome == "built" else "")
        lines = list(used.values())
        terminalreporter.write_sep("-", "seeded databases")
        terminalreporter.write_line("; ".join(lines))
    left_out = config.stash.get(_SERIAL_LEFT_OUT, 0)
    if left_out and not _is_worker(config):
        expression = config.option.markexpr
        marks = f"serial and ({expression})" if expression else "serial"
        given = config.args_source == pytest.Config.ArgsSource.ARGS
        paths = " ".join(config.args) if given else ""
        terminalreporter.write_sep("-", "serial tests not run")
        terminalreporter.write_line(
            f"{left_out} timing-based test(s) are left out of a parallel run. Run them next, "
            f'without -n: python -m pytest -m "{marks}"' + (f" {paths}" if paths else "")
        )
    if _is_worker(config) or not _DURATIONS:
        return
    slow = sorted(
        ((seconds, nodeid) for nodeid, seconds in _DURATIONS.items() if seconds > SLOW_SECONDS),
        reverse=True,
    )
    terminalreporter.write_sep("-", f"tests over {SLOW_SECONDS:.0f} s outside budget")
    for seconds, nodeid in slow:
        terminalreporter.write_line(f"{seconds:7.1f} s  {nodeid}")
    if not slow:
        terminalreporter.write_line("none")
    wall = time.monotonic() - config.stash[_STARTED_AT]
    terminalreporter.write_line(f"wall time {int(wall // 60)} min {wall % 60:.0f} s")


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    """Clone this process's session database from the ``schema`` seed (one per worker)."""
    seeds.clone("schema", SESSION_DATABASE)
    reload_settings()
    try:
        yield
    finally:
        get_engine().dispose()
        seeds.drop(SESSION_DATABASE)


@pytest.fixture
def migrated_database():
    """Return a factory for a private database at the Alembic head, cloned from the ``schema`` seed.

    The application lifespan still runs its checks, its Alembic head check and the model bootstrap
    against it. Each clone is dropped when the test ends. ``name`` is kept for readability only.
    """
    created: list[str] = []

    def create(name: str = "test") -> str:
        database = f"t_{uuid4().hex[:16]}"
        created.append(database)
        return seeds.clone("schema", database).render_as_string(hide_password=False)

    yield create
    # Dropped WITH (FORCE), which also closes connections the application's pool kept open.
    for database in created:
        seeds.drop(database)

