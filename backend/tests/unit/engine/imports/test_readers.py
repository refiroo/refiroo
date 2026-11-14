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


def test_every_column_of_a_header_that_repeats_a_name_can_be_named(tmp_path):
    path = tmp_path / "wide.csv"
    path.write_text("ID,Currency,Price,Currency,Price,Currency,Currency #2\nA,EUR,1,USD,2,GBP,x\n")
    file = CsvFile(path, ",")
    columns = file.table(None, Area()).columns()
    assert columns["Currency"] == 1
    assert columns["Price #2"] == 4
    assert columns["Currency #3"] == 5
    # A column really called that keeps its name.
    assert columns["Currency #2"] == 6


def test_a_csv_row_shorter_than_its_header_is_padded_to_its_width(tmp_path):
    table = _csv(tmp_path, b"A,B,C\n1,2\n3\n").table(None, Area())
    assert _rows(table) == [(2, ["1", "2", None]), (3, ["3", None, None])]


def _with_dimension(path, ref):
    """The workbook at ``path`` with its first sheet declaring ``ref`` as its dimension."""
    import re
    import zipfile

    source = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source)) as old, zipfile.ZipFile(path, "w") as new:
        for item in old.infolist():
            data = old.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = re.sub(rb'<dimension ref="[^"]*"', f'<dimension ref="{ref}"'.encode(), data)
            new.writestr(item, data)


def test_a_workbook_declaring_a_wrong_dimension_is_read_whole_and_padded(tmp_path):
    book = Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append(["A", "B", "C", "D"])
    sheet.append(["1", "2", "3", "4"])
    sheet.append(["5", None, None, None])
    sheet.append(["6", "7", None, "8"])
    path = tmp_path / "book.source"
    book.save(path)
    _with_dimension(path, "A1:B2")
    workbook = XlsxFile(path)
    table = workbook.table("Data", Area())
    assert table.header == ["A", "B", "C", "D"]
    assert _rows(table) == [
        (2, ["1", "2", "3", "4"]),
        (3, ["5", None, None, None]),
        (4, ["6", "7", None, "8"]),
    ]
    assert [cells[0] for _, cells in workbook.rows("Data")] == ["A", "1", "5", "6"]
    workbook.close()


def test_a_workbook_part_that_is_not_xml_is_refused_not_a_server_error(tmp_path):
    import zipfile

    book = Workbook()
    book.active.append(["A"])
    path = tmp_path / "book.source"
    book.save(path)
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as old, zipfile.ZipFile(path, "w") as new:
        for item in old.infolist():
            data = old.read(item.filename)
            new.writestr(item, b"<not xml" if item.filename == "xl/worksheets/sheet1.xml" else data)
    with pytest.raises(ApiError) as caught:
        XlsxFile(path).table(None, Area())
    assert caught.value.code == "IMPORT_FILE_UNREADABLE"


def test_a_value_in_a_column_without_a_heading_is_read_with_the_declared_width_or_beyond_it(
    tmp_path,
):
    """A heading row below the first row; the last column has no heading. With the right dimension
    the column is part of the table (a binding by letter can name it); with a dimension too short
    its value is still in the row, never cut off."""
    book = Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append(["Title"])
    sheet.append(["A", "B", None])
    sheet.append(["1", "2", "3"])
    path = tmp_path / "book.source"
    book.save(path)
    workbook = XlsxFile(path)
    table = workbook.table("Data", Area(2))
    assert table.header == ["A", "B", None]
    assert _rows(table) == [(3, ["1", "2", "3"])]
    workbook.close()

    for declared in ("A1:B3", "A1:A1"):
        _with_dimension(path, declared)
        again = XlsxFile(path)
        table = again.table("Data", Area(2))
        assert table.header[:2] == ["A", "B"]
        assert _rows(table) == [(3, ["1", "2", "3"])]
        again.close()
