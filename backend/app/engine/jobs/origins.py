"""Where a job comes from, and jobs grouped by it (0.13 JG).

A job's origin is the assistant task it belongs to (an ``aiTask`` job names it in its parameters;
every other job its session queued was requested by the task's session client) or else the model
draft it works on (``parameters.draftId``). It is worked out in the query, by joins, so a list of
any size is grouped by the database: one row per origin and one per job without one, newest
activity first.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, String, and_, case, cast, func, literal, select
from sqlalchemy.orm import Session, aliased

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import AiTask, Job, ModelDraft, SourceFile

ORIGIN_KINDS = ("aiTask", "modelDraft")
STATES = (
    "queued",
    "running",
    "awaiting_confirmation",
    "completed",
    "failed",
    "cancelled",
    "expired",
)
# The longest an instruction is shown as a task's name, as the assistant page shows it.
_WORDS_NAME = 80


@dataclass(frozen=True)
class JobOrigin:
    kind: str
    id: str
    name: str


@dataclass(frozen=True)
class JobGroup:
    """One row of the grouped list: an origin with its jobs, or a job without one."""

    origin: JobOrigin | None
    jobs: int
    states: dict[str, int]
    latest_at: datetime
    latest_sequence_id: int


def parse_origin(text: str) -> tuple[str, str]:
    """``aiTask:<id>`` or ``modelDraft:<id>`` as a kind and an ID."""
    kind, _, identifier = text.partition(":")
    if kind not in ORIGIN_KINDS or not identifier:
        raise api_error(
            422,
            "INVALID_ORIGIN",
            "origin must be aiTask:<id> or modelDraft:<id>",
            {"path": "/query/origin"},
        )
    return kind, identifier


def _tasks() -> Any:
    """Assistant tasks with the name the assistant page shows: the workbook's file name, else the
    instruction (shortened), else ``Instruction``."""
    file_name = (
        select(SourceFile.name)
        .where(SourceFile.task_id == AiTask.id)
        .order_by(SourceFile.id)
        .limit(1)
        .scalar_subquery()
    )
    words = func.trim(func.coalesce(AiTask.words, ""))
    shortened = case(
        (func.length(words) > _WORDS_NAME, func.left(words, _WORDS_NAME - 1) + literal("…")),
        else_=words,
    )
    name = func.coalesce(func.nullif(file_name, ""), func.nullif(shortened, ""), "Instruction")
    return select(AiTask.id, AiTask.public_id, AiTask.client_id, name.label("name")).subquery(
        "origin_tasks"
    )


def _origin_query(*columns: Any) -> tuple[Select[Any], Any, Any, Any]:
    """Jobs joined to their task and draft: the origin's kind, ID and name as columns."""
    tasks = _tasks()
    by_parameter = tasks.alias("task_by_parameter")
    by_client = tasks.alias("task_by_client")
    draft = aliased(ModelDraft)
    has_task = func.coalesce(by_parameter.c.id, by_client.c.id).is_not(None)
    kind = case((has_task, "aiTask"), (draft.id.is_not(None), "modelDraft"), else_=None)
    identifier = case(
        (has_task, func.coalesce(by_parameter.c.public_id, by_client.c.public_id)),
        (draft.id.is_not(None), draft.public_id),
        else_=None,
    )
    name = case(
        (has_task, func.coalesce(by_parameter.c.name, by_client.c.name)),
        (draft.id.is_not(None), draft.name),
        else_=None,
    )
    statement = (
        select(
            *columns,
            kind.label("origin_kind"),
            identifier.label("origin_id"),
            name.label("origin_name"),
        )
        .select_from(Job)
        .outerjoin(by_parameter, by_parameter.c.public_id == Job.task_ref)
        .outerjoin(by_client, by_client.c.client_id == Job.requested_by_client_id)
        .outerjoin(draft, draft.public_id == Job.draft_ref)
    )
    return statement, kind, identifier, name


def origins_of(session: Session, jobs: list[Job]) -> dict[int, JobOrigin]:
    """The origin of each of these jobs that has one, by sequence ID: one query for the lot."""
    if not jobs:
        return {}
    statement, _, _, _ = _origin_query(Job.sequence_id)
    rows = session.execute(
        statement.where(Job.sequence_id.in_([job.sequence_id for job in jobs]))
    ).all()
    return {
        row.sequence_id: JobOrigin(row.origin_kind, row.origin_id, row.origin_name)
        for row in rows
        if row.origin_kind is not None
    }


def origin_job_ids(kind: str, identifier: str) -> Any:
    """A select of the sequence IDs of one origin's jobs."""
    statement, origin_kind, origin_id, _ = _origin_query(Job.sequence_id)
    return statement.where(and_(origin_kind == kind, origin_id == identifier)).with_only_columns(
        Job.sequence_id
    )


def grouped_page(
    session: Session,
    *,
    visible: Any,
    workspace_key: str | None,
    kind: str | None,
    state: str | None,
    origin: tuple[str, str] | None,
    page: PageRequest,
    page_size: int,
) -> tuple[Page[Any], dict[int, Job]]:
    """The jobs one row per origin and one per job without one, newest activity first, and the
    newest job of each row. Counts are of the jobs the filters leave."""
    statement, origin_kind, origin_id, _name = _origin_query(
        Job.sequence_id, Job.state, Job.created_at
    )
    if visible is not None:
        statement = statement.where(visible)
    if workspace_key is not None:
        statement = statement.where(Job.workspace_key == workspace_key)
    if kind is not None:
        statement = statement.where(Job.kind == kind)
    if state is not None:
        statement = statement.where(Job.state == state)
    if origin is not None:
        statement = statement.where(and_(origin_kind == origin[0], origin_id == origin[1]))
    tagged = statement.subquery("tagged")
    group_key = func.coalesce(
        tagged.c.origin_kind + literal(":") + tagged.c.origin_id,
        literal("job:") + cast(tagged.c.sequence_id, String),
    )
    grouped = (
        select(
            func.max(tagged.c.sequence_id).label("latest_sequence_id"),
            func.max(tagged.c.created_at).label("latest_at"),
            func.count().label("jobs"),
            func.max(tagged.c.origin_kind).label("origin_kind"),
            func.max(tagged.c.origin_id).label("origin_id"),
            func.max(tagged.c.origin_name).label("origin_name"),
            *(
                func.count().filter(tagged.c.state == name).label(f"state_{name}")
                for name in STATES
            ),
        )
        .group_by(group_key)
        .subquery("grouped")
    )
    rows = paginate_statement(
        session,
        select(grouped),
        keys=(
            integer_key(
                "latestSequenceId",
                grouped.c.latest_sequence_id,
                "latest_sequence_id",
                descending=True,
            ),
        ),
        scope="jobs-grouped",
        filters={
            "workspaceKey": workspace_key,
            "kind": kind,
            "state": state,
            "origin": None if origin is None else f"{origin[0]}:{origin[1]}",
        },
        page=page,
        page_size=page_size,
        message="Job list cursor is invalid",
        rows=True,
    )
    newest = {
        job.sequence_id: job
        for job in session.scalars(
            select(Job).where(Job.sequence_id.in_([row.latest_sequence_id for row in rows.items]))
        )
    }
    return rows, newest


def group_of(row: Any) -> JobGroup:
    origin = (
        None
        if row.origin_kind is None
        else JobOrigin(row.origin_kind, row.origin_id, row.origin_name)
    )
    return JobGroup(
        origin=origin,
        jobs=row.jobs,
        states={name: getattr(row, f"state_{name}") for name in STATES},
        latest_at=row.latest_at,
        latest_sequence_id=row.latest_sequence_id,
    )
