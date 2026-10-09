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
from ..related_columns import RelatedKeyError, is_related_field, related_field_column

ANCESTOR_FIELD_PREFIX = "ancestor:"

# Where a relation column may stand (Base 0.9 K5, D141, D145).
RELATED_COLUMN_PLACES = (
    "a table view's columns, a children or table panel's columns, or (where a row holds at most"
    " one) a table view's sort fields"
)


def require_schema(model: EngineModel, minimum: str, path: str, feature: str) -> None:
    """Refuse ``feature`` at ``path`` when the model's schema version predates ``minimum``."""
    if _schema_version(model.schemaVersion) < _schema_version(minimum):
        raise ModelReferenceError(
            "INVALID_MODEL",
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
    related_model: EngineModel | None = None,
) -> None:
    """Every named field must be built in, an attached attribute, or a known ancestor reference.

    With ``related_model``, a ``related:<key>`` relation column is allowed too, resolved for every
    listed type against that model (schema 0.9); without it, one is refused.
    """
    present = [field for field in fields if field is not None]
    if len(present) != len(set(present)):
        raise ModelReferenceError("DUPLICATE_KEY", path, f"{label} has duplicate fields")

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
                "INVALID_REFERENCE",
                path,
                f"{label} references unknown ancestor object type '{ancestor_type_key}'",
            )
    related_fields = [field for field in present if is_related_field(field)]
    if related_fields:
        _check_related_fields(related_fields, object_types, related_model, label=label, path=path)
    unknown = set(present) - ancestor_fields - set(related_fields) - attached - DETAIL_FIELD_KEYS
    if unknown:
        raise ModelReferenceError(
            "INVALID_MODEL", path, f"{label} references unavailable fields: {sorted(unknown)}"
        )


def _check_related_fields(
    fields: Sequence[str],
    object_types: Sequence[ObjectTypeDefinition],
    model: EngineModel | None,
    *,
    label: str,
    path: str,
) -> None:
    if model is None:
        raise ModelReferenceError(
            "INVALID_MODEL",
            path,
            f"{label} cannot show relation column '{fields[0]}': a relation column is allowed only"
            f" in {RELATED_COLUMN_PLACES}",
        )
    require_schema(model, "0.9", path, f"{label} relation column '{fields[0]}'")
    for field in fields:
        key = field.removeprefix("related:")
        for object_type in object_types:
            try:
                related_field_column(model, object_type.key, key)
            except RelatedKeyError as error:
                raise ModelReferenceError(
                    "INVALID_REFERENCE", path, f"{label} relation column '{field}': {error}"
                ) from None


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
            "INVALID_MODEL", path, f"{label} requires at least one object type"
        )
    if len(keys) != len(set(keys)):
        raise ModelReferenceError("DUPLICATE_KEY", path, f"{label} has duplicate object types")
    unknown = set(keys) - set(object_map)
    if unknown:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
            path,
            f"{label} references unknown object types: {sorted(unknown)}",
        )
    unavailable = set(keys) - set(application.objectTypeKeys)
    if unavailable:
        raise ModelReferenceError(
            "INVALID_MODEL",
            path,
            f"{label} uses object types outside the application: {sorted(unavailable)}",
        )
