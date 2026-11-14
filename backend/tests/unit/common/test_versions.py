"""One reading of dotted version text, and what each caller makes of unreadable text."""

from app.common.versions import dotted_version
from app.engine.model.raising import schema_side
from app.engine.sources.inference.compare import _version


def test_dotted_version_reads_numbers_and_refuses_text():
    assert dotted_version("0.8") == (0, 8)
    assert dotted_version("1.10.2") == (1, 10, 2)
    assert dotted_version("next") is None
    assert dotted_version("") is None
    assert dotted_version(None) is None


def test_each_caller_keeps_its_own_meaning_of_unreadable():
    assert schema_side("not.a.version") == "unreadable"
    assert schema_side("99.0") == "after"
    assert _version("0.8") == (0, 8)
    assert _version(None) == (0,)
    assert _version("x") == (0,)
