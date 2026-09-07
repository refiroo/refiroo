"""Persistence-only helpers for ADR-024 workspace revision membership.

WP6 deliberately exposes no lifecycle routes.  These helpers define the copy-on-write read rule so
WP7 editing and publication can reuse one authoritative interpretation of draft membership.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.database import (
    WorkspaceDraft,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)


@dataclass(frozen=True)
class EffectiveDraftMembership:
    draft: WorkspaceDraft
    objects: tuple[WorkspaceRevisionObject | WorkspaceDraftObject, ...]
    relations: tuple[WorkspaceRevisionRelation | WorkspaceDraftRelation, ...]


def effective_draft_membership(session: Session, draft_id: str) -> EffectiveDraftMembership:
    """Resolve a draft's immutable base plus its changed rows and tombstones.

    A draft row replaces the same stable public ID from its base.  A tombstone hides that base row;
    therefore an edit does not copy unrelated records from the source revision.
    """
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    objects: dict[str, WorkspaceRevisionObject | WorkspaceDraftObject] = {}
    relations: dict[str, WorkspaceRevisionRelation | WorkspaceDraftRelation] = {}
    if draft.derived_from_revision_id is not None:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == draft.derived_from_revision_id)
        )
        if revision is None or revision.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft base revision is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(WorkspaceRevisionObject).where(
                    WorkspaceRevisionObject.revision_id == revision.id
                )
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(WorkspaceRevisionRelation).where(
                    WorkspaceRevisionRelation.revision_id == revision.id
                )
            )
        }
    for item in session.scalars(
        select(WorkspaceDraftObject).where(WorkspaceDraftObject.draft_id == draft.id)
    ):
        if item.is_deleted:
            objects.pop(item.object_id, None)
        else:
            objects[item.object_id] = item
    for item in session.scalars(
        select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft.id)
    ):
        if item.is_deleted:
            relations.pop(item.relation_id, None)
        else:
            relations[item.relation_id] = item
    return EffectiveDraftMembership(
        draft=draft,
        objects=tuple(objects[key] for key in sorted(objects)),
        relations=tuple(relations[key] for key in sorted(relations)),
    )
