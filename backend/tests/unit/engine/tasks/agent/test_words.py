"""The assistant's prompt wording (``engine/tasks/agent/words.py``)."""

from app.engine.tasks.agent.words import _starting_point


def test_what_the_workspace_holds_decides_whether_the_session_adds_or_may_start_anew():
    assert "add to it" in _starting_point({"a": 2, "b": 1})
    assert "3 records" in _starting_point({"a": 2, "b": 1})
    assert "new one" in _starting_point({})


def test_a_proposal_prompt_says_a_partial_move_is_prepared_on_acceptance_not_done_by_hand():
    """The session of a split of some records of a type is told what accepting prepares, so its
    summary never hands the person manual restructuring (0.13 DOC11 14)."""
    from app.engine.tasks.agent import words as agent_words

    prompt = agent_words.propose_prompt(
        "Split the routes", "ws", "http://engine", {}, workbook=False
    )
    assert "partial move" in prompt and "stage nothing now" in prompt
    assert "Never tell the person to prepare a release or to restructure records by hand" in prompt
