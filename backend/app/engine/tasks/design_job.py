"""A task's way through the engine, beside the session (Product 0.16 AP8).

A session (``agent.py``) does its own designing and loading through the API. What is here is what
surrounds it: its next turn, the person's answers and acceptance, and the saved layout's path: a
file a saved profile still fits gets the engine's own proposal, no AI, and after the person accepts
one dry run of every row and the import into a new change set.
"""

from datetime import UTC, datetime
from typing import Any

from openpyxl.utils.cell import column_index_from_string
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import (
    AiTask,
    AuditEvent,
    ChangeSet,
    Job,
    ModelDraft,
    ModelRelease,
    SourceFile,
    WorkspaceModel,
)
from ...models.imports import (
    ImportProfileCreate,
    ImportProfileDefinition,
    ImportRequest,
    InlineProfile,
)
from ..change_sets.lifecycle import create_change_set, discard_change_set
from ..identity.clients import retire_session_client
from ..imports.profiles import load_profile, parsed, source_order
from ..imports.profiles import save_profile as save_import_profile
from ..imports.submit import submit_import
from ..jobs.store import start_job
from ..model.compiler import compile_model
from ..model.releases import activate_model_release, install_model_release, next_free_version
from ..model.workspace_models import load_assignment
from ..sources.dry_run import is_items_run
from ..sources.profile_check import previous_file
from ..sources.store import stored_upload
from . import agent, design_checks, draft_plan, matching, store
from .profile_reading import headers_of
from .store import claim, finish, load_task, note, require_state, touch


def task_source(session: Session, task: AiTask) -> SourceFile:
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    assert source is not None
    return source


def workbook_of(session: Session, task: AiTask) -> SourceFile | None:
    """The task's workbook; ``None`` for an instruction given without one."""
    return session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))


def working_source(session: Session, draft_id: int) -> SourceFile | None:
    return session.scalar(
        select(SourceFile).where(
            SourceFile.draft_id == draft_id, SourceFile.superseded_at.is_(None)
        )
    )


def start(session: Session, task: AiTask) -> ModelDraft:
    """The task's draft of its workspace's model, opened once (a reading run again after an
    interruption keeps it); the caller commits."""
    if task.draft_id is not None:
        found = session.get(ModelDraft, task.draft_id)
        if found is not None:
            return found
    source = workbook_of(session, task)
    title = source.name if source is not None else (task.words or "an instruction")[:120]
    draft = draft_plan.open_draft(session, task.workspace_key, f"Assistant: {title}")
    task.draft_id = draft.id
    return draft


def quiet_tables(task: AiTask) -> frozenset[str]:
    """The tables the rules read as updates with nothing to decide: sent to the assistant in a
    line each, and loaded as the rules' profile reads them unless the design changes them."""
    return frozenset(
        t["table"]
        for t in (task.reading or {}).get("tables", [])
        if t["as"] == "update" and not t.get("attention") and t["choices"]["load"]["value"]
    )


def kept_sources(task: AiTask) -> list[dict[str, Any]]:
    """The rules' profile's sources of the quiet tables."""
    current = task.design or {}
    profile = current.get("rulesProfile") or {}
    sources = profile.get("sources") or []
    quiet = quiet_tables(task)
    return [
        sources[item["index"]]
        for item in current.get("rulesSources") or []
        if item["table"] in quiet and item["index"] < len(sources)
    ]


def _words_heard(session: Session, task_id: str) -> None:
    """The turn is recorded: the person's words and the start are spent."""
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    if design.pop("pendingWords", None) is not None or design.pop("startSession", None) is not None:
        task.design = design
    session.commit()


def run_turns(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    *,
    record_call: Any,
) -> None:
    """One design job. A session's next turn (the person's words or their acceptance); else a saved
    layout's proposal, or its accepted working copy going to the dry run. The caller completes the
    job."""
    task = load_task(session, task_id)
    current = dict(task.design or {})
    # Kept until the turn is recorded: a worker that stops mid-turn finds them again (R-F18).
    words = current.get("pendingWords")
    begin = current.get("startSession", False)
    if (
        current.get("agentSession")
        and not begin
        and not current.get("origin")
        and current.get("stage") != "load"
        and not agent.resumable(ctx.files, task)
    ):
        # The session was stopped before it wrote a transcript: there is no conversation to resume,
        # so the turn starts it again, with the words the person gave (not the default "go on").
        begin = True
        if words == "That stopped. Go on from where you were.":
            words = None
    if current.get("agentSession") and not begin:
        if current.get("stage") == "load":
            # A load turn the earlier worker left running is undone before it loads again.
            agent.undo_interrupted_load(session, task_id)
            agent.accepted(session, job, ctx, task_id, words)
        else:
            agent.said(session, job, ctx, task_id, words or "", dry_run_check)
        _words_heard(session, task_id)
        return
    source = workbook_of(session, task)
    if agent.enabled() and (begin or source is None):
        # The session starts here: words alone have no file to read first, and a task that had no
        # session (a saved layout that does not fit, a reading that failed) takes the person's words.
        path = ctx.files.upload(source.public_id) if source is not None else None
        agent.start(session, job, ctx, task_id, path, dry_run_check, words)
        _words_heard(session, task_id)
        return
    _words_heard(session, task_id)
    if current.get("stage", "load") == "model":
        _propose(session, job, ctx, task_id, record_call)
        return
    task = load_task(session, task_id, for_update=True)
    if _complete(task.design or {}):
        queue_check(session, task, ctx.files, ctx.retention_days)
    else:
        note(task, "warning", "The saved layout does not fit the workbook")
        task.state = "checked"
    session.commit()


def _latest_check(session: Session, draft: ModelDraft) -> Job | None:
    job = session.scalar(
        select(Job)
        .where(Job.kind == "dryRun", Job.parameters["draftId"].as_string() == draft.public_id)
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )
    return job if job is not None and job.state == "completed" else None


def check_is_stale(session: Session, draft: ModelDraft) -> bool:
    """Whether the draft's latest check ran on another version of the draft than the one it has
    now (R-F17)."""
    job = _latest_check(session, draft)
    return job is not None and job.parameters.get("draftVersion") != draft.version


def dry_run_check(session: Session, draft: ModelDraft) -> dict[str, Any] | None:
    """The check a draft's latest dry run gives, whoever asked for it."""
    job = _latest_check(session, draft)
    if job is None:
        return None
    # A check from before the draft's last change does not cover the model as it stands.
    return {
        **check_of_job(session, job, draft, 0),
        "draftChanged": job.parameters.get("draftVersion") != draft.version,
    }


def _followed(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The tables the saved profile reads: what it found, by its own key."""
    return [t for t in tables if t.get("profile") is not None]


def _engine_outline(tables: list[dict[str, Any]], types: Any) -> list[dict[str, str]]:
    return [
        {
            "objectTypeKey": t["objectTypeKey"],
            "text": f"from “{t['sheet']}”: {t['matched']} rows are stored records, {t['new']} are new",
        }
        for t in _followed(tables)
        if t.get("objectTypeKey") in types
    ]


def _engine_summary(tables: list[dict[str, Any]], name: str) -> str:
    parts = [
        f"“{t['sheet']}”: {t['matched']} of {int(t['matched']) + int(t['new'])} rows match stored "
        f"records, {t['new']} are new."
        for t in _followed(tables)
    ]
    left_out = [t["sheet"] for t in tables if t.get("profile") is None]
    if left_out:
        parts.append("Not read, as before: " + ", ".join(f"“{sheet}”" for sheet in left_out) + ".")
    return f"The saved profile “{name}” reads this file. " + " ".join(parts)


def _set_outcome(
    session: Session,
    task: AiTask,
    current: dict[str, Any],
    draft: ModelDraft,
    released: dict[str, Any] | None,
    applied: dict[str, Any],
    source: SourceFile | None,
) -> dict[str, Any]:
    kept = kept_sources(task)
    current["profile"] = (current.get("match") or {}).get("profile") or (
        {"sources": [], "valueMaps": {}} if kept else None
    )
    checked = draft_plan.check(draft, full_profile(current, draft.model_json, kept))
    if current.get("stage") == "model" and current.get("profile") is None:
        checked.pop("profileProblems", None)
    unresolved = draft_plan.unresolved_links(
        session, source, task.workspace_key, current.get("profile"), []
    )
    if unresolved:
        checked["unresolved"] = unresolved
    left_out = columns_left_out(task, current)
    current["leftOut"] = left_out
    current["checks"] = design_checks.run(
        session,
        task_reading=task.reading,
        file_id=source.id if source is not None else None,
        workspace=task.workspace_key,
        profile=full_profile(current, draft.model_json, kept),
        model=draft.model_json,
        base=released,
        explains=current.get("explains") or {},
    )
    open_checks = [c for c in current["checks"] if c["open"]]
    if open_checks:
        checked["checks"] = open_checks
    last_run = (current.get("outcome") or {}).get("dryRun")
    outcome = {
        "modelOperations": applied,
        **checked,
        **({"dryRun": last_run} if last_run else {}),
    }
    current["outcome"] = outcome
    return outcome


def _propose(session: Session, job: Job, ctx: Any, task_id: str, record_call: Any) -> None:
    """A saved layout read again: the engine's own proposal, with no AI; the differences from the
    stored records are the person's questions."""
    task = load_task(session, task_id)
    current = dict(task.design or {})
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    opened = session.get(ModelRelease, draft.base_model_release_id)
    released = opened.model_json if opened is not None else None
    source = workbook_of(session, task)
    compiled = compile_model(draft.model_json).model
    assert compiled is not None
    types = {t.key for t in compiled.objectTypes}
    answers = current.get("answers") or {}
    found = matching.run(
        session,
        tables=(task.reading or {}).get("tables", []),
        file_id=source.id,
        workspace=task.workspace_key,
        model=compiled,
        answers=answers,
    )
    saved = load_profile(session, task.reading["profile"]["key"])
    found = {
        **found,
        "profile": {
            k: v
            for k, v in parsed(saved).model_dump(mode="json", exclude_none=True).items()
            if k in ("sources", "valueMaps", "csv")
        },
        "unplaced": [],
        "unmatched": [],
    }
    current["match"] = found
    current["engineQuestions"] = found["questions"]
    tables = (task.reading or {}).get("tables", [])
    current["summary"] = _engine_summary(tables, task.reading["profile"]["name"])
    current["outline"] = _engine_outline(tables, types)
    current["questions"] = found["questions"]
    _set_outcome(session, task, current, draft, released, {"applied": 0, "draftErrors": []}, source)
    task = load_task(session, task_id, for_update=True)
    task.design = dict(current)
    task.state = "checked"
    session.commit()


def saved_layout_fits(
    session: Session, task: AiTask, source: SourceFile, model: Any, reading_found: dict[str, Any]
) -> bool:
    """Whether a saved profile reads this file as well as the engine's match does, with no new
    column: then no AI is needed."""
    if not reading_found.get("profile"):
        return False
    task.reading = reading_found
    found = matching.run(
        session,
        tables=reading_found.get("tables", []),
        file_id=source.id,
        workspace=task.workspace_key,
        model=model,
        answers={},
    )
    # What the file the profile read before also had and the profile did not read was left out on
    # purpose: a helper sheet no more decides the fit than a column does.
    key = reading_found["profile"]["key"]
    earlier = headers_of(session, previous_file(session, key, source))
    fits = _same_layout(task, found, {}, set(earlier)) and not _new_columns(
        task, found, set(earlier)
    )
    session.rollback()
    return fits


def _new_columns(
    task: AiTask, found: dict[str, Any], sheets_before: set[str] = frozenset()
) -> list[dict[str, Any]]:
    """Of the columns the match could not place, those the file the saved profile read before did
    not have: what that profile left out it left out on purpose."""
    earlier = {
        (t["sheet"], c.get("header"))
        for t in (task.reading or {}).get("tables", [])
        for c in t.get("columns") or []
        if c.get("known") or c.get("binding") is not None
    }
    followed = {
        t["sheet"] for t in (task.reading or {}).get("tables", []) if t.get("profile") is not None
    }
    left_out = sheets_before - followed
    return [
        u
        for u in found["unplaced"]
        if (u["sheet"], u["column"]) not in earlier and u["sheet"] not in left_out
    ]


def _same_layout(
    task: AiTask,
    found: dict[str, Any],
    answers: dict[str, str],
    sheets_before: set[str] = frozenset(),
) -> bool:
    """Whether the saved profile the reading followed finds as many stored records as the match,
    on every table: one that would make new what the match finds stored is no such profile. An
    answer against what the match assumed needs the match's own profile."""
    if any(
        answers.get(q["text"], q.get("assumed")) != q.get("assumed") for q in found["questions"]
    ):
        return False
    new_by_sheet = {f["sheet"]: f.get("new", 0) for f in found["facts"]}
    tables = (task.reading or {}).get("tables", [])
    followed = [t for t in tables if t.get("profile") is not None]
    return bool(followed) and all(
        (t.get("profile") is not None and int(t.get("new") or 0) <= new_by_sheet.get(t["sheet"], 0))
        or (t.get("profile") is None and t["sheet"] in sheets_before)
        for t in tables
    )


def columns_left_out(task: AiTask, current: dict[str, Any]) -> list[dict[str, Any]]:
    """The columns of the sheets the design reads that no source of their sheet loads, each with
    the assistant's reason when it gave one (``None`` otherwise)."""
    own = list((current.get("profile") or {}).get("sources") or [])
    # As the load reads them: a quiet table's kept source only where the design has none.
    kept = [k for k in kept_sources(task) if not any(_same_place(k, s) for s in own)]
    sources = [*own, *kept]
    bound: dict[str, set[str]] = {}
    lettered: dict[str, set[int]] = {}
    for source in sources:
        names = bound.setdefault(source.get("sheet") or "", set())
        names |= {
            c["column"]
            for c in source.get("columns") or []
            if c.get("column") and not c.get("ignore")
        }
        # A column named by its letter (0.13 AQ) is loaded whatever its header says.
        lettered.setdefault(source.get("sheet") or "", set()).update(
            column_index_from_string(c["letter"])
            for c in source.get("columns") or []
            if c.get("letter") and not c.get("ignore")
        )
    reasons = current.get("reasons") or {}
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for table in (task.reading or {}).get("tables", []):
        sheet = table.get("sheet") or ""
        if sheet not in bound:
            continue
        for column in table.get("columns") or []:
            header = column.get("header")
            if not header or header in bound[sheet] or (sheet, header) in seen:
                continue
            if column.get("number") in lettered.get(sheet, ()):
                continue
            seen.add((sheet, header))
            found.append(
                {"sheet": sheet, "column": header, "reason": reasons.get(f"{sheet}\x1f{header}")}
            )
    return found


def _model_complete(current: dict[str, Any]) -> bool:
    """A proposal stands when the draft compiles and took the assistant's operations."""
    outcome = current.get("outcome") or {}
    return "refused" not in (outcome.get("modelOperations") or {}) and not outcome.get(
        "draftErrors"
    )


def _complete(current: dict[str, Any]) -> bool:
    outcome = current.get("outcome") or {}
    return (
        current.get("profile") is not None
        and "refused" not in (outcome.get("modelOperations") or {})
        and not outcome.get("draftErrors")
        and not outcome.get("profileProblems")
    )


def _same_place(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("sheet") == b.get("sheet")
        and a.get("headerRow", 1) == b.get("headerRow", 1)
        and (a.get("block") or {}).get("firstColumn") == (b.get("block") or {}).get("firstColumn")
    )


def full_profile(
    current: dict[str, Any], model: dict[str, Any], kept: list[dict[str, Any]] | None = None
) -> dict[str, Any] | None:
    """The quiet tables' sources the design does not replace (``kept``), then the design's; the
    rules' value maps under the design's."""
    profile = current.get("profile")
    if profile is None:
        return None
    own = list(profile.get("sources") or [])
    kept = [k for k in kept or [] if not any(_same_place(k, s) for s in own)]
    maps = {
        **((current.get("rulesProfile") or {}).get("valueMaps") or {}),
        **(profile.get("valueMaps") or {}),
    }
    return {**profile, "sources": kept + own, "valueMaps": maps}


def queue_check(session: Session, task: AiTask, files: Any, retention_days: int) -> Job | None:
    """Stage the file as the draft's and queue its dry run against the draft."""
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    current = task.design or {}
    original = task_source(session, task)
    content = files.upload(original.public_id).read_bytes()
    work = draft_plan.stage(
        session, draft, content, original.name, task.workspace_key, files, lambda: None
    )
    profile = full_profile(current, draft.model_json, kept_sources(task))
    # A source the file cannot be read by stops no other: the rest are checked, it is reported.
    fitting, not_fit = draft_plan.fit_to_file(session, work, profile)
    definition = ImportProfileDefinition.model_validate(fitting)
    job = start_job(
        session,
        kind="dryRun",
        workspace_key=task.workspace_key,
        change_set_id=None,
        model_release_id=load_assignment(session, task.workspace_key)[1].id,
        parameters={
            "policy": "independent",
            "run": "background",
            "stage": "preview",
            "onExisting": "overwrite",
            "otherWorkspaceIds": "refuse",
            "taskId": task.public_id,
            "taskVersion": task.version,
            "draftId": draft.public_id,
            "draftVersion": draft.version,
            "sourceFileId": work.public_id,
            "notFit": draft_plan.not_fit_refusals(not_fit),
            "profile": {
                "key": None,
                "version": None,
                "definition": definition.model_dump(mode="json", exclude_none=True),
            },
            "file": {
                "name": work.name,
                "format": work.format,
                "bytes": work.bytes,
                "sha256": work.sha256,
            },
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    task.job_id = job.id
    task.state = "checking"
    return job


_OUTCOMES = text(
    """
SELECT o.source_index, o.status, o.outcome ->> 'action' AS action, count(*) AS items,
    count(DISTINCT o.row_number) AS rows
FROM job_items o JOIN jobs j ON j.sequence_id = o.job_id
WHERE j.id = :job AND o.source_index IS NOT NULL
  -- A relationship found as it should be is no record unchanged, and on a new one it was just made.
  AND NOT (o.outcome ->> 'action' = 'unchanged' AND o.outcome ->> 'relationId' IS NOT NULL)
GROUP BY 1, 2, 3
"""
)


_ROWS = text(
    """
SELECT o.source_index, count(DISTINCT o.row_number) FROM job_items o
JOIN jobs j ON j.sequence_id = o.job_id
WHERE j.id = :job AND o.source_index IS NOT NULL GROUP BY 1
"""
)


def check_of_job(
    session: Session, job: Job, draft: ModelDraft | None, rounds: int
) -> dict[str, Any]:
    """A dry run's check per sheet from its outcomes."""
    if is_items_run(job.parameters):
        return items_check(job)
    definition = (job.parameters.get("profile") or {}).get("definition")
    if definition is None:
        key = (job.parameters.get("profile") or {}).get("key")
        definition = load_profile(session, key).definition if key else {"sources": []}
    sources = definition["sources"]
    # A job's rows name a source by the place it loads in, not its place in the profile.
    compiled = compile_model(draft.model_json).model if draft is not None else None
    if compiled is not None:
        order = source_order(compiled, ImportProfileDefinition.model_validate(definition))
        if order:
            sources = [sources[index] for index in order]
    figures: dict[int, dict[str, Any]] = {}

    def figure(index: int) -> dict[str, Any]:
        source = sources[index]
        return figures.setdefault(
            index,
            {
                "source": index,
                "sheet": source.get("sheet"),
                "objectTypeKey": source.get("objectTypeKey"),
                "rows": 0,
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "refused": 0,
                "skipped": 0,
            },
        )

    for row in session.execute(_OUTCOMES, {"job": job.id}):
        if row.source_index is None or row.source_index >= len(sources):
            continue
        entry = figure(row.source_index)
        if row.status == "rejected":
            entry["refused"] += row.rows
        elif row.action in ("created", "updated", "unchanged"):
            entry[row.action] += row.items
    for at, rows in session.execute(_ROWS, {"job": job.id}):
        if at in figures:
            figures[at]["rows"] = rows
    refused = [
        *draft_plan.refusals(session, job.id, sources),
        *(job.parameters.get("notFit") or []),
    ]
    for index, found in draft_plan.skipped(session, job, sources).items():
        entry = figure(index)
        entry["skipped"] = found["rows"]
        entry["rows"] += found["rows"]
        if found["rows"] * 2 > entry["rows"]:
            # Most of a source's rows wrote nothing: a key the rows do not fill, not a few notes.
            refused.append(
                {
                    "sheet": sources[index].get("sheet"),
                    "objectTypeKey": sources[index].get("objectTypeKey"),
                    "code": "ROWS_SKIPPED",
                    "rows": found["rows"],
                    "examples": [
                        {
                            "row": number,
                            "message": "The row wrote nothing: its key is empty and the source "
                            "skips rows without a key",
                            "details": {"key": sources[index].get("key")},
                        }
                        for number in found["examples"]
                    ],
                }
            )
    return {
        "dryRunJobId": job.id,
        "ranAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sheets": [figures[k] for k in sorted(figures)],
        "refused": refused,
        "summary": {
            "created": sum(f["created"] for f in figures.values()),
            "updated": sum(f["updated"] for f in figures.values()),
            "unchanged": sum(f["unchanged"] for f in figures.values()),
            # A row skipped for an empty key was not refused: it wrote nothing, as the source says.
            "refused": sum(r["rows"] for r in refused if r.get("code") != "ROWS_SKIPPED"),
            "skipped": sum(f["skipped"] for f in figures.values()),
        },
        "rounds": rounds,
    }


def items_check(job: Job) -> dict[str, Any]:
    """The check a dry run of items gives (0.13 AB): the figures of its summary in the check's
    shape, the refused items by code with three examples each, and the summary itself under
    ``itemsSummary`` for the task's design. No sheets: the items name their cells."""
    summary = (job.report or {}).get("itemsDryRun") or {}
    figures = summary.get("figures") or {}
    refused = summary.get("refused") or []
    return {
        "dryRunJobId": job.id,
        "ranAt": summary.get("ranAt") or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "mode": "items",
        "sheets": [],
        "refused": [
            {
                "sheet": None,
                "objectTypeKey": None,
                "code": found["code"],
                "rows": found["items"],
                "examples": [
                    {
                        "row": item["index"] + 1,
                        "message": f"{item['ref'] + ': ' if item.get('ref') else ''}"
                        f"{item.get('message') or found['code']}",
                    }
                    for item in [
                        r for r in refused if (r.get("code") or "REFUSED") == found["code"]
                    ][:3]
                ],
            }
            for found in summary.get("refusedByCode") or []
        ],
        "summary": {
            "created": figures.get("recordsNew", 0),
            "updated": figures.get("recordsChanged", 0),
            "unchanged": figures.get("recordsMatched", 0) - figures.get("recordsChanged", 0),
            "refused": figures.get("refused", 0),
            "relationships": figures.get("relationshipsNew", 0),
            "skipped": 0,
        },
        "rounds": 0,
        "itemsSummary": summary,
    }


def checked(session: Session, task: AiTask, job: Job, *, ai: Any, retention_days: int) -> None:
    """The worker recorded a saved layout's dry run: the check per sheet from the outcomes, and the
    task is ``checked``. The caller commits."""
    if task.job_id != job.id:
        return
    draft = session.get(ModelDraft, task.draft_id)
    task.check = check_of_job(session, job, draft, 0)
    task.state = "checked"
    touch(task, ai.task_retention_days if ai else 90)


def dry_run_failed(
    session: Session, job: Job, error: dict[str, Any] | None, *, ai: Any, retention_days: int
) -> None:
    """A saved layout's dry run that stopped as a whole: the reason in a note. The caller commits."""
    task = session.scalar(select(AiTask).where(AiTask.public_id == job.parameters.get("taskId")))
    if task is None or task.job_id != job.id:
        return
    note(task, "warning", f"The check could not run: {(error or {}).get('message')}")
    task.state = "checked"
    touch(task, ai.task_retention_days if ai else 90)


# --- the load ----------------------------------------------------------------------------------


def changes_model(session: Session, draft: ModelDraft) -> bool:
    base = session.get(ModelRelease, draft.base_model_release_id)
    return base is None or base.model_json != draft.model_json


def _next_version(session: Session, key: str, version: str) -> str:
    """The version the assistant's release takes: ``next_free_version``."""
    return next_free_version(session, key, version)


def install_and_activate(session: Session, task: AiTask, draft: ModelDraft, max_items: int) -> str:
    """The draft as a new release of its model, activated in the task's workspace; the release's
    public ID. Refused as the editor's installation and activation are."""
    release = draft.model_json.get("release") or {}
    key, version = release.get("key", ""), str(release.get("version", "0.0.0"))
    applied = draft_plan.apply(
        session,
        draft,
        [{"kind": "setRelease", "version": _next_version(session, key, version)}],
        max_items,
    )
    if "refused" in applied:
        raise api_error(409, "AI_TASK_STATE", "The draft's release could not be named")
    draft = session.get(ModelDraft, draft.id)
    assert draft is not None
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        raise api_error(
            422, "INVALID_MODEL", "The assistant's model draft is invalid and cannot be installed"
        )
    installed, _ = install_model_release(session, compiled.model)
    # The page keeps showing what the draft changed, against the model it was drafted on.
    task.design = {
        **(task.design or {}),
        "modelBaseReleaseId": (task.design or {}).get("modelBaseReleaseId")
        or draft.base_model_release_id,
    }
    draft.base_model_release_id = installed.id
    assignment, current = load_assignment(session, task.workspace_key, for_update=True)
    activate_model_release(
        session,
        task.workspace_key,
        installed.public_id,
        expected_version=assignment.version,
        expected_release_id=current.public_id,
    )
    return installed.public_id


def person_profile(task: AiTask) -> dict[str, Any] | None:
    """The profile of the person's sheets alone (the quiet tables' sources the design kept, then
    its own; no structure sheet): what the next file of the layout loads by."""
    current = task.design or {}
    profile = current.get("profile")
    if profile is None:
        return None
    own = list(profile.get("sources") or [])
    kept = [k for k in kept_sources(task) if not any(_same_place(k, s) for s in own)]
    maps = {
        **((current.get("rulesProfile") or {}).get("valueMaps") or {}),
        **(profile.get("valueMaps") or {}),
    }
    return {**profile, "sources": kept + own, "valueMaps": maps}


def queue_load(
    session: Session,
    task_id: str,
    expected_version: int,
    *,
    change_set_name: str | None,
    save_profile: dict[str, str] | None,
    files: Any,
    import_max_bytes: int,
    max_operations: int,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """Load a checked design: the draft installed and activated in the workspace when it changed
    the model, a new change set, the import of the working copy into it, and the profile of the
    person's sheets saved when asked. Commits."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "checked")
    draft = session.get(ModelDraft, task.draft_id)
    design_now = task.design or {}
    if draft is None or not design_now.get("profile"):
        raise api_error(409, "AI_TASK_NOTHING_TO_LOAD", "The design loads nothing yet")
    if check_is_stale(session, draft):
        raise api_error(
            409,
            "AI_TASK_CHECK_STALE",
            "The draft changed after the check; check it again",
        )
    release_id = None
    if changes_model(session, draft):
        release_id = install_and_activate(session, task, draft, max_operations)
        # The change set reads the workspace's model in a snapshot of its own: the activation is
        # committed first (a load that fails after it leaves the model activated, as the editor's
        # install-and-activate does).
        session.commit()
        task = load_task(session, task_id, for_update=True)
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    profile = full_profile(task.design or {}, draft.model_json, kept_sources(task))
    workbook = workbook_of(session, task)
    assignment_release = load_assignment(session, task.workspace_key)[1]
    change_set = create_change_set(
        session,
        task.workspace_key,
        assignment_release.id,
        name=change_set_name
        or (f"Load of {workbook.name}" if workbook is not None else "Assistant's changes"),
        source="currentLive",
        expected_model_runtime_release_id=assignment_release.id,
    )
    work = working_source(session, draft.id)
    if work is None:
        raise api_error(409, "AI_TASK_STATE", "The design has not been checked yet")
    # As it was checked: a source the file cannot be read by is reported, not loaded.
    profile, not_fit = draft_plan.fit_to_file(session, work, profile)
    left_out = [item["source"] for item in not_fit]
    task.state = "loading"
    task.result = {
        "changeSetId": change_set.id,
        "changeSetName": change_set.name,
        "importJobId": None,
        "profileKey": None,
        **({"releaseId": release_id} if release_id else {}),
    }
    touch(task, task_retention_days)
    request = ImportRequest(
        changeSetId=change_set.id,
        expectedChangeSetVersion=change_set.version,
        profile=InlineProfile.model_validate(profile),
        policy="independent",
        onExisting="overwrite",
        stage="execute",
        sourceFileId=work.public_id,
    )
    with stored_upload(session, work.public_id, files=files, max_bytes=import_max_bytes) as upload:
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
    task.result = {
        **(task.result or {}),
        "importJobId": job.id,
    }
    session.commit()
    own = person_profile(task)
    if own is not None:
        own = {**own, "sources": [s for s in own["sources"] if s not in left_out]}
    if save_profile is not None and own is not None:
        # The load is committed: a profile that cannot be saved is said on the task, not a failure
        # of the load. The same layout loaded again is the profile's next version.
        try:
            save_import_profile(
                session,
                ImportProfileCreate.model_validate(
                    {
                        **own,
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
            # The import read this layout: the next file is compared with this one's headers.
            imported = session.scalar(select(Job).where(Job.id == job.id))
            if imported is not None:
                imported.parameters = {
                    **imported.parameters,
                    "profile": {**imported.parameters["profile"], "key": save_profile["key"]},
                }
        session.commit()
    return task


def queue_answers(
    session: Session,
    task_id: str,
    expected_version: int,
    answers: dict[str, str],
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """The person's answers to the design's questions: a design round that takes them. Answers that
    are all the assumed options the draft already holds are recorded and queue nothing (0.13 AQ,
    AQ-D4). Commits."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "checked")
    assumed = {q.get("text"): q.get("assumed") for q in (task.design or {}).get("questions") or []}
    if answers and all(
        assumed.get(text) is not None and assumed[text] == answer
        for text, answer in answers.items()
    ):
        task.design = {
            **(task.design or {}),
            "answers": {**((task.design or {}).get("answers") or {}), **answers},
        }
        touch(task, task_retention_days)
        session.commit()
        return task
    session.rollback()

    def change(current: dict[str, Any]) -> None:
        current["answers"] = {**(current.get("answers") or {}), **answers}
        current["pendingWords"] = "\n".join(f"{q} {a}" for q, a in answers.items())

    return _design_again(
        session, task_id, expected_version, change, retention_days, task_retention_days
    )


def queue_correction(
    session: Session,
    task_id: str,
    expected_version: int,
    correction: str,
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """The person's words wherever a task can go on (AP-D54): the proposal, a stopped or failed task,
    a load that is wrong and not yet published (its change set is discarded and the same session
    loads again), a saved layout's load stage. The words win over the assistant's own choices.
    Commits."""
    return _go_on(
        session,
        task_id,
        expected_version,
        correction,
        ("checked", "failed", "stopped", "loaded"),
        retention_days,
        task_retention_days,
        retry=False,
    )


def queue_accept(
    session: Session,
    task_id: str,
    expected_version: int,
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """The steward accepts the proposed model: the load stage maps the sheets onto it and the dry
    run checks every row. ``409 AI_TASK_STATE`` unless the task holds a proposal. Commits."""
    task = load_task(session, task_id)
    current = task.design or {}
    if current.get("stage") != "model" or not _model_complete(current):
        raise api_error(
            409,
            "AI_TASK_STATE",
            f"AI task '{task_id}' has no valid model proposal to accept; correct it in words",
            {"state": task.state},
        )

    def change(current: dict[str, Any]) -> None:
        current["stage"] = "load"
        current["acceptedModel"] = True

    return _design_again(
        session, task_id, expected_version, change, retention_days, task_retention_days
    )


def queue_retry(
    session: Session,
    task_id: str,
    expected_version: int,
    words: str | None,
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """A task that stopped goes on from where it was: its load after an acceptance, its proposal
    otherwise, with the person's words when there are some (AP-D54). A saved layout that does not fit
    is read with the assistant (AP-D60). Commits."""
    return _go_on(
        session,
        task_id,
        expected_version,
        words,
        ("failed", "stopped", "checked"),
        retention_days,
        task_retention_days,
        retry=True,
    )


def _go_on(
    session: Session,
    task_id: str,
    expected_version: int,
    words: str | None,
    allowed: tuple[str, ...],
    retention_days: int,
    task_retention_days: int,
    *,
    retry: bool,
) -> AiTask:
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, *allowed)
    design = dict(task.design or {})
    state = task.state
    lives = agent.lives(task)
    if state in ("failed", "stopped"):
        # Its reasons were the page's while it stood there; going on, they are no longer true.
        task.notes = []
    if state == "failed" and (task.result or {}).get("changeSetId"):
        # What a failed load left behind goes first, so a second try never leaves two change sets.
        _discard_kept(session, task)
        task = load_task(session, task_id, for_update=True)
        task.result = None
    if retry and state == "checked" and design.get("agentSession"):
        # Going on without words is for a task that stopped, or one the assistant has not read yet.
        raise api_error(409, "AI_TASK_STATE", "Only a task that stopped can be tried again")
    if state == "loaded":
        if not lives:
            raise api_error(
                409,
                "AI_TASK_STATE",
                "The assistant's session has ended, so it cannot load again: start a new task",
            )
        _discard_loaded(session, task)
        task = load_task(session, task_id, for_update=True)
        task.result = None
    ran = bool(design.get("agentSession")) and bool(design.get("agentRan") or design.get("origin"))
    if not ran and not agent.enabled():
        raise api_error(
            409,
            "AI_NOT_CONFIGURED",
            "The assistant is not set up here, so it cannot take your words",
        )
    # A load the engine ran from the check (0.13 AB) has no session turn to repeat: new words go to
    # the session as a correction of the proposal, which checks the records again.
    at_load = (
        ran
        and design.get("stage") == "load"
        and state in ("failed", "loaded")
        and not design.get("itemsLoad")
    )
    design["stage"] = "load" if at_load else "model"
    if not ran:
        design["startSession"] = True
    if words:
        design["corrections"] = [*(design.get("corrections") or []), words]
        design["pendingWords"] = words
    elif ran and not at_load:
        design["pendingWords"] = "That stopped. Go on from where you were."
    design["reasonsAsked"] = False
    design["checksAsked"] = False
    task.design = design
    task.state = "checked"
    task.finished_at = None
    session.flush()
    return _design_again(
        session,
        task_id,
        expected_version,
        lambda current: None,
        retention_days,
        task_retention_days,
    )


def _discard_loaded(session: Session, task: AiTask) -> None:
    """The change set a loaded task holds, discarded (commits); a published one cannot be."""
    change_set_id = (task.result or {}).get("changeSetId")
    if not change_set_id:
        return
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(
            409,
            "AI_TASK_STATE",
            "The change set is no longer open: it was published or discarded. Start a new task",
        )
    discard_change_set(session, change_set.id, change_set.version)


def _discard_kept(session: Session, task: AiTask) -> None:
    """The change set a failed load left on the task, discarded when it is still open (commits)."""
    change_set_id = (task.result or {}).get("changeSetId")
    if change_set_id and session.scalar(select(ChangeSet.id).where(ChangeSet.id == change_set_id)):
        _discard_loaded(session, task)


def queue_back(
    session: Session, task_id: str, expected_version: int, retention_days: int
) -> AiTask:
    """From a saved layout's load stage back to the proposal it came from (AP-D54); no job. Commits."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "checked")
    design = dict(task.design or {})
    if design.get("stage") != "load" or design.get("agentSession"):
        raise api_error(409, "AI_TASK_STATE", "The task has no load stage to go back from")
    design["stage"] = "model"
    task.design = design
    touch(task, retention_days)
    session.commit()
    return task


def discard(session: Session, task_id: str, files: Any, retention_days: int) -> AiTask:
    """The person discards the task: it ends and its draft and folder go; the change set a loaded task
    holds goes with it (AP-D55). Commits."""
    task = load_task(session, task_id, for_update=True)
    require_state(task, "checked", "read", "stopped", "failed", "loaded")
    discarded_set = False
    if task.state in ("loaded", "failed"):
        change_set_id = (task.result or {}).get("changeSetId")
        if change_set_id and session.scalar(
            select(ChangeSet.id).where(ChangeSet.id == change_set_id)
        ):
            _discard_loaded(session, task)
            discarded_set = True
            task = load_task(session, task_id, for_update=True)
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id else None
    task.draft_id = None
    session.flush()
    if draft is not None:
        session.delete(draft)
    agent.remove_folder(files, task)
    agent.retire_unused_releases(session, task)
    retire_session_client(session, task.client_id)
    if agent.lives(task):
        task.design = {**(task.design or {}), "sessionEnded": True}
    if discarded_set:
        note(task, "note", "You discarded the change set. Live data was never changed.")
    finish(task, "cancelled", retention_days)
    session.commit()
    return task


def sync(session: Session, task: AiTask, retention_days: int, files: Any) -> None:
    """Bring a task up to date wherever it is read: the job it waits for (``store.sync``), what a
    stopped load had written, and a loaded task's change set published or discarded and its migration
    confirmed, which end the session (AP-D56)."""
    if task.state == "loading" and task.job_id is not None:
        job = session.scalar(select(Job).where(Job.id == task.job_id))
        if job is not None and job.state == "cancelled":
            _discard_written(session, task)
    store.sync(session, task, retention_days)
    agent.recover_load(session, task, retention_days)
    if task.state == "loaded":
        _settle(session, task, retention_days, files)
        session.flush()


def _discard_written(session: Session, task: AiTask) -> None:
    """What a stopped load wrote into the change set it made is not kept (AP-D55). Commits."""
    result = task.result or {}
    change_set_id = result.get("changeSetId")
    change_set = (
        session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        if change_set_id
        else None
    )
    if change_set is not None:
        discard_change_set(session, change_set.id, change_set.version)
    if result.get("releaseId"):
        note(task, "note", "The model change it installed stays activated in the workspace.")


def _settle(session: Session, task: AiTask, retention_days: int, files: Any) -> None:
    """A loaded task whose work is now in the person's hands for good: the change set was published
    (the task says so and points onward) or discarded elsewhere (the task ends), or the migration it
    prepared was confirmed. The session and its folder go with it (AP-D56)."""
    if agent.lives(task) and not agent.folder_of(files, task).exists():
        # A task recorded before the session outlived its load: its folder went at the load, so there
        # is no session to tell anything (AP13). The task stands; its words box is not offered.
        agent.end_session(session, files, task, retire_releases=False)
    result = dict(task.result or {})
    change_set_id = result.get("changeSetId")
    if change_set_id and not result.get("published"):
        if session.scalar(select(ChangeSet.id).where(ChangeSet.id == change_set_id)) is not None:
            return
        publication = session.scalar(
            select(AuditEvent.aggregate_id).where(
                AuditEvent.aggregate_type == "publication",
                AuditEvent.action == "published",
                AuditEvent.changes["changeSetId"].as_string() == change_set_id,
            )
        )
        if publication is not None:
            task.result = {**result, "published": True, "publicationId": publication}
            touch(task, retention_days)
            agent.end_session(session, files, task, retire_releases=False)
        else:
            agent.end_session(session, files, task)
            note(task, "note", "The change set was discarded. Live data was never changed.")
            finish(task, "cancelled", retention_days)
        return
    migration = result.get("migration")
    if migration and agent.lives(task):
        running = session.scalar(
            select(ModelRelease.public_id)
            .join(WorkspaceModel, WorkspaceModel.model_release_id == ModelRelease.id)
            .where(WorkspaceModel.workspace_key == task.workspace_key)
        )
        if running == migration.get("releaseId"):
            agent.end_session(session, files, task)
            touch(task, retention_days)


def _design_again(
    session: Session,
    task_id: str,
    expected_version: int,
    change: Any,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """A design job from the task as the person left it (``change`` applied to its design)."""
    task = load_task(session, task_id, for_update=True)
    claim(task, expected_version)
    require_state(task, "checked")
    current = dict(task.design or {})
    change(current)
    if (
        task.draft_id is None
        and not current.get("agentSession")
        and not current.get("startSession")
    ):
        raise api_error(409, "AI_TASK_STATE", "The task has no design to answer")
    # The person has spoken: the repairs start again from what they said.
    current["rounds"] = 0
    current["history"] = []
    task.design = current
    job = start_job(
        session,
        kind="aiTask",
        workspace_key=task.workspace_key,
        change_set_id=None,
        model_release_id=load_assignment(session, task.workspace_key)[1].id,
        parameters={
            "phase": "design",
            "taskId": task.public_id,
            "taskVersion": task.version + 1,
            "sendLevel": None,
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    task.job_id = job.id
    task.state = "checking"
    touch(task, task_retention_days)
    session.commit()
    return task
