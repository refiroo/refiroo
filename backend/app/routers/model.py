import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import and_, or_, select

from ..config import cursor_signing_key
from ..db import SessionLocal
from ..errors import api_error
from ..models.api import (
    AllowedObjectTypePair,
    ApplicationResponse,
    AttributeBindingResponse,
    AttributeTypeResponse,
    CapabilitiesResponse,
    MetadataPage,
    ModelAdminCapabilities,
    ModelChangeResponse,
    ModelCompatibilityResponse,
    ModelDiagnosticResponse,
    ModelDocumentRequest,
    ModelReleaseDiffResponse,
    ModelReleasePage,
    ModelReleaseResponse,
    ModelValidationResponse,
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
from ..services.model_compatibility import analyze_compatibility
from ..services.model_compiler import ModelDiagnostic, compile_model
from ..services.model_diff import semantic_diff
from ..services.model_registry import ActiveModelSnapshot, ModelSnapshot
from ..services.objects import get_application, get_object_type

router = APIRouter(prefix="/api/v1", tags=["model"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(request: Request) -> CapabilitiesResponse:
    mutations_enabled = bool(request.app.state.model_admin_mutations_enabled)
    return CapabilitiesResponse(
        modelAdmin=ModelAdminCapabilities(
            readReleases=True,
            manageDrafts=mutations_enabled,
            install=mutations_enabled,
            activate=mutations_enabled,
        )
    )


@router.get(
    "/model",
    responses={
        200: {
            "headers": {
                "ETag": {
                    "description": "Quoted SHA-256 entity tag of the active immutable model",
                    "schema": {"type": "string"},
                },
                "X-Model-Release-Id": {
                    "description": "Public UUID of the active installed release",
                    "schema": {"type": "string", "format": "uuid"},
                },
            }
        }
    },
)
def get_model(response: Response, snapshot: ActiveModelSnapshot) -> dict[str, Any]:
    response.headers["ETag"] = f'"{snapshot.model_hash}"'
    response.headers["X-Model-Release-Id"] = snapshot.release_id
    return snapshot.model.model_dump(mode="json")


@router.post(
    "/model-validations",
    response_model=ModelValidationResponse,
    response_model_exclude_none=True,
)
def validate_model(payload: ModelDocumentRequest) -> ModelValidationResponse:
    compiled = compile_model(payload.model)
    return ModelValidationResponse(
        valid=compiled.valid,
        diagnostics=[_diagnostic_response(item) for item in compiled.diagnostics],
    )


@router.get("/applications", response_model=MetadataPage[ApplicationResponse])
def get_applications(
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ApplicationResponse]:
    model = snapshot.model
    items, next_cursor = _paginate_metadata(
        model.applications,
        lambda item: (item.key,),
        cursor,
        page_size,
        scope="applications",
    )
    return MetadataPage(
        items=_build_application_responses(snapshot, items), nextCursor=next_cursor
    )


@router.get("/applications/{application_key}", response_model=ApplicationResponse)
def get_application_detail(
    application_key: str, snapshot: ActiveModelSnapshot
) -> ApplicationResponse:
    application = get_application(snapshot.model, application_key)
    return _build_application_responses(snapshot, [application])[0]


@router.get("/attribute-types", response_model=MetadataPage[AttributeTypeResponse])
def list_attribute_types(
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[AttributeTypeResponse]:
    model = snapshot.model
    items, next_cursor = _paginate_metadata(
        model.attributeTypes,
        lambda item: (item.key,),
        cursor,
        page_size,
        scope="attribute-types",
    )
    return MetadataPage(
        items=_build_attribute_type_responses(snapshot, items), nextCursor=next_cursor
    )


@router.get("/attribute-types/{attribute_type_key}", response_model=AttributeTypeResponse)
def get_attribute_type(
    attribute_type_key: str, snapshot: ActiveModelSnapshot
) -> AttributeTypeResponse:
    definition = snapshot.model.attribute_type(attribute_type_key)
    if not definition:
        raise api_error(
            404, "unknown_attribute_type", f"Attribute type '{attribute_type_key}' not found"
        )
    return _build_attribute_type_responses(snapshot, [definition])[0]


@router.get("/object-types", response_model=MetadataPage[ObjectTypeResponse])
def list_object_types(
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeResponse]:
    model = snapshot.model
    items, next_cursor = _paginate_metadata(
        model.objectTypes,
        lambda item: (item.key,),
        cursor,
        page_size,
        scope="object-types",
    )
    return MetadataPage(
        items=_build_object_type_responses(snapshot, items), nextCursor=next_cursor
    )


@router.get("/object-types/{object_type_key}", response_model=ObjectTypeResponse)
def get_object_type_detail(
    object_type_key: str, snapshot: ActiveModelSnapshot
) -> ObjectTypeResponse:
    object_type = get_object_type(snapshot.model, object_type_key)
    return _build_object_type_responses(snapshot, [object_type])[0]


@router.get("/relation-types", response_model=MetadataPage[RelationTypeResponse])
def list_relation_types(
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[RelationTypeResponse]:
    model = snapshot.model
    items, next_cursor = _paginate_metadata(
        model.relationTypes,
        lambda item: (item.key,),
        cursor,
        page_size,
        scope="relation-types",
    )
    return MetadataPage(
        items=_build_relation_type_responses(snapshot, items), nextCursor=next_cursor
    )


@router.get("/relation-types/{relation_type_key}", response_model=RelationTypeResponse)
def get_relation_type(
    relation_type_key: str, snapshot: ActiveModelSnapshot
) -> RelationTypeResponse:
    model = snapshot.model
    definition = model.relation_type(relation_type_key)
    if not definition:
        raise api_error(
            404, "unknown_relation_type", f"Relation type '{relation_type_key}' not found"
        )
    return _build_relation_type_responses(snapshot, [definition])[0]


@router.get("/object-type-relations", response_model=MetadataPage[ObjectTypeRelationResponse])
def get_object_type_relations(
    snapshot: ActiveModelSnapshot,
    from_object_type: str | None = Query(default=None, alias="fromObjectType"),
    to_object_type: str | None = Query(default=None, alias="toObjectType"),
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeRelationResponse]:
    relations = snapshot.model.objectTypeRelations
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
        scope="object-type-relations",
        sort=("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey"),
        filters={
            "fromObjectType": from_object_type,
            "toObjectType": to_object_type,
        },
    )
    return MetadataPage(
        items=_build_object_type_relation_responses(snapshot, items), nextCursor=next_cursor
    )


@router.get(
    "/model-releases",
    response_model=ModelReleasePage,
)
def list_model_releases(
    snapshot: ActiveModelSnapshot,
    release_key: str | None = Query(default=None, alias="releaseKey"),
    active: bool | None = None,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelReleasePage:
    cursor_context = {
        "releaseKey": release_key,
        "active": active,
        "activeReleaseId": snapshot.release_id,
    }
    cursor_sort = ("installedAt", "publicId")
    with SessionLocal() as session:
        statement = select(ModelRelease)
        if release_key is not None:
            statement = statement.where(ModelRelease.release_key == release_key)
        if active is True:
            statement = statement.where(ModelRelease.public_id == snapshot.release_id)
        elif active is False:
            statement = statement.where(ModelRelease.public_id != snapshot.release_id)
        if cursor is not None:
            cursor_identity = _decode_cursor(
                cursor,
                scope="model-releases",
                sort=cursor_sort,
                filters=cursor_context,
            )
            if len(cursor_identity) != 2:
                raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
            try:
                cursor_installed_at = datetime.fromisoformat(cursor_identity[0])
            except ValueError:
                raise api_error(422, "invalid_cursor", "Metadata cursor is invalid") from None
            statement = statement.where(
                or_(
                    ModelRelease.installed_at > cursor_installed_at,
                    and_(
                        ModelRelease.installed_at == cursor_installed_at,
                        ModelRelease.public_id > cursor_identity[1],
                    ),
                )
            )
        releases = list(
            session.scalars(
                statement.order_by(ModelRelease.installed_at, ModelRelease.public_id).limit(
                    page_size + 1
                )
            )
        )

    visible = releases[:page_size]
    next_cursor = (
        _encode_cursor(
            (_as_utc(visible[-1].installed_at).isoformat(), visible[-1].public_id),
            scope="model-releases",
            sort=cursor_sort,
            filters=cursor_context,
        )
        if len(releases) > page_size
        else None
    )
    return ModelReleasePage(
        items=[_build_model_release_response(item, snapshot.release_id) for item in visible],
        nextCursor=next_cursor,
    )


@router.get(
    "/model-releases/{release_id}",
    response_model=ModelReleaseResponse,
    response_model_exclude_none=True,
)
def get_model_release(
    release_id: str,
    snapshot: ActiveModelSnapshot,
    include_model: bool = Query(default=False, alias="includeModel"),
) -> ModelReleaseResponse:
    with SessionLocal() as session:
        release = session.scalar(
            select(ModelRelease).where(ModelRelease.public_id == release_id)
        )
        if release is None:
            raise api_error(404, "model_release_not_found", f"Model release '{release_id}' not found")
        return _build_model_release_response(
            release,
            snapshot.release_id,
            include_model=include_model,
        )


@router.get(
    "/model-releases/{release_id}/diff",
    response_model=ModelReleaseDiffResponse,
    response_model_exclude_unset=True,
)
def diff_model_release(
    release_id: str,
    snapshot: ActiveModelSnapshot,
    against_release_id: str = Query(alias="againstReleaseId"),
) -> ModelReleaseDiffResponse:
    with SessionLocal() as session:
        releases = {
            release.public_id: release
            for release in session.scalars(
                select(ModelRelease).where(
                    ModelRelease.public_id.in_([release_id, against_release_id])
                )
            )
        }
        candidate_release = releases.get(release_id)
        if candidate_release is None:
            raise api_error(
                404,
                "model_release_not_found",
                f"Model release '{release_id}' not found",
            )
        baseline_release = releases.get(against_release_id)
        if baseline_release is None:
            raise api_error(
                404,
                "model_release_not_found",
                f"Model release '{against_release_id}' not found",
            )

        candidate = compile_model(candidate_release.model_json)
        baseline = compile_model(baseline_release.model_json)
        invalid = candidate if not candidate.valid else baseline
        if not invalid.valid:
            raise api_error(
                500,
                "invalid_installed_model",
                "An installed model release failed validation",
                [
                    _diagnostic_response(item).model_dump(exclude_none=True)
                    for item in invalid.diagnostics
                ],
            )
        if (
            candidate.model is None
            or candidate.canonical_model is None
            or baseline.canonical_model is None
        ):
            raise api_error(500, "internal_error", "Compiled model result is incomplete")

        compatibility = analyze_compatibility(
            session,
            snapshot.model,
            candidate.model,
            snapshot.release_id,
        )
        changes = semantic_diff(baseline.canonical_model, candidate.canonical_model)

    return ModelReleaseDiffResponse(
        againstReleaseId=against_release_id,
        releaseId=release_id,
        changes=[_change_response(item) for item in changes],
        compatibility=ModelCompatibilityResponse(
            classification=compatibility.classification,
            activeReleaseId=compatibility.active_release_id,
            diagnostics=[
                _diagnostic_response(item) for item in compatibility.diagnostics
            ],
        ),
    )


def _build_model_release_response(
    release: ModelRelease,
    active_release_id: str,
    *,
    include_model: bool = False,
) -> ModelReleaseResponse:
    return ModelReleaseResponse(
        id=release.public_id,
        key=release.release_key,
        name=release.release_name,
        version=release.release_version,
        schemaVersion=release.schema_version,
        modelHash=release.model_hash,
        installedAt=_as_utc(release.installed_at),
        active=release.public_id == active_release_id,
        model=release.model_json if include_model else None,
    )


def _diagnostic_response(item: ModelDiagnostic) -> ModelDiagnosticResponse:
    values = {
        "severity": item.severity,
        "code": item.code,
        "path": item.path,
        "message": item.message,
    }
    if item.count is not None:
        values["count"] = item.count
    return ModelDiagnosticResponse(**values)


def _change_response(item) -> ModelChangeResponse:
    values = {
        "kind": item.kind,
        "path": item.path,
    }
    if item.kind != "added":
        values["before"] = item.before
    if item.kind != "removed":
        values["after"] = item.after
    return ModelChangeResponse(
        **values,
    )


def _paginate_metadata[MetadataItem](
    items: list[MetadataItem] | tuple[MetadataItem, ...],
    identity: Callable[[MetadataItem], tuple[str, ...]],
    cursor: str | None,
    page_size: int,
    *,
    scope: str,
    sort: tuple[str, ...] = ("key",),
    filters: dict[str, Any] | None = None,
) -> tuple[list[MetadataItem], str | None]:
    cursor_filters = filters or {}
    ordered = sorted(items, key=identity)
    if cursor is not None:
        cursor_identity = _decode_cursor(
            cursor,
            scope=scope,
            sort=sort,
            filters=cursor_filters,
        )
        expected_width = len(identity(ordered[0])) if ordered else len(cursor_identity)
        if len(cursor_identity) != expected_width:
            raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
        ordered = [item for item in ordered if identity(item) > cursor_identity]
    page = ordered[: page_size + 1]
    visible = page[:page_size]
    next_cursor = (
        _encode_cursor(
            identity(visible[-1]),
            scope=scope,
            sort=sort,
            filters=cursor_filters,
        )
        if len(page) > page_size
        else None
    )
    return visible, next_cursor


def _encode_cursor(
    identity: tuple[str, ...],
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "version": 1,
            "scope": scope,
            "sort": sort,
            "filters": _filter_fingerprint(filters),
            "position": identity,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    signature = hmac.digest(cursor_signing_key(), payload, "sha256")
    return f"{_base64_encode(payload)}.{_base64_encode(signature)}"


def _decode_cursor(
    cursor: str,
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
) -> tuple[str, ...]:
    try:
        encoded_payload, encoded_signature = cursor.split(".")
        payload = _base64_decode(encoded_payload)
        signature = _base64_decode(encoded_signature)
        expected_signature = hmac.digest(cursor_signing_key(), payload, "sha256")
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError
        decoded = json.loads(payload)
    except (ValueError, json.JSONDecodeError):
        raise api_error(422, "invalid_cursor", "Metadata cursor is invalid") from None
    if (
        not isinstance(decoded, dict)
        or decoded.get("version") != 1
        or decoded.get("scope") != scope
        or decoded.get("sort") != list(sort)
        or decoded.get("filters") != _filter_fingerprint(filters)
        or not isinstance(decoded.get("position"), list)
        or not decoded["position"]
        or not all(isinstance(item, str) for item in decoded["position"])
    ):
        raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
    return tuple(decoded["position"])


def _filter_fingerprint(filters: dict[str, Any]) -> str:
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _base64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    if _base64_encode(decoded) != value:
        raise ValueError
    return decoded


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_application_responses(
    snapshot: ModelSnapshot,
    applications: list,
) -> list[ApplicationResponse]:
    with SessionLocal() as session:
        app_meta = {
            row.key: row
            for row in session.scalars(
                select(ApplicationMeta).where(
                    ApplicationMeta.model_release_id == snapshot.release_db_id
                )
            )
        }
        ot_ids = {
            row.key: row.public_id
            for row in session.scalars(
                select(ObjectTypeMeta).where(
                    ObjectTypeMeta.model_release_id == snapshot.release_db_id
                )
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
    snapshot: ModelSnapshot,
    attribute_types: list,
) -> list[AttributeTypeResponse]:
    with SessionLocal() as session:
        meta_by_key = {
            row.key: row
            for row in session.scalars(
                select(AttributeTypeMeta).where(
                    AttributeTypeMeta.model_release_id == snapshot.release_db_id
                )
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
    snapshot: ModelSnapshot,
    object_types: list,
) -> list[ObjectTypeResponse]:
    model = snapshot.model
    with SessionLocal() as session:
        type_meta = {
            row.key: row
            for row in session.scalars(
                select(ObjectTypeMeta).where(
                    ObjectTypeMeta.model_release_id == snapshot.release_db_id
                )
            )
        }
        binding_meta = {}
        for row in session.scalars(
            select(ObjectTypeAttributeMeta).where(
                ObjectTypeAttributeMeta.model_release_id == snapshot.release_db_id
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
    snapshot: ModelSnapshot,
    relation_types: list,
) -> list[RelationTypeResponse]:
    model = snapshot.model
    with SessionLocal() as session:
        type_meta = {
            row.key: row
            for row in session.scalars(
                select(RelationTypeMeta).where(
                    RelationTypeMeta.model_release_id == snapshot.release_db_id
                )
            )
        }
        pair_meta: dict[str, list[tuple]] = {}
        for row in session.scalars(
            select(ObjectTypeRelationMeta).where(
                ObjectTypeRelationMeta.model_release_id == snapshot.release_db_id
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
    snapshot: ModelSnapshot,
    relations: list,
) -> list[ObjectTypeRelationResponse]:
    with SessionLocal() as session:
        meta = {
            (row.relation_type_key, row.from_object_type_key, row.to_object_type_key): row
            for row in session.scalars(
                select(ObjectTypeRelationMeta).where(
                    ObjectTypeRelationMeta.model_release_id == snapshot.release_db_id
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
