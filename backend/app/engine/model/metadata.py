"""Projections that attach stable public IDs to active-model definitions.

Installed releases are immutable, so the key-to-public-ID maps for a release never change once the
release exists. They are therefore cached per release row id; the cache is cleared alongside the
parsed-model cache in :class:`~app.engine.model.registry.ModelRegistry`.
"""

from dataclasses import dataclass
from threading import Lock
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import (
    ApplicationMeta,
    AttributeTypeMeta,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
)


@dataclass(frozen=True)
class MetadataIdentifiers:
    """Public IDs of one installed release's metadata projection, keyed by model key."""

    applications: dict[str, str]
    attribute_types: dict[str, str]
    object_types: dict[str, str]
    relation_types: dict[str, str]
    object_type_attributes: dict[tuple[str, str], str]
    object_type_relations: dict[tuple[str, str, str], str]


_identifier_cache: dict[int, MetadataIdentifiers] = {}
_identifier_lock = Lock()


def clear_metadata_cache() -> None:
    with _identifier_lock:
        _identifier_cache.clear()


def metadata_identifiers(session: Session, release_db_id: int) -> MetadataIdentifiers:
    """Load, and then reuse, the public-ID maps of one immutable release."""
    with _identifier_lock:
        cached = _identifier_cache.get(release_db_id)
    if cached is not None:
        return cached

    identifiers = MetadataIdentifiers(
        applications=_keyed(session, ApplicationMeta, release_db_id),
        attribute_types=_keyed(session, AttributeTypeMeta, release_db_id),
        object_types=_keyed(session, ObjectTypeMeta, release_db_id),
        relation_types=_keyed(session, RelationTypeMeta, release_db_id),
        object_type_attributes={
            (row.object_type_key, row.attribute_type_key): row.public_id
            for row in session.scalars(
                select(ObjectTypeAttributeMeta).where(
                    ObjectTypeAttributeMeta.model_release_id == release_db_id
                )
            )
        },
        object_type_relations={
            (row.relation_type_key, row.from_object_type_key, row.to_object_type_key): row.public_id
            for row in session.scalars(
                select(ObjectTypeRelationMeta).where(
                    ObjectTypeRelationMeta.model_release_id == release_db_id
                )
            )
        },
    )
    with _identifier_lock:
        _identifier_cache[release_db_id] = identifiers
    return identifiers


def _keyed(session: Session, entity: Any, release_db_id: int) -> dict[str, str]:
    return {
        row.key: row.public_id
        for row in session.scalars(
            select(entity).where(entity.model_release_id == release_db_id)
        )
    }
