"""Test configuration: the PostgreSQL test harness (PG-D8, H1), parallel runs (H2) and the groups.

Every test runs on the harness's private PostgreSQL server (``postgres_server.py``), started for the
run and stopped after it. Databases are clones of seeds built once and reused (``seeds.py``): the
session database, which the modules importing ``app.main.app`` share, and each database a test asks
for through ``migrated_database`` or the volume fixture.

``pytest -n auto`` runs the modules on several worker processes (pytest-xdist, ``--dist loadfile``
in ``pyproject.toml``). The run's own process starts the server, removes databases an interrupted
run left behind and builds the ``schema`` seed before any worker starts; each worker has its own
session database. Timing-based checks are ``serial``: a parallel run leaves them out and names the
command that runs them, in a second, non-parallel invocation.
"""

import os
from uuid import uuid4

import postgres_server
import pytest
import seeds

_WORKER = os.environ.get("PYTEST_XDIST_WORKER")
SESSION_DATABASE = f"t_session_{_WORKER + '_' if _WORKER else ''}{uuid4().hex[:8]}"
_STARTED_SERVER = pytest.StashKey[bool]()
_SERIAL_LEFT_OUT = pytest.StashKey[int]()

# A worker inherits the run's environment, including the URL this module set in the run's own
# process; it replaces it with its own session database, so no two workers share one.
_SESSION_URL = postgres_server.url(SESSION_DATABASE).render_as_string(hide_password=False)
if _WORKER:
    os.environ["DATABASE_URL"] = _SESSION_URL
else:
    os.environ.setdefault("DATABASE_URL", _SESSION_URL)

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
    "test_relation_matrix.py": ("matrix", "queries", "change_sets"),
    "test_relation_matrix_volume.py": ("matrix", "volume"),
    "test_relation_matrix_writes.py": ("matrix", "mapping", "change_sets", "records"),
    "test_matrix_states.py": ("matrix", "change_sets", "records", "startup"),
    "test_parent_candidates.py": ("records", "queries", "change_sets"),
    "test_change_lists.py": ("change_sets", "queries"),
    "test_change_lists_volume.py": ("volume", "change_sets"),
    "test_type_changes.py": ("change_sets", "records", "matrix"),
    "test_restructuring_planner.py": ("change_sets", "records", "matrix"),
    "test_restructuring_volume.py": ("volume", "change_sets"),
    "test_graph_validation_scale.py": ("change_sets", "volume"),
    "test_restructuring_api.py": ("change_sets", "records", "matrix"),
    "test_cross_type_lookup.py": ("queries", "change_sets"),
    "test_model_query.py": ("queries", "change_sets"),
    "test_effective_periods.py": ("queries", "records", "change_sets", "model"),
    "test_workspace_edge_list.py": ("mapping", "queries"),
    "test_batches.py": ("jobs", "records", "change_sets"),
    "test_job_settings.py": ("startup", "jobs"),
    "test_batch_volume.py": ("volume", "jobs"),
    "test_batch_matrix_states.py": ("jobs", "matrix"),
    "test_background_jobs.py": ("jobs", "change_sets"),
    "test_background_volume.py": ("volume", "jobs"),
}


# Timing-based checks (H2): wall-time budgets and races decided by a timer, which other processes'
# load would distort. The `volume` group is serial as a whole; single tests carry the marker.
SERIAL_GROUPS = ("volume",)
SERIAL_DESCRIPTION = "timing-based check: left out of a parallel run, run with `pytest -m serial`"


def _is_worker(config: pytest.Config) -> bool:
    return hasattr(config, "workerinput")


def _is_parallel(config: pytest.Config) -> bool:
    """True in a worker of a parallel run and in the process that runs the workers."""
    return _is_worker(config) or bool(getattr(config.option, "tx", None))


def pytest_configure(config: pytest.Config) -> None:
    for group, description in GROUP_DESCRIPTIONS.items():
        config.addinivalue_line("markers", f"{group}: {description}")
    config.addinivalue_line("markers", f"serial: {SERIAL_DESCRIPTION}")
    config.stash[_SERIAL_LEFT_OUT] = 0


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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    unclassified = set()
    for item in items:
        groups = TEST_GROUPS.get(item.path.name)
        if groups is None:
            unclassified.add(item.path.name)
            continue
        for group in groups:
            item.add_marker(group)
        if any(group in SERIAL_GROUPS for group in groups):
            item.add_marker("serial")
    if unclassified:
        raise pytest.UsageError(
            "Unclassified test module(s): "
            + ", ".join(sorted(unclassified))
            + ". Add each to TEST_GROUPS in backend/tests/conftest.py with the contract groups it "
            "protects, and to docs/testing/EXECUTION_GUIDE.md."
        )
    if _is_parallel(config):
        serial = [item for item in items if item.get_closest_marker("serial")]
        if serial:
            items[:] = [item for item in items if not item.get_closest_marker("serial")]
            config.hook.pytest_deselected(items=serial)
            config.stash[_SERIAL_LEFT_OUT] = len(serial)


def pytest_sessionfinish(session: pytest.Session) -> None:
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
    serial tests a parallel run left out with the command that runs them (H2)."""
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

