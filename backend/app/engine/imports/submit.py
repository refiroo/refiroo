"""Submitting an import (Base 0.9 J2, INTEGRATION_API §J1, D64, D67).

``POST /imports`` sends a file and its request in one ``multipart/form-data`` body. Before a job is
stored, the request is checked as a background batch's is (its context, a change set's version
claim), the file's size against ``IMPORT_MAX_BYTES``, its format, and the profile against the
context's model release; a refusal stores nothing. The file is then written to ``JOB_FILE_DIR`` as
``{jobId}.source`` and the job is queued with it in one commit, so the worker never claims a job
whose file is not there. An ``Idempotency-Key`` covers the request and the file's SHA-256: a retry
answers with the first job, another file under the same key is refused.
"""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ChangeSet, Job
from ...models.imports import ImportProfileDefinition, ImportRequest
from ..jobs.batches import check_batch_context, open_batch_context
from ..jobs.files import JobFiles
from ..jobs.store import remember_key, replayed_job, request_fingerprint, start_job
from .profiles import check_profile, invalid_profile, load_profile, parsed, require_model
from .readers import PROFILE_SHEET, carried_profile, unreadable

IMPORTS_SCOPE = "POST /imports"
SUFFIXES = {".xlsx": "xlsx", ".csv": "csv", ".jsonl": "jsonl", ".ndjson": "jsonl"}
_READ = 1 << 20


@dataclass(frozen=True)
class Upload:
    """The file part as received: its name, its spooled content, its size and SHA-256."""

    name: str
    file: BinaryIO
    size: int
    sha256: str

    @classmethod
    def read(cls, name: str, file: BinaryIO, max_bytes: int) -> Upload:
        digest = hashlib.sha256()
        size = 0
        file.seek(0)
        while chunk := file.read(_READ):
            size += len(chunk)
            digest.update(chunk)
        if size > max_bytes:
            raise api_error(
                413,
                "IMPORT_TOO_LARGE",
                f"The file has {size} bytes; an import takes at most {max_bytes}",
                {"setting": "IMPORT_MAX_BYTES", "maximum": max_bytes, "bytes": size},
            )
        file.seek(0)
        return cls(name, file, size, digest.hexdigest())


def file_format(request: ImportRequest, upload: Upload) -> str:
    """The request's ``format``, or the file name's suffix. A legacy ``.xls`` workbook is refused:
    convert it to XLSX first (A-D4)."""
    if request.format is not None:
        return request.format
    suffix = Path(upload.name).suffix.lower()
    if suffix in SUFFIXES:
        return SUFFIXES[suffix]
    hint = " Save it as XLSX first." if suffix == ".xls" else ""
    raise api_error(
        422,
        "UNSUPPORTED_FILE_FORMAT",
        f"An import reads XLSX, CSV and JSON Lines files; '{upload.name}' is none of them.{hint} "
        "Name the format in the request when the file name does not say it",
        {"fileName": upload.name},
    )


def submit_import(
    session: Session,
    request: ImportRequest,
    upload: Upload,
    *,
    files: JobFiles,
    idempotency_key: str | None,
    retention_days: int,
    origin: dict[str, Any] | None = None,
) -> tuple[Job, bool]:
    """Queue the import with its file and commit; or, for a key seen before, the job it queued.
    ``True`` marks a replayed job."""
    fingerprint = request_fingerprint(
        {"request": request.model_dump(mode="json", exclude_unset=True), "file": upload.sha256}
    )
    if idempotency_key is not None:
        replayed = replayed_job(
            session,
            scope=IMPORTS_SCOPE,
            workspace_key=_workspace_key(session, request),
            key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed, True
    found_format = file_format(request, upload)
    context = open_batch_context(session, request)
    if (
        context.change_set is not None
        and context.change_set.version != request.expectedChangeSetVersion
    ):
        raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")
    profile = _profile(session, request, context.model, found_format, upload, origin)
    if context.change_set is None and _deletes_missing(profile):
        raise api_error(
            422,
            "MISSING_DELETE_NEEDS_CHANGE_SET",
            "The profile deletes the records missing from the file (missing: delete), which only "
            "a load into a change set may do; name a change set, or set the source's missing to "
            "report",
        )
    job = start_job(
        session,
        kind="import",
        workspace_key=context.workspace_key,
        change_set_id=context.change_set.id if context.change_set else None,
        model_release_id=context.model_release_id,
        parameters={
            "policy": request.policy,
            "run": "background",
            "onExisting": request.onExisting,
            "otherWorkspaceIds": request.otherWorkspaceIds,
            "stage": request.stage,
            "profile": profile,
            "file": {
                "name": upload.name,
                "format": found_format,
                "bytes": upload.size,
                "sha256": upload.sha256,
            },
            # The stored source file imported (0.10 A3), which a profile's check compares the
            # next version with (A5c, D83).
            **({"sourceFileId": request.sourceFileId} if request.sourceFileId else {}),
        },
        total=None,
        retention_days=retention_days,
        queued=True,
        change_set_version=request.expectedChangeSetVersion,
    )
    target = files.source(job.id)
    files.directory.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("wb") as copy:
            shutil.copyfileobj(upload.file, copy, _READ)
        if idempotency_key is not None:
            try:
                remember_key(
                    session,
                    scope=IMPORTS_SCOPE,
                    workspace_key=context.workspace_key,
                    key=idempotency_key,
                    fingerprint=fingerprint,
                    job=job,
                )
            except IntegrityError:
                # A concurrent request with the key committed first: answer as its retry.
                session.rollback()
                target.unlink(missing_ok=True)
                replayed = replayed_job(
                    session,
                    scope=IMPORTS_SCOPE,
                    workspace_key=context.workspace_key,
                    key=idempotency_key,
                    fingerprint=fingerprint,
                )
                if replayed is None:
                    raise
                return replayed, True
        session.commit()
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return job, False


def _profile(
    session: Session,
    request: ImportRequest,
    model: Any,
    found_format: str,
    upload: Upload,
    origin: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """The profile as the job will use it, checked against the context's release: a stored one
    with its key and version, the inline one, or the one a workbook for people carries (0.9 J6,
    D185) with what the workbook says it is; none for JSON Lines or an export's tables."""
    if request.profileKey is None and request.profile is None:
        carried = carried_profile(upload.file) if found_format == "xlsx" else None
        if carried is None:
            return None
        description, body = carried
        try:
            definition = ImportProfileDefinition.model_validate(body)
        except ValidationError:
            raise unreadable(
                f"The workbook's sheet '{PROFILE_SHEET}' holds no import profile this engine "
                "reads; export the workbook again, or name a profile"
            ) from None
        problems = check_profile(model, definition)
        if problems:
            raise invalid_profile(problems)
        return {
            "key": None,
            "version": None,
            "embedded": description,
            "definition": definition.model_dump(mode="json", exclude_none=True),
        }
    if found_format == "jsonl":
        raise api_error(
            422,
            "UNSUPPORTED_FILE_FORMAT",
            "A JSON Lines file holds batch items and is imported without a profile",
            {"format": found_format},
        )
    if request.profileKey is not None:
        stored = load_profile(session, request.profileKey)
        require_model(session, stored, model)
        definition = parsed(stored)
        described = {"key": stored.key, "version": stored.version}
    else:
        definition = ImportProfileDefinition.model_validate(
            request.profile.model_dump(include={"csv", "sources", "valueMaps"}, exclude_none=True)
        )
        # What the profile came from, kept when a preview is read again with other fields.
        described = {"key": None, "version": None, **(origin or {})}
    problems = check_profile(model, definition)
    if problems:
        raise invalid_profile(problems)
    return {
        **described,
        "definition": definition.model_dump(mode="json", exclude_none=True),
    }


def _deletes_missing(profile: dict[str, Any] | None) -> bool:
    """Whether a source of the profile deletes the records missing from the file (D82)."""
    if profile is None:
        return False
    return any(source.get("missing") == "delete" for source in profile["definition"]["sources"])


def _workspace_key(session: Session, request: ImportRequest) -> str:
    """The workspace an idempotency key is scoped to, read without the write's checks, so a
    finished job is answered again even if its workspace has since been retired."""
    check_batch_context(request)
    if request.changeSetId is None:
        return request.workspaceKey
    workspace_key = session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == str(request.changeSetId))
    )
    if workspace_key is None:
        raise api_error(
            404, "CHANGE_SET_NOT_FOUND", f"Change set '{request.changeSetId}' not found"
        )
    return workspace_key
