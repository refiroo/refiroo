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
    "model_admin": "model releases, drafts, installation, activation, diff and draft pins",
    "startup": "lifespan bootstrap, Alembic migrations, interrupted migration, schema upgrade",
    "records": "live objects, fields, relations, translations and signed deletion",
    "queries": "typed filters, sort, search, cursor pagination and scope",
    "workspaces": "workspace catalogue, explicit scope, pinned contexts and retirement",
    "drafts": "data drafts: sources, edits, graph validation, activation and history",
    "mapping": "mapping coverage, atomic replacement and relation-set versions",
    "contract": "locked OpenAPI document and route inventories",
}
TEST_GROUPS: dict[str, tuple[str, ...]] = {
    "test_model.py": ("model",),
    "test_model_diagnostics.py": ("model",),
    "test_model_independence.py": ("model",),
    "test_model_compatibility.py": ("model", "model_admin"),
    "test_model_lifecycle.py": ("model_admin",),
    "test_build07_wp11.py": ("model_admin",),
    "test_build07_wp6.py": ("model_admin", "drafts"),
    "test_startup.py": ("startup",),
    "test_migrations.py": ("startup",),
    "test_wp8_audit_migration.py": ("startup",),
    "test_model_schema_upgrade.py": ("startup", "model_admin"),
    "test_api.py": ("records",),
    "test_attributes.py": ("records",),
    "test_relations.py": ("records",),
    "test_translations.py": ("records",),
    "test_cascade_delete.py": ("records",),
    "test_pagination.py": ("queries",),
    "test_typed_table_queries.py": ("queries", "drafts"),
    "test_query_foundations.py": ("queries", "records"),
    "test_workspaces.py": ("workspaces",),
    "test_wp81a_context.py": ("workspaces", "model_admin"),
    "test_request_scope.py": ("workspaces",),
    "test_wp8_retirement.py": ("workspaces", "drafts"),
    "test_workspace_revisions.py": ("drafts",),
    "test_wp7_canonical_crud.py": ("drafts",),
    "test_wp8_draft_lifecycle.py": ("drafts",),
    "test_wp8_graph_validation.py": ("drafts",),
    "test_wp8_activation.py": ("drafts",),
    "test_wp8_activation_merge.py": ("drafts",),
    "test_wp81b_current_live_bases.py": ("drafts",),
    "test_wp8_history.py": ("drafts",),
    "test_wp8_review_regressions.py": ("drafts", "records"),
    "test_mapping_coverage.py": ("mapping",),
    "test_mapping_replacement.py": ("mapping", "drafts"),
    "test_relation_set_versions.py": ("mapping", "records"),
    "test_openapi_contract.py": ("contract",),
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
