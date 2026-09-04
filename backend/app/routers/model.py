import base64
import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from ..db import SessionLocal
from ..errors import api_error
from ..models.api import (
    AllowedObjectTypePair,
    ApplicationResponse,
    AttributeBindingResponse,
    AttributeTypeResponse,
    MetadataPage,
    ObjectTypeRelationResponse,
    ObjectTypeResponse,
    RelationTypeResponse,
)
from ..models.database import (
    ApplicationMeta,
    AttributeTypeMeta,
    ModelRelease,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
)
from ..services.model_loader import current_model
from ..services.objects import get_application, get_object_type

router = APIRouter(prefix="/api/v1", tags=["model"])


@router.get("/model")
def get_model() -> dict[str, Any]:
    return current_model().model_dump(mode="json")


@router.get("/applications", response_model=MetadataPage[ApplicationResponse])
def get_applications(
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ApplicationResponse]:
    model = current_model()
    items, next_cursor = _paginate_metadata(
        model.applications, lambda item: (item.key,), cursor, page_size
    )
    return MetadataPage(items=_build_application_responses(items), nextCursor=next_cursor)


@router.get("/applications/{application_key}", response_model=ApplicationResponse)
def get_application_detail(application_key: str) -> ApplicationResponse:
    application = get_application(application_key)
    return _build_application_responses([application])[0]


@router.get("/attribute-types", response_model=MetadataPage[AttributeTypeResponse])
def list_attribute_types(
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[AttributeTypeResponse]:
    model = current_model()
    items, next_cursor = _paginate_metadata(
        model.attributeTypes, lambda item: (item.key,), cursor, page_size
    )
    return MetadataPage(items=_build_attribute_type_responses(items), nextCursor=next_cursor)


@router.get("/attribute-types/{attribute_type_key}", response_model=AttributeTypeResponse)
def get_attribute_type(attribute_type_key: str) -> AttributeTypeResponse:
    definition = current_model().attribute_type(attribute_type_key)
    if not definition:
        raise api_error(
            404, "unknown_attribute_type", f"Attribute type '{attribute_type_key}' not found"
        )
    return _build_attribute_type_responses([definition])[0]


@router.get("/object-types", response_model=MetadataPage[ObjectTypeResponse])
def list_object_types(
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeResponse]:
    model = current_model()
    items, next_cursor = _paginate_metadata(
        model.objectTypes, lambda item: (item.key,), cursor, page_size
    )
    return MetadataPage(items=_build_object_type_responses(model, items), nextCursor=next_cursor)


@router.get("/object-types/{object_type_key}", response_model=ObjectTypeResponse)
def get_object_type_detail(object_type_key: str) -> ObjectTypeResponse:
    model = current_model()
    object_type = get_object_type(object_type_key)
    return _build_object_type_responses(model, [object_type])[0]


@router.get("/relation-types", response_model=MetadataPage[RelationTypeResponse])
def list_relation_types(
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[RelationTypeResponse]:
    model = current_model()
    items, next_cursor = _paginate_metadata(
        model.relationTypes, lambda item: (item.key,), cursor, page_size
    )
    return MetadataPage(items=_build_relation_type_responses(model, items), nextCursor=next_cursor)


@router.get("/relation-types/{relation_type_key}", response_model=RelationTypeResponse)
def get_relation_type(relation_type_key: str) -> RelationTypeResponse:
    model = current_model()
    definition = model.relation_type(relation_type_key)
    if not definition:
        raise api_error(
            404, "unknown_relation_type", f"Relation type '{relation_type_key}' not found"
        )
    return _build_relation_type_responses(model, [definition])[0]


@router.get("/object-type-relations", response_model=MetadataPage[ObjectTypeRelationResponse])
def get_object_type_relations(
    from_object_type: str | None = Query(default=None, alias="fromObjectType"),
    to_object_type: str | None = Query(default=None, alias="toObjectType"),
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeRelationResponse]:
    relations = current_model().objectTypeRelations
    if from_object_type:
        relations = [item for item in relations if item.fromObjectTypeKey == from_object_type]
    if to_object_type:
        relations = [item for item in relations if item.toObjectTypeKey == to_object_type]
    items, next_cursor = _paginate_metadata(
        relations,
        lambda item: (
            item.relationTypeKey,
            item.fromObjectTypeKey,
            item.toObjectTypeKey,
        ),
        cursor,
        page_size,
    )
    return MetadataPage(items=_build_object_type_relation_responses(items), nextCursor=next_cursor)


def _paginate_metadata[MetadataItem](
    items: list[MetadataItem],
    identity: Callable[[MetadataItem], tuple[str, ...]],
    cursor: str | None,
    page_size: int,
) -> tuple[list[MetadataItem], str | None]:
    ordered = sorted(items, key=identity)
    if cursor is not None:
        cursor_identity = _decode_cursor(cursor)
        expected_width = len(identity(ordered[0])) if ordered else len(cursor_identity)
        if len(cursor_identity) != expected_width:
            raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
        ordered = [item for item in ordered if identity(item) > cursor_identity]
    page = ordered[: page_size + 1]
    visible = page[:page_size]
    next_cursor = _encode_cursor(identity(visible[-1])) if len(page) > page_size else None
    return visible, next_cursor


def _encode_cursor(identity: tuple[str, ...]) -> str:
    payload = json.dumps(identity, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, ...]:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(cursor + padding)
        identity = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        raise api_error(422, "invalid_cursor", "Metadata cursor is invalid") from None
    if (
        not isinstance(identity, list)
        or not identity
        or not all(isinstance(item, str) for item in identity)
    ):
        raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
    return tuple(identity)


def _build_application_responses(
    applications: list,
) -> list[ApplicationResponse]:
    with SessionLocal() as session:
        release = session.scalar(select(ModelRelease).where(ModelRelease.is_active == True))
        app_meta = {
            row.key: row
            for row in session.scalars(
                select(ApplicationMeta).where(ApplicationMeta.model_release_id == release.id)
            )
        }
        ot_ids = {
            row.key: row.public_id
            for row in session.scalars(
                select(ObjectTypeMeta).where(ObjectTypeMeta.model_release_id == release.id)
            )
        }

    results = []
    for app in applications:
        data = app.model_dump(mode="json")
        _inject_object_type_ids(data, ot_ids)
        results.append(
            ApplicationResponse(
                id=app_meta[app.key].public_id if app.key in app_meta else "",
                **data,
            )
        )
    return results


def _inject_object_type_ids(obj: Any, ot_ids: dict[str, str]) -> None:
    if isinstance(obj, dict):
        if "objectTypeKey" in obj:
            obj["objectTypeId"] = ot_ids.get(obj["objectTypeKey"], "")
        for v in obj.values():
            _inject_object_type_ids(v, ot_ids)
    elif isinstance(obj, list):
        for item in obj:
            _inject_object_type_ids(item, ot_ids)


def _build_attribute_type_responses(
    attribute_types: list,
) -> list[AttributeTypeResponse]:
    with SessionLocal() as session:
        release = session.scalar(select(ModelRelease).where(ModelRelease.is_active == True))
        meta_by_key = {
            row.key: row
            for row in session.scalars(
                select(AttributeTypeMeta).where(AttributeTypeMeta.model_release_id == release.id)
            )
        }

    return [
        AttributeTypeResponse(
            id=meta_by_key[at.key].public_id if at.key in meta_by_key else "",
            key=at.key,
            name=at.name,
            description=at.description,
            valueType=at.valueType,
            default=at.default,
            features=at.features,
            validation=at.validation,
            ui=at.ui,
        )
        for at in attribute_types
    ]


def _build_object_type_responses(
    model,
    object_types: list,
) -> list[ObjectTypeResponse]:
    with SessionLocal() as session:
        release = session.scalar(select(ModelRelease).where(ModelRelease.is_active == True))
        type_meta = {
            row.key: row
            for row in session.scalars(
                select(ObjectTypeMeta).where(ObjectTypeMeta.model_release_id == release.id)
            )
        }
        binding_meta = {}
        for row in session.scalars(
            select(ObjectTypeAttributeMeta).where(
                ObjectTypeAttributeMeta.model_release_id == release.id
            )
        ):
            binding_meta.setdefault(row.object_type_key, {})[row.attribute_type_key] = row

    results = []
    for ot in object_types:
        meta = type_meta.get(ot.key)
        ot_bindings = binding_meta.get(ot.key, {})
        attribute_responses = []
        for binding in ot.attributes:
            attr_type = model.attribute_type(binding.attributeTypeKey)
            b_meta = ot_bindings.get(binding.attributeTypeKey)
            attribute_responses.append(
                AttributeBindingResponse(
                    id=b_meta.public_id if b_meta else "",
                    attributeTypeKey=binding.attributeTypeKey,
                    name=attr_type.name if attr_type else binding.attributeTypeKey,
                    valueType=attr_type.valueType if attr_type else "text",
                    required=binding.required,
                    readOnly=binding.readOnly,
                    order=binding.order,
                )
            )
        results.append(
            ObjectTypeResponse(
                id=meta.public_id if meta else "",
                key=ot.key,
                name=ot.name,
                pluralName=ot.pluralName,
                description=ot.description,
                icon=ot.icon,
                displayAttributeTypeKey=ot.displayAttributeTypeKey,
                attributes=attribute_responses,
                features=ot.features,
                behavior=ot.behavior,
                validation=ot.validation,
            )
        )
    return results


def _build_relation_type_responses(
    model,
    relation_types: list,
) -> list[RelationTypeResponse]:
    with SessionLocal() as session:
        release = session.scalar(select(ModelRelease).where(ModelRelease.is_active == True))
        type_meta = {
            row.key: row
            for row in session.scalars(
                select(RelationTypeMeta).where(RelationTypeMeta.model_release_id == release.id)
            )
        }
        pair_meta: dict[str, list[tuple]] = {}
        for row in session.scalars(
            select(ObjectTypeRelationMeta).where(
                ObjectTypeRelationMeta.model_release_id == release.id
            )
        ):
            pair_meta.setdefault(row.relation_type_key, []).append(row)

    relation_keys = {rt.key for rt in relation_types}
    allowed_by_key: dict[str, list] = {key: [] for key in relation_keys}
    for otr in model.objectTypeRelations:
        if otr.relationTypeKey in relation_keys:
            allowed_by_key[otr.relationTypeKey].append(otr)

    results = []
    for rt in relation_types:
        meta = type_meta.get(rt.key)
        db_pairs = {
            (r.from_object_type_key, r.to_object_type_key): r for r in pair_meta.get(rt.key, [])
        }
        pairs = []
        for otr in allowed_by_key.get(rt.key, []):
            p_meta = db_pairs.get((otr.fromObjectTypeKey, otr.toObjectTypeKey))
            pairs.append(
                AllowedObjectTypePair(
                    id=p_meta.public_id if p_meta else "",
                    fromObjectTypeKey=otr.fromObjectTypeKey,
                    toObjectTypeKey=otr.toObjectTypeKey,
                    cardinality=otr.cardinality,
                    required=otr.required,
                    attributeTypeKeys=otr.attributeTypeKeys,
                    features=otr.features,
                )
            )
        results.append(
            RelationTypeResponse(
                id=meta.public_id if meta else "",
                key=rt.key,
                name=rt.name,
                reverseKey=rt.reverseKey,
                reverseName=rt.reverseName,
                isOriented=rt.isOriented,
                features=rt.features,
                allowedPairs=pairs,
            )
        )
    return results


def _build_object_type_relation_responses(
    relations: list,
) -> list[ObjectTypeRelationResponse]:
    with SessionLocal() as session:
        release = session.scalar(select(ModelRelease).where(ModelRelease.is_active == True))
        meta = {
            (row.relation_type_key, row.from_object_type_key, row.to_object_type_key): row
            for row in session.scalars(
                select(ObjectTypeRelationMeta).where(
                    ObjectTypeRelationMeta.model_release_id == release.id
                )
            )
        }

    return [
        ObjectTypeRelationResponse(
            id=meta[(item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey)].public_id,
            relationTypeKey=item.relationTypeKey,
            fromObjectTypeKey=item.fromObjectTypeKey,
            toObjectTypeKey=item.toObjectTypeKey,
            cardinality=item.cardinality,
            required=item.required,
            attributeTypeKeys=item.attributeTypeKeys,
            features=item.features,
        )
        for item in relations
    ]
