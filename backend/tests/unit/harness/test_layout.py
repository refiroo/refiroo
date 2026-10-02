"""The journey IDs a test may name and where a unit test sits (tests/layout.py)."""

from pathlib import Path

import layout


def test_the_catalogue_defines_journeys_and_variants_but_not_retired_ones():
    ids = layout.journey_ids()
    assert {"J01", "J02", "J02.2", "J13.5", "J26", "J12.9"} <= ids
    assert "J09" not in ids  # retired 2026-10-02
    assert not {key for key in ids if key.startswith("J09.")}


def test_unknown_journeys_are_named():
    assert layout.unknown_journeys(("J02.2", "J09", "J99.1", "J02")) == ["J09", "J99.1"]


def test_a_journey_selects_its_variants_and_a_variant_only_itself():
    assert layout.walks(("J02.2",), "J02")
    assert layout.walks(("J02",), "J02")
    assert not layout.walks(("J02",), "J02.2")
    assert not layout.walks(("J20.1",), "J02")


def test_a_unit_test_path_mirrors_the_module_it_tests():
    unit = layout.UNIT
    assert layout.unit_target(unit / "engine/records/test_rules.py") == layout.APP / "engine/records/rules.py"
    split = unit / "engine/records/test_rules__parents.py"
    assert layout.unit_target(split) == layout.APP / "engine/records/rules.py"
    assert layout.unit_target(unit / "harness/test_seeds.py") == layout.TESTS / "seeds.py"
    assert layout.unit_target(unit / "engine/records/test_no_such_module.py") is None
    assert layout.unit_target(unit / "engine/test_records.py") is None  # a package, not a module
    assert layout.unit_target(unit / "engine/records/rules_test.py") is None


def test_kind_follows_the_folder():
    assert layout.kind(layout.JOURNEYS / "test_x.py") == "journey"
    assert layout.kind(layout.UNIT / "harness/test_layout.py") == "unit"
    assert layout.kind(layout.TESTS / "test_api.py") == "suite"
    assert layout.kind(Path(__file__)) == "unit"
