"""
In-memory pub/sub for real-time log streaming via SSE.

LogWatcher.publish() is called by the log handler on every write.
LogWatcher.subscribe() is an async generator consumed by SSE endpoints.
Zero subscribers = zero overhead.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import asyncio
from collections import deque

# Level ordering for filtering
_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


def _matches_filter(entry: dict, level: str | None = None, component: str | None = None,
                    source: str | None = None, drone_id: int | None = None) -> bool:
    """Check if a log entry matches the given filters."""
    if level and _LEVEL_ORDER.get(entry.get("level", ""), 0) < _LEVEL_ORDER.get(level, 0):
        return False
    if component and entry.get("component") != component:
        return False
    if source and entry.get("source") != source:
        return False
    if drone_id is not None and entry.get("drone_id") != drone_id:
        return False
    return True


class LogWatcher:
    """In-memory pub/sub for real-time log streaming."""

    def __init__(self, max_buffer: int = 100):
        self._subscribers: list[asyncio.Queue] = []
        self._buffer: deque = deque(maxlen=max_buffer)

    def publish(self, log_entry: dict) -> None:
        """Called by log handler on every write. Non-blocking."""
        self._buffer.append(log_entry)
        for queue in self._subscribers:
            try:
                queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass  # Drop entry if subscriber is slow

    async def subscribe(self, level: str | None = None, component: str | None = None,
                        source: str | None = None, drone_id: int | None = None):
        """Async generator yielding filtered log entries."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(queue)
        try:
            # Send buffered recent lines first
            for entry in self._buffer:
                if _matches_filter(entry, level, component, source, drone_id):
                    yield entry
            # Stream live
            while True:
                entry = await queue.get()
                if _matches_filter(entry, level, component, source, drone_id):
                    yield entry
        finally:
            self._subscribers.remove(queue)


# Global watcher instance — shared across the process
_watcher = LogWatcher()


def get_watcher() -> LogWatcher:
    """Get the global LogWatcher instance."""
    return _watcher
