"""A relationships grid's rows and column groups: filter, sort and count in SQL (0.13 RG).

The grid is a layout of a ``relationTable`` view: every record of the ``from`` type that matches
the ``from:`` filters and the search is one row (linked or not), and every record of the ``to``
type that matches the ``to:`` filters and the viewer's pick is one column group, at most
:data:`COLUMN_CAP` of them. A ``relation:<attribute>`` filter keeps the rows with a relationship to
a shown column record whose value equals the filter's. The rows page by cursor and are ordered by a
``from:`` sort field (any other sort field falls back to the record's name), records without a
value last, closed by the record's ID. Live, change set and publication reads share the mapping
projections (``mapping_projection.py``), as the rows layout does.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import JSON, Select, and_, case, exists, func, literal, select, type_coerce
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import SortKey
from ...errors import api_error
from ...models.database import RdmObject
from ...models.schema import EngineModel, RelationTableViewConfig
from ..model.candidates import filter_operators
from ..model.related_columns import is_related_field
from ..model.relation_table import descending, grid_filter_fields, split_ref
from .model_query import list_relation_filters, split_relation_filters
from .object_query import Day, build_object_query, escape_like, parse_filter_value, parse_typed
from .relation_table import (
    NEUTRAL,
    end_value,
    format_value,
    json_value,
    value_kind,
)
from .snapshot_reads import build_snapshot_object_query, change_set_context, publication_context

# Selects the IDs of the records of a type that the object list's filters keep.
RecordIds = Callable[[str, list[tuple[str, str, str]], str | None], Select[Any]]


def record_ids_selector(
    session: Session,
    model: EngineModel,
    *,
    workspace_key: str,
    change_set_id: str | None,
    publication_id: str | None,
) -> RecordIds:
    """The grid's ends are records of two types, so each end is selected by the filters the object
    list takes for that type (typed operators, ``related:``), live, in a change set or in a
    publication: the same validation, the same errors (0.13 RG)."""
    context = (
        change_set_context(session, change_set_id)
        if change_set_id
        else publication_context(session, publication_id)
        if publication_id
        else None
    )

    def select_ids(
        object_type_key: str, filters: list[tuple[str, str, str]], search: str | None
    ) -> Select[Any]:
        related, typed = split_relation_filters(filters)
        id_filter = list_relation_filters(
            model, object_type_key, related, workspace_key=workspace_key, context=context
        ).id_filter
        if context is None:
            query = build_object_query(
                model,
                object_type_key=object_type_key,
                application_key=None,
                workspace_key=workspace_key,
                parent_object_id=None,
                search=search,
                sort=None,
                field_filters=typed,
                id_filter=id_filter,
                session=session,
            )
            return query.statement.with_only_columns(RdmObject.id)
        snapshot = build_snapshot_object_query(
            model,
            context,
            object_type_key=object_type_key,
            application_key=None,
            parent_object_id=None,
            search=search,
            sort=None,
            field_filters=typed,
            id_filter=id_filter,
            session=session,
        )
        return select(snapshot.statement.subquery().c.object_id)

    return select_ids


# Fields every list offers without declaring them (live data records the two stamps).
_ALWAYS_OFFERED = frozenset({"createdAt", "updatedAt"})


def _relation_condition(
    model: EngineModel, relation: Any, field: str, operator: str, lexical: str
) -> Any:
    """One filter on a relationship's attribute, with the operators the attribute's type takes."""
    definition = model.attribute_type(field)
    value_type = definition.valueType
    parameter = f"filter.relation:{field}.{operator}"
    if operator not in filter_operators(value_type, attribute=True):
        raise api_error(
            422,
            "INVALID_FILTER",
            f"Operator '{operator}' is not supported for field '{field}'",
            {"path": f"/query/{parameter}"},
        )
    value = parse_filter_value(value_type, operator, lexical, f"relation:{field}")
    column = json_value(type_coerce(relation.c.attributes, JSON), field, value_type)
    if operator in {"isNull", "isUnset"}:
        return column.is_(None) if value else column.is_not(None)
    if isinstance(value, Day):
        start, end = value.bounds()
        return {
            "eq": and_(column >= start, column < end),
            "lt": column < start,
            "lte": column < end,
            "gt": column >= end,
            "gte": column >= start,
        }[operator]
    if operator == "contains":
        return column.ilike(f"%{escape_like(value)}%", escape="\\")
    if operator == "startsWith":
        return column.ilike(f"{escape_like(value)}%", escape="\\")
    return {
        "eq": column == value,
        "lt": column < value,
        "lte": column <= value,
        "gt": column > value,
        "gte": column >= value,
    }[operator]


# The most column groups one read shows; the answer says how many there are in all.
COLUMN_CAP = 50
_FALLBACK_SORT = "from:name"


@dataclass(frozen=True)
class GridQuery:
    """The statements of one grid read.

    ``columns`` selects the column records (``id``, ``name``) in name order and ``column_total``
    counts them. Rows depend on the shown columns (a relationship filter reads them), so
    ``rows_for`` builds them once the columns are known.
    """

    columns: Select[Any]
    column_total: Select[Any]
    rows_for: Callable[..., GridRows]


@dataclass(frozen=True)
class GridRows:
    """The page source and its keyset, the count of rows under the request's filters, and per
    shown column record how many of those rows are related to it."""

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    seek: Callable[[str], Any]
    row_total: Select[Any]
    linked: Select[Any]
    filters: dict[str, Any]


def build_relation_grid_query(
    model: EngineModel,
    config: RelationTableViewConfig,
    objects: Subquery,
    relations: Subquery,
    *,
    live: bool,
    application_key: str,
    record_ids: RecordIds,
    to_object_ids: list[str],
    field_filters: list[tuple[str, str, str]],
    search: str | None,
    to_search: str | None = None,
    sort: str | None,
) -> GridQuery:
    from_end, to_end = objects.alias("grid_from"), objects.alias("grid_to")
    match = relations.alias("grid_match")
    ends = {"from": from_end, "to": to_end}

    def value_of(ref: str) -> tuple[Any, str]:
        parts = split_ref(ref)
        assert parts is not None  # the model's validation holds every field of the view
        place, field = parts
        if place == "relation":
            value_type = model.attribute_type(field).valueType
            return json_value(type_coerce(match.c.attributes, JSON), field, value_type), value_kind(
                value_type
            )
        return end_value(model, ends[place], field, live=live)

    allowed = grid_filter_fields(model, application_key, config)
    # A record's fields are the object list's filters, with its operators and refusals; a
    # relationship's value is compared as typed, with the operators its type takes.
    ends_filters: dict[str, list[tuple[str, str, str]]] = {"from": [], "to": []}
    relation_filters: list[tuple[str, str, str]] = []
    for ref, operator, lexical in field_filters:
        place = split_ref(ref)
        offered = place is not None and (
            ref in allowed
            or (place[0] != "relation" and place[1] in _ALWAYS_OFFERED)
            or (place[0] != "relation" and is_related_field(place[1]))
        )
        if not offered:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"'{ref}' is not one of the view's filterFields",
                {"path": f"/query/filter.{ref}.{operator}"},
            )
        assert place is not None
        if place[0] == "relation":
            relation_filters.append((place[1], operator, lexical))
        else:
            ends_filters[place[0]].append((place[1], operator, lexical))
    relation_conditions = [
        _relation_condition(model, match, field, operator, lexical)
        for field, operator, lexical in relation_filters
    ]
    normalized = sorted(
        [
            {"field": f"{place}:{field}", "operator": operator, "value": value}
            for place, entries in (*ends_filters.items(), ("relation", relation_filters))
            for field, operator, value in entries
        ],
        key=lambda item: (item["field"], item["operator"], item["value"]),
    )
    by_place: dict[str, list[Any]] = {"from": [], "to": [], "relation": relation_conditions}
    for place, end, text in (("from", from_end, search), ("to", to_end, to_search)):
        if ends_filters[place] or text:
            type_key = config.fromObjectTypeKey if place == "from" else config.toObjectTypeKey
            by_place[place].append(end.c.id.in_(record_ids(type_key, ends_filters[place], text)))

    column_conditions: list[Any] = [to_end.c.object_type_key == config.toObjectTypeKey]
    column_conditions.extend(by_place["to"])
    if to_object_ids:
        column_conditions.append(to_end.c.id.in_(to_object_ids))
    columns = (
        select(to_end.c.id, to_end.c.name)
        .where(*column_conditions)
        .order_by(to_end.c.name, to_end.c.id)
    )
    column_total = select(func.count()).select_from(to_end).where(*column_conditions)

    token = sort or config.defaultSort
    ref, down = descending(token)
    if ref not in config.sortFields:
        raise api_error(
            422,
            "INVALID_SORT",
            f"'{ref}' is not one of the view's sortFields",
            {"path": "/query/sort"},
        )
    if not ref.startswith("from:"):
        ref, down = _FALLBACK_SORT, False
    sort_place = split_ref(ref)
    assert sort_place is not None
    sort_field = sort_place[1]

    base_filters = {
        "relationTypeKey": config.relationTypeKey,
        "search": search,
        "toSearch": to_search,
        "filters": normalized,
        "toObjectIds": sorted(to_object_ids),
        "sort": f"-{ref}" if down else ref,
    }

    def rows_for(shown: list[str], except_ids: list[str] | None = None) -> GridRows:
        conditions: list[Any] = [from_end.c.object_type_key == config.fromObjectTypeKey]
        conditions.extend(by_place["from"])
        if except_ids:
            conditions.append(from_end.c.id.not_in(except_ids))
        if by_place["relation"]:
            conditions.append(
                exists(
                    select(literal(1)).where(
                        match.c.relation_type_key == config.relationTypeKey,
                        match.c.from_object_id == from_end.c.id,
                        match.c.to_object_id.in_(shown or [""]),
                        and_(*by_place["relation"]),
                    )
                )
            )
        keys: list[SortKey] = []
        selected: list[Any] = [from_end.c.id.label("from_id")]

        def add_key(
            name: str, column: Any, parse: Callable[[str], Any], *, descend: bool = False
        ) -> None:
            label = f"sort_{len(keys)}"
            selected.append(column.label(label))
            keys.append(
                SortKey(
                    name=name,
                    column=column,
                    attribute=label,
                    descending=descend,
                    parse=parse,
                    format=format_value,
                )
            )

        column, kind = end_value(model, from_end, sort_field, live=live)
        neutral = literal(NEUTRAL[kind], column.type)

        def parse(raw: str, kind: str = kind) -> Any:
            return parse_typed(kind, raw)

        # Records without a value come last whichever way the values run.
        add_key(f"{ref}:null", case((column.is_(None), 1), else_=0), int)
        add_key(ref, func.coalesce(column, neutral), parse, descend=down)
        add_key("record", from_end.c.id, str)
        rank, value_key = keys[0], keys[1]

        def seek(raw: str) -> Any:
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

        links = relations.alias("grid_links")
        return GridRows(
            statement=select(*selected).select_from(from_end).where(*conditions),
            keys=tuple(keys),
            seek=seek,
            row_total=select(func.count()).select_from(from_end).where(*conditions),
            linked=select(links.c.to_object_id.label("to_id"), func.count().label("rows"))
            .select_from(links.join(from_end, from_end.c.id == links.c.from_object_id))
            .where(
                links.c.relation_type_key == config.relationTypeKey,
                links.c.to_object_id.in_(shown or [""]),
                *conditions,
            )
            .group_by(links.c.to_object_id),
            filters={**base_filters, "shown": sorted(shown)},
        )

    return GridQuery(columns, column_total, rows_for)
