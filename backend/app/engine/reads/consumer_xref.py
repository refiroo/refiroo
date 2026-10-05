"""XREF: a consumer API's scored lookup (Base 0.9 C4, C-D34–C-D41), and the lookups of batch
resolve (C14), which are XREF's ``expect=one`` for many items at once (C-D51).

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
statement Python builds from the definition, and nothing scores row by row (C-D34). The terms of
every lookup are one relation ``(item, term, text)``: a rule's exact matches of every term are read
through a ``LATERAL`` bounded at :data:`MATCH_LIMIT` + 1 rows, and its contains matches by one
bounded select per term with the pattern bound, which PostgreSQL plans on that pattern. So a
lookup's cost follows its terms, and one statement serves one lookup or many; the lookups that
read contains matches go at most :data:`CONTAINS_TERMS_PER_STATEMENT` terms to a statement. The
records a lookup's terms match are
counted from the same reads: past :data:`MATCH_LIMIT` the lookup is refused, a documented limit
rather than a silent cap or a slow read (C-D37). A term shorter than :data:`MIN_INDEXED_LENGTH`
matches exactly only.

**Exact first** (C-D52). Contains rules are the costly reads, so a single best match is first sought
with the exact rules alone. A lookup is settled there when its top score is above the most any
contains match can give (:func:`contains_ceiling`) and every object holding the top score got it
from an own exact rule or a promoted rule no contains weight precedes in ``firstMatch``
(:func:`safe_positions`): then no contains match can reach, raise or break the top, and the answer
equals full scoring. Only the lookups left unsettled are scored again with every rule.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import (
    ARRAY,
    Integer,
    Select,
    String,
    and_,
    bindparam,
    case,
    column,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.orm import Session, aliased

from ...common.pagination import PageRequest, integer_key, paginate_statement, text_key
from ...errors import ApiError, api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject
from ...models.schema import (
    ConsumerApiDefinition,
    ConsumerMatch,
    ConsumerMatchRule,
    ConsumerPromotedMatch,
    EngineModel,
)
from ...models.search_index import MIN_INDEXED_LENGTH
from ..model.consumer_contract import projection_targets
from ..records.values import VALUE_COLUMNS
from .consumer_objects import ConsumerObjects, one_target
from .consumer_parameters import ConsumerFilter, without_target
from .object_query import INDEXED_MATCH_LIMIT, escape_like, parse_typed

# The records a query may match before it is refused as too broad (C-D37).
MATCH_LIMIT = INDEXED_MATCH_LIMIT
# The terms one query may hold (C-D38).
MAX_TERMS = 100
# The tied objects an ambiguous ``expect=one`` names (C-D40).
AMBIGUOUS_CANDIDATES = 10
# The contains terms one statement reads, each a select per contains rule (C14): a batch's
# unsettled lookups are scored in statements of at most this many, so none outgrows the driver's
# parameter limit or plans for long.
CONTAINS_TERMS_PER_STATEMENT = 200
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


def contains_ceiling(match: ConsumerMatch) -> int:
    """The highest score a contains match can give an object: its own contains weights together,
    or the highest promoted contains weight (C-D52)."""
    own = sum(rule.contains or 0 for rule in match.own)
    promoted = max((rule.contains or 0 for entry in match.promoted for rule in entry.firstMatch), default=0)
    return max(own, promoted)


def safe_positions(promoted: ConsumerPromotedMatch) -> set[int]:
    """The ``firstMatch`` rules whose exact weight no contains weight precedes: a related record
    matching one exactly passes that weight even when contains rules are read (C-D52)."""
    safe = set()
    for position, rule in enumerate(promoted.firstMatch):
        safe.add(position)
        if rule.contains is not None:
            break
    return safe


def _too_broad() -> ApiError:
    return api_error(
        400,
        "QUERY_TOO_BROAD",
        f"The query matches more than {MATCH_LIMIT:,} records, the most XREF scores in one request;"
        f" use a longer or more specific term (contains matching needs at least {MIN_INDEXED_LENGTH}"
        " characters)",
        {"path": "/query/query", "limit": MATCH_LIMIT, "minimumContainsLength": MIN_INDEXED_LENGTH},
    )


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


class _Terms:
    """The lookups' terms: as rows, as the relation ``(item, term, text)`` the exact matches read,
    and per value type the terms that parse for it as ``(item, term, value)``."""

    def __init__(self, model: EngineModel, lookups: Sequence[Sequence[str]]) -> None:
        rows = [(item, number, term) for item, terms in enumerate(lookups) for number, term in enumerate(terms)]
        self.rows = rows
        self.relation = _unnest(
            "terms",
            [
                ("item", Integer, [row[0] for row in rows]),
                ("term", Integer, [row[1] for row in rows]),
                ("text", String, [row[2] for row in rows]),
            ],
        )
        self._model = model
        self._typed: dict[str, Any] = {}

    def typed(self, value_type: str) -> Any:
        """``(item, term, value)`` for the terms that parse as ``value_type``; ``None`` when none do."""
        if value_type not in self._typed:
            parsed = []
            for item, number, term in self.rows:
                try:
                    parsed.append((item, number, parse_typed(value_type, term)))
                except ValueError:
                    continue
            value_column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
            self._typed[value_type] = (
                _unnest(
                    f"terms_{value_type}",
                    [
                        ("item", Integer, [row[0] for row in parsed]),
                        ("term", Integer, [row[1] for row in parsed]),
                        ("value", value_column.type, [row[2] for row in parsed]),
                    ],
                )
                if parsed
                else None
            )
        return self._typed[value_type]


def _unnest(name: str, columns: Sequence[tuple[str, Any, list[Any]]]) -> Any:
    """A relation of parallel arrays, as a CTE: four parameters whatever the rows."""
    arrays = [bindparam(None, values, type_=ARRAY(type_)) for _name, type_, values in columns]
    rows = func.unnest(*arrays).table_valued(*(column(label, type_) for label, type_, _ in columns))
    derived = rows.render_derived(name=f"{name}_rows")
    return select(*(derived.c[label] for label, _, _ in columns)).cte(name)


class _Scoring:
    """The statements of a set of lookups over one definition in one workspace, narrowed by
    ``narrowed``; with ``contains`` false, the exact rules only (C-D52)."""

    def __init__(
        self,
        model: EngineModel,
        definition: ConsumerApiDefinition,
        workspace_key: str,
        lookups: Sequence[Sequence[str]],
        narrowed: ConsumerFilter,
        *,
        contains: bool = True,
    ) -> None:
        assert definition.match is not None
        self.model = model
        self.definition = definition
        self.match = definition.match
        self.workspace_key = workspace_key
        self.terms = _Terms(model, lookups)
        self.narrowed = narrowed
        self.contains = contains
        self.exposed = list(definition.objectTypes)
        self.own = self.own_hits()
        self.promoted = [
            (promoted, hits)
            for number, promoted in enumerate(self.match.promoted)
            if (hits := self.promoted_hits(number, promoted)) is not None
        ]

    # --- what one rule matches ---

    def _arms(
        self, rule: ConsumerMatchRule, type_keys: Sequence[str], contains: bool, columns: tuple[Any, ...]
    ) -> list[Select[Any]]:
        """``(item, term, id, *columns)`` for each term and record of ``type_keys`` the rule's
        exact (or contains) weight matches, at most ``MATCH_LIMIT + 1`` records per term.

        Exact matches of every term are one select, each term seeking its index through a
        ``LATERAL``. Contains matches are one select per term with its pattern bound: PostgreSQL
        then plans each probe on the pattern it reads, where a pattern from the terms relation
        would be planned as matching a thousand records and join every record of the types (0.9 C14,
        measured at 22 ms against 4 ms per probe)."""
        if contains:
            return [
                select(literal(item).label("item"), literal(number).label("term"), matched.c.id, *columns)
                .select_from(matched)
                for item, number, term in self.terms.rows
                if len(term) >= MIN_INDEXED_LENGTH
                for matched in [self._matched(rule.field, type_keys, contains_pattern=f"%{escape_like(term)}%")]
            ]
        source = self.terms.relation
        if rule.field not in ("id", "name"):
            value_type = self.model.attribute_type(rule.field).valueType
            if value_type not in _TEXT_TYPES:
                source = self.terms.typed(value_type)
                if source is None:
                    return []
        bounded = self._matched(rule.field, type_keys, terms=source).lateral()
        return [select(source.c.item, source.c.term, bounded.c.id, *columns).select_from(source).join(bounded, true())]

    def _matched(
        self, field: str, type_keys: Sequence[str], *, terms: Any = None, contains_pattern: str | None = None
    ) -> Any:
        """The IDs of the records of ``type_keys`` in the workspace whose ``field`` equals a term of
        ``terms`` ignoring case (a typed field by its parsed value), or holds ``contains_pattern``;
        at most ``MATCH_LIMIT + 1`` of them. A contains read is a subquery of its own, so it reads the
        tables unaliased: aliasing them for each of hundreds of terms cost SQLAlchemy more time than
        PostgreSQL took to run them (0.9 C14b)."""
        record = aliased(RdmObject) if terms is not None else RdmObject
        scope = [record.workspace_key == self.workspace_key, record.object_type_key.in_(list(type_keys))]
        if field == "id":
            # Object IDs are UUIDs in lower case; validation keeps contains off them.
            matched = select(record.id).where(*scope, record.id == func.lower(terms.c.text))
        elif field == "name":
            matched = select(record.id).where(*scope, _text_match(record.name, terms, contains_pattern))
        else:
            value_type = self.model.attribute_type(field).valueType
            value = aliased(AttributeValue) if terms is not None else AttributeValue
            stored = getattr(value, VALUE_COLUMNS[value_type])
            comparison = (
                _text_match(stored, terms, contains_pattern) if value_type in _TEXT_TYPES else stored == terms.c.value
            )
            matched = (
                select(record.id)
                .join(value, value.object_id == record.id)
                .where(*scope, value.attribute_type_key == field, comparison)
            )
        bounded = matched.limit(MATCH_LIMIT + 1)
        return bounded if terms is not None else bounded.subquery()

    def _weights(self, rule: ConsumerMatchRule) -> list[tuple[bool, int]]:
        weights = [(False, rule.exact)]
        if self.contains:
            weights.append((True, rule.contains))
        return [(contains, weight) for contains, weight in weights if weight is not None]

    def own_hits(self) -> Any | None:
        """``(item, term, id, exact, contains)`` for each own rule's match."""
        arms = [
            arm
            for rule in self.match.own
            for contains, weight in self._weights(rule)
            for arm in self._arms(
                rule,
                self.exposed,
                contains,
                (
                    literal(0 if contains else weight).label("exact"),
                    literal(weight if contains else 0).label("contains"),
                ),
            )
        ]
        return union_all(*arms).cte("own_hits") if arms else None

    def _targets(self, promoted: ConsumerPromotedMatch) -> list[str]:
        route = self.definition.projections[promoted.projection].from_
        targets = projection_targets(self.model, self.definition, route.relation, route.direction)
        return [item.key for item in targets]

    def promoted_hits(self, number: int, promoted: ConsumerPromotedMatch) -> Any | None:
        """``(item, term, id, position, weight, safe)`` for each related record a ``firstMatch``
        rule matches; ``position`` orders the rules, an exact weight before a contains weight of the
        same rule; ``safe`` marks an exact weight no contains weight precedes."""
        targets = self._targets(promoted)
        safe = safe_positions(promoted)
        arms = [
            arm
            for position, rule in enumerate(promoted.firstMatch)
            for contains, weight in self._weights(rule)
            for arm in self._arms(
                rule,
                targets,
                contains,
                (
                    literal(position * 2 + int(contains)).label("position"),
                    literal(weight).label("weight"),
                    literal(not contains and position in safe).label("safe"),
                ),
            )
        ]
        return union_all(*arms).cte(f"promoted_hits_{number}") if arms else None

    def hits(self) -> list[Any]:
        """The hit relations that can match: the own one and one per promoted entry."""
        return ([self.own] if self.own is not None else []) + [hits for _promoted, hits in self.promoted]

    # --- scores ---

    def _passed(self, promoted: ConsumerPromotedMatch, hits: Any) -> Select[Any]:
        """``(item, object_id, score, safe)``: each related record's first matching weight, passed to
        the exposed objects it relates to through the projection (C-D36); with a ``scoresFrom``
        parameter over the projection, only by the related records it matches (C-D43)."""
        best = (
            select(hits.c.item, hits.c.id, hits.c.term, hits.c.weight, hits.c.safe)
            .distinct(hits.c.item, hits.c.id, hits.c.term)
            .order_by(hits.c.item, hits.c.id, hits.c.term, hits.c.position)
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
        columns = [best.c.item, own.label("object_id"), best.c.weight.label("score"), best.c.safe]
        if preferred:
            is_preferred = owner.object_type_key.in_(preferred)
            columns += [
                is_preferred.label("preferred"),
                func.bool_or(is_preferred)
                .over(partition_by=(best.c.item, best.c.id, best.c.term))
                .label("has_preferred"),
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
        return select(chosen.c.item, chosen.c.object_id, chosen.c.score, chosen.c.safe).where(
            or_(~chosen.c.has_preferred, chosen.c.preferred)
        )

    def matched(self) -> Select[Any] | None:
        """``(item, matched)``: the distinct records each lookup's terms match, own matches and the
        related records promotion reads, at most ``MATCH_LIMIT + 1`` per rule and term. Parameters
        do not count: they narrow what the terms match (C-D44)."""
        hits = self.hits()
        if not hits:
            return None
        ids = union_all(*(select(item.c.item, item.c.id) for item in hits)).subquery()
        return select(ids.c.item, func.count(func.distinct(ids.c.id)).label("matched")).group_by(ids.c.item)

    def ranked(self) -> _Ranked | None:
        """``(item, id, score, safe_score, public_name, name)`` of the scored objects the parameters
        keep, or ``None`` when no rule can match any term. ``safe_score`` is the object's best score
        from sources no contains match can lower (C-D52)."""
        parts: list[Select[Any]] = []
        if self.own is not None:
            own = self.own
            exact, contains = func.sum(own.c.exact), func.sum(own.c.contains)
            parts.append(
                select(
                    own.c.item,
                    own.c.id.label("object_id"),
                    case((exact > 0, exact), else_=contains).label("score"),
                    (exact > 0).label("safe"),
                ).group_by(own.c.item, own.c.id, own.c.term)
            )
        for promoted, hits in self.promoted:
            parts.append(self._passed(promoted, hits))
        if not parts:
            return None
        scores = union_all(*parts).subquery()
        best = (
            select(
                scores.c.item,
                scores.c.object_id,
                func.max(scores.c.score).label("score"),
                func.max(case((scores.c.safe, scores.c.score))).label("safe_score"),
            )
            .group_by(scores.c.item, scores.c.object_id)
            .subquery()
        )
        public_name = case(
            {key: item.publicName for key, item in self.definition.objectTypes.items()},
            value=RdmObject.object_type_key,
            else_=literal(None, String),
        )
        ranked = (
            select(
                best.c.item,
                RdmObject.id.label("id"),
                best.c.score.label("score"),
                best.c.safe_score,
                public_name.label("public_name"),
                RdmObject.name.label("name"),
            )
            .join(best, best.c.object_id == RdmObject.id)
            .where(*self.narrowed.on(RdmObject))
            .subquery("ranked")
        )
        return _Ranked(select(ranked.c.id, ranked.c.score, ranked.c.public_name, ranked.c.name), ranked.c)

    def tops(self, session: Session) -> dict[int, tuple[int, list[Any]]]:
        """Each lookup's matched count and its top ``AMBIGUOUS_CANDIDATES + 1`` objects in order, each
        with ``same`` (the objects sharing its score) and ``tie_safe`` (whether all of them hold it
        from safe sources), in one statement. A lookup that matched nothing is absent."""
        matched = self.matched()
        ranked = self.ranked()
        if matched is None or ranked is None:
            return {}
        counts = matched.subquery("counts")
        c = ranked.columns
        order = [c.score.desc(), c.public_name.asc(), c.name.asc(), c.id.asc()]
        windowed = select(
            c.item,
            c.id,
            c.score,
            c.public_name,
            c.name,
            func.row_number().over(partition_by=c.item, order_by=order).label("rank"),
            func.count().over(partition_by=(c.item, c.score)).label("same"),
            func.bool_and(func.coalesce(c.safe_score, -1) == c.score)
            .over(partition_by=(c.item, c.score))
            .label("tie_safe"),
        ).subquery("windowed")
        rows = session.execute(
            select(
                counts.c.item,
                counts.c.matched,
                windowed.c.id,
                windowed.c.score,
                windowed.c.public_name,
                windowed.c.name,
                windowed.c.same,
                windowed.c.tie_safe,
            )
            .select_from(counts)
            .outerjoin(
                windowed,
                and_(windowed.c.item == counts.c.item, windowed.c.rank <= AMBIGUOUS_CANDIDATES + 1),
            )
            .order_by(counts.c.item, windowed.c.rank)
        ).all()
        tops: dict[int, tuple[int, list[Any]]] = {}
        for row in rows:
            _count, found = tops.setdefault(row.item, (row.matched, []))
            if row.id is not None:
                found.append(row)
        return tops


def _text_match(stored: Any, terms: Any, contains_pattern: str | None) -> Any:
    """``stored`` holds the contains pattern (through a trigram index, 20261005_02) or, exactly,
    equals a term of ``terms`` ignoring case (through its ``lower(…)`` index, 20261005_01)."""
    if contains_pattern is not None:
        return stored.ilike(contains_pattern, escape="\\")
    return func.lower(stored) == func.lower(terms.c.text)


@dataclass(frozen=True)
class Found:
    """A lookup's single best object and its score."""

    id: str
    score: int


def resolve_lookups(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace_key: str,
    lookups: Sequence[Sequence[str]],
    narrowed: ConsumerFilter,
) -> list[Found | ApiError]:
    """Each lookup's ``expect=one`` answer (C-D40): its single top object, or the refusal the single
    read gives: ``404 NO_MATCH``, ``409 AMBIGUOUS_MATCH`` naming the tied objects, ``400
    QUERY_TOO_BROAD``. Exact rules first, contains only for the lookups they leave unsettled (C-D52)."""
    if definition.match is None:
        return [_no_match() for _ in lookups]
    match = definition.match
    has_contains = any(rule.contains is not None for rule in match.own) or any(
        rule.contains is not None for entry in match.promoted for rule in entry.firstMatch
    )
    ceiling = contains_ceiling(match)
    answers: list[Found | ApiError | None] = [None] * len(lookups)
    exact = _Scoring(model, definition, workspace_key, lookups, narrowed, contains=False).tops(session)
    unsettled = []
    for item, terms in enumerate(lookups):
        matched, rows = exact.get(item, (0, []))
        reads_contains = has_contains and any(len(term) >= MIN_INDEXED_LENGTH for term in terms)
        if matched > MATCH_LIMIT:
            answers[item] = _too_broad()
        elif not reads_contains or (rows and rows[0].score > ceiling and rows[0].tie_safe):
            answers[item] = _decided(rows)
        else:
            unsettled.append(item)
    for chunk in _chunks(unsettled, lookups):
        full = _Scoring(model, definition, workspace_key, [lookups[item] for item in chunk], narrowed).tops(session)
        for number, item in enumerate(chunk):
            matched, rows = full.get(number, (0, []))
            answers[item] = _too_broad() if matched > MATCH_LIMIT else _decided(rows)
    return [answer for answer in answers if answer is not None]


def _chunks(items: Sequence[int], lookups: Sequence[Sequence[str]]) -> list[list[int]]:
    """``items`` in order, in runs of at most :data:`CONTAINS_TERMS_PER_STATEMENT` contains terms
    (a lookup with more stays whole)."""
    chunks: list[list[int]] = []
    held = 0
    for item in items:
        terms = sum(1 for term in lookups[item] if len(term) >= MIN_INDEXED_LENGTH)
        if not chunks or held + terms > CONTAINS_TERMS_PER_STATEMENT:
            chunks.append([])
            held = 0
        chunks[-1].append(item)
        held += terms
    return chunks


def _no_match() -> ApiError:
    return api_error(404, "NO_MATCH", "No object matches the query")


def _decided(rows: Sequence[Any]) -> Found | ApiError:
    """The top object of ordered rows, or the refusal when there is none or the top is shared."""
    if not rows:
        return _no_match()
    top = rows[0]
    if top.same > 1:
        tied = [row for row in rows if row.score == top.score]
        return api_error(
            409,
            "AMBIGUOUS_MATCH",
            f"{top.same} objects share the top score {top.score}; the query does not identify one",
            {
                "count": top.same,
                "candidates": [
                    {"id": row.id, "objectType": row.public_name, "name": row.name, "matchScore": row.score}
                    for row in tied[:AMBIGUOUS_CANDIDATES]
                ],
            },
        )
    return Found(top.id, top.score)


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
    carries ``matchScore`` after its declared fields (C-D41), and with a crosswalk target ``target``
    before it (C15). ``parameters`` are the request's parameter values, bound into the cursor with the
    terms, the workspace and the contract version; a ``to.`` value is not bound (C-D54)."""
    composer = ConsumerObjects(model, definition)
    if expect_one:
        (answer,) = resolve_lookups(session, model, definition, workspace_key, [terms], narrowed)
        if isinstance(answer, ApiError):
            raise answer
        composed = composer.compose(session, workspace_key, [answer.id], narrowed)
        return {**one_target(composed[answer.id], answer.id, narrowed.target), "matchScore": answer.score}
    ranked = None
    if definition.match is not None:
        scoring = _Scoring(model, definition, workspace_key, [terms], narrowed)
        counted = scoring.matched()
        matched = session.scalar(select(counted.subquery().c.matched)) if counted is not None else 0
        if (matched or 0) > MATCH_LIMIT:
            raise _too_broad()
        ranked = scoring.ranked()
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
            "parameters": {name: sorted(values) for name, values in sorted(without_target(parameters).items())},
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

