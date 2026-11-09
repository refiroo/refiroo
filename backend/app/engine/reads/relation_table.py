"""A relationships table's rows: filter, sort and group in SQL (0.13 RV).

The rows are the relationships of one binding, read in live data, a change set or a publication
through the mapping projections (``mapping_projection.py``), with both end records joined. A field is
``from:<field>`` or ``to:<field>`` (the record's name or a scalar attribute of its type) or
``relation:<attribute>`` (a value of the relationship); a live end's attribute is read from the
typed value table, every other value from the JSON a snapshot row keeps. A filter is an equality on
a field the view declares; a sort orders by one of the view's sort fields, records without a value
last, and is closed by the relationship's ID so every page can be sought. With ``groupBy`` the rows
are ordered by the group end's name first, so a group's rows stand together.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Numeric,
    Select,
    and_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
    type_coerce,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import SortKey
from ...errors import api_error
from ...models.database import AttributeValue
from ...models.schema import EngineModel, RelationTableViewConfig
from ..model.relation_table import descending, split_ref
from ..records.values import VALUE_COLUMNS
from .object_query import parse_typed

# What a record without a value sorts as inside its rank, so a cursor holds a value to compare.
_NEUTRAL: dict[str, Any] = {
    "text": "",
    "integer": 0,
    "decimal": Decimal(0),
    "boolean": False,
    "date": date(1970, 1, 1),
    "dateTime": datetime(1970, 1, 1, tzinfo=UTC),
}
_SCALAR = {"text": "text", "longText": "text"}


def _kind(value_type: str) -> str:
    return _SCALAR.get(value_type, value_type)


@dataclass(frozen=True)
class RelationTableQuery:
    """The statement of one page's source, its keyset and what binds a cursor to the request.

    The statement selects the relationship, both end IDs and a ``sort_<n>`` per ordering key.
    ``group_rows`` counts the filtered rows per group record (none without ``groupBy``), which
    :func:`group_counts` narrows to the groups a page shows.
    """

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]
    seek: Callable[[str], Any]
    group_rows: Select[Any] | None
    group_column: Any | None


def _format(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _end_value(
    model: EngineModel,
    end: Subquery,
    field: str,
    *,
    live: bool,
) -> tuple[Any, str]:
    """A record's field as a typed SQL value, and the value type it holds."""
    if field == "name":
        return end.c.name, "text"
    value_type = model.attribute_type(field).valueType
    if live:
        column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
        value = (
            select(column)
            .where(AttributeValue.object_id == end.c.id, AttributeValue.attribute_type_key == field)
            .correlate_except(AttributeValue)
            .scalar_subquery()
        )
        return value, _kind(value_type)
    return _json_value(type_coerce(end.c.attributes, JSON), field, value_type), _kind(value_type)


def _json_value(document: Any, key: str, value_type: str) -> Any:
    """One value of a JSON ``attributes`` document, typed as the value table types it."""
    item = document[key]
    kind = _kind(value_type)
    if kind == "text":
        return item.as_string()
    if kind == "integer":
        return item.as_integer()
    if kind == "boolean":
        return item.as_boolean()
    if kind == "decimal":
        return cast(item.as_string(), Numeric)
    if kind == "date":
        return cast(item.as_string(), Date)
    return cast(item.as_string(), DateTime(timezone=True))


def build_relation_table_query(
    model: EngineModel,
    config: RelationTableViewConfig,
    objects: Subquery,
    relations: Subquery,
    *,
    live: bool,
    from_object_id: str | None,
    to_object_id: str | None,
    field_filters: list[tuple[str, str, str]],
    search: str | None,
    sort: str | None,
) -> RelationTableQuery:
    """The view's relationships, narrowed by the ends, the field filters and the search, ordered by
    ``sort`` (the view's default when ``None``)."""
    from_end, to_end = objects.alias("from_end"), objects.alias("to_end")
    ends = {"from": from_end, "to": to_end}

    def value_of(ref: str) -> tuple[Any, str]:
        parts = split_ref(ref)
        assert parts is not None  # the model's validation holds every field of the view
        place, field = parts
        if place == "relation":
            value_type = model.attribute_type(field).valueType
            return _json_value(type_coerce(relations.c.attributes, JSON), field, value_type), _kind(
                value_type
            )
        return _end_value(model, ends[place], field, live=live)

    conditions: list[Any] = [
        relations.c.relation_type_key == config.relationTypeKey,
        from_end.c.object_type_key == config.fromObjectTypeKey,
        to_end.c.object_type_key == config.toObjectTypeKey,
    ]
    if from_object_id:
        conditions.append(relations.c.from_object_id == from_object_id)
    if to_object_id:
        conditions.append(relations.c.to_object_id == to_object_id)
    if search:
        conditions.append(
            or_(
                from_end.c.name.icontains(search, autoescape=True),
                to_end.c.name.icontains(search, autoescape=True),
            )
        )

    normalized: list[dict[str, str]] = []
    for ref, operator, lexical in field_filters:
        if ref not in config.filterFields:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"'{ref}' is not one of the view's filterFields",
                {"path": f"/query/filter.{ref}.{operator}"},
            )
        if operator != "eq":
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Operator '{operator}' is not supported on a relationships table; use eq",
                {"path": f"/query/filter.{ref}.{operator}"},
            )
        value, kind = value_of(ref)
        try:
            parsed = parse_typed(kind, lexical)
        except ValueError:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Invalid {kind} value for '{ref}'",
                {"path": f"/query/filter.{ref}.{operator}"},
            ) from None
        conditions.append(value == literal(parsed, value.type))
        normalized.append({"field": ref, "operator": operator, "value": _format(parsed)})
    normalized.sort(key=lambda item: (item["field"], item["value"]))

    join = relations.join(from_end, from_end.c.id == relations.c.from_object_id).join(
        to_end, to_end.c.id == relations.c.to_object_id
    )
    keys: list[SortKey] = []
    selected: list[Any] = [
        relations.c.id.label("relation_id"),
        relations.c.version.label("relation_version"),
        relations.c.attributes.label("relation_attributes"),
        relations.c.relation_type_key,
        relations.c.from_object_id,
        relations.c.to_object_id,
        from_end.c.id.label("from_id"),
        to_end.c.id.label("to_id"),
    ]

    def add_key(name: str, column: Any, parse: Callable[[str], Any], *, down: bool = False) -> None:
        label = f"sort_{len(keys)}"
        selected.append(column.label(label))
        keys.append(
            SortKey(
                name=name,
                column=column,
                attribute=label,
                descending=down,
                parse=parse,
                format=_format,
            )
        )

    group_column = None
    if config.groupBy:
        group_end = ends[config.groupBy]
        group_column = group_end.c.id
        add_key("group", group_end.c.name, str)
        add_key("groupId", group_end.c.id, str)

    token = sort or config.defaultSort
    ref, down = descending(token)
    if ref not in config.sortFields:
        raise api_error(
            422,
            "INVALID_SORT",
            f"'{ref}' is not one of the view's sortFields",
            {"path": "/query/sort"},
        )
    column, kind = value_of(ref)
    neutral = literal(_NEUTRAL[kind], column.type)

    def parse(raw: str, kind: str = kind) -> Any:
        return parse_typed(kind, raw)

    # Records without a value come last whichever way the values run.
    add_key(f"{ref}:null", case((column.is_(None), 1), else_=0), int)
    add_key(ref, func.coalesce(column, neutral), parse, down=down)
    first_value = len(keys) - 1
    add_key("relation", relations.c.id, str)

    statement = select(*selected).select_from(join).where(*conditions)
    group_rows = (
        select(group_column.label("group_id"), func.count().label("rows"))
        .select_from(join)
        .where(*conditions)
        .group_by(group_column)
        if group_column is not None
        else None
    )
    rank = keys[first_value - 1]
    value_key = keys[first_value]

    def seek(raw: str) -> Any:
        """At or after a value of the first thing the list orders by: the group's name when
        grouped, else the sort field's value (records without one come last)."""
        if config.groupBy:
            group_name = keys[0]
            return (
                group_name.column >= raw if not group_name.descending else group_name.column <= raw
            )
        try:
            value = value_key.parse(raw)
        except ValueError:
            raise api_error(
                422,
                "INVALID_SEEK",
                "Seek value is invalid for the list's sort",
                {"path": "/query/seek"},
            ) from None
        bound = literal(value, value_key.column.type)
        past = value_key.column <= bound if value_key.descending else value_key.column >= bound
        return and_(rank.column == 0, past)

    return RelationTableQuery(
        statement=statement,
        keys=tuple(keys),
        filters={
            "relationTypeKey": config.relationTypeKey,
            "fromObjectId": from_object_id,
            "toObjectId": to_object_id,
            "search": search,
            "filters": normalized,
            "groupBy": config.groupBy,
        },
        seek=seek,
        group_rows=group_rows,
        group_column=group_column,
    )


def group_counts(
    query: RelationTableQuery, session: Session, group_ids: list[str]
) -> dict[str, int]:
    """How many rows each of the groups holds under the request's filters, in one statement."""
    if query.group_rows is None or not group_ids:
        return {}
    statement = query.group_rows.where(query.group_column.in_(group_ids))
    return {group_id: count for group_id, count in session.execute(statement)}
