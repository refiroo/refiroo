"""Reading a change set for a write or a validation: the change set itself, its claim, its pinned model and its effective membership."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    Workspace,
)
from ..model.registry import resolve_pinned_release
from ..records.writes import ChangeSetWrites


@dataclass(frozen=True)
class EffectiveChangeSetMembership:
    change_set: ChangeSet
    objects: tuple[PublicationObject | ChangeSetBaseObject | ChangeSetObject, ...]
    relations: tuple[
        PublicationRelation | ChangeSetBaseRelation | ChangeSetRelation, ...
    ]


def effective_change_set_membership(session: Session, change_set_id: str) -> EffectiveChangeSetMembership:
    """Resolve a change set's immutable base plus its changed rows and tombstones.

    A change set row replaces the same stable public ID from its base.  A tombstone hides that base row;
    therefore an edit does not copy unrelated records from the source publication.
    """
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "change_set_not_found", f"Change set '{change_set_id}' not found")
    objects: dict[
        str, PublicationObject | ChangeSetBaseObject | ChangeSetObject
    ] = {}
    relations: dict[
        str, PublicationRelation | ChangeSetBaseRelation | ChangeSetRelation
    ] = {}
    if change_set.derived_from_publication_id is not None:
        publication = session.scalar(
            select(Publication).where(Publication.id == change_set.derived_from_publication_id)
        )
        if publication is None or publication.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set base publication is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(PublicationObject).where(
                    PublicationObject.publication_id == publication.id
                )
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(PublicationRelation).where(
                    PublicationRelation.publication_id == publication.id
                )
            )
        }
    if change_set.base_id is not None:
        base = session.get(ChangeSetBase, change_set.base_id)
        if base is None or base.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set current-live base is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(ChangeSetBaseObject).where(ChangeSetBaseObject.base_id == base.id)
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(ChangeSetBaseRelation).where(
                    ChangeSetBaseRelation.base_id == base.id
                )
            )
        }
    for item in session.scalars(
        select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set.id)
    ):
        if item.is_deleted:
            objects.pop(item.object_id, None)
        else:
            objects[item.object_id] = item
    for item in session.scalars(
        select(ChangeSetRelation).where(ChangeSetRelation.change_set_id == change_set.id)
    ):
        if item.is_deleted:
            relations.pop(item.relation_id, None)
        else:
            relations[item.relation_id] = item
    return EffectiveChangeSetMembership(
        change_set=change_set,
        objects=tuple(objects[key] for key in sorted(objects)),
        relations=tuple(relations[key] for key in sorted(relations)),
    )


def load_change_set(session: Session, change_set_id: str, *, for_update: bool = False) -> ChangeSet:
    """The change set; ``for_update`` locks it for a write in an active workspace.

    A write first takes a key share lock on the workspace row (lock order: workspace, then change
    set), so a retirement or deletion waits for the write and a write waits for them, while live
    writes and other change sets' writes go on beside it (0.9.0-alpha.1 PG3).
    """
    if for_update:
        _lock_workspace(session, change_set_id)
    statement = select(ChangeSet).where(ChangeSet.id == change_set_id)
    if for_update:
        statement = statement.with_for_update()
    item = session.scalar(statement)
    if item is None:
        raise api_error(404, "change_set_not_found", f"Change set '{change_set_id}' not found")
    return item


def _lock_workspace(session: Session, change_set_id: str) -> None:
    # A change set never moves to another workspace, so its key is read without a lock.
    workspace_key = session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == change_set_id)
    )
    if workspace_key is None:
        return  # The change set's own load answers 404.
    status = session.scalar(
        select(Workspace.status)
        .where(Workspace.key == workspace_key)
        .with_for_update(read=True, key_share=True)
    )
    if status is None:
        raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
    if status != "active":
        raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")


def ensure_change_set_writable(session: Session, change_set_id: str) -> ChangeSet:
    """Resolve a change set and reject mutations against a retired workspace."""
    return load_change_set(session, change_set_id, for_update=True)


def claim_change_set_version(session: Session, change_set: ChangeSet, expected: int) -> None:
    """Claim the change set aggregate version for an external write operation."""
    ChangeSetWrites(session, change_set).claim(expected)


def change_set_model(session: Session, change_set: ChangeSet) -> Any:
    return resolve_pinned_release(session, change_set.model_release_id, require_ready=False).model
