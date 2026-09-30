"""Responses of the model-aware object query (Base 0.9 Q3, D17).

Every item carries ``id``, ``objectTypeKey`` and ``version``. Without ``select`` it is the object
list's item; with ``select`` the chosen values are under ``fields``, keyed by field, since attribute
keys are model keys and could equal a property of the item itself. ``expanded`` holds one entry per
``expand`` of the query, in its order, and is omitted when the query expands nothing.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from .common import CollectionPage, omitted_when_none, without_default
from .records import ObjectResponse


class SelectedRecord(BaseModel):
    """A record with the fields a ``select`` named.

    ``fields`` maps each selected field to its value: a built-in field's, an attribute's (null when
    the record has none), or for ``ancestor:<type>`` the ``id`` and ``name`` of the ancestor of that
    type nearest the root (null when there is none).
    """

    id: str
    objectTypeKey: str
    version: int
    fields: dict[str, Any]


class ExpandedRecord(BaseModel):
    """A relation of the item and the record at its other end."""

    relationId: str
    object: ObjectResponse | SelectedRecord


class ExpandedRelations(BaseModel):
    """The first records at the other end of one binding, in name order, and how many there are.

    ``nextCursor`` continues on ``GET /api/v1/relations`` with the item as ``objectId``, the same
    ``direction``, ``relationTypeKey`` and context, and the default sort; null when ``items`` holds
    every one of them.
    """

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    count: int
    items: list[ExpandedRecord]
    nextCursor: str | None


def _expanded() -> Any:
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class QueryObject(ObjectResponse):
    """An item without ``select``: the object list's item."""

    expanded: list[ExpandedRelations] | SkipJsonSchema[None] = _expanded()


class QuerySelectedObject(SelectedRecord):
    """An item with ``select``."""

    expanded: list[ExpandedRelations] | SkipJsonSchema[None] = _expanded()


class ObjectQueryPage(CollectionPage[QueryObject | QuerySelectedObject]):
    """One page of the query's records in its sort order (ADR-030)."""
