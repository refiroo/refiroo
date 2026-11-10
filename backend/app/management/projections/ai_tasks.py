"""Assistant tasks as the API answers them (Product 0.16 AP6a)."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...engine.identity.principals import named, ref
from ...engine.jobs.worker import ASSISTANT_KINDS
from ...engine.tasks import agent
from ...engine.tasks.model_changes import model_changes
from ...models.database import AiTask, Job, ModelDraft, ModelRelease, SourceFile
from ..schemas.ai_tasks import AiTaskPage, AiTaskResponse, TaskChange, TaskChangePage

_JOB_PHASES = {"profiling", "reading", "designing", "checking"}


def _phase(session: Session, task: AiTask) -> str | None:
    """What the running job is doing; ``None`` when none runs."""
    if task.state not in ("reading", "checking") or task.job_id is None:
        return None
    job = session.scalar(select(Job).where(Job.id == task.job_id))
    if job is None or job.state != "running":
        return None
    if job.kind == "dryRun":
        return "checking"
    return job.stage if job.stage in _JOB_PHASES else None


def _ahead(session: Session, task: AiTask) -> int | None:
    """The assistant jobs before the task's queued job, in the order the worker takes them (0.13 AQ,
    AQ-D5): a close count, not a promise. ``None`` once the job runs, or when none waits."""
    if task.state not in ("reading", "checking") or task.job_id is None:
        return None
    job = session.scalar(select(Job).where(Job.id == task.job_id))
    if job is None or job.state != "queued" or job.kind not in ASSISTANT_KINDS:
        return None
    return session.scalar(
        select(func.count())
        .select_from(Job)
        .where(
            Job.kind.in_(ASSISTANT_KINDS),
            Job.state.in_(("queued", "running")),
            Job.sequence_id < job.sequence_id,
        )
    )


def _design(session: Session, task: AiTask) -> dict[str, Any] | None:
    """The design with its model changes as the draft holds them now, against the model it was drafted
    on: what the assistant did, by whatever steps, and what the person changed since in the editor."""
    if task.design is None or task.draft_id is None:
        return task.design
    draft = session.get(ModelDraft, task.draft_id)
    if draft is None:
        return task.design
    base_id = task.design.get("modelBaseReleaseId") or draft.base_model_release_id
    release = session.get(ModelRelease, base_id) if base_id else None
    base = release.model_json if release else {}
    return {**task.design, "operations": model_changes(base, draft.model_json)}


def _can_tell(task: AiTask) -> bool:
    """Whether the person may tell the assistant something now (AP-D54): the assistant is on and the
    task is where it goes on, or a loaded one whose session still lives."""
    if not agent.enabled():
        return False
    if task.state in ("checked", "failed", "stopped"):
        return True
    return task.state == "loaded" and agent.lives(task) and not (task.result or {}).get("published")


def task_response(session: Session, task: AiTask) -> AiTaskResponse:
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    return AiTaskResponse.model_validate(
        {
            "id": task.public_id,
            "workspaceKey": task.workspace_key,
            "fileName": source.name if source else "",
            "sourceFileId": source.public_id if source else "",
            "words": task.words,
            "title": task.title,
            "state": task.state,
            "version": task.version,
            "jobId": task.job_id,
            "phase": _phase(session, task),
            "createdAt": as_utc(task.created_at),
            "updatedAt": as_utc(task.updated_at),
            "requestedBy": named(
                session, ref(task.requested_by_user_id, task.requested_by_client_id)
            ),
            "reading": task.reading,
            "check": task.check,
            "design": _design(session, task),
            "draftId": (
                session.scalar(select(ModelDraft.public_id).where(ModelDraft.id == task.draft_id))
                if task.draft_id is not None
                else None
            ),
            "notes": task.notes,
            "result": task.result,
            "canTell": _can_tell(task),
            "ahead": _ahead(session, task),
        }
    )


def task_page(session: Session, page: Page[AiTask]) -> AiTaskPage:
    return AiTaskPage(items=[task_response(session, task) for task in page.items], **page.links())


def change_page(items: list[dict[str, Any]], page: Page[Any]) -> TaskChangePage:
    return TaskChangePage(items=[TaskChange.model_validate(item) for item in items], **page.links())
