"""Which unmapped sources a proposal job asks about, and the candidates each may take (Product 0.16
AP2, AP2-D2), selected in PostgreSQL when the job binds.

The view's unmapped sources, in the change set's context, become the job's inputs, one row each, in
one ``INSERT … SELECT``; no source is read into Python. The candidates are the targets the mapping
grid's candidate search would offer (``MappingScope.eligible_clauses``): when at most ``WHOLE_LIST``
are eligible every call gets the whole list, stored once with the job; otherwise each source's input
carries its ``PER_SOURCE`` closest by ``pg_trgm`` similarity of the target's name and candidate
search fields to the source's name and source columns, found with a ``LATERAL`` top-N so the pairs
are scored in the database and only the winners are kept.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    Select,
    String,
    and_,
    func,
    insert,
    literal,
    literal_column,
    select,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from ...models.database import Job, JobInput, RelationSetVersion
from ..reads.mapping_scope import MappingScope

# At most this many eligible targets and every call gets the whole list; more and each source gets
# its own closest ones.
WHOLE_LIST = 100
PER_SOURCE = 20


@dataclass(frozen=True)
class Selection:
    """What binding stored: the number of sources (the job's total) and the candidates every call
    shares, or ``None`` when each source's input holds its own."""

    total: int
    whole_list: list[dict[str, Any]] | None


def _key(name: str) -> Any:
    """A JSON key as a SQL literal (a model's attribute key: never a request's text)."""
    return literal_column("'" + name.replace("'", "''") + "'")


def _fields(attributes: Any, columns: list[str]) -> Any:
    """``{column: value as text}`` of the columns an object has, in SQL."""
    pairs: list[Any] = []
    for column in columns:
        pairs += [_key(column), attributes[column].as_string()]
    return func.json_strip_nulls(func.json_build_object(*pairs))


def _text(name: Any, attributes: Any, columns: list[str]) -> Any:
    """The name and the fields as one text, what similarity compares."""
    return func.concat_ws(" ", name, *(attributes[column].as_string() for column in columns))


def eligible_count(session: Session, scope: MappingScope) -> int:
    return (
        session.scalar(select(func.count()).select_from(scope.eligible_targets().subquery())) or 0
    )


def _whole_list(session: Session, scope: MappingScope) -> list[dict[str, Any]]:
    columns = scope.attribute_columns(scope.config.targetDisplayColumns)
    found = session.execute(scope.eligible_targets().order_by("name", "id"))
    return [
        {
            "id": row.id,
            "name": row.name,
            "fields": {
                column: str(value)
                for column in columns
                if (value := (row.attributes or {}).get(column)) is not None
            },
        }
        for row in found
    ]


def _sources(scope: MappingScope, change_set_id: str, **narrowing: Any) -> Any:
    """The unmapped sources with the version of the set each is the anchor of."""
    unmapped = scope.unmapped_sources(**narrowing).subquery("unmapped")
    config = scope.config
    return (
        select(
            unmapped.c.id,
            unmapped.c.name,
            unmapped.c.attributes,
            func.coalesce(RelationSetVersion.version, 0).label("version"),
        )
        .select_from(unmapped)
        .outerjoin(
            RelationSetVersion,
            and_(
                RelationSetVersion.workspace_key == scope.workspace_key,
                RelationSetVersion.change_set_id == change_set_id,
                RelationSetVersion.relation_type_key == config.relationTypeKey,
                RelationSetVersion.from_object_type_key == config.fromObjectTypeKey,
                RelationSetVersion.to_object_type_key == config.toObjectTypeKey,
                RelationSetVersion.direction == config.direction,
                RelationSetVersion.anchor_object_id == unmapped.c.id,
            ),
        )
        .subquery("sources")
    )


def bind(
    session: Session,
    job: Job,
    scope: MappingScope,
    *,
    application_key: str,
    parent_object_id: str | None,
    search: str | None,
    fits_whole_list: Callable[[list[dict[str, Any]]], bool] = lambda _: True,
) -> Selection:
    """Store the job's inputs: one per unmapped source of the view, ordered by name. The caller
    sets the job's total from the result."""
    assert scope.change_set_id is not None
    config = scope.config
    sources = _sources(
        scope,
        scope.change_set_id,
        application_key=application_key,
        parent_object_id=parent_object_id,
        search=search,
    )
    source_columns = scope.attribute_columns(config.sourceColumns)
    base = [
        _key("sourceId"),
        sources.c.id,
        _key("mappingVersion"),
        sources.c.version,
        _key("name"),
        sources.c.name,
        _key("fields"),
        _fields(sources.c.attributes, source_columns),
    ]
    whole_list: list[dict[str, Any]] | None = None
    if eligible_count(session, scope) <= WHOLE_LIST:
        whole_list = _whole_list(session, scope)
        # A list too large for the model's window with one source (AI_CONTEXT_TOKENS): each
        # source gets its closest instead.
        if not fits_whole_list(whole_list):
            whole_list = None
    if whole_list is not None:
        statement: Select[Any] = select(
            literal(job.sequence_id),
            (func.row_number().over(order_by=(sources.c.name, sources.c.id)) - 1),
            sources.c.id.cast(String),
            func.json_build_object(*base),
        )
    else:
        statement = _with_closest(scope, sources, base, source_columns, job)
    session.execute(
        insert(JobInput).from_select(["job_id", "item_index", "ref", "item"], statement)
    )
    total = session.scalar(select(func.count()).where(JobInput.job_id == job.sequence_id)) or 0
    return Selection(total, whole_list)


def _with_closest(
    scope: MappingScope, sources: Any, base: list[Any], source_columns: list[str], job: Job
) -> Select[Any]:
    """Each source with its ``PER_SOURCE`` closest eligible targets, scored in PostgreSQL."""
    config = scope.config
    eligible = scope.eligible_targets().cte("eligible").prefix_with("MATERIALIZED")
    target_display = scope.attribute_columns(config.targetDisplayColumns)
    search_columns = scope.attribute_columns(config.candidateSearchFields)
    source_text = _text(sources.c.name, sources.c.attributes, source_columns)
    target_text = _text(eligible.c.name, eligible.c.attributes, search_columns)
    score = func.greatest(
        func.similarity(eligible.c.name, sources.c.name),
        func.word_similarity(sources.c.name, eligible.c.name),
        func.similarity(target_text, source_text),
    )
    closest = (
        select(
            eligible.c.id,
            eligible.c.name,
            eligible.c.attributes,
            score.label("score"),
        )
        .order_by(score.desc(), eligible.c.name, eligible.c.id)
        .limit(PER_SOURCE)
        .correlate(sources)
        .subquery("closest")
    )
    candidate = func.json_build_object(
        _key("id"),
        closest.c.id,
        _key("name"),
        closest.c.name,
        _key("fields"),
        _fields(closest.c.attributes, target_display),
    )
    candidates = (
        select(
            func.coalesce(
                func.json_agg(
                    aggregate_order_by(
                        candidate, closest.c.score.desc(), closest.c.name, closest.c.id
                    )
                ),
                literal_column("'[]'::json"),
            )
        )
        .select_from(closest)
        .correlate(sources)
        .scalar_subquery()
    )
    with_candidates = select(
        sources.c.id,
        sources.c.name,
        sources.c.attributes,
        sources.c.version,
        candidates.label("candidates"),
    ).subquery("with_candidates")
    grouped = with_candidates.c
    return select(
        literal(job.sequence_id),
        (func.row_number().over(order_by=(grouped.name, grouped.id)) - 1),
        grouped.id.cast(String),
        func.json_build_object(
            _key("sourceId"),
            grouped.id,
            _key("mappingVersion"),
            grouped.version,
            _key("name"),
            grouped.name,
            _key("fields"),
            _fields(grouped.attributes, source_columns),
            _key("candidates"),
            grouped.candidates,
        ),
    )
