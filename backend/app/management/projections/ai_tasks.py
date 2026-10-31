"""Assistant tasks as the API answers them (Product 0.16 AP6a)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...engine.identity.principals import named, ref
from ...models.database import AiTask, Job, ModelDraft, ModelDraftOperation, SourceFile
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


def _design(session: Session, task: AiTask) -> dict[str, Any] | None:
    """The design with its model changes as the draft's history holds them now: what the assistant
    applied and what the person changed since in the model editor, without what was undone."""
    if task.design is None or task.draft_id is None:
        return task.design
    applied = [
        {"kind": kind, **parameters}
        for kind, parameters in session.execute(
            select(ModelDraftOperation.kind, ModelDraftOperation.parameters)
            .where(
                ModelDraftOperation.draft_id == task.draft_id,
                ModelDraftOperation.undone_by_step.is_(None),
                ModelDraftOperation.origin["type"].as_string() != "undo",
            )
            .order_by(ModelDraftOperation.sequence)
        )
    ]
    return {**task.design, "operations": applied}


def task_response(session: Session, task: AiTask) -> AiTaskResponse:
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    plan = {"profile": task.plan["profile"], "steps": task.plan["steps"]} if task.plan else None
    return AiTaskResponse.model_validate(
        {
            "id": task.public_id,
            "workspaceKey": task.workspace_key,
            "fileName": source.name if source else "",
            "sourceFileId": source.public_id if source else "",
            "words": task.words,
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
            "plan": plan,
            "check": task.check,
            "design": _design(session, task),
            "draftId": (
                session.scalar(select(ModelDraft.public_id).where(ModelDraft.id == task.draft_id))
                if task.draft_id is not None
                else None
            ),
            "notes": task.notes,
            "result": task.result,
        }
    )


def task_page(session: Session, page: Page[AiTask]) -> AiTaskPage:
    return AiTaskPage(items=[task_response(session, task) for task in page.items], **page.links())


def change_page(items: list[dict[str, Any]], page: Page[Any]) -> TaskChangePage:
    return TaskChangePage(items=[TaskChange.model_validate(item) for item in items], **page.links())
