"""``engine/sources/profile_check.py``: the profile as the check reads the next file (0.10 A5c,
D83): renamed columns under their new header, members naming a missing column left out, a source
with nothing left to load not read."""

from app.engine.sources.profile_check import _follow

SOURCE = {
    "sheet": "Items",
    "applicationKey": "store",
    "objectTypeKey": "item",
    "key": {"attributeTypeKey": "code"},
    "missing": "delete",
    "columns": [
        {"column": "Code", "attributeTypeKey": "code"},
        {"column": "Name", "field": "name"},
        {
            "columns": ["Cold", "Dry"],
            "relationFlags": {
                "relationTypeKey": "kept",
                "objectTypeKey": "zone",
                "matchBy": {"field": "name"},
                "targets": {"Cold": "Cold", "Dry": "Dry"},
            },
        },
        {"column": "Notes", "ignore": True},
    ],
}


def test_a_renamed_column_is_read_under_its_new_header_everywhere():
    followed = _follow(SOURCE, {"Cold": "Chilled", "Name": "Title"}, set())
    assert followed["columns"][1] == {"column": "Title", "field": "name"}
    flags = followed["columns"][2]
    assert flags["columns"] == ["Chilled", "Dry"]
    assert flags["relationFlags"]["targets"] == {"Chilled": "Cold", "Dry": "Dry"}


def test_a_missing_column_is_left_out_and_a_missing_key_column_drops_the_key_and_its_deletes():
    followed = _follow(SOURCE, {}, {"Dry", "Code"})
    assert [b.get("column") or b.get("columns") for b in followed["columns"]] == [
        "Name",
        ["Cold"],
        "Notes",
    ]
    assert "key" not in followed and "missing" not in followed


def test_a_source_left_with_ignored_columns_only_is_not_read():
    assert _follow(SOURCE, {}, {"Code", "Name", "Cold", "Dry"}) is None


def test_a_check_compares_with_the_previous_file_of_its_own_workspace(seeded):
    """The profile's earlier file is the latest profiled one read in the same workspace: a file read
    for workspace B never has workspace A's file as its previous one."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.sources.profile_check import previous_file
    from app.models.database import ImportProfile, ModelRelease, SourceFile, SourceFileSheet

    def stored(session, number, workspace):
        item = SourceFile(
            profile_key="check-profile",
            name=f"file-{number}.csv",
            format="csv",
            bytes=1,
            sha256="0" * 64,
            workspace_key=workspace,
        )
        session.add(item)
        session.flush()
        session.add(SourceFileSheet(source_file_id=item.id, sheet_index=0, name="s", profile={}))
        return item

    with SessionLocal() as session:
        session.add(
            ImportProfile(
                key="check-profile",
                name="Check",
                definition={},
                checked_release_id=session.scalar(select(ModelRelease.id).limit(1)),
            )
        )
        session.flush()
        first_a = stored(session, 1, "workspace-a")
        first_b = stored(session, 2, "workspace-b")
        second_a = stored(session, 3, "workspace-a")
        second_b = stored(session, 4, "workspace-b")
        session.flush()
        assert previous_file(session, "check-profile", second_b).id == first_b.id
        assert previous_file(session, "check-profile", second_a).id == first_a.id
        third_b = stored(session, 5, "workspace-b")
        session.flush()
        assert previous_file(session, "check-profile", third_b).id == second_b.id
        only_c = stored(session, 6, "workspace-c")
        session.flush()
        assert previous_file(session, "check-profile", only_c) is None
        session.rollback()
