"""Rules for applications and the views they expose."""

from collections.abc import Sequence

from ....common.json_pointer import pointer_segment
from ....models.schema import (
    BUILT_IN_COLUMNS,
    DETAIL_FIELD_KEYS,
    ApplicationDefinition,
    EngineModel,
    MappingGridViewDefinition,
    ObjectTypeAttributeDefinition,
    ObjectTypeDefinition,
    ObjectTypeRelationDefinition,
    RelationMatrixViewConfig,
    RelationMatrixViewDefinition,
    RelationTableViewDefinition,
    TableViewDefinition,
    TreeViewConfig,
    TreeViewDefinition,
    ViewDefinition,
)
from ..diagnostics import ModelReferenceError, ModelReferenceErrors
from ..related_columns import RELATED_FIELD_PREFIX, is_related_field, related_field_column
from ..relation_table import END_BUILT_INS, descending, split_ref
from ..traversal import ancestor_type_keys, parent_type_keys
from .detail_view_rules import check_details
from .fields import check_fields
from .index import ModelIndex


def check(model: EngineModel, index: ModelIndex) -> None:
    # Views and detail pages report every problem they have; the first problem of anything else
    # (an application's types, default view, navigation) ends the pass, with those found before it.
    problems: list[ModelReferenceError] = []
    try:
        for application in model.applications:
            _check_application(model, application, index, problems)
    except ModelReferenceError as error:
        raise ModelReferenceErrors([*problems, error]) from error
    if problems:
        raise ModelReferenceErrors(problems)


def _check_application(
    model: EngineModel,
    application: ApplicationDefinition,
    index: ModelIndex,
    problems: list[ModelReferenceError],
) -> None:
    application_path = f"/applications/{pointer_segment(application.key)}"
    _check_object_type_keys(application, application_path, index)
    views = _view_map(application, application_path)
    if application.defaultView not in views:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{application_path}/defaultView",
            f"Application '{application.key}' has unknown default view "
            f"'{application.defaultView}'",
        )
    for view in application.views:
        view_path = f"{application_path}/views/{pointer_segment(view.key)}"
        try:
            if isinstance(view, TableViewDefinition):
                _check_table_view(model, application, view, view_path, index)
            elif isinstance(view, MappingGridViewDefinition):
                _check_mapping_grid_view(application, view, view_path, model, index)
            elif isinstance(view, RelationMatrixViewDefinition):
                _check_relation_matrix_view(application, view, view_path, model, index)
            elif isinstance(view, RelationTableViewDefinition):
                _check_relation_table_view(application, view, view_path, model, index)
            elif isinstance(view, TreeViewDefinition):
                _check_tree_view(application, view, view_path, model, index)
        except ModelReferenceError as error:
            problems.append(error)
    check_details(model, application, application_path, index, problems)
    if application.navigation is not None:
        _check_navigation(model, application, f"{application_path}/navigation")


def view_source(view: ViewDefinition) -> str:
    """The collection a view belongs to: its source type, as the sidebar groups lenses (ADR-029)."""
    if isinstance(view, TableViewDefinition):
        return view.objectTypeKey
    if isinstance(view, RelationMatrixViewDefinition):
        return view.config.rowObjectTypeKey
    if isinstance(view, TreeViewDefinition):
        return view.config.rootObjectTypeKeys[0]
    if isinstance(view, RelationTableViewDefinition):
        return view.config.fromObjectTypeKey
    if view.config.direction == "outgoing":
        return view.config.fromObjectTypeKey
    return view.config.toObjectTypeKey


def collection_keys(application: ApplicationDefinition) -> list[str]:
    """The application's collections, first seen first: each view's source type, as the sidebar
    groups lenses (ADR-029)."""
    result: list[str] = []
    for view in application.views:
        source = view_source(view)
        if source not in result:
            result.append(source)
    return result


def _check_navigation(
    model: EngineModel, application: ApplicationDefinition, navigation_path: str
) -> None:
    """Schema 0.10 navigation groups (0.10 N1): unique keys, each entry a collection of the
    application or a relation matrix view of it (``{"view": key}``), each in at most one group, and
    the views collections open on (``opens``). An empty group is valid (D27)."""
    navigation = application.navigation
    collections = set(collection_keys(application))
    matrices = {
        view.key for view in application.views if isinstance(view, RelationMatrixViewDefinition)
    }
    group_of: dict[tuple[str, str], str] = {}
    keys: set[str] = set()
    for group in navigation.groups if navigation else ():
        group_path = f"{navigation_path}/groups/{pointer_segment(group.key)}"
        if group.key in keys:
            raise ModelReferenceError(
                "DUPLICATE_KEY",
                group_path,
                f"Application '{application.key}' declares navigation group '{group.key}' twice",
            )
        keys.add(group.key)
        for position, entry in enumerate(group.collections):
            entry_path = f"{group_path}/collections/{position}"
            if isinstance(entry, str):
                name, what = ("collection", entry), "Collection"
                if entry not in collections:
                    raise ModelReferenceError(
                        "INVALID_REFERENCE",
                        entry_path,
                        f"Navigation group '{group.key}' names '{entry}', which is no collection "
                        f"of application '{application.key}'; its collections are "
                        f"{sorted(collections)}",
                    )
            else:
                name, what = ("view", entry.view), "Relation matrix"
                if entry.view not in matrices:
                    raise ModelReferenceError(
                        "INVALID_REFERENCE",
                        f"{entry_path}/view",
                        f"Navigation group '{group.key}' names view '{entry.view}', which is no "
                        f"relation matrix view of application '{application.key}'; its matrices "
                        f"are {sorted(matrices)}",
                    )
            if name in group_of:
                raise ModelReferenceError(
                    "INVALID_MODEL",
                    entry_path,
                    f"{what} '{name[1]}' is already in navigation group "
                    f"'{group_of[name]}'; it stands in at most one group",
                )
            group_of[name] = group.key
    for collection, view_key in (navigation.opens if navigation else {}).items():
        opens_path = f"{navigation_path}/opens/{pointer_segment(collection)}"
        if collection not in collections:
            raise ModelReferenceError(
                "INVALID_REFERENCE",
                opens_path,
                f"Navigation 'opens' names '{collection}', which is no collection of application "
                f"'{application.key}'; its collections are {sorted(collections)}",
            )
        view = next((item for item in application.views if item.key == view_key), None)
        if view is None or view_source(view) != collection:
            raise ModelReferenceError(
                "INVALID_REFERENCE",
                opens_path,
                f"Collection '{collection}' opens on '{view_key}', which is no view of that "
                f"collection in application '{application.key}'",
            )


def _check_object_type_keys(
    application: ApplicationDefinition, application_path: str, index: ModelIndex
) -> None:
    unknown = set(application.objectTypeKeys) - set(index.object_types)
    if not unknown:
        return
    first_unknown = min(unknown)
    position = application.objectTypeKeys.index(first_unknown)
    raise ModelReferenceError(
        "UNKNOWN_OBJECT_TYPE",
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
                "DUPLICATE_KEY",
                f"{application_path}/views/{pointer_segment(view.key)}",
                f"Duplicate view in {application.key} key '{view.key}'",
            )
        result[view.key] = view
    return result


def _check_table_view(
    model: EngineModel,
    application: ApplicationDefinition,
    view: TableViewDefinition,
    view_path: str,
    index: ModelIndex,
) -> None:
    if view.objectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
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
        related_model=model,
    )
    attached = {
        binding.attributeTypeKey for binding in index.object_types[view.objectTypeKey].attributes
    }
    related = {column for column in view.config.columns if is_related_field(column)}
    unsupported_columns = set(view.config.columns) - BUILT_IN_COLUMNS - attached - related
    if unsupported_columns:
        raise ModelReferenceError(
            "INVALID_MODEL",
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
            related_model=model,
        )
        for field in fields:
            _check_query_capability(model, view, field, purpose, view_path, index)
    default_field = view.config.defaultSort.removeprefix("-")
    if default_field not in view.config.sortFields:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{view_path}/config/defaultSort",
            "Table defaultSort must name one of its sortFields",
        )


def _check_unique_fields(fields: tuple[str, ...], view_path: str, name: str) -> None:
    if len(fields) != len(set(fields)):
        raise ModelReferenceError(
            "DUPLICATE_KEY",
            f"{view_path}/config/{name}",
            f"View {name} must contain unique fields",
        )


def _check_query_capability(
    model: EngineModel,
    view: TableViewDefinition,
    field: str,
    purpose: str,
    view_path: str,
    index: ModelIndex,
) -> None:
    built_in = {"id", "name", "createdAt", "updatedAt"}
    # Any list sorts by its records' object type name; filters take stored fields only.
    if field in built_in or (purpose == "sort" and field == "objectType"):
        return
    if is_related_field(field):
        # check_fields resolved it; only a column whose row holds at most one sorts (D145), and a
        # filter names the relationship alone (0.9 K6, D154).
        text = field.removeprefix(RELATED_FIELD_PREFIX)
        column = related_field_column(model, view.objectTypeKey, text)
        if purpose == "filter":
            if column.field is not None or column.key != text:
                raise ModelReferenceError(
                    "INVALID_MODEL",
                    f"{view_path}/config/filterFields",
                    f"Relationship filter '{field}' names a field of the related records; a"
                    " filter names the relationship alone (related:<key>)",
                )
            return
        if column.field is not None:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{view_path}/config/{purpose}Fields",
                f"Relation column '{field}' shows a field of the related records and cannot be used"
                f" to {purpose}; only one showing their name sorts (D151)",
            )
        if not column.single_valued:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{view_path}/config/{purpose}Fields",
                f"Relation column '{field}' can hold several records in a row and cannot be used"
                f" to {purpose}; only one whose row holds at most one sorts",
            )
        return
    object_type = index.object_types[view.objectTypeKey]
    if field not in {binding.attributeTypeKey for binding in object_type.attributes}:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{view_path}/config/{purpose}Fields",
            f"Field '{field}' is not supported for table {purpose}",
        )
    attribute = index.attribute_types[field]
    if attribute.valueType == "json":
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{view_path}/config/{purpose}Fields",
            f"Attribute '{field}' holds JSON and cannot be used to {purpose}",
        )
    # Every scalar attribute sorts (S4R3 revision); filtering stays opt-in per attribute type.
    if purpose == "filter" and not attribute.features.get("filterable"):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{view_path}/config/{purpose}Fields",
            f"Attribute '{field}' is not filterable",
        )


def _check_mapping_grid_view(
    application: ApplicationDefinition,
    view: MappingGridViewDefinition,
    view_path: str,
    model: EngineModel,
    index: ModelIndex,
) -> None:
    config = view.config
    config_path = f"{view_path}/config"

    if config.relationTypeKey not in index.relation_types:
        raise ModelReferenceError(
            "UNKNOWN_RELATION_TYPE",
            f"{config_path}/relationTypeKey",
            f"Mapping grid '{application.key}.{view.key}' references unknown relation type "
            f"'{config.relationTypeKey}'",
        )

    if config.fromObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
            f"{config_path}/fromObjectTypeKey",
            f"Mapping grid '{application.key}.{view.key}' references unknown object type "
            f"'{config.fromObjectTypeKey}'",
        )
    if config.toObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
            f"{config_path}/toObjectTypeKey",
            f"Mapping grid '{application.key}.{view.key}' references unknown object type "
            f"'{config.toObjectTypeKey}'",
        )

    matching_triple = None
    for allowed in model.objectTypeRelations:
        if (
            allowed.relationTypeKey == config.relationTypeKey
            and allowed.fromObjectTypeKey == config.fromObjectTypeKey
            and allowed.toObjectTypeKey == config.toObjectTypeKey
        ):
            matching_triple = allowed
            break
    if matching_triple is None:
        raise ModelReferenceError(
            "INVALID_REFERENCE",
            config_path,
            f"Mapping grid '{application.key}.{view.key}' references a relation binding "
            f"({config.relationTypeKey}, {config.fromObjectTypeKey} → {config.toObjectTypeKey}) "
            f"that is not declared in objectTypeRelations",
        )

    relation_type = index.relation_types[config.relationTypeKey]
    if relation_type.features.get("parentOf"):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/relationTypeKey",
            f"Mapping grid '{application.key}.{view.key}' cannot use containment relation type "
            f"'{config.relationTypeKey}'",
        )

    if matching_triple.required and matching_triple.cardinality in (
        "one-to-one",
        "one-to-many",
    ):
        raise ModelReferenceError(
            "INVALID_MODEL",
            config_path,
            f"Mapping grid '{application.key}.{view.key}' cannot use a required-ownership binding "
            f"({config.relationTypeKey}, {config.fromObjectTypeKey} → {config.toObjectTypeKey})",
        )

    source_type_key = (
        config.fromObjectTypeKey
        if config.direction == "outgoing"
        else config.toObjectTypeKey
    )
    source_type = index.object_types[source_type_key]
    check_fields(
        config.sourceColumns,
        [source_type],
        index.object_types,
        label=f"Mapping grid '{application.key}.{view.key}' sourceColumns",
        path=f"{config_path}/sourceColumns",
    )
    _check_unique_fields(config.sourceColumns, view_path, "sourceColumns")

    target_type_key = (
        config.toObjectTypeKey
        if config.direction == "outgoing"
        else config.fromObjectTypeKey
    )
    target_type = index.object_types[target_type_key]
    check_fields(
        config.targetDisplayColumns,
        [target_type],
        index.object_types,
        label=f"Mapping grid '{application.key}.{view.key}' targetDisplayColumns",
        path=f"{config_path}/targetDisplayColumns",
    )
    _check_unique_fields(config.targetDisplayColumns, view_path, "targetDisplayColumns")

    target_attached = {
        binding.attributeTypeKey for binding in target_type.attributes
    }
    candidate_built_in = {"name"}
    for field in config.candidateSearchFields:
        if field in candidate_built_in:
            continue
        if field not in target_attached:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/candidateSearchFields",
                f"Mapping grid '{application.key}.{view.key}' candidateSearchFields references "
                f"'{field}' which is not attached to target type '{target_type_key}'",
            )
        attribute = index.attribute_types[field]
        if not attribute.features.get("searchable"):
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/candidateSearchFields",
                f"Mapping grid '{application.key}.{view.key}' candidateSearchFields references "
                f"'{field}' which is not searchable",
            )
    _check_unique_fields(config.candidateSearchFields, view_path, "candidateSearchFields")


def _check_relation_matrix_view(
    application: ApplicationDefinition,
    view: RelationMatrixViewDefinition,
    view_path: str,
    model: EngineModel,
    index: ModelIndex,
) -> None:
    """Rows are records of one type; a cell holds a row's related records under one column record.

    The binding may be optional or required, of any cardinality, and read from either end; the
    column type is any type that can contain the cell type at some depth.
    """
    config = view.config
    config_path = f"{view_path}/config"
    label = f"Relation matrix '{application.key}.{view.key}'"

    for field in ("rowObjectTypeKey", "columnObjectTypeKey", "cellObjectTypeKey"):
        key = getattr(config, field)
        if key not in index.object_types:
            raise ModelReferenceError(
                "UNKNOWN_OBJECT_TYPE",
                f"{config_path}/{field}",
                f"{label} references unknown object type '{key}'",
            )
        if key not in application.objectTypeKeys:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/{field}",
                f"{label} uses object type '{key}' outside application '{application.key}'",
            )

    relation_path = f"{config_path}/relationTypeKey"
    if config.relationTypeKey not in index.relation_types:
        raise ModelReferenceError(
            "UNKNOWN_RELATION_TYPE",
            relation_path,
            f"{label} references unknown relation type '{config.relationTypeKey}'",
        )
    if index.relation_types[config.relationTypeKey].features.get("parentOf"):
        raise ModelReferenceError(
            "INVALID_MODEL",
            relation_path,
            f"{label} cannot use containment relation type '{config.relationTypeKey}'",
        )
    from_key, to_key = (
        (config.rowObjectTypeKey, config.cellObjectTypeKey)
        if config.direction == "outgoing"
        else (config.cellObjectTypeKey, config.rowObjectTypeKey)
    )
    binding = model.allowed_relation(config.relationTypeKey, from_key, to_key)
    if binding is None:
        raise ModelReferenceError(
            "INVALID_REFERENCE",
            relation_path,
            f"{label} references a relation binding ({config.relationTypeKey}, {from_key} → "
            f"{to_key}) that is not declared in objectTypeRelations",
        )

    if config.columnObjectTypeKey not in ancestor_type_keys(model, config.cellObjectTypeKey):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/columnObjectTypeKey",
            f"{label} column type '{config.columnObjectTypeKey}' cannot contain "
            f"'{config.cellObjectTypeKey}' through parentRelationTypeKeys",
        )

    row_type = index.object_types[config.rowObjectTypeKey]
    check_fields(
        config.rowColumns,
        [row_type],
        index.object_types,
        label=f"{label} rowColumns",
        path=f"{config_path}/rowColumns",
    )

    column_type = index.object_types[config.columnObjectTypeKey]
    if config.columnLabelField != "name" and config.columnLabelField not in _scalar_fields(
        column_type.attributes, index
    ):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/columnLabelField",
            f"{label} columnLabelField '{config.columnLabelField}' is not 'name' or a "
            f"scalar attribute attached to '{config.columnObjectTypeKey}'",
        )

    _check_unique_fields(config.cellFields, view_path, "cellFields")
    cell_type = index.object_types[config.cellObjectTypeKey]
    cell_bindings = {binding.attributeTypeKey: binding for binding in cell_type.attributes}
    for position, field in enumerate(config.cellFields):
        if field not in cell_bindings:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/cellFields/{position}",
                f"{label} cellFields references '{field}', which is not attached to "
                f"'{config.cellObjectTypeKey}'",
            )

    _check_unique_fields(config.searchFields, view_path, "searchFields")
    searchable = {
        binding.attributeTypeKey
        for binding in row_type.attributes
        if index.attribute_types[binding.attributeTypeKey].features.get("searchable")
    }
    for position, field in enumerate(config.searchFields):
        if field != "name" and field not in searchable:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/searchFields/{position}",
                f"{label} searchFields references '{field}', which is not 'name' or a "
                f"searchable attribute attached to '{config.rowObjectTypeKey}'",
            )

    _check_unique_fields(config.cellActions, view_path, "cellActions")
    for position, action in enumerate(config.cellActions):
        reason = _cell_action_refusal(action, config, binding, cell_bindings, model, index)
        if reason:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/cellActions/{position}",
                f"{label} cannot offer '{action}': {reason}",
            )


def _check_relation_table_view(
    application: ApplicationDefinition,
    view: RelationTableViewDefinition,
    view_path: str,
    model: EngineModel,
    index: ModelIndex,
) -> None:
    """The relationships of one declared binding, one row each (0.13 RV).

    The relation type is not a containment, and every field a column, filter or sort names exists where it is read: on an end's type, or on the
    binding as an attribute of the relationship.
    """
    config = view.config
    config_path = f"{view_path}/config"
    label = f"Relationships table '{application.key}.{view.key}'"

    for field in ("fromObjectTypeKey", "toObjectTypeKey"):
        key = getattr(config, field)
        if key not in index.object_types:
            raise ModelReferenceError(
                "UNKNOWN_OBJECT_TYPE",
                f"{config_path}/{field}",
                f"{label} references unknown object type '{key}'",
            )
    relation_path = f"{config_path}/relationTypeKey"
    if config.relationTypeKey not in index.relation_types:
        raise ModelReferenceError(
            "UNKNOWN_RELATION_TYPE",
            relation_path,
            f"{label} references unknown relation type '{config.relationTypeKey}'",
        )
    if index.relation_types[config.relationTypeKey].features.get("parentOf"):
        raise ModelReferenceError(
            "INVALID_MODEL",
            relation_path,
            f"{label} cannot use containment relation type '{config.relationTypeKey}'",
        )
    binding = model.allowed_relation(
        config.relationTypeKey, config.fromObjectTypeKey, config.toObjectTypeKey
    )
    if binding is None:
        raise ModelReferenceError(
            "INVALID_REFERENCE",
            relation_path,
            f"{label} references a relation binding ({config.relationTypeKey}, "
            f"{config.fromObjectTypeKey} \u2192 {config.toObjectTypeKey}) that is not declared in "
            "objectTypeRelations",
        )

    ends = {
        "from": index.object_types[config.fromObjectTypeKey],
        "to": index.object_types[config.toObjectTypeKey],
    }
    scalar = {end: _scalar_fields(item.attributes, index) for end, item in ends.items()}
    for name, end in (("fromColumns", "from"), ("toColumns", "to")):
        columns: tuple[str, ...] = getattr(config, name)
        _check_unique_fields(columns, view_path, name)
        for position, field in enumerate(columns):
            if field not in END_BUILT_INS and field not in scalar[end]:
                raise ModelReferenceError(
                    "INVALID_MODEL",
                    f"{config_path}/{name}/{position}",
                    f"{label} {name} references '{field}', which is not 'name' or a scalar "
                    f"attribute attached to '{ends[end].key}'",
                )

    declared = set(binding.attributeTypeKeys)
    _check_unique_fields(config.attributeColumns, view_path, "attributeColumns")
    for position, field in enumerate(config.attributeColumns):
        if field not in declared:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/attributeColumns/{position}",
                f"{label} attributeColumns references '{field}', which binding "
                f"({config.relationTypeKey}, {config.fromObjectTypeKey} \u2192 "
                f"{config.toObjectTypeKey}) does not declare in attributeTypeKeys",
            )

    for purpose, fields in (("filter", config.filterFields), ("sort", config.sortFields)):
        name = f"{purpose}Fields"
        _check_unique_fields(fields, view_path, name)
        for position, ref in enumerate(fields):
            _check_relation_table_ref(
                ref, purpose, f"{config_path}/{name}/{position}", label, binding, ends, scalar, index
            )
    if descending(config.defaultSort)[0] not in config.sortFields:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/defaultSort",
            f"{label} defaultSort must name one of its sortFields",
        )


def _check_relation_table_ref(
    ref: str,
    purpose: str,
    path: str,
    label: str,
    binding: ObjectTypeRelationDefinition,
    ends: dict[str, ObjectTypeDefinition],
    scalar: dict[str, set[str]],
    index: ModelIndex,
) -> None:
    """One ``from:<field>``, ``to:<field>`` or ``relation:<attribute>`` of a filter or a sort."""
    parts = split_ref(ref)
    if parts is None:
        raise ModelReferenceError(
            "INVALID_MODEL",
            path,
            f"{label} {purpose} field '{ref}' must be from:<field>, to:<field> or "
            "relation:<attribute>",
        )
    place, field = parts
    if place == "relation":
        if field not in binding.attributeTypeKeys:
            raise ModelReferenceError(
                "INVALID_MODEL",
                path,
                f"{label} {purpose} field '{ref}': the binding does not declare attribute "
                f"'{field}' in attributeTypeKeys",
            )
    elif field in END_BUILT_INS:
        return
    elif field not in scalar[place]:
        raise ModelReferenceError(
            "INVALID_MODEL",
            path,
            f"{label} {purpose} field '{ref}': '{field}' is not 'name' or a scalar attribute "
            f"attached to '{ends[place].key}'",
        )
    if purpose == "filter" and not index.attribute_types[field].features.get("filterable"):
        raise ModelReferenceError(
            "INVALID_MODEL", path, f"{label} filter field '{ref}': attribute '{field}' is not filterable"
        )
    if index.attribute_types[field].valueType == "json":
        raise ModelReferenceError(
            "INVALID_MODEL", path, f"{label} {purpose} field '{ref}' holds JSON and cannot be used"
        )


def _cell_action_refusal(
    action: str,
    config: RelationMatrixViewConfig,
    binding: ObjectTypeRelationDefinition,
    cell_bindings: dict[str, ObjectTypeAttributeDefinition],
    model: EngineModel,
    index: ModelIndex,
) -> str | None:
    """Why a cell action could never succeed for this model, so no view offers it."""
    if action == "edit" and all(cell_bindings[field].readOnly for field in config.cellFields):
        return "every cellFields entry is read-only"
    if action == "unlink" and binding.required:
        return f"'{config.relationTypeKey}' is required and cannot be removed on its own"
    if action != "create":
        return None
    # A cell record is created with its cellFields and this one relation, so it must need no more.
    missing = [
        field
        for field, cell_binding in cell_bindings.items()
        if cell_binding.required
        and field not in config.cellFields
        and index.attribute_types[field].default is None
    ]
    if missing:
        return f"required fields {missing} of '{config.cellObjectTypeKey}' are not cellFields"
    cell_type = index.object_types[config.cellObjectTypeKey]
    parent_relations = set(cell_type.behavior.get("parentRelationTypeKeys", []))
    other_required = sorted(
        {
            allowed.relationTypeKey
            for allowed in model.objectTypeRelations
            if allowed.toObjectTypeKey == config.cellObjectTypeKey
            and allowed.required
            and allowed.relationTypeKey not in parent_relations
            # The engine checks a required relation by its key, which the cell's own one satisfies.
            and not (
                config.direction == "outgoing"
                and allowed.relationTypeKey == config.relationTypeKey
            )
        }
    )
    if other_required:
        return f"'{config.cellObjectTypeKey}' also requires relations {other_required}"
    return None


# Built-in fields a tree branch can sort by, as the list query does.
_TREE_SORT_BUILT_INS = {"id", "name", "createdAt", "updatedAt"}


def _check_tree_view(
    application: ApplicationDefinition,
    view: TreeViewDefinition,
    view_path: str,
    model: EngineModel,
    index: ModelIndex,
) -> None:
    """A tree shows records of its node types, from root records down through their containers.

    Every node type must be reachable from a root type through containers the tree also shows, so no
    record of a listed type is unreachable by expanding branches.
    """
    config = view.config
    config_path = f"{view_path}/config"
    label = f"Tree '{application.key}.{view.key}'"

    _check_unique_fields(config.objectTypeKeys, view_path, "objectTypeKeys")
    for position, key in enumerate(config.objectTypeKeys):
        if key not in index.object_types:
            raise ModelReferenceError(
                "UNKNOWN_OBJECT_TYPE",
                f"{config_path}/objectTypeKeys/{position}",
                f"{label} references unknown object type '{key}'",
            )
        if key not in application.objectTypeKeys:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/objectTypeKeys/{position}",
                f"{label} uses object type '{key}' outside application '{application.key}'",
            )
    node_types = set(config.objectTypeKeys)

    _check_unique_fields(config.rootObjectTypeKeys, view_path, "rootObjectTypeKeys")
    for position, key in enumerate(config.rootObjectTypeKeys):
        root_path = f"{config_path}/rootObjectTypeKeys/{position}"
        if key not in node_types:
            raise ModelReferenceError(
                "INVALID_MODEL",
                root_path,
                f"{label} root type '{key}' is not one of its objectTypeKeys",
            )
        if not index.object_types[key].features.get("rootCreatable"):
            raise ModelReferenceError(
                "INVALID_MODEL",
                root_path,
                f"{label} root type '{key}' cannot exist without a parent (rootCreatable)",
            )

    reached = set(config.rootObjectTypeKeys)
    containers = {key: parent_type_keys(model, key) & node_types for key in node_types}
    while grown := {key for key in node_types - reached if containers[key] & reached}:
        reached |= grown
    for position, key in enumerate(config.objectTypeKeys):
        if key not in reached:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/objectTypeKeys/{position}",
                f"{label} node type '{key}' is not reachable from its root types through "
                "parentRelationTypeKeys of the types it shows",
            )

    nodes = [index.object_types[key] for key in config.objectTypeKeys]
    shared_scalars = set.intersection(*(_scalar_fields(node.attributes, index) for node in nodes))
    if config.labelField != "name" and config.labelField not in shared_scalars:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/labelField",
            f"{label} labelField '{config.labelField}' is not 'name' or a scalar attribute "
            "attached to every node type",
        )
    if (
        config.secondaryField is not None
        and config.secondaryField not in DETAIL_FIELD_KEYS
        and config.secondaryField not in shared_scalars
    ):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{config_path}/secondaryField",
            f"{label} secondaryField '{config.secondaryField}' is not a built-in field or a "
            "scalar attribute attached to every node type",
        )

    for key, sort in config.childSort.items():
        sort_path = f"{config_path}/childSort/{pointer_segment(key)}"
        if key not in node_types:
            raise ModelReferenceError(
                "INVALID_MODEL",
                sort_path,
                f"{label} childSort names '{key}', which is not one of its objectTypeKeys",
            )
        field = sort.removeprefix("-")
        if field not in _TREE_SORT_BUILT_INS and field not in _scalar_fields(
            index.object_types[key].attributes, index
        ):
            raise ModelReferenceError(
                "INVALID_MODEL",
                sort_path,
                f"{label} cannot sort '{key}' by '{field}': it is not a sortable built-in field "
                "or a scalar attribute attached to that type",
            )

    _check_unique_fields(config.actions, view_path, "actions")
    if config.availabilityField is not None:
        if "setAvailability" not in config.actions:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/availabilityField",
                f"{label} declares availabilityField without the setAvailability action",
            )
        for node in nodes:
            binding = next(
                (item for item in node.attributes if item.attributeTypeKey == config.availabilityField),
                None,
            )
            if (
                binding is None
                or index.attribute_types[config.availabilityField].valueType != "boolean"
            ):
                raise ModelReferenceError(
                    "INVALID_MODEL",
                    f"{config_path}/availabilityField",
                    f"{label} availabilityField '{config.availabilityField}' is not a boolean "
                    f"attribute attached to '{node.key}'",
                )
    for position, action in enumerate(config.actions):
        reason = tree_action_refusal(action, config, nodes, containers)
        if reason:
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{config_path}/actions/{position}",
                f"{label} cannot offer '{action}': {reason}",
            )


def tree_action_refusal(
    action: str,
    config: TreeViewConfig,
    nodes: Sequence[ObjectTypeDefinition],
    containers: dict[str, set[str]],
) -> str | None:
    """Why a tree action could never succeed for this model, so no view offers it."""
    if action in {"createChild", "move"} and not any(containers.values()):
        return "no node type can contain another"
    if action == "setAvailability":
        if config.availabilityField is None:
            return "it needs availabilityField"
        return _read_only_on(config.availabilityField, nodes)
    if action == "rename" and config.labelField != "name":
        return _read_only_on(config.labelField, nodes)
    return None


def _read_only_on(field: str, nodes: Sequence[ObjectTypeDefinition]) -> str | None:
    for node in nodes:
        if any(item.attributeTypeKey == field and item.readOnly for item in node.attributes):
            return f"'{field}' is read-only on '{node.key}'"
    return None


def _scalar_fields(bindings: Sequence[ObjectTypeAttributeDefinition], index: ModelIndex) -> set[str]:
    return {
        binding.attributeTypeKey
        for binding in bindings
        if index.attribute_types[binding.attributeTypeKey].valueType != "json"
    }
