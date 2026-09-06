
from fastapi import APIRouter, Query, Response, status
from sqlalchemy.orm import Session

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AttributeInput,
    AttributeValueResponse,
    AttributeValueWrite,
    ObjectDraftActivationRequest,
    ObjectDraftUpdate,
    ObjectResponse,
)
from ..models.schema import EngineModel
from ..services.attributes import (
    build_attribute_value_response,
    load_attribute_value,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from ..services.model.registry import ActiveModelSnapshot
from ..services.object_lifecycle import (
    activate_draft,
    clone_revision_to_draft,
    effective_model_release_id,
    load_active_object,
    update_draft,
)
from ..services.objects import (
    build_object_responses,
    get_object_type,
)
from ..services.workspaces import resolve_workspace

router = APIRouter(prefix="/api/v1", tags=["attributes"])

ATTRIBUTE_VALUE_PATH = "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"


def _write_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    model_release_db_id: int,
    *,
    require_absent: bool,
) -> ObjectResponse:
    """Shared write path for creating and replacing a single attribute value."""
    object_type = get_object_type(model, object_type_key)
    item = load_active_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    if item.version != payload.expectedVersion:
        raise api_error(409, "version_conflict", "Object version has changed")
    active_revision_id = item.active_revision_id or ""
    draft = clone_revision_to_draft(
        session,
        model,
        model_release_db_id=model_release_db_id,
        object_type_key=object_type_key,
        object_id=object_id,
        derived_from_revision_id=active_revision_id,
        commit=False,
    )
    if require_absent:
        if attribute_type_key in draft.attributes:
            raise api_error(
                409,
                "attribute_already_exists",
                f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'",
            )
    else:
        if attribute_type_key not in draft.attributes:
            raise api_error(
                404,
                "attribute_not_found",
                f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
            )
    attributes = dict(draft.attributes)
    attributes.update(
        validate_attributes(
            model, object_type, {attribute_type_key: payload.value}, partial=True
        )
    )
    draft = update_draft(
        session,
        model,
        draft.id,
        ObjectDraftUpdate(
            expectedVersion=draft.version,
            attributes=[
                AttributeInput(attributeTypeKey=key, value=value)
                for key, value in attributes.items()
            ],
        ),
        commit=False,
    )
    activate_draft(
        session,
        model,
        current_model_release_db_id=model_release_db_id,
        draft_id=draft.id,
        payload=ObjectDraftActivationRequest(
            expectedDraftVersion=draft.version,
            expectedActiveRevisionId=active_revision_id,
        ),
    )
    item = load_active_object(session, object_id, object_type_key)
    return build_object_responses(session, model, [item])[0]


@router.get(ATTRIBUTE_VALUE_PATH, response_model=AttributeValueResponse)
def get_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> AttributeValueResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    item = load_active_object(session, object_id, object_type_key)
    row = load_attribute_value(session, item.id, attribute_type_key)
    return build_attribute_value_response(model, row, item.version)


@router.post(
    ATTRIBUTE_VALUE_PATH,
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    return _write_attribute_value(
        session,
        snapshot.model,
        object_type_key,
        object_id,
        attribute_type_key,
        payload,
        effective_model_release_id(session, snapshot.release_db_id),
        require_absent=True,
    )


@router.patch(ATTRIBUTE_VALUE_PATH, response_model=ObjectResponse, include_in_schema=False)
def update_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    return _write_attribute_value(
        session,
        snapshot.model,
        object_type_key,
        object_id,
        attribute_type_key,
        payload,
        effective_model_release_id(session, snapshot.release_db_id),
        require_absent=False,
    )


@router.delete(ATTRIBUTE_VALUE_PATH, status_code=204, include_in_schema=False)
def delete_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
) -> Response:
    model = snapshot.model
    model_release_id = effective_model_release_id(session, snapshot.release_db_id)
    object_type = get_object_type(model, object_type_key)
    item = load_active_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    if item.version != expected_version:
        raise api_error(409, "version_conflict", "Object version has changed")
    active_revision_id = item.active_revision_id or ""
    draft = clone_revision_to_draft(
        session,
        model,
        model_release_db_id=model_release_id,
        object_type_key=object_type_key,
        object_id=object_id,
        derived_from_revision_id=active_revision_id,
        commit=False,
    )
    if attribute_type_key not in draft.attributes:
        raise api_error(
            404,
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    validate_deletable_attribute(object_type, attribute_type_key)
    remaining_attributes = dict(draft.attributes)
    remaining_attributes.pop(attribute_type_key, None)
    validate_object_attribute_rules(object_type, remaining_attributes)
    draft = update_draft(
        session,
        model,
        draft.id,
        ObjectDraftUpdate(
            expectedVersion=draft.version,
            attributes=[
                AttributeInput(attributeTypeKey=key, value=value)
                for key, value in remaining_attributes.items()
            ],
        ),
        commit=False,
    )
    activate_draft(
        session,
        model,
        current_model_release_db_id=model_release_id,
        draft_id=draft.id,
        payload=ObjectDraftActivationRequest(
            expectedDraftVersion=draft.version,
            expectedActiveRevisionId=active_revision_id,
        ),
    )
    return Response(status_code=204)
