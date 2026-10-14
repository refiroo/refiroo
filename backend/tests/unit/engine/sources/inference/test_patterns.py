"""The table patterns (``engine/sources/inference/patterns.py``, 0.10 A6, D90): each rule finds its
pattern on a generated table, with its columns and evidence, and leaves a control column alone.

W1 itself is generated with several seeds and sizes and its columns shuffled: the patterns found do
not depend on the order of the columns or the number of rows. The patterns W1 does not hold (level
columns, translations by column, a reference to another sheet, a multi-valued cell on its own) have
small tables of their own.
"""

import random
import uuid

import pytest
import workbooks

from app.engine.sources.inference.patterns import find, fold, is_language

from .memory import workbook


def _w1(seed: int, rows: int, shuffle: bool):
    book = workbooks.w1(seed, rows)
    headers = list(book.headers)
    if shuffle:
        # The flag columns move as one block, the multi-valued column beside them too (D97).
        block = ["F1", "F2", "Fo"]
        rest = [h for h in headers if h not in block] + ["flags"]
        random.Random(seed).shuffle(rest)
        headers = [s for h in rest for s in (block if h == "flags" else [h])]
    main = {book.header(s): [row.get(s) for row in book.rows] for s in headers}
    names = {workbooks.S2_HEADERS[s]: [row[s] for row in book.names] for s in ("K", "Lang", "N")}
    return book, workbook((workbooks.S1, main), (workbooks.S2, names))


@pytest.mark.parametrize(("seed", "rows", "shuffle"), [(1, 200, False), (2, 60, True), (3, 120, True), (4, 400, False)])
def test_w1_gives_its_patterns_whatever_the_seed_size_and_column_order(seed, rows, shuffle):
    book, found = _w1(seed, rows, shuffle)
    findings = find(found)
    by_pattern = {}
    for finding in findings:
        assert finding.pattern not in by_pattern, finding.pattern
        by_pattern[finding.pattern] = finding
    assert set(by_pattern) == {
        "keyColumn", "repeatedParent", "textLookup", "placeholders", "codeAndName", "nameDrift",
        "flagColumns", "externalId", "translationsByRow", "navigationGroup",
    }
    table = found.sheets[0]
    headers = {c.number: c.header for c in table.columns}

    def columns(pattern):
        return [headers[n] for n in by_pattern[pattern].columns]

    h = book.header
    assert columns("keyColumn") == [h("K"), h("N")]
    assert columns("repeatedParent")[0] == h("P")
    assert set(columns("repeatedParent")) == {h("P"), h("Po"), h("Pi")}
    assert by_pattern["repeatedParent"].detail["key"] == next(n for n, x in headers.items() if x == h("Pi"))
    assert columns("textLookup") == [h("T")]
    assert columns("codeAndName") == [h("Lc"), h("Ln")]
    assert set(columns("flagColumns")) >= {h("F1"), h("F2")}
    assert columns("externalId") == [h("X")]
    # The controls: the name is no lookup, the GUID no key, the order no parent.
    assert h("N") not in columns("textLookup") + columns("codeAndName")
    assert h("X") not in columns("keyColumn")
    assert columns("repeatedParent")[0] != h("Po")


def test_flag_columns_join_the_multi_valued_column_beside_them_only():
    _, found = _w1(1, 200, False)
    flags = next(f for f in find(found) if f.pattern == "flagColumns")
    assert flags.evidence["joined"] == workbooks.HEADERS["Fo"]
    # The same columns apart, with a text column between: the multi-valued column is its own list.
    book = workbooks.w1(1, 200)
    order = ["K", "N", "F1", "F2", "T", "Fo"]
    apart = workbook((workbooks.S1, {book.header(s): [r.get(s) for r in book.rows] for s in order}))
    patterns = {f.pattern: f for f in find(apart)}
    assert patterns["flagColumns"].evidence["joined"] is None
    assert patterns["multiValued"].evidence["delimiter"] == ";"


def test_a_single_yes_no_column_is_not_a_flag_set():
    rng = random.Random(5)
    table = {"Code": [f"A{i:03d}" for i in range(80)], "Name": [f"Thing {i}" for i in range(80)], "Active": [rng.choice("YN") for _ in range(80)]}
    found = find(workbook(("Things", table)))
    assert "flagColumns" not in [f.pattern for f in found]
    active = next(f for f in found if f.columns == [3])
    assert (active.pattern, active.evidence["valueType"], active.evidence["vocabulary"]) == ("attribute", "boolean", ["n", "y"])


def test_level_columns_and_a_parent_code_column_are_hierarchies():
    rng = random.Random(7)
    rows = 90
    regions = [f"Region {i}" for i in range(3)]
    levels = {
        "Code": [f"N{i:03d}" for i in range(rows)],
        "Name": [f"Node number {i}" for i in range(rows)],
        "Level 1": [rng.choice(regions) for _ in range(rows)],
        "Level 2": [None] * rows,
        "Notes": [f"Free note {rng.random():.6f}" for _ in range(rows)],
    }
    levels["Level 2"] = [f"{region} area {rng.randint(1, 4)}" for region in levels["Level 1"]]
    found = {f.pattern: f for f in find(workbook(("Nodes", levels)))}
    assert found["levelColumns"].evidence["levels"] == 2
    assert "Notes" not in [c.header for c in workbook(("Nodes", levels)).sheets[0].columns if c.number in found["levelColumns"].columns]

    codes = [f"N{i:03d}" for i in range(rows)]
    parent = {"Code": codes, "Name": [f"Node number {i}" for i in range(rows)], "Parent code": [None, *[rng.choice(codes[:i]) for i in range(1, rows)]]}
    self_found = [f for f in find(workbook(("Nodes", parent))) if f.pattern == "levelColumns"]
    assert self_found and self_found[0].evidence["parentOf"] == "Code"


def test_translations_by_column_translate_the_name_column():
    table = {
        "Code": [f"P{i:02d}" for i in range(30)],
        "Name": [f"Product number {i}" for i in range(30)],
        "Name (de)": [f"Produkt Nummer {i}" for i in range(30)],
        "Name FR": [f"Produit numéro {i}" for i in range(30)],
        "Weight (kg)": [float(i) / 3 for i in range(30)],
    }
    found = next(f for f in find(workbook(("Products", table))) if f.pattern == "translationsByColumn")
    assert found.evidence["languages"] == ["de", "FR"]
    assert "Weight (kg)" not in found.evidence.get("columns", [{}])[0].get("column", "")


def test_a_column_of_another_sheets_codes_refers_to_its_records():
    rng = random.Random(9)
    suppliers = {"Supplier code": [f"S{i:02d}" for i in range(20)], "Supplier name": [f"Supplier company {i}" for i in range(20)]}
    items = {
        "Item code": [f"I{i:03d}" for i in range(100)],
        "Item name": [f"Item number {i}" for i in range(100)],
        "Supplier": [rng.choice(suppliers["Supplier code"]) for _ in range(100)],
        "Batch": [f"B{rng.randint(1000, 9999)}" for _ in range(100)],
    }
    found = find(workbook(("Items", items), ("Suppliers", suppliers)))
    references = [f for f in found if f.pattern == "sheetReference"]
    assert len(references) == 1 and references[0].detail["target"] == "Suppliers"
    assert references[0].evidence["share"] >= 0.9


def test_a_text_column_with_many_values_is_no_lookup_and_a_guid_column_no_key():
    rng = random.Random(11)
    table = {
        "Id": [str(uuid.UUID(int=rng.getrandbits(128))) for _ in range(150)],
        "Code": [f"C{i:03d}" for i in range(150)],
        "Title": [f"Title {rng.randint(0, 120)}" for _ in range(150)],
        "Note": [f"Note {i}" for i in range(150)],
    }
    found = {f.pattern: f for f in find(workbook(("Rows", table)))}
    sheet = workbook(("Rows", table)).sheets[0]
    assert sheet.columns[found["keyColumn"].columns[0] - 1].header == "Code"
    assert found["externalId"].evidence["unique"] is True
    assert "textLookup" not in found


def test_names_fold_case_accents_punctuation_and_a_plural():
    assert fold("Items") == fold("item") == "item"
    assert fold("Catégorie-ID") == fold("categorie id")
    assert fold("Class") == "class"
    assert is_language("de") and is_language("German") and not is_language("Deutschmark")


def test_a_sheet_with_one_clear_table_is_read_by_it_and_lists_side_by_side_are_not():
    """facts.main_block (reported on a real workbook, 2026-10-14): a wide table with a narrow note
    beside it is read by the table; lists of two columns side by side, or blocks of like size, are
    left to A8."""
    from app.engine.sources.inference.facts import main_block

    def block(first, last, rows):
        return {"firstColumn": first, "lastColumn": last, "rows": rows}

    assert main_block([block("A", "AF", 212), block("AH", "AI", 211)]) == 0
    assert main_block([block("A", "B", 30), block("D", "L", 200)]) == 1
    assert main_block([block("B", "C", 11), block("E", "F", 18), block("H", "I", 16), block("K", "L", 8)]) is None
    assert main_block([block("F", "I", 38), block("K", "N", 38), block("P", "S", 35), block("U", "X", 29)]) is None
    assert main_block([block("A", "B", 500), block("D", "E", 10)]) is None, "too narrow to be a table"


# --- a model description (0.10 A7, D107) --------------------------------------------------------


def _described(types, targets, fields=None):
    fields = fields or [f"Field {i}" for i in range(len(types))]
    return workbook(
        ("Fields", {"Field": fields, "Kind": types, "Target": targets}),
        ("Colours", {"ID": ["C1", "C2", "C3"], "Name": ["Red", "Green", "Blue"]}),
        ("Sizes", {"ID": ["S1", "S2"], "Name": ["Small", "Large"]}),
    )


@pytest.mark.parametrize(
    ("word", "kind"),
    [("lookup", "lookup"), ("List", "lookup"), ("Multi-Select", "multi"), ("multi lookup", "multi"), ("Yes/No", "flag"),
     ("checkbox", "flag"), ("String", "text"), ("long_text", "longText"), ("Number", "integer"), ("decimal", "decimal"), ("DATE", "date")],
)
def test_each_type_word_reads_as_its_kind(word, kind):
    found = find(_described(["lookup", "lookup", word], ["Colours", "Sizes", None]))
    (description,) = [f for f in found if f.pattern == "modelDescription"]
    assert description.detail["fields"][2]["kind"] == kind


def test_a_description_claims_its_sheet_and_the_sheets_it_names():
    found = find(_described(["lookup", "multi", "text"], ["Colours", "Sizes", None]))
    patterns = [(f.pattern, f.sheet) for f in found]
    assert ("modelDescription", "Fields") in patterns
    assert {s for p, s in patterns if p == "describedList"} == {"Colours", "Sizes"}
    assert not [p for p in patterns if p[0] in ("keyColumn", "textLookup", "attribute")]


def test_a_type_column_needs_four_fifths_type_words_and_a_target_column_half_sheet_names():
    four_of_five = find(_described(["lookup", "lookup", "text", "text", "whatever"], ["Colours", "Sizes", None, None, None]))
    assert [f for f in four_of_five if f.pattern == "modelDescription"]
    three_of_five = find(_described(["lookup", "lookup", "text", "huh", "whatever"], ["Colours", "Sizes", None, None, None]))
    assert not [f for f in three_of_five if f.pattern == "modelDescription"]
    under_half = find(_described(["lookup", "lookup", "lookup"], ["Colours", "Elsewhere", "Nowhere"]))
    assert not [f for f in under_half if f.pattern == "modelDescription"]


def test_a_column_naming_sheets_without_type_words_is_no_description():
    found = find(_described(["alpha", "beta", "gamma"], ["Colours", "Sizes", "Colours"]))
    assert not [f for f in found if f.pattern.startswith(("modelDescription", "described"))]
    assert {f.sheet for f in found if f.pattern == "keyColumn"} >= {"Colours", "Sizes"}


def test_a_list_sheet_of_placeholders_is_to_be_defined_and_a_placeholder_key_is_skipped():
    book = workbook(
        ("Fields", {"Field": ["Colour", "Finish"], "Kind": ["lookup", "lookup"], "Target": ["Colours", "Finishes"]}),
        ("Colours", {"ID": ["C1", "C2", "?"], "Name": ["Red", "Green", "Unknown"]}),
        ("Finishes", {"ID": ["To be defined"], "Name": [None]}),
    )
    lists = {f.evidence["target"]: f for f in find(book) if f.pattern == "describedList"}
    assert lists["Finishes"].evidence["toBeDefined"] is True
    assert lists["Colours"].detail["placeholders"] == ["?"]
