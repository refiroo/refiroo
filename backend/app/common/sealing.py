"""Secrets the engine must read back, sealed with a deployment key (Base 0.9 C11, C-D96).

A webhook signing key cannot be hashed like a password: signing needs the key itself. It is stored
sealed with AES-256-GCM under a key kept outside the database, so a database backup or replica alone
does not reveal it. A sealed value starts with its format byte, then the 12-byte nonce, then the
ciphertext with its tag, so a later format (another deployment key, 0.12's rotation) can be told
apart without a schema change.
"""

import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_FORMAT = b"\x01"
_NONCE_BYTES = 12


class SealError(Exception):
    """A sealed value that the deployment key does not open: another key, or damaged data."""


def seal(key: bytes, plaintext: bytes, context: bytes) -> bytes:
    """``plaintext`` sealed under ``key``, bound to ``context`` (it opens only with the same one)."""
    nonce = secrets.token_bytes(_NONCE_BYTES)
    return _FORMAT + nonce + AESGCM(key).encrypt(nonce, plaintext, context)


def unseal(key: bytes, sealed: bytes, context: bytes) -> bytes:
    if sealed[:1] != _FORMAT:
        raise SealError("The sealed value has an unknown format")
    nonce, ciphertext = sealed[1 : 1 + _NONCE_BYTES], sealed[1 + _NONCE_BYTES :]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, context)
    except InvalidTag:
        raise SealError("The deployment key does not open the sealed value") from None
