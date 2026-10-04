"""A consumer API definition's parameters as SQL predicates (Base 0.9 C3, C-D31–C-D33).

Every definition parameter applies to get by ID and to every list; XREF (C4, C5) and batch resolve
(C14) reuse the same predicates. Each parameter becomes a predicate on the record, so a filter, its
total and a position jump stay in the database:

- ``objectType`` keeps the records of the named public types;
- ``ancestor`` keeps the records below a matching record of its types, at any depth;
- ``related`` keeps the records linked to a matching record through its routes: a projection, the
  record itself (``self``), or a shared projection (both relate to one projected record, the
  matching record itself excluded);
- ``projection`` limits a projection's items to the matching ones, and with ``requireMatch`` also
  drops the records left with none.

A value first finds its candidates: the records of the listed types whose match field equals it,
text ignoring case, read through the indexes a search reads. A value that does not parse for a typed
field does not match that field. A parameter's values are alternatives; different parameters
combine with AND.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ARRAY, Select, String, and_, any_, bindparam, exists, false, or_, select
from sqlalchemy.orm import Session, aliased

from ...errors import api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject
from ...models.schema import (
    AncestorParameter,
    ConsumerApiDefinition,
    EngineModel,
    ObjectTypeParameter,
    ProjectionParameter,
    RelatedParameter,
)
from ..model.consumer_contract import projection_targets, split_ancestor_reference
from ..model.traversal import ancestor_type_keys
from ..records.values import VALUE_COLUMNS
from .object_query import SEARCH_CANDIDATE_LIMIT, escape_like, parse_typed

# A condition on a record, given the entity (``RdmObject`` or an alias of it) that holds it.
Predicate = Callable[[Any], Any]

VIA_SELF = "self"
VIA_SHARED = "sharedProjection:"


def split_values(raw: Iterable[str]) -> list[str]:
    """A parameter's values, repeated or comma-separated or both (C-D32). In a value ``\\,`` is a
    comma and ``\\\\`` a backslash; any other backslash is kept as it is."""
    values: list[str] = []
    for item in raw:
        current: list[str] = []
        index = 0
        while index < len(item):
            char = item[index]
            following = item[index + 1] if index + 1 < len(item) else ""
            if char == "\\" and following in {",", "\\"}:
                current.append(following)
                index += 2
                continue
            if char == ",":
                values.append("".join(current))
                current = []
            else:
                current.append(char)
            index += 1
        values.append("".join(current))
    return values


@dataclass(frozen=True)
class ConsumerFilter:
    """What a read's parameters ask: conditions on the record, and on each projection's items."""

    records: tuple[Predicate, ...] = ()
    limits: Mapping[str, Predicate] = field(default_factory=dict)

    def on(self, entity: Any) -> list[Any]:
        return [predicate(entity) for predicate in self.records]


NO_FILTER = ConsumerFilter()


def consumer_filter(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace_key: str,
    values: Mapping[str, Sequence[str]],
) -> ConsumerFilter:
    """The predicates of the definition parameters in ``values`` (name to its split values)."""
    builder = _Builder(session, model, definition, workspace_key)
    records: list[Predicate] = []
    limits: dict[str, list[Predicate]] = {}
    for name, given in values.items():
        parameter = definition.parameters[name]
        if isinstance(parameter, ObjectTypeParameter):
            records.append(builder.object_type(given))
        elif isinstance(parameter, AncestorParameter):
            records.append(builder.ancestor(parameter, given))
        elif isinstance(parameter, RelatedParameter):
            records.append(builder.related(parameter, given))
        elif isinstance(parameter, ProjectionParameter):
            item, required = builder.projection(parameter, given)
            limits.setdefault(parameter.projection, []).append(item)
            if required is not None:
                records.append(required)
    return ConsumerFilter(
        records=tuple(records),
        limits={name: _all(predicates) for name, predicates in limits.items()},
    )


def _all(predicates: list[Predicate]) -> Predicate:
    return lambda entity: and_(*(predicate(entity) for predicate in predicates))


class _Builder:
    def __init__(
        self, session: Session, model: EngineModel, definition: ConsumerApiDefinition, workspace_key: str
    ) -> None:
        self.session = session
        self.model = model
        self.definition = definition
        self.workspace_key = workspace_key

    def object_type(self, names: Sequence[str]) -> Predicate:
        by_name = {item.publicName: key for key, item in self.definition.objectTypes.items()}
        unknown = [name for name in names if name not in by_name]
        if unknown:
            public = sorted(by_name)
            raise api_error(
                400,
                "UNKNOWN_OBJECT_TYPE",
                f"Unknown object type '{unknown[0]}'; this API exposes {', '.join(public)}",
                {"objectTypes": unknown, "publicNames": public},
            )
        keys = sorted({by_name[name] for name in names})
        return lambda entity: entity.object_type_key.in_(keys)

    def ancestor(self, parameter: AncestorParameter, values: Sequence[str]) -> Predicate:
        starts = self.candidates(parameter.objectTypes, parameter.matchFields, values)
        return below(self.session, self.model, self.workspace_key, starts, self.definition.objectTypes)

    def related(self, parameter: RelatedParameter, values: Sequence[str]) -> Predicate:
        candidates = self.candidates(parameter.objectTypes, parameter.matchFields, values)

        def predicate(entity: Any) -> Any:
            routes = []
            for via in parameter.via:
                if via == VIA_SELF:
                    routes.append(entity.id.in_(candidates))
                elif via.startswith(VIA_SHARED):
                    routes.append(self._shared(entity, via.removeprefix(VIA_SHARED), candidates))
                else:
                    routes.append(self._linked(entity, via, entity_ids=candidates))
            return or_(*routes)

        return predicate

    def projection(
        self, parameter: ProjectionParameter, values: Sequence[str]
    ) -> tuple[Predicate, Predicate | None]:
        """The condition on the projection's items, and on the record when ``requireMatch``."""
        route = self.definition.projections[parameter.projection].from_
        targets = [item.key for item in projection_targets(self.model, self.definition, route.relation, route.direction)]
        matches: list[Predicate] = []
        for match_field in parameter.matchFields:
            reference = split_ancestor_reference(match_field)
            if reference is None:
                matches.append(
                    lambda entity, name=match_field: entity.id.in_(self.candidates(targets, [name], values))
                )
            else:
                type_key, name = reference
                starts = self.candidates([type_key], [name], values)
                matches.append(below(self.session, self.model, self.workspace_key, starts, targets))

        def item(entity: Any) -> Any:
            return or_(*(match(entity) for match in matches))

        if not parameter.requireMatch:
            return item, None
        related = aliased(RdmObject)
        matching = select(related.id).where(item(related))
        return item, lambda entity: self._linked(entity, parameter.projection, entity_ids=matching)

    def candidates(self, type_keys: Sequence[str], fields: Sequence[str], values: Sequence[str]) -> Select[Any]:
        """The IDs of the records of ``type_keys`` in the workspace whose ``fields`` match a value."""
        record = aliased(RdmObject)
        matches = [
            match for value in values for name in fields if (match := self._match(record, name, value)) is not None
        ]
        return select(record.id).where(
            record.workspace_key == self.workspace_key,
            record.object_type_key.in_(list(type_keys)),
            or_(*matches) if matches else false(),
        )

    def _match(self, record: Any, name: str, value: str) -> Any:
        """``record``'s field ``name`` equals ``value`` (text ignoring case); ``None`` when the value
        does not parse for the field's type."""
        if name == "id":
            return record.id == value
        if name == "name":
            return record.name.ilike(escape_like(value), escape="\\")
        value_type = self.model.attribute_type(name).valueType
        column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
        if value_type in {"text", "longText"}:
            comparison = column.ilike(escape_like(value), escape="\\")
        else:
            try:
                comparison = column == parse_typed(value_type, value)
            except ValueError:
                return None
        return record.id.in_(
            select(AttributeValue.object_id).where(AttributeValue.attribute_type_key == name, comparison)
        )

    def _ends(self, relation: Any, projection: str) -> tuple[str, Any, Any]:
        route = self.definition.projections[projection].from_
        outgoing = route.direction == "outgoing"
        own = relation.from_object_id if outgoing else relation.to_object_id
        other = relation.to_object_id if outgoing else relation.from_object_id
        return route.relation, own, other

    def _linked(self, entity: Any, projection: str, *, entity_ids: Select[Any]) -> Any:
        """``entity`` relates through the projection to a record of ``entity_ids``."""
        relation = aliased(ObjectRelation)
        key, own, other = self._ends(relation, projection)
        return exists(
            select(relation.sequence_id).where(
                relation.relation_type_key == key, own == entity.id, other.in_(entity_ids)
            )
        )

    def _shared(self, entity: Any, projection: str, candidates: Select[Any]) -> Any:
        """``entity`` and another record of ``candidates`` relate through the projection to one
        projected record."""
        mine, theirs = aliased(ObjectRelation), aliased(ObjectRelation)
        key, own, other = self._ends(mine, projection)
        _key, their_own, their_other = self._ends(theirs, projection)
        return exists(
            select(mine.sequence_id)
            .join(theirs, and_(theirs.relation_type_key == key, their_other == other))
            .where(
                mine.relation_type_key == key,
                own == entity.id,
                their_own.in_(candidates),
                their_own != entity.id,
            )
        )


def below(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    starts: Select[Any],
    type_keys: Iterable[str],
) -> Predicate:
    """Records of ``type_keys`` anywhere below a record of ``starts`` (an ``id`` column).

    As the model query's ancestor criterion does, one recursive CTE walks down from the starts
    through the records of the types that can contain ``type_keys`` only, each step probing the
    (workspace, parent, type) index; a record is below a start when its parent is one of them. The
    records being listed are never walked, so the cost follows the containers, not the records.

    The containers are read first and bound as a list while they are few, as a search's candidates
    are (``search_candidates``): PostgreSQL estimates a recursive CTE far above what it holds and
    would then hash every value of a sorted list instead of walking its index (0.9 C3a). Past
    :data:`SEARCH_CANDIDATE_LIMIT` the walk stays a subquery.
    """
    containers = sorted(set().union(*(ancestor_type_keys(model, key) for key in type_keys)))
    walk = starts.cte(recursive=True)
    child = aliased(RdmObject)
    # UNION, not UNION ALL: a record met twice ends the walk, whatever the data holds.
    walk = walk.union(
        select(child.id)
        .select_from(walk)
        .join(child, child.parent_object_id == walk.c.id)
        .where(child.workspace_key == workspace_key, child.object_type_key.in_(containers))
    )
    walked = select(walk.c.id)
    found = list(session.scalars(walked.limit(SEARCH_CANDIDATE_LIMIT + 1)))
    if len(found) > SEARCH_CANDIDATE_LIMIT:
        return lambda entity: entity.parent_object_id.in_(walked)
    listed = bindparam(None, found, type_=ARRAY(String))
    return lambda entity: entity.parent_object_id == any_(listed)
