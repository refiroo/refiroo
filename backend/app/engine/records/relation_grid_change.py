"""One value set on many relationships of a relationships grid (0.13 RG).

The selection, the counts and the lists of what to change are read in PostgreSQL: the rows (the
ticked records, or every record the grid's filters select) crossed with the chosen column records,
left-joined to the binding's relationships in live data or a change set, then counted per outcome
in one statement and listed in another. What is written goes through the write unit as one batch
(``relation_batch.py``): the relationships whose value differs are updated, and with ``link_missing``
the pairs not related are related with that value, each decided over the batch lookup with the
rules of a single write, so any refusal refuses all and names the items. A change larger than
``ATOMIC_JOB_MAX_ITEMS`` is refused before anything is read into Python.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import JSON, and_, func, select, true, type_coerce
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...errors import ApiError, api_error
from ...models.schema import EngineModel
from ..model.relation_table import find_relation_table
from ..reads.object_query import parse_typed
from ..reads.relation_grid import RecordIds, build_relation_grid_query
from ..reads.relation_table import NEUTRAL, json_value, value_kind
from .batch_lookup import BatchLookup
from .relation_batch import RelationLink, RelationValues, decide_relation_values


@dataclass(frozen=True)
class GridChange:
    """What one grid change asks: the rows, the columns, the attribute and its value."""

    application_key: str
    view_key: str
    from_object_ids: list[str] | None
    to_object_ids: list[str]
    field_filters: list[tuple[str, str, str]]
    search: str | None
    attribute_type_key: str
    value: Any
    link_missing: bool
    except_ids: list[str] | None = None


@dataclass(frozen=True)
class GridChangePlan:
    """The counts of the outcomes and, when the plan was asked to collect, what to write."""

    change: int
    same: int
    missing: int
    updates: list[RelationValues]
    links: list[RelationLink]

    @property
    def linked(self) -> int:
        return len(self.links)


def _lexical(value: Any) -> str:
    """A JSON scalar as the lexical form ``parse_typed`` reads."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    raise ValueError("not a scalar value")


def plan_grid_change(
    session: Session,
    model: EngineModel,
    change: GridChange,
    objects: Subquery,
    relations: Subquery,
    *,
    live: bool,
    record_ids: RecordIds,
    max_items: int,
    collect: bool,
) -> GridChangePlan:
    """Count the relationships that change, already hold the value and are missing; with
    ``collect`` also list the ones to update and the pairs to link (when ``link_missing``).

    Refused before anything is listed: ``422 INVALID_GRID_CHANGE`` for an attribute the binding
    does not declare or that is not scalar, a value of the wrong type, or ends of the wrong type;
    ``413 BATCH_TOO_LARGE`` above ``max_items`` relationships to write.
    """
    config = find_relation_table(model, change.application_key, change.view_key)
    binding = model.allowed_relation(
        config.relationTypeKey, config.fromObjectTypeKey, config.toObjectTypeKey
    )
    key = change.attribute_type_key
    if binding is None or key not in binding.attributeTypeKeys:
        raise api_error(
            422,
            "INVALID_GRID_CHANGE",
            f"'{key}' is not an attribute of the relationship that the binding declares",
            {"path": "/attributeTypeKey"},
        )
    value_type = model.attribute_type(key).valueType
    kind = value_kind(value_type)
    if kind not in NEUTRAL:
        raise api_error(
            422,
            "INVALID_GRID_CHANGE",
            f"'{key}' holds {value_type} values; a grid sets scalar values only",
            {"path": "/attributeTypeKey"},
        )
    typed: Any = None
    if change.value is not None:
        try:
            typed = parse_typed(kind, _lexical(change.value))
        except ValueError:
            raise api_error(
                422,
                "INVALID_GRID_CHANGE",
                f"The value is not a valid {value_type} for '{key}'",
                {"path": "/value"},
            ) from None

    to_ids = list(dict.fromkeys(change.to_object_ids))
    _require_type(session, objects, to_ids, config.toObjectTypeKey, "toObjectIds")
    if change.from_object_ids is not None:
        from_ids = list(dict.fromkeys(change.from_object_ids))
        _require_type(session, objects, from_ids, config.fromObjectTypeKey, "fromObjectIds")
        rows = select(objects.c.id).where(objects.c.id.in_(from_ids)).subquery("grid_pick")
    else:
        query = build_relation_grid_query(
            model,
            config,
            objects,
            relations,
            live=live,
            application_key=change.application_key,
            record_ids=record_ids,
            to_object_ids=to_ids,
            field_filters=change.field_filters,
            search=change.search,
            sort=None,
        )
        rows = (
            select(
                query.rows_for(to_ids, change.except_ids)
                .statement.subquery("grid_rows")
                .c.from_id.label("id")
            )
        ).subquery("grid_pick")
    columns = select(objects.c.id).where(objects.c.id.in_(to_ids)).subquery("grid_columns")
    held = relations.alias("grid_held")
    value = json_value(type_coerce(held.c.attributes, JSON), key, value_type)
    holds = value.is_(None) if typed is None else value.is_not_distinct_from(typed)
    source = rows.join(columns, true()).outerjoin(
        held,
        and_(
            held.c.relation_type_key == config.relationTypeKey,
            held.c.from_object_id == rows.c.id,
            held.c.to_object_id == columns.c.id,
        ),
    )
    counts = session.execute(
        select(
            func.count().filter(held.c.id.is_(None)).label("missing"),
            func.count().filter(and_(held.c.id.is_not(None), holds)).label("same"),
            func.count().filter(and_(held.c.id.is_not(None), ~holds)).label("change"),
        ).select_from(source)
    ).one()
    writes = counts.change + (counts.missing if change.link_missing else 0)
    if writes > max_items:
        raise api_error(
            413,
            "BATCH_TOO_LARGE",
            f"The change would write {writes} relationships; at most {max_items} are written "
            "in one request",
            {"setting": "ATOMIC_JOB_MAX_ITEMS", "maximum": max_items, "items": writes},
        )
    updates: list[RelationValues] = []
    links: list[RelationLink] = []
    if collect:
        values = {key: change.value}
        updates = [
            RelationValues(row.id, row.version, dict(values))
            for row in session.execute(
                select(held.c.id, held.c.version)
                .select_from(source)
                .where(held.c.id.is_not(None), ~holds)
                .order_by(held.c.id)
            )
        ]
        if change.link_missing:
            attributes = {} if change.value is None else values
            links = [
                RelationLink(config.relationTypeKey, row.from_id, row.to_id, dict(attributes))
                for row in session.execute(
                    select(rows.c.id.label("from_id"), columns.c.id.label("to_id"))
                    .select_from(source)
                    .where(held.c.id.is_(None))
                    .order_by(rows.c.id, columns.c.id)
                )
            ]
    return GridChangePlan(counts.change, counts.same, counts.missing, updates, links)


def _require_type(
    session: Session, objects: Subquery, ids: list[str], type_key: str, name: str
) -> None:
    """Every id names a record of ``type_key`` in the context."""
    found = set(
        session.scalars(
            select(objects.c.id).where(objects.c.id.in_(ids), objects.c.object_type_key == type_key)
        )
    )
    absent = [item for item in ids if item not in found]
    if absent:
        raise api_error(
            422,
            "INVALID_GRID_CHANGE",
            f"{len(absent)} of the records are not '{type_key}' records of this workspace",
            {"path": f"/{name}", "objectIds": absent[:20]},
        )


@dataclass(frozen=True)
class GridChangeResult:
    """The plan and, on a dry run, what the write would be refused for."""

    plan: GridChangePlan
    refused: list[dict[str, Any]]


def decide_grid_change(
    lookup: BatchLookup, model: EngineModel, plan: GridChangePlan, *, collect: bool
) -> list[dict[str, Any]]:
    """Decide the plan's updates and links over ``lookup``. A refusal raises
    ``RELATION_BATCH_REFUSED`` (nothing is written); with ``collect`` (a dry run) the refused
    items are returned instead."""
    try:
        decide_relation_values(lookup, model, plan.updates, plan.links)
    except ApiError as error:
        if not collect or error.code != "RELATION_BATCH_REFUSED":
            raise
        return list(error.details["items"])
    return []
