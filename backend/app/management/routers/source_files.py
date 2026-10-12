"""Source files and a model draft's dry run (Product 0.10 A3, D5, D6, D65–D71).

``router`` reads source files and their profiles and is always registered; ``write_router``
uploads and deletes them and is registered only with ``INTEGRATION_JOBS_ENABLED`` (D6).
``dry_run_router`` runs and reads a draft's dry run and is registered only when model
administration and integration jobs are both enabled: it reads a draft and runs a job.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Json
from sqlalchemy.orm import Session

from ...engine.imports.submit import Upload
from ...engine.jobs.inline import BatchLimits
from ...engine.sources.dry_run import InvalidDraft, latest_dry_run, submit_dry_run
from ...engine.sources.store import (
    delete_source_file,
    load_source_file,
    store_source_file,
)
from ...engine.sources.store import source_file_page as read_source_files
from ...errors import api_error
from ...models.database import Job
from ...models.sources import DryRunRequest, SourceFileRequest
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import diagnostic_details
from ..projections.job_rows import job_row_page
from ..projections.source_files import (
    column_page,
    dry_run_response,
    sheet_page,
    source_file_page,
    source_file_response,
)
from ..schemas.jobs import JobRowPage
from ..schemas.sources import (
    DryRunResponse,
    SourceColumnPage,
    SourceFilePage,
    SourceFileResponse,
    SourceSheetPage,
)

router = APIRouter(prefix="/api/v1", tags=["source files"])
write_router = APIRouter(prefix="/api/v1", tags=["source files"])
dry_run_router = APIRouter(prefix="/api/v1", tags=["model administration"])


def _wake_worker(request: Request) -> None:
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()


@write_router.post("/source-files", response_model=SourceFileResponse, status_code=201)
def create_source_file(
    request: Request,
    session: DbSession,
    file: Annotated[UploadFile, File(description="The XLSX workbook or CSV file")],
    payload: Annotated[
        Json[SourceFileRequest],
        Form(
            alias="request",
            description="The request as JSON: owner ({draftId} or {profileKey}), format, csv "
            "(delimiter) and workspaceKey, whose records the profile compares the columns with",
        ),
    ],
) -> SourceFileResponse:
    """Store a file for a model draft or an import profile and profile it (0.10 A3).

    Answers 201 with the file and its profile's job (``kind: profile``); the profile is read at
    ``GET /source-files/{id}/profile/sheets`` once the job completed. The owner's earlier file is
    superseded and deleted ``JOB_RETENTION_DAYS`` later. Refused: ``413 IMPORT_TOO_LARGE`` over
    ``IMPORT_MAX_BYTES``, ``422 UNSUPPORTED_FILE_FORMAT`` for a file that is neither XLSX nor CSV,
    ``404`` for an unknown owner or workspace.
    """
    limits: BatchLimits = request.app.state.batch_limits
    upload = Upload.read(file.filename or "", file.file, limits.import_max_bytes)
    source = store_source_file(
        session,
        payload,
        upload,
        files=request.app.state.job_files,
        retention_days=limits.retention_days,
    )
    _wake_worker(request)
    return source_file_response(session, source)


@router.get("/source-files", response_model=SourceFilePage)
def list_source_files(
    session: DbSession,
    paging: PageQuery,
    draft_id: str | None = Query(default=None, alias="draftId"),
    profile_key: str | None = Query(default=None, alias="profileKey"),
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SourceFilePage:
    """Source files, newest first: a draft's, a profile's, or all."""
    page = read_source_files(
        session,
        draft_public_id=draft_id,
        profile_key=profile_key,
        page=paging,
        page_size=page_size,
    )
    return source_file_page(session, page)


@router.get("/source-files/{source_file_id}", response_model=SourceFileResponse)
def get_source_file(source_file_id: str, session: DbSession) -> SourceFileResponse:
    return source_file_response(session, load_source_file(session, source_file_id))


@write_router.delete("/source-files/{source_file_id}", status_code=204)
def remove_source_file(
    source_file_id: str,
    request: Request,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> Response:
    """Delete the file, its staged cells and its profile (``409 VERSION_CONFLICT`` at another
    version)."""
    delete_source_file(
        session, source_file_id, expected_version, files=request.app.state.job_files
    )
    return Response(status_code=204)


@router.get("/source-files/{source_file_id}/profile/sheets", response_model=SourceSheetPage)
def list_source_sheets(
    source_file_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SourceSheetPage:
    """The file's sheets in workbook order, each with its rows, header row and blocks (D68);
    ``409 SOURCE_FILE_PROFILE_NOT_READY`` with the profile's state until it is stored."""
    return sheet_page(session, load_source_file(session, source_file_id), paging, page_size)


@router.get(
    "/source-files/{source_file_id}/profile/sheets/{sheet}/columns",
    response_model=SourceColumnPage,
)
def list_source_columns(
    source_file_id: str,
    sheet: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> SourceColumnPage:
    """A sheet's columns in column order with their statistics (D68–D70); ``404
    SOURCE_SHEET_NOT_FOUND`` for a sheet the file does not have."""
    source = load_source_file(session, source_file_id)
    return column_page(session, source, sheet, paging, page_size)


@dry_run_router.post(
    "/model-drafts/{draft_id}/dry-run", response_model=DryRunResponse, status_code=202
)
def run_dry_run(
    draft_id: str, payload: DryRunRequest, request: Request, session: DbSession
) -> JSONResponse:
    """Run the import of one of the draft's source files against the draft's model, writing
    nothing (D65–D67).

    Answers 202 with the dry run ``checking``; ``GET /model-drafts/{id}/dry-run`` reads it, with
    its summary of every row once completed. A dry run still running for the draft is cancelled.
    Refused: ``422 INVALID_MODEL`` for a draft that does not compile (D71), ``422
    INVALID_IMPORT_PROFILE`` for a profile the draft's model does not fit, ``404
    SOURCE_FILE_NOT_FOUND`` for a file the draft does not own, ``409
    SOURCE_FILE_PROFILE_NOT_READY`` before the file is profiled.
    """
    limits: BatchLimits = request.app.state.batch_limits
    try:
        job = submit_dry_run(session, draft_id, payload, retention_days=limits.retention_days)
    except InvalidDraft as invalid:
        raise api_error(
            422,
            "INVALID_MODEL",
            "Model draft is invalid; a dry run needs a draft that compiles",
            diagnostic_details(invalid.diagnostics),
        ) from None
    _wake_worker(request)
    return JSONResponse(dry_run_response(job).model_dump(mode="json"), status_code=202)


@dry_run_router.get("/model-drafts/{draft_id}/dry-run", response_model=DryRunResponse)
def get_dry_run(draft_id: str, session: DbSession) -> DryRunResponse:
    """The draft's latest dry run: ``checking``, or finished with its summary (``404
    DRY_RUN_NOT_FOUND`` before the first)."""
    return dry_run_response(_latest(session, draft_id))


@dry_run_router.get("/model-drafts/{draft_id}/dry-run/rows", response_model=JobRowPage)
def list_dry_run_rows(
    draft_id: str,
    session: DbSession,
    paging: PageQuery,
    source: int | None = Query(default=None, ge=0, description="A source, in load order"),
    status: Literal["applied", "rejected", "unprocessed"] | None = Query(default=None),
    code: str | None = Query(default=None, description="Rows with an outcome refused this code"),
    page_size: int = Query(default=500, ge=1, le=1000, alias="pageSize"),
) -> JobRowPage:
    """The rows behind the latest dry run's figures, in source then row order, as ``GET
    /jobs/{id}/rows`` reads an import's."""
    return job_row_page(
        session,
        _latest(session, draft_id),
        status=status,
        page=paging,
        page_size=page_size,
        source=source,
        code=code,
    )


def _latest(session: Session, draft_id: str) -> Job:
    job = latest_dry_run(session, draft_id)
    if job is None:
        raise api_error(
            404, "DRY_RUN_NOT_FOUND", f"Model draft '{draft_id}' has no dry run yet"
        )
    return job
