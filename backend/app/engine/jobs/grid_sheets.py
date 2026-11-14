"""A relationships table and a relationships grid as workbooks for people (Base 0.17 EX1).

* **Rows** (``layout: rows``): one row per relationship of the view's binding, the ``from`` and ``to``
  records' columns for reading, the relationship's values and its hidden IDs and version. The
  profile is the relationships sheet of 0.9 J6 (D187): a value edited changes the relationship under
  its version, a row without IDs adds one by the records' names.
* **Grid** (``layout: grid``): one row per ``from`` record and, per ``to`` record shown, a column group:
  *Linked* (Yes or No) and the relationship's values, with the relationship's version hidden. The
  profile reads a group as one relationship: Yes on an unlinked pair links it (with the values),
  values of a linked pair change it under its version, No removes nothing.

Reads are set statements over the context's tables, one per sheet part; Python formats cells.
"""

from dataclasses import dataclass, field
from typing import Any

from psycopg import sql
from sqlalchemy import column, func, insert, literal, select, table, text
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.queries import ModelQuery, QueryContext
from ...models.schema import EngineModel, RelationTableViewDefinition
from ..model.registry import ModelSnapshot
from ..model.related_columns import related_column
from ..reads.context_sets import record_source
from ..reads.model_query import plan_model_query
from ..reads.snapshot_reads import SnapshotContext
from . import xlsx
from .export_views import ViewExport
from .people import (
    HUES,
    ID_LABEL,
    SUMMARY,
    YES_NO,
    CellSpec,
    Labels,
    PeoplePlan,
    SheetPlan,
    SheetWriter,
    ViewWritten,
    field_sql,
    fill_links,
    invalid_layout,
    plan_sheet,
    restrict_links,
)

GRAY = "FFD9D9D9"
_GRID_TABLES = (
    (
        "CREATE TEMPORARY TABLE export_grid_columns (pos integer, column_id varchar(36) PRIMARY KEY)"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE export_grid_cells (row_id varchar(36) PRIMARY KEY, cells jsonb)"
        " ON COMMIT DROP"
    ),
)
_COLUMNS = table("export_grid_columns", column("pos"), column("column_id"))


@dataclass
class _Relationships:
    """What the two layouts share: the view, its binding's relationship read from the ``from`` end,
    and the ``to`` criteria."""

    model: EngineModel
    view: ViewExport
    change_set_id: str | None
    publication_id: str | None

    @property
    def definition(self) -> RelationTableViewDefinition:
        assert isinstance(self.view.definition, RelationTableViewDefinition)
        return self.view.definition

    @property
    def config(self) -> Any:
        return self.definition.config

    def related(self) -> Any:
        """The relationship the view reads, from its ``from`` records to its ``to`` records."""
        config = self.config
        relation = self.model.relation_type(config.relationTypeKey)
        found = related_column(self.model, config.fromObjectTypeKey, relation.key)
        bindings = tuple(
            item for item in found.bindings if item.toObjectTypeKey == config.toObjectTypeKey
        )
        if not bindings:
            raise invalid_layout(
                "The view's relationship is not allowed between its two types", "/view/viewKey"
            )
        return type(found)(
            found.key, found.relation_type_key, found.direction, bindings, found.field
        )

    def to_ids(
        self,
        session: Session,
        workspace_key: str,
        context: SnapshotContext | None,
        where: list[Any],
        path: str,
    ) -> Any:
        """The ``to`` records the criteria let through, as a select of IDs; a criterion the model
        cannot answer is refused at its pointer in the request."""
        query = ModelQuery(
            objectTypeKey=self.config.toObjectTypeKey,
            context=QueryContext(changeSetId=self.change_set_id, publicationId=self.publication_id),
            where=list(where),
        )
        try:
            planned = plan_model_query(
                self.model, query, workspace_key=workspace_key, context=context
            )
        except ApiError as error:
            if error.code != "INVALID_QUERY" or not error.details:
                raise
            raise api_error(
                422,
                "INVALID_QUERY",
                error.message,
                {
                    **error.details,
                    "path": path + str(error.details.get("path", "")).replace("/where", "", 1),
                },
            ) from error
        return planned.query.statement.with_only_columns(planned.query.record.id).order_by(None)

    def application(self, type_key: str) -> str:
        return next(
            (item.key for item in self.model.applications if type_key in item.objectTypeKeys), ""
        )


@dataclass
class RowsSheets(_Relationships):
    """A relationships table: its relationships as rows."""

    plan: PeoplePlan | None = None
    sheet: SheetPlan | None = None

    def __post_init__(self) -> None:
        config = self.config
        related = self.related()
        sheet = plan_sheet(self.model, config.fromObjectTypeKey, related.key, related)
        self.sheet = SheetPlan(
            sheet.key,
            sheet.related,
            False,
            True,
            None,
            title=self.definition.name,
            attributes=tuple(config.attributeColumns),
            orientation_from=tuple(config.fromColumns),
            orientation_to=tuple(config.toColumns),
        )
        self.plan = PeoplePlan(
            config.fromObjectTypeKey,
            self.application(config.fromObjectTypeKey),
            (),
            (self.sheet,),
            main=False,
        )

    def list_plans(self) -> tuple[PeoplePlan, ...]:
        """The plan whose cells offer lists: both records of a row, as a relationship sheet does."""
        return (self.plan,)

    def check(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        if self.view.state.toWhere:
            self.to_ids(
                session, workspace_key, context, self.view.state.toWhere, "/view/state/toWhere"
            )

    def prepare(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        fill_links(
            session, 0, self.sheet.related, workspace_key, context, self.config.fromObjectTypeKey
        )
        if self.view.state.toWhere:
            restrict_links(
                session,
                0,
                self.to_ids(
                    session, workspace_key, context, self.view.state.toWhere, "/view/state/toWhere"
                ),
            )

    def write(self, writer: SheetWriter) -> ViewWritten:
        if self.view.state.search:
            # The page's search matches either end's name; the far records are read by now.
            with writer.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM people_links l WHERE l.part = 0 AND NOT ("
                    " EXISTS (SELECT 1 FROM export_records r WHERE r.object_id = l.anchor_id"
                    " AND strpos(lower(r.name), lower(%(q)s)) > 0)"
                    " OR EXISTS (SELECT 1 FROM people_records o WHERE o.object_id = l.related_id"
                    " AND strpos(lower(o.name), lower(%(q)s)) > 0))",
                    {"q": self.view.state.search},
                )
        titles, count, source = writer.relationships(self.plan, self.sheet, 0)
        model, config = self.model, self.config
        row_name = model.object_type(config.fromObjectTypeKey).pluralName.lower()
        to_name = model.object_type(config.toObjectTypeKey).pluralName.lower()
        sources = [{**source, "sheet": titles[0]}] if source is not None else []
        return ViewWritten(
            titles=titles,
            sources=sources,
            counts={},
            relations={config.relationTypeKey: count},
            holds=[
                ("Rows", f"{count} relationships between {row_name} and {to_name}", None),
                (
                    "Columns",
                    "Both records' names and the columns the view shows, then the relationship's"
                    " own values: " + (", ".join(self._attribute_names()) or "none"),
                    None,
                ),
            ],
            loads=[
                (
                    "Edit a value",
                    "Changes that relationship; refused if it changed since this export.",
                    None,
                ),
                (
                    "Add a row",
                    "Leave the IDs empty and name the two records: the row adds the relationship.",
                    None,
                ),
                (
                    "Delete a row",
                    "Changes nothing. Removing a relationship is done in the app.",
                    None,
                ),
                ("Columns marked (not imported)", "For reading only.", None),
            ],
        )

    def _attribute_names(self) -> list[str]:
        return [
            self.model.attribute_type(key).name
            for key in self.config.attributeColumns
            if self.model.attribute_type(key) is not None
        ]


@dataclass
class GridSheets(_Relationships):
    """A relationships grid: a row per ``from`` record, a column group per ``to`` record."""

    columns: list[tuple[str, str]] = field(default_factory=list)

    def check(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        state, config = self.view.state, self.config
        to_source = record_source(workspace_key, context, [config.toObjectTypeKey])
        named = list(state.columnIds or [])
        # Only the named columns are read back; the whole set is counted in the database.
        found = (
            set(
                session.scalars(
                    select(to_source.c.object_id).where(to_source.c.object_id.in_(named))
                )
            )
            if named
            else set()
        )
        for index, key in enumerate(named):
            if key not in found:
                raise invalid_layout(
                    f"'{key}' is no '{config.toObjectTypeKey}' record of the exported context",
                    f"/view/state/columnIds/{index}",
                )
        if len(set(named)) != len(named):
            raise invalid_layout("Each column is named once", "/view/state/columnIds")
        if state.toWhere:
            self.to_ids(session, workspace_key, context, state.toWhere, "/view/state/toWhere")
        count = len(named) or session.scalar(select(func.count()).select_from(to_source)) or 0
        wide = len(config.fromColumns) + 1 + count * (1 + len(config.attributeColumns) + 1)
        if wide > xlsx.SHEET_COLUMNS:
            raise invalid_layout(
                f"The grid would need {wide} columns ({count} groups); a sheet holds"
                f" {xlsx.SHEET_COLUMNS}. Name fewer columns in columnIds",
                "/view/state/columnIds",
            )

    def prepare(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        for statement in _GRID_TABLES:
            session.execute(text(statement))
        config, state = self.config, self.view.state
        source = record_source(workspace_key, context, [config.toObjectTypeKey])
        shown = select(source.c.object_id, source.c.name)
        if state.columnIds:
            shown = shown.where(source.c.object_id.in_(list(state.columnIds)))
        if state.toSearch:
            shown = shown.where(source.c.name.icontains(state.toSearch, autoescape=True))
        if state.toWhere:
            shown = shown.where(
                source.c.object_id.in_(
                    self.to_ids(
                        session, workspace_key, context, state.toWhere, "/view/state/toWhere"
                    )
                )
            )
        ordered = shown.subquery("grid_to")
        position = (
            func.array_position(literal(list(state.columnIds)), ordered.c.object_id)
            if state.columnIds
            else func.row_number().over(order_by=(ordered.c.name, ordered.c.object_id))
        )
        session.execute(
            insert(_COLUMNS).from_select(
                ["pos", "column_id"], select(position, ordered.c.object_id)
            )
        )
        fill_links(session, 0, self.related(), workspace_key, context, config.fromObjectTypeKey)
        restrict_links(
            session, 0, select(column("column_id")).select_from(text("export_grid_columns"))
        )
        session.execute(
            text(
                "INSERT INTO people_choices (list, object_id)"
                " SELECT -2, object_id FROM export_records"
                " UNION ALL SELECT -4, column_id FROM export_grid_columns"
            )
        )

    def write(self, writer: SheetWriter) -> ViewWritten:
        model, config = self.model, self.config
        from_type = model.object_type(config.fromObjectTypeKey)
        to_type = model.object_type(config.toObjectTypeKey)
        styles = writer.book.styles
        gray = styles.xf(fill=GRAY, bold=True, border=True)
        attributes = [
            key for key in config.attributeColumns if model.attribute_type(key) is not None
        ]
        label_field = config.toColumns[0]
        with writer.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT k.column_id, c.name, {label} FROM export_grid_columns k"
                    " JOIN people_records c ON c.object_id = k.column_id ORDER BY k.pos"
                ).format(label=field_sql(model, "c", label_field))
            )
            found = cursor.fetchall()
            cursor.execute(
                "INSERT INTO export_grid_cells (row_id, cells)"
                " SELECT l.anchor_id, jsonb_object_agg(l.related_id, jsonb_build_object("
                "'v', l.version::text, 'a', coalesce(l.attributes::jsonb, '{}'::jsonb)))"
                " FROM people_links l WHERE l.part = 0 GROUP BY l.anchor_id"
            )
        labels = Labels()
        cells: list[CellSpec] = []
        bindings: list[dict[str, Any]] = []
        for key in config.fromColumns:
            label = labels.take(f"{writer.row_field_label(key)} {SUMMARY}")
            cells.append(CellSpec(label, writer.row_field("o", key, from_type.key), header=gray))
            bindings.append({"column": label, "ignore": True})
        fixed = len(cells)
        groups = [(1, fixed, from_type.name, gray)] if fixed else []
        id_label = labels.take(ID_LABEL)
        hidden = [
            CellSpec(id_label, sql.SQL("r.object_id"), hidden=True, header=writer.plain_header)
        ]
        related = self.related()
        maps: dict[str, dict[str, Any]] = {}
        for number, (to_id, name, shown) in enumerate(found):
            group = name if not shown or shown == name else f"{name} ({shown})"
            hue = HUES[number % len(HUES)]
            header = styles.xf(fill=hue[0], ink=hue[1], bold=True, border=True)
            group_style = styles.xf(fill=hue[0], ink=hue[1], bold=True, border=True, wrap="center")
            start = len(cells) + 1
            linked = labels.take(f"Linked · {group}")
            version = labels.take(f"{group} · relationship version")
            cells.append(
                CellSpec(
                    linked,
                    sql.SQL("(CASE WHEN g.cells ? {} THEN 'Yes' ELSE 'No' END)").format(
                        sql.Literal(to_id)
                    ),
                    "yesno",
                    header=header,
                    list_='"Yes,No"',
                )
            )
            values = []
            for key in attributes:
                attribute = model.attribute_type(key)
                label = labels.take(f"{attribute.name} · {group}")
                value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
                cells.append(
                    CellSpec(
                        label,
                        _relationship_value(to_id, key, attribute.valueType),
                        value_type,
                        style=writer.date if attribute.valueType == "date" else 0,
                        header=header,
                        list_='"Yes,No"' if value_type == "yesno" else None,
                    )
                )
                values.append(
                    {"column": label, "attributeTypeKey": key}
                    | ({"valueMap": YES_NO} if value_type == "yesno" else {})
                )
            groups.append((start, len(cells), group, group_style))
            hidden.append(
                CellSpec(
                    version,
                    sql.SQL("(g.cells -> {} ->> 'v')").format(sql.Literal(to_id)),
                    "number",
                    hidden=True,
                    header=writer.plain_header,
                )
            )
            map_key = f"link-{number}"
            maps[map_key] = {"Yes": to_id, "No": ""}
            bindings.append(
                {
                    "column": linked,
                    "valueMap": map_key,
                    "relation": {
                        "relationTypeKey": related.relation_type_key,
                        "direction": related.direction,
                        "objectTypeKey": to_type.key,
                        "matchBy": {"field": "id"},
                        "versionColumn": version,
                        **({"attributes": values} if values else {}),
                    },
                }
            )
        cells += hidden
        titles, count = writer._sheet(
            self.definition.name,
            cells,
            sql.SQL(
                "export_records r JOIN people_records o ON o.object_id = r.object_id"
                " LEFT JOIN export_grid_cells g ON g.row_id = r.object_id"
                " WHERE r.object_type_key = {}"
            ).format(sql.Literal(from_type.key)),
            sql.SQL("o.name, r.object_id"),
            groups=groups,
            freeze_columns=fixed,
        )
        with writer.connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM people_links WHERE part = 0")
            links = cursor.fetchone()[0]
        names = ", ".join(model.attribute_type(key).name.lower() for key in attributes)
        return ViewWritten(
            titles=titles,
            sources=[
                {
                    "sheet": titles[0],
                    "headerRow": 2,
                    "applicationKey": writer.application_of(
                        from_type.key, self.application(from_type.key)
                    ),
                    "objectTypeKey": from_type.key,
                    "record": "existing",
                    "key": {"column": id_label},
                    "columns": bindings or [{"column": id_label, "ignore": True}],
                }
            ],
            counts={from_type.key: count},
            relations={related.relation_type_key: links},
            value_maps=maps,
            holds=[
                ("Rows", f"{count} {from_type.pluralName.lower()}", None),
                (
                    "Columns",
                    f"{len(found)} {to_type.pluralName.lower()} × linked (Yes or No)"
                    + (f", {names}" if names else ""),
                    None,
                ),
                ("Relationships", str(links), None),
            ],
            loads=[
                (
                    "Edit a value",
                    "Changes that relationship; refused if it changed since this export.",
                    None,
                ),
                (
                    "Yes on an unlinked pair",
                    "Links the two records, with the values in the cells.",
                    None,
                ),
                ("No", "Changes nothing. Removing a relationship is done in the app.", None),
                ("Name and the columns marked (not imported)", "For reading only.", None),
            ],
        )


def _relationship_value(to_id: str, key: str, value_type: str) -> sql.Composable:
    """A relationship's own value in the grid cell of its ``to`` record, as text."""
    value = sql.SQL("(g.cells -> {} -> 'a' ->> {})").format(sql.Literal(to_id), sql.Literal(key))
    if value_type == "json":
        return sql.SQL("(g.cells -> {} -> 'a' -> {})::text").format(
            sql.Literal(to_id), sql.Literal(key)
        )
    if value_type == "boolean":
        return sql.SQL("(CASE {} WHEN 'true' THEN 'Yes' WHEN 'false' THEN 'No' END)").format(value)
    return value
