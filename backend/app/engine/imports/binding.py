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

**Records missing from the file** (0.10 A5c, D82): a source loading its records by a key finds
the records of its type the context holds with the key filled and no row of the file names, in one
statement; the report counts them per source, and a source with ``missing: "delete"`` deletes them
after every other item. A profile's check (``kind: profileCheck``) also reads what binding found
before the temporary tables go: the new values of match columns, the rows naming a found record by
another name (drift) and the missing records (:func:`_findings`).

**The binding report** (0.9 J3, D86) says per source and column what binding made of the cells:
read, empty, converted, value-mapped, refused; for a match column (a parent, a relationship, a flag)
how many values found one record, none or several. The cell counts are kept while the rows stream;
the match counts are one statement over the temporary tables once every match is resolved.

A JSON Lines file is batch items already, and an export's CSV or XLSX tables (D71) map row by row,
so both skip the matching. Python never holds the set: rows go to the database in chunks, and the
statements per import do not grow with its rows.
"""

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any
from uuid import UUID

from openpyxl.utils.cell import column_index_from_string
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import cast, column, insert, select, table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...common.copy_rows import CopyRows
from ...errors import ApiError, api_error
from ...models.commands import BatchItem
from ...models.database import Job
from ...models.imports import ColumnBinding, ImportProfileDefinition, MatchBy, Source
from ...models.schema import EngineModel
from ..jobs.batches import MISSING_REF
from ..model.candidate_places import identifying_fields
from ..model.traversal import ancestor_type_keys
from ..reads.context_sets import record_source, relation_source
from ..reads.snapshot_reads import SnapshotContext, change_set_context
from ..records.counterparts import counterpart
from .cells import attribute_value, cell_text, flag_set, is_empty
from .places import Place, PlaceReads, PlaceRequest, resolve_places
from .profiles import check_profile, invalid_profile, source_order
from .readers import Area, Table, TabularFile, jsonl_lines, open_tabular
from .readings import apply_readings, clashes, reading_columns, virtual_columns

# Rows written to the database per round of COPY statements.
CHUNK_ROWS = 5_000
# A cancel request and the lease are looked at after this many rows are read.
CHECK_ROWS = 10_000
MAX_NAME = 500
# A related record's version cell holding this leaves the record out of its row (0.9 J6a, D195).
NOT_LOADED = "not loaded"
_ITEM = TypeAdapter(BatchItem)
# Opens the rows a profile binds: the format and the CSV delimiter in, the rows out.
type BookOpener = Callable[[str, str], TabularFile]
_RECORD_COLUMNS = ("objectTypeKey", "applicationKey", "id", "version", "name", "parentObjectId")

_TEMPORARY_TABLES = (
    (
        "CREATE TEMPORARY TABLE import_rows (row_id integer PRIMARY KEY, src integer NOT NULL,"
        " row_number integer NOT NULL, ref text NOT NULL, object_type_key text, application_key text,"
        " mode text, key_kind text, key_attr text, key_value jsonb, key_column text, name text,"
        " attributes jsonb NOT NULL DEFAULT '{}', parent jsonb, error jsonb, rep_id integer,"
        " record_id text, existing boolean NOT NULL DEFAULT false, current_name text, parent_id text,"
        " depth integer NOT NULL DEFAULT -1, expected_version integer) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_rows (object_type_key, name)",
    "CREATE INDEX ON import_rows (record_id)",
    (
        "CREATE TEMPORARY TABLE import_links (row_id integer NOT NULL, link_no integer NOT NULL,"
        " relation_type_key text, direction text, object_type_key text, match jsonb, column_name text,"
        " replace boolean, required boolean, candidates integer, target_id text,"
        " expected_version integer, attributes jsonb, scope text NOT NULL DEFAULT '')"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_related (entry_id integer PRIMARY KEY, row_id integer NOT NULL,"
        " grp integer NOT NULL, relation_type_key text, direction text, application_key text,"
        " object_type_key text, parent jsonb, match_attr text, name text, fallback_name text,"
        " attributes jsonb NOT NULL DEFAULT '{}', required boolean, column_name text,"
        " parent_candidates integer, parent_id text, related_candidates integer, related_id text,"
        " existing boolean NOT NULL"
        " DEFAULT false, current_name text, expected_version integer, hint text) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_matches (match_id serial PRIMARY KEY, object_type_key text,"
        " field text, attr text, scope text NOT NULL DEFAULT '', label_attr text NOT NULL DEFAULT '',"
        " container text NOT NULL DEFAULT '', value jsonb, candidates integer NOT NULL DEFAULT 0,"
        " resolved text, creates boolean NOT NULL DEFAULT false, created boolean NOT NULL DEFAULT false,"
        " UNIQUE (object_type_key, field, attr, scope, label_attr, container, value))"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_context (object_id text PRIMARY KEY, object_type_key text,"
        " name text, parent_object_id text, attributes jsonb, version integer,"
        " application_key text) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_context (object_type_key, name)",
    # The attribute values a key or a match reads, of the context's records and of the file's rows,
    # one row each, so a lookup by attribute is an equality join PostgreSQL can hash (0.10 A5c): a
    # join on ``attributes -> attr`` naming both tables compares every row with every record.
    (
        "CREATE TEMPORARY TABLE import_context_values (object_type_key text, attr text, value jsonb,"
        " object_id text, PRIMARY KEY (object_type_key, attr, value, object_id)) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE import_row_values (object_type_key text, attr text, value jsonb,"
        " record_id text) ON COMMIT DROP"
    ),
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
    # The context's records of a keyed source's type that no row names (0.10 A5c, D82).
    (
        "CREATE TEMPORARY TABLE import_missing (src integer, object_id text PRIMARY KEY, name text,"
        " key_value jsonb, version integer) ON COMMIT DROP"
    ),
    # The records of each link-matrix column and what each could be listed by: one row per record and
    # field, over the fields that identify the cell type (0.17 EX1, PP-D25).
    (
        "CREATE TEMPORARY TABLE import_scope_values (scope text, object_type_key text, field text,"
        " value text, object_id text) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_scope_values (scope, field, value)",
    # The records each match found, kept where it found several: a row already related to some of
    # them by the link's relationship means those (an unchanged cell names its own links).
    (
        "CREATE TEMPORARY TABLE import_match_candidates (match_id integer, object_id text)"
        " ON COMMIT DROP"
    ),
    "CREATE TEMPORARY TABLE import_fields (scope text, field text, rank integer) ON COMMIT DROP",
    # The rows of a value sheet (PP-D27) with each field a link cell may name them by: a main-sheet
    # value naming one is that record, whether its row updates a record or creates a new one.
    (
        "CREATE TEMPORARY TABLE import_value_rows (scope text, object_type_key text, field text,"
        " value text, record_id text) ON COMMIT DROP"
    ),
    "CREATE INDEX ON import_value_rows (scope, field, value)",
    # The place a new cell record goes where the file's column holds none yet, created with the
    # first record that goes in it (0.17 PP-D24).
    (
        "CREATE TEMPORARY TABLE import_new_places (place_id text PRIMARY KEY, object_type_key text,"
        " name text, column_id text, attributes jsonb, application_key text) ON COMMIT DROP"
    ),
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
    # A profile check's findings (0.10 A5c): new values, drift and missing records.
    findings: dict[str, list[dict[str, Any]]] | None = None


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


def _lettered(
    source: Source, found: Table, columns: dict[str, int], at: str, mismatch: _Mismatch
) -> Source:
    """The source with each binding that names its column by a letter (0.13 AQ) naming it by the
    header the letter holds, or, for a column whose header cell is empty, by ``Column AJ``, which is
    added to ``columns``. A letter beyond the table's last column is added to ``mismatch``."""
    if not any(binding.letter is not None for binding in source.columns):
        return source
    named: dict[int, str] = {}
    for name, position in columns.items():
        named.setdefault(position, name)
    resolved = []
    for index, binding in enumerate(source.columns):
        if binding.letter is None:
            resolved.append(binding)
            continue
        position = column_index_from_string(binding.letter) - found.first_column
        if not 0 <= position < len(found.header):
            mismatch.add(
                f"{at}/columns/{index}/letter",
                "COLUMN_NOT_FOUND",
                f"The header row has no column {binding.letter}",
            )
            resolved.append(binding)
            continue
        name = named.get(position) or f"Column {binding.letter}"
        columns.setdefault(name, position)
        resolved.append(binding.model_copy(update={"column": name, "letter": None}))
    return source.model_copy(update={"columns": resolved})


def _source_columns(
    book: TabularFile, source: Source, at: str, xlsx: bool, mismatch: _Mismatch
) -> tuple[dict[str, int], Source] | None:
    """The columns of the source's table and the source with its letters resolved, its missing
    sheet, header row and columns added to ``mismatch``; ``None`` when there is no table to read."""
    if xlsx and source.sheet is not None and source.sheet not in book.sheet_names:
        mismatch.add(
            f"{at}/sheet",
            "SHEET_NOT_FOUND",
            f"The workbook has no sheet '{source.sheet}'; it has {', '.join(book.sheet_names)}",
        )
        return None
    found = book.table(source.sheet if xlsx else None, _area(source))
    if found is None:
        mismatch.add(
            f"{at}/headerRow",
            "HEADER_ROW_NOT_FOUND",
            f"The sheet ends before its header row {source.headerRow}",
        )
        return None
    columns = found.columns()
    for path, name in clashes(source, found):
        mismatch.add(
            f"{at}{path}",
            "COLUMN_CLASH",
            f"The table already has a column '{name}'; a reading of the source adds one of that name",
        )
    source = _lettered(source, found, columns, at, mismatch)
    for offset, name in enumerate(virtual_columns(source)):
        columns.setdefault(name, len(found.header) + offset)
    for path, name in named_columns(source, at):
        if name not in columns:
            mismatch.add(path, "COLUMN_NOT_FOUND", f"The header has no column '{name}'")
    return columns, source


def source_mismatch(book: TabularFile, source: Source, at: str) -> list[dict[str, str]]:
    """What of the workbook's source its file lacks: the problems a binding would raise for it."""
    mismatch = _Mismatch()
    _source_columns(book, source, at, True, mismatch)
    return mismatch.problems


def bind_import(
    session: Session,
    job: Job,
    path: Path,
    model: EngineModel,
    check: Callable[[], None],
    limits: ImportLimits,
    open_book: BookOpener | None = None,
) -> Bound:
    """Bind the file at ``path`` into the job's outcomes and inputs; the caller commits. ``check``
    is called every :data:`CHECK_ROWS` rows read and raises to stop. ``open_book`` reads the rows
    from elsewhere than the file, as a dry run reads a source file's staged cells (0.10 A3, D66);
    it serves a binding through a profile only."""
    if open_book is None and not path.is_file():
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
        opener = open_book or partial(open_tabular, path)
        _ProfileBinding(session, job, model, profile, context, rows, report).run(
            opener, file_format
        )
    else:
        report = _Report()
        _bind_table_layout(session, path, file_format, model, rows, report)
    stored = _store(session, job, limits)
    return Bound(
        stored.rejected,
        stored.items,
        report.finish(session) if report else None,
        _findings(session) if job.kind == "profileCheck" and definition is not None else None,
    )


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
        # How each relationship or matrix column was read (PP-D26), by source and column.
        self.readings: dict[tuple[int, str], dict[str, Any]] = {}

    def source(self, src: int, sheet: str, object_type_key: str | None) -> None:
        self.sources[src] = {
            "sheet": sheet,
            "objectTypeKey": object_type_key,
            "rows": 0,
            "rejectedRows": 0,
            "skippedRows": 0,
        }
        self.columns[src] = {}

    def row(self, src: int) -> None:
        self.sources[src]["rows"] += 1

    def skip(self, src: int) -> None:
        """A row read and then skipped: no row of the source's, one skipped (D110)."""
        self.sources[src]["rows"] -= 1
        self.sources[src]["skippedRows"] += 1

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
        missing = dict(
            session.execute(text("SELECT src, count(*) FROM import_missing GROUP BY src")).all()
        )
        report = []
        for src in sorted(self.sources):
            columns = []
            for entry in self.columns[src].values():
                if "resolved" in entry:
                    counts = found.get((src, entry["column"]), (0, 0, 0))
                    entry["resolved"], entry["notFound"], entry["ambiguous"] = counts
                reading = self.readings.get((src, entry["column"]))
                if reading is not None and reading["binding"] == entry["binding"]:
                    entry["reading"] = reading
                columns.append(entry)
            source = self.sources[src] | {
                "rejectedRows": rejected.get(src, 0),
                "missingRecords": missing.get(src, 0),
            }
            report.append(source | {"columns": columns})
        return report


def _field_label(model: EngineModel, field_: str) -> str:
    """A matching field in words: ``Name``, an attribute's name, or the older label reading."""
    if field_ == "name":
        return "Name"
    if field_ == "@label":
        return "Name with its display field"
    attribute = model.attribute_type(field_)
    return attribute.name if attribute is not None else field_


def _best_field(found: list[Any], model: EngineModel) -> tuple[str, str | None]:
    """The field a column is read by, and what to say when the choice was not clear (PP-D26): the
    one every value finds one record by, else the one most do, a tie going to the field offered
    first. ``found`` is (field, rank, cells, matched, ambiguous) per field."""
    cells = found[0][2]
    if not cells:
        return found[0][0], None
    ranked = sorted(found, key=lambda item: (-item[3], item[4], item[1]))
    best = ranked[0]
    tied = [item for item in ranked if item[3] == best[3] and item[4] == best[4]]
    names = " and ".join(_field_label(model, item[0]) for item in tied)
    chosen = _field_label(model, best[0])
    if best[3] == cells:
        if len(tied) == 1:
            return best[0], None
        return best[0], f"{names} each match every value; {chosen} was chosen."
    if len(tied) > 1:
        return (
            best[0],
            f"No field matches every value: {names} each match {best[3]} of {cells}; {chosen} was chosen.",
        )
    note = f"No field matches every value: {chosen} matches the most, {best[3]} of {cells}."
    return best[0], note


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


# Each relationship of the context from both of its ends, as plain equalities (``near`` is the end the
# row's record stands at): the first CTE of every statement that follows a record's relationships.
_ENDS = """ends AS (
        SELECT relation_type_key, 'outgoing' AS direction, from_id AS near, to_id AS far
        FROM import_context_relations
        UNION ALL
        SELECT relation_type_key, 'incoming', to_id, from_id FROM import_context_relations),"""


# --- writing rows ----------------------------------------------------------------------------------


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


def _items_copy(session: Session) -> CopyRows:
    return CopyRows(
        session, "import_items", ("phase", "src", "depth", "row_number", "sub", "ref", "item")
    )


def _errors_copy(session: Session) -> CopyRows:
    return CopyRows(session, "import_errors", ("src", "row_number", "ref", "error"))


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
                if _holds_unstorable(dumped):
                    errors.add(
                        0, number, ref, _error("INVALID_CELL", _UNSTORABLE_MESSAGE.format("Line"))
                    )
                else:
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
            guarded = _guarded_positions(model, columns) if file_format == "csv" else ()
            for number, cells in found.rows:
                rows.tick()
                report.row(src)
                ref = f"{sheet}!{number}"
                if guarded:
                    cells = _unquoted(cells, guarded)
                unstorable = next(
                    (
                        name
                        for name, position in columns.items()
                        if position < len(cells)
                        and isinstance(cells[position], str)
                        and _UNSTORABLE.search(cells[position])
                    ),
                    None,
                )
                try:
                    if unstorable is not None:
                        raise _RowError(
                            _error(
                                "INVALID_CELL",
                                _UNSTORABLE_MESSAGE.format(f"Column {unstorable}"),
                                column=unstorable,
                            )
                        )
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


# A CSV export writes a text starting with a formula character, or with quotes then one, with one
# quote in front (``jobs/exports._csv_text``); the import takes exactly one off.
_ESCAPED_TEXT = re.compile(r"^'+[=+\-@\t\r]")


def _guarded_positions(model: EngineModel, columns: dict[str, int]) -> tuple[int, ...]:
    """The positions of the CSV columns the export escapes: the name and the text attributes."""
    positions = [columns["name"]] if "name" in columns else []
    for name, position in columns.items():
        if name.startswith("#"):
            definition = model.attribute_type(name[1:])
            if definition is not None and definition.valueType in {"text", "longText"}:
                positions.append(position)
    return tuple(positions)


def _unquoted(cells: list[Any], positions: tuple[int, ...]) -> list[Any]:
    """``cells`` with the export's single quote taken off the escaped texts."""
    cells = list(cells)
    for position in positions:
        if position < len(cells):
            value = cells[position]
            if isinstance(value, str) and _ESCAPED_TEXT.match(value):
                cells[position] = value[1:]
    return cells


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


# A character PostgreSQL cannot store in a text or JSON value: NUL, and a surrogate half that no
# pair completes (a lone one cannot be encoded as UTF-8).
_UNSTORABLE = re.compile("[\x00\ud800-\udfff]")


_UNSTORABLE_MESSAGE = "{} holds a character that cannot be stored (a NUL or an unpaired surrogate)"


def _holds_unstorable(value: Any) -> bool:
    if isinstance(value, str):
        return _UNSTORABLE.search(value) is not None
    if isinstance(value, dict):
        return any(_holds_unstorable(k) or _holds_unstorable(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_holds_unstorable(v) for v in value)
    return False


def _unstorable(plan: _Plan, cells: list[Any], failures: list[dict[str, Any]]) -> list[Any]:
    """``cells`` with each one that holds an unstorable character emptied, and a refusal of its
    column in ``failures``: the character would fail the whole bind at the ``COPY``."""
    found = [
        position
        for position, value in enumerate(cells)
        if isinstance(value, str) and _UNSTORABLE.search(value)
    ]
    if not found:
        return cells
    names = {position: name for name, position in reversed(plan.columns.items())}
    cells = list(cells)
    for position in found:
        cells[position] = None
        name = names.get(position)
        if name is not None:
            failures.append(
                _error(
                    "INVALID_CELL",
                    _UNSTORABLE_MESSAGE.format(f"Column {name}"),
                    column=name,
                )
            )
    return cells


def _key_cell_failed(source: Source, failures: list[dict[str, Any]]) -> bool:
    """Whether a cell of the source's key failed to read, as against being empty."""
    key = source.key
    columns = {name for name in (key.column, key.nameColumn) if name is not None}
    keyed = set(key.attributeTypeKeys or [])
    if key.attributeTypeKey is not None:
        keyed.add(key.attributeTypeKey)
    columns |= {b.column for b in source.columns if b.attributeTypeKey in keyed}
    if key.field == "name":
        columns |= {b.column for b in source.columns if b.field == "name"}
    return any(
        failure["code"] != "MISSING_RECORD_KEY" and failure["details"].get("column") in columns
        for failure in failures
    )


# A match value is a key of the matches' unique index, whose entries PostgreSQL limits to about 2.7 KB:
# a longer value would fail the whole bind, and no name or key is that long.
_MATCH_VALUE_BYTES = 2000


def _short_enough(value: Any, column_name: str | None) -> None:
    """Refuse a match value too long to be looked up."""
    # A character is at most four bytes: only a long text is encoded to be measured.
    if (
        isinstance(value, str)
        and len(value) * 4 > _MATCH_VALUE_BYTES
        and len(value.encode("utf-8", "replace")) > _MATCH_VALUE_BYTES
    ):
        raise _RowError(
            _error(
                "INVALID_CELL",
                f"Column {column_name} holds a value too long to find a record by"
                f" (over {_MATCH_VALUE_BYTES} bytes)",
                column=column_name,
            )
        )


def _uuid(value: Any, column_name: str) -> str:
    try:
        return str(UUID(cell_text(value).strip()))
    except ValueError:
        raise _RowError(
            _error("INVALID_CELL", f"Column {column_name} must hold an ID", column=column_name)
        ) from None


def _version(value: Any, column_name: str, lowest: int = 1) -> int:
    """A version cell: a record's or a relationship's from 1, a relation set's from 0 (a set no
    write has touched yet)."""
    text_value = cell_text(value).strip()
    # ``isdigit`` accepts digits ``int`` does not (superscripts) and other scripts' digits ``int``
    # reads: only ASCII digits are a version.
    if not (text_value.isascii() and text_value.isdigit()) or int(text_value) < lowest:
        raise _RowError(
            _error(
                "INVALID_CELL",
                f"Column {column_name} must hold a version ({lowest} or more)",
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
        self.match_cells = CopyRows(session, "import_match_cells", ("src", "column_name", "match"))
        # Where new cell records go, by column record (0.17 PP-D24), and the places to create.
        self.places: dict[tuple[str, str, str, str, str], Place] = {}
        self.place_reads = PlaceReads()
        self.new_places: dict[str, Place] = {}
        self.place_columns: dict[str, str] = {}
        # Per source and column, how a link-matrix column was read (PP-D26), for the report.
        self.readings: dict[tuple[int, str], dict[str, Any]] = {}
        self.row_id = 0
        self.plans: list[_Plan] = []
        # Each source's named columns, by plan index (rows empty in all of them are skipped).
        self._names: dict[int, list[str]] = {}
        self.entry_id = 0
        self.rows = CopyRows(
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
                "expected_version",
            ),
        )
        self.links = CopyRows(
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
                "expected_version",
                "attributes",
                "scope",
            ),
        )
        self.related = CopyRows(
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
                "expected_version",
                "hint",
            ),
        )

    # --- reading ---

    def run(self, open_book: BookOpener, file_format: str) -> None:
        delimiter = self.profile.csv.delimiter if self.profile.csv is not None else ","
        book = open_book(file_format, delimiter)
        try:
            plans = self.plans = self._plans(book, file_format == "xlsx")
            self._places()
            for plan in plans:
                found = book.table(
                    plan.source.sheet if file_format == "xlsx" else None, _area(plan.source)
                )
                found = apply_readings(found, plan.source)
                for number, cells in found.rows:
                    self.counter.tick()
                    self._row(plan, number, cells)
                    if len(self.rows.rows) >= CHUNK_ROWS:
                        self._flush()
            self._flush()
        finally:
            book.close()
        self._resolve()
        self.report.readings = self._reading_report()

    def _plans(self, book: TabularFile, xlsx: bool) -> list[_Plan]:
        """Each source's columns, in the order the sources load; every missing sheet, header row
        and column is a problem, raised together before a row is read."""
        mismatch = _Mismatch()
        plans = []
        order = source_order(self.model, self.profile) or list(range(len(self.profile.sources)))
        for position, index in enumerate(order):
            source = self.profile.sources[index]
            at = f"/sources/{index}"
            found = _source_columns(book, source, at, xlsx, mismatch)
            if found is None:
                continue
            columns, source = found
            sheet = (source.sheet or book.sheet_names[0]) if xlsx else book.sheet_names[0]
            plans.append(_Plan(index, position, source, sheet, columns))
            self.report.source(position, sheet, source.objectTypeKey)
        mismatch.raise_if_any()
        return plans

    def _row(self, plan: _Plan, number: int, cells: list[Any]) -> None:
        # A row holding nothing in any column the source names is no record of it: a list or
        # parent read from the rows of another type's sheet, on a row without one (0.10 A6b, D99).
        names = self._names.get(plan.index)
        if names is None:
            names = self._names[plan.index] = [name for _, name in named_columns(plan.source, "")]
        if names and all(_cell(plan.columns, cells, name) is None for name in names):
            return
        self.row_id += 1
        row_id = self.row_id
        source = plan.source
        ref = f"{plan.sheet}!{number}"
        self.report.row(plan.order)
        state = _RowState()
        failures: list[dict[str, Any]] = []
        cells = _unstorable(plan, cells, failures)
        for binding in source.columns:
            if binding.ignore:
                continue
            try:
                self._binding(plan, binding, cells, state)
            except _RowError as rejected:
                failures.append(rejected.body)
        if source.parent is not None:
            # 0.10 A8c (D141): the source's one parent, on every row; no column names it.
            fixed = source.parent
            try:
                state.parent = self._match(fixed.objectTypeKey, fixed.matchBy, fixed.value, None)
                if fixed.missing == "create":
                    state.parent["create"] = True
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
            elif source.key is not None and source.key.attributeTypeKeys is not None:
                # 0.16 AP-D43: the values of several attributes together; one empty cell leaves the
                # row without a key. The row holds the attribute keys and the columns as JSON lists
                # in the key's order, and the values as an object by attribute key.
                keys = source.key.attributeTypeKeys
                columns = [
                    next(b.column for b in source.columns if b.attributeTypeKey == attribute)
                    for attribute in keys
                ]
                key_kind = "combination"
                key_attr, key_column = json.dumps(keys), json.dumps(columns)
                values = {attribute: state.attributes.get(attribute) for attribute in keys}
                empty = [
                    column
                    for attribute, column in zip(keys, columns, strict=True)
                    if values[attribute] is None
                ]
                if not empty:
                    key_value = values
                elif not all(column in failed for column in empty):
                    raise _RowError(
                        _error(
                            "MISSING_RECORD_KEY",
                            f"The key column {empty[0]} is empty",
                            column=empty[0],
                        )
                    )
            elif source.key is not None and source.key.field == "name":
                # 0.10 A8a (D117): the record of the type named as the row names it.
                key_kind = "name"
                key_column = next(b.column for b in source.columns if b.field == "name")
                key_value = state.name
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
                if key_value is None and source.key.nameColumn is not None:
                    key_column = source.key.nameColumn
                    entry = self.report.cell(plan.order, key_column, "key", "name")
                    key_value = _tally(
                        entry,
                        _cell(plan.columns, cells, key_column),
                        False,
                        lambda raw: _name(raw, key_column),
                    )
                    key_kind = "name"
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
        if source.under is not None and key_value is None and not failures:
            # A value sheet's row without an ID is a new record in the column's place (PP-D27).
            under = source.under
            place = self._value_place(source)
            if not under.creates:
                failures.append(
                    _error(
                        "REFERENCE_NOT_FOUND",
                        "This sheet only edits the records it lists; a row without a record ID would"
                        " add one, and this view does not add records",
                        column=source.key.column,
                    )
                )
            elif place is None or place.container_id is None:
                failures.append(
                    _error(
                        "REFERENCE_NOT_FOUND",
                        (place.message if place is not None and place.message else None)
                        or "There is no place for a new record in this column; create one in the app",
                        column=source.key.column,
                    )
                )
            else:
                state.parent = {
                    "type": place.type_key,
                    "field": "id",
                    "attr": "",
                    "value": place.container_id,
                    "column": source.key.column,
                }
        if (
            key_value is None
            and source.key is not None
            and source.rowsWithoutKey == "skip"
            and not _key_cell_failed(source, failures)
        ):
            # A row without a key is no record of the source (0.10 A7, D110): counted, not loaded.
            # A key cell that fails is no empty one: the row is refused below, as any refused row.
            self.report.skip(plan.order)
            return
        expected_version = None
        if source.key is not None and source.key.versionColumn is not None:
            version_column = source.key.versionColumn
            entry = self.report.cell(plan.order, version_column, "key", "version")
            try:
                expected_version = _tally(
                    entry,
                    _cell(plan.columns, cells, version_column),
                    False,
                    lambda raw: _version(raw, version_column),
                )
            except _RowError as rejected:
                failures.append(rejected.body)
        error = None
        if failures:
            error = _cells_error(failures)
            # The row keeps the key it read: a refused row still names its record, so the record is
            # not counted as missing from the file (no delete item under ``missing: "delete"``).
            state.links, state.related = [], {}
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
            expected_version if key_value is not None else None,
        )
        for link_no, link in enumerate(state.links):
            self.links.add(row_id, link_no, *link)
        for group, entry in state.related.items():
            if entry["skip"] or (not entry["attributes"] and entry["name"] is None):
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
                entry["version"],
                entry["hint"],
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
                entry,
                src,
                parent.objectTypeKey,
                parent.matchBy,
                raw,
                binding.column,
                parent.missing == "create",
            )
        elif binding.relation is not None:
            state.links += self._relations(plan, binding, raw, cells)
        elif binding.relatedRecord is not None:
            self._related(plan, binding, raw, mapped, cells, state.related)

    def _raw(
        self, plan: _Plan, binding: ColumnBinding, column_name: str, cells: list[Any]
    ) -> tuple[Any, bool]:
        """The cell, through the binding's value map; ``True`` when the map replaced it."""
        raw = _cell(plan.columns, cells, column_name)
        if binding.relation is not None and binding.relation.split is not None:
            # A split cell is mapped piece by piece (:meth:`_relations`), never as a whole first.
            return raw, False
        if binding.valueMap is not None and raw is not None:
            mapping = self.profile.valueMaps[binding.valueMap]
            key = cell_text(raw)
            if key in mapping:
                mapped = mapping[key]
                return (None if is_empty(mapped) else mapped), True
        return raw, False

    def _mapped(self, value_map: str | None, raw: Any) -> Any:
        """A relationship value's cell through its value map, as :meth:`_raw` reads a column's."""
        if value_map is None or raw is None:
            return raw
        mapping = self.profile.valueMaps[value_map]
        key = cell_text(raw)
        if key not in mapping:
            return raw
        return None if is_empty(mapping[key]) else mapping[key]

    def _value(self, attribute_type_key: str, raw: Any, column_name: str) -> Any:
        try:
            return attribute_value(self.model.attribute_type(attribute_type_key), raw)
        except ApiError as error:
            raise _RowError(_from_api(error, column_name)) from None

    def _match(
        self, object_type_key: str, match: MatchBy, raw: Any, column_name: str | None
    ) -> dict[str, Any]:
        """A match's JSON; ``column_name`` is ``None`` for a source's fixed parent (D141)."""
        if match.attributeTypeKey is not None:
            value = self._value(match.attributeTypeKey, raw, column_name)
        elif match.field == "id":
            value = _uuid(raw, column_name)
        else:
            value = cell_text(raw)
        _short_enough(value, column_name)
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
        create: bool = False,
    ) -> dict[str, Any]:
        """A match cell's value, kept for the report's resolution counts. ``create``: a match that
        finds no record creates one by the cell's name (0.10 A5, D77)."""
        try:
            found = self._match(object_type_key, match, raw, column_name)
        except _RowError:
            entry["refused"] += 1
            raise
        if create:
            found["create"] = True
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

    def _relations(
        self, plan: _Plan, binding: ColumnBinding, raw: Any, cells: list[Any]
    ) -> list[tuple[Any, ...]]:
        relation = binding.relation
        entry = self.report.cell(
            plan.order, binding.column, "relation", relation.relationTypeKey, matched=True
        )
        match_by = relation.matchBy
        if relation.idColumn is not None:
            # One relationship per row (0.9 J6): its record's ID, when the row holds one, finds it.
            held = _cell(plan.columns, cells, relation.idColumn)
            if held is not None:
                raw, match_by = held, MatchBy(field="id")
        version, attributes, failures = None, None, []
        if relation.versionColumn is not None:
            try:
                version = _tally(
                    self.report.cell(plan.order, relation.versionColumn, "key", "version"),
                    _cell(plan.columns, cells, relation.versionColumn),
                    False,
                    lambda raw: _version(raw, relation.versionColumn, 0 if relation.replace else 1),
                )
            except _RowError as error:
                failures.append(error.body)
        if relation.attributes:
            attributes = {}
            for value in relation.attributes:
                try:
                    converted = _tally(
                        self.report.cell(
                            plan.order, value.column, "attributeTypeKey", value.attributeTypeKey
                        ),
                        self._mapped(value.valueMap, _cell(plan.columns, cells, value.column)),
                        False,
                        lambda raw, value=value: self._value(
                            value.attributeTypeKey, raw, value.column
                        ),
                    )
                except _RowError as error:
                    failures.append(error.body)
                    continue
                if converted is not None:
                    attributes[value.attributeTypeKey] = converted
        if failures:
            raise _RowError(failures[0] if len(failures) == 1 else _cells_error(failures))
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
        required = self._required(
            plan, relation.relationTypeKey, relation.direction, relation.objectTypeKey
        )
        within = relation.within
        if not pieces:
            entry["empty"] += 1
            # A column's part of a set changes nothing when its cell is empty (0.17 EX1).
            if not relation.replace or within is not None:
                return []
            # An empty cell makes the set empty (0.9 R-F5, D187): a link that names no record,
            # which the set replacement takes as no target.
            return [
                (
                    relation.relationTypeKey,
                    relation.direction,
                    relation.objectTypeKey,
                    None,
                    binding.column,
                    True,
                    required,
                    version,
                    attributes,
                    "",
                )
            ]
        if within is not None:
            return [
                (
                    relation.relationTypeKey,
                    relation.direction,
                    relation.objectTypeKey,
                    self._labelled(plan, relation, within, entry, piece, binding.column),
                    binding.column,
                    True,
                    required,
                    version,
                    attributes,
                    within.value,
                )
                for piece in pieces
            ]
        return [
            (
                relation.relationTypeKey,
                relation.direction,
                relation.objectTypeKey,
                self._matched(
                    entry,
                    plan.order,
                    relation.objectTypeKey,
                    match_by,
                    piece,
                    binding.column,
                    relation.missing == "create" and match_by is relation.matchBy,
                ),
                binding.column,
                relation.replace,
                required,
                version,
                attributes,
                "",
            )
            for piece in pieces
        ]

    def _labelled(
        self,
        plan: _Plan,
        relation: Any,
        within: Any,
        entry: dict[str, Any],
        piece: Any,
        column_name: str,
    ) -> dict[str, Any]:
        """A link-matrix cell's value (0.17 EX1): a record under the column record named by the field
        the file records (``within.field``), by its label (``name (display)``) or name for a file
        from before the field was recorded, or by a field not yet known (``attr`` empty): the binding
        guesses it from the column's records once they are read (PP-D26). Kept for the report like any
        match; a value that finds none creates one in the place the model gives when the binding
        allows it (PP-D24)."""
        _short_enough(cell_text(piece), column_name)
        place = self._place(plan.source.objectTypeKey, relation, within.value, within.container)
        container = place.container_id if place is not None and place.container_id else ""
        found = {
            "type": relation.objectTypeKey,
            "field": "cell",
            "attr": within.field or ("@label" if within.labelAttributeTypeKey else ""),
            "scope": within.value,
            "labelAttr": within.labelAttributeTypeKey or "",
            "container": container,
            "value": cell_text(piece),
            "column": column_name,
        }
        if relation.missing == "create" and container:
            # Any recorded field creates (PP-D27): the record's name is the value, and the attribute
            # holds it too when the field is not the name. A guessed field other than the name does
            # not (the choice drops the flag).
            found["create"] = True
        self.match_cells.add(plan.order, column_name, found)
        return found

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
                        flags.missing == "create",
                    ),
                    column_name,
                    False,
                    required,
                    None,
                    None,
                    "",
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
            parent.objectTypeKey if parent else None,
            parent.matchBy.field if parent else None,
            parent.matchBy.attributeTypeKey if parent else None,
            parent.value if parent else None,
            parent.column if parent else None,
            parent.valueMap if parent else None,
            spec.matchBy.attributeTypeKey if spec.matchBy else None,
            spec.idColumn,
            spec.under.value if spec.under else None,
        )
        group = plan.groups.setdefault(identity, len(plan.groups))
        entry = entries.get(group)
        if entry is None:
            parent_match = None
            if parent is not None:
                parent_raw = (
                    parent.value
                    if parent.value is not None
                    else _cell(plan.columns, cells, parent.column)
                )
                if parent.valueMap is not None and parent_raw is not None:
                    mapping = self.profile.valueMaps[parent.valueMap]
                    if cell_text(parent_raw) in mapping:
                        parent_raw = mapping[cell_text(parent_raw)]
                        parent_raw = None if is_empty(parent_raw) else parent_raw
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
                if parent_match is not None and parent.missing == "create":
                    # A parent no record matches is created by its name (0.10 A6, D93).
                    parent_match["create"] = True
            if spec.under is not None:
                place = self._place(plan.source.objectTypeKey, spec, spec.under.value, None)
                if place is not None and place.container_id is not None:
                    # The place is a record of the context, or one this load creates first.
                    parent_match = {
                        "type": place.type_key,
                        "field": "id",
                        "attr": "",
                        "value": place.container_id,
                        "column": spec.idColumn or binding.column,
                    }
            hint = None
            if spec.idColumn is not None:
                held = _cell(plan.columns, cells, spec.idColumn)
                if held is not None:
                    hint = _uuid(held, spec.idColumn)
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
                "column": spec.idColumn or binding.column,
                "version": None,
                "skip": False,
                "hint": hint,
            }
            entries[group] = entry
        if spec.versionColumn is not None and entry["version"] is None and not entry["skip"]:
            self._related_version(plan, spec.versionColumn, cells, entry)
        if entry["skip"]:
            # A pair the file shows as several records is left out whole (D195): its cells are a
            # summary, never converted.
            return
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
        if entry["parent"] is None and entry["hint"] is None:
            if spec.under is not None:
                found_place = self._place(plan.source.objectTypeKey, spec, spec.under.value, None)
                raise _RowError(
                    _error(
                        "REFERENCE_NOT_FOUND",
                        (
                            found_place.message
                            if found_place is not None and found_place.message
                            else None
                        )
                        or "There is no place for a new record in this column; create one in the app",
                        column=spec.idColumn or binding.column,
                    )
                )
            if parent is None:
                raise _RowError(
                    _error(
                        "REFERENCE_NOT_FOUND",
                        "A new record here has no place to go: the column names no container and"
                        " its cell has no record ID; the cell is not loaded",
                        column=spec.idColumn,
                    )
                )
            raise _RowError(
                _error(
                    "REFERENCE_NOT_FOUND",
                    "The related record's parent column is empty",
                    column=parent.column or binding.column,
                )
            )

    def _related_version(
        self, plan: _Plan, column_name: str, cells: list[Any], entry: dict[str, Any]
    ) -> None:
        """The version a row claims for a related record (0.9 J6a, D194); ``not loaded`` marks a
        pair the file cannot show in one cell, which the row leaves out (D195)."""
        raw = _cell(plan.columns, cells, column_name)
        if raw is not None and cell_text(raw).strip() == NOT_LOADED:
            entry["skip"] = True
            return
        entry["version"] = _tally(
            self.report.cell(plan.order, column_name, "key", "version"),
            raw,
            False,
            lambda raw: _version(raw, column_name),
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
                    column("version"),
                    column("application_key"),
                )
            ).from_select(
                [
                    "object_id",
                    "object_type_key",
                    "name",
                    "parent_object_id",
                    "attributes",
                    "version",
                    "application_key",
                ],
                select(
                    source.c.object_id,
                    source.c.object_type_key,
                    source.c.name,
                    source.c.parent_object_id,
                    cast(source.c.attributes, JSONB),
                    source.c.version,
                    source.c.application_key,
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
            | {
                b.relation.relationTypeKey
                for s in self.profile.sources
                for b in s.columns
                if b.relation and b.relation.within
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
        self._virtual_places()
        self._scope_values()
        run("ANALYZE import_rows")
        run("ANALYZE import_context")
        self._duplicates()
        self._identities()
        self._matches()
        self._names_under_parents()
        self._hierarchy()
        self._related_identities()
        self._members()
        self._items()
        self._missing()

    def _missing(self) -> None:
        """The records missing from the file (D82): per source that loads its records by a key,
        the context's records of its type with the key filled that no row of the file names; each
        counted once, by the first such source. A source with ``missing: "delete"`` deletes them
        after every other item, in name order."""
        for plan in sorted(self.plans, key=lambda found: found.order):
            source = plan.source
            if source.key is None or source.record == "existing":
                continue
            # A combination (AP-D43): ``attr`` is the JSON list of its attribute keys, as a row of
            # the combination holds it, and ``keys`` the same list as jsonb (NULL for the others).
            combination = source.key.attributeTypeKeys
            attribute = (
                json.dumps(combination) if combination is not None else source.key.attributeTypeKey
            )
            # Through the context's values, on plain equalities, so it stays a hash anti-join; left
            # out for any other key, as a statement here runs over every record of the type.
            named_by_combination = (
                """AND NOT EXISTS (SELECT 1 FROM import_rows r JOIN import_context_values v
                          ON v.object_type_key = r.object_type_key AND v.attr = r.key_attr
                            AND v.value = r.key_value
                          WHERE r.key_kind = 'combination' AND v.object_id = c.object_id)"""
                if combination is not None
                else ""
            )
            self.session.execute(
                text(
                    f"""
                    INSERT INTO import_missing (src, object_id, name, key_value, version)
                    SELECT :src, c.object_id, c.name,
                        CASE WHEN k.keys IS NOT NULL THEN {_COMBINATION_VALUE.format(c="c")}
                            WHEN k.attr IS NULL THEN to_jsonb(c.object_id)
                            ELSE c.attributes -> k.attr END,
                        c.version
                    FROM import_context c,
                        (SELECT CAST(:attr AS text) AS attr, CAST(:combo AS jsonb) AS keys) k
                    WHERE c.object_type_key = :type
                      AND (CASE WHEN k.keys IS NOT NULL THEN {_COMBINATION_HELD.format(c="c")}
                            ELSE k.attr IS NULL OR c.attributes -> k.attr IS NOT NULL END)
                      -- Four anti-joins on plain equalities, so each is a hash anti-join: a
                      -- row that found the record, a row naming its key, its ID or its name. A
                      -- row keyed by name finds no record when its name is ambiguous or the row
                      -- failed first, and the records it names are then not missing (0.10 R-F1).
                      AND NOT EXISTS (SELECT 1 FROM import_rows r WHERE r.record_id = c.object_id)
                      AND NOT EXISTS (SELECT 1 FROM import_rows r
                          WHERE r.key_kind = 'attribute' AND r.object_type_key = c.object_type_key
                            AND r.key_attr = k.attr AND r.key_value = c.attributes -> k.attr)
                      {named_by_combination}
                      AND NOT EXISTS (SELECT 1 FROM import_rows r
                          WHERE r.key_kind = 'id' AND r.key_value #>> '{{}}' = c.object_id)
                      AND NOT EXISTS (SELECT 1 FROM import_rows r
                          WHERE r.key_kind = 'name' AND r.object_type_key = c.object_type_key
                            AND r.key_value #>> '{{}}' = c.name)
                    ON CONFLICT (object_id) DO NOTHING
                    """
                ),
                {
                    "src": plan.order,
                    "attr": attribute,
                    "combo": json.dumps(combination) if combination is not None else None,
                    "type": source.objectTypeKey,
                },
            )
            if source.missing == "delete":
                self.session.execute(
                    text(
                        """
                        INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
                        SELECT 9, m.src, 0, NULL, row_number() OVER (ORDER BY m.name, m.object_id),
                            CAST(:ref AS text) || m.object_id,
                            jsonb_build_object('op', 'delete', 'ref', CAST(:ref AS text) || m.object_id,
                                'target', jsonb_build_object('id', m.object_id),
                                'expectedVersion', m.version)
                        FROM import_missing m WHERE m.src = :src
                        """
                    ),
                    {"src": plan.order, "ref": MISSING_REF},
                )

    # --- where new records go, and how a matrix column is read (0.17 PP-D24 to PP-D26) ---

    def _place(
        self, source_type: str, relation: Any, column_value: str, container: Any
    ) -> Place | None:
        """Where a new record of the column goes: the profile's container when it names one, else
        what the model's rules gave for the column record (:meth:`_places`)."""
        if container is not None:
            return Place(container.value)
        return self.places.get(
            (
                source_type,
                relation.relationTypeKey,
                relation.direction,
                relation.objectTypeKey,
                column_value,
            )
        )

    def _value_place(self, source: Any) -> Place | None:
        """Where a new record of a value sheet goes: the place of its column record."""
        under = source.under
        return self.places.get(
            (
                under.rowObjectTypeKey,
                under.relationTypeKey,
                under.direction,
                source.objectTypeKey,
                under.value,
            )
        )

    def _places(self) -> None:
        """The place for each column record a new record may be created under, read once before the
        rows are: a link matrix column that creates (``missing: create``) without a container, and a
        create matrix column (``under``). The answer comes from the context's records and the
        binding's candidate criteria (:func:`resolve_places`), for every column record in whole-set
        statements; a place that does not exist yet is created with the first record that goes in
        it."""
        requests: dict[tuple[str, str, str, str, str], PlaceRequest] = {}
        for plan in self.plans:
            source_type = plan.source.objectTypeKey
            if plan.source.under is not None and plan.source.under.creates:
                under = plan.source.under
                self._place_request(
                    requests,
                    under.rowObjectTypeKey,
                    under.relationTypeKey,
                    under.direction,
                    source_type,
                    under.objectTypeKey,
                    under.value,
                )
            for binding in plan.source.columns:
                specs: list[tuple[Any, str, str]] = []
                relation = binding.relation
                if (
                    relation is not None
                    and relation.within is not None
                    and relation.within.container is None
                    and relation.missing == "create"
                ):
                    specs.append((relation, relation.within.objectTypeKey, relation.within.value))
                if binding.relatedRecord is not None and binding.relatedRecord.under is not None:
                    under = binding.relatedRecord.under
                    specs.append((binding.relatedRecord, under.objectTypeKey, under.value))
                for spec, column_type, column_value in specs:
                    self._place_request(
                        requests,
                        source_type,
                        spec.relationTypeKey,
                        spec.direction,
                        spec.objectTypeKey,
                        column_type,
                        column_value,
                    )
        found = resolve_places(
            self.session,
            self.model,
            self.job.workspace_key,
            self.context,
            list(requests.values()),
            self.place_reads,
        )
        for key, request, place in zip(requests, requests.values(), found, strict=True):
            self.places[key] = place
            if place.new is not None and place.container_id is not None:
                self.new_places[place.container_id] = place
                self.place_columns[place.container_id] = request.column_record_id

    def _place_request(
        self,
        requests: dict[tuple[str, str, str, str, str], PlaceRequest],
        row_type: str,
        relation_type_key: str,
        direction: str,
        cell_type: str,
        column_type: str,
        column_value: str,
    ) -> None:
        """The request for the place a new ``cell_type`` record under the column record goes, once
        per column."""
        key = (row_type, relation_type_key, direction, cell_type, column_value)
        if key in self.places or key in requests:
            return
        outgoing = direction == "outgoing"
        allowed = (
            self.model.allowed_relation(relation_type_key, row_type, cell_type)
            if outgoing
            else self.model.allowed_relation(relation_type_key, cell_type, row_type)
        )
        criteria = allowed.candidates_at("to" if outgoing else "from") if allowed else ()
        requests[key] = PlaceRequest(
            column_record_id=column_value,
            column_type_key=column_type,
            cell_type_key=cell_type,
            criteria=criteria,
            relation_type_key=relation_type_key,
            direction=direction,
            row_type_key=row_type,
        )

    def _virtual_places(self) -> None:
        """The places this load creates, as records of the context: a match by ID finds them, and
        the records created under them have a parent."""
        for place_id, place in self.new_places.items():
            assert place.new is not None
            attributes = [
                {"attributeTypeKey": key, "value": value}
                for key, value in place.new.attributes.items()
            ]
            self.session.execute(
                text(
                    "INSERT INTO import_new_places (place_id, object_type_key, name, column_id,"
                    " attributes, application_key) VALUES (:id, :type, :name, :column,"
                    " CAST(:attributes AS jsonb), coalesce((SELECT c.application_key FROM"
                    " import_context c WHERE c.object_id = :column), :application))"
                ),
                {
                    "id": place_id,
                    "type": place.new.object_type_key,
                    "name": place.new.name,
                    "column": self.place_columns[place_id],
                    "attributes": json.dumps(attributes),
                    "application": self.model.application_of_type(place.new.object_type_key),
                },
            )
        self._sql(
            """
            INSERT INTO import_context (object_id, object_type_key, name, parent_object_id,
                attributes, version, application_key)
            SELECT place_id, object_type_key, name, column_id,
                (SELECT coalesce(jsonb_object_agg(a ->> 'attributeTypeKey', a -> 'value'), '{}'::jsonb)
                 FROM jsonb_array_elements(attributes) a),
                1, application_key
            FROM import_new_places
            """
        )

    def _scope_values(self) -> None:
        """The records of each link-matrix column with each value they could be listed by, and then
        which field each column is read by (PP-D26): one walk down from the column record through
        the container types to the cell records per column, over the context's records, one row per
        record and identifying field of the cell type (``name``, its display attribute, its unique
        attributes), and for a file from before the field was recorded the label ``name (display)``."""
        seen: set[tuple[str, str, str]] = set()
        for source in self.profile.sources:
            for binding in source.columns:
                relation = binding.relation
                if relation is None or relation.within is None:
                    continue
                within = relation.within
                label_attr = within.labelAttributeTypeKey or ""
                if (within.value, label_attr, relation.objectTypeKey) in seen:
                    continue
                seen.add((within.value, label_attr, relation.objectTypeKey))
                fields = identifying_fields(self.model, relation.objectTypeKey)
                for rank, field_ in enumerate(fields):
                    self.session.execute(
                        text("INSERT INTO import_fields VALUES (:scope, :field, :rank)"),
                        {"scope": within.value, "field": field_, "rank": rank},
                    )
                values = ["('name', c.name)"]
                params: dict[str, Any] = {}
                for number, field_ in enumerate(item for item in fields if item != "name"):
                    values.append(f"(:field{number}, c.attributes ->> :field{number})")
                    params[f"field{number}"] = field_
                if label_attr:
                    values.append(
                        "('@label:' || :label_attr, CASE WHEN c.attributes ->> :label_attr IS NOT NULL"
                        " AND c.attributes ->> :label_attr <> c.name"
                        " THEN c.name || ' (' || (c.attributes ->> :label_attr) || ')' ELSE c.name END)"
                    )
                self.session.execute(
                    text(
                        f"""
                        INSERT INTO import_scope_values
                            (scope, object_type_key, field, value, object_id)
                        WITH RECURSIVE down(object_id, depth) AS (
                            SELECT c.object_id, 1 FROM import_context c
                            WHERE c.parent_object_id = :scope AND c.object_type_key = ANY(:walk)
                            UNION ALL
                            SELECT c.object_id, d.depth + 1 FROM down d
                            JOIN import_context c ON c.parent_object_id = d.object_id
                            WHERE c.object_type_key = ANY(:walk) AND d.depth < 64)
                        -- A cell is cut at its separator, so a value holding one is read with it as a
                        -- comma, as the export writes it.
                        SELECT :scope, c.object_type_key, f.field, replace(f.value, ';', ','),
                            c.object_id
                        FROM down d JOIN import_context c ON c.object_id = d.object_id
                        CROSS JOIN LATERAL (VALUES {", ".join(values)}) AS f(field, value)
                        WHERE c.object_type_key = :cell_type AND f.value IS NOT NULL AND f.value <> ''
                        """
                    ),
                    {
                        "scope": within.value,
                        "label_attr": label_attr,
                        "walk": self._walk_types(relation),
                        "cell_type": relation.objectTypeKey,
                        **params,
                    },
                )
        self._guess_fields()

    def _guess_fields(self) -> None:
        """Each link-matrix column's cells against each identifying field of the column's records,
        in one statement over the distinct values (PP-D26): how many values find exactly one record by
        each field, and how many find several. A column whose file records no field is read by the
        best one: every value finding one record, else the most, a tie going to the field offered
        first (the name). The choice is written into the column's matches before they are resolved;
        what was compared is kept for the report."""
        self._sql(
            """
            CREATE TEMPORARY TABLE import_hits ON COMMIT DROP AS
            WITH cells AS (
                SELECT DISTINCT c.src, c.column_name, c.match ->> 'scope' AS scope,
                    c.match ->> 'type' AS type, (c.match -> 'value') #>> '{}' AS v
                FROM import_match_cells c WHERE c.match ->> 'field' = 'cell')
            SELECT d.src, d.column_name, f.field, f.rank, count(*) AS cells,
                count(*) FILTER (WHERE h.n = 1) AS matched,
                count(*) FILTER (WHERE h.n > 1) AS ambiguous
            FROM cells d JOIN import_fields f ON f.scope = d.scope
            LEFT JOIN LATERAL (
                SELECT count(DISTINCT s.object_id) AS n FROM import_scope_values s
                WHERE s.scope = d.scope AND s.object_type_key = d.type AND s.field = f.field
                  AND s.value = d.v) h ON true
            GROUP BY d.src, d.column_name, f.field, f.rank
            """
        )
        hits: dict[tuple[int, str], list[Any]] = {}
        for src, column_name, field_, rank, cells, matched, ambiguous in self.session.execute(
            text(
                "SELECT src, column_name, field, rank, cells, matched, ambiguous FROM import_hits"
                " ORDER BY src, column_name, rank"
            )
        ):
            hits.setdefault((src, column_name), []).append(
                (field_, rank, cells, matched, ambiguous)
            )
        declared = {
            (src, column_name): attr
            for src, column_name, attr in self.session.execute(
                text(
                    "SELECT DISTINCT src, column_name, match ->> 'attr' FROM import_match_cells"
                    " WHERE match ->> 'field' = 'cell'"
                )
            )
        }
        chosen: list[dict[str, Any]] = []
        for key, found in hits.items():
            options = [
                {"field": field_, "cells": cells, "matched": matched, "ambiguous": ambiguous}
                for field_, _rank, cells, matched, ambiguous in found
            ]
            attr = declared.get(key, "")
            reading: dict[str, Any] = {"options": options}
            if attr:
                reading |= {"field": attr, "recorded": True, "guessed": False}
            else:
                best, note = _best_field(found, self.model)
                chosen.append({"src": key[0], "column": key[1], "field": best})
                reading |= {"field": best, "recorded": False, "guessed": True, "note": note}
            self.readings[key] = reading
        if chosen:
            self.session.execute(
                text(
                    "CREATE TEMPORARY TABLE import_choice (src integer, column_name text, field text)"
                    " ON COMMIT DROP"
                )
            )
            self.session.execute(
                text("INSERT INTO import_choice VALUES (:src, :column, :field)"), chosen
            )
            for statement in (
                """
                UPDATE import_links l SET match = (l.match || jsonb_build_object('attr', g.field))
                    - CASE WHEN g.field = 'name' THEN '' ELSE 'create' END
                FROM import_rows r, import_choice g
                WHERE r.row_id = l.row_id AND g.src = r.src AND g.column_name = l.match ->> 'column'
                  AND l.match ->> 'field' = 'cell' AND l.match ->> 'attr' = ''
                """,
                """
                UPDATE import_match_cells l SET match = (l.match || jsonb_build_object('attr', g.field))
                    - CASE WHEN g.field = 'name' THEN '' ELSE 'create' END
                FROM import_choice g
                WHERE g.src = l.src AND g.column_name = l.column_name
                  AND l.match ->> 'field' = 'cell' AND l.match ->> 'attr' = ''
                """,
            ):
                self._sql(statement)

    def _reading_report(self) -> dict[tuple[int, str], dict[str, Any]]:
        """How each matrix and relationship column was read, for the preview (PP-D26): the field it
        is matched by and whether the file recorded it, what each field of the column's records
        would have matched, and where a new record goes."""
        found: dict[tuple[int, str], dict[str, Any]] = {}
        placed: set[str] = set()
        from_sheets = self._value_sheet_counts()
        for plan in self.plans:
            if plan.source.under is not None:
                found.update(self._value_sheet_reading(plan))
            for binding in plan.source.columns:
                relation = binding.relation
                if relation is not None and relation.within is not None:
                    within = relation.within
                    reading = dict(self.readings.get((plan.order, binding.column), {}))
                    if not reading:
                        field_ = within.field or (
                            "@label" if within.labelAttributeTypeKey else "name"
                        )
                        reading = {
                            "field": field_,
                            "recorded": bool(within.field or within.labelAttributeTypeKey),
                            "guessed": False,
                            "options": [
                                {"field": item, "cells": 0, "matched": 0, "ambiguous": 0}
                                for item in identifying_fields(self.model, relation.objectTypeKey)
                            ],
                        }
                    reading["binding"] = "relation"
                    for option in reading["options"]:
                        option["label"] = _field_label(self.model, option["field"])
                    reading["label"] = _field_label(self.model, reading["field"])
                    place = self._place(
                        plan.source.objectTypeKey, relation, within.value, within.container
                    )
                    if relation.missing == "create" and place is not None:
                        reading["newRecords"] = self._new_records(place, relation.objectTypeKey)
                    reading |= from_sheets.get((plan.order, binding.column), {})
                    found[(plan.order, binding.column)] = reading
                elif relation is not None and relation.idColumn is None:
                    by = relation.matchBy
                    if by.field == "id":
                        continue
                    field_ = by.attributeTypeKey or "name"
                    found[(plan.order, binding.column)] = {
                        "binding": "relation",
                        "field": field_,
                        "label": _field_label(self.model, field_),
                        "recorded": True,
                        "guessed": False,
                        "options": [
                            {"field": item, "label": _field_label(self.model, item)}
                            for item in identifying_fields(self.model, relation.objectTypeKey)
                        ],
                    }
                elif binding.relatedRecord is not None and binding.relatedRecord.under is not None:
                    spec = binding.relatedRecord
                    if spec.under.value in placed:
                        continue
                    placed.add(spec.under.value)
                    place = self._place(plan.source.objectTypeKey, spec, spec.under.value, None)
                    found[(plan.order, binding.column)] = {
                        "binding": "relatedRecord",
                        "recorded": True,
                        "guessed": False,
                        "options": [],
                        "newRecords": self._new_records(place, spec.objectTypeKey),
                    }
        return found

    def _value_sheet_counts(self) -> dict[tuple[int, str], dict[str, int]]:
        """For each link column of a file with value sheets: how many of its distinct values name a
        row of a value sheet, and how many name no record at all and so create one (PP-D27)."""
        if not any(plan.source.under is not None for plan in self.plans):
            return {}
        return {
            (src, column_name): {"fromValueSheet": from_sheet, "createdValues": created}
            for src, column_name, from_sheet, created in self.session.execute(
                text(
                    f"""
                    SELECT c.src, c.column_name,
                        count(DISTINCT m.match_id) FILTER (WHERE NOT m.created AND EXISTS (
                            SELECT 1 FROM import_value_rows v
                            WHERE v.scope = m.scope AND v.record_id = m.resolved)),
                        count(DISTINCT m.match_id) FILTER (WHERE m.created)
                    FROM import_match_cells c JOIN import_matches m ON {_JOINED.format(s="c.match")}
                    WHERE m.field = 'cell'
                    GROUP BY c.src, c.column_name
                    """
                )
            )
        }

    def _value_sheet_reading(self, plan: _Plan) -> dict[tuple[int, str], dict[str, Any]]:
        """How a value sheet is read, on its first column: the rows that update a record, the rows
        that are new records and where they go (PP-D27)."""
        source, under = plan.source, plan.source.under
        updated, new = self.session.execute(
            text(
                "SELECT count(*) FILTER (WHERE existing), count(*) FILTER (WHERE NOT existing)"
                " FROM import_rows WHERE src = :src AND error IS NULL AND rep_id IS NULL"
            ),
            {"src": plan.order},
        ).one()
        reading: dict[str, Any] = {
            "binding": "field",
            "valueSheet": True,
            "recorded": True,
            "guessed": False,
            "options": [],
            "updatedRows": updated,
            "newRows": new,
        }
        if under.creates:
            reading["newRecords"] = self._new_records(
                self._value_place(source), source.objectTypeKey
            )
        first = next((item for item in source.columns if item.field == "name"), None)
        return {(plan.order, first.column): reading} if first is not None else {}

    def _new_records(self, place: Place | None, cell_type: str) -> dict[str, Any]:
        """Where a new record of the column goes, for the report: an existing container, a place
        this load creates, or nowhere (and why)."""
        if place is not None and place.container_id is not None:
            found: dict[str, Any] = {
                "objectTypeKey": place.type_key,
                "name": place.name,
                "willBeCreated": place.new is not None,
            }
            if place.new is not None:
                # "will create group X under Y" (PP-D28): the kind in words and the column record.
                kind = self.model.object_type(place.type_key)
                found["typeName"] = kind.name if kind is not None else place.type_key
                column_id = self.place_columns.get(place.container_id)
                found["under"] = (
                    self.session.scalar(
                        text("SELECT name FROM import_context WHERE object_id = :id"),
                        {"id": column_id},
                    )
                    if column_id
                    else None
                )
            return found
        return {
            "objectTypeKey": None,
            "name": None,
            "willBeCreated": False,
            "reason": "several" if place is not None and place.several else "none",
            "message": place.message if place is not None else None,
        }

    def _walk_types(self, relation: Any) -> list[str]:
        """The types a walk down from a link-matrix column record passes to its cells: the cell
        type and the container types between (another column record ends a branch)."""
        column_type, cell_type = relation.within.objectTypeKey, relation.objectTypeKey
        containers = {
            key
            for key in ancestor_type_keys(self.model, cell_type)
            if key != column_type and column_type in ancestor_type_keys(self.model, key)
        }
        return sorted(containers | {cell_type})

    def _context_types(self) -> set[str]:
        # The types the places hold, which a match by ID finds them among.
        types: set[str] = {place.type_key for place in self.places.values() if place.type_key}
        for source in self.profile.sources:
            types.add(source.objectTypeKey)
            if source.under is not None:
                types.add(source.under.objectTypeKey)
            if source.parent is not None:
                types.add(source.parent.objectTypeKey)
            for binding in source.columns:
                if binding.parent is not None:
                    types.add(binding.parent.objectTypeKey)
                for relation in (binding.relation, binding.relationFlags):
                    if relation is not None:
                        types.add(relation.objectTypeKey)
                if binding.relation is not None and binding.relation.within is not None:
                    within = binding.relation.within
                    types.add(within.objectTypeKey)
                    types |= set(self._walk_types(binding.relation))
                    if within.container is not None:
                        types.add(within.container.objectTypeKey)
                if binding.relatedRecord is not None:
                    types.add(binding.relatedRecord.objectTypeKey)
                    if binding.relatedRecord.parent is not None:
                        types.add(binding.relatedRecord.parent.objectTypeKey)
                    if binding.relatedRecord.under is not None:
                        types.add(binding.relatedRecord.under.objectTypeKey)
        return types

    def _sql(self, statement: str) -> None:
        self.session.execute(text(statement))

    def _counterpart_matches(self) -> None:
        """Each match by ID naming another workspace's live record, with its counterpart here
        (0.9 J5, D100): one statement finds them, one ``COPY`` stores the counterparts. A record
        of a workspace running another model has none (0.11 M4, D44): the match stays unresolved,
        and the row's item, naming that record, is refused when it runs."""
        workspace_key = self.job.workspace_key
        held = self.session.execute(
            text(
                "SELECT m.match_id, o.id FROM import_matches m JOIN objects o"
                " ON o.id = m.value #>> '{}'"
                " JOIN workspace_models w ON w.workspace_key = o.workspace_key"
                " JOIN model_releases r ON r.id = w.model_release_id"
                " WHERE m.field = 'id' AND o.workspace_key <> :workspace AND r.release_key = :model"
            ),
            {"workspace": workspace_key, "model": self.model.release.key},
        ).all()
        counterparts = CopyRows(self.session, "import_counterparts", ("match_id", "object_id"))
        for match_id, object_id in held:
            counterparts.add(match_id, counterpart(workspace_key, object_id))
        counterparts.flush()

    def _duplicates(self) -> None:
        """D69: upsert rows of one type with one key, from any source of the load, are one record
        when their own values agree (an empty cell agrees with any value, and the record takes
        every value the rows fill); when they differ, every such row is rejected naming the others.
        Rows keyed by name under a parent are one key with the rows of any source naming that
        parent (0.10 A8c, D142)."""
        self._sql(
            f"""
            WITH keyed AS (
                SELECT r.*, {_KEY_GROUP.format(r="r")} AS grp FROM import_rows r
                WHERE r.error IS NULL AND r.key_value IS NOT NULL),
            -- An empty cell says nothing: rows differ only where two of them fill one field
            -- with different values (the first row of a group often carries the details).
            clashes AS (
                SELECT DISTINCT k.grp FROM keyed k CROSS JOIN LATERAL jsonb_each(k.attributes) a
                GROUP BY k.grp, a.key HAVING count(DISTINCT a.value) > 1),
            groups AS (
                SELECT grp, min(row_id) AS rep,
                       CASE WHEN count(DISTINCT name) > 1 OR count(DISTINCT parent - 'column') > 1
                            OR grp IN (SELECT grp FROM clashes) THEN 2 ELSE 1 END AS variants,
                       array_agg(row_number ORDER BY src, row_number) AS numbers,
                       array_agg(ref ORDER BY src, row_number) AS refs
                FROM keyed GROUP BY grp HAVING count(*) > 1)
            UPDATE import_rows r SET
                error = CASE WHEN g.variants > 1 THEN jsonb_build_object(
                    'code', 'DUPLICATE_KEY_IN_FILE',
                    'message', format('Rows %s hold one key with different values; none of them is'
                        ' loaded', array_to_string(g.refs, ', ')),
                    'details', jsonb_build_object(
                        'rows', (SELECT coalesce(jsonb_agg(u.n), '[]') FROM unnest(g.numbers, g.refs) AS u(n, f)
                                 WHERE u.f <> r.ref),
                        'refs', to_jsonb(array_remove(g.refs, r.ref)),
                        'column', r.key_column)) END,
                rep_id = CASE WHEN g.variants = 1 AND r.row_id <> g.rep THEN g.rep END
            FROM groups g WHERE {_KEY_GROUP.format(r="r")} = g.grp AND r.error IS NULL
            """
        )
        # The record a group loads holds every value its rows fill.
        self._sql(
            """
            WITH members AS (
                SELECT coalesce(m.rep_id, m.row_id) AS rep, m.name, m.parent, m.attributes
                FROM import_rows m
                WHERE m.error IS NULL AND (m.rep_id IS NOT NULL OR EXISTS (
                    SELECT 1 FROM import_rows x WHERE x.rep_id = m.row_id))),
            filled AS (
                SELECT v.rep, jsonb_object_agg(a.key, a.value) AS attributes
                FROM members v CROSS JOIN LATERAL jsonb_each(v.attributes) a GROUP BY v.rep),
            merged AS (
                SELECT u.rep, max(u.name) AS name,
                       (array_agg(u.parent) FILTER (WHERE u.parent IS NOT NULL))[1] AS parent,
                       coalesce(f.attributes, '{}'::jsonb) AS attributes
                FROM members u LEFT JOIN filled f ON f.rep = u.rep
                GROUP BY u.rep, f.attributes)
            UPDATE import_rows r SET name = coalesce(r.name, g.name),
                parent = coalesce(r.parent, g.parent), attributes = g.attributes
            FROM merged g WHERE r.row_id = g.rep
            """
        )

    def _identities(self) -> None:
        """Each row's record: found by its key in the context, or a new ID; a member row of a
        repeated key takes its first row's."""
        self._sql(
            f"""
            INSERT INTO import_context_values (object_type_key, attr, value, object_id)
            SELECT c.object_type_key, k.attr, {_KEY_OF_RECORD}, c.object_id
            FROM {_KEYS_USED} k
            JOIN import_context c ON c.object_type_key = k.object_type_key
            WHERE {_RECORD_HOLDS_KEY}
            ON CONFLICT DO NOTHING
            """
        )
        self._sql("ANALYZE import_context_values")
        # A stored-unique key two records now hold finds neither: the row says so (0.16 AP7).
        self._sql(
            f"""
            UPDATE import_rows r SET error = jsonb_build_object(
                'code', 'KEY_AMBIGUOUS',
                'message', CASE WHEN r.key_kind = 'combination'
                    THEN 'Several records hold this combination: ' || {_COMBINATION_TEXT.format(r="r")}
                    ELSE 'Several records hold this key: ' || (r.key_value #>> '{{}}') END,
                'column', {_KEY_COLUMN.format(r="r")})
            FROM (SELECT c.object_type_key, k.attr, {_KEY_OF_RECORD} AS value
                  FROM {_KEYS_USED} k
                  JOIN import_context c ON c.object_type_key = k.object_type_key
                  WHERE {_RECORD_HOLDS_KEY}
                  GROUP BY 1, 2, 3 HAVING count(*) > 1) d
            WHERE r.error IS NULL AND r.key_kind IN ('attribute', 'combination')
              AND d.object_type_key = r.object_type_key AND d.attr = r.key_attr
              AND d.value = r.key_value
            """
        )
        self._sql(
            """
            UPDATE import_rows r SET record_id = c.object_id, existing = true, current_name = c.name
            FROM import_context_values v JOIN import_context c ON c.object_id = v.object_id
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.key_kind IN ('attribute', 'combination')
              AND v.object_type_key = r.object_type_key AND v.attr = r.key_attr
              AND v.value = r.key_value
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
            f"""
            WITH found AS (
                SELECT r.row_id, count(c.object_id) AS n, min(c.object_id) AS one, min(c.name) AS name
                FROM import_rows r LEFT JOIN import_context c
                    ON c.object_type_key = r.object_type_key AND c.name = r.key_value #>> '{{}}'
                WHERE r.error IS NULL AND r.rep_id IS NULL AND r.key_kind = 'name'
                  AND NOT ({_UNDER_PARENT.format(r="r")})
                GROUP BY r.row_id)
            UPDATE import_rows r SET
                record_id = CASE WHEN f.n = 1 THEN f.one END, existing = f.n = 1,
                current_name = CASE WHEN f.n = 1 THEN f.name END,
                error = CASE WHEN f.n > 1 THEN jsonb_build_object(
                    'code', CASE WHEN r.mode = 'upsert' THEN 'AMBIGUOUS_NAME_KEY'
                        ELSE 'REFERENCE_AMBIGUOUS' END,
                    'message', format('%s %s records are named %s', f.n, r.object_type_key, r.key_value),
                    'details', jsonb_build_object('column', r.key_column, 'count', f.n)) END
            FROM found f WHERE f.row_id = r.row_id
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
            WHERE error IS NULL AND rep_id IS NULL AND record_id IS NULL AND mode = 'upsert'
            """
        )
        # A new record two sources of the file key alike is one record: the first source's row
        # creates it and the later ones update it (two sheets listing the same IDs, 0.16 AP6).
        self._sql(
            """
            UPDATE import_rows r SET record_id = f.record_id
            FROM (SELECT DISTINCT ON (object_type_key, key_attr, key_value)
                      object_type_key, key_attr, key_value, record_id
                  FROM import_rows
                  WHERE error IS NULL AND rep_id IS NULL AND mode = 'upsert' AND NOT existing
                    AND key_kind IN ('attribute', 'combination')
                  ORDER BY object_type_key, key_attr, key_value, src, row_number) f
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'upsert' AND NOT r.existing
              AND r.key_kind IN ('attribute', 'combination') AND r.object_type_key = f.object_type_key
              AND r.key_attr = f.key_attr AND r.key_value = f.key_value
              AND r.record_id <> f.record_id
            """
        )
        # An existing-records row also finds the record another row of the file creates by the same
        # key, as a sheet of translations names the records the main sheet loads (0.10 A6, D93).
        self._sql(
            """
            UPDATE import_rows r SET record_id = f.record_id FROM import_rows f
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'existing' AND NOT r.existing
              AND r.key_kind IN ('attribute', 'combination') AND f.mode = 'upsert'
              AND f.error IS NULL AND f.rep_id IS NULL AND f.object_type_key = r.object_type_key
              AND f.key_kind = r.key_kind AND f.key_attr = r.key_attr AND f.key_value = r.key_value
            """
        )
        # Or by the value another row of the file writes into the key's attribute, whatever that row
        # is keyed by: a main sheet keyed by name that fills a new code, and a sheet of translations
        # keyed by the code (0.16 AP6). Only where the value names one record.
        self._sql(
            """
            WITH wanted AS (
                SELECT DISTINCT object_type_key, key_attr AS attr FROM import_rows
                WHERE error IS NULL AND rep_id IS NULL AND mode = 'existing'
                  AND NOT existing AND record_id IS NULL AND key_kind = 'attribute'),
            values_written AS (
                SELECT f.object_type_key, k.attr, f.attributes -> k.attr AS value, f.record_id,
                    f.existing, f.current_name
                FROM wanted k JOIN import_rows f ON f.object_type_key = k.object_type_key
                WHERE f.mode = 'upsert' AND f.error IS NULL AND f.rep_id IS NULL
                  AND f.attributes -> k.attr IS NOT NULL),
            written AS (
                SELECT r.row_id, min(f.record_id) AS one, count(DISTINCT f.record_id) AS n,
                    bool_and(f.existing) AS existing, min(f.current_name) AS current_name
                FROM import_rows r JOIN values_written f
                    ON f.object_type_key = r.object_type_key AND f.attr = r.key_attr
                   AND f.value = r.key_value
                WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'existing'
                  AND NOT r.existing AND r.record_id IS NULL AND r.key_kind = 'attribute'
                GROUP BY r.row_id)
            UPDATE import_rows r SET record_id = w.one, existing = w.existing,
                current_name = w.current_name
            FROM written w WHERE w.row_id = r.row_id AND w.n = 1
            """
        )
        self._sql(
            f"""
            UPDATE import_rows r SET error = jsonb_build_object(
                'code', 'REFERENCE_NOT_FOUND',
                'message', format('No %s record has the key %s', r.object_type_key, r.key_value),
                'details', jsonb_build_object('column', {_KEY_COLUMN.format(r="r")}))
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'existing' AND NOT r.existing
              AND NOT EXISTS (
                  SELECT 1 FROM import_rows f WHERE f.mode = 'upsert' AND f.error IS NULL
                    AND f.rep_id IS NULL AND f.object_type_key = r.object_type_key
                    AND f.record_id = r.record_id)
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
            INSERT INTO import_matches
                (object_type_key, field, attr, scope, label_attr, container, value, creates)
            SELECT m ->> 'type', m ->> 'field', m ->> 'attr', coalesce(m ->> 'scope', ''),
                coalesce(m ->> 'labelAttr', ''), coalesce(m ->> 'container', ''), m -> 'value',
                bool_or(coalesce((m ->> 'create')::boolean, false)) FROM (
                SELECT parent AS m FROM import_rows WHERE parent IS NOT NULL AND error IS NULL
                UNION ALL SELECT match FROM import_links WHERE match IS NOT NULL
                UNION ALL SELECT parent FROM import_related WHERE parent IS NOT NULL
                UNION ALL SELECT match FROM import_match_cells) found
            GROUP BY 1, 2, 3, 4, 5, 6, 7
            """
        )
        self._sql("ANALYZE import_matches")
        self._value_rows()
        self._sql(
            """
            INSERT INTO import_context_values (object_type_key, attr, value, object_id)
            SELECT c.object_type_key, k.attr, c.attributes -> k.attr, c.object_id
            FROM (SELECT DISTINCT object_type_key, attr FROM import_matches
                  WHERE attr <> '' AND field <> 'cell') k
            JOIN import_context c ON c.object_type_key = k.object_type_key
            WHERE c.attributes -> k.attr IS NOT NULL
            ON CONFLICT DO NOTHING
            """
        )
        self._sql(
            """
            INSERT INTO import_row_values (object_type_key, attr, value, record_id)
            SELECT f.object_type_key, k.attr, f.attributes -> k.attr, f.record_id
            FROM (SELECT DISTINCT object_type_key, attr FROM import_matches
                  WHERE attr <> '' AND field <> 'cell') k
            JOIN import_rows f ON f.object_type_key = k.object_type_key AND f.mode = 'upsert'
                AND f.rep_id IS NULL AND f.error IS NULL
            WHERE f.attributes -> k.attr IS NOT NULL
            """
        )
        self._sql("ANALYZE import_context_values")
        self._sql("ANALYZE import_row_values")
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
                UNION SELECT m.match_id, v.object_id FROM import_matches m
                JOIN import_context_values v ON v.object_type_key = m.object_type_key
                    AND m.attr <> '' AND m.field <> 'cell' AND v.attr = m.attr AND v.value = m.value
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_rows f ON f.object_type_key = m.object_type_key AND f.mode = 'upsert'
                    AND f.rep_id IS NULL AND f.error IS NULL
                    AND m.field = 'name' AND f.name = m.value #>> '{}'
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_rows f ON f.object_type_key = m.object_type_key AND f.mode = 'upsert'
                    AND f.rep_id IS NULL AND f.error IS NULL
                    AND m.field = 'id' AND f.record_id = m.value #>> '{}'
                UNION SELECT m.match_id, f.record_id FROM import_matches m
                JOIN import_row_values f ON f.object_type_key = m.object_type_key
                    AND m.attr <> '' AND m.field <> 'cell' AND f.attr = m.attr AND f.value = m.value
                UNION SELECT m.match_id, s.object_id FROM import_matches m
                JOIN import_scope_values s ON s.scope = m.scope
                    AND s.object_type_key = m.object_type_key AND m.field = 'cell'
                    AND s.value = m.value #>> '{}'
                    AND (s.field = m.attr
                         OR (m.attr = '@label' AND s.field IN ('name', '@label:' || m.label_attr)))
                    -- A record the file's value sheet lists keeps its old value, unless another row
                    -- of the sheet holds that value now: then it is that row's.
                    AND NOT (
                        EXISTS (SELECT 1 FROM import_value_rows y
                                WHERE y.scope = s.scope AND y.record_id = s.object_id)
                        AND EXISTS (SELECT 1 FROM import_value_rows x
                                    WHERE x.scope = s.scope AND x.object_type_key = s.object_type_key
                                      AND x.value = s.value AND x.record_id <> s.object_id))
                UNION SELECT m.match_id, v.record_id FROM import_matches m
                JOIN import_value_rows v ON v.scope = m.scope
                    AND v.object_type_key = m.object_type_key AND m.field = 'cell'
                    AND v.value = m.value #>> '{}'
                    AND (v.field = m.attr OR (m.attr = '@label' AND v.field = 'name'))),
            counted AS (
                SELECT match_id, count(*) AS n, min(object_id) AS one FROM candidates GROUP BY match_id),
            kept AS (
                INSERT INTO import_match_candidates (match_id, object_id)
                SELECT a.match_id, a.object_id FROM candidates a
                JOIN counted c ON c.match_id = a.match_id AND c.n > 1)
            UPDATE import_matches m SET candidates = c.n, resolved = CASE WHEN c.n = 1 THEN c.one END
            FROM counted c WHERE c.match_id = m.match_id
            """
        )
        self._sql("ANALYZE import_match_candidates")
        # A name no record has, in a column that creates what it names, is a new record (D77).
        self._sql(
            """
            UPDATE import_matches SET resolved = gen_random_uuid()::text, candidates = 1, created = true
            WHERE creates AND candidates = 0
              AND (field = 'name' OR field = 'cell')
              AND jsonb_typeof(value) = 'string'
              AND btrim(value #>> '{}') <> ''
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
        # A value several records match, in a row whose record is already related to some of them by
        # the link's relationship: those records, in turn for a value the cell names more than once
        # (two linked records sharing a name and every field are still each one). A value that matches
        # none of the row's records stays ambiguous.
        self._sql(
            f"""
            WITH {_ENDS}
            ambiguous AS (
                SELECT l.row_id, l.link_no, r.record_id, l.relation_type_key, l.direction,
                    m.match_id,
                    row_number() OVER (PARTITION BY l.row_id, m.match_id, l.relation_type_key, l.direction
                        ORDER BY l.link_no) AS turn
                FROM import_links l
                JOIN import_rows r ON r.row_id = l.row_id AND r.existing AND r.error IS NULL
                JOIN import_matches m ON {joined.format(s="l.match")}
                WHERE l.candidates > 1),
            linked AS (
                SELECT a.row_id, a.link_no, a.turn, k.object_id,
                    row_number() OVER (PARTITION BY a.row_id, a.link_no ORDER BY k.object_id) AS turn_of
                FROM ambiguous a
                JOIN import_match_candidates k ON k.match_id = a.match_id
                JOIN ends x ON x.relation_type_key = a.relation_type_key
                    AND x.direction = a.direction AND x.near = a.record_id AND x.far = k.object_id)
            UPDATE import_links l SET target_id = k.object_id, candidates = 1
            FROM linked k WHERE k.row_id = l.row_id AND k.link_no = l.link_no AND k.turn_of = k.turn
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

    def _value_rows(self) -> None:
        """The rows of the file's value sheets, each by every field a link cell may name it by, in
        one statement per sheet's source (PP-D27). A value is cut at the cell's separator as the
        export writes it. A value a sheet's row holds is that row's record in a match, ahead of a
        context record that held it before (a renamed record is still found by its old value
        unless another row took it)."""
        for plan in self.plans:
            source = plan.source
            if source.under is None:
                continue
            fields = identifying_fields(self.model, source.objectTypeKey)
            values = ["('name', coalesce(r.name, r.current_name))"]
            params: dict[str, Any] = {}
            for number, field_ in enumerate(item for item in fields if item != "name"):
                values.append(f"(:field{number}, r.attributes ->> :field{number})")
                params[f"field{number}"] = field_
            self.session.execute(
                text(
                    f"""
                    INSERT INTO import_value_rows (scope, object_type_key, field, value, record_id)
                    SELECT :scope, r.object_type_key, f.field, replace(f.value, ';', ','),
                        r.record_id
                    FROM import_rows r CROSS JOIN LATERAL (VALUES {", ".join(values)}) AS f(field, value)
                    WHERE r.src = :src AND r.error IS NULL AND r.rep_id IS NULL
                      AND f.value IS NOT NULL AND f.value <> ''
                    """
                ),
                {"scope": source.under.value, "src": plan.order, **params},
            )
        self._sql("ANALYZE import_value_rows")

    def _names_under_parents(self) -> None:
        """D142 (0.10 A8c): a row keyed by name under a parent is the record of that name among the
        parent's children. Such rows took a new ID in :meth:`_identities`, so the file's rows match
        them and stand under them as any new record; level by level, from the rows whose parent is
        settled, each finding a record takes its ID, and every match, parent and link naming the
        row follows."""
        self._sql(
            f"""
            CREATE TEMPORARY TABLE import_pending ON COMMIT DROP AS
            SELECT row_id, record_id FROM import_rows r
            WHERE r.error IS NULL AND r.rep_id IS NULL AND {_UNDER_PARENT.format(r="r")}
            """
        )
        self._sql(
            "CREATE TEMPORARY TABLE import_settled (row_id integer, old text, one text, name text,"
            " n integer) ON COMMIT DROP"
        )
        while True:
            self._sql("TRUNCATE import_settled")
            settled = self.session.execute(
                text(
                    """
                    WITH ready AS (
                        SELECT r.row_id, r.record_id, r.parent_id, r.object_type_key, r.key_value
                        FROM import_rows r JOIN import_pending p ON p.row_id = r.row_id
                        WHERE NOT EXISTS (
                            SELECT 1 FROM import_pending q WHERE q.record_id = r.parent_id)),
                    found AS (
                        SELECT d.row_id, d.record_id, count(c.object_id) AS n,
                            min(c.object_id) AS one, min(c.name) AS name
                        FROM ready d LEFT JOIN import_context c
                            ON c.object_type_key = d.object_type_key
                            AND c.name = d.key_value #>> '{}' AND c.parent_object_id = d.parent_id
                        GROUP BY d.row_id, d.record_id),
                    gone AS (
                        DELETE FROM import_pending p USING found f WHERE p.row_id = f.row_id)
                    INSERT INTO import_settled SELECT row_id, record_id, one, name, n FROM found
                    """
                )
            ).rowcount
            if not settled:
                break
            self._sql(
                """
                UPDATE import_rows r SET error = jsonb_build_object(
                    'code', 'AMBIGUOUS_NAME_KEY',
                    'message', format('%s %s records under the row''s parent are named %s', s.n,
                        r.object_type_key, r.key_value),
                    'details', jsonb_build_object('column', r.key_column, 'count', s.n))
                FROM import_settled s WHERE s.row_id = r.row_id AND s.n > 1
                """
            )
            self._sql("DELETE FROM import_settled WHERE n <> 1")
            self._sql(
                """
                UPDATE import_rows r SET record_id = s.one, existing = true, current_name = s.name
                FROM import_settled s
                -- With the rows that found it by a key another row writes (an existing-records
                -- sheet): they hold the row's provisional ID.
                WHERE r.row_id = s.row_id OR r.rep_id = s.row_id OR r.record_id = s.old
                """
            )
            self._sql(
                "UPDATE import_rows r SET parent_id = s.one FROM import_settled s WHERE r.parent_id = s.old"
            )
            self._sql(
                "UPDATE import_matches m SET resolved = s.one FROM import_settled s WHERE m.resolved = s.old"
            )
            self._sql(
                "UPDATE import_links l SET target_id = s.one FROM import_settled s WHERE l.target_id = s.old"
            )
            self._sql(
                "UPDATE import_related d SET parent_id = s.one FROM import_settled s WHERE d.parent_id = s.old"
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
        # Each row's record's relationships first, both directions as one set of plain equalities,
        # then the related record by its key: joined by an OR of the two directions and planned
        # without statistics, it compared every candidate with every relationship, 53 s for W1′'s
        # 1,400 translations against the 1,400 a first load stored (0.10 R, found by the composed
        # runner).
        self._sql("ANALYZE import_related")
        self._sql("ANALYZE import_context_relations")
        self._sql(
            f"""
            WITH {_ENDS}
            candidates AS (
                SELECT d.entry_id, c.object_id, c.name FROM import_related d
                JOIN import_rows r ON r.row_id = d.row_id AND r.error IS NULL AND r.existing
                JOIN ends x ON x.relation_type_key = d.relation_type_key AND x.direction = d.direction
                    AND x.near = r.record_id
                JOIN import_context c ON c.object_id = x.far AND c.object_type_key = d.object_type_key
                    AND c.parent_object_id = d.parent_id
                    AND (d.match_attr IS NULL OR c.attributes -> d.match_attr = d.attributes -> d.match_attr)
                WHERE d.hint IS NULL),
            counted AS (
                SELECT entry_id, count(DISTINCT object_id) AS n, min(object_id) AS one,
                       min(name) AS name FROM candidates GROUP BY entry_id)
            UPDATE import_related d SET related_id = CASE WHEN c.n = 1 THEN c.one END,
                existing = c.n = 1, current_name = c.name, related_candidates = c.n
            FROM counted c WHERE c.entry_id = d.entry_id
            """
        )
        # A record that exists is written in the application it belongs to, whichever application
        # the profile names for its type (a type several applications list, 0.17 EX1).
        self._sql(
            """
            UPDATE import_related d SET application_key = c.application_key
            FROM import_context c WHERE d.existing AND c.object_id = d.related_id
              AND d.hint IS NULL AND c.application_key IS NOT NULL
            """
        )
        # A new one stands in the application of the parent it goes under (a place is a record of its
        # own application, which may not be the one the profile names for the type).
        self._sql(
            """
            UPDATE import_related d SET application_key = c.application_key
            FROM import_context c WHERE NOT d.existing AND d.parent_id = c.object_id
              AND d.hint IS NULL AND c.application_key IS NOT NULL
            """
        )
        # A related record named by its ID cell (0.17 EX1): the record of that ID the relationship
        # joins to the row's record, wherever it stands; it keeps its parent.
        self._sql(
            f"""
            WITH {_ENDS}
            found AS (
                SELECT d.entry_id, c.object_id, c.name, c.parent_object_id, c.application_key
                FROM import_related d
                JOIN import_rows r ON r.row_id = d.row_id AND r.error IS NULL AND r.existing
                JOIN ends x ON x.relation_type_key = d.relation_type_key AND x.direction = d.direction
                    AND x.near = r.record_id AND x.far = d.hint
                JOIN import_context c ON c.object_id = d.hint AND c.object_type_key = d.object_type_key
                WHERE d.hint IS NOT NULL)
            UPDATE import_related d SET related_id = f.object_id, existing = true,
                current_name = f.name, related_candidates = 1, parent_id = f.parent_object_id,
                application_key = coalesce(f.application_key, d.application_key)
            FROM found f WHERE f.entry_id = d.entry_id
            """
        )
        self._sql(
            """
            UPDATE import_rows r SET error = jsonb_build_object(
                'code', 'REFERENCE_NOT_FOUND',
                'message', format('No %s record with the ID in column %s is related to the row''s record',
                    d.object_type_key, d.column_name),
                'details', jsonb_build_object('column', d.column_name))
            FROM import_related d WHERE d.row_id = r.row_id AND d.hint IS NOT NULL
                AND d.related_id IS NULL AND r.error IS NULL
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
        # Records a column creates by name (D77) run first, each with the first row naming it.
        applications = {
            item.key: key
            for item in self.model.objectTypes
            if (key := self.model.application_of_type(item.key))
        }
        self.session.execute(
            text(
                f"""
                INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
                SELECT 0, n.src, 0, n.row_number, n.match_id, n.ref,
                    jsonb_build_object('op', 'upsert', 'ref', n.ref,
                        'applicationKey', coalesce(
                            (SELECT c.application_key FROM import_context c
                             WHERE m.container <> '' AND c.object_id = m.container),
                            CAST(:applications AS jsonb) ->> m.object_type_key),
                        'objectTypeKey', m.object_type_key, 'key', jsonb_build_object('id', m.resolved),
                        'name', left(btrim(m.value #>> '{{}}'), {MAX_NAME}),
                        'attributes', CASE WHEN m.field = 'cell' AND m.attr NOT IN ('', 'name', '@label')
                            THEN jsonb_build_array(jsonb_build_object(
                                'attributeTypeKey', m.attr, 'value', btrim(m.value #>> '{{}}')))
                            ELSE '[]'::jsonb END)
                    || CASE WHEN m.container <> ''
                        THEN jsonb_build_object('parent', jsonb_build_object('id', m.container))
                        ELSE '{{}}'::jsonb END
                FROM import_matches m
                JOIN LATERAL (
                    SELECT r.src, r.row_number, r.ref, m.match_id FROM import_rows r
                    WHERE r.error IS NULL AND (
                        (r.parent IS NOT NULL AND {_JOINED.format(s="r.parent")})
                        OR EXISTS (SELECT 1 FROM import_links l
                                   WHERE l.row_id = r.row_id AND {_JOINED.format(s="l.match")})
                        OR EXISTS (SELECT 1 FROM import_related d
                                   WHERE d.row_id = r.row_id AND d.parent IS NOT NULL
                                     AND {_JOINED.format(s="d.parent")}))
                    ORDER BY r.src, r.row_number LIMIT 1) n ON true
                WHERE m.created
                """
            ),
            {"applications": json.dumps(applications)},
        )
        # A place this load creates (PP-D24) goes before the first record that stands in it.
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 0, n.src, 0, n.row_number, -1, 'place-' || p.place_id,
                jsonb_build_object('op', 'create', 'ref', 'place-' || p.place_id,
                    'id', p.place_id, 'applicationKey', p.application_key,
                    'objectTypeKey', p.object_type_key, 'name', p.name,
                    'parent', jsonb_build_object('id', p.column_id),
                    'attributes', p.attributes)
            FROM import_new_places p
            JOIN LATERAL (
                SELECT u.src, u.row_number FROM (
                    SELECT r.src, r.row_number FROM import_matches m
                    JOIN import_links l ON {_JOINED.format(s="l.match")}
                    JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
                    WHERE m.created AND m.container = p.place_id
                    UNION ALL
                    SELECT r.src, r.row_number FROM import_related d
                    JOIN import_rows r ON r.row_id = d.row_id AND r.error IS NULL
                    WHERE d.parent_id = p.place_id
                    UNION ALL
                    SELECT r.src, r.row_number FROM import_rows r
                    WHERE r.error IS NULL AND r.parent_id = p.place_id) u
                ORDER BY u.src, u.row_number LIMIT 1) n ON true
            """
        )
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 1, r.src, r.depth, r.row_number, 0, r.ref,
                jsonb_build_object('op', 'upsert', 'ref', r.ref, 'applicationKey', r.application_key,
                    'objectTypeKey', r.object_type_key, 'key', jsonb_build_object('id', r.record_id),
                    'name', coalesce(r.name, r.current_name), 'attributes', {attributes.format(s="r")})
                || CASE WHEN r.expected_version IS NOT NULL AND r.existing
                    THEN jsonb_build_object('expectedVersion', r.expected_version)
                    ELSE '{{}}'::jsonb END
                || CASE WHEN r.parent_id IS NOT NULL
                    THEN jsonb_build_object('parent', jsonb_build_object('id', r.parent_id))
                    ELSE '{{}}'::jsonb END
                || coalesce(required.relations, '{{}}'::jsonb)
            FROM import_rows r
            -- The required links of each row and of the rows repeating its key, collected once
            -- (a lookup per row scanned every link each time: rows times links, 0.10 A3).
            LEFT JOIN (
                SELECT coalesce(g.rep_id, g.row_id) AS row_id,
                    jsonb_build_object('initialRelations', jsonb_agg(DISTINCT jsonb_build_object(
                        'relationTypeKey', l.relation_type_key, 'direction', 'incoming',
                        'object', jsonb_build_object('id', l.target_id)))) AS relations
                FROM import_links l JOIN import_rows g ON g.row_id = l.row_id
                WHERE l.required AND l.target_id IS NOT NULL AND g.error IS NULL
                GROUP BY coalesce(g.rep_id, g.row_id)
            ) required ON required.row_id = r.row_id
            WHERE r.error IS NULL AND r.rep_id IS NULL AND r.mode = 'upsert'
            """
        )
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            SELECT 2, r.src, 0, r.row_number, d.grp, r.ref,
                jsonb_build_object('op', 'upsert', 'ref', r.ref, 'applicationKey', d.application_key,
                    'objectTypeKey', d.object_type_key, 'key', jsonb_build_object('id', d.related_id),
                    'name', left(coalesce(d.name, d.current_name, d.fallback_name), {MAX_NAME}),
                    'attributes', {attributes.format(s="d")})
                || CASE WHEN d.parent_id IS NOT NULL
                    THEN jsonb_build_object('parent', jsonb_build_object('id', d.parent_id))
                    ELSE '{{}}'::jsonb END
                || CASE WHEN d.expected_version IS NOT NULL AND d.existing
                    THEN jsonb_build_object('expectedVersion', d.expected_version)
                    ELSE '{{}}'::jsonb END
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
                || CASE WHEN l.attributes IS NOT NULL
                    THEN jsonb_build_object('attributes', l.attributes) ELSE '{}'::jsonb END
                || CASE WHEN l.expected_version IS NOT NULL
                    THEN jsonb_build_object('expectedVersion', l.expected_version)
                    ELSE '{}'::jsonb END
            FROM (SELECT DISTINCT ON (r.record_id, l.relation_type_key, l.direction, l.target_id)
                    r.src, r.row_number, r.ref, r.record_id, l.link_no, l.relation_type_key,
                    l.direction, l.target_id, l.attributes, l.expected_version
                  FROM import_links l JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
                  WHERE NOT l.replace
                  ORDER BY r.record_id, l.relation_type_key, l.direction, l.target_id, r.row_id,
                    l.link_no) l
            """
        )
        self._sql(
            f"""
            INSERT INTO import_items (phase, src, depth, row_number, sub, ref, item)
            WITH {_ENDS}
            -- A link-matrix column's part of the set (0.17 EX1): the columns the file edits, and the
            -- row's other links, which the replacement keeps.
            edited AS (
                SELECT DISTINCT r.record_id, l.relation_type_key, l.direction, l.object_type_key, l.scope
                FROM import_links l JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
                WHERE l.replace AND l.scope <> ''),
            kept AS (
                SELECT g.record_id, g.relation_type_key, g.direction, g.object_type_key,
                    x.far AS target_id
                FROM (SELECT DISTINCT record_id, relation_type_key, direction, object_type_key
                      FROM edited) g
                JOIN ends x ON x.relation_type_key = g.relation_type_key
                    AND x.direction = g.direction AND x.near = g.record_id
                JOIN import_context c ON c.object_id = x.far AND c.object_type_key = g.object_type_key
                WHERE NOT EXISTS (
                    SELECT 1 FROM edited e JOIN import_scope_values s
                        ON s.scope = e.scope AND s.field = 'name' AND s.object_id = x.far
                    WHERE e.record_id = g.record_id AND e.relation_type_key = g.relation_type_key
                      AND e.direction = g.direction AND e.object_type_key = g.object_type_key)),
            grouped AS (
                SELECT min(r.src) AS src, min(r.row_number) AS row_number, min(r.ref) AS ref,
                    min(r.object_type_key) AS row_type, r.record_id, l.relation_type_key,
                    l.direction, l.object_type_key, min(l.expected_version) AS version,
                    coalesce(jsonb_agg(DISTINCT jsonb_build_object(
                        'object', jsonb_build_object('id', l.target_id)))
                        FILTER (WHERE l.target_id IS NOT NULL), '[]'::jsonb) AS targets
                FROM import_links l JOIN import_rows r ON r.row_id = l.row_id AND r.error IS NULL
                WHERE l.replace
                GROUP BY r.record_id, l.relation_type_key, l.direction, l.object_type_key)
            SELECT 3, g.src, 0, g.row_number, 2000, g.ref,
                jsonb_build_object('op', 'replaceRelationSet', 'ref', g.ref,
                    'relationTypeKey', g.relation_type_key,
                    'fromObjectTypeKey', CASE WHEN g.direction = 'outgoing'
                        THEN g.row_type ELSE g.object_type_key END,
                    'toObjectTypeKey', CASE WHEN g.direction = 'outgoing'
                        THEN g.object_type_key ELSE g.row_type END,
                    'direction', g.direction,
                    'anchor', jsonb_build_object('id', g.record_id),
                    'targets', g.targets || coalesce((
                        SELECT jsonb_agg(jsonb_build_object('object', jsonb_build_object('id', k.target_id)))
                        FROM kept k WHERE k.record_id = g.record_id
                          AND k.relation_type_key = g.relation_type_key
                          AND k.direction = g.direction AND k.object_type_key = g.object_type_key),
                        '[]'::jsonb))
                || CASE WHEN g.version IS NOT NULL
                    THEN jsonb_build_object('expectedRelationSetVersion', g.version)
                    ELSE '{{}}'::jsonb END
            FROM grouped g
            """
        )
        self._sql(
            """
            INSERT INTO import_errors (src, row_number, ref, error)
            SELECT src, row_number, ref, error FROM import_rows WHERE error IS NOT NULL
            """
        )


# A match's row in ``import_matches``; {s} is the match's JSON.
# A row keyed by name under a parent (0.10 A8c, D142), found among the parent's children; {r} is
# the row's alias.
_UNDER_PARENT = "{r}.mode = 'upsert' AND {r}.key_kind = 'name' AND {r}.parent IS NOT NULL"
# A key of several attributes (AP-D43) is held by a row as ``key_attr`` (the JSON list of the
# attribute keys), ``key_column`` (the JSON list of their columns) and ``key_value`` (an object by
# attribute key). Where a statement joins a record of the context to the keys the file uses
# (``k``, with ``k.keys`` the list as jsonb, NULL for a single attribute), the record's value of
# the combination, and whether the record holds every attribute of it:
_COMBINATION_VALUE = (
    "(SELECT jsonb_object_agg(a, {c}.attributes -> a) FROM jsonb_array_elements_text(k.keys) a)"
)
_COMBINATION_HELD = (
    "jsonb_exists_all({c}.attributes, ARRAY(SELECT jsonb_array_elements_text(k.keys)))"
)
# The attribute keys the rows of the file use to find records, each once per type.
_KEYS_USED = (
    "(SELECT DISTINCT object_type_key, key_attr AS attr,"
    " CASE WHEN key_kind = 'combination' THEN CAST(key_attr AS jsonb) END AS keys"
    " FROM import_rows WHERE key_kind IN ('attribute', 'combination'))"
)
# The key's value of a record of the context, and whether it holds one (``k`` as above).
_KEY_OF_RECORD = (
    "CASE WHEN k.keys IS NOT NULL THEN " + _COMBINATION_VALUE + " ELSE c.attributes -> k.attr END"
).format(c="c")
_RECORD_HOLDS_KEY = (
    "CASE WHEN k.keys IS NOT NULL THEN "
    + _COMBINATION_HELD
    + " ELSE c.attributes -> k.attr IS NOT NULL END"
).format(c="c")
# The column a key error points at: a combination's first.
_KEY_COLUMN = "CASE WHEN {r}.key_kind = 'combination' THEN {r}.key_column::jsonb ->> 0 ELSE {r}.key_column END"
# The columns and values of a combination, for a message.
_COMBINATION_TEXT = (
    "(SELECT string_agg(c.col || ' = ' || coalesce({r}.key_value ->> a.attr, ''), ', ' ORDER BY c.i)"
    " FROM jsonb_array_elements_text({r}.key_column::jsonb) WITH ORDINALITY c(col, i)"
    " JOIN jsonb_array_elements_text({r}.key_attr::jsonb) WITH ORDINALITY a(attr, i2) ON a.i2 = c.i)"
)
# What makes rows one key (D69): for upsert rows the type and the key, whichever source of the load
# they come from; for rows keyed by name under a parent, the type, the parent the row names and
# the name (D142); for rows of existing records, the source and the key.
_KEY_GROUP = (
    "CASE WHEN {r}.mode = 'upsert' AND {r}.key_kind = 'name' AND {r}.parent IS NOT NULL"
    " THEN jsonb_build_array({r}.object_type_key, {r}.parent - 'column' - 'create', {r}.key_value)"
    " WHEN {r}.mode = 'upsert'"
    " THEN jsonb_build_array({r}.object_type_key, {r}.key_kind, {r}.key_attr, {r}.key_value)"
    " ELSE jsonb_build_array({r}.src, {r}.key_value) END"
)

_JOINED = (
    "m.object_type_key = {s} ->> 'type' AND m.field = {s} ->> 'field'"
    " AND m.attr = {s} ->> 'attr' AND m.value = {s} -> 'value'"
    " AND m.scope = coalesce({s} ->> 'scope', '')"
    " AND m.label_attr = coalesce({s} ->> 'labelAttr', '')"
    " AND m.container = coalesce({s} ->> 'container', '')"
)

# A match that found no record or several, as a row's refusal; {s} is the match's JSON.
_MATCH_ERROR = (
    "jsonb_build_object("
    "'code', CASE WHEN m.candidates = 0 THEN 'REFERENCE_NOT_FOUND' ELSE 'REFERENCE_AMBIGUOUS' END,"
    " 'message', CASE WHEN m.candidates = 0"
    " THEN format('No %s record matches %s', m.object_type_key, {s} -> 'value')"
    " ELSE format('%s %s records match %s', m.candidates, m.object_type_key, {s} -> 'value') END"
    " || coalesce(' in column ' || ({s} ->> 'column'), ', the source''s parent'),"
    " 'details', jsonb_build_object('column', {s} ->> 'column', 'count', m.candidates))"
)


def _area(source: Source) -> Area:
    return Area.of(source.headerRow, source.block)


def named_columns(source: Source, at: str) -> Iterator[tuple[str, str]]:
    """Every column of the file the source names, with its pointer: those its bindings name and
    those its readings name, but not the columns a reading adds (0.17 PL3b)."""
    added = set(virtual_columns(source))
    for path, name in _binding_columns(source, at):
        if name not in added:
            yield path, name
    for path, name in reading_columns(source):
        yield f"{at}{path}", name


def _binding_columns(source: Source, at: str) -> Iterator[tuple[str, str]]:
    if source.key is not None:
        for name in ("column", "versionColumn", "nameColumn"):
            if getattr(source.key, name) is not None:
                yield f"{at}/key/{name}", getattr(source.key, name)
    for index, binding in enumerate(source.columns):
        if binding.columns is not None:
            for position, name in enumerate(binding.columns):
                yield f"{at}/columns/{index}/columns/{position}", name
        elif binding.column is not None:
            yield f"{at}/columns/{index}/column", binding.column
        if binding.relation is not None:
            relation = binding.relation
            for name in ("idColumn", "versionColumn"):
                if getattr(relation, name) is not None:
                    yield f"{at}/columns/{index}/relation/{name}", getattr(relation, name)
            for position, value in enumerate(relation.attributes):
                yield f"{at}/columns/{index}/relation/attributes/{position}/column", value.column
        if binding.relatedRecord is not None and binding.relatedRecord.versionColumn is not None:
            yield (
                f"{at}/columns/{index}/relatedRecord/versionColumn",
                binding.relatedRecord.versionColumn,
            )
        if binding.relatedRecord is not None and binding.relatedRecord.idColumn is not None:
            yield (
                f"{at}/columns/{index}/relatedRecord/idColumn",
                binding.relatedRecord.idColumn,
            )
        if (
            binding.relatedRecord is not None
            and binding.relatedRecord.parent is not None
            and binding.relatedRecord.parent.column is not None
        ):
            yield (
                f"{at}/columns/{index}/relatedRecord/parent/column",
                binding.relatedRecord.parent.column,
            )


# --- a profile check's findings (0.10 A5c, D83) -----------------------------------------------------


def _findings(session: Session) -> dict[str, list[dict[str, Any]]]:
    """What a profile's check lists, read from the temporary tables before they go: each value of
    a match column that names no record of the context (one the load creates, or refuses), with
    its rows; each row whose key finds a record by another name than the row's (drift); each record
    missing from the file. Every list in source, then column or row order."""
    new_values = session.execute(
        text(
            f"""
            SELECT c.src, c.column_name, m.value, m.created, count(*) AS cells
            FROM import_match_cells c JOIN import_matches m ON {_JOINED.format(s="c.match")}
            WHERE m.created OR m.candidates = 0
            GROUP BY c.src, c.column_name, m.value, m.created
            ORDER BY c.src, c.column_name, m.value #>> '{{}}'
            """
        )
    ).all()
    drift = session.execute(
        text(
            """
            SELECT src, row_number, record_id, key_value, name, current_name FROM import_rows
            WHERE existing AND mode = 'upsert' AND name IS NOT NULL
              AND current_name IS DISTINCT FROM name
            ORDER BY src, row_number
            """
        )
    ).all()
    missing = session.execute(
        text(
            "SELECT src, object_id, name, key_value FROM import_missing ORDER BY src, name, object_id"
        )
    ).all()
    return {
        "newValues": [
            {
                "source": src,
                "column": column_name,
                "value": value,
                "created": created,
                "cells": cells,
            }
            for src, column_name, value, created, cells in new_values
        ],
        "drift": [
            {
                "source": src,
                "row": number,
                "recordId": record_id,
                "key": key,
                "name": name,
                "recordName": current,
            }
            for src, number, record_id, key, name, current in drift
        ],
        "missingRecords": [
            {"source": src, "recordId": object_id, "name": name, "key": key}
            for src, object_id, name, key in missing
        ],
    }


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
