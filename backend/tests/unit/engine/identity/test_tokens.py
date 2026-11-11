"""Token verification: ES256 alone, every claim required, refusals named (D258)."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.engine.identity.settings import IdentitySettings
from app.engine.identity.tokens import TokenRefused, read_unverified, verify

SETTINGS = IdentitySettings(
    encryption_key=b"k" * 32,
    issuer="https://rdm.example",
    access_token_seconds=3600,
    signing_key_days=30,
)
KEY = ec.generate_private_key(ec.SECP256R1())


def _claims(**changes):
    now = int(time.time())
    claims = {
        "iss": SETTINGS.issuer,
        "sub": "client-1",
        "aud": "management",
        "iat": now,
        # Built at collection, so valid for the whole run, however long.
        "exp": now + 3600,
        "jti": "j",
        "principalKind": "client",
    }
    claims.update(changes)
    return {key: value for key, value in claims.items() if value is not None}


def _token(key=KEY, algorithm="ES256", **changes):
    return jwt.encode(_claims(**changes), key, algorithm=algorithm, headers={"kid": "k1"})


def _reason(token, audience="management"):
    with pytest.raises(TokenRefused) as refused:
        verify(token, KEY.public_key(), SETTINGS, audience)
    return refused.value.reason


def test_a_token_of_this_key_verifies():
    assert verify(_token(), KEY.public_key(), SETTINGS, "management")["sub"] == "client-1"


@pytest.mark.parametrize(
    ("token", "audience", "reason"),
    [
        (_token(exp=int(time.time()) - 5), "management", "expired"),
        (_token(), "consumer", "audience"),
        (_token(iss="https://elsewhere.example"), "management", "signature"),
        (_token(jti=None), "management", "signature"),
        (_token(key=ec.generate_private_key(ec.SECP256R1())), "management", "signature"),
    ],
    ids=["expired", "audience", "issuer", "missing-claim", "other-key"],
)
def test_a_token_refused_with_its_reason(token, audience, reason):
    assert _reason(token, audience) == reason


def test_an_hmac_token_is_never_accepted():
    """Algorithm confusion: a token signed with HS256 is refused before any key is chosen."""
    forged = jwt.encode(_claims(), "s" * 32, algorithm="HS256", headers={"kid": "k1"})
    with pytest.raises(TokenRefused) as refused:
        read_unverified(forged)
    assert refused.value.reason == "malformed"


@pytest.mark.parametrize(
    "token",
    [
        "",
        "a.b",
        "not a token",
        jwt.encode(_claims(principalKind="robot"), KEY, "ES256", {"kid": "k"}),
    ],
    ids=["empty", "two-parts", "text", "unknown-principal-kind"],
)
def test_a_token_that_is_not_ours_is_malformed(token):
    with pytest.raises(TokenRefused) as refused:
        read_unverified(token)
    assert refused.value.reason == "malformed"
