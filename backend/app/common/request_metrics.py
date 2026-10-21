"""This process's request counters (Product 0.11 O1, D194), kept by ``RequestObservation`` and
reported with the process's heartbeat.

Requests are counted by method, the matched route's template and status, and timed per route
template; never by path, so a record ID never becomes a label. A request no route matched counts
under ``unmatched``.
"""

import bisect
import threading
from dataclasses import dataclass, field
from typing import Any

# Seconds; the last bucket counts every request slower than the last bound.
DURATION_BOUNDS: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
UNMATCHED_ROUTE = "unmatched"


@dataclass
class _Durations:
    counts: list[int] = field(default_factory=lambda: [0] * (len(DURATION_BOUNDS) + 1))
    total: float = 0.0


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = {}
        self._durations: dict[str, _Durations] = {}

    def record(self, method: str, route: str, status: int, seconds: float) -> None:
        with self._lock:
            key = (method, route, status)
            self._requests[key] = self._requests.get(key, 0) + 1
            durations = self._durations.setdefault(route, _Durations())
            durations.counts[bisect.bisect_left(DURATION_BOUNDS, seconds)] += 1
            durations.total += seconds

    def snapshot(self) -> dict[str, Any]:
        """The counters as the heartbeat stores them (JSON)."""
        with self._lock:
            return {
                "requests": [
                    {"method": method, "route": route, "status": status, "count": count}
                    for (method, route, status), count in sorted(self._requests.items())
                ],
                "durations": [
                    {"route": route, "counts": list(item.counts), "sum": item.total}
                    for route, item in sorted(self._durations.items())
                ],
            }


request_metrics = RequestMetrics()
