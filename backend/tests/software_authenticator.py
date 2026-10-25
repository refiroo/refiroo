"""A software WebAuthn authenticator for the journeys (Product 0.12 I4c, D391).

It makes what a browser's navigator.credentials.create and .get hand back, from the options the
engine answered: a registration with attestation ``none`` and an assertion signed with a generated
P-256 key. ``origin`` and ``verified`` can be changed per call to make the answers a real
authenticator would not give, a passkey of another site or one without the user verified.
"""

import base64
import hashlib
import json
import os
import struct
from typing import Any

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

_USER_PRESENT, _USER_VERIFIED, _ATTESTED = 0x01, 0x04, 0x40


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SoftwareAuthenticator:
    def __init__(self, origin: str):
        self.origin = origin
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        self.user_handle = b""
        self.sign_count = 0

    def _client_data(self, kind: str, challenge: str, origin: str | None) -> bytes:
        return json.dumps(
            {"type": kind, "challenge": challenge, "origin": origin or self.origin,
             "crossOrigin": False}
        ).encode()  # fmt: skip

    def register(
        self, options: dict[str, Any], *, origin: str | None = None, verified: bool = True
    ) -> dict[str, Any]:
        """The credential a browser returns for a registration's ``options``."""
        self.user_handle = unb64(options["user"]["id"])
        numbers = self.key.public_key().public_numbers()
        cose = cbor2.dumps(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )
        flags = _USER_PRESENT | _ATTESTED | (_USER_VERIFIED if verified else 0)
        data = (
            hashlib.sha256(options["rp"]["id"].encode()).digest()
            + bytes([flags])
            + struct.pack(">I", 0)
            + bytes(16)
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + cose
        )
        client = self._client_data("webauthn.create", options["challenge"], origin)
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client),
                "attestationObject": b64(
                    cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": data})
                ),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform",
        }

    def assertion(
        self, options: dict[str, Any], *, origin: str | None = None, verified: bool = True
    ) -> dict[str, Any]:
        """The credential a browser returns for an authentication's ``options``."""
        self.sign_count += 1
        flags = _USER_PRESENT | (_USER_VERIFIED if verified else 0)
        data = (
            hashlib.sha256(options["rpId"].encode()).digest()
            + bytes([flags])
            + struct.pack(">I", self.sign_count)
        )
        client = self._client_data("webauthn.get", options["challenge"], origin)
        signature = self.key.sign(data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client),
                "authenticatorData": b64(data),
                "signature": b64(signature),
                "userHandle": b64(self.user_handle),
            },
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform",
        }
