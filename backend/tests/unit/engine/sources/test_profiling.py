"""A source file's profile (``engine/sources/profiling.py``, 0.10 A3): header rows and blocks
(``find_headers``, D68).

A block is a run of columns between empty columns; each row is given as its number, its filled
columns and whether every cell is text.
"""

from app.engine.sources.profiling import find_headers


def _rows(*rows):
    return [(number, frozenset(columns), text) for number, columns, text in rows]


def test_a_table_header_is_its_first_row():
    rows = _rows((1, {1, 2, 3}, True), (2, {1, 2, 3}, False), (3, {1, 3}, False))
    assert find_headers([(1, 3)], [rows]) == [1]


def test_a_title_row_above_the_header_is_passed_over():
    rows = _rows((1, {1}, True), (2, {1, 2, 3}, True), (3, {1, 2, 3}, False))
    assert find_headers([(1, 3)], [rows]) == [2]


def test_a_block_starting_after_an_empty_first_column():
    rows = _rows((4, {2, 3}, True), (5, {2, 3}, True), (6, {3}, False))
    assert find_headers([(2, 3)], [rows]) == [4]


def test_one_column_lists_under_section_and_group_rows_share_their_header_row():
    sectioned = _rows((1, {1}, True), (2, {1}, True), (3, {1}, True), (4, {1}, True))
    grouped = _rows((2, {3}, True), (3, {3}, True), (4, {3}, True))
    plain = _rows((3, {5, 6}, True), (4, {5, 6}, True), (5, {5}, True))
    assert find_headers([(1, 1), (3, 3), (5, 6)], [sectioned, grouped, plain]) == [3, 3, 3]


def test_without_a_shared_row_each_block_has_its_own():
    left = _rows((1, {1, 2}, True), (2, {1, 2}, False))
    right = _rows((5, {4}, True), (6, {4}, False))
    assert find_headers([(1, 2), (4, 4)], [left, right]) == [1, 5]


def test_a_header_with_an_empty_cell_is_the_text_row_with_the_most_cells():
    rows = _rows((1, {1}, True), (2, {1, 3}, True), (3, {1, 2, 3}, False))
    assert find_headers([(1, 3)], [rows]) == [2]


def test_a_block_of_numbers_only_has_no_header():
    rows = _rows((1, {1, 2}, False), (2, {1, 2}, False))
    assert find_headers([(1, 2)], [rows]) == [None]
