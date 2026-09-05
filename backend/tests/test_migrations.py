from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.models.database import Base


def test_fresh_migration_provisions_the_complete_current_schema(tmp_path):
    database_path = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    for table_name, table in Base.metadata.tables.items():
        assert {column["name"] for column in inspector.get_columns(table_name)} == {
            column.name for column in table.columns
        }


def test_public_id_migration_upgrades_existing_metadata_table(tmp_path):
    database_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE model_releases (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO model_releases (id) VALUES (1)"))

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260903_01")

    columns = {column["name"]: column for column in inspect(engine).get_columns("model_releases")}
    assert columns["public_id"]["nullable"] is False
    indexes = {index["name"]: index for index in inspect(engine).get_indexes("model_releases")}
    assert indexes["ix_model_releases_public_id"]["unique"] == 1
    with engine.connect() as connection:
        public_id = connection.scalar(text("SELECT public_id FROM model_releases WHERE id = 1"))
    assert str(UUID(public_id)) == public_id


def test_runtime_state_migration_adopts_one_legacy_active_release(tmp_path):
    database_path = tmp_path / "model-0-4.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260903_01")

    runtime_object_id = "22222222-2222-4222-8222-222222222222"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO model_releases "
                "(public_id, release_key, release_name, release_version, schema_version, "
                "model_hash, model_json, is_active, installed_at) VALUES "
                "(:public_id, 'starter', 'Starter', '0.4.0', '0.4', :model_hash, '{}', true, "
                ":installed_at)"
            ),
            {
                "public_id": "11111111-1111-4111-8111-111111111111",
                "model_hash": "a" * 64,
                "installed_at": "2026-09-04T12:00:00Z",
            },
        )
        connection.execute(
            text(
                "INSERT INTO objects "
                "(id, workspace_key, application_key, object_type_key, parent_object_id, state, "
                "name, version, created_at, updated_at) VALUES "
                "(:object_id, 'migration-workspace', 'rdm-master', 'domain', NULL, 'active', "
                "'Preserved domain', 3, :created_at, :updated_at)"
            ),
            {
                "object_id": runtime_object_id,
                "created_at": "2026-09-04T12:00:00Z",
                "updated_at": "2026-09-04T12:05:00Z",
            },
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        state = connection.execute(
            text("SELECT id, active_model_release_id, version FROM model_runtime_state")
        ).one()
        release_id = connection.scalar(
            text("SELECT id FROM model_releases WHERE public_id = :public_id"),
            {"public_id": "11111111-1111-4111-8111-111111111111"},
        )
        runtime_object = connection.execute(
            text(
                "SELECT id, workspace_key, object_type_key, name, version FROM objects "
                "WHERE id = :object_id"
            ),
            {"object_id": runtime_object_id},
        ).one()
    assert state == (1, release_id, 1)
    assert runtime_object == (
        runtime_object_id,
        "migration-workspace",
        "domain",
        "Preserved domain",
        3,
    )
    unique_constraints = inspect(engine).get_unique_constraints("model_releases")
    assert any(item["name"] == "uq_model_release_identity" for item in unique_constraints)


def test_runtime_state_migration_rejects_ambiguous_legacy_active_releases(tmp_path):
    database_path = tmp_path / "ambiguous-model-0-4.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260903_01")

    with engine.begin() as connection:
        for index in (1, 2):
            connection.execute(
                text(
                    "INSERT INTO model_releases "
                    "(public_id, release_key, release_name, release_version, schema_version, "
                    "model_hash, model_json, is_active, installed_at) VALUES "
                    "(:public_id, 'starter', 'Starter', :version, '0.4', :model_hash, '{}', true, "
                    ":installed_at)"
                ),
                {
                    "public_id": f"{index}1111111-1111-4111-8111-111111111111",
                    "version": f"0.4.{index}",
                    "model_hash": str(index) * 64,
                    "installed_at": "2026-09-04T12:00:00Z",
                },
            )

    try:
        command.upgrade(config, "head")
    except RuntimeError as exc:
        assert str(exc) == (
            "Cannot initialize model runtime state: multiple legacy active releases exist"
        )
    else:
        raise AssertionError("Ambiguous legacy active releases must stop the migration")


def test_runtime_state_migration_rejects_duplicate_legacy_release_identities(tmp_path):
    database_path = tmp_path / "duplicate-identity-model-0-4.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260903_01")

    with engine.begin() as connection:
        for index in (1, 2):
            connection.execute(
                text(
                    "INSERT INTO model_releases "
                    "(public_id, release_key, release_name, release_version, schema_version, "
                    "model_hash, model_json, is_active, installed_at) VALUES "
                    "(:public_id, 'starter', 'Starter', '0.4.0', '0.4', :model_hash, '{}', false, "
                    ":installed_at)"
                ),
                {
                    "public_id": f"{index}1111111-1111-4111-8111-111111111111",
                    "model_hash": str(index) * 64,
                    "installed_at": "2026-09-04T12:00:00Z",
                },
            )

    try:
        command.upgrade(config, "head")
    except RuntimeError as exc:
        assert str(exc) == (
            "Cannot add model release identity uniqueness; duplicate releases exist: starter@0.4.0"
        )
    else:
        raise AssertionError("Duplicate legacy release identities must stop the migration")


def test_audit_subject_migration_backfills_deterministic_object_and_relation_events(tmp_path):
    database_path = tmp_path / "audit-subjects.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260904_02")

    object_id = "11111111-1111-4111-8111-111111111111"
    other_id = "22222222-2222-4222-8222-222222222222"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events "
                "(event_id, aggregate_type, aggregate_id, action, version, changes, occurred_at) "
                "VALUES "
                "('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'object', :object_id, "
                "'created', 1, '{}', '2026-09-05T12:00:00Z'), "
                "('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'relation', "
                "'cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'created', 1, :relation_changes, "
                "'2026-09-05T12:00:00Z'), "
                "('dddddddd-dddd-4ddd-8ddd-dddddddddddd', 'relation', "
                "'cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'updated', 2, '{}', "
                "'2026-09-05T12:00:00Z')"
            ),
            {
                "object_id": object_id,
                "relation_changes": (
                    '{"fromObjectId":"' + object_id + '","toObjectId":"' + other_id + '"}'
                ),
            },
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        subjects = connection.execute(
            text(
                "SELECT e.event_id, s.object_id FROM audit_event_subjects s "
                "JOIN audit_events e ON e.sequence_id = s.audit_event_id "
                "ORDER BY e.event_id, s.object_id"
            )
        ).all()
    assert subjects == [
        ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", object_id),
        ("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", object_id),
        ("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", other_id),
    ]
