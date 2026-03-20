"""
Environment variable names, defaults, and deprecation shims.

All logging configuration flows through environment variables with the
MDS_LOG_* prefix. Old DRONE_* vars are supported via shim for one release.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import os
import warnings

DEFAULTS = {
    "log_level": "INFO",
    "file_log_level": "DEBUG",
    "max_sessions": 10,
    "max_size_mb": 100,
    "log_dir": "logs/sessions",
    "console_format": "text",
    "flush": True,
    "background_pull": False,
    "pull_interval_sec": 30,
    "pull_level": "WARNING",
    "pull_max_drones": 10,
}


def _get_with_shim(new_key: str, old_key: str | None, default: str) -> str:
    """Read env var with fallback to deprecated name."""
    value = os.environ.get(new_key)
    if value is not None:
        return value
    if old_key:
        old_value = os.environ.get(old_key)
        if old_value is not None:
            warnings.warn(
                f"Environment variable {old_key} is deprecated, use {new_key} instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            return old_value
    return default


def get_log_level() -> str:
    return _get_with_shim("MDS_LOG_LEVEL", "DRONE_LOG_LEVEL", DEFAULTS["log_level"])


def get_file_log_level() -> str:
    return os.environ.get("MDS_LOG_FILE_LEVEL", DEFAULTS["file_log_level"])


def get_max_sessions() -> int:
    return int(os.environ.get("MDS_LOG_MAX_SESSIONS", DEFAULTS["max_sessions"]))


def get_max_size_mb() -> int:
    return int(os.environ.get("MDS_LOG_MAX_SIZE_MB", DEFAULTS["max_size_mb"]))


def get_log_dir() -> str:
    return _get_with_shim("MDS_LOG_DIR", "DRONE_LOG_FILE", DEFAULTS["log_dir"])


def get_console_format() -> str:
    return os.environ.get("MDS_LOG_CONSOLE_FORMAT", DEFAULTS["console_format"])


def get_flush_enabled() -> bool:
    return os.environ.get("MDS_LOG_FLUSH", str(DEFAULTS["flush"])).lower() in ("true", "1", "yes")


# --- Background pull configuration ---

def get_background_pull_enabled() -> bool:
    return os.environ.get("MDS_LOG_BACKGROUND_PULL", "false").lower() in ("true", "1", "yes")


def get_pull_interval_sec() -> int:
    return int(os.environ.get("MDS_LOG_PULL_INTERVAL_SEC", DEFAULTS["pull_interval_sec"]))


def get_pull_level() -> str:
    return os.environ.get("MDS_LOG_PULL_LEVEL", DEFAULTS["pull_level"])


def get_pull_max_drones() -> int:
    return int(os.environ.get("MDS_LOG_PULL_MAX_DRONES", DEFAULTS["pull_max_drones"]))
