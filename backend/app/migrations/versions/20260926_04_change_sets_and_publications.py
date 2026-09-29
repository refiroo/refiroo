"""Change sets and publications (Base 0.8 W2, ADR-031).

Renames the data-draft storage to change sets and the workspace revision storage to publications:
``workspace_draft*`` tables become ``change_set*`` (``draft_id`` becomes ``change_set_id``),
``workspace_revision*`` become ``publication*`` (``revision_id`` becomes ``publication_id``,
``revision_number`` becomes ``publication_number``, ``activated_at`` and ``retired_at`` become
``published_at`` and ``withdrawn_at``, status ``retired`` becomes ``withdrawn``), and every column,
index and constraint named after them follows. ``workspaces.active_revision_id`` and
``relation_set_versions.workspace_draft_id`` follow too, snapshot value owners are recorded as
``publication``, ``base`` and ``change_set``, and stored audit aggregate, action and payload names
are rewritten to the same terms.

SQLite cannot rename a constraint or change a CHECK, so each table is rebuilt: a copy named
``_w2_<table>`` is created from the DDL below, filled, and swapped in, then its indexes are created.
SQLite commits DDL as it runs, so every step first looks at what an interrupted run left: a source
table still in its earlier shape is copied again from the start, and a finished copy whose source
is gone is swapped in. The DDL is copied here rather than taken from the ORM, so this revision keeps
its meaning when ``app/models/database.py`` changes. Automatic upgrade is supported for SQLite only;
another dialect is refused with a recovery instruction (PostgreSQL arrives with 0.11).
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20260926_04"
down_revision = "20260926_03"
branch_labels = None
depends_on = None

# Identifier renames applied to the DDL of every table below, in order.
_NAMES = (
    ("workspace_revisions", "publications"),
    ("workspace_revision", "publication"),
    ("workspace_drafts", "change_sets"),
    ("workspace_draft", "change_set"),
    ("revision_number", "publication_number"),
    ("revision_id", "publication_id"),
    ("draft_id", "change_set_id"),
    ("activated_at", "published_at"),
    ("retired_at", "withdrawn_at"),
)


def _rename(sql: str) -> str:
    for old, new in _NAMES:
        sql = sql.replace(old, new)
    return sql


@dataclass(frozen=True)
class _Table:
    """One table before this revision: its DDL and index DDL, copied from revision 20260926_03."""

    name: str
    ddl: str
    indexes: tuple[str, ...]
    # Text found only in the earlier DDL of a table that keeps its name.
    marker: str | None = None
    # Extra DDL edits beyond identifier renames: (before, after).
    edits: tuple[tuple[str, str], ...] = ()
    # Column value changes: column -> (forward SQL expression, backward SQL expression).
    values: tuple[tuple[str, str, str], ...] = ()

    @property
    def new_name(self) -> str:
        return _rename(self.name)

    @property
    def new_ddl(self) -> str:
        sql = _rename(self.ddl)
        for before, after in self.edits:
            sql = sql.replace(before, after)
        return sql

    @property
    def new_marker(self) -> str | None:
        if self.marker is None:
            return None
        return dict(self.edits).get(self.marker, _rename(self.marker))

    def columns(self) -> list[tuple[str, str]]:
        """(earlier, new) column names in DDL order."""
        return [(name, _rename(name)) for name in _COLUMN.findall(self.ddl)]


_COLUMN = re.compile(
    r'^\s+"?([a-z_]+)"? (?:INTEGER|VARCHAR|DATETIME|DATE|JSON|BOOLEAN|TEXT|NUMERIC)', re.MULTILINE
)


_TABLES = (
    _Table(
        "workspace_revisions",
        """CREATE TABLE workspace_revisions (
    sequence_id INTEGER NOT NULL,
    id VARCHAR(36) NOT NULL,
    workspace_key VARCHAR(160) NOT NULL,
    model_release_id INTEGER NOT NULL,
    revision_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    derived_from_revision_id VARCHAR(36),
    supersedes_revision_id VARCHAR(36),
    created_at DATETIME NOT NULL,
    activated_at DATETIME NOT NULL,
    retired_at DATETIME,
    PRIMARY KEY (sequence_id),
    CONSTRAINT ck_workspace_revision_status CHECK (status IN ('active', 'retired')),
    FOREIGN KEY(model_release_id) REFERENCES model_releases (id) ON DELETE RESTRICT,
    FOREIGN KEY(workspace_key) REFERENCES workspaces ("key") ON DELETE RESTRICT,
    FOREIGN KEY(derived_from_revision_id) REFERENCES workspace_revisions (id) ON DELETE RESTRICT,
    FOREIGN KEY(supersedes_revision_id) REFERENCES workspace_revisions (id) ON DELETE RESTRICT,
    UNIQUE (id),
    CONSTRAINT uq_workspace_revision_number UNIQUE (workspace_key, revision_number)
)""",
        (
            (
                "CREATE INDEX ix_workspace_revisions_derived_from_revision_id "
                "ON workspace_revisions (derived_from_revision_id)"
            ),
            "CREATE UNIQUE INDEX ix_workspace_revisions_id ON workspace_revisions (id)",
            (
                "CREATE INDEX ix_workspace_revisions_model_release_id "
                "ON workspace_revisions (model_release_id)"
            ),
            "CREATE INDEX ix_workspace_revisions_status ON workspace_revisions (status)",
            (
                "CREATE INDEX ix_workspace_revisions_supersedes_revision_id "
                "ON workspace_revisions (supersedes_revision_id)"
            ),
            "CREATE INDEX ix_workspace_revisions_workspace_key ON workspace_revisions (workspace_key)",
        ),
        edits=(("status IN ('active', 'retired')", "status IN ('active', 'withdrawn')"),),
        values=(
            (
                "status",
                "CASE status WHEN 'retired' THEN 'withdrawn' ELSE status END",
                "CASE status WHEN 'withdrawn' THEN 'retired' ELSE status END",
            ),
        ),
    ),
    _Table(
        "workspace_revision_objects",
        """CREATE TABLE workspace_revision_objects (
    sequence_id INTEGER NOT NULL,
    revision_id VARCHAR(36) NOT NULL,
    object_id VARCHAR(36) NOT NULL,
    application_key VARCHAR(160) NOT NULL,
    object_type_key VARCHAR(160) NOT NULL,
    name VARCHAR(500) NOT NULL,
    parent_object_id VARCHAR(36),
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(revision_id) REFERENCES workspace_revisions (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_revision_object UNIQUE (revision_id, object_id)
)""",
        (
            (
                "CREATE INDEX ix_workspace_revision_objects_object_id "
                "ON workspace_revision_objects (object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_objects_parent_name ON workspace_revision_objects "
                "(revision_id, parent_object_id, object_type_key, name, object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_objects_revision_id "
                "ON workspace_revision_objects (revision_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_objects_type_name ON workspace_revision_objects "
                "(revision_id, object_type_key, name, object_id)"
            ),
        ),
    ),
    _Table(
        "workspace_revision_relations",
        """CREATE TABLE workspace_revision_relations (
    sequence_id INTEGER NOT NULL,
    revision_id VARCHAR(36) NOT NULL,
    relation_id VARCHAR(36) NOT NULL,
    relation_type_key VARCHAR(160) NOT NULL,
    from_object_id VARCHAR(36) NOT NULL,
    to_object_id VARCHAR(36) NOT NULL,
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(revision_id) REFERENCES workspace_revisions (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_revision_relation UNIQUE (revision_id, relation_id)
)""",
        (
            (
                "CREATE INDEX ix_workspace_revision_relations_from ON workspace_revision_relations "
                "(revision_id, from_object_id, relation_type_key, relation_id, to_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_relations_relation_id "
                "ON workspace_revision_relations (relation_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_relations_revision_id "
                "ON workspace_revision_relations (revision_id)"
            ),
            (
                "CREATE INDEX ix_workspace_revision_relations_to ON workspace_revision_relations "
                "(revision_id, to_object_id, relation_type_key, relation_id, from_object_id)"
            ),
        ),
    ),
    _Table(
        "workspace_draft_bases",
        """CREATE TABLE workspace_draft_bases (
    id VARCHAR(36) NOT NULL,
    workspace_key VARCHAR(160) NOT NULL,
    model_release_id INTEGER NOT NULL,
    model_runtime_version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(workspace_key) REFERENCES workspaces ("key") ON DELETE RESTRICT,
    FOREIGN KEY(model_release_id) REFERENCES model_releases (id) ON DELETE RESTRICT
)""",
        (
            (
                "CREATE INDEX ix_workspace_draft_bases_model_release_id "
                "ON workspace_draft_bases (model_release_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_bases_workspace_key "
                "ON workspace_draft_bases (workspace_key)"
            ),
        ),
    ),
    _Table(
        "workspace_draft_base_objects",
        """CREATE TABLE workspace_draft_base_objects (
    sequence_id INTEGER NOT NULL,
    base_id VARCHAR(36) NOT NULL,
    object_id VARCHAR(36) NOT NULL,
    application_key VARCHAR(160) NOT NULL,
    object_type_key VARCHAR(160) NOT NULL,
    name VARCHAR(500) NOT NULL,
    parent_object_id VARCHAR(36),
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(base_id) REFERENCES workspace_draft_bases (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_draft_base_object UNIQUE (base_id, object_id)
)""",
        (
            (
                "CREATE INDEX ix_workspace_draft_base_objects_base_id "
                "ON workspace_draft_base_objects (base_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_objects_object_id "
                "ON workspace_draft_base_objects (object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_objects_object_type_key "
                "ON workspace_draft_base_objects (object_type_key)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_objects_parent_name ON workspace_draft_base_objects "
                "(base_id, parent_object_id, object_type_key, name, object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_objects_parent_object_id "
                "ON workspace_draft_base_objects (parent_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_objects_type_name ON workspace_draft_base_objects "
                "(base_id, object_type_key, name, object_id)"
            ),
        ),
    ),
    _Table(
        "workspace_draft_base_relations",
        """CREATE TABLE workspace_draft_base_relations (
    sequence_id INTEGER NOT NULL,
    base_id VARCHAR(36) NOT NULL,
    relation_id VARCHAR(36) NOT NULL,
    relation_type_key VARCHAR(160) NOT NULL,
    from_object_id VARCHAR(36) NOT NULL,
    to_object_id VARCHAR(36) NOT NULL,
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(base_id) REFERENCES workspace_draft_bases (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_draft_base_relation UNIQUE (base_id, relation_id)
)""",
        (
            (
                "CREATE INDEX ix_workspace_draft_base_relations_base_id "
                "ON workspace_draft_base_relations (base_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_from ON workspace_draft_base_relations "
                "(base_id, from_object_id, relation_type_key, relation_id, to_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_from_object_id "
                "ON workspace_draft_base_relations (from_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_relation_id "
                "ON workspace_draft_base_relations (relation_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_relation_type_key "
                "ON workspace_draft_base_relations (relation_type_key)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_to ON workspace_draft_base_relations "
                "(base_id, to_object_id, relation_type_key, relation_id, from_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_base_relations_to_object_id "
                "ON workspace_draft_base_relations (to_object_id)"
            ),
        ),
    ),
    _Table(
        "workspace_drafts",
        """CREATE TABLE workspace_drafts (
    sequence_id INTEGER NOT NULL,
    id VARCHAR(36) NOT NULL,
    workspace_key VARCHAR(160) NOT NULL,
    model_release_id INTEGER NOT NULL,
    derived_from_revision_id VARCHAR(36),
    version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    name VARCHAR(300),
    base_id VARCHAR(36),
    PRIMARY KEY (sequence_id),
    CONSTRAINT fk_workspace_drafts_base_id_workspace_draft_bases FOREIGN KEY(base_id) REFERENCES workspace_draft_bases (id) ON DELETE RESTRICT,
    UNIQUE (id),
    FOREIGN KEY(model_release_id) REFERENCES model_releases (id) ON DELETE RESTRICT,
    FOREIGN KEY(derived_from_revision_id) REFERENCES workspace_revisions (id) ON DELETE RESTRICT,
    FOREIGN KEY(workspace_key) REFERENCES workspaces ("key") ON DELETE RESTRICT
)""",
        (
            "CREATE INDEX ix_workspace_drafts_base_id ON workspace_drafts (base_id)",
            (
                "CREATE INDEX ix_workspace_drafts_derived_from_revision_id "
                "ON workspace_drafts (derived_from_revision_id)"
            ),
            "CREATE UNIQUE INDEX ix_workspace_drafts_id ON workspace_drafts (id)",
            "CREATE INDEX ix_workspace_drafts_model_release_id ON workspace_drafts (model_release_id)",
            "CREATE INDEX ix_workspace_drafts_workspace_key ON workspace_drafts (workspace_key)",
        ),
    ),
    _Table(
        "workspace_draft_objects",
        """CREATE TABLE workspace_draft_objects (
    sequence_id INTEGER NOT NULL,
    draft_id VARCHAR(36) NOT NULL,
    object_id VARCHAR(36) NOT NULL,
    application_key VARCHAR(160) NOT NULL,
    object_type_key VARCHAR(160) NOT NULL,
    name VARCHAR(500) NOT NULL,
    parent_object_id VARCHAR(36),
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(draft_id) REFERENCES workspace_drafts (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_draft_object UNIQUE (draft_id, object_id)
)""",
        (
            "CREATE INDEX ix_workspace_draft_objects_draft_id ON workspace_draft_objects (draft_id)",
            "CREATE INDEX ix_workspace_draft_objects_object_id ON workspace_draft_objects (object_id)",
        ),
    ),
    _Table(
        "workspace_draft_relations",
        """CREATE TABLE workspace_draft_relations (
    sequence_id INTEGER NOT NULL,
    draft_id VARCHAR(36) NOT NULL,
    relation_id VARCHAR(36) NOT NULL,
    relation_type_key VARCHAR(160) NOT NULL,
    from_object_id VARCHAR(36) NOT NULL,
    to_object_id VARCHAR(36) NOT NULL,
    attributes JSON NOT NULL,
    version INTEGER NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    PRIMARY KEY (sequence_id),
    FOREIGN KEY(draft_id) REFERENCES workspace_drafts (id) ON DELETE CASCADE,
    CONSTRAINT uq_workspace_draft_relation UNIQUE (draft_id, relation_id)
)""",
        (
            (
                "CREATE INDEX ix_workspace_draft_relations_draft_id "
                "ON workspace_draft_relations (draft_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_relations_from ON workspace_draft_relations "
                "(draft_id, from_object_id, relation_type_key, relation_id, to_object_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_relations_relation_id "
                "ON workspace_draft_relations (relation_id)"
            ),
            (
                "CREATE INDEX ix_workspace_draft_relations_to ON workspace_draft_relations "
                "(draft_id, to_object_id, relation_type_key, relation_id, from_object_id)"
            ),
        ),
    ),
    _Table(
        "relation_set_versions",
        """CREATE TABLE relation_set_versions (
    sequence_id INTEGER NOT NULL,
    workspace_key VARCHAR(160) NOT NULL,
    workspace_draft_id VARCHAR(36),
    relation_type_key VARCHAR(160) NOT NULL,
    from_object_type_key VARCHAR(160) NOT NULL,
    to_object_type_key VARCHAR(160) NOT NULL,
    anchor_object_id VARCHAR(36) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (sequence_id),
    CONSTRAINT ck_rsv_direction CHECK (direction IN ('outgoing', 'incoming')),
    FOREIGN KEY(workspace_key) REFERENCES workspaces ("key") ON DELETE CASCADE,
    FOREIGN KEY(workspace_draft_id) REFERENCES workspace_drafts (id) ON DELETE CASCADE,
    CONSTRAINT uq_relation_set_version UNIQUE (workspace_key, workspace_draft_id, relation_type_key, from_object_type_key, to_object_type_key, anchor_object_id, direction)
)""",
        (
            (
                "CREATE INDEX ix_relation_set_versions_workspace_key "
                "ON relation_set_versions (workspace_key)"
            ),
            (
                "CREATE INDEX ix_relation_set_versions_workspace_draft_id "
                "ON relation_set_versions (workspace_draft_id)"
            ),
            (
                "CREATE INDEX ix_relation_set_versions_anchor_object_id "
                "ON relation_set_versions (anchor_object_id)"
            ),
            (
                "CREATE UNIQUE INDEX uq_relation_set_version_live ON relation_set_versions "
                "(workspace_key, relation_type_key, from_object_type_key, to_object_type_key, "
                "anchor_object_id, direction) WHERE workspace_draft_id IS NULL"
            ),
        ),
        marker="workspace_draft_id",
    ),
    _Table(
        "workspaces",
        """CREATE TABLE workspaces (
    "key" VARCHAR(160) NOT NULL,
    label VARCHAR(300) NOT NULL,
    status VARCHAR(20) NOT NULL,
    version INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    active_revision_id VARCHAR(36),
    PRIMARY KEY ("key"),
    CONSTRAINT ck_workspace_status CHECK (status IN ('active', 'retired')),
    CONSTRAINT fk_workspaces_active_revision_id_workspace_revisions FOREIGN KEY(active_revision_id) REFERENCES workspace_revisions (id) ON DELETE RESTRICT
)""",
        (
            "CREATE INDEX ix_workspaces_active_revision_id ON workspaces (active_revision_id)",
            "CREATE INDEX ix_workspaces_status ON workspaces (status)",
        ),
        marker="active_revision_id",
    ),
    _Table(
        "snapshot_attribute_values",
        """CREATE TABLE snapshot_attribute_values (
    sequence_id INTEGER NOT NULL,
    owner_kind VARCHAR(10) NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    object_id VARCHAR(36) NOT NULL,
    attribute_type_key VARCHAR(160) NOT NULL,
    value_type VARCHAR(40) NOT NULL,
    text_value TEXT,
    integer_value INTEGER,
    decimal_value NUMERIC,
    boolean_value BOOLEAN,
    date_value DATE,
    datetime_value DATETIME,
    json_value JSON,
    PRIMARY KEY (sequence_id),
    CONSTRAINT ck_snapshot_attribute_owner_kind CHECK (owner_kind IN ('revision', 'base', 'draft')),
    CONSTRAINT uq_snapshot_attribute_value UNIQUE (owner_id, object_id, attribute_type_key)
)""",
        (
            (
                "CREATE INDEX ix_snapshot_attribute_values_owner_key "
                "ON snapshot_attribute_values (owner_id, attribute_type_key)"
            ),
            (
                "CREATE INDEX ix_snapshot_attribute_values_owner_key_text "
                "ON snapshot_attribute_values (owner_id, attribute_type_key, text_value, object_id)"
            ),
        ),
        marker="owner_kind IN ('revision', 'base', 'draft')",
        edits=(
            ("owner_kind VARCHAR(10)", "owner_kind VARCHAR(20)"),
            (
                "owner_kind IN ('revision', 'base', 'draft')",
                "owner_kind IN ('publication', 'base', 'change_set')",
            ),
        ),
        values=(
            (
                "owner_kind",
                (
                    "CASE owner_kind WHEN 'revision' THEN 'publication' "
                    "WHEN 'draft' THEN 'change_set' ELSE owner_kind END"
                ),
                (
                    "CASE owner_kind WHEN 'publication' THEN 'revision' "
                    "WHEN 'change_set' THEN 'draft' ELSE owner_kind END"
                ),
            ),
        ),
    ),
)

# The trigram index over snapshot text values (20260926_03) lives on triggers of its source table,
# which the rebuild drops with the table.
_SEARCH_INDEX = "snapshot_attribute_values_text_search"
_SEARCH_SOURCE = "snapshot_attribute_values"

# Stored audit names: (aggregate type, action) before and after. ``None`` keeps the action.
_AUDIT_NAMES = (
    (("workspace-draft", None), ("change-set", None)),
    (("object-draft", None), ("change-set-object", None)),
    (("workspace-revision", "activated"), ("publication", "published")),
    (("workspace-revision", None), ("publication", None)),
    (("workspace", "publication-retired"), ("workspace", "publication-withdrawn")),
)
# Top-level ``changes`` keys of non-model audit events.
_AUDIT_KEYS = (
    ("workspaceDraftId", "changeSetId"),
    ("workspaceRevisionId", "publicationId"),
    ("derivedFromRevisionId", "derivedFromPublicationId"),
    ("supersedesRevisionId", "supersedesPublicationId"),
    ("retiredRevisionId", "withdrawnPublicationId"),
    ("revisionNumber", "publicationNumber"),
)
# The publish event named its change set ``draftId``; every other event ``workspaceDraftId``.
_PUBLISHED_DRAFT_KEY = ("draftId", "changeSetId")


def upgrade() -> None:
    bind = op.get_bind()
    if _needs_upgrade(bind) and bind.dialect.name != "sqlite":
        raise RuntimeError(
            "Renaming workspace drafts and revisions to change sets and publications is supported "
            "automatically only for SQLite. Stop application processes, take a consistent backup, "
            "and report the database engine and current Alembic revision."
        )
    if bind.dialect.name != "sqlite":
        return
    for table in _TABLES:
        forward = {column: expression for column, expression, _backward in table.values}
        _swap(
            bind,
            source=table.name,
            source_marker=table.marker,
            target=table.new_name,
            target_ddl=table.new_ddl,
            target_indexes=[_rename(index) for index in table.indexes],
            columns=[(new, forward.get(old, f'"{old}"')) for old, new in table.columns()],
        )
    _restore_search_index(bind)
    _rewrite_audit(bind, forward=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    for table in reversed(_TABLES):
        backward = {_rename(column): expression for column, _forward, expression in table.values}
        _swap(
            bind,
            source=table.new_name,
            source_marker=table.new_marker,
            target=table.name,
            target_ddl=table.ddl,
            target_indexes=list(table.indexes),
            columns=[(old, backward.get(new, f'"{new}"')) for old, new in table.columns()],
        )
    _restore_search_index(bind)
    _rewrite_audit(bind, forward=False)


def _needs_upgrade(bind: sa.Connection) -> bool:
    return any(table.name in sa.inspect(bind).get_table_names() for table in _TABLES[:9])


def _table_sql(bind: sa.Connection, name: str) -> str | None:
    return bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": name},
    ).scalar()


def _swap(
    bind: sa.Connection,
    *,
    source: str,
    source_marker: str | None,
    target: str,
    target_ddl: str,
    target_indexes: list[str],
    columns: list[tuple[str, str]],
) -> None:
    """Move ``source`` into ``target`` through ``_w2_<target>``; resumes an interrupted run.

    ``columns`` pairs each target column with the SQL expression over ``source`` that fills it.
    """
    staging = f"_w2_{target}"
    source_sql = _table_sql(bind, source)
    source_pending = source_sql is not None and (
        source_marker is None or source_marker in source_sql
    )
    if source_pending:
        expected = {expression.strip('"') for _column, expression in columns if '"' in expression}
        existing = {row[1] for row in bind.execute(sa.text(f'PRAGMA table_info("{source}")'))}
        if not expected <= existing:
            raise RuntimeError(
                f"{source} lacks columns {sorted(expected - existing)} from an earlier interrupted "
                "or manual change; restore the pre-upgrade backup and rerun the upgrade"
            )
        bind.execute(sa.text(f'DROP TABLE IF EXISTS "{staging}"'))
        prefix = f"CREATE TABLE {target} ("
        if not target_ddl.startswith(prefix):
            raise RuntimeError(f"Migration DDL for {target} is malformed")
        bind.execute(sa.text(f'CREATE TABLE "{staging}" (' + target_ddl[len(prefix) :]))
        targets = ", ".join(f'"{column}"' for column, _expression in columns)
        expressions = ", ".join(expression for _column, expression in columns)
        bind.execute(
            sa.text(f'INSERT INTO "{staging}" ({targets}) SELECT {expressions} FROM "{source}"')
        )
        bind.execute(sa.text(f'DROP TABLE "{source}"'))
    if _table_sql(bind, staging) is not None:
        bind.execute(sa.text(f'ALTER TABLE "{staging}" RENAME TO "{target}"'))
    elif _table_sql(bind, target) is None:
        raise RuntimeError(
            f"Neither {source} nor {target} exists; restore the pre-upgrade backup and rerun the "
            "upgrade"
        )
    for index in target_indexes:
        bind.execute(sa.text(index.replace(" INDEX ", " INDEX IF NOT EXISTS ", 1)))


def _restore_search_index(bind: sa.Connection) -> None:
    """Recreate the triggers the rebuild dropped and refill the index from its source."""
    exists = bind.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": _SEARCH_INDEX},
    ).scalar()
    if not exists:
        return
    index, source, value = _SEARCH_INDEX, _SEARCH_SOURCE, "text_value"
    for statement in (
        *(f"DROP TRIGGER IF EXISTS {index}_{name}" for name in ("insert", "delete", "update")),
        (
            f"CREATE TRIGGER {index}_insert AFTER INSERT ON {source} BEGIN "
            f"INSERT INTO {index}(rowid, {value}) VALUES (new.sequence_id, new.{value}); END"
        ),
        (
            f"CREATE TRIGGER {index}_delete AFTER DELETE ON {source} BEGIN "
            f"INSERT INTO {index}({index}, rowid, {value}) "
            f"VALUES ('delete', old.sequence_id, old.{value}); END"
        ),
        (
            f"CREATE TRIGGER {index}_update AFTER UPDATE OF {value} ON {source} BEGIN "
            f"INSERT INTO {index}({index}, rowid, {value}) "
            f"VALUES ('delete', old.sequence_id, old.{value}); "
            f"INSERT INTO {index}(rowid, {value}) VALUES (new.sequence_id, new.{value}); END"
        ),
        f"INSERT INTO {index}({index}) VALUES ('rebuild')",
    ):
        bind.execute(sa.text(statement))


def _rewrite_audit(bind: sa.Connection, *, forward: bool) -> None:
    names = _AUDIT_NAMES if forward else tuple((after, before) for before, after in _AUDIT_NAMES)
    for (aggregate, action), (new_aggregate, new_action) in names:
        statement = "UPDATE audit_events SET aggregate_type = :new_aggregate"
        parameters = {"aggregate": aggregate, "new_aggregate": new_aggregate}
        if new_action:
            statement += ", action = :new_action"
            parameters["new_action"] = new_action
        statement += " WHERE aggregate_type = :aggregate"
        if action:
            statement += " AND action = :action"
            parameters["action"] = action
        bind.execute(sa.text(statement), parameters)
    keys = _AUDIT_KEYS if forward else tuple((new, old) for old, new in _AUDIT_KEYS)
    published = "publication" if forward else "workspace-revision"

    def rename_keys(aggregate: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        mapping = dict(keys)
        if aggregate == published:
            old, new = _PUBLISHED_DRAFT_KEY
            mapping.pop("changeSetId", None)
            mapping.update({old: new} if forward else {new: old})
        return lambda changes: {mapping.get(key, key): value for key, value in changes.items()}

    candidates = [old for old, _new in keys] + [
        _PUBLISHED_DRAFT_KEY[0] if forward else _PUBLISHED_DRAFT_KEY[1]
    ]
    pattern = " OR ".join(f"changes LIKE :k{i}" for i in range(len(candidates)))
    rows = bind.execute(
        sa.text(
            "SELECT sequence_id, aggregate_type, changes FROM audit_events "
            f"WHERE aggregate_type NOT LIKE 'model%' AND ({pattern})"
        ),
        {f"k{i}": f'%"{key}"%' for i, key in enumerate(candidates)},
    ).all()
    for sequence_id, aggregate, changes in rows:
        value = json.loads(changes) if isinstance(changes, str) else changes
        if not isinstance(value, dict):
            continue
        renamed = rename_keys(aggregate)(value)
        if renamed != value:
            bind.execute(
                sa.text("UPDATE audit_events SET changes = :changes WHERE sequence_id = :id"),
                {"changes": json.dumps(renamed), "id": sequence_id},
            )
