"""The send level's policy (``engine/proposals/context.py``, AP-D3): the window estimate, and the
levels with the features each offers."""

from app.engine.proposals.context import FEATURE_LEVELS, Policy, within_window


def test_the_window_estimate_is_half_the_window_and_absent_without_one():
    assert within_window(10**9, None)
    assert within_window(300, 200) and not within_window(303, 200)
    assert not within_window(300, 200, answer_tokens=1)


def test_levels_are_ordered_and_a_feature_is_offered_only_at_its_level():
    assert Policy("values", 1).allows("samples") and Policy("samples", 1).allows("structure")
    assert not Policy("structure", 1).allows("samples")
    assert not Policy("samples", 1).allows("values")
    for purpose, needed in FEATURE_LEVELS.items():
        assert Policy(needed, 1).offers(purpose)
