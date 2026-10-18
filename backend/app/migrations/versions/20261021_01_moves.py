"""Selection and the dry run of a move (Product 0.11 X2, D114–D123).

``jobs.kind`` gains ``move``. ``pgcrypto`` is installed for its SHA-1, and
``rdm_counterpart(workspace_key, object_id)`` derives in PostgreSQL the ID another workspace's
record has in ``workspace_key``, the same as ``records/counterparts.counterpart`` (D120): the
name-based UUID of ``{workspaceKey}/{id}`` in the counterparts' namespace, marked as version 4.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261020_01``.
"""

from alembic import op

revision = "20261021_01"
down_revision = "20261020_01"
branch_labels = None
depends_on = None

KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference', 'move')"
)
OLD_KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference')"
)

# SHA-1 over the namespace's bytes and the name (uuid5), the first 16 bytes with the version
# nibble set to 4 and the variant to RFC 4122, as ``UUID(bytes=..., version=4)`` sets them.
COUNTERPART = r"""
CREATE FUNCTION rdm_counterpart(workspace_key text, object_id text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT encode(
        set_byte(set_byte(h, 6, (get_byte(h, 6) & 15) | 64), 8, (get_byte(h, 8) & 63) | 128),
        'hex')::uuid::text
    FROM (SELECT substring(digest(
        '\x2218e355f6274a22a009bebe5423891c'::bytea
            || convert_to(workspace_key || '/' || object_id, 'UTF8'),
        'sha1') FROM 1 FOR 16) AS h) hashed
$$
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(COUNTERPART)
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'move'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.execute("DROP FUNCTION rdm_counterpart(text, text)")
