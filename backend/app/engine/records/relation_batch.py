"""Setting attribute values on many relationships at once (0.13 RV).

Every item is decided over the batch lookup, each seeing the items before it, and nothing is written
unless every item holds: one stale version or one invalid value refuses the whole batch, naming each
item that failed. What is written is written as one batch through the write unit (``bulk.py``), so
the batch and a single ``PATCH /relations/{id}`` share one decide step and answer with the same
codes. An item's ``attributes`` are the values to set over the relationship's stored ones; ``null``
clears a value.
"""

from dataclasses import dataclass
from typing import Any

from ...errors import ApiError, api_error
from ...models.schema import EngineModel
from . import rules
from .batch_lookup import BatchLookup
from .relation_writes import decide_relation_create, decide_relation_update


@dataclass(frozen=True)
class RelationValues:
    """One item: the relationship, the version the caller read and the values to set."""

    relation_id: str
    expected_version: int
    attributes: dict[str, Any]


@dataclass(frozen=True)
class RelationLink:
    """A relationship to create: its type, ends and values (a grid change's "also link")."""

    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: dict[str, Any]


def decide_relation_values(
    lookup: BatchLookup,
    model: EngineModel,
    items: list[RelationValues],
    links: list[RelationLink] | None = None,
) -> None:
    """Decide every item over ``lookup``, then every link, each seeing those before it; raise
    ``RELATION_BATCH_REFUSED`` with every one that failed (its position, relationship, code,
    message and details) when any did."""
    links = links or []
    ids = [item.relation_id for item in items]
    if len(set(ids)) != len(ids):
        repeated = sorted({item for item in ids if ids.count(item) > 1})
        raise api_error(
            422,
            "DUPLICATE_BATCH_ITEMS",
            "A relationship may appear once in a batch",
            {"relationIds": repeated},
        )
    lookup.prefetch_relation_ids(ids)
    failed: list[dict[str, Any]] = []
    for position, item in enumerate(items):
        relation = None
        try:
            with lookup.deciding():
                relation = lookup.relation(item.relation_id)
                if relation is None:
                    raise api_error(
                        404, "RELATION_NOT_FOUND", f"Relation '{item.relation_id}' not found"
                    )
                merged = {
                    key: value
                    for key, value in {**(relation.attributes or {}), **item.attributes}.items()
                    if value is not None
                }
                decide_relation_update(lookup, model, relation, item.expected_version, merged)
        except ApiError as error:
            failed.append(
                {
                    "index": position,
                    "relationId": item.relation_id,
                    # The ends, so a caller can say which pair was refused (absent when the relationship is).
                    **(
                        {
                            "fromObjectId": relation.from_object_id,
                            "toObjectId": relation.to_object_id,
                        }
                        if relation is not None
                        else {}
                    ),
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            )
    if links:
        ends = [end for link in links for end in (link.from_object_id, link.to_object_id)]
        lookup.prefetch_objects(ends)
        for relation_type_key in {link.relation_type_key for link in links}:
            same = [link for link in links if link.relation_type_key == relation_type_key]
            lookup.prefetch_relations(
                [link.from_object_id for link in same], "outgoing", [relation_type_key]
            )
            lookup.prefetch_relations(
                [link.to_object_id for link in same], "incoming", [relation_type_key]
            )
    for offset, link in enumerate(links, start=len(items)):
        try:
            with lookup.deciding():
                found = lookup.objects([link.from_object_id, link.to_object_id])
                for end in (link.from_object_id, link.to_object_id):
                    if end not in found:
                        raise rules.relation_endpoint_missing(end)
                decide_relation_create(
                    lookup,
                    model,
                    link.relation_type_key,
                    found[link.from_object_id],
                    found[link.to_object_id],
                    link.attributes,
                )
        except ApiError as error:
            failed.append(
                {
                    "index": offset,
                    "relationId": None,
                    "fromObjectId": link.from_object_id,
                    "toObjectId": link.to_object_id,
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            )
    if failed:
        stale = any(entry["code"] in _CONFLICTS for entry in failed)
        raise api_error(
            409 if stale else 422,
            "RELATION_BATCH_REFUSED",
            f"{len(failed)} of {len(items) + len(links)} items were refused; nothing was written",
            {"items": failed},
        )


# A stale item sends the caller to refresh, whatever else was wrong in the batch.
_CONFLICTS = frozenset({"VERSION_CONFLICT"})
