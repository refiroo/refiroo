"""``engine/model/authoring/keys.py``: A-D6's key from a label."""

import pytest

from app.engine.model.authoring.keys import key_from_label


@pytest.mark.parametrize(
    ("label", "taken", "key"),
    [
        ("Shelf código", set(), "shelf-codigo"),
        ("  Ünits & Měřítka ", set(), "units-meritka"),
        ("Unit", {"unit"}, "unit-2"),
        ("Unit", {"unit", "unit-2"}, "unit-3"),
        ("€€€", set(), "element"),
    ],
)
def test_a_key_is_lower_case_hyphenated_ascii_numbered_on_a_clash(label, taken, key):
    assert key_from_label(label, taken) == key
