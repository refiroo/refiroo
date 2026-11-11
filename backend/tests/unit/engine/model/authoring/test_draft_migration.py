"""``engine/model/authoring/draft_migration.py``: where the records of a moved type go (0.13 MG)."""

from app.engine.model.authoring.draft_migration import application_target


def test_a_type_that_left_one_application_for_another_sends_its_records_there():
    # Listed in four applications, one of which it left for a fifth: a released type moved out of the
    # application its records stand in while others still list it.
    assert (
        application_target(
            {"a", "b", "c", "d"},
            {"e", "b", "c", "d"},
        )
        == "e"
    )
    assert application_target({"a"}, {"b"}) == "b"


def test_a_type_that_left_no_application_or_only_left_names_no_destination():
    assert application_target({"a", "b"}, {"a", "b"}) is None
    assert application_target({"a", "b"}, {"a"}) is None
    assert application_target({"a"}, {"a", "b"}) is None
    assert application_target(set(), {"a"}) is None


def test_a_type_gained_by_several_applications_goes_to_the_one_where_it_is_own():
    # "a" is first alphabetically but only borrows the type for a view (R13-F12).
    assert application_target({"x"}, {"a", "b"}, owned_in={"b"}) == "b"
    assert application_target({"x"}, {"a", "b"}, owned_in={"a", "b"}) is None
    assert application_target({"x"}, {"a", "b"}, owned_in=set()) is None


def test_a_type_is_own_where_a_table_or_a_tree_view_holds_it():
    from app.engine.model.authoring.draft_migration import owned_in_applications

    model = {
        "applications": [
            {
                "key": "a",
                "objectTypeKeys": ["t", "u"],
                "views": [
                    {"type": "relationTable", "config": {"fromObjectTypeKey": "t"}},
                    {"type": "tree", "config": {"objectTypeKeys": ["u"]}},
                ],
            },
            {
                "key": "b",
                "objectTypeKeys": ["t"],
                "views": [{"type": "table", "objectTypeKey": "t"}],
            },
        ]
    }
    assert owned_in_applications(model) == {"u": {"a"}, "t": {"b"}}


def test_several_replace_model_steps_leave_one_model_replaced_note(monkeypatch):
    # The note said the same sentence once per step, which the notice drew as duplicate keys (R13-F41).
    from types import SimpleNamespace

    from app.engine.model.authoring import draft_migration

    steps = [
        SimpleNamespace(
            step=number, sequence=number, kind="replaceModel", parameters={}, effects={}, inverse={}
        )
        for number in (1, 2)
    ]
    monkeypatch.setattr(draft_migration, "effective_entries", lambda session, draft: steps)
    monkeypatch.setattr(draft_migration, "base_release", lambda session, draft: None)
    draft = SimpleNamespace(model_json={}, version=3)

    migration = draft_migration.derive(None, draft)

    assert [note["code"] for note in migration["notes"]] == ["MODEL_REPLACED"]
