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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
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
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
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
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
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

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    workspace_key: Mapped[str] = mapped_column(String(160), default="default", index=True)
    application_key: Mapped[str] = mapped_column(String(160), index=True)
    object_type_key: Mapped[str] = mapped_column(String(160), index=True)
    parent_object_id: Mapped[str | None] = mapped_column(
        ForeignKey("objects.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(String(60), default="active", index=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
    datetime_value: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    sequence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    aggregate_type: Mapped[str] = mapped_column(String(40), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
