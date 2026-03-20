"""Tests for optional background log pull task."""
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

# Add gcs-server to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'gcs-server'))


class TestBackgroundPull:
    @pytest.mark.asyncio
    async def test_pull_disabled_by_default(self):
        from log_background import BackgroundLogPuller
        puller = BackgroundLogPuller(log_dir="/tmp/test")
        assert puller.enabled is False

    @pytest.mark.asyncio
    async def test_pull_stores_entries(self, tmp_path):
        from log_background import BackgroundLogPuller
        drone_log_dir = str(tmp_path / "drone_logs")

        puller = BackgroundLogPuller(log_dir=drone_log_dir)
        puller.enabled = True

        mock_sessions = {
            "sessions": [{"session_id": "s_20260319_100000", "size_bytes": 100}]
        }
        mock_content = {
            "session_id": "s_20260319_100000",
            "count": 1,
            "lines": [
                {"ts": "2026-03-19T10:00:00.000Z", "level": "WARNING",
                 "component": "coord", "source": "drone", "drone_id": 1,
                 "session_id": "s_20260319_100000", "msg": "Low battery"}
            ],
        }

        with patch("log_background.load_config",
                    return_value=[{"hw_id": "1", "ip": "192.168.1.101"}]):
            with patch("log_background.fetch_drone_sessions",
                       new_callable=AsyncMock, return_value=mock_sessions):
                with patch("log_background.fetch_drone_session_content",
                           new_callable=AsyncMock, return_value=mock_content):
                    await puller._pull_once()

        drone_dir = os.path.join(drone_log_dir, "drone_1")
        assert os.path.isdir(drone_dir)
        files = os.listdir(drone_dir)
        assert len(files) == 1
        with open(os.path.join(drone_dir, files[0])) as f:
            line = json.loads(f.readline())
            assert line["msg"] == "Low battery"

    @pytest.mark.asyncio
    async def test_pull_skips_unreachable_drones(self, tmp_path):
        from log_background import BackgroundLogPuller
        puller = BackgroundLogPuller(log_dir=str(tmp_path))
        puller.enabled = True

        with patch("log_background.load_config",
                    return_value=[{"hw_id": "1", "ip": "192.168.1.101"}]):
            with patch("log_background.fetch_drone_sessions",
                       new_callable=AsyncMock, return_value=None):
                # Should not raise
                await puller._pull_once()

    @pytest.mark.asyncio
    async def test_enable_disable_runtime(self):
        from log_background import BackgroundLogPuller
        puller = BackgroundLogPuller(log_dir="/tmp/test")
        assert puller.enabled is False
        puller.set_enabled(True)
        assert puller.enabled is True
        puller.set_enabled(False)
        assert puller.enabled is False
