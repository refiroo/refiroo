"""Server-sent event streams that follow the database's change notices (D58).

A stream subscribes to the job listener under a key, reads where it stands, then waits for the
listener to wake it and reads again. Two streams use it and keep their own reading: a job's
(ends on a final state, sends only what changed) and the inbox's (named events, catch-up loop).
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from ..engine.jobs.events import JobListener, Subscription

# A stream sends a comment this often while nothing changes, so proxies keep it open.
KEEP_ALIVE_SECONDS = 15.0
KEEP_ALIVE = ": keep-alive\n\n"


def frame(name: str, body: Any) -> str:
    """One named event with its data as compact JSON."""
    return f"event: {name}\ndata: {json.dumps(body, separators=(',', ':'))}\n\n"


async def subscribe[T](
    request: Request, key: str, read: Callable[..., T], *args: Any
) -> tuple[Subscription, T]:
    """Subscribe under ``key`` and run ``read(request, *args)`` in a thread for the first state;
    when it fails the subscription is dropped again."""
    listener: JobListener = request.app.state.job_listener
    subscription = listener.subscribe(key)
    try:
        return subscription, await run_in_threadpool(read, request, *args)
    except BaseException:
        listener.unsubscribe(subscription)
        raise


async def woken(subscription: Subscription) -> bool:
    """Wait for the next change notice; ``False`` after ``KEEP_ALIVE_SECONDS`` without one (the
    caller then sends ``KEEP_ALIVE``). A notice is cleared once seen."""
    try:
        await asyncio.wait_for(subscription.woken.wait(), KEEP_ALIVE_SECONDS)
    except TimeoutError:
        return False
    subscription.woken.clear()
    return True


def respond(
    request: Request, subscription: Subscription, events: AsyncIterator[str]
) -> StreamingResponse:
    """The streaming response of ``events``, dropping the subscription when it ends."""
    listener: JobListener = request.app.state.job_listener

    async def stream() -> AsyncIterator[str]:
        try:
            async for chunk in events:
                yield chunk
        finally:
            listener.unsubscribe(subscription)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
