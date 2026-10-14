"""The lists of a sheet laid out for reading (``engine/sources/layout.py``, 0.10 A8a, D115, D119).

A sheet is given as a grid of the cells written into it; each case names the shape it holds, as the
user's reading-layout workbooks do: lists side by side and stacked, a header with an empty row under
it, titles over several lists, a note under a header and prose.
"""

from app.engine.sources.layout import Cell, note_meaning, split


def _grid(cells: dict[tuple[int, int], str]) -> dict[int, dict[int, Cell]]:
    grid: dict[int, dict[int, Cell]] = {}
    for (row, column), value in cells.items():
        grid.setdefault(row, {})[column] = Cell(value, len(value))
    return grid


def _runs(cells: dict[tuple[int, int], str]) -> list[tuple[int, int]]:
    runs: list[list[int]] = []
    for column in sorted({c for _, c in cells}):
        if runs and runs[-1][1] == column - 1:
            runs[-1][1] = column
        else:
            runs.append([column, column])
    return [(a, b) for a, b in runs]


def _lists(cells: dict[tuple[int, int], str]) -> list[tuple[int, int, int, int, tuple[str, ...]]]:
    return [
        (b.first_column, b.last_column, b.header_row, b.last_row, b.titles)
        for b in split(_runs(cells), _grid(cells))
    ]


def _column(column: int, top: int, *values: str) -> dict[tuple[int, int], str]:
    return {(top + offset, column): value for offset, value in enumerate(values)}


def test_lists_side_by_side_under_a_section_and_a_group_title_share_their_header_row():
    cells = {
        **_column(1, 1, "Section", "Group", "Colours", "Red", "Blue"),
        **_column(3, 3, "Sizes", "Small", "Large", "Huge"),
        **_column(5, 2, "Other group", "Shapes", "Round"),
        **_column(7, 3, "Weights", "Light", "Heavy"),
    }
    assert _lists(cells) == [
        (1, 1, 3, 5, ("Section", "Group")),
        (3, 3, 3, 6, ("Section", "Group")),
        (5, 5, 3, 4, ("Section", "Other group")),
        (7, 7, 3, 5, ("Section", "Other group")),
    ]


def test_lists_stacked_in_one_run_are_split_at_empty_rows_each_under_its_header():
    cells = {
        **_column(1, 1, "Status", "Open", "Closed"),
        **_column(1, 5, "Format", "Paper", "Screen", "Phone"),
        **_column(2, 5, "Formato", "Papel", "Pantalla", "Vía"),
    }
    assert _lists(cells) == [(1, 1, 1, 3, ()), (1, 2, 5, 8, ())]


def test_a_header_followed_by_an_empty_row_keeps_its_values():
    cells = {**_column(1, 1, "Kinds"), **_column(1, 3, "Big", "Small"), **_column(3, 1, "Ways"), **_column(3, 3, "Fast", "Slow", "Late")}
    assert _lists(cells) == [(1, 1, 1, 4, ()), (3, 3, 1, 5, ())]


def test_a_one_cell_row_over_lists_side_by_side_is_their_title_not_a_header():
    cells = {
        (2, 1): "Intake",
        **_column(1, 4, "Type", "One", "Two"),
        **_column(3, 4, "Role", "Main", "Partner"),
        **_column(5, 4, "Reason", "First", "Second", "Third"),
    }
    assert _lists(cells) == [(1, 1, 4, 6, ("Intake",)), (3, 3, 4, 6, ("Intake",)), (5, 5, 4, 7, ("Intake",))]


def test_a_title_reaches_the_lists_up_to_the_next_title_on_its_row():
    cells = {
        (1, 1): "Medical",
        (1, 5): "Lab",
        **_column(1, 3, "Exams", "Scan", "Biopsy"),
        **_column(3, 3, "Therapies", "Infusion", "Injection"),
        **_column(5, 3, "Blood", "Count", "Iron"),
        **_column(7, 3, "Seat", "Wash", "Count"),
    }
    assert [t for *_, t in _lists(cells)] == [("Medical",), ("Medical",), ("Lab",), ("Lab",)]


def test_titles_on_rows_apart_are_sections_one_after_the_other_not_levels():
    cells = {
        (1, 1): "Episode",
        **_column(1, 3, "Type", "One", "Two"),
        **_column(3, 3, "Role", "Main", "Partner"),
        (7, 1): "Person",
        **_column(1, 9, "Gender", "Female", "Male"),
        **_column(3, 9, "Status", "Single", "Married"),
    }
    assert [t for *_, t in _lists(cells)] == [("Episode",), ("Person",), ("Episode",), ("Person",)]


def test_prose_under_a_list_is_no_part_of_it():
    sentence = "These values are reviewed every year by the people who maintain the catalogue."
    cells = {**_column(1, 1, "Kinds", "Big", "Small"), (5, 1): sentence, **_column(3, 1, "Ways", "Fast", "Slow")}
    assert _lists(cells) == [(1, 1, 1, 3, ()), (3, 3, 1, 3, ())]


def test_a_header_with_nothing_under_it_is_a_list_without_values():
    cells = {
        (1, 1): "Category", (1, 2): "Categoría",
        (3, 1): "Status", (3, 2): "Estado",
        **_column(1, 5, "Open", "Closed"),
        **_column(2, 5, "Abierto", "Suspendido"),
    }
    assert _lists(cells) == [(1, 2, 1, 1, ()), (1, 2, 3, 6, ())]


def test_a_note_under_the_header_is_found_with_what_it_says():
    cells = {**_column(1, 1, "Reasons", "(Multiple answers)", "First", "Second"), **_column(2, 1, "Motivos", "(Varias vías)", "Primero", "Segundo")}
    (found,) = split(_runs(cells), _grid(cells))
    assert found.note == {"row": 2, "text": "(Multiple answers)", "meaning": "many"}


def test_note_words_are_folded_and_values_are_not_notes():
    assert [note_meaning(v) for v in ("Multiple choice", "(multiple answer)", "Free field", "Single answer", "Several")] == [
        "many", "many", "free", "one", "many"
    ]
    assert [note_meaning(v) for v in ("Multiple", "Free", "Open", "Several kinds")] == [None, None, None, None]
