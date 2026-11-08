"""``app/cli/create_admin.py``: without a terminal it names ``--password-stdin`` and creates nobody."""

import io
import sys

from app.cli import create_admin


def test_without_a_terminal_it_names_the_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    created = []
    monkeypatch.setattr(create_admin, "create_user", lambda *a, **k: created.append(1))
    monkeypatch.setattr(create_admin, "create_database", lambda: created.append(1))
    assert create_admin.main(["--username", "ada", "--name", "Ada"]) == 2
    assert "--password-stdin" in capsys.readouterr().err
    assert not created
