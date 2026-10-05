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
    func,
    literal_column,
    text,
)
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


class ChangeSet(Base):
    __tablename__ = "change_sets"

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
    # A change to live data takes the next position of its workspace's feed (Base 0.9 F1); other
    # entries have none. ``feed_subject`` names what the entry changed (object or relation type,
    # relation ends), kept here since a later delete leaves nothing to look it up by.
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
    feed_subject: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


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


class Job(Base):
    """A bulk write, import or export: its parameters, state and counts (Base 0.9, ADR-036).

    A synchronous batch is a job run inline. Its outcomes are ``JobItem`` rows in item order; the
    counts and ``result`` summarize them once the job is finished.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("kind IN ('batch', 'import', 'export')", name="ck_job_kind"),
        CheckConstraint(
            "state IN ('queued', 'running', 'awaiting_confirmation', 'completed', 'failed', "
            "'cancelled', 'expired')",
            name="ck_job_state",
        ),
        Index("ix_jobs_workspace_created", "workspace_key", "sequence_id"),
        Index("ix_jobs_state", "state", "sequence_id"),
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
    )

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.sequence_id", ondelete="CASCADE"), nullable=False
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
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

