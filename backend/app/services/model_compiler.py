import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from ..models.schema import EngineModel


@dataclass(frozen=True)
class ModelDiagnostic:
    severity: Literal["error", "warning"]
    code: str
    path: str
    message: str
    count: int | None = None


@dataclass(frozen=True)
class CompilationResult:
    valid: bool
    model: EngineModel | None
    canonical_model: dict[str, Any] | None
    model_hash: str | None
    diagnostics: tuple[ModelDiagnostic, ...]


def compile_model(source: Any) -> CompilationResult:
    """Validate and canonicalize a model without reading or writing persistence."""
    try:
        model = EngineModel.model_validate(source)
    except ValidationError as exc:
        return CompilationResult(
            valid=False,
            model=None,
            canonical_model=None,
            model_hash=None,
            diagnostics=tuple(_validation_diagnostic(source, error) for error in exc.errors()),
        )

    model_json, model_hash = canonical_model(model)
    return CompilationResult(
        valid=True,
        model=model,
        canonical_model=model_json,
        model_hash=model_hash,
        diagnostics=(),
    )


def canonical_model(model: EngineModel) -> tuple[dict[str, Any], str]:
    model_json = model.model_dump(mode="json")
    canonical = json.dumps(model_json, sort_keys=True, separators=(",", ":"))
    return model_json, hashlib.sha256(canonical.encode()).hexdigest()


def _validation_diagnostic(source: Any, error: dict[str, Any]) -> ModelDiagnostic:
    message = str(error.get("msg", "Model validation failed"))
    message = message.removeprefix("Value error, ")
    error_type = str(error.get("type", ""))
    code = _diagnostic_code(message, error_type)
    path = _diagnostic_path(source, error.get("loc", ()), message)
    return ModelDiagnostic(severity="error", code=code, path=path, message=message)


def _diagnostic_code(message: str, error_type: str) -> str:
    lowered = message.lower()
    if error_type == "missing":
        return "missing_field"
    if error_type == "extra_forbidden":
        return "unknown_field"
    if "duplicate" in lowered:
        return "duplicate_key"
    if "unknown object type" in lowered or "unknown source" in lowered or "unknown target" in lowered:
        return "unknown_object_type"
    if "unknown attribute" in lowered or "unbound attribute" in lowered:
        return "unknown_attribute_type"
    if "unknown relation type" in lowered:
        return "unknown_relation_type"
    if "references unknown" in lowered or "incompatible" in lowered:
        return "invalid_reference"
    return "invalid_model"


def _diagnostic_path(source: Any, loc: Any, message: str) -> str:
    inferred = _inferred_reference_path(source, message)
    if inferred is not None:
        return inferred
    if not isinstance(loc, (list, tuple)):
        return ""
    return "".join(f"/{_pointer_segment(item)}" for item in loc)


def _inferred_reference_path(source: Any, message: str) -> str | None:
    if not isinstance(source, dict):
        return None

    match = re.search(
        r"Duplicate (attribute type|object type|relation type|application) key '([^']+)'",
        message,
    )
    if match:
        collection = {
            "attribute type": "attributeTypes",
            "object type": "objectTypes",
            "relation type": "relationTypes",
            "application": "applications",
        }[match.group(1)]
        return f"/{collection}/{_pointer_segment(match.group(2))}"

    match = re.search(r"Duplicate view in ([^ ]+) key '([^']+)'", message)
    if match:
        return (
            f"/applications/{_pointer_segment(match.group(1))}/views/"
            f"{_pointer_segment(match.group(2))}"
        )

    match = re.search(r"Duplicate attribute binding '([^']+)' in '([^']+)'", message)
    if match:
        return (
            f"/objectTypes/{_pointer_segment(match.group(2))}/attributes/"
            f"{_pointer_segment(match.group(1))}"
        )

    match = re.search(r"Attribute type '([^']+)' declares 'unique'", message)
    if match:
        return f"/attributeTypes/{_pointer_segment(match.group(1))}/features/unique"

    match = re.search(r"Attribute type '([^']+)' validation\.(minimum|maximum)", message)
    if match:
        return (
            f"/attributeTypes/{_pointer_segment(match.group(1))}/validation/"
            f"{match.group(2)}"
        )

    match = re.search(
        r"Attribute type '([^']+)' declares 'validation\.(minimum|maximum)'", message
    )
    if match:
        return (
            f"/attributeTypes/{_pointer_segment(match.group(1))}/validation/"
            f"{match.group(2)}"
        )

    match = re.search(r"Duplicate relation or reverse key '([^']+)'", message)
    if match:
        duplicate_key = match.group(1)
        relations = source.get("relationTypes", [])
        matches = [
            item
            for item in relations
            if isinstance(item, dict)
            and duplicate_key in {item.get("key"), item.get("reverseKey")}
        ]
        if matches:
            item = matches[-1]
            field = "key" if item.get("key") == duplicate_key else "reverseKey"
            return (
                f"/relationTypes/{_pointer_segment(item.get('key', duplicate_key))}/"
                f"{field}"
            )

    if message.startswith("Duplicate object-type relation "):
        seen_relations: set[tuple[Any, Any, Any]] = set()
        for item in source.get("objectTypeRelations", []):
            if not isinstance(item, dict):
                continue
            identity = tuple(
                item.get(field)
                for field in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey")
            )
            if identity in seen_relations:
                return _relation_path(item)
            seen_relations.add(identity)

    match = re.search(r"Object type '([^']+)' validation\.atLeastOneOf", message)
    if match:
        return f"/objectTypes/{_pointer_segment(match.group(1))}/validation/atLeastOneOf"

    match = re.search(
        r"Application '([^']+)' detail '([^']+)'(?: (header)| panel '([^']+)')?",
        message,
    )
    if match:
        path = (
            f"/applications/{_pointer_segment(match.group(1))}/details/"
            f"{_pointer_segment(match.group(2))}"
        )
        if match.group(3):
            return f"{path}/header"
        if match.group(4):
            return f"{path}/panels/{_pointer_segment(match.group(4))}"
        return path

    match = re.search(r"View '([^']+)\.([^']+)'", message)
    if match and "references unavailable fields" in message:
        return (
            f"/applications/{_pointer_segment(match.group(1))}/views/"
            f"{_pointer_segment(match.group(2))}/config/columns"
        )

    match = re.search(r"Application '([^']+)' references unknown object types: \[(.+)\]", message)
    if match:
        missing = _first_quoted_value(match.group(2))
        application = _keyed_item(source, "applications", match.group(1))
        if application is not None and missing is not None:
            values = application.get("objectTypeKeys", [])
            index = values.index(missing) if missing in values else 0
            return f"/applications/{_pointer_segment(match.group(1))}/objectTypeKeys/{index}"

    match = re.search(
        r"Object type '([^']+)' references unknown attribute type '([^']+)'", message
    )
    if match:
        return (
            f"/objectTypes/{_pointer_segment(match.group(1))}/attributes/"
            f"{_pointer_segment(match.group(2))}/attributeTypeKey"
        )

    match = re.search(
        r"Object type '([^']+)' display attribute '([^']+)' is not attached", message
    )
    if match:
        return f"/objectTypes/{_pointer_segment(match.group(1))}/displayAttributeTypeKey"

    match = re.search(r"Object type '([^']+)' .*unbound attributes: \[(.+)\]", message)
    if match:
        missing = _first_quoted_value(match.group(2)) or "0"
        return (
            f"/objectTypes/{_pointer_segment(match.group(1))}/validation/atLeastOneOf/"
            f"{_pointer_segment(missing)}"
        )

    match = re.search(
        r"Object type '([^']+)' has incompatible parent relation '([^']+)'", message
    )
    if match:
        return (
            f"/objectTypes/{_pointer_segment(match.group(1))}/behavior/"
            f"parentRelationTypeKeys/{_pointer_segment(match.group(2))}"
        )

    relations = source.get("objectTypeRelations", [])
    if "unknown unique ancestor object type" in message:
        known = {item.get("key") for item in source.get("objectTypes", [])}
        item = next(
            (
                item
                for item in relations
                if item.get("features", {}).get("uniqueToAncestorTypeKey") not in known
            ),
            None,
        )
        if item:
            return f"{_relation_path(item)}/features/uniqueToAncestorTypeKey"
    if "invalid uniqueWhenToAttributeEquals condition" in message:
        item = next(
            (
                item
                for item in relations
                if "uniqueWhenToAttributeEquals" in item.get("features", {})
            ),
            None,
        )
        if item:
            return f"{_relation_path(item)}/features/uniqueWhenToAttributeEquals"
    if "unknown relation type" in message:
        known = {item.get("key") for item in source.get("relationTypes", [])}
        item = next(
            (item for item in relations if item.get("relationTypeKey") not in known), None
        )
        if item:
            return f"{_relation_path(item)}/relationTypeKey"
    if "unknown source" in message or "unknown target" in message:
        known = {item.get("key") for item in source.get("objectTypes", [])}
        field = "fromObjectTypeKey" if "unknown source" in message else "toObjectTypeKey"
        item = next((item for item in relations if item.get(field) not in known), None)
        if item:
            return f"{_relation_path(item)}/{field}"
    if "has unknown attributes" in message:
        known = {item.get("key") for item in source.get("attributeTypes", [])}
        item = next(
            (
                item
                for item in relations
                if any(key not in known for key in item.get("attributeTypeKeys", []))
            ),
            None,
        )
        if item:
            missing = next(key for key in item.get("attributeTypeKeys", []) if key not in known)
            return f"{_relation_path(item)}/attributeTypeKeys/{_pointer_segment(missing)}"

    match = re.search(r"Application '([^']+)' has unknown default view '([^']+)'", message)
    if match:
        return f"/applications/{_pointer_segment(match.group(1))}/defaultView"
    match = re.search(r"View '([^']+)\.([^']+)' references unknown object type", message)
    if match:
        return (
            f"/applications/{_pointer_segment(match.group(1))}/views/"
            f"{_pointer_segment(match.group(2))}/objectTypeKey"
        )
    return None


def _keyed_item(source: dict[str, Any], collection: str, key: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in source.get(collection, [])
            if isinstance(item, dict) and item.get("key") == key
        ),
        None,
    )


def _relation_path(item: dict[str, Any]) -> str:
    return "/objectTypeRelations/" + "/".join(
        _pointer_segment(item.get(field, ""))
        for field in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey")
    )


def _first_quoted_value(value: str) -> str | None:
    match = re.search(r"['\"]([^'\"]+)['\"]", value)
    return match.group(1) if match else None


def _pointer_segment(value: Any) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")
