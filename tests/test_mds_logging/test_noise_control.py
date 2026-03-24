"""Tests for external logger noise suppression."""

from __future__ import annotations

import logging

from mds_logging import configure_external_loggers


def test_configure_external_loggers_suppresses_http_client_debug_noise():
    logger = logging.getLogger("urllib3.connectionpool")
    original_level = logger.level
    try:
        logger.setLevel(logging.DEBUG)
        configure_external_loggers()
        assert logger.level == logging.WARNING
    finally:
        logger.setLevel(original_level)


def test_configure_external_loggers_does_not_lower_existing_stricter_level():
    logger = logging.getLogger("uvicorn.access")
    original_level = logger.level
    try:
        logger.setLevel(logging.ERROR)
        configure_external_loggers()
        assert logger.level == logging.ERROR
    finally:
        logger.setLevel(original_level)
