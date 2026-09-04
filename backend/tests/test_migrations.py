from pathlib import Path
from uuid import UUID

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
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
    command.upgrade(config, "head")

    columns = {column["name"]: column for column in inspect(engine).get_columns("model_releases")}
    assert columns["public_id"]["nullable"] is False
    indexes = {index["name"]: index for index in inspect(engine).get_indexes("model_releases")}
    assert indexes["ix_model_releases_public_id"]["unique"] == 1
    with engine.connect() as connection:
        public_id = connection.scalar(text("SELECT public_id FROM model_releases WHERE id = 1"))
    assert str(UUID(public_id)) == public_id
