"""Secrets sealed with a deployment key (Base 0.9 C11, C-D96)."""

import pytest

from app.common.sealing import SealError, seal, unseal

KEY = b"k" * 32


def test_a_sealed_value_opens_with_the_same_key_and_context_only():
    sealed = seal(KEY, b"signing key", b"subscription-1")
    assert b"signing key" not in sealed
    assert unseal(KEY, sealed, b"subscription-1") == b"signing key"
    assert seal(KEY, b"signing key", b"subscription-1") != sealed  # a fresh nonce each time
    with pytest.raises(SealError):
        unseal(b"x" * 32, sealed, b"subscription-1")
    with pytest.raises(SealError):
        unseal(KEY, sealed, b"subscription-2")


def test_a_value_of_another_format_is_refused():
    sealed = seal(KEY, b"signing key", b"c")
    with pytest.raises(SealError, match="unknown format"):
        unseal(KEY, b"\x02" + sealed[1:], b"c")
