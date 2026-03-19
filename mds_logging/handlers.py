"""
Session-aware file handler with flush-on-write for crash safety.

Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import logging
import os


class SessionFileHandler(logging.FileHandler):
    """File handler that creates parent dirs and optionally flushes every line."""

    def __init__(self, filename: str, flush_every_line: bool = True, **kwargs):
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        self._flush_every_line = flush_every_line
        super().__init__(filename, mode="a", encoding="utf-8", **kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        if self._flush_every_line:
            self.flush()


class WatcherHandler(logging.Handler):
    """Handler that publishes log entries to a LogWatcher for SSE streaming.

    Shared by both drone.py and server.py init functions.
    """

    def __init__(self, watcher, formatter):
        super().__init__()
        self._watcher = watcher
        self._formatter = formatter

    def emit(self, record):
        import json
        try:
            line = self._formatter.format(record)
            entry = json.loads(line)
            self._watcher.publish(entry)
        except Exception:
            pass  # Never crash the app for watcher failures
