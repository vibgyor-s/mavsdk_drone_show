"""Tests for mds_logging.constants — env var reading and deprecation shims."""
import os
import pytest
from unittest.mock import patch
from mds_logging.constants import (
    get_log_level, get_file_log_level, get_max_sessions,
    get_max_size_mb, get_log_dir, get_console_format, get_flush_enabled,
    get_background_pull_enabled, get_pull_interval_sec,
    get_pull_level, get_pull_max_drones,
    DEFAULTS,
)


class TestDefaults:
    def test_default_log_level(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_log_level() == "INFO"

    def test_default_file_log_level(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_file_log_level() == "DEBUG"

    def test_default_max_sessions(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_max_sessions() == 10

    def test_default_max_size_mb(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_max_size_mb() == 100

    def test_default_log_dir(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_log_dir() == "logs/sessions"

    def test_default_console_format(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_console_format() == "text"

    def test_default_flush(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_flush_enabled() is True


class TestEnvOverrides:
    def test_mds_log_level_override(self):
        with patch.dict(os.environ, {"MDS_LOG_LEVEL": "DEBUG"}):
            assert get_log_level() == "DEBUG"

    def test_mds_log_max_sessions_override(self):
        with patch.dict(os.environ, {"MDS_LOG_MAX_SESSIONS": "20"}):
            assert get_max_sessions() == 20

    def test_mds_log_dir_override(self):
        with patch.dict(os.environ, {"MDS_LOG_DIR": "/tmp/test_logs"}):
            assert get_log_dir() == "/tmp/test_logs"


class TestDeprecationShims:
    def test_drone_log_level_fallback(self):
        """Old DRONE_LOG_LEVEL env var still works via shim."""
        with patch.dict(os.environ, {"DRONE_LOG_LEVEL": "WARNING"}, clear=True):
            assert get_log_level() == "WARNING"

    def test_mds_takes_precedence_over_drone(self):
        """New MDS_LOG_LEVEL takes precedence over old DRONE_LOG_LEVEL."""
        with patch.dict(os.environ, {
            "MDS_LOG_LEVEL": "ERROR",
            "DRONE_LOG_LEVEL": "DEBUG",
        }):
            assert get_log_level() == "ERROR"


class TestBackgroundPullDefaults:
    def test_default_background_pull_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_background_pull_enabled() is False

    def test_default_pull_interval(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_pull_interval_sec() == 30

    def test_default_pull_level(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_pull_level() == "WARNING"

    def test_default_pull_max_drones(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_pull_max_drones() == 10

    def test_enable_background_pull(self):
        with patch.dict(os.environ, {"MDS_LOG_BACKGROUND_PULL": "true"}):
            assert get_background_pull_enabled() is True

    def test_custom_pull_interval(self):
        with patch.dict(os.environ, {"MDS_LOG_PULL_INTERVAL_SEC": "60"}):
            assert get_pull_interval_sec() == 60
