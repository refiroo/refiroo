"""The event deriver's thread (Base 0.9 C10): derives each workspace's feed into consumer events and
expires them with the feed.

Once a second it compares each workspace's feed position with its checkpoint (one statement) and
derives where they differ, a page per workspace in turn; the write path is untouched and never
waits for it. A workspace that fails is left alone for a growing wait (``RETRY_SECONDS``, doubling
up to ``MAX_BACKOFF_SECONDS``) while the others go on at their own pace; its failure is logged. A workspace created since the last look gets a checkpoint at 0. Every hour it deletes
the events below the change feed's retention floor (``FEED_RETENTION_DAYS``, never past the active
publication's position, D40, C-D92); the audit log is not pruned. Tests drive it themselves
(``run_until_idle``, ``sweep``) with ``run_event_deriver`` False.
"""

import logging
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, exists, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...common.outage import OutageLog, database_unavailable
from ...models.database import ConsumerEvent, ConsumerEventCheckpoint, Workspace
from ..model.consumer_definitions import consumer_apis, kept_store_key, served_versions
from ..model.registry import model_registry
from ..reads.feed import retention_floor
from .deriver import PAGE_ENTRIES, derive_page
from .plan import EventPlan

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.0
RETRY_SECONDS = 2.0
# The longest a workspace that keeps failing is left alone between its tries.
MAX_BACKOFF_SECONDS = 300.0
SWEEP_SECONDS = 3600.0
# The thread's name, which a measurement of one request's statements leaves out.
THREAD_NAME = "rdm-event-deriver"


class EventDeriver:
    """Derives consumer events in this process: ``run_until_idle`` once; ``start`` on a thread."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        retention_days: int = 30,
        page_entries: int = PAGE_ENTRIES,
    ) -> None:
        self.session_factory = session_factory
        self.retention_days = retention_days
        self.page_entries = page_entries
        self._plans: dict[int, tuple[EventPlan, ...]] = {}
        # A failing workspace's failures in a row and when it is tried again (monotonic seconds).
        self._failing: dict[str, tuple[int, float]] = {}
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    # --- one step ---------------------------------------------------------------------------------

    def pending(self) -> list[str]:
        """The workspaces whose feed is ahead of their checkpoint; a workspace without one gets it
        at 0 first (a new workspace's feed starts empty)."""
        with self.session_factory() as session:
            session.execute(
                insert(ConsumerEventCheckpoint)
                .from_select(
                    ["workspace_key", "position", "start_position", "updated_at"],
                    select(Workspace.key, literal(0), literal(0), literal(datetime.now(UTC))).where(
                        ~exists().where(ConsumerEventCheckpoint.workspace_key == Workspace.key)
                    ),
                )
                .on_conflict_do_nothing()
            )
            behind = list(
                session.scalars(
                    select(Workspace.key)
                    .join(ConsumerEventCheckpoint, ConsumerEventCheckpoint.workspace_key == Workspace.key)
                    .where(Workspace.feed_position > ConsumerEventCheckpoint.position)
                    .order_by(Workspace.key)
                )
            )
            session.commit()
        return behind

    def derive(self, workspace_key: str) -> bool:
        """Derive the workspace's next page; ``False`` when there is none, or another deriver holds
        the workspace."""
        with self.session_factory() as session:
            try:
                return derive_page(session, workspace_key, self._plans_for, self.page_entries)
            except OperationalError as exc:
                # Another deriver moved the checkpoint after this one's snapshot began: it has the
                # range; this one looks again later.
                if getattr(exc.orig, "sqlstate", None) == "40001":
                    session.rollback()
                    return False
                raise

    def run_round(self) -> tuple[bool, list[Exception]]:
        """A page for each workspace that is behind and not waiting out a failure, every one in
        turn: whether any was derived, and the errors of those that failed. A workspace that fails
        does not hold up the others (0.9 R-F11) and is tried again after a growing wait."""
        derived: list[bool] = []
        failures: list[Exception] = []
        now = time.monotonic()
        behind = self.pending()
        for key in set(self._failing) - set(behind):
            del self._failing[key]  # caught up or gone: its failure no longer counts
        for key in behind:
            if key in self._failing and self._failing[key][1] > now:
                continue
            try:
                derived.append(self.derive(key))
            except Exception as exc:
                failed = self._failing.get(key, (0, 0.0))[0] + 1
                wait = min(RETRY_SECONDS * 2 ** (failed - 1), MAX_BACKOFF_SECONDS)
                self._failing[key] = (failed, time.monotonic() + wait)
                failures.append(exc)
                if failed == 1 or failed % 10 == 0:
                    logger.error(
                        "The event deriver cannot derive workspace '%s' (failure %s in a row); it "
                        "tries it again in %.0f s and goes on with the others",
                        key,
                        failed,
                        wait,
                        exc_info=exc,
                    )
            else:
                self._failing.pop(key, None)
        return any(derived), failures

    def run_once(self) -> bool:
        """``run_round``, raising the first error once every workspace had its turn."""
        derived, failures = self.run_round()
        if failures:
            raise failures[0]
        return derived

    def run_until_idle(self) -> int:
        """Derive until every workspace is at its head; the pages derived. Waits briefly while
        another deriver holds a workspace that is still behind."""
        pages = 0
        while True:
            behind = self.pending()
            if not behind:
                return pages
            derived = sum(1 for key in behind if self.derive(key))
            pages += derived
            if not derived:
                time.sleep(0.01)

    def sweep(self) -> int:
        """Delete every workspace's events below its retention floor; the number deleted."""
        removed = 0
        with self.session_factory() as session:
            for key in session.scalars(select(ConsumerEventCheckpoint.workspace_key)).all():
                floor = retention_floor(session, key, self.retention_days)
                removed += session.execute(
                    delete(ConsumerEvent).where(
                        ConsumerEvent.workspace_key == key,
                        ConsumerEvent.position < floor.earliest_position,
                    )
                ).rowcount
            session.commit()
        return removed

    def _plans_for(self, session: Session, release_id: int) -> Sequence[EventPlan]:
        """The plans of the release's definitions that declare events, built once per release."""
        if release_id not in self._plans:
            model = model_registry.resolve_release(session, release_id, require_ready=False).model
            plans = [EventPlan(model, definition) for definition in consumer_apis(model) if definition.events]
            # Each earlier version the model keeps derives its own events (DF3).
            for definition in consumer_apis(model):
                for kept in served_versions(model, definition.key)[1:]:
                    if kept.definition.events:
                        plans.append(EventPlan(model, kept.definition, kept_store_key(kept.definition)))
            self._plans[release_id] = tuple(plans)
        return self._plans[release_id]

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name=THREAD_NAME, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """Stop after the running page; a page not committed is derived again by the next start."""
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _loop(self) -> None:
        next_sweep = 0.0
        outage = OutageLog(logger, "The event deriver", RETRY_SECONDS)
        while not self._stopping.is_set():
            wait = POLL_SECONDS
            try:
                if time.monotonic() >= next_sweep:
                    # Its own failure never stops the deriving: a sweep that failed is tried again
                    # in a short while, one that worked in an hour.
                    try:
                        self.sweep()
                        next_sweep = time.monotonic() + SWEEP_SECONDS
                    except Exception as exc:
                        next_sweep = time.monotonic() + RETRY_SECONDS * 15
                        logger.error("The event deriver's expiry sweep failed", exc_info=exc)
                while not self._stopping.is_set():
                    derived, failures = self.run_round()
                    if failures:
                        # The failing workspaces wait out their own backoff; only a database that
                        # cannot be reached is reported as an outage of the thread.
                        unreachable = [exc for exc in failures if database_unavailable(exc)]
                        if unreachable:
                            raise unreachable[0]
                    if not derived:
                        break
                outage.succeeded()
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
                wait = RETRY_SECONDS
            self._stopping.wait(wait)
