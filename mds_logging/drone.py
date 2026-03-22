"""
Drone-side logging initialization.

Call init_drone_logging() once at startup in coordinator, drone_show, etc.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import logging
import os
import sys

import mds_logging
from mds_logging.constants import (
    get_log_level, get_file_log_level, get_log_dir,
    get_console_format, get_flush_enabled, get_max_sessions, get_max_size_mb,
)
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter
from mds_logging.session import create_session, cleanup_sessions, get_session_filepath
from mds_logging.handlers import SessionFileHandler, WatcherHandler
from mds_logging.watcher import get_watcher


def init_drone_logging(drone_id: int | None = None, log_dir: str | None = None) -> str:
    """Initialize logging for a drone-side component.

    Returns the session_id.
    """
    log_dir = log_dir or get_log_dir()

    # Cleanup old sessions
    cleanup_sessions(log_dir, get_max_sessions(), get_max_size_mb())

    # Create new session
    session_id = create_session(log_dir)
    session_file = get_session_filepath(log_dir, session_id)

    # Set global state
    mds_logging.set_session(session_id)
    mds_logging.set_source("drone")
    mds_logging.set_drone_id(drone_id if drone_id is not None else os.environ.get("MDS_HW_ID"))

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    # File handler — JSONL, DEBUG level
    file_handler = SessionFileHandler(session_file, flush_every_line=get_flush_enabled())
    file_handler.setLevel(getattr(logging, get_file_log_level()))
    file_handler.setFormatter(JSONLFormatter())
    root.addHandler(file_handler)

    # Console handler — colored text, configurable level
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = get_log_level()
    console_handler.setLevel(getattr(logging, console_level))
    if get_console_format() == "json":
        console_handler.setFormatter(JSONLFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root.addHandler(console_handler)

    # Watcher handler — for SSE streaming (Phase 2)
    watcher_handler = WatcherHandler(get_watcher(), JSONLFormatter())
    watcher_handler.setLevel(logging.DEBUG)
    root.addHandler(watcher_handler)

    return session_id
