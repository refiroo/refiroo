"""The ``aiTask`` job and what follows a task's dry run (Product 0.16 AP6).

A task works in jobs of one phase each, never holding a database transaction open while the provider
answers (each call is preceded by a commit, 0.16 AP1 finding J48.8), and checking for a cancel
between calls:

- **read**: profile the workbook and read it by the rules (``reading.py``). With the AI provider
  offered, the assistant designs (``design_job.py``); without it the task is ``read`` and the
  person decides.
- **plan**: apply the person's choices, build the import profile (``plan.py``), check it against the
  workspace's model, queue a ``dryRun`` of every row; the task stays ``checking``.
- the worker records the dry run and calls :func:`checked`: the task's check is its summary per
  table with what was refused, and the task is ``checked``.
- **design**: a round of the assistant's design after a dry run refused rows (``design_job.py``).

A provider failure, an answer out of shape or ``AI_MAX_STEPS`` reached is a warning in the task's
notes, never a failed task: what the rules read, and what the assistant proposed and the engine
accepted, stand (AP-D26).
"""

import copy
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import AiCall, AiTask, Job, SourceFile
from ...models.imports import (
    ImportProfileCreate,
    ImportProfileDefinition,
    ImportRequest,
    InlineProfile,
)
from ...models.schema import EngineModel
from ..change_sets.lifecycle import create_change_set
from ..imports.profiles import check_profile
from ..imports.profiles import save_profile as save_import_profile
from ..imports.submit import Upload, submit_import
from ..jobs.files import JobFiles
from ..jobs.store import complete_job, job_parameter, start_job
from ..model.registry import resolve_model_snapshot
from ..model.workspace_models import load_assignment
from ..proposals.registry import AiConfiguration
from ..sources.profiling import profile_source_file
from ..sources.store import load_source_file, store_task_file, stored_upload, upload_format
from ..workspaces.catalogue import resolve_workspace
from . import agent, design_job, plan, reading, turns, workbook
from .store import (
    claim,
    create_task,
    load_task,
    note,
    require_state,
    touch,
)

KIND = "aiTask"
MAX_NOTES = 20


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


class Notes:
    """What the person is told when the step ends."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, kind: str, message: str) -> None:
        if (kind, message) not in self.items and len(self.items) < MAX_NOTES:
            self.items.append((kind, message))

    def write(self, task: AiTask) -> None:
        for kind, message in self.items:
            note(task, kind, message)


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
        if not agent.enabled():
            design_job.start(session, task)
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


def queue_plan(
    session: Session,
    task_id: str,
    expected_version: int,
    tables: list[dict[str, Any]],
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """The person's choices for the plan: claim the task's version, check the choices against the
    reading, queue the job that applies them and checks the plan; commits."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "read", "checked")
    known = {t["table"]: t for t in (task.reading or {}).get("tables", [])}
    asked = []
    notes = []
    for choice in tables:
        table = known.get(choice["table"])
        if table is None:
            raise api_error(
                422,
                "AI_TASK_TABLE_UNKNOWN",
                f"The workbook has no table '{choice['table']}' (tables: {', '.join(known)})",
                {"table": choice["table"]},
            )
        column = choice.get("keyColumn")
        if column is not None and column not in {o["column"] for o in table["keyOptions"]}:
            raise api_error(
                422,
                "AI_TASK_COLUMN_UNKNOWN",
                f"Table '{choice['table']}' cannot be matched by column '{column}': "
                "its key options are "
                + (", ".join(o["column"] for o in table["keyOptions"]) or "none"),
                {"table": choice["table"], "column": column},
            )
        if table["as"] != "update":
            if choice.get("load"):
                notes.append(
                    f"Table {table['table']} ('{table['sheet']}') is {table['as']}: "
                    "this version loads updates of existing records only, so it is not loaded"
                )
            continue
        asked.append(choice)
    snapshot = resolve_model_snapshot(session, task.workspace_key)
    job = start_job(
        session,
        kind=KIND,
        workspace_key=task.workspace_key,
        change_set_id=None,
        model_release_id=snapshot.release_db_id,
        parameters={
            "phase": "plan",
            "taskId": task.public_id,
            "taskVersion": task.version + 1,
            "choices": asked,
            "sendLevel": None,
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    _stop_dry_runs(session, task)
    for message in notes:
        note(task, "note", message)
    task.state = "checking"
    task.job_id = job.id
    task.finished_at = None
    touch(task, task_retention_days)
    session.commit()
    return task


def queue_run(
    session: Session,
    task_id: str,
    expected_version: int,
    *,
    change_set_name: str | None,
    save_profile: dict[str, str] | None,
    files: JobFiles,
    import_max_bytes: int,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """Load the checked plan: a new change set, the saved profile when asked, and the import of the
    task's workbook through the plan into it (``stage: execute``, ``independent``, ``overwrite``)."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "checked")
    if not task.plan:
        raise api_error(
            409, "AI_TASK_NOTHING_TO_LOAD", "The plan loads no table; choose a table to load"
        )
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    assert source is not None
    release_id = load_assignment(session, task.workspace_key)[1].id
    change_set = create_change_set(
        session,
        task.workspace_key,
        release_id,
        name=change_set_name or f"Load of {source.name}",
        source="currentLive",
        expected_model_runtime_release_id=release_id,
    )
    task.state = "loading"
    task.result = {
        "changeSetId": change_set.id,
        "changeSetName": change_set.name,
        "importJobId": None,
        "profileKey": task.plan.get("profileKey"),
    }
    touch(task, task_retention_days)
    definition = task.plan["profile"]
    request = ImportRequest(
        changeSetId=change_set.id,
        expectedChangeSetVersion=change_set.version,
        profile=InlineProfile.model_validate(definition),
        policy="independent",
        onExisting="overwrite",
        stage="execute",
        sourceFileId=source.public_id,
    )
    with stored_upload(
        session, source.public_id, files=files, max_bytes=import_max_bytes
    ) as upload:
        job, _ = submit_import(
            session,
            request,
            upload,
            files=files,
            idempotency_key=None,
            retention_days=retention_days,
        )
    task = load_task(session, task_id, for_update=True)
    task.job_id = job.id
    task.result = {**(task.result or {}), "importJobId": job.id}
    session.commit()
    if save_profile is not None:
        # The same layout loaded again is the profile's next version; the load is committed, so a
        # profile that cannot be saved is said on the task, not a failure of the load.
        try:
            save_import_profile(
                session,
                ImportProfileCreate.model_validate(
                    {
                        **definition,
                        "key": save_profile["key"],
                        "name": save_profile["name"],
                        "workspaceKey": task.workspace_key,
                    }
                ),
            )
        except ApiError as error:
            session.rollback()
            task = load_task(session, task_id, for_update=True)
            note(
                task,
                "warning",
                f"The import was loaded but not saved as a profile: {error.message}",
            )
        else:
            task = load_task(session, task_id, for_update=True)
            task.result = {**(task.result or {}), "profileKey": save_profile["key"]}
        session.commit()
    return task


def request_cancel(session: Session, task_id: str, expected_version: int | None) -> AiTask:
    """Ask the job the task waits for to stop; the task becomes ``cancelled`` when it does."""
    task = load_task(session, task_id, for_update=True)
    if expected_version is not None:
        claim(task, expected_version)
    require_state(task, "reading", "checking")
    session.execute(
        update(Job)
        .where(Job.id == task.job_id, Job.state.in_(("queued", "running")))
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    session.commit()
    return task


def _stop_dry_runs(session: Session, task: AiTask) -> None:
    session.execute(
        update(Job)
        .where(
            Job.kind == "dryRun",
            Job.state.in_(("queued", "running")),
            job_parameter("taskId") == task.public_id,
        )
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )


# --- the worker's steps --------------------------------------------------------------------------


def run(session: Session, job: Job, ctx: Context) -> None:
    {"read": run_read, "plan": run_plan, "design": run_design}[job.parameters["phase"]](
        session, job, ctx
    )


def _offered(ctx: Context) -> bool:
    return ctx.ai is not None and ctx.ai.provider is not None and ctx.ai.offers("workbookLoad")


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
    notes = Notes()
    if not agent.enabled():
        notes.add(
            "warning",
            "The AI assistant is not set up (AI_AGENT_COMMAND): the file was read by the rules alone",
        )
    else:
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
        return
    reading.finish(found)
    task = load_task(session, parameters["taskId"], for_update=True)
    task.reading = found
    notes.write(task)
    task.state = "read"
    touch(task, _retention(ctx))
    ctx.hold(cancellable=True)
    job = session.get(Job, sequence_id)
    complete_job(session, job, retention_days=ctx.retention_days)
    job.result = None
    session.commit()


def run_design(session: Session, job: Job, ctx: Context) -> None:
    """A design round after a dry run refused rows (``design_job``)."""
    sequence_id = job.sequence_id
    _stage(session, job, "designing")
    design_job.run_turns(session, job, ctx, job.parameters["taskId"], record_call=ctx.record)
    ctx.hold(cancellable=True)
    job = session.get(Job, sequence_id)
    complete_job(session, job, retention_days=ctx.retention_days)
    job.result = None
    session.commit()


def _retention(ctx: Context) -> int:
    return ctx.ai.task_retention_days if ctx.ai else 90


def _columns(table: dict[str, Any]) -> tuple[int, int | None]:
    key = next(c for c in table["columns"] if c["column"] == table["keyColumn"])["number"]
    name = next(
        (
            c["number"]
            for c in table["columns"]
            if c["binding"] == {"field": "name"} and c["column"] != table["keyColumn"]
        ),
        None,
    )
    return key, name


# --- the plan ------------------------------------------------------------------------------------


def run_plan(session: Session, job: Job, ctx: Context) -> None:
    parameters = dict(job.parameters)
    sequence_id = job.sequence_id
    task = load_task(session, parameters["taskId"])
    if task.version != parameters["taskVersion"]:
        return _complete(session, sequence_id, ctx)
    workspace = task.workspace_key
    found = copy.deepcopy(task.reading)
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    assert source is not None
    file_id = source.id
    model = resolve_model_snapshot(session, workspace).model
    types = reading.type_infos(model)
    _stage(session, job, "checking")
    rekeyed: set[str] = set()
    for choice in parameters["choices"]:
        table = next(t for t in found["tables"] if t["table"] == choice["table"])
        if choice.get("keyColumn") is not None:
            option = next(o for o in table["keyOptions"] if o["column"] == choice["keyColumn"])
            if option["column"] != table["keyColumn"] or option["key"] != table["key"]:
                # The matches by meaning were for the old key; cleared before the figures and
                # the evidence are made for the new one.
                table["meaning"] = []
                reading.as_update(
                    session, file_id, workspace, types, table, table["objectTypeKey"], option
                )
                rekeyed.add(table["table"])
            table["owner"] = "person"
        for name in ("newRecords", "names", "missing"):
            if choice.get(name) is not None:
                table["choices"][name] = {"value": choice[name], "owner": "person"}
        if choice.get("load") is not None:
            table["choices"]["load"] = {"value": bool(choice["load"]), "owner": "person"}
    notes = Notes()
    session.commit()
    if rekeyed:
        # Only a task read without the AI provider is planned, so the new key is matched exactly.
        notes.add("warning", "The AI provider is not set up: the new key is matched exactly only")
    _settle(
        session,
        job,
        ctx,
        task_id=parameters["taskId"],
        found=found,
        notes=notes,
    )


def _complete(session: Session, sequence_id: int, ctx: Context) -> None:
    ctx.hold(cancellable=True)
    job = session.get(Job, sequence_id)
    complete_job(session, job, retention_days=ctx.retention_days)
    job.result = None
    session.commit()


def _computed(
    session: Session, file_id: int, workspace: str, table: dict[str, Any]
) -> plan.Computed:
    out = plan.Computed()
    if table["key"] is None:
        return out
    key_column, name_column = _columns(table)
    key = table["key"]
    args = (session, file_id, table["place"], workspace, table["objectTypeKey"], key_column, key)
    if table["choices"]["newRecords"]["value"] == "leaveOut":
        out.new_keys = reading.new_keys(*args, name_column)
    if table["choices"]["names"]["value"] == "stored" and name_column is not None:
        out.names, out.unmapped_names = reading.stored_names(*args, name_column)
    return out


def _settle(
    session: Session,
    job: Job,
    ctx: Context,
    *,
    task_id: str,
    found: dict[str, Any],
    notes: Notes,
) -> None:
    """Build the plan from the reading, check it against the model and queue the dry run; commits."""
    sequence_id = job.sequence_id
    task = load_task(session, task_id)
    workspace = task.workspace_key
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    assert source is not None
    model = resolve_model_snapshot(session, workspace).model
    kept = (task.plan or {}).get("fixes", [])
    csv_delimiter = source.csv_delimiter if source.format == "csv" else None
    computed = {
        t["table"]: _computed(session, source.id, workspace, t)
        for t in found["tables"]
        if plan.loads(t)
    }
    reading.finish(found)
    built, refused = _checked_plan(
        found["tables"],
        computed,
        kept,
        csv_delimiter,
        model,
        found.get("profile"),
        found.get("profileMaps") or {},
    )
    for message in refused:
        notes.add("refused", message)
    task = load_task(session, task_id, for_update=True)
    if task.version != job.parameters["taskVersion"] and job.parameters["phase"] == "plan":
        return _complete(session, sequence_id, ctx)
    task.reading = found
    notes.write(task)
    if built is None:
        task.plan, task.check = None, None
        task.state = "checked"
        task.job_id = None
        touch(task, _retention(ctx))
    else:
        for message in built.notes:
            note(task, "note", message)
        task.plan = {
            "profile": built.profile,
            "steps": built.steps,
            "sources": built.sources,
            "fixes": kept,
            "rounds": 0,
            "profileKey": built.profile_key,
        }
        dry = _queue_dry_run(session, task, source, built.profile, ctx.retention_days)
        task.job_id = dry.id
        task.updated_at = datetime.now(UTC)
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


def _queue_dry_run(
    session: Session, task: AiTask, source: SourceFile, profile: dict[str, Any], retention_days: int
) -> Job:
    """The dry run of every row of the plan on the workspace's live data (a ``dryRun`` job whose
    subject is the task); an earlier one still running is asked to stop."""
    _stop_dry_runs(session, task)
    snapshot = resolve_model_snapshot(session, task.workspace_key)
    return start_job(
        session,
        kind="dryRun",
        workspace_key=task.workspace_key,
        change_set_id=None,
        model_release_id=snapshot.release_db_id,
        parameters={
            "policy": "independent",
            "run": "background",
            "stage": "preview",
            "onExisting": "overwrite",
            "otherWorkspaceIds": "refuse",
            "taskId": task.public_id,
            "taskVersion": task.version,
            "sourceFileId": source.public_id,
            "profile": {"key": None, "version": None, "definition": profile},
            "file": {
                "name": source.name,
                "format": source.format,
                "bytes": source.bytes,
                "sha256": source.sha256,
            },
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )


# --- what follows the dry run --------------------------------------------------------------------

_CELL_REFUSALS = """
SELECT o.source_index, x ->> 'code', x ->> 'column', count(DISTINCT o.row_number)
FROM job_items o,
    jsonb_array_elements(CASE
        WHEN jsonb_typeof(o.outcome::jsonb -> 'error' -> 'details' -> 'cells') = 'array'
        THEN o.outcome::jsonb -> 'error' -> 'details' -> 'cells' ELSE '[]'::jsonb END) x
WHERE o.job_id = :job AND o.status = 'rejected' AND o.source_index IS NOT NULL
GROUP BY 1, 2, 3
"""

_OTHER_REFUSALS = """
SELECT o.source_index, o.outcome -> 'error' ->> 'code', min(o.outcome -> 'error' ->> 'message'),
    count(DISTINCT o.row_number)
FROM job_items o
WHERE o.job_id = :job AND o.status = 'rejected' AND o.source_index IS NOT NULL
  AND coalesce(jsonb_array_length(CASE
        WHEN jsonb_typeof(o.outcome::jsonb -> 'error' -> 'details' -> 'cells') = 'array'
        THEN o.outcome::jsonb -> 'error' -> 'details' -> 'cells' ELSE '[]'::jsonb END), 0) = 0
GROUP BY 1, 2
"""

_REFUSED_VALUES = """
SELECT c.text, count(*) FROM job_items o
JOIN source_file_cells c ON c.source_file_id = :file AND c.sheet_index = :sheet
    AND c.row_number = o.row_number AND c.column_number = :column
WHERE o.job_id = :job AND o.source_index = :source AND o.status = 'rejected'
  AND EXISTS (SELECT 1 FROM jsonb_array_elements(o.outcome::jsonb -> 'error' -> 'details' -> 'cells') x
      WHERE x ->> 'column' = :header AND x ->> 'code' = :code)
GROUP BY c.text ORDER BY 2 DESC, 1 LIMIT :limit
"""


def checked(session: Session, job: Job, *, ai: AiConfiguration | None, retention_days: int) -> None:
    """The worker recorded a task's dry run: the task's check is its summary per table with what was
    refused, and the task is ``checked``. A dry run its plan has left behind is ignored. The caller
    commits."""
    task = load_task(session, job.parameters["taskId"], for_update=True)
    if task.draft_id is not None:
        design_job.checked(session, task, job, ai=ai, retention_days=retention_days)
        return
    if task.job_id != job.id or task.version != job.parameters["taskVersion"] or not task.plan:
        return
    report = job.report["dryRun"]
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    assert source is not None
    tables = {t["table"]: t for t in task.reading["tables"]}
    figures = []
    for item in task.plan["sources"]:
        table = tables[item["table"]]
        entry = next(s for s in report["sources"] if s["profileSource"] == item["index"])
        refused = _refusals(session, job, source.id, table, entry["source"])
        figures.append(
            {
                "table": table["table"],
                "sheet": table["sheet"],
                "typeName": table["typeName"],
                "source": entry["source"],
                "rows": entry["rows"],
                "changed": entry["records"]["updated"],
                "unchanged": entry["records"]["unchanged"],
                "created": entry["records"]["created"],
                "removed": entry["records"]["deleted"],
                "skipped": entry.get("skippedRows", 0),
                "translations": entry.get("relatedRecords", 0),
                "refused": refused,
                "leftOut": [c["header"] for c in table["columns"] if c["binding"] is None],
            }
        )
        figures[-1]["nothingToDo"] = not (
            figures[-1]["changed"]
            or figures[-1]["created"]
            or figures[-1]["removed"]
            or figures[-1]["translations"]
            or refused
        )
    rounds = task.plan.get("rounds", 0)
    task.check = {
        "dryRunJobId": job.id,
        "ranAt": report["ranAt"],
        "tables": figures,
        "summary": {
            "changed": sum(f["changed"] for f in figures),
            "unchanged": sum(f["unchanged"] for f in figures),
            "created": sum(f["created"] for f in figures),
            "removed": sum(f["removed"] for f in figures),
            "refused": sum(g["rows"] for f in figures for g in f["refused"]),
            "translations": sum(f["translations"] for f in figures),
            "tablesWithChanges": sum(
                1
                for f in figures
                if f["changed"] or f["created"] or f["removed"] or f["translations"]
            ),
        },
        "fixes": task.plan.get("fixes", []),
        "rounds": rounds,
    }
    task.state = "checked"
    touch(task, ai.task_retention_days if ai else 90)


def _refusals(
    session: Session, job: Job, file_id: int, table: dict[str, Any], source: int
) -> list[dict[str, Any]]:
    """The rows the dry run refused in a source, grouped by code and column, with the cell values
    most often refused (from the staged cells, in SQL)."""
    columns = {c["header"]: c for c in table["columns"]}
    found: list[dict[str, Any]] = []
    for at, code, header, rows in session.execute(text(_CELL_REFUSALS), {"job": job.sequence_id}):
        if at != source:
            continue
        column = columns.get(header)
        entry: dict[str, Any] = {
            "code": code,
            "rows": rows,
            "column": column["column"] if column else None,
            "header": header,
        }
        if column is not None:
            entry["values"] = [
                {"value": value, "count": count}
                for value, count in session.execute(
                    text(_REFUSED_VALUES),
                    {
                        "job": job.sequence_id,
                        "file": file_id,
                        "sheet": table["place"]["sheetIndex"],
                        "column": column["number"],
                        "source": source,
                        "header": header,
                        "code": code,
                        "limit": turns.REFUSED_VALUES,
                    },
                )
            ]
        found.append(entry)
    for at, code, message, rows in session.execute(text(_OTHER_REFUSALS), {"job": job.sequence_id}):
        if at == source:
            found.append(
                {"code": code, "rows": rows, "column": None, "header": None, "message": message}
            )
    return sorted(found, key=lambda item: (-item["rows"], item["code"] or ""))


__all__ = [
    "KIND",
    "Context",
    "checked",
    "queue_plan",
    "queue_run",
    "request_cancel",
    "run",
    "submit",
]
