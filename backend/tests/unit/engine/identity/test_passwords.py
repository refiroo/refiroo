"""The password rules at their edges (D252) and Argon2id storage."""

import pytest

from app.engine.identity.passwords import (
    DEFAULT_MIN_LENGTH,
    MAX_LENGTH,
    check_password,
    hash_secret,
    verify_secret,
)
from app.errors import ApiError


@pytest.mark.parametrize(
    ("password", "username", "reason"),
    [
        ("x" * (DEFAULT_MIN_LENGTH - 1), None, "tooShort"),
        ("x" * (MAX_LENGTH + 1), None, "tooLong"),
        ("Ada.Lovelace.1815", "ada.lovelace.1815", "username"),
        ("PasswordPassword", None, "common"),
        ("  ", None, "tooShort"),
    ],
)
def test_a_password_the_rules_refuse(password, username, reason):
    with pytest.raises(ApiError) as refused:
        check_password(password, username)
    assert (refused.value.status, refused.value.code) == (422, "PASSWORD_REJECTED")
    assert refused.value.details == {"reason": reason}


@pytest.mark.parametrize(
    "password",
    [
        "x" * DEFAULT_MIN_LENGTH,
        "é" * MAX_LENGTH,
        "no rules about digits or case",
        "1234 5678 9012 345",
    ],
)
def test_a_password_the_rules_allow(password):
    check_password(password, "someone")


def test_a_stored_secret_verifies_only_itself():
    stored = hash_secret("a long passphrase of mine")
    assert stored.startswith("$argon2id$") and "passphrase" not in stored
    assert verify_secret("a long passphrase of mine", stored)
    assert not verify_secret("a long passphrase of yours", stored)
    assert not verify_secret("anything", "not a hash")
    assert hash_secret("same") != hash_secret("same")


def test_a_deployment_sets_the_least_length():
    """`PASSWORD_MIN_LENGTH` (D276): 15 by default; a development machine may allow a short
    password, the common ones still refused."""
    assert DEFAULT_MIN_LENGTH == 15
    check_password("pasword", "someone", min_length=1)
    with pytest.raises(ApiError) as refused:
        check_password("password", "someone", min_length=1)
    assert refused.value.details == {"reason": "common"}
    with pytest.raises(ApiError) as longer:
        check_password("x" * 11, "someone", min_length=12)
    assert longer.value.message == "A password needs at least 12 characters"
