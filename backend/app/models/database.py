from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from ..common.time import as_utc
from .search_index import (
    CHANGE_SET_BASE_NAMES,
    CHANGE_SET_NAMES,
    LIVE_NAMES,
    LIVE_VALUES,
    PUBLICATION_NAMES,
    SNAPSHOT_VALUES,
    search_index,
)


class UTCDateTime(TypeDecorator[datetime]):
    """A timestamp stored as UTC and always read back as an aware UTC ``datetime``.

    PostgreSQL reads ``timestamptz`` back in the session's time zone. Converting on the way in and
    out keeps the instant and lets every API response carry the same explicit offset, ``+00:00``,
    whatever the server's or session's zone.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return as_utc(value) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return as_utc(value) if value is not None else None


# The audit entries that are security events (0.12 Z4, D317, D318): outside every workspace.
SECURITY_AGGREGATES = (
    "user",
    "group",
    "role",
    "grant",
    "client",
    "token-signing-key",
    "sign-in",
    "sign-in-provider",
    "mail-settings",
    "approval-policy",
)
SECURITY_AGGREGATES_SQL = ", ".join(f"'{item}'" for item in SECURITY_AGGREGATES)


class Base(DeclarativeBase):
    pass


class ModelRelease(Base):
    __tablename__ = "model_releases"
    __table_args__ = (
        UniqueConstraint("release_key", "release_version", name="uq_model_release_identity"),
        CheckConstraint("status IN ('active', 'retired')", name="ck_model_release_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    release_key: Mapped[str] = mapped_column(String(160), index=True)
    release_name: Mapped[str] = mapped_column(String(300))
    release_version: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(40))
    model_hash: Mapped[str] = mapped_column(String(64), unique=True)
    model_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    installed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    # A retired release is never chosen again; what runs on it keeps running (0.12 MR1, D457).
    # The snapshot stays immutable: only the status and its version change.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active", index=True
    )
    status_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    retired_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)




class ModelDraft(Base):
    __tablename__ = "model_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(300))
    base_model_release_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_releases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    # The draft's import profile (0.10 A5, D75), changed only by operations; ``None`` for none.
    profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ModelDraftOperation(Base):
    """One operation applied to a model draft, in its history (0.10 A2, ADR-041)."""

    __tablename__ = "model_draft_operations"
    __table_args__ = (
        UniqueConstraint("draft_id", "sequence", name="uq_model_draft_operations_sequence"),
        Index("ix_model_draft_operations_step", "draft_id", "step"),
        CheckConstraint(
            "num_nonnulls(author_user_id, author_client_id) <= 1", name="ck_model_draft_operations_author_one"
        ),
        Index(
            "ix_model_draft_operations_author_user",
            "author_user_id",
            postgresql_where=text("author_user_id IS NOT NULL"),
        ),
        Index(
            "ix_model_draft_operations_author_client",
            "author_client_id",
            postgresql_where=text("author_client_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("model_drafts.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    inverse: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Who applied it (0.12 Z4, D315); nobody for one from before Z4.
    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    author_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    origin: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # The elements the entry created, re-keyed and named, as element atoms (D8's dependants).
    effects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    undone_by_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'retired')", name="ck_workspace_status"),
    )

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    label: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    active_publication_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "publications.id",
            name="fk_workspaces_active_publication_id_publications",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    # The workspace's feed: the last position a live write took (Base 0.9 F1, INTEGRATION_API F3).
    feed_position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class WorkspaceModel(Base):
    """The release a workspace runs (Product 0.11 M1, ADR-042, D30), with the assignment's version.

    A row of its own rather than columns on ``workspaces``: a write rechecks its workspace's release
    under a share lock on this row as it commits (``registry.require_resolved_release``), and
    activation holds it for update, so neither waits on the locks live writes and publishing take
    on the workspace row. A trigger keeps ``unique_attribute_values`` following each row's release.
    """

    __tablename__ = "workspace_models"

    workspace_key: Mapped[str] = mapped_column(
        ForeignKey(
            "workspaces.key",
            name="fk_workspace_models_workspace_key_workspaces",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey(
            "model_releases.id",
            name="fk_workspace_models_model_release_id_model_releases",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class WorkspaceRuntimeState(Base):
    __tablename__ = "workspace_runtime_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_workspace_runtime_state_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ApplicationMeta(Base):
    __tablename__ = "model_applications"
    __table_args__ = (UniqueConstraint("model_release_id", "key", name="uq_model_application_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class AttributeTypeMeta(Base):
    __tablename__ = "model_attribute_types"
    __table_args__ = (
        UniqueConstraint("model_release_id", "key", name="uq_model_attribute_type_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300))
    value_type: Mapped[str] = mapped_column(String(40))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class ObjectTypeMeta(Base):
    __tablename__ = "model_object_types"
    __table_args__ = (UniqueConstraint("model_release_id", "key", name="uq_model_object_type_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class ObjectTypeAttributeMeta(Base):
    __tablename__ = "model_object_type_attributes"
    __table_args__ = (
        UniqueConstraint(
            "model_release_id",
            "object_type_key",
            "attribute_type_key",
            name="uq_model_object_type_attribute",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    attribute_type_key: Mapped[str] = mapped_column(String(160), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class RelationTypeMeta(Base):
    __tablename__ = "model_relation_types"
    __table_args__ = (
        UniqueConstraint("model_release_id", "key", name="uq_model_relation_type_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(160))
    reverse_key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300))
    reverse_name: Mapped[str] = mapped_column(String(300))
    is_oriented: Mapped[bool] = mapped_column(Boolean, default=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class ObjectTypeRelationMeta(Base):
    __tablename__ = "model_object_type_relations"
    __table_args__ = (
        UniqueConstraint(
            "model_release_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            name="uq_model_object_type_relation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    to_object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    cardinality: Mapped[str] = mapped_column(String(40))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class ApplicationObjectTypeMeta(Base):
    __tablename__ = "model_application_object_types"
    __table_args__ = (
        UniqueConstraint(
            "model_release_id",
            "application_key",
            "object_type_key",
            name="uq_model_application_object_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    application_key: Mapped[str] = mapped_column(String(160), index=True)
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)


class ViewDefinitionMeta(Base):
    __tablename__ = "model_view_definitions"
    __table_args__ = (
        UniqueConstraint("model_release_id", "application_key", "key", name="uq_model_view_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="CASCADE"), index=True
    )
    application_key: Mapped[str] = mapped_column(String(160), index=True)
    key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300))
    view_type: Mapped[str] = mapped_column(String(60))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)


class RdmObject(Base):
    __tablename__ = "objects"
    __table_args__ = (
        search_index(LIVE_NAMES),
        # Name-ordered pages by type and by parent seek to their position (migration 20260925_03).
        Index("ix_objects_type_name", "workspace_key", "object_type_key", "name", "sequence_id"),
        Index(
            "ix_objects_parent_name",
            "workspace_key",
            "parent_object_id",
            "object_type_key",
            "name",
            "sequence_id",
        ),
        # An exact lookup ignoring case seeks the name (0.9 C4, 20261005_01).
        Index("ix_objects_workspace_lower_name", "workspace_key", func.lower(literal_column("name"))),
        # A lookup's contains match reads the names of its types in its workspace in one probe
        # (0.9 C14, 20261005_02; btree_gin for the key columns).
        Index(
            "ix_objects_type_name_trigram",
            "workspace_key",
            "object_type_key",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), default="default", index=True
    )
    application_key: Mapped[str] = mapped_column(String(160), index=True)
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    parent_object_id: Mapped[str | None] = mapped_column(
        ForeignKey("objects.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(500), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    @property
    def object_id(self) -> str:
        """The public ID, under the name change set and publication rows give it."""
        return self.id


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint("workspace_key", "publication_number", name="uq_publication_number"),
        CheckConstraint("status IN ('active', 'withdrawn')", name="ck_publication_status"),
        CheckConstraint(
            "num_nonnulls(published_by_user_id, published_by_client_id) <= 1", name="ck_publications_published_by_one"
        ),
        Index(
            "ix_publications_published_by_user",
            "published_by_user_id",
            postgresql_where=text("published_by_user_id IS NOT NULL"),
        ),
        Index(
            "ix_publications_published_by_client",
            "published_by_client_id",
            postgresql_where=text("published_by_client_id IS NOT NULL"),
        ),
        CheckConstraint(
            "num_nonnulls(withdrawn_by_user_id, withdrawn_by_client_id) <= 1", name="ck_publications_withdrawn_by_one"
        ),
        Index(
            "ix_publications_withdrawn_by_user",
            "withdrawn_by_user_id",
            postgresql_where=text("withdrawn_by_user_id IS NOT NULL"),
        ),
        Index(
            "ix_publications_withdrawn_by_client",
            "withdrawn_by_client_id",
            postgresql_where=text("withdrawn_by_client_id IS NOT NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    publication_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    derived_from_publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    supersedes_publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # The position of its ``published`` feed entry (Base 0.9 F1); none before that revision.
    feed_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Who published and who withdrew it (0.12 Z4, D315); neither from before Z4.
    published_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    published_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    withdrawn_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    withdrawn_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )


class ChangeSet(Base):
    __tablename__ = "change_sets"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(created_by_user_id, created_by_client_id) <= 1", name="ck_change_sets_created_by_one"
        ),
        Index(
            "ix_change_sets_created_by_user",
            "created_by_user_id",
            postgresql_where=text("created_by_user_id IS NOT NULL"),
        ),
        Index(
            "ix_change_sets_created_by_client",
            "created_by_client_id",
            postgresql_where=text("created_by_client_id IS NOT NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    derived_from_publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # A current-live base is deliberately not a publication.  Legacy change sets retain a
    # null base id and continue to resolve their original empty/publication source.
    base_id: Mapped[str | None] = mapped_column(
        ForeignKey("change_set_bases.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    # A move's deletion change set in its source workspace: the target's change set holding the
    # copy, which must publish first (0.11 X3, D135).
    waits_for_change_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Who created it (0.12 Z4, D315); nobody for one from before Z4.
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )


class ApprovalPolicy(Base):
    """A workspace's approval policy (0.12 A1, D425): absent means both flags off. ``second_person``
    needs ``require_approval``."""

    __tablename__ = "approval_policies"
    __table_args__ = (
        CheckConstraint(
            "NOT second_person OR require_approval", name="ck_approval_policies_second_person"
        ),
    )

    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), primary_key=True
    )
    require_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    second_person: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ChangeSetSubmission(Base):
    """A change set submitted for publication (0.12 A1, D427): one row per submission.

    ``change_set_id`` is no foreign key: an approved change set is deleted by its publication and
    the request stays as history, with the change set's name as it was. ``state`` is ``submitted``
    until it is withdrawn, approved or sent back; a change set is submitted while its latest
    submission is.
    """

    __tablename__ = "change_set_submissions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('submitted', 'withdrawn', 'approved', 'sentBack')",
            name="ck_change_set_submissions_state",
        ),
        CheckConstraint(
            "num_nonnulls(submitted_by_user_id, submitted_by_client_id) <= 1",
            name="ck_change_set_submissions_submitted_by_one",
        ),
        Index("ix_change_set_submissions_change_set", "change_set_id", "sequence_id"),
        Index("ix_change_set_submissions_workspace", "workspace_key", "sequence_id"),
        # A change set is submitted at most once at a time.
        Index(
            "uq_change_set_submissions_open",
            "change_set_id",
            unique=True,
            postgresql_where=text("state = 'submitted'"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False
    )
    change_set_id: Mapped[str] = mapped_column(String(36), nullable=False)
    change_set_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    version_submitted: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="submitted")
    # The publication an approval made.
    publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=True
    )


class ChangeSetDecision(Base):
    """One decision on a submission (0.12 A1, D427, D242): who, when, the change set's version,
    the outcome (``approve`` or ``sendBack``) and the comment."""

    __tablename__ = "change_set_decisions"
    __table_args__ = (
        CheckConstraint("outcome IN ('approve', 'sendBack')", name="ck_change_set_decisions_outcome"),
        CheckConstraint(
            "num_nonnulls(decided_by_user_id, decided_by_client_id) <= 1",
            name="ck_change_set_decisions_decided_by_one",
        ),
        Index("ix_change_set_decisions_submission", "submission_sequence_id", "sequence_id"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    submission_sequence_id: Mapped[int] = mapped_column(
        ForeignKey("change_set_submissions.sequence_id", ondelete="CASCADE"), nullable=False
    )
    decided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class Notification(Base):
    """A notice in a person's or client's inbox (0.12 A2, D233): a request waiting for their
    approval, a decision on theirs, a job they started that finished. ``details`` holds what a
    client words the notice from (names, the comment, the job's kind and state); it is read as it
    was when the notice was made. Triggers send the stream its wake-up (revision ``20261111_01``)
    and close a job's request for confirmation once answered (``20261116_01``); the job worker's
    sweep deletes notices older than 90 days (0.12 NT1)."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("num_nonnulls(user_id, client_id) = 1", name="ck_notifications_one_principal"),
        Index("ix_notifications_user", "user_id", "sequence_id"),
        Index("ix_notifications_client", "client_id", "sequence_id"),
        Index(
            "ix_notifications_unread_user", "user_id", "sequence_id", postgresql_where=text("read_at IS NULL")
        ),
        Index(
            "ix_notifications_unread_client",
            "client_id",
            "sequence_id",
            postgresql_where=text("read_at IS NULL"),
        ),
        Index("ix_notifications_subject", "subject_kind", "subject_id"),
        Index("ix_notifications_created", "created_at"),
        Index(
            "ix_notifications_unmailed",
            "sequence_id",
            postgresql_where=text("mailed_at IS NULL AND read_at IS NULL AND user_id IS NOT NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False
    )
    subject_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # When the mail sender handled the notice (0.12 M2, D432): mailed, or passed over.
    mailed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class WorkspaceEventHead(Base):
    """How far a workspace's events are numbered (0.12 A2): the position of the newest one."""

    __tablename__ = "workspace_event_heads"

    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkspaceEvent(Base):
    """A change-set event of a workspace (0.12 A2, D233): ``change-set.submitted``,
    ``change-set.approved`` or ``change-set.sent-back``, delivered to subscriptions with the
    workspace source. ``payload`` is the event as sent; ``position`` numbers a workspace's events
    without gaps."""

    __tablename__ = "workspace_events"
    __table_args__ = (
        UniqueConstraint("workspace_key", "position", name="uq_workspace_event_order"),
        Index("ix_workspace_events_occurred", "occurred_at"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    change_set_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class RecordOrigin(Base):
    """Where a record a move created came from (0.11 X3, D23, D132): the record copied, in its
    workspace. No foreign keys: written when the move loads its change set, kept when that change
    set is discarded; every lookup joins a record that exists."""

    __tablename__ = "record_origins"

    object_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    origin_workspace_key: Mapped[str] = mapped_column(String(160), nullable=False)
    origin_object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.now()
    )


class AttributeValue(Base):
    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("object_id", "attribute_type_key", name="uq_object_attribute_value"),
        # A live write's unique-value check and a key reference seek to the value (0.9 B2,
        # 20261001_01), as a change set's do through ix_snapshot_attribute_values_owner_key_text.
        Index("ix_attribute_values_key_text", "attribute_type_key", "text_value", "object_id"),
        # An attribute sort reads the records with a value in value order (0.9 C3a, 20261004_04).
        *(
            Index(f"ix_attribute_values_key_{name}", "attribute_type_key", f"{name}_value", "object_id")
            for name in ("integer", "decimal", "boolean", "date", "datetime")
        ),
        search_index(LIVE_VALUES),
        # An exact lookup ignoring case seeks the text value (0.9 C4, 20261005_01).
        Index(
            "ix_attribute_values_key_lower_text",
            "attribute_type_key",
            func.lower(literal_column("text_value")),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    object_id: Mapped[str] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True)
    attribute_type_key: Mapped[str] = mapped_column(String(160), index=True)
    value_type: Mapped[str] = mapped_column(String(40))
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    integer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decimal_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    datetime_value: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    json_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    value_source: Mapped[str] = mapped_column(String(40), default="own")
    version: Mapped[int] = mapped_column(Integer, default=1)


class UniqueAttributeValue(Base):
    """A live value of an attribute its workspace's release declares ``unique``, held once per
    workspace (ADR-010, 0.9 J2a, D75, 0.11 D28).

    PostgreSQL keeps these rows: triggers on ``attribute_values`` add them as values are written,
    the ``attribute_values`` cascade removes them, and a trigger on ``workspace_models`` follows
    each workspace's release. No code writes them; ``engine/indexes/unique_values.py`` reads them at the
    end of a write. The constraint is deferred, so values handed between records within one write
    pass; it holds at commit whatever wrote the values.
    """

    __tablename__ = "unique_attribute_values"
    __table_args__ = (
        UniqueConstraint(
            "workspace_key",
            "attribute_type_key",
            "value_digest",
            name="uq_unique_attribute_values",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_unique_attribute_values_object_id", "object_id"),
    )

    value_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_values.sequence_id", ondelete="CASCADE"), primary_key=True
    )
    workspace_key: Mapped[str] = mapped_column(String(160))
    attribute_type_key: Mapped[str] = mapped_column(String(160))
    object_id: Mapped[str] = mapped_column(String(36))
    # SHA-256 of the value's canonical JSON (``rdm_value_json``): equal values, equal digests.
    value_digest: Mapped[bytes] = mapped_column(LargeBinary)


class ObjectRelation(Base):
    __tablename__ = "object_relations"
    __table_args__ = (
        UniqueConstraint(
            "relation_type_key",
            "from_object_id",
            "to_object_id",
            name="uq_object_relation",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_id: Mapped[str] = mapped_column(
        ForeignKey("objects.id", ondelete="CASCADE"), index=True
    )
    to_object_id: Mapped[str] = mapped_column(
        ForeignKey("objects.id", ondelete="CASCADE"), index=True
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    @property
    def relation_id(self) -> str:
        """The public ID, under the name change set and publication rows give it."""
        return self.id


class PublicationObject(Base):
    __tablename__ = "publication_objects"
    __table_args__ = (
        search_index(PUBLICATION_NAMES),
        UniqueConstraint("publication_id", "object_id", name="uq_publication_object"),
        # Ordered history pages by type and by parent (Base 0.8 S2).
        Index(
            "ix_publication_objects_type_name",
            "publication_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        Index(
            "ix_publication_objects_parent_name",
            "publication_id",
            "parent_object_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        # A consumer read pinned to the publication matches as live reads do (0.9 C6a, 20261005_03):
        # exactly ignoring case, and by contains within one type.
        Index("ix_publication_objects_lower_name", "publication_id", func.lower(literal_column("name"))),
        Index(
            "ix_publication_objects_type_name_trigram",
            "publication_id",
            "object_type_key",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    # Type and parent are read inside one publication through the indexes above (A6, D28).
    object_type_key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class PublicationRelation(Base):
    __tablename__ = "publication_relations"
    __table_args__ = (
        UniqueConstraint("publication_id", "relation_id", name="uq_publication_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_publication_relations_from",
            "publication_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_publication_relations_to",
            "publication_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Ends and type are read inside one publication through the indexes above (A6, D28).
    relation_type_key: Mapped[str] = mapped_column(String(160))
    from_object_id: Mapped[str] = mapped_column(String(36))
    to_object_id: Mapped[str] = mapped_column(String(36))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ChangeSetBase(Base):
    """Private immutable current-live source captured for one mutable change set."""

    __tablename__ = "change_set_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_runtime_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ChangeSetBaseObject(Base):
    __tablename__ = "change_set_base_objects"
    __table_args__ = (
        search_index(CHANGE_SET_BASE_NAMES),
        UniqueConstraint("base_id", "object_id", name="uq_change_set_base_object"),
        # Ordered change set pages by type and by parent (Base 0.8 S2).
        Index(
            "ix_change_set_base_objects_type_name",
            "base_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        Index(
            "ix_change_set_base_objects_parent_name",
            "base_id",
            "parent_object_id",
            "object_type_key",
            "name",
            "object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_id: Mapped[str] = mapped_column(
        ForeignKey("change_set_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ChangeSetBaseRelation(Base):
    __tablename__ = "change_set_base_relations"
    __table_args__ = (
        UniqueConstraint("base_id", "relation_id", name="uq_change_set_base_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_change_set_base_relations_from",
            "base_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_change_set_base_relations_to",
            "base_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_id: Mapped[str] = mapped_column(
        ForeignKey("change_set_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_id: Mapped[str] = mapped_column(String(36), index=True)
    to_object_id: Mapped[str] = mapped_column(String(36), index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ChangeSetObject(Base):
    __tablename__ = "change_set_objects"
    __table_args__ = (
        search_index(CHANGE_SET_NAMES),
        UniqueConstraint("change_set_id", "object_id", name="uq_change_set_object"),
        # The page indexes of the publication and base object tables, so a change set's own rows
        # are found by type and by parent inside it; walks down seek children by (change set,
        # parent) (migration 20260928_01, A6).
        Index(
            "ix_change_set_objects_type_name",
            "change_set_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        Index(
            "ix_change_set_objects_parent_name",
            "change_set_id",
            "parent_object_id",
            "object_type_key",
            "name",
            "object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    change_set_id: Mapped[str] = mapped_column(
        ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    object_type_key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ChangeSetRelation(Base):
    __tablename__ = "change_set_relations"
    __table_args__ = (
        UniqueConstraint("change_set_id", "relation_id", name="uq_change_set_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_change_set_relations_from",
            "change_set_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_change_set_relations_to",
            "change_set_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    change_set_id: Mapped[str] = mapped_column(
        ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Ends and type are read inside one change set through the indexes above (A6, D28).
    relation_type_key: Mapped[str] = mapped_column(String(160))
    from_object_id: Mapped[str] = mapped_column(String(36))
    to_object_id: Mapped[str] = mapped_column(String(36))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SnapshotAttributeValue(Base):
    """Typed index of one attribute value held as JSON by a publication, change-set base or change set row.

    ``owner_id`` is the publication, change set base or change set that owns the object row, so one query
    builder can filter and sort change set and history reads exactly as live ``attribute_values`` rows.
    The JSON ``attributes`` column stays the source of truth; these rows are derived from it by
    ``engine/indexes/snapshot_values.py`` whenever the owning row is written (D1, Base 0.8 S2).
    """

    __tablename__ = "snapshot_attribute_values"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "object_id", "attribute_type_key", name="uq_snapshot_attribute_value"
        ),
        CheckConstraint(
            "owner_kind IN ('publication', 'base', 'change_set')", name="ck_snapshot_attribute_owner_kind"
        ),
        # A record's value is found by the unique key; an (owner, attribute) read uses the next
        # index's prefix. A separate (owner, attribute) index was dropped in 20261003_01: on rows
        # without statistics yet the planner chose it for a record's value and read every value of
        # the attribute in the owner (0.9.0-alpha.1 PG5).
        # A change set write's unique-value check seeks to the value (S2b, 20260926_02).
        Index(
            "ix_snapshot_attribute_values_owner_key_text",
            "owner_id",
            "attribute_type_key",
            "text_value",
            "object_id",
        ),
        search_index(SNAPSHOT_VALUES),
        # A consumer read pinned to a publication looks up and sorts its values as live reads do;
        # partial, so change-set bases and change sets do not maintain them (0.9 C6a, 20261005_03).
        Index(
            "ix_snapshot_attribute_values_publication_lower_text",
            "owner_id",
            "attribute_type_key",
            func.lower(literal_column("text_value")),
            postgresql_where=text("owner_kind = 'publication'"),
        ),
        *(
            Index(
                f"ix_snapshot_attribute_values_publication_key_{name}",
                "owner_id",
                "attribute_type_key",
                f"{name}_value",
                "object_id",
                postgresql_where=text("owner_kind = 'publication'"),
            )
            for name in ("integer", "decimal", "boolean", "date", "datetime")
        ),
        # A change set write's unique check and key reference seek a number, decimal, date or
        # instant (0.11 Q2, D187, 20261023_01); a change set's attribute sort reads them, and
        # booleans, in value order (0.11 Q3, D205, D207, 20261026_01). A row enters only its own
        # type's index.
        *(
            Index(
                f"ix_snapshot_attribute_values_change_set_key_{name}",
                "owner_id",
                "attribute_type_key",
                f"{name}_value",
                "object_id",
                postgresql_where=text(
                    f"owner_kind IN ('base', 'change_set') AND {name}_value IS NOT NULL"
                ),
            )
            for name in ("integer", "decimal", "boolean", "date", "datetime")
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    attribute_type_key: Mapped[str] = mapped_column(String(160), nullable=False)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    integer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decimal_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    datetime_value: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    json_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class RelationSetVersion(Base):
    __tablename__ = "relation_set_versions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_key",
            "change_set_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
            name="uq_relation_set_version",
        ),
        CheckConstraint("direction IN ('outgoing', 'incoming')", name="ck_rsv_direction"),
        Index(
            "uq_relation_set_version_live",
            "workspace_key",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
            unique=True,
            postgresql_where=text("change_set_id IS NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False, index=True
    )
    change_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    relation_type_key: Mapped[str] = mapped_column(String(160), nullable=False)
    from_object_type_key: Mapped[str] = mapped_column(String(160), nullable=False)
    to_object_type_key: Mapped[str] = mapped_column(String(160), nullable=False)
    anchor_object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class MatrixCellState(Base):
    """Derived state of one relation matrix cell: (row, column) of one matrix shape in one owner.

    Owners: live records of a workspace (``live``, owner = workspace key), a publication, a private
    change set base (``base``), a change set's overlay (``change_set``) and a workspace's publication
    history (``history``, owner = workspace key). A change set's rows for a row record replace all
    the base's rows for it; its sentinel row (``column_id`` empty) marks the row as replaced. A
    history row records the first publication that held a record in the cell. Records remain the
    source of truth; ``engine/indexes/matrix_states.py`` derives and maintains these rows (Base 0.8 A3b).
    """

    __tablename__ = "matrix_cell_states"
    __table_args__ = (
        UniqueConstraint(
            "owner_kind", "owner_id", "shape_key", "row_id", "column_id", name="uq_matrix_cell_state"
        ),
        CheckConstraint(
            "owner_kind IN ('live', 'history', 'publication', 'base', 'change_set')",
            name="ck_matrix_cell_state_owner_kind",
        ),
        # The row state filter reads the selected columns of one owner and shape from this index.
        Index(
            "ix_matrix_cell_states_column",
            "owner_kind",
            "owner_id",
            "shape_key",
            "column_id",
            "row_id",
            "record_count",
            "matching_count",
            "first_publication_number",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(160), nullable=False)
    shape_key: Mapped[str] = mapped_column(String(32), nullable=False)
    row_id: Mapped[str] = mapped_column(String(36), nullable=False)
    column_id: Mapped[str] = mapped_column(String(36), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matching_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_publication_number: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MatrixStateBuild(Base):
    """One owner's cell states of one matrix shape are complete and maintained (Base 0.8 A3b).

    Reads use the stored states only when every owner they need has this row; otherwise they derive
    the cells from records. ``shape`` holds the shape's definition, so maintenance needs no model.
    """

    __tablename__ = "matrix_state_builds"
    __table_args__ = (
        UniqueConstraint("owner_kind", "owner_id", "shape_key", name="uq_matrix_state_build"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(160), nullable=False)
    shape_key: Mapped[str] = mapped_column(String(32), nullable=False)
    shape: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    built_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("workspace_key", "feed_position", name="uq_audit_event_feed_position"),
        # The feed's retention floor: the first entry within the period, in one probe (0.9 F2).
        Index(
            "ix_audit_events_feed_time",
            "workspace_key",
            "occurred_at",
            "feed_position",
            postgresql_where=text("feed_position IS NOT NULL"),
        ),
        CheckConstraint(
            "num_nonnulls(actor_user_id, actor_client_id) <= 1", name="ck_audit_events_actor_one"
        ),
        # One person's or client's changes newest first (0.12 Z6, D347).
        Index(
            "ix_audit_events_actor_user",
            "actor_user_id",
            "occurred_at",
            "sequence_id",
            postgresql_where=text("actor_user_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_events_actor_client",
            "actor_client_id",
            "occurred_at",
            "sequence_id",
            postgresql_where=text("actor_client_id IS NOT NULL"),
        ),
        CheckConstraint(
            "(actor_kind IS NULL AND num_nonnulls(actor_user_id, actor_client_id) = 0)"
            " OR (actor_kind = 'engine' AND num_nonnulls(actor_user_id, actor_client_id) = 0)"
            " OR (actor_kind = 'user' AND actor_user_id IS NOT NULL)"
            " OR (actor_kind = 'client' AND actor_client_id IS NOT NULL)",
            name="ck_audit_events_actor_kind",
        ),
        # Security events newest first (0.12 Z4, D317); they stand outside every workspace.
        Index(
            "ix_audit_events_security",
            "occurred_at",
            "sequence_id",
            postgresql_where=text(f"aggregate_type IN ({SECURITY_AGGREGATES_SQL})"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    aggregate_type: Mapped[str] = mapped_column(String(40), index=True)
    # Wide enough to hold the longest legal Workspace.key (String(160)) for the workspace-scoped
    # lifecycle aggregate (publication withdrawal aggregates on the real workspace key).
    aggregate_id: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), index=True
    )
    # What made the change when it was not a single write: a job (Base 0.9, INTEGRATION_API P6).
    cause_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cause_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # Who made it, beside the cause (0.12 Z4, D313): ``user`` or ``client`` with its row, or
    # ``engine`` for the engine's own changes; none for an entry from before Z4.
    actor_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    actor_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    # The workspace an entry belongs to, live or in one of its change sets (0.12 Z6, D341); a
    # change to live data also takes the next position of its feed (Base 0.9 F1), other entries
    # have none. ``subject`` names what a record or relationship entry changed (record type,
    # relation type and ends), kept here since a later delete leaves nothing to look it up by.
    workspace_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    feed_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_release_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "model_releases.id",
            name="fk_audit_events_model_release_id_model_releases",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    subject: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AuditEventSubject(Base):
    __tablename__ = "audit_event_subjects"
    __table_args__ = (
        UniqueConstraint("audit_event_id", "object_id", name="uq_audit_event_subject"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_event_id: Mapped[int] = mapped_column(
        ForeignKey("audit_events.sequence_id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class ConsumerEvent(Base):
    """A consumer event derived from a feed entry (Base 0.9 C10, CONSUMER_API C-D8).

    One per position, consumer API, event and object; ``ordinal`` orders the events of one position.
    It keeps no values: identity and the object are read when the event is read or sent (C-D7,
    C-D89). ``object_type_key`` is the type the event is about (the previous one for a type change
    told as a deletion), ``object_type`` its public name in the definition that derived it.
    """

    __tablename__ = "consumer_events"
    __table_args__ = (
        UniqueConstraint(
            "workspace_key", "consumer_api", "position", "ordinal", name="uq_consumer_event_order"
        ),
        CheckConstraint("change IN ('created', 'updated', 'deleted')", name="ck_consumer_event_change"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False
    )
    consumer_api: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    change: Mapped[str] = mapped_column(String(20), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    object_type_key: Mapped[str] = mapped_column(String(160), nullable=False)
    object_type: Mapped[str] = mapped_column(String(300), nullable=False)
    changed: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cause_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cause_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False
    )


class ConsumerEventCheckpoint(Base):
    """How far a workspace's feed is derived into consumer events (C10): every entry up to
    ``position``. ``start_position`` is where derivation began (C-D92): earlier entries have no
    events."""

    __tablename__ = "consumer_event_checkpoints"

    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ConsumerSubscription(Base):
    """Where a consumer API's events go (Base 0.9 C11, CONSUMER_API "Subscriptions").

    Deployment data, never part of a model release. ``contract_version`` is the version the
    subscription was accepted under (C-D99); ``acknowledged_position`` and ``acknowledged_ordinal``
    are where delivery continues, inside a position too, as a pull-feed cursor (C-D91). A suspended
    subscription names its reason (C-D98). ``signing_key`` is sealed with the deployment key
    (``common/sealing``, C-D96) and never returned after create.
    """

    __tablename__ = "consumer_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "max_events_per_batch BETWEEN 1 AND 1000", name="ck_consumer_subscription_max_events_per_batch"
        ),
        CheckConstraint("payload IN ('full', 'identity')", name="ck_consumer_subscription_payload"),
        CheckConstraint("format IN ('rdm', 'cloudevents')", name="ck_consumer_subscription_format"),
        CheckConstraint("status IN ('active', 'suspended')", name="ck_consumer_subscription_status"),
        Index("ix_consumer_subscriptions_api", "consumer_api", "sequence_id"),
        Index("ix_consumer_subscriptions_workspace", "workspace_key", "sequence_id"),
        Index("ix_consumer_subscriptions_due", "next_attempt_at", postgresql_where=text("status = 'active'")),
        CheckConstraint(
            "num_nonnulls(created_by_user_id, created_by_client_id) <= 1",
            name="ck_consumer_subscriptions_one_created_by",
        ),
        Index("ix_consumer_subscriptions_created_by_user", "created_by_user_id"),
        Index("ix_consumer_subscriptions_created_by_client", "created_by_client_id"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    # What the operator calls it (U5a, C-D115); not unique.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    consumer_api: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, nullable=False)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="RESTRICT"), nullable=False
    )
    event_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    filters: Mapped[dict[str, list[str]]] = mapped_column(JSON, nullable=False, default=dict)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    # How requests are made (C17): at most this many events each, with each object or its identity,
    # in RDM JSON or CloudEvents.
    max_events_per_batch: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(String(20), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    suspension_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    suspension_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspension_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    acknowledged_position: Mapped[int] = mapped_column(Integer, nullable=False)
    acknowledged_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    signing_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signing_key_created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    # The key a rotation replaced, sealed like ``signing_key``, signing beside it until the overlap
    # ends (0.12 K1, D238); empty for a subscription never rotated.
    previous_signing_key: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    previous_signing_key_expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    # Delivery (C12): which process delivers it until when (C-D106); the batch being sent or
    # retried, by its delivery ID and the event key it ends at (C-D111); the failed attempts of that
    # batch (C-D103); the last acknowledgement. None of it changes ``version`` (C-D108).
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    pending_delivery_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pending_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failing_since: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    # Who created it (0.12 Z3, D310); neither for one from before Z3.
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )


WEBHOOK_REQUEST_STATUSES = ("queued", "sending", "retrying", "succeeded", "failed", "dropped")


class ConsumerWebhookRequest(Base):
    """One request of a webhook batch (U5a, C-D116): a batch is one request, so ``delivery_id``, the
    request's ``RDM-Delivery-Id``, is also ``batch_id``, the subscription's ``pending_delivery_id``
    while it is retried; a resend (C-D129) is a batch of its own.
    ``request_body`` is the text of the latest attempt's body exactly as sent. Removed with its
    subscription, and after ``CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`` (C-D118)."""

    __tablename__ = "consumer_webhook_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'sending', 'retrying', 'succeeded', 'failed', 'dropped')",
            name="ck_consumer_webhook_request_status",
        ),
        UniqueConstraint("subscription_sequence_id", "delivery_id", name="uq_consumer_webhook_request_delivery"),
        Index("ix_consumer_webhook_requests_batch", "subscription_sequence_id", "batch_id"),
        Index("ix_consumer_webhook_requests_created", "created_at"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_sequence_id: Mapped[int] = mapped_column(
        ForeignKey("consumer_subscriptions.sequence_id", ondelete="CASCADE"), nullable=False
    )
    delivery_id: Mapped[str] = mapped_column(String(36), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    # A resend by hand (C-D129–C-D131): the delivery ID of the request it repeats.
    resend_of: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ConsumerWebhookRequestEvent(Base):
    """An event a request carries: one row of a subscription's deliveries (C-D119). ``ordinal``
    orders them within the request."""

    __tablename__ = "consumer_webhook_request_events"

    request_sequence_id: Mapped[int] = mapped_column(
        ForeignKey("consumer_webhook_requests.sequence_id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    change: Mapped[str] = mapped_column(String(20), nullable=False)
    object_type: Mapped[str] = mapped_column(String(300), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ConsumerWebhookAttempt(Base):
    """One attempt to send a request: when it started and completed, the receiver's status, or the
    error's kind and message, and up to 4 KiB of the answer (C-D116)."""

    __tablename__ = "consumer_webhook_attempts"

    request_sequence_id: Mapped[int] = mapped_column(
        ForeignKey("consumer_webhook_requests.sequence_id", ondelete="CASCADE"), primary_key=True
    )
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)


class Job(Base):
    """A bulk write, import or export: its parameters, state and counts (Base 0.9, ADR-036).

    A synchronous batch is a job run inline. Its outcomes are ``JobItem`` rows in item order; the
    counts and ``result`` summarize them once the job is finished.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', "
            "'profileCheck', 'migration', 'mappingInference', 'move')",
            name="ck_job_kind",
        ),
        CheckConstraint(
            "state IN ('queued', 'running', 'awaiting_confirmation', 'completed', 'failed', "
            "'cancelled', 'expired')",
            name="ck_job_state",
        ),
        CheckConstraint(
            "num_nonnulls(requested_by_user_id, requested_by_client_id) <= 1",
            name="ck_jobs_one_requested_by",
        ),
        Index("ix_jobs_workspace_created", "workspace_key", "sequence_id"),
        Index("ix_jobs_state", "state", "sequence_id"),
        Index("ix_jobs_requested_by_user", "requested_by_user_id"),
        Index("ix_jobs_requested_by_client", "requested_by_client_id"),
        # The jobs a draft, a profile, a source file or a model mapping has (0.10 R, R-F14; 0.11
        # X1), read through `jobs.store.job_parameter`, which writes the key literally so these
        # match.
        *(
            Index(
                name,
                text(f"(parameters ->> '{key}')"),
                "sequence_id",
                postgresql_where=text(f"(parameters ->> '{key}') IS NOT NULL"),
            )
            for name, key in (
                ("ix_jobs_draft", "draftId"),
                ("ix_jobs_profile", "profileKey"),
                ("ix_jobs_source_file", "sourceFileId"),
                ("ix_jobs_mapping", "mappingKey"),
            )
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    workspace_key: Mapped[str] = mapped_column(String(160), nullable=False)
    change_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # The model release the job was created under (ADR-015 extended to a job).
    model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # The request's choices: policy, run and onExisting for a batch.
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # For a job in a change set, the version the job holds: its claim while it runs, the version
    # it left once finished.
    change_set_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    # The worker running a background job, until the lease expires (P6).
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # Set by a cancel request; the worker finishes the job as cancelled (D28).
    cancel_requested_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # A completed export's manifest (0.9 J1, D52); its file is in JOB_FILE_DIR under the job's ID.
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # An import's binding report and its preview's summary (0.9 J3, D86): ``bindingReport``,
    # ``preview``.
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # When a previewed import was confirmed (D87); the worker then runs it as ``execute``.
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # Who asked for it; it runs with their permissions (0.12 Z2, D236, D294). Neither for a job
    # from before Z2.
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    requested_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )


class JobInput(Base):
    """One item of a background job, waiting for the worker (D27). The rows go when the job
    reaches a final state."""

    __tablename__ = "job_inputs"
    __table_args__ = (UniqueConstraint("job_id", "item_index", name="uq_job_input"),)

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.sequence_id", ondelete="CASCADE"), nullable=False
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # An import's item: the source (in load order) and the row of the file it came from (0.9 J3).
    source_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The item as the request gave it: only the fields it set.
    item: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class JobItem(Base):
    """One item's outcome, at its position in the job's request (INTEGRATION_API P2)."""

    __tablename__ = "job_items"
    __table_args__ = (
        UniqueConstraint("job_id", "item_index", name="uq_job_item"),
        CheckConstraint(
            "status IN ('applied', 'rejected', 'unprocessed')", name="ck_job_item_status"
        ),
        Index("ix_job_items_status", "job_id", "status", "item_index"),
        Index("ix_job_items_rows", "job_id", "source_index", "row_number"),
        # A migration's items by outcome (0.11 V1).
        Index(
            "ix_job_items_outcome",
            "job_id",
            text("(outcome ->> 'outcome')"),
            "item_index",
            postgresql_where=text("(outcome ->> 'outcome') IS NOT NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.sequence_id", ondelete="CASCADE"), nullable=False
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # An import's outcome: its source and row, read grouped by ``GET /jobs/{id}/rows`` (0.9 J3).
    source_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The rest of the outcome: action, record identity and version, error, or reason.
    outcome: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class IdempotencyKey(Base):
    """A client's ``Idempotency-Key`` for a job-creating request (INTEGRATION_API P5).

    Scoped to the route and the workspace; the fingerprint is a SHA-256 of the canonical request.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("scope", "workspace_key", "key", name="uq_idempotency_key"),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    workspace_key: Mapped[str] = mapped_column(String(160), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.sequence_id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)



class ImportProfile(Base):
    """A stored import profile (Base 0.9 J2, INTEGRATION_API §J3): how a file's sheets and columns
    become records and relationships. Instance-wide, as the model is (D65); an import names the
    workspace. ``checked_release_id`` is the release it was last checked against."""

    __tablename__ = "import_profiles"

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # The profile as saved: csv, sources and valueMaps.
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    checked_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class SourceFile(Base):
    """A file a model draft or an import profile owns (Product 0.10 A3, D5), deleted with its
    owner. The file is in ``JOB_FILE_DIR`` as ``{public_id}.upload``; its filled cells are staged in
    ``source_file_cells`` by its profiling job (D66). A newer file of the same owner supersedes it,
    and the job retention sweep removes it ``JOB_RETENTION_DAYS`` later."""

    __tablename__ = "source_files"
    __table_args__ = (
        CheckConstraint(
            "(draft_id IS NULL) <> (profile_key IS NULL)", name="ck_source_files_one_owner"
        ),
        CheckConstraint(
            "num_nonnulls(uploaded_by_user_id, uploaded_by_client_id) <= 1",
            name="ck_source_files_one_uploaded_by",
        ),
        Index("ix_source_files_draft", "draft_id", "id"),
        Index("ix_source_files_profile", "profile_key", "id"),
        Index("ix_source_files_uploaded_by_user", "uploaded_by_user_id"),
        Index("ix_source_files_uploaded_by_client", "uploaded_by_client_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_drafts.id", ondelete="CASCADE"), nullable=True
    )
    profile_key: Mapped[str | None] = mapped_column(
        ForeignKey("import_profiles.key", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # The delimiter a CSV file was staged with; ``None`` for a workbook.
    csv_delimiter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # The workspace whose records the profile's overlaps read (D69); ``None`` for none.
    workspace_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    superseded_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    profile_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Who uploaded it (0.12 Z2, D295); neither for a file from before Z2.
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    uploaded_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )


class SourceFileCell(Base):
    """One filled cell of a source file, as its profiling job read it (0.10 A3, D66): its kind
    (``text``, ``integer``, ``decimal``, ``boolean``, ``date``, ``dateTime``), its text as an import
    matches it, and its value as the reader gave it (``value.py`` in ``engine/sources``)."""

    __tablename__ = "source_file_cells"
    __table_args__ = (
        PrimaryKeyConstraint(
            "source_file_id", "sheet_index", "row_number", "column_number",
            name="pk_source_file_cells",
        ),
    )

    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False
    )
    sheet_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)


class SourceFileSheet(Base):
    """A sheet of a source file's profile (0.10 A3): its rows, header row and blocks."""

    __tablename__ = "source_file_sheets"
    __table_args__ = (
        PrimaryKeyConstraint("source_file_id", "sheet_index", name="pk_source_file_sheets"),
    )

    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False
    )
    sheet_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class SourceFileColumn(Base):
    """A column of a block of a source file's profile (0.10 A3; per block since A8a, D115): its
    statistics."""

    __tablename__ = "source_file_columns"
    __table_args__ = (
        PrimaryKeyConstraint(
            "source_file_id",
            "sheet_index",
            "block_index",
            "column_number",
            name="pk_source_file_columns",
        ),
    )

    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False
    )
    sheet_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    column_number: Mapped[int] = mapped_column(Integer, nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ModelDraftProposal(Base):
    """A proposal of a model draft's latest inference (Product 0.10 A6, D87–D89): its pattern,
    the columns and evidence it rests on, the operations it applies and their alternatives. A newer
    inference replaces the draft's proposals; whether one was applied or rejected is read from the
    draft's history (D92), not stored here."""

    __tablename__ = "model_draft_proposals"
    __table_args__ = (Index("ix_model_draft_proposals_draft", "draft_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("model_drafts.id", ondelete="CASCADE"), nullable=False
    )
    # The inference job's public ID.
    inference_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    pattern: Mapped[str] = mapped_column(String(60), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ModelMapping(Base):
    """A saved mapping from one model to another (Product 0.11 X1, D18, D104): what each type,
    attribute, relation and parent of the source model becomes in the target model. Keyed by its
    two models' release keys; checked against the two releases it names, which its definition also
    holds (``sourceReleaseId``, ``targetReleaseId``) so that re-pointing it is a step of its history.
    Changed only by operations (``model_mapping_operations``)."""

    __tablename__ = "model_mappings"
    __table_args__ = (
        Index("ix_model_mappings_models", "source_model_key", "target_model_key", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_model_key: Mapped[str] = mapped_column(String(160), nullable=False)
    target_model_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # The definition as API.md shows it: the two releases' IDs, ``types`` and ``valueMaps``.
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ModelMappingOperation(Base):
    """One operation applied to a model mapping, in its history (0.11 X1, D105), as a draft's."""

    __tablename__ = "model_mapping_operations"
    __table_args__ = (
        UniqueConstraint("mapping_id", "sequence", name="uq_model_mapping_operations_sequence"),
        Index("ix_model_mapping_operations_step", "mapping_id", "step"),
        CheckConstraint(
            "num_nonnulls(author_user_id, author_client_id) <= 1", name="ck_model_mapping_operations_author_one"
        ),
        Index(
            "ix_model_mapping_operations_author_user",
            "author_user_id",
            postgresql_where=text("author_user_id IS NOT NULL"),
        ),
        Index(
            "ix_model_mapping_operations_author_client",
            "author_client_id",
            postgresql_where=text("author_client_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("model_mappings.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    inverse: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    mapping_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Who applied it (0.12 Z4, D315); nobody for one from before Z4.
    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    author_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    origin: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # The entries the operation created and named, as element atoms (D8's dependants).
    effects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    undone_by_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class ModelMappingProposal(Base):
    """A proposal of a model mapping's latest inference (0.11 X1, D108): one source type's or one
    relation's target with its evidence, operations and alternatives. A newer inference replaces
    them; whether one is applied, held or rejected is read from the mapping and its history."""

    __tablename__ = "model_mapping_proposals"
    __table_args__ = (Index("ix_model_mapping_proposals_mapping", "mapping_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("model_mappings.id", ondelete="CASCADE"), nullable=False
    )
    # The inference job's public ID.
    inference_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class EngineProcess(Base):
    """A running engine process as it last reported itself (Product 0.11 O1, D192).

    Each process upserts its row every ``PROCESS_HEARTBEAT_SECONDS`` and deletes it when it stops
    cleanly; a row silent for a day is deleted by any process. ``report`` holds what only the
    process knows: whether it is ready, its background threads, its pool, the releases it cannot
    serve and its counters (``engine/processes/report.py``). Operational state, never a domain
    record.
    """

    __tablename__ = "engine_processes"

    process_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class BackupRehearsal(Base):
    """A backup restored into a separate database and checked there (Product 0.11 O2, D198–D200).

    Written by ``app.cli.restore_check`` into the instance that was backed up, passed or failed;
    ``workspaces`` holds each active workspace of the copy: its release, whether it was served and
    why not, and its counts beside the instance's records. Operational state, never a domain record.
    """

    __tablename__ = "backup_rehearsals"
    __table_args__ = (
        CheckConstraint("result IN ('passed', 'failed')", name="ck_backup_rehearsal_result"),
        Index("ix_backup_rehearsals_checked", "checked_at", "public_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    backup: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_as_of: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    revision_before: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision_after: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspaces: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class User(Base):
    """A person who signs in (Product 0.12 I1, ADR-043).

    Deactivated, never deleted, so history always resolves who acted (D237). ``password_hash`` is
    an Argon2id PHC string, or none for a person who has not set a password (D252); the username is
    unique ignoring case. ``local_kept``: the person signs in with a password while local sign-in is
    off, the way back made on the server (I3, D365).
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ux_users_username", func.lower(literal_column("username")), unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_sign_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    local_kept: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # When the person switched on mail for their inbox; none: off (0.12 M2, D432).
    notice_mail_since: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # The notice kinds the person does not want mailed; all others are (0.12 M2 follow-up, D435).
    notice_mail_kinds_off: Mapped[list[str]] = mapped_column(
        ARRAY(String(160)), nullable=False, default=list, server_default="{}"
    )


class SignInProvider(Base):
    """An OpenID Connect provider people sign in with (Product 0.12 I3, D361, D366).

    ``key`` is fixed: it is in the address registered with the provider. The client secret is
    sealed with ``SECRETS_ENCRYPTION_KEY`` (D253) and never answered. A provider somebody signed in
    with is disabled, not deleted (``user_identities`` refuses it).
    """

    __tablename__ = "sign_in_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    groups_claim: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Signing out of the engine signs the person out of the provider too (I4a, D379).
    sign_out_of_provider: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_sign_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class LocalSignIn(Base):
    """Whether people sign in with a password: one row (I3, D365)."""

    __tablename__ = "local_sign_in"
    __table_args__ = (CheckConstraint("id = 1", name="ck_local_sign_in_one_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # A password needs a second factor: an authenticator app set up on the sign-in page (I4b, D388).
    second_factor_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class MailSettings(Base):
    """The SMTP connection the engine sends mail through: one row, absent until set (0.12 M1, D419).

    The password is sealed with ``SECRETS_ENCRYPTION_KEY`` (D253) and never answered.
    ``application_url`` is where the links in mail point (D422); empty, the first browser origin.
    """

    __tablename__ = "mail_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_mail_settings_one_row"),
        CheckConstraint(
            "security IN ('tls', 'starttls', 'none')", name="ck_mail_settings_security"
        ),
        CheckConstraint(
            "password IS NULL OR username IS NOT NULL", name="ck_mail_settings_password_user"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    security: Mapped[str] = mapped_column(String(16), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    from_address: Mapped[str] = mapped_column(String(320), nullable=False)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class MailOutbox(Base):
    """A message waiting to be sent, sent or given up on (0.12 M1, D419).

    ``body`` is sealed (it holds a one-time link) and emptied once the message is sent or failed.
    ``lease_*`` is the sending process's claim, as a webhook subscription's is.
    """

    __tablename__ = "mail_outbox"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_mail_outbox_status"),
        Index(
            "ix_mail_outbox_due",
            "next_attempt_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_mail_outbox_created", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    to_address: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    lease_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class UserIdentity(Base):
    """A person as a provider knows them: the provider and the ID token's ``sub`` (I3, D363)."""

    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider_id", "subject", name="ux_user_identities_provider_subject"),
        Index("ix_user_identities_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("sign_in_providers.id", ondelete="RESTRICT"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_sign_in_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProviderSignIn(Base):
    """A sign-in between the engine's redirect to the provider and its return (I3, D361).

    Stored as the state's and the browser binding's SHA-256, with the nonce, the PKCE verifier the
    engine sends the provider and the browser's own authorization request; used once, within
    ``expires_at``.
    """

    __tablename__ = "provider_sign_ins"
    __table_args__ = (Index("ix_provider_sign_ins_expires", "expires_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("sign_in_providers.id", ondelete="CASCADE"), nullable=False
    )
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    browser_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class OAuthClient(Base):
    """A system that calls the API with the client credentials grant (Product 0.12 I1, D226).

    Its ``public_id`` is the OAuth ``client_id``. Deactivated, never deleted (D237).
    """

    __tablename__ = "oauth_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class OAuthClientSecret(Base):
    """One of a client's secrets, hashed with Argon2id and shown once (D253). A client has two
    during a rotation: the previous one ``expires_at`` the end of its overlap."""

    __tablename__ = "oauth_client_secrets"
    __table_args__ = (Index("ix_oauth_client_secrets_client", "client_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    client_id: Mapped[int] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False
    )
    secret_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # The secret's last four characters, to tell secrets apart (SP2, D350); None before SP2.
    hint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class TokenSigningKey(Base):
    """A key that signs access tokens (ES256, D254), its private half sealed with
    ``SECRETS_ENCRYPTION_KEY`` (D253).

    The current key has no ``rotated_at``; one key at most is current. A rotated key verifies the
    tokens it signed until ``retired_at``: the end of their lifetime after a scheduled rotation, at
    once after "rotate now".
    """

    __tablename__ = "token_signing_keys"
    __table_args__ = (
        Index(
            "ux_token_signing_keys_current",
            literal_column("(rotated_at IS NULL)"),
            unique=True,
            postgresql_where=text("rotated_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    private_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    public_jwk: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class UserSession(Base):
    """A person's browser session (Product 0.12 I2, ADR-043, D234, D251).

    Started when the browser exchanges a sign-in's code; renewed through refresh tokens, each used
    once. It ends when signed out, when a used refresh token is presented again, after
    ``idle_ends_at`` or ``ends_at``, or when the person is deactivated; an ended session's access
    tokens are refused from the next request (``sid``).
    """

    __tablename__ = "user_sessions"
    __table_args__ = (Index("ix_user_sessions_user", "user_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    signed_in_with: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    idle_ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    ended_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # The provider's ID token, sealed, kept while the session is open when its provider signs
    # people out too (I4a, D380).
    provider_id_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class SessionRefreshToken(Base):
    """One refresh token of a session, stored as its SHA-256 (I2). Each is used once; presenting a
    used one again ends the session (D251)."""

    __tablename__ = "session_refresh_tokens"
    __table_args__ = (Index("ix_session_refresh_tokens_session", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class AuthorizationCode(Base):
    """A sign-in's one-time code (I2, RFC 6749 §4.1 with PKCE ``S256``), stored as its SHA-256 and
    bound to the redirect address and the browser's code challenge; it lasts a minute."""

    __tablename__ = "authorization_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(128), nullable=False)
    signed_in_with: Mapped[str] = mapped_column(String(64), nullable=False)
    # The provider's ID token, sealed, handed on to the session the code starts (I4a, D380).
    provider_id_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # The session the code started, so a code presented twice ends it (RFC 6749 §4.1.2).
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True
    )


class UserSecondFactor(Base):
    """A person's authenticator app (Product 0.12 I4b, D383, D384): the TOTP secret sealed with
    ``SECRETS_ENCRYPTION_KEY``, confirmed once the person typed a code from it (none while they are
    setting it up), and the last time step a code was accepted for, so each works once."""

    __tablename__ = "user_second_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class UserRecoveryCode(Base):
    """One of a person's recovery codes (I4b, D385), stored as its SHA-256; used once."""

    __tablename__ = "user_recovery_codes"
    __table_args__ = (Index("ix_user_recovery_codes_user", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class SignInStep(Base):
    """A sign-in between the right password and its second step (I4b, D388), stored as the token's
    SHA-256 with the browser's authorization request. ``stage``: ``code`` (a second factor to
    present), ``setup`` (the requirement is on and the person sets one up), ``codes`` (set up; the
    recovery codes are shown before the sign-in goes on), and for a passkey (I4c) ``passkey-add``
    (a person registering one) and ``passkey-in`` (signing in with one alone). Used once, within
    ``expires_at``."""

    __tablename__ = "sign_in_steps"
    __table_args__ = (Index("ix_sign_in_steps_expires", "expires_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # None for a passkey ceremony used before anyone is known (I4c, D393).
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # The challenge of a passkey ceremony in progress (I4c).
    challenge: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class UserPasskey(Base):
    """A person's passkey (Product 0.12 I4c, D389–D394): a WebAuthn credential the engine verifies
    with its public key; ``sign_count`` is the authenticator's last counter. The name is the
    person's, to tell their passkeys apart."""

    __tablename__ = "user_passkeys"
    __table_args__ = (Index("ix_user_passkeys_user", "user_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class PasswordResetLink(Base):
    """A one-time link that sets a person's password (I2, D272), stored as its SHA-256. A newer
    link replaces an older one; it is used once and lasts ``PASSWORD_RESET_HOURS``."""

    __tablename__ = "password_reset_links"
    __table_args__ = (Index("ix_password_reset_links_user", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class SignInFailure(Base):
    """Failed sign-ins counted per account (the username as typed, lower case) and per address, to
    slow guessing without locking anyone out (I2, D252, D271)."""

    __tablename__ = "sign_in_failures"
    __table_args__ = (UniqueConstraint("kind", "key", name="ux_sign_in_failures_kind_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    key: Mapped[str] = mapped_column(String(320), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_failure_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class Role(Base):
    """A set of action groups that a grant gives (Product 0.12 Z1, ADR-044, D227).

    The nine predefined roles are rows like the others, marked ``predefined`` and read-only; their
    groups are in the code's catalogue (D279). A custom role's groups are its
    ``role_action_groups``. A role still granted cannot be deleted.
    """

    __tablename__ = "roles"
    __table_args__ = (Index("ux_roles_name", func.lower(literal_column("name")), unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    predefined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class RoleActionGroup(Base):
    """One action group of a custom role."""

    __tablename__ = "role_action_groups"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    group_key: Mapped[str] = mapped_column(String(64), primary_key=True)


class UserGroup(Base):
    """A group of people; a grant to it applies to its members (Z1, D229).

    A provider group (I3, D364) names its provider and the groups claim's value; its members are
    those the provider named at their last sign-in.
    """

    __tablename__ = "user_groups"
    __table_args__ = (
        Index("ux_user_groups_name", func.lower(literal_column("name")), unique=True),
        CheckConstraint("(provider_id IS NULL) = (claim_value IS NULL)", name="ck_user_groups_source"),
        Index(
            "ux_user_groups_provider_claim",
            "provider_id",
            "claim_value",
            unique=True,
            postgresql_where=text("provider_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("sign_in_providers.id", ondelete="CASCADE"), nullable=True
    )
    claim_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class UserGroupMember(Base):
    __tablename__ = "user_group_members"
    __table_args__ = (Index("ix_user_group_members_user", "user_id"),)

    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    # A provider group's member: when a sign-in last named them in it (I3, D364).
    seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class Grant(Base):
    """A role given to one person, client or group, at the instance (no workspace) or in one
    workspace, optionally narrowing writes to applications and record types (Z1, D228, D243,
    D281); or, instead of a role, read of one consumer API in one workspace, never narrowed (Z3,
    D306). Created and deleted, never changed; it goes with its workspace."""

    __tablename__ = "grants"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(user_id, client_id, group_id) = 1", name="ck_grants_one_principal"
        ),
        CheckConstraint(
            "workspace_key IS NOT NULL OR (cardinality(applications) = 0 "
            "AND cardinality(record_types) = 0)",
            name="ck_grants_instance_not_narrowed",
        ),
        CheckConstraint(
            "num_nonnulls(role_id, consumer_api) = 1", name="ck_grants_role_or_consumer_api"
        ),
        CheckConstraint(
            "consumer_api IS NULL OR (workspace_key IS NOT NULL AND cardinality(applications) = 0 "
            "AND cardinality(record_types) = 0)",
            name="ck_grants_consumer_api_scope",
        ),
        Index("ix_grants_consumer_api", "consumer_api", "workspace_key"),
        Index("ix_grants_user", "user_id"),
        Index("ix_grants_client", "client_id"),
        Index("ix_grants_group", "group_id"),
        Index("ix_grants_role", "role_id"),
        Index("ix_grants_workspace", "workspace_key", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=True
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=True
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=True
    )
    # The consumer API a grant without a role lets its holder read in its workspace (D306).
    consumer_api: Mapped[str | None] = mapped_column(String(160), nullable=True)
    workspace_key: Mapped[str | None] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=True
    )
    applications: Mapped[list[str]] = mapped_column(
        ARRAY(String(160)), nullable=False, default=list
    )
    record_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(160)), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class AuthorizationState(Base):
    """One row: the generation PostgreSQL triggers raise whenever roles, groups, memberships,
    grants or a principal's ``active`` change; a process reads a caller's permissions again when
    it differs (Z1, D278). No code writes it."""

    __tablename__ = "authorization_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_authorization_state_one_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generation: Mapped[int] = mapped_column(BigInteger, nullable=False)


class AiCall(Base):
    """One call to the proposal provider (0.16 AP1, AP-D4): who asked, for what, of which provider
    and model, how much went each way and how it ended. The request and answer are kept only with
    ``AI_LOG_CONTENT`` on, and emptied once ``content_expires_at`` passes."""

    __tablename__ = "ai_calls"
    __table_args__ = (
        CheckConstraint("outcome IN ('answered', 'failed')", name="ck_ai_calls_outcome"),
        CheckConstraint(
            "num_nonnulls(requested_by_user_id, requested_by_client_id) <= 1",
            name="ck_ai_calls_one_requested_by",
        ),
        Index("ix_ai_calls_started", "started_at", "id"),
        Index(
            "ix_ai_calls_content_expiry",
            "content_expires_at",
            postgresql_where=text("content_expires_at IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(160), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    send_level: Mapped[str] = mapped_column(String(16), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    requested_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("oauth_clients.id", ondelete="RESTRICT"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    bytes_in: Mapped[int] = mapped_column(Integer, nullable=False)
    bytes_out: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    content_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
