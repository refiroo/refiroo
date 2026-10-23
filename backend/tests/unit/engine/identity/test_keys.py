"""The signing key replaced when due, at issue (D254, D264), on a clone of a scenario seed."""

import base64
from datetime import UTC, datetime, timedelta

from harness_identity import SECRETS_ENCRYPTION_KEY
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.identity import keys
from app.engine.identity.settings import IdentitySettings
from app.models.database import TokenSigningKey

SETTINGS = IdentitySettings(
    encryption_key=base64.urlsafe_b64decode(SECRETS_ENCRYPTION_KEY),
    issuer="http://localhost:8000",
    access_token_seconds=3600,
    signing_key_days=30,
)


def test_the_current_key_signs_until_it_is_due_then_a_new_one_does(seeded):
    with SessionLocal() as session:
        kid, _ = keys.signing_key(session, SETTINGS)
        assert keys.signing_key(session, SETTINGS)[0] == kid
        current = session.scalar(select(TokenSigningKey).where(TokenSigningKey.kid == kid))
        current.created_at = datetime.now(UTC) - timedelta(days=30, seconds=1)
        session.commit()
        replaced, _ = keys.signing_key(session, SETTINGS)
        assert replaced != kid
        old = session.scalar(select(TokenSigningKey).where(TokenSigningKey.kid == kid))
        # The old key keeps verifying the tokens it signed until they expire.
        assert old.rotated_at is not None
        assert old.retired_at - old.rotated_at == timedelta(seconds=3600)
        assert keys.verifies(old, datetime.now(UTC))
        assert not keys.verifies(old, old.retired_at)
        assert [jwk["kid"] for jwk in keys.published(session)][:2] == [replaced, kid]


def test_a_key_younger_than_its_days_is_kept(seeded):
    with SessionLocal() as session:
        kid, _ = keys.signing_key(session, SETTINGS)
        current = session.scalar(select(TokenSigningKey).where(TokenSigningKey.kid == kid))
        current.created_at = datetime.now(UTC) - timedelta(days=29, hours=23)
        session.commit()
        assert keys.signing_key(session, SETTINGS)[0] == kid
