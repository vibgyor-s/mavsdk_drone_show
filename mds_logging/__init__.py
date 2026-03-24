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
_drone_id: int | str | None = None

_NOISY_EXTERNAL_LOGGERS = {
    # HTTP client internals can flood DEBUG logs during normal polling.
    "urllib3": logging.WARNING,
    "urllib3.connectionpool": logging.WARNING,
    "requests": logging.WARNING,
    "aiohttp": logging.WARNING,
    "aiohttp.access": logging.WARNING,
    "httpx": logging.WARNING,
    # Uvicorn access logs duplicate the structured API request logs we already emit.
    "uvicorn.access": logging.WARNING,
    # File-watcher reload internals are not operator signal.
    "watchfiles": logging.WARNING,
    "watchfiles.main": logging.WARNING,
}


def _normalize_drone_id(drone_id: int | str | None) -> int | str | None:
    """Normalize drone identifiers while preserving non-numeric IDs."""
    if drone_id is None:
        return None

    text = str(drone_id).strip()
    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return text


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
            record.mds_drone_id = getattr(record, "mds_drone_id", _drone_id)
            if not hasattr(record, "mds_extra"):
                record.mds_extra = None
            return True

    logger.addFilter(_MDSFilter())
    _loggers[component] = logger
    return logger


def configure_external_loggers() -> None:
    """Quiet third-party debug noise while preserving warning/error signal."""
    for logger_name, minimum_level in _NOISY_EXTERNAL_LOGGERS.items():
        logger = logging.getLogger(logger_name)
        if logger.level == logging.NOTSET or logger.level < minimum_level:
            logger.setLevel(minimum_level)


def set_session(session_id: str) -> None:
    """Set the current session ID (called by init functions)."""
    global _session_id
    _session_id = session_id


def set_source(source: str) -> None:
    """Set the source type (called by init functions)."""
    global _source
    _source = source


def set_drone_id(drone_id: int | str | None) -> None:
    """Set the current process-wide drone identifier."""
    global _drone_id
    _drone_id = _normalize_drone_id(drone_id)


def get_context_defaults() -> dict:
    """Return the active process-wide logging defaults."""
    return {
        "session_id": _session_id,
        "source": _source,
        "drone_id": _drone_id,
    }


def reset() -> None:
    """Reset global state (for testing)."""
    global _session_id, _source, _drone_id
    _loggers.clear()
    _session_id = ""
    _source = "gcs"
    _drone_id = None
