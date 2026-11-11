"""A source file read from its staged cells gives the reader's rows (``engine/sources/staged.py``,
0.10 A3, D66): the dry run binds them through the same binding as an import of the file. An empty
cell reads as ``None``, where the CSV reader gives an empty string: the binding reads both as no
value (``cells.is_empty``)."""

# A workbook's dates are naive, as openpyxl reads them.
# ruff: noqa: DTZ001

import csv
import io
from datetime import datetime

import pytest
from openpyxl import Workbook

from app.db import SessionLocal
from app.engine.imports.cells import is_empty
from app.engine.imports.readers import Area, open_tabular
from app.engine.sources.profiling import profile_source_file
from app.engine.sources.staged import StagedFile
from app.models.database import ModelDraft, SourceFile

ROWS = [
    ("Code", "Name", "Count", "Since", "Active", None, "Note"),
    ("A1", "Alpha", 3, datetime(2026, 1, 2), True, None, None),
    (None, None, None, None, None, None, None),
    ("A2", "  Beta ", 2.5, datetime(2026, 1, 2, 9, 30), False, None, "x;y"),
    ("A3", None, None, None, None, None, "tail"),
]


def _cells(rows):
    return [
        (number, [None if is_empty(cell) else cell for cell in cells]) for number, cells in rows
    ]


def _xlsx(path):
    book = Workbook()
    sheet = book.active
    sheet.title = "Main"
    sheet.append(["Report"])
    for row in ROWS:
        sheet.append(list(row))
    book.create_sheet("Empty")
    buffer = io.BytesIO()
    book.save(buffer)
    path.write_bytes(buffer.getvalue())


def _csv(path):
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=";").writerows(
        [["" if cell is None else str(cell) for cell in row] for row in ROWS]
    )
    path.write_text(buffer.getvalue(), encoding="utf-8")


@pytest.mark.parametrize(
    ("file_format", "write", "areas"),
    [
        ("xlsx", _xlsx, [Area(2), Area(1), Area.of(2, None)]),
        ("csv", _csv, [Area(1), Area(2, first_column=2, last_column=4, last_row=4)]),
    ],
)
def test_staged_rows_and_tables_are_the_readers(seeded, tmp_path, file_format, write, areas):
    path = tmp_path / f"file.{file_format}"
    write(path)
    delimiter = ";" if file_format == "csv" else None
    with SessionLocal() as session:
        draft = ModelDraft(name="Staged", model_json={})
        session.add(draft)
        session.flush()
        source = SourceFile(
            draft_id=draft.id,
            name=path.name,
            format=file_format,
            bytes=1,
            sha256="0" * 64,
            csv_delimiter=delimiter,
        )
        session.add(source)
        session.flush()
        profile_source_file(session, source.public_id, path, lambda: None)

        reader = open_tabular(path, file_format, delimiter or ",")
        staged = StagedFile(session, source.id)
        try:
            names = [name for name in reader.sheet_names if name != "Empty"]
            assert staged.sheet_names[: len(names)] == names
            for name in names:
                assert _cells(staged.rows(name)) == _cells(reader.rows(name))
                for area in areas:
                    expected, found = reader.table(name, area), staged.table(name, area)
                    assert (
                        found.header[: len(expected.header)] == expected.header[: len(found.header)]
                    )
                    width = len(found.header)
                    assert _cells(
                        (number, cells[:width]) for number, cells in expected.rows
                    ) == _cells(found.rows)
        finally:
            reader.close()
        session.rollback()
