"""Where a passkey belongs (Product 0.12 I4c, D392): the relying party is the host of PUBLIC_URL and
its pages' origin, never an address a browser reached the engine by some other way."""

import pytest

from app.engine.identity.passkeys import relying_party
from app.engine.identity.settings import IdentitySettings


def _settings(issuer: str) -> IdentitySettings:
    return IdentitySettings(
        encryption_key=bytes(32), issuer=issuer, access_token_seconds=3600, signing_key_days=30
    )


@pytest.mark.parametrize(
    ("issuer", "host", "origin"),
    [
        (
            "https://rdm.northfield.example",
            "rdm.northfield.example",
            "https://rdm.northfield.example",
        ),
        (
            "https://rdm.northfield.example:8443",
            "rdm.northfield.example",
            "https://rdm.northfield.example:8443",
        ),
        ("http://localhost:8000", "localhost", "http://localhost:8000"),
    ],
)
def test_the_relying_party_is_the_public_urls_host_and_origin(issuer, host, origin):
    assert relying_party(_settings(issuer)) == (host, origin)
