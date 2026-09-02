
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models.api import ObjectResponse
from ..models.database import ObjectRelation, RdmObject
from ..models.schema import ObjectTypeDefinition
from .attributes import load_attribute_values
from .model_loader import current_model


def get_object_type(object_type_key: str) -> ObjectTypeDefinition:
    definition = current_model().object_type(object_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown object type")
    return definition


def get_application(application_key: str):
    application = next(
        (item for item in current_model().applications if item.key == application_key), None
    )
    if not application:
        raise HTTPException(status_code=404, detail="Unknown application")
    return application


def validate_application_object_type(application_key: str, object_type_key: str) -> None:
    application = get_application(application_key)
    if object_type_key not in application.objectTypeKeys:
        raise HTTPException(
            status_code=422,
            detail=f"Object type '{object_type_key}' is not available in '{application_key}'",
        )


def load_object(session: Session, object_id: str, object_type_key: str | None = None) -> RdmObject:
    statement = select(RdmObject).where(RdmObject.id == object_id)
    if object_type_key:
        statement = statement.where(RdmObject.object_type_key == object_type_key)
    item = session.scalar(statement)
    if not item:
        raise HTTPException(status_code=404, detail="Object not found")
    return item


def validate_parent(
    session: Session,
    object_type_key: str,
    application_key: str,
    workspace_key: str,
    parent_object_id: str | None,
    moving_object_id: str | None = None,
) -> tuple[RdmObject | None, str | None]:
    object_type = get_object_type(object_type_key)
    root_creatable = object_type.features.get("rootCreatable", False)
    if parent_object_id is None:
        if not root_creatable:
            raise HTTPException(status_code=422, detail="This object type requires a parent")
        return None, None

    parent = load_object(session, parent_object_id)
    if parent.application_key != application_key or parent.workspace_key != workspace_key:
        raise HTTPException(
            status_code=422, detail="Parent must be in the same application and workspace"
        )
    if moving_object_id and _would_create_parent_cycle(session, moving_object_id, parent.id):
        raise HTTPException(status_code=422, detail="Parent selection would create a cycle")

    model = current_model()
    permitted = set(object_type.behavior.get("parentRelationTypeKeys", []))
    matches = [
        relation
        for relation in model.objectTypeRelations
        if relation.relationTypeKey in permitted
        and relation.fromObjectTypeKey == parent.object_type_key
        and relation.toObjectTypeKey == object_type_key
    ]
    if len(matches) != 1:
        raise HTTPException(
            status_code=422, detail="Parent type is not permitted for this object type"
        )
    return parent, matches[0].relationTypeKey


def replace_parent_relation(
    session: Session,
    item: RdmObject,
    parent: RdmObject | None,
    parent_relation: str | None,
) -> None:
    parent_relation_types = set(
        get_object_type(item.object_type_key).behavior.get("parentRelationTypeKeys", [])
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


def build_object_responses(session: Session, objects: list[RdmObject]) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            state=item.state,
            name=item.name,
            path=_object_path(session, item),
            attributes=values[item.id],
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _object_path(session: Session, item: RdmObject) -> list[dict[str, str]]:
    path = [{"id": item.id, "name": item.name, "objectTypeKey": item.object_type_key}]
    parent_id = item.parent_object_id
    visited = {item.id}
    while parent_id:
        if parent_id in visited:
            break
        visited.add(parent_id)
        parent = session.scalar(select(RdmObject).where(RdmObject.id == parent_id))
        if not parent:
            break
        path.append({"id": parent.id, "name": parent.name, "objectTypeKey": parent.object_type_key})
        parent_id = parent.parent_object_id
    return list(reversed(path))


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
