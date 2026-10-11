"""The consumer API's shared object (0.9 C2, ``engine/reads/consumer_objects.py``): a related
record's ``ancestor:`` field."""

from app.engine.reads.consumer_objects import _projected, _Record


def test_an_ancestor_field_shows_the_ancestor_nearest_the_root():
    """0.9 R-F16, D209: under two ancestors of one type (a type that nests), the one nearest the
    root, as ``path`` and the management API show it."""
    ancestors = {
        "inner": _Record("inner", "group", "Inner", "outer"),
        "outer": _Record("outer", "group", "Outer", "top"),
        "top": _Record("top", "domain", "Top", None),
    }
    leaf = _Record("leaf", "item", "Leaf", "inner")
    assert _projected(leaf, ("group", "name"), ancestors) == "Outer"
    assert _projected(leaf, ("domain", "name"), ancestors) == "Top"
    assert _projected(leaf, ("other", "name"), ancestors) is None
