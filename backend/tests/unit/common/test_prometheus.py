"""The Prometheus text format /metrics writes (Product 0.11 O1, D193)."""

import math

from app.common.prometheus import Family, render


def test_label_values_are_escaped():
    family = Family("rdm_x_total", "counter", "Back\\slash and\nnewline")
    family.add({"route": 'a"b\\c\nd'}, 3)
    text = render([family])
    assert "# HELP rdm_x_total Back\\\\slash and\\nnewline\n" in text
    assert 'rdm_x_total{route="a\\"b\\\\c\\nd"} 3\n' in text
    assert text.endswith("\n")


def test_histogram_buckets_are_cumulative_and_end_at_inf():
    family = Family("rdm_t_seconds", "histogram", "Time")
    family.histogram({"route": "/r"}, (0.1, 1), [2, 0, 3], 4.5)
    lines = render([family]).splitlines()[2:]
    assert lines == [
        'rdm_t_seconds_bucket{route="/r",le="0.1"} 2',
        'rdm_t_seconds_bucket{route="/r",le="1"} 2',
        'rdm_t_seconds_bucket{route="/r",le="+Inf"} 5',
        'rdm_t_seconds_sum{route="/r"} 4.5',
        'rdm_t_seconds_count{route="/r"} 5',
    ]


def test_numbers_and_an_unlabelled_sample():
    family = Family("rdm_g", "gauge", "G")
    for value in (2.0, 0.25, math.inf, math.nan):
        family.add({}, value)
    assert render([family]).splitlines()[2:] == ["rdm_g 2", "rdm_g 0.25", "rdm_g +Inf", "rdm_g NaN"]
