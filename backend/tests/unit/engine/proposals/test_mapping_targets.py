"""Targets for unmapped values (``engine/proposals/mapping_targets.py``, 0.16 AP2): the references a
call uses, and which of an answer may be used."""

from app.engine.proposals.mapping_targets import (
    TargetAnswer,
    TargetsAnswer,
    batch_of,
    chosen,
    fits,
    sized,
    tokens,
)

LIST = [{"id": f"id-t{n}", "name": f"Target {n}", "fields": {"code": f"C{n}"}} for n in range(1, 4)]


def _inputs(count: int, candidates: bool = False) -> list[dict]:
    return [
        {
            "sourceId": f"id-s{n}",
            "mappingVersion": 0,
            "name": f"Source {n}",
            "fields": {},
            **({"candidates": LIST[n - 1 : n + 1]} if candidates else {}),
        }
        for n in range(1, count + 1)
    ]


def _answer(*items: tuple[str, str | None, float]) -> TargetsAnswer:
    return TargetsAnswer(
        answers=[
            TargetAnswer(source=s, target=t, reason=" because ", confidence=c) for s, t, c in items
        ]
    )


def test_a_whole_list_is_sent_once_and_sources_carry_no_candidates_of_their_own():
    batch = batch_of(_inputs(2), LIST)
    assert [c["ref"] for c in batch.context["candidates"]] == ["t1", "t2", "t3"]
    assert all("candidates" not in s for s in batch.context["sources"])
    assert batch.allowed == {"s1": None, "s2": None}
    assert batch.sources == {"s1": "id-s1", "s2": "id-s2"}


def test_each_sources_own_candidates_are_shared_where_they_overlap():
    batch = batch_of(_inputs(2, candidates=True), None)
    shown = {c["ref"]: c["name"] for c in batch.context["candidates"]}
    # Source 1 holds targets 1 and 2, source 2 holds 2 and 3: three records, named once.
    assert shown == {"t1": "Target 1", "t2": "Target 2", "t3": "Target 3"}
    assert [s["candidates"] for s in batch.context["sources"]] == [["t1", "t2"], ["t2", "t3"]]
    assert batch.allowed == {"s1": {"t1", "t2"}, "s2": {"t2", "t3"}}


def test_chosen_keeps_a_known_candidate_at_or_above_the_floor_with_its_reason():
    batch = batch_of(_inputs(2), LIST)
    found = chosen(_answer(("s1", "t3", 0.5), ("s2", "t1", 0.8123)), batch, 0.5)
    assert [(c.source_id, c.target_id, c.confidence, c.reason) for c in found.chosen] == [
        ("id-s1", "id-t3", 0.5, "because"),
        ("id-s2", "id-t1", 0.81, "because"),
    ]
    assert found.unmatched == [] and found.unanswered == []


def test_null_invented_below_floor_and_foreign_answers_leave_the_source_unmatched():
    batch = batch_of(_inputs(4, candidates=True), None)
    # s1 may take t1 or t2; s2 t2 or t3; s3 t3 only (and a fourth with no candidate named).
    found = chosen(
        _answer(
            ("s1", None, 0.9),  # no match
            ("s2", "t99", 0.9),  # invented
            ("s3", "t1", 0.9),  # a real candidate, but not one of this source's own
            ("s4", "t3", 0.2),  # below the floor
        ),
        batch,
        0.5,
    )
    assert found.chosen == []
    assert found.unmatched == ["id-s1", "id-s2", "id-s3", "id-s4"]
    assert found.unanswered == []


def test_a_source_the_answer_leaves_out_is_unanswered_and_a_duplicate_answer_is_ignored():
    batch = batch_of(_inputs(3), LIST)
    found = chosen(
        _answer(("s1", "t1", 0.9), ("s1", "t2", 0.9), ("s9", "t1", 0.9), ("s2", "t2", 0.9)),
        batch,
        0.5,
    )
    # The first answer for s1 stands; s9 is no source of the call; s3 was not mentioned.
    assert [(c.source_id, c.target_id) for c in found.chosen] == [
        ("id-s1", "id-t1"),
        ("id-s2", "id-t2"),
    ]
    assert found.unanswered == ["id-s3"]


def test_a_field_repeating_the_name_or_holding_a_uuid_is_not_sent():
    batch = batch_of(
        [
            {
                "sourceId": "id-s1",
                "mappingVersion": 0,
                "name": "Blood Test",
                "fields": {
                    "label": " blood test ",
                    "external": "a3b01d7b-7377-48db-bbb4-96118878a0fa",
                    "code": "06-RE-029",
                    "empty": None,
                },
            }
        ],
        LIST,
    )
    assert batch.context["sources"][0]["fields"] == {"code": "06-RE-029"}


def test_calls_are_sized_to_half_the_context_window_and_never_below_one_source():
    inputs = [
        {
            "sourceId": f"id-s{n}",
            "mappingVersion": 0,
            "name": f"Source {n} " + "x" * 200,
            "fields": {},
        }
        for n in range(1, 26)
    ]
    assert sized(inputs, LIST, None) == 25
    count = sized(inputs, LIST, 2048)
    assert 1 <= count < 25
    assert (
        tokens(batch_of(inputs[:count], LIST)) <= 1024 < tokens(batch_of(inputs[: count + 1], LIST))
    )
    assert sized(inputs, LIST, 256) == 1
    assert fits(batch_of(inputs[:1], LIST), None) and not fits(batch_of(inputs[:1], LIST), 256)
