"""``app/cli/generate_key.py``: ``--help`` prints help, not a key."""

import pytest

from app.cli import generate_key


def test_help_prints_no_key_and_an_unknown_argument_exits_2(capsys):
    with pytest.raises(SystemExit) as stop:
        generate_key.main(["--help"])
    assert stop.value.code == 0
    assert "SECRETS_ENCRYPTION_KEY" in capsys.readouterr().out
    with pytest.raises(SystemExit) as stop:
        generate_key.main(["--unknown"])
    assert stop.value.code == 2
