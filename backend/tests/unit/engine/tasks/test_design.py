"""The model as the assistant designs against it (``engine/tasks/design.py``) and the records of the
structure it needs (``engine/tasks/draft_plan.py``): what the brief tells it, and the sheets and
profile sources that load the records before the person's sheets."""


from openpyxl import Workbook, load_workbook

from app.engine.tasks import design, design_job, draft_plan
from app.engine.tasks.design import RecordParent, StructureRecord

MODEL = {
    "applications": [{"key": "atlas", "name": "Atlas", "objectTypeKeys": ["domain", "ledger"]}],
    "objectTypes": [
        {"key": "domain", "name": "Domain", "attributes": []},
        {
            "key": "ledger",
            "name": "Ledger",
            "attributes": [
                {"attributeTypeKey": "number"},
                {"attributeTypeKey": "score", "required": True},
            ],
            "behavior": {"parentRelationTypeKeys": ["holds"]},
        },
    ],
    "attributeTypes": [
        {"key": "number", "valueType": "text", "features": {"unique": True}},
        {"key": "score", "valueType": "integer"},
    ],
    "relationTypes": [
        {"key": "holds", "reverseKey": "held-by", "name": "Holds", "features": {"parentOf": True}},
        {"key": "cites", "reverseKey": "cited-by", "name": "Cites"},
    ],
    "objectTypeRelations": [
        {
            "relationTypeKey": "holds",
            "fromObjectTypeKey": "domain",
            "toObjectTypeKey": "ledger",
            "cardinality": "one-to-many",
        },
        {
            "relationTypeKey": "cites",
            "fromObjectTypeKey": "ledger",
            "toObjectTypeKey": "domain",
            "cardinality": "many-to-many",
            "required": True,
        },
    ],
}


def _records():
    """Two ledgers under a domain, listed before it."""
    domain = RecordParent(objectTypeKey="domain", name="North")
    return [
        StructureRecord(
            ref="l2",
            objectTypeKey="ledger",
            name="Ledger two",
            attributes={"number": "L-2", "score": 5},
            parent=domain,
        ),
        StructureRecord(
            ref="l1",
            objectTypeKey="ledger",
            name="Ledger one",
            attributes={"number": "L-1"},
            parent=domain,
        ),
        StructureRecord(ref="d", objectTypeKey="domain", name="North", applicationKey="atlas"),
    ]


def test_the_brief_gives_each_type_its_parents_top_flag_attributes_and_stored_records():
    brief = design.model_brief(MODEL, {"ledger": 7})
    types = {t["key"]: t for t in brief["objectTypes"]}
    assert types["ledger"]["parents"] == ["domain"] and types["ledger"]["top"] is False
    assert types["domain"]["parents"] == [] and types["domain"]["top"] is True
    assert types["ledger"]["parentRelationTypes"] == ["holds"]
    assert types["ledger"]["attributes"] == [
        {"key": "number", "valueType": "text", "unique": True},
        {"key": "score", "valueType": "integer", "required": True},
    ]
    assert (types["ledger"]["records"], types["domain"]["records"]) == (7, 0)
    assert types["ledger"]["applications"] == ["atlas"]
    assert brief["attributeTypes"] == ["number", "score"]


def test_the_brief_marks_containment_and_the_joins_that_are_required():
    relations = {r["key"]: r for r in design.model_brief(MODEL, {})["relationTypes"]}
    assert relations["holds"]["containment"] is True and "containment" not in relations["cites"]
    assert relations["holds"]["joins"] == [
        {"from": "domain", "to": "ledger", "cardinality": "one-to-many"}
    ]
    assert relations["cites"]["joins"] == [
        {"from": "ledger", "to": "domain", "cardinality": "many-to-many", "required": True}
    ]


def test_structure_sources_load_the_parents_first_keyed_by_a_unique_attribute_else_the_name():
    sources = draft_plan.structure_sources(_records(), MODEL)
    assert [s["sheet"] for s in sources] == ["Structure Domain", "Structure Ledger"]
    domain, ledger = sources
    assert domain["objectTypeKey"] == "domain" and domain["key"] == {"field": "name"}
    assert domain["columns"] == [{"column": "Name", "field": "name"}]
    assert ledger["applicationKey"] == "atlas"
    assert ledger["key"] == {"attributeTypeKey": "number"}
    assert [c["column"] for c in ledger["columns"]] == ["Name", "number", "score", "Parent"]
    assert ledger["columns"][-1]["parent"] == {
        "objectTypeKey": "domain",
        "matchBy": {"field": "name"},
    }


def test_the_working_copy_adds_one_sheet_per_type_after_the_persons_and_avoids_their_names(
    tmp_path,
):
    original = tmp_path / "upload"
    book = Workbook()
    book.active.title = "Records"
    book.active.append(["Code"])
    book.create_sheet("Structure Domain").append(["The person's own sheet"])
    with original.open("wb") as handle:
        book.save(handle)
    content, sources = draft_plan.working_book(original, _records(), MODEL)
    assert [s["sheet"] for s in sources] == ["Structure Domain 2", "Structure Ledger"]
    saved = tmp_path / "work.xlsx"
    saved.write_bytes(content)
    sheets = load_workbook(saved)
    assert sheets.sheetnames == [
        "Records",
        "Structure Domain",
        "Structure Domain 2",
        "Structure Ledger",
    ]
    assert [[c.value for c in row] for row in sheets["Structure Domain"]] == [
        ["The person's own sheet"]
    ]
    assert [[c.value for c in row] for row in sheets["Structure Domain 2"]] == [
        ["Name"],
        ["North"],
    ]
    assert [[c.value for c in row] for row in sheets["Structure Ledger"]] == [
        ["Name", "number", "score", "Parent"],
        ["Ledger two", "L-2", 5, "North"],
        ["Ledger one", "L-1", None, "North"],
    ]


def test_the_release_the_assistant_installs_is_numbered_after_the_newest():
    from unittest.mock import MagicMock


    session = MagicMock()
    session.scalars.return_value = ["0.9.5", "0.10.0", "0.9.6"]
    # The draft came from 0.9.5, but 0.10.0 is the newest: the new release is 0.10.1.
    assert design_job._next_version(session, "model", "0.9.5") == "0.10.1"


