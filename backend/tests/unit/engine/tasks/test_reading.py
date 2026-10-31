"""The evidence sentence of an update table (``engine/tasks/reading.evidence``): it is made from the
figures as they are, so it agrees with the choices the page shows; found on the user's first try,
where it still said "1 keys are new" after the key had been matched by meaning."""

from app.engine.tasks.reading import evidence


def _table(**figures):
    return {
        "keyColumn": "A",
        "key": {"attributeTypeKey": "code"},
        "keyKind": "code",
        "columns": [{"column": "A", "header": "Code"}],
        "matched": 4,
        "new": 0,
        "namesDiffer": 0,
        "missing": 0,
        "meaning": [],
        **figures,
    }


def test_only_the_figures_that_are_not_zero_are_said():
    assert evidence(_table()) == "Its 'Code' column holds the records' code: 4 of 4 match."


def test_one_and_several_are_said_in_their_own_words():
    one = evidence(_table(new=1, namesDiffer=1, missing=1, meaning=[{}]))
    assert one == (
        "Its 'Code' column holds the records' code: 4 of 6 match. 1 row is spelled differently "
        "but means a stored record. 1 key is new. 1 name differs from the stored ones. 1 stored "
        "record is not in the file."
    )
    several = evidence(_table(new=2, namesDiffer=3, missing=2, meaning=[{}, {}]))
    assert "2 rows are spelled differently but mean" in several
    assert "2 keys are new. 3 names differ" in several and "2 stored records are not" in several


def test_a_key_moved_to_the_names_says_names():
    table = _table(key={"field": "name"}, keyKind="code", columns=[{"column": "A", "header": "Name"}])
    assert evidence(table).startswith("Its 'Name' column holds the records' names:")
