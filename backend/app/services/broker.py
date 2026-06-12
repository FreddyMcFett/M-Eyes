"""In-process async pub/sub used by the SSE live event stream."""

import asyncio
import json
from typing import Any


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def publish(self, kind: str, payload: dict[str, Any]) -> None:
        """Thread-safe publish; callable from sync request handlers."""
        if self._loop is None or not self._subscribers:
            return
        message = json.dumps({"kind": kind, **payload}, default=str)

        def _fanout() -> None:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    pass

        try:
            self._loop.call_soon_threadsafe(_fanout)
        except RuntimeError:
            pass  # loop already closed (shutdown)


broker = EventBroker()
