"""The ``aiTask`` job and what follows a saved layout's dry run (Product 0.16 AP8).

A task works in jobs of one phase each, never holding a database transaction open while the session
runs, and checking for a cancel between steps:

- **read**: profile the workbook and read it by the rules (``reading.py``). A saved profile that
  still fits takes the engine's path with no AI (``design_job.py``); otherwise a session starts
  (``agent.py``).
- **design**: a session's next turn, or a saved layout's accepted file going to its dry run.
- the worker records that dry run and calls :func:`checked`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session

from ...models.database import AiCall, AiTask, Job
from ...models.imports import (
    ImportProfileDefinition,
)
from ...models.schema import EngineModel
from ..imports.profiles import check_profile
from ..imports.submit import Upload
from ..jobs.files import JobFiles
from ..jobs.store import complete_job, start_job
from ..model.registry import resolve_model_snapshot
from ..proposals.registry import AiConfiguration
from ..sources.profiling import profile_source_file
from ..sources.store import load_source_file, store_task_file, upload_format
from ..workspaces.catalogue import resolve_workspace
from . import agent, design_job, plan, reading, workbook
from .store import (
    claim,
    create_task,
    load_task,
    require_state,
)

KIND = "aiTask"


@dataclass
class Context:
    """What the worker gives a task's step."""

    ai: AiConfiguration | None
    files: JobFiles
    check: Callable[[], None]
    record: Callable[[AiCall], None]
    hold: Callable[..., None]
    retention_days: int
    # The operations one model-draft step may hold (MODEL_OPERATION_MAX_ITEMS).
    max_operations: int = 500


# --- starting ------------------------------------------------------------------------------------


def submit(
    session: Session,
    *,
    workspace_key: str,
    words: str | None,
    upload: Upload | None,
    send_level: str | None,
    files: JobFiles,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """Store the workbook as the new task's file and queue the job that reads it; commits. Without
    a workbook (an instruction on the workspace's records, 0.16 AP6) the task opens its draft and
    queues the design at once. Refused before anything is stored: ``422 UNSUPPORTED_FILE_FORMAT``
    and the workspace's own refusals."""
    workspace = resolve_workspace(session, workspace_key, require_active=True)
    if upload is not None:
        upload_format(upload)
    snapshot = resolve_model_snapshot(session, workspace.key)
    task = create_task(
        session,
        workspace_key=workspace.key,
        words=(words or "").strip() or None,
        retention_days=task_retention_days,
    )
    if upload is None:
        task.design = {"stage": "model", "rulesProfile": None, "rulesSources": []}
        job = start_job(
            session,
            kind=KIND,
            workspace_key=workspace.key,
            change_set_id=None,
            model_release_id=snapshot.release_db_id,
            parameters={
                "phase": "design",
                "taskId": task.public_id,
                "taskVersion": task.version,
                "sendLevel": send_level,
            },
            total=None,
            retention_days=retention_days,
            queued=True,
        )
        task.job_id = job.id
        session.commit()
        return task
    source = store_task_file(session, task.id, upload, workspace_key=workspace.key, files=files)
    try:
        job = start_job(
            session,
            kind=KIND,
            workspace_key=workspace.key,
            change_set_id=None,
            model_release_id=snapshot.release_db_id,
            parameters={
                "phase": "read",
                "taskId": task.public_id,
                "taskVersion": task.version,
                "sendLevel": send_level,
                "sourceFileId": source.public_id,
                "file": {"name": source.name, "format": source.format, "bytes": source.bytes},
            },
            total=None,
            retention_days=retention_days,
            queued=True,
        )
        task.job_id = job.id
        session.commit()
    except BaseException:
        files.upload(source.public_id).unlink(missing_ok=True)
        raise
    return task


def request_cancel(session: Session, task_id: str, expected_version: int | None) -> AiTask:
    """Ask the job the task waits for to stop (a load: its import). The turn ends, not the task:
    the task goes back to where the person can go on when it does (AP-D55)."""
    task = load_task(session, task_id, for_update=True)
    if expected_version is not None:
        claim(task, expected_version)
    require_state(task, "reading", "checking", "loading")
    session.execute(
        update(Job)
        .where(Job.id == task.job_id, Job.state.in_(("queued", "running")))
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    session.commit()
    return task


# --- the worker's steps --------------------------------------------------------------------------


def run(session: Session, job: Job, ctx: Context) -> None:
    {"read": run_read, "design": run_design}[job.parameters["phase"]](session, job, ctx)


def _stage(session: Session, job: Job, stage: str) -> None:
    """Show the phase, and end the transaction so none stays open meanwhile."""
    job.stage = stage
    session.commit()


def run_read(session: Session, job: Job, ctx: Context) -> None:
    parameters = dict(job.parameters)
    sequence_id = job.sequence_id
    task = load_task(session, parameters["taskId"])
    workspace = task.workspace_key
    source_public = parameters["sourceFileId"]
    _stage(session, job, "profiling")
    profile_source_file(session, source_public, ctx.files.upload(source_public), ctx.check)
    session.commit()
    model = resolve_model_snapshot(session, workspace).model
    _stage(session, job, "reading")
    source = load_source_file(session, source_public)
    found = workbook.read_workbook(session, source, workspace, model)
    session.commit()
    reading.finish(found)
    task = load_task(session, parameters["taskId"], for_update=True)
    fits = design_job.saved_layout_fits(session, task, source, model, found)
    task = load_task(session, parameters["taskId"], for_update=True)
    task.reading = found
    task.state = "reading"
    session.commit()
    _stage(session, job, "designing")
    if fits:
        # The same layout again: the saved profile reads it, and no AI is asked.
        computed = {t["table"]: plan.Computed() for t in found["tables"]}
        built, _ = _checked_plan(
            found["tables"],
            computed,
            [],
            source.csv_delimiter,
            model,
            found.get("profile"),
            found.get("profileMaps") or {},
        )
        task = load_task(session, parameters["taskId"], for_update=True)
        task.design = {
            "stage": "model",
            "rulesProfile": built.profile if built is not None else None,
            "rulesSources": built.sources if built is not None else [],
        }
        design_job.start(session, task)
        session.commit()
        design_job.run_turns(session, job, ctx, parameters["taskId"], record_call=ctx.record)
    else:
        agent.start(
            session,
            job,
            ctx,
            parameters["taskId"],
            ctx.files.upload(source_public),
            design_job.dry_run_check,
        )
    ctx.hold(cancellable=True)
    job = session.get(Job, sequence_id)
    complete_job(session, job, retention_days=ctx.retention_days)
    job.result = None
    session.commit()


def run_design(session: Session, job: Job, ctx: Context) -> None:
    """A session's next turn, or a saved layout's next step (``design_job``)."""
    sequence_id = job.sequence_id
    _stage(session, job, "designing")
    design_job.run_turns(session, job, ctx, job.parameters["taskId"], record_call=ctx.record)
    ctx.hold(cancellable=True)
    job = session.get(Job, sequence_id)
    complete_job(session, job, retention_days=ctx.retention_days)
    job.result = None
    session.commit()


def _checked_plan(
    tables: list[dict[str, Any]],
    computed: dict[str, plan.Computed],
    fixes: list[dict[str, Any]],
    csv_delimiter: str | None,
    model: EngineModel,
    profile: dict[str, Any] | None = None,
    profile_maps: dict[str, dict[str, Any]] | None = None,
) -> tuple[plan.Built | None, list[str]]:
    """The plan, with every table the profile check refuses left out and named (a problem refuses
    the table, not the task)."""
    skip: set[str] = set()
    refused: list[str] = []
    for table in tables:
        if plan.loads(table) and not any(c["binding"] for c in table["columns"]):
            skip.add(table["table"])
            refused.append(f"Table {table['table']} ('{table['sheet']}') has no column to load")
    for _ in range(len(tables) + 1):
        built = plan.build(
            tables,
            computed,
            fixes,
            csv_delimiter=csv_delimiter,
            skip=frozenset(skip),
            profile=profile,
            profile_maps=profile_maps,
        )
        if built is None:
            return None, refused
        try:
            definition = ImportProfileDefinition.model_validate(built.profile)
        except ValidationError as error:
            refused.append(f"The plan is not a valid profile ({error.error_count()} problems)")
            return None, refused
        problems = check_profile(model, definition)
        if not problems:
            return built, refused
        bad = {
            built.sources[int(p.path.split("/")[2])]["table"]
            for p in problems
            if p.path.startswith("/sources/")
        }
        if not bad:
            refused.append(
                "The plan does not fit the model: " + "; ".join(p.message for p in problems)
            )
            return None, refused
        for problem in problems:
            refused.append(f"{problem.message} (at {problem.path})")
        skip |= bad
    return None, refused


# --- what follows the dry run --------------------------------------------------------------------


def checked(session: Session, job: Job, *, ai: AiConfiguration | None, retention_days: int) -> None:
    """The worker recorded a saved layout's dry run. The caller commits."""
    task = load_task(session, job.parameters["taskId"], for_update=True)
    design_job.checked(session, task, job, ai=ai, retention_days=retention_days)
