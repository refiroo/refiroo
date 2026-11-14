"""The sign-in sentences are one set for the engine's pages and the application's JSON sign-in."""

from app.management import sign_in_messages as messages


def test_waits_read_in_seconds_then_in_whole_minutes():
    assert messages.wait_text(1) == "1 second"
    assert messages.wait_text(59) == "59 seconds"
    assert messages.wait_text(60) == "1 minute"
    assert messages.wait_text(89) == "2 minutes"


def test_the_sentences_keep_their_wording():
    assert messages.too_many_attempts(75).endswith(
        "try again in 2 minutes. An administrator can reset the password."
    )
    assert messages.too_many_codes(30).startswith(
        "Too many wrong codes for this account or from this address."
    )
    assert (
        messages.WRONG_CREDENTIALS
        == "The e-mail address or password is not right. Check both and try again."
    )
