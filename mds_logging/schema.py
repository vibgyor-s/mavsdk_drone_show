"""
JSONL log entry schema — the single source of truth for log format.

Every log line across every MDS component follows this schema.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

from datetime import datetime, timezone

REQUIRED_FIELDS = ("ts", "level", "component", "source", "drone_id", "session_id", "msg")
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
VALID_SOURCES = ("drone", "gcs", "frontend", "infra")


def build_log_entry(
    level: str,
    component: str,
    source: str,
    msg: str,
    session_id: str,
    drone_id: int | None = None,
    extra: dict | None = None,
    ts: str | None = None,
) -> dict:
    """Build a validated JSONL log entry dict."""
    if level not in VALID_LEVELS:
        raise ValueError(f"Invalid level '{level}', must be one of {VALID_LEVELS}")
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}', must be one of {VALID_SOURCES}")
    if ts is None:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return {
        "ts": ts,
        "level": level,
        "component": component,
        "source": source,
        "drone_id": drone_id,
        "session_id": session_id,
        "msg": msg,
        "extra": extra,
    }
