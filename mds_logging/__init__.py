"""
MDS Unified Logging — shared contract for all components.

Usage:
    from mds_logging import get_logger, register_component

    # At component startup:
    register_component("my_component", "drone", "Description")
    logger = get_logger("my_component")
    logger.info("Hello from unified logging")

Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import logging
from typing import Dict

from mds_logging.registry import register_component, get_registry  # noqa: F401

# Lazy logger cache
_loggers: Dict[str, logging.Logger] = {}
_session_id: str = ""
_source: str = "gcs"  # default, overridden by init_drone_logging / init_server_logging


def get_logger(component: str) -> logging.Logger:
    """Get a logger configured with MDS metadata.

    Must be called after init_logging() (from drone.py or server.py).
    """
    if component in _loggers:
        return _loggers[component]

    logger = logging.getLogger(f"mds.{component}")

    # Inject MDS fields into every record via a filter
    class _MDSFilter(logging.Filter):
        def filter(self, record):
            record.mds_component = component
            record.mds_source = _source
            record.mds_session_id = _session_id
            record.mds_drone_id = getattr(record, "mds_drone_id", None)
            if not hasattr(record, "mds_extra"):
                record.mds_extra = None
            return True

    logger.addFilter(_MDSFilter())
    _loggers[component] = logger
    return logger


def set_session(session_id: str) -> None:
    """Set the current session ID (called by init functions)."""
    global _session_id
    _session_id = session_id


def set_source(source: str) -> None:
    """Set the source type (called by init functions)."""
    global _source
    _source = source


def reset() -> None:
    """Reset global state (for testing)."""
    global _session_id, _source
    _loggers.clear()
    _session_id = ""
    _source = "gcs"
