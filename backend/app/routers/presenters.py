"""Shared renderers from service dataclasses to API response models.

These live beside the routers rather than inside one of them so no router has to import another
router's internals.
"""

from typing import Any

from ..models.api import AttributeOutput, ModelChangeResponse, ModelDiagnosticResponse
from ..models.schema import EngineModel
from ..services.model.compiler import ModelDiagnostic
from ..services.model.diff import SemanticChange


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
