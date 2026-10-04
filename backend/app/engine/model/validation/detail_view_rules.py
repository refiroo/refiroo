"""Rules for application detail views and their panels."""

from collections.abc import Sequence

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
from ..traversal import ancestor_type_keys, related_object_types
from .fields import ANCESTOR_FIELD_PREFIX, check_fields, check_panel_object_types, require_schema
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
            raise ModelReferenceError("DUPLICATE_KEY", detail_path, f"{label} is duplicated")
        seen_object_type_keys.add(detail.objectTypeKey)
        if detail.objectTypeKey not in index.object_types:
            raise ModelReferenceError(
                "UNKNOWN_OBJECT_TYPE", detail_path, f"{label} references an unknown object type"
            )
        if detail.objectTypeKey not in application.objectTypeKeys:
            raise ModelReferenceError(
                "INVALID_MODEL", detail_path, f"{label} is not available in the application"
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
            raise ModelReferenceError("DUPLICATE_KEY", panel_path, f"{label} is duplicated")
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
                "INVALID_MODEL",
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
                "UNKNOWN_RELATION_TYPE",
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
                "INVALID_MODEL",
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
    _check_relations_panel_sort(model, panel, detail, panel_path, label, index)


def _check_relations_panel_sort(
    model: EngineModel,
    panel: RelationsPanelDefinition,
    detail: DetailViewDefinition,
    panel_path: str,
    label: str,
    index: ModelIndex,
) -> None:
    """Declared sort options must be ones the relation list accepts for the records it lists.

    ``name``, ``objectType`` and ``relationship`` sort any list, and a scalar attribute bound to one
    of the related types sorts it with the other records last. A reachable ``ancestor:<type>``
    needs the panel to list one related object type, as the relation query does. Every data column
    sorts from its header regardless; ``sortFields`` adds fields to the sort menu and
    ``defaultSort`` chooses the initial order.
    """
    config = panel.config
    config_path = f"{panel_path}/config"
    if config.sortFields is None and config.defaultSort is None:
        return
    first_path = f"{config_path}/{'sortFields' if config.sortFields is not None else 'defaultSort'}"
    require_schema(model, "0.7", first_path, f"{label} sort configuration")
    if config.sortFields is not None and len(config.sortFields) != len(set(config.sortFields)):
        raise ModelReferenceError(
            "DUPLICATE_KEY", f"{config_path}/sortFields", f"{label} sortFields must be unique"
        )

    related_types = related_object_types(
        model, detail.objectTypeKey, config.direction, config.relationTypeKeys
    )
    fields = [
        (f"{config_path}/sortFields/{position}", field)
        for position, field in enumerate(config.sortFields or ())
    ]
    if config.defaultSort is not None:
        fields.append((f"{config_path}/defaultSort", config.defaultSort.removeprefix("-")))
    for field_path, field in fields:
        _check_relation_sort_field(model, related_types, field, field_path, label, index)


def _check_relation_sort_field(
    model: EngineModel,
    related_types: Sequence[ObjectTypeDefinition],
    field: str,
    field_path: str,
    label: str,
    index: ModelIndex,
) -> None:
    if field in {"name", "objectType", "relationship"}:
        return
    if field.startswith(ANCESTOR_FIELD_PREFIX):
        ancestor_key = field.removeprefix(ANCESTOR_FIELD_PREFIX)
        if len(related_types) != 1:
            related_keys = sorted(related_type.key for related_type in related_types)
            raise ModelReferenceError(
                "INVALID_MODEL",
                field_path,
                f"{label} cannot sort by '{field}': it lists several related object types "
                f"{related_keys}, and an ancestor sort needs one",
            )
        if ancestor_key not in ancestor_type_keys(model, related_types[0].key):
            raise ModelReferenceError(
                "INVALID_REFERENCE",
                field_path,
                f"{label} cannot sort by '{field}': '{related_types[0].key}' has no ancestor of "
                f"type '{ancestor_key}'",
            )
        return
    if field not in index.attribute_types:
        raise ModelReferenceError(
            "INVALID_MODEL",
            field_path,
            f"{label} cannot sort by '{field}'; a relations panel sorts by name, objectType, "
            "relationship, a scalar attribute or an ancestor",
        )
    bound = {binding.attributeTypeKey for item in related_types for binding in item.attributes}
    if field not in bound:
        raise ModelReferenceError(
            "INVALID_MODEL",
            field_path,
            f"{label} cannot sort by '{field}': it is not attached to any related object type",
        )
    if index.attribute_types[field].valueType == "json":
        raise ModelReferenceError(
            "INVALID_MODEL",
            field_path,
            f"{label} cannot sort by '{field}': attribute '{field}' holds JSON",
        )
