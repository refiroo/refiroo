"""Shared renderers from service dataclasses to API response models.

These live beside the routers rather than inside one of them so no router has to import another
router's internals.
"""

from typing import Any

from sqlalchemy.orm import Session

from ..common.pagination import Page
from ..common.time import as_utc
from ..engine.model.compiler import ModelDiagnostic
from ..engine.model.consumer_contract import contract_diagnostics
from ..engine.model.diff import SemanticChange
from ..engine.reads.object_query import live_object_paths
from ..engine.records.attributes import load_attribute_values
from ..engine.records.values import row_value
from ..engine.workspaces.catalogue import delete_blocker, load_workspace_runtime_state
from ..models.database import (
    AttributeValue,
    AuditEvent,
    ObjectRelation,
    RdmObject,
    Workspace,
    WorkspaceRuntimeState,
)
from ..models.schema import EngineModel
from .schemas.model import (
    ModelChangeResponse,
    ModelConsumerContractsResponse,
    ModelDiagnosticResponse,
)
from .schemas.records import (
    AttributeOutput,
    AttributeValueResponse,
    AuditEventPage,
    AuditEventResponse,
    ObjectResponse,
    RelationResponse,
)
from .schemas.workspaces import (
    WorkspaceDetailResponse,
    WorkspaceResponse,
    WorkspaceRuntimeStateResponse,
)


def snapshot_attributes(
    model: EngineModel, object_id: str, attributes: dict[str, Any] | None
) -> list[AttributeOutput]:
    """A change set or publication row's JSON values in the object read's attribute shape."""
    outputs = []
    for key, value in (attributes or {}).items():
        definition = model.attribute_type(key)
        outputs.append(
            AttributeOutput(
                id=f"{object_id}:{key}",
                attributeTypeKey=key,
                name=definition.name if definition else key,
                valueType=definition.valueType if definition else "text",
                value=value,
            )
        )
    return outputs


def diagnostic_response(item: ModelDiagnostic) -> ModelDiagnosticResponse:
    values: dict[str, Any] = {
        "severity": item.severity,
        "code": item.code,
        "path": item.path,
        "message": item.message,
    }
    if item.count is not None:
        values["count"] = item.count
    return ModelDiagnosticResponse(**values)


def consumer_contracts_response(
    active: EngineModel, candidate: EngineModel, active_release_id: str
) -> ModelConsumerContractsResponse:
    """The candidate's consumer API definitions checked against the active release's (C-D17)."""
    diagnostics = contract_diagnostics(active, candidate)
    breaking = any(item.severity == "error" for item in diagnostics)
    return ModelConsumerContractsResponse(
        classification="version_required" if breaking else "compatible",
        activeReleaseId=active_release_id,
        diagnostics=[diagnostic_response(item) for item in diagnostics],
    )


def diagnostic_details(diagnostics: Any) -> list[dict[str, Any]]:
    """Render diagnostics for the ``details`` payload of a structured API error."""
    return [diagnostic_response(item).model_dump(exclude_none=True) for item in diagnostics]


def change_response(item: SemanticChange) -> ModelChangeResponse:
    values: dict[str, Any] = {"kind": item.kind, "path": item.path}
    if item.kind != "added":
        values["before"] = item.before
    if item.kind != "removed":
        values["after"] = item.after
    return ModelChangeResponse(**values)


def build_attribute_value_response(
    model: EngineModel, row: AttributeValue, object_version: int
) -> AttributeValueResponse:
    key = row.attribute_type_key
    definition = model.attribute_type(key)
    return AttributeValueResponse(
        id=row.id,
        attributeTypeKey=key,
        name=definition.name if definition else key,
        valueType=definition.valueType if definition else "text",
        value=row_value(row),
        objectVersion=object_version,
    )


def build_object_responses(
    session: Session, model: EngineModel, objects: list[RdmObject]
) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    paths = live_object_paths(session, objects)
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            name=item.name,
            path=paths[item.id],
            attributes=_build_attribute_outputs(model, values[item.id]),
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _build_attribute_outputs(model: EngineModel, values: dict) -> list[AttributeOutput]:
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


def build_relation_response(relation: ObjectRelation) -> RelationResponse:
    return RelationResponse(
        id=relation.id,
        relationTypeKey=relation.relation_type_key,
        fromObjectId=relation.from_object_id,
        toObjectId=relation.to_object_id,
        attributes=relation.attributes,
        version=relation.version,
        createdAt=relation.created_at,
        updatedAt=relation.updated_at,
    )


def workspace_response(item: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        key=item.key,
        label=item.label,
        status=item.status,
        version=item.version,
        createdAt=as_utc(item.created_at),
        updatedAt=as_utc(item.updated_at),
    )


def workspace_detail_response(session: Session, item: Workspace) -> WorkspaceDetailResponse:
    blocker, _ = delete_blocker(
        session, item.key, load_workspace_runtime_state(session).default_workspace_key
    )
    return WorkspaceDetailResponse(
        **workspace_response(item).model_dump(), deletable=blocker is None, deleteBlockedBy=blocker
    )


def runtime_state_response(item: WorkspaceRuntimeState) -> WorkspaceRuntimeStateResponse:
    return WorkspaceRuntimeStateResponse(
        defaultWorkspaceKey=item.default_workspace_key,
        version=item.version,
        updatedAt=as_utc(item.updated_at),
    )


def _audit_response(event: AuditEvent) -> AuditEventResponse:
    changes = event.changes if isinstance(event.changes, dict) else {}
    attributes = changes.get("attributes")
    if event.action == "reclassified":
        # A type change (ADR-034) stores its full before state; the history names what changed
        # and the attribute types it moved, mapped, restored or left without a place, not values.
        changed_fields = [str(key) for key in changes.get("changedFields", [])]
        attribute_type_keys = sorted(str(key) for key in changes.get("attributeTypeKeys", []))
    else:
        changed_fields = sorted(str(key) for key in changes)
        attribute_type_keys = _attribute_type_keys(event, attributes)
    return AuditEventResponse(
        id=event.event_id,
        aggregateType=event.aggregate_type,
        aggregateId=event.aggregate_id,
        action=event.action,
        version=event.version,
        changedFields=changed_fields,
        attributeTypeKeys=attribute_type_keys,
        occurredAt=event.occurred_at,
    )


def _attribute_type_keys(event: AuditEvent, attributes: Any) -> list[str]:
    if not isinstance(attributes, dict):
        return []
    if event.aggregate_type == "relation" and event.action == "updated":
        return sorted(
            {
                str(key)
                for position in ("from", "to")
                for key in (
                    attributes.get(position)
                    if isinstance(attributes.get(position), dict)
                    else {}
                )
            }
        )
    return sorted(str(key) for key in attributes)


def audit_event_page(events: Page[AuditEvent]) -> AuditEventPage:
    return AuditEventPage(items=[_audit_response(event) for event in events.items], **events.links())


def change_set_object_response(item, change_set_id: str, model, *, path=None) -> ObjectResponse:
    attrs = snapshot_attributes(model, item.object_id, item.attributes)
    return ObjectResponse(
        id=item.object_id,
        workspaceKey=(getattr(item, "workspace_key", None) or ""),
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        parentObjectId=item.parent_object_id,
        name=item.name,
        path=path or [],
        attributes=attrs,
        version=item.version,
        # Not recorded for change set and history rows (WP-10K); never substitute the current time.
        createdAt=None,
        updatedAt=None,
    )
