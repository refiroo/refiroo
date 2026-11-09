"""Source files, their profiles and a draft's dry run, as the API answers them (Product 0.10 A3)."""

from typing import Any

from openpyxl.utils.cell import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...engine.sources.staged import cell_range, cell_rows
from ...engine.sources.store import profile_state, require_profile
from ...errors import api_error
from ...models.database import (
    Job,
    ModelDraft,
    SourceFile,
    SourceFileCell,
    SourceFileColumn,
    SourceFileSheet,
)
from ..schemas.sources import (
    DryRunResponse,
    SourceCellPage,
    SourceCellRow,
    SourceColumnPage,
    SourceColumnResponse,
    SourceFileOwnerResponse,
    SourceFilePage,
    SourceFileProfileState,
    SourceFileResponse,
    SourceSheetPage,
    SourceSheetResponse,
)

_SHEET_KEYS = (integer_key("index", SourceFileSheet.sheet_index, "sheet_index"),)
_COLUMN_KEYS = (
    integer_key("block", SourceFileColumn.block_index, "block_index"),
    integer_key("column", SourceFileColumn.column_number, "column_number"),
)


def source_file_response(session: Session, source: SourceFile) -> SourceFileResponse:
    draft_id = (
        session.scalar(select(ModelDraft.public_id).where(ModelDraft.id == source.draft_id))
        if source.draft_id is not None
        else None
    )
    return SourceFileResponse(
        id=source.public_id,
        name=source.name,
        format=source.format,
        bytes=source.bytes,
        sha256=source.sha256,
        owner=SourceFileOwnerResponse(draftId=draft_id, profileKey=source.profile_key),
        workspaceKey=source.workspace_key,
        csvDelimiter=source.csv_delimiter,
        uploadedAt=source.uploaded_at,
        supersededAt=source.superseded_at,
        version=source.version,
        profile=SourceFileProfileState(**profile_state(session, source)),
    )


def source_file_page(session: Session, page: Page[SourceFile]) -> SourceFilePage:
    return SourceFilePage(
        items=[source_file_response(session, item) for item in page.items], **page.links()
    )


def sheet_page(
    session: Session, source: SourceFile, page: PageRequest, page_size: int
) -> SourceSheetPage:
    """The file's profiled sheets in workbook order; ``409 SOURCE_FILE_PROFILE_NOT_READY`` until
    the profile is stored."""
    require_profile(session, source)
    found: Page[SourceFileSheet] = paginate_statement(
        session,
        select(SourceFileSheet).where(SourceFileSheet.source_file_id == source.id),
        keys=_SHEET_KEYS,
        scope="source-file-sheets",
        filters={"sourceFileId": source.public_id},
        page=page,
        page_size=page_size,
        message="Source file sheet cursor is invalid",
    )
    return SourceSheetPage(
        items=[
            SourceSheetResponse(index=item.sheet_index, name=item.name, **item.profile)
            for item in found.items
        ],
        **found.links(),
    )


def _sheet_index(session: Session, source: SourceFile, sheet: str) -> int:
    index = session.scalar(
        select(SourceFileSheet.sheet_index).where(
            SourceFileSheet.source_file_id == source.id, SourceFileSheet.name == sheet
        )
    )
    if index is None:
        raise api_error(
            404,
            "SOURCE_SHEET_NOT_FOUND",
            f"Source file '{source.public_id}' has no sheet '{sheet}'",
            {"sheet": sheet},
        )
    return index


def column_page(
    session: Session, source: SourceFile, sheet: str, page: PageRequest, page_size: int
) -> SourceColumnPage:
    """A sheet's profiled columns, block by block, each block's in column order (a column of a
    sheet laid out for reading may be in several blocks, 0.10 A8a)."""
    require_profile(session, source)
    index = _sheet_index(session, source, sheet)
    found: Page[SourceFileColumn] = paginate_statement(
        session,
        select(SourceFileColumn).where(
            SourceFileColumn.source_file_id == source.id, SourceFileColumn.sheet_index == index
        ),
        keys=_COLUMN_KEYS,
        scope="source-file-columns",
        filters={"sourceFileId": source.public_id, "sheet": sheet},
        page=page,
        page_size=page_size,
        message="Source file column cursor is invalid",
    )
    return SourceColumnPage(
        items=[SourceColumnResponse(sheet=sheet, **item.statistics) for item in found.items],
        **found.links(),
    )


_CELL_ROW_KEYS = (integer_key("row", SourceFileCell.row_number, "row_number"),)


def cell_page(
    session: Session, source: SourceFile, sheet: str, raw: str, page: PageRequest, page_size: int
) -> SourceCellPage:
    """The rows of a range of a sheet holding a cell, in row order, each with its cells by column
    letter (0.10 A8b, D124)."""
    require_profile(session, source)
    index = _sheet_index(session, source, sheet)
    area = cell_range(session, source.id, index, raw)
    found: Page[Any] = paginate_statement(
        session,
        cell_rows(source.id, index, area),
        keys=_CELL_ROW_KEYS,
        scope="source-file-cells",
        filters={"sourceFileId": source.public_id, "sheet": sheet, "range": raw},
        page=page,
        page_size=page_size,
        message="Source file cell cursor is invalid",
        rows=True,
    )
    return SourceCellPage(
        items=[
            SourceCellRow(
                row=item.row_number,
                cells={get_column_letter(int(number)): cell for number, cell in sorted(item.cells.items(), key=lambda pair: int(pair[0]))},
            )
            for item in found.items
        ],
        **found.links(),
    )


def dry_run_response(job: Job) -> DryRunResponse:
    parameters: dict[str, Any] = job.parameters
    report = job.report or {}
    summary = report.get("dryRun")
    return DryRunResponse(
        jobId=job.id,
        state="checking" if job.state in {"queued", "running"} else job.state,
        draftId=parameters["draftId"],
        draftVersion=parameters["draftVersion"],
        sourceFileId=parameters.get("sourceFileId"),
        workspaceKey=job.workspace_key,
        items=report.get("itemsDryRun"),
        summary=(
            {key: summary[key] for key in (
                "coverage", "rows", "sources", "difference", "previousJobId", "ranAt"
            )}
            if summary
            else None
        ),
        bindingReport=report.get("bindingReport"),
        error=job.error,
    )
