from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.api import AttributeOutput, ObjectResponse
from ..models.database import ObjectRelation, RdmObject
from ..models.schema import EngineModel, ObjectTypeDefinition
from .attributes import load_attribute_values


def get_object_type(model: EngineModel, object_type_key: str) -> ObjectTypeDefinition:
    definition = model.object_type(object_type_key)
    if not definition:
        raise api_error(404, "unknown_object_type", f"Object type '{object_type_key}' not found")
    return definition


def get_application(model: EngineModel, application_key: str):
    application = next((item for item in model.applications if item.key == application_key), None)
    if not application:
        raise api_error(404, "unknown_application", f"Application '{application_key}' not found")
    return application


def validate_application_object_type(
    model: EngineModel, application_key: str, object_type_key: str
) -> None:
    application = get_application(model, application_key)
    if object_type_key not in application.objectTypeKeys:
        raise api_error(
            422,
            "invalid_object_type_for_application",
            f"Object type '{object_type_key}' is not available in application '{application_key}'",
        )


def load_object(session: Session, object_id: str, object_type_key: str | None = None) -> RdmObject:
    statement = select(RdmObject).where(RdmObject.id == object_id)
    if object_type_key:
        statement = statement.where(RdmObject.object_type_key == object_type_key)
    item = session.scalar(statement)
    if not item:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    return item


def claim_object_version(session: Session, item: RdmObject, expected_version: int) -> None:
    result = session.execute(
        update(RdmObject)
        .where(RdmObject.id == item.id, RdmObject.version == expected_version)
        .values(version=expected_version + 1, updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise api_error(409, "version_conflict", "Object version has changed")
    session.refresh(item)


def validate_parent(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    application_key: str,
    workspace_key: str,
    parent_object_id: str | None,
    moving_object_id: str | None = None,
) -> tuple[RdmObject | None, str | None]:
    object_type = get_object_type(model, object_type_key)
    root_creatable = object_type.features.get("rootCreatable", False)
    if parent_object_id is None:
        if not root_creatable:
            raise api_error(422, "parent_required", "This object type requires a parent")
        return None, None

    parent = load_object(session, parent_object_id)
    if parent.application_key != application_key or parent.workspace_key != workspace_key:
        raise api_error(
            422, "parent_wrong_scope", "Parent must be in the same application and workspace"
        )
    if moving_object_id and _would_create_parent_cycle(session, moving_object_id, parent.id):
        raise api_error(422, "parent_cycle", "Parent selection would create a cycle")

    permitted = set(object_type.behavior.get("parentRelationTypeKeys", []))
    matches = [
        relation
        for relation in model.objectTypeRelations
        if relation.relationTypeKey in permitted
        and relation.fromObjectTypeKey == parent.object_type_key
        and relation.toObjectTypeKey == object_type_key
    ]
    if len(matches) != 1:
        raise api_error(
            422, "invalid_parent_type", "Parent type is not permitted for this object type"
        )
    return parent, matches[0].relationTypeKey


def replace_parent_relation(
    session: Session,
    model: EngineModel,
    item: RdmObject,
    parent: RdmObject | None,
    parent_relation: str | None,
) -> None:
    parent_relation_types = set(
        get_object_type(model, item.object_type_key).behavior.get("parentRelationTypeKeys", [])
    )
    session.execute(
        delete(ObjectRelation).where(
            ObjectRelation.to_object_id == item.id,
            ObjectRelation.relation_type_key.in_(parent_relation_types),
        )
    )
    item.parent_object_id = parent.id if parent else None
    if parent and parent_relation:
        session.add(
            ObjectRelation(
                relation_type_key=parent_relation,
                from_object_id=parent.id,
                to_object_id=item.id,
            )
        )


def build_object_responses(
    session: Session, model: EngineModel, objects: list[RdmObject]
) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    paths = _object_paths(session, objects)
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            state=item.state,
            name=item.name,
            path=paths[item.id],
            attributes=_build_attribute_outputs(model, values[item.id]),
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _build_attribute_outputs(model, values: dict) -> list[AttributeOutput]:
    result = []
    for key, (value_id, value) in values.items():
        definition = model.attribute_type(key)
        result.append(
            AttributeOutput(
                id=value_id,
                attributeTypeKey=key,
                name=definition.name if definition else key,
                valueType=definition.valueType if definition else "text",
                value=value,
            )
        )
    return result


def _object_paths(session: Session, objects: list[RdmObject]) -> dict[str, list[dict[str, str]]]:
    # Resolve ancestor chains for a batch in level order so the number of queries is bounded by
    # hierarchy depth rather than by the object count (avoids an N+1 per-object traversal).
    paths = {
        item.id: [{"id": item.id, "name": item.name, "objectTypeKey": item.object_type_key}]
        for item in objects
    }
    visited = {item.id: {item.id} for item in objects}
    frontier = {item.id: item.parent_object_id for item in objects if item.parent_object_id}
    while frontier:
        parent_ids = {parent_id for parent_id in frontier.values() if parent_id}
        if not parent_ids:
            break
        parent_map = {
            row.id: row
            for row in session.scalars(select(RdmObject).where(RdmObject.id.in_(parent_ids)))
        }
        next_frontier: dict[str, str | None] = {}
        for object_id, parent_id in frontier.items():
            parent = parent_map.get(parent_id) if parent_id else None
            if parent is None or parent.id in visited[object_id]:
                continue
            visited[object_id].add(parent.id)
            paths[object_id].append(
                {"id": parent.id, "name": parent.name, "objectTypeKey": parent.object_type_key}
            )
            if parent.parent_object_id:
                next_frontier[object_id] = parent.parent_object_id
        frontier = next_frontier
    return {object_id: list(reversed(path)) for object_id, path in paths.items()}


def _would_create_parent_cycle(session: Session, object_id: str, parent_id: str) -> bool:
    current_id: str | None = parent_id
    visited: set[str] = set()
    while current_id:
        if current_id == object_id or current_id in visited:
            return True
        visited.add(current_id)
        current_id = session.scalar(
            select(RdmObject.parent_object_id).where(RdmObject.id == current_id)
        )
    return False
