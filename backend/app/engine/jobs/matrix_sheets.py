"""A relation matrix as a workbook for people (Base 0.17 EX1, PP-D19, PP-D20).

One row per row record (the view's row columns, for reading); then, per column record, either

* a **create matrix** (``create`` or ``edit`` cell actions): a group of the view's cell fields, with
  the cell record's ID and version in hidden columns. The profile reads each cell back as a related
  record of the row (``relatedRecord``): an edited cell changes its record under its version, a
  filled empty cell creates the record in the place the model's candidate rules give under the column
  record (``under``), a cleared cell changes nothing, and a cell holding several records is written
  joined with its version ``not loaded``;
* a **link matrix** (``link`` or ``unlink``): one column listing the cell records linked to the row,
  each by the field the request chose (``cellField``, PP-D25; its name with its display field when
  none), ``"; "`` between them; the profile reads it back as the column's part of the row's set
  (``relation.within``, with the field), under the row's set version, and a value that finds no
  record the column may link creates one in the place the model gives where the view also creates;
  and (0.17 PP-D27) **a value sheet per column**: the records the column offers as full rows (every
  bound field, the group, a hidden ID and version) in an Excel table, which the main sheet's soft
  dropdowns read through a defined name, so a row added or renamed there shows in them. The import
  reads a value-sheet row with an ID as an update and one without as a new record in the column's
  place (``Source.under``), and a main-sheet value naming a value-sheet row is that record.

The cells, rows and options are set statements over the context's tables (``matrix_cells``,
``matrix_read``), kept in temporary tables the sheets then stream from. Nothing here names a type or
relation: the view's definition says which.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from psycopg import sql
from sqlalchemy import column, func, insert, literal, select, table, text
from sqlalchemy.orm import Session

from ...models.schema import EngineModel, RelationMatrixViewDefinition
from ..model.registry import ModelSnapshot
from ..reads.context_sets import record_source
from ..reads.matrix_cells import cell_columns, cell_records
from ..reads.matrix_read import MatrixRead, build_matrix_read, cells_under, derived_place
from ..reads.model_query import candidate_ids
from ..reads.snapshot_reads import SnapshotContext
from . import xlsx
from .export_views import ViewExport
from .people import (
    HUES,
    ID_LABEL,
    NUMBERS_STEPS,
    SPLIT,
    SUMMARY,
    YES_NO,
    CellSpec,
    Labels,
    SheetWriter,
    ViewWritten,
    build_object,
    field_sql,
    invalid_layout,
    separator_safe,
)

# A matrix's columns in the order shown, each cell record with the row and column it sits in, each
# row's cells as one JSON value, and for a link matrix the records each column may link.
_TABLES = (
    (
        "CREATE TEMPORARY TABLE export_matrix_columns (pos integer, column_id varchar(36) PRIMARY KEY)"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE export_matrix_cells (row_id varchar(36), column_id varchar(36),"
        " cell_id varchar(36)) ON COMMIT DROP"
    ),
    "CREATE INDEX ON export_matrix_cells (row_id, column_id)",
    (
        "CREATE TEMPORARY TABLE export_matrix_grid (row_id varchar(36) PRIMARY KEY, cells jsonb)"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE export_matrix_options (column_id varchar(36), cell_id varchar(36))"
        " ON COMMIT DROP"
    ),
)
_COLUMNS = table("export_matrix_columns", column("pos"), column("column_id"))
_CELLS = table("export_matrix_cells", column("row_id"), column("column_id"), column("cell_id"))
_OPTIONS = table("export_matrix_options", column("column_id"), column("cell_id"))
GRAY = "FFD9D9D9"


@dataclass
class _Column:
    id: str
    name: str
    group: str


@dataclass
class _ValueField:
    """One column of a value sheet: the cell record's field, its label, value type and whether the
    import writes it back."""

    key: str
    label: str
    value_type: str
    editable: bool
    expression: sql.Composable


@dataclass
class _ValueSheet:
    """A column's value sheet: its title, its Excel table, and the defined name the dropdowns read."""

    column: _Column
    title: str
    table: str
    name: str


@dataclass
class MatrixSheets:
    """The view's sheets: planned from the model, checked and read against the context."""

    model: EngineModel
    view: ViewExport
    change_set_id: str | None
    publication_id: str | None
    read: MatrixRead | None = None
    columns: list[_Column] = field(default_factory=list)

    @property
    def definition(self) -> RelationMatrixViewDefinition:
        assert isinstance(self.view.definition, RelationMatrixViewDefinition)
        return self.view.definition

    @property
    def config(self) -> Any:
        return self.definition.config

    @property
    def links(self) -> bool:
        """Whether the cells link records (and so list them) rather than hold their fields."""
        return bool(set(self.config.cellActions) & {"link", "unlink"})

    @property
    def creates(self) -> bool:
        return "create" in self.config.cellActions

    @property
    def chosen(self) -> str:
        """The field a link matrix's cells list the records by (PP-D25, PP-D27): the request's, else
        the name."""
        return self.view.cell_field or "name"

    @property
    def loads_values(self) -> bool:
        """Whether the value sheets load back (edit by ID, new rows): where the view edits or creates."""
        return self.creates or "edit" in self.config.cellActions

    # --- checking -----------------------------------------------------------------------------

    def check(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        """The columns the request names are records of the context, and the matrix is not wider than
        a sheet."""
        state, config = self.view.state, self.config
        source = record_source(workspace_key, context, [config.columnObjectTypeKey])
        named = list(state.columnIds or [])
        # Only the named columns are read back; the whole set is counted in the database.
        found = (
            set(session.scalars(select(source.c.object_id).where(source.c.object_id.in_(named))))
            if named
            else set()
        )
        for index, key in enumerate(named):
            if key not in found:
                raise invalid_layout(
                    f"'{key}' is no '{config.columnObjectTypeKey}' record of the exported context",
                    f"/view/state/columnIds/{index}",
                )
        if len(set(named)) != len(named):
            raise invalid_layout("Each column is named once", "/view/state/columnIds")
        count = len(named) or session.scalar(select(func.count()).select_from(source)) or 0
        if self.links and count > xlsx.VALUE_SHEETS:
            raise invalid_layout(
                f"A link matrix keeps the records each column may link on a sheet of its own, so"
                f" {count} columns would need {count} sheets; a workbook of this kind holds"
                f" {xlsx.VALUE_SHEETS} of them. Name fewer columns in columnIds",
                "/view/state/columnIds",
            )
        per_column = 1 if self.links else len(config.cellFields) + 2
        wide = len(config.rowColumns) + count * per_column + 2
        if wide > xlsx.SHEET_COLUMNS:
            raise invalid_layout(
                f"The matrix would need {wide} columns ({count} columns shown); a sheet holds"
                f" {xlsx.SHEET_COLUMNS}. Name fewer columns in columnIds",
                "/view/state/columnIds",
            )

    def _read(self, session: Session, workspace_key: str, snapshot: ModelSnapshot) -> MatrixRead:
        if self.read is None:
            self.read = build_matrix_read(
                session,
                workspace_key,
                snapshot,
                self.definition,
                self.view.application_key,
                self.change_set_id,
                self.publication_id,
            )
        return self.read

    # --- reading ------------------------------------------------------------------------------

    def prepare(
        self,
        session: Session,
        snapshot: ModelSnapshot,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        """The columns, the cells of the exported rows and, for a link matrix, each column's
        options, in temporary tables; their records are queued to be read with the far records."""
        for statement in _TABLES:
            session.execute(text(statement))
        config, state = self.config, self.view.state
        read = self._read(session, workspace_key, snapshot)
        source = record_source(workspace_key, context, [config.columnObjectTypeKey])
        if state.columnIds:
            ids = list(state.columnIds)
            statement = select(
                func.array_position(literal(ids), source.c.object_id), source.c.object_id
            ).where(source.c.object_id.in_(ids))
        else:
            statement = select(
                func.row_number().over(order_by=(source.c.name, source.c.object_id)),
                source.c.object_id,
            )
        session.execute(insert(_COLUMNS).from_select(["pos", "column_id"], statement))
        session.execute(text("ANALYZE export_matrix_columns"))
        cells = cell_columns(read, cell_records(read, None, rows_of_type=True))
        rows = select(column("object_id")).select_from(text("export_records"))
        shown = select(column("column_id")).select_from(text("export_matrix_columns"))
        session.execute(
            insert(_CELLS).from_select(
                ["row_id", "column_id", "cell_id"],
                select(cells.c.row_id, cells.c.column_id, cells.c.cell_id).where(
                    cells.c.row_id.in_(rows), cells.c.column_id.in_(shown)
                ),
            )
        )
        session.execute(text("ANALYZE export_matrix_cells"))
        if self.links:
            self._options(session, read, workspace_key, context)
        # The records the sheets show, read with the far records: rows, columns, cells and options.
        session.execute(
            text(
                "INSERT INTO people_choices (list, object_id)"
                " SELECT -2, object_id FROM export_records"
                " UNION ALL SELECT -4, column_id FROM export_matrix_columns"
                " UNION ALL SELECT -5, cell_id FROM export_matrix_cells"
                " UNION ALL SELECT -6, cell_id FROM export_matrix_options"
            )
        )

    def _options(
        self,
        session: Session,
        read: MatrixRead,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        """The records each column may link: those under it of the cell type that the binding's
        candidate criteria let be chosen (the matrix's own candidate read, D196)."""
        ids = list(
            session.scalars(select(column("column_id")).select_from(text("export_matrix_columns")))
        )
        if not ids:
            return
        under = cells_under(read, ids)
        statement = select(under.c.column_id, under.c.cell_id)
        criteria = read.binding.candidates_at("to" if read.outgoing else "from")
        if criteria:
            statement = statement.where(
                under.c.cell_id.in_(
                    candidate_ids(
                        self.model,
                        self.model.object_type(self.config.cellObjectTypeKey),
                        criteria,
                        workspace_key=workspace_key,
                        context=context,
                    )
                )
            )
        session.execute(insert(_OPTIONS).from_select(["column_id", "cell_id"], statement))
        # The records linked in the column are offered too, whatever the candidate rules say now.
        session.execute(
            text(
                "INSERT INTO export_matrix_options (column_id, cell_id)"
                " SELECT DISTINCT m.column_id, m.cell_id FROM export_matrix_cells m"
                " WHERE NOT EXISTS (SELECT 1 FROM export_matrix_options p"
                " WHERE p.column_id = m.column_id AND p.cell_id = m.cell_id)"
            )
        )
        session.execute(text("ANALYZE export_matrix_options"))

    # --- writing ------------------------------------------------------------------------------

    def write(self, writer: SheetWriter) -> ViewWritten:
        model, config = self.model, self.config
        self._load_columns(writer)
        row_type = model.object_type(config.rowObjectTypeKey)
        cell_type = model.object_type(config.cellObjectTypeKey)
        styles = writer.book.styles
        gray = styles.xf(fill=GRAY, bold=True, border=True)
        labels = Labels()
        cells: list[CellSpec] = []
        bindings: list[dict[str, Any]] = []
        # The row's own columns, for reading.
        for field_ in config.rowColumns:
            label = labels.take(f"{writer.row_field_label(field_)} {SUMMARY}")
            attribute = model.attribute_type(field_)
            value_type = "text"
            style = 0
            if attribute is not None:
                value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
                style = writer.date if attribute.valueType == "date" else 0
            cells.append(
                CellSpec(
                    label,
                    writer.row_field("o", field_, row_type.key),
                    value_type,
                    style=style,
                    header=gray,
                )
            )
            bindings.append({"column": label, "ignore": True})
        fixed = len(cells)
        groups: list[tuple[int, int, str, int]] = [(1, fixed, row_type.name, gray)] if fixed else []
        id_label = labels.take(ID_LABEL)
        hidden: list[CellSpec] = [
            CellSpec(id_label, sql.SQL("r.object_id"), hidden=True, header=writer.plain_header)
        ]
        version_label = None
        if self.links:
            relation = model.relation_type(config.relationTypeKey)
            set_name = relation.name if config.direction == "outgoing" else relation.reverseName
            version_label = labels.take(f"{set_name} set version")
            hidden.append(self._set_version_cell(writer, version_label))
        fields = self._cell_fields(writer)
        soft: set[str] = set()
        lists: dict[str, str] = {}
        value_sheets: list[_ValueSheet] = []
        value_fields: list[_ValueField] = []
        if self.links:
            value_fields = self._value_fields(writer)
            chosen = next((item for item in value_fields if item.key == self.chosen), None)
            for number, found in enumerate(self.columns, 1):
                value_sheets.append(
                    _ValueSheet(
                        found,
                        writer.book.reserve(f"Values · {found.group}"),
                        f"tbl_values_{number}",
                        f"values_{number}",
                    )
                )
                if chosen is not None:
                    writer.book.define(
                        f"values_{number}",
                        f"tbl_values_{number}[{_column_reference(chosen.label)}]",
                    )
                    lists[found.id] = f"values_{number}"
        cell_application = next(
            (item.key for item in model.applications if cell_type.key in item.objectTypeKeys), ""
        )
        self._grid(writer, fields)
        for number, found in enumerate(self.columns):
            hue = HUES[number % len(HUES)]
            fill = styles.xf(fill=hue[0], ink=hue[1], bold=True, border=True)
            header = styles.xf(fill=hue[0], ink=hue[1], bold=True, border=True, wrap="center")
            body = writer.base
            start = len(cells) + 1
            if self.links:
                label = f"{found.group} · linked {cell_type.pluralName.lower()}"
                label = labels.take(label)
                letter = xlsx.column(len(cells) + 1)
                cells.append(
                    CellSpec(
                        label,
                        sql.SQL("(g.cells -> {} ->> 't')").format(sql.Literal(found.id)),
                        style=body,
                        header=fill,
                        list_=lists.get(found.id),
                    )
                )
                if found.id in lists:
                    soft.add(letter)
                groups.append((start, start, found.group, header))
                bindings.append(self._link_binding(label, found, cell_type.key, version_label))
                continue
            id_name = labels.take(f"{found.group} · {cell_type.name} ID")
            version_name = labels.take(f"{found.group} · {cell_type.name} version")
            for index, (key, value_type, editable) in enumerate(fields):
                attribute = None if key == "name" else model.attribute_type(key)
                label = "Name" if attribute is None else attribute.name
                shown = label if editable else f"{label} {SUMMARY}"
                letter = xlsx.column(len(cells) + 1)
                cells.append(
                    CellSpec(
                        shown,
                        sql.SQL("(g.cells -> {} ->> {})").format(
                            sql.Literal(found.id), sql.Literal(f"f{index}")
                        ),
                        value_type,
                        style=writer.date if value_type == "date" else body,
                        header=fill,
                        list_='"Yes,No"' if value_type == "yesno" else None,
                    )
                )
                if editable and (self.creates or "edit" in config.cellActions):
                    bindings.append(
                        self._cell_binding(
                            letter,
                            key,
                            value_type,
                            found,
                            cell_type.key,
                            cell_application,
                            id_name,
                            version_name,
                        )
                    )
            groups.append((start, len(cells), found.group, header))
            hidden += [
                CellSpec(
                    id_name,
                    sql.SQL("(g.cells -> {} ->> 'id')").format(sql.Literal(found.id)),
                    hidden=True,
                    header=writer.plain_header,
                ),
                CellSpec(
                    version_name,
                    sql.SQL("(g.cells -> {} ->> 'v')").format(sql.Literal(found.id)),
                    "version",
                    hidden=True,
                    header=writer.plain_header,
                ),
            ]
        cells += hidden
        source_sql = sql.SQL(
            "export_records r JOIN people_records o ON o.object_id = r.object_id"
            " LEFT JOIN export_matrix_grid g ON g.row_id = r.object_id"
            " WHERE r.object_type_key = {}"
        ).format(sql.Literal(row_type.key))
        titles, count = writer._sheet(
            self.view.definition.name or row_type.pluralName,
            cells,
            source_sql,
            sql.SQL("o.name, r.object_id"),
            groups=groups,
            freeze_columns=fixed,
            soft_lists=frozenset(soft),
        )
        sources = [
            {
                "sheet": titles[0],
                "headerRow": 2,
                "applicationKey": writer.application_of(
                    row_type.key,
                    next(
                        (a.key for a in model.applications if row_type.key in a.objectTypeKeys), ""
                    ),
                ),
                "objectTypeKey": row_type.key,
                "record": "existing",
                "key": {"column": id_label},
                "columns": bindings or [{"column": id_label, "ignore": True}],
            }
        ]
        for sheet in value_sheets:
            titles += self._value_sheet(writer, sheet, value_fields, sources)
        held, several = self._cell_counts(writer)
        return ViewWritten(
            titles=titles,
            sources=sources,
            counts={row_type.key: count},
            relations={config.relationTypeKey: held + several} if self.links else {},
            holds=self._holds(count, held, several, fields),
            loads=self._loads(writer),
            extra=self._extra(),
            value_maps={},
        )

    # --- the pieces ---------------------------------------------------------------------------

    def _load_columns(self, writer: SheetWriter) -> None:
        """The columns in order, each with its group label."""
        config = self.config
        with writer.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT k.column_id, c.name, {label} FROM export_matrix_columns k"
                    " JOIN people_records c ON c.object_id = k.column_id ORDER BY k.pos"
                ).format(label=field_sql(self.model, "c", config.columnLabelField))
            )
            found = cursor.fetchall()
        self.columns = []
        for column_id, name, shown in found:
            group = name if not shown or shown == name else f"{name} ({shown})"
            self.columns.append(_Column(column_id, name, group))

    def _cell_fields(self, writer: SheetWriter) -> list[tuple[str, str, bool]]:
        """The view's cell fields: (key, value type, loads back)."""
        found = []
        cell_type = self.model.object_type(self.config.cellObjectTypeKey)
        bound = {item.attributeTypeKey: item for item in cell_type.attributes}
        for key in self.config.cellFields:
            if key == "name":
                found.append(("name", "text", True))
                continue
            attribute = self.model.attribute_type(key)
            if attribute is None:
                continue
            value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
            binding = bound.get(key)
            found.append((key, value_type, binding is not None and not binding.readOnly))
        return found

    def _grid(self, writer: SheetWriter, fields: list[tuple[str, str, bool]]) -> None:
        """Each row's cells as one JSON value, by column record, in one statement: for a create
        matrix the cell's ID, its version (``not loaded`` for several records, D195) and its
        fields; for a link matrix the labels of the linked records joined."""
        model = self.model
        if self.links and self.chosen != "name":
            self._require_values(writer)
        if self.links:
            display = model.object_type(self.config.cellObjectTypeKey).displayAttributeTypeKey
            label = _label_sql(model, "o", display, self.chosen)
            cell = sql.SQL(
                "jsonb_build_object('t', string_agg({label}, {split} ORDER BY o.name, o.object_id),"
                " 'n', count(*))"
            ).format(label=label, split=sql.Literal(SPLIT))
        else:
            cell = build_object(
                [
                    (
                        sql.Literal("id"),
                        sql.SQL("CASE WHEN count(*) = 1 THEN max(m.cell_id) END"),
                    ),
                    (
                        sql.Literal("v"),
                        sql.SQL(
                            "CASE WHEN count(*) = 1 THEN max(o.version)::text ELSE {skip} END"
                        ).format(skip=sql.Literal("not loaded")),
                    ),
                    *(
                        (
                            sql.Literal(f"f{number}"),
                            sql.SQL(
                                "CASE WHEN count(*) = 1 THEN max({value})"
                                " ELSE string_agg({value}, {split} ORDER BY o.name) END"
                            ).format(
                                value=field_sql(model, "o", None if key == "name" else key),
                                split=sql.Literal(SPLIT),
                            ),
                        )
                        for number, (key, _kind, _editable) in enumerate(fields)
                    ),
                ]
            )
        with writer.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "INSERT INTO export_matrix_grid (row_id, cells)"
                    " SELECT s.row_id, jsonb_object_agg(s.column_id, s.cell) FROM ("
                    " SELECT m.row_id, m.column_id, {cell} AS cell FROM export_matrix_cells m"
                    " JOIN people_records o ON o.object_id = m.cell_id"
                    " GROUP BY m.row_id, m.column_id) s GROUP BY s.row_id"
                ).format(cell=cell)
            )

    def _require_values(self, writer: SheetWriter) -> None:
        """A cell lists its records by the field the request chose, so a linked record without a value
        there would be left out, and an import of the file would unlink it: refuse the export."""
        field_ = self.chosen
        value = field_sql(self.model, "o", field_)
        with writer.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT count(DISTINCT o.object_id), min(o.name) FROM export_matrix_cells m"
                    " JOIN people_records o ON o.object_id = m.cell_id"
                    " WHERE {value} IS NULL OR {value} = ''"
                ).format(value=value)
            )
            number, example = cursor.fetchone()
        if number:
            label = self.model.attribute_type(field_).name
            raise invalid_layout(
                f"{number} linked records (for example {example}) have no {label}; choose another"
                " field for the cells, or fill it in first",
                "/view/cellField",
            )

    def _set_version_cell(self, writer: SheetWriter, label: str) -> CellSpec:
        config = self.config
        outgoing = config.direction == "outgoing"
        from_key, to_key = (
            (config.rowObjectTypeKey, config.cellObjectTypeKey)
            if outgoing
            else (config.cellObjectTypeKey, config.rowObjectTypeKey)
        )
        return CellSpec(
            label,
            sql.SQL(
                "coalesce((SELECT v.version FROM relation_set_versions v"
                " WHERE v.workspace_key = {ws} AND v.change_set_id IS NOT DISTINCT FROM {cs}"
                " AND v.relation_type_key = {rel} AND v.from_object_type_key = {source}"
                " AND v.to_object_type_key = {target} AND v.direction = {direction}"
                " AND v.anchor_object_id = r.object_id), 0)"
            ).format(
                ws=sql.Literal(writer.workspace_key),
                cs=sql.Literal(self.change_set_id),
                rel=sql.Literal(config.relationTypeKey),
                source=sql.Literal(from_key),
                target=sql.Literal(to_key),
                direction=sql.Literal(config.direction),
            ),
            "number",
            hidden=True,
            header=writer.plain_header,
        )

    def _cell_binding(
        self,
        letter: str,
        key: str,
        value_type: str,
        found: _Column,
        cell_key: str,
        application: str,
        id_name: str,
        version_name: str,
    ) -> dict[str, Any]:
        """A create matrix's cell field, read back as a field of the related record (0.9 J6a): found
        by the cell's ID, else created in the place the model gives under the column record."""
        config = self.config
        related: dict[str, Any] = {
            "relationTypeKey": config.relationTypeKey,
            "direction": config.direction,
            "applicationKey": application,
            "objectTypeKey": cell_key,
            "idColumn": id_name,
            "versionColumn": version_name,
            **({"field": "name"} if key == "name" else {"attributeTypeKey": key}),
        }
        if self.creates:
            related["under"] = {"objectTypeKey": config.columnObjectTypeKey, "value": found.id}
        entry: dict[str, Any] = {"letter": letter, "relatedRecord": related}
        if value_type == "yesno":
            entry["valueMap"] = YES_NO
        return entry

    def _link_binding(
        self, label: str, found: _Column, cell_key: str, version_label: str | None
    ) -> dict[str, Any]:
        """A link matrix's column, read back as that column's part of the row's set."""
        config = self.config
        within: dict[str, Any] = {"objectTypeKey": config.columnObjectTypeKey, "value": found.id}
        within["field"] = self.chosen
        relation: dict[str, Any] = {
            "relationTypeKey": config.relationTypeKey,
            "direction": config.direction,
            "objectTypeKey": cell_key,
            "matchBy": {"field": "name"},
            "split": SPLIT.strip(),
            "replace": True,
            "versionColumn": version_label,
        }
        if self.creates:
            relation["missing"] = "create"
        relation["within"] = within
        return {"column": label, "relation": relation}

    def _cell_application(self, cell_type_key: str) -> str:
        """The application a value sheet's records are written in: the view's own where it lists the
        cell type (the records are read through it), else the model's first that does."""
        applications = self.model.applications
        own = next((item for item in applications if item.key == self.view.application_key), None)
        if own is not None and cell_type_key in own.objectTypeKeys:
            return own.key
        return next((item.key for item in applications if cell_type_key in item.objectTypeKeys), "")

    def _value_fields(self, writer: SheetWriter) -> list[_ValueField]:
        """The columns of every value sheet: the name, then each attribute the cell type binds (a JSON
        one is left out), as the cell record holds them."""
        model = self.model
        cell_type = model.object_type(self.config.cellObjectTypeKey)
        labels = Labels()
        found = [
            _ValueField("name", labels.take("Name"), "text", True, field_sql(model, "o", None))
        ]
        for binding in cell_type.attributes:
            attribute = model.attribute_type(binding.attributeTypeKey)
            if attribute is None or attribute.valueType == "json":
                continue
            value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
            label = attribute.name if not binding.readOnly else f"{attribute.name} {SUMMARY}"
            found.append(
                _ValueField(
                    attribute.key,
                    labels.take(label),
                    value_type,
                    not binding.readOnly,
                    field_sql(model, "o", attribute.key),
                )
            )
        return found

    def _value_sheet(
        self,
        writer: SheetWriter,
        sheet: _ValueSheet,
        fields: list[_ValueField],
        sources: list[dict[str, Any]],
    ) -> list[str]:
        """One column's records as full rows in an Excel table (PP-D27), and the source that reads
        the sheet back: a row with an ID updates its record, one without is a new record in the
        column's place."""
        model, config = self.model, self.config
        cell_type = model.object_type(config.cellObjectTypeKey)
        labels = Labels()
        for item in fields:
            labels.take(item.label)
        group_label = labels.take(f"Group {SUMMARY}")
        id_label = labels.take(f"{cell_type.name} ID")
        version_label = labels.take(f"{cell_type.name} version")
        header = writer.header(cell_type.key)
        cells = [
            CellSpec(
                item.label,
                item.expression,
                item.value_type,
                style=writer.date if item.value_type == "date" else writer.fill(cell_type.key),
                header=header,
                list_='"Yes,No"' if item.value_type == "yesno" else None,
            )
            for item in fields
        ]
        cells += [
            CellSpec(
                group_label,
                sql.SQL(
                    "(SELECT p.name FROM people_records p WHERE p.object_id = o.parent_object_id)"
                ),
                header=header,
            ),
            CellSpec(id_label, sql.SQL("o.object_id"), hidden=True, header=writer.plain_header),
            CellSpec(
                version_label,
                sql.SQL("o.version"),
                "version",
                hidden=True,
                header=writer.plain_header,
            ),
        ]
        titles, _ = writer._sheet(
            sheet.title,
            cells,
            sql.SQL(
                "export_matrix_options p JOIN people_records o ON o.object_id = p.cell_id"
                " WHERE p.column_id = {}"
            ).format(sql.Literal(sheet.column.id)),
            sql.SQL("o.name, o.object_id"),
            reserved=True,
            table=sheet.table,
        )
        if self.loads_values:
            columns: list[dict[str, Any]] = []
            for item in fields:
                if not item.editable:
                    columns.append({"column": item.label, "ignore": True})
                elif item.key == "name":
                    columns.append({"column": item.label, "field": "name"})
                else:
                    entry: dict[str, Any] = {"column": item.label, "attributeTypeKey": item.key}
                    if item.value_type == "yesno":
                        entry["valueMap"] = YES_NO
                    columns.append(entry)
            columns.append({"column": group_label, "ignore": True})
            sources.append(
                {
                    "sheet": titles[0],
                    "headerRow": 1,
                    "applicationKey": self._cell_application(cell_type.key),
                    "objectTypeKey": cell_type.key,
                    "record": "upsert",
                    "key": {"column": id_label, "versionColumn": version_label},
                    "under": {
                        "relationTypeKey": config.relationTypeKey,
                        "direction": config.direction,
                        "rowObjectTypeKey": config.rowObjectTypeKey,
                        "objectTypeKey": config.columnObjectTypeKey,
                        "value": sheet.column.id,
                        "creates": self.creates,
                    },
                    "columns": columns,
                }
            )
        return titles

    def _cell_counts(self, writer: SheetWriter) -> tuple[int, int]:
        with writer.connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FILTER (WHERE n = 1), count(*) FILTER (WHERE n > 1) FROM ("
                " SELECT count(*) AS n FROM export_matrix_cells GROUP BY row_id, column_id) x"
            )
            held, several = cursor.fetchone()
        return held or 0, several or 0

    # --- the About sheet's part ---------------------------------------------------------------

    def _holds(
        self, rows: int, held: int, several: int, fields: list[tuple[str, str, bool]]
    ) -> list[tuple[str, str, str | None]]:
        model, config = self.model, self.config
        row_name = model.object_type(config.rowObjectTypeKey).pluralName.lower()
        column_name = model.object_type(config.columnObjectTypeKey).pluralName.lower()
        cell_name = model.object_type(config.cellObjectTypeKey).pluralName.lower()
        names = [
            "name" if key == "name" else model.attribute_type(key).name.lower()
            for key, *_ in fields
        ]
        if self.links:
            columns = (
                f"{len(self.columns)} {column_name}; a cell lists the {cell_name} linked to the"
                f" row, each by its {self._field_text()}"
            )
            cells = f"{held + several}"
        else:
            columns = f"{len(self.columns)} {column_name} × " + ", ".join(names)
            cells = f"{held}" + (
                f" (+{several} holding several, shown joined and not loaded back)"
                if several
                else ""
            )
        return [
            ("Rows", f"{rows} {row_name}", None),
            ("Columns", columns, None),
            ("Cells holding a link" if self.links else "Cells holding a record", cells, None),
        ]

    def _field_text(self) -> str:
        """What a link cell lists a record by, in words."""
        field_ = self.chosen
        return "name" if field_ == "name" else self.model.attribute_type(field_).name.lower()

    def _loads(self, writer: SheetWriter) -> list[tuple[str, str, str | None]]:
        model, config = self.model, self.config
        cell_name = model.object_type(config.cellObjectTypeKey).name.lower()
        row_name = model.object_type(config.rowObjectTypeKey).name.lower()
        if self.links:
            rows = [
                (
                    "Edit a cell",
                    (
                        f"The cell's links become the {cell_name} records listed: one added is"
                        f" linked, one left out is unlinked; refused if the {row_name}'s links"
                        " changed since this export."
                    ),
                    None,
                ),
                (
                    "Fill an empty cell",
                    f"Links the {cell_name} records listed."
                    + (
                        " A value that finds no record in that column creates one in the place"
                        " listed below."
                        if self.creates
                        else ""
                    ),
                    None,
                ),
                (
                    "Clear a cell",
                    "Changes nothing. Unlinking every record of a cell is done in the app.",
                    None,
                ),
                (
                    "Choose a record",
                    (
                        "The dropdown offers the records the view may link in that column; a typed"
                        " name is checked on import."
                    ),
                    None,
                ),
            ]
        else:
            rows = [
                (
                    "Edit a cell",
                    f"Changes that {cell_name}; refused if someone changed it since this export.",
                    None,
                ),
                (
                    "Fill an empty cell",
                    f"Adds a {cell_name} for that {row_name} in the place listed below."
                    if self.creates
                    else f"Not loaded: this matrix does not add {cell_name} records.",
                    None,
                ),
                (
                    "Clear a cell",
                    f"Changes nothing. Removing a {cell_name} is done in the app.",
                    None,
                ),
            ]
        columns = ", ".join(
            labelled
            for key in config.rowColumns
            if (labelled := writer.row_field_label(key)) and key != "name"
        )
        rows.append(
            ("Name" + (f", {columns}" if columns else ""), "For reading; not imported.", None)
        )
        return rows

    def _extra(self) -> list[tuple[str, list[tuple[str, str, str | None]]]]:
        """The parts of the About sheet a matrix adds: where a new record goes (PP-D24, PP-D28), listed
        exactly when the view allows ``create``; and, where the cells carry lists (PP-D27), how to type
        in them in Numbers, which turns a list into a pop-up menu that takes only its items."""
        found: list[tuple[str, list[tuple[str, str, str | None]]]] = []
        model, config = self.model, self.config
        if self.creates and self.read is not None:
            cell_name = model.object_type(config.cellObjectTypeKey).pluralName
            column_name = model.object_type(config.columnObjectTypeKey).name.lower()
            place = derived_place(self.read)
            if place is not None and not place.proposed:
                kind = model.object_type(place.object_type_key).name.lower()
                where = (
                    f"In the {kind} named {place.name} under the {column_name}, which is created"
                    " when the column has none"
                )
            else:
                where = (
                    f"In the group this view already uses under the {column_name}; where there is"
                    " none, the import preview proposes one and confirming the import creates it"
                )
            found.append((f"New {cell_name.lower()} go into", [("Place", where, None)]))
        if self.links:
            found.append(("Editing in Numbers", list(_NUMBERS_STEPS)))
        return found


# A link matrix adds to the shared steps for Numbers (PP-D27) where its value sheets stand.
_NUMBERS_STEPS: tuple[tuple[str, str, str | None], ...] = (
    *NUMBERS_STEPS,
    ("Values sheets", "Their cells are plain and can be edited in Numbers as they are", None),
)


def _label_sql(
    model: EngineModel, alias: str, display: str | None, cell_field: str | None = None
) -> sql.Composable:
    """A record as a cell lists it: the field the request chose, else its name with its display
    field in parentheses when it has one that differs from the name; the text an import reads the
    record back from."""
    # A cell is cut at its separator, so a separator in a label is written as a comma (the import
    # reads the records' labels the same way); the guard is the people export's, ``separator_safe``.
    if cell_field:
        value = field_sql(model, alias, None if cell_field == "name" else cell_field)
        return separator_safe(sql.SQL("coalesce({value}, '')").format(value=value))
    if not display or display == "name" or model.attribute_type(display) is None:
        return separator_safe(sql.SQL("{alias}.name").format(alias=sql.SQL(alias)))
    value = field_sql(model, alias, display)
    return separator_safe(
        sql.SQL(
            "{alias}.name || CASE WHEN {value} IS NOT NULL AND {value} <> {alias}.name"
            " THEN ' (' || {value} || ')' ELSE '' END"
        ).format(alias=sql.SQL(alias), value=value)
    )


def _column_reference(label: str) -> str:
    """A table column as a structured reference names it: a plain label as it is, one with a special
    character in double brackets, ``[ ] # '`` escaped with a quote."""
    escaped = re.sub(r"([\[\]#'])", r"'\1", label)
    return escaped if re.fullmatch(r"[\w ]+", label) else f"[{escaped}]"
