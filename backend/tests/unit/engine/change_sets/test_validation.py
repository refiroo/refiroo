"""``engine/change_sets/validation.py``: the cap a refusal body puts on its list of findings."""

from app.engine.change_sets.validation import LISTED_PER_CODE, cap_per_code


def test_each_code_lists_its_first_findings_and_counts_the_rest():
    found = [{"code": "VERSION_MISMATCH", "id": str(n)} for n in range(LISTED_PER_CODE + 5)]
    found += [{"code": "DUPLICATE_EDGE", "id": "edge"}]
    found += [{"code": "ID_COLLISION", "id": str(n)} for n in range(LISTED_PER_CODE)]
    listed, left_out = cap_per_code(found)
    assert [item["id"] for item in listed if item["code"] == "VERSION_MISMATCH"] == [
        str(n) for n in range(LISTED_PER_CODE)
    ]
    assert len(listed) == 2 * LISTED_PER_CODE + 1
    assert left_out == {"VERSION_MISMATCH": 5}


def test_a_list_within_the_cap_is_whole_and_leaves_nothing_out():
    found = [{"code": "A"}, {"code": "B"}, {"code": "A"}]
    assert cap_per_code(found) == (found, {})
