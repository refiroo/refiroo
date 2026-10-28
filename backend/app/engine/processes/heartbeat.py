"""The thread that reports this process to the others (Product 0.11 O1, D192).

Every ``PROCESS_HEARTBEAT_SECONDS`` it upserts the process's ``engine_processes`` row with its
report and deletes the rows of processes silent for a day. A clean stop deletes the row; a process
that dies leaves it, read as silent once three heartbeats are missed. A database outage is logged
as the other threads log it (``OutageLog``).
"""

import logging
import threading
from collections.abc import Callable, Collection
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...common.outage import OutageLog
from ...config import ENGINE_VERSION
from ...models.database import EngineProcess
from ..model.registry import model_registry
from .report import HEARTBEAT_THREAD, build_report, this_process

logger = logging.getLogger(__name__)

# How long a silent process's row is kept, so an operator still sees a process that died.
SILENT_ROW_RETENTION = timedelta(days=1)


def beat(session: Session, started_threads: Collection[str]) -> None:
    """Write this process's row now, in ``session``'s transaction; the caller commits."""
    identity = this_process()
    now = datetime.now(UTC)
    values = {
        "process_id": identity.process_id,
        "host": identity.host,
        "pid": identity.pid,
        "engine_version": ENGINE_VERSION,
        "started_at": identity.started_at,
        "heartbeat_at": now,
        "report": build_report(session, started_threads),
    }
    statement = insert(EngineProcess).values(**values)
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[EngineProcess.process_id],
            set_={"heartbeat_at": now, "report": statement.excluded.report},
        )
    )
    session.execute(
        delete(EngineProcess).where(EngineProcess.heartbeat_at < now - SILENT_ROW_RETENTION)
    )


class ProcessHeartbeat:
    def __init__(self, session_factory: Callable[[], Session], interval_seconds: int) -> None:
        self.session_factory = session_factory
        self.interval_seconds = interval_seconds
        # The background threads this process started; the others report ``off``.
        self.started_threads: set[str] = set()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def beat(self, session: Session) -> None:
        if model_registry.waiting_for_a_servable_model:
            # Another process may have raised the releases this one waits for (0.12 R, R-F9).
            model_registry.refresh_servable(session)
        beat(session, self.started_threads | {HEARTBEAT_THREAD})

    def start(self) -> None:
        """Report now, so the process is listed as soon as it serves, then every interval."""
        self._stopping.clear()
        try:
            with self.session_factory() as session:
                self.beat(session)
                session.commit()
        except Exception:
            # A lasting failure is reported by the thread's OutageLog.
            logger.debug("The process heartbeat's first report failed", exc_info=True)
        self._thread = threading.Thread(target=self._loop, name=HEARTBEAT_THREAD, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stopping.set()
        if self._thread is None:
            return
        self._thread.join(timeout)
        self._thread = None
        try:
            with self.session_factory() as session:
                session.execute(
                    delete(EngineProcess).where(
                        EngineProcess.process_id == this_process().process_id
                    )
                )
                session.commit()
        except Exception:
            # Its row turns silent and is deleted after a day instead.
            logger.debug("The process heartbeat could not delete its row", exc_info=True)

    def _loop(self) -> None:
        outage = OutageLog(logger, "The process heartbeat", self.interval_seconds)
        while not self._stopping.wait(self.interval_seconds):
            try:
                with self.session_factory() as session:
                    self.beat(session)
                    session.commit()
                outage.succeeded()
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
