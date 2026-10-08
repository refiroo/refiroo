"""Binding an import's file: rows become batch items (Base 0.9 J2, INTEGRATION_API §J3, D68–D72).

The worker binds an import before its first chunk, in one transaction:

1. **Rows, in Python.** A reader streams the file; each bound cell is converted through the attribute
   registry (``cells.py``) and each row is written to temporary tables by ``COPY``: the row's own
   values, its relationship cells (``import_links``) and its related records (``import_related``).
   A cell that does not convert rejects its row; the row's other cells are still converted, so its
   refusal names every cell that failed (D85).
2. **Sets, in PostgreSQL.** Statements over those tables and the context's records
   (``reads/context_sets.py``, live data or the change set) find each row's record by its key or
   give it a new ID; reject rows repeating a key with other values (D69); resolve every match, against
   the context and the rows of the file, so a row can name a record the same file creates (none or
   several reject the row); order a source's own hierarchy by depth, rejecting a ring; find each
   related record through its relationship and parent (D70); and build the items as JSON.
3. **The job's inputs.** Rejected rows become the job's first outcomes, in row order; the items
   follow as its inputs, in the order they must run: records by source order, depth and row, then
   related records, then relationships (D72). Each carries its source and row (0.9 J3), so the
   outcomes read by row. The batch path runs them unchanged.

**The binding report** (0.9 J3, D86) says per source and column what binding made of the cells:
read, empty, converted, value-mapped, refused; for a match column (a parent, a relationship, a flag)
how many values found one record, none or several. The cell counts are kept while the rows stream;
the match counts are one statement over the temporary tables once every match is resolved.

A JSON Lines file is batch items already, and an export's CSV or XLSX tables (D71) map row by row,
so both skip the matching. Python never holds the set: rows go to the database in chunks, and the
statements per import do not grow with its rows.
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import cast, column, insert, select, table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import BatchItem
from ...models.database import Job
from ...models.imports import ColumnBinding, ImportProfileDefinition, MatchBy, Source
from ...models.schema import EngineModel
from ..reads.context_sets import record_source, relation_source
from ..reads.snapshot_reads import SnapshotContext, change_set_context
from ..records.counterparts import counterpart
from .cells import attribute_value, cell_text, flag_set, is_empty
from .profiles import check_profile, invalid_profile, source_order
from .readers import Area, Table, TabularFile, jsonl_lines, open_tabular

# Rows written to the database per round of COPY statements.
CHUNK_ROWS = 5_000
# A cancel request and the lease are looked at after this many rows are read.
CHECK_ROWS = 10_000
MAX_NAME = 500
_ITEM = TypeAdapter(BatchItem)
_RECORD_COLUMNS = ("objectTypeKey", "applicationKey", "id", "version", "name", "parentObjectId")

_TEMPORARY_TABLES = (
    (
        "CREATE TEMPORARY TABLE import_rows (row_id integer PRIMARY KEY, src integer NOT NULL,"
        " row_number integer NOT NULL, ref text NOT NULL, object_type_key text, application_key text,"
        " mode text, key_kind text, key_attr text, key_value jsonb, key_column text, name text,"
        " attributes jsonb NOT NULL DEFAULT '{}', parent jsonb, error jsonb, rep_id integer,"
        " record_id text, existing boolean NOT NULL DEFAULT false, current_name text, parent_id text,"
        " depth integer NOT NULL DEFAULT -1) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_rows (object_type_key, name)",
    "CREATE INDEX ON import_rows (record_id)",
    (
        "CREATE TEMPORARY TABLE import_links (row_id integer NOT NULL, link_no integer NOT NULL,"
        " relation_type_key text, direction text, object_type_key text, match jsonb, column_name text,"
        " replace boolean, required boolean, candidates integer, target_id text) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_related (entry_id integer PRIMARY KEY, row_id integer NOT NULL,"
        " grp integer NOT NULL, relation_type_key text, direction text, application_key text,"
        " object_type_key text, parent jsonb, match_attr text, name text, fallback_name text,"
        " attributes jsonb NOT NULL DEFAULT '{}', required boolean, column_name text,"
        " parent_candidates integer, parent_id text, related_candidates integer, related_id text,"
        " existing boolean NOT NULL"
        " DEFAULT false, current_name text) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_matches (match_id serial PRIMARY KEY, object_type_key text,"
        " field text, attr text, value jsonb, candidates integer NOT NULL DEFAULT 0, resolved text,"
        " UNIQUE (object_type_key, field, attr, value)) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_context (object_id text PRIMARY KEY, object_type_key text,"
        " name text, parent_object_id text, attributes jsonb) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_context (object_type_key, name)",
    (
        "CREATE TEMPORARY TABLE import_context_relations (relation_type_key text, from_id text,"
        " to_id text) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_items (phase integer, src integer, depth integer,"
        " row_number integer, sub integer, ref text, item jsonb) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_errors (src integer, row_number integer, ref text,"
        " error jsonb) ON COMMIT DROP"
    ),
    # With counterparts (0.9 J5, D100): a match by ID naming another workspace's record, and the
    # ID of its counterpart here, derived in Python (PostgreSQL has no SHA-1 of its own).
    "CREATE TEMPORARY TABLE import_counterparts (match_id integer, object_id text) ON COMMIT DROP",
    # Every match cell the file holds, for the binding report: a refused row's too.
    (
        "CREATE TEMPORARY TABLE import_match_cells (src integer, column_name text, match jsonb)"
        " ON COMMIT DROP"
    ),
)


@dataclass(frozen=True)
class Bound:
    """What binding stored: the rows rejected and the items queued; the binding report (none for
    JSON Lines)."""

    rejected: int
    items: int
    report: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class ImportLimits:
    atomic_max_items: int
    background_max_items: int


class _Mismatch:
    """Problems found reading the file's headers, raised together as ``IMPORT_FILE_MISMATCH``."""

    def __init__(self) -> None:
        self.problems: list[dict[str, str]] = []

    def add(self, path: str, code: str, message: str) -> None:
        self.problems.append({"path": path, "code": code, "message": message})

    def raise_if_any(self) -> None:
        if self.problems:
            raise api_error(
                422,
                "IMPORT_FILE_MISMATCH",
                f"The file does not fit the import profile: {len(self.problems)} problem(s)",
                {"problems": self.problems},
            )


def bind_import(
    session: Session,
    job: Job,
    path: Path,
    model: EngineModel,
    check: Callable[[], None],
    limits: ImportLimits,
) -> Bound:
    """Bind the file at ``path`` into the job's outcomes and inputs; the caller commits. ``check``
    is called every :data:`CHECK_ROWS` rows read and raises to stop."""
    if not path.is_file():
        raise api_error(
            410,
            "IMPORT_FILE_MISSING",
            f"The file of import '{job.id}' is no longer in the job file directory; send it "
            "again. Operators: check JOB_FILE_DIR and what removes files from it",
        )
    for statement in _TEMPORARY_TABLES:
        session.execute(text(statement))
    parameters = job.parameters
    file_format = parameters["file"]["format"]
    definition = (parameters.get("profile") or {}).get("definition")
    rows = _RowCounter(check)
    report: _Report | None = None
    if file_format == "jsonl":
        _bind_jsonl(session, path, rows)
    elif definition is not None:
        profile = ImportProfileDefinition.model_validate(definition)
        problems = check_profile(model, profile)
        if problems:
            raise invalid_profile(problems)
        context = (
            change_set_context(session, job.change_set_id)
            if job.change_set_id is not None
            else None
        )
        report = _Report()
        _ProfileBinding(session, job, model, profile, context, rows, report).run(path, file_format)
    else:
        report = _Report()
        _bind_table_layout(session, path, file_format, model, rows, report)
    stored = _store(session, job, limits)
    return Bound(stored.rejected, stored.items, report.finish(session) if report else None)


class _RowCounter:
    def __init__(self, check: Callable[[], None]) -> None:
        self.check = check
        self.count = 0

    def tick(self) -> None:
        self.count += 1
        if self.count % CHECK_ROWS == 0:
            self.check()


class _Report:
    """The binding report (D86): per source and column, what binding made of the cells.

    A converted column counts ``empty``, ``converted``, ``valueMapped`` (a cell a value map
    replaced) and ``refused`` cells; a match column ``empty`` and ``refused`` cells and, once the
    matches are resolved, the values that found one record (``resolved``), none (``notFound``) or
    several (``ambiguous``): a split cell holds several values."""

    CONVERTED = ("converted", "valueMapped", "refused")
    MATCHED = ("resolved", "notFound", "ambiguous", "refused")

    def __init__(self) -> None:
        self.sources: dict[int, dict[str, Any]] = {}
        self.columns: dict[int, dict[tuple[str, str, str | None], dict[str, Any]]] = {}

    def source(self, src: int, sheet: str, object_type_key: str | None) -> None:
        self.sources[src] = {
            "sheet": sheet,
            "objectTypeKey": object_type_key,
            "rows": 0,
            "rejectedRows": 0,
        }
        self.columns[src] = {}

    def row(self, src: int) -> None:
        self.sources[src]["rows"] += 1

    def cell(
        self, src: int, column_name: str, binding: str, target: str | None, *, matched: bool = False
    ) -> dict[str, Any]:
        """The column's counts, with one more cell read."""
        columns = self.columns[src]
        entry = columns.get((column_name, binding, target))
        if entry is None:
            entry = columns[(column_name, binding, target)] = {
                "column": column_name,
                "binding": binding,
                "target": target,
                "cells": 0,
                "empty": 0,
            } | dict.fromkeys(self.MATCHED if matched else self.CONVERTED, 0)
        entry["cells"] += 1
        return entry

    def finish(self, session: Session) -> list[dict[str, Any]]:
        """The report, its match and rejected-row counts read from the temporary tables."""
        resolved = session.execute(
            text(
                f"""
                SELECT c.src, c.column_name,
                       count(*) FILTER (WHERE m.candidates = 1),
                       count(*) FILTER (WHERE m.candidates = 0),
                       count(*) FILTER (WHERE m.candidates > 1)
                FROM import_match_cells c JOIN import_matches m ON {_JOINED.format(s="c.match")}
                GROUP BY c.src, c.column_name
                """
            )
        ).all()
        found = {(src, name): counts for src, name, *counts in resolved}
        rejected = dict(
            session.execute(text("SELECT src, count(*) FROM import_errors GROUP BY src")).all()
        )
        report = []
        for src in sorted(self.sources):
            columns = []
            for entry in self.columns[src].values():
                if "resolved" in entry:
                    counts = found.get((src, entry["column"]), (0, 0, 0))
                    entry["resolved"], entry["notFound"], entry["ambiguous"] = counts
                columns.append(entry)
            source = self.sources[src] | {"rejectedRows": rejected.get(src, 0)}
            report.append(source | {"columns": columns})
        return report


def _tally(entry: dict[str, Any], raw: Any, mapped: bool, convert: Callable[[Any], Any]) -> Any:
    """Convert one cell, counting what became of it in its report column."""
    if raw is None:
        entry["valueMapped" if mapped else "empty"] += 1
        return None
    try:
        value = convert(raw)
    except _RowError:
        entry["refused"] += 1
        raise
    entry["valueMapped" if mapped else "converted"] += 1
    return value


# --- writing rows ----------------------------------------------------------------------------------


class _Copy:
    """Rows for one temporary table, written by ``COPY`` in chunks."""

    def __init__(self, session: Session, table_name: str, columns: tuple[str, ...]) -> None:
        self.session = session
        self.statement = f"COPY {table_name} ({', '.join(columns)}) FROM STDIN"
        self.rows: list[tuple[Any, ...]] = []

    def add(self, *values: Any) -> None:
        self.rows.append(tuple(_copy_value(value) for value in values))

    def flush(self) -> None:
        if not self.rows:
            return
        connection = self.session.connection().connection.driver_connection
        with connection.cursor() as cursor, cursor.copy(self.statement) as copy:
            for row in self.rows:
                copy.write_row(row)
        self.rows = []


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _error(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details}


def _from_api(error: ApiError, column_name: str) -> dict[str, Any]:
    details = dict(error.details) if isinstance(error.details, dict) else {}
    details["column"] = column_name
    return {"code": error.code, "message": error.message, "details": details}


def _cells_error(failures: list[dict[str, Any]]) -> dict[str, Any]:
    """A row's refusal for its failing cells (D85): the first cell's error, with every failing
    cell in ``details.cells``."""
    first = failures[0]
    details = dict(first.get("details") or {})
    details["cells"] = [
        {"column": f["details"].get("column"), "code": f["code"], "message": f["message"]}
        for f in failures
    ]
    return {**first, "details": details}


# --- JSON Lines and the export's tables (no profile) ----------------------------------------------


def _items_copy(session: Session) -> _Copy:
    return _Copy(
        session, "import_items", ("phase", "src", "depth", "row_number", "sub", "ref", "item")
    )


def _errors_copy(session: Session) -> _Copy:
    return _Copy(session, "import_errors", ("src", "row_number", "ref", "error"))


def _bind_jsonl(session: Session, path: Path, rows: _RowCounter) -> None:
    items, errors = _items_copy(session), _errors_copy(session)
    for number, value in jsonl_lines(path):
        rows.tick()
        ref = f"jsonl!{number}"
        if isinstance(value, ValueError):
            errors.add(
                0,
                number,
                ref,
                _error("REQUEST_VALIDATION_ERROR", f"Line {number} is not JSON: {value}"),
            )
        else:
            try:
                item = _ITEM.validate_python(value)
            except ValidationError as error:
                first = error.errors()[0]
                where = "/".join(str(part) for part in first["loc"])
                errors.add(
                    0,
                    number,
                    ref,
                    _error(
                        "REQUEST_VALIDATION_ERROR",
                        f"Line {number} is not a batch item: {first['msg']} at {where or 'the line'}",
                    ),
                )
            else:
                dumped = item.model_dump(mode="json", exclude_unset=True)
                dumped["ref"] = ref
                items.add(0, 0, 0, number, 0, ref, dumped)
        if len(items.rows) + len(errors.rows) >= CHUNK_ROWS:
            items.flush()
            errors.flush()
    items.flush()
    errors.flush()


def _bind_table_layout(
    session: Session,
    path: Path,
    file_format: str,
    model: EngineModel,
    rows: _RowCounter,
    report: _Report,
) -> None:
    """An export's tables read back (D71): a records row is an ``upsert`` by its ID with its
    version as ``expectedVersion`` (a ``create`` without an ID), a relationships row an
    ``ensureRelation``."""
    book = open_tabular(path, file_format)
    try:
        tables = _layout_tables(book)
        if not tables:
            mismatch = _Mismatch()
            mismatch.add(
                "",
                "NOT_A_TABLE_LAYOUT",
                "Without a profile a CSV or XLSX file must be an export's table layout, with an "
                "objectTypeKey or relationTypeKey column; name a profile for any other file",
            )
            mismatch.raise_if_any()
        items, errors = _items_copy(session), _errors_copy(session)
        for src, (sheet, found) in enumerate(tables):
            columns = found.columns()
            report.source(src, sheet, None)
            if "objectTypeKey" in columns and "applicationKey" not in columns:
                mismatch = _Mismatch()
                mismatch.add(
                    f"/{sheet}/applicationKey",
                    "COLUMN_NOT_FOUND",
                    f"Sheet '{sheet}' has records but no applicationKey column",
                )
                mismatch.raise_if_any()
            for number, cells in found.rows:
                rows.tick()
                report.row(src)
                ref = f"{sheet}!{number}"
                try:
                    item = _layout_item(model, columns, cells, partial(report.cell, src))
                except _RowError as error:
                    errors.add(src, number, ref, error.body)
                else:
                    if item is not None:
                        item["ref"] = ref
                        items.add(0, src, 0, number, 0, ref, item)
                if len(items.rows) + len(errors.rows) >= CHUNK_ROWS:
                    items.flush()
                    errors.flush()
        items.flush()
        errors.flush()
    finally:
        book.close()


def _layout_tables(book: TabularFile) -> list[tuple[str, Table]]:
    """The sheets holding an export's tables, each with the header row that names its columns
    (the first, or the second below a row of labels)."""
    found = []
    for sheet in book.sheet_names:
        for header_row in (1, 2):
            candidate = book.table(sheet, Area(header_row))
            if candidate is None:
                break
            names = set(candidate.columns())
            if names & {"objectTypeKey", "relationTypeKey"}:
                found.append((sheet, candidate))
                break
    return found


class _RowError(Exception):
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body


def _cell(columns: dict[str, int], cells: list[Any], name: str) -> Any:
    position = columns.get(name)
    if position is None or position >= len(cells):
        return None
    value = cells[position]
    return None if is_empty(value) else value


def _uuid(value: Any, column_name: str) -> str:
    try:
        return str(UUID(cell_text(value).strip()))
    except ValueError:
        raise _RowError(
            _error("INVALID_CELL", f"Column {column_name} must hold an ID", column=column_name)
        ) from None


def _version(value: Any, column_name: str) -> int:
    text_value = cell_text(value).strip()
    if not text_value.isdigit() or int(text_value) < 1:
        raise _RowError(
            _error(
                "INVALID_CELL",
                f"Column {column_name} must hold a version (1 or more)",
                column=column_name,
            )
        )
    return int(text_value)


# A report column of the layout's sheet: (column, binding, target) -> its counts.
_Column = Callable[[str, str, str | None], dict[str, Any]]


def _layout_item(
    model: EngineModel, columns: dict[str, int], cells: list[Any], column: _Column
) -> dict[str, Any] | None:
    object_type_key = _cell(columns, cells, "objectTypeKey")
    if object_type_key is not None:
        return _layout_record(model, columns, cells, cell_text(object_type_key), column)
    relation_type_key = _cell(columns, cells, "relationTypeKey")
    if relation_type_key is not None:
        return _layout_relation(model, columns, cells, cell_text(relation_type_key), column)
    return None


def _layout_values(
    model: EngineModel,
    columns: dict[str, int],
    cells: list[Any],
    keys: list[str],
    column: _Column,
) -> dict[str, Any]:
    """The ``#key`` columns' values; every cell that does not convert refuses the row (D85)."""
    values, failures = {}, []
    for key in keys:
        column_name = f"#{key}"
        if column_name not in columns:
            continue
        definition = model.attribute_type(key)

        def convert(raw: Any, column_name: str = column_name, definition: Any = definition) -> Any:
            try:
                return attribute_value(definition, raw)
            except ApiError as error:
                raise _RowError(_from_api(error, column_name)) from None

        entry = column(column_name, "attributeTypeKey", key)
        try:
            value = _tally(entry, _cell(columns, cells, column_name), False, convert)
        except _RowError as error:
            failures.append(error.body)
            continue
        if value is not None:
            values[key] = value
    if failures:
        raise _RowError(_cells_error(failures))
    return values


def _layout_record(
    model: EngineModel,
    columns: dict[str, int],
    cells: list[Any],
    object_type_key: str,
    column: _Column,
) -> dict[str, Any]:
    definition = model.object_type(object_type_key)
    if definition is None:
        raise _RowError(
            _error(
                "INVALID_CELL",
                f"Object type '{object_type_key}' is not in the model",
                column="objectTypeKey",
            )
        )
    application = _cell(columns, cells, "applicationKey")
    if application is None:
        raise _RowError(
            _error("INVALID_CELL", "Column applicationKey is empty", column="applicationKey")
        )
    name = _cell(columns, cells, "name")
    entry = column("name", "field", "name")
    if name is None:
        entry["empty"] += 1
        raise _RowError(_error("NAME_REQUIRED", "Column name is empty", column="name"))
    name = cell_text(name)
    if len(name) > MAX_NAME:
        entry["refused"] += 1
        raise _RowError(
            _error("INVALID_NAME", f"A name holds at most {MAX_NAME} characters", column="name")
        )
    entry["converted"] += 1
    values = _layout_values(
        model,
        columns,
        cells,
        [b.attributeTypeKey for b in definition.attributes if not b.readOnly],
        column,
    )
    attributes = [{"attributeTypeKey": key, "value": value} for key, value in values.items()]
    item: dict[str, Any] = {
        "applicationKey": cell_text(application),
        "objectTypeKey": object_type_key,
        "name": name,
        "attributes": attributes,
    }
    parent = _cell(columns, cells, "parentObjectId")
    if parent is not None:
        item["parent"] = {"id": _uuid(parent, "parentObjectId")}
    record_id = _cell(columns, cells, "id")
    if record_id is None:
        return {"op": "create", **item}
    item = {"op": "upsert", "key": {"id": _uuid(record_id, "id")}, **item}
    version = _cell(columns, cells, "version")
    if version is not None:
        item["expectedVersion"] = _version(version, "version")
    return item


def _layout_relation(
    model: EngineModel,
    columns: dict[str, int],
    cells: list[Any],
    relation_type_key: str,
    column: _Column,
) -> dict[str, Any]:
    if model.relation_type(relation_type_key) is None:
        raise _RowError(
            _error(
                "INVALID_CELL",
                f"Relation type '{relation_type_key}' is not in the model",
                column="relationTypeKey",
            )
        )
    item: dict[str, Any] = {
        "op": "ensureRelation",
        "relationTypeKey": relation_type_key,
        "from": {"id": _uuid(_cell(columns, cells, "fromId"), "fromId")},
        "to": {"id": _uuid(_cell(columns, cells, "toId"), "toId")},
    }
    carried = {
        key
        for binding in model.objectTypeRelations
        if binding.relationTypeKey == relation_type_key
        for key in binding.attributeTypeKeys
    }
    attributes = _layout_values(model, columns, cells, sorted(carried), column)
    if attributes:
        item["attributes"] = attributes
    version = _cell(columns, cells, "version")
    if version is not None:
        item["expectedVersion"] = _version(version, "version")
    return item


# --- through a profile -----------------------------------------------------------------------------


@dataclass
class _Plan:
    """One source as the rows read it: where each named column is."""

    index: int
    order: int
    source: Source
    sheet: str
    columns: dict[str, int]
    groups: dict[tuple[Any, ...], int] = field(default_factory=dict)


@dataclass
class _RowState:
    """What a row's cells bound to so far."""

    name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    parent: dict[str, Any] | None = None
    links: list[tuple[Any, ...]] = field(default_factory=list)
    related: dict[int, dict[str, Any]] = field(default_factory=dict)


def _name(raw: Any, column_name: str) -> str:
    name = cell_text(raw)
    if len(name) > MAX_NAME:
        raise _RowError(
            _error(
                "INVALID_NAME", f"A name holds at most {MAX_NAME} characters", column=column_name
            )
        )
    return name


class _ProfileBinding:
    def __init__(
        self,
        session: Session,
        job: Job,
        model: EngineModel,
        profile: ImportProfileDefinition,
        context: SnapshotContext | None,
        rows: _RowCounter,
        report: _Report,
    ) -> None:
        self.session = session
        self.job = job
        self.model = model
        self.profile = profile
        self.context = context
        self.counter = rows
        self.report = report
        self.match_cells = _Copy(session, "import_match_cells", ("src", "column_name", "match"))
        self.row_id = 0
        self.entry_id = 0
        self.rows = _Copy(
            session,
            "import_rows",
            (
                "row_id",
                "src",
                "row_number",
                "ref",
                "object_type_key",
                "application_key",
                "mode",
                "key_kind",
                "key_attr",
                "key_value",
                "key_column",
                "name",
                "attributes",
                "parent",
                "error",
            ),
        )
        self.links = _Copy(
            session,
            "import_links",
            (
                "row_id",
                "link_no",
                "relation_type_key",
                "direction",
                "object_type_key",
                "match",
                "column_name",
                "replace",
                "required",
            ),
        )
        self.related = _Copy(
            session,
            "import_related",
            (
                "entry_id",
                "row_id",
                "grp",
                "relation_type_key",
                "direction",
                "application_key",
                "object_type_key",
                "parent",
                "match_attr",
                "name",
                "fallback_name",
                "attributes",
                "required",
                "column_name",
            ),
        )

    # --- reading ---

    def run(self, path: Path, file_format: str) -> None:
        delimiter = self.profile.csv.delimiter if self.profile.csv is not None else ","
        book = open_tabular(path, file_format, delimiter)
        try:
            plans = self._plans(book, file_format == "xlsx")
            for plan in plans:
                found = book.table(
                    plan.source.sheet if file_format == "xlsx" else None, _area(plan.source)
                )
                for number, cells in found.rows:
                    self.counter.tick()
                    self._row(plan, number, cells)
                    if len(self.rows.rows) >= CHUNK_ROWS:
                        self._flush()
            self._flush()
        finally:
            book.close()
        self._resolve()

    def _plans(self, book: TabularFile, xlsx: bool) -> list[_Plan]:
        """Each source's columns, in the order the sources load; every missing sheet, header row
        and column is a problem, raised together before a row is read."""
        mismatch = _Mismatch()
        plans = []
        order = source_order(self.model, self.profile) or list(range(len(self.profile.sources)))
        for position, index in enumerate(order):
            source = self.profile.sources[index]
            at = f"/sources/{index}"
            if xlsx and source.sheet is not None and source.sheet not in book.sheet_names:
                mismatch.add(
                    f"{at}/sheet",
                    "SHEET_NOT_FOUND",
                    f"The workbook has no sheet '{source.sheet}'; it has {', '.join(book.sheet_names)}",
                )
                continue
            found = book.table(source.sheet if xlsx else None, _area(source))
            if found is None:
                mismatch.add(
                    f"{at}/headerRow",
                    "HEADER_ROW_NOT_FOUND",
                    f"The sheet ends before its header row {source.headerRow}",
                )
                continue
            columns = found.columns()
            for path, name in _named_columns(source, at):
                if name not in columns:
                    mismatch.add(path, "COLUMN_NOT_FOUND", f"The header has no column '{name}'")
            sheet = (source.sheet or book.sheet_names[0]) if xlsx else book.sheet_names[0]
            plans.append(_Plan(index, position, source, sheet, columns))
            self.report.source(position, sheet, source.objectTypeKey)
        mismatch.raise_if_any()
        return plans

    def _row(self, plan: _Plan, number: int, cells: list[Any]) -> None:
        self.row_id += 1
        row_id = self.row_id
        source = plan.source
        ref = f"{plan.sheet}!{number}"
        self.report.row(plan.order)
        state = _RowState()
        failures: list[dict[str, Any]] = []
        for binding in source.columns:
            if binding.ignore:
                continue
            try:
                self._binding(plan, binding, cells, state)
            except _RowError as rejected:
                failures.append(rejected.body)
        key_value, key_kind, key_attr, key_column = None, None, None, None
        failed = {failure["details"].get("column") for failure in failures}
        try:
            if source.key is not None and source.key.attributeTypeKey is not None:
                key_kind, key_attr = "attribute", source.key.attributeTypeKey
                key_column = next(
                    b.column for b in source.columns if b.attributeTypeKey == key_attr
                )
                key_value = state.attributes.get(key_attr)
                if key_value is None and key_column not in failed:
                    raise _RowError(
                        _error(
                            "MISSING_RECORD_KEY",
                            f"The key column {key_column} is empty",
                            column=key_column,
                        )
                    )
            elif source.key is not None:
                key_kind, key_column = "id", source.key.column
                entry = self.report.cell(plan.order, key_column, "key", "id")
                key_value = _tally(
                    entry,
                    _cell(plan.columns, cells, key_column),
                    False,
                    lambda raw: _uuid(raw, key_column),
                )
                if key_value is None:
                    key_kind = None
                    if source.record == "existing":
                        raise _RowError(
                            _error(
                                "MISSING_RECORD_KEY",
                                f"The key column {key_column} is empty",
                                column=key_column,
                            )
                        )
        except _RowError as rejected:
            failures.append(rejected.body)
        error = None
        if failures:
            error = _cells_error(failures)
            state.links, state.related = [], {}
            key_value, key_kind, key_attr, key_column = None, None, None, None
        self.rows.add(
            row_id,
            plan.order,
            number,
            ref,
            source.objectTypeKey,
            source.applicationKey,
            source.record,
            key_kind,
            key_attr,
            json.dumps(key_value) if key_value is not None else None,
            key_column,
            state.name,
            state.attributes,
            state.parent,
            error,
        )
        for link_no, link in enumerate(state.links):
            self.links.add(row_id, link_no, *link)
        for group, entry in state.related.items():
            if not entry["attributes"] and entry["name"] is None:
                continue
            self.entry_id += 1
            self.related.add(
                self.entry_id,
                row_id,
                group,
                entry["relation"],
                entry["direction"],
                entry["application"],
                entry["type"],
                entry["parent"],
                entry["match"],
                entry["name"],
                entry["fallback"],
                entry["attributes"],
                entry["required"],
                entry["column"],
            )

    def _binding(
        self, plan: _Plan, binding: ColumnBinding, cells: list[Any], state: _RowState
    ) -> None:
        """One column binding of the row, into ``state``; a cell that does not convert raises."""
        src = plan.order
        if binding.relationFlags is not None:
            state.links += self._flags(plan, binding, cells)
            return
        raw, mapped = self._raw(plan, binding, binding.column, cells)
        if binding.field == "name":
            entry = self.report.cell(src, binding.column, "field", "name")
            name = _tally(entry, raw, mapped, lambda raw: _name(raw, binding.column))
            if name is not None:
                state.name = name
        elif binding.attributeTypeKey is not None:
            key = binding.attributeTypeKey
            entry = self.report.cell(src, binding.column, "attributeTypeKey", key)
            value = _tally(entry, raw, mapped, lambda raw: self._value(key, raw, binding.column))
            if value is not None:
                state.attributes[key] = value
        elif binding.parent is not None:
            parent = binding.parent
            entry = self.report.cell(
                src, binding.column, "parent", parent.objectTypeKey, matched=True
            )
            if raw is None:
                entry["empty"] += 1
                return
            state.parent = self._matched(
                entry, src, parent.objectTypeKey, parent.matchBy, raw, binding.column
            )
        elif binding.relation is not None:
            state.links += self._relations(plan, binding, raw)
        elif binding.relatedRecord is not None:
            self._related(plan, binding, raw, mapped, cells, state.related)

    def _raw(
        self, plan: _Plan, binding: ColumnBinding, column_name: str, cells: list[Any]
    ) -> tuple[Any, bool]:
        """The cell, through the binding's value map; ``True`` when the map replaced it."""
        raw = _cell(plan.columns, cells, column_name)
        if binding.valueMap is not None and raw is not None:
            mapping = self.profile.valueMaps[binding.valueMap]
            key = cell_text(raw)
            if key in mapping:
                mapped = mapping[key]
                return (None if is_empty(mapped) else mapped), True
        return raw, False

    def _value(self, attribute_type_key: str, raw: Any, column_name: str) -> Any:
        try:
            return attribute_value(self.model.attribute_type(attribute_type_key), raw)
        except ApiError as error:
            raise _RowError(_from_api(error, column_name)) from None

    def _match(
        self, object_type_key: str, match: MatchBy, raw: Any, column_name: str
    ) -> dict[str, Any]:
        if match.attributeTypeKey is not None:
            value = self._value(match.attributeTypeKey, raw, column_name)
        elif match.field == "id":
            value = _uuid(raw, column_name)
        else:
            value = cell_text(raw)
        return {
            "type": object_type_key,
            "field": match.field or "",
            "attr": match.attributeTypeKey or "",
            "value": value,
            "column": column_name,
        }

    def _matched(
        self,
        entry: dict[str, Any],
        src: int,
        object_type_key: str,
        match: MatchBy,
        raw: Any,
        column_name: str,
    ) -> dict[str, Any]:
        """A match cell's value, kept for the report's resolution counts."""
        try:
            found = self._match(object_type_key, match, raw, column_name)
        except _RowError:
            entry["refused"] += 1
            raise
        self.match_cells.add(src, column_name, found)
        return found

    def _required(
        self, plan: _Plan, relation_type_key: str, direction: str, other_type: str
    ) -> bool:
        """Whether a new record of the row's type needs this relationship when it is created: a
        required binding into its type that is not its containment."""
        if direction != "incoming":
            return False
        binding = self.model.allowed_relation(
            relation_type_key, other_type, plan.source.objectTypeKey
        )
        return binding is not None and binding.required

    def _relations(self, plan: _Plan, binding: ColumnBinding, raw: Any) -> list[tuple[Any, ...]]:
        relation = binding.relation
        entry = self.report.cell(
            plan.order, binding.column, "relation", relation.relationTypeKey, matched=True
        )
        pieces = [] if raw is None else [raw]
        if raw is not None and relation.split is not None:
            mapping = self.profile.valueMaps.get(binding.valueMap or "", {})
            pieces = []
            for piece in cell_text(raw).split(relation.split):
                piece = piece.strip()
                if piece and piece in mapping:
                    piece = mapping[piece]
                if not is_empty(piece):
                    pieces.append(piece)
        if not pieces:
            entry["empty"] += 1
            return []
        required = self._required(
            plan, relation.relationTypeKey, relation.direction, relation.objectTypeKey
        )
        return [
            (
                relation.relationTypeKey,
                relation.direction,
                relation.objectTypeKey,
                self._matched(
                    entry,
                    plan.order,
                    relation.objectTypeKey,
                    relation.matchBy,
                    piece,
                    binding.column,
                ),
                binding.column,
                relation.replace,
                required,
            )
            for piece in pieces
        ]

    def _flags(
        self, plan: _Plan, binding: ColumnBinding, cells: list[Any]
    ) -> list[tuple[Any, ...]]:
        flags = binding.relationFlags
        required = self._required(plan, flags.relationTypeKey, flags.direction, flags.objectTypeKey)
        links = []
        for column_name in binding.columns or []:
            entry = self.report.cell(
                plan.order, column_name, "relationFlags", flags.relationTypeKey, matched=True
            )
            if not flag_set(_cell(plan.columns, cells, column_name), flags.trueValues):
                entry["empty"] += 1
                continue
            links.append(
                (
                    flags.relationTypeKey,
                    flags.direction,
                    flags.objectTypeKey,
                    self._matched(
                        entry,
                        plan.order,
                        flags.objectTypeKey,
                        flags.matchBy,
                        flags.targets[column_name],
                        column_name,
                    ),
                    column_name,
                    False,
                    required,
                )
            )
        return links

    def _related(
        self,
        plan: _Plan,
        binding: ColumnBinding,
        raw: Any,
        mapped: bool,
        cells: list[Any],
        entries: dict[int, dict[str, Any]],
    ) -> None:
        spec = binding.relatedRecord
        parent = spec.parent
        identity = (
            spec.relationTypeKey,
            spec.direction,
            spec.applicationKey,
            spec.objectTypeKey,
            parent.objectTypeKey,
            parent.matchBy.field,
            parent.matchBy.attributeTypeKey,
            parent.value,
            parent.column,
            spec.matchBy.attributeTypeKey if spec.matchBy else None,
        )
        group = plan.groups.setdefault(identity, len(plan.groups))
        entry = entries.get(group)
        if entry is None:
            parent_raw = (
                parent.value
                if parent.value is not None
                else _cell(plan.columns, cells, parent.column)
            )
            parent_match = (
                self._match(
                    parent.objectTypeKey,
                    parent.matchBy,
                    parent_raw,
                    parent.column or binding.column,
                )
                if parent_raw is not None
                else None
            )
            backward = spec.direction == "outgoing"
            source_type, target_type = (
                (plan.source.objectTypeKey, spec.objectTypeKey)
                if backward
                else (spec.objectTypeKey, plan.source.objectTypeKey)
            )
            relation = self.model.allowed_relation(spec.relationTypeKey, source_type, target_type)
            entry = {
                "relation": spec.relationTypeKey,
                "direction": spec.direction,
                "application": spec.applicationKey,
                "type": spec.objectTypeKey,
                "parent": parent_match,
                "match": spec.matchBy.attributeTypeKey if spec.matchBy else None,
                "name": None,
                "fallback": None,
                "attributes": {},
                "required": bool(relation and relation.required and backward),
                "column": binding.column,
            }
            entries[group] = entry
        counts = self.report.cell(plan.order, binding.column, "relatedRecord", spec.objectTypeKey)
        if spec.field == "name":
            name = _tally(counts, raw, mapped, cell_text)
            if name is None:
                return
            entry["name"] = name
        else:
            value = _tally(
                counts,
                raw,
                mapped,
                lambda raw: self._value(spec.attributeTypeKey, raw, binding.column),
            )
            if value is None:
                return
            entry["attributes"][spec.attributeTypeKey] = value
            if entry["fallback"] is None:
                entry["fallback"] = cell_text(raw)
        if entry["parent"] is None:
            raise _RowError(
                _error(
                    "REFERENCE_NOT_FOUND",
                    "The related record's parent column is empty",
                    column=parent.column or binding.column,
                )
            )

    def _flush(self) -> None:
        self.rows.flush()
        self.links.flush()
        self.related.flush()
        self.match_cells.flush()

    # --- resolving, in the database ---

    def _resolve(self) -> None:
        run = self._sql
        types = self._context_types()
        source = record_source(self.job.workspace_key, self.context, sorted(types))
        self.session.execute(
            insert(
                table(
                    "import_context",
                    column("object_id"),
                    column("object_type_key"),
                    column("name"),
                    column("parent_object_id"),
                    column("attributes"),
                )
            ).from_select(
                ["object_id", "object_type_key", "name", "parent_object_id", "attributes"],
                select(
                    source.c.object_id,
                    source.c.object_type_key,
                    source.c.name,
                    source.c.parent_object_id,
                    cast(source.c.attributes, JSONB),
                ),
            )
        )
        relation_types = sorted(
            {
                b.relatedRecord.relationTypeKey
                for s in self.profile.sources
                for b in s.columns
                if b.relatedRecord
            }
        )
        if relation_types:
            relations = relation_source(self.context)
            known = select(column("object_id")).select_from(table("import_context"))
            self.session.execute(
                insert(
                    table(
                        "import_context_relations",
                        column("relation_type_key"),
                        column("from_id"),
                        column("to_id"),
                    )
                ).from_select(
                    ["relation_type_key", "from_id", "to_id"],
                    select(
                        relations.c.relation_type_key,
                        relations.c.from_object_id,
                        relations.c.to_object_id,
                    )
                    .where(relations.c.relation_type_key.in_(relation_types))
                    .where(
                        relations.c.from_object_id.in_(known) | relations.c.to_object_id.in_(known)
                    ),
                )
            )
        run("ANALYZE import_rows")
        run("ANALYZE import_context")
        self._duplicates()
        self._identities()
        self._matches()
        self._hierarchy()
        self._related_identities()
        self._members()
        self._items()

    def _context_types(self) -> set[str]:
        types: set[str] = set()
        for source in self.profile.sources:
            types.add(source.objectTypeKey)
            for binding in source.columns:
                if binding.parent is not None:
                    types.add(binding.parent.objectTypeKey)
                for relation in (binding.relation, binding.relationFlags):
                    if relation is not None:
                        types.add(relation.objectTypeKey)
                if binding.relatedRecord is not None:
                    types.add(binding.relatedRecord.objectTypeKey)
                    types.add(binding.relatedRecord.parent.objectTypeKey)
        return types

    def _sql(self, statement: str) -> None:
        self.session.execute(text(statement))

    def _counterpart_matches(self) -> None:
        """Each match by ID naming another workspace's live record, with its counterpart here
        (0.9 J5, D100): one statement finds them, one ``COPY`` stores the counterparts."""
        workspace_key = self.job.workspace_key
        held = self.session.execute(
            text(
                "SELECT m.match_id, o.id FROM import_matches m JOIN objects o"
                " ON o.id = m.value #>> '{}' WHERE m.field = 'id' AND o.workspace_key <> :workspace"
            ),
            {"workspace": workspace_key},
        ).all()
        counterparts = _Copy(self.session, "import_counterparts", ("match_id", "object_id"))
        for match_id, object_id in held:
            counterparts.add(match_id, counterpart(workspace_key, object_id))
        counterparts.flush()

    def _duplicates(self) -> None:
        """D69: rows of one source with one key are one record when their own values agree; when
        they differ, every such row is rejected naming the others."""
        self._sql(
            """
            WITH groups AS (
                SELECT src, key_value, min(row_id) AS rep,
                       count(DISTINCT jsonb_build_array(name, attributes, parent)) AS variants,
                       array_agg(row_number ORDER BY row_number) AS numbers
                FROM import_rows WHERE error IS NULL AND key_value IS NOT NULL
                GROUP BY src, key_value HAVING count(*) > 1)
            UPDATE import_rows r SET
                error = CASE WHEN g.variants > 1 THEN jsonb_build_object(
                    'code', 'DUPLICATE_KEY_IN_FILE',
                    'message', format('Rows %s hold one key with different values; none of them is'
                        ' loaded', array_to_string(g.numbers, ', ')),
                    'details', jsonb_build_object(
                        'rows', to_jsonb(array_remove(g.numbers, r.row_number)),
                        'column', r.key_column)) END,
                rep_id = CASE WHEN g.variants = 1 AND r.row_id <> g.rep THEN g.rep END
            FROM groups g WHERE r.src = g.src AND r.key_value = g.key_value AND r.error IS NULL
            """
        )

    def _identities(self) -> None:
        """Each row's record: found by its key in the context, or a new ID; a member row of a
        repeated key takes its first row's."""
        self._sql(
            """
            UPDATE import_rows r SET record_id = c.object_id, existing = true, current_name = c.name
            FROM import_context c
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.key_kind = 'attribute'
              AND c.object_type_key = r.object_type_key AND c.attributes -> r.key_attr = r.key_value
            """
        )
        self._sql(
            """
            UPDATE import_rows r SET record_id = r.key_value #>> '{}',
                existing = EXISTS (SELECT 1 FROM import_context c WHERE c.object_id = r.key_value #>> '{}'),
                current_name = (SELECT c.name FROM import_context c WHERE c.object_id = r.key_value #>> '{}')
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.key_kind = 'id'
            """
        )
        self._sql(
            """
            UPDATE import_rows SET error = jsonb_build_object(
                'code', 'REFERENCE_NOT_FOUND',
                'message', format('No %s record has the key %s', object_type_key, key_value),
                'details', jsonb_build_object('column', key_column))
            WHERE error IS NULL AND rep_id IS NULL AND mode = 'existing' AND NOT existing
            """
        )
        self._sql(
            """
            UPDATE import_rows SET error = jsonb_build_object(
                'code', 'NAME_REQUIRED',
                'message', 'A new record needs a name, and the row has none',
                'details', jsonb_build_object('column', NULL))
            WHERE error IS NULL AND rep_id IS NULL AND mode = 'upsert' AND NOT existing AND name IS NULL
            """
        )
        self._sql(
            """
            UPDATE import_rows SET record_id = gen_random_uuid()::text
            WHERE error IS NULL AND rep_id IS NULL AND record_id IS NULL
            """
        )
        self._sql(
            """
            UPDATE import_rows m SET record_id = r.record_id, existing = r.existing,
                current_name = r.current_name
            FROM import_rows r WHERE m.rep_id = r.row_id
            """
        )

    def _matches(self) -> None:
        """Every distinct match resolved once, against the context's records and the file's own
        rows; a row whose parent, relationship or related record's parent finds none or several is
        rejected with the first such column."""
        self._sql(
            """
            INSERT INTO import_matches (object_type_key, field, attr, value)
            SELECT DISTINCT m ->> 'type', m ->> 'field', m ->> 'attr', m -> 'value' FROM (
                SELECT parent AS m FROM import_rows WHERE parent IS NOT NULL AND error IS NULL
                UNION ALL SELECT match FROM import_links
                UNION ALL SELECT parent FROM import_related WHERE parent IS NOT NULL
                UNION ALL SELECT match FROM import_match_cells) found
            """
        )
        self._sql("ANALYZE import_matches")
        if self.job.parameters.get("otherWorkspaceIds") == "counterparts":
            self._counterpart_matches()
        self._sql(
            """
            WITH candidates AS (
                SELECT m.match_id, c.object_id FROM import_matches m
                JOIN import_context c ON c.object_type_key = m.object_type_key
                    AND m.field = 'name' AND c.name = m.value #>> '{}'
                UNION SELECT m.match_id, c.object_id FROM import_matches m
                JOIN import_context c ON c.object_type_key = m.object_type_key
                    AND m.field = 'id' AND c.object_id = m.value #>> '{}'
                UNION SELECT m.match_id, c.object_id FROM import_matches m
                JOIN import_counterparts k ON k.match_id = m.match_id
                JOIN import_context c ON c.object_type_key = m.object_type_key
                    AND c.object_id = k.object_id
                UNION SELECT m.match_id, c.object_id FROM import_matches m
                JOIN import_context c ON c.object_type_key = m.object_type_key
                    AND m.attr <> '' AND c.attributes -> m.attr = m.value
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_rows f ON f.object_type_key = m.object_type_key AND f.mode = 'upsert'
                    AND f.rep_id IS NULL AND f.error IS NULL
                    AND m.field = 'name' AND f.name = m.value #>> '{}'
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_rows f ON f.object_type_key = m.object_type_key AND f.mode = 'upsert'
                    AND f.rep_id IS NULL AND f.error IS NULL
                    AND m.field = 'id' AND f.record_id = m.value #>> '{}'
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_rows f ON f.object_type_key = m.object_type_key AND f.mode = 'upsert'
                    AND f.rep_id IS NULL AND f.error IS NULL
                    AND m.attr <> '' AND f.attributes -> m.attr = m.value),
            counted AS (
                SELECT match_id, count(*) AS n, min(object_id) AS one FROM candidates GROUP BY match_id)
            UPDATE import_matches m SET candidates = c.n, resolved = CASE WHEN c.n = 1 THEN c.one END
            FROM counted c WHERE c.match_id = m.match_id
            """
        )
        joined = _JOINED
        self._sql(
            f"""
            UPDATE import_rows r SET parent_id = m.resolved,
                error = CASE WHEN m.candidates = 1 THEN NULL ELSE {_MATCH_ERROR.format(s="r.parent")} END
            FROM import_matches m WHERE r.parent IS NOT NULL AND r.error IS NULL
              AND {joined.format(s="r.parent")}
            """
        )
        self._sql(
            f"""
            UPDATE import_links l SET target_id = m.resolved, candidates = m.candidates
            FROM import_matches m WHERE {joined.format(s="l.match")}
            """
        )
        self._sql(
            f"""
            UPDATE import_related d SET parent_id = m.resolved, parent_candidates = m.candidates
            FROM import_matches m WHERE d.parent IS NOT NULL AND {joined.format(s="d.parent")}
            """
        )
        self._sql(
            f"""
            UPDATE import_rows r SET error = e.error FROM (
                SELECT DISTINCT ON (l.row_id) l.row_id, {_MATCH_ERROR.format(s="l.match")} AS error
                FROM import_links l JOIN import_matches m ON {joined.format(s="l.match")}
                WHERE l.candidates <> 1 ORDER BY l.row_id, l.link_no) e
            WHERE r.row_id = e.row_id AND r.error IS NULL
            """
        )
        self._sql(
            f"""
            UPDATE import_rows r SET error = e.error FROM (
                SELECT DISTINCT ON (d.row_id) d.row_id, {_MATCH_ERROR.format(s="d.parent")} AS error
                FROM import_related d JOIN import_matches m ON {joined.format(s="d.parent")}
                WHERE d.parent_candidates <> 1 ORDER BY d.row_id, d.entry_id) e
            WHERE r.row_id = e.row_id AND r.error IS NULL
            """
        )

    def _hierarchy(self) -> None:
        """A source's rows under rows of the same source load parents first (depth); rows whose
        parents form a ring never reach a top and are rejected."""
        self._sql(
            """
            WITH RECURSIVE tree(row_id, depth) AS (
                SELECT r.row_id, 0 FROM import_rows r
                WHERE r.error IS NULL AND r.rep_id IS NULL AND (r.parent_id IS NULL OR NOT EXISTS (
                    SELECT 1 FROM import_rows p WHERE p.src = r.src AND p.rep_id IS NULL
                      AND p.error IS NULL AND p.record_id = r.parent_id AND p.row_id <> r.row_id))
                UNION ALL
                SELECT c.row_id, t.depth + 1 FROM tree t
                JOIN import_rows p ON p.row_id = t.row_id
                JOIN import_rows c ON c.parent_id = p.record_id AND c.src = p.src
                    AND c.rep_id IS NULL AND c.error IS NULL AND c.row_id <> p.row_id)
            UPDATE import_rows r SET depth = t.depth FROM tree t WHERE r.row_id = t.row_id
            """
        )
        self._sql(
            """
            UPDATE import_rows SET error = jsonb_build_object(
                'code', 'REFERENCE_CYCLE',
                'message', 'The row''s parent leads back to the row through other rows of the file',
                'details', jsonb_build_object('column', parent ->> 'column'))
            WHERE error IS NULL AND rep_id IS NULL AND depth < 0
            """
        )

    def _related_identities(self) -> None:
        """D70: a related record is the one of its type under its parent that the relationship
        already joins to the row's record (narrowed by ``matchBy``); several are ambiguous; none
        means a new one, shared by the rows naming the same one. Rows naming one related record with
        different values are rejected."""
        self._sql(
            """
            WITH candidates AS (
                SELECT d.entry_id, c.object_id, c.name FROM import_related d
                JOIN import_rows r ON r.row_id = d.row_id AND r.error IS NULL AND r.existing
                JOIN import_context c ON c.object_type_key = d.object_type_key
                    AND c.parent_object_id = d.parent_id
                    AND (d.match_attr IS NULL OR c.attributes -> d.match_attr = d.attributes -> d.match_attr)
                JOIN import_context_relations x ON x.relation_type_key = d.relation_type_key
                    AND ((d.direction = 'outgoing' AND x.from_id = r.record_id AND x.to_id = c.object_id)
                      OR (d.direction = 'incoming' AND x.to_id = r.record_id AND x.from_id = c.object_id))),
            counted AS (
                SELECT entry_id, count(DISTINCT object_id) AS n, min(object_id) AS one,
                       min(name) AS name FROM candidates GROUP BY entry_id)
            UPDATE import_related d SET related_id = CASE WHEN c.n = 1 THEN c.one END,
                existing = c.n = 1, current_name = c.name, related_candidates = c.n
            FROM counted c WHERE c.entry_id = d.entry_id
            """
        )
        self._sql(
            """
            UPDATE import_rows r SET error = jsonb_build_object(
                'code', 'REFERENCE_AMBIGUOUS',
                'message', format('%s related %s records match; name which one with matchBy',
                    d.related_candidates, d.object_type_key),
                'details', jsonb_build_object('column', d.column_name, 'count', d.related_candidates))
            FROM import_related d WHERE d.row_id = r.row_id AND d.related_candidates > 1 AND r.error IS NULL
            """
        )
        self._sql(
            """
            UPDATE import_related d SET related_id = g.id FROM (
                SELECT r.record_id, d2.grp, d2.parent_id, d2.attributes -> coalesce(d2.match_attr, '') AS narrowed,
                       gen_random_uuid()::text AS id
                FROM import_related d2 JOIN import_rows r ON r.row_id = d2.row_id
                WHERE d2.related_id IS NULL AND r.error IS NULL
                GROUP BY r.record_id, d2.grp, d2.parent_id, d2.attributes -> coalesce(d2.match_attr, '')) g,
                import_rows r
            WHERE r.row_id = d.row_id AND d.related_id IS NULL AND r.error IS NULL
              AND g.record_id = r.record_id AND g.grp = d.grp AND g.parent_id = d.parent_id
              AND g.narrowed IS NOT DISTINCT FROM d.attributes -> coalesce(d.match_attr, '')
            """
        )
        self._sql(
            """
            WITH groups AS (
                SELECT d.related_id, count(DISTINCT jsonb_build_array(d.name, d.attributes)) AS variants,
                       array_agg(r.row_number ORDER BY r.row_number) AS numbers
                FROM import_related d JOIN import_rows r ON r.row_id = d.row_id AND r.error IS NULL
                WHERE d.related_id IS NOT NULL GROUP BY d.related_id HAVING count(*) > 1)
            UPDATE import_rows r SET error = jsonb_build_object(
                'code', 'DUPLICATE_KEY_IN_FILE',
                'message', format('Rows %s give one related record different values',
                    array_to_string(g.numbers, ', ')),
                'details', jsonb_build_object('rows', to_jsonb(array_remove(g.numbers, r.row_number)),
                    'column', d.column_name))
            FROM import_related d JOIN groups g ON g.related_id = d.related_id AND g.variants > 1
            WHERE d.row_id = r.row_id AND r.error IS NULL
            """
        )

    def _members(self) -> None:
        """A row repeating a key whose first row was rejected is rejected with it."""
        self._sql(
            """
            UPDATE import_rows m SET error = r.error || jsonb_build_object('details',
                coalesce(r.error -> 'details', '{}'::jsonb) || jsonb_build_object('row', r.row_number))
            FROM import_rows r WHERE m.rep_id = r.row_id AND r.error IS NOT NULL AND m.error IS NULL
            """
        )

    def _items(self) -> None:
        """The items, in the order they run: records, then related records, then relationships."""
        attributes = (
            "(SELECT coalesce(jsonb_agg(jsonb_build_object('attributeTypeKey', a.key, 'value', a.value)"
            " ORDER BY a.key), '[]'::jsonb) FROM jsonb_each({s}.attributes) a)"
        )
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 1, r.src, r.depth, r.row_number, 0, r.ref,
                jsonb_build_object('op', 'upsert', 'ref', r.ref, 'applicationKey', r.application_key,
                    'objectTypeKey', r.object_type_key, 'key', jsonb_build_object('id', r.record_id),
                    'name', coalesce(r.name, r.current_name), 'attributes', {attributes.format(s="r")})
                || CASE WHEN r.parent_id IS NOT NULL
                    THEN jsonb_build_object('parent', jsonb_build_object('id', r.parent_id))
                    ELSE '{{}}'::jsonb END
                || coalesce((
                    SELECT jsonb_build_object('initialRelations', jsonb_agg(DISTINCT jsonb_build_object(
                        'relationTypeKey', l.relation_type_key, 'direction', 'incoming',
                        'object', jsonb_build_object('id', l.target_id))))
                    FROM import_links l JOIN import_rows g ON g.row_id = l.row_id
                    WHERE l.required AND l.target_id IS NOT NULL AND g.error IS NULL
                      AND (g.row_id = r.row_id OR g.rep_id = r.row_id)
                    HAVING count(*) > 0), '{{}}'::jsonb)
            FROM import_rows r WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'upsert'
            """
        )
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 2, r.src, 0, r.row_number, d.grp, r.ref,
                jsonb_build_object('op', 'upsert', 'ref', r.ref, 'applicationKey', d.application_key,
                    'objectTypeKey', d.object_type_key, 'key', jsonb_build_object('id', d.related_id),
                    'name', left(coalesce(d.name, d.current_name, d.fallback_name), {MAX_NAME}),
                    'parent', jsonb_build_object('id', d.parent_id),
                    'attributes', {attributes.format(s="d")})
                || CASE WHEN d.required AND NOT d.existing THEN jsonb_build_object('initialRelations',
                    jsonb_build_array(jsonb_build_object('relationTypeKey', d.relation_type_key,
                        'direction', 'incoming', 'object', jsonb_build_object('id', r.record_id))))
                    ELSE '{{}}'::jsonb END
            FROM (SELECT DISTINCT ON (d.related_id) d.* FROM import_related d
                  JOIN import_rows x ON x.row_id = d.row_id AND x.error IS NULL
                  WHERE d.related_id IS NOT NULL ORDER BY d.related_id, d.entry_id) d
            JOIN import_rows r ON r.row_id = d.row_id
            """
        )
        self._sql(
            """
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 3, r.src, 0, r.row_number, d.grp, r.ref,
                jsonb_build_object('op', 'ensureRelation', 'ref', r.ref,
                    'relationTypeKey', d.relation_type_key,
                    'from', jsonb_build_object('id', CASE WHEN d.direction = 'outgoing'
                        THEN r.record_id ELSE d.related_id END),
                    'to', jsonb_build_object('id', CASE WHEN d.direction = 'outgoing'
                        THEN d.related_id ELSE r.record_id END))
            FROM (SELECT DISTINCT ON (d.related_id) d.* FROM import_related d
                  JOIN import_rows x ON x.row_id = d.row_id AND x.error IS NULL
                  WHERE d.related_id IS NOT NULL ORDER BY d.related_id, d.entry_id) d
            JOIN import_rows r ON r.row_id = d.row_id
            """
        )
        self._sql(
            """
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 3, l.src, 0, l.row_number, 1000 + l.link_no, l.ref,
                jsonb_build_object('op', 'ensureRelation', 'ref', l.ref,
                    'relationTypeKey', l.relation_type_key,
                    'from', jsonb_build_object('id', CASE WHEN l.direction = 'outgoing'
                        THEN l.record_id ELSE l.target_id END),
                    'to', jsonb_build_object('id', CASE WHEN l.direction = 'outgoing'
                        THEN l.target_id ELSE l.record_id END))
            FROM (SELECT DISTINCT ON (r.record_id, l.relation_type_key, l.direction, l.target_id)
                    r.src, r.row_number, r.ref, r.record_id, l.link_no, l.relation_type_key,
                    l.direction, l.target_id
                  FROM import_links l JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
                  WHERE NOT l.replace
                  ORDER BY r.record_id, l.relation_type_key, l.direction, l.target_id, r.row_id,
                    l.link_no) l
            """
        )
        self._sql(
            """
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 3, min(r.src), 0, min(r.row_number), 2000, min(r.ref),
                jsonb_build_object('op', 'replaceRelationSet', 'ref', min(r.ref),
                    'relationTypeKey', l.relation_type_key,
                    'fromObjectTypeKey', CASE WHEN l.direction = 'outgoing'
                        THEN min(r.object_type_key) ELSE l.object_type_key END,
                    'toObjectTypeKey', CASE WHEN l.direction = 'outgoing'
                        THEN l.object_type_key ELSE min(r.object_type_key) END,
                    'direction', l.direction,
                    'anchor', jsonb_build_object('id', r.record_id),
                    'targets', jsonb_agg(DISTINCT jsonb_build_object(
                        'object', jsonb_build_object('id', l.target_id))))
            FROM import_links l JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
            WHERE l.replace
            GROUP BY r.record_id, l.relation_type_key, l.direction, l.object_type_key
            """
        )
        self._sql(
            """
            INSERT INTO import_errors (src, row_number, ref, error)
            SELECT src, row_number, ref, error FROM import_rows WHERE error IS NOT NULL
            """
        )


# A match's row in ``import_matches``; {s} is the match's JSON.
_JOINED = (
    "m.object_type_key = {s} ->> 'type' AND m.field = {s} ->> 'field'"
    " AND m.attr = {s} ->> 'attr' AND m.value = {s} -> 'value'"
)

# A match that found no record or several, as a row's refusal; {s} is the match's JSON.
_MATCH_ERROR = (
    "jsonb_build_object("
    "'code', CASE WHEN m.candidates = 0 THEN 'REFERENCE_NOT_FOUND' ELSE 'REFERENCE_AMBIGUOUS' END,"
    " 'message', CASE WHEN m.candidates = 0"
    " THEN format('No %s record matches %s in column %s', m.object_type_key, {s} -> 'value', {s} ->> 'column')"
    " ELSE format('%s %s records match %s in column %s', m.candidates, m.object_type_key,"
    " {s} -> 'value', {s} ->> 'column') END,"
    " 'details', jsonb_build_object('column', {s} ->> 'column', 'count', m.candidates))"
)


def _area(source: Source) -> Area:
    return Area.of(source.headerRow, source.block)


def _named_columns(source: Source, at: str) -> Iterator[tuple[str, str]]:
    """Every column the source names, with its pointer."""
    if source.key is not None and source.key.column is not None:
        yield f"{at}/key/column", source.key.column
    for index, binding in enumerate(source.columns):
        if binding.columns is not None:
            for position, name in enumerate(binding.columns):
                yield f"{at}/columns/{index}/columns/{position}", name
        elif binding.column is not None:
            yield f"{at}/columns/{index}/column", binding.column
        if binding.relatedRecord is not None and binding.relatedRecord.parent.column is not None:
            yield (
                f"{at}/columns/{index}/relatedRecord/parent/column",
                binding.relatedRecord.parent.column,
            )


# --- the job's outcomes and inputs ------------------------------------------------------------------


def _store(session: Session, job: Job, limits: ImportLimits) -> Bound:
    rejected = session.scalar(text("SELECT count(*) FROM import_errors")) or 0
    items = session.scalar(text("SELECT count(*) FROM import_items")) or 0
    atomic = job.parameters.get("policy") == "atomic"
    for setting, maximum, applies in (
        ("BACKGROUND_JOB_MAX_ITEMS", limits.background_max_items, True),
        ("ATOMIC_JOB_MAX_ITEMS", limits.atomic_max_items, atomic),
    ):
        if applies and items > maximum:
            raise api_error(
                422,
                "IMPORT_TOO_MANY_ITEMS",
                f"The file's rows make {items} items; at most {maximum} run in one "
                f"{'atomic' if atomic and setting.startswith('ATOMIC') else 'background'} job",
                {"setting": setting, "maximum": maximum, "items": items},
            )
    session.execute(
        text(
            "INSERT INTO job_items"
            " (job_id, item_index, ref, source_index, row_number, status, outcome)"
            " SELECT :job, row_number() OVER (ORDER BY src, row_number) - 1, left(ref, 200),"
            " src, row_number, 'rejected', jsonb_build_object('error', error)::json"
            " FROM import_errors"
        ),
        {"job": job.sequence_id},
    )
    session.execute(
        text(
            "INSERT INTO job_inputs (job_id, item_index, ref, source_index, row_number, item)"
            " SELECT :job, :offset + row_number() OVER"
            " (ORDER BY phase, src, depth, row_number, sub) - 1, left(ref, 200), src, row_number,"
            " item::json FROM import_items"
        ),
        {"job": job.sequence_id, "offset": rejected},
    )
    return Bound(rejected=rejected, items=items)
