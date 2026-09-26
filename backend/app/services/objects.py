from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Select, and_, case, delete, exists, func, not_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from ..errors import api_error
from ..models.api import (
    AttributeOutput,
    ObjectCreate,
    ObjectResponse,
    ObjectUpdate,
    RelationCreate,
)
from ..models.database import AttributeValue, ObjectRelation, RdmObject
from ..models.schema import ApplicationDefinition, EngineModel, ObjectTypeDefinition
from ..models.search_index import LIVE_VALUES, MIN_INDEXED_LENGTH, SearchIndex, match_phrase
from .attributes import (
    VALUE_COLUMNS,
    apply_attribute_values,
    check_attribute_uniqueness,
    current_attribute_values,
    load_attribute_values,
    remove_attribute_value_row,
    save_attribute_values,
    validate_attribute_change,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from .audit import record_audit_event
from .model.traversal import ancestor_type_keys
from .model.validation.fields import ANCESTOR_FIELD_PREFIX
from .pagination import (
    Overlay,
    SortKey,
    datetime_key,
    integer_key,
    seek_error,
    seek_predicate,
    text_key,
)

OBJECT_SORT_COLUMNS: dict[str, Any] = {
    "id": RdmObject.id,
    "name": RdmObject.name,
    "createdAt": RdmObject.created_at,
    "updatedAt": RdmObject.updated_at,
    "sequenceId": RdmObject.sequence_id,
}

_SEQUENCE_FIELD = "sequenceId"
# Every object and relation list defaults to name order in live, draft and history (D22), closed by
# its context's unique tiebreak, so a default page can be sought by name.
DEFAULT_SORT = "name"


@dataclass(frozen=True)
class ObjectQuery:
    """A filtered object collection query with the keyset it must be paged by.

    ``seek`` turns a ``seek`` value into the predicate for rows at or after it in list order.
    ``overlay`` names a draft list's parts, through which position reads resolve.
    """

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]
    seek: Callable[[str], Any]
    overlay: Overlay | None = None


@dataclass(frozen=True)
class ObjectColumns:
    """Where an object collection query reads record columns and their typed values.

    Live reads use ``objects`` with ``attribute_values``; draft and history reads use a
    base-plus-overlay projection with ``snapshot_attribute_values``. A relation list reads the
    record at the other end of each relation the same way. One builder serves all of them, so
    search, typed filters and sort mean the same in every context and on every list.

    ``select_sort_values`` selects each sort value as a labelled column and reads cursor positions
    back from it, for statements whose rows are not the records themselves; such a list joins an
    attribute sort's value rather than looking it up per row. ``value_match`` relates a (possibly
    aliased) values table to the record. ``ancestor`` joins the
    name of each record's ``ancestor:<type>`` into a statement; lists without it cannot sort by one.
    ``object_type`` is the record's object type key, which ``objectType`` sorts by its model name.
    ``relationship`` maps a relation list's row to its relation type key and whether the listed
    record is at the relation's far end, which ``relationship`` sorts by the label the row shows.
    ``search_values`` narrows a search's value look-up to records with a value of the given
    attributes that the trigram index matches a phrase in (:func:`indexed_value_match`); a list
    without it, such as a relation list bounded by its anchor, looks up each row's values.
    """

    source: Any
    id: Any
    name: Any
    values: Any
    value_match: Callable[[Any], tuple[Any, ...]]
    builtin: dict[str, Any]
    tiebreak: Callable[[bool], SortKey]
    select_sort_values: bool = False
    ancestor: Callable[[Select[Any], str], tuple[Select[Any], Any]] | None = None
    object_type: Any = None
    relationship: tuple[Any, Any] | None = None
    search_values: Callable[[str, list[str]], Any] | None = None


# A value match read from the trigram index costs its matches; one looked up per record costs the
# records whose name does not match. Past this many index matches, the per-record look-up is the
# cheaper one (S8 measurements).
INDEXED_VALUE_LIMIT = 10_000


def indexed_value_match(
    index: SearchIndex, phrase: str, candidates: Callable[[Select[Any]], Any]
) -> Any:
    """Restrict a value look-up to ``candidates`` of the index's matches, while they are few.

    ``candidates`` turns the matching value rows' sequence IDs into a predicate on the listed
    record. The count is bounded and uncorrelated, so SQLite evaluates it once per statement and
    reads at most ``INDEXED_VALUE_LIMIT + 1`` matches for it; with more, every record is looked up.
    It comes first in an ``OR`` rather than a ``CASE``, which SQLite evaluated more slowly.
    """
    fts = index.fts
    matches = select(fts.c.rowid).where(fts.c[index.column].match(phrase))
    many = (
        select(func.count())
        .select_from(matches.limit(INDEXED_VALUE_LIMIT + 1).subquery())
        .scalar_subquery()
        > INDEXED_VALUE_LIMIT
    )
    return or_(many, candidates(matches))


def _live_value_candidates(phrase: str, attributes: list[str]) -> Any:
    """Live records with a value of ``attributes`` that the trigram index matches ``phrase`` in.

    Compared by sequence ID, which the (type, name) index a search walks already holds, so a
    record whose name does not match is checked without reading its table row.
    """
    value, record = aliased(AttributeValue), aliased(RdmObject)

    def candidates(matches: Select[Any]) -> Any:
        matched = select(value.object_id).where(
            value.sequence_id.in_(matches), value.attribute_type_key.in_(attributes)
        )
        return RdmObject.sequence_id.in_(select(record.sequence_id).where(record.id.in_(matched)))

    return indexed_value_match(LIVE_VALUES, phrase, candidates)


LIVE_OBJECT_COLUMNS = ObjectColumns(
    source=RdmObject,
    id=RdmObject.id,
    name=RdmObject.name,
    values=AttributeValue,
    value_match=lambda values: (values.object_id == RdmObject.id,),
    builtin=OBJECT_SORT_COLUMNS,
    tiebreak=lambda descending: integer_key(
        _SEQUENCE_FIELD, RdmObject.sequence_id, "sequence_id", descending=descending
    ),
    object_type=RdmObject.object_type_key,
    search_values=_live_value_candidates,
)


def get_object_type(model: EngineModel, object_type_key: str) -> ObjectTypeDefinition:
    definition = model.object_type(object_type_key)
    if not definition:
        raise api_error(404, "unknown_object_type", f"Object type '{object_type_key}' not found")
    return definition


def get_application(model: EngineModel, application_key: str) -> ApplicationDefinition:
    application = next((item for item in model.applications if item.key == application_key), None)
    if not application:
        raise api_error(404, "unknown_application", f"Application '{application_key}' not found")
    return application


def validate_application_object_type(
    model: EngineModel, application_key: str, object_type_key: str
) -> None:
    application = get_application(model, application_key)
    if object_type_key not in application.objectTypeKeys:
        raise api_error(
            422,
            "invalid_object_type_for_application",
            f"Object type '{object_type_key}' is not available in application '{application_key}'",
        )


def build_object_query(
    model: EngineModel,
    *,
    object_type_key: str,
    application_key: str | None,
    workspace_key: str,
    parent_object_id: str | None,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]] | None = None,
    top_level: bool = False,
) -> ObjectQuery:
    """Build the filtered statement, keyset and cursor filters for an object collection."""
    object_type = get_object_type(model, object_type_key)
    if application_key:
        validate_application_object_type(model, application_key, object_type_key)

    statement = select(RdmObject).where(
        RdmObject.object_type_key == object_type_key,
        RdmObject.workspace_key == workspace_key,
    )
    if application_key:
        statement = statement.where(RdmObject.application_key == application_key)
    if parent_object_id:
        statement = statement.where(RdmObject.parent_object_id == parent_object_id)
    if top_level:
        statement = statement.where(RdmObject.parent_object_id.is_(None))
    statement, keys, seek, normalized_filters = refine_object_query(
        model,
        LIVE_OBJECT_COLUMNS,
        statement,
        object_types=(object_type,),
        search=search,
        sort=sort,
        field_filters=field_filters or [],
    )
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={
            "applicationKey": application_key,
            "objectTypeKey": object_type_key,
            "parentObjectId": parent_object_id,
            "search": search,
            "typedFilters": normalized_filters,
            "workspaceKey": workspace_key,
            **top_level_filter(top_level),
        },
        seek=seek,
    )


def top_level_filter(top_level: bool) -> dict[str, Any]:
    """Bind ``topLevel`` into a cursor only when set, so cursors issued before it stay valid."""
    return {"topLevel": True} if top_level else {}


def refine_object_query(
    model: EngineModel,
    columns: ObjectColumns,
    statement: Select[Any],
    *,
    object_types: Sequence[ObjectTypeDefinition],
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
) -> tuple[Select[Any], tuple[SortKey, ...], Callable[[str], Any], list[dict[str, str]]]:
    """Add search and typed filters to an object statement and return its keyset and seek.

    ``object_types`` are the types the listed records can have: search covers the searchable
    fields of all of them and sort any scalar attribute bound to one of them, while a filter or an
    ancestor sort needs exactly one.
    """
    if search:
        statement = statement.where(_search_predicate(model, columns, object_types, search))
    normalized_filters, predicates = _typed_filter_predicates(
        model, columns, object_types, field_filters
    )
    if predicates:
        statement = statement.where(and_(*predicates))
    statement, keys, seek_values = _object_sort_keys(model, columns, statement, object_types, sort)
    if columns.select_sort_values:
        statement, keys = _select_sort_values(statement, keys)
    return statement, keys, _object_seek(keys, seek_values, sort), normalized_filters


def _object_seek(
    keys: tuple[SortKey, ...], seek_values: Callable[[str], list[Any]], sort: str | None
) -> Callable[[str], Any]:
    """Seek by the sorted field's value, which is the name when no sort is given."""

    def seek(raw: str) -> Any:
        try:
            return seek_predicate(keys, seek_values(raw))
        except ValueError:
            field_name = (sort or DEFAULT_SORT).removeprefix("-")
            raise seek_error(f"Invalid seek value for sort '{field_name}'") from None

    return seek


def _search_predicate(
    model: EngineModel,
    columns: ObjectColumns,
    object_types: Sequence[ObjectTypeDefinition],
    search: str,
) -> Any:
    """A case-insensitive "contains" match on the name or a searchable attribute (D25).

    The name is matched on the row. A value is looked up only for a record the trigram index
    names, when the search is long enough to hold a trigram; the ``LIKE`` then decides, so the
    index never changes the result, only which records are looked up.
    """
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    searchable_attributes = list(
        dict.fromkeys(
            binding.attributeTypeKey
            for object_type in object_types
            for binding in object_type.attributes
            if model.attribute_type(binding.attributeTypeKey).features.get("searchable")
        )
    )
    values = columns.values
    attribute_match = exists(
        select(values.sequence_id).where(
            *columns.value_match(values),
            values.attribute_type_key.in_(searchable_attributes),
            values.text_value.ilike(f"%{escaped}%", escape="\\"),
        )
    )
    indexable = searchable_attributes and len(search) >= MIN_INDEXED_LENGTH
    if columns.search_values is not None and indexable:
        indexed = columns.search_values(match_phrase(search), searchable_attributes)
        attribute_match = and_(indexed, attribute_match)
    return or_(columns.name.ilike(f"%{escaped}%", escape="\\"), attribute_match)


def _object_sort_keys(
    model: EngineModel,
    columns: ObjectColumns,
    statement: Select[Any],
    object_types: Sequence[ObjectTypeDefinition],
    sort: str | None,
) -> tuple[Select[Any], tuple[SortKey, ...], Callable[[str], list[Any]]]:
    """Sort keys for an object collection, always closed by the source's unique tiebreak.

    Also returns how a ``seek`` value becomes the leading key values. Attribute and ancestor sorts
    put records without a value last.
    """
    sort_name = sort or DEFAULT_SORT
    descending = sort_name.startswith("-")
    field_name = sort_name.removeprefix("-")
    tiebreak = columns.tiebreak(descending)
    if field_name == _SEQUENCE_FIELD or (
        field_name == tiebreak.name and field_name not in columns.builtin
    ):
        _query_error("invalid_sort", f"Unknown sort field '{field_name}'", "sort")
    if field_name == tiebreak.name:
        return statement, (tiebreak,), lambda raw: [tiebreak.parse(raw)]

    label_sort = _label_sort(model, columns, field_name)
    if label_sort is not None:
        label, extract = label_sort
        label_key = SortKey(
            name=field_name, column=label, attribute="", descending=descending, extract=extract
        )
        # Many records share a label, so the name orders them before the unique tiebreak.
        name_key = SortKey(
            name="name",
            column=columns.name,
            attribute="",
            descending=descending,
            extract=lambda _session, row: _row_name(row),
        )
        return statement, (label_key, name_key, tiebreak), lambda raw: [raw]

    if field_name.startswith(ANCESTOR_FIELD_PREFIX):
        statement, column = _query_ancestor(model, columns, statement, object_types, field_name)
        value_key = SortKey(
            name=field_name,
            column=column,
            attribute="",
            descending=descending,
            parse=lambda token: None if token == "~null" else token,
            format=lambda value: "~null" if value is None else str(value),
        )
        return statement, (_null_rank_key(field_name, column), value_key, tiebreak), lambda raw: [0, raw]

    column = columns.builtin.get(field_name)
    if column is None:
        definition = _sort_attribute(model, object_types, field_name)
        if columns.select_sort_values:
            # One outer join on the unique (record, attribute) key reads the value once per row.
            values = aliased(columns.values)
            statement = statement.outerjoin(
                values,
                and_(*columns.value_match(values), values.attribute_type_key == field_name),
            )
            column = getattr(values, VALUE_COLUMNS[definition.valueType])
        else:
            column = _attribute_scalar(columns, field_name, definition.valueType)
        null_rank = _null_rank_key(field_name, column)
        null_rank = replace(
            null_rank,
            extract=lambda session, row: int(
                _attribute_sort_value(session, columns, row, field_name, definition.valueType)
                is None
            ),
        )
        value_key = SortKey(
            name=field_name,
            column=column,
            attribute="",
            descending=descending,
            parse=lambda token: _parse_cursor_value(definition.valueType, token),
            format=lambda value: "~null" if value is None else _format_typed_value(value),
            extract=lambda session, row: _attribute_sort_value(
                session, columns, row, field_name, definition.valueType
            ),
        )
        return (
            statement,
            (null_rank, value_key, tiebreak),
            lambda raw: [0, _parse_typed(definition.valueType, raw)],
        )
    if field_name in {"createdAt", "updatedAt"}:
        attribute = "created_at" if field_name == "createdAt" else "updated_at"
        primary = datetime_key(field_name, column, attribute, descending=descending)
    else:
        primary = text_key(field_name, column, column.key, descending=descending)
    return statement, (primary, tiebreak), lambda raw: [primary.parse(raw)]


def _label_sort(
    model: EngineModel, columns: ObjectColumns, field_name: str
) -> tuple[Any, Callable[[Session, Any], Any]] | None:
    """The label a ``objectType`` or ``relationship`` column shows, as an orderable expression.

    Labels come from the model, so the list orders by what the user reads rather than by keys.
    Returns the expression and how a record row's label is read back for its cursor position.
    """
    if field_name == "objectType" and columns.object_type is not None:
        names = {item.key: item.name for item in model.objectTypes}
        attribute = columns.object_type.key
        return (
            case(names, value=columns.object_type, else_=columns.object_type),
            lambda _session, row: names.get(getattr(row, attribute), getattr(row, attribute)),
        )
    if field_name == "relationship" and columns.relationship is not None:
        type_key, reverse = columns.relationship
        forward = {item.key: item.name for item in model.relationTypes}
        backward = {item.key: item.reverseName or item.name for item in model.relationTypes}
        label = case(
            *((and_(type_key == key, reverse), name) for key, name in backward.items()),
            *((type_key == key, name) for key, name in forward.items()),
            else_=type_key,
        )
        # Relation lists select sort values as columns, so no row extraction is needed.
        return label, lambda _session, _row: None
    return None


def _row_name(row: Any) -> Any:
    return row.name


def _sort_attribute(model: EngineModel, object_types: Sequence[ObjectTypeDefinition], field: str):
    """Any scalar attribute bound to a listed type sorts; records without it sort last."""
    bound = {item.attributeTypeKey for object_type in object_types for item in object_type.attributes}
    definition = model.attribute_type(field) if field in bound else None
    if definition is None:
        _query_error("invalid_sort", f"Unknown field '{field}'", "sort")
    if definition.valueType == "json":
        _query_error("invalid_sort", f"Field '{field}' holds JSON and cannot be sorted", "sort")
    return definition


def _null_rank_key(field_name: str, column: Any) -> SortKey:
    """Orders records with a value before those without, whatever the value's direction."""
    return SortKey(
        name=f"{field_name}:null",
        column=case((column.is_(None), 1), else_=0),
        attribute="",
        parse=int,
    )


def _select_sort_values(
    statement: Select[Any], keys: tuple[SortKey, ...]
) -> tuple[Select[Any], tuple[SortKey, ...]]:
    """Select every key but the tiebreak as a labelled column and read positions back from it."""
    labelled = []
    for index, key in enumerate(keys[:-1]):
        label = f"sort_{index}"
        statement = statement.add_columns(key.column.label(label))
        labelled.append(replace(key, attribute=label, extract=None))
    return statement, (*labelled, keys[-1])


def _query_ancestor(
    model: EngineModel,
    columns: ObjectColumns,
    statement: Select[Any],
    object_types: Sequence[ObjectTypeDefinition],
    field: str,
) -> tuple[Select[Any], Any]:
    ancestor_type_key = field.removeprefix(ANCESTOR_FIELD_PREFIX)
    if columns.ancestor is None:
        _query_error("invalid_sort", f"Field '{field}' is not sortable in this list", "sort")
    if len(object_types) != 1:
        _query_error(
            "invalid_sort",
            f"Sorting by '{field}' needs one object type; this list holds several",
            "sort",
        )
    if ancestor_type_key not in ancestor_type_keys(model, object_types[0].key):
        _query_error(
            "invalid_sort",
            f"Object type '{object_types[0].key}' has no ancestor of type '{ancestor_type_key}'",
            "sort",
        )
    return columns.ancestor(statement, ancestor_type_key)


def _typed_filter_predicates(
    model: EngineModel,
    columns: ObjectColumns,
    object_types: Sequence[ObjectTypeDefinition],
    filters: list[tuple[str, str, str]],
) -> tuple[list[dict[str, str]], list[Any]]:
    parsed: list[tuple[str, str, Any, str, Any]] = []
    for field, operator, lexical in filters:
        column = columns.builtin.get(field)
        value_type = _built_in_value_type(field)
        if column is None:
            definition = _query_attribute(model, object_types, field, "filterable", "filter")
            value_type = definition.valueType
            column = getattr(columns.values, VALUE_COLUMNS[value_type])
        allowed = _filter_operators(value_type, attribute=field not in columns.builtin)
        if operator not in allowed:
            _query_error(
                "invalid_filter",
                f"Operator '{operator}' is not supported for field '{field}'",
                f"filter.{field}.{operator}",
            )
        value = _parse_filter_value(value_type, operator, lexical, field)
        parsed.append((field, operator, value, value_type, column))

    predicates: list[Any] = []
    eq_groups: dict[str, list[tuple[Any, str, Any]]] = {}
    for field, operator, value, value_type, column in parsed:
        if operator == "eq":
            eq_groups.setdefault(field, []).append((value, value_type, column))
        else:
            predicates.append(_filter_predicate(columns, field, operator, value, column))
    for field, values in eq_groups.items():
        predicates.append(
            or_(
                *[
                    _filter_predicate(columns, field, "eq", value, column)
                    for value, _value_type, column in values
                ]
            )
        )
    normalized = sorted(
        (
            {"field": field, "operator": operator, "value": _format_typed_value(value)}
            for field, operator, value, _value_type, _column in parsed
        ),
        key=lambda item: (item["field"], item["operator"], item["value"]),
    )
    return normalized, predicates


def _filter_predicate(
    columns: ObjectColumns, field: str, operator: str, value: Any, column: Any
) -> Any:
    is_attribute = field not in columns.builtin
    base = [*columns.value_match(columns.values), columns.values.attribute_type_key == field]
    if operator == "isUnset":
        present = exists(select(columns.values.sequence_id).where(*base))
        return not_(present) if value else present
    if operator == "isNull":
        comparison = column.is_(None) if value else column.is_not(None)
    elif operator == "eq":
        comparison = column == value
    elif operator == "contains":
        comparison = column.ilike(f"%{_escape_like(value)}%", escape="\\")
    elif operator == "startsWith":
        comparison = column.ilike(f"{_escape_like(value)}%", escape="\\")
    else:
        comparisons = {"lt": column < value, "lte": column <= value, "gt": column > value, "gte": column >= value}
        comparison = comparisons[operator]
    if not is_attribute:
        return comparison
    return exists(select(columns.values.sequence_id).where(*base, comparison))


def _query_attribute(
    model: EngineModel,
    object_types: Sequence[ObjectTypeDefinition],
    field: str,
    capability: str,
    parameter: str,
):
    bound = {item.attributeTypeKey for object_type in object_types for item in object_type.attributes}
    if field not in bound:
        _query_error(f"invalid_{parameter}", f"Unknown field '{field}'", parameter)
    if len(object_types) != 1:
        _query_error(
            f"invalid_{parameter}",
            f"Field '{field}' needs one object type; this list holds several",
            parameter,
        )
    definition = model.attribute_type(field)
    if definition is None or definition.valueType == "json" or not definition.features.get(capability):
        _query_error(
            f"invalid_{parameter}",
            f"Field '{field}' is not {capability}",
            parameter,
        )
    return definition


def _built_in_value_type(field: str) -> str:
    if field in {"createdAt", "updatedAt"}:
        return "dateTime"
    return "text"


def _filter_operators(value_type: str, *, attribute: bool) -> set[str]:
    suffix = {"isUnset"} if attribute else set()
    if value_type in {"text", "longText"}:
        return {"eq", "contains", "startsWith", "isNull"} | suffix
    if value_type in {"integer", "decimal", "date", "dateTime"}:
        return {"eq", "lt", "lte", "gt", "gte", "isNull"} | suffix
    if value_type == "boolean":
        return {"eq", "isNull"} | suffix
    return set()


def _parse_filter_value(value_type: str, operator: str, lexical: str, field: str) -> Any:
    if operator in {"isNull", "isUnset"}:
        if lexical not in {"true", "false"}:
            _query_error("invalid_filter", f"Filter '{operator}' requires true or false", f"filter.{field}.{operator}")
        return lexical == "true"
    try:
        return _parse_typed(value_type, lexical)
    except ValueError:
        _query_error("invalid_filter", f"Invalid {value_type} value for field '{field}'", f"filter.{field}.{operator}")


def _parse_typed(value_type: str, lexical: str) -> Any:
    """A lexical value in its declared type; ``ValueError`` when it is not one."""
    try:
        if value_type in {"text", "longText"}:
            return lexical
        if value_type == "integer":
            return int(lexical)
        if value_type == "decimal":
            value = Decimal(lexical)
            if value.is_finite():
                return value
        if value_type == "boolean" and lexical in {"true", "false"}:
            return lexical == "true"
        if value_type == "date":
            return date.fromisoformat(lexical)
        if value_type == "dateTime" and ("T" in lexical or " " in lexical):
            return datetime.fromisoformat(lexical)
    except (ValueError, InvalidOperation):
        pass
    raise ValueError(f"Invalid {value_type} value")


def _query_error(code: str, message: str, path: str) -> None:
    raise api_error(422, code, message, {"path": f"/query/{path}"})


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _attribute_scalar(columns: ObjectColumns, field: str, value_type: str) -> Any:
    column = getattr(columns.values, VALUE_COLUMNS[value_type])
    return (
        select(column)
        .where(*columns.value_match(columns.values), columns.values.attribute_type_key == field)
        .correlate_except(columns.values)
        .scalar_subquery()
    )


def _attribute_sort_value(
    session: Session, columns: ObjectColumns, row: Any, field: str, value_type: str
) -> Any:
    """Read one row's sort value back for its cursor position."""
    statement = select(_attribute_scalar(columns, field, value_type))
    if columns.source is RdmObject:
        statement = statement.where(RdmObject.id == row.id)
    else:
        statement = statement.select_from(columns.source).where(
            columns.id == row.object_id, columns.source.c.values_owner_id == row.values_owner_id
        )
    return session.scalar(statement)


def _parse_cursor_value(value_type: str, token: str) -> Any:
    if token == "~null":
        return None
    return _parse_filter_value(value_type, "eq", token, "cursor")


def _format_typed_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def create_object_record(session: Session, model: EngineModel, payload: ObjectCreate) -> RdmObject:
    """Create one object in the workspace's live object store.

    Requires an active (non-retired) workspace.  The record is immediately part of the
    authoritative live projection; no workspace revision is minted.
    """
    from .relations import create_relation_instance
    from .workspaces import resolve_workspace

    workspace = resolve_workspace(session, payload.workspaceKey, require_active=True)
    workspace_key = workspace.key
    object_type_key = payload.objectTypeKey
    object_type = get_object_type(model, object_type_key)
    validate_application_object_type(model, payload.applicationKey, object_type_key)
    attributes = validate_attributes(model, object_type, attributes_to_dict(payload.attributes))
    validate_object_attribute_rules(object_type, attributes)
    _require_initial_relations(model, object_type, object_type_key, payload)

    public_id = str(payload.id) if payload.id is not None else None
    if public_id is not None:
        existing = session.scalar(select(RdmObject.id).where(RdmObject.id == public_id))
        if existing:
            raise api_error(
                409, "object_already_exists", f"An object with ID '{public_id}' already exists"
            )

    parent, parent_relation = validate_parent(
        session,
        model,
        object_type_key,
        payload.applicationKey,
        workspace_key,
        str(payload.parentObjectId) if payload.parentObjectId is not None else None,
    )
    check_attribute_uniqueness(session, model, attributes, workspace_key=workspace_key)
    item = RdmObject(
        workspace_key=workspace_key,
        application_key=payload.applicationKey,
        object_type_key=object_type_key,
        parent_object_id=parent.id if parent else None,
        name=payload.name,
    )
    if public_id is not None:
        item.id = public_id
    session.add(item)
    session.flush()
    save_attribute_values(session, model, item.id, attributes)
    if parent and parent_relation:
        session.add(
            ObjectRelation(
                relation_type_key=parent_relation,
                from_object_id=parent.id,
                to_object_id=item.id,
            )
        )
    for initial in payload.initialRelations:
        if initial.direction == "outgoing":
            from_id, to_id = item.id, str(initial.otherObjectId)
            from_object, to_object = item, None
        else:
            from_id, to_id = str(initial.otherObjectId), item.id
            from_object, to_object = None, item
        try:
            create_relation_instance(
                session,
                model,
                RelationCreate(
                    relationTypeKey=initial.relationTypeKey,
                    fromObjectId=from_id,
                    toObjectId=to_id,
                    attributes=initial.attributes,
                ),
                from_object=from_object,
                to_object=to_object,
            )
        except IntegrityError:
            session.rollback()
            raise api_error(409, "duplicate_relation", "Relation already exists") from None
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="created",
        version=1,
        changes={
            "objectTypeKey": object_type_key,
            "attributes": attributes,
            "initialRelations": [
                relation.model_dump(mode="json") for relation in payload.initialRelations
            ],
        },
        object_ids=[item.id],
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise api_error(409, "duplicate_relation", "Relation already exists") from None
    return item


def update_object_record(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
) -> RdmObject:
    """Apply a partial live object update under optimistic concurrency."""
    from .relations import validate_scoped_relations_for_subtree
    from .workspaces import resolve_workspace

    object_type = get_object_type(model, object_type_key)
    attributes = (
        validate_attributes(
            model, object_type, attributes_to_dict(payload.attributes), partial=True
        )
        if payload.attributes is not None
        else None
    )

    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    claim_object_version(session, item, payload.expectedVersion)

    if attributes is not None:
        validate_attribute_change(session, model, object_type, item, attributes)

    changes: dict[str, Any] = {}
    if payload.name is not None:
        changes["name"] = {"from": item.name, "to": payload.name}
        item.name = payload.name
    if "parentObjectId" in payload.model_fields_set:
        old_parent = item.parent_object_id
        parent, parent_relation = validate_parent(
            session,
            model,
            object_type_key,
            item.application_key,
            item.workspace_key,
            str(payload.parentObjectId) if payload.parentObjectId is not None else None,
            moving_object_id=item.id,
        )
        replace_parent_relation(session, model, item, parent, parent_relation)
        changes["parentObjectId"] = {
            "from": old_parent,
            "to": parent.id if parent else None,
        }
    if attributes is not None:
        save_attribute_values(session, model, item.id, attributes)
        changes["attributes"] = attributes

    validate_scoped_relations_for_subtree(session, model, item)

    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes=changes,
        object_ids=[item.id],
    )
    session.commit()
    return item


def set_live_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    value: Any,
    expected_version: int,
    *,
    create_only: bool = False,
) -> RdmObject:
    """Set one live attribute value under the object's optimistic-concurrency version.

    ``create_only`` (POST) requires the value to be absent; otherwise the value must already exist
    (PATCH).  The object version is claimed and bumped, the merged rules are re-validated, and the
    attribute row is upserted.
    """
    from .workspaces import resolve_workspace

    object_type = get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    present = attribute_type_key in current_attribute_values(session, item.id)
    if create_only and present:
        raise api_error(
            409,
            "attribute_already_exists",
            f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'",
        )
    if not create_only and not present:
        raise api_error(
            404,
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    normalized = validate_attributes(model, object_type, {attribute_type_key: value}, partial=True)
    claim_object_version(session, item, expected_version)
    apply_attribute_values(session, model, object_type, item, normalized)
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": normalized},
        object_ids=[item.id],
    )
    session.commit()
    return item


def delete_live_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    expected_version: int,
) -> RdmObject:
    """Delete one live attribute value under the object's optimistic-concurrency version.

    Read-only and required attributes cannot be deleted; object-level rules are re-validated over
    the surviving values before the row is removed.
    """
    from .workspaces import resolve_workspace

    object_type = get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    validate_deletable_attribute(object_type, attribute_type_key)
    current = current_attribute_values(session, item.id)
    if attribute_type_key not in current:
        raise api_error(
            404,
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    remaining = {
        key: value for key, value in current.items() if key != attribute_type_key
    }
    validate_object_attribute_rules(object_type, remaining)
    claim_object_version(session, item, expected_version)
    remove_attribute_value_row(session, item.id, attribute_type_key)
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": {attribute_type_key: None}},
        object_ids=[item.id],
    )
    session.commit()
    return item


def attributes_to_dict(attributes: list) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in attributes:
        if item.attributeTypeKey in result:
            raise api_error(
                422,
                "duplicate_attribute",
                f"Attribute '{item.attributeTypeKey}' occurs more than once",
            )
        result[item.attributeTypeKey] = item.value
    return result


def _require_initial_relations(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    object_type_key: str,
    payload: ObjectCreate,
) -> None:
    parent_relation_keys = set(object_type.behavior.get("parentRelationTypeKeys", []))
    required_relation_keys = {
        allowed.relationTypeKey
        for allowed in model.objectTypeRelations
        if allowed.toObjectTypeKey == object_type_key
        and allowed.required
        and allowed.relationTypeKey not in parent_relation_keys
    }
    provided_required_keys = {
        relation.relationTypeKey
        for relation in payload.initialRelations
        if relation.direction == "incoming"
    }
    missing_relation_keys = required_relation_keys - provided_required_keys
    if missing_relation_keys:
        raise api_error(
            422,
            "missing_required_relations",
            f"Required relationships missing: {sorted(missing_relation_keys)}",
            {"relationTypeKeys": sorted(missing_relation_keys)},
        )


def load_object(session: Session, object_id: str, object_type_key: str | None = None) -> RdmObject:
    statement = select(RdmObject).where(RdmObject.id == object_id)
    if object_type_key:
        statement = statement.where(RdmObject.object_type_key == object_type_key)
    item = session.scalar(statement)
    if not item:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    return item


def load_active_projection(
    session: Session, object_id: str, object_type_key: str | None = None
) -> RdmObject:
    """Load a live record from the workspace's active object store.

    The active object store is the authoritative, directly-mutable projection; an object is
    visible here as soon as it is written, with no workspace revision required.
    """
    return load_object(session, object_id, object_type_key)


def claim_object_version(session: Session, item: RdmObject, expected_version: int) -> None:
    result = session.execute(
        update(RdmObject)
        .where(RdmObject.id == item.id, RdmObject.version == expected_version)
        .values(version=expected_version + 1, updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise api_error(409, "version_conflict", "Object version has changed")
    session.refresh(item)


def validate_parent(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    application_key: str,
    workspace_key: str,
    parent_object_id: str | None,
    moving_object_id: str | None = None,
) -> tuple[RdmObject | None, str | None]:
    object_type = get_object_type(model, object_type_key)
    root_creatable = object_type.features.get("rootCreatable", False)
    if parent_object_id is None:
        if not root_creatable:
            raise api_error(422, "parent_required", "This object type requires a parent")
        return None, None

    parent = load_object(session, parent_object_id)
    if parent.application_key != application_key or parent.workspace_key != workspace_key:
        raise api_error(
            422, "parent_wrong_scope", "Parent must be in the same application and workspace"
        )
    if moving_object_id and _would_create_parent_cycle(session, moving_object_id, parent.id):
        raise api_error(422, "parent_cycle", "Parent selection would create a cycle")

    permitted = set(object_type.behavior.get("parentRelationTypeKeys", []))
    matches = [
        relation
        for relation in model.objectTypeRelations
        if relation.relationTypeKey in permitted
        and relation.fromObjectTypeKey == parent.object_type_key
        and relation.toObjectTypeKey == object_type_key
    ]
    if len(matches) != 1:
        raise api_error(
            422, "invalid_parent_type", "Parent type is not permitted for this object type"
        )
    return parent, matches[0].relationTypeKey


def replace_parent_relation(
    session: Session,
    model: EngineModel,
    item: RdmObject,
    parent: RdmObject | None,
    parent_relation: str | None,
) -> None:
    parent_relation_types = set(
        get_object_type(model, item.object_type_key).behavior.get("parentRelationTypeKeys", [])
    )
    session.execute(
        delete(ObjectRelation).where(
            ObjectRelation.to_object_id == item.id,
            ObjectRelation.relation_type_key.in_(parent_relation_types),
        )
    )
    item.parent_object_id = parent.id if parent else None
    if parent and parent_relation:
        session.add(
            ObjectRelation(
                relation_type_key=parent_relation,
                from_object_id=parent.id,
                to_object_id=item.id,
            )
        )


def build_object_responses(
    session: Session, model: EngineModel, objects: list[RdmObject]
) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    paths = _object_paths(session, objects)
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            name=item.name,
            path=paths[item.id],
            attributes=_build_attribute_outputs(model, values[item.id]),
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _build_attribute_outputs(model: EngineModel, values: dict) -> list[AttributeOutput]:
    result = []
    for key, (value_id, value) in values.items():
        definition = model.attribute_type(key)
        result.append(
            AttributeOutput(
                id=value_id,
                attributeTypeKey=key,
                name=definition.name if definition else key,
                valueType=definition.valueType if definition else "text",
                value=value,
            )
        )
    return result


def _object_paths(session: Session, objects: list[RdmObject]) -> dict[str, list[dict[str, str]]]:
    # Resolve ancestor chains for a batch in level order so the number of queries is bounded by
    # hierarchy depth rather than by the object count (avoids an N+1 per-object traversal).
    paths = {
        item.id: [{"id": item.id, "name": item.name, "objectTypeKey": item.object_type_key}]
        for item in objects
    }
    visited = {item.id: {item.id} for item in objects}
    frontier = {item.id: item.parent_object_id for item in objects if item.parent_object_id}
    while frontier:
        parent_ids = {parent_id for parent_id in frontier.values() if parent_id}
        if not parent_ids:
            break
        parent_map = {
            row.id: row
            for row in session.scalars(select(RdmObject).where(RdmObject.id.in_(parent_ids)))
        }
        next_frontier: dict[str, str | None] = {}
        for object_id, parent_id in frontier.items():
            parent = parent_map.get(parent_id) if parent_id else None
            if parent is None or parent.id in visited[object_id]:
                continue
            visited[object_id].add(parent.id)
            paths[object_id].append(
                {"id": parent.id, "name": parent.name, "objectTypeKey": parent.object_type_key}
            )
            if parent.parent_object_id:
                next_frontier[object_id] = parent.parent_object_id
        frontier = next_frontier
    return {object_id: list(reversed(path)) for object_id, path in paths.items()}


def _would_create_parent_cycle(session: Session, object_id: str, parent_id: str) -> bool:
    current_id: str | None = parent_id
    visited: set[str] = set()
    while current_id:
        if current_id == object_id or current_id in visited:
            return True
        visited.add(current_id)
        current_id = session.scalar(
            select(RdmObject.parent_object_id).where(RdmObject.id == current_id)
        )
    return False
