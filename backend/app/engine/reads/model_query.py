"""Model-aware object query (Base 0.9 Q3, INTEGRATION_API §Q3, D4, D17–D19).

``POST /workspaces/{key}/queries/objects`` lists one object type's records in live, change set and
publication contexts. It answers through the per-type list's builders, so a criterion the list can
express selects the same records in the same order, pages the same way and has the same meaning
in every context. The query adds what query parameters cannot carry, each as a set the listed record's ID or parent
ID must be in (:class:`SetFilter`), which the builders apply to every part of a change set's union:

* ``ancestor:<type>`` with ``eq`` on an ancestor's ID, read from the containment path: the records
  under that ancestor at any depth, as those whose parent is the ancestor or one of the containers
  below it. The walk goes down from the ancestor through containers only.
* ``ancestor:<type>.<field>`` (0.9 K7, D178): the records under an ancestor of that type whose
  field meets the criterion, by the list's operators. Criteria on one ancestor type are met by one
  ancestor; the walk starts from every ancestor that meets them.
* one ``related`` hop: records with at least one record at the other end of a binding that matches
  the hop's own criteria (``not`` inverts it). It reads the binding's relations once, as a set,
  never once per listed record.

Every name in the body is checked against the model before anything runs, and a name the model
does not give the queried type is refused as ``INVALID_QUERY`` at its JSON pointer (D19).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, NoReturn

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import aliased

from ...errors import ApiError, api_error
from ...models.database import ObjectRelation, RdmObject
from ...models.queries import ModelQuery, QueryCriterion, QueryExpansion, RelatedCriterion
from ...models.schema import CandidateCriterion, EngineModel, ObjectTypeDefinition
from ..model.candidates import filter_operators
from ..model.consumer_contract import split_ancestor_reference
from ..model.related_columns import (
    RELATED_FIELD_PREFIX,
    RelatedKeyError,
    is_related_field,
    related_column,
    related_field_column,
)
from ..model.traversal import ancestor_type_keys, related_object_types
from ..model.validation.fields import ANCESTOR_FIELD_PREFIX
from .object_query import (
    LIVE_OBJECT_COLUMNS,
    ObjectColumns,
    ObjectQuery,
    filter_value_type,
    parse_filter_value,
    refine_object_query,
    require_effective_period,
    typed_filter_predicates,
)
from .snapshot_reads import (
    UNRECORDED_TIMESTAMPS,
    SnapshotContext,
    object_projection,
    relation_projection,
    snapshot_object_columns,
    snapshot_object_query,
)

# The fields of an ancestor a criterion may compare besides its attributes (0.9 K7).
ANCESTOR_FILTER_FIELDS = ("name",)
# Built-in fields a criterion may name, on the queried records and at the other end of a hop.
FILTER_FIELDS = ("id", "name", "parentObjectId", "createdAt", "updatedAt")
# Built-in fields ``select`` may name besides attributes and ``ancestor:<type>``; every item also
# carries ``id``, ``objectTypeKey`` and ``version``.
SELECT_FIELDS = (
    "name",
    "workspaceKey",
    "applicationKey",
    "parentObjectId",
    "path",
    "createdAt",
    "updatedAt",
)
ALWAYS_SELECTED = ("id", "objectTypeKey", "version")


@dataclass(frozen=True)
class Expansion:
    """One ``expand`` entry, checked against the model."""

    relation_type_key: str
    direction: str
    select: tuple[str, ...] | None
    limit: int
    # The per-type list's field of each related record beside its name (0.9 K5a); Q3 names none.
    field: str | None = None


@dataclass(frozen=True)
class SetFilter:
    """A criterion as a set the listed record's ID or parent ID must (or, inverted, must not) be in."""

    column: str  # "id" or "parent"
    predicate: Callable[[Any], Any]


@dataclass(frozen=True)
class ModelQueryPlan:
    """The query's statement, keyset and cursor filters, and what each item returns."""

    query: ObjectQuery
    scope: str
    select: tuple[str, ...] | None
    expansions: tuple[Expansion, ...]


def query_scope(context: SnapshotContext | None) -> str:
    """The cursor scope, distinct from every list's, so no list accepts a query's cursors."""
    if context is None:
        return "object-query"
    return "object-query-change-set" if context.kind == "change_set" else "object-query-publication"


def plan_model_query(
    model: EngineModel,
    request: ModelQuery,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> ModelQueryPlan:
    """Check the query against the model and build its statement in the context (live when ``None``)."""
    object_type = model.object_type(request.objectTypeKey)
    if object_type is None:
        _invalid(f"Unknown object type '{request.objectTypeKey}'", "/objectTypeKey")
    as_of = _as_of(object_type, request.asOf)
    field_filters: list[tuple[str, str, str]] = []
    sets: list[SetFilter] = []
    ancestor_fields: list[tuple[QueryCriterion, str]] = []
    for index, criterion in enumerate(request.where):
        pointer = f"/where/{index}"
        if criterion.related is not None:
            sets.append(
                _related_predicate(model, object_type, criterion, pointer, workspace_key, context)
            )
        elif is_ancestor_field(criterion.field):
            ancestor_fields.append((criterion, pointer))
        elif criterion.field is not None and criterion.field.startswith(ANCESTOR_FIELD_PREFIX):
            sets.append(
                _ancestor_predicate(model, object_type, criterion, pointer, workspace_key, context)
            )
        else:
            field_filters.append(_field_filter(model, (object_type,), criterion, pointer, context))
    sets.extend(
        ancestor_field_sets(model, object_type, ancestor_fields, workspace_key=workspace_key, context=context)
    )
    _check_sort(request.sort)
    select_fields = (
        None if request.select is None else _selected(model, (object_type,), request.select, "/select")
    )
    expansions = _expansions(model, object_type, request.expand)

    options = {
        "sort": request.sort,
        "field_filters": field_filters,
        "id_filter": _combined(sets, "id"),
        "parent_filter": _combined(sets, "parent"),
        "as_of": as_of,
    }
    try:
        if context is None:
            query = _live_query(model, object_type, workspace_key, **options)
        else:
            query = _snapshot_query(model, object_type, context, **options)
    except ApiError as error:
        if error.code != "INVALID_SORT":
            raise
        _invalid(error.message, "/sort")
    owner = (
        {"workspaceKey": workspace_key}
        if context is None
        else {"changeSetId" if context.kind == "change_set" else "publicationId": context.id}
    )
    return ModelQueryPlan(
        query=replace(query, filters={**owner, "query": request.criteria()}),
        scope=query_scope(context),
        select=select_fields,
        expansions=expansions,
    )


def _live_query(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    workspace_key: str,
    *,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
    id_filter: Callable[[Any], Any] | None,
    parent_filter: Callable[[Any], Any] | None,
    as_of: date | None,
) -> ObjectQuery:
    """The live statement."""
    statement = select(RdmObject).where(
        RdmObject.object_type_key == object_type.key,
        RdmObject.workspace_key == workspace_key,
    )
    if id_filter is not None:
        statement = statement.where(id_filter(RdmObject.id))
    if parent_filter is not None:
        statement = statement.where(parent_filter(RdmObject.parent_object_id))
    statement, keys, seek, _normalized = refine_object_query(
        model,
        _live_columns(RdmObject),
        statement,
        object_types=(object_type,),
        search=None,
        sort=sort,
        field_filters=field_filters,
        as_of=as_of,
    )
    return ObjectQuery(statement=statement, keys=keys, filters={}, seek=seek)


def _snapshot_query(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    context: SnapshotContext,
    *,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
    id_filter: Callable[[Any], Any] | None,
    parent_filter: Callable[[Any], Any] | None,
    as_of: date | None,
) -> ObjectQuery:
    return snapshot_object_query(
        model,
        context,
        object_types=(object_type,),
        narrowing={"object_type_key": object_type.key},
        filters={},
        search=None,
        sort=sort,
        field_filters=field_filters,
        id_filter=id_filter,
        parent_filter=parent_filter,
        builtin=lambda projection: {"parentObjectId": projection.c.parent_object_id},
        as_of=as_of,
    )


def _combined(sets: Sequence[SetFilter], column: str) -> Callable[[Any], Any] | None:
    """The sets on ``column`` as one predicate, or ``None`` when there are none."""
    predicates = [item.predicate for item in sets if item.column == column]
    if not predicates:
        return None
    return lambda value: and_(*(predicate(value) for predicate in predicates))


def _live_columns(record: Any) -> ObjectColumns:
    """The live list's columns for ``record`` (``RdmObject`` or an alias), with ``parentObjectId``."""
    if record is RdmObject:
        return replace(
            LIVE_OBJECT_COLUMNS,
            builtin={**LIVE_OBJECT_COLUMNS.builtin, "parentObjectId": RdmObject.parent_object_id},
        )
    return replace(
        LIVE_OBJECT_COLUMNS,
        source=record,
        id=record.id,
        name=record.name,
        value_match=lambda values: (values.object_id == record.id,),
        builtin={
            "id": record.id,
            "name": record.name,
            "parentObjectId": record.parent_object_id,
            "createdAt": record.created_at,
            "updatedAt": record.updated_at,
        },
        search_values=None,
    )


def _field_filter(
    model: EngineModel,
    object_types: Sequence[ObjectTypeDefinition],
    criterion: QueryCriterion,
    pointer: str,
    context: SnapshotContext | None,
    *,
    capability: str | None = "filterable",
) -> tuple[str, str, str]:
    """A field criterion as the list's ``(field, operator, lexical value)``, checked as the list
    checks it and refused at the part of the criterion that is wrong. ``capability`` as
    :func:`typed_filter_predicates` takes it."""
    if criterion.not_:
        _invalid("'not' applies to a related criterion only", f"{pointer}/not")
    if criterion.field is None:
        _invalid("A criterion names a field or a related hop", f"{pointer}/field")
    if criterion.op is None:
        _invalid(f"Criterion on '{criterion.field}' has no operator", f"{pointer}/op")
    field, operator = criterion.field, criterion.op
    if context is not None and field in UNRECORDED_TIMESTAMPS:
        _invalid(
            f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in change sets or publications",
            f"{pointer}/field",
        )
    builtin = dict.fromkeys(FILTER_FIELDS)
    try:
        value_type, is_attribute = filter_value_type(
            model, builtin, object_types, field, capability=capability
        )
    except ApiError as error:
        _invalid(error.message, f"{pointer}/field")
    if operator not in filter_operators(value_type, attribute=is_attribute):
        _invalid(f"Operator '{operator}' is not supported for field '{field}'", f"{pointer}/op")
    lexical = _lexical(value_type, operator, criterion.value, field, f"{pointer}/value")
    try:
        parse_filter_value(value_type, operator, lexical, field)
    except ApiError as error:
        _invalid(error.message, f"{pointer}/value")
    return field, operator, lexical


def _lexical(value_type: str, operator: str, value: Any, field: str, pointer: str) -> str:
    """A JSON value as the list's lexical form, when its JSON type suits the field's value type.

    ``isNull`` and ``isUnset`` take a boolean; text and dates a string; integers an integer;
    decimals a number or a decimal string; booleans a boolean. The list then parses it as its own.
    """
    if operator in {"isNull", "isUnset"} or value_type == "boolean":
        if isinstance(value, bool):
            return "true" if value else "false"
        expected = "true or false"
    elif value_type == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        expected = "an integer"
    elif value_type == "decimal":
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            return str(value)
        expected = "a number"
    else:
        if isinstance(value, str):
            return value
        expected = "a string"
    _invalid(f"Criterion '{field} {operator}' needs {expected}", pointer)


def _ancestor_predicate(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    criterion: QueryCriterion,
    pointer: str,
    workspace_key: str,
    context: SnapshotContext | None,
) -> SetFilter:
    """Records under the ancestor ``value`` of type ``<type>``, at any depth (``ancestor:<type>``).

    Any ancestor of that type counts, so a type that nests matches at each of its levels. The
    walk collects the containers: the ancestor and the records below it of the types that can
    stand between it and the queried type. A record is under the ancestor when its parent is one
    of them, so the walk reads containers only, never the records listed (20,000 items under one
    group: a walk of their few containers, not of every item).
    """
    field = criterion.field or ""
    ancestor_type_key = field.removeprefix(ANCESTOR_FIELD_PREFIX)
    if criterion.not_:
        _invalid("'not' applies to a related criterion only", f"{pointer}/not")
    if ancestor_type_key not in ancestor_type_keys(model, object_type.key):
        _invalid(
            f"Object type '{object_type.key}' has no ancestor of type '{ancestor_type_key}'",
            f"{pointer}/field",
        )
    if criterion.op != "eq":
        _invalid(f"Field '{field}' supports eq on the ancestor's ID only", f"{pointer}/op")
    if not isinstance(criterion.value, str):
        _invalid(f"Criterion '{field} eq' needs the ancestor's ID as a string", f"{pointer}/value")
    ancestor_id = criterion.value
    if context is None:
        start = select(RdmObject.id.label("id")).where(
            RdmObject.id == ancestor_id,
            RdmObject.object_type_key == ancestor_type_key,
            RdmObject.workspace_key == workspace_key,
        )
    else:
        origin = object_projection(
            context, object_ids=[ancestor_id], object_type_key=ancestor_type_key
        )
        start = select(origin.c.object_id.label("id"))
    containers = _containers_below(
        model, object_type.key, ancestor_type_key, start, workspace_key=workspace_key, context=context
    )
    return SetFilter("parent", lambda column: column.in_(containers))


def _containers_below(
    model: EngineModel,
    object_type_key: str,
    ancestor_type_key: str,
    start: Select[Any],
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Select[Any]:
    """The ancestors ``start`` selects (as ``id``) and the containers below them of the types that
    can stand between ``ancestor_type_key`` and ``object_type_key``: a record of that type is under
    one of the ancestors when its parent is one of these."""
    through = sorted(
        key
        for key in ancestor_type_keys(model, object_type_key)
        if ancestor_type_key in ancestor_type_keys(model, key)
    )
    walk = start.cte("ancestor_descendants", recursive=True)
    if context is None:
        child = aliased(RdmObject, name="descendant")
        # UNION, not UNION ALL: a record met twice ends the walk, whatever the data holds. Each
        # step probes the (workspace, parent, type) index with the queued record.
        walk = walk.union(
            select(child.id)
            .select_from(walk)
            .join(child, child.parent_object_id == walk.c.id)
            .where(
                child.workspace_key == workspace_key,
                child.object_type_key.in_(through),
            )
        )
    else:
        children = object_projection(context, object_type_keys=through)
        walk = walk.union(
            select(children.c.object_id)
            .select_from(walk)
            .join(children, children.c.parent_object_id == walk.c.id)
        )
    return select(walk.c.id)


def is_ancestor_field(field: str | None) -> bool:
    """Whether ``field`` is ``ancestor:<type>.<field>``, a field of an ancestor (0.9 K7)."""
    return field is not None and split_ancestor_reference(field) not in (None, ("", ""))


def ancestor_field_sets(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    criteria: Sequence[tuple[QueryCriterion, str]],
    *,
    workspace_key: str,
    context: SnapshotContext | None,
    capability: str | None = "filterable",
) -> list[SetFilter]:
    """``ancestor:<type>.<field>`` criteria (0.9 K7, D178), each with its pointer, as one set per
    ancestor type: the records under an ancestor of that type meeting all of that type's criteria,
    at any depth. The ancestors are matched with the list's own predicates over the ancestor type,
    then walked down through containers only, so the listed records are never read one by one."""
    by_type: dict[str, list[tuple[str, str, str]]] = {}
    for criterion, pointer in criteria:
        if criterion.not_:
            _invalid("'not' applies to a related criterion only", f"{pointer}/not")
        reference = split_ancestor_reference(criterion.field or "")
        assert reference is not None
        ancestor_type_key, field = reference
        ancestor = model.object_type(ancestor_type_key)
        if ancestor is None or ancestor_type_key not in ancestor_type_keys(model, object_type.key):
            _invalid(
                f"Object type '{object_type.key}' has no ancestor of type '{ancestor_type_key}'",
                f"{pointer}/field",
            )
        if field not in ANCESTOR_FILTER_FIELDS and model.attribute_type(field) is None:
            _invalid(f"'{field}' is no field an ancestor criterion can compare", f"{pointer}/field")
        nested = criterion.model_copy(update={"field": field})
        by_type.setdefault(ancestor_type_key, []).append(
            _field_filter(model, (ancestor,), nested, pointer, context, capability=capability)
        )
    sets = []
    for ancestor_type_key, filters in by_type.items():
        ancestor = model.object_type(ancestor_type_key)
        assert ancestor is not None
        if context is None:
            other = aliased(RdmObject, name="matched_ancestor")
            _normalized, predicates = typed_filter_predicates(
                model, _live_columns(other), (ancestor,), filters, capability=capability
            )
            start = select(other.id.label("id")).where(
                other.object_type_key == ancestor_type_key,
                other.workspace_key == workspace_key,
                *predicates,
            )
        else:
            others = object_projection(context, object_type_keys=[ancestor_type_key])
            columns = snapshot_object_columns(others, context, search_index=False)
            _normalized, predicates = typed_filter_predicates(
                model, columns, (ancestor,), filters, capability=capability
            )
            start = select(others.c.object_id.label("id")).select_from(others).where(*predicates)
        containers = _containers_below(
            model, object_type.key, ancestor_type_key, start, workspace_key=workspace_key, context=context
        )
        sets.append(SetFilter("parent", lambda column, containers=containers: column.in_(containers)))
    return sets


def candidate_ids(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    criteria: Sequence[CandidateCriterion],
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Select[Any]:
    """The IDs (as ``id``) of the records of ``object_type`` that meet a binding end's candidate
    criteria in the context (0.9 K7, D177): its own fields with the list's predicates, any non-JSON
    attribute, and its ancestors' fields through :func:`ancestor_field_sets`. One statement; the
    candidate read narrows a list to it and the write rule asks which records it holds."""
    own: list[tuple[str, str, str]] = []
    ancestors: list[tuple[QueryCriterion, str]] = []
    for index, item in enumerate(criteria):
        criterion = QueryCriterion(field=item.field, op=item.op, value=item.value)
        if is_ancestor_field(criterion.field):
            ancestors.append((criterion, f"/{index}"))
        else:
            own.append(_field_filter(model, (object_type,), criterion, f"/{index}", context, capability=None))
    parents = [
        item.predicate
        for item in ancestor_field_sets(
            model, object_type, ancestors, workspace_key=workspace_key, context=context, capability=None
        )
    ]
    if context is None:
        record = aliased(RdmObject, name="candidate")
        _normalized, predicates = typed_filter_predicates(
            model, _live_columns(record), (object_type,), own, capability=None
        )
        return select(record.id.label("id")).where(
            record.object_type_key == object_type.key,
            record.workspace_key == workspace_key,
            *predicates,
            *(predicate(record.parent_object_id) for predicate in parents),
        )
    records = object_projection(context, object_type_keys=[object_type.key])
    columns = snapshot_object_columns(records, context, search_index=False)
    _normalized, predicates = typed_filter_predicates(model, columns, (object_type,), own, capability=None)
    return (
        select(records.c.object_id.label("id"))
        .select_from(records)
        .where(*predicates, *(predicate(records.c.parent_object_id) for predicate in parents))
    )


def _related_predicate(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    criterion: QueryCriterion,
    pointer: str,
    workspace_key: str,
    context: SnapshotContext | None,
) -> SetFilter:
    """Records with at least one record at the other end of the binding matching the hop's criteria.

    The other end's criteria are the list's, over the types the binding allows there (D18): built-in
    fields always, an attribute only where that is one type binding it as filterable.
    """
    hop = criterion.related
    assert hop is not None
    # By value, not by what was sent: an export's stored request carries every field, null ones too.
    if criterion.field is not None or criterion.op is not None or criterion.value is not None:
        _invalid("A related criterion names no field, operator or value", f"{pointer}/related")
    targets = _binding_targets(model, object_type, hop.relationTypeKey, hop.direction, f"{pointer}/related")
    criteria = []
    for index, nested in enumerate(hop.where):
        nested_pointer = f"{pointer}/related/where/{index}"
        if nested.related is not None:
            _invalid("A related criterion takes no further hop", f"{nested_pointer}/related")
        if nested.field is not None and nested.field.startswith(ANCESTOR_FIELD_PREFIX):
            _invalid("A related criterion takes no ancestor criterion", f"{nested_pointer}/field")
        criteria.append(_field_filter(model, targets, nested, nested_pointer, context))
    target_keys = sorted(item.key for item in targets)
    if context is None:
        relation, other = aliased(ObjectRelation, name="hop_relation"), aliased(RdmObject, name="hop")
        anchor, far = _ends(relation.from_object_id, relation.to_object_id, hop.direction)
        _normalized, predicates = typed_filter_predicates(model, _live_columns(other), targets, criteria)
        matched = (
            select(anchor)
            .join(other, other.id == far)
            .where(
                relation.relation_type_key == hop.relationTypeKey,
                other.workspace_key == workspace_key,
                other.object_type_key.in_(target_keys),
                *predicates,
            )
        )
    else:
        relations = relation_projection(context, relation_type_keys=[hop.relationTypeKey])
        others = object_projection(context, object_type_keys=target_keys)
        anchor, far = _ends(relations.c.from_object_id, relations.c.to_object_id, hop.direction)
        columns = snapshot_object_columns(others, context, search_index=False)
        columns = replace(
            columns, builtin={**columns.builtin, "parentObjectId": others.c.parent_object_id}
        )
        _normalized, predicates = typed_filter_predicates(model, columns, targets, criteria)
        matched = (
            select(anchor)
            .select_from(relations)
            .join(others, others.c.object_id == far)
            .where(*predicates)
        )
    if criterion.not_:
        return SetFilter("id", lambda column: column.not_in(matched))
    return SetFilter("id", lambda column: column.in_(matched))


def _ends(from_column: Any, to_column: Any, direction: str) -> tuple[Any, Any]:
    """The queried record's end of a relation and the other end, for a hop in ``direction``."""
    return (from_column, to_column) if direction == "outgoing" else (to_column, from_column)


def _binding_targets(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    relation_type_key: str,
    direction: str,
    pointer: str,
) -> tuple[ObjectTypeDefinition, ...]:
    """The types a binding of the queried type allows at the other end; none refuses the binding."""
    if model.relation_type(relation_type_key) is None:
        _invalid(f"Unknown relation type '{relation_type_key}'", f"{pointer}/relationTypeKey")
    targets = related_object_types(model, object_type.key, direction, [relation_type_key])
    if not targets:
        _invalid(
            f"Object type '{object_type.key}' has no {direction} binding of relation type"
            f" '{relation_type_key}'",
            f"{pointer}/direction",
        )
    return targets


def _check_sort(sort: str | None) -> None:
    """The list's sorts; ``parentObjectId`` is a criterion here, not a sort."""
    if sort is not None and sort.removeprefix("-") == "parentObjectId":
        _invalid("Unknown sort field 'parentObjectId'", "/sort")


def _selected(
    model: EngineModel,
    object_types: Sequence[ObjectTypeDefinition],
    fields: Sequence[str],
    pointer: str,
) -> tuple[str, ...]:
    """``select`` checked against the types: built-ins, attributes one of them binds, ancestors."""
    bound = {item.attributeTypeKey for object_type in object_types for item in object_type.attributes}
    ancestors = set().union(*(ancestor_type_keys(model, item.key) for item in object_types))
    for index, field in enumerate(fields):
        known = (
            field in SELECT_FIELDS
            or field in ALWAYS_SELECTED
            or field in bound
            or (
                field.startswith(ANCESTOR_FIELD_PREFIX)
                and field.removeprefix(ANCESTOR_FIELD_PREFIX) in ancestors
            )
        )
        if not known:
            _invalid(f"Unknown field '{field}'", f"{pointer}/{index}")
    return tuple(dict.fromkeys(field for field in fields if field not in ALWAYS_SELECTED))


def _expansions(
    model: EngineModel, object_type: ObjectTypeDefinition, expand: Sequence[QueryExpansion]
) -> tuple[Expansion, ...]:
    result, seen = [], set()
    for index, item in enumerate(expand):
        pointer = f"/expand/{index}"
        targets = _binding_targets(model, object_type, item.relationTypeKey, item.direction, pointer)
        if (item.relationTypeKey, item.direction) in seen:
            _invalid(
                f"Relation type '{item.relationTypeKey}' ({item.direction}) is expanded twice",
                pointer,
            )
        seen.add((item.relationTypeKey, item.direction))
        select_fields = (
            None if item.select is None else _selected(model, targets, item.select, f"{pointer}/select")
        )
        result.append(Expansion(item.relationTypeKey, item.direction, select_fields, item.limit))
    return tuple(result)


# The per-type list's relation columns (0.9 K5, D142): each record shown by its name. Their number is
# bounded by the model, the relationships the type has, each named once (D142 revised in K6a).
LIST_EXPANSION_SELECT = ("name",)


def list_expansions(
    model: EngineModel, object_type_key: str, keys: Sequence[str], limit: int
) -> tuple[Expansion, ...]:
    """The per-type list's ``expand``: relation keys or reverse keys of the listed type, each read
    as Q3 reads an ``expand`` of that relation type and direction, its records narrowed to ``name``,
    and to a field beside it when the key names one (``<key>.<field>``, 0.9 K5a).
    """
    result: list[Expansion] = []
    for key in keys:
        if key in keys[: len(result)]:
            _invalid_expand(f"expand names '{key}' twice", key)
        try:
            column = related_field_column(model, object_type_key, key)
        except RelatedKeyError as error:
            _invalid_expand(str(error), key)
        result.append(
            Expansion(
                column.relation_type_key,
                column.direction,
                LIST_EXPANSION_SELECT,
                limit,
                column.field,
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class RelationFilters:
    """The per-type list's relationship filters (0.9 K6): one condition on the listed record's ID,
    and their normalized form, which a cursor binds."""

    id_filter: Callable[[Any], Any] | None
    normalized: tuple[tuple[str, str, str], ...]


def split_relation_filters(
    filters: Sequence[tuple[str, str, str]],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """The list's ``filter.<field>.<operator>`` parameters as (relationship filters, the others)."""
    related = [item for item in filters if is_related_field(item[0])]
    return related, [item for item in filters if not is_related_field(item[0])]


def list_relation_filters(
    model: EngineModel,
    object_type_key: str,
    filters: Sequence[tuple[str, str, str]],
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> RelationFilters:
    """``filter.related:<key>.eq=<id>`` (repeatable: related to any of them) and ``.isNull``
    (``true``: related to none, ``false``: to any), as conditions on the listed record's ID built by
    Q3's hop (D155, D156), so the list and the query mean the same in every context. Filters on one
    relationship are alternatives when they name records; different relationships combine with AND.
    Anything else is ``INVALID_FILTER``.
    """
    if not filters:
        return RelationFilters(None, ())
    object_type = model.object_type(object_type_key)
    if object_type is None:
        # The list refuses the unknown type itself (UNKNOWN_OBJECT_TYPE).
        return RelationFilters(None, ())
    by_key: dict[str, list[tuple[str, str]]] = {}
    for field, operator, value in filters:
        parameter = f"filter.{field}.{operator}"
        key = field.removeprefix(RELATED_FIELD_PREFIX)
        try:
            column = related_field_column(model, object_type_key, key)
        except RelatedKeyError as error:
            _invalid_filter(f"Cannot filter by '{field}': {error}", parameter)
        if column.field is not None or column.key != key:
            _invalid_filter(
                f"Cannot filter by '{field}': a relationship filter names the relationship, not a"
                " field of its records",
                parameter,
            )
        if operator not in {"eq", "isNull"}:
            _invalid_filter(
                f"Operator '{operator}' is not supported for relationship '{key}': eq or isNull",
                parameter,
            )
        if operator == "isNull" and value not in {"true", "false"}:
            _invalid_filter(f"isNull takes true or false, not '{value}'", parameter)
        by_key.setdefault(key, []).append((operator, value))
    conditions = []
    for key, items in by_key.items():
        column = related_field_column(model, object_type_key, key)
        ids = [value for operator, value in items if operator == "eq"]
        flags = {value for operator, value in items if operator == "isNull"}
        hop = RelatedCriterion(
            relationTypeKey=column.relation_type_key,
            direction=column.direction,
            where=[QueryCriterion(field="id", op="eq", value=value) for value in ids],
        )
        if ids:
            conditions.append(_hop_condition(model, object_type, hop, False, workspace_key, context))
        for flag in sorted(flags):
            plain = hop.model_copy(update={"where": []})
            conditions.append(
                _hop_condition(model, object_type, plain, flag == "true", workspace_key, context)
            )

    def id_filter(column: Any) -> Any:
        return and_(*(condition(column) for condition in conditions))

    return RelationFilters(id_filter, tuple(sorted((f, o, v) for f, o, v in filters)))


def _hop_condition(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    hop: RelatedCriterion,
    inverted: bool,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Callable[[Any], Any]:
    criterion = QueryCriterion(related=hop, **{"not": inverted})
    return _related_predicate(
        model, object_type, criterion, "/filter", workspace_key, context
    ).predicate


@dataclass(frozen=True)
class CandidateFilter:
    """The per-type list's ``candidateFor`` (0.9 K7, D173): a condition on the listed record's ID,
    ``None`` when the end is unrestricted, and what a cursor binds."""

    id_filter: Callable[[Any], Any] | None
    bound: tuple[str, str] | None


def list_candidate_filter(
    model: EngineModel,
    object_type_key: str,
    candidate_for: str | None,
    anchor_type_key: str | None,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> CandidateFilter:
    """``candidateFor=<key>&anchorTypeKey=<type>``: the listed records a record of the anchor type
    may choose through that relationship (``key`` a relation key or reverse key read from the
    anchor's type), by the criteria the binding sets at the listed records' end."""
    if candidate_for is None and anchor_type_key is None:
        return CandidateFilter(None, None)
    if not candidate_for or not anchor_type_key:
        _invalid_filter("candidateFor and anchorTypeKey come together", "candidateFor")
    try:
        column = related_column(model, anchor_type_key, candidate_for)
    except RelatedKeyError as error:
        _invalid_filter(str(error), "candidateFor")
    end = "to" if column.direction == "outgoing" else "from"
    binding = next(
        (
            item
            for item in column.bindings
            if (item.toObjectTypeKey if end == "to" else item.fromObjectTypeKey) == object_type_key
        ),
        None,
    )
    object_type = model.object_type(object_type_key)
    if binding is None or object_type is None:
        _invalid_filter(
            f"'{candidate_for}' from '{anchor_type_key}' records reaches no '{object_type_key}' records",
            "candidateFor",
        )
    criteria = binding.candidates_at(end)
    if not criteria:
        return CandidateFilter(None, (candidate_for, anchor_type_key))
    ids = candidate_ids(model, object_type, criteria, workspace_key=workspace_key, context=context)
    return CandidateFilter(lambda column: column.in_(ids), (candidate_for, anchor_type_key))


def both_filters(
    first: Callable[[Any], Any] | None, second: Callable[[Any], Any] | None
) -> Callable[[Any], Any] | None:
    """Two optional conditions on one column as one."""
    if first is None or second is None:
        return first or second
    return lambda column: and_(first(column), second(column))


def _invalid_filter(message: str, parameter: str) -> NoReturn:
    raise api_error(422, "INVALID_FILTER", message, {"path": f"/query/{parameter}"})


def _invalid_expand(message: str, value: str) -> NoReturn:
    raise api_error(422, "INVALID_EXPAND", message, {"parameter": "expand", "value": value})


def _as_of(object_type: ObjectTypeDefinition, as_of: str | None) -> date | None:
    """``asOf`` as a date, on a type that declares an effective period (ADR-038). It filters the
    queried records only; a hop's far end and expansions are not dated (D22)."""
    if as_of is None:
        return None
    try:
        if len(as_of) != 10:
            raise ValueError(as_of)
        parsed = date.fromisoformat(as_of)
    except ValueError:
        _invalid("asOf must be a date (YYYY-MM-DD)", "/asOf")
    require_effective_period(object_type, "/asOf")
    return parsed


def _invalid(message: str, pointer: str) -> NoReturn:
    raise api_error(422, "INVALID_QUERY", message, {"path": pointer})

