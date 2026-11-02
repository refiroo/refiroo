"""A statement may cite only the facts the provider was sent (``summaries.checked``, AO-D2)."""

from app.engine.proposals import summaries
from app.engine.proposals.summaries import SummaryAnswer


def _answer(*cited):
    return SummaryAnswer.model_validate(
        {"statements": [{"text": f"About {ids}.", "factIds": list(ids)} for ids in cited]}
    )


def test_a_fact_not_sent_cannot_be_cited_though_it_exists():
    context = {"facts": [{"id": "re-1"}, {"id": "re-2"}], "more": [{"id": "more-records"}]}
    kept, removed = summaries.checked(
        _answer(["re-1"], ["more-records"], ["re-9"], ["re-1", "re-9"], []), context
    )
    assert [item.fact_ids for item in kept] == [("re-1",), ("more-records",)]
    assert removed == 3
