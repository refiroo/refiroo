"""Import profiles and imports (Base 0.9 J2, INTEGRATION_API §J1–§J3).

``write_router`` saves profiles and starts imports and is registered only with
``INTEGRATION_JOBS_ENABLED`` (D10); ``router`` reads profiles and is always registered. An import's
progress and outcomes are the job routes' (``jobs.py``).
"""

from contextlib import nullcontext
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Header, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Json
from sqlalchemy.orm import Session

from ...engine.imports.loads import last_loads
from ...engine.imports.profiles import (
    create_profile,
    delete_profile,
    profile_page,
    read_profile,
    stored_page,
    update_profile,
)
from ...engine.imports.submit import Upload, submit_import
from ...engine.jobs.inline import BatchLimits
from ...engine.sources.profile_check import latest_check, submit_check
from ...engine.sources.store import stored_upload
from ...errors import api_error
from ...models.database import Job
from ...models.imports import ImportProfileCreate, ImportProfileUpdate, ImportRequest
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import import_profile_page, import_profile_response, job_responses
from ..projections.job_rows import job_row_page
from ..projections.profile_check import check_response, finding_page
from ..schemas.imports import (
    CheckDriftPage,
    CheckMissingRecordPage,
    CheckNewValuePage,
    ImportProfilePage,
    ImportProfileResponse,
    ProfileCheckResponse,
)
from ..schemas.jobs import JobResponse, JobRowPage

router = APIRouter(prefix="/api/v1", tags=["imports"])
write_router = APIRouter(prefix="/api/v1", tags=["imports"])


@router.get("/import-profiles", response_model=ImportProfilePage)
def list_import_profiles(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> ImportProfilePage:
    """Import profiles in key order, each read under the active model release, with its last load
    (0.10 A5c)."""
    page = profile_page(session, paging, page_size)
    loads = last_loads(session, [profile.key for profile in page.items])
    return import_profile_page(stored_page(session, page.items), page, loads)


@router.get("/import-profiles/{profile_key}", response_model=ImportProfileResponse)
def get_import_profile(profile_key: str, session: DbSession) -> ImportProfileResponse:
    """A profile, with ``valid`` and ``problems`` under the active model release, and its last
    load: the latest import naming it and what became of what it loaded (0.10 A5c)."""
    found = read_profile(session, profile_key)
    return import_profile_response(found, last_loads(session, [found.profile.key]).get(profile_key))


@write_router.post("/import-profiles", response_model=ImportProfileResponse, status_code=201)
def create_import_profile(
    payload: ImportProfileCreate, session: DbSession
) -> ImportProfileResponse:
    """Save a profile: how a file's sheets and columns become records and relationships. It is
    checked against the active model release, and refused with every problem at its JSON pointer
    (``422 INVALID_IMPORT_PROFILE``); ``409 IMPORT_PROFILE_EXISTS`` for a key in use."""
    return import_profile_response(create_profile(session, payload))


@write_router.put("/import-profiles/{profile_key}", response_model=ImportProfileResponse)
def update_import_profile(
    profile_key: str, payload: ImportProfileUpdate, session: DbSession
) -> ImportProfileResponse:
    """Replace a profile at ``expectedVersion`` (``409 IMPORT_PROFILE_VERSION_CONFLICT`` naming
    the current version otherwise); checked as a new one is."""
    found = update_profile(session, profile_key, payload)
    return import_profile_response(found, last_loads(session, [found.profile.key]).get(profile_key))


@write_router.delete("/import-profiles/{profile_key}", status_code=204)
def delete_import_profile(
    profile_key: str,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> Response:
    delete_profile(session, profile_key, expected_version)
    return Response(status_code=204)


@write_router.post(
    "/imports",
    response_model=JobResponse,
    status_code=202,
    responses={
        202: {
            "description": "The queued import: follow it at GET /jobs/{jobId}",
            "headers": {
                "Idempotent-Replayed": {
                    "description": "true when the job is an earlier request's, answered again "
                    "for the same Idempotency-Key",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
def create_import(
    request: Request,
    session: DbSession,
    payload: Annotated[
        Json[ImportRequest],
        Form(
            alias="request",
            description="The import request as JSON: the context (workspaceKey, or changeSetId "
            "with expectedChangeSetVersion), profileKey or an inline profile (neither for JSON "
            "Lines or an export's tables), format, policy, onExisting and stage; sourceFileId "
            "to import a stored source file in place of the file part",
        ),
    ],
    file: Annotated[
        UploadFile | None,
        File(
            description="The XLSX, CSV or JSON Lines file; none when the request names "
            "sourceFileId"
        ),
    ] = None,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
        pattern=r"^[\x20-\x7e]+$",
        description="Answer a retry of the same request and file with the first job",
    ),
) -> JSONResponse:
    """Import a file as a background job (0.9 J2).

    Answers 202 with the queued job (``kind: import``). The worker binds the file, then runs its
    items as a background batch: each item's outcome names its sheet and row in ``ref``, and a row
    that cannot be bound (a value that does not convert, a match finding no record or several, a
    key repeated with other values) is rejected with the column. Under ``atomic`` such a row stops
    the import before anything is written. A file that does not fit the profile fails the job with
    every problem (``IMPORT_FILE_MISMATCH``). ``sourceFileId`` imports a stored source file (0.10
    A3) instead of a file part. Refused before a job is stored: ``413
    IMPORT_TOO_LARGE``, ``422 UNSUPPORTED_FILE_FORMAT``, ``422 INVALID_IMPORT_PROFILE`` and the
    context's codes.
    """
    limits: BatchLimits = request.app.state.batch_limits
    files = request.app.state.job_files
    if (file is None) == (payload.sourceFileId is None):
        raise api_error(
            422,
            "REQUEST_VALIDATION_ERROR",
            "Send the file part or name a stored source file in sourceFileId, not both",
            [{"loc": ["body", "file"], "msg": "file or request.sourceFileId, exactly one"}],
        )
    with (
        stored_upload(
            session, payload.sourceFileId, files=files, max_bytes=limits.import_max_bytes
        )
        if file is None
        else nullcontext(Upload.read(file.filename or "", file.file, limits.import_max_bytes))
    ) as upload:
        job, replayed = submit_import(
            session,
            payload,
            upload,
            files=files,
            idempotency_key=idempotency_key,
            retention_days=limits.retention_days,
        )
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return JSONResponse(
        job_responses(session, [job])[0].model_dump(mode="json"),
        status_code=202,
        headers={"Idempotent-Replayed": "true"} if replayed else None,
    )


# --- a profile's check of its next file (0.10 A5c, D83) ------------------------------------------


@router.get("/import-profiles/{profile_key}/check", response_model=ProfileCheckResponse)
def get_profile_check(profile_key: str, session: DbSession) -> ProfileCheckResponse:
    """The check of the profile's latest file (D83): ``checking``, then the columns new, missing
    and renamed, the profile against the active release, what the load would do and the counts of
    new values, drifting names and records missing from the file; ``404 PROFILE_CHECK_NOT_FOUND``
    before the profile's first file is checked."""
    return check_response(_check(session, profile_key))


@write_router.post(
    "/import-profiles/{profile_key}/check", response_model=ProfileCheckResponse, status_code=202
)
def run_profile_check(profile_key: str, request: Request, session: DbSession) -> JSONResponse:
    """Check the profile's current file again, as after a change to the profile; a check still
    running is cancelled. Refused: ``404 SOURCE_FILE_NOT_FOUND`` when the profile holds no file,
    ``409 SOURCE_FILE_PROFILE_NOT_READY`` before it is profiled."""
    limits: BatchLimits = request.app.state.batch_limits
    job = submit_check(session, profile_key, retention_days=limits.retention_days)
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return JSONResponse(check_response(job).model_dump(mode="json", by_alias=True), status_code=202)


@router.get("/import-profiles/{profile_key}/check/new-values", response_model=CheckNewValuePage)
def list_check_new_values(
    profile_key: str,
    session: DbSession,
    paging: PageQuery,
    source: int | None = Query(default=None, ge=0, description="A source, in load order"),
    page_size: int = Query(default=100, ge=1, le=1000, alias="pageSize"),
) -> CheckNewValuePage:
    """Values of match columns naming no record, each with its cells: created by the load or
    refused, in source, column and value order."""
    found = finding_page(
        session, _check(session, profile_key), "newValues", source=source, page=paging,
        page_size=page_size,
    )
    return CheckNewValuePage(items=[row.value for row in found.items], **found.links())


@router.get("/import-profiles/{profile_key}/check/drift", response_model=CheckDriftPage)
def list_check_drift(
    profile_key: str,
    session: DbSession,
    paging: PageQuery,
    source: int | None = Query(default=None, ge=0, description="A source, in load order"),
    page_size: int = Query(default=100, ge=1, le=1000, alias="pageSize"),
) -> CheckDriftPage:
    """Rows whose key finds a record named otherwise, in source and row order."""
    found = finding_page(
        session, _check(session, profile_key), "drift", source=source, page=paging,
        page_size=page_size,
    )
    return CheckDriftPage(items=[row.value for row in found.items], **found.links())


@router.get(
    "/import-profiles/{profile_key}/check/missing-records", response_model=CheckMissingRecordPage
)
def list_check_missing_records(
    profile_key: str,
    session: DbSession,
    paging: PageQuery,
    source: int | None = Query(default=None, ge=0, description="A source, in load order"),
    page_size: int = Query(default=100, ge=1, le=1000, alias="pageSize"),
) -> CheckMissingRecordPage:
    """Records of a source's type no row names (D82), in source and name order: kept by a load,
    or deleted by one into a change set when the source says ``missing: delete``."""
    found = finding_page(
        session, _check(session, profile_key), "missingRecords", source=source, page=paging,
        page_size=page_size,
    )
    return CheckMissingRecordPage(items=[row.value for row in found.items], **found.links())


@router.get("/import-profiles/{profile_key}/check/rows", response_model=JobRowPage)
def list_check_rows(
    profile_key: str,
    session: DbSession,
    paging: PageQuery,
    source: int | None = Query(default=None, ge=0, description="A source, in load order"),
    status: Literal["applied", "rejected", "unprocessed"] | None = Query(default=None),
    code: str | None = Query(default=None, description="Rows with an outcome refused this code"),
    page_size: int = Query(default=500, ge=1, le=1000, alias="pageSize"),
) -> JobRowPage:
    """The rows behind the check's figures, as ``GET /model-drafts/{id}/dry-run/rows`` reads a
    dry run's."""
    return job_row_page(
        session,
        _check(session, profile_key),
        status=status,
        page=paging,
        page_size=page_size,
        source=source,
        code=code,
    )


def _check(session: Session, profile_key: str) -> Job:
    job = latest_check(session, profile_key)
    if job is None:
        raise api_error(
            404,
            "PROFILE_CHECK_NOT_FOUND",
            f"Import profile '{profile_key}' has no checked file yet; upload one with "
            "POST /source-files naming the profile as its owner",
        )
    return job
