"""Slowing failed sign-ins at its edges (D271) and the PKCE ``S256`` challenge (RFC 7636)."""

import base64
import hashlib

import pytest

from app.engine.identity.sign_in import (
    FREE_FAILURES,
    LONGEST_WAIT_SECONDS,
    challenge_of,
    valid_challenge,
    wait_after,
)


@pytest.mark.parametrize("kind", ["account", "address"])
def test_the_free_failures_cost_nothing_then_the_wait_doubles(kind):
    free = FREE_FAILURES[kind]
    assert [wait_after(free - 1, kind), wait_after(free, kind)] == [0, 0]
    assert [wait_after(free + n, kind) for n in range(1, 5)] == [1, 2, 4, 8]


def test_the_wait_never_passes_fifteen_minutes():
    assert wait_after(FREE_FAILURES["account"] + 10, "account") == 512
    assert wait_after(FREE_FAILURES["account"] + 11, "account") == LONGEST_WAIT_SECONDS
    assert wait_after(10_000, "account") == LONGEST_WAIT_SECONDS


def test_an_office_behind_one_address_gets_more_free_failures_than_an_account():
    assert FREE_FAILURES["address"] > FREE_FAILURES["account"]


def test_the_challenge_is_the_unpadded_base64url_sha256_of_the_verifier():
    verifier = "a" * 43
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    assert challenge_of(verifier) == expected.decode().rstrip("=")
    assert valid_challenge(challenge_of(verifier))


@pytest.mark.parametrize("challenge", [None, "", "a" * 42, "a" * 44, "a" * 42 + "="])
def test_a_challenge_not_s256_shaped_is_refused(challenge):
    assert not valid_challenge(challenge)
