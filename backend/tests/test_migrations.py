import json
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.models.database import Base, WorkspaceRevision


def test_fresh_migration_provisions_the_complete_current_schema(tmp_path):
    database_path = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "20260906_01")
    assert {"object_drafts", "object_revisions"}.issubset(inspect(engine).get_table_names())
    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    for table_name, table in Base.metadata.tables.items():
        assert {column["name"] for column in inspector.get_columns(table_name)} == {
            column.name for column in table.columns
        }
    assert "object_revisions" not in inspector.get_table_names()
    assert "object_drafts" not in inspector.get_table_names()
    assert "active_revision_id" not in {column["name"] for column in inspector.get_columns("objects")}
    assert any(
        foreign_key["referred_table"] == "workspace_revisions"
        and foreign_key["constrained_columns"] == ["active_revision_id"]
        for foreign_key in inspector.get_foreign_keys("workspaces")
    )


def test_object_lifecycle_migration_recovers_empty_sqlite_ddl_from_interrupted_run(
    tmp_path,
):
    database_path = tmp_path / "interrupted-object-lifecycle.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260906_01")

    WorkspaceRevision.__table__.create(engine)

    command.upgrade(config, "head")

    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260907_03"
        )
    assert any(
        foreign_key["referred_table"] == "workspace_revisions"
        and foreign_key["constrained_columns"] == ["active_revision_id"]
        for foreign_key in inspector.get_foreign_keys("workspaces")
    )


def test_workspace_revision_migration_refuses_unknown_partial_ddl(tmp_path):
    database_path = tmp_path / "unsafe-interrupted-workspace-revision.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260906_01")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE workspace_revisions (id VARCHAR(36))"))

    with pytest.raises(RuntimeError, match="workspace_revisions has an unexpected schema"):
        command.upgrade(config, "head")


def test_base_0_5_graph_becomes_one_workspace_revision_with_stable_ids(tmp_path):
    database_path = tmp_path / "base-0-5-graph.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260905_02")
    parent_id = "11111111-1111-4111-8111-111111111111"
    child_id = "22222222-2222-4222-8222-222222222222"
    relation_id = "33333333-3333-4333-8333-333333333333"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO model_releases "
                "(public_id, release_key, release_name, release_version, schema_version, "
                "model_hash, model_json, is_active, installed_at) VALUES "
                "('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'starter', 'Starter', '0.5.0', "
                "'0.5', :hash, '{}', true, :at)"
            ),
            {"hash": "a" * 64, "at": "2026-09-07T10:00:00Z"},
        )
        release_id = connection.scalar(text("SELECT id FROM model_releases"))
        connection.execute(
            text(
                "INSERT INTO model_runtime_state (id, active_model_release_id, version, updated_at) "
                "VALUES (1, :release_id, 1, :at)"
            ),
            {"release_id": release_id, "at": "2026-09-07T10:00:00Z"},
        )
        for object_id, object_type, name, parent in (
            (parent_id, "domain", "Parent", None),
            (child_id, "codelist", "Child", parent_id),
        ):
            connection.execute(
                text(
                    "INSERT INTO objects (id, workspace_key, application_key, object_type_key, "
                    "parent_object_id, state, name, version, created_at, updated_at) VALUES "
                    "(:id, 'default', 'rdm-master', :type, :parent, 'active', :name, 7, :at, :at)"
                ),
                {"id": object_id, "type": object_type, "parent": parent, "name": name, "at": "2026-09-07T10:00:00Z"},
            )
        connection.execute(
            text(
                "INSERT INTO attribute_values (id, object_id, attribute_type_key, value_type, "
                "integer_value, value_source, version) VALUES "
                "('44444444-4444-4444-8444-444444444444', :object_id, 'rank', 'integer', 42, 'own', 3)"
            ),
            {"object_id": child_id},
        )
        connection.execute(
            text(
                "INSERT INTO object_relations (id, relation_type_key, from_object_id, to_object_id, "
                "attributes, version, created_at, updated_at) VALUES "
                "(:id, 'contains', :parent, :child, :attributes, 5, :at, :at)"
            ),
            {
                "id": relation_id,
                "parent": parent_id,
                "child": child_id,
                "attributes": json.dumps({"order": 1}),
                "at": "2026-09-07T10:00:00Z",
            },
        )

    command.upgrade(config, "20260906_01")
    assert {"object_drafts", "object_revisions"}.issubset(inspect(engine).get_table_names())
    # The rejected WP4 migration leaves objects as a projection.  Deliberately diverge it from
    # the selected immutable snapshots: WP6 must copy the effective snapshots, then rebuild the
    # projection, rather than silently promoting these stale base-row values.
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE objects SET name = 'stale projection', parent_object_id = NULL, version = 99 "
                "WHERE id = :object_id"
            ),
            {"object_id": child_id},
        )
        connection.execute(
            text(
                "UPDATE attribute_values SET integer_value = 999 "
                "WHERE object_id = :object_id AND attribute_type_key = 'rank'"
            ),
            {"object_id": child_id},
        )
    command.upgrade(config, "head")

    with engine.connect() as connection:
        revision_id = connection.scalar(
            text("SELECT active_revision_id FROM workspaces WHERE key = 'default'")
        )
        objects = connection.execute(
            text(
                "SELECT object_id, parent_object_id, attributes, version FROM workspace_revision_objects "
                "WHERE revision_id = :revision_id ORDER BY object_id"
            ),
            {"revision_id": revision_id},
        ).all()
        projection = connection.execute(
            text(
                "SELECT name, parent_object_id, version FROM objects WHERE id = :object_id"
            ),
            {"object_id": child_id},
        ).one()
        projected_attribute = connection.execute(
            text(
                "SELECT value_type, integer_value FROM attribute_values "
                "WHERE object_id = :object_id AND attribute_type_key = 'rank'"
            ),
            {"object_id": child_id},
        ).one()
        relations = connection.execute(
            text(
                "SELECT relation_id, from_object_id, to_object_id, attributes, version "
                "FROM workspace_revision_relations WHERE revision_id = :revision_id"
            ),
            {"revision_id": revision_id},
        ).all()
    assert revision_id is not None
    assert objects == [
        (parent_id, None, "{}", 7),
        (child_id, parent_id, '{"rank": 42}', 99),
    ]
    assert relations == [(relation_id, parent_id, child_id, '{"order": 1}', 5)]
    assert projection == ("Child", parent_id, 99)
    assert projected_attribute == ("integer", 42)
    inspector = inspect(engine)
    assert {"object_drafts", "object_revisions"}.isdisjoint(inspector.get_table_names())
    assert "active_revision_id" not in {column["name"] for column in inspector.get_columns("objects")}


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
        workspaces = connection.execute(
            text("SELECT key, label, status, version FROM workspaces ORDER BY key")
        ).all()
        workspace_state = connection.execute(
            text("SELECT id, default_workspace_key, version FROM workspace_runtime_state")
        ).one()
    assert state == (1, release_id, 1)
    assert runtime_object == (
        runtime_object_id,
        "migration-workspace",
        "domain",
        "Preserved domain",
        3,
    )
    assert workspaces == [
        ("default", "Default", "active", 1),
        ("migration-workspace", "migration-workspace", "active", 1),
    ]
    assert workspace_state == (1, "default", 1)
    assert any(
        foreign_key["referred_table"] == "workspaces"
        and foreign_key["constrained_columns"] == ["workspace_key"]
        for foreign_key in inspect(engine).get_foreign_keys("objects")
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


def test_workspace_revision_migration_refuses_mixed_object_lifecycle_states(tmp_path):
    database_path = tmp_path / "object-states.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260903_01")
    ids = {
        "active": "11111111-1111-4111-8111-111111111111",
        "draft": "22222222-2222-4222-8222-222222222222",
        "retired": "33333333-3333-4333-8333-333333333333",
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO model_releases (public_id, release_key, release_name, "
                "release_version, schema_version, model_hash, model_json, is_active, installed_at) "
                "VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'starter', 'Starter', "
                "'0.5.0', '0.5', :model_hash, :model_json, true, '2026-09-06T10:00:00Z')"
            ),
            {
                "model_hash": "a" * 64,
                "model_json": json.dumps(
                    {
                        "objectTypes": [
                            {
                                "key": "translation",
                                "behavior": {"parentRelationTypeKeys": []},
                            }
                        ],
                        "objectTypeRelations": [
                            {
                                "relationTypeKey": "owns",
                                "toObjectTypeKey": "translation",
                                "required": True,
                            }
                        ],
                    }
                ),
            },
        )
        for state, object_id in ids.items():
            connection.execute(
                text(
                    "INSERT INTO objects (id, workspace_key, application_key, object_type_key, "
                    "parent_object_id, state, name, version, created_at, updated_at) VALUES "
                    "(:id, 'default', 'rdm-master', :object_type, NULL, :state, :name, 3, "
                    "'2026-09-06T10:00:00Z', '2026-09-06T10:05:00Z')"
                ),
                {
                    "id": object_id,
                    "state": state,
                    "name": state.title(),
                    "object_type": "translation" if state == "draft" else "domain",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO attribute_values (id, object_id, attribute_type_key, value_type, "
                    "text_value, value_source, version) VALUES "
                    "(:value_id, :object_id, 'domain-code', 'text', :value, 'own', 1)"
                ),
                {
                    "value_id": str(UUID(int=len(state))),
                    "object_id": object_id,
                    "value": state.upper(),
                },
            )
        connection.execute(
            text(
                "INSERT INTO object_relations (id, relation_type_key, from_object_id, "
                "to_object_id, attributes, version, created_at, updated_at) VALUES "
                "('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'owns', :source_id, :target_id, "
                ":attributes, 1, '2026-09-06T10:00:00Z', '2026-09-06T10:00:00Z')"
            ),
            {
                "source_id": ids["active"],
                "target_id": ids["draft"],
                "attributes": '{"rank":1}',
            },
        )

    with pytest.raises(RuntimeError, match="workspace 'default'.*states are ambiguous"):
        command.upgrade(config, "head")


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


def test_object_revision_migration_rejects_unknown_legacy_states_with_counts(tmp_path):
    database_path = tmp_path / "unknown-object-state.db"
    engine = create_engine(f"sqlite:///{database_path}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260905_02")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO objects (id, workspace_key, application_key, object_type_key, "
                "parent_object_id, state, name, version, created_at, updated_at) VALUES "
                "('11111111-1111-4111-8111-111111111111', 'default', 'rdm-master', "
                "'domain', NULL, 'archived', 'Unknown state one', 1, "
                "'2026-09-06T10:00:00Z', '2026-09-06T10:00:00Z'), "
                "('22222222-2222-4222-8222-222222222222', 'default', 'rdm-master', "
                "'domain', NULL, 'archived', 'Unknown state two', 1, "
                "'2026-09-06T10:00:00Z', '2026-09-06T10:00:00Z')"
            )
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "Cannot migrate runtime-object lifecycle; unknown object states exist: "
            r"archived \(2\)"
        ),
    ):
        command.upgrade(config, "head")
    assert "object_revisions" not in inspect(engine).get_table_names()
