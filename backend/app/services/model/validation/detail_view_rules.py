"""Rules for application detail views and their panels."""

from ....common.json_pointer import pointer_segment
from ....models.schema import (
    ApplicationDefinition,
    AttributesPanelDefinition,
    ChildrenPanelDefinition,
    DetailViewDefinition,
    EngineModel,
    ObjectTypeDefinition,
    RelationsPanelDefinition,
    TablePanelDefinition,
)
from ..diagnostics import ModelReferenceError
from .fields import check_fields, check_panel_object_types
from .index import ModelIndex


def check_details(
    model: EngineModel,
    application: ApplicationDefinition,
    application_path: str,
    index: ModelIndex,
) -> None:
    seen_object_type_keys: set[str] = set()
    for detail in application.details:
        detail_path = (
            f"{application_path}/details/{pointer_segment(detail.objectTypeKey)}"
        )
        label = f"Application '{application.key}' detail '{detail.objectTypeKey}'"

        if detail.objectTypeKey in seen_object_type_keys:
            raise ModelReferenceError("duplicate_key", detail_path, f"{label} is duplicated")
        seen_object_type_keys.add(detail.objectTypeKey)
        if detail.objectTypeKey not in index.object_types:
            raise ModelReferenceError(
                "unknown_object_type", detail_path, f"{label} references an unknown object type"
            )
        if detail.objectTypeKey not in application.objectTypeKeys:
            raise ModelReferenceError(
                "invalid_model", detail_path, f"{label} is not available in the application"
            )

        detail_type = index.object_types[detail.objectTypeKey]
        check_fields(
            [detail.header.titleField, detail.header.subtitleField],
            [detail_type],
            index.object_types,
            label=f"{label} header",
            path=f"{detail_path}/header",
        )
        _check_panels(model, application, detail, detail_type, detail_path, label, index)


def _check_panels(
    model: EngineModel,
    application: ApplicationDefinition,
    detail: DetailViewDefinition,
    detail_type: ObjectTypeDefinition,
    detail_path: str,
    detail_label: str,
    index: ModelIndex,
) -> None:
    seen_panel_keys: set[str] = set()
    for panel in detail.panels:
        panel_path = f"{detail_path}/panels/{pointer_segment(panel.key)}"
        label = f"{detail_label} panel '{panel.key}'"
        if panel.key in seen_panel_keys:
            raise ModelReferenceError("duplicate_key", panel_path, f"{label} is duplicated")
        seen_panel_keys.add(panel.key)

        if isinstance(panel, AttributesPanelDefinition):
            check_fields(
                panel.config.fields,
                [detail_type],
                index.object_types,
                label=label,
                path=panel_path,
            )
        elif isinstance(panel, ChildrenPanelDefinition):
            _check_children_panel(
                model, application, panel, detail, panel_path, label, index
            )
        elif isinstance(panel, RelationsPanelDefinition):
            _check_relations_panel(model, panel, detail, panel_path, label, index)
        elif isinstance(panel, TablePanelDefinition):
            check_panel_object_types(
                [panel.config.objectTypeKey],
                application,
                index.object_types,
                label=label,
                path=panel_path,
            )
            check_fields(
                panel.config.columns,
                [index.object_types[panel.config.objectTypeKey]],
                index.object_types,
                label=label,
                path=panel_path,
            )


def _check_children_panel(
    model: EngineModel,
    application: ApplicationDefinition,
    panel: ChildrenPanelDefinition,
    detail: DetailViewDefinition,
    panel_path: str,
    label: str,
    index: ModelIndex,
) -> None:
    check_panel_object_types(
        panel.config.objectTypeKeys,
        application,
        index.object_types,
        label=label,
        path=panel_path,
    )
    child_types = [index.object_types[key] for key in panel.config.objectTypeKeys]
    check_fields(
        panel.config.columns, child_types, index.object_types, label=label, path=panel_path
    )
    for child_type in child_types:
        parent_keys = set(child_type.behavior.get("parentRelationTypeKeys", []))
        if not any(
            allowed.fromObjectTypeKey == detail.objectTypeKey
            and allowed.toObjectTypeKey == child_type.key
            and allowed.relationTypeKey in parent_keys
            for allowed in model.objectTypeRelations
        ):
            raise ModelReferenceError(
                "invalid_model",
                panel_path,
                f"{label} object type '{child_type.key}' is not a configured child of "
                f"'{detail.objectTypeKey}'",
            )


def _check_relations_panel(
    model: EngineModel,
    panel: RelationsPanelDefinition,
    detail: DetailViewDefinition,
    panel_path: str,
    label: str,
    index: ModelIndex,
) -> None:
    related_types: list[ObjectTypeDefinition] = []
    for relation_key in panel.config.relationTypeKeys:
        if relation_key not in index.relation_types:
            raise ModelReferenceError(
                "unknown_relation_type",
                panel_path,
                f"{label} references unknown relation type '{relation_key}'",
            )
        matches = [
            allowed
            for allowed in model.objectTypeRelations
            if allowed.relationTypeKey == relation_key
            and (
                panel.config.direction in {"outgoing", "both"}
                and allowed.fromObjectTypeKey == detail.objectTypeKey
                or panel.config.direction in {"incoming", "both"}
                and allowed.toObjectTypeKey == detail.objectTypeKey
            )
        ]
        if not matches:
            raise ModelReferenceError(
                "invalid_model",
                panel_path,
                f"{label} relation '{relation_key}' is incompatible with "
                f"'{detail.objectTypeKey}' and direction '{panel.config.direction}'",
            )
        for allowed in matches:
            related_key = (
                allowed.toObjectTypeKey
                if allowed.fromObjectTypeKey == detail.objectTypeKey
                else allowed.fromObjectTypeKey
            )
            related_types.append(index.object_types[related_key])
    check_fields(
        panel.config.columns, related_types, index.object_types, label=label, path=panel_path
    )
