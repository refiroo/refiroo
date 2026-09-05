"""Shared renderers from service dataclasses to API response models.

These live beside the routers rather than inside one of them so no router has to import another
router's internals.
"""

from typing import Any

from ..models.api import ModelChangeResponse, ModelDiagnosticResponse
from ..services.model.compiler import ModelDiagnostic
from ..services.model.diff import SemanticChange


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
