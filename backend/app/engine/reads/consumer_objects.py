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

from sqlalchemy import ARRAY, Select, String, and_, any_, bindparam, false, select, true
from sqlalchemy.orm import Session

from ...common.time import as_utc
from ...errors import ApiError, api_error
from ...models.schema import (
    PARENT_BLOCK_PREFIX,
    ConsumerApiDefinition,
    ConsumerProjection,
    EngineModel,
)
from ..model.consumer_contract import (
    BUILT_IN_FIELDS,
    OBJECT_ROLES,
    PROJECTION_TYPE_SOURCE,
    RELATION_REFERENCE_PREFIX,
    block_shape,
    exposed_types,
    parent_source_type,
    parent_types,
    source_type,
    split_ancestor_reference,
)
from ..model.consumer_definitions import ServedVersion, served_versions
from ..records.values import VALUE_COLUMNS, canonical_decimal, stored_json_value
from .consumer_parameters import (
    NO_FILTER,
    ConsumerFilter,
    ItemPredicate,
    Target,
    as_of_not_supported,
)
from .consumer_source import ConsumerSource

# The targets an ambiguous crosswalk names, as many as an ambiguous match's candidates (C-D55).
AMBIGUOUS_TARGETS = 10


def served_consumer_version(model: EngineModel, consumer_api: str, contract_version: str) -> ServedVersion:
    """The version ``contract_version`` of ``consumer_api`` the model serves (C-D3): the current one,
    or an earlier one it keeps (0.13 DF3)."""
    versions = served_versions(model, consumer_api)
    if not versions:
        raise api_error(404, "CONSUMER_API_NOT_FOUND", f"Consumer API '{consumer_api}' not found")
    found = next((item for item in versions if str(item.definition.contractVersion) == contract_version), None)
    if found is None:
        served = [item.definition.contractVersion for item in versions]
        noun = "version" if len(served) == 1 else "versions"
        raise api_error(
            404,
            "CONTRACT_VERSION_NOT_FOUND",
            f"Consumer API '{consumer_api}' has no contract version '{contract_version}'; it serves"
            f" {noun} {', '.join(str(number) for number in served)}",
            {"contractVersion": served[0], "servedContractVersions": served},
        )
    return found


def consumer_definition(model: EngineModel, consumer_api: str, contract_version: str) -> ConsumerApiDefinition:
    """The definition ``consumer_api`` serves at ``contract_version``: the active release's current
    one, or an earlier one it keeps (C-D3, 0.13 DF3)."""
    return served_consumer_version(model, consumer_api, contract_version).definition


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
    # The key in the answer; ``name`` is what filters and ``include`` call it (``parent.<output>`` for
    # a block of the parent, CA1).
    output: str
    name: str
    served: str
    relation: str
    direction: str
    many: bool
    # Output name to the related record's field, or to (ancestor type, field).
    fields: tuple[tuple[str, str | tuple[str, str]], ...]

    @property
    def attribute_keys(self) -> set[str]:
        sources = {source for _output, source in self.fields if isinstance(source, str)}
        return {
            source for source in sources if not source.startswith(RELATION_REFERENCE_PREFIX)
        } - set(BUILT_IN_FIELDS) - {PROJECTION_TYPE_SOURCE}

    @property
    def reads_relation(self) -> bool:
        """Whether a field reads the relationship's own values (``relation:<attribute>``)."""
        return any(
            isinstance(source, str) and source.startswith(RELATION_REFERENCE_PREFIX)
            for _output, source in self.fields
        )

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
        # The parent's fields by output name, read as the object's own are (CA1).
        parents = parent_types(model, definition)
        role_types = {
            role: source_type(model, types, getattr(shape, role).source)
            for role in OBJECT_ROLES
            if getattr(shape, role) is not None
        }
        self.parent_fields = (
            {
                output: _Field(
                    output,
                    tuple(item.source),
                    _encode(parent_source_type(model, parents, role_types, item.source), item.default),
                )
                for output, item in shape.parent.fields.items()
            }
            if shape.parent is not None
            else {}
        )
        self.path = shape.path
        self.hierarchy = shape.hierarchy
        self.projections = [
            self._block(model, definition, name, name, item) for name, item in definition.projections.items()
        ]
        self.parent_projections = (
            []
            if shape.parent is None
            else [
                self._block(model, definition, f"{PARENT_BLOCK_PREFIX}{name}", name, item)
                for name, item in shape.parent.projections.items()
            ]
        )
        role_fields = [*self.roles.values()]
        self._own_keys = _attribute_keys([*role_fields, *self.attributes])
        # An ancestor shows through the roles parent, path and hierarchy read, the sources the parent
        # shows and the blocks' ancestor fields.
        ancestor_roles = [self.roles[role] for role in ("id", "code", "name") if role in self.roles]
        parent_sources = {name for item in self.parent_fields.values() for name in item.sources}
        self._ancestor_keys = (
            _attribute_keys(ancestor_roles)
            | {key for projection in self._blocks() for key in projection.ancestor_keys}
            | {name for name in parent_sources if split_ancestor_reference(name) is None}
            | {ref[1] for name in parent_sources if (ref := split_ancestor_reference(name)) is not None}
        ) - set(BUILT_IN_FIELDS)
        self._objects_read_ancestors = bool(self.parent or self.path or self.hierarchy)

    @staticmethod
    def _block(
        model: EngineModel, definition: ConsumerApiDefinition, name: str, output: str, item: ConsumerProjection
    ) -> _Projection:
        return _Projection(
            output=output,
            name=name,
            served=item.served,
            relation=item.from_.relation,
            direction=item.from_.direction,
            many=block_shape(model, definition, name) == "many",
            fields=tuple(
                (field, split_ancestor_reference(source) or source) for field, source in item.fields.items()
            ),
        )

    def _blocks(self) -> list[_Projection]:
        return [*self.projections, *self.parent_projections]

    def compose(
        self,
        session: Session,
        source: ConsumerSource,
        object_ids: Sequence[str],
        narrowed: ConsumerFilter = NO_FILTER,
    ) -> dict[str, dict[str, Any]]:
        """The shared object of each exposed record of ``object_ids`` in the source (the workspace's
        live data or a publication), by ID, in the
        order given; a record of another type or workspace, or no record, is left out, and so is one
        ``narrowed``'s parameters filter out. They also limit the projections' items (C3); with a
        crosswalk target, each object carries its projection's items again as ``target``, in the
        projection's shape (C15)."""
        objects = source.objects
        records = _load(
            session,
            source,
            select(objects.id, objects.object_type_key, objects.name, objects.parent_object_id)
            .where(
                objects.id.in_(list(object_ids)),
                objects.workspace_key == source.workspace_key,
                objects.object_type_key.in_(list(self.public_names)),
                *narrowed.on(objects),
            )
            .subquery(),
            self._own_keys,
        )
        include = narrowed.include
        target = narrowed.target
        # A block served on request is read only when the request names it, or a crosswalk shows it as
        # ``target``; a filter still limits and narrows it unread (CA1, PP-D32).
        wanted = [
            item
            for item in self._blocks()
            if item.served == "always" or item.name in include or (target is not None and item.name == target.projection)
        ]
        parent_ids = sorted({record.parent_id for record in records.values() if record.parent_id is not None})
        related = {
            item.name: self._related(
                session,
                source,
                item,
                list(records) if item.name == item.output else parent_ids,
                narrowed.limits.get(item.name),
            )
            for item in wanted
        }
        starts = {record.parent_id for record in records.values()} if self._objects_read_ancestors else set()
        for item in wanted:
            if item.reads_ancestors:
                starts |= {found.parent_id for _owner, found in related[item.name]}
        ancestors = self._ancestors(session, source, starts - {None})
        return {
            object_id: self._object(records[object_id], related, ancestors, narrowed)
            for object_id in object_ids
            if object_id in records
        }

    def identities(
        self, session: Session, source: ConsumerSource, object_ids: Sequence[str]
    ) -> dict[str, tuple[Any, Any]]:
        """The ``code`` and ``name`` of each record of ``object_ids`` the source holds, of any type,
        as the object's roles read them (the name falling back to the built-in name), in one
        statement: what a consumer event names its object by (C10, C-D89)."""
        objects = source.objects
        keys = _attribute_keys([self.roles[role] for role in ("code", "name") if role in self.roles])
        records = _load(
            session,
            source,
            select(objects.id, objects.object_type_key, objects.name, objects.parent_object_id)
            .where(objects.id.in_(list(object_ids)), objects.workspace_key == source.workspace_key)
            .subquery(),
            keys,
        )
        code = self.roles.get("code")
        return {
            object_id: (code.read(record) if code is not None else None, self._name(record))
            for object_id, record in records.items()
        }

    def _related(
        self,
        session: Session,
        source: ConsumerSource,
        projection: _Projection,
        owner_ids: list[str],
        limit: ItemPredicate | None,
    ) -> list[tuple[str, _Record]]:
        """``(owner ID, related record)`` for each relationship of the projection, by name then ID;
        ``limit`` keeps only the related records it holds for."""
        if not owner_ids:
            return []
        outgoing = projection.direction == "outgoing"
        relations, objects = source.relations, source.objects
        own = relations.from_object_id if outgoing else relations.to_object_id
        other = relations.to_object_id if outgoing else relations.from_object_id
        pairs = (
            select(
                own.label("owner_id"),
                objects.id,
                objects.object_type_key,
                objects.name,
                objects.parent_object_id,
                *([relations.attributes.label("relation_attributes")] if projection.reads_relation else []),
            )
            .select_from(relations)
            .join(objects, objects.id == other)
            .where(
                relations.relation_type_key == projection.relation,
                own.in_(owner_ids),
                objects.workspace_key == source.workspace_key,
                *([] if limit is None else [limit(objects, relations)]),
            )
            .subquery()
        )
        rows = _rows(
            session,
            source,
            pairs,
            projection.attribute_keys,
            extra=(pairs.c.owner_id, *([pairs.c.relation_attributes] if projection.reads_relation else [])),
        )
        found: dict[tuple[str, str], _Record] = {}
        for row in rows:
            record = found.get((row.owner_id, row.id))
            if record is None:
                record = found[(row.owner_id, row.id)] = _record(row)
                if projection.reads_relation:
                    # The relationship's own values, from the same rows the relation is (live or a
                    # publication's); a value the relationship has not set stays absent.
                    for key, value in (row.relation_attributes or {}).items():
                        record.values[f"{RELATION_REFERENCE_PREFIX}{key}"] = value
            _add_value(record, row)
        return [(owner, record) for (owner, _id), record in found.items()]

    def _ancestors(self, session: Session, source: ConsumerSource, starts: set[str]) -> dict[str, _Record]:
        """Every record above ``starts``, with them: the walk's IDs in one recursive statement, then
        those records and their values by the list of IDs.

        Each step of the walk finds the parent by its ID through a bounded ``LATERAL``, an index
        probe PostgreSQL cannot flatten into a join; the records are then read by a bound list, as a
        filter's walked containers are (``consumer_parameters.below``). Read as one statement,
        PostgreSQL estimated the walk a hundred times too large (54,540 rows for 540 at full volume)
        and hashed every record and every value: 192 ms where the walk reads 540 rows (0.9 C14b)."""
        if not starts:
            return {}
        objects = source.objects
        up = select(objects.id, objects.parent_object_id).where(objects.id.in_(sorted(starts))).cte(
            "up", recursive=True
        )
        parent = source.object_alias()
        step = (
            select(parent.id, parent.parent_object_id)
            .where(parent.id == up.c.parent_object_id)
            .limit(1)
            .lateral("parent")
        )
        up = up.union(select(step.c.id, step.c.parent_object_id).select_from(up).join(step, true()))
        walked = sorted(session.scalars(select(up.c.id)))
        listed = bindparam(None, walked, type_=ARRAY(String))
        chain = (
            select(objects.id, objects.object_type_key, objects.name, objects.parent_object_id)
            .where(objects.id == any_(listed))
            .subquery()
        )
        return _load(session, source, chain, self._ancestor_keys)

    def _object(
        self,
        record: _Record,
        related: dict[str, list[tuple[str, _Record]]],
        ancestors: dict[str, _Record],
        narrowed: ConsumerFilter,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"objectType": self.public_names[record.type_key]}
        for item in self.roles.values():
            result[item.output] = item.read(record)
        for item in self.attributes:
            result[item.output] = item.read(record)
        chain = _chain(record.parent_id, ancestors)
        if self.parent is not None:
            result[self.parent.output] = self._parent(chain, ancestors, related, narrowed.include) if chain else None
        if self.path is not None or self.hierarchy is not None:
            names = [self._name(item) for item in reversed(chain)]
            if self.path is not None:
                result[self.path] = "/".join(names)
            if self.hierarchy is not None:
                result[self.hierarchy] = names
        blocks = {item.output: self._items(item, record.id, related, ancestors) for item in self.projections if item.name in related}
        for item in self.projections:
            if item.name in related and self._shown(item, narrowed.include):
                result[item.output] = blocks[item.output]
        if narrowed.target is not None:
            result["target"] = blocks[narrowed.target.projection]
        return result

    @staticmethod
    def _shown(item: _Projection, include: frozenset[str]) -> bool:
        return item.served == "always" or item.name in include

    def _items(
        self,
        projection: _Projection,
        owner_id: str,
        related: dict[str, list[tuple[str, _Record]]],
        ancestors: dict[str, _Record],
    ) -> Any:
        """The block's items of one owner: a list, or the item or ``None`` for a block of one."""
        items = [
            {
                output: self.public_names.get(item.type_key)
                if source == PROJECTION_TYPE_SOURCE
                else _projected(item, source, ancestors)
                for output, source in projection.fields
            }
            for owner, item in related[projection.name]
            if owner == owner_id
        ]
        return items if projection.many else (items[0] if items else None)

    def _parent(
        self,
        chain: list[_Record],
        ancestors: dict[str, _Record],
        related: dict[str, list[tuple[str, _Record]]],
        include: frozenset[str],
    ) -> dict[str, Any]:
        """The parent (``chain[0]``) as the definition shows it: its fields, then its blocks (CA1)."""
        parent = chain[0]
        built_in = {
            "objectType": self.public_names.get(parent.type_key),
            "id": self.roles["id"].read(parent),
            "code": self.roles["code"].read(parent) if "code" in self.roles else None,
            "name": self._name(parent),
        }
        result: dict[str, Any] = {}
        for output, item in self.parent_fields.items():
            value = None
            for name in item.sources:
                if name in built_in:
                    value = built_in[name]
                elif (reference := split_ancestor_reference(name)) is not None:
                    value = _projected(parent, reference, ancestors)
                else:
                    value = parent.field(name)
                if value is not None:
                    break
            result[output] = item.default if value is None else value
        for item in self.parent_projections:
            if item.name in related and self._shown(item, include):
                result[item.output] = self._items(item, parent.id, related, ancestors)
        return result

    def _name(self, record: _Record) -> Any:
        """The ``name`` role, falling back to the built-in name."""
        role = self.roles.get("name")
        value = role.read(record) if role is not None else None
        return record.name if value is None else value


def _projected(record: _Record, source: str | tuple[str, str], ancestors: dict[str, _Record]) -> Any:
    if isinstance(source, str):
        return record.field(source)
    type_key, name = source
    # The ancestor of that type nearest the root, as ``path`` and the management reads show it
    # (D209): the chain runs from the parent up, so the last match.
    found = [item for item in _chain(record.parent_id, ancestors) if item.type_key == type_key]
    return found[-1].field(name) if found else None


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


def _rows(
    session: Session, source: ConsumerSource, records: Any, keys: set[str], extra: tuple[Any, ...] = ()
) -> Sequence[Any]:
    """The rows of ``records`` with their values of ``keys``, one row per value (or one without)."""
    values = source.values
    value_columns = [getattr(values, name).label(name) for name in _VALUE_COLUMNS]
    statement: Select[Any] = (
        select(
            *extra,
            records.c.id,
            records.c.object_type_key,
            records.c.name,
            records.c.parent_object_id,
            values.attribute_type_key,
            values.value_type,
            *value_columns,
        )
        .select_from(records)
        .outerjoin(
            values,
            and_(
                values.object_id == records.c.id,
                values.attribute_type_key.in_(sorted(keys)) if keys else false(),
            ),
        )
        .order_by(records.c.name, records.c.id)
    )
    return session.execute(statement).all()


def _load(session: Session, source: ConsumerSource, records: Any, keys: set[str]) -> dict[str, _Record]:
    found: dict[str, _Record] = {}
    for row in _rows(session, source, records, keys):
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
    source: ConsumerSource,
    object_id: str,
    narrowed: ConsumerFilter = NO_FILTER,
) -> dict[str, Any]:
    """Get by ID: the shared object of the record with this object ID (C-D24), or
    ``404 OBJECT_NOT_FOUND`` for an unknown or deleted record, one in another workspace, one of a
    type the definition does not expose, or one the parameters filter out (C-D31); with a crosswalk
    target, its single item (``one_target``). With ``asOf``, a record of a type without a period is
    ``400 AS_OF_NOT_SUPPORTED`` and a dated one not effective that day ``404`` (C-D77)."""
    if narrowed.as_of is not None:
        refusal = undated_refusal(session, definition, source, [object_id], narrowed).get(object_id)
        if refusal is not None:
            raise refusal
    composed = ConsumerObjects(model, definition).compose(session, source, [object_id], narrowed)
    if object_id not in composed:
        raise object_not_found(object_id)
    return one_target(composed[object_id], object_id, narrowed.target)


def one_target(body: dict[str, Any], object_id: str, target: Target | None) -> dict[str, Any]:
    """The answer of a read of one object (get by ID, XREF ``expect=one``, a batch item): with a
    crosswalk target, ``target`` is its single item. None is ``404 TARGET_NOT_FOUND``, several
    ``409 AMBIGUOUS_TARGET``, each naming the object (C-D55)."""
    if target is None:
        return body
    found = body["target"]
    items = found if isinstance(found, list) else ([] if found is None else [found])
    details = {
        "id": object_id,
        "objectType": body["objectType"],
        "parameter": target.name,
        "path": f"/query/{target.name}",
    }
    if not items:
        raise api_error(
            404,
            "TARGET_NOT_FOUND",
            f"{body['objectType']} '{object_id}' has no item of '{target.projection}' that {target.name} matches",
            details,
        )
    if len(items) > 1:
        raise api_error(
            409,
            "AMBIGUOUS_TARGET",
            f"{body['objectType']} '{object_id}' has {len(items)} items of '{target.projection}' that"
            f" {target.name} matches; the target does not identify one",
            {**details, "count": len(items), "targets": items[:AMBIGUOUS_TARGETS]},
        )
    return {**body, "target": items[0]}


def undated_refusal(
    session: Session,
    definition: ConsumerApiDefinition,
    source: ConsumerSource,
    object_ids: Sequence[str],
    narrowed: ConsumerFilter,
) -> dict[str, ApiError]:
    """``AS_OF_NOT_SUPPORTED`` for each of ``object_ids`` that is an exposed record of a type without
    a period, read in one statement: a get by ID with ``asOf`` names an undated type rather than
    answering ``404``; an unknown record is left to ``404`` (C-D77)."""
    objects = source.objects
    rows = session.execute(
        select(objects.id, objects.object_type_key).where(
            objects.id.in_(list(object_ids)),
            objects.workspace_key == source.workspace_key,
            objects.object_type_key.in_(list(definition.objectTypes)),
        )
    )
    return {
        row.id: as_of_not_supported([definition.objectTypes[row.object_type_key].publicName])
        for row in rows
        if row.object_type_key not in narrowed.dated
    }


def object_not_found(object_id: str) -> ApiError:
    """Get by ID's refusal, which batch resolve gives a by-ID item as well (C14)."""
    return api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")

