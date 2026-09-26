"""Shared field and object-type reference checks used by view and detail-panel rules.

Each helper takes the JSON pointer of the node it is checking, so a failure reports the exact
location rather than the collection it was reached through.
"""

from collections.abc import Sequence

from ....models.schema import (
    DETAIL_FIELD_KEYS,
    ApplicationDefinition,
    EngineModel,
    ObjectTypeDefinition,
)
from ..diagnostics import ModelReferenceError

ANCESTOR_FIELD_PREFIX = "ancestor:"


def require_schema(model: EngineModel, minimum: str, path: str, feature: str) -> None:
    """Refuse ``feature`` at ``path`` when the model's schema version predates ``minimum``."""
    if _schema_version(model.schemaVersion) < _schema_version(minimum):
        raise ModelReferenceError(
            "invalid_model",
            path,
            f"{feature} requires schema version {minimum} or later; "
            f"this model uses {model.schemaVersion}",
        )


def _schema_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def check_fields(
    fields: Sequence[str | None],
    object_types: Sequence[ObjectTypeDefinition],
    object_map: dict[str, ObjectTypeDefinition],
    *,
    label: str,
    path: str,
) -> None:
    """Every named field must be built in, an attached attribute, or a known ancestor reference."""
    present = [field for field in fields if field is not None]
    if len(present) != len(set(present)):
        raise ModelReferenceError("duplicate_key", path, f"{label} has duplicate fields")

    attached = {
        binding.attributeTypeKey
        for object_type in object_types
        for binding in object_type.attributes
    }
    ancestor_fields = {
        field for field in present if field.startswith(ANCESTOR_FIELD_PREFIX)
    }
    for field in sorted(ancestor_fields):
        ancestor_type_key = field.removeprefix(ANCESTOR_FIELD_PREFIX)
        if not ancestor_type_key or ancestor_type_key not in object_map:
            raise ModelReferenceError(
                "invalid_reference",
                path,
                f"{label} references unknown ancestor object type '{ancestor_type_key}'",
            )
    unknown = set(present) - ancestor_fields - attached - DETAIL_FIELD_KEYS
    if unknown:
        raise ModelReferenceError(
            "invalid_model", path, f"{label} references unavailable fields: {sorted(unknown)}"
        )


def check_panel_object_types(
    keys: Sequence[str],
    application: ApplicationDefinition,
    object_map: dict[str, ObjectTypeDefinition],
    *,
    label: str,
    path: str,
) -> None:
    if not keys:
        raise ModelReferenceError(
            "invalid_model", path, f"{label} requires at least one object type"
        )
    if len(keys) != len(set(keys)):
        raise ModelReferenceError("duplicate_key", path, f"{label} has duplicate object types")
    unknown = set(keys) - set(object_map)
    if unknown:
        raise ModelReferenceError(
            "unknown_object_type",
            path,
            f"{label} references unknown object types: {sorted(unknown)}",
        )
    unavailable = set(keys) - set(application.objectTypeKeys)
    if unavailable:
        raise ModelReferenceError(
            "invalid_model",
            path,
            f"{label} uses object types outside the application: {sorted(unavailable)}",
        )
