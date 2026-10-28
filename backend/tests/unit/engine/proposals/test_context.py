"""The context builder (``engine/proposals/context.py``, AP-D3): no value leaves above its level,
and a value is not even read below the level that allows it."""

import pytest

from app.engine.proposals.context import FEATURE_LEVELS, Policy, sheet

ROWS = [[f"v{r}-{c}" for c in range(3)] for r in range(50)]


def _reader(calls: list[int]):
    def read(limit: int) -> list[list[str | None]]:
        calls.append(limit)
        return ROWS  # more than asked, to prove the builder cuts it

    return read


def test_structure_sends_names_and_headers_and_never_reads_a_value():
    calls: list[int] = []
    shown = sheet(Policy("structure", 20), "Items", ["A", "B", "C"], _reader(calls), 40)
    assert shown == {"name": "Items", "headers": ["A", "B", "C"]} and calls == []
    assert "v0-0" not in str(shown)


@pytest.mark.parametrize("samples", [1, 3, 20, 50, 80])
@pytest.mark.parametrize("wanted", [1, 10, 40])
def test_at_samples_at_most_the_sample_rows_are_read_and_sent(samples, wanted):
    calls: list[int] = []
    shown = sheet(Policy("samples", samples), "Items", ["A", "B", "C"], _reader(calls), wanted)
    allowed = min(samples, wanted)
    assert calls == [allowed] and shown["rows"] == ROWS[:allowed]


@pytest.mark.parametrize("wanted", [1, 10, 40, 50])
def test_at_values_the_rows_a_feature_asks_for_are_sent_whatever_the_sample_size(wanted):
    calls: list[int] = []
    shown = sheet(Policy("values", 3), "Items", ["A", "B", "C"], _reader(calls), wanted)
    assert calls == [wanted] and shown["rows"] == ROWS[:wanted]


def test_levels_are_ordered_and_a_feature_is_offered_only_at_its_level():
    assert Policy("values", 1).allows("samples") and Policy("samples", 1).allows("structure")
    assert not Policy("structure", 1).allows("samples")
    assert not Policy("samples", 1).allows("values")
    for purpose, needed in FEATURE_LEVELS.items():
        assert Policy(needed, 1).offers(purpose)
