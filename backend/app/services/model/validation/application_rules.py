"""Rules for applications and the views they expose."""

from ....common.json_pointer import pointer_segment
from ....models.schema import BUILT_IN_COLUMNS, ApplicationDefinition, EngineModel, ViewDefinition
from ..diagnostics import ModelReferenceError
from .detail_view_rules import check_details
from .fields import check_fields
from .index import ModelIndex


def check(model: EngineModel, index: ModelIndex) -> None:
    for application in model.applications:
        application_path = f"/applications/{pointer_segment(application.key)}"
        _check_object_type_keys(application, application_path, index)
        views = _view_map(application, application_path)
        if application.defaultView not in views:
            raise ModelReferenceError(
                "invalid_model",
                f"{application_path}/defaultView",
                f"Application '{application.key}' has unknown default view "
                f"'{application.defaultView}'",
            )
        for view in application.views:
            _check_view(application, view, application_path, index)
        check_details(model, application, application_path, index)


def _check_object_type_keys(
    application: ApplicationDefinition, application_path: str, index: ModelIndex
) -> None:
    unknown = set(application.objectTypeKeys) - set(index.object_types)
    if not unknown:
        return
    first_unknown = min(unknown)
    position = application.objectTypeKeys.index(first_unknown)
    raise ModelReferenceError(
        "unknown_object_type",
        f"{application_path}/objectTypeKeys/{position}",
        f"Application '{application.key}' references unknown object types: {sorted(unknown)}",
    )


def _view_map(
    application: ApplicationDefinition, application_path: str
) -> dict[str, ViewDefinition]:
    result: dict[str, ViewDefinition] = {}
    for view in application.views:
        if view.key in result:
            raise ModelReferenceError(
                "duplicate_key",
                f"{application_path}/views/{pointer_segment(view.key)}",
                f"Duplicate view in {application.key} key '{view.key}'",
            )
        result[view.key] = view
    return result


def _check_view(
    application: ApplicationDefinition,
    view: ViewDefinition,
    application_path: str,
    index: ModelIndex,
) -> None:
    view_path = f"{application_path}/views/{pointer_segment(view.key)}"
    if view.objectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "unknown_object_type",
            f"{view_path}/objectTypeKey",
            f"View '{application.key}.{view.key}' references unknown object type "
            f"'{view.objectTypeKey}'",
        )
    check_fields(
        view.config.columns,
        [index.object_types[view.objectTypeKey]],
        index.object_types,
        label=f"View '{application.key}.{view.key}'",
        path=f"{view_path}/config/columns",
    )
    attached = {
        binding.attributeTypeKey for binding in index.object_types[view.objectTypeKey].attributes
    }
    unsupported_columns = set(view.config.columns) - BUILT_IN_COLUMNS - attached
    if unsupported_columns:
        raise ModelReferenceError(
            "invalid_model",
            f"{view_path}/config/columns",
            f"Table columns are not available on '{view.objectTypeKey}': {sorted(unsupported_columns)}",
        )
    _check_unique_fields(view.config.columns, view_path, "columns")
    _check_unique_fields(view.config.filterFields, view_path, "filterFields")
    _check_unique_fields(view.config.sortFields, view_path, "sortFields")
    for purpose, fields in (
        ("filter", view.config.filterFields),
        ("sort", view.config.sortFields),
    ):
        check_fields(
            fields,
            [index.object_types[view.objectTypeKey]],
            index.object_types,
            label=f"View '{application.key}.{view.key}'",
            path=f"{view_path}/config/{purpose}Fields",
        )
        for field in fields:
            _check_query_capability(view, field, purpose, view_path, index)
    default_field = view.config.defaultSort.removeprefix("-")
    if default_field not in view.config.sortFields:
        raise ModelReferenceError(
            "invalid_model",
            f"{view_path}/config/defaultSort",
            "Table defaultSort must name one of its sortFields",
        )


def _check_unique_fields(fields: tuple[str, ...], view_path: str, name: str) -> None:
    if len(fields) != len(set(fields)):
        raise ModelReferenceError(
            "duplicate_key",
            f"{view_path}/config/{name}",
            f"Table {name} must contain unique fields",
        )


def _check_query_capability(
    view: ViewDefinition,
    field: str,
    purpose: str,
    view_path: str,
    index: ModelIndex,
) -> None:
    built_in = {"id", "name", "state", "createdAt", "updatedAt"}
    if field in built_in:
        return
    object_type = index.object_types[view.objectTypeKey]
    if field not in {binding.attributeTypeKey for binding in object_type.attributes}:
        raise ModelReferenceError(
            "invalid_model",
            f"{view_path}/config/{purpose}Fields",
            f"Field '{field}' is not supported for table {purpose}",
        )
    attribute = index.attribute_types[field]
    capability = "filterable" if purpose == "filter" else "sortable"
    if attribute.valueType == "json" or not attribute.features.get(capability):
        raise ModelReferenceError(
            "invalid_model",
            f"{view_path}/config/{purpose}Fields",
            f"Attribute '{field}' is not {capability}",
        )
