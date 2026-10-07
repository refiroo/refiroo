"""Job change notifications for the job event stream (Base 0.9 J1u, D58).

A trigger on ``jobs`` sends ``pg_notify('rdm_job_events', <job id>)`` when a change to a job
commits (revision ``20261007_05``). One listener thread per process holds a connection that
``LISTEN``s and wakes the streams following that job; each stream then reads the job again. Several
processes each listen to the same database, so a change made by any of them reaches every stream.
Nothing is polled: a stream waits until it is woken, sending a keep-alive while it waits.

After an outage the listener reconnects with the ``OutageLog`` and wakes every stream once, since a
notification sent while it was away is lost; each stream reads its job again and sends it only if
it changed.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import psycopg

from ...common.outage import OutageLog

logger = logging.getLogger(__name__)

CHANNEL = "rdm_job_events"
RETRY_SECONDS = 2.0
# How long the listener waits for a notification before it looks whether it should stop.
WAIT_SECONDS = 1.0
THREAD_NAME = "rdm-job-listener"


@dataclass(eq=False)
class Subscription:
    """One stream's wake-up: set from the listener thread, awaited on the stream's event loop."""

    job_id: str
    loop: asyncio.AbstractEventLoop
    woken: asyncio.Event = field(default_factory=asyncio.Event)

    def wake(self) -> None:
        self.loop.call_soon_threadsafe(self.woken.set)


class JobListener:
    """Listens for job notifications in this process and wakes the streams that follow each job."""

    def __init__(self, conninfo: Callable[[], str]) -> None:
        self._conninfo = conninfo
        self._subscriptions: dict[str, set[Subscription]] = defaultdict(set)
        self._lock = threading.Lock()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def subscribe(self, job_id: str) -> Subscription:
        """Called on the stream's event loop, before it reads the job, so no change is missed."""
        subscription = Subscription(job_id, asyncio.get_running_loop())
        with self._lock:
            self._subscriptions[job_id].add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            followers = self._subscriptions.get(subscription.job_id)
            if followers is not None:
                followers.discard(subscription)
                if not followers:
                    del self._subscriptions[subscription.job_id]

    def notify(self, job_id: str | None = None) -> None:
        """Wake the streams of ``job_id``, or every stream."""
        with self._lock:
            if job_id is None:
                woken = [item for followers in self._subscriptions.values() for item in followers]
            else:
                woken = list(self._subscriptions.get(job_id, ()))
        for subscription in woken:
            subscription.wake()

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name=THREAD_NAME, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _loop(self) -> None:
        outage = OutageLog(logger, "The job listener", RETRY_SECONDS)
        while not self._stopping.is_set():
            try:
                with psycopg.connect(self._conninfo(), autocommit=True) as connection:
                    connection.execute(f"LISTEN {CHANNEL}")
                    if outage.failing:
                        # Notifications sent while the listener was away are lost: every stream
                        # reads its job again.
                        self.notify()
                    outage.succeeded()
                    while not self._stopping.is_set():
                        for message in connection.notifies(timeout=WAIT_SECONDS):
                            self.notify(message.payload)
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
                self._stopping.wait(RETRY_SECONDS)
