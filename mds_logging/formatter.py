"""
Log formatters — JSONL for files, colored text for console.

JSONLFormatter produces one JSON object per line for machine parsing.
ConsoleFormatter produces colored human-readable output for terminals.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JSONLFormatter(logging.Formatter):
    """Formats log records as single-line JSON (JSONL)."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"
        from mds_logging import get_context_defaults

        context = get_context_defaults()
        entry = {
            "ts": ts_str,
            "level": record.levelname,
            "component": getattr(record, "mds_component", record.name),
            "source": getattr(record, "mds_source", context.get("source") or "gcs"),
            "drone_id": getattr(record, "mds_drone_id", context.get("drone_id")),
            "session_id": getattr(record, "mds_session_id", context.get("session_id") or ""),
            "msg": record.getMessage(),
            "extra": getattr(record, "mds_extra", None),
        }
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            entry["traceback"] = record.exc_text
        return json.dumps(entry, default=str)


# ANSI color codes
_COLORS = {
    "DEBUG": "\033[36m",       # cyan
    "INFO": "\033[32m",        # green
    "WARNING": "\033[33m",     # yellow
    "ERROR": "\033[31m",       # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"


class ConsoleFormatter(logging.Formatter):
    """Formats log records as colored human-readable text for terminals."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        ts_str = ts.strftime("%H:%M:%S.") + f"{ts.microsecond // 1000:03d}"
        level = record.levelname
        color = _COLORS.get(level, "")
        component = getattr(record, "mds_component", record.name)
        msg = record.getMessage()
        extra = getattr(record, "mds_extra", None)

        parts = [f"{ts_str} {color}{level:<8}{_RESET} [{component}] {msg}"]
        if extra:
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            parts[0] += f" ({kv})"
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            parts.append(record.exc_text)
        return "\n".join(parts)
