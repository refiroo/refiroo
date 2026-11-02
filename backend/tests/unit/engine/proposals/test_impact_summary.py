"""``engine/proposals/impact_summary.py`` and ``summaries.py``: the facts, what the provider is
sent and what makes a cached answer reusable (0.16 AO1, AO-D12 to AO-D15)."""

from datetime import UTC, datetime, timedelta

from app.engine.model.diff import SemanticChange
from app.engine.proposals import impact_summary as summary
from app.engine.proposals import summaries
from app.engine.proposals.impact_summary import Fact, SummaryAnswer


def _changes(count: int) -> list[Fact]:
    return [
        Fact(summary.fact_id("change", "added", f"/attributeTypes/a{n}"), "change", f"Added {n}")
        for n in range(count)
    ]


def test_a_fact_keeps_its_id_and_a_kind_changes_it():
    first = summary.fact_id("change", "added", "/attributeTypes/a")
    assert first == summary.fact_id("change", "added", "/attributeTypes/a")
    assert first != summary.fact_id("data", "added", "/attributeTypes/a")
    assert first != summary.fact_id("change", "removed", "/attributeTypes/a")


def test_the_provider_is_sent_forty_of_a_kind_the_true_total_and_a_group_to_cite():
    facts = _changes(55) + [Fact("re-1", "records", "R has 7 records", "/objectTypes/r", 7)]
    context = summary.context_of(facts, "en")
    assert len([f for f in context["facts"] if f["kind"] == "change"]) == summary.FACT_LIMIT
    assert context["totals"] == {"change": 55, "records": 1}
    assert context["more"] == [
        {
            "id": "more-change",
            "kind": "change",
            "count": 15,
            "text": "and 15 more change facts",
        }
    ]
    assert context["language"] == "en"


def test_the_largest_counts_come_first_and_a_change_is_cut_at_two_hundred_characters():
    facts = [
        Fact("da-a", "data", "small", None, 1),
        Fact("da-b", "data", "large", None, 90),
    ]
    assert [f["id"] for f in summary.context_of(facts, "en")["facts"]] == ["da-b", "da-a"]
    long = Fact("ch-x", "change", "t", None, None, "x" * 500, "y")
    sent = summary.context_of([long], "en")["facts"][0]
    assert len(sent["before"]) == summary.TEXT_LIMIT and sent["after"] == "y"


def test_a_statement_needs_a_fact_that_exists_and_a_group_counts_as_one():
    facts = _changes(2)
    answer = SummaryAnswer.model_validate(
        {
            "statements": [
                {"text": "ok", "factIds": [facts[0].id]},
                # Few facts: no group of "more" was sent, so it cannot be cited (R-F27).
                {"text": "group", "factIds": ["more-change"]},
                {"text": "unknown", "factIds": ["ch-ffffffff"]},
                {"text": "none", "factIds": []},
                {"text": " ", "factIds": [facts[1].id]},
            ]
        }
    )
    kept, removed = summary.checked(answer, facts)
    assert [item.text for item in kept] == ["ok"] and removed == 4


def test_a_change_is_worded_from_the_models_labels():
    document = {
        "objectTypes": [{"key": "t", "name": "Delivery method"}],
        "attributeTypes": [{"key": "a", "name": "Carrier"}],
    }
    names = summary._Names(document)
    change = SemanticChange("added", "/objectTypes/t/attributes/a", after={"required": False})
    assert summary.describe(change, names) == (
        "Attribute 'Carrier' is added to object type 'Delivery method' (optional)"
    )
    assert summary.touched_types([change], document) == ["t"]


def test_the_cache_hash_covers_everything_asked_and_a_row_lasts_an_hour():
    base = summaries.input_hash("p", "v1", [{"a": 1}, "structure", "fake", "fake-1"])
    assert base == summaries.input_hash("p", "v1", [{"a": 1}, "structure", "fake", "fake-1"])
    for other in (
        summaries.input_hash("p", "v2", [{"a": 1}, "structure", "fake", "fake-1"]),
        summaries.input_hash("p", "v1", [{"a": 2}, "structure", "fake", "fake-1"]),
        summaries.input_hash("p", "v1", [{"a": 1}, "values", "fake", "fake-1"]),
        summaries.input_hash("p", "v1", [{"a": 1}, "structure", "fake", "fake-2"]),
    ):
        assert other != base
    assert summaries.LIFETIME == timedelta(hours=1)
    assert datetime(2026, 11, 1, tzinfo=UTC) + summaries.LIFETIME > datetime(
        2026, 11, 1, tzinfo=UTC
    )
