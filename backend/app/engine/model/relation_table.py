"""A relationships table's field references (0.13 RV).

A filter or sort field of a ``relationTable`` view names the place it reads: ``from:<field>`` or
``to:<field>`` for a record at that end (``name`` or an attribute of its type) and
``relation:<attribute>`` for a value of the relationship itself. ``fromColumns``, ``toColumns`` and
``attributeColumns`` name the field alone, as their list says where it is read.
"""

from typing import Any, Literal

from ...errors import api_error
from ...models.schema import EngineModel, RelationTableViewConfig, RelationTableViewDefinition

Place = Literal["from", "to", "relation"]

PLACES: tuple[Place, ...] = ("from", "to", "relation")
# What an end record offers besides its attributes.
END_BUILT_INS = frozenset({"name"})


def split_ref(ref: str) -> tuple[Place, str] | None:
    """``("from", "name")`` for ``from:name``; ``None`` when ``ref`` names no place."""
    place, separator, field = ref.partition(":")
    if separator and field and place in PLACES:
        return place, field  # type: ignore[return-value]
    return None


def descending(sort: str) -> tuple[str, bool]:
    """A sort token's field reference and whether it sorts descending."""
    return (sort[1:], True) if sort.startswith("-") else (sort, False)


def find_relation_table(
    model: EngineModel, application_key: str, view_key: str
) -> RelationTableViewConfig:
    """The configuration of the relationships table ``view_key`` of ``application_key``;
    ``404 RELATION_TABLE_NOT_FOUND`` when the model has none by that name."""
    application = next((row for row in model.applications if row.key == application_key), None)
    view = (
        next((row for row in application.views if row.key == view_key), None)
        if application
        else None
    )
    if not isinstance(view, RelationTableViewDefinition):
        raise api_error(
            404, "RELATION_TABLE_NOT_FOUND", "Relationships table not found in the selected model"
        )
    return view.config


def _source_type(view: Any) -> str | None:
    """The object type a view lists, as the browser groups views into collections."""
    config = getattr(view, "config", None)
    if view.type == "table":
        return view.objectTypeKey
    if view.type == "relationMatrix":
        return config.rowObjectTypeKey
    if view.type == "tree":
        return config.rootObjectTypeKeys[0] if config.rootObjectTypeKeys else None
    if view.type == "relationTable":
        return config.fromObjectTypeKey
    return config.fromObjectTypeKey if config.direction == "outgoing" else config.toObjectTypeKey


def main_view_filter_fields(
    model: EngineModel, application_key: str, object_type_key: str
) -> tuple[str, ...]:
    """The filter fields of the table view a type's collection opens with (0.13 RG), as plain field
    names that a grid can compare: ``name`` or a ``filterable`` scalar attribute bound to the type.

    The collection is the one the grid's own application lists, else the first application that
    lists the type. It opens on the view its navigation names for the type, else the application's
    default view, else its table; a view that is not a table gives no fields.
    """
    applications = [row for row in model.applications if row.key == application_key] + [
        row for row in model.applications if row.key != application_key
    ]
    application = next((row for row in applications if object_type_key in row.objectTypeKeys), None)
    object_type = model.object_type(object_type_key)
    if application is None or object_type is None:
        return ()
    views = [view for view in application.views if _source_type(view) == object_type_key]
    opens = application.navigation.opens.get(object_type_key) if application.navigation else None
    main = (
        next((view for view in views if view.key == opens), None)
        or next((view for view in views if view.key == application.defaultView), None)
        or next((view for view in views if view.type == "table"), None)
        or (views[0] if views else None)
    )
    if main is None or main.type != "table":
        return ()
    bound = {item.attributeTypeKey for item in object_type.attributes}
    fields: list[str] = []
    for field in main.config.filterFields:
        if field == "name":
            fields.append(field)
            continue
        definition = model.attribute_type(field)
        if (
            field in bound
            and definition is not None
            and definition.valueType != "json"
            and definition.features.get("filterable")
        ):
            fields.append(field)
    return tuple(fields)


def grid_filter_fields(
    model: EngineModel, application_key: str, config: RelationTableViewConfig
) -> tuple[str, ...]:
    """The references a relationships grid may filter by: its own ``filterFields``, then the main
    view's filter fields of each end type as ``from:`` and ``to:`` references, without duplicates."""
    refs = list(config.filterFields)
    # Every attribute of the relationship the grid shows is a filter, as a column of its own is.
    refs.extend(
        f"relation:{key}"
        for key in config.attributeColumns
        if (definition := model.attribute_type(key)) is not None and definition.valueType != "json"
    )
    for place, type_key in (("from", config.fromObjectTypeKey), ("to", config.toObjectTypeKey)):
        refs.extend(
            f"{place}:{field}"
            for field in main_view_filter_fields(model, application_key, type_key)
        )
    return tuple(dict.fromkeys(refs))
