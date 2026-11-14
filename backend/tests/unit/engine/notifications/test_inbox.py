"""``engine/notifications/inbox.after``: the stream's read of an inbox, with a notice that committed
after a later one (its sequence ID is lower)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from app.db import SessionLocal
from app.engine.notifications import inbox
from app.models.database import Notification, User


def _notice(sequence_id: int, user_id: int, created_at: datetime) -> Notification:
    return Notification(
        sequence_id=sequence_id,
        user_id=user_id,
        kind="job-finished",
        workspace_key="default",
        subject_kind="job",
        subject_id=f"subject-{sequence_id}",
        details={},
        created_at=created_at,
    )


def test_a_notice_committed_late_is_read_once_though_its_id_is_lower(seeded):
    now = datetime.now(UTC)
    with SessionLocal() as session:
        user = session.scalar(select(User).limit(1))
        if user is None:
            user = User(name="Reader", email="reader@example.org")
            session.add(user)
            session.flush()
        owner = ("user", user.id)
        high = session.scalar(
            text("SELECT coalesce(max(sequence_id), 0) + 1000 FROM notifications")
        )
        session.add(_notice(high, user.id, now))
        session.commit()
        # The stream read the notice with ID ``high``; one made before it commits only now.
        session.add(_notice(high - 1, user.id, now - timedelta(seconds=2)))
        session.commit()

        by_id = [n.sequence_id for n in inbox.after(session, owner, high)]
        assert by_id == []  # read by ID alone, the late notice is never seen

        since = now - timedelta(seconds=30)
        late = inbox.after(session, owner, high, recent_since=since, known={high})
        assert [n.sequence_id for n in late] == [high - 1]
        sent = inbox.after(session, owner, high, recent_since=since, known={high, high - 1})
        assert sent == []
