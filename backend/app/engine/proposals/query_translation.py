"""A question in words becomes the filters of a table list (Product 0.16 AG4).

The model builds a query and nothing else: it is sent the question, today's date and the list's
fields, conditions and relationships with their labels and the names of the types a relationship's
records can sit under. Where the send level allows values (``samples`` or ``values``) and the types a
relationship reaches, with those they can sit under, hold at most ``SHORT_LIST`` records in the
context asked about, it is also sent those records' names, so it can choose them by their meaning
("above 100 km" from "120 km"); no other value, no ID (AG-D35, revised 2026-11-01). What comes
back is checked here before the person sees it:

* a filter on a field the list does not offer, or with a condition the field does not take, makes the
  whole answer a failed call, recorded as such, and nothing is applied (AG-D38);
* a record named in words is looked up in the database, in the context asked about, among the proper
  types: the exact name first, ignoring case, otherwise one record whose name contains it. None or
  several is a part the list cannot express, with the reason, never a guess (AG-D37);
* each filter then goes through the list's own validation, by building the list's statement with it,
  so a filter the list would refuse is refused here.

When any part is not expressed ``applied`` is false: the filters that could be built are still
returned, for the person to take or change. The route releases its transaction before the provider
is called and holds none while it answers (J48.8).
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, NoReturn

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import AiCall, RdmObject
from ...models.schema import EngineModel, ObjectTypeDefinition, TableViewDefinition
from ..model.candidates import filter_operators
from ..model.related_columns import RelatedKeyError, is_related_field, related_field_column
from ..model.traversal import ancestor_type_keys
from ..reads.model_query import list_relation_filters, split_relation_filters
from ..reads.object_query import build_object_query, name_contains
from ..reads.snapshot_reads import (
    SnapshotContext,
    build_snapshot_object_query,
    object_projection,
)
from . import calls
from .context import Policy
from .provider import ProposalRequest
from .registry import AiConfiguration

PROMPT_VERSION = "query-translation/3"
# The longest question the route takes.
MAX_QUESTION = 500
# Stamps every record carries, offered on a live list without being declared (AG-D33).
TIMESTAMPS = {"createdAt": "Created", "updatedAt": "Updated"}
BUILT_IN = {"name": "Name", "id": "ID", **TIMESTAMPS}
RELATION_CONDITIONS = ("eq", "isNull", "under", "notUnder")
RECORD_CONDITIONS = ("eq", "under", "notUnder")
# How many records a lookup reads to say which several match.
SEVERAL = 5
# The most records a relationship's type set may hold for their names to be sent (2026-11-01).
SHORT_LIST = 50

INSTRUCTIONS = """You turn a question about a list of records into filters on that list.
The context holds the question, today's date and the list's fields. Each field has a key, a label, a kind and the conditions it takes.
Answer with filters, a search text and the parts you cannot express.
- A filter names a field by its key and a condition from that field's list, and a value as text.
- Dates are written yyyy-mm-dd; a day given for a date-time field means the whole day. Work out relative dates ("last month", "this year") from today's date.
- Yes or no values are true or false. The conditions isNull and isUnset take the value true or false.
- A condition on a relationship (eq, under, notUnder) takes the name of a record. under and notUnder mean a related record at any depth below the record named; they are offered only where the relationship lists the types it can sit under.
- Where a relationship lists recordNames (or, for under and notUnder, ancestorNames), those are all the records there are. Choose records by understanding their names, also by meaning: "above 100 km" with names such as "50 km", "120 km" and "300 km" means 120 km and 300 km. Give one eq filter per chosen record with its name exactly as listed; several eq filters on one relationship mean any of them. Choose only from the names listed and never invent one. Where a relationship lists no names, give the name as the person wrote it.
- If no listed name fits a part of the question, or the question compares in a way the names cannot answer, that part goes to notExpressed.
- When the question names what a relationship's records stand under (the relationship lists canSitUnder types), "with" it is under and "without" it is notUnder, with the name given. isNull is only for "has none at all" and says nothing about any named record.
- search is words to look for in the records' names, only when the question asks for a word or name that no field covers. Otherwise leave it empty.
- Every part of the question must end up as a filter, in search or in notExpressed; never leave a part out. A word that names the kind of record asked for ("trains") is a part: when a relationship lists names that contain it, choose those records with eq filters, otherwise put it in search.
- Everything the filters and the search cannot say goes to notExpressed, with the words of the question (part) and why (reason). Asking for an order or a sort, for who changed a record, or for a field not in the context is never expressed.
- Never approximate. Never invent a field or a condition. Do not repeat the question in filters."""


class _Filter(BaseModel):
    field: str
    condition: str
    value: str


class _NotExpressed(BaseModel):
    part: str
    reason: str


class TranslationAnswer(BaseModel):
    """What the provider answers: the filters, a search text and the parts it cannot express."""

    filters: list[_Filter] = Field(default_factory=list)
    search: str = ""
    notExpressed: list[_NotExpressed] = Field(default_factory=list)


@dataclass(frozen=True)
class ListField:
    """One field the answer may use on a list."""

    key: str
    label: str
    kind: str  # text, number, date, boolean or relationship
    conditions: tuple[str, ...]
    # A relationship's own: the types at its far end, and the types they can sit under.
    record_types: tuple[ObjectTypeDefinition, ...] = ()
    ancestor_types: tuple[ObjectTypeDefinition, ...] = ()
    # The names of those types' records, when the send level allows them and the list is short.
    record_names: tuple[str, ...] | None = None
    ancestor_names: tuple[str, ...] | None = None

    def shown(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "field": self.key,
            "label": self.label,
            "kind": self.kind,
            "conditions": list(self.conditions),
        }
        if self.kind == "relationship":
            entry["recordTypes"] = [item.name for item in self.record_types]
            if self.ancestor_types:
                entry["canSitUnder"] = [item.name for item in self.ancestor_types]
            if self.record_names is not None:
                entry["recordNames"] = list(self.record_names)
            if self.ancestor_names is not None:
                entry["ancestorNames"] = list(self.ancestor_names)
        return entry


@dataclass(frozen=True)
class ProposedFilter:
    field: str
    operator: str
    value: str


@dataclass(frozen=True)
class Unexpressed:
    part: str
    reason: str


@dataclass(frozen=True)
class Translation:
    filters: list[ProposedFilter]
    search: str
    not_expressed: list[Unexpressed]

    @property
    def applied(self) -> bool:
        return not self.not_expressed


@dataclass(frozen=True)
class _Prepared:
    """What the route reads before the provider is called, and nothing that holds the database."""

    table: TableViewDefinition
    fields: dict[str, ListField]
    request: ProposalRequest
    object_type: ObjectTypeDefinition


def table_view(model: EngineModel, application_key: str, view_key: str) -> TableViewDefinition:
    """The table view asked about; another view type has no filters to build (AG-D34)."""
    application = next((item for item in model.applications if item.key == application_key), None)
    view = (
        next((item for item in application.views if item.key == view_key), None)
        if application
        else None
    )
    if view is None:
        raise api_error(404, "VIEW_NOT_FOUND", "View not found in the selected model")
    if not isinstance(view, TableViewDefinition):
        raise api_error(
            422,
            "QUERY_TRANSLATION_VIEW_UNSUPPORTED",
            f"A question in words applies to a table view; '{view.key}' is a {view.type} view",
            {"viewKey": view.key, "viewType": view.type},
        )
    return view


def list_fields(
    model: EngineModel, view: TableViewDefinition, *, live: bool
) -> dict[str, ListField]:
    """The fields an answer may use: the view's filter fields, every relationship the listed type has
    in either direction (the list's filters take any, declared or not), and on a live list the two
    stamps."""
    object_type = model.object_type(view.objectTypeKey)
    assert object_type is not None
    keys = list(dict.fromkeys(view.config.filterFields))
    keys += [key for key in relationship_fields(model, object_type.key) if key not in keys]
    if live:
        keys += [key for key in TIMESTAMPS if key not in keys]
    found: dict[str, ListField] = {}
    for key in keys:
        if is_related_field(key):
            relationship = _relationship(model, object_type, key)
            if relationship is not None:
                found[key] = relationship
        elif key in BUILT_IN:
            kind = "date" if key in TIMESTAMPS else "text"
            value_type = "dateTime" if key in TIMESTAMPS else "text"
            found[key] = ListField(
                key,
                BUILT_IN[key],
                kind,
                tuple(sorted(filter_operators(value_type, attribute=False))),
            )
        else:
            attribute = model.attribute_type(key)
            if attribute is None:
                continue
            operators = filter_operators(attribute.valueType, attribute=True)
            if operators:
                found[key] = ListField(
                    key, attribute.name, _kind(attribute.valueType), tuple(sorted(operators))
                )
    return found


def relationship_fields(model: EngineModel, object_type_key: str) -> list[str]:
    """``related:<key>`` of each relationship the type has: the relation's key where the type is at
    the ``from`` end of a binding, its reverse key where it is at the ``to`` end."""
    found: list[str] = []
    for relation in model.relationTypes:
        bindings = [b for b in model.objectTypeRelations if b.relationTypeKey == relation.key]
        if any(b.fromObjectTypeKey == object_type_key for b in bindings):
            found.append(f"related:{relation.key}")
        if relation.reverseKey and any(b.toObjectTypeKey == object_type_key for b in bindings):
            found.append(f"related:{relation.reverseKey}")
    return list(dict.fromkeys(found))


def _kind(value_type: str) -> str:
    if value_type in {"integer", "decimal"}:
        return "number"
    if value_type in {"date", "dateTime"}:
        return "date"
    return "boolean" if value_type == "boolean" else "text"


def _relationship(
    model: EngineModel, object_type: ObjectTypeDefinition, key: str
) -> ListField | None:
    try:
        column = related_field_column(model, object_type.key, key.removeprefix("related:"))
    except RelatedKeyError:
        return None
    if column.field is not None:
        return None
    relation = model.relation_type(column.relation_type_key)
    assert relation is not None
    label = relation.name if column.direction == "outgoing" else relation.reverseName
    targets = tuple(
        item
        for item in (model.object_type(type_key) for type_key in column.target_type_keys)
        if item is not None
    )
    above = sorted({above for item in targets for above in ancestor_type_keys(model, item.key)})
    ancestors = tuple(item for item in (model.object_type(type_key) for type_key in above) if item)
    conditions = RELATION_CONDITIONS if ancestors else ("eq", "isNull")
    return ListField(key, label, "relationship", conditions, targets, ancestors)


def prepare(
    model: EngineModel,
    application_key: str,
    view_key: str,
    question: str,
    *,
    live: bool,
    today: date,
) -> _Prepared:
    """The request for the provider: the question, today and the list's fields (no record value)."""
    view = table_view(model, application_key, view_key)
    fields = list_fields(model, view, live=live)
    object_type = model.object_type(view.objectTypeKey)
    assert object_type is not None
    request = ProposalRequest(
        purpose="queryTranslation",
        instructions=INSTRUCTIONS,
        prompt_version=PROMPT_VERSION,
        context={
            "question": question,
            "today": today.isoformat(),
            "list": {"name": view.name, "records": object_type.pluralName},
            "fields": [item.shown() for item in fields.values()],
        },
        answer=TranslationAnswer,
    )
    return _Prepared(view, fields, request, object_type)


def with_names(
    session: Session,
    prepared: _Prepared,
    policy: Policy,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> _Prepared:
    """Add to each relationship the names of the records of the types it reaches and of those they
    can sit under, when the send level in force allows values (``samples`` or ``values``) and that
    type set holds at most ``SHORT_LIST`` records in the context asked about. One set statement reads
    each type set; at ``structure``, or for a longer set, no name is read or sent. The caller releases
    its transaction before the provider is called."""
    if not policy.allows("samples"):
        return prepared
    read: dict[frozenset[str], dict[str, list[str]] | None] = {}
    fields: dict[str, ListField] = {}
    for key, spec in prepared.fields.items():
        if spec.kind != "relationship":
            fields[key] = spec
            continue
        type_keys = frozenset(item.key for item in (*spec.record_types, *spec.ancestor_types))
        if type_keys not in read:
            read[type_keys] = _short_names(session, sorted(type_keys), workspace_key, context)
        names = read[type_keys]
        if names is None:
            fields[key] = spec
            continue
        fields[key] = replace(
            spec,
            record_names=_names_of(names, spec.record_types),
            ancestor_names=_names_of(names, spec.ancestor_types) if spec.ancestor_types else None,
        )
    shown = {**prepared.request.context, "fields": [item.shown() for item in fields.values()]}
    return replace(prepared, fields=fields, request=replace(prepared.request, context=shown))


def _names_of(
    names: dict[str, list[str]], types: Sequence[ObjectTypeDefinition]
) -> tuple[str, ...]:
    return tuple(sorted({name for item in types for name in names.get(item.key, [])}))


def _short_names(
    session: Session, type_keys: list[str], workspace_key: str, context: SnapshotContext | None
) -> dict[str, list[str]] | None:
    """The names of the records of these types by type, in one statement, or ``None`` when they
    hold more than ``SHORT_LIST`` records."""
    if not type_keys:
        return {}
    if context is None:
        statement: Select[Any] = select(RdmObject.object_type_key, RdmObject.name).where(
            RdmObject.workspace_key == workspace_key, RdmObject.object_type_key.in_(type_keys)
        )
    else:
        records = object_projection(context, object_type_keys=type_keys)
        statement = select(records.c.object_type_key, records.c.name).select_from(records)
    rows = session.execute(statement.limit(SHORT_LIST + 1)).all()
    if len(rows) > SHORT_LIST:
        return None
    found: dict[str, list[str]] = {}
    for type_key, name in rows:
        found.setdefault(type_key, []).append(name)
    return found


def finish(
    session: Session,
    ai: AiConfiguration,
    prepared: _Prepared,
    model: EngineModel,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
    application_key: str,
    requester: calls.Requester,
) -> Translation:
    """Ask the provider, then check and resolve what it answered. The caller has released its
    transaction; a failure of any kind is a recorded failed call and ``502 QUERY_TRANSLATION_FAILED``,
    with nothing applied."""
    recorded: list[AiCall] = []
    record = calls.record_in(session)

    def keep(row: AiCall) -> None:
        record(row)
        recorded.append(row)

    outcome = calls.ask(ai, prepared.request, record=keep, requester=requester)
    if outcome.answer is None:
        _failed(session, outcome.call_id, outcome.failure or "The provider did not answer")
    assert isinstance(outcome.answer, TranslationAnswer)
    try:
        return _check(
            session,
            prepared,
            model,
            outcome.answer,
            workspace_key=workspace_key,
            context=context,
            application_key=application_key,
        )
    except _Refused as refused:
        row = recorded[0]
        row.outcome, row.failure_kind, row.failure = "failed", "malformed", refused.reason
        _failed(session, outcome.call_id, refused.reason)


class _Refused(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _failed(session: Session, call_id: str, reason: str) -> NoReturn:
    session.commit()
    raise api_error(
        502,
        "QUERY_TRANSLATION_FAILED",
        f"The question could not be turned into filters: {reason}",
        {"callId": call_id},
    )


def _check(
    session: Session,
    prepared: _Prepared,
    model: EngineModel,
    answer: TranslationAnswer,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
    application_key: str,
) -> Translation:
    not_expressed = [
        Unexpressed(item.part.strip(), item.reason.strip()) for item in answer.notExpressed
    ]
    proposed: list[ProposedFilter] = []
    for item in answer.filters:
        spec = prepared.fields.get(item.field)
        if spec is None:
            raise _Refused(f"the answer names a field the list does not offer ('{item.field}')")
        if item.condition not in spec.conditions:
            raise _Refused(
                f"the answer uses a condition '{item.condition}' that '{spec.label}' does not take"
            )
        if spec.kind == "relationship" and item.condition in RECORD_CONDITIONS:
            resolved = _resolve(session, model, spec, item, workspace_key, context)
            if isinstance(resolved, Unexpressed):
                not_expressed.append(resolved)
                continue
            proposed.append(ProposedFilter(item.field, item.condition, resolved))
        else:
            proposed.append(ProposedFilter(item.field, item.condition, item.value.strip()))
    _validate(
        model,
        prepared,
        proposed,
        answer.search.strip(),
        workspace_key=workspace_key,
        context=context,
        application_key=application_key,
    )
    if not (proposed or answer.search.strip() or not_expressed):
        not_expressed.append(
            Unexpressed(
                prepared.request.context["question"],
                "Nothing in it could be turned into a filter or a search of this list",
            )
        )
    return Translation(proposed, answer.search.strip(), not_expressed)


def _validate(
    model: EngineModel,
    prepared: _Prepared,
    proposed: Sequence[ProposedFilter],
    search: str,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
    application_key: str,
) -> None:
    """The list's own validation: build its statement with these filters. A refusal ends the call."""
    triples = [(item.field, item.operator, item.value) for item in proposed]
    related, plain = split_relation_filters(triples)
    type_key = prepared.object_type.key
    try:
        relations = list_relation_filters(
            model, type_key, related, workspace_key=workspace_key, context=context
        )
        if context is None:
            build_object_query(
                model,
                object_type_key=type_key,
                application_key=application_key,
                workspace_key=workspace_key,
                parent_object_id=None,
                search=search or None,
                sort=None,
                field_filters=plain,
                id_filter=relations.id_filter,
            )
        else:
            build_snapshot_object_query(
                model,
                context,
                object_type_key=type_key,
                application_key=application_key,
                parent_object_id=None,
                search=search or None,
                sort=None,
                field_filters=plain,
                id_filter=relations.id_filter,
            )
    except ApiError as error:
        raise _Refused(f"the list refuses it ({error.message})") from error


def _resolve(
    session: Session,
    model: EngineModel,
    spec: ListField,
    item: _Filter,
    workspace_key: str,
    context: SnapshotContext | None,
) -> str | Unexpressed:
    """The ID of the record a filter names in words, or why it cannot be one (AG-D37)."""
    name = item.value.strip()
    types = spec.ancestor_types if item.condition in {"under", "notUnder"} else spec.record_types
    keys = sorted(entry.key for entry in types)
    noun = " or ".join(f"'{entry.name}'" for entry in types) or "record"
    if not name:
        return Unexpressed(spec.label, f"No {noun} was named")
    for exact in (True, False):
        found = _lookup(session, keys, name, exact, workspace_key, context)
        if len(found) == 1:
            return found[0][0]
        if len(found) > 1:
            names = ", ".join(f"'{entry[1]}'" for entry in found[:SEVERAL])
            more = ", and more" if len(found) > SEVERAL else ""
            kind = "are named" if exact else "have a name containing"
            return Unexpressed(
                f'"{name}"',
                f'Several {noun} records {kind} "{name}": {names}{more}. Name one of them exactly',
            )
    return Unexpressed(f'"{name}"', f'No {noun} record is named or contains "{name}" here')


def _lookup(
    session: Session,
    type_keys: list[str],
    name: str,
    exact: bool,
    workspace_key: str,
    context: SnapshotContext | None,
) -> list[tuple[str, str]]:
    """Up to ``SEVERAL + 1`` records of the types whose name is ``name`` (ignoring case), or
    contains it, in the live workspace or the change set or publication."""
    if context is None:
        statement: Select[Any] = select(RdmObject.id, RdmObject.name).where(
            RdmObject.workspace_key == workspace_key, RdmObject.object_type_key.in_(type_keys)
        )
        column = RdmObject.name
        order = RdmObject.id
    else:
        records = object_projection(context, object_type_keys=type_keys)
        statement = select(records.c.object_id, records.c.name).select_from(records)
        column = records.c.name
        order = records.c.object_id
    statement = statement.where(
        func.lower(column) == func.lower(name) if exact else name_contains(column, name)
    )
    return [
        (row[0], row[1]) for row in session.execute(statement.order_by(order).limit(SEVERAL + 1))
    ]
