from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from ..common.time import as_utc


class UTCDateTime(TypeDecorator[datetime]):
    """A timestamp stored as UTC and always read back as an aware UTC ``datetime``.

    SQLite drops the zone of ``DateTime(timezone=True)``: an offset value would be stored as its wall
    clock and read back zone-less. Converting on the way in and attaching UTC on the way out keeps
    the instant and lets every API response carry an explicit offset on every database.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return as_utc(value) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return as_utc(value) if value is not None else None


class Base(DeclarativeBase):
    pass


class ModelRelease(Base):
    __tablename__ = "model_releases"
    __table_args__ = (
        UniqueConstraint("release_key", "release_version", name="uq_model_release_identity"),
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    installed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )


class ModelRuntimeState(Base):
    __tablename__ = "model_runtime_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_model_runtime_state_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_model_release_id: Mapped[int] = mapped_column(
        ForeignKey("model_releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


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
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
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
    active_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "workspace_revisions.id",
            name="fk_workspaces_active_revision_id_workspace_revisions",
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


class WorkspaceRevision(Base):
    __tablename__ = "workspace_revisions"
    __table_args__ = (
        UniqueConstraint("workspace_key", "revision_number", name="uq_workspace_revision_number"),
        CheckConstraint("status IN ('active', 'retired')", name="ck_workspace_revision_status"),
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
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    derived_from_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_revisions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    supersedes_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_revisions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    activated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    retired_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class WorkspaceDraft(Base):
    __tablename__ = "workspace_drafts"

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
    derived_from_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_revisions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # A current-live base is deliberately not a publication revision.  Legacy drafts retain a
    # null base id and continue to resolve their original empty/revision source.
    base_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_draft_bases.id", ondelete="RESTRICT"), nullable=True, index=True
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


class AttributeValue(Base):
    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("object_id", "attribute_type_key", name="uq_object_attribute_value"),
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


class WorkspaceRevisionObject(Base):
    __tablename__ = "workspace_revision_objects"
    __table_args__ = (
        UniqueConstraint("revision_id", "object_id", name="uq_workspace_revision_object"),
        # Ordered history pages by type and by parent (Base 0.8 S2).
        Index(
            "ix_workspace_revision_objects_type_name",
            "revision_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        Index(
            "ix_workspace_revision_objects_parent_name",
            "revision_id",
            "parent_object_id",
            "object_type_key",
            "name",
            "object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkspaceRevisionRelation(Base):
    __tablename__ = "workspace_revision_relations"
    __table_args__ = (
        UniqueConstraint("revision_id", "relation_id", name="uq_workspace_revision_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_workspace_revision_relations_from",
            "revision_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_workspace_revision_relations_to",
            "revision_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_id: Mapped[str] = mapped_column(String(36), index=True)
    to_object_id: Mapped[str] = mapped_column(String(36), index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkspaceDraftBase(Base):
    """Private immutable current-live source captured for one mutable draft."""

    __tablename__ = "workspace_draft_bases"

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


class WorkspaceDraftBaseObject(Base):
    __tablename__ = "workspace_draft_base_objects"
    __table_args__ = (
        UniqueConstraint("base_id", "object_id", name="uq_workspace_draft_base_object"),
        # Ordered draft pages by type and by parent (Base 0.8 S2).
        Index(
            "ix_workspace_draft_base_objects_type_name",
            "base_id",
            "object_type_key",
            "name",
            "object_id",
        ),
        Index(
            "ix_workspace_draft_base_objects_parent_name",
            "base_id",
            "parent_object_id",
            "object_type_key",
            "name",
            "object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_draft_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkspaceDraftBaseRelation(Base):
    __tablename__ = "workspace_draft_base_relations"
    __table_args__ = (
        UniqueConstraint("base_id", "relation_id", name="uq_workspace_draft_base_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_workspace_draft_base_relations_from",
            "base_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_workspace_draft_base_relations_to",
            "base_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_draft_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_id: Mapped[str] = mapped_column(String(36), index=True)
    to_object_id: Mapped[str] = mapped_column(String(36), index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkspaceDraftObject(Base):
    __tablename__ = "workspace_draft_objects"
    __table_args__ = (UniqueConstraint("draft_id", "object_id", name="uq_workspace_draft_object"),)

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application_key: Mapped[str] = mapped_column(String(160))
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(500))
    parent_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class WorkspaceDraftRelation(Base):
    __tablename__ = "workspace_draft_relations"
    __table_args__ = (
        UniqueConstraint("draft_id", "relation_id", name="uq_workspace_draft_relation"),
        # Relation pages read one record's relations inside one owner (migrations 20260925_02,
        # 20260926_01); they cover the type filter and the related end, so listing reads the index.
        Index(
            "ix_workspace_draft_relations_from",
            "draft_id",
            "from_object_id",
            "relation_type_key",
            "relation_id",
            "to_object_id",
        ),
        Index(
            "ix_workspace_draft_relations_to",
            "draft_id",
            "to_object_id",
            "relation_type_key",
            "relation_id",
            "from_object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(
        ForeignKey("workspace_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type_key: Mapped[str] = mapped_column(String(160), index=True)
    from_object_id: Mapped[str] = mapped_column(String(36), index=True)
    to_object_id: Mapped[str] = mapped_column(String(36), index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SnapshotAttributeValue(Base):
    """Typed index of one attribute value held as JSON by a revision, draft-base or draft row.

    ``owner_id`` is the revision, draft base or draft that owns the object row, so one query
    builder can filter and sort draft and history reads exactly as live ``attribute_values`` rows.
    The JSON ``attributes`` column stays the source of truth; these rows are derived from it by
    ``services/snapshot_values.py`` whenever the owning row is written (D1, Base 0.8 S2).
    """

    __tablename__ = "snapshot_attribute_values"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "object_id", "attribute_type_key", name="uq_snapshot_attribute_value"
        ),
        CheckConstraint(
            "owner_kind IN ('revision', 'base', 'draft')", name="ck_snapshot_attribute_owner_kind"
        ),
        Index("ix_snapshot_attribute_values_owner_key", "owner_id", "attribute_type_key"),
        # A draft write's unique-value check seeks to the value (S2b, 20260926_02).
        Index(
            "ix_snapshot_attribute_values_owner_key_text",
            "owner_id",
            "attribute_type_key",
            "text_value",
            "object_id",
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_kind: Mapped[str] = mapped_column(String(10), nullable=False)
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
            "workspace_draft_id",
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
            sqlite_where=text("workspace_draft_id IS NULL"),
            postgresql_where=text("workspace_draft_id IS NULL"),
        ),
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_key: Mapped[str] = mapped_column(
        ForeignKey("workspaces.key", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_draft_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_drafts.id", ondelete="CASCADE"), nullable=True, index=True
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


class AuditEvent(Base):
    __tablename__ = "audit_events"

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    aggregate_type: Mapped[str] = mapped_column(String(40), index=True)
    # Wide enough to hold the longest legal Workspace.key (String(160)) for the workspace-scoped
    # lifecycle aggregate (publication retirement aggregates on the real workspace key).
    aggregate_id: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), index=True
    )


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
