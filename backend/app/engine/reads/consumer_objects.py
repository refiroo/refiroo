"""The consumer API's shared object, composed for a set of object IDs (Base 0.9 C2).

Every consumer read finds its records in its own way (get by ID by the object ID; lists by parent and
position; XREF by score) and then builds the shared object here, from the definition alone
(CONSUMER_API "The shared object"). The statements are fixed in number, whatever the set's size: one
for the records and their values, one per projection, and one recursive CTE for every ancestor the
objects and their projected records need. Nothing is loaded per object.

Field resolution is the contract's (``consumer_contract``), so the validated contract and the composed
response cannot drift apart. A field takes the first of its sources that has a value, then its
``default``, then ``null``; empty text is no value, as everywhere in the engine (C-D26). Values keep
their declared types in the management API's encoding.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, false, select
from sqlalchemy.orm import Session

from ...common.time import as_utc
from ...errors import api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject
from ...models.schema import ConsumerApiDefinition, EngineModel
from ..model.consumer_contract import (
    BUILT_IN_FIELDS,
    OBJECT_ROLES,
    exposed_types,
    projection_shape,
    source_type,
    split_ancestor_reference,
)
from ..records.values import VALUE_COLUMNS, canonical_decimal, stored_json_value


def consumer_definition(model: EngineModel, api_key: str, contract_version: str) -> ConsumerApiDefinition:
    """The active release's definition ``api_key`` at ``contract_version``, the one it declares (C-D3)."""
    definition = next((item for item in model.consumerApis or () if item.key == api_key), None)
    if definition is None:
        raise api_error(404, "CONSUMER_API_NOT_FOUND", f"Consumer API '{api_key}' not found")
    if contract_version != str(definition.contractVersion):
        raise api_error(
            404,
            "CONTRACT_VERSION_NOT_FOUND",
            f"Consumer API '{api_key}' has no contract version '{contract_version}'; it serves"
            f" version {definition.contractVersion}",
            {"contractVersion": definition.contractVersion},
        )
    return definition


@dataclass(frozen=True)
class _Field:
    """A role or attribute of the shared object: its sources and its encoded default."""

    output: str
    sources: tuple[str, ...]
    default: Any

    def read(self, record: _Record) -> Any:
        for source in self.sources:
            value = record.field(source)
            if value is not None:
                return value
        return self.default


@dataclass
class _Record:
    """One record as the composition reads it: built-in fields and the values it needs."""

    id: str
    type_key: str
    name: str
    parent_id: str | None
    values: dict[str, Any] = field(default_factory=dict)

    def field(self, name: str) -> Any:
        """A built-in field or an attribute value; ``None`` when it has none (empty text is none)."""
        if name == "id":
            return self.id
        if name == "name":
            return self.name
        value = self.values.get(name)
        return None if value == "" else value


@dataclass(frozen=True)
class _Projection:
    output: str
    relation: str
    direction: str
    many: bool
    # Output name to the related record's field, or to (ancestor type, field).
    fields: tuple[tuple[str, str | tuple[str, str]], ...]

    @property
    def attribute_keys(self) -> set[str]:
        return {source for _output, source in self.fields if isinstance(source, str)} - set(BUILT_IN_FIELDS)

    @property
    def ancestor_keys(self) -> set[str]:
        return {source[1] for _output, source in self.fields if isinstance(source, tuple)} - set(BUILT_IN_FIELDS)

    @property
    def reads_ancestors(self) -> bool:
        return any(isinstance(source, tuple) for _output, source in self.fields)


class ConsumerObjects:
    """The shared object of one definition, composed for sets of object IDs."""

    def __init__(self, model: EngineModel, definition: ConsumerApiDefinition) -> None:
        self.definition = definition
        types = exposed_types(model, definition)
        self.public_names = {key: item.publicName for key, item in definition.objectTypes.items()}
        shape = definition.object
        self.roles: dict[str, _Field] = {}
        for role in OBJECT_ROLES:
            declared = getattr(shape, role)
            if declared is not None:
                value_type = source_type(model, types, declared.source)
                self.roles[role] = _Field(
                    declared.output, tuple(declared.source), _encode(value_type, declared.default)
                )
        self.attributes = [
            _Field(name, tuple(item.source), _encode(source_type(model, types, item.source), item.default))
            for name, item in shape.attributes.items()
        ]
        self.parent = shape.parent
        self.path = shape.path
        self.hierarchy = shape.hierarchy
        self.projections = [
            _Projection(
                output=name,
                relation=item.from_.relation,
                direction=item.from_.direction,
                many=projection_shape(model, definition, item.from_.relation, item.from_.direction) == "many",
                fields=tuple(
                    (output, split_ancestor_reference(source) or source)
                    for output, source in item.fields.items()
                ),
            )
            for name, item in definition.projections.items()
        ]
        role_fields = [*self.roles.values()]
        self._own_keys = _attribute_keys([*role_fields, *self.attributes])
        # An ancestor shows through the roles parent, path and hierarchy read.
        ancestor_roles = [self.roles[role] for role in ("id", "code", "name") if role in self.roles]
        self._ancestor_keys = _attribute_keys(ancestor_roles) | {
            key for projection in self.projections for key in projection.ancestor_keys
        }
        self._objects_read_ancestors = bool(self.parent or self.path or self.hierarchy)

    def compose(
        self, session: Session, workspace_key: str, object_ids: Sequence[str]
    ) -> dict[str, dict[str, Any]]:
        """The shared object of each exposed record of ``object_ids`` in the workspace, by ID, in the
        order given; a record of another type or workspace, or no record, is left out."""
        records = _load(
            session,
            select(RdmObject.id, RdmObject.object_type_key, RdmObject.name, RdmObject.parent_object_id)
            .where(
                RdmObject.id.in_(list(object_ids)),
                RdmObject.workspace_key == workspace_key,
                RdmObject.object_type_key.in_(list(self.public_names)),
            )
            .subquery(),
            self._own_keys,
        )
        related = {
            projection.output: self._related(session, workspace_key, projection, list(records))
            for projection in self.projections
        }
        starts = {record.parent_id for record in records.values()} if self._objects_read_ancestors else set()
        for projection in self.projections:
            if projection.reads_ancestors:
                starts |= {item.parent_id for _owner, item in related[projection.output]}
        ancestors = self._ancestors(session, starts - {None})
        return {
            object_id: self._object(records[object_id], related, ancestors)
            for object_id in object_ids
            if object_id in records
        }

    def _related(
        self, session: Session, workspace_key: str, projection: _Projection, owner_ids: list[str]
    ) -> list[tuple[str, _Record]]:
        """``(owner ID, related record)`` for each relationship of the projection, by name then ID."""
        if not owner_ids:
            return []
        outgoing = projection.direction == "outgoing"
        own = ObjectRelation.from_object_id if outgoing else ObjectRelation.to_object_id
        other = ObjectRelation.to_object_id if outgoing else ObjectRelation.from_object_id
        pairs = (
            select(
                own.label("owner_id"),
                RdmObject.id,
                RdmObject.object_type_key,
                RdmObject.name,
                RdmObject.parent_object_id,
            )
            .join(RdmObject, RdmObject.id == other)
            .where(
                ObjectRelation.relation_type_key == projection.relation,
                own.in_(owner_ids),
                RdmObject.workspace_key == workspace_key,
            )
            .subquery()
        )
        rows = _rows(session, pairs, projection.attribute_keys, extra=(pairs.c.owner_id,))
        found: dict[tuple[str, str], _Record] = {}
        for row in rows:
            record = found.setdefault((row.owner_id, row.id), _record(row))
            _add_value(record, row)
        return [(owner, record) for (owner, _id), record in found.items()]

    def _ancestors(self, session: Session, starts: set[str]) -> dict[str, _Record]:
        """Every record above ``starts``, with them, in one recursive statement."""
        if not starts:
            return {}
        up = (
            select(RdmObject.id, RdmObject.parent_object_id)
            .where(RdmObject.id.in_(sorted(starts)))
            .cte("up", recursive=True)
        )
        up = up.union(
            select(RdmObject.id, RdmObject.parent_object_id).join(up, RdmObject.id == up.c.parent_object_id)
        )
        chain = (
            select(RdmObject.id, RdmObject.object_type_key, RdmObject.name, RdmObject.parent_object_id)
            .join(up, up.c.id == RdmObject.id)
            .subquery()
        )
        return _load(session, chain, self._ancestor_keys)

    def _object(
        self,
        record: _Record,
        related: dict[str, list[tuple[str, _Record]]],
        ancestors: dict[str, _Record],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"objectType": self.public_names[record.type_key]}
        for item in self.roles.values():
            result[item.output] = item.read(record)
        for item in self.attributes:
            result[item.output] = item.read(record)
        chain = _chain(record.parent_id, ancestors)
        if self.parent is not None:
            result[self.parent.output] = self._parent(chain[0]) if chain else None
        if self.path is not None or self.hierarchy is not None:
            names = [self._name(item) for item in reversed(chain)]
            if self.path is not None:
                result[self.path] = "/".join(names)
            if self.hierarchy is not None:
                result[self.hierarchy] = names
        for projection in self.projections:
            items = [
                {
                    output: _projected(item, source, ancestors)
                    for output, source in projection.fields
                }
                for owner, item in related[projection.output]
                if owner == record.id
            ]
            result[projection.output] = items if projection.many else (items[0] if items else None)
        return result

    def _parent(self, parent: _Record) -> dict[str, Any]:
        values = {
            "objectType": self.public_names.get(parent.type_key),
            "id": self.roles["id"].read(parent),
            "code": self.roles["code"].read(parent) if "code" in self.roles else None,
            "name": self._name(parent),
        }
        assert self.parent is not None
        return {name: values[name] for name in self.parent.fields}

    def _name(self, record: _Record) -> Any:
        """The ``name`` role, falling back to the built-in name."""
        role = self.roles.get("name")
        value = role.read(record) if role is not None else None
        return record.name if value is None else value


def _projected(record: _Record, source: str | tuple[str, str], ancestors: dict[str, _Record]) -> Any:
    if isinstance(source, str):
        return record.field(source)
    type_key, name = source
    for item in _chain(record.parent_id, ancestors):
        if item.type_key == type_key:
            return item.field(name)
    return None


def _chain(parent_id: str | None, ancestors: dict[str, _Record]) -> list[_Record]:
    """The ancestors from the parent up to the top."""
    chain: list[_Record] = []
    seen: set[str] = set()
    while parent_id is not None and parent_id in ancestors and parent_id not in seen:
        seen.add(parent_id)
        chain.append(ancestors[parent_id])
        parent_id = ancestors[parent_id].parent_id
    return chain


def _attribute_keys(fields: Iterable[_Field]) -> set[str]:
    return {source for item in fields for source in item.sources} - set(BUILT_IN_FIELDS)


_VALUE_COLUMNS = sorted(set(VALUE_COLUMNS.values()))


def _rows(session: Session, records: Any, keys: set[str], extra: tuple[Any, ...] = ()) -> Sequence[Any]:
    """The rows of ``records`` with their values of ``keys``, one row per value (or one without)."""
    value_columns = [getattr(AttributeValue, name).label(name) for name in _VALUE_COLUMNS]
    statement: Select[Any] = (
        select(
            *extra,
            records.c.id,
            records.c.object_type_key,
            records.c.name,
            records.c.parent_object_id,
            AttributeValue.attribute_type_key,
            AttributeValue.value_type,
            *value_columns,
        )
        .select_from(records)
        .outerjoin(
            AttributeValue,
            and_(
                AttributeValue.object_id == records.c.id,
                AttributeValue.attribute_type_key.in_(sorted(keys)) if keys else false(),
            ),
        )
        .order_by(records.c.name, records.c.id)
    )
    return session.execute(statement).all()


def _load(session: Session, records: Any, keys: set[str]) -> dict[str, _Record]:
    found: dict[str, _Record] = {}
    for row in _rows(session, records, keys):
        _add_value(found.setdefault(row.id, _record(row)), row)
    return found


def _record(row: Any) -> _Record:
    return _Record(row.id, row.object_type_key, row.name, row.parent_object_id)


def _add_value(record: _Record, row: Any) -> None:
    if row.attribute_type_key is not None:
        record.values[row.attribute_type_key] = stored_json_value(
            getattr(row, VALUE_COLUMNS[row.value_type])
        )


def _encode(value_type: str | None, default: Any) -> Any:
    """A definition's default in the encoding values have (validation checked its type)."""
    if default is None:
        return None
    if value_type == "decimal":
        return format(canonical_decimal(Decimal(str(default))), "f")
    if value_type == "dateTime":
        return as_utc(datetime.fromisoformat(default)).isoformat()
    return default


def read_consumer_object(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace_key: str,
    object_id: str,
) -> dict[str, Any]:
    """Get by ID: the shared object of the record with this object ID (C-D24), or
    ``404 OBJECT_NOT_FOUND`` for an unknown or deleted record, one in another workspace, or one of a
    type the definition does not expose."""
    composed = ConsumerObjects(model, definition).compose(session, workspace_key, [object_id])
    if object_id not in composed:
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
    return composed[object_id]

