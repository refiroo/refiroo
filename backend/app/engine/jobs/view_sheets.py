"""The workbooks of the views that are not a sheet per type (Base 0.17 EX1): a relation matrix
(``matrix_sheets``), a relationships table (one row per relationship) and a relationships grid
(``grid_sheets``). The other views (a table, a tree, a mapping grid) are sheets of their types
(``people.py``)."""

from ...models.exports import ExportRequest
from ...models.schema import (
    EngineModel,
    RelationMatrixViewDefinition,
    RelationTableViewDefinition,
    ViewDefinition,
)
from . import about
from .export_views import ViewExport
from .grid_sheets import GridSheets, RowsSheets
from .matrix_sheets import MatrixSheets
from .people import WorkbookPlan


def plan_view_workbook(
    model: EngineModel, request: ExportRequest, view: ViewExport | None
) -> WorkbookPlan | None:
    """The view's own workbook, planned against the model; ``None`` for a view that is a sheet per
    type."""
    if view is None:
        return None
    definition = view.definition
    if isinstance(definition, RelationMatrixViewDefinition):
        return WorkbookPlan(
            (),
            MatrixSheets(model, view, request.context.changeSetId, request.context.publicationId),
        )
    if isinstance(definition, RelationTableViewDefinition):
        sheets = GridSheets if definition.config.layout == "grid" else RowsSheets
        return WorkbookPlan(
            (), sheets(model, view, request.context.changeSetId, request.context.publicationId)
        )
    return None


def kind_words(definition: ViewDefinition) -> str:
    """The view's kind as the About sheet says it: "a matrix", "a matrix that links"."""
    if isinstance(definition, RelationMatrixViewDefinition):
        actions = set(definition.config.cellActions)
        if actions & {"link", "unlink"} and not actions & {"create"}:
            return "a matrix that links"
        if actions & {"link", "unlink"}:
            return "a matrix that creates and links"
        return "a matrix"
    if isinstance(definition, RelationTableViewDefinition) and definition.config.layout == "grid":
        return "a relationships grid"
    return about.KIND_WORDS[definition.type]
