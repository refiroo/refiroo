from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..services.model_loader import current_model
from ..services.objects import get_application, get_object_type

router = APIRouter(prefix="/api/v1", tags=["model"])


@router.get("/model")
def get_model() -> dict[str, Any]:
    return current_model().model_dump(mode="json")


@router.get("/applications")
def get_applications() -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in current_model().applications]


@router.get("/applications/{application_key}")
def get_application_detail(application_key: str) -> dict[str, Any]:
    application = get_application(application_key)
    return application.model_dump(mode="json")


@router.get("/attribute-types/{attribute_type_key}")
def get_attribute_type(attribute_type_key: str) -> dict[str, Any]:
    definition = current_model().attribute_type(attribute_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown attribute type")
    return definition.model_dump(mode="json")


@router.get("/object-types/{object_type_key}")
def get_object_type_detail(object_type_key: str) -> dict[str, Any]:
    return get_object_type(object_type_key).model_dump(mode="json")


@router.get("/relation-types/{relation_type_key}")
def get_relation_type(relation_type_key: str) -> dict[str, Any]:
    definition = current_model().relation_type(relation_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown relation type")
    return definition.model_dump(mode="json")


@router.get("/object-type-relations")
def get_object_type_relations(
    from_object_type: str | None = Query(default=None, alias="fromObjectType"),
    to_object_type: str | None = Query(default=None, alias="toObjectType"),
) -> list[dict[str, Any]]:
    relations = current_model().objectTypeRelations
    if from_object_type:
        relations = [item for item in relations if item.fromObjectTypeKey == from_object_type]
    if to_object_type:
        relations = [item for item in relations if item.toObjectTypeKey == to_object_type]
    return [item.model_dump(mode="json") for item in relations]
