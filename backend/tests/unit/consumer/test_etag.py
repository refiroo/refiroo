"""``app/consumer/etag.py``: entity tags and ``If-None-Match`` (Base 0.9 C6a, C-D65)."""

from itertools import product

import pytest

from app.consumer.etag import entity_tag, none_match

TAG = entity_tag(("live", "default", "41", "release-a"), 1)
OTHER = entity_tag(("live", "default", "42", "release-a"), 1)


def test_a_tag_is_quoted_opaque_and_names_the_contract_version():
    assert TAG.startswith('"') and TAG.endswith(':1"')
    assert "default" not in TAG and "release-a" not in TAG
    assert TAG == entity_tag(("live", "default", "41", "release-a"), 1)


def test_any_changed_part_changes_the_tag():
    parts = ("live", "default", "41", "release-a")
    for index in range(len(parts)):
        changed = (*parts[:index], parts[index] + "x", *parts[index + 1 :])
        assert entity_tag(changed, 1) != TAG
    assert entity_tag(parts, 2) != TAG
    # Parts are separated, not concatenated: moving a character between them is another tag.
    assert entity_tag(("live", "default4", "1", "release-a"), 1) != TAG


@pytest.mark.parametrize(
    ("weak", "position", "spacing"),
    list(product((False, True), ("only", "first", "last"), ("", " ", "  "))),
)
def test_a_listed_tag_matches_weakly_wherever_it_stands(weak, position, spacing):
    listed = ("W/" if weak else "") + TAG
    others = [OTHER, 'W/"elsewhere:1"']
    tags = {"only": [listed], "first": [listed, *others], "last": [*others, listed]}[position]
    assert none_match(f",{spacing}".join(tags), TAG)


@pytest.mark.parametrize(
    "header",
    [None, "", OTHER, f"{OTHER}, W/{OTHER}", TAG.strip('"'), TAG[:-2] + '2"', f"W/ {TAG}", "**"],
)
def test_no_listed_tag_or_a_malformed_one_does_not_match(header):
    assert not none_match(header, TAG)


@pytest.mark.parametrize("header", ["*", " * "])
def test_a_star_matches_any_tag(header):
    assert none_match(header, TAG)
