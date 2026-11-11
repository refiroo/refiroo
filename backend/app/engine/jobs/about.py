"""The "About this export" sheet's content (0.17 EX1, PP-D22): one writer's input for every XLSX
export, so a file says what it holds in the same words and order whatever its layout.

The sections are the same for every layout: what was exported, what it holds, how it loads back,
and the layout's own part where it has one (a matrix's containers). The sheet is written by
:meth:`xlsx.Workbook.about`; this module decides its words.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import ChangeSet, Publication
from ...models.exports import ExportRequest
from ...models.schema import EngineModel
from . import xlsx

Rows = list[tuple[str, str, str | None]]

KIND_WORDS = {
    "table": "a table",
    "tree": "a tree",
    "relationMatrix": "a matrix",
    "mappingGrid": "a mapping grid",
    "relationTable": "a relationships table",
}


@dataclass
class AboutFacts:
    """What the export was asked for and read from, as a person words it."""

    workspace_key: str
    application: str | None
    view: str | None
    scope: str | None
    read_from: str
    filters: str
    exported_at: datetime
    job_id: str
    as_of: str | None = None


def read_from(session: Session, request: ExportRequest) -> str:
    """The context the file was read from, named as the person knows it."""
    if request.context.changeSetId is not None:
        name = session.scalar(
            select(ChangeSet.name).where(ChangeSet.id == request.context.changeSetId)
        )
        return (
            f"Change set “{name}” ({request.context.changeSetId})"
            if name
            else (f"Change set {request.context.changeSetId}")
        )
    if request.context.publicationId is not None:
        number = session.scalar(
            select(Publication.publication_number).where(
                Publication.id == request.context.publicationId
            )
        )
        return f"Publication {number}" if number is not None else "A publication"
    return "Live data"


def title_and_sentence(
    facts: AboutFacts, *, technical: bool, grouped: bool, view_kind: str | None
) -> tuple[str, str]:
    """The sheet's title and its one sentence."""
    if technical:
        return (
            facts.scope or "Technical export",
            (
                "The engine's technical tables, for systems and full copies: the Records and"
                " Relationships sheets hold the data, and an import reads them back as they are."
                " This sheet is ignored by an import."
            ),
        )
    if view_kind is not None and facts.view:
        return (
            facts.view,
            "The view as it was shown, ready to edit in a spreadsheet and import back. "
            + (
                "The first sheet holds the data."
                if grouped
                else "Each sheet holds the records of one type, or one kind of relationship."
            ),
        )
    return (
        facts.scope or "Export",
        (
            "The records as they stood, ready to edit in a spreadsheet and import back. Each sheet"
            " holds one type."
        ),
    )


def sections(
    facts: AboutFacts, holds: Rows, loads: Rows, extra: list[tuple[str, Rows]]
) -> list[xlsx.AboutSection]:
    """The sheet's sections, in their one order."""
    source: Rows = []
    if facts.application:
        source.append(("Application", facts.application, None))
    if facts.view:
        source.append(("View", facts.view, None))
    if facts.scope and not facts.view:
        source.append(("Scope", facts.scope, None))
    source += [
        ("Workspace", facts.workspace_key, None),
        ("Read from", facts.read_from, None),
        ("Search and filters", facts.filters, None),
    ]
    if facts.as_of:
        source.append(("Valid on", facts.as_of, None))
    source += [
        ("Exported", facts.exported_at.strftime("%Y-%m-%d %H:%M"), None),
        ("Export job", facts.job_id, None),
    ]
    found = [
        xlsx.AboutSection("What was exported", source),
        xlsx.AboutSection("What it holds", holds),
        xlsx.AboutSection("How it loads back", loads),
    ]
    found += [xlsx.AboutSection(title, rows) for title, rows in extra]
    return found


def describe_filters(
    model: EngineModel, search: str | None, criteria: list[object], extra: list[str]
) -> str:
    """The page's search and filters in words: "None" when nothing narrowed it."""
    parts = []
    if search:
        parts.append(f"Search “{search}”")
    for item in criteria:
        text = _criterion(model, item)
        if text:
            parts.append(text)
    parts += extra
    return "; ".join(parts) if parts else "None"


def _criterion(model: EngineModel, item: object) -> str:
    field = getattr(item, "field", None)
    op = getattr(item, "op", None)
    value = getattr(item, "value", None)
    related = getattr(item, "related", None)
    if related is not None:
        relation = model.relation_type(related.relationTypeKey)
        name = relation.name if relation is not None else related.relationTypeKey
        inner = ", ".join(_criterion(model, nested) for nested in related.where)
        prefix = "No " if getattr(item, "not_", False) else "Any "
        return f"{prefix}{name}" + (f" ({inner})" if inner else "")
    if field is None:
        return ""
    attribute = model.attribute_type(field)
    label = attribute.name if attribute is not None else field
    words = {
        "eq": "is",
        "neq": "is not",
        "contains": "contains",
        "startsWith": "starts with",
        "isNull": "is empty" if value in (True, "true") else "is set",
        "isUnset": "is empty" if value in (True, "true") else "is set",
    }.get(str(op), str(op))
    if op in ("isNull", "isUnset"):
        return f"{label} {words}"
    return f"{label} {words} {value}"
