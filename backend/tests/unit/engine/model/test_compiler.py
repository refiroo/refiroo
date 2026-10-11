"""``engine/model/compiler.py``: a shape error's path is a JSON pointer into the document.

Pydantic's ``loc`` names a tagged union's member (a consumer parameter's ``kind``) between the node
and its field; the document has no such node. J25 meets one tag; here the tag, a missing field that
equals a value of its object, and list indexes are checked.
"""

from app.engine.model.compiler import SCHEMA_VERSIONS, compile_model, document_location


def test_a_union_tag_is_left_out():
    source = {"parameters": {"zone": {"kind": "ancestor", "targetable": True}}}
    location = ("parameters", "zone", "ancestor", "targetable")
    assert document_location(location, source) == ["parameters", "zone", "targetable"]


def test_a_missing_last_field_is_kept_even_when_a_value_spells_it():
    source = {"rules": [{"field": "exact"}]}
    assert document_location(("rules", 0, "exact"), source) == ["rules", 0, "exact"]


def test_a_key_is_kept_and_a_path_below_a_missing_node_is_kept_whole():
    source = {"items": [{"name": "a"}], "name": "items"}
    assert document_location(("items", 0, "name"), source) == ["items", 0, "name"]
    assert document_location(("other", "inner", "leaf"), source) == ["other", "inner", "leaf"]


def test_schema_versions_are_listed_oldest_first_by_number():
    """0.10 N1: ``0.10`` follows ``0.9``; a text sort would place it before ``0.5``."""
    numbers = [tuple(int(part) for part in version.split(".")) for version in SCHEMA_VERSIONS]
    assert numbers == sorted(numbers) and SCHEMA_VERSIONS[-1] == "0.10"
    (diagnostic,) = compile_model({"schemaVersion": "9.9"}).diagnostics
    assert diagnostic.code == "UNSUPPORTED_SCHEMA_VERSION"
    assert diagnostic.message.endswith(str(list(SCHEMA_VERSIONS)))
