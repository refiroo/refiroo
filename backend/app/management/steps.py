"""A model draft step's answer (0.10 A2, A5, A6): shared by the operation, undo, redo and
inference application routes."""

from fastapi import Request
from sqlalchemy.orm import Session

from ..engine.model.authoring import history
from ..engine.sources import draft_profile
from .presenters import diagnostic_response
from .schemas.model import ModelDraftOperationEntry, ModelDraftStepResponse, StepDryRun


def step_response(session: Session, result: history.StepResult, request: Request) -> ModelDraftStepResponse:
    """The step's answer; a step that can change what the load writes queues the draft's dry run
    when integration jobs are enabled (0.10 A5, D79). Commits."""
    response = ModelDraftStepResponse(
        version=result.draft.version,
        entries=[ModelDraftOperationEntry(**history.entry_response(row)) for row in result.entries],
        valid=result.valid,
        diagnostics=[diagnostic_response(item) for item in result.diagnostics],
        dryRun=None,
    )
    job = None
    if request.app.state.integration_jobs_enabled:
        job = draft_profile.dry_run_after(
            session,
            result.draft,
            list(result.operations),
            retention_days=request.app.state.batch_limits.retention_days,
        )
    session.commit()
    if job is not None:
        response.dryRun = StepDryRun(state="checking", jobId=job.id)
        worker = getattr(request.app.state, "job_worker", None)
        if worker is not None:
            worker.wake()
    return response
