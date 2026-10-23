"""Tests and the seeds call the engine directly too, outside a request or a job: such a session
writes as the engine itself (Product 0.12 Z2, D292). A request names its caller and a job step its
requester, replacing this writer; the application has no such default, so a path there that forgets
to name one is refused with ``WRITER_UNKNOWN``.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.engine.authorization.writes import SYSTEM, set_writer, writer_of


@event.listens_for(Session, "after_begin")
def _engine_writes(session: Session, _transaction, _connection) -> None:
    if writer_of(session) is None:
        set_writer(session, SYSTEM)
