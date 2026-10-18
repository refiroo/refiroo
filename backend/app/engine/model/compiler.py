"""Validate and canonicalize a model document without touching persistence."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ...common.json_pointer import pointer_segment
from ...models.schema import EngineModel
from .consumer_definitions import compiled_consumer_apis
from .consumer_legacy import LegacyEngineModel, is_legacy, legacy_consumer_apis_refusal
from .diagnostics import ModelDiagnostic, ModelReferenceError, ModelValidationError
from .validation import validate_references

# Oldest first: versions compare as numbers, so a text sort would put 0.10 before 0.5.
SCHEMA_VERSIONS: tuple[str, ...] = ("0.5", "0.6", "0.7", "0.8", "0.9", "0.10")
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset(SCHEMA_VERSIONS)

__all__ = [
    "SCHEMA_VERSIONS",
    "SUPPORTED_SCHEMA_VERSIONS",
    "CompilationResult",
    "ModelDiagnostic",
    "ModelValidationError",
    "after_window",
    "canonical_model",
    "compile_authored_model",
    "compile_model",
    "parse_model",
]


def after_window(version: str) -> bool:
    """Whether ``version`` is newer than every version in the window: a model written for a later
    engine (0.11 V4, D101), not one an older engine left behind."""
    try:
        parts = tuple(int(part) for part in version.split("."))
    except ValueError:
        return False
    return parts > tuple(int(part) for part in SCHEMA_VERSIONS[-1].split("."))


@dataclass(frozen=True)
class CompilationResult:
    valid: bool
    model: EngineModel | None
    canonical_model: dict[str, Any] | None
    model_hash: str | None
    diagnostics: tuple[ModelDiagnostic, ...]
    unsupported_schema_version: str | None = None


def compile_model(source: Any) -> CompilationResult:
    """Validate shape, then expand consumer API definitions, then references, then canonicalize.

    A document of schema 0.8 or earlier is read with its own consumer API shape (C18). It compiles
    as stored: refusing a new one is the authoring routes' check (``legacy_consumer_apis_refusal``).
    """
    if isinstance(source, dict) and source.get("schemaVersion") not in {None, *SUPPORTED_SCHEMA_VERSIONS}:
        supplied = source.get("schemaVersion")
        return _invalid(
            (
                ModelDiagnostic(
                    severity="error",
                    code="UNSUPPORTED_SCHEMA_VERSION",
                    path="/schemaVersion",
                    message=f"Schema version '{supplied}' is unsupported; supported versions: {list(SCHEMA_VERSIONS)}",
                ),
            ),
            unsupported_schema_version=str(supplied),
        )
    try:
        model = (LegacyEngineModel if is_legacy(source) else EngineModel).model_validate(source)
    except ValidationError as exc:
        return _invalid(tuple(_shape_diagnostic(error, source) for error in exc.errors()))
    try:
        compiled_consumer_apis(model)
    except ModelReferenceError as exc:
        return _invalid((exc.as_diagnostic(),))

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


def compile_authored_model(source: Any) -> CompilationResult:
    """:func:`compile_model` for a document an author submits (install, draft compile, validation):
    schema 0.8 consumer API definitions are no longer written (C18, C-D134)."""
    refusal = legacy_consumer_apis_refusal(source)
    if refusal is not None:
        return _invalid((refusal,))
    return compile_model(source)


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


def _shape_diagnostic(error: dict[str, Any], source: Any) -> ModelDiagnostic:
    """Render one Pydantic shape error, whose ``loc`` points at the failing node of ``source``."""
    message = str(error.get("msg", "Model validation failed"))
    error_type = str(error.get("type", ""))
    code = _shape_code(error_type)
    location = error.get("loc", ())
    path = (
        "".join(f"/{pointer_segment(item)}" for item in document_location(location, source))
        if isinstance(location, (list, tuple))
        else ""
    )
    return ModelDiagnostic(severity="error", code=code, path=path, message=message)


def document_location(location: Sequence[Any], source: Any) -> list[Any]:
    """``location`` without the tags Pydantic inserts for a tagged union (``…/zone/ancestor/…`` for a
    parameter of kind ``ancestor``): a segment before the last that is no key of its object but one
    of its values names the union member, not a node of the document (0.9 C15); so does one before
    a key of its object, or a name inside a list (a consumer API field's form, C18)."""
    node, kept = source, []
    for position, item in enumerate(location):
        inner = position < len(location) - 1
        if isinstance(node, dict):
            if item not in node and inner and (item in node.values() or location[position + 1] in node):
                continue
            node = node.get(item)
        elif isinstance(node, list) and isinstance(item, str) and inner:
            continue
        elif isinstance(node, list) and isinstance(item, int) and 0 <= item < len(node):
            node = node[item]
        else:
            node = None
        kept.append(item)
    return kept


def _shape_code(error_type: str) -> str:
    if error_type == "missing":
        return "missing_field"
    if error_type == "extra_forbidden":
        return "unknown_field"
    return "INVALID_MODEL"
