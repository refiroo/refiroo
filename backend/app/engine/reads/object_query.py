"""Live object queries: filters, typed sorts, search and seek over one type or across types, and the ancestor paths a response shows."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import (
    ARRAY,
    Integer,
    Select,
    String,
    and_,
    any_,
    bindparam,
    case,
    cast,
    exists,
    false,
    func,
    not_,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session, aliased

from ...common.pagination import (
    Keyed,
    Overlay,
    SortKey,
    datetime_key,
    integer_key,
    seek_error,
    seek_predicate,
    text_key,
)
from ...errors import api_error
from ...models.database import AttributeValue, RdmObject
from ...models.schema import EngineModel, ObjectTypeDefinition
from ...models.search_index import LIVE_VALUES, MIN_INDEXED_LENGTH, SearchIndex
from ..model.traversal import ancestor_type_keys
from ..model.validation.fields import ANCESTOR_FIELD_PREFIX
from ..records.rules import get_object_type, validate_application_object_type
from ..records.values import VALUE_COLUMNS

OBJECT_SORT_COLUMNS: dict[str, Any] = {
    "id": RdmObject.id,
    "name": RdmObject.name,
    "createdAt": RdmObject.created_at,
    "updatedAt": RdmObject.updated_at,
    "sequenceId": RdmObject.sequence_id,
}


_SEQUENCE_FIELD = "sequenceId"


# Every object and relation list defaults to name order in live, change set and history (D22), closed by
# its context's unique tiebreak, so a default page can be sought by name.
DEFAULT_SORT = "name"


@dataclass(frozen=True)
class ObjectQuery:
    """A filtered object collection query with the keyset it must be paged by.

    ``seek`` turns a ``seek`` value into the predicate for rows at or after it in list order, over
    ``keys`` or the keys it is given. ``overlay`` names a change set list's parts, through which
    position reads resolve. ``parts`` read an attribute sort in value order (0.9 C3a; publications
    since C6a). ``record`` holds the listed record's ``id``, ``name``, ``object_type_key`` and
    ``parent_object_id``, which a condition added to the statement addresses: ``RdmObject`` for a live
    list, the projection's columns for a change set or publication list.
    """

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]
    seek: Callable[..., Any]
    overlay: Overlay | None = None
    parts: tuple[Keyed, ...] | None = None
    record: Any = RdmObject

    def then_by_name(self) -> ObjectQuery:
        """The same query with the name ordering ties before the unique tiebreak."""

        def widened(keys: tuple[SortKey, ...]) -> tuple[SortKey, ...]:
            return (*keys[:-1], text_key("name", self.record.name, "name"), keys[-1])

        return replace(
            self,
            keys=widened(self.keys),
            parts=None
            if self.parts is None
            else tuple(Keyed(part.statement, widened(tuple(part.keys))) for part in self.parts),
        )


@dataclass(frozen=True)
class ObjectColumns:
    """Where an object collection query reads record columns and their typed values.

    Live reads use ``objects`` with ``attribute_values``; change set and history reads use a
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
    ``search_names`` likewise narrows a name match to the records whose name the trigram index
    matches a phrase in; without it each row's name is matched.
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
    search_names: Callable[[str], Any] | None = None


# A match read from a trigram index costs its matches; one made on each record costs the records
# the search reads. Past this many index matches, matching each record is the cheaper one (S8
# measurements for values; 0.9.0-alpha.1 PG5 for names).
INDEXED_MATCH_LIMIT = 10_000


def bounded_match(matches: Select[Any], candidates: Any) -> Any:
    """``candidates``, a predicate on the listed record built from ``matches``, while the index
    matches are few; true for every record past :data:`INDEXED_MATCH_LIMIT`, so the search's
    ``LIKE`` is made on each one. The count is bounded and uncorrelated, so it is evaluated once
    per statement and reads at most ``INDEXED_MATCH_LIMIT + 1`` matches."""
    many = (
        select(func.count())
        .select_from(matches.limit(INDEXED_MATCH_LIMIT + 1).subquery())
        .scalar_subquery()
        > INDEXED_MATCH_LIMIT
    )
    return or_(many, candidates)


def indexed_value_match(
    index: SearchIndex, pattern: str, candidates: Callable[[Select[Any]], Any]
) -> Any:
    """Restrict a value look-up to ``candidates`` of the index's matches, while they are few.

    ``candidates`` turns the matching value rows' sequence IDs into a predicate on the listed
    record (:func:`bounded_match`).
    """
    matches = index.matches(pattern)
    return bounded_match(matches, candidates(matches))


def _live_value_candidates(pattern: str, attributes: list[str]) -> Any:
    """Live records with a value of ``attributes`` that the trigram index matches ``pattern`` in.

    Compared by sequence ID, which the (type, name) index a search walks already holds, so a
    record whose name does not match is checked without reading its table row.
    """
    value, record = aliased(AttributeValue), aliased(RdmObject)

    def candidates(matches: Select[Any]) -> Any:
        matched = select(value.object_id).where(
            value.sequence_id.in_(matches), value.attribute_type_key.in_(attributes)
        )
        return RdmObject.sequence_id.in_(select(record.sequence_id).where(record.id.in_(matched)))

    return indexed_value_match(LIVE_VALUES, pattern, candidates)


# A search whose phrase the trigram indexes match in at most this many records reads those records
# by ID; one matching more walks the type, matching each record (0.9.0-alpha.1 PG5).
SEARCH_CANDIDATE_LIMIT = 1_000


def search_candidates(session: Session, parts: Sequence[Select[Any]]) -> list[str] | None:
    """The record IDs ``parts`` select (each a set of IDs read from a trigram index), or ``None``
    when there are more than :data:`SEARCH_CANDIDATE_LIMIT`.

    Read before the search's statements are built, so each of them names the records it may
    return as a list: PostgreSQL then reads those records by ID, in every arm of a change set's
    projection, instead of walking every record of the type in name order to probe a set.
    """
    if not parts:
        return None
    # UNION ALL stops at the limit; UNION would first collect every match of a common phrase.
    statement = union_all(*parts) if len(parts) > 1 else parts[0]
    found = list(session.scalars(statement.limit(SEARCH_CANDIDATE_LIMIT + 1)))
    return list(dict.fromkeys(found)) if len(found) <= SEARCH_CANDIDATE_LIMIT else None


def live_search_candidates(
    session: Session,
    model: EngineModel,
    *,
    workspace_key: str,
    object_type: ObjectTypeDefinition,
    search: str,
    search_fields: Sequence[str] | None,
) -> list[str] | None:
    """The live records of ``object_type`` whose name or searchable value the trigram indexes
    match ``search`` in (:func:`search_candidates`); ``None`` for a phrase too short to index."""
    if len(search) < MIN_INDEXED_LENGTH:
        return None
    pattern = f"%{escape_like(search)}%"
    parts = []
    if search_fields is None or "name" in search_fields:
        parts.append(
            select(RdmObject.id).where(
                RdmObject.workspace_key == workspace_key,
                RdmObject.object_type_key == object_type.key,
                RdmObject.name.ilike(pattern, escape="\\"),
            )
        )
    attributes = searchable_attribute_keys(model, (object_type,), search_fields)
    if attributes:
        record = aliased(RdmObject)
        parts.append(
            select(AttributeValue.object_id)
            .join(record, record.id == AttributeValue.object_id)
            .where(
                AttributeValue.sequence_id.in_(LIVE_VALUES.matches(pattern)),
                AttributeValue.attribute_type_key.in_(attributes),
                record.workspace_key == workspace_key,
                record.object_type_key == object_type.key,
            )
        )
    return search_candidates(session, parts)


def _live_name_candidates(pattern: str) -> Any:
    """Live records whose name the trigram index matches ``pattern`` in (:func:`bounded_match`)."""
    record = aliased(RdmObject)
    matches = select(record.sequence_id).where(record.name.ilike(pattern, escape="\\"))
    return bounded_match(matches, RdmObject.sequence_id.in_(matches))


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
    search_names=_live_name_candidates,
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
    search_fields: Sequence[str] | None = None,
    id_filter: Callable[[Any], Any] | None = None,
    as_of: date | None = None,
    session: Session | None = None,
) -> ObjectQuery:
    """Build the filtered statement, keyset and cursor filters for an object collection.

    ``search_fields`` limits ``search`` to those fields (``name`` or searchable attributes), as a
    view declares them; ``id_filter`` restricts the records by a predicate on their public ID;
    ``as_of`` keeps the records effective on that date (Base 0.9 Q4). With ``session``, a search
    first reads its candidates from the trigram indexes (:func:`search_candidates`).
    """
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
    if id_filter is not None:
        statement = statement.where(id_filter(RdmObject.id))
    search_ids = None
    if session is not None and search:
        search_ids = live_search_candidates(
            session,
            model,
            workspace_key=workspace_key,
            object_type=object_type,
            search=search,
            search_fields=search_fields,
        )
    statement, keys, seek, normalized_filters = refine_object_query(
        model,
        LIVE_OBJECT_COLUMNS,
        statement,
        object_types=(object_type,),
        search=search,
        sort=sort,
        field_filters=field_filters or [],
        search_fields=search_fields,
        as_of=as_of,
        search_ids=search_ids,
    )
    return ObjectQuery(
        parts=value_order_parts(
            model,
            statement,
            keys,
            sort,
            AttributeValue,
            lambda values: (values.object_id == RdmObject.id,),
        ),
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
            **as_of_filter(as_of),
        },
        seek=seek,
    )


def value_order_parts(
    model: EngineModel,
    statement: Select[Any],
    keys: tuple[SortKey, ...],
    sort: str | None,
    values: Any,
    value_match: Callable[[Any], tuple[Any, ...]],
) -> tuple[Keyed, ...] | None:
    """An attribute sort read in two parts (0.9 C3a, D46): the records with a value, joined to it
    and ordered through the (attribute, value) index, then the records without one. Each part holds
    its null rank constant, so a position in the other part costs it nothing. ``None`` for any other
    sort. ``values`` is the typed value table, ``value_match`` relates an alias of it to the listed
    record: live values, or a publication's (C6a, C-D67)."""
    field_name = (sort or DEFAULT_SORT).removeprefix("-")
    if len(keys) != 3 or keys[0].name != f"{field_name}:null":
        return None
    null_rank, value_key, tiebreak = keys
    column_name = VALUE_COLUMNS[model.attribute_type(field_name).valueType]
    held, absent = aliased(values), aliased(values)
    held_value = getattr(held, column_name)
    with_value = statement.join(
        held,
        and_(
            *value_match(held),
            held.attribute_type_key == field_name,
            held_value.is_not(None),
        ),
    )
    without_value = statement.where(
        ~exists(
            select(absent.sequence_id).where(
                *value_match(absent),
                absent.attribute_type_key == field_name,
                getattr(absent, column_name).is_not(None),
            )
        )
    )
    return (
        Keyed(
            with_value,
            (replace(null_rank, column=cast(0, Integer)), replace(value_key, column=held_value), tiebreak),
        ),
        Keyed(
            without_value,
            (
                replace(null_rank, column=cast(1, Integer)),
                replace(value_key, column=cast(null(), held_value.type)),
                tiebreak,
            ),
        ),
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
    search_fields: Sequence[str] | None = None,
    as_of: date | None = None,
    search_ids: Sequence[str] | None = None,
) -> tuple[Select[Any], tuple[SortKey, ...], Callable[[str], Any], list[dict[str, str]]]:
    """Add search and typed filters to an object statement and return its keyset and seek.

    ``object_types`` are the types the listed records can have: search covers the searchable
    fields of all of them, or only ``search_fields`` when given, and sort any scalar attribute
    bound to one of them, while a filter, an ancestor sort or ``as_of`` needs exactly one.
    ``search_ids`` are the search's candidates when they were read first (:func:`search_candidates`).
    """
    if as_of is not None:
        (object_type,) = object_types
        require_effective_period(object_type, "/query/asOf")
        statement = statement.where(as_of_predicate(columns, object_type, as_of))
    if search:
        statement = statement.where(
            _search_predicate(model, columns, object_types, search, search_fields, search_ids)
        )
    normalized_filters, predicates = typed_filter_predicates(
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

    def seek(raw: str, part_keys: Sequence[SortKey] = keys) -> Any:
        try:
            return seek_predicate(part_keys, seek_values(raw))
        except ValueError:
            field_name = (sort or DEFAULT_SORT).removeprefix("-")
            raise seek_error(f"Invalid seek value for sort '{field_name}'") from None

    return seek


def _search_predicate(
    model: EngineModel,
    columns: ObjectColumns,
    object_types: Sequence[ObjectTypeDefinition],
    search: str,
    search_fields: Sequence[str] | None = None,
    search_ids: Sequence[str] | None = None,
) -> Any:
    """A case-insensitive "contains" match on the name or a searchable attribute (D25).

    When the search is long enough to hold a trigram, the name and the values are matched only
    for the records their trigram indexes name: the ``search_ids`` read first, or else sets the
    statement reads itself, bounded as :func:`bounded_match` bounds them. The ``LIKE`` then
    decides, so an index never changes the result, only which records are looked up. A shorter
    search matches every row's name. ``search_fields`` narrows the match to the name and
    searchable attributes it names.
    """
    escaped = escape_like(search)
    searchable_attributes = searchable_attribute_keys(model, object_types, search_fields)
    if search_ids is not None:
        values = columns.values
        matches = []
        if search_fields is None or "name" in search_fields:
            matches.append(name_contains(columns.name, search))
        if searchable_attributes:
            matches.append(
                exists(
                    select(values.sequence_id).where(
                        *columns.value_match(values),
                        values.attribute_type_key.in_(searchable_attributes),
                        values.text_value.ilike(f"%{escaped}%", escape="\\"),
                    )
                )
            )
        listed = bindparam("search_ids", list(search_ids), type_=ARRAY(String))
        return and_(columns.id == any_(listed), or_(*matches)) if matches else false()
    name_match = name_contains(columns.name, search)
    if columns.search_names is not None and len(search) >= MIN_INDEXED_LENGTH:
        name_match = and_(columns.search_names(f"%{escaped}%"), name_match)
    if not searchable_attributes:
        return name_match if search_fields is None or "name" in search_fields else false()
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
        indexed = columns.search_values(f"%{escaped}%", searchable_attributes)
        attribute_match = and_(indexed, attribute_match)
    if search_fields is not None and "name" not in search_fields:
        return attribute_match
    return or_(name_match, attribute_match)


def searchable_attribute_keys(
    model: EngineModel,
    object_types: Sequence[ObjectTypeDefinition],
    search_fields: Sequence[str] | None,
) -> list[str]:
    """The searchable attributes of ``object_types`` a search covers, narrowed by ``search_fields``."""
    return list(
        dict.fromkeys(
            binding.attributeTypeKey
            for object_type in object_types
            for binding in object_type.attributes
            if model.attribute_type(binding.attributeTypeKey).features.get("searchable")
            and (search_fields is None or binding.attributeTypeKey in search_fields)
        )
    )


def name_contains(column: Any, search: str) -> Any:
    """A case-insensitive literal "contains" match of ``search`` in a name column."""
    return column.ilike(f"%{escape_like(search)}%", escape="\\")


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
        query_error("INVALID_SORT", f"Unknown sort field '{field_name}'", "sort")
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
            lambda raw: [0, parse_typed(definition.valueType, raw)],
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
        query_error("INVALID_SORT", f"Unknown field '{field}'", "sort")
    if definition.valueType == "json":
        query_error("INVALID_SORT", f"Field '{field}' holds JSON and cannot be sorted", "sort")
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
        query_error("INVALID_SORT", f"Field '{field}' is not sortable in this list", "sort")
    if len(object_types) != 1:
        query_error(
            "INVALID_SORT",
            f"Sorting by '{field}' needs one object type; this list holds several",
            "sort",
        )
    if ancestor_type_key not in ancestor_type_keys(model, object_types[0].key):
        query_error(
            "INVALID_SORT",
            f"Object type '{object_types[0].key}' has no ancestor of type '{ancestor_type_key}'",
            "sort",
        )
    return columns.ancestor(statement, ancestor_type_key)


def require_effective_period(object_type: ObjectTypeDefinition, path: str) -> None:
    """``asOf`` needs a declared period; a type without one never infers one from a date field."""
    if object_type.effectivePeriod is None:
        raise api_error(
            422,
            "AS_OF_NOT_SUPPORTED",
            f"Object type '{object_type.key}' declares no effective period, so asOf does not apply",
            {"path": path, "objectTypeKey": object_type.key},
        )


def as_of_predicate(columns: ObjectColumns, object_type: ObjectTypeDefinition, as_of: date) -> Any:
    """Records effective on ``as_of`` by the type's period (ADR-038): no start after the date and
    no end on or before it. An empty start or end is open. It reads the context's typed values, so
    it means the same live, in a change set and in a publication."""
    period = object_type.effectivePeriod
    assert period is not None
    values = columns.values

    def has_value(key: str, comparison: Any) -> Any:
        return exists(
            select(values.sequence_id).where(
                *columns.value_match(values), values.attribute_type_key == key, comparison
            )
        )

    return and_(
        not_(has_value(period.startAttributeTypeKey, values.date_value > as_of)),
        not_(has_value(period.endAttributeTypeKey, values.date_value <= as_of)),
    )


def as_of_filter(as_of: date | None) -> dict[str, Any]:
    """Bind ``asOf`` into a cursor only when set, so cursors issued before it stay valid."""
    return {"asOf": as_of.isoformat()} if as_of is not None else {}


def typed_filter_predicates(
    model: EngineModel,
    columns: ObjectColumns,
    object_types: Sequence[ObjectTypeDefinition],
    filters: list[tuple[str, str, str]],
) -> tuple[list[dict[str, str]], list[Any]]:
    """Parse ``(field, operator, lexical value)`` filters and return them normalized with their
    predicates: equalities on one field are alternatives, everything else is combined with AND."""
    parsed: list[tuple[str, str, Any, str, Any]] = []
    for field, operator, lexical in filters:
        value_type, is_attribute = filter_value_type(model, columns.builtin, object_types, field)
        column = (
            getattr(columns.values, VALUE_COLUMNS[value_type])
            if is_attribute
            else columns.builtin[field]
        )
        if operator not in filter_operators(value_type, attribute=is_attribute):
            query_error(
                "INVALID_FILTER",
                f"Operator '{operator}' is not supported for field '{field}'",
                f"filter.{field}.{operator}",
            )
        value = parse_filter_value(value_type, operator, lexical, field)
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


def filter_value_type(
    model: EngineModel,
    builtin: dict[str, Any],
    object_types: Sequence[ObjectTypeDefinition],
    field: str,
) -> tuple[str, bool]:
    """The value type a filter on ``field`` compares, and whether the field is an attribute.

    A built-in field is one of ``builtin``; an attribute must be bound, filterable and not JSON,
    on a list of one object type.
    """
    if field in builtin:
        return _built_in_value_type(field), False
    return _query_attribute(model, object_types, field, "filterable", "filter").valueType, True


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
        comparison = column.ilike(f"%{escape_like(value)}%", escape="\\")
    elif operator == "startsWith":
        comparison = column.ilike(f"{escape_like(value)}%", escape="\\")
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
        query_error(f"invalid_{parameter}", f"Unknown field '{field}'", parameter)
    if len(object_types) != 1:
        query_error(
            f"invalid_{parameter}",
            f"Field '{field}' needs one object type; this list holds several",
            parameter,
        )
    definition = model.attribute_type(field)
    if definition is None or definition.valueType == "json" or not definition.features.get(capability):
        query_error(
            f"invalid_{parameter}",
            f"Field '{field}' is not {capability}",
            parameter,
        )
    return definition


def _built_in_value_type(field: str) -> str:
    if field in {"createdAt", "updatedAt"}:
        return "dateTime"
    return "text"


def filter_operators(value_type: str, *, attribute: bool) -> set[str]:
    suffix = {"isUnset"} if attribute else set()
    if value_type in {"text", "longText"}:
        return {"eq", "contains", "startsWith", "isNull"} | suffix
    if value_type in {"integer", "decimal", "date", "dateTime"}:
        return {"eq", "lt", "lte", "gt", "gte", "isNull"} | suffix
    if value_type == "boolean":
        return {"eq", "isNull"} | suffix
    return set()


def parse_filter_value(value_type: str, operator: str, lexical: str, field: str) -> Any:
    if operator in {"isNull", "isUnset"}:
        if lexical not in {"true", "false"}:
            query_error("INVALID_FILTER", f"Filter '{operator}' requires true or false", f"filter.{field}.{operator}")
        return lexical == "true"
    try:
        return parse_typed(value_type, lexical)
    except ValueError:
        query_error("INVALID_FILTER", f"Invalid {value_type} value for field '{field}'", f"filter.{field}.{operator}")


def parse_typed(value_type: str, lexical: str) -> Any:
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


def query_error(code: str, message: str, path: str) -> None:
    raise api_error(422, code, message, {"path": f"/query/{path}"})


def escape_like(value: str) -> str:
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
    return parse_filter_value(value_type, "eq", token, "cursor")


def _format_typed_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def live_object_paths(session: Session, objects: list[RdmObject]) -> dict[str, list[dict[str, str]]]:
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
        # Only the columns a path shows: a page of deep records reads each ancestor once per
        # level, and whole records would cost more than the page itself (0.9 Q1).
        parent_map = {
            row.id: row
            for row in session.execute(
                select(
                    RdmObject.id,
                    RdmObject.name,
                    RdmObject.object_type_key,
                    RdmObject.parent_object_id,
                ).where(RdmObject.id.in_(parent_ids))
            )
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
