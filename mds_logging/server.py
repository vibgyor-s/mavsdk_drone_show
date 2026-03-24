"""
GCS server-side logging initialization.

Call init_server_logging() once at FastAPI startup.
Provides convenience wrappers that match the old gcs_logging.py API
to minimize migration churn in app_fastapi.py.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import logging
import sys

import mds_logging
from mds_logging import configure_external_loggers
from mds_logging.constants import (
    get_log_level, get_file_log_level, get_log_dir,
    get_console_format, get_flush_enabled, get_max_sessions, get_max_size_mb,
)
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter
from mds_logging.session import create_session, cleanup_sessions, get_session_filepath
from mds_logging.handlers import SessionFileHandler, WatcherHandler
from mds_logging.watcher import get_watcher

# Module-level logger for server convenience functions
_server_logger: logging.Logger | None = None


def init_server_logging(log_dir: str | None = None) -> str:
    """Initialize logging for GCS server. Returns session_id."""
    global _server_logger
    log_dir = log_dir or get_log_dir()

    cleanup_sessions(log_dir, get_max_sessions(), get_max_size_mb())
    session_id = create_session(log_dir)
    session_file = get_session_filepath(log_dir, session_id)

    mds_logging.set_session(session_id)
    mds_logging.set_source("gcs")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = SessionFileHandler(session_file, flush_every_line=get_flush_enabled())
    file_handler.setLevel(getattr(logging, get_file_log_level()))
    file_handler.setFormatter(JSONLFormatter())
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_level = get_log_level()
    console_handler.setLevel(getattr(logging, console_level))
    if get_console_format() == "json":
        console_handler.setFormatter(JSONLFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root.addHandler(console_handler)

    watcher_handler = WatcherHandler(get_watcher(), JSONLFormatter())
    watcher_handler.setLevel(logging.DEBUG)
    root.addHandler(watcher_handler)

    configure_external_loggers()

    _server_logger = mds_logging.get_logger("gcs")
    return session_id


# --- Convenience wrappers matching old gcs_logging.py API ---
# These allow minimal changes in app_fastapi.py during migration.

def get_logger(component: str = "gcs") -> logging.Logger:
    """Get a logger (delegates to mds_logging.get_logger)."""
    return mds_logging.get_logger(component)


def log_system_event(message: str, level: str = "INFO", component: str = "system") -> None:
    """Log a system event (replaces old gcs_logging.log_system_event)."""
    logger = mds_logging.get_logger(component)
    log_level = getattr(logging, level, logging.INFO)
    logger.log(log_level, message)


def log_system_error(message: str, component: str = "system") -> None:
    """Log a system error (replaces old gcs_logging.log_system_error)."""
    logger = mds_logging.get_logger(component)
    logger.error(message)


def log_system_warning(message: str, component: str = "system") -> None:
    """Log a system warning (replaces old gcs_logging.log_system_warning)."""
    logger = mds_logging.get_logger(component)
    logger.warning(message)


def log_system_startup(message: str, component: str = "system") -> None:
    """Log a startup event."""
    logger = mds_logging.get_logger(component)
    logger.info(message)


def log_drone_command(message: str, drone_id: int | None = None, component: str = "command") -> None:
    """Log a drone command event."""
    logger = mds_logging.get_logger(component)
    logger.info(message, extra={"mds_drone_id": drone_id})


def log_drone_telemetry(message: str, drone_id: int | None = None, component: str = "telemetry") -> None:
    """Log a telemetry event."""
    logger = mds_logging.get_logger(component)
    logger.debug(message, extra={"mds_drone_id": drone_id})


def initialize_logging(**kwargs) -> str:
    """Alias for init_server_logging (backward compat)."""
    return init_server_logging(**kwargs)
