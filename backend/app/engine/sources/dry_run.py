"""A model draft's dry run (Product 0.10 A3, D65–D67, D71): the 0.9 import preview of a source file
run against the draft's compiled model, writing nothing.

``POST /model-drafts/{id}/dry-run`` names one of the draft's source files, a workspace and the
profile that binds the file (D65), checked against the draft's model; a draft that does not compile
is refused (D71). It queues a job of kind ``dryRun`` and asks the draft's earlier dry run, if one
still runs, to stop. The worker binds the file's staged cells (``staged.py``, D66) as an import
binds its file and previews every item (D67) in a transaction it rolls back, as J3's preview does,
with the draft's model in the context in place of the active release's. A dry run whose draft has
changed since it was sent stops as ``cancelled``: its answer would be about a model no longer there.

The summary counts, per source in load order: rows, records created, updated, unchanged and
deleted, the values they write, relationships, related records, the records missing from the file
(0.10 A5c, D82), the rows skipped for want of a key (0.10 A7, D110) and the rows refused by code;
and the difference from the draft's previous completed dry run of the same file. A profile's check
(``profile_check.py``) summarizes its run the same way.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...db import lock_job_subject
from ...errors import api_error
from ...models.database import Job, ModelDraft, ModelDraftOperation, SourceFile
from ...models.imports import ImportProfileDefinition
from ...models.schema import EngineModel
from ...models.sources import DryRunRequest
from ..imports.profiles import check_profile, invalid_profile, source_order
from ..imports.readers import TabularFile, open_tabular
from ..jobs.background import open_job_context
from ..jobs.batches import BatchContext, JobCancelled
from ..jobs.files import JobFiles
from ..jobs.store import ItemOutcome, complete_job, job_parameter, record_outcomes, start_job
from ..model.compiler import compile_model
from ..model.drafts import load_draft
from ..model.registry import resolve_model_snapshot
from ..workspaces.catalogue import resolve_workspace
from .profile_export import definition as exported_profile
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
    if request.profile is not None:
        sent = request.profile.model_dump(
            include={"csv", "sources", "valueMaps"}, exclude_none=True
        )
    else:
        # The draft's own profile, as GET /model-drafts/{id}/profile exports it (0.13 AT).
        sent, _ = exported_profile(draft.profile_json)
        if sent is None:
            raise api_error(
                422,
                "INVALID_IMPORT_PROFILE",
                f"Model draft '{draft_id}' has no profile that loads a column; send a profile",
                {"pointer": "/profile"},
            )
    definition = ImportProfileDefinition.model_validate(sent)
    problems = check_profile(model, definition)
    if problems:
        raise invalid_profile(problems)
    lock_job_subject(session, KIND, draft.public_id)
    session.execute(
        update(Job)
        .where(
            Job.kind == KIND,
            Job.state.in_(RUNNING),
            job_parameter("draftId") == draft.public_id,
        )
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    job = start_job(
        session,
        kind=KIND,
        workspace_key=workspace.key,
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session, workspace.key).release_db_id,
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
    since fails it, as any job's. An assistant task's dry run (0.16 AP6a) runs on the workspace's
    live data under its active release, as an import does."""
    if "taskId" in job.parameters and "draftId" not in job.parameters:
        return open_job_context(session, job)
    workspace = resolve_workspace(session, job.workspace_key, require_active=True)
    snapshot = resolve_model_snapshot(session, workspace.key)
    if snapshot.release_db_id != job.model_release_id:
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            "The model release changed while the dry run waited; run it again",
        )
    draft = _current_draft(session, job)
    return BatchContext(workspace.key, None, _compiled(draft), snapshot.release_db_id, None)


# Steps of only these kinds change nothing a load writes, so no dry run follows them (D79): labels,
# the release identity, layout, navigation and consumer API definitions.
NO_DRY_RUN = frozenset(
    {
        "setLabel",
        "setRelease",
        "setProfile",
        "addView",
        "removeView",
        "insertViewItem",
        "addPanel",
        "moveViewItem",
        "removeViewItem",
        "setViewProperty",
        "addDetailPage",
        "removeDetailPage",
        "addNavigationGroup",
        "removeNavigationGroup",
        "setNavigationGroup",
        "placeCollection",
        "setCollectionOpening",
        "addConsumerApi",
        "removeConsumerApi",
        "setConsumerApiPart",
        "insertConsumerApiPart",
        "moveConsumerApiPart",
        "removeConsumerApiPart",
    }
)


def runs_dry_run(operations: list[dict[str, Any]]) -> bool:
    """Whether a step of these operations can change what the load writes (D79)."""
    for operation in operations:
        name = operation.get("kind")
        if name == "restoreElements":
            name = (operation.get("undoes") or {}).get("kind")
        if name == "setProfile" and operation.get("kind") == "setProfile" and (
            "sources" in operation or "valueMaps" in operation
        ):
            # A whole profile changes the load (0.13 AQ); its key and name alone do not.
            return True
        if name not in NO_DRY_RUN:
            return True
    return False


def superseded(session: Session, parameters: dict[str, Any]) -> bool:
    """Whether a dry run's draft (its job's ``parameters``) went, or took a step since the dry run
    was sent that can change what the load writes (D79). A step that cannot, a rename or a layout
    change, queues no dry run of its own, so the running one goes on: stopping it left the drawer
    at Stopped with no result (0.10 R, found by the composed runner)."""
    draft_id = session.scalar(select(ModelDraft.id).where(ModelDraft.public_id == parameters["draftId"]))
    if draft_id is None:
        return True
    steps = session.execute(
        select(ModelDraftOperation.kind, ModelDraftOperation.parameters).where(
            ModelDraftOperation.draft_id == draft_id,
            ModelDraftOperation.draft_version > parameters["draftVersion"],
        )
    ).all()
    return runs_dry_run([{**(found or {}), "kind": kind} for kind, found in steps])


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
            path = files.upload(source.public_id)
            if not path.is_file():
                raise _deleted(job)
            return open_tabular(path, file_format, delimiter)
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
    require_file(session, job)
    record_outcomes(session, job, outcomes)
    found = summary(session, job, model)
    # A model draft's dry run is compared with its previous one; a task's check is not (0.16 AP6a).
    previous = _previous(session, job) if "draftId" in job.parameters else None
    found["difference"] = (
        _difference(previous["sources"], found["sources"]) if previous is not None else None
    )
    found["previousJobId"] = previous["jobId"] if previous is not None else None
    job.report = {**(job.report or {}), "dryRun": found}
    complete_job(session, job, retention_days=retention_days)


def require_file(session: Session, job: Job) -> None:
    """Refuse to record a run whose source file was deleted while it read the file's cells: what
    it read may be part of the file only (0.10 R-F8). A file deleted stays deleted, so one there
    now was there throughout."""
    found = session.scalar(
        select(SourceFile.id).where(SourceFile.public_id == job.parameters["sourceFileId"])
    )
    if found is None:
        raise _deleted(job)


def _deleted(job: Job) -> Exception:
    return api_error(
        404,
        "SOURCE_FILE_NOT_FOUND",
        f"Source file '{job.parameters['sourceFileId']}' was deleted while it was read",
    )


def latest_dry_run(session: Session, draft_id: str) -> Job | None:
    draft = load_draft(session, draft_id)
    return session.scalar(
        select(Job)
        .where(Job.kind == KIND, job_parameter("draftId") == draft.public_id)
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


def summary(session: Session, job: Job, model: EngineModel) -> dict[str, Any]:
    """Per source in load order, what the job's previewed items would do (module docstring)."""
    definition = ImportProfileDefinition.model_validate(job.parameters["profile"]["definition"])
    order = source_order(model, definition) or list(range(len(definition.sources)))
    bound = (job.report or {}).get("bindingReport") or []
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
                "records": {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0},
                "values": 0,
                "relationships": 0,
                "relatedRecords": 0,
                "missingRecords": (bound[position] if position < len(bound) else {}).get(
                    "missingRecords", 0
                ),
                "skippedRows": (bound[position] if position < len(bound) else {}).get(
                    "skippedRows", 0
                ),
                "rejections": {},
            }
        )
    parameters = {"job": job.sequence_id}
    # The job's tens of thousands of outcomes and inputs were written moments ago; planned by
    # statistics that had not seen them, the counts joined each outcome with every input of the
    # job: 64 s of a 10,000-row check (0.10 R). ANALYZE samples a bounded number of rows.
    session.execute(text("ANALYZE job_items, job_inputs"))
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
        if row.op == "delete":
            entry["records"]["deleted"] += row.items if row.action == "deleted" else 0
        elif row.op in _RECORD_OPS:
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
    drafted = (
        {"draftId": job.parameters["draftId"], "draftVersion": job.parameters["draftVersion"]}
        if "draftId" in job.parameters
        else {}
    )
    if "taskId" in job.parameters:
        drafted = {"taskId": job.parameters["taskId"]}
    return {
        "jobId": job.id,
        **drafted,
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
            job_parameter("draftId") == job.parameters["draftId"],
            job_parameter("sourceFileId") == job.parameters["sourceFileId"],
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
        "missingRecords": entry.get("missingRecords", 0),
        "skippedRows": entry.get("skippedRows", 0),
    }
    figures.update({f"rejections.{item['code']}": item["rows"] for item in entry["rejections"]})
    return figures


def _difference(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Per source (by its sheet, the type it loads and its place among the sources sharing them),
    each figure that changed: what it is now and what it was. A source new or gone since compares
    with zeros. Several sources may load one type from one sheet: a list read block by block
    (D141), or translations by language (0.10 R-F2)."""

    def keyed(entries: list[dict[str, Any]]) -> list[tuple[tuple[str | None, str, int], dict[str, Any]]]:
        seen: dict[tuple[str | None, str], int] = {}
        found = []
        for entry in entries:
            shared = (entry["sheet"], entry["objectTypeKey"])
            seen[shared] = seen.get(shared, -1) + 1
            found.append(((*shared, seen[shared]), entry))
        return found

    old = {key: _figures(entry) for key, entry in keyed(before)}
    changed = []
    for key, entry in keyed(after):
        now, was = _figures(entry), old.pop(key, {})
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
    for (sheet, type_key, _place), was in old.items():
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
    """The dry run's draft, unless it went or took a step that can change the load since (its
    model then differs from the dry run's only in what the load does not read)."""
    draft = session.scalar(
        select(ModelDraft).where(ModelDraft.public_id == job.parameters["draftId"])
    )
    if draft is None or superseded(session, job.parameters):
        raise JobCancelled
    return draft


def _compiled(draft: ModelDraft) -> EngineModel:
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        raise InvalidDraft(compiled.diagnostics)
    return compiled.model
