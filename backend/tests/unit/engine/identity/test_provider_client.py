"""A sign-in provider's answers checked (Product 0.12 I3, D361, D362, D363, D364).

The ID token's signature and claims, the groups a token names, and
why a provider's discovery document is refused, against the harness provider where a provider must
answer.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from oidc_provider import OidcProvider

from app.engine.identity import provider_client
from app.engine.identity.provider_client import Discovery, ProviderError
from app.engine.identity.provider_sign_in import claim_values

ISSUER = "https://id.example.org"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def discovery(monkeypatch):
    found = Discovery(ISSUER, f"{ISSUER}/authorize", f"{ISSUER}/token", f"{ISSUER}/jwks", ())
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
    published = {"keys": [{**jwk, "kid": "k1"}]}
    monkeypatch.setitem(provider_client._keys, found.jwks_uri, (time.monotonic(), published))
    # A key the token names but the set lacks is fetched again once: the same set here.
    monkeypatch.setattr(provider_client, "_get", lambda url, what: published)
    return found


def _token(key=KEY, algorithm="RS256", kid="k1", **changes) -> str:
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": "s-1", "aud": "engine", "iat": now, "exp": now + 300,
              "nonce": "n-1", **changes}  # fmt: skip
    return jwt.encode(
        {k: v for k, v in claims.items() if v is not None}, key, algorithm, {"kid": kid}
    )


def _refused(discovery, token: str, kind: str) -> None:
    with pytest.raises(ProviderError) as refused:
        provider_client.verify_id_token(discovery, token, client_id="engine", nonce="n-1")
    assert refused.value.kind == kind, str(refused.value)


def test_an_id_token_is_checked_claim_by_claim(discovery):
    claims = provider_client.verify_id_token(discovery, _token(), client_id="engine", nonce="n-1")
    assert claims["sub"] == "s-1"
    _refused(discovery, _token(iss=f"{ISSUER}/other"), "issuer")
    _refused(discovery, _token(aud="someone-else"), "audience")
    _refused(discovery, _token(aud=["engine", "other"]), "audience")
    _refused(discovery, _token(aud=["engine", "other"], azp="other"), "audience")
    _refused(discovery, _token(nonce="replayed"), "nonce")
    _refused(discovery, _token(exp=int(time.time()) - 3600), "token")
    _refused(discovery, _token(sub=None), "token")
    _refused(
        discovery,
        _token(key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
        "token",
    )


def test_only_asymmetric_algorithms_are_accepted(discovery):
    _refused(discovery, jwt.encode({"sub": "s"}, "shared-secret", "HS256", {"kid": "k1"}), "token")
    unsigned = jwt.encode({"sub": "s"}, None, "none")
    _refused(discovery, unsigned, "token")
    _refused(
        discovery, _token(key=ec.generate_private_key(ec.SECP256R1()), algorithm="ES256"), "token"
    )


def test_the_groups_a_token_names():
    assert claim_values({"groups": ["a", "b", "a", " ", 7, None, {"x": 1}]}, "groups") == [
        "a",
        "b",
        "7",
    ]
    assert claim_values({"groups": "one"}, "groups") == ["one"]
    assert claim_values({}, "groups") == []
    assert claim_values({"roles": ["r"]}, "groups") == []


def test_a_providers_discovery_is_refused_with_its_reason(monkeypatch):
    with OidcProvider() as idp:
        provider_client.check(idp.issuer)
        with pytest.raises(ProviderError) as other:
            provider_client.discover(f"{idp.issuer}/", fresh=True)
        assert other.value.kind == "issuer" and idp.issuer in str(other.value)
    with pytest.raises(ProviderError) as gone:
        provider_client.discover("http://127.0.0.1:9", fresh=True)
    assert gone.value.kind == "unreachable"
    with pytest.raises(ProviderError) as plain:
        provider_client.discover("http://id.example.org", fresh=True)
    assert plain.value.kind == "address"


def test_the_providers_sign_out_address():
    """RP-Initiated Logout (I4a): the address carries the hint, the return address and the state; a
    provider whose discovery names none offers no sign-out."""
    with OidcProvider() as idp:
        found = provider_client.discover(idp.issuer, fresh=True)
        url = provider_client.sign_out_url(
            found, id_token_hint="a.b.c", post_logout_redirect_uri="https://e/x?y=1", state="s"
        )
        assert url is not None and url.startswith(f"{idp.issuer}/logout?id_token_hint=a.b.c&")
        assert "post_logout_redirect_uri=https%3A%2F%2Fe%2Fx%3Fy%3D1" in url and "state=s" in url
        provider_client.check_sign_out(idp.issuer)
        idp.end_session = False
        with pytest.raises(ProviderError) as none:
            provider_client.check_sign_out(idp.issuer)
        assert none.value.kind == "sign-out"
        bare = provider_client.discover(idp.issuer, fresh=True)
        assert (
            provider_client.sign_out_url(
                bare, id_token_hint="t", post_logout_redirect_uri="https://e/x", state="s"
            )
            is None
        )
