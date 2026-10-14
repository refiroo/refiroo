"""One rectangle of a sheet read as a list on the administrator's request (Product 0.10 A8b, D128).

A list the inference left out (a free field, a header read as a title, a list dropped) is loaded by
asking for its rectangle: it is read by A8a's rules for a list (``patterns.list_block``,
``Builder.list_proposal``) against the draft as it is now, and the proposal is answered, not
stored. The editor sends its operations to ``POST …/operations``, so the list is the
administrator's. The rectangle's column statistics are one statement over the staged cells, so the
answer needs no job.
"""

from typing import Any

from openpyxl.utils.cell import column_index_from_string
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....errors import api_error
from ....models.database import SourceFileSheet
from ....models.sources import ListProposalRequest
from ...model.authoring.released import base_release, released_atoms
from ...model.drafts import load_draft
from ..draft_profile import current_source
from ..profiling import rectangle_columns
from ..staged import cell_range
from ..store import require_profile
from .build import Builder
from .facts import block_tables
from .patterns import list_block


class _OneList:
    """The workbook a single list is built against: no table sheets, no shared columns."""

    sheets: tuple[Any, ...] = ()
    blocks: tuple[Any, ...] = ()

    def common(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        return 0


def propose_list(session: Session, draft_id: str, request: ListProposalRequest) -> dict[str, Any]:
    """The list proposal for a rectangle of the draft's current file: its pattern, sheet, columns,
    summary, evidence, operations and alternatives. Refused ``404 SOURCE_FILE_NOT_FOUND`` (no file),
    ``409 SOURCE_FILE_PROFILE_NOT_READY``, ``404 SOURCE_SHEET_NOT_FOUND`` and ``422 INVALID_RANGE``
    for a rectangle that is not one, or holds no value under its header."""
    draft = load_draft(session, draft_id)
    source = current_source(session, draft)
    if source is None:
        raise api_error(404, "SOURCE_FILE_NOT_FOUND", f"Model draft '{draft_id}' has no source file")
    require_profile(session, source)
    sheet = session.scalar(
        select(SourceFileSheet).where(SourceFileSheet.source_file_id == source.id, SourceFileSheet.name == request.sheet)
    )
    if sheet is None:
        raise api_error(404, "SOURCE_SHEET_NOT_FOUND", f"Source file '{source.public_id}' has no sheet '{request.sheet}'", {"sheet": request.sheet})
    block = request.block
    last_row = block.lastRow or request.headerRow
    raw = f"{block.firstColumn}{request.headerRow}:{block.lastColumn}{last_row}"
    cell_range(session, source.id, sheet.sheet_index, raw)
    first, last = column_index_from_string(block.firstColumn), column_index_from_string(block.lastColumn)
    described, columns = rectangle_columns(session, source.id, sheet.sheet_index, first, last, request.headerRow, last_row)
    tables = block_tables(session, source.id, sheet, [described], columns)
    if not tables or not tables[0].columns or not tables[0].columns[0].filled:
        raise api_error(
            422,
            "INVALID_RANGE",
            f"'{raw}' holds no value under its header to load as a list",
            {"range": raw, "path": "/block"},
        )
    table = tables[0]
    finding = list_block(table, asked=True)
    profile = draft.profile_json or {}
    base = base_release(session, draft)
    builder = Builder(
        draft.model_json,
        profile,
        _OneList(),
        mode="extend",
        file_name=source.name,
        application_key=request.applicationKey,
        application_name=None,
        reuse={},
        released=released_atoms(base.model_json if base else None).__contains__,
    )
    proposal = builder.list_proposal(finding, _application(draft.model_json, profile, request), _translations(profile)) if finding else None
    if proposal is None:
        raise api_error(422, "INVALID_RANGE", f"'{raw}' is not a list", {"range": raw, "path": "/block"})
    body = proposal.body()
    return {name: body[name] for name in ("pattern", "sheet", "columns", "summary", "evidence", "operations", "alternatives")}


def _application(model: dict[str, Any], profile: dict[str, Any], request: ListProposalRequest) -> str | None:
    """Where the new list goes: the application named, else the one the sheet's sources load into
    most, else the model's first."""
    if request.applicationKey:
        if not any(a.get("key") == request.applicationKey for a in model.get("applications") or []):
            raise api_error(
                422,
                "INVALID_INFERENCE_REQUEST",
                f"The draft has no application '{request.applicationKey}'",
                {"pointer": "/applicationKey"},
            )
        return request.applicationKey
    counts: dict[str, int] = {}
    for source in profile.get("sources") or []:
        if source.get("sheet") == request.sheet and source.get("applicationKey"):
            counts[source["applicationKey"]] = counts.get(source["applicationKey"], 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return (model.get("applications") or [{}])[0].get("key")


def _translations(profile: dict[str, Any]) -> tuple[str, str] | None:
    """The draft's language list and translation type, as its profile's translations name them."""
    for source in profile.get("sources") or []:
        for binding in source.get("columns") or []:
            related = binding.get("relatedRecord") or {}
            language = (related.get("parent") or {}).get("objectTypeKey")
            if language and related.get("objectTypeKey"):
                return language, related["objectTypeKey"]
    return None
