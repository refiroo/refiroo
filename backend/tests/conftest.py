"""Test configuration: the PostgreSQL test harness (PG-D8, H1) and the contract groups.

Every test runs on the harness's private PostgreSQL server (``postgres_server.py``), started for the
run and stopped after it. Databases are clones of seeds built once and reused (``seeds.py``): the
session database, which the modules importing ``app.main.app`` share, and each database a test asks
for through ``migrated_database`` or the volume fixture.
"""

import os
from uuid import uuid4

import postgres_server
import pytest
import seeds

SESSION_DATABASE = f"t_session_{uuid4().hex[:8]}"

os.environ.setdefault(
    "DATABASE_URL", postgres_server.url(SESSION_DATABASE).render_as_string(hide_password=False)
)

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


def pytest_configure(config: pytest.Config) -> None:
    for group, description in GROUP_DESCRIPTIONS.items():
        config.addinivalue_line("markers", f"{group}: {description}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    unclassified = set()
    for item in items:
        groups = TEST_GROUPS.get(item.path.name)
        if groups is None:
            unclassified.add(item.path.name)
            continue
        for group in groups:
            item.add_marker(group)
    if unclassified:
        raise pytest.UsageError(
            "Unclassified test module(s): "
            + ", ".join(sorted(unclassified))
            + ". Add each to TEST_GROUPS in backend/tests/conftest.py with the contract groups it "
            "protects, and to docs/testing/EXECUTION_GUIDE.md."
        )


def pytest_terminal_summary(terminalreporter) -> None:
    """Name each seed the run used and whether it was reused or built (H1's evidence)."""
    if seeds.ACTIVITY:
        used: dict[str, str] = {}
        for name, outcome, seconds in seeds.ACTIVITY:
            if outcome == "built" or name not in used:
                used[name] = f"{name}: {outcome}" + (f" in {seconds:.1f} s" if outcome == "built" else "")
        lines = list(used.values())
        terminalreporter.write_sep("-", "seeded databases")
        terminalreporter.write_line("; ".join(lines))


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    """Start the test server, and clone the session database from the ``schema`` seed."""
    started = postgres_server.start()
    seeds.drop_clones()
    seeds.clone("schema", SESSION_DATABASE)
    reload_settings()
    try:
        yield
    finally:
        get_engine().dispose()
        seeds.drop(SESSION_DATABASE)
        if started:
            postgres_server.stop()


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

