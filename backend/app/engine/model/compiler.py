"""Validate and canonicalize a model document without touching persistence."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ...common.json_pointer import pointer_segment
from ...models.schema import EngineModel
from .diagnostics import ModelDiagnostic, ModelValidationError
from .validation import validate_references

SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"0.5", "0.6", "0.7"})

__all__ = [
    "SUPPORTED_SCHEMA_VERSIONS",
    "CompilationResult",
    "ModelDiagnostic",
    "ModelValidationError",
    "canonical_model",
    "compile_model",
    "parse_model",
]


@dataclass(frozen=True)
class CompilationResult:
    valid: bool
    model: EngineModel | None
    canonical_model: dict[str, Any] | None
    model_hash: str | None
    diagnostics: tuple[ModelDiagnostic, ...]
    unsupported_schema_version: str | None = None


def compile_model(source: Any) -> CompilationResult:
    """Validate shape, then references, then canonicalize."""
    if isinstance(source, dict) and source.get("schemaVersion") not in {None, *SUPPORTED_SCHEMA_VERSIONS}:
        supplied = source.get("schemaVersion")
        return _invalid(
            (
                ModelDiagnostic(
                    severity="error",
                    code="unsupported_schema_version",
                    path="/schemaVersion",
                    message=f"Schema version '{supplied}' is unsupported; supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
                ),
            ),
            unsupported_schema_version=str(supplied),
        )
    try:
        model = EngineModel.model_validate(source)
    except ValidationError as exc:
        return _invalid(tuple(_shape_diagnostic(error) for error in exc.errors()))

    reference_diagnostics = validate_references(model)
    if reference_diagnostics:
        return _invalid(reference_diagnostics)

    model_json, model_hash = canonical_model(model)
    return CompilationResult(
        valid=True,
        model=model,
        canonical_model=model_json,
        model_hash=model_hash,
        diagnostics=(),
    )


def parse_model(source: Any) -> EngineModel:
    """Parse a model that must be valid, raising :class:`ModelValidationError` when it is not.

    Runtime code may only ever hold a model whose references resolve, so every path that turns a
    stored or supplied document into an :class:`EngineModel` goes through here or through
    :func:`compile_model`.
    """
    compiled = compile_model(source)
    if not compiled.valid or compiled.model is None:
        raise ModelValidationError(compiled.diagnostics)
    return compiled.model


def canonical_model(model: EngineModel) -> tuple[dict[str, Any], str]:
    model_json = model.model_dump(mode="json")
    canonical = json.dumps(model_json, sort_keys=True, separators=(",", ":"))
    return model_json, hashlib.sha256(canonical.encode()).hexdigest()


def _invalid(
    diagnostics: tuple[ModelDiagnostic, ...],
    *,
    unsupported_schema_version: str | None = None,
) -> CompilationResult:
    return CompilationResult(
        valid=False,
        model=None,
        canonical_model=None,
        model_hash=None,
        diagnostics=diagnostics,
        unsupported_schema_version=unsupported_schema_version,
    )


def _shape_diagnostic(error: dict[str, Any]) -> ModelDiagnostic:
    """Render one Pydantic shape error, whose ``loc`` already points at the failing node."""
    message = str(error.get("msg", "Model validation failed"))
    error_type = str(error.get("type", ""))
    code = _shape_code(error_type)
    location = error.get("loc", ())
    path = (
        "".join(f"/{pointer_segment(item)}" for item in location)
        if isinstance(location, (list, tuple))
        else ""
    )
    return ModelDiagnostic(severity="error", code=code, path=path, message=message)


def _shape_code(error_type: str) -> str:
    if error_type == "missing":
        return "missing_field"
    if error_type == "extra_forbidden":
        return "unknown_field"
    return "invalid_model"
