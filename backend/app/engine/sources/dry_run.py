"""A model draft's dry run (Product 0.10 A3, D65–D67, D71): the 0.9 import preview of a source file
run against the draft's compiled model, writing nothing.

``POST /model-drafts/{id}/dry-run`` names one of the draft's source files, a workspace and the
profile that binds the file (D65), checked against the draft's model; a draft that does not compile
is refused (D71). It queues a job of kind ``dryRun`` and asks the draft's earlier dry run, if one
still runs, to stop. The worker binds the file's staged cells (``staged.py``, D66) as an import
binds its file and previews every item (D67) in a transaction it rolls back, as J3's preview does,
with the draft's model in the context in place of the active release's. A dry run whose draft has
changed since it was sent stops as ``cancelled``: its answer would be about a model no longer there.

The summary counts, per source in load order: rows, records created, updated and unchanged, the
values they write, relationships, related records, and the rows refused by code; and the
difference from the draft's previous completed dry run of the same file.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import Job, ModelDraft, SourceFile
from ...models.imports import ImportProfileDefinition
from ...models.schema import EngineModel
from ...models.sources import DryRunRequest
from ..imports.profiles import check_profile, invalid_profile, source_order
from ..imports.readers import TabularFile, open_tabular
from ..jobs.batches import BatchContext, JobCancelled
from ..jobs.files import JobFiles
from ..jobs.store import ItemOutcome, complete_job, record_outcomes, start_job
from ..model.compiler import compile_authored_model
from ..model.drafts import load_draft
from ..model.registry import resolve_model_snapshot
from ..workspaces.catalogue import resolve_workspace
from .staged import StagedFile
from .store import load_source_file, require_profile

KIND = "dryRun"
RUNNING = ("queued", "running")


class InvalidDraft(Exception):
    """The draft does not compile; its diagnostics say why (D71)."""

    def __init__(self, diagnostics: Any) -> None:
        super().__init__("The model draft is invalid")
        self.diagnostics = diagnostics


def submit_dry_run(
    session: Session, draft_id: str, request: DryRunRequest, *, retention_days: int
) -> Job:
    """Queue the draft's dry run and stop its earlier one; commits."""
    draft = load_draft(session, draft_id)
    source = _draft_source(session, draft, request.sourceFileId)
    require_profile(session, source)
    model = _compiled(draft)
    workspace = resolve_workspace(session, request.workspaceKey, require_active=True)
    definition = ImportProfileDefinition.model_validate(
        request.profile.model_dump(include={"csv", "sources", "valueMaps"}, exclude_none=True)
    )
    problems = check_profile(model, definition)
    if problems:
        raise invalid_profile(problems)
    session.execute(
        update(Job)
        .where(
            Job.kind == KIND,
            Job.state.in_(RUNNING),
            Job.parameters["draftId"].as_string() == draft.public_id,
        )
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    job = start_job(
        session,
        kind=KIND,
        workspace_key=workspace.key,
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session).release_db_id,
        parameters={
            "policy": "independent",
            "run": "background",
            "stage": "preview",
            "onExisting": request.onExisting,
            "otherWorkspaceIds": "refuse",
            "draftId": draft.public_id,
            "draftVersion": draft.version,
            "sourceFileId": source.public_id,
            "profile": {
                "key": None,
                "version": None,
                "definition": definition.model_dump(mode="json", exclude_none=True),
            },
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
    session.commit()
    return job


def dry_run_context(session: Session, job: Job) -> BatchContext:
    """The dry run's context: the workspace, with the draft's model at the version the dry run
    was sent for. A draft changed since stops the dry run (``JobCancelled``); a release activated
    since fails it, as any job's."""
    workspace = resolve_workspace(session, job.workspace_key, require_active=True)
    snapshot = resolve_model_snapshot(session)
    if snapshot.release_db_id != job.model_release_id:
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            "The model release changed while the dry run waited; run it again",
        )
    draft = _current_draft(session, job)
    return BatchContext(workspace.key, None, _compiled(draft), snapshot.release_db_id, None)


def superseded(session: Session, parameters: dict[str, Any]) -> bool:
    """Whether a dry run's draft (its job's ``parameters``) changed or went since it was sent."""
    version = session.scalar(
        select(ModelDraft.version).where(ModelDraft.public_id == parameters["draftId"])
    )
    return version != parameters["draftVersion"]


def book_opener(session: Session, job: Job, files: JobFiles):
    """What the binding reads (D66): the staged cells, or the stored file when the profile reads
    a CSV file with another delimiter than it was staged with."""
    source = session.scalar(
        select(SourceFile).where(SourceFile.public_id == job.parameters["sourceFileId"])
    )
    if source is None:
        raise api_error(
            404,
            "SOURCE_FILE_NOT_FOUND",
            f"Source file '{job.parameters['sourceFileId']}' was deleted",
        )

    def open_book(file_format: str, delimiter: str) -> TabularFile:
        if file_format == "csv" and delimiter != source.csv_delimiter:
            return open_tabular(files.upload(source.public_id), file_format, delimiter)
        return StagedFile(session, source.id)

    return open_book


def record_dry_run(
    session: Session,
    job: Job,
    outcomes: list[ItemOutcome],
    model: EngineModel,
    *,
    retention_days: int,
) -> None:
    """The dry run's outcomes, its summary and its difference from the draft's previous one; the
    job completes. The caller commits."""
    record_outcomes(session, job, outcomes)
    summary = _summary(session, job, model)
    previous = _previous(session, job)
    summary["difference"] = (
        _difference(previous["sources"], summary["sources"]) if previous is not None else None
    )
    summary["previousJobId"] = previous["jobId"] if previous is not None else None
    job.report = {**(job.report or {}), "dryRun": summary}
    complete_job(session, job, retention_days=retention_days)


def latest_dry_run(session: Session, draft_id: str) -> Job | None:
    draft = load_draft(session, draft_id)
    return session.scalar(
        select(Job)
        .where(Job.kind == KIND, Job.parameters["draftId"].as_string() == draft.public_id)
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )


# Per source, status, action and refusal code: the items, the rows, and the values written.
_COUNTS = """
SELECT o.source_index, i.item ->> 'op' AS op, i.item ->> 'objectTypeKey' AS type_key,
    o.status, o.outcome ->> 'action' AS action, o.outcome -> 'error' ->> 'code' AS code,
    count(*) AS items, count(DISTINCT o.row_number) AS rows,
    coalesce(sum(CASE WHEN jsonb_typeof(i.item::jsonb -> 'attributes') = 'array'
        THEN jsonb_array_length(i.item::jsonb -> 'attributes') END), 0) AS vals
FROM job_items o
LEFT JOIN job_inputs i ON i.job_id = o.job_id AND i.item_index = o.item_index
WHERE o.job_id = :job AND o.source_index IS NOT NULL
GROUP BY 1, 2, 3, 4, 5, 6
"""

_ROWS = """
SELECT source_index, count(DISTINCT row_number) FROM job_items
WHERE job_id = :job AND source_index IS NOT NULL GROUP BY source_index
"""

_RECORD_OPS = {"create", "update", "upsert"}


def _summary(session: Session, job: Job, model: EngineModel) -> dict[str, Any]:
    definition = ImportProfileDefinition.model_validate(job.parameters["profile"]["definition"])
    order = source_order(model, definition) or list(range(len(definition.sources)))
    sources: list[dict[str, Any]] = []
    for position, index in enumerate(order):
        source = definition.sources[index]
        sources.append(
            {
                "source": position,
                "profileSource": index,
                "sheet": source.sheet,
                "objectTypeKey": source.objectTypeKey,
                "rows": 0,
                "records": {"created": 0, "updated": 0, "unchanged": 0},
                "values": 0,
                "relationships": 0,
                "relatedRecords": 0,
                "rejections": {},
            }
        )
    parameters = {"job": job.sequence_id}
    for at, rows in session.execute(text(_ROWS), parameters):
        sources[at]["rows"] = rows
    for row in session.execute(text(_COUNTS), parameters):
        entry = sources[row.source_index]
        if row.status == "rejected":
            code = row.code or "REJECTED"
            entry["rejections"][code] = entry["rejections"].get(code, 0) + row.rows
            continue
        if row.status != "applied":
            continue
        if row.op in _RECORD_OPS:
            if row.type_key == entry["objectTypeKey"]:
                entry["records"][row.action] = entry["records"].get(row.action, 0) + row.items
            elif row.action != "unchanged":
                entry["relatedRecords"] += row.items
            if row.action != "unchanged":
                entry["values"] += int(row.vals)
        elif row.action != "unchanged":
            entry["relationships"] += row.items
    for entry in sources:
        entry["rejections"] = [
            {"code": code, "rows": rows} for code, rows in sorted(entry["rejections"].items())
        ]
    rows_total = sum(entry["rows"] for entry in sources)
    return {
        "jobId": job.id,
        "draftId": job.parameters["draftId"],
        "draftVersion": job.parameters["draftVersion"],
        "sourceFileId": job.parameters["sourceFileId"],
        "workspaceKey": job.workspace_key,
        "coverage": "complete",
        "rows": {"total": rows_total, "run": rows_total},
        "sources": sources,
        "ranAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _previous(session: Session, job: Job) -> dict[str, Any] | None:
    """The draft's last completed dry run of the same file before this one."""
    for (report,) in session.execute(
        select(Job.report)
        .where(
            Job.kind == KIND,
            Job.state == "completed",
            Job.sequence_id < job.sequence_id,
            Job.parameters["draftId"].as_string() == job.parameters["draftId"],
            Job.parameters["sourceFileId"].as_string() == job.parameters["sourceFileId"],
        )
        .order_by(Job.sequence_id.desc())
        .limit(1)
    ):
        return (report or {}).get("dryRun")
    return None


def _figures(entry: dict[str, Any]) -> dict[str, int]:
    figures = {
        "rows": entry["rows"],
        **{f"records.{name}": count for name, count in entry["records"].items()},
        "values": entry["values"],
        "relationships": entry["relationships"],
        "relatedRecords": entry["relatedRecords"],
    }
    figures.update({f"rejections.{item['code']}": item["rows"] for item in entry["rejections"]})
    return figures


def _difference(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Per source (by the type it loads and its sheet), each figure that changed: what it is now
    and what it was. A source new or gone since compares with zeros."""

    def key(entry: dict[str, Any]) -> tuple[str | None, str]:
        return entry["sheet"], entry["objectTypeKey"]

    old = {key(entry): _figures(entry) for entry in before}
    changed = []
    for entry in after:
        now, was = _figures(entry), old.pop(key(entry), {})
        figures = {
            name: {"now": now.get(name, 0), "was": was.get(name, 0)}
            for name in sorted(set(now) | set(was))
            if now.get(name, 0) != was.get(name, 0)
        }
        if figures:
            changed.append(
                {"source": entry["source"], "objectTypeKey": entry["objectTypeKey"],
                 "sheet": entry["sheet"], "figures": figures}
            )
    for (sheet, type_key), was in old.items():
        figures = {name: {"now": 0, "was": count} for name, count in sorted(was.items()) if count}
        if figures:
            changed.append(
                {"source": None, "objectTypeKey": type_key, "sheet": sheet, "figures": figures}
            )
    return changed


def _draft_source(session: Session, draft: ModelDraft, source_file_id: str) -> SourceFile:
    source = load_source_file(session, source_file_id)
    if source.draft_id != draft.id:
        raise api_error(
            404,
            "SOURCE_FILE_NOT_FOUND",
            f"Model draft '{draft.public_id}' has no source file '{source_file_id}'",
        )
    return source


def _current_draft(session: Session, job: Job) -> ModelDraft:
    draft = session.scalar(
        select(ModelDraft).where(ModelDraft.public_id == job.parameters["draftId"])
    )
    if draft is None or draft.version != job.parameters["draftVersion"]:
        raise JobCancelled
    return draft


def _compiled(draft: ModelDraft) -> EngineModel:
    compiled = compile_authored_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        raise InvalidDraft(compiled.diagnostics)
    return compiled.model
