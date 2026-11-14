"""The sentences of the sign-in, written once.

The engine's own sign-in pages (``sign_in_pages.py``, served by ``routers/oauth.py``) and the
application's JSON sign-in (``routers/oauth_app.py``) say the same thing for the same refusal, and
the browser matches none of them by their words: the page shows the engine's message as it is. The
wording here is the one both surfaces had; a change is made here and reaches both.
"""


def wait_text(seconds: int) -> str:
    """A wait as a person reads it: seconds up to a minute, else whole minutes rounded up."""
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    minutes = (seconds + 59) // 60
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


WRONG_CREDENTIALS = "The e-mail address or password is not right. Check both and try again."
WRONG_CODE = "That code is not right, or was already used. Wait for the next one and try again."


def too_many_attempts(wait_seconds: int) -> str:
    """Too many password tries."""
    return (
        "Too many attempts for this account or from this address. You can try again in "
        f"{wait_text(wait_seconds)}. An administrator can reset the password."
    )


def too_many_codes(wait_seconds: int) -> str:
    """Too many wrong second-factor codes."""
    return (
        "Too many wrong codes for this account or from this address. You can try again in "
        f"{wait_text(wait_seconds)}. An administrator can reset the second factor."
    )


def too_many_requests(wait_seconds: int) -> str:
    """Too many asks for a password-reset e-mail."""
    return (
        "Too many requests for this account or from this address. You can try again in "
        f"{wait_text(wait_seconds)}."
    )
