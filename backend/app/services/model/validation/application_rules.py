"""Rules for applications and the views they expose."""

from ....common.json_pointer import pointer_segment
from ....models.schema import ApplicationDefinition, EngineModel, ViewDefinition
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
    if not view.objectTypeKey:
        return
    view_path = f"{application_path}/views/{pointer_segment(view.key)}"
    if view.objectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "unknown_object_type",
            f"{view_path}/objectTypeKey",
            f"View '{application.key}.{view.key}' references unknown object type "
            f"'{view.objectTypeKey}'",
        )
    check_fields(
        view.config.get("columns", []),
        [index.object_types[view.objectTypeKey]],
        index.object_types,
        label=f"View '{application.key}.{view.key}'",
        path=f"{view_path}/config/columns",
    )
