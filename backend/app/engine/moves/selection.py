"""What a move selects in its source (Product 0.11 X2, I7, D116, D117).

A selection names types (each with an export's criteria, through the model query's builders),
a subtree (a record and every record under it), records by ID, or nothing: the whole workspace.
A record is selected when every given part selects it. The source is the workspace's live data or
one of its publications (I30). Checked when the move is sent, so a refused selection creates no
job; then read as one statement of IDs when the job binds.
"""

from typing import Any

from sqlalchemy import intersect, select, union_all
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import Publication, RdmObject
from ...models.moves import MoveSelection
from ...models.queries import ModelQuery, QueryContext
from ...models.schema import EngineModel
from ..reads.model_query import plan_model_query
from ..reads.snapshot_reads import SnapshotContext, object_projection, publication_context


def source_context(
    session: Session, workspace_key: str, source_at: str
) -> tuple[SnapshotContext | None, Publication | None]:
    """``None`` for live data, or the publication ``source_at`` names, which must be the source
    workspace's."""
    if source_at == "live":
        return None, None
    publication = session.scalar(
        select(Publication).where(
            Publication.id == source_at, Publication.workspace_key == workspace_key
        )
    )
    if publication is None:
        raise api_error(
            404,
            "PUBLICATION_NOT_FOUND",
            f"Workspace '{workspace_key}' has no publication '{source_at}'",
            {"path": "/sourceAt"},
        )
    return publication_context(session, publication.id), publication


def check_selection(
    session: Session,
    model: EngineModel,
    selection: MoveSelection,
    workspace_key: str,
    context: SnapshotContext | None,
) -> None:
    """Refuse what the source cannot answer: an unknown type or criterion at its pointer, a subtree
    record or a selected record the source does not hold."""
    selected_ids(model, selection, workspace_key, context)
    named = [str(selection.parentObjectId)] if selection.parentObjectId else []
    named += [str(item) for item in selection.objectIds or []]
    if not named:
        return
    tree = _tree(workspace_key, context)
    found = set(session.scalars(select(tree.c.object_id).where(tree.c.object_id.in_(named))))
    if selection.parentObjectId is not None and str(selection.parentObjectId) not in found:
        raise api_error(
            404,
            "OBJECT_NOT_FOUND",
            f"Record '{selection.parentObjectId}' is not in the source",
            {"path": "/selection/parentObjectId"},
        )
    for index, object_id in enumerate(selection.objectIds or []):
        if str(object_id) not in found:
            raise api_error(
                404,
                "OBJECT_NOT_FOUND",
                f"Record '{object_id}' is not in the source",
                {"path": f"/selection/objectIds/{index}"},
            )


def selected_ids(
    model: EngineModel,
    selection: MoveSelection,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Any:
    """The IDs every part of the selection selects, as one statement; ``None`` for the whole
    workspace."""
    parts: list[Any] = []
    if selection.types is not None:
        parts.append(_typed(model, selection, workspace_key, context))
    tree = _tree(workspace_key, context)
    if selection.parentObjectId is not None:
        top = str(selection.parentObjectId)
        subtree = (
            select(tree.c.object_id)
            .where(tree.c.object_id == top)
            .cte("move_subtree", recursive=True)
        )
        below = _tree(workspace_key, context)
        subtree = subtree.union_all(
            select(below.c.object_id).join(subtree, below.c.parent_object_id == subtree.c.object_id)
        )
        parts.append(select(subtree.c.object_id))
    if selection.objectIds is not None:
        parts.append(
            select(tree.c.object_id).where(
                tree.c.object_id.in_([str(item) for item in selection.objectIds])
            )
        )
    if not parts:
        return None
    return intersect(*parts) if len(parts) > 1 else parts[0]


def _typed(
    model: EngineModel,
    selection: MoveSelection,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Any:
    """The selected types' records through the model query, each type with its criteria; a type or
    criterion the model cannot answer is refused at its pointer in the body."""
    query_context = (
        QueryContext(publicationId=context.id) if context is not None else QueryContext()
    )
    selects = []
    for index, item in enumerate(selection.types or []):
        prefix = f"/selection/types/{index}"
        if model.object_type(item.objectTypeKey) is None:
            raise api_error(
                422,
                "INVALID_QUERY",
                f"Unknown object type '{item.objectTypeKey}'",
                {"path": f"{prefix}/objectTypeKey"},
            )
        query = ModelQuery(
            objectTypeKey=item.objectTypeKey, context=query_context, where=item.where
        )
        try:
            planned = plan_model_query(model, query, workspace_key=workspace_key, context=context)
        except ApiError as error:
            if error.code != "INVALID_QUERY" or not error.details:
                raise
            path = str(error.details.get("path", ""))
            raise api_error(
                422, "INVALID_QUERY", error.message, {**error.details, "path": prefix + path}
            ) from error
        selects.append(
            planned.query.statement.with_only_columns(planned.query.record.id).order_by(None)
        )
    return union_all(*selects) if len(selects) > 1 else selects[0]


def _tree(workspace_key: str, context: SnapshotContext | None) -> Any:
    """Every record of the source with its parent, for walks down the tree."""
    if context is not None:
        projection = object_projection(context)
        return select(projection.c.object_id, projection.c.parent_object_id).subquery()
    return (
        select(RdmObject.id.label("object_id"), RdmObject.parent_object_id)
        .where(RdmObject.workspace_key == workspace_key)
        .subquery()
    )
