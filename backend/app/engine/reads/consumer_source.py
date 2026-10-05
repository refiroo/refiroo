"""Where a consumer read's rows are: live data, or one publication (Base 0.9 C6a).

Every consumer read is written over the live tables' shape: records (``RdmObject``), their typed
values (``AttributeValue``) and relationships (``ObjectRelation``), scoped by the workspace. A
publication holds the same rows in its own tables (``publication_objects``, the publication's
``snapshot_attribute_values`` and ``publication_relations``). The publication source presents them in
the live shape: each entity is the live class mapped onto a subquery of the publication's rows, so a
read builds the same statements over either. PostgreSQL pulls such a subquery into the statement, so
the publication's indexes serve it as the live ones serve live reads.

A read uses ``objects``, ``values`` and ``relations`` where the live code names a table directly, and
``object_alias()`` and its siblings where it aliases one. The live source returns the live classes
and ``aliased`` of them, so live statements are unchanged. A publication alias is a fresh subquery:
aliasing an entity mapped onto a subquery would alias the live table instead.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Integer, String, literal, null, select
from sqlalchemy.orm import aliased

from ...models.database import (
    AttributeValue,
    ObjectRelation,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    SnapshotAttributeValue,
    UTCDateTime,
)

# Where a pinned read's cursor scope names its publication; the router reads it back from a cursor
# so that ``publication=latest`` continues in the cursor's publication (C-D64).
PUBLICATION_SCOPE = ":publication:"
_TYPED = ("text_value", "integer_value", "decimal_value", "boolean_value", "date_value", "datetime_value", "json_value")


@dataclass(frozen=True)
class ConsumerSource:
    """The rows one consumer read reads: the workspace's live data, or one of its publications."""

    workspace_key: str
    publication_id: str | None = None
    objects: Any = field(init=False, compare=False)
    values: Any = field(init=False, compare=False)
    relations: Any = field(init=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "objects", RdmObject if self.publication_id is None else self.object_alias())
        object.__setattr__(self, "values", AttributeValue if self.publication_id is None else self.value_alias())
        object.__setattr__(
            self, "relations", ObjectRelation if self.publication_id is None else self.relation_alias()
        )

    @property
    def pinned(self) -> bool:
        return self.publication_id is not None

    def object_alias(self) -> Any:
        if self.publication_id is None:
            return aliased(RdmObject)
        rows = PublicationObject
        published = select(
            rows.sequence_id.label("sequence_id"),
            rows.object_id.label("id"),
            literal(self.workspace_key, String).label("workspace_key"),
            rows.application_key.label("application_key"),
            rows.object_type_key.label("object_type_key"),
            rows.parent_object_id.label("parent_object_id"),
            rows.name.label("name"),
            rows.version.label("version"),
            null().cast(UTCDateTime()).label("created_at"),
            null().cast(UTCDateTime()).label("updated_at"),
        ).where(rows.publication_id == self.publication_id)
        return aliased(RdmObject, published.subquery(), adapt_on_names=True)

    def value_alias(self) -> Any:
        if self.publication_id is None:
            return aliased(AttributeValue)
        rows = SnapshotAttributeValue
        published = select(
            rows.sequence_id.label("sequence_id"),
            null().cast(String).label("id"),
            rows.object_id.label("object_id"),
            rows.attribute_type_key.label("attribute_type_key"),
            rows.value_type.label("value_type"),
            *(getattr(rows, name).label(name) for name in _TYPED),
            literal("own", String).label("value_source"),
            literal(1, Integer).label("version"),
        ).where(rows.owner_id == self.publication_id, rows.owner_kind == "publication")
        return aliased(AttributeValue, published.subquery(), adapt_on_names=True)

    def relation_alias(self) -> Any:
        if self.publication_id is None:
            return aliased(ObjectRelation)
        rows = PublicationRelation
        published = select(
            rows.sequence_id.label("sequence_id"),
            rows.relation_id.label("id"),
            rows.relation_type_key.label("relation_type_key"),
            rows.from_object_id.label("from_object_id"),
            rows.to_object_id.label("to_object_id"),
            rows.attributes.label("attributes"),
            rows.version.label("version"),
            null().cast(UTCDateTime()).label("created_at"),
            null().cast(UTCDateTime()).label("updated_at"),
        ).where(rows.publication_id == self.publication_id)
        return aliased(ObjectRelation, published.subquery(), adapt_on_names=True)


def cursor_scope(scope: str, source: ConsumerSource) -> str:
    """A read's cursor scope, naming the publication a pinned read pages: a cursor then continues in
    it, and is refused by a read of live data or of another publication (C-D64)."""
    return scope if source.publication_id is None else f"{scope}{PUBLICATION_SCOPE}{source.publication_id}"
