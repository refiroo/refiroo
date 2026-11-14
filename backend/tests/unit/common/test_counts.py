"""A count with its noun."""

from app.common.counts import count_noun


def test_count_noun_words_and_thousands():
    assert count_noun(1, "row") == "1 row"
    assert count_noun(0, "row") == "0 rows"
    assert count_noun(1286, "row", thousands=True) == "1,286 rows"
    assert count_noun(1286, "row") == "1286 rows"
    assert count_noun(2, "person", "people") == "2 people"
    assert count_noun(1, "key is", "keys are") == "1 key is"
