"""An assistant task that designs (Product 0.16 AP6, the user's five cases).

The task's reading phase profiles the workbook and reads it by the rules (AP6a); with the assistant
offered, it opens a draft of the workspace's model, the engine matches the workbook with the
workspace (``matching.py``) and drafts the profile, and the AI is asked only about what the engine
left open or what the person said (``design.py``, AP7). The person reviews the proposal. An accepted
design is checked by a dry run of every row of the working copy against the draft (a ``dryRun`` job
naming the task and the draft); what it refuses goes to the AI in up to :data:`REPAIRS` calls, then
to the person. The load
installs the draft as a release and activates it in the workspace when the model changed, then
imports the working copy into a new change set and saves the profile of the person's sheets.

A turn never holds a transaction while the provider answers (each is preceded by a commit).
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import AiTask, Job, ModelDraft, ModelRelease, SourceFile
from ...models.imports import (
    ImportProfileCreate,
    ImportProfileDefinition,
    ImportRequest,
    InlineProfile,
)
from ..change_sets.access import load_change_set
from ..change_sets.lifecycle import create_change_set
from ..imports.profiles import load_profile, parsed, source_order
from ..imports.profiles import save_profile as save_import_profile
from ..imports.submit import submit_import
from ..jobs.store import start_job
from ..model.compiler import compile_model
from ..model.releases import activate_model_release, install_model_release
from ..model.workspace_models import load_assignment
from ..sources.store import stored_upload
from . import agent, design, design_checks, draft_plan, links, matching
from .store import claim, finish, load_task, note, require_state, touch


def held_counts(session: Session, workspace: str) -> dict[str, int]:
    return dict(
        session.execute(
            text(
                "SELECT object_type_key, count(*) FROM objects WHERE workspace_key = :w GROUP BY 1"
            ),
            {"w": workspace},
        ).all()
    )


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
    if current.get("agentSession"):
        words = current.pop("pendingWords", None)
        task = load_task(session, task_id, for_update=True)
        task.design = current
        session.commit()
        if current.get("stage") == "load":
            agent.accepted(session, job, ctx, task_id)
        else:
            agent.said(session, job, ctx, task_id, words or "", dry_run_check)
        return
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


def dry_run_check(session: Session, draft: ModelDraft) -> dict[str, Any] | None:
    """The check a draft's latest dry run gives, whoever asked for it."""
    job = session.scalar(
        select(Job)
        .where(Job.kind == "dryRun", Job.parameters["draftId"].as_string() == draft.public_id)
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )
    if job is None or job.state != "completed":
        return None
    return check_of_job(session, job, draft, 0, [])


def _engine_outline(found: dict[str, Any], types: Any) -> list[dict[str, str]]:
    return [
        {
            "objectTypeKey": fact["type"],
            "text": (
                f"from “{fact['sheet']}”: {fact['found']} of {fact['rows']} rows are stored "
                f"records found by “{fact['key']}”, {fact['new']} are new"
            ),
        }
        for fact in found.get("facts") or []
        if fact.get("type") in types
    ]


def _engine_summary(found: dict[str, Any]) -> str:
    parts = []
    for fact in found.get("facts") or []:
        if fact.get("type"):
            parts.append(
                f"“{fact['sheet']}”: {fact['found']} of {fact['rows']} rows match stored records "
                f"by “{fact['key']}”, {fact['new']} are new."
            )
        else:
            parts.append(f"“{fact['sheet']}”: {fact['rows']} rows, {fact['found']}.")
    return " ".join(parts)


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
    compiled = compile_model(draft.model_json).model
    found_links = []
    for raw in current.get("links") or []:
        try:
            rule = links.LinkRule.model_validate(raw)
        except ValidationError as error:
            found_links.append({"rule": raw, "refused": str(error)[:300]})
            continue
        if compiled is None:
            found_links.append({"rule": raw, "refused": "The draft does not compile"})
            continue
        found_links.append({"rule": raw, **links.check(session, compiled, task.workspace_key, rule)})
    if found_links:
        checked["links"] = found_links
        if current.get("profile") is None and source is None:
            # An instruction on the workspace's records: nothing to import.
            checked.pop("profileProblems", None)
    problems = draft_plan.derived_problems(session, source, current)
    if problems:
        checked["profileProblems"] = [*(checked.get("profileProblems") or []), *problems]
    unresolved = draft_plan.unresolved_links(
        session,
        source,
        task.workspace_key,
        current.get("profile"),
        current.get("records") or [],
    )
    if unresolved:
        checked["unresolved"] = unresolved
    unloaded = sheets_not_loaded(task, current)
    if unloaded:
        checked["sheetsNotLoaded"] = unloaded
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
    current["summary"] = _engine_summary(found)
    current["outline"] = _engine_outline(found, types)
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
    fits = _same_layout(task, found, {}) and not _new_columns(task, found)
    session.rollback()
    return fits


def _new_columns(task: AiTask, found: dict[str, Any]) -> list[dict[str, Any]]:
    """Of the columns the match could not place, those the file the saved profile read before did
    not have: what that profile left out it left out on purpose."""
    earlier = {
        (t["sheet"], c.get("header"))
        for t in (task.reading or {}).get("tables", [])
        for c in t.get("columns") or []
        if c.get("known") or c.get("binding") is not None
    }
    return [u for u in found["unplaced"] if (u["sheet"], u["column"]) not in earlier]


def _same_layout(task: AiTask, found: dict[str, Any], answers: dict[str, str]) -> bool:
    """Whether the saved profile the reading followed finds as many stored records as the match,
    on every table: one that would make new what the match finds stored is no such profile. An
    answer against what the match assumed needs the match's own profile."""
    if any(
        answers.get(q["text"], q.get("assumed")) != q.get("assumed") for q in found["questions"]
    ):
        return False
    new_by_sheet = {f["sheet"]: f.get("new", 0) for f in found["facts"]}
    tables = (task.reading or {}).get("tables", [])
    return all(
        t.get("profile") is not None and int(t.get("new") or 0) <= new_by_sheet.get(t["sheet"], 0)
        for t in tables
    )


def sheets_not_loaded(task: AiTask, current: dict[str, Any]) -> list[str]:
    """The workbook's sheets with a table that no source of the design reads (the quiet tables'
    sheets are read by their kept sources)."""
    found = (task.reading or {}).get("tables", [])
    read = {s.get("sheet") for s in (current.get("profile") or {}).get("sources") or []}
    read |= {s.get("sheet") for s in kept_sources(task)}
    read |= {s for d in current.get("derived") or [] for s in d.get("sheets") or []}
    return sorted({t["sheet"] for t in found} - read)


def columns_left_out(task: AiTask, current: dict[str, Any]) -> list[dict[str, Any]]:
    """The columns of the sheets the design reads that no source of their sheet loads, each with
    the assistant's reason when it gave one (``None`` otherwise)."""
    own = list((current.get("profile") or {}).get("sources") or [])
    # As the load reads them: a quiet table's kept source only where the design has none.
    kept = [k for k in kept_sources(task) if not any(_same_place(k, s) for s in own)]
    sources = [*own, *kept]
    bound: dict[str, set[str]] = {}
    for source in sources:
        names = bound.setdefault(source.get("sheet") or "", set())
        names |= {c["column"] for c in source.get("columns") or [] if not c.get("ignore")}
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
        (current.get("profile") is not None or bool(current.get("links")))
        and "refused" not in (outcome.get("modelOperations") or {})
        and not outcome.get("draftErrors")
        and not outcome.get("profileProblems")
        and not any("refused" in item for item in outcome.get("links") or [])
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
    """The structure sheets' sources first, then the quiet tables' sources the design does not
    replace (``kept``), then the design's; the rules' value maps under the design's."""
    profile = current.get("profile")
    if profile is None:
        return None
    records = [design.StructureRecord.model_validate(r) for r in current.get("records") or []]
    structure = draft_plan.structure_sources(records, model)
    own = list(profile.get("sources") or [])
    kept = [k for k in kept or [] if not any(_same_place(k, s) for s in own)]
    maps = {
        **((current.get("rulesProfile") or {}).get("valueMaps") or {}),
        **(profile.get("valueMaps") or {}),
    }
    return {**profile, "sources": structure + kept + own, "valueMaps": maps}


def design_so_far(current: dict[str, Any], rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """The design the engine holds, sent back every turn: the profile, the records and the links
    whole, each data sheet by its columns, row count and first rows (the model's changes are in
    the model, marked new). A part the answer leaves out is kept, so a fix changes only what the
    outcome refused."""
    profile = current.get("profile")
    # ``rules``: the rules' profile as the request sends it (its quiet tables' sources left out).
    rules = rules if rules is not None else current.get("rulesProfile") or {}
    same = bool(profile) and all(
        (profile or {}).get(part) == rules.get(part) for part in ("sources", "valueMaps")
    )
    return {
        # Still the rules' profile: named, not sent twice.
        "profile": "rulesProfile" if same else profile,
        "records": current.get("records") or [],
        "links": current.get("links") or [],
        "rounds": current.get("history") or [],
        "derived": current.get("derived") or [],
        "sheets": [
            {
                "name": sheet["name"],
                "columns": sheet["columns"],
                "rowCount": len(sheet["rows"]),
                "firstRows": sheet["rows"][:5],
            }
            for sheet in current.get("sheets") or []
        ],
    }


def queue_check(session: Session, task: AiTask, files: Any, retention_days: int) -> Job | None:
    """Stage the working copy as the draft's file and queue its dry run against the draft. A
    design that imports nothing (relationships between stored records only) is checked by the
    counts of its rules: the task is ``checked`` at once."""
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    current = task.design or {}
    if current.get("profile") is None:
        found = (current.get("outcome") or {}).get("links") or []
        task.check = {
            "dryRunJobId": None,
            "ranAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "sheets": [],
            "refused": [],
            "links": found,
            "summary": {
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "refused": 0,
                "relationships": sum(int(item.get("pairs") or 0) for item in found),
            },
            "rounds": int(current.get("rounds", 0)),
        }
        task.state = "checked"
        touch(task, 90, bump=False)
        return None
    records = [design.StructureRecord.model_validate(r) for r in current.get("records") or []]
    original = task_source(session, task)
    data = [design.DataSheet.model_validate(d) for d in current.get("sheets") or []]
    derived = draft_plan.derived_sheets(session, original, current.get("derived") or [])
    content, _ = draft_plan.working_book(
        files.upload(original.public_id), records, draft.model_json, data, derived
    )
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
    session: Session, job: Job, draft: ModelDraft | None, rounds: int, found_links: list[Any]
) -> dict[str, Any]:
    """A dry run's check per sheet from its outcomes."""
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
                "structure": str(source.get("sheet") or "").startswith(draft_plan.STRUCTURE),
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
        "links": found_links,
        "summary": {
            "created": sum(f["created"] for f in figures.values()),
            "updated": sum(f["updated"] for f in figures.values()),
            "unchanged": sum(f["unchanged"] for f in figures.values()),
            "refused": sum(r["rows"] for r in refused),
            "relationships": sum(int(item.get("pairs") or 0) for item in found_links),
        },
        "rounds": rounds,
    }


def checked(session: Session, task: AiTask, job: Job, *, ai: Any, retention_days: int) -> None:
    """The worker recorded a saved layout's dry run: the check per sheet from the outcomes, and the
    task is ``checked``. The caller commits."""
    if task.job_id != job.id:
        return
    current = dict(task.design or {})
    found_links = (current.get("outcome") or {}).get("links") or []
    draft = session.get(ModelDraft, task.draft_id)
    task.check = check_of_job(session, job, draft, 0, found_links)
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
    """The version after the highest the model's releases (and the draft) have, its last number
    bumped: a release the assistant installs is the newest, whatever release the draft came from."""
    taken = set(
        session.scalars(select(ModelRelease.release_version).where(ModelRelease.release_key == key))
    )

    def order(text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in re.findall(r"\d+", text))

    highest = max([*taken, version], key=order)
    match = re.match(r"^(.*?)(\d+)$", highest)
    head, number = (match.group(1), int(match.group(2))) if match else (f"{highest}.", 0)
    number += 1
    while f"{head}{number}" in taken:
        number += 1
    return f"{head}{number}"


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
    # The next file holds the person's sheets, not the sheets this design derived or wrote.
    written = {d["name"] for d in current.get("derived") or []} | {
        s["name"] for s in current.get("sheets") or []
    }
    own = [s for s in profile.get("sources") or [] if s.get("sheet") not in written]
    kept = [k for k in kept_sources(task) if not any(_same_place(k, s) for s in own)]
    maps = {
        **((current.get("rulesProfile") or {}).get("valueMaps") or {}),
        **(profile.get("valueMaps") or {}),
    }
    return {**profile, "sources": kept + own, "valueMaps": maps}


def working_file(session: Session, task: AiTask, files: Any) -> tuple[SourceFile, Path]:
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    work = working_source(session, draft.id)
    if work is None:
        raise api_error(409, "AI_TASK_STATE", "The design has not been checked yet")
    return work, files.upload(work.public_id)


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
    if draft is None or not (design_now.get("profile") or design_now.get("links")):
        raise api_error(409, "AI_TASK_NOTHING_TO_LOAD", "The design loads nothing yet")
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
    if profile is None:
        # Relationships between stored records only: one batch into the change set.
        task.state = "loading"
        task.result = {
            "changeSetId": change_set.id,
            "changeSetName": change_set.name,
            "importJobId": None,
            "profileKey": None,
            **({"releaseId": release_id} if release_id else {}),
        }
        touch(task, task_retention_days)
        job = queue_links(session, task, change_set, retention_days)
        if job is None:
            raise api_error(409, "AI_TASK_NOTHING_TO_LOAD", "The design's rules relate nothing")
        task.job_id = job.id
        session.commit()
        return task
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
        **({"linksPending": True} if (task.design or {}).get("links") else {}),
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


def queue_links(session: Session, task: AiTask, change_set: Any, retention_days: int) -> Job | None:
    """The design's relationships as a batch into the task's change set (``links.py``); the caller
    commits."""
    snapshot = load_assignment(session, task.workspace_key)[1]
    model = compile_model(snapshot.model_json).model
    assert model is not None
    return links.queue(
        session,
        model,
        workspace=task.workspace_key,
        change_set=change_set,
        model_release_id=snapshot.id,
        rules=links.rules_of(task.design or {}),
        retention_days=retention_days,
    )


def import_finished(session: Session, job_id: str, retention_days: int) -> None:
    """The worker finished an import: when it was a design's with relationships, their batch
    follows into the same change set and the task waits for it. The caller commits."""
    task = session.scalar(
        select(AiTask).where(AiTask.job_id == job_id, AiTask.state == "loading").with_for_update()
    )
    if task is not None and (task.result or {}).get("linksPending"):
        after_import(session, task, retention_days)


def after_import(session: Session, task: AiTask, retention_days: int) -> bool:
    """Queue the relationships of a design whose import finished into the same change set; the
    task waits for them. ``False`` when there is none to run. The caller commits."""
    result = dict(task.result or {})
    if not result.pop("linksPending", False):
        return False
    change_set = load_change_set(session, result["changeSetId"])
    job = queue_links(session, task, change_set, retention_days)
    task.result = {**result, **({"linksJobId": job.id} if job is not None else {})}
    if job is None:
        return False
    task.job_id = job.id
    return True


def queue_answers(
    session: Session,
    task_id: str,
    expected_version: int,
    answers: dict[str, str],
    *,
    retention_days: int,
    task_retention_days: int,
) -> AiTask:
    """The person's answers to the design's questions: a design round that takes them. Commits."""

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
    """The steward's correction of the proposed model, in words: the model stage again, the words
    winning over the assistant's own choices. Commits."""

    def change(current: dict[str, Any]) -> None:
        current["stage"] = "model"
        current["corrections"] = [*(current.get("corrections") or []), correction]
        current["pendingWords"] = correction
        current["reasonsAsked"] = False
        current["checksAsked"] = False

    return _design_again(
        session, task_id, expected_version, change, retention_days, task_retention_days
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


def discard(session: Session, task_id: str, files: Any, retention_days: int) -> AiTask:
    """The person discards a proposal: the task ends and its draft and folder go. Commits."""
    task = load_task(session, task_id, for_update=True)
    require_state(task, "checked", "read")
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id else None
    task.draft_id = None
    session.flush()
    if draft is not None:
        session.delete(draft)
    agent.remove_folder(files, task)
    finish(task, "cancelled", retention_days)
    session.commit()
    return task


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
    if task.draft_id is None:
        raise api_error(409, "AI_TASK_STATE", "The task has no design to answer")
    current = dict(task.design or {})
    change(current)
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
