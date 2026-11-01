"""Loading a workbook into a workspace with the assistant (Product 0.16 AP6a, AP-D12 to AP-D26).

``router`` reads tasks and is always registered; ``write_router`` creates, plans, runs and cancels
them and is registered only with ``INTEGRATION_JOBS_ENABLED``, as imports are. Every route needs
Bulk and import in the task's workspace (``bulk.write``) and Use AI proposals there; a task is
visible to its requester and to those who administer its workspace, otherwise ``404
AI_TASK_NOT_FOUND`` (AP-D23).
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Json
from sqlalchemy.orm import Session

from ...engine.imports.submit import Upload
from ...engine.jobs.inline import BatchLimits
from ...engine.model.registry import resolve_model_snapshot
from ...engine.tasks import changes, design_job
from ...engine.tasks import job as task_job
from ...engine.tasks import store as task_store
from ...errors import api_error
from ...models.commands import (
    AiTaskAcceptRequest,
    AiTaskAnswersRequest,
    AiTaskCorrectionRequest,
    AiTaskRequest,
    AiTaskRunRequest,
)
from ...models.database import AiTask, ModelDraft
from ..access import AI_TASK_PATH, IMPORT_FORM, SIGNED_IN, AuthorizedRoute, forbidden, requires
from ..ai import GROUP, assistant_requested, configuration
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import ai_tasks as present
from ..schemas.ai_tasks import AiTaskPage, AiTaskResponse, TaskChangePage

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["ai"])
write_router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["ai"])


def _wake(request: Request) -> None:
    worker = getattr(request.app.state, "assistant_worker", None)
    if worker is not None:
        worker.wake()


def _visible(
    request: Request, session: Session, principal: CurrentPrincipal, task_id: str
) -> AiTask:
    """The task, for a caller who may see it and holds Use AI proposals in its workspace, its
    state brought up to date with the job it waits for."""
    task = task_store.load_task(session, task_id)
    permissions = request.state.permissions
    if not task_store.may_see(task, permissions, principal.kind, principal.row_id):
        raise task_store.not_found(task_id)
    if not permissions.allows(GROUP, task.workspace_key):
        raise api_error(
            403,
            "FORBIDDEN",
            f"Using AI proposals in workspace '{task.workspace_key}' needs Use AI proposals",
            {"action": "ai-proposals", "groups": [GROUP], "workspaceKey": task.workspace_key},
        )
    task_store.sync(session, task, configuration(request).task_retention_days)
    session.commit()
    return task


@write_router.post("/ai/tasks", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=IMPORT_FORM)
def create_ai_task(
    request: Request,
    session: DbSession,
    payload: Annotated[
        Json[AiTaskRequest],
        Form(
            alias="request",
            description="The request as JSON: workspaceKey, the person's words and sendLevel",
        ),
    ],
    file: Annotated[
        UploadFile | None,
        File(
            description="The XLSX workbook or CSV file; without one, the words are an instruction "
            "on the workspace's records"
        ),
    ] = None,
) -> JSONResponse:
    """Give the assistant a workbook and the workspace it goes into (0.16 AP6a).

    Answers 202 with the task, ``reading``, and the job that reads it. Nothing in the workspace
    changes. Refused before a task exists: ``403 FORBIDDEN`` without Use AI proposals, ``409
    AI_NOT_CONFIGURED``, ``409 AI_SEND_LEVEL_TOO_LOW``, ``413 IMPORT_TOO_LARGE``, ``422
    UNSUPPORTED_FILE_FORMAT``.
    """
    assistant_requested(request, workspace_key=payload.workspaceKey, send_level=payload.sendLevel)
    ai = configuration(request)
    limits: BatchLimits = request.app.state.batch_limits
    upload = (
        Upload.read(file.filename or "", file.file, limits.import_max_bytes)
        if file is not None
        else None
    )
    if upload is None and not (payload.words or "").strip():
        raise api_error(
            422,
            "AI_TASK_NEEDS_WORDS",
            "Without a workbook, say in a few words what the assistant should do",
        )
    task = task_job.submit(
        session,
        workspace_key=payload.workspaceKey,
        words=payload.words,
        upload=upload,
        send_level=payload.sendLevel,
        files=request.app.state.job_files,
        retention_days=limits.retention_days,
        task_retention_days=ai.task_retention_days,
    )
    _wake(request)
    return _accepted(session, task)


def _accepted(session: Session, task: AiTask) -> JSONResponse:
    return JSONResponse(
        present.task_response(session, task).model_dump(mode="json", by_alias=True),
        status_code=202,
    )


@router.get("/ai/tasks", response_model=AiTaskPage)
@requires("signed-in", at=SIGNED_IN)
def list_ai_tasks(
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> AiTaskPage:
    """The caller's tasks, and those of the workspaces they administer, newest first."""
    permissions = request.state.permissions
    page = task_store.task_page(
        session,
        visible_to=task_store.visible(permissions, principal.kind, principal.row_id),
        page=paging,
        page_size=page_size,
    )
    for task in page.items:
        task_store.sync(session, task, configuration(request).task_retention_days)
    session.commit()
    return present.task_page(session, page)


@router.get("/ai/tasks/{task_id}", response_model=AiTaskResponse)
@requires("bulk.write", at=AI_TASK_PATH)
def get_ai_task(
    task_id: str, request: Request, session: DbSession, principal: CurrentPrincipal
) -> AiTaskResponse:
    """The task: its state, the reading per table, the plan, the latest check and the result."""
    return present.task_response(session, _visible(request, session, principal, task_id))


@router.get("/ai/tasks/{task_id}/changes", response_model=TaskChangePage)
@requires("bulk.write", at=AI_TASK_PATH)
def list_ai_task_changes(
    task_id: str,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
    paging: PageQuery,
    source: int | None = Query(
        default=None, description="A design's sheet: its source in the check's sheets"
    ),
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> TaskChangePage:
    """The records the latest check would change in a sheet of the check (``source``), each with the fields that differ and what it holds now and after.
    ``409 AI_TASK_STATE`` before a check, ``422 AI_TASK_TABLE_UNKNOWN``."""
    task = _visible(request, session, principal, task_id)
    model = resolve_model_snapshot(session, task.workspace_key).model
    items, page = changes.change_page(
        session, task, model, source_index=source, page=paging, page_size=page_size
    )
    return present.change_page(items, page)


@write_router.post("/ai/tasks/{task_id}/run", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def run_ai_task(
    task_id: str,
    payload: AiTaskRunRequest,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Load the checked plan into a new change set (named after the file unless ``changeSetName``
    says otherwise); live data is unchanged. ``saveProfile`` keeps the plan as an import profile.
    Allowed when the task is ``checked``. Refused: ``403 FORBIDDEN`` without Work in change sets,
    ``409 AI_TASK_VERSION_CONFLICT``, ``409 AI_TASK_STATE``, ``409 IMPORT_PROFILE_EXISTS``."""
    task = _visible(request, session, principal, task_id)
    if not request.state.permissions.allows("change-sets", task.workspace_key):
        raise forbidden("records.write", ("change-sets",), task.workspace_key)
    limits: BatchLimits = request.app.state.batch_limits
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id is not None else None
    if draft is not None:
        if design_job.changes_model(session, draft):
            # A design that changes the model installs it and activates it in the workspace.
            permissions = request.state.permissions
            if not permissions.allows("model-release", None):
                raise forbidden("model.install", ("model-release",), None)
            if not permissions.allows("model-release", task.workspace_key):
                raise forbidden("model.activate", ("model-release",), task.workspace_key)
        task = design_job.queue_load(
            session,
            task_id,
            payload.expectedVersion,
            change_set_name=payload.changeSetName,
            save_profile=payload.saveProfile.model_dump() if payload.saveProfile else None,
            files=request.app.state.job_files,
            import_max_bytes=limits.import_max_bytes,
            max_operations=request.app.state.model_operation_max_items,
            retention_days=limits.retention_days,
            task_retention_days=configuration(request).task_retention_days,
        )
        _wake(request)
        return _accepted(session, task)
    raise api_error(409, "AI_TASK_NOTHING_TO_LOAD", "The task holds nothing to load")


@write_router.post("/ai/tasks/{task_id}/answers", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def answer_ai_task(
    task_id: str,
    payload: AiTaskAnswersRequest,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Answer the design's questions (0.16 AP6): the assistant designs again with the answers and
    the design is checked again. Allowed when the task is ``checked`` and has a design. Refused:
    ``409 AI_TASK_VERSION_CONFLICT``, ``409 AI_TASK_STATE``."""
    _visible(request, session, principal, task_id)
    limits: BatchLimits = request.app.state.batch_limits
    task = design_job.queue_answers(
        session,
        task_id,
        payload.expectedVersion,
        payload.answers,
        retention_days=limits.retention_days,
        task_retention_days=configuration(request).task_retention_days,
    )
    _wake(request)
    return _accepted(session, task)


@write_router.post("/ai/tasks/{task_id}/model", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def correct_ai_task_model(
    task_id: str,
    payload: AiTaskCorrectionRequest,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Correct the proposed model in words (0.16 AP6r): the assistant proposes the model again,
    the correction winning over its own choices. Allowed when the task is ``checked`` and has a
    design. Refused: ``409 AI_TASK_VERSION_CONFLICT``, ``409 AI_TASK_STATE``."""
    _visible(request, session, principal, task_id)
    limits: BatchLimits = request.app.state.batch_limits
    task = design_job.queue_correction(
        session,
        task_id,
        payload.expectedVersion,
        payload.correction,
        retention_days=limits.retention_days,
        task_retention_days=configuration(request).task_retention_days,
    )
    _wake(request)
    return _accepted(session, task)


@write_router.post("/ai/tasks/{task_id}/accept", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def accept_ai_task_model(
    task_id: str,
    payload: AiTaskAcceptRequest,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Accept the proposed model (0.16 AP6r): the assistant maps the sheets onto it and every row
    is checked in a dry run; nothing is installed or loaded before ``/run``. Refused:
    ``409 AI_TASK_VERSION_CONFLICT``, ``409 AI_TASK_STATE`` (no proposal to accept)."""
    _visible(request, session, principal, task_id)
    limits: BatchLimits = request.app.state.batch_limits
    task = design_job.queue_accept(
        session,
        task_id,
        payload.expectedVersion,
        retention_days=limits.retention_days,
        task_retention_days=configuration(request).task_retention_days,
    )
    _wake(request)
    return _accepted(session, task)


@write_router.post("/ai/tasks/{task_id}/retry", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def retry_ai_task(
    task_id: str,
    payload: AiTaskAcceptRequest,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Try a stopped session again (0.16): it goes on from where it was, its folder and session
    kept. ``409 AI_TASK_STATE`` unless the task failed and has a session."""
    _visible(request, session, principal, task_id)
    limits: BatchLimits = request.app.state.batch_limits
    task = design_job.queue_retry(
        session,
        task_id,
        payload.expectedVersion,
        retention_days=limits.retention_days,
        task_retention_days=configuration(request).task_retention_days,
    )
    _wake(request)
    return _accepted(session, task)


@write_router.post("/ai/tasks/{task_id}/discard", response_model=AiTaskResponse)
@requires("bulk.write", at=AI_TASK_PATH)
def discard_ai_task(
    task_id: str,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> AiTaskResponse:
    """Throw a proposal away: the task ends ``cancelled``, its draft and working folder go. Nothing
    was installed or loaded. ``409 AI_TASK_STATE`` unless the task waits for the person."""
    _visible(request, session, principal, task_id)
    task = design_job.discard(
        session,
        task_id,
        request.app.state.job_files,
        configuration(request).task_retention_days,
    )
    return present.task_response(session, task)


@write_router.post("/ai/tasks/{task_id}/cancel", response_model=AiTaskResponse, status_code=202)
@requires("bulk.write", at=AI_TASK_PATH)
def cancel_ai_task(
    task_id: str,
    request: Request,
    session: DbSession,
    principal: CurrentPrincipal,
) -> JSONResponse:
    """Ask the job the task waits for (its reading or its check) to stop; the task becomes
    ``cancelled`` when it does. A task that is loading is stopped through its import job. ``409
    AI_TASK_STATE`` otherwise."""
    _visible(request, session, principal, task_id)
    task = task_job.request_cancel(session, task_id, None)
    _wake(request)
    return _accepted(session, task)
