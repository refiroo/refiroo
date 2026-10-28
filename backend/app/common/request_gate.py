"""At most as many requests inside the application as the connection pool has connections.

A request's sign-in step takes a pooled connection and keeps it for the request (one session per
request), then needs a worker thread again for its next step. When a page sent more requests at
once than the pool holds (a sidebar asking for 100 lists), the requests without a connection took
every worker thread and each blocked in it waiting for a connection, while the requests holding
the connections waited for a thread: nothing moved until DATABASE_POOL_TIMEOUT, and every request
answered 503 (found on a real instance with a model of 101 types, 2026-10-28). Here a request
waits for its turn on the event loop, holding neither a thread nor a connection; it is let in
while fewer than DATABASE_POOL_SIZE + DATABASE_POOL_MAX_OVERFLOW requests are inside, and leaves
when its answer starts (the session has closed by then, so a long stream holds no turn). One that
waits longer than DATABASE_POOL_TIMEOUT is answered 503 ``poolExhausted`` as a pool timeout is.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

# Answered without the database, so never held back.
_EXEMPT = frozenset({"/health/live", "/metrics"})


class RequestGate:
    def __init__(
        self,
        app: Any,
        *,
        capacity: int,
        timeout: float,
        refuse: Callable[[dict[str, Any], Any, Any], Awaitable[None]],
    ) -> None:
        self.app = app
        self.timeout = timeout
        self.refuse = refuse
        self.turns = asyncio.Semaphore(capacity)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] in _EXEMPT:
            await self.app(scope, receive, send)
            return
        try:
            await asyncio.wait_for(self.turns.acquire(), self.timeout)
        except TimeoutError:
            await self.refuse(scope, receive, send)
            return
        inside = True

        def leave() -> None:
            nonlocal inside
            if inside:
                inside = False
                self.turns.release()

        async def sending(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                leave()
            await send(message)

        try:
            await self.app(scope, receive, sending)
        finally:
            leave()
