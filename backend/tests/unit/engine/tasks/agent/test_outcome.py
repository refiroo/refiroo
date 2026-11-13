"""What the assistant session reached and how it is worded (``engine/tasks/agent/outcome.py``)."""

import json
from types import SimpleNamespace

from app.engine.tasks.agent.outcome import _left_out, _shape


def _type(key, *attributes):
    return {
        "key": key,
        "name": key.title(),
        "attributes": [{"attributeTypeKey": a} for a in attributes],
    }


def test_the_shape_names_what_a_proposal_adds_changes_or_loads_and_leaves_the_rest_out():
    base = {"objectTypes": [_type("kept", "a"), _type("grown", "a"), _type("loaded", "a")]}
    model = {
        "objectTypes": [
            _type("kept", "a"),
            _type("grown", "a", "b"),
            _type("loaded", "a"),
            _type("fresh", "a", "b", "c"),
        ]
    }
    shape = _shape(model, base, {"loaded": 1, "fresh": 1200})
    assert [(item["name"], item["text"]) for item in shape] == [
        ("Grown", "Changed type (adds b), 2 attributes"),
        ("Loaded", "1 attribute, 1 record"),
        ("Fresh", "New type, 3 attributes, 1,200 records"),
    ]


def test_a_type_that_differs_only_in_form_is_not_changed_and_a_real_difference_is_named():
    base = {
        "attributeTypes": [{"key": "a", "name": "Alpha"}, {"key": "b", "name": "Beta"}],
        "objectTypes": [
            {
                "key": "same",
                "name": "Same",
                "attributes": [
                    {"attributeTypeKey": "a", "required": True, "order": 10, "ui": {}},
                    {"attributeTypeKey": "b", "order": 20},
                ],
            },
            {
                "key": "loosened",
                "name": "Loosened",
                "attributes": [{"attributeTypeKey": "a", "required": True}],
            },
        ],
    }
    model = {
        "attributeTypes": base["attributeTypes"],
        "objectTypes": [
            {
                "key": "same",
                "name": "Same",
                # Listed the other way round, defaults spelled out, another order number.
                "attributes": [
                    {
                        "attributeTypeKey": "b",
                        "required": False,
                        "readOnly": False,
                        "order": 5,
                        "ui": None,
                    },
                    {
                        "attributeTypeKey": "a",
                        "required": True,
                        "readOnly": False,
                        "order": 6,
                        "ui": {},
                    },
                ],
            },
            {
                "key": "loosened",
                "name": "Loosened",
                "attributes": [{"attributeTypeKey": "a", "required": False}],
            },
        ],
    }
    assert [(i["name"], i["text"]) for i in _shape(model, base, {})] == [
        ("Loosened", "Changed type (changes how Alpha is filled in), 1 attribute")
    ]


def test_types_holding_records_that_a_model_drops_are_flagged_and_empty_ones_are_not():
    base = {"objectTypes": [_type("held"), _type("empty")]}
    assert _left_out({"objectTypes": [_type("held")]}, base, {"held": 3}) == []
    assert _left_out({"objectTypes": []}, base, {}) == []
    found = _left_out({"objectTypes": []}, base, {"held": 3})
    assert found[0]["open"] and "Held (3)" in found[0]["text"]


def _landing(monkeypatch, tmp_path, proposal, *, workbook):
    """``_proposal_landed`` for a task whose session wrote ``proposal`` (``workbook``: the task has a file)."""
    from unittest.mock import MagicMock

    from app.engine.tasks.agent import outcome as agent_outcome
    from app.engine.tasks.agent import words as agent_words

    task = SimpleNamespace(
        id=1,
        state="reading",
        notes=[],
        design={"stage": "model"},
        draft_id=None,
        check="old",
        title=None,
    )
    monkeypatch.setattr(agent_outcome, "load_task", lambda *args, **kwargs: task)
    monkeypatch.setattr(agent_outcome, "touch", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr("app.engine.tasks.store.touch", lambda *args, **kwargs: None)
    (tmp_path / agent_words.PROPOSAL).write_text(json.dumps(proposal))
    session = MagicMock()
    session.scalar.return_value = 7 if workbook else None
    progress = SimpleNamespace(result={"result": "Done."})
    agent_outcome._proposal_landed(session, None, "t", tmp_path, progress, None, None)
    return task


def test_a_words_proposal_without_a_draft_is_a_proposal_with_no_model_change(monkeypatch, tmp_path):
    task = _landing(
        monkeypatch,
        tmp_path,
        {"draftId": None, "summary": "Set the abbreviation.", "questions": [{"text": "Sure?"}]},
        workbook=False,
    )
    assert task.state == "checked" and task.draft_id is None and task.check is None
    assert task.design["modelUnchanged"] is True and task.design["stage"] == "model"
    assert task.design["summary"] == "Set the abbreviation."
    assert task.design["questions"][0]["text"] == "Sure?"
    assert task.design["moves"] == [] and task.design["outline"] == []


def test_a_workbook_proposal_without_a_draft_still_fails(monkeypatch, tmp_path):
    task = _landing(monkeypatch, tmp_path, {"draftId": None, "summary": "A plan."}, workbook=True)
    assert task.state == "failed" and "modelUnchanged" not in task.design


def test_a_words_proposal_without_a_summary_or_with_moves_or_a_missing_draft_still_fails(
    monkeypatch, tmp_path
):
    for proposal in (
        {"draftId": None, "summary": " "},
        {"draftId": None, "summary": "Merge.", "moves": [{"from": "a", "to": "b"}]},
    ):
        assert _landing(monkeypatch, tmp_path, proposal, workbook=False).state == "failed"


def test_accepting_a_proposal_without_a_draft_asks_for_the_change_set_on_the_live_release():
    from app.engine.tasks.agent import words as agent_words

    assert "install no release" in agent_words.ACCEPTED_UNCHANGED
    assert "source currentLive" in agent_words.ACCEPTED_UNCHANGED and agent_words.LAST_LINE in (
        agent_words.ACCEPTED_UNCHANGED
    )
    assert "Install" in agent_words.ACCEPTED


def test_the_note_of_a_type_removed_in_a_partial_move_says_its_records_move_not_that_they_are_deleted():
    """A removed type whose records the change set restructures into other types is not a deletion
    (0.13 DOC11 14); a real deletion keeps its counts."""
    from app.engine.tasks.agent.outcome import _removal_account, _requested_removals

    base = {"objectTypes": [{"key": "route", "name": "Route"}]}
    final = {
        "objectTypes": [
            {"key": "local", "name": "Local route"},
            {"key": "other", "name": "Other route"},
        ]
    }
    landing = SimpleNamespace(
        losses={"route": {"records": 4}},
        value_losses={},
        relationship_losses={("served-by", "stop", "route"): 72},
    )
    words = "remove the emptied Route type"
    asked = {"kind": "objectType", "key": "route", "words": words}
    moved = _requested_removals({"removals": [{**asked, "movedTo": ["local", "other"]}]}, words)
    _, stated = _removal_account(landing, moved, base, final)
    assert stated[0]["text"] == (
        "As you asked, Route is removed: its 4 records move to Local route and Other route."
    )
    deleted = _requested_removals({"removals": [asked]}, words)
    _, stated = _removal_account(landing, deleted, base, final)
    assert stated[0]["text"] == (
        "As you asked, Route is deleted, deleting 4 records, 72 relationships."
    )


_SENT = {
    "sources": [
        {
            "sheet": "Terms",
            "applicationKey": "words",
            "objectTypeKey": "term",
            "columns": [{"column": "Code", "field": "name"}],
            "key": {"field": "name"},
        }
    ],
    "valueMaps": {},
}


class _Session:
    """A session that answers the dry run's job: what the check read the workbook by."""

    def __init__(self, parameters):
        self.job = SimpleNamespace(parameters=parameters)

    def scalar(self, _statement):
        return self.job


def test_a_check_through_a_profile_the_draft_does_not_hold_fails_the_task_with_its_reason():
    """The session may send its dry run a profile inline and store none on the draft (0.17 PL3b): the
    design would have no profile to load by, so the task says so rather than offering it."""
    from app.engine.tasks.agent.outcome import _unstored_profile, profile_not_stored

    check = {"dryRunJobId": "job"}
    sent = {"profile": {"definition": _SENT}}
    for stored in (None, {}, {"key": "terms", "name": "Terms", "sources": [], "valueMaps": {}}):
        draft = SimpleNamespace(profile_json=stored)
        reason = _unstored_profile(_Session(sent), draft, check)
        assert reason is not None and "stored none on the model draft" in reason

    # Stored as the draft holds it (an id, a key and a name of its own), it is the same profile.
    held = {
        "key": "terms",
        "name": "Terms",
        "sources": [{"id": "terms", **_SENT["sources"][0]}],
        "valueMaps": {},
    }
    assert _unstored_profile(_Session(sent), SimpleNamespace(profile_json=held), check) is None
    changed = {**held, "sources": [{**held["sources"][0], "headerRow": 2}]}
    other = _unstored_profile(_Session(sent), SimpleNamespace(profile_json=changed), check)
    assert other is not None and "not the one stored" in other

    # A dry run of items reads no workbook, and a check without a job has nothing to compare.
    items = {"mode": "items"}
    assert _unstored_profile(_Session(items), SimpleNamespace(profile_json=None), check) is None
    assert profile_not_stored(None, None) is None
