"""``migrations/versions/20261129_01_sign_in_managed.py``: the upgrade from the preceding revision
(0.17 SA1). A person who existed before the column has it off, and the column has no default left."""

import seeds
from alembic import command
from sqlalchemy import create_engine, text

from app.db import migration_config


def test_a_person_from_the_preceding_revision_is_not_managed():
    url = seeds.create_empty()
    engine = create_engine(url)
    try:
        config = migration_config(url)
        command.upgrade(config, "20261128_01")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (public_id, name, email, active, version, created_at, "
                    "updated_at, local_kept, notice_mail_kinds_off, notice_mail_kinds_digest) "
                    "VALUES ('p1', 'A', 'a@example.org', true, 1, now(), now(), false, '{}', '{}')"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            managed = connection.scalar(
                text("SELECT sign_in_managed FROM users WHERE public_id = 'p1'")
            )
            column = connection.execute(
                text(
                    "SELECT is_nullable, column_default FROM information_schema.columns "
                    "WHERE table_name = 'users' AND column_name = 'sign_in_managed'"
                )
            ).one()
        assert managed is False
        assert tuple(column) == ("NO", None)
    finally:
        engine.dispose()
        seeds.drop(url.database)
