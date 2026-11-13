"""The shapes workbooks showed (0.10 A6b, D99–D103, 2026-10-14), on generated tables
of the same shape: a list of an ID and a name, repeated columns with empty cells, translations by
their values, yes/no columns apart, repeated descriptions, and names taken from headers."""

import random
import uuid

from app.engine.sources.inference.patterns import find

from .memory import workbook
from .test_build import _build


def _operations(proposals, kind):
    return [o for p in proposals for o in p.operations if o["kind"] == kind]


def test_a_list_of_an_id_and_a_name_is_a_type_keyed_by_its_id_and_named_after_its_sheet():
    names = [
        f"{word} services" for word in ("Alpine", "Regional", "Express", "Local", "Night", "Scenic")
    ]
    book = workbook(
        (
            "RBStopStatus",
            {"Id": [str(uuid.UUID(int=i + 1)) for i in range(6)], "Name": names},
        )
    )
    proposals = _build(book)
    (key,) = [p for p in proposals if p.pattern == "keyColumn"]
    assert key.columns == ["Id", "Name"]
    (added,) = _operations(proposals, "addObjectType")
    assert (added["name"], added["pluralName"]) == (
        "RB Stop Status",
        "RB Stop Statuses",
    )


def test_one_parent_per_type_optional_where_cells_are_empty_and_a_further_repeated_column_a_list():
    rng = random.Random(7)
    rows = 120
    category = [rng.choice(["Bus", "Tram", "Train", "Boat"]) for _ in range(rows)]
    category[5] = None
    slot = [rng.choice(["Morning", "Evening", "Weekend"]) for _ in range(rows)]
    data = {
        "Type Code": [f"T-{i:04d}" for i in range(rows)],
        "Customer Name": [f"Service kind number {i}" for i in range(rows)],
        "Category": category,
        "Category order": [
            None if c is None else {"Bus": 1, "Tram": 2, "Train": 3, "Boat": 4}[c] for c in category
        ],
        "TimeBand_Name": slot,
        "Slot internal": [
            {"Morning": "early", "Evening": "late", "Weekend": "off"}[s] for s in slot
        ],
    }
    proposals = _build(workbook(("FINAL COPY (09-03)", data)))
    (row_type,) = [o for o in _operations(proposals, "addObjectType") if o["name"] == "Type"]
    contained = [
        o for o in _operations(proposals, "setContainment") if o["objectType"] == row_type["key"]
    ]
    assert len(contained) == 1, "one parent"
    assert contained[0]["parent"]["optional"] is True, "a row without a category has no parent"
    slot_list = next(
        o for o in _operations(proposals, "addObjectType") if o["name"] == "Time Band Name"
    )
    (relation,) = [
        o for o in _operations(proposals, "allowRelation") if o["to"] == slot_list["key"]
    ]
    assert (relation["from"], relation["cardinality"]) == (row_type["key"], "many-to-one")


def test_columns_translating_another_by_their_values_are_its_translations_whatever_their_headers():
    rng = random.Random(8)
    rows = 150
    english = ["Bus line", "Tram line", "Train line", "Boat line", "Cable car"]
    spanish = dict(
        zip(
            english,
            [
                "Línea de autobús",
                "Línea de tranvía",
                "Línea de tren",
                "Línea de barco",
                "Teleférico",
            ],
            strict=True,
        )
    )
    czech = dict(
        zip(
            english,
            [
                "Autobusová linka",
                "Tramvajová linka",
                "Vlaková linka",
                "Lodní linka",
                "Lanovka",
            ],
            strict=True,
        )
    )
    category = [rng.choice(english) for _ in range(rows)]
    data = {
        "Code": [f"C-{i:04d}" for i in range(rows)],
        "Name": [f"Kind number {i}" for i in range(rows)],
        "Category": category,
        "Categoría": [spanish[c] for c in category],
        "Kategorie": [czech[c] for c in category],
        "Note": [f"remark {rng.random():.6f}" for _ in range(rows)],
    }
    findings = find(workbook(("Kinds", data)))
    (translations,) = [f for f in findings if f.pattern == "translationsByColumn"]
    headers = list(data)
    assert [headers[n - 1] for n in translations.columns] == ["Categoría", "Kategorie"]
    assert headers[translations.detail["base"] - 1] == "Category"
    assert sorted(translations.detail["languages"].values()) == ["Language 1", "Language 2"]
    assert not any(f.pattern == "repeatedParent" for f in findings), "translations are no parent"


def test_yes_no_columns_apart_form_one_set_and_repeated_descriptions_are_no_parent():
    rng = random.Random(9)
    rows = 100
    descriptions = [
        f"Use this kind when the passenger {verb} and the operator needs a follow up within a week"
        for verb in ("calls", "writes", "visits")
    ]
    data = {
        "Code": [f"K-{i:04d}" for i in range(rows)],
        "Name": [f"Kind number {i}" for i in range(rows)],
        "CRGH": [rng.choice("YN") for _ in range(rows)],
        "Headway": [f"{rng.choice([15, 30, 45])} min" for _ in range(rows)],
        "SYNC": [rng.choice("YN") for _ in range(rows)],
        "Definition": [rng.choice(descriptions) for _ in range(rows)],
        "Format": [rng.choice(["Video", "Counter"]) for _ in range(rows)],
    }
    findings = find(workbook(("Kinds", data)))
    (flags,) = [f for f in findings if f.pattern == "flagColumns"]
    assert len(flags.columns) == 2
    assert not [f for f in findings if f.pattern == "repeatedParent" and f.columns[0] == 6]
    definition = next(f for f in findings if f.columns == [6])
    assert definition.pattern == "attribute"
