"""SQL projections of effective draft membership for bounded mapping queries."""

from sqlalchemy import Select, literal, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ..errors import api_error
from ..models.database import (
    WorkspaceDraft,
    WorkspaceDraftBase,
    WorkspaceDraftBaseObject,
    WorkspaceDraftBaseRelation,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)


def draft_mapping_projection(session: Session, draft_id: str) -> tuple[Subquery, Subquery]:
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
    if draft.base_id:
        base = session.get(WorkspaceDraftBase, draft.base_id)
        if base is None or base.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Draft base is missing or belongs to another workspace",
            )
        object_base, relation_base = WorkspaceDraftBaseObject, WorkspaceDraftBaseRelation
        base_filter = object_base.base_id == draft.base_id
        relation_filter = relation_base.base_id == draft.base_id
    elif draft.derived_from_revision_id:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == draft.derived_from_revision_id)
        )
        if revision is None or revision.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Draft base revision is missing or belongs to another workspace",
            )
        object_base, relation_base = WorkspaceRevisionObject, WorkspaceRevisionRelation
        base_filter = object_base.revision_id == revision.id
        relation_filter = relation_base.revision_id == revision.id
    else:
        raise api_error(
            409,
            "workspace_draft_base_invalid",
            "Draft has no immutable base; recreate the draft from live data",
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
        )

    # Any overlay, including a tombstone, hides the base ID. Only non-deleted
    # overlays are added back. Both unions execute inside the mapping read snapshot.
    object_overrides = select(WorkspaceDraftObject.object_id).where(
        WorkspaceDraftObject.draft_id == draft_id
    )
    relation_overrides = select(WorkspaceDraftRelation.relation_id).where(
        WorkspaceDraftRelation.draft_id == draft_id
    )
    return (
        union_all(
            objects(object_base).where(base_filter, ~object_base.object_id.in_(object_overrides)),
            objects(WorkspaceDraftObject).where(
                WorkspaceDraftObject.draft_id == draft_id,
                WorkspaceDraftObject.is_deleted.is_(False),
            ),
        ).subquery("mapping_objects"),
        union_all(
            relations(relation_base).where(
                relation_filter, ~relation_base.relation_id.in_(relation_overrides)
            ),
            relations(WorkspaceDraftRelation).where(
                WorkspaceDraftRelation.draft_id == draft_id,
                WorkspaceDraftRelation.is_deleted.is_(False),
            ),
        ).subquery("mapping_relations"),
    )


def revision_mapping_projection(session: Session, revision_id: str) -> tuple[Subquery, Subquery]:
    """Project one immutable workspace revision into the shared mapping query shape."""
    revision = session.scalar(select(WorkspaceRevision).where(WorkspaceRevision.id == revision_id))
    if revision is None:
        raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
    objects = select(
        WorkspaceRevisionObject.object_id.label("id"),
        WorkspaceRevisionObject.application_key,
        WorkspaceRevisionObject.object_type_key,
        WorkspaceRevisionObject.name,
        WorkspaceRevisionObject.parent_object_id,
        WorkspaceRevisionObject.attributes,
        literal(None).label("created_at"),
        literal(None).label("updated_at"),
    ).where(WorkspaceRevisionObject.revision_id == revision_id)
    relations = select(
        WorkspaceRevisionRelation.relation_id.label("id"),
        WorkspaceRevisionRelation.relation_type_key,
        WorkspaceRevisionRelation.from_object_id,
        WorkspaceRevisionRelation.to_object_id,
        WorkspaceRevisionRelation.attributes,
    ).where(WorkspaceRevisionRelation.revision_id == revision_id)
    return objects.subquery("mapping_objects"), relations.subquery("mapping_relations")
