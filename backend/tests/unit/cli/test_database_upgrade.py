"""``app/cli/database_upgrade.py``: ``--help`` prints help and does not migrate."""

import pytest

from app.cli import database_upgrade


def test_help_does_not_migrate_and_an_unknown_argument_exits_2(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(database_upgrade, "create_database", lambda: called.append(1))
    with pytest.raises(SystemExit) as stop:
        database_upgrade.main(["--help"])
    assert stop.value.code == 0
    assert "database" in capsys.readouterr().out.lower()
    with pytest.raises(SystemExit) as stop:
        database_upgrade.main(["--unknown"])
    assert stop.value.code == 2
    assert not called
