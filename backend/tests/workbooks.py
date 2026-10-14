"""The acceptance workbooks W1, W1′, W2 and W3 (BASE_0_10_IMPLEMENTATION_PLAN, acceptance
workbooks; 0.10 A3).

Synthetic workbooks with the shapes of the private samples, generated from a seed and a size, so a
fixture is deterministic and holds no client data. Headers are plain words of an invented
office-supplies catalogue; tests name the **structures** (``K``, ``N``, ``P``, …) and read the
header a structure has from the generated workbook, never a header text.

- **W1**, sheet ``S1`` (one row per record): ``K`` the key (unique, code-like); ``N`` the name
  (names repeat across records);
  ``P`` a parent repeated per row (about ``n/15`` distinct) with ``Po`` its sort order and ``Pi``
  its external ID; ``T`` a text lookup (8 values) with ``N/A`` and ``-`` on about 5% of rows; ``Lc``
  and ``Ln`` a code and name pair (6 codes, two of them carrying two names); ``F1``, ``F2`` two
  Y/N columns and ``Fo`` a text column, ``;``-separated on some rows, naming members of one set;
  ``X`` a GUID per row. Sheet ``S2``: ``K``, ``Lang`` and ``N`` translated, one row per record and
  language (7), one ``N`` differing from ``S1``'s for its language.
- **W1′**: W1 with 5 records changed, 3 added, 2 missing, one new ``T`` value, a new column ``Y``,
  and ``Ln`` renamed.
- **W2**: sheet ``D`` describing W1's ``T``, ``Lc`` and the flag set (field code, field type, lookup
  target); one sheet per lookup with ID and name; ``?`` IDs, a list "to be defined", names drifting
  from W1 for the same IDs, and only part of W1's IDs.
- **W3**: one sheet of 20–40 blocks side by side, separated by empty columns, under a section row
  and a group row; some blocks with a column per language, some with a Y/N column per item, some
  with a "multiple answers" note under the header.
"""

import io
import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from openpyxl import Workbook

S1, S2 = "Items", "Item names"
HEADERS = {
    "K": "Item code",
    "N": "Item name",
    "P": "Category",
    "Po": "Category order",
    "Pi": "Category ID",
    "T": "Material",
    "Lc": "Colour code",
    "Ln": "Colour",
    "F1": "Recycled",
    "F2": "Refillable",
    "Fo": "Other features",
    "X": "Supplier ID",
}
S2_HEADERS = {"K": "Item code", "Lang": "Language", "N": "Item name"}
LANGUAGES = ("en", "de", "fr", "es", "it", "nl", "pl")
MATERIALS = ("Paper", "Card", "Plastic", "Steel", "Aluminium", "Wood", "Glass", "Fabric")
PLACEHOLDERS = ("N/A", "-")
COLOURS = {
    "C1": ("Black",),
    "C2": ("Navy", "Navy blue"),
    "C3": ("Red",),
    "C4": ("Green", "Leaf green"),
    "C5": ("White",),
    "C6": ("Yellow",),
}
FEATURES = ("Compact", "Eco", "Bulk", "Gift")
NOUNS = ("Folder", "Pen", "Stapler", "Binder", "Marker", "Ruler", "Clip", "Notebook", "Tray")
ADJECTIVES = ("Classic", "Slim", "Large", "Mini", "Office", "Studio", "Desk", "Travel")


@dataclass
class W1:
    """A generated W1 (or W1′): its file, its rows by structure, and what the tests check."""

    content: bytes
    rows: list[dict[str, Any]]
    names: list[dict[str, Any]]
    headers: dict[str, str] = field(default_factory=lambda: dict(HEADERS))

    def header(self, structure: str) -> str:
        return self.headers[structure]

    def column(self, structure: str) -> str:
        """The structure's column letter in ``S1``."""
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[list(self.headers).index(structure)]

    def distinct(self, structure: str) -> set[Any]:
        return {row[structure] for row in self.rows}


def w1(seed: int = 1, rows: int = 200) -> W1:
    rng = random.Random(seed)
    parents = max(1, rows // 15)
    categories = [
        (f"Category {index + 1:02d}", index + 1, str(uuid.UUID(int=rng.getrandbits(128))))
        for index in range(parents)
    ]
    records = []
    for index in range(rows):
        category, order, category_id = rng.choice(categories)
        code = rng.choice(sorted(COLOURS))
        features = rng.sample(FEATURES, rng.randint(0, 2))
        records.append(
            {
                "K": f"IT-{index + 1:05d}",
                "N": f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)}",
                "P": category,
                "Po": order,
                "Pi": category_id,
                "T": rng.choice(PLACEHOLDERS) if rng.random() < 0.05 else rng.choice(MATERIALS),
                "Lc": code,
                "Ln": rng.choice(COLOURS[code]),
                "F1": rng.choice("YN"),
                "F2": rng.choice("YN"),
                "Fo": "; ".join(features) if len(features) > 1 else (features[0] if features else None),
                "X": str(uuid.UUID(int=rng.getrandbits(128))),
            }
        )
    _ensure_shapes(records)
    names = _names(records)
    return W1(_book(records, names, HEADERS), records, names)


def w1_next(seed: int = 1, rows: int = 200) -> W1:
    """W1′: 5 changed, 3 added, 2 missing, a new ``T`` value, a new column ``Y``, ``Ln`` renamed."""
    base = w1(seed, rows)
    records = [dict(row) for row in base.rows[2:]]
    for row in records[:5]:
        row["N"] = f"{row['N']} (new)"
    records[5]["T"] = "Bamboo"
    for index in range(3):
        number = rows + index + 1
        records.append({**records[index], "K": f"IT-{number:05d}", "N": f"Added item {number}",
                        "X": str(uuid.UUID(int=seed * 1000 + number))})
    headers = dict(HEADERS)
    headers["Ln"] = "Colour name"
    headers["Y"] = "Pack size"
    for row in records:
        row["Y"] = 10
    names = _names(records)
    return W1(_book(records, names, headers), records, names, headers)


DESCRIPTION = "D"
D_HEADERS = {"F": "Field code", "Ty": "Field type", "Tg": "Lookup target"}


@dataclass
class W2:
    """A generated W2: its file and, by role, what its sheets hold. ``lists`` are the target sheets
    with rows (each list's ID and name, without the placeholder row); ``undefined`` the target sheet
    holding only "To be defined"; ``flags`` the flag target, which has no sheet; ``fields`` each
    described field's type and target, in the description's order."""

    content: bytes
    fields: list[tuple[str, str, str]]
    lists: dict[str, list[tuple[Any, str]]]
    undefined: str
    flags: str
    placeholder: tuple[str, str]
    description: str = DESCRIPTION
    headers: dict[str, str] = field(default_factory=lambda: dict(D_HEADERS))

    def lookups(self) -> dict[str, str]:
        """Each lookup field and the list sheet it names."""
        return {f: t for f, kind, t in self.fields if kind == "lookup"}


def w2(seed: int = 1, rows: int = 200) -> W2:
    """W2 for the W1 of the same seed and size."""
    base = w1(seed, rows)
    rng = random.Random(seed + 2)
    book = Workbook()
    book.remove(book.active)
    fields = [
        (HEADERS["T"], "lookup", "Materials"),
        (HEADERS["Lc"], "lookup", "Colours"),
        (HEADERS["F1"], "flag", "Features"),
        (HEADERS["F2"], "flag", "Features"),
        ("Finish", "lookup", "Finishes"),
    ]
    description = book.create_sheet(DESCRIPTION)
    description.append(list(D_HEADERS.values()))
    for entry in fields:
        description.append(list(entry))
    lists: dict[str, list[tuple[Any, str]]] = {}
    materials = book.create_sheet("Materials")
    materials.append(["ID", "Name"])
    present = sorted(base.distinct("T") - set(PLACEHOLDERS))
    lists["Materials"] = list(enumerate(present[: max(1, len(present) - 2)], start=1))
    for index, name in lists["Materials"]:
        materials.append([index, name])
    placeholder = ("?", "Unknown material")
    materials.append(list(placeholder))
    colours = book.create_sheet("Colours")
    colours.append(["ID", "Name"])
    lists["Colours"] = []
    for code, names in sorted(COLOURS.items()):
        drifted = names[0] if rng.random() < 0.5 else f"{names[0]} colour"
        colours.append([code, drifted])
        lists["Colours"].append((code, drifted))
    finishes = book.create_sheet("Finishes")
    finishes.append(["ID", "Name"])
    finishes.append(["To be defined", None])
    return W2(_save(book), fields, lists, "Finishes", "Features", placeholder)


@dataclass
class W3:
    content: bytes
    blocks: list[dict[str, Any]]
    sheet: str = "Lists"
    header_row: int = 3


def w3(seed: int = 1, blocks: int = 24) -> W3:
    rng = random.Random(seed + 3)
    book = Workbook()
    sheet = book.active
    sheet.title = "Lists"
    column = 1
    described = []
    for index in range(blocks):
        shape = ("plain", "languages", "flags", "multiple")[index % 4]
        title = f"List {index + 1:02d}"
        headers = {
            "plain": [title],
            "languages": [title, f"{title} (de)", f"{title} (fr)"],
            "flags": [title, "Allowed"],
            "multiple": [title],
        }[shape]
        if index % 6 == 0:
            sheet.cell(row=1, column=column, value=f"Section {index // 6 + 1}")
        if index % 3 == 0:
            sheet.cell(row=2, column=column, value=f"Group {index // 3 + 1}")
        for offset, header in enumerate(headers):
            sheet.cell(row=3, column=column + offset, value=header)
        first_value = 4
        if shape == "multiple":
            sheet.cell(row=4, column=column, value="(multiple answers)")
            first_value = 5
        count = rng.randint(3, 9)
        for value_index in range(count):
            row = first_value + value_index
            sheet.cell(row=row, column=column, value=f"{title} value {value_index + 1}")
            if shape == "languages":
                sheet.cell(row=row, column=column + 1, value=f"{title} Wert {value_index + 1}")
                sheet.cell(row=row, column=column + 2, value=f"{title} valeur {value_index + 1}")
            elif shape == "flags":
                sheet.cell(row=row, column=column + 1, value=rng.choice("YN"))
        width = len(headers)
        described.append(
            {
                "first": column,
                "last": column + width - 1,
                "lastRow": first_value + count - 1,
                "shape": shape,
                "title": title,
            }
        )
        column += width + 1
    return W3(_save(book), described)


@dataclass
class W4:
    """The shapes of real workbooks (0.10 A6b, D99–D103): sheet ``Kinds`` keyed by ``Kind Code``,
    named by a repeating ``Customer Name``; a ``Category`` with its ``Category ID`` and ``Sort
    Order`` empty on some rows, translated value for value by ``Categoría`` and ``Kategorie``; a
    ``Slot_Name`` with its ``Slot hours``; yes/no columns ``North`` and ``South`` apart; a repeated
    ``Definition`` in sentences; a second ``Customer Name`` column. Sheet ``Statuses``: a GUID
    ``Id`` and a ``Name`` of several words."""

    content: bytes
    rows: int
    blank_categories: int


W4_CATEGORIES = {
    "Night tram": ("Tranvía nocturno", "Noční tramvaj", 1),
    "Admin timetable": ("Tren regional", "Osobní vlak", 2),
    "Train train": ("Tren de cercanías", "Rychlík se sestrou", 3),
    "Boat": ("Imagen", "Zobrazování", 4),
    "Massage": ("Autobús", "Autobus", 5),
}
W4_DEFINITIONS = (
    "Use this kind when the caller asks for a first conversation before any treatment is planned",
    "Use this kind when results arrived and a clinician needs to talk them through with the passenger",
    "Use this kind for internal planning only; it is never offered to the people booking online",
)


def w4(seed: int = 1, rows: int = 120) -> W4:
    rng = random.Random(seed + 4)
    book = Workbook()
    kinds = book.active
    kinds.title = "Kinds"
    kinds.append(
        ["Kind Code", "Customer Name", "Category ID", "Sort Order", "Category", "Slot_Name", "Slot hours", "North",
         "Duration", "South", "Definition", "Categoría", "Kategorie", "Customer Name"]
    )
    ids = {name: str(uuid.UUID(int=index + 1)) for index, name in enumerate(W4_CATEGORIES)}
    slots = {"Morning": "8-12", "Evening": "17-21", "Weekend": "9-13"}
    blank = 0
    for index in range(rows):
        category = rng.choice(list(W4_CATEGORIES)) if index % 25 else None
        blank += category is None
        spanish, czech, order = W4_CATEGORIES[category] if category else (None, None, None)
        slot = rng.choice(list(slots))
        kinds.append(
            [f"K-{index + 1:04d}", f"Kind {index // 2 + 1}", ids.get(category), order, category, slot, slots[slot],
             rng.choice("YN"), f"{rng.choice([15, 30, 45])} min", rng.choice("YN"), rng.choice(W4_DEFINITIONS),
             spanish, czech, f"Druh {index // 2 + 1}"]
        )
    statuses = book.create_sheet("Statuses")
    statuses.append(["Id", "Name"])
    for index, name in enumerate(("Booked and confirmed", "Waiting for payment", "No show", "Cancelled by station", "Arrived")):
        statuses.append([str(uuid.UUID(int=1000 + index)), name])
    return W4(_save(book), rows, blank)


def _ensure_shapes(records: list[dict[str, Any]]) -> None:
    """The structures every W1 holds whatever its size: both names of each two-named colour code,
    both placeholders, and a ``;``-separated ``Fo``."""
    for offset, (code, names) in enumerate((c, n) for c, n in sorted(COLOURS.items()) if len(n) > 1):
        for position, name in enumerate(names):
            row = records[(offset * 2 + position) % len(records)]
            row["Lc"], row["Ln"] = code, name
    for position, placeholder in enumerate(PLACEHOLDERS):
        records[-1 - position]["T"] = placeholder
    records[len(records) // 2]["Fo"] = "Compact; Eco"


def _names(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = []
    for index, row in enumerate(records):
        for language in LANGUAGES:
            name = row["N"] if language == "en" else f"{row['N']} [{language}]"
            if index == 0 and language == "en":
                name = f"{row['N']} (renamed)"
            names.append({"K": row["K"], "Lang": language, "N": name})
    return names


def _book(records: list[dict[str, Any]], names: list[dict[str, Any]], headers: dict[str, str]) -> bytes:
    book = Workbook()
    main = book.active
    main.title = S1
    main.append(list(headers.values()))
    for row in records:
        main.append([row.get(structure) for structure in headers])
    second = book.create_sheet(S2)
    second.append(list(S2_HEADERS.values()))
    for row in names:
        second.append([row[structure] for structure in S2_HEADERS])
    return _save(book)


def _save(book: Workbook) -> bytes:
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
