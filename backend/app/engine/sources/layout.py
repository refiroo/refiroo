"""The lists of a sheet laid out for reading (Product 0.10 A8a, D115, D119).

A sheet with no main table (``inference.facts.main_block``) holds lists placed side by side, in
column runs split by empty columns (A3, D68), and stacked in a run, split by empty rows. This module
reads such a sheet's filled cells, a bounded set the profile hands it, and finds each list:

- **Prose** (a row of a run whose cells average more than :data:`PROSE_AVERAGE` characters) is no
  part of any list and is read as if the row were empty there.
- A run's rows split at every empty row into **parts**. Parts of different runs whose rows overlap,
  directly or through others, form a **band**; a band's **header row** is the row most of its parts
  start on (the first of equals), as lists side by side share their header row.
- A one-row part directly above a part (at most one empty row between) is its header, unless it
  is one cell and a part of another run starts on the same row with no one-row part above it: then
  it is a **title** over them.
- A part holding its band's header row (the row most parts without a header start on, at least
  two, with values under it in two parts at least) under nothing but one-cell rows has that row as
  its header, and those rows are titles. A part under a header with nothing below it (at most one
  empty row between) is that header's list; any other part's header is its first row. A one-row
  part left over is a title when it is one cell, else a header with no values.
- A list's **note** (D119) is the first row under its header when a cell of it is a note word;
  else, in a list with yes/no columns, a **second header row** (0.10 A8c, D144): a first row naming
  something and answering none of them while every later row answers one.
- A list's titles are the nearest title above it whose columns reach it (a title reaches from its
  column to the next title on its row) and the titles on the rows directly above that one.

Colour, bold and merged cells are not read (A-D9): a merged title is the text of its first cell.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

# A row of a run whose cells average more than this many characters is prose, not a list.
PROSE_AVERAGE = 60
# D119: words that note how a list is answered, folded (case, brackets, punctuation, a final "s").
NOTE_WORDS = {
    "multiple answer": "many",
    "multiple choice": "many",
    "multi select": "many",
    "several": "many",
    "single answer": "one",
    "single choice": "one",
    "one answer": "one",
    "free field": "free",
    "free text": "free",
}
# The words of a yes/no column (A6's vocabularies), which tell a second header row (D144).
YES_NO = frozenset({"y", "n", "yes", "no", "x", "true", "false", "1", "0"})


def note_meaning(value: str) -> str | None:
    """What a note word says of a list (D119): ``many``, ``one`` or ``free``; ``None`` for a value."""
    words = re.findall(r"[a-z0-9]+", value.lower())
    folded = " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words)
    return NOTE_WORDS.get(folded)


@dataclass(frozen=True)
class Cell:
    text: str
    length: int


# A sheet's cells by row, then by column.
Grid = Mapping[int, Mapping[int, Cell]]


@dataclass
class Found:
    """A list of the sheet: its columns, header row, last row and what lies around it."""

    first_column: int
    last_column: int
    header_row: int
    last_row: int
    titles: tuple[str, ...] = ()
    note: dict[str, object] | None = None


@dataclass
class _Part:
    run: int
    rows: list[int]
    header: int | None = None
    data: list[int] = field(default_factory=list)
    consumed: bool = False

    @property
    def first(self) -> int:
        return self.rows[0]

    @property
    def last(self) -> int:
        return self.rows[-1]


def split(runs: Sequence[tuple[int, int]], grid: Grid) -> list[Found]:
    """The lists of a sheet of ``runs`` (first and last column) and its ``grid``, ordered by column
    then row."""
    prose = _prose(runs, grid)
    parts: list[_Part] = []
    for index, (first, last) in enumerate(runs):
        rows = [
            row
            for row in sorted(grid)
            if any(first <= column <= last and (row, column) not in prose for column in grid[row])
        ]
        for row in rows:
            if parts and parts[-1].run == index and parts[-1].last == row - 1:
                parts[-1].rows.append(row)
            else:
                parts.append(_Part(index, [row]))
    titles: list[tuple[int, int, str]] = []

    def cells(part: _Part, row: int) -> dict[int, Cell]:
        first, last = runs[part.run]
        return {c: v for c, v in grid[row].items() if first <= c <= last and (row, c) not in prose}

    by_run: dict[int, list[_Part]] = {}
    for part in parts:
        by_run.setdefault(part.run, []).append(part)

    def above_of(part: _Part) -> _Part | None:
        """The part directly above in its run, at most one empty row between."""
        run_parts = by_run[part.run]
        position = run_parts.index(part)
        if position == 0:
            return None
        above = run_parts[position - 1]
        return above if part.first - above.last - 1 <= 1 else None

    def headed(part: _Part) -> bool:
        above = above_of(part)
        return above is not None and len(above.rows) == 1

    # A one-row part directly above a list is its header, unless it is one cell over lists beside
    # it that start on the same row with no such row above them: then it is their title.
    for run_parts in by_run.values():
        for part in reversed(run_parts):
            above = above_of(part)
            if part.header is not None or part.consumed or len(part.rows) < 2 or above is None:
                continue
            if above.consumed or above.header is not None or len(above.rows) != 1:
                continue
            siblings = [p for p in parts if p.run != part.run and p.first == part.first and not headed(p)]
            if len(cells(above, above.first)) == 1 and siblings:
                continue
            part.header, part.data = above.first, list(part.rows)
            part.rows = above.rows + part.rows
            above.consumed = True
    # Lists side by side share their band's header row.
    for band in _bands([p for p in parts if not p.consumed]):
        open_parts = [p for p in band if p.header is None]
        starts: dict[int, int] = {}
        for part in open_parts:
            starts[part.first] = starts.get(part.first, 0) + 1
        if not starts:
            continue
        header = min(starts, key=lambda row: (-starts[row], row))
        if starts[header] < 2 or sum(1 for p in open_parts if p.last > header) < 2:
            continue
        for part in open_parts:
            above = [row for row in part.rows if row < header]
            if header in part.rows and all(len(cells(part, row)) == 1 for row in above):
                part.header = header
                part.data = [r for r in part.rows if r > header]
                for row in above:
                    column, cell = min(cells(part, row).items())
                    titles.append((row, column, cell.text))
    for run_parts in by_run.values():
        # A header with nothing under it takes the list after its empty row.
        for part in reversed(run_parts):
            above = above_of(part)
            if part.header is not None or part.consumed or len(part.rows) < 2 or above is None:
                continue
            if not above.consumed and above.header == above.last and not above.data:
                part.header, part.data = above.header, list(part.rows)
                part.rows = above.rows + part.rows
                above.consumed = True
        for part in run_parts:
            if part.header is not None or part.consumed:
                continue
            if len(part.rows) >= 2:
                part.header, part.data = part.first, part.rows[1:]
            elif len(cells(part, part.first)) == 1:
                column, cell = min(cells(part, part.first).items())
                titles.append((part.first, column, cell.text))
                part.consumed = True
            else:
                part.header, part.data = part.first, []
    found = []
    for part in parts:
        if part.consumed or part.header is None:
            continue
        used = [c for row in (part.header, *part.data) for c in cells(part, row)]
        block = Found(min(used), max(used), part.header, part.data[-1] if part.data else part.header)
        if part.data:
            under = cells(part, part.data[0])
            meaning = next(((cell.text, note_meaning(cell.text)) for _, cell in sorted(under.items()) if note_meaning(cell.text)), None)
            if meaning is not None:
                block.note = {"row": part.data[0], "text": meaning[0], "meaning": meaning[1]}
            else:
                block.note = heading(block.first_column, block.last_column, [(row, cells(part, row)) for row in part.data])
        block.titles = _titles_of(block, titles)
        found.append(block)
    return sorted(found, key=lambda b: (b.first_column, b.header_row))


def heading(first_column: int, last_column: int, rows: Sequence[tuple[int, Mapping[int, Cell]]]) -> dict[str, object] | None:
    """D144 (0.10 A8c): a second header row, read as the list's note. In a list with yes/no
    columns (every value one of :data:`YES_NO`), its first row under the header (``rows``, by row
    number, with their cells) when it names something and answers none of them while every later
    row answers one at least."""
    if len(rows) < 2:
        return None
    (first_row, first), later = rows[0], [cells for _, cells in rows[1:]]
    flags = [
        column
        for column in range(first_column + 1, last_column + 1)
        if any(column in row for row in later)
        and all(row[column].text.strip().lower() in YES_NO for row in later if column in row)
    ]
    if not flags or first_column not in first or any(column in first for column in flags):
        return None
    if not all(any(column in row for column in flags) for row in later):
        return None
    return {"row": first_row, "text": first[first_column].text, "meaning": "heading"}


def _prose(runs: Sequence[tuple[int, int]], grid: Grid) -> set[tuple[int, int]]:
    """The cells of each run's rows of prose."""
    found: set[tuple[int, int]] = set()
    for first, last in runs:
        for row, columns in grid.items():
            inside = [(c, v) for c, v in columns.items() if first <= c <= last]
            if inside and sum(v.length for _, v in inside) / len(inside) > PROSE_AVERAGE:
                found |= {(row, c) for c, _ in inside}
    return found


def _bands(parts: list[_Part]) -> list[list[_Part]]:
    """Parts whose rows overlap, directly or through others."""
    ordered = sorted(parts, key=lambda p: (p.first, p.last))
    bands: list[list[_Part]] = []
    reach = -1
    for part in ordered:
        if bands and part.first <= reach:
            bands[-1].append(part)
            reach = max(reach, part.last)
        else:
            bands.append([part])
            reach = part.last
    return bands


def _titles_of(block: Found, titles: list[tuple[int, int, str]]) -> tuple[str, ...]:
    """The nearest title reaching the block from above, and those on the rows directly above it."""

    def reaches(title: tuple[int, int, str]) -> bool:
        row, column, _ = title
        if row >= block.header_row or column > block.first_column:
            return False
        beside = [c for r, c, _ in titles if r == row and column < c <= block.first_column]
        return not beside

    above = sorted((t for t in titles if reaches(t)), key=lambda t: -t[0])
    if not above:
        return ()
    chosen = [above[0]]
    for title in above[1:]:
        if title[0] == chosen[-1][0] - 1:
            chosen.append(title)
    return tuple(t[2] for t in reversed(chosen))
