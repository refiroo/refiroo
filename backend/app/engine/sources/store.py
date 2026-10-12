"""Source files: a draft's or a profile's file, kept for as long as its owner (Product 0.10 A3, D5).

``POST /source-files`` checks the file as an import's upload is checked (``IMPORT_MAX_BYTES``, a
workbook or CSV format) and stores it in ``JOB_FILE_DIR`` as ``{id}.upload``, then queues the job
of kind ``profile`` that stages its cells and profiles them (``profiling.py``), in one commit. The
owner's earlier file is superseded: it stays readable, and the job retention sweep removes it
``JOB_RETENTION_DAYS`` after the newer one arrived (:func:`expire_superseded`). A file goes with its
draft or profile; its cells and profile go with its row, and the sweep removes the file from disk
(``JobFiles.reconcile``).
"""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import (
    Job,
    ModelDraft,
    SourceFile,
    SourceFileSheet,
)
from ...models.sources import SourceFileRequest
from ..imports.profiles import load_profile
from ..imports.submit import Upload
from ..jobs.files import JobFiles
from ..jobs.store import start_job
from ..model.drafts import load_draft
from ..model.registry import resolve_model_snapshot
from ..workspaces.catalogue import resolve_workspace

SUFFIXES = {".xlsx": "xlsx", ".csv": "csv"}
_READ = 1 << 20
_KEYS = (integer_key("id", SourceFile.id, "id", descending=True),)


def store_source_file(
    session: Session,
    request: SourceFileRequest,
    upload: Upload,
    *,
    files: JobFiles,
    retention_days: int,
) -> SourceFile:
    """Store the file, supersede its owner's earlier one and queue its profile; commits."""
    found_format = source_format(request, upload)
    draft_id, profile_key = _owner(session, request)
    if request.workspaceKey is not None:
        resolve_workspace(session, request.workspaceKey)
    now = datetime.now(UTC)
    source = SourceFile(
        draft_id=draft_id,
        profile_key=profile_key,
        name=upload.name or f"source.{found_format}",
        format=found_format,
        bytes=upload.size,
        sha256=upload.sha256,
        csv_delimiter=(request.csv.delimiter if request.csv else ",")
        if found_format == "csv"
        else None,
        workspace_key=request.workspaceKey,
        version=1,
        uploaded_at=now,
    )
    session.add(source)
    session.flush()
    session.execute(
        update(SourceFile)
        .where(
            _same_owner(draft_id, profile_key),
            SourceFile.id != source.id,
            SourceFile.superseded_at.is_(None),
        )
        .values(superseded_at=now)
        .execution_options(synchronize_session=False)
    )
    job = start_job(
        session,
        kind="profile",
        workspace_key=resolve_workspace(session, request.workspaceKey).key,
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session).release_db_id,
        parameters={
            "sourceFileId": source.public_id,
            "file": {"name": source.name, "format": found_format, "bytes": upload.size},
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    source.profile_job_id = job.id
    target = files.upload(source.public_id)
    files.directory.mkdir(parents=True, exist_ok=True)
    try:
        upload.file.seek(0)
        with target.open("wb") as copy:
            shutil.copyfileobj(upload.file, copy, _READ)
        session.commit()
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return source


@contextmanager
def stored_upload(
    session: Session, source_file_id: str, *, files: JobFiles, max_bytes: int
) -> Iterator[Upload]:
    """A stored source file as an import's upload (D5): ``POST /imports`` naming
    ``sourceFileId`` imports it as if it had been sent."""
    source = load_source_file(session, source_file_id)
    path = files.upload(source.public_id)
    if not path.is_file():
        raise api_error(
            410,
            "SOURCE_FILE_MISSING",
            f"The file of source file '{source_file_id}' is no longer in the job file directory; "
            "upload it again. Operators: check JOB_FILE_DIR and what removes files from it",
        )
    with path.open("rb") as file:
        yield Upload.read(source.name, file, max_bytes)


def source_format(request: SourceFileRequest, upload: Upload) -> str:
    """The request's ``format``, or the file name's suffix: a workbook or a CSV file."""
    if request.format is not None:
        return request.format
    suffix = Path(upload.name).suffix.lower()
    if suffix in SUFFIXES:
        return SUFFIXES[suffix]
    hint = " Save it as XLSX first." if suffix == ".xls" else ""
    raise api_error(
        422,
        "UNSUPPORTED_FILE_FORMAT",
        f"A source file is an XLSX workbook or a CSV file; '{upload.name}' is neither.{hint} "
        "Name the format in the request when the file name does not say it",
        {"fileName": upload.name},
    )


def load_source_file(session: Session, source_file_id: str) -> SourceFile:
    source = session.scalar(select(SourceFile).where(SourceFile.public_id == source_file_id))
    if source is None:
        raise api_error(
            404, "SOURCE_FILE_NOT_FOUND", f"Source file '{source_file_id}' not found"
        )
    return source


def source_file_page(
    session: Session,
    *,
    draft_public_id: str | None,
    profile_key: str | None,
    page: PageRequest,
    page_size: int,
) -> Page[SourceFile]:
    """An owner's source files, newest first; every file without an owner named."""
    statement = select(SourceFile)
    if draft_public_id is not None:
        statement = statement.join(ModelDraft, ModelDraft.id == SourceFile.draft_id).where(
            ModelDraft.public_id == draft_public_id
        )
    if profile_key is not None:
        statement = statement.where(SourceFile.profile_key == profile_key)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="source-files",
        filters={"draftId": draft_public_id, "profileKey": profile_key},
        page=page,
        page_size=page_size,
        message="Source file list cursor is invalid",
    )


def delete_source_file(
    session: Session, source_file_id: str, expected_version: int, *, files: JobFiles
) -> None:
    """Delete the file at ``expectedVersion``, its cells and profile; a profile job still running
    is asked to stop. Commits."""
    source = load_source_file(session, source_file_id)
    session.refresh(source, with_for_update=True)
    if source.version != expected_version:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            f"Source file '{source_file_id}' is at version {source.version}",
            {"currentVersion": source.version},
        )
    if source.profile_job_id is not None:
        session.execute(
            update(Job)
            .where(Job.id == source.profile_job_id, Job.state.in_(("queued", "running")))
            .values(cancel_requested_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
    session.execute(delete(SourceFile).where(SourceFile.id == source.id))
    session.commit()
    files.upload(source_file_id).unlink(missing_ok=True)


def profile_state(session: Session, source: SourceFile) -> dict[str, object]:
    """Where the file's profile stands: ``completed`` once its sheets are stored; otherwise its
    job's state (``queued``, ``running``, ``failed``, ``cancelled``), with the job's error."""
    ready = session.scalar(
        select(exists().where(SourceFileSheet.source_file_id == source.id))
    )
    state: dict[str, object] = {"jobId": source.profile_job_id}
    if ready:
        return {"state": "completed", **state}
    job = (
        session.scalar(select(Job).where(Job.id == source.profile_job_id))
        if source.profile_job_id
        else None
    )
    if job is None:
        return {"state": "failed", **state}
    found: dict[str, object] = {"state": job.state, **state}
    if job.error is not None:
        found["error"] = job.error
    return found


def require_profile(session: Session, source: SourceFile) -> None:
    """Refuse a read of a profile not stored yet, with where it stands."""
    state = profile_state(session, source)
    if state["state"] != "completed":
        raise api_error(
            409,
            "SOURCE_FILE_PROFILE_NOT_READY",
            f"Source file '{source.public_id}' is not profiled yet: its profile is "
            f"{state['state']}",
            state,
        )


def expire_superseded(session: Session, now: datetime, retention_days: int) -> list[str]:
    """Delete the files superseded more than ``retention_days`` ago (D5); their IDs, whose files the
    caller removes from disk once it committed."""
    return list(
        session.scalars(
            delete(SourceFile)
            .where(
                SourceFile.superseded_at.is_not(None),
                SourceFile.superseded_at <= now - timedelta(days=retention_days),
            )
            .returning(SourceFile.public_id)
        )
    )


def _owner(session: Session, request: SourceFileRequest) -> tuple[int | None, str | None]:
    owner = request.owner
    if owner.draftId is not None:
        return load_draft(session, owner.draftId).id, None
    return None, load_profile(session, owner.profileKey).key


def _same_owner(draft_id: int | None, profile_key: str | None):
    if draft_id is not None:
        return SourceFile.draft_id == draft_id
    return SourceFile.profile_key == profile_key
