"""Draft and history reads in SQL (Base 0.8 S2).

A revision's objects and relations are its own rows. A draft's are its base rows (a revision or a
private current-live base) that no draft row replaces, plus its non-deleted draft rows; any draft
row, including a tombstone, hides the base row with the same public ID. Every read here states that
rule as one statement, so a page or a record costs its own rows rather than the whole membership.

Validation, activation and draft writes still resolve the whole graph through
``workspace_revisions.effective_draft_membership``; they need all of it by definition.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import Row, String, literal, or_, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ..errors import api_error
from ..models.database import (
    SnapshotAttributeValue,
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
from ..models.schema import EngineModel
from .objects import (
    ObjectColumns,
    ObjectQuery,
    _query_error,
    get_object_type,
    refine_object_query,
    validate_application_object_type,
)
from .pagination import text_key

# Draft and history rows record no timestamps; a query on them is refused, not matched as empty.
UNRECORDED_TIMESTAMPS = {"createdAt": "Created", "updatedAt": "Updated"}


@dataclass(frozen=True)
class SnapshotBase:
    """The immutable rows a draft starts from: a revision or a private current-live base."""

    objects: Any
    relations: Any
    owner_column: str
    owner_id: str


@dataclass(frozen=True)
class SnapshotContext:
    """One draft or revision read context."""

    kind: Literal["draft", "revision"]
    id: str
    workspace_key: str
    draft: WorkspaceDraft | None
    base: SnapshotBase | None


def draft_context(session: Session, draft_id: str) -> SnapshotContext:
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    base = None
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
        base = SnapshotBase(
            WorkspaceRevisionObject, WorkspaceRevisionRelation, "revision_id", revision.id
        )
    if draft.base_id is not None:
        current_live = session.get(WorkspaceDraftBase, draft.base_id)
        if current_live is None or current_live.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft current-live base is missing or belongs to another workspace",
            )
        base = SnapshotBase(
            WorkspaceDraftBaseObject, WorkspaceDraftBaseRelation, "base_id", current_live.id
        )
    return SnapshotContext("draft", draft.id, draft.workspace_key, draft, base)


def revision_context(session: Session, revision_id: str) -> SnapshotContext:
    revision = session.scalar(select(WorkspaceRevision).where(WorkspaceRevision.id == revision_id))
    if revision is None:
        raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
    return SnapshotContext(
        "revision",
        revision.id,
        revision.workspace_key,
        None,
        SnapshotBase(WorkspaceRevisionObject, WorkspaceRevisionRelation, "revision_id", revision.id),
    )


def object_projection(
    context: SnapshotContext,
    *,
    object_type_key: str | None = None,
    application_key: str | None = None,
    parent_object_id: str | None = None,
    object_ids: Iterable[str] | None = None,
) -> Subquery:
    """The context's effective object rows, narrowed inside each arm so indexes apply.

    ``values_owner_id`` names the owner of each row's typed values in ``snapshot_attribute_values``.
    """
    ids = list(object_ids) if object_ids is not None else None

    def arm(entity: Any, owner_id: str, *conditions: Any) -> Any:
        where = list(conditions)
        if object_type_key is not None:
            where.append(entity.object_type_key == object_type_key)
        if application_key:
            where.append(entity.application_key == application_key)
        if parent_object_id:
            where.append(entity.parent_object_id == parent_object_id)
        if ids is not None:
            where.append(entity.object_id.in_(ids))
        return select(
            entity.object_id,
            entity.application_key,
            entity.object_type_key,
            entity.name,
            entity.parent_object_id,
            entity.attributes,
            entity.version,
            literal(owner_id, String).label("values_owner_id"),
        ).where(*where)

    return _effective(
        context,
        WorkspaceDraftObject,
        "object_id",
        arm,
        lambda base: getattr(base.objects, base.owner_column) == base.owner_id,
        lambda base: base.objects,
        name="snapshot_objects",
    )


def relation_projection(
    context: SnapshotContext,
    *,
    object_id: str | None = None,
    direction: str = "both",
    relation_type_key: str | None = None,
    relation_ids: Iterable[str] | None = None,
) -> Subquery:
    """The context's effective relation rows touching ``object_id`` in ``direction``."""
    ids = list(relation_ids) if relation_ids is not None else None

    def arm(entity: Any, _owner_id: str, *conditions: Any) -> Any:
        where = list(conditions)
        if object_id is not None:
            ends = []
            if direction in {"outgoing", "both"}:
                ends.append(entity.from_object_id == object_id)
            if direction in {"incoming", "both"}:
                ends.append(entity.to_object_id == object_id)
            where.append(or_(*ends))
        if relation_type_key:
            where.append(entity.relation_type_key == relation_type_key)
        if ids is not None:
            where.append(entity.relation_id.in_(ids))
        return select(
            entity.relation_id,
            entity.relation_type_key,
            entity.from_object_id,
            entity.to_object_id,
            entity.attributes,
            entity.version,
        ).where(*where)

    return _effective(
        context,
        WorkspaceDraftRelation,
        "relation_id",
        arm,
        lambda base: getattr(base.relations, base.owner_column) == base.owner_id,
        lambda base: base.relations,
        name="snapshot_relations",
    )


def _effective(context, overlay, identity, arm, base_filter, base_entity, *, name) -> Subquery:
    base = context.base
    if context.kind == "revision":
        return arm(base_entity(base), base.owner_id, base_filter(base)).subquery(name)
    arms = []
    if base is not None:
        entity = base_entity(base)
        overridden = select(getattr(overlay, identity)).where(overlay.draft_id == context.id)
        arms.append(
            arm(entity, base.owner_id, base_filter(base), ~getattr(entity, identity).in_(overridden))
        )
    arms.append(arm(overlay, context.id, overlay.draft_id == context.id, overlay.is_deleted.is_(False)))
    return (union_all(*arms) if len(arms) > 1 else arms[0]).subquery(name)


def find_objects(session: Session, context: SnapshotContext, object_ids: Iterable[str]) -> dict[str, Row]:
    ids = list(dict.fromkeys(object_ids))
    if not ids:
        return {}
    projection = object_projection(context, object_ids=ids)
    return {row.object_id: row for row in session.execute(select(projection))}


def find_object(
    session: Session, context: SnapshotContext, object_id: str, object_type_key: str | None = None
) -> Row | None:
    row = find_objects(session, context, [object_id]).get(object_id)
    if row is None or (object_type_key is not None and row.object_type_key != object_type_key):
        return None
    return row


def find_relation(session: Session, context: SnapshotContext, relation_id: str) -> Row | None:
    projection = relation_projection(context, relation_ids=[relation_id])
    return session.execute(select(projection)).first()


def object_path(session: Session, context: SnapshotContext, item: Any) -> list[dict[str, Any]]:
    """The record's ancestor path, one lookup per level: its cost is the hierarchy depth."""
    path, seen, current = [], set(), item
    while current is not None and current.object_id not in seen:
        seen.add(current.object_id)
        path.append(
            {"id": current.object_id, "name": current.name, "objectTypeKey": current.object_type_key}
        )
        parent_id = current.parent_object_id
        current = find_object(session, context, parent_id) if parent_id else None
    path.reverse()
    return path


def snapshot_object_columns(projection: Subquery) -> ObjectColumns:
    values = SnapshotAttributeValue
    return ObjectColumns(
        source=projection,
        id=projection.c.object_id,
        name=projection.c.name,
        values=values,
        value_match=(
            values.owner_id == projection.c.values_owner_id,
            values.object_id == projection.c.object_id,
        ),
        builtin={"id": projection.c.object_id, "name": projection.c.name},
        default_sort="id",
        tiebreak=lambda descending: text_key(
            "id", projection.c.object_id, "object_id", descending=descending
        ),
    )


def build_snapshot_object_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_type_key: str,
    application_key: str | None,
    parent_object_id: str | None,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
) -> ObjectQuery:
    """The draft or revision object collection query, with the same contract as a live one."""
    object_type = get_object_type(model, object_type_key)
    if application_key:
        validate_application_object_type(model, application_key, object_type_key)
    for field, operator, _raw in field_filters:
        if field in UNRECORDED_TIMESTAMPS:
            _query_error(
                "invalid_filter",
                f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in drafts or history",
                f"filter.{field}.{operator}",
            )
    sort_field = (sort or "").removeprefix("-")
    if sort_field in UNRECORDED_TIMESTAMPS:
        _query_error(
            "invalid_sort",
            f"{UNRECORDED_TIMESTAMPS[sort_field]} is not recorded in drafts or history",
            "sort",
        )
    projection = object_projection(
        context,
        object_type_key=object_type_key,
        application_key=application_key,
        parent_object_id=parent_object_id,
    )
    statement, keys, normalized_filters = refine_object_query(
        model,
        snapshot_object_columns(projection),
        select(projection),
        object_type=object_type,
        search=search,
        sort=sort,
        field_filters=field_filters,
    )
    owner = "draftId" if context.kind == "draft" else "revisionId"
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={
            owner: context.id,
            "applicationKey": application_key,
            "objectTypeKey": object_type_key,
            "parentObjectId": parent_object_id,
            "search": search,
            "typedFilters": normalized_filters,
        },
    )


def object_scope(context: SnapshotContext) -> str:
    return "objects-draft" if context.kind == "draft" else "objects-revision"
