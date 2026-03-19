"""Tests for mds_logging.watcher — in-memory pub/sub for SSE."""
import asyncio
import pytest
from mds_logging.watcher import LogWatcher


class TestLogWatcher:
    def test_publish_to_empty_watcher(self):
        """Publishing with no subscribers should not error."""
        watcher = LogWatcher()
        watcher.publish({"msg": "test"})  # no error

    def test_buffer_stores_recent_entries(self):
        watcher = LogWatcher(max_buffer=5)
        for i in range(10):
            watcher.publish({"msg": f"entry_{i}"})
        assert len(watcher._buffer) == 5
        assert watcher._buffer[0]["msg"] == "entry_5"

    @pytest.mark.asyncio
    async def test_subscribe_receives_published(self):
        watcher = LogWatcher()
        received = []

        async def consumer():
            async for entry in watcher.subscribe():
                received.append(entry)
                if len(received) >= 3:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        for i in range(3):
            watcher.publish({"msg": f"live_{i}"})
        await asyncio.wait_for(task, timeout=2.0)
        assert len(received) == 3

    @pytest.mark.asyncio
    async def test_subscribe_with_level_filter(self):
        watcher = LogWatcher()
        received = []

        async def consumer():
            async for entry in watcher.subscribe(level="ERROR"):
                received.append(entry)
                if len(received) >= 1:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        watcher.publish({"level": "INFO", "msg": "skip"})
        watcher.publish({"level": "ERROR", "msg": "catch"})
        await asyncio.wait_for(task, timeout=2.0)
        assert received[0]["msg"] == "catch"
