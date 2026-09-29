import os
import shutil
from pathlib import Path

import pytest

TEST_DB_PATH = Path(__file__).resolve().parent / "test-rdm-engine.db"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

from app.config import reload_settings
from app.db import create_database, get_engine
from app.models.database import Base

# Contract/risk groups (docs/testing/EXECUTION_GUIDE.md). Every test module is listed with the
# groups it is evidence for; `pytest -m <group>` selects them. A module missing here fails
# collection, so a new test file cannot silently fall outside every focused selection.
GROUP_DESCRIPTIONS = {
    "model": "model parsing, compilation, reference validation and compatibility classes",
    "model_admin": "model releases, model drafts, installation, activation, diff and change-set pins",
    "startup": "lifespan bootstrap, Alembic migrations, interrupted migration, schema upgrade",
    "records": "live objects, fields, relations, translations and signed deletion",
    "queries": "typed filters, sort, search, cursor pagination and scope",
    "workspaces": "workspace catalogue, explicit scope, pinned contexts, retirement and withdrawal",
    "change_sets": "change sets: sources, edits, graph validation, publishing and publications",
    "mapping": "mapping coverage, atomic replacement and relation-set versions",
    "matrix": "relation matrix reads: cells, states, row state filter and columns",
    "contract": "locked OpenAPI document and route inventories",
    "volume": "Track S volume fixture: read and write budgets as the dataset grows",
}
TEST_GROUPS: dict[str, tuple[str, ...]] = {
    "test_model.py": ("model",),
    "test_model_diagnostics.py": ("model",),
    "test_model_independence.py": ("model",),
    "test_model_placements.py": ("model", "contract"),
    "test_model_compatibility.py": ("model", "model_admin"),
    "test_model_lifecycle.py": ("model_admin",),
    "test_build07_wp11.py": ("model_admin",),
    "test_build07_wp6.py": ("model_admin", "change_sets"),
    "test_build07_wp9_acceptance.py": ("model_admin", "change_sets", "workspaces"),
    "test_startup.py": ("startup",),
    "test_migrations.py": ("startup",),
    "test_schema_drift.py": ("startup",),
    "test_change_set_object_index_migration.py": ("startup", "change_sets"),
    "test_wp8_audit_migration.py": ("startup",),
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
    "test_encoding.py": ("records",),
    "test_rule_parity.py": ("records", "change_sets"),
    "test_volume_baseline.py": ("volume",),
    "test_context_read_parity.py": ("change_sets", "queries"),
    "test_snapshot_value_migration.py": ("startup", "change_sets"),
    "test_paging_contract.py": ("volume", "queries", "contract"),
    "test_change_set_position_reads.py": ("volume", "queries", "change_sets"),
    "test_change_set_write_lookups.py": ("change_sets",),
    "test_snapshot_lookup_index_migration.py": ("startup", "change_sets"),
    "test_search_index.py": ("queries", "change_sets", "startup"),
    "test_page_index_migrations.py": ("startup", "change_sets"),
    "test_change_set_rename_migration.py": ("startup", "change_sets"),
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


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    yield
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def _migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One empty database at the Alembic head, migrated once per session.

    Migrating a fresh file costs ~0.2 s; copying this template costs ~1 ms. Tests that verify
    migration or startup from an empty or older database must not use it.
    """
    path = tmp_path_factory.mktemp("migrated-template") / "template.db"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{path}")
        reload_settings()
        create_database()
        get_engine().dispose()
    reload_settings()
    return path


@pytest.fixture
def migrated_database(_migrated_template: Path, tmp_path: Path):
    """Return a factory for a private, already-migrated SQLite URL under ``tmp_path``.

    Each call copies the session template, so every test still owns its database file and the
    application lifespan still runs its Alembic head check and model bootstrap against it.
    """

    def create(name: str = "test.db") -> str:
        path = tmp_path / name
        shutil.copyfile(_migrated_template, path)
        return f"sqlite:///{path}"

    return create
