"""SQL projections of effective change set membership for bounded mapping queries."""

from sqlalchemy import JSON, Select, literal, null, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
)

_NO_ORIGIN = null().cast(JSON)


def change_set_mapping_projection(session: Session, change_set_id: str) -> tuple[Subquery, Subquery]:
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
    if change_set.base_id:
        base = session.get(ChangeSetBase, change_set.base_id)
        if base is None or base.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "CHANGE_SET_BASE_INVALID",
                "Change set base is missing or belongs to another workspace",
            )
        object_base, relation_base = ChangeSetBaseObject, ChangeSetBaseRelation
        base_filter = object_base.base_id == change_set.base_id
        relation_filter = relation_base.base_id == change_set.base_id
    elif change_set.derived_from_publication_id:
        publication = session.scalar(
            select(Publication).where(Publication.id == change_set.derived_from_publication_id)
        )
        if publication is None or publication.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "CHANGE_SET_BASE_INVALID",
                "Change set base publication is missing or belongs to another workspace",
            )
        object_base, relation_base = PublicationObject, PublicationRelation
        base_filter = object_base.publication_id == publication.id
        relation_filter = relation_base.publication_id == publication.id
    else:
        raise api_error(
            409,
            "CHANGE_SET_BASE_INVALID",
            "Change set has no immutable base; recreate the change set from live data",
        )

    def objects(entity) -> Select:
        return select(
            entity.object_id.label("id"),
            entity.application_key,
            entity.object_type_key,
            entity.name,
            entity.parent_object_id,
            entity.attributes,
            literal(None).label("created_at"),
            literal(None).label("updated_at"),
        )

    def relations(entity) -> Select:
        return select(
            entity.relation_id.label("id"),
            entity.relation_type_key,
            entity.from_object_id,
            entity.to_object_id,
            entity.attributes,
            entity.version,
            # Who proposed the edge when a person did not (0.16 AP2); only a change set holds one.
            (entity.origin if entity is ChangeSetRelation else _NO_ORIGIN).label("origin"),
        )

    # Any overlay, including a tombstone, hides the base ID. Only non-deleted
    # overlays are added back. Both unions execute inside the mapping read snapshot.
    object_overrides = select(ChangeSetObject.object_id).where(
        ChangeSetObject.change_set_id == change_set_id
    )
    relation_overrides = select(ChangeSetRelation.relation_id).where(
        ChangeSetRelation.change_set_id == change_set_id
    )
    return (
        union_all(
            objects(object_base).where(base_filter, ~object_base.object_id.in_(object_overrides)),
            objects(ChangeSetObject).where(
                ChangeSetObject.change_set_id == change_set_id,
                ChangeSetObject.is_deleted.is_(False),
            ),
        ).subquery("mapping_objects"),
        union_all(
            relations(relation_base).where(
                relation_filter, ~relation_base.relation_id.in_(relation_overrides)
            ),
            relations(ChangeSetRelation).where(
                ChangeSetRelation.change_set_id == change_set_id,
                ChangeSetRelation.is_deleted.is_(False),
            ),
        ).subquery("mapping_relations"),
    )


def publication_mapping_projection(session: Session, publication_id: str) -> tuple[Subquery, Subquery]:
    """Project one immutable publication into the shared mapping query shape."""
    publication = session.scalar(select(Publication).where(Publication.id == publication_id))
    if publication is None:
        raise api_error(404, "PUBLICATION_NOT_FOUND", "Publication not found")
    objects = select(
        PublicationObject.object_id.label("id"),
        PublicationObject.application_key,
        PublicationObject.object_type_key,
        PublicationObject.name,
        PublicationObject.parent_object_id,
        PublicationObject.attributes,
        literal(None).label("created_at"),
        literal(None).label("updated_at"),
    ).where(PublicationObject.publication_id == publication_id)
    relations = select(
        PublicationRelation.relation_id.label("id"),
        PublicationRelation.relation_type_key,
        PublicationRelation.from_object_id,
        PublicationRelation.to_object_id,
        PublicationRelation.attributes,
        PublicationRelation.version,
        _NO_ORIGIN.label("origin"),
    ).where(PublicationRelation.publication_id == publication_id)
    return objects.subquery("mapping_objects"), relations.subquery("mapping_relations")


def context_projection(
    session: Session,
    workspace_key: str,
    change_set_id: str | None,
    publication_id: str | None,
) -> tuple[Subquery, Subquery]:
    """The objects and relations of live data, a change set or a publication, in one shape."""
    if change_set_id:
        return change_set_mapping_projection(session, change_set_id)
    if publication_id:
        return publication_mapping_projection(session, publication_id)
    objects = (
        select(
            RdmObject.id,
            RdmObject.application_key,
            RdmObject.object_type_key,
            RdmObject.name,
            RdmObject.parent_object_id,
            literal(None).label("attributes"),
            RdmObject.created_at,
            RdmObject.updated_at,
        )
        .where(RdmObject.workspace_key == workspace_key)
        .subquery("mapping_objects")
    )
    relations = select(
        ObjectRelation.id,
        ObjectRelation.relation_type_key,
        ObjectRelation.from_object_id,
        ObjectRelation.to_object_id,
        ObjectRelation.attributes,
        ObjectRelation.version,
        _NO_ORIGIN.label("origin"),
    ).subquery("mapping_relations")
    return objects, relations
