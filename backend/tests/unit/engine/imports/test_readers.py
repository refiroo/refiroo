"""Reading an import's CSV and XLSX files (``engine/imports/readers.py``, 0.9 J2).

The CSV dialect's edges: a byte order mark, another delimiter, a quoted value across lines (rows are
numbered by record), broken quoting and text that is not UTF-8, refused with where it failed. A
block narrows a sheet; a header row past the end is no table; empty rows are left out.
"""

import io

import pytest
from openpyxl import Workbook

from app.engine.imports.readers import Area, CsvFile, XlsxFile
from app.errors import ApiError


def _csv(tmp_path, content: bytes, delimiter=","):
    path = tmp_path / "file.source"
    path.write_bytes(content)
    return CsvFile(path, delimiter)


def _rows(table):
    return list(table.rows)


def test_a_bom_another_delimiter_and_a_value_across_lines(tmp_path):
    content = '﻿Name;Note\n"Alpha";"two\nlines"\n\nBeta;"say ""hi"""\n'.encode()
    table = _csv(tmp_path, content, ";").table(None, Area())
    assert table.header == ["Name", "Note"]
    assert _rows(table) == [(2, ["Alpha", "two\nlines"]), (4, ["Beta", 'say "hi"'])]


def test_a_header_row_further_down_and_a_block(tmp_path):
    content = b"title,,\nA,B,C\n1,2,3\n4,5,6\n"
    table = _csv(tmp_path, content).table(None, Area(2, 2, 3, 3))
    assert table.header == ["B", "C"]
    assert _rows(table) == [(3, ["2", "3"])]
    assert _csv(tmp_path, content).table(None, Area(9)) is None


@pytest.mark.parametrize(
    ("content", "fragment"),
    [(b'Name\n"open\nnever closed', "quoting"), (b"Name\n\xff\xfe broken", "UTF-8")],
)
def test_a_file_the_reader_cannot_read_is_refused_saying_where(tmp_path, content, fragment):
    with pytest.raises(ApiError) as caught:
        _rows(_csv(tmp_path, content).table(None, Area()))
    assert caught.value.code == "IMPORT_FILE_UNREADABLE" and fragment in caught.value.message


def test_a_workbook_is_read_by_its_values_and_a_bad_one_refused(tmp_path):
    book = Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append(["Code", "Total", None])
    sheet.append(["007", 3, None])
    sheet.append([None, None, None])
    sheet.append(["a_x0001_b", "=1+2", None])
    buffer = io.BytesIO()
    book.save(buffer)
    path = tmp_path / "book.source"
    path.write_bytes(buffer.getvalue())
    workbook = XlsxFile(path)
    table = workbook.table("Data", Area())
    assert table.header == ["Code", "Total", None]
    rows = _rows(table)
    assert rows[0] == (2, ["007", 3, None])
    assert rows[1][0] == 4 and rows[1][1][0] == "a\x01b"
    workbook.close()

    path.write_bytes(b"not a workbook")
    with pytest.raises(ApiError) as caught:
        XlsxFile(path)
    assert caught.value.code == "IMPORT_FILE_UNREADABLE"
