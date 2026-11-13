"""An export that names a view (Base 0.17 EX1, PP-D18).

``POST /exports`` with ``view`` gives the file the page showing that view gives: the engine derives
the records, and the workbook's shape, from the view's definition and the state the page was
narrowed to. This module reads the definition and the state into an ordinary request
(:func:`effective_request`: a scope of types with criteria, a layout, columns) and the predicates the
state adds that criteria cannot say (:func:`row_predicates`: the page's search, a matrix's cell
state, a mapping's coverage state). A matrix, a relationships table and a relationships grid have
sheets of their own (``view_sheets.py``); every other view is a sheet per type
(``people.py``).

Nothing here names a type, relation or application: the view's definition says which.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from ...models.exports import (
    ExportRequest,
    ExportScope,
    ExportType,
    ExportViewState,
    PeopleLayout,
)
from ...models.queries import QueryCriterion
from ...models.schema import (
    EngineModel,
    MappingGridViewDefinition,
    RelationMatrixViewDefinition,
    RelationTableViewDefinition,
    TableViewDefinition,
    TreeViewDefinition,
    ViewDefinition,
)
from ..model.candidate_places import identifying_fields
from ..model.registry import ModelSnapshot
from ..reads.context_sets import record_source, relation_source
from ..reads.matrix_read import build_matrix_read, state_filter
from ..reads.object_query import build_object_query
from ..reads.snapshot_reads import SnapshotContext, build_snapshot_object_query
from .people import invalid_layout, is_identifying

# The state parts each kind of view reads; the others are refused at their pointer.
_READS: dict[str, frozenset[str]] = {
    "table": frozenset({"search", "where", "parentObjectId", "columns"}),
    "tree": frozenset({"search", "parentObjectId"}),
    "relationMatrix": frozenset({"search", "where", "parentObjectId", "columnIds", "cellState"}),
    "mappingGrid": frozenset({"search", "where", "parentObjectId", "mappingState"}),
    "relationTable": frozenset({"search", "where", "toWhere", "toSearch", "columnIds"}),
}


@dataclass(frozen=True)
class ViewExport:
    """The view an export names, found in the model."""

    application_key: str
    definition: ViewDefinition
    state: ExportViewState
    cell_field: str | None

    @property
    def kind(self) -> str:
        return self.definition.type


def resolve_view(model: EngineModel, request: ExportRequest) -> ViewExport | None:
    """The request's view found in the model, its state checked against what that kind reads."""
    if request.view is None:
        return None
    named = request.view
    application = next(
        (item for item in model.applications if item.key == named.applicationKey), None
    )
    if application is None:
        raise invalid_layout(
            f"Unknown application '{named.applicationKey}'", "/view/applicationKey"
        )
    definition = next((item for item in application.views if item.key == named.viewKey), None)
    if definition is None:
        raise invalid_layout(
            f"Application '{application.key}' has no view '{named.viewKey}'", "/view/viewKey"
        )
    kind = definition.type
    shown = named.state.model_dump(exclude_defaults=True, exclude_none=True)
    for part in shown:
        if part not in _READS[kind]:
            raise invalid_layout(
                f"A view of this kind ({kind}) does not read '{part}'", f"/view/state/{part}"
            )
    if named.state.cellState is not None and not named.state.columnIds:
        raise invalid_layout(
            "A cell state applies to the columns named by columnIds", "/view/state/cellState"
        )
    grid = kind == "relationTable" and definition.config.layout == "grid"
    if named.state.columnIds and kind == "relationTable" and not grid:
        raise invalid_layout(
            "Columns apply to a relationships grid, not to its rows", "/view/state/columnIds"
        )
    if named.cellField is not None:
        links = kind == "relationMatrix" and bool(
            set(definition.config.cellActions) & {"link", "unlink"}
        )
        if not links:
            raise invalid_layout(
                "The field a cell lists applies to a matrix whose cells link records",
                "/view/cellField",
            )
        cell_type = definition.config.cellObjectTypeKey
        choices = identifying_fields(model, cell_type)
        if named.cellField not in choices:
            raise invalid_layout(
                f"'{named.cellField}' does not identify a '{cell_type}' record; choose one of"
                f" {', '.join(choices)}",
                "/view/cellField",
            )
    return ViewExport(application.key, definition, named.state, named.cellField)


def tree_types(model: EngineModel, definition: TreeViewDefinition) -> list[str]:
    """The tree's node types, in the model's order."""
    return [item.key for item in model.objectTypes if item.key in definition.config.objectTypeKeys]


def mapping_columns(model: EngineModel, definition: MappingGridViewDefinition) -> PeopleLayout:
    """A mapping grid as a table of its sources: the source columns, then the mapped target (by its
    display field where that finds one record, by name otherwise) as a relation column."""
    config = definition.config
    outgoing = config.direction == "outgoing"
    relation = model.relation_type(config.relationTypeKey)
    key = relation.key if outgoing else relation.reverseKey
    target = config.toObjectTypeKey if outgoing else config.fromObjectTypeKey
    chosen = next(
        (
            column
            for column in config.targetDisplayColumns
            if column != "name" and is_identifying(model, (target,), column)
        ),
        None,
    )
    mapped = f"related:{key}"
    layout = PeopleLayout(
        columns=[*dict.fromkeys(config.sourceColumns), mapped],
        columnFields={mapped: chosen} if chosen else {},
        referenceLists=[key],
    )
    # The grid maps to one type: the column edits the relationships to it, and lists its records.
    layout._targets = {mapped: target}
    return layout


def effective_request(
    model: EngineModel, request: ExportRequest, view: ViewExport | None
) -> ExportRequest:
    """The request a view stands for: its scope of types with the page's criteria, its layout and its
    columns. A request without a view is as it was sent."""
    if view is None:
        return request
    state, definition = view.state, view.definition
    layout = request.layout or "people"
    if view.kind != "table" and layout != "people":
        raise invalid_layout(
            "This kind of view is exported for editing (layout people); a table is also offered"
            " as the technical tables",
            "/layout",
        )
    parent = (
        [QueryCriterion(field="parentObjectId", op="eq", value=state.parentObjectId)]
        if state.parentObjectId and view.kind != "tree"
        else []
    )
    where = [*state.where, *parent]
    people = request.people
    types: list[str]
    config = definition.config
    below: str | None = None
    if isinstance(definition, TableViewDefinition):
        types = [definition.objectTypeKey]
        if layout == "people":
            columns = state.columns or (list(people.columns) if people and people.columns else None)
            people = (people or PeopleLayout()).model_copy(
                update={"columns": columns or list(config.columns)}
            )
    elif isinstance(definition, TreeViewDefinition):
        types, where, below = tree_types(model, definition), [], state.parentObjectId
    elif isinstance(definition, MappingGridViewDefinition):
        types = [
            config.fromObjectTypeKey if config.direction == "outgoing" else config.toObjectTypeKey
        ]
        people = mapping_columns(model, definition)
    elif isinstance(definition, RelationMatrixViewDefinition):
        types = [config.rowObjectTypeKey]
    else:
        types = [config.fromObjectTypeKey]
    scope = ExportScope(
        types=[ExportType(objectTypeKey=key, where=list(where)) for key in types],
        parentObjectId=below,
    )
    return request.model_copy(update={"scope": scope, "layout": layout, "people": people})


# --- what the page's state adds to the criteria ---------------------------------------------------

Predicate = Callable[[Any], Any]


def row_predicates(
    session: Session,
    snapshot: ModelSnapshot,
    request: ExportRequest,
    view: ViewExport,
    *,
    workspace_key: str,
    context: SnapshotContext | None,
) -> dict[str, list[Predicate]]:
    """Predicates on a record's ID, by type, for the state criteria cannot say: the page's search,
    a matrix's cell state and a mapping's coverage state."""
    state, definition, model = view.state, view.definition, snapshot.model
    found: dict[str, list[Predicate]] = {}
    # A relationships table's search matches either end's name: it narrows the relationships, not the
    # records (the rows sheet applies it); a grid's search is over its rows' names.
    rows_search = not (
        isinstance(definition, RelationTableViewDefinition) and definition.config.layout != "grid"
    )
    for type_key in (item.objectTypeKey for item in request.scope.types):
        predicates: list[Predicate] = []
        if state.search and rows_search:
            search_fields = (
                definition.config.searchFields
                if isinstance(definition, RelationMatrixViewDefinition)
                else None
            )
            options: dict[str, Any] = {
                "object_type_key": type_key,
                "application_key": None,
                "parent_object_id": None,
                "search": state.search,
                "sort": None,
                "field_filters": [],
                "search_fields": search_fields,
            }
            if context is None:
                query = build_object_query(
                    model, workspace_key=workspace_key, session=session, **options
                )
                ids = query.statement.order_by(None).subquery().c.id
            else:
                query = build_snapshot_object_query(model, context, session=session, **options)
                ids = query.statement.order_by(None).subquery().c.object_id
            predicates.append(lambda column, ids=ids: column.in_(select(ids)))
        found[type_key] = predicates
    if state.cellState is not None and isinstance(definition, RelationMatrixViewDefinition):
        read = build_matrix_read(
            session,
            workspace_key,
            snapshot,
            definition,
            view.application_key,
            request.context.changeSetId,
            request.context.publicationId,
        )
        found[definition.config.rowObjectTypeKey].append(
            state_filter(read, list(state.columnIds or []), state.cellState)
        )
    if state.mappingState is not None and isinstance(definition, MappingGridViewDefinition):
        found[request_type(definition)].append(
            _coverage(model, definition, state.mappingState, workspace_key, context)
        )
    return found


def request_type(definition: MappingGridViewDefinition) -> str:
    config = definition.config
    return config.fromObjectTypeKey if config.direction == "outgoing" else config.toObjectTypeKey


def _coverage(
    model: EngineModel,
    definition: MappingGridViewDefinition,
    state: str,
    workspace_key: str,
    context: SnapshotContext | None,
) -> Predicate:
    """A source's coverage as the mapping grid counts it: mapped (one target where a source holds
    one, any otherwise), ambiguous (several where a source holds one) or unmapped."""
    config = definition.config
    outgoing = config.direction == "outgoing"
    relations = relation_source(context)
    target_type = config.toObjectTypeKey if outgoing else config.fromObjectTypeKey
    targets = record_source(workspace_key, context, [target_type])
    anchor = relations.c.from_object_id if outgoing else relations.c.to_object_id
    other = relations.c.to_object_id if outgoing else relations.c.from_object_id
    counted = (
        select(anchor.label("source_id"), func.count().label("targets"))
        .join(targets, targets.c.object_id == other)
        .where(relations.c.relation_type_key == config.relationTypeKey)
        .group_by(anchor)
        .subquery("mapping_coverage")
    )
    allowed = model.allowed_relation(
        config.relationTypeKey, config.fromObjectTypeKey, config.toObjectTypeKey
    )
    holds_one = allowed.holds_one("from" if outgoing else "to")

    def predicate(column: Any) -> Any:
        mapped = select(counted.c.source_id).where(
            counted.c.targets == 1 if holds_one else counted.c.targets >= 1
        )
        if state == "mapped":
            return column.in_(mapped)
        if state == "ambiguous":
            return column.in_(
                select(counted.c.source_id).where(counted.c.targets > 1 if holds_one else false())
            )
        return ~column.in_(select(counted.c.source_id))

    return predicate
