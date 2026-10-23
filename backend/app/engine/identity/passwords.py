"""Passwords and client secrets: the rules a password meets and how both are stored (D252, D253).

A local password is 15 to 128 characters with no composition rules, refused when it equals the
username or is one of the most common (NIST SP 800-63B rev. 4 for a password used alone). Passwords
and client secrets are stored as Argon2id PHC strings, never sealed: the engine never reads them
back, only compares.
"""

import secrets

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from ...errors import api_error

MIN_LENGTH = 15
MAX_LENGTH = 128

# Long passwords people choose most often, from the public breach lists; compared ignoring case.
COMMON = frozenset(
    {
        "123456789012345",
        "1234567890123456",
        "12345678901234567890",
        "111111111111111",
        "000000000000000",
        "qwertyuiopasdfg",
        "qwertyuiopasdfgh",
        "qwertyuiopasdfghjkl",
        "qwertyuiopasdfghjklzxcvbnm",
        "1qaz2wsx3edc4rfv",
        "1q2w3e4r5t6y7u8i",
        "passwordpassword",
        "password1234567",
        "password12345678",
        "passwordpassword1",
        "iloveyouiloveyou",
        "welcomewelcome1",
        "administrator123",
        "letmeinletmein1",
        "abcdefghijklmnop",
        "abcdefghijklmnopqrstuvwxyz",
        "aaaaaaaaaaaaaaa",
        "correcthorsebatterystaple",
        "changemechangeme",
        "trustno1trustno1",
    }
)

# OWASP's Argon2id parameters: 19 MiB, two passes, one lane.
_MEMORY_KIB = 19 * 1024
_ITERATIONS = 2
_LANES = 1


def check_password(password: str, username: str | None) -> None:
    """Refuse a password the rules do not allow, with ``422 PASSWORD_REJECTED`` and the reason."""
    if len(password) < MIN_LENGTH:
        reason, message = "tooShort", f"A password needs at least {MIN_LENGTH} characters"
    elif len(password) > MAX_LENGTH:
        reason, message = "tooLong", f"A password has at most {MAX_LENGTH} characters"
    elif username is not None and password.casefold() == username.casefold():
        reason, message = "username", "A password cannot be the username"
    elif password.casefold() in COMMON:
        reason, message = "common", "This password is one of the most common; choose another"
    else:
        return
    raise api_error(422, "PASSWORD_REJECTED", message, {"reason": reason})


def hash_secret(value: str) -> str:
    kdf = Argon2id(
        salt=secrets.token_bytes(16),
        length=32,
        iterations=_ITERATIONS,
        lanes=_LANES,
        memory_cost=_MEMORY_KIB,
    )
    return kdf.derive_phc_encoded(value.encode())


def verify_secret(value: str, encoded: str) -> bool:
    try:
        Argon2id.verify_phc_encoded(value.encode(), encoded)
    except InvalidKey, ValueError:
        return False
    return True
