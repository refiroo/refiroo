"""Proposals from findings (``engine/sources/inference/build.py``, 0.10 A6): columns of one workbook
sharing a header and a value type share one global attribute type (D98), and extend mode matches
what the draft's model declares before adding anything (D91)."""

import random

from app.engine.sources.inference.build import Builder
from app.engine.sources.inference.patterns import find

from .memory import workbook


def _model(**more):
    model = {
        "schemaVersion": "0.10",
        "applications": [{"key": "app", "name": "App", "objectTypeKeys": [], "views": [], "details": []}],
        "objectTypes": [],
        "attributeTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
    }
    model.update(more)
    return model


def _build(book, model=None, mode="newApplication", identifiers=None):
    builder = Builder(
        model or _model(),
        None,
        book,
        mode=mode,
        file_name="lists.xlsx",
        application_key=None,
        application_name=None,
        reuse={},
        released=lambda _atom: False,
        identifiers=identifiers,
    )
    return builder.build(find(book))


def _added(proposals, name):
    return [o["key"] for p in proposals for o in p.operations if o["kind"] == "addAttributeType" and o["name"] == name]


def _attached(proposals, key):
    return {o["objectType"] for p in proposals for o in p.operations if o["kind"] == "attachAttribute" and o["attributeType"] == key}


def _sheet(prefix, rows, rng, **columns):
    data = {"Code": [f"{prefix}{i:03d}" for i in range(rows)], "Name": [f"{prefix} item number {i}" for i in range(rows)]}
    data.update({header: values(rng, rows) for header, values in columns.items()})
    return data


def test_columns_of_two_sheets_with_one_header_and_type_share_one_attribute_type():
    rng = random.Random(3)
    note = lambda r, n: [f"remark {r.random():.8f}" for _ in range(n)]
    book = workbook(("Materials", _sheet("M", 80, rng, Note=note)), ("Colours", _sheet("C", 60, rng, Note=note)))
    proposals = _build(book)
    (code,) = _added(proposals, "Code")
    (shared,) = _added(proposals, "Note")
    assert len(_attached(proposals, code)) == 2
    assert len(_attached(proposals, shared)) == 2


def test_a_different_value_type_a_shared_unique_value_or_one_unique_side_keeps_them_apart():
    rng = random.Random(4)
    whole = lambda r, n: [r.randint(1, 10_000) for _ in range(n)]
    worded = lambda r, n: [f"about {r.random():.6f} units" for _ in range(n)]
    unique = lambda r, n: [f"REF-{i:05d}" for i in range(n)]
    repeated = lambda r, n: [f"REF-{r.randint(0, 40):05d}" for _ in range(n)]
    first = _sheet("A", 70, rng, Size=whole, Ref=unique)
    second = _sheet("A", 70, rng, Size=worded, Ref=repeated)
    second["Code"] = [f"A{i:03d}" for i in range(35, 105)]
    proposals = _build(workbook(("Firsts", first), ("Seconds", second)))
    assert len(_added(proposals, "Size")) == 2, "an integer and a text column"
    assert len(_added(proposals, "Code")) == 2, "unique codes with values in common"
    assert len(_added(proposals, "Ref")) == 2, "a unique and a repeated column"


def test_extend_mode_maps_onto_the_type_and_attributes_the_model_declares():
    rng = random.Random(5)
    model = _model(
        objectTypes=[{"key": "material", "name": "Material", "pluralName": "Materials", "attributes": [{"attributeTypeKey": "material-code"}]}],
        attributeTypes=[
            {"key": "material-code", "name": "Code", "valueType": "text", "features": {"unique": True}},
            {"key": "remark", "name": "Notes", "valueType": "text"},
        ],
    )
    model["applications"][0]["objectTypeKeys"] = ["material"]
    note = lambda r, n: [f"remark {r.random():.8f}" for _ in range(n)]
    book = workbook(("Materials", _sheet("M", 80, rng, Note=note)))
    proposals = _build(book, model, mode="extend")
    operations = [o for p in proposals for o in p.operations]
    assert not [o for o in operations if o["kind"] == "addObjectType"]
    assert not [o for o in operations if o["kind"] == "addAttributeType"]
    source = next(o for o in operations if o["kind"] == "addSource")
    assert (source["objectType"], source["key"]) == ("material", {"attributeTypeKey": "material-code"})
    assert {"kind": "attachAttribute", "objectType": "material", "attributeType": "remark"} in operations


def test_extend_mode_relates_an_id_column_to_the_records_holding_its_values():
    """D96: the values are an existing type's unique values under one parent record."""
    rng = random.Random(6)
    model = _model(
        objectTypes=[
            {"key": "system", "name": "System", "attributes": []},
            {"key": "system-value", "name": "System value", "attributes": [{"attributeTypeKey": "external-id"}]},
        ],
        attributeTypes=[{"key": "external-id", "name": "External ID", "valueType": "text", "features": {"unique": True}}],
    )
    model["applications"][0]["objectTypeKeys"] = ["system", "system-value"]
    guid = lambda r, n: [f"{r.getrandbits(32):08x}-0000-4000-8000-{r.getrandbits(48):012x}" for _ in range(n)]
    book = workbook(("Items", _sheet("I", 50, rng, **{"ERP ID": guid})))
    hint = {("Items", "ERP ID"): {"type": "system-value", "attribute": "external-id", "parentType": "system", "parent": "ERP"}}
    proposals = _build(book, model, mode="extend", identifiers=hint)
    external = next(p for p in proposals if p.pattern == "externalId")
    mapped = next(o for o in external.operations if o["kind"] == "mapColumn")
    relation = mapped["binding"]["relation"]
    assert (relation["objectTypeKey"], relation["matchBy"]) == ("system-value", {"attributeTypeKey": "external-id"})
    assert "ERP" in external.summary
    assert not [o for o in external.operations if o["kind"] == "addAttributeType"]


# --- extend mode across files (0.10 A7, D111) ---------------------------------------------------


def _described_model():
    """A type with three fields (an attribute and two relations) and a list of colours."""
    return _model(
        applications=[{"key": "app", "name": "App", "objectTypeKeys": ["thing", "colour"], "views": [], "details": []}],
        objectTypes=[
            {"key": "thing", "name": "D", "pluralName": "Ds", "attributes": [{"attributeTypeKey": "weight"}]},
            {"key": "colour", "name": "Colour", "pluralName": "Colours", "attributes": []},
        ],
        attributeTypes=[{"key": "weight", "name": "Weight", "valueType": "decimal"}],
        relationTypes=[{"key": "shade", "name": "Shade"}, {"key": "tone", "name": "Tone"}],
        objectTypeRelations=[
            {"relationTypeKey": "shade", "fromObjectTypeKey": "thing", "toObjectTypeKey": "colour"},
            {"relationTypeKey": "tone", "fromObjectTypeKey": "thing", "toObjectTypeKey": "colour"},
        ],
    )


def _builder(model, mode="extend"):
    return Builder(model, None, workbook(), mode=mode, file_name="x.xlsx", application_key=None, application_name=None, reuse={}, released=lambda _a: False)


def test_a_sheet_maps_to_the_type_half_of_whose_fields_are_its_headers():
    builder = _builder(_described_model())
    assert builder.described_by({"weight", "shade", "price"}) == "thing"
    assert builder.described_by({"shade", "price"}) is None, "one of three fields is under half"
    assert builder.described_by({"weight"}) is None, "two fields at least"
    assert _builder(_described_model(), mode="newApplication").described_by({"weight", "shade", "tone"}) is None


def test_a_list_proposed_under_an_existing_types_name_or_plural_is_that_type():
    builder = _builder(_described_model())
    assert builder.existing_list("Colour") == "colour"
    assert builder.existing_list("colours") == "colour"
    assert builder.existing_list("Côlour!") == "colour"
    assert builder.existing_list("Size") is None
