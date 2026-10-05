"""XREF: a consumer API's scored lookup (Base 0.9 C4, C-D34–C-D41).

A consuming system finds business objects by what it knows. The candidates are the live records of
the definition's exposed types in the workspace, and the definition's ``match`` scores them for each
term of the query:

- **own rules** compare the term with a field of the object: exact is equality ignoring case (a
  typed field by its parsed value), contains a substring of a text field. The exact weights that
  apply add up; the contains weights add up and count only when no exact weight applied (C-D35).
- **promoted rules** read a projection's related records: each takes the weight of its first
  matching rule in ``firstMatch`` order and passes it to the exposed objects it relates to through
  the projection; with ``preferTargetTypes``, a related record relating to an object of a preferred
  type passes it only to those (C-D36).

An object's score is the highest of its own and promoted scores over every term (C-D38). Results
order by score, then the type's public name, then name, then object ID.

The definition's parameters act on the scored objects (C5, C-D42): an object is a result when it
scored and every parameter keeps it, with the score it has without them, and ``projection``
parameters limit the projections' items as on a list. A parameter declaring ``scoresFrom`` acts
before that, on promotion: only the related records it matches pass their weight through its
projection (C-D43).

Everything is scored at read time over existing indexes (the trigram indexes on names and text
values for contains, their ``lower(…)`` indexes for exact matches, the object ID index), in one
statement Python builds from the definition, and nothing scores row by row (C-D34). Before it runs, one bounded statement counts the records the terms match:
past :data:`MATCH_LIMIT` the request is refused, a documented limit rather than a silent cap or a
slow read (C-D37). A term shorter than :data:`MIN_INDEXED_LENGTH` matches exactly only.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import Select, String, and_, case, func, literal, or_, select, union, union_all
from sqlalchemy.orm import Session, aliased

from ...common.pagination import PageRequest, integer_key, paginate_statement, text_key
from ...errors import api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject
from ...models.schema import (
    ConsumerApiDefinition,
    ConsumerMatchRule,
    ConsumerPromotedMatch,
    EngineModel,
)
from ...models.search_index import MIN_INDEXED_LENGTH
from ..model.consumer_contract import projection_targets
from ..records.values import VALUE_COLUMNS
from .consumer_objects import ConsumerObjects
from .consumer_parameters import ConsumerFilter
from .object_query import INDEXED_MATCH_LIMIT, escape_like, parse_typed

# The records a query may match before it is refused as too broad (C-D37).
MATCH_LIMIT = INDEXED_MATCH_LIMIT
# The terms one query may hold (C-D38).
MAX_TERMS = 100
# The tied objects an ambiguous ``expect=one`` names (C-D40).
AMBIGUOUS_CANDIDATES = 10
_TEXT_TYPES = {"text", "longText"}


def xref_terms(values: Sequence[str]) -> list[str]:
    """The query's terms: each value trimmed, empty ones dropped; ``400 QUERY_REQUIRED`` without
    any and ``400 TOO_MANY_TERMS`` past :data:`MAX_TERMS` (C-D38)."""
    terms = [stripped for value in values if (stripped := value.strip())]
    if not terms:
        raise api_error(
            400, "QUERY_REQUIRED", "XREF needs a query: one or more terms in 'query'", {"path": "/query/query"}
        )
    if len(terms) > MAX_TERMS:
        raise api_error(
            400,
            "TOO_MANY_TERMS",
            f"A query holds at most {MAX_TERMS} terms; this one holds {len(terms)}",
            {"path": "/query/query", "limit": MAX_TERMS, "count": len(terms)},
        )
    return terms


@dataclass(frozen=True)
class _Ranked:
    """The scored statement and the order it pages in."""

    statement: Select[Any]
    columns: Any

    @property
    def keys(self) -> list[Any]:
        c = self.columns
        return [
            integer_key("score", c.score, "score", descending=True),
            text_key("type", c.public_name, "public_name"),
            text_key("name", c.name, "name"),
            text_key("id", c.id, "id"),
        ]


class _Scoring:
    """The statements of one query over one definition in one workspace, narrowed by ``narrowed``."""

    def __init__(
        self,
        model: EngineModel,
        definition: ConsumerApiDefinition,
        workspace_key: str,
        terms: Sequence[str],
        narrowed: ConsumerFilter,
    ) -> None:
        assert definition.match is not None
        self.model = model
        self.definition = definition
        self.match = definition.match
        self.workspace_key = workspace_key
        self.terms = list(terms)
        self.narrowed = narrowed
        self.exposed = list(definition.objectTypes)

    # --- what one rule matches ---

    def _matcher(self, field: str, term: str, contains: bool) -> Callable[[Any], Any] | None:
        """A condition on a record: its field ``field`` equals (or, with ``contains``, holds) ``term``,
        ignoring case. ``None`` when it cannot: a contains term too short to index, or a term that
        does not parse for a typed field. An attribute matches through its value rows."""
        if contains and len(term) < MIN_INDEXED_LENGTH:
            return None
        if field == "id":
            # Object IDs are UUIDs in lower case; validation keeps contains off them.
            return lambda record: record.id == term.lower()
        if field == "name":
            return lambda record: _text_match(record.name, term, contains)
        value_type = self.model.attribute_type(field).valueType
        column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
        if value_type in _TEXT_TYPES:
            comparison = _text_match(column, term, contains)
        else:
            try:
                comparison = column == parse_typed(value_type, term)
            except ValueError:
                return None
        values = select(AttributeValue.object_id).where(AttributeValue.attribute_type_key == field, comparison)
        return lambda record: record.id.in_(values)

    def _rule_arms(self, rule: ConsumerMatchRule, type_keys: Sequence[str], columns: Any) -> list[Select[Any]]:
        """One select per term and weight of ``rule``: the IDs of the records of ``type_keys`` in the
        workspace it matches, with ``columns(term_index, contains, weight)``."""
        arms = []
        for index, term in enumerate(self.terms):
            for contains, weight in ((False, rule.exact), (True, rule.contains)):
                matcher = None if weight is None else self._matcher(rule.field, term, contains)
                if matcher is None:
                    continue
                record = aliased(RdmObject)
                arms.append(
                    select(record.id, *columns(index, contains, weight)).where(
                        record.workspace_key == self.workspace_key,
                        record.object_type_key.in_(list(type_keys)),
                        matcher(record),
                    )
                )
        return arms

    def own_arms(self) -> list[Select[Any]]:
        """``(id, term, exact, contains)`` for each own rule's match."""
        return [
            arm
            for rule in self.match.own
            for arm in self._rule_arms(
                rule,
                self.exposed,
                lambda index, contains, weight: (
                    literal(index).label("term"),
                    literal(0 if contains else weight).label("exact"),
                    literal(weight if contains else 0).label("contains"),
                ),
            )
        ]

    def _targets(self, promoted: ConsumerPromotedMatch) -> list[str]:
        route = self.definition.projections[promoted.projection].from_
        targets = projection_targets(self.model, self.definition, route.relation, route.direction)
        return [item.key for item in targets]

    def promoted_arms(self, promoted: ConsumerPromotedMatch) -> list[Select[Any]]:
        """``(id, term, position, weight)`` for each related record a ``firstMatch`` rule matches;
        ``position`` orders the rules, an exact weight before a contains weight of the same rule."""
        targets = self._targets(promoted)
        return [
            arm
            for position, rule in enumerate(promoted.firstMatch)
            for arm in self._rule_arms(
                rule,
                targets,
                lambda index, contains, weight, position=position: (
                    literal(index).label("term"),
                    literal(position * 2 + int(contains)).label("position"),
                    literal(weight).label("weight"),
                ),
            )
        ]

    # --- scores ---

    def _passed(self, promoted: ConsumerPromotedMatch, arms: list[Select[Any]]) -> Select[Any]:
        """``(object_id, score)``: each related record's first matching weight, passed to the exposed
        objects it relates to through the projection (C-D36); with a ``scoresFrom`` parameter over
        the projection, only by the related records it matches (C-D43)."""
        hits = union_all(*arms).subquery()
        best = (
            select(hits.c.id, hits.c.term, hits.c.weight)
            .distinct(hits.c.id, hits.c.term)
            .order_by(hits.c.id, hits.c.term, hits.c.position)
        )
        scoring = self.narrowed.scoring.get(promoted.projection)
        if scoring is not None:
            related = aliased(RdmObject)
            best = best.join(related, related.id == hits.c.id).where(scoring(related))
        best = best.subquery()
        route = self.definition.projections[promoted.projection].from_
        relation, owner = aliased(ObjectRelation), aliased(RdmObject)
        outgoing = route.direction == "outgoing"
        own = relation.from_object_id if outgoing else relation.to_object_id
        other = relation.to_object_id if outgoing else relation.from_object_id
        preferred = list(promoted.preferTargetTypes)
        columns = [own.label("object_id"), best.c.weight.label("score")]
        if preferred:
            is_preferred = owner.object_type_key.in_(preferred)
            columns += [
                is_preferred.label("preferred"),
                func.bool_or(is_preferred).over(partition_by=(best.c.id, best.c.term)).label("has_preferred"),
            ]
        passed = (
            select(*columns)
            .select_from(best)
            .join(relation, and_(relation.relation_type_key == route.relation, other == best.c.id))
            .join(owner, owner.id == own)
            .where(owner.workspace_key == self.workspace_key, owner.object_type_key.in_(self.exposed))
        )
        if not preferred:
            return passed
        chosen = passed.subquery()
        return select(chosen.c.object_id, chosen.c.score).where(or_(~chosen.c.has_preferred, chosen.c.preferred))

    def ranked(self) -> _Ranked | None:
        """The scored objects with their public type name and name, or ``None`` when no rule can
        match any term."""
        parts: list[Select[Any]] = []
        own = self.own_arms()
        if own:
            hits = union_all(*own).subquery()
            exact, contains = func.sum(hits.c.exact), func.sum(hits.c.contains)
            parts.append(
                select(hits.c.id.label("object_id"), case((exact > 0, exact), else_=contains).label("score"))
                .group_by(hits.c.id, hits.c.term)
            )
        for promoted in self.match.promoted:
            arms = self.promoted_arms(promoted)
            if arms:
                parts.append(self._passed(promoted, arms))
        if not parts:
            return None
        scores = union_all(*parts).subquery()
        best = (
            select(scores.c.object_id, func.max(scores.c.score).label("score"))
            .group_by(scores.c.object_id)
            .subquery()
        )
        public_name = case(
            {key: item.publicName for key, item in self.definition.objectTypes.items()},
            value=RdmObject.object_type_key,
            else_=literal(None, String),
        )
        ranked = (
            select(
                RdmObject.id.label("id"),
                best.c.score.label("score"),
                public_name.label("public_name"),
                RdmObject.name.label("name"),
            )
            .join(best, best.c.object_id == RdmObject.id)
            .where(*self.narrowed.on(RdmObject))
            .subquery("ranked")
        )
        return _Ranked(select(ranked.c.id, ranked.c.score, ranked.c.public_name, ranked.c.name), ranked.c)

    def matched_count(self, session: Session) -> int:
        """The distinct records the terms match, own matches and the related records promotion reads,
        counted up to ``MATCH_LIMIT + 1``: each rule reads at most that many, so a common term costs
        no more than the limit. Parameters do not count: they narrow what the terms match (C-D44)."""
        arms = self.own_arms()
        for promoted in self.match.promoted:
            arms += self.promoted_arms(promoted)
        if not arms:
            return 0
        bounded = [select(arm.limit(MATCH_LIMIT + 1).subquery().c.id) for arm in arms]
        matched = union(*bounded).subquery() if len(bounded) > 1 else bounded[0].subquery()
        return session.scalar(select(func.count()).select_from(matched)) or 0


def _text_match(column: Any, term: str, contains: bool) -> Any:
    """``column`` holds ``term`` (through its trigram index) or, exactly, equals it ignoring case
    (through its ``lower(…)`` index, 20261005_01)."""
    if contains:
        return column.ilike(f"%{escape_like(term)}%", escape="\\")
    return func.lower(column) == func.lower(term)


def read_xref(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    *,
    workspace_key: str,
    terms: Sequence[str],
    narrowed: ConsumerFilter,
    parameters: Mapping[str, Sequence[str]],
    expect_one: bool,
    page: PageRequest,
    page_size: int,
) -> dict[str, Any]:
    """XREF's answer: a page of scored shared objects in the envelope (C-D39), or with
    ``expect_one`` the single top object (C-D40), of those ``narrowed`` keeps (C-D42). Each object
    carries ``matchScore`` after its declared fields (C-D41). ``parameters`` are the request's
    parameter values, bound into the cursor with the terms, the workspace and the contract version."""
    scoring = (
        _Scoring(model, definition, workspace_key, terms, narrowed) if definition.match is not None else None
    )
    ranked = None
    if scoring is not None:
        matched = scoring.matched_count(session)
        if matched > MATCH_LIMIT:
            raise api_error(
                400,
                "QUERY_TOO_BROAD",
                f"The query matches more than {MATCH_LIMIT:,} records, the most XREF scores in one request;"
                f" use a longer or more specific term (contains matching needs at least {MIN_INDEXED_LENGTH}"
                " characters)",
                {"path": "/query/query", "limit": MATCH_LIMIT, "minimumContainsLength": MIN_INDEXED_LENGTH},
            )
        ranked = scoring.ranked()
    composer = ConsumerObjects(model, definition)
    if expect_one:
        return _expect_one(session, composer, workspace_key, ranked, narrowed)
    if ranked is None:
        nothing = {"nextCursor": None, "prevCursor": None, "anchor": None, "totalCount": 0, "startIndex": 0}
        return _envelope([], terms, workspace_key, page_size, nothing)
    found = paginate_statement(
        session,
        ranked.statement,
        keys=ranked.keys,
        scope=f"consumer-xref:{definition.key}",
        filters={
            "workspace": workspace_key,
            "contractVersion": definition.contractVersion,
            "query": sorted(set(terms)),
            "parameters": {name: sorted(values) for name, values in sorted(parameters.items())},
        },
        page=replace(page, include_total=True),
        page_size=page_size,
        rows=True,
    )
    scores = {row.id: row.score for row in found.items}
    composed = composer.compose(session, workspace_key, list(scores), narrowed)
    results = [
        {**composed[object_id], "matchScore": score}
        for object_id, score in scores.items()
        if object_id in composed
    ]
    return _envelope(results, terms, workspace_key, page_size, found.links())


def _envelope(
    results: list[dict[str, Any]],
    terms: Sequence[str],
    workspace_key: str,
    page_size: int,
    links: dict[str, Any],
) -> dict[str, Any]:
    return {
        "results": results,
        "query": list(terms),
        "workspace": workspace_key,
        "pageSize": page_size,
        **links,
    }


def _expect_one(
    session: Session,
    composer: ConsumerObjects,
    workspace_key: str,
    ranked: _Ranked | None,
    narrowed: ConsumerFilter,
) -> dict[str, Any]:
    """The single top object; ``404 NO_MATCH`` when nothing matched, ``409 AMBIGUOUS_MATCH`` naming
    the tied objects when the top score is shared (C-D40)."""
    rows = []
    if ranked is not None:
        order = [key.column.desc() if key.descending else key.column.asc() for key in ranked.keys]
        ordered = ranked.statement.order_by(*order)
        rows = list(session.execute(ordered.limit(AMBIGUOUS_CANDIDATES + 1)).all())
    if not rows:
        raise api_error(404, "NO_MATCH", "No object matches the query")
    top = rows[0].score
    tied = [row for row in rows if row.score == top]
    if len(tied) > 1:
        assert ranked is not None
        count = len(tied)
        if count > AMBIGUOUS_CANDIDATES:
            count = session.scalar(
                select(func.count())
                .select_from(ranked.statement.where(ranked.columns.score == top).subquery())
            )
        raise api_error(
            409,
            "AMBIGUOUS_MATCH",
            f"{count} objects share the top score {top}; the query does not identify one",
            {
                "count": count,
                "candidates": [
                    {"id": row.id, "objectType": row.public_name, "name": row.name, "matchScore": row.score}
                    for row in tied[:AMBIGUOUS_CANDIDATES]
                ],
            },
        )
    composed = composer.compose(session, workspace_key, [rows[0].id], narrowed)
    return {**composed[rows[0].id], "matchScore": top}
